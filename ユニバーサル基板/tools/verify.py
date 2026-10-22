"""Geometry-derived electrical extraction, DRC/LVS and measurable metrics."""
from __future__ import annotations

import heapq
from collections import Counter, defaultdict

from model import (COMPARE, EPS, distance, hole, rect_intersects,
                   segment_distance, write_csv)


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != x:
            old = self.parent[x]
            self.parent[x] = root
            x = old
        return root

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def issue(code, detail, severity="error", **context):
    return dict(code=code, severity=severity, detail=detail, **context)


def placement_drc(p):
    out = []
    allowed = p.body_allowed_rect
    occupied = defaultdict(list)
    for pin in p.pins.values():
        occupied[pin.xy].append(pin)
        if not p.usable(pin.xy):
            out.append(issue("PIN_OFFBOARD_OR_KEEPOUT", f"{pin.label} at {hole(pin.xy)}", part=pin.part, hole=hole(pin.xy)))
    for xy, pins in occupied.items():
        if len(pins) > 1:
            out.append(issue("PIN_COLLISION", f"{hole(xy)} occupied by {', '.join(q.label for q in pins)}"))
    for xy, label in p.reserved_pads.items():
        if xy in occupied:
            out.append(issue("RESERVED_PAD_COLLISION", f"{label} collides with pin at {hole(xy)}"))
        if not p.usable(xy):
            out.append(issue("PIN_OFFBOARD_OR_KEEPOUT", f"{label} at {hole(xy)}"))
    parts = list(p.parts.values())
    for i, part in enumerate(parts):
        r = part.rect
        if r[0] < allowed[0] - EPS or r[1] < allowed[1] - EPS or r[2] > allowed[2] + EPS or r[3] > allowed[3] + EPS:
            out.append(issue("BODY_OFFBOARD", part.id, part=part.id))
        for a, b, name in p.keepouts:
            ko = ((a[0] - 0.5) * p.pitch, (a[1] - 0.5) * p.pitch, (b[0] + 0.5) * p.pitch, (b[1] + 0.5) * p.pitch)
            if rect_intersects(r, ko):
                out.append(issue("BODY_KEEPOUT", f"{part.id} intersects {name}", part=part.id))
        for other in parts[i + 1:]:
            if rect_intersects(r, other.rect, p.board.get("body_clearance_mm", 0.5)):
                out.append(issue("BODY_OVERLAP", f"{part.id} / {other.id}", parts=[part.id, other.id]))
        if part.footprint.get("provisional"):
            out.append(issue("PROVISIONAL_FOOTPRINT", part.id, "warning", part=part.id))
        if part.footprint.get("requires_Claude_approval") and not part.data.get("substitution_approved", False):
            out.append(issue("PROPOSED_SUBSTITUTION", f"{part.id}: T5 proposal requires supervisor approval", part=part.id))
    return out


def net_graph(p, net):
    """Weighted physical graph; exposed wires split at every contacted grid hole.

    Jumper interiors are private vertices, even if they pass through another hole.
    Endpoint coordinate vertices are shared by soldered terminals.
    """
    graph = defaultdict(dict)

    def edge(a, b, length):
        graph[a][b] = min(graph[a].get(b, float("inf")), length)
        graph[b][a] = min(graph[b].get(a, float("inf")), length)

    for c in p.conductors:
        if c["net"] != net:
            continue
        if c["kind"] == "jumper":
            edge(c["contacts"][0], c["contacts"][-1], c["length_mm"])
        else:
            for a, b in zip(c["contacts"], c["contacts"][1:]):
                edge(a, b, p.pitch)
    for pin in p.pins.values():
        if pin.net == net:
            graph.setdefault(pin.xy, {})
    return graph


def shortest(graph, source):
    best, queue = {source: 0.0}, [(0.0, source)]
    while queue:
        cost, xy = heapq.heappop(queue)
        if cost > best[xy] + EPS:
            continue
        for target, weight in graph.get(xy, {}).items():
            value = cost + weight
            if value < best.get(target, float("inf")) - EPS:
                best[target] = value
                heapq.heappush(queue, (value, target))
    return best


