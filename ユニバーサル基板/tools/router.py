"""Deterministic bottom-grid A* tree router with insulated fallback."""
from __future__ import annotations

import copy
import colorsys
import heapq
from collections import defaultdict

from model import EPS, compress, distance, hole, number, require
from verify import UnionFind, extract, placement_drc, wiring_drc

PALETTE = ["#167d8d", "#547c20", "#3849ad", "#b63e77", "#7250a3", "#007f58", "#ab6b00", "#436c93"]


def net_colour(net, nets=()):
    special = {"VM": "#d32f2f", "GND": "#202020", "+5V": "#ef7900", "+3V3": "#be168a", "VREF": "#008577", "VSYS": "#c95e00", "VIN_RAW": "#a71313", "VIN_FUSED": "#cc4444", "VIN_PROT": "#b82920"}
    if net in special:
        return special[net]
    if "OUT" in net:
        return "#88532e"
    controls = sorted(["ARM", "ARM_SW", "SLEEP", "FAULT", "SN_BUS", "SN_PU", "SN_RX_IN", "UART_RX"] + [f"HDD{i}_{suffix}" for i in range(1, 5) for suffix in ("IN1", "IN2", "CS")])
    if net in controls:
        # Distinct scope signal colours, avoiding the power-red sector.
        hue = 0.12 + 0.67 * controls.index(net) / (len(controls) - 1)
        rgb = colorsys.hsv_to_rgb(hue, 0.78, 0.65)
        return "#" + "".join(f"{round(v * 255):02x}" for v in rgb)
    # Stable regardless of hash randomisation or ordering of unrelated nets.
    return PALETTE[sum((i + 1) * ord(c) for i, c in enumerate(net)) % len(PALETTE)]


def astar(p, source, goals, blocked, bend_penalty=0.4, *, max_expansions=None):
    """State includes heading: bend cost cannot be correctly optimised by xy alone."""
    goals = set(goals)
    if source in goals:
        return [source]
    if not goals:
        return None
    def heuristic(xy):
        return min(abs(xy[0] - q[0]) + abs(xy[1] - q[1]) for q in goals)
    start = (source, 4)
    best, previous = {start: 0.0}, {}
    queue = [(heuristic(source), 0.0, source, 4)]
    expansions = 0
    directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
    while queue:
        _, cost, xy, heading = heapq.heappop(queue)
        state = xy, heading
        if cost > best[state] + EPS:
            continue
        if xy in goals:
            path = [xy]
            while state in previous:
                state = previous[state]
                path.append(state[0])
            return list(reversed(path))
        expansions += 1
        if max_expansions is not None and expansions > max_expansions:
            return None
        for direction, (dx, dy) in enumerate(directions):
            target = xy[0] + dx, xy[1] + dy
            if not p.usable(target) or target in blocked:
                continue
            value = cost + 1 + (bend_penalty if heading != 4 and heading != direction else 0)
            nxt = target, direction
            if value < best.get(nxt, float("inf")) - EPS:
                best[nxt] = value
                previous[nxt] = (xy, heading)
                heapq.heappush(queue, (value + heuristic(target), value, target, direction))
    return None


