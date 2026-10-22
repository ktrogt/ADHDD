"""Read-only L1/L2 comparison using the shared outline and Claude v0.2 rules.

All output stays under tools/_check. Candidate Python programs are never run.
"""
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from model import Project, load_json, save_json
from verify import verify


def main():
    tools = Path(__file__).resolve().parent
    base = tools.parent
    rules = base / "design_rules_v0.2.json"
    board = base / "board.json"
    protected = [board, rules, base / "footprints_ub.json", base / "netlist_ub.csv"]
    for candidate in ("L1", "L2"):
        directory = base / "candidates" / candidate
        protected.extend(directory / name for name in ("board.json", "footprints_ub.json", "netlist.csv", "placement.json", "wiring.json", "design_rules.json"))
    def hashes():
        return {str(path.relative_to(base)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected if path.exists()}
    before, results = hashes(), {}
    for candidate in ("L1", "L2"):
        directory = base / "candidates" / candidate
        out = tools / "_check" / candidate
        command = [sys.executable, str(tools / "ub.py"), "verify", "--project", str(directory), "--board", str(board), "--rules", str(rules), "--rules-weights", "--out", str(out)]
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env)
        out.mkdir(parents=True, exist_ok=True)
        (out / "verify.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode not in (0, 1):
            raise RuntimeError(f"{candidate}: verify input error: {result.stderr}")
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        legacy = verify(Project(directory).clone(rules=load_json(rules, (1, "adhdd-perfboard-rules/1.0"))))
        results[candidate] = dict(lvs_pass=report["lvs_pass"], legacy_passed=report["passed"], comparison_tuple=report["metrics"]["comparison_tuple"], hard_failed_rule_ids=report["metrics"]["hard_failed_rule_ids"], unchecked_hard_count=report["metrics"]["unchecked_hard_count"], unchecked_hard_rule_ids=[r["id"] for r in report["metrics"]["unchecked_hard_rules"]], partially_unchecked_hard_rules=report["metrics"]["partially_unchecked_hard_rules"], body_offboard_before=sum(i["code"] == "BODY_OFFBOARD" for i in legacy["issues"]), body_offboard_after=sum(i["code"] == "BODY_OFFBOARD" for i in report["issues"]), core_errors_by_code=dict(Counter(i["code"] for i in report["issues"] if i["severity"] == "error" and not i["code"].startswith(("RULE:", "LVS:")))), hard_fail_findings=sum(i["code"].startswith("RULE:") and i["severity"] == "error" and i.get("status") != "UNCHECKED" for i in report["issues"]), edge_and_access=[r for r in report["rule_checks"] if r["id"] in ("M06", "M07", "M08", "M09")])
        print(candidate, json.dumps(results[candidate], ensure_ascii=False))
    after = hashes()
    save_json(tools / "_check" / "candidate_comparison.json", dict(schema_version=1, board="ユニバーサル基板/board.json", rules="ユニバーサル基板/design_rules_v0.2.json", inputs_unchanged_during_check=before == after, input_sha256=before, candidates=results))
    if before != after:
        raise RuntimeError("Candidate/source inputs changed during this audit; rerun for a stable snapshot")


if __name__ == "__main__":
    main()