def extract(p):
    uf = UnionFind()
    contacts = defaultdict(list)
    for pin in p.pins.values():
        uf.find(pin.xy)
    for i, c in enumerate(p.conductors):
        for xy in c["contacts"]:
            contacts[xy].append(i)
            uf.union(c["contacts"][0], xy)
    grouped_pins, grouped_wires = defaultdict(list), defaultdict(list)
    for pin in p.pins.values():
        grouped_pins[uf.find(pin.xy)].append(pin)
    for i, c in enumerate(p.conductors):
        grouped_wires[uf.find(c["contacts"][0])].append(i)
    out, actual, components = [], {}, []
    used_labels = set(p.nets) | {"NC"}
    allocated = set()
    count = 0
    for root in sorted(set(grouped_pins) | set(grouped_wires)):
        pins, indices = grouped_pins[root], grouped_wires[root]
        claims = {p.conductors[i]["net"] for i in indices}
        expected_nets = {pin.net for pin in pins if pin.net != "NC"}
        nc = [pin for pin in pins if pin.net == "NC"]
        for pin in nc:
            if indices or len(pins) > 1:
                out.append(issue("NC_CONNECTED", f"{pin.label} has physical connection at {hole(pin.xy)}"))
        if not pins:
            out.append(issue("FLOATING_CONDUCTOR", f"{', '.join(p.conductors[i]['id'] for i in indices)} has no component terminal"))
        if len(expected_nets) > 1 or (nc and (len(pins) > 1 or indices)) or len(claims) > 1:
            out.append(issue("SHORT", f"physical island joins {', '.join(sorted(expected_nets | claims))}" + (" and NC" if nc else ""), pins=[pin.label for pin in pins], conductors=[p.conductors[i]["id"] for i in indices]))
        if claims and expected_nets and claims != expected_nets:
            out.append(issue("WIRE_NET_MISMATCH", f"labels {sorted(claims)} meet expected pins on {sorted(expected_nets)}", pins=[pin.label for pin in pins]))
        if len(pins) == 1 and nc and not indices:
            label = "NC"
        elif len(expected_nets | claims) == 1 and not nc:
            label = next(iter(expected_nets | claims))
            if label in allocated:
                count += 1
                label = f"__OPEN_{count}"
                while label in used_labels:
                    count += 1
                    label = f"__OPEN_{count}"
            else:
                allocated.add(label)
        else:
            count += 1
            label = f"__ISLAND_{count}"
            while label in used_labels:
                count += 1
                label = f"__ISLAND_{count}"
        for pin in pins:
            actual[pin.key] = pin.row(label)
        components.append(dict(actual_net=label, pins=sorted(pin.label for pin in pins), expected_nets=sorted(expected_nets), conductor_nets=sorted(claims), conductors=[p.conductors[i]["id"] for i in indices]))
    return out, actual, components, contacts, uf


def wiring_drc(p, contacts):
    out = []
    claims = defaultdict(set)
    for pin in p.pins.values():
        claims[pin.xy].add(pin.net if pin.net != "NC" else f"NC:{pin.label}")
    for xy, indices in contacts.items():
        claims[xy].update(p.conductors[i]["net"] for i in indices)
        if xy in p.reserved_pads:
            out.append(issue("EXTRA_PAD_CONNECTED", f"{p.reserved_pads[xy]} at {hole(xy)} must remain unconnected"))
    for xy, nets in sorted(claims.items()):
        if len(nets) > 1:
            out.append(issue("HOLE_NET_CONFLICT", f"{hole(xy)}: {', '.join(sorted(nets))}", hole=hole(xy), nets=sorted(nets)))
    for c in p.conductors:
        if c["net"] not in p.nets:
            out.append(issue("UNKNOWN_WIRE_NET", f"{c['id']}: {c['net']}"))
        if c["kind"] != "jumper" and c["side"] == "top" and p.board.get("type", "single_sided_independent") != "double_sided_plated":
            out.append(issue("UNSUPPORTED_TOP_EXPOSED", f"{c['id']}: single-sided board requires bottom bare/bridge"))
        bad = [hole(xy) for xy in (c["contacts"] if c["kind"] != "jumper" else c["xy"]) if not p.usable(xy)]
        if bad:
            out.append(issue("WIRE_OFFBOARD_OR_KEEPOUT", f"{c['id']}: {', '.join(bad)}", conductor=c["id"]))
        if c["kind"] == "jumper":
            for a, b, name in p.keepouts:
                corners = [(a[0] - 0.5, a[1] - 0.5), (b[0] + 0.5, a[1] - 0.5), (b[0] + 0.5, b[1] + 0.5), (a[0] - 0.5, b[1] + 0.5)]
                if any(segment_distance(x, y, c0, c1) < EPS for x, y in zip(c["xy"], c["xy"][1:]) for c0, c1 in zip(corners, corners[1:] + corners[:1])):
                    out.append(issue("WIRE_KEEPOUT", f"{c['id']} crosses {name}"))
    for i, a in enumerate(p.conductors):
        if a["kind"] == "jumper":
            continue
        aset = set(a["contacts"])
        for b in p.conductors[i + 1:]:
            if b["kind"] == "jumper" or a["net"] == b["net"]:
                continue
            shared = aset & set(b["contacts"])
            if shared:
                code = "BARE_CROSSING" if a["side"] == b["side"] else "PLATED_HOLE_SHORT"
                out.append(issue(code, f"{a['id']} / {b['id']} touch at {', '.join(hole(xy) for xy in sorted(shared))}", conductors=[a["id"], b["id"]]))
    return out


