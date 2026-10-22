#!/usr/bin/env python3
"""Verify ADHDD's approved original -> existing-library netlist translation.

Standard library only. Run without arguments to check the saved CSV and invoke
compare_netlist.py on it. --write regenerates only netlist_expected_lib.csv.
Library bytes must be present in ignored libs/, with the recorded exact hashes.
Multi-pad symbol pins use the exact XML connect/@pad string in pin_number.
"""

import argparse
import copy
import csv
import hashlib
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
from compare_netlist import compare, read_rows  # noqa: E402

ROOT = Path(__file__).resolve().parent
COLUMNS = ("net", "ref", "pin_number", "pin_name")
INPUT_HASHES = {
    "parts.csv": "fae4b318a92d053631b493cf7823b51e84d5b1d3cc22d94dac20e28f3ad375a5",
    "netlist_expected.csv": "1296648ffc0aad997c3bb86e27edfac6cec5153da8a2d53282195f420cb9440d",
}
LIB_HASHES = {
    "adafruit.lbr": "3d2af8aa33f0629a2b5c75b7fac3f5a1775724983b71f44c05028fa264d0e99e",
    "Capacitor.lbr": "a2ca8866f712705052a6e4bb44e183e9d7234d64cb377a3a4985d879dc5be502",
    "Connector.lbr": "6e559a2445a0d9a84a3d4d14ab1e693fbf3578cce9e46a1a07d6456ff940c8a4",
    "Diode.lbr": "66b4bba8ba41e88f3b487500bccfca41c2910348c679172fe5b0b2ca55647de5",
    "IC_Logic.lbr": "808589af1600fe2647208ba49c0e5008f97a8fbb2f4c7ff9b7e97dfeb8984fb9",
    "Power_Symbols.lbr": "47c8a99f482aae76d7a2118b67310aab166436f9e2e767b0bfb6768f690bee97",
    "Development_Boards.lbr": "849fec07c6a47d43a7b020e9882cc21654d31ca4b739b6be61d609b297fbb81b",
    "SparkFun-AnalogIC.lbr": "2f2c6b24d9d05a4f8b3e47580f60e59d92fc430defe7642781d74f83354a51ff",
}
POLOLU_REFS = {"U310", "U320", "U330", "U340"}
DEBUG_NC = {"SWCLK": "D1", "SWDIO": "D3"}
PICO_GND_PADS = {"3", "8", "13", "18", "23", "28", "38", "D2"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames is not None, f"{path.name}: missing header")
        require(len(reader.fieldnames) == len(set(reader.fieldnames)),
                f"{path.name}: duplicate columns")
        rows = list(reader)
        require(all(None not in r and all(v is not None for v in r.values()) for r in rows),
                f"{path.name}: malformed row")
        return rows


def check_hashes():
    for name, digest in INPUT_HASHES.items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
                f"{name}: approved input changed; re-review before translating")
    for name, digest in LIB_HASHES.items():
        require(hashlib.sha256((ROOT / "libs" / name).read_bytes()).hexdigest() == digest,
                f"{name}: missing/changed library bytes; use the documented snapshot")


def device_connections(row, libraries):
    require(row["decision"] in {"use", "use_with_mismatch"},
            f"{row['ref']}: unresolved library decision")
    path = Path(row["library_file_or_url"])
    require(path.parent == Path("libs") and path.name in LIB_HASHES,
            f"{row['ref']}: unknown library file {path}")
    library = libraries[path.name]
    deviceset = next((x for x in library.findall("devicesets/deviceset")
                      if x.get("name") == row["deviceset"]), None)
    require(deviceset is not None, f"{row['ref']}: deviceset missing")
    device = next((x for x in deviceset.findall("devices/device")
                   if x.get("name") == row["device"]), None)
    require(device is not None and device.get("package") == row["package"],
            f"{row['ref']}: device/package mismatch")
    package = next((x for x in library.findall("packages/package")
                    if x.get("name") == row["package"]), None)
    require(package is not None, f"{row['ref']}: package missing")
    pads = {x.get("name") for x in package if x.tag in {"pad", "smd"}}
    connections = {}
    used_pads = set()
    for connect in device.findall("connects/connect"):
        name, gate_name = connect.get("pin"), connect.get("gate")
        require(name not in connections, f"{row['ref']}: ambiguous symbol pin {name}")
        gate = next(x for x in deviceset.findall("gates/gate")
                    if x.get("name") == gate_name)
        symbol = next(x for x in library.findall("symbols/symbol")
                      if x.get("name") == gate.get("symbol"))
        require(any(x.get("name") == name for x in symbol.findall("pin")),
                f"{row['ref']}: symbol pin {name} missing")
        pad_string = connect.get("pad")
        connected_pads = set(pad_string.split())
        require(connected_pads <= pads, f"{row['ref']}: nonexistent package pad")
        require(not used_pads.intersection(connected_pads),
                f"{row['ref']}: package pad used by two logical pins")
        used_pads.update(connected_pads)
        connections[name] = pad_string
    require(used_pads == pads, f"{row['ref']}: unaccounted package copper pads")
    return connections


