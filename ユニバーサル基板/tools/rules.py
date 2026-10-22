"""Fail-closed, data-driven layout rule engine (interface v1)."""
from __future__ import annotations

import fnmatch
import math
import re

from model import EPS, distance, number, rect_distance, require, segment_distance
from verify import issue, net_graph, shortest

TYPES = {"min_part_distance", "near_pin", "max_net_length", "max_branch_length", "net_clearance", "edge", "star", "wire_gauge"}
WEIGHTS = {"wire_mm", "jumpers", "bridges", "crossings", "area_mm2", "error", "warning", "info"}


def select(p, patterns, kind):
    require(isinstance(patterns, list) and bool(patterns) and all(isinstance(x, str) for x in patterns), f"{kind} selectors must be a nonempty string array")
    universe = sorted(p.parts) if kind == "part" else p.nets
    definitions = p.rules.get("groups" if kind == "part" else "net_classes", {})
    selected = set()

    def add(pattern, stack=()):
        if pattern.startswith("@"):
            key = pattern[1:]
            require(key in definitions, f"unknown {kind} group {pattern}")
            require(key not in stack, f"recursive {kind} group {pattern}")
            require(isinstance(definitions[key], list), f"{kind} group {pattern} must be array")
            for child in definitions[key]:
                add(child, stack + (key,))
            return
        matches = [name for name in universe if fnmatch.fnmatchcase(name, pattern) or (kind == "part" and fnmatch.fnmatchcase(p.parts[name].ref, pattern))]
        require(matches, f"{kind} selector {pattern!r} matches nothing")
        selected.update(matches)

    for pattern in patterns:
        add(pattern)
    require(selected, f"empty {kind} selection")
    return sorted(selected)


def net_pieces(p, names):
    pieces = []
    for c in p.conductors:
        if c["net"] in names:
            pieces.extend(zip(c["xy"], c["xy"][1:]))
    pieces.extend((q.xy, q.xy) for q in p.pins.values() if q.net in names)
    return pieces


def area_from_wire(c):
    if "area_mm2" in c:
        return number(c["area_mm2"], c["id"] + ".area_mm2", 0.00001), None
    match = re.fullmatch(r"AWG\s*([0-9]+(?:\.[0-9]+)?)", str(c.get("gauge", "")).upper())
    if not match:
        return None, None
    awg = float(match[1])
    require(0 <= awg <= 50, f"{c['id']}: AWG outside supported range 0..50")
    diameter = 0.127 * 92 ** ((36 - awg) / 39)
    return math.pi * diameter * diameter / 4, awg