def metrics(p, issues=(), *, lvs_ok=None):
    lengths = {k: 0.0 for k in ("bare", "bridge", "jumper")}
    net_lengths = Counter()
    for c in p.conductors:
        lengths[c["kind"]] += c["length_mm"]
        net_lengths[c["net"]] += c["length_mm"]
    crossings = 0
    for a in p.conductors:
        if a["kind"] != "jumper":
            continue
        for b in p.conductors:
            if b["kind"] == "jumper" or a["net"] == b["net"]:
                continue
            # Count intersecting segment pairs, excluding soldered jumper endpoints.
            for x, y in zip(a["xy"], a["xy"][1:]):
                for z, w in zip(b["xy"], b["xy"][1:]):
                    if segment_distance(x, y, z, w) < EPS:
                        crossings += 1
    rectangles = [part.rect for part in p.parts.values()]
    for c in p.conductors:
        for x, y in c["xy"]:
            rectangles.append((x * p.pitch, y * p.pitch, x * p.pitch, y * p.pitch))
    bbox = [min(r[0] for r in rectangles), min(r[1] for r in rectangles), max(r[2] for r in rectangles), max(r[3] for r in rectangles)] if rectangles else [0, 0, 0, 0]
    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    power_paths = []
    # Explicit roots override defaults. Report only actual reachable paths; no inferred connections through components.
    roots = p.rules.get("power_roots", {"VM": "J104.VM", "GND": "J101.SLEEVE"})
    for net, source in roots.items():
        try:
            xy = p.pin_at(source)
        except ValueError:
            continue
        costs = shortest(net_graph(p, net), xy)
        for pin in p.pins.values():
            if pin.ref.startswith("U3") and pin.net == net and pin.name in ("VIN", "GND@2", "GND@13"):
                power_paths.append(dict(net=net, source=source, target=pin.label, length_mm=round(costs[pin.xy], 3) if pin.xy in costs else None))
    severity = Counter(i["severity"] for i in issues)
    rule_severity = Counter(i["severity"] for i in issues if i["code"].startswith("RULE:"))
    result = dict(wire_length_mm={k: round(v, 3) for k, v in lengths.items()}, total_wire_mm=round(sum(lengths.values()), 3), jumpers=sum(c["kind"] == "jumper" for c in p.conductors), bridges=sum(c["kind"] == "bridge" for c in p.conductors), conductors=len(p.conductors), jumper_over_exposed_crossings=crossings, bbox_mm=[round(v, 3) for v in bbox], used_bbox_area_mm2=round(area, 3), used_area_fraction=round(area / (p.columns * p.rows * p.pitch ** 2), 5), power_path_lengths=power_paths, longest_signal_nets=[dict(net=n, length_mm=round(v, 3)) for n, v in net_lengths.most_common() if n not in {"VM", "GND", "+5V", "+3V3", "VSYS", "VIN_RAW", "VIN_FUSED", "VIN_PROT"}][:10], violations_by_severity=dict(severity), rule_violations_by_severity=dict(rule_severity))
    weights = dict(wire_mm=1, jumpers=20, bridges=1, crossings=2, area_mm2=0.01, error=100000, warning=1000, info=0)
    weights.update(p.rules.get("weights", {}))
    result["score"] = round(sum(lengths.values()) * weights["wire_mm"] + result["jumpers"] * weights["jumpers"] + result["bridges"] * weights["bridges"] + crossings * weights["crossings"] + area * weights["area_mm2"] + sum(severity[s] * weights[s] for s in ("error", "warning", "info")), 3)
    result["score_weights"] = weights
    if lvs_ok is None:
        electrical, actual, _, contacts, _ = extract(p)
        lvs_ok = not electrical and not COMPARE.compare(p.expected, actual, "name") and not any(i["severity"] == "error" for i in wiring_drc(p, contacts))
    from scoring import comparison
    result.update(comparison(p, issues, lvs_ok, jumpers=result["jumpers"], total_length=result["total_wire_mm"]))
    return result


