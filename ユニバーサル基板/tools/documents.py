"""Ordered build wires and bare-board continuity test data."""
from __future__ import annotations

from itertools import combinations

from model import distance, hole, segment_distance, write_csv
from verify import verify


def wirelist(p, path):
    power = {"VM", "GND", "+5V", "+3V3", "VSYS", "VIN_RAW", "VIN_FUSED", "VIN_PROT"}
    def order(c):
        return (0 if c["kind"] == "bridge" else 1 if c["kind"] == "bare" and c["net"] in power else 2 if c["kind"] == "bare" else 3, c["net"], c["id"])
    rows = []
    for step, c in enumerate(sorted(p.conductors, key=order), 1):
        rows.append(dict(step=step, id=c["id"], net=c["net"], kind=c["kind"], from_hole=c["path"][0], to_hole=c["path"][-1], path=" -> ".join(c["path"]), length_mm=f"{c['length_mm']:.3f}", gauge=c.get("gauge", ""), type=c.get("type", ""), colour=c.get("colour", ""), side=c["side"], solder_holes=" ".join(hole(xy) for xy in c["contacts"])))
    fields = ("step", "id", "net", "kind", "from_hole", "to_hole", "path", "length_mm", "gauge", "type", "colour", "side", "solder_holes")
    write_csv(path, fields, rows)
    return len(rows)


def continuity(p, path):
    # A wire continuity test is meaningful on the unpopulated board or with
    # socketed modules removed. Resistors, diodes and capacitors otherwise alter beep behaviour.
    rows, seen = [], set()
    instructions = "POWER OFF; bare wired board before components / modules; discharge capacitors; component paths are excluded"

    def add(a, b, beep, na, nb, reason):
        if a == b and beep:
            return
        marker = (tuple(sorted((a, b))), beep)
        if marker in seen:
            return
        seen.add(marker)
        rows.append(dict(step=len(rows) + 1, expected="BEEP" if beep else "NO_BEEP", from_hole=hole(a), to_hole=hole(b), from_net=na, to_net=nb, reason=reason, condition=instructions))
    groups = {n: sorted({q.xy for q in p.pins.values() if q.net == n}) for n in p.nets}
    for net, nodes in groups.items():
        for target in nodes[1:]:
            add(nodes[0], target, True, net, net, "all expected terminals connected (spanning set)")
    power = [n for n in ("GND", "VM", "VIN_RAW", "VIN_FUSED", "VIN_PROT", "+5V", "+3V3", "VSYS") if groups.get(n)]
    for a, b in combinations(power, 2):
        add(groups[a][0], groups[b][0], False, a, b, "power isolation")
    # Test close exposed lands (including pin-only lands and jumper endpoints).
    land_nets = {}
    for pin in p.pins.values():
        land_nets.setdefault(pin.xy, set()).add(pin.net if pin.net != "NC" else f"NC:{pin.label}")
    for xy, label in p.reserved_pads.items():
        land_nets.setdefault(xy, set()).add("NC_EXTRA:" + label)
    for c in p.conductors:
        for xy in c["contacts"]:
            land_nets.setdefault(xy, set()).add(c["net"])
    for xy in sorted(land_nets):
        for dx, dy in ((1, 0), (0, 1), (1, 1), (-1, 1)):
            other = xy[0] + dx, xy[1] + dy
            if other not in land_nets:
                continue
            for a in sorted(land_nets[xy]):
                for b in sorted(land_nets[other]):
                    if a != b:
                        add(xy, other, False, a, b, "adjacent different-net lands")
    # Also record insulated crossings, where failure of insulation would short nets.
    for i, a in enumerate(p.conductors):
        for b in p.conductors[i + 1:]:
            if a["net"] == b["net"] or "jumper" not in (a["kind"], b["kind"]):
                continue
            gap = min(segment_distance(x, y, z, w) for x, y in zip(a["xy"], a["xy"][1:]) for z, w in zip(b["xy"], b["xy"][1:]))
            if gap <= 1:
                add(a["contacts"][0], b["contacts"][0], False, a["net"], b["net"], "near/crossing insulated conductors")
    write_csv(path, ("step", "expected", "from_hole", "to_hole", "from_net", "to_net", "reason", "condition"), rows)
    return len(rows)
