"""Reproducible scoped development data. All dimensions explicitly provisional."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from model import (COMPARE, Project, hole, rect_intersects, save_json,
                   write_csv)


def source_dir():
    return next(parent / "基板" for parent in Path(__file__).resolve().parents if (parent / "基板" / "parts.csv").exists())


def provisional(row):
    fid = row["footprint"]
    identities = [token.split(":", 1) for token in row["pins"].split(";")]
    # Values below are transcribed/snapped from footprint_details, NOT mechanical approvals.
    if fid == "RPI_PICO_SOCKET":
        coords = [(0, i) for i in range(20)] + [(7, 39 - i) for i in range(20, 40)]
        bounds, height = (-1.61, -1.37, 21, 51), 10.5
    elif fid == "POLOLU_4035_SOCKET":
        coords = [(0, i) for i in range(7)] + [(5, 13 - i) for i in range(7, 14)]
        bounds, height = (-1.27, -1.27, 15.2, 17.8), 12
    elif fid == "SOT23_5_SOT25":
        # Logical SOT23 mapping onto a hypothetical adapter, not snapped SMD lands.
        coords = [(0, 0), (0, 1), (0, 2), (3, 2), (3, 0)]
        bounds, height = (-1.27, -1.27, 10.16, 7.62), 4
    elif fid == "MJ179PH_PLACEHOLDER":
        coords = [(0, 0), (2, 0), (4, 0)]
        bounds, height = (-2, -5.5, 14.5, 11), 9
    elif fid == "M78AR05_1_SIP3":
        coords = [(0, 0), (1, 0), (2, 0)]
        bounds, height = (-3.21, -3.775, 11.5, 7.55), 10.2
    else:
        pitch_match = re.search(r"(?:pitch|Pitch)\s*([0-9]+(?:\.[0-9]+)?)", row["footprint_details"])
        pitch = float(pitch_match[1]) if pitch_match else 2.54
        n = max(1, round(pitch / 2.54))
        if fid.startswith("R_AXIAL") or fid.startswith("D_DO35"):
            n, bodyw, bodyh, height = 3, (4 if fid.startswith("R") else 3.8), 2.1, 3
        elif fid.startswith("D_DO201"):
            n, bodyw, bodyh, height = 6, 9.5, 5.3, 5.3
        elif fid.startswith("D_DO41"):
            n, bodyw, bodyh, height = 4, 5.2, 2.7, 2.7
        elif fid.startswith("CP_RADIAL_D10"):
            n, bodyw, bodyh, height = 2, 10.5, 10.5, 17.5
        elif fid.startswith("CP_RADIAL_D6"):
            n, bodyw, bodyh, height = 1, 6.8, 6.8, 12.5
        elif fid.startswith("F_MFR"):
            n, bodyw, bodyh, height = 2, 12, 3, 18.3
        elif fid.startswith("JST_VH"):
            n, bodyw, bodyh, height = 2, 7.86, 6, 9
        elif fid.startswith("JST_XH"):
            n, bodyw, bodyh, height = 1, 7.4, 5.8, 7
        elif fid.startswith("HDR"):
            n, bodyw, bodyh, height = 1, 5.08, 2.5, 2.5
        elif fid.startswith("TP"):
            n, bodyw, bodyh, height = 1, 1.3, 1.3, 2
        else:
            bodyw, bodyh, height = (4.5, 3.15, 3.5) if "P5.0" in fid else (3.8, 2.8, 3.8)
        coords = [(n * i, 0) for i in range(len(identities))]
        mid = n * (len(identities) - 1) * 2.54 / 2
        bounds = (mid - bodyw / 2, -bodyh / 2, bodyw, bodyh)
    pins = [dict(number=num, name=name, dx=xy[0], dy=xy[1]) for (num, name), xy in zip(identities, coords)]
    result = dict(pins=pins, body_mm=dict(zip(("x", "y", "width", "height"), bounds)), height_mm=height, hot=fid in ("POLOLU_4035_SOCKET", "M78AR05_1_SIP3", "D_DO201AD_P15.24"), provisional=True, notes="DEVELOPMENT ONLY: grid approximation from parts.csv footprint_details; mechanical fit unverified. " + row["footprint_details"], sources=row["dimension_source"].split(" | "))
    if identities[0][1] in ("K", "POS", "VM") or row["ref"].startswith(("U", "J")):
        result["polarity"] = dict(pin=identities[0][0], label=identities[0][1])
    return result


def make_demo(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    source = source_dir()
    with (source / "parts.csv").open(encoding="utf-8-sig", newline="") as f:
        all_parts = list(csv.DictReader(f))
    probes = {"TP460", "TP461", "TP462", "TP463", "TP466", "TP467", "TP468", "TP471", "TP472", "TP473", "TP474"}
    rows = [r for r in all_parts if r["populate"] == "yes" and (not r["ref"].startswith("TP") or r["ref"] in probes)]
    refs = {r["ref"] for r in rows}
    with (source / "netlist_expected.csv").open(encoding="utf-8-sig", newline="") as f:
        original = list(csv.DictReader(f))
    excluded_gpio = {"GP17", "GP18", "GP26", "GP27", "GP28"}
    netlist, changes = [], []
    for row in original:
        if row["ref"] not in refs:
            continue
        if row["ref"] == "U201" and row["pin_name"] in excluded_gpio:
            changes.append(f"- U201.{row['pin_name']}: {row['net']} -> NC (removed scaffold)")
            row = dict(row, net="NC")
        netlist.append(row)
    write_csv(directory / "netlist.csv", COMPARE.COLUMNS, netlist)
    footprints = {"schema_version": 1, "footprints": {}}
    for row in rows:
        fp = provisional(row)
        # Pin names differ among otherwise identical 2-pin headers; pin_map maps identities later.
        footprints["footprints"].setdefault(row["footprint"], fp)
    save_json(directory / "footprints.json", footprints)
    board = dict(schema_version=1, name="60x45 provisional independent-land board", columns=60, rows=45, pitch_mm=2.54, type="single_sided_independent", edge_margin_holes=1, body_clearance_mm=0.5, keepouts=[dict(id="mount-TL", **{"from": "A1", "to": "B2"}), dict(id="mount-BR", **{"from": "BG44", "to": "BH45"})], provisional=True)
    save_json(directory / "board.json", board)
    save_json(directory / "wiring.json", dict(schema_version=1, conductors=[]))
    rules = dict(schema_version=1, groups={"drivers": ["U310", "U320", "U330", "U340"]}, router=dict(power_nets=["VM", "GND"], power_gauge="AWG20", signal_gauge="AWG26", bend_penalty=0.4, use_bridges=True, jumper_side="bottom"), power_roots={"VM": "J104.VM", "GND": "J101.SLEEVE"}, weights=dict(wire_mm=1, jumpers=20, bridges=1, crossings=2, area_mm2=0.01, error=100000, warning=1000), rules=[dict(id="power-wire", type="wire_gauge", nets=["VM", "GND"], max_awg=20, current_a=2.6, min_area_mm2=0.5, severity="error"), dict(id="demo-cap-proximity", type="near_pin", parts=["C312"], pin="U310.VIN", max_holes=5, severity="warning")])
    save_json(directory / "design_rules.json", rules)
    placement = dict(schema_version=1, parts={})
    rows_by_ref = {r["ref"]: r for r in rows}

    def add(ref, x, y, locked=False):
        row = rows_by_ref[ref]
        mapping = dict(zip((p["number"] for p in footprints["footprints"][row["footprint"]]["pins"]), (dict(number=n, name=name) for n, name in (s.split(":", 1) for s in row["pins"].split(";")))))
        placement["parts"][ref] = dict(footprint=row["footprint"], hole=hole((x, y)), rotation=0, locked=locked, value=row["value"], pin_map=mapping)

    add("U201", 3, 3, True)
    for i, x in enumerate((16, 27, 38, 49), 1):
        base = 300 + 10 * i
        add(f"U{base}", x, 29, True)
        add(f"C{base + 1}", x + 3, 25)
        add(f"C{base + 2}", x + 7, 29)
        add(f"J{base + 3}", x + 3, 40)
    # Greedy shelf packing in the upper-right area, avoiding pre-placed modules.
    from verify import placement_drc
    empty_rules = {"schema_version": 1, "rules": []}
    for row in sorted(rows, key=lambda r: (r["ref"][0] not in "JUDFC", r["ref"])):
        ref = row["ref"]
        if ref in placement["parts"]:
            continue
        placed = False
        for y in range(3, 22):
            for x in range(15, 57):
                add(ref, x, y)
                candidate = Project(directory, board=board, footprints=footprints, placement=placement, wiring={"schema_version": 1, "conductors": []}, rules=empty_rules)
                if not any(i["severity"] == "error" for i in placement_drc(candidate)):
                    placed = True
                    break
            if placed:
                break
        if not placed:
            failures = [i["detail"] for i in placement_drc(candidate) if i["severity"] == "error"]
            raise ValueError(f"demo packing failed for {ref}: {failures[:8]}")
    save_json(directory / "placement.json", placement)
    note = """# Development demo scope — 2026-10-22

NOT A PRODUCTION LAYOUT. All footprints and board dimensions are provisional.
Source: 基板/parts.csv and 基板/netlist_expected.csv (read-only).
Scope: populate=yes; scaffold/DNP omitted. Reduced probes: TP460..TP463, TP466..TP468, TP471..TP474.
No component-internal continuity is assumed (including module GND pins).
SOT23-5 U207 uses a hypothetical grid adapter; J101 contact positions are placeholders;
JST 2.50/3.96 mm pitches are snapped and NOT a confirmed fit. D103 lead/hole fit is unverified.
This demo verifies tool connectivity, not this physical design's fitness or noise/thermal behaviour.

## Intentional netlist scope changes

""" + "\n".join(changes) + "\n\nOmitted refs: " + ", ".join(r["ref"] for r in all_parts if r["ref"] not in refs) + "\n"
    (directory / "SCOPE.md").write_text(note, encoding="utf-8")
    return Project(directory)