def route(p, *, keep_all=False):
    from rules import evaluate
    evaluate(p, placement_only=True)  # Validate the entire rule interface before generating output.
    hard = [i for i in placement_drc(p) if i["severity"] == "error"]
    require(not hard, "routing requires valid placement: " + "; ".join(i["detail"] for i in hard[:8]))
    existing = [copy.deepcopy(c) for c in p.wire_data()["conductors"] if keep_all or c.get("locked", False)]
    config = p.rules.get("router", {})
    number(config.get("bend_penalty", 0.4), "router.bend_penalty", 0)
    for key in ("power_gauge", "signal_gauge"):
        require(isinstance(config.get(key, "AWG20" if key == "power_gauge" else "AWG26"), str), f"router.{key} must be a string")
    trunks = config.get("trunks", [])
    require(isinstance(trunks, list), "router.trunks must be an array")
    ids = {c.get("id") for c in existing}
    for i, t in enumerate(trunks):
        cid = t.get("id", f"TRUNK{i + 1}")
        if cid in ids:
            continue
        existing.append(dict(id=cid, net=t["net"], kind="bare", side="bottom", path=t["path"], gauge=t.get("gauge", config.get("power_gauge", "AWG20")), type="tinned copper", colour=net_colour(t["net"]), locked=True))
        ids.add(cid)
    seed = p.clone(wiring={"schema_version": 1, "conductors": existing})
    extraction, _, _, contact_map, _ = extract(seed)
    bad = [i for i in wiring_drc(seed, contact_map) + extraction if i["severity"] == "error" and i["code"] != "FLOATING_CONDUCTOR"]
    require(not bad, "invalid pre-routed conductors: " + "; ".join(i["detail"] for i in bad[:8]))
    from star_router import route_stars, prove_stars
    preserved_count = len(existing)
    star_wires, star_specs = route_stars(seed, config)
    star_nets = {s["net"] for s in star_specs}
    if star_wires:
        existing.extend(star_wires)
        ids.update(c["id"] for c in star_wires)
        seed = p.clone(wiring={"schema_version": 1, "conductors": existing})
    occupied, uf = defaultdict(set), UnionFind()
    net_locations = defaultdict(set)
    for pin in seed.pins.values():
        occupied[pin.xy].add(pin.net if pin.net != "NC" else f"NC:{pin.label}")
        if pin.net != "NC":
            net_locations[pin.net].add(pin.xy)
        uf.find(pin.xy)
    for xy, label in seed.reserved_pads.items():
        occupied[xy].add("NC_EXTRA:" + label)
    for c in seed.conductors:
        for xy in c["contacts"]:
            occupied[xy].add(c["net"])
            net_locations[c["net"]].add(xy)
            uf.union(c["contacts"][0], xy)
    power = config.get("power_nets", [n for n in ("VM", "GND") if n in p.nets])
    require(isinstance(power, list) and len(set(power)) == len(power) and all(n in p.nets for n in power), "router.power_nets: distinct existing nets required")
    extra_power = {"VM", "GND", "+5V", "+3V3", "VSYS", "VIN_RAW", "VIN_FUSED", "VIN_PROT"}
    net_order = [n for n in list(power) + sorted((n for n in p.nets if n not in power), key=lambda n: (n not in extra_power, -len(net_locations[n]), n)) if n not in star_nets]
    output = existing
    stats = dict(bare_routes=sum(c["kind"] == "bare" for c in star_wires), jumper_fallbacks=sum(c["kind"] == "jumper" for c in star_wires), preserved=preserved_count)
    if star_specs:
        stats["star_conductors"] = len(star_wires)
    roots = p.rules.get("power_roots", {})
    serial = 0
    for net in net_order:
        points = net_locations[net]
        if not points:
            continue
        root = p.pin_at(roots[net]) if net in roots else min(points)
        require(root in points, f"root for {net} ({roots.get(net)}) is not a terminal or pre-routed point of that net")
        while True:
            connected = {xy for xy in points if uf.find(xy) == uf.find(root)}
            remaining = points - connected
            if not remaining:
                break
            # Nearest remaining island endpoint; deterministic tie breaks on coordinate tuples.
            _, source, nearest = min((abs(a[0] - b[0]) + abs(a[1] - b[1]), a, b) for a in remaining for b in connected)
            blocked = {xy for xy, labels in occupied.items() if labels - {net}}
            path = astar(p, source, connected, blocked, config.get("bend_penalty", 0.4))
            kind, side = "bare", "bottom"
            gauge = config.get("power_gauge", "AWG20") if net in set(power) | extra_power else config.get("signal_gauge", "AWG26")
            if path is None:
                kind, side = "jumper", config.get("jumper_side", "top")
                require(side in ("top", "bottom"), "router.jumper_side must be top/bottom")
                # Insulated path may cross other lands, but cannot cross a mounting keepout.
                path = astar(p, source, {nearest}, set(), config.get("bend_penalty", 0.4))
                require(path is not None, f"no physical jumper path for {net}: {hole(source)} -> {hole(nearest)}")
                stats["jumper_fallbacks"] += 1
                contacts = [path[0], path[-1]]
            else:
                stats["bare_routes"] += 1
                contacts = path
                if len(path) == 2 and config.get("use_bridges", False) and net not in set(power) | extra_power:
                    kind = "bridge"
                    gauge = "unknown"  # Solder bridge size cannot be inferred from copper AWG.
            serial += 1
            cid = f"W{serial:04d}"
            while cid in ids:
                serial += 1
                cid = f"W{serial:04d}"
            ids.add(cid)
            output.append(dict(id=cid, net=net, kind=kind, side=side, path=[hole(xy) for xy in compress(path)], gauge=gauge, type="insulated copper" if kind == "jumper" else "solder" if kind == "bridge" else "tinned copper", colour=net_colour(net), locked=False))
            for xy in contacts:
                occupied[xy].add(net)
                points.add(xy)
                uf.union(source, xy)
    result = {"schema_version": 1, "conductors": output, "router_stats": stats}
    # Fail closed: never publish wiring which fails the geometry-derived LVS.
    from verify import verify
    routed = p.clone(wiring=result)
    report = verify(routed)
    require(report["lvs_pass"], "router produced invalid connectivity: " + "; ".join(i["detail"] for i in report["issues"] if i["code"].startswith("LVS:") or i["code"] in ("SHORT", "NC_CONNECTED")))
    prove_stars(routed, star_specs)
    return result
