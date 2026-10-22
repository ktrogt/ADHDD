"""Additive comparison policy; preserves legacy verify status and metrics.score."""
from collections import defaultdict


def comparison(p, findings, lvs_ok, *, jumpers, total_length):
    rules = {r["id"]: r for r in p.rules.get("rules", [])}
    hard_failed, hard_unchecked = set(), defaultdict(list)
    unchecked_soft = set()
    soft = defaultdict(float)
    for finding in findings:
        if not finding["code"].startswith("RULE:"):
            continue
        rid = finding["code"][5:]
        rule = rules.get(rid, {})
        severity = finding.get("rule_severity", rule.get("severity", finding["severity"]))
        hard = severity in ("hard", "error")
        unchecked = finding.get("status") == "UNCHECKED"
        if hard and unchecked:
            hard_unchecked[rid].append(finding["detail"])
        elif hard:
            hard_failed.add(rid)
        if severity == "soft" and not unchecked:
            soft[rid] += finding.get("t7_penalty", rule.get("weight", 0))
        elif severity == "soft" and unchecked:
            unchecked_soft.add(rid)
    core_errors = sum(f["severity"] == "error" and not f["code"].startswith(("RULE:", "LVS:")) for f in findings)
    # Collinear waypoints are not bends. Count a change in geometric direction,
    # independent of the arbitrary number of path vertices used in the input.
    bends = 0
    for conductor in p.conductors:
        directions = []
        for a, b in zip(conductor["xy"], conductor["xy"][1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = (dx * dx + dy * dy) ** 0.5
            directions.append((dx / length, dy / length))
        bends += sum(abs(a[0] - b[0]) > 1e-8 or abs(a[1] - b[1]) > 1e-8 for a, b in zip(directions, directions[1:]))
    penalty = round(sum(soft.values()), 6)
    vector = [bool(lvs_ok), core_errors, len(hard_failed), jumpers, penalty, bends, total_length]
    fully_unchecked = [dict(id=k, reasons=v) for k, v in sorted(hard_unchecked.items()) if k not in hard_failed]
    partial = [dict(id=k, reasons=v) for k, v in sorted(hard_unchecked.items()) if k in hard_failed]
    return dict(t7_soft_penalty=penalty, t7_soft_penalty_by_rule={k: round(v, 6) for k, v in sorted(soft.items())}, unchecked_soft_rule_ids=sorted(unchecked_soft), soft_penalty_complete=not unchecked_soft, hard_fail_count=len(hard_failed), hard_failed_rule_ids=sorted(hard_failed), unchecked_hard_rules=fully_unchecked, unchecked_hard_count=len(fully_unchecked), partially_unchecked_hard_rules=partial, partially_unchecked_hard_count=len(partial), core_drc_errors=core_errors, bends=bends, comparison_tuple=vector, comparison_tuple_fields=["lvs_ok", "core_drc_errors", "hard_fail_count", "jumpers", "t7_soft_penalty", "bends", "total_wire_mm"], comparison_directions=["max", "min", "min", "min", "min", "min", "min"], lexicographic_sort_key=[0 if lvs_ok else 1] + vector[1:], ranking_pass=bool(lvs_ok and not core_errors and not hard_failed))
