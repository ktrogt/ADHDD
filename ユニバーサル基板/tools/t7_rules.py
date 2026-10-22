"""Adapter for T7 adhdd-perfboard-rules/1.0. Never silently accepts missing evidence.

The canonical v1 engine is deliberately small. This adapter retains T7's richer
requirements, reports unsupported geometry/assembly checks as UNCHECKED, and
implements the parts that can be proved using the provided model.
"""
from __future__ import annotations

import copy
import math

from model import EPS, distance, number, point, rect_distance, require
from verify import issue, net_graph, shortest


class Unchecked(Exception):
    pass


def evaluate_t7(p, *, placement_only=False):
    from rules import select
    out, ids = [], set()

    def resolve(selector):
        if selector.startswith("$"):
            name = selector[1:]
            definition = p.rules.get("nodes", {}).get(name)
            if not definition:
                raise Unchecked(f"undefined node {selector}")
            anchor = resolve(definition["anchor"])
            declaration = p.placement.get("nodes", {}).get(name)
            if declaration is None:
                raise Unchecked(f"placement.nodes.{name} must declare the physical junction hole; anchor {definition['anchor']} is at {anchor}")
            xy = point(declaration if isinstance(declaration, str) else declaration["hole"])
            if xy != anchor:
                raise Unchecked(f"node {name} is not at anchor {definition['anchor']}; remote node links need explicit branch evidence")
            return xy
        if "." in selector:
            ref, pn = selector.split(".", 1)
            return p.pin_at(f"{ref}.#{pn}" if pn.isdigit() else selector)
        return p.pin_at(selector)

    def parts(selector):
        if selector == "all_populated":
            return sorted(p.parts)
        return select(p, selector if isinstance(selector, list) else [selector], "part")

    def inferred_net(selector):
        if selector.startswith("$"):
            return p.rules["nodes"][selector[1:]]["net"]
        xy = resolve(selector)
        matches = {q.net for q in p.pins.values() if q.xy == xy}
        if len(matches) != 1 or "NC" in matches:
            raise Unchecked(f"cannot resolve a unique named net for {selector}")
        return next(iter(matches))

    for rule in p.rules.get("rules", []):
        rid, kind = rule.get("id"), rule.get("type")
        require(isinstance(rid, str) and rid and rid not in ids, f"T7 rule ID missing/duplicated: {rid}")
        ids.add(rid)
        require(rule.get("severity") in ("hard", "soft"), f"T7 {rid}: hard/soft severity required")
        severity = "error" if rule["severity"] == "hard" else "warning"
        params = rule.get("params", {})

        def emit(detail, status="FAIL", measured=None, bound=None, **context):
            # Preserve T7 weight/priority for lexicographic policy consumers.
            weight = number(rule.get("weight", 0), f"T7 {rid}.weight", 0)
            penalty = weight if measured is None or bound is None else weight * max(0, abs(measured - bound) / (bound or 1))
            out.append(issue("RULE:" + rid, detail, severity, status=status, rule_type=kind, priority=rule.get("priority"), rule_severity=rule["severity"], t7_weight=weight, t7_penalty=0 if status == "UNCHECKED" else penalty, **context))

        def val(name):
            return number(params.get(name), f"T7 {rid}.{name}", 0)

        try:
            if kind == "connectivity":
                # Core verifier always performs scoped CSV comparison, but we must
                # not pretend it proved derivation/approval of the scoped CSV.
                raise Unchecked("core LVS checks project/netlist.csv; approval/provenance of the main_minus_scaffold scope requires supervisor evidence")
            elif kind == "near":
                require(params.get("metric") == "manhattan_pin", f"T7 {rid}: unsupported near metric")
                bound = val("max_holes")
                for pair in params["pairs"]:
                    a, b = resolve(pair["a"]), resolve(pair["b"])
                    measured = abs(a[0] - b[0]) + abs(a[1] - b[1])
                    if measured > bound + EPS:
                        emit(f"{pair['a']} / {pair['b']}: {measured} holes > {bound}", measured=measured, bound=bound)
            elif kind == "min_part_distance":
                require(params.get("metric") == "body_edge_euclidean", f"T7 {rid}: unsupported body metric")
                bound, seen = val("min_holes"), set()
                for a in parts(params["a"]):
                    for b in parts(params["b"]):
                        pair = tuple(sorted((a, b)))
                        if a == b or pair in seen:
                            continue
                        seen.add(pair)
                        measured = rect_distance(p.parts[a].rect, p.parts[b].rect) / p.pitch
                        if measured < bound - EPS:
                            emit(f"{a} / {b}: body gap {measured:.3f} holes < {bound}", measured=measured, bound=bound)
            elif kind == "on_edge":
                bound = val("max_holes")
                reference = params.get("reference", "board_edge")
                for name in parts(params["parts"]):
                    try:
                        feature = p.feature_at(name, params["feature"])
                        measured = p.edge_distance(feature["xy_mm"], params["edges"], reference) / p.pitch
                    except (ValueError, KeyError) as error:
                        emit(str(error), "UNCHECKED", part=name, reference=reference)
                        continue
                    if measured > bound + EPS:
                        emit(f"{name}.{params['feature']}: {measured:.3f} holes from {reference} > {bound}", measured=measured, bound=bound, part=name, reference=reference)
            elif kind == "accessible" and "approach_by_part" in params:
                # Approach selection is implemented, but current footprints do not
                # declare a complete 3D plug/latch/grip swept volume. Do not turn
                # a top-mating connector into a failing outward corridor check.
                approaches = params.get("approach_by_part", {})
                require(isinstance(approaches, dict), f"T7 {rid}: approach_by_part must be an object")
                for name in parts(params["targets"]):
                    approach = approaches.get(name, approaches.get(p.parts[name].ref, params.get("approach")))
                    require(approach in ("top", "outward", "two_sides"), f"T7 {rid}: unsupported approach {approach!r} for {name}")
                    emit(f"{name}: approach={approach}; {params.get('feature')} needs a declared 3D mating/access envelope and wire heights; planar body bounds cannot prove access", "UNCHECKED", part=name, approach=approach, feature=params.get("feature"))
            elif kind == "max_branch_length":
                bound = val("max_holes")
                if params.get("include_offboard"):
                    raise Unchecked("off-board harness lengths are not represented by hole-coordinate paths")
                for pair in params["pairs"]:
                    a, b = resolve(pair["a"]), resolve(pair["b"])
                    na, nb = inferred_net(pair["a"]), inferred_net(pair["b"])
                    require(na == nb and ("net" not in params or params["net"] == na), f"T7 {rid}: endpoints do not share the declared net")
                    if placement_only:
                        continue
                    value = shortest(net_graph(p, na), a).get(b)
                    measured = value / p.pitch if value is not None else None
                    if measured is None or measured > bound + EPS:
                        emit(f"{pair['a']} -> {pair['b']}: {'OPEN' if measured is None else f'{measured:.3f} holes'} (max {bound})", measured=measured, bound=bound)
            elif kind == "star":
                root, net = resolve(params["root"]), params["net"]
                require(net in p.nets, f"T7 {rid}: unknown star net")
                if params.get("max_shared_holes") != 0:
                    raise Unchecked("nonzero allowed shared star length is not implemented")
                branches = []
                for branch in params["branches"]:
                    for s in branch["endpoints"]:
                        require(inferred_net(s) == net, f"T7 {rid}: branch endpoint not on {net}")
                    branches.append((branch["id"], [(s, resolve(s)) for s in branch["endpoints"]]))
                if placement_only:
                    continue
                graph = net_graph(p, net)
                reachable, reduced = shortest(graph, root), {a: {b: v for b, v in edges.items() if b != root} for a, edges in graph.items() if a != root}
                for branchid, endpoints in branches:
                    for s, xy in endpoints:
                        if xy not in reachable:
                            emit(f"{branchid} {s} is OPEN from {params['root']}")
                for i, (aid, aa) in enumerate(branches):
                    for bid, bb in branches[i + 1:]:
                        for sa, a in aa:
                            paths = shortest(reduced, a) if a != root else {}
                            for sb, b in bb:
                                if b != root and b in paths:
                                    emit(f"{aid}:{sa} and {bid}:{sb} share copper beyond root {params['root']}")
            elif kind == "group":
                require(params.get("metric") == "pin_bbox_max_dimension", f"T7 {rid}: unsupported group metric")
                names, bound = parts(params["parts"]), val("max_span_holes")
                coords = [q.xy for name in names for q in p.parts[name].pins]
                measured = max(max(x for x, y in coords) - min(x for x, y in coords), max(y for x, y in coords) - min(y for x, y in coords))
                if measured > bound + EPS:
                    emit(f"pin bbox span {measured} holes > {bound}", measured=measured, bound=bound)
            elif kind == "orientation" and params.get("mode") == "same_rotation":
                names = parts(params["parts"])
                angles = {p.parts[name].data.get("rotation", 0) for name in names}
                if len(angles) > 1 or not angles <= set(params["allowed_degrees"]):
                    emit(f"rotation mismatch: {sorted(angles)}")
            elif kind == "max_jumpers":
                require(params.get("count_policy") == "insulated_point_to_point", f"T7 {rid}: unsupported jumper policy")
                bound = val("max_count")
                if placement_only:
                    continue
                measured = sum(c["kind"] == "jumper" for c in p.conductors)
                if measured > bound:
                    emit(f"{measured} jumpers > {bound}", measured=measured, bound=bound)
            elif kind == "order":
                seq, bound = params["sequence"], 0
                centroids = []
                for item in seq:
                    names = parts("@" + item if item in p.rules.get("groups", {}) else item)
                    pins = [q.xy for name in names for q in p.parts[name].pins]
                    centroids.append(tuple(sum(q[k] for q in pins) / len(pins) for k in (0, 1)))
                axes = [0, 1] if params["axis"] == "either" else [0 if params["axis"] == "x" else 1]
                valid = False
                for axis in axes:
                    values = [c[axis] for c in centroids]
                    valid |= all(a <= b for a, b in zip(values, values[1:])) or (params.get("allow_reverse") and all(a >= b for a, b in zip(values, values[1:])))
                if not valid:
                    emit("functional-block centroids are not monotonic in the requested axis")
            elif kind == "routing" and params.get("check") == "signal_bends":
                names, bound = set(params["nets"]), val("max_bends_per_branch")
                if placement_only:
                    continue
                # This check is per declared conductor. Multi-conductor electrical
                # branches need branch IDs, hence cannot be accepted from this alone.
                for c in p.conductors:
                    if c["net"] in names and len(c["xy"]) - 2 > bound:
                        emit(f"{c['id']}: {len(c['xy']) - 2} bends > {bound}", measured=len(c["xy"]) - 2, bound=bound)
                raise Unchecked("per-conductor bends checked; complete branch IDs and preferred-material policy are not represented")
            else:
                raise Unchecked(f"T7 {kind}/{params.get('check', '')}: requires feature, branch, surface-clearance, off-board or assembly evidence beyond v1 hole paths")
        except (Unchecked, KeyError, ValueError) as error:
            emit(str(error), "UNCHECKED")
    return out
