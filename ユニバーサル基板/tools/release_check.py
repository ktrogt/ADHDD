"""Re-run meaningful release checks and refresh review artifacts under tools/."""
import contextlib
import io
import json
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import selftest
from documents import continuity, wirelist
from model import Project, load_json, save_json
from render import render
from router import route
from schemas import generate
from verify import summary, verify, write_actual


def main():
    root = Path(__file__).parent
    log = io.StringIO()
    tests = unittest.defaultTestLoader.loadTestsFromModule(selftest)
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(tests)
    if not result.wasSuccessful():
        print(log.getvalue())
        raise SystemExit(1)
    (root / "selftest.log").write_text(log.getvalue(), encoding="utf-8")
    selftest.write_fixtures()
    generate(root / "schemas")
    p = Project(root / "demo")
    rerouted = route(p)
    assert p.clone(wiring=rerouted).wire_data() == p.wire_data(), "demo routing changed / nondeterministic"
    report = verify(p)
    assert report["passed"] and report["lvs_pass"], summary(report)
    out = p.directory / "out"
    save_json(out / "report.json", report)
    save_json(out / "metrics.json", report["metrics"])
    write_actual(out / "netlist_actual.csv", report)
    (out / "summary.txt").write_text(summary(report) + "\n" + "\n".join(f"{i['severity'].upper()} {i['code']}: {i['detail']}" for i in report["issues"]) + "\n", encoding="utf-8")
    views = render(p, out) + render(p, out / "print-2x", scale=2, tiles=True)
    for path in views:
        ET.parse(path)
    ns = {"s": "http://www.w3.org/2000/svg"}
    top, bottom = ET.parse(out / "top.svg").getroot(), ET.parse(out / "bottom.svg").getroot()
    def col_x(svg):
        return next(float(t.attrib["x"]) for t in svg.findall(".//s:text", ns) if t.text == "A")
    assert col_x(top) < col_x(bottom), "bottom labels were not mirrored"
    assert any(t.text == "BOTTOM VIEW (mirrored)" for t in bottom.findall(".//s:text", ns))
    assert float(top.attrib["width"][:-2]) <= 277 and float(top.attrib["height"][:-2]) <= 190, "1x demo does not fit printable A4 landscape"
    wire_count = wirelist(p, out / "wirelist.csv")
    test_count = continuity(p, out / "continuity.csv")
    faults = verify(Project(root / "fixtures" / "faults"))
    assert {"SHORT", "BARE_CROSSING", "LVS:SPLIT"} <= {i["code"] for i in faults["issues"]}
    save_json(root / "fixtures" / "faults" / "out" / "report.json", faults)
    valid = Project(root / "fixtures" / "faults", wiring=load_json(root / "fixtures" / "faults" / "wiring.valid.json"))
    assert verify(valid)["passed"]
    audits = {}
    for filename, folder, versions in (("design_rules.json", "t7-audit", (1, "adhdd-perfboard-rules/1.0")), ("design_rules_t6_subset.json", "t7-subset-audit", (1,))):
        source = root.parent / filename
        if source.exists():
            audit = verify(p.clone(rules=load_json(source, versions)))
            save_json(out / folder / "report.json", audit)
            save_json(out / folder / "metrics.json", audit["metrics"])
            (out / folder / "summary.txt").write_text(summary(audit) + "\n" + "\n".join(f"{i['severity'].upper()} {i['code']}: {i['detail']}" for i in audit["issues"]) + "\n", encoding="utf-8")
            audits[filename] = dict(lvs_pass=audit["lvs_pass"], passed=audit["passed"], unchecked_rules=audit["unchecked_rules"], rule_statuses=dict(Counter(r["status"] for r in audit["rule_checks"])))
    checks = dict(schema_version=1, selftests=result.testsRun, selftests_pass=True, demo_pass=report["passed"], demo_lvs_pass=report["lvs_pass"], deterministic_reroute=True, svg_xml_files=len(views), svg_bottom_mirrored=True, svg_1x_fits_printable_a4_landscape=True, wirelist_steps=wire_count, continuity_tests=test_count, deliberate_faults_detected=True, valid_synthetic_case_pass=True, metrics=report["metrics"], t7_audits=audits)
    save_json(root / "verification_results.json", checks)
    print(f"{result.testsRun} self-tests PASS; deterministic demo LVS PASS; {len(views)} SVGs parsed; {wire_count} wires; {test_count} continuity tests")
    print(json.dumps(audits, ensure_ascii=False))


if __name__ == "__main__":
    main()
