#!/usr/bin/env python3
"""Create a reviewable T5 proposal project; does not replace an existing placement."""
import argparse
import copy
from pathlib import Path

from model import COMPARE, Project, load_footprints, save_json, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--footprints", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    p = Project(args.project)
    library = load_footprints(args.footprints)
    placement = copy.deepcopy(p.placement)
    for pid, part in p.parts.items():
        fid = library.get("ref_to_type", {}).get(part.ref)
        if fid is None:
            raise ValueError(f"T5 has no ref_to_type entry for {part.ref}")
        source_pins = {(q.number, q.name) for q in part.pins}
        target_pins = {(q["number"], q["name"]) for q in library["footprints"][fid]["pins"]}
        if source_pins != target_pins:
            raise ValueError(f"{pid}: pin identity mapping changed; explicit supervisor decision required")
        placement["parts"][pid]["footprint"] = fid
        placement["parts"][pid].pop("pin_map", None)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in (("board", p.board), ("footprints", library), ("placement", placement), ("wiring", {"schema_version": 1, "conductors": []}), ("design_rules", p.rules)):
        save_json(args.out / (name + ".json"), data)
    write_csv(args.out / "netlist.csv", COMPARE.COLUMNS, p.expected.values())
    print("Created T5 PROPOSAL; geometry may fail DRC and substitutions remain unapproved:", args.out)


if __name__ == "__main__":
    main()
