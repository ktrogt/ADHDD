"""Opt-in isolated-spoke routing, including hierarchical star hubs.

Every planned edge can meet another edge only at its explicitly declared end.
This is stricter than within-branch trunk sharing and therefore preserves the
declared star partitions. Bare bottom paths are preferred; jumpers are fallback.
"""
import copy

from model import hole, point, require


def resolve(p, selector):
    if selector.startswith("$"):
        name = selector[1:]
        definition = p.rules.get("nodes", {}).get(name)
        declaration = p.placement.get("nodes", {}).get(name)
        require(definition is not None and declaration is not None, f"star node {selector}: rules.nodes and placement.nodes declarations are required")
        xy = point(declaration if isinstance(declaration, str) else declaration["hole"])
        require(xy == resolve(p, definition["anchor"]), f"star node {selector}: remote anchor link is not supported")
        return xy
    if "." in selector:
        ref, pin = selector.split(".", 1)
        if pin.isdigit():
            selector = ref + ".#" + pin
    return p.pin_at(selector)


def specifications(p, config):
    specs = copy.deepcopy(config.get("stars", []))
    require(isinstance(specs, list), "router.stars must be an array")
    ids = config.get("star_rule_ids", [])
    require(isinstance(ids, list) and len(ids) == len(set(ids)), "router.star_rule_ids must be a distinct rule-ID array")
    by_id = {r["id"]: r for r in p.rules.get("rules", [])}
    for rid in ids:
        require(rid in by_id and by_id[rid]["type"] == "star", f"router star rule {rid}: missing or not a star rule")
        rule = by_id[rid]
        if "params" in rule:
            spec = copy.deepcopy(rule["params"])
            require(spec.get("max_shared_holes") == 0 and spec.get("shared_segment_policy") in ("none", "within_branch_only"), f"star {rid}: only zero shared length between branches is supported")
        else:
            spec = dict(net=rule["net"], root=rule["root"], branches=[dict(id=f"branch{i + 1}", endpoints=[target]) for i, target in enumerate(rule["targets"])])
        specs.append(dict(spec, id=rid))
    used = set()
    for i, spec in enumerate(specs):
        spec.setdefault("id", f"USER_STAR_{i + 1}")
        require(spec["id"] not in used, "duplicate router star ID")
        used.add(spec["id"])
        require(spec.get("net") in p.nets, f"{spec['id']}: unknown star net")
        require(isinstance(spec.get("branches"), list) and len(spec["branches"]) >= 2, f"{spec['id']}: at least two branches required")
        require(all(isinstance(b.get("endpoints"), list) and b["endpoints"] for b in spec["branches"]), f"{spec['id']}: branches need endpoint arrays")
    return specs


def route_stars(p, config):
    from router import astar, net_colour
    from model import compress
    specs = specifications(p, config)
    if not specs:
        return [], []
    nets = {s["net"] for s in specs}
    require(not any(c["net"] in nets for c in p.conductors), "star routing requires no preserved/pre-routed conductors on the selected star nets; route those nets by hand or clear their preserved wires")
    occupied = {q.xy for q in p.pins.values()} | set(p.reserved_pads)
    occupied.update(xy for c in p.conductors for xy in c["contacts"])
    net_claims = {}
    for q in p.pins.values():
        net_claims.setdefault(q.xy, set()).add(q.net)
    for c in p.conductors:
        for xy in c["contacts"]:
            net_claims.setdefault(xy, set()).add(c["net"])
    plans, planned, roots, targets = [], set(), {}, {}
    for spec in specs:
        net, root = spec["net"], resolve(p, spec["root"])
        roots.setdefault(net, set()).add(root)
        for branch in spec["branches"]:
            for selector in branch["endpoints"]:
                target = resolve(p, selector)
                targets.setdefault(net, set()).add(target)
                edge = (net, tuple(sorted((root, target))))
                if root != target and edge not in planned:
                    plans.append((net, target, root, spec["id"], branch.get("id", selector)))
                    planned.add(edge)
    # Unlisted terminals become separate spokes at the topmost hub, not hidden
    # taps on one of the protected motor/logic branches.
    for net in sorted(nets):
        outer = sorted(roots[net] - targets.get(net, set()))
        require(len(outer) == 1, f"{net}: stars must form one hierarchy with a unique top-level root")
        mentioned = {xy for n, a, b, _, _ in plans if n == net for xy in (a, b)}
        for q in sorted((q for q in p.pins.values() if q.net == net), key=lambda q: q.label):
            if q.xy not in mentioned and q.xy != outer[0]:
                plans.append((net, q.xy, outer[0], "UNLISTED_TERMINALS", q.label))
                mentioned.add(q.xy)
    reserved = {xy for _, a, b, _, _ in plans for xy in (a, b)}
    wire_ids = {c["id"] for c in p.conductors}
    output = []
    for serial, (net, source, target, sid, bid) in enumerate(plans, 1):
        for xy in (source, target):
            require(p.usable(xy) and xy not in p.reserved_pads, f"star {sid}: unusable junction {hole(xy)}")
            require(not net_claims.get(xy, set()) - {net}, f"star {sid}: junction {hole(xy)} belongs to another net/NC")
        blocked = (occupied | reserved) - {source, target}
        path = astar(p, source, {target}, blocked, config.get("bend_penalty", 0.4))
        kind, side = "bare", "bottom"
        if path is None:
            kind, side = "jumper", config.get("jumper_side", "top")
            require(side in ("top", "bottom"), "router.jumper_side must be top/bottom")
            path = astar(p, source, {target}, set(), config.get("bend_penalty", 0.4))
            require(path is not None, f"star {sid}: no physical path from {hole(source)} to {hole(target)}")
        contacts = path if kind == "bare" else (source, target)
        occupied.update(contacts)
        for xy in contacts:
            net_claims.setdefault(xy, set()).add(net)
        cid = f"STAR_{serial:04d}"
        require(cid not in wire_ids, f"reserved generated star conductor ID {cid} already exists")
        gauge = config.get("power_gauge", "AWG20") if net in ("VM", "GND", "+5V", "+3V3", "VSYS") else config.get("signal_gauge", "AWG26")
        output.append(dict(id=cid, net=net, kind=kind, side=side, path=[hole(xy) for xy in compress(path)], gauge=gauge, type="tinned copper" if kind == "bare" else "insulated copper", colour=net_colour(net), locked=False, star_rule=sid, branch=bid))
    return output, specs


def prove_stars(p, specs):
    if not specs:
        return
    from t7_rules import evaluate_t7
    proof = dict(schema_version="adhdd-perfboard-rules/1.0", nodes=p.rules.get("nodes", {}), rules=[dict(id=s["id"], type="star", severity="hard", weight=0, params=dict(net=s["net"], root=s["root"], branches=s["branches"], shared_segment_policy="within_branch_only", max_shared_holes=0)) for s in specs])
    findings = evaluate_t7(p.clone(rules=proof))
    require(not findings, "router cannot satisfy configured star partitions: " + "; ".join(f["detail"] for f in findings[:5]))
