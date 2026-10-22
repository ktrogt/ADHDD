#!/usr/bin/env python3
"""Strict CSV netlist comparison; standard library only. See README.md.

NC is a per-pin disconnected state, never a shared electrical net.
Exit codes: 0 = identical / self-test passed, 1 = mismatch, 2 = invalid input.
"""

import argparse
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

COLUMNS = ("net", "ref", "pin_number", "pin_name")


def read_rows(stream, key, label):
    reader = csv.DictReader(stream)
    if reader.fieldnames is None or set(reader.fieldnames) != set(COLUMNS):
        raise ValueError(f"{label}: header must contain exactly {','.join(COLUMNS)}")
    if len(reader.fieldnames) != len(COLUMNS):
        raise ValueError(f"{label}: duplicate header column")
    result = {}
    names = set()
    numbers = set()
    field = "pin_name" if key == "name" else "pin_number"
    for line, raw in enumerate(reader, 2):
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError(f"{label}:{line}: malformed CSV row")
        row = {k: v.strip() for k, v in raw.items()}
        if any(not row[k] for k in ("net", "ref", "pin_name", field)):
            raise ValueError(f"{label}:{line}: required field is empty")
        identity = row["ref"], row[field]
        if identity in result:
            raise ValueError(f"{label}:{line}: duplicate pin {identity}")
        name_identity = row["ref"], row["pin_name"]
        if name_identity in names:
            raise ValueError(f"{label}:{line}: non-unique pin name {name_identity}")
        names.add(name_identity)
        if row["pin_number"]:
            number_identity = row["ref"], row["pin_number"]
            if number_identity in numbers:
                raise ValueError(f"{label}:{line}: duplicate pin number {number_identity}")
            numbers.add(number_identity)
        result[identity] = row
    if not result:
        raise ValueError(f"{label}: empty netlist")
    return result


def groups(rows):
    """Return each pin's partition ID and partition members, including NC singletons."""
    membership = {}
    grouped = defaultdict(set)
    for pin, row in rows.items():
        group = ("NC", pin) if row["net"] == "NC" else ("NET", row["net"])
        membership[pin] = group
        grouped[group].add(pin)
    return membership, grouped


def display(pin):
    return f"{pin[0]}.{pin[1]}"


def members(pins):
    return ", ".join(display(p) for p in sorted(pins))


def compare(expected, actual, key="number"):
    errors = []
    expected_refs = {p[0] for p in expected}
    for pin in sorted(expected.keys() - actual.keys()):
        errors.append(("MISSING", f"{display(pin)} expected net {expected[pin]['net']}"))
    for pin in sorted(actual.keys() - expected.keys()):
        kind = "UNKNOWN_REF" if pin[0] not in expected_refs else "UNKNOWN_PIN"
        errors.append((kind, f"extra connection {display(pin)} on {actual[pin]['net']}"))
    common = expected.keys() & actual.keys()
    for pin in sorted(common):
        e, a = expected[pin], actual[pin]
        # In name mode a physical number may be unavailable; when present it must agree.
        metadata = "pin_number" if key == "name" else "pin_name"
        if a[metadata] and a[metadata] != e[metadata]:
            errors.append(("PIN_ID_MISMATCH", f"{display(pin)} {metadata}: "
                           f"expected {e[metadata]!r}, actual {a[metadata]!r}"))
        if e["net"] != a["net"]:
            errors.append(("WRONG_NET", f"{display(pin)} expected {e['net']}, actual {a['net']}"))
    em, eg = groups(expected)
    am, ag = groups(actual)
    for pin in sorted(common):
        if expected[pin]["net"] == "NC" and len(ag[am[pin]]) > 1:
            errors.append(("NC_CONNECTED", f"{display(pin)} connected to "
                           f"{members(ag[am[pin]] - {pin})}"))
    for group, pins in sorted(eg.items(), key=lambda item: str(item[0])):
        observed = {am[p] for p in pins if p in actual}
        if len(observed) > 1:
            detail = "; ".join(members(ag[g] & pins) for g in sorted(observed, key=str))
            errors.append(("SPLIT", f"expected {group[1]} ({len(pins)} pins) split into {detail}"))
    for group, pins in sorted(ag.items(), key=lambda item: str(item[0])):
        # Unknown pins remain distinct, so attaching an unknown pin also counts as a merge.
        observed = {em[p] if p in expected else ("UNKNOWN", p) for p in pins}
        if len(observed) > 1:
            labels = ", ".join(str(g[1]) for g in sorted(observed, key=str))
            errors.append(("MERGED", f"actual {group[1]} combines expected groups {labels}: {members(pins)}"))
    return errors