def expected_physical_target(part, number):
    """Independent physical-number convention, not derived from pin_map."""
    ref, family = part["ref"], part["footprint"]
    if ref in POLOLU_REFS:
        n = int(number)
        return ref + ("A" if n <= 7 else "B"), str(n if n <= 7 else 15 - n)
    if family in {"D_DO201AD_P15.24", "D_DO35_P7.62", "D_DO41_P10.16"}:
        return ref, {"1": "C", "2": "A"}[number]
    if family == "CP_RADIAL_D10_P5.0":
        return ref, {"1": "+", "2": "-"}[number]
    return ref, number


def translate(parts, mapping_rows, original, libraries):
    require(len(parts) == 80 and len(mapping_rows) == 80, "expected80 source/map refs")
    part_by_ref = {p["ref"]: p for p in parts}
    require(len(part_by_ref) == 80, "duplicate part reference")
    require(Counter(p["ref"] for p in parts) == Counter(r["ref"] for r in mapping_rows),
            "map must contain each original reference exactly once")
    pinmaps, connections_by_ref, declared = {}, {}, set()
    source_pins = set()
    for row in mapping_rows:
        ref, part = row["ref"], part_by_ref[row["ref"]]
        original_pins = [x.split(":", 1) for x in part["pins"].split(";")]
        for number, name in original_pins:
            source_pins.add((ref, number, name))
        pairs = [x.split(":", 1) for x in row["pin_map"].split(";")]
        require(Counter(n for _, n in original_pins) == Counter(n for n, _ in pairs),
                f"{ref}: pin_map omits or repeats an input pin")
        pinmaps[ref] = dict(pairs)
        con = device_connections(row, libraries)
        actual_refs = [ref + "A", ref + "B"] if ref in POLOLU_REFS else [ref]
        for placed_ref in actual_refs:
            declared.add(placed_ref)
            connections_by_ref[placed_ref] = con
    actual_original = [(r["ref"], r["pin_number"], r["pin_name"]) for r in original]
    require(len(actual_original) == len(set(actual_original)) == 252,
            "original CSV must have252 unique terminals")
    require(set(actual_original) == source_pins, "parts/source netlist terminal mismatch")

    output, evidence = {}, {}
    for source in original:
        ref, original_name = source["ref"], source["pin_name"]
        target = pinmaps[ref][original_name]
        if ref in POLOLU_REFS:
            require("." in target, f"{ref}: composite target requires placedref.pin")
            placed_ref, library_pin = target.rsplit(".", 1)
            require(placed_ref in {ref + "A", ref + "B"}, f"{ref}: wrongA/B ref")
        else:
            placed_ref, library_pin = ref, target
        con = connections_by_ref[placed_ref]
        require(library_pin in con, f"{placed_ref}: absent library pin {library_pin}")
        pad_string = con[library_pin]
        expected_ref, expected_pad = expected_physical_target(
            part_by_ref[ref], source["pin_number"])
        require(placed_ref == expected_ref and expected_pad in pad_string.split(),
                f"{ref}.{original_name}: library mapping changes physical terminal")
        key = (placed_ref, library_pin)
        record = dict(net=source["net"], ref=placed_ref,
                      pin_number=pad_string, pin_name=library_pin)
        if key in output:
            require(ref == "U201" and library_pin == "GND" and source["net"] == "GND",
                    f"{ref}: unapproved duplicate/merged symbol pin")
            require(output[key]["net"] == source["net"], "merged pins are on different nets")
        else:
            output[key] = record
        evidence[(ref, source["pin_number"], original_name)] = key

    require(set(evidence) == source_pins, "not every original row is represented")
    ground = output[("U201", "GND")]
    require(set(ground["pin_number"].split()) == PICO_GND_PADS and ground["net"] == "GND",
            "Pico merged GND/padD2 differs from supervisor approval")
    require(sum(key == ("U201", "GND") for key in evidence.values()) == 7,
            "Pico must merge exactly seven original perimeter grounds")
    for pin, pad in DEBUG_NC.items():
        require(connections_by_ref["U201"][pin] == pad, "debug pad mapping changed")
        require(("U201", pin) not in output, "debug pin overlaps original terminal")
        output[("U201", pin)] = dict(net="NC", ref="U201", pin_number=pad, pin_name=pin)
    for placed_ref, con in connections_by_ref.items():
        require({pin for ref, pin in output if ref == placed_ref} == set(con),
                f"{placed_ref}: unrepresented library pin or extra output pin")
    require({r["ref"] for r in output.values()} == declared and len(declared) == 84,
            "expected84 placed refs, with all four PololuA/B pairs")
    for source in original:
        key = evidence[(source["ref"], source["pin_number"], source["pin_name"])]
        require(output[key]["net"] == source["net"], "translation changed a net")
    require(len(output) == 248, "expected248 library symbol-pin rows")
    require(sum(r["net"] == "NC" for r in output.values()) == 24, "expected24 NCs")
    physical_pads = {(r["ref"], pad) for r in output.values()
                     for pad in r["pin_number"].split()}
    require(len(physical_pads) == 255, "expected252 original plus3 approved debug pads")
    return list(output.values())