def evaluate(p, *, placement_only=False):
    if p.rules.get("schema_version") == "adhdd-perfboard-rules/1.0":
        from t7_rules import evaluate_t7
        return evaluate_t7(p, placement_only=placement_only)
    require(isinstance(p.rules.get("rules", []), list), "rules.rules must be an array")
    for key, value in p.rules.get("weights", {}).items():
        require(key in WEIGHTS, f"unknown score weight {key}")
        number(value, f"weight.{key}", 0)
    out, ids = [], set()
    for r in p.rules.get("rules", []):
        rid, kind = r.get("id"), r.get("type")
        require(isinstance(rid, str) and rid and rid not in ids, f"rule id missing or duplicated: {rid}")
        ids.add(rid)
        require(kind in TYPES, f"rule {rid}: unsupported type {kind!r}")
        require(type(r.get("enabled", True)) is bool, f"rule {rid}: enabled must be boolean")
        severity = r.get("severity", "error")
        require(severity in ("error", "warning", "info"), f"rule {rid}: invalid severity")
        if not r.get("enabled", True):
            continue

        def emit(detail, **kwargs):
            out.append(issue("RULE:" + rid, detail, severity, rule_type=kind, **kwargs))

        def val(key):
            return number(r.get(key), f"rule {rid}.{key}", 0)

        def net():
            require(r.get("net") in p.nets, f"rule {rid}: unknown net {r.get('net')}")
            return r["net"]

        if kind == "min_part_distance":
            aa, bb, threshold = select(p, r.get("a"), "part"), select(p, r.get("b"), "part"), val("min_mm")
            seen = set()
            for a in aa:
                for b in bb:
                    pair = tuple(sorted((a, b)))
                    if a == b or pair in seen:
                        continue
                    seen.add(pair)
                    measured = rect_distance(p.parts[a].rect, p.parts[b].rect)
                    if measured < threshold - EPS:
                        emit(f"{a} / {b}: {measured:.3f} mm < {threshold} mm", parts=[a, b], measured_mm=measured)
        elif kind == "near_pin":
            parts, target, threshold = select(p, r.get("parts"), "part"), p.pin_at(r["pin"]), val("max_holes")
            for name in parts:
                measured = min(distance(q.xy, target) for q in p.parts[name].pins)
                if measured > threshold + EPS:
                    emit(f"{name} to {r['pin']}: {measured:.3f} holes > {threshold}", part=name, measured_holes=measured)
        elif kind == "edge":
            parts, threshold = select(p, r.get("parts"), "part"), val("max_holes")
            edge = r.get("edge", "any")
            require(edge in ("top", "bottom", "left", "right", "any"), f"rule {rid}: invalid edge")
            for name in parts:
                x0, y0, x1, y1 = p.parts[name].rect
                gaps = dict(left=x0 + p.pitch / 2, top=y0 + p.pitch / 2, right=(p.columns - 0.5) * p.pitch - x1, bottom=(p.rows - 0.5) * p.pitch - y1)
                measured = (min(gaps.values()) if edge == "any" else gaps[edge]) / p.pitch
                if measured > threshold + EPS:
                    emit(f"{name}: {measured:.3f} holes from {edge} edge > {threshold}", part=name, measured_holes=measured)
        elif kind == "max_net_length":
            name, threshold = net(), val("max_mm")
            if placement_only:
                continue
            measured = sum(c["length_mm"] for c in p.conductors if c["net"] == name)
            if measured > threshold + EPS:
                emit(f"{name}: total {measured:.3f} mm > {threshold}", measured_mm=measured)
        elif kind == "max_branch_length":
            name, threshold = net(), val("max_mm")
            source, targets = p.pin_at(r["from"]), r.get("to")
            require(isinstance(targets, list) and targets, f"rule {rid}: nonempty to array required")
            targets = [(s, p.pin_at(s)) for s in targets]
            if placement_only:
                continue
            costs = shortest(net_graph(p, name), source)
            for selector, target in targets:
                measured = costs.get(target)
                if measured is None or measured > threshold + EPS:
                    emit(f"{name} {r['from']} -> {selector}: {'OPEN' if measured is None else f'{measured:.3f} mm'} (max {threshold} mm)", measured_mm=measured)
        elif kind == "net_clearance":
            aa, bb, threshold = select(p, r.get("a"), "net"), select(p, r.get("b"), "net"), val("min_holes")
            require(not set(aa) & set(bb), f"rule {rid}: net clearance selections overlap")
            for a in aa:
                for b in bb:
                    ap = [(q.xy, q.xy) for q in p.pins.values() if q.net == a] if placement_only else net_pieces(p, {a})
                    bp = [(q.xy, q.xy) for q in p.pins.values() if q.net == b] if placement_only else net_pieces(p, {b})
                    measured = min((segment_distance(x, y, z, w) for x, y in ap for z, w in bp), default=float("inf"))
                    if measured < threshold - EPS:
                        emit(f"{a} / {b}: projected spacing {measured:.3f} holes < {threshold}", nets=[a, b], measured_holes=measured)
        elif kind == "star":
            name, source = net(), p.pin_at(r["root"])
            require(isinstance(r.get("targets"), list) and len(r["targets"]) >= 2, f"rule {rid}: >= 2 targets required")
            targets = [(s, p.pin_at(s)) for s in r["targets"]]
            require(len({xy for _, xy in targets}) == len(targets) and source not in {xy for _, xy in targets}, f"rule {rid}: root/targets must be distinct")
            if placement_only:
                continue
            graph = net_graph(p, name)
            reachable = shortest(graph, source)
            for s, xy in targets:
                if xy not in reachable:
                    emit(f"{s} not connected to root {r['root']}")
            visited, components = set(), {}
            for xy in sorted(graph):
                if xy == source or xy in visited:
                    continue
                stack, marker = [xy], xy
                while stack:
                    node = stack.pop()
                    if node in visited or node == source:
                        continue
                    visited.add(node)
                    components[node] = marker
                    stack.extend(graph[node])
            for i, (sa, a) in enumerate(targets):
                for sb, b in targets[i + 1:]:
                    if a in components and components.get(a) == components.get(b):
                        emit(f"{sa} and {sb} share branch beyond root {r['root']}")
        elif kind == "wire_gauge":
            names = select(p, r.get("nets"), "net")
            require(any(k in r for k in ("max_awg", "min_area_mm2", "ampacity_a_per_mm2")), f"rule {rid}: gauge/area/current constraint required")
            for k in ("max_awg", "min_area_mm2", "current_a", "ampacity_a_per_mm2"):
                if k in r:
                    val(k)
            minimum = r.get("min_area_mm2", 0)
            if "ampacity_a_per_mm2" in r:
                require("current_a" in r and r["ampacity_a_per_mm2"] > 0, f"rule {rid}: positive ampacity density and current_a required")
                minimum = max(minimum, r["current_a"] / r["ampacity_a_per_mm2"])
            if placement_only:
                continue
            for c in p.conductors:
                if c["net"] not in names:
                    continue
                area, awg = area_from_wire(c)
                if area is None:
                    emit(f"{c['id']} {c['net']}: unknown conductor size")
                elif area < minimum - EPS or ("max_awg" in r and area < math.pi * (0.127 * 92 ** ((36 - r["max_awg"]) / 39)) ** 2 / 4 - EPS):
                    emit(f"{c['id']} {c['net']}: {area:.4f} mm2 does not meet required gauge/area", conductor=c["id"], area_mm2=area)
    # A T7 subset is useful for screening, but its missing policy must stay visible.
    for rid in p.rules.get("uncovered_rule_ids", []):
        out.append(issue("RULE:RESIDUAL_" + rid, "Full T7 policy rule is outside the supplied subset", "error", rule_type="policy_coverage", status="UNCHECKED", original_rule_id=rid))
    for rid in p.rules.get("partially_covered_rule_ids", []):
        out.append(issue("RULE:RESIDUAL_" + rid, p.rules.get("residual_requirements", "Full T7 rule is only partially checked"), "error", rule_type="policy_coverage", status="UNCHECKED", original_rule_id=rid))
    return out