def verify(p, *, check_rules=True):
    from rules import evaluate
    issues, actual, components, contacts, uf = extract(p)
    issues = placement_drc(p) + wiring_drc(p, contacts) + issues
    compared = COMPARE.compare(p.expected, actual, "name")
    issues.extend(issue("LVS:" + code, detail) for code, detail in compared)
    if check_rules:
        issues.extend(evaluate(p))
    issues.sort(key=lambda x: ({"error": 0, "warning": 1, "info": 2}[x["severity"]], x["code"], x["detail"]))
    lvs_codes = {"SHORT", "NC_CONNECTED", "EXTRA_PAD_CONNECTED", "RESERVED_PAD_COLLISION", "WIRE_NET_MISMATCH", "UNKNOWN_WIRE_NET", "FLOATING_CONDUCTOR", "HOLE_NET_CONFLICT", "BARE_CROSSING", "PLATED_HOLE_SHORT", "UNSUPPORTED_TOP_EXPOSED"}
    lvs_ok = not compared and not any(i["code"] in lvs_codes for i in issues)
    rule_checks = []
    for rule in p.rules.get("rules", []):
        found = [i for i in issues if i["code"] == "RULE:" + rule["id"]]
        status = "DISABLED" if not rule.get("enabled", True) else "UNCHECKED" if not check_rules or any(i.get("status") == "UNCHECKED" for i in found) else "FAIL" if found else "PASS"
        failures = sum(i.get("status") != "UNCHECKED" for i in found)
        # Newly implemented on_edge is checked per part: a missing header feature
        # must not hide a measured, real failure on another connector.
        if rule["type"] == "on_edge" and failures and status != "DISABLED":
            status = "FAIL"
        rule_checks.append(dict(id=rule["id"], type=rule["type"], status=status, findings=len(found), fail_findings=failures, unchecked_findings=sum(i.get("status") == "UNCHECKED" for i in found)))
    present_ids = {r["id"] for r in rule_checks}
    for finding in issues:
        if finding["code"].startswith("RULE:") and finding["code"][5:] not in present_ids:
            rid = finding["code"][5:]
            rule_checks.append(dict(id=rid, type=finding.get("rule_type", "unknown"), status=finding.get("status", "FAIL"), findings=1))
            present_ids.add(rid)
    report = dict(schema_version=1, passed=not any(i["severity"] == "error" for i in issues), lvs_pass=lvs_ok, expected_pins=len(p.expected), physical_pins=len(p.pins), expected_nets=len(p.nets), nc_pins=sum(r["net"] == "NC" for r in p.expected.values()), issues=issues, rule_checks=rule_checks, unchecked_rules=sum(r["status"] == "UNCHECKED" for r in rule_checks), actual_netlist=sorted(actual.values(), key=lambda r: (r["ref"], r["pin_name"])), components=components, metrics=metrics(p, issues, lvs_ok=lvs_ok), proof_scope="Independent lands; every exposed path hole is solder-contacted; insulated jumper interiors never connect; component internal circuitry excluded. Provisional dimensions require physical validation.")
    return report


def write_actual(path, report):
    write_csv(path, COMPARE.COLUMNS, report["actual_netlist"])


def summary(report):
    counts = Counter(i["severity"] for i in report["issues"])
    return (f"{'PASS' if report['passed'] else 'FAIL'}; LVS {'PASS' if report['lvs_pass'] else 'FAIL'}; "
            f"{report['physical_pins']}/{report['expected_pins']} pins, {report['expected_nets']} nets, {report['nc_pins']} NC; "
            f"{counts['error']} errors, {counts['warning']} warnings; "
            f"{report['metrics']['total_wire_mm']:.1f} mm wire, {report['metrics']['jumpers']} jumpers; score {report['metrics']['score']:.1f}")