def comparator_rows(rows, key="number"):
    import io
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    stream.seek(0)
    return read_rows(stream, key, "translation")


def negative_checks(parts, mappings, original, libraries, expected):
    wrong = copy.deepcopy(mappings)
    row = next(r for r in wrong if r["ref"] == "U310")
    row["pin_map"] = row["pin_map"].replace("VM:U310A.1", "VM:U310B.1")
    try:
        translate(parts, wrong, original, libraries)
    except ValueError:
        pass
    else:
        raise ValueError("negative check failed: swapped Pololu column accepted")
    wrong = copy.deepcopy(original)
    next(r for r in wrong if r["ref"] == "U201" and r["pin_number"] == "8")["net"] = "+3V3"
    try:
        translate(parts, mappings, wrong, libraries)
    except ValueError:
        pass
    else:
        raise ValueError("negative check failed: conflicting merged GND accepted")
    for mutation in ("wrong_net", "missing", "extra_debug_connected"):
        changed = copy.deepcopy(expected)
        if mutation == "wrong_net":
            changed[0]["net"] = "WRONG_NET"
        elif mutation == "missing":
            changed.pop()
        else:
            next(r for r in changed if r["ref"] == "U201" and
                 r["pin_name"] == "SWCLK")["net"] = "GND"
        require(compare(comparator_rows(expected), comparator_rows(changed)),
                f"negative check failed: {mutation} accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate translated CSV")
    args = parser.parse_args()
    try:
        check_hashes()
        parts = read_csv(ROOT / "parts.csv")
        mappings = read_csv(ROOT / "library_map.csv")
        original = read_csv(ROOT / "netlist_expected.csv")
        libraries = {name: ET.parse(ROOT / "libs" / name).find(".//library")
                     for name in LIB_HASHES}
        expected = translate(parts, mappings, original, libraries)
        negative_checks(parts, mappings, original, libraries, expected)
        path = ROOT / "netlist_expected_lib.csv"
        if args.write:
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(expected)
        actual = read_csv(path)
        require(len(actual) == len(expected), "saved translated row count differs")
        for key in ("number", "name"):
            errors = compare(comparator_rows(expected, key), comparator_rows(actual, key), key)
            require(not errors, f"saved translation differs ({key}): {errors[:3]}")
        print("PASS:252 original terminals represented without net changes;"
              "7 Pico grounds merge on GND;3 approved extra pads accounted for.")
        print("PASS:80 source refs ->84 placed refs;248 symbol-pin rows/255 pads;"
              "24 NCs;8 library hashes;5 negative checks.")
        result = subprocess.run([sys.executable, str(ROOT / "compare_netlist.py"),
                                 str(path), str(path)], check=False)
        require(result.returncode == 0, "compare_netlist.py self-comparison failed")
        return 0
    except (OSError, ValueError, csv.Error, ET.ParseError, KeyError, StopIteration) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
