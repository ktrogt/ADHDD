#!/usr/bin/env python3
"""Perfboard layout/routing/verification; Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from model import Project, load_footprints, load_json, save_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "metrics", "route", "optimize", "render", "wirelist", "continuity", "all", "demo"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project", type=Path, required=True, help="directory containing the v1 input files")
        cmd.add_argument("--out", type=Path, help="output directory (default PROJECT/out)")
        cmd.add_argument("--rules", type=Path, help="override project rules file; accepts canonical v1 or T7 rules/1.0")
        cmd.add_argument("--board", type=Path, help="override board geometry without changing the project")
        cmd.add_argument("--rules-weights", action="store_true", help="print T7 weighted soft penalty and comparison tuple (automatic for T7)")
        cmd.add_argument("--footprints", type=Path, help="override project footprint library (e.g. T5 footprints_ub.json)")
        cmd.add_argument("--placement", type=Path, help="override placement (e.g. placement.optimized.json)")
        cmd.add_argument("--wiring", type=Path, help="override wiring (e.g. wiring.valid.json)")
        if name in ("route", "all"):
            cmd.add_argument("--keep-all", action="store_true", help="preserve all existing conductors, not only locked ones")
        if name == "optimize":
            cmd.add_argument("--iterations", type=int, default=1000)
            cmd.add_argument("--seed", type=int, default=1)
        if name in ("render", "all", "demo"):
            cmd.add_argument("--scale", type=int, choices=(1, 2), default=1)
            cmd.add_argument("--tiles", action="store_true", help="also output A4 landscape tiles at exact scale")
            cmd.add_argument("--annotate-wires", action="store_true")
    sub.add_parser("selftest")
    sub.add_parser("schemas")
    args = parser.parse_args(argv)
    try:
        if args.command == "selftest":
            from selftest import run
            return 0 if run() else 1
        if args.command == "schemas":
            from schemas import generate
            generate(Path(__file__).parent / "schemas")
            print("Schemas generated under tools/schemas/")
            return 0
        out = args.out or args.project / "out"
        out.mkdir(parents=True, exist_ok=True)
        if args.command == "demo":
            from demo_data import make_demo
            p = make_demo(args.project)
        else:
            p = Project(args.project)
        overrides = {}
        if args.board:
            overrides["board"] = load_json(args.board)
        if args.rules:
            overrides["rules"] = load_json(args.rules, (1, "adhdd-perfboard-rules/1.0"))
        if args.footprints:
            overrides["footprints"] = load_footprints(args.footprints)
        if args.placement:
            overrides["placement"] = load_json(args.placement)
        if args.wiring:
            overrides["wiring"] = load_json(args.wiring)
        if overrides:
            p = p.clone(**overrides)
        command = args.command
        from verify import verify, metrics, summary, write_actual
        if command in ("route", "all", "demo"):
            from router import route
            wiring = route(p, keep_all=getattr(args, "keep_all", False))
            save_json(args.project / "wiring.json", wiring)
            p = p.clone(wiring=wiring)
            print("ROUTED:", json.dumps(wiring["router_stats"]))
        if command in ("verify", "metrics", "route", "all", "demo"):
            report = verify(p)
            save_json(out / "report.json", report)
            save_json(out / "metrics.json", report["metrics"])
            write_actual(out / "netlist_actual.csv", report)
            (out / "summary.txt").write_text(summary(report) + "\n" + "\n".join(f"{i['severity'].upper()} {i['code']}: {i['detail']}" for i in report["issues"]) + "\n", encoding="utf-8")
            print(summary(report))
            if args.rules_weights or p.rules.get("schema_version") == "adhdd-perfboard-rules/1.0":
                print("COMPARISON (LVS ok max; remaining fields min):", json.dumps(report["metrics"]["comparison_tuple"]))
                print("UNCHECKED hard rules (excluded from comparison failures):", ", ".join(r["id"] for r in report["metrics"]["unchecked_hard_rules"]) or "none")
                if report["metrics"]["partially_unchecked_hard_rules"]:
                    print("FAIL rules with additional UNCHECKED parts:", ", ".join(r["id"] for r in report["metrics"]["partially_unchecked_hard_rules"]))
            if command == "metrics":
                print(json.dumps(report["metrics"], indent=2, ensure_ascii=False))
            elif command == "verify":
                for i in report["issues"]:
                    print(f"{i['severity'].upper()} {i['code']}: {i['detail']}")
        if command in ("render", "all", "demo"):
            from render import render
            for path in render(p, out, scale=args.scale, tiles=args.tiles, annotate=args.annotate_wires):
                print("SVG:", path)
        if command in ("wirelist", "all", "demo"):
            from documents import wirelist
            print("WIRE LIST:", wirelist(p, out / "wirelist.csv"), "steps")
        if command in ("continuity", "all", "demo"):
            from documents import continuity
            print("CONTINUITY:", continuity(p, out / "continuity.csv"), "tests (bare board, power off)")
        if command == "optimize":
            from optimize import optimize
            placement, stats = optimize(p, iterations=args.iterations, seed=args.seed)
            save_json(args.project / "placement.optimized.json", placement)
            save_json(out / "optimization.json", stats)
            print(json.dumps(stats, indent=2))
        if command in ("verify", "metrics", "route", "all", "demo"):
            return 0 if report["passed"] else 1
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, OverflowError, csv.Error, UnicodeError) as error:
        print(f"INPUT ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
