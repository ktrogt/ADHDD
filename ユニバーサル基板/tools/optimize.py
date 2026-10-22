"""Seeded simulated annealing of unlocked placements; never moves locked wiring."""
from __future__ import annotations

import copy
import math
import random

from model import EPS, hole, point, require
from rules import evaluate
from verify import placement_drc


def estimate(p):
    """Manhattan MST lower estimate, plus the same configurable violation weights.

    This avoids routing every proposal. Final ranking must use routed metrics.
    """
    weights = dict(wire_mm=1, error=100000, warning=1000, info=0)
    weights.update(p.rules.get("weights", {}))
    wire = 0.0
    for net in p.nets:
        nodes = sorted({q.xy for q in p.pins.values() if q.net == net})
        if not nodes:
            continue
        tree, remaining = {nodes[0]}, set(nodes[1:])
        while remaining:
            cost, target = min((abs(a[0] - b[0]) + abs(a[1] - b[1]), a) for a in remaining for b in tree)
            wire += cost * p.pitch
            tree.add(target)
            remaining.remove(target)
    violations = placement_drc(p) + evaluate(p, placement_only=True)
    return wire * weights["wire_mm"] + sum(weights.get(i["severity"], 0) for i in violations), wire, violations


def optimize(p, *, iterations=1000, seed=1):
    require(type(iterations) is int and iterations >= 0, "iterations must be >= 0")
    # Conservative: preserve any part touched by locked conductors, including wires
    # passing through an empty pad now occupied by a component pin.
    fixed_contacts = {xy for c in p.conductors if c.get("locked", False) for xy in c["contacts"]}
    movable = sorted(name for name, part in p.parts.items() if not part.data.get("locked", False) and not any(q.xy in fixed_contacts for q in part.pins))
    current = copy.deepcopy(p.placement)
    current_score, initial_wire, initial_issues = estimate(p)
    best, best_score = copy.deepcopy(current), current_score
    rng, accepted, feasible = random.Random(seed), 0, 0
    initial_score = current_score
    for step in range(iterations if movable else 0):
        proposal = copy.deepcopy(current)
        name = rng.choice(movable)
        data = proposal["parts"][name]
        x, y = point(data["hole"])
        if rng.random() < 0.22:
            data["rotation"] = rng.choice((0, 90, 180, 270))
        else:
            radius = max(1, int(8 * (1 - step / max(iterations, 1))))
            x += rng.randint(-radius, radius)
            y += rng.randint(-radius, radius)
            if not 0 <= x < p.columns or not 0 <= y < p.rows:
                continue
            data["hole"] = hole((x, y))
        candidate = p.clone(placement=proposal)
        # Hard placement constraints are never traded for a shorter wire estimate.
        if any(i["severity"] == "error" for i in placement_drc(candidate)):
            continue
        value, _, issues = estimate(candidate)
        # Edge and other configured error-level placement rules are hard constraints.
        if any(i["severity"] == "error" for i in issues if i["code"].startswith("RULE:")):
            continue
        feasible += 1
        temperature = max(0.1, 30.0 * (1 - step / max(iterations, 1)) ** 2)
        if value <= current_score or rng.random() < math.exp(max(-700, (current_score - value) / temperature)):
            current, current_score = proposal, value
            accepted += 1
            if value < best_score - EPS:
                best, best_score = copy.deepcopy(proposal), value
    final = p.clone(placement=best)
    final_score, final_wire, final_issues = estimate(final)
    stats = dict(schema_version=1, seed=seed, iterations=iterations, movable_parts=movable, accepted_moves=accepted, feasible_proposals=feasible, initial_estimate_score=round(initial_score, 3), final_estimate_score=round(final_score, 3), initial_wire_estimate_mm=round(initial_wire, 3), final_wire_estimate_mm=round(final_wire, 3), final_placement_errors=sum(i["severity"] == "error" for i in final_issues), objective="Manhattan MST estimate + configured placement-rule penalties; compare final candidates after routing with metrics.score")
    return best, stats