def selftest():
    base = [
        ["A", "U1", "1", "IN"], ["A", "R1", "1", "P1"],
        ["B", "U1", "2", "OUT"], ["B", "R1", "2", "P2"],
        ["NC", "U1", "3", "UNUSED"], ["NC", "U1", "4", "UNUSED2"],
    ]

    def parse(rows, key="number"):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
        stream.seek(0)
        return read_rows(stream, key, "selftest")

    def changed(fn):
        rows = [r[:] for r in base]
        fn(rows)
        return rows

    def kinds(rows, key="number"):
        return {code for code, _ in compare(parse(base, key), parse(rows, key), key)}

    def require(condition, label):
        if not condition:
            raise AssertionError(label)
        print(f"SELFTEST PASS: {label}")

    require(not kinds(base), "identical and separate NC pins")
    swapped = changed(lambda rows: (rows[0].__setitem__(0, "B"), rows[2].__setitem__(0, "A")))
    require({"WRONG_NET", "SPLIT", "MERGED"} <= kinds(swapped), "swapped pin")
    merged = [["A" if r[0] == "B" else r[0], *r[1:]] for r in base]
    require({"WRONG_NET", "MERGED"} <= kinds(merged), "merged net")
    split = changed(lambda rows: rows[1].__setitem__(0, "C"))
    require("SPLIT" in kinds(split), "split net")
    nc = changed(lambda rows: rows[4].__setitem__(0, "A"))
    require("NC_CONNECTED" in kinds(nc), "connected NC pin")
    nc_short = changed(lambda rows: (rows[4].__setitem__(0, "FLOAT"), rows[5].__setitem__(0, "FLOAT")))
    require("NC_CONNECTED" in kinds(nc_short), "two NC pins shorted together")
    renamed = [["RENAMED" if r[0] == "A" else r[0], *r[1:]] for r in base]
    require(kinds(renamed) == {"WRONG_NET"}, "renaming preserves partition but fails exact names")
    require("MISSING" in kinds(base[:-1]), "missing pin")
    require("UNKNOWN_REF" in kinds(base + [["A", "U9", "1", "X"]]), "unknown reference")
    require("UNKNOWN_PIN" in kinds(base + [["A", "U1", "9", "X"]]), "unknown pin")
    no_numbers = [[r[0], r[1], "", r[3]] for r in base]
    require(not kinds(no_numbers, "name"), "name key without actual pin numbers")
    require("WRONG_NET" in kinds(swapped, "name"), "swapped pin with name key")
    for rows, label in [(base + [base[0]], "duplicate row"), ([], "empty input")]:
        try:
            parse(rows)
        except ValueError:
            print(f"SELFTEST PASS: rejects {label}")
        else:
            raise AssertionError(label)
    print("SELFTEST PASS: all 14 cases")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", nargs="?")
    parser.add_argument("actual", nargs="?")
    parser.add_argument("--key", choices=("name", "number"), default="number")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        if args.expected or args.actual:
            parser.error("--selftest does not accept CSV paths")
        selftest()
        return 0
    if not args.expected or not args.actual:
        parser.error("expected.csv and actual.csv are required")
    try:
        with Path(args.expected).open(encoding="utf-8-sig", newline="") as stream:
            expected = read_rows(stream, args.key, "expected")
        with Path(args.actual).open(encoding="utf-8-sig", newline="") as stream:
            actual = read_rows(stream, args.key, "actual")
        errors = compare(expected, actual, args.key)
    except (OSError, ValueError, csv.Error, UnicodeError) as error:
        print(f"INPUT ERROR: {error}", file=sys.stderr)
        return 2
    for code, detail in errors:
        print(f"{code}: {detail}")
    if errors:
        print(f"FAIL: {len(errors)} differences; key={args.key}")
        return 1
    net_count = len({r['net'] for r in expected.values()} - {"NC"})
    nc_count = sum(r["net"] == "NC" for r in expected.values())
    print(f"PASS: {len(expected)} pins, {net_count} named nets, {nc_count} NC pins; "
          f"names, pin identities and connectivity partitions identical; key={args.key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
