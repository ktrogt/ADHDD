"""Validated v1 input model and geometry. Python standard library only."""
from __future__ import annotations

import copy
import csv
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Import the read-only approved comparator without creating a cache beside it.
sys.dont_write_bytecode = True

EPS = 1e-8
HOLE = re.compile(r"([A-Z]+)([1-9][0-9]*)\Z")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value, label, minimum=None, integer=False):
    require(type(value) in (int, float) and math.isfinite(value), f"{label}: finite number required")
    require(not integer or type(value) is int, f"{label}: integer required")
    require(minimum is None or value >= minimum, f"{label}: must be >= {minimum}")
    return value


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: nonempty string required")
    return value


def boolean(value, label):
    require(type(value) is bool, f"{label}: boolean required")
    return value


def column(x):
    require(x >= 0, "negative column")
    text = ""
    x += 1
    while x:
        x, digit = divmod(x - 1, 26)
        text = chr(65 + digit) + text
    return text


def hole(xy):
    x, y = xy
    return f"{column(x)}{y + 1}" if x >= 0 and y >= 0 else f"({x},{y})"


def point(text):
    require(isinstance(text, str), "hole must be a string")
    match = HOLE.fullmatch(text)
    require(match is not None, f"invalid hole {text!r}; use TOP-view A1, AA12, ...")
    x = 0
    for c in match[1]:
        x = 26 * x + ord(c) - 64
    return x - 1, int(match[2]) - 1


def rotate(p, angle):
    x, y = p
    return ((x, y), (-y, x), (-x, -y), (y, -x))[angle // 90]


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def segment_points(a, b):
    require(a != b, "zero-length exposed segment")
    require(a[0] == b[0] or a[1] == b[1], "exposed wires must follow orthogonal grid lines")
    n = abs(a[0] - b[0]) + abs(a[1] - b[1])
    dx, dy = (b[0] - a[0]) // n, (b[1] - a[1]) // n
    return [(a[0] + k * dx, a[1] + k * dy) for k in range(n + 1)]


def path_points(path):
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        out.extend(segment_points(a, b)[1:])
    return out


def compress(path):
    if len(path) < 3:
        return path[:]
    out = [path[0]]
    for a, b, c in zip(path, path[1:], path[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.append(b)
    return out + [path[-1]]


def rect_distance(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def rect_intersects(a, b, clearance=0):
    # Tangency at zero clearance is allowed; positive clearance uses Euclidean gap.
    overlap = a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS
    return overlap or rect_distance(a, b) < clearance - EPS


def segment_distance(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on(p, q, r):
        return abs(cross(p, q, r)) < EPS and min(p[0], q[0]) - EPS <= r[0] <= max(p[0], q[0]) + EPS and min(p[1], q[1]) - EPS <= r[1] <= max(p[1], q[1]) + EPS

    if (cross(a, b, c) * cross(a, b, d) < -EPS and cross(c, d, a) * cross(c, d, b) < -EPS) or any((on(a, b, c), on(a, b, d), on(c, d, a), on(c, d, b))):
        return 0.0

    def pd(p, x, y):
        vx, vy = y[0] - x[0], y[1] - x[1]
        den = vx * vx + vy * vy
        t = max(0, min(1, ((p[0] - x[0]) * vx + (p[1] - x[1]) * vy) / den)) if den else 0
        return distance(p, (x[0] + t * vx, x[1] + t * vy))

    return min(pd(a, c, d), pd(b, c, d), pd(c, a, b), pd(d, a, b))


def load_json(path, versions=(1,)):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, f"{path}: duplicate JSON key {k}")
            result[k] = v
        return result
    with Path(path).open(encoding="utf-8-sig") as f:
        result = json.load(f, object_pairs_hook=pairs)
    require(isinstance(result, dict), f"{path}: JSON object required")
    require(type(result.get("schema_version")) in (int, str) and result.get("schema_version") in versions, f"{path}: unsupported schema_version (expected {versions})")
    return result


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_footprints(path):
    """Accept canonical v1 and T5's published 1.0/depth spelling without data loss."""
    data = load_json(path, (1, "1.0"))
    if data["schema_version"] == "1.0":
        data = copy.deepcopy(data)
        data["source_schema_version"] = data["schema_version"]
        data["schema_version"] = 1
        for fp in data["footprints"].values():
            body = fp["body_mm"]
            if "height" not in body and "depth" in body:
                body["height"] = body["depth"]
            if "polarity_mark" in fp and "polarity" not in fp:
                fp["polarity"] = dict(pin=fp["pins"][0]["number"], label=fp["polarity_mark"])
            # Published T5 library explicitly has unresolved fit checks.
            fp.setdefault("provisional", True)
    return data


def comparator():
    for parent in Path(__file__).resolve().parents:
        path = parent / "基板" / "compare_netlist.py"
        if path.is_file():
            spec = importlib.util.spec_from_file_location("approved_compare_netlist", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ValueError("cannot find 基板/compare_netlist.py in repository ancestors")


COMPARE = comparator()


@dataclass
class Pin:
    ref: str
    number: str
    name: str
    xy: tuple
    part: str
    net: str = ""

    @property
    def key(self):
        return self.ref, self.name

    @property
    def label(self):
        return f"{self.ref}.{self.name}"

    def row(self, net):
        return dict(net=net, ref=self.ref, pin_number=self.number, pin_name=self.name)


@dataclass
class Part:
    id: str
    ref: str
    footprint: dict
    data: dict
    pins: list
    rect: tuple


class Project:
    def __init__(self, directory, *, board=None, footprints=None, placement=None, wiring=None, rules=None, expected=None):
        self.directory = Path(directory)
        self.board = board if board is not None else load_json(self.directory / "board.json")
        if footprints is None:
            path = self.directory / "footprints.json"
            if not path.exists():
                path = self.directory / "footprints_ub.json"
            footprints = load_footprints(path)
        self.footprints = footprints
        self.placement = placement if placement is not None else load_json(self.directory / "placement.json")
        self.wiring = wiring if wiring is not None else (load_json(self.directory / "wiring.json") if (self.directory / "wiring.json").exists() else {"schema_version": 1, "conductors": []})
        self.rules = rules if rules is not None else (load_json(self.directory / "design_rules.json", (1, "adhdd-perfboard-rules/1.0")) if (self.directory / "design_rules.json").exists() else {"schema_version": 1, "rules": []})
        if expected is None:
            with (self.directory / "netlist.csv").open(encoding="utf-8-sig", newline="") as f:
                expected = COMPARE.read_rows(f, "name", "netlist.csv")
        self.expected = expected
        self.validate()

    def clone(self, **kwargs):
        data = dict(board=self.board, footprints=self.footprints, placement=self.placement, wiring=self.wiring, rules=self.rules, expected=self.expected)
        data.update(kwargs)
        return Project(self.directory, **data)

    def validate(self):
        for label, value in (("board", self.board), ("footprints", self.footprints), ("placement", self.placement), ("wiring", self.wiring)):
            require(isinstance(value, dict) and type(value.get("schema_version")) is int and value.get("schema_version") == 1, f"{label}: schema_version must be integer 1")
        b = self.board
        self.columns = number(b.get("columns"), "board.columns", 1, True)
        self.rows = number(b.get("rows"), "board.rows", 1, True)
        self.pitch = number(b.get("pitch_mm"), "board.pitch_mm", 0.01)
        require(abs(self.pitch - 2.54) < EPS, "v1 supports 2.54 mm pitch only")
        require(b.get("type", "single_sided_independent") in ("single_sided_independent", "double_sided_plated"), "unsupported board type")
        number(b.get("body_clearance_mm", 0.5), "body clearance", 0)
        self.margin = number(b.get("edge_margin_holes", 0), "edge margin", 0, True)
        # All existing geometry remains in millimetres relative to A1. The
        # physical outline is translated into that frame rather than moving pins.
        self.has_outline = "outline_mm" in b
        if self.has_outline:
            outline, origin = b["outline_mm"], b.get("grid_origin_mm", {})
            width = number(outline.get("width"), "outline_mm.width", 0.01)
            height = number(outline.get("height"), "outline_mm.height", 0.01)
            ox = number(origin.get("x"), "grid_origin_mm.x", 0)
            oy = number(origin.get("y"), "grid_origin_mm.y", 0)
            require(ox + (self.columns - 1) * self.pitch <= width + EPS and oy + (self.rows - 1) * self.pitch <= height + EPS, "hole grid lies outside physical outline")
            self.board_rect = (-ox, -oy, width - ox, height - oy)
            margin = number(b.get("body_edge_margin_mm", 1.0), "body_edge_margin_mm", 0)
        else:
            self.board_rect = (-self.pitch / 2, -self.pitch / 2, (self.columns - 0.5) * self.pitch, (self.rows - 0.5) * self.pitch)
            margin = self.margin * self.pitch
        self.body_allowed_rect = (self.board_rect[0] + margin, self.board_rect[1] + margin, self.board_rect[2] - margin, self.board_rect[3] - margin)
        require(self.body_allowed_rect[0] < self.body_allowed_rect[2] and self.body_allowed_rect[1] < self.body_allowed_rect[3], "body margin consumes physical board")
        self.keepouts = []
        for ko in b.get("keepouts", []):
            a, z = point(ko["from"]), point(ko["to"])
            require(a[0] <= z[0] and a[1] <= z[1], "keepout from must be upper left")
            self.keepouts.append((a, z, ko.get("id", "keepout")))
        require(isinstance(self.footprints.get("footprints"), dict), "footprints.footprints must be an object")
        for name, fp in self.footprints["footprints"].items():
            require(isinstance(fp, dict), f"{name}: footprint must be an object")
            require(isinstance(fp.get("pins"), list) and bool(fp["pins"]), f"{name}: nonempty pins array required")
            names, numbers, holes = set(), set(), set()
            for pin in fp["pins"]:
                require(isinstance(pin, dict), f"{name}: pin must be an object")
                pn, label = nonempty(pin.get("number"), name + ".pin.number"), nonempty(pin.get("name"), name + ".pin.name")
                require(pn not in numbers and label not in names, f"{name}: duplicate pin identity")
                numbers.add(pn)
                names.add(label)
                xy = (number(pin.get("dx"), name + ".dx", integer=True), number(pin.get("dy"), name + ".dy", integer=True))
                require(xy not in holes, f"{name}: two pins in one footprint hole")
                holes.add(xy)
            require((0, 0) in holes, f"{name}: one pin must be at origin")
            body = fp.get("body_mm", {})
            for k in ("x", "y", "width", "height"):
                number(body.get(k), f"{name}.body_mm.{k}", 0.001 if k in ("width", "height") else None)
            number(fp.get("height_mm"), name + ".height_mm", 0)
            boolean(fp.get("hot"), name + ".hot")
            if "polarity" in fp:
                require(fp["polarity"]["pin"] in numbers, f"{name}: unknown polarity pin")
        self.parts, self.pins, self.reserved_pads = {}, {}, {}
        require(isinstance(self.placement.get("parts"), dict), "placement.parts must be an object")
        for pid, data in self.placement["parts"].items():
            fid = data["footprint"]
            require(fid in self.footprints["footprints"], f"{pid}: unknown footprint {fid}")
            fp = self.footprints["footprints"][fid]
            origin = point(data["hole"])
            angle = data.get("rotation", 0)
            require(type(angle) is int and angle in (0, 90, 180, 270), f"{pid}: invalid rotation")
            boolean(data.get("locked", False), pid + ".locked")
            boolean(data.get("substitution_approved", False), pid + ".substitution_approved")
            ref = nonempty(data.get("ref", pid), pid + ".ref")
            pins = []
            mapping = data.get("pin_map", {})
            require(set(mapping) <= {p["number"] for p in fp["pins"]}, f"{pid}: pin_map has unknown source pin")
            for p in fp["pins"]:
                dx, dy = rotate((p["dx"], p["dy"]), angle)
                identity = mapping.get(p["number"], p)
                pin = Pin(ref, nonempty(identity.get("number"), pid + ".mapped number"), nonempty(identity.get("name"), pid + ".mapped name"), (origin[0] + dx, origin[1] + dy), pid)
                require(pin.key not in self.pins, f"duplicate physical pin {pin.label}")
                require(not any(q.ref == pin.ref and q.number == pin.number for q in self.pins.values()), f"duplicate physical number {pin.ref}.#{pin.number}")
                pin.net = self.expected.get(pin.key, {}).get("net", f"UNKNOWN:{pin.label}")
                self.pins[pin.key] = pin
                pins.append(pin)
            r = fp["body_mm"]
            corners = [rotate((x, y), angle) for x in (r["x"], r["x"] + r["width"]) for y in (r["y"], r["y"] + r["height"])]
            rect = (origin[0] * self.pitch + min(x for x, y in corners), origin[1] * self.pitch + min(y for x, y in corners), origin[0] * self.pitch + max(x for x, y in corners), origin[1] * self.pitch + max(y for x, y in corners))
            self.parts[pid] = Part(pid, ref, fp, data, pins, rect)
            for extra in fp.get("extra_pads", []):
                require(extra.get("net") == "NC", f"{pid}: extra pads must explicitly be NC")
                dx, dy = rotate((number(extra.get("dx"), pid + ".extra.dx", integer=True), number(extra.get("dy"), pid + ".extra.dy", integer=True)), angle)
                xy = origin[0] + dx, origin[1] + dy
                require(xy not in self.reserved_pads, f"{pid}: duplicate reserved pad")
                self.reserved_pads[xy] = f"{pid}.extra:{extra.get('physical_pin', 'NC')}"
        self.nets = sorted({r["net"] for r in self.expected.values()} - {"NC"})
        self.conductors = []
        ids = set()
        require(isinstance(self.wiring.get("conductors"), list), "wiring.conductors must be an array")
        for i, c in enumerate(self.wiring["conductors"]):
            c = dict(c)
            c.setdefault("id", f"W{i + 1:04d}")
            require(nonempty(c["id"], "wire.id") not in ids, f"duplicate wire id {c['id']}")
            ids.add(c["id"])
            nonempty(c.get("net"), c["id"] + ".net")
            require(c.get("kind") in ("bare", "bridge", "jumper"), f"{c['id']}: invalid kind")
            c.setdefault("side", "top" if c["kind"] == "jumper" else "bottom")
            require(c["side"] in ("top", "bottom"), f"{c['id']}: invalid side")
            require(isinstance(c.get("path"), list) and len(c["path"]) >= 2, f"{c['id']}: path needs >= 2 holes")
            c["xy"] = [point(h) for h in c["path"]]
            require(all(a != z for a, z in zip(c["xy"], c["xy"][1:])), f"{c['id']}: zero-length segment")
            if c["kind"] != "jumper":
                c["contacts"] = path_points(c["xy"])
                require(len(set(c["contacts"])) == len(c["contacts"]), f"{c['id']}: repeated/self-intersecting exposed path; split into conductors")
                if c["kind"] == "bridge":
                    require(len(c["xy"]) == 2 and len(c["contacts"]) == 2, f"{c['id']}: bridge must join two adjacent holes")
            else:
                c["contacts"] = [c["xy"][0], c["xy"][-1]]
                require(c["contacts"][0] != c["contacts"][-1], f"{c['id']}: jumper endpoints must differ")
            boolean(c.get("locked", False), c["id"] + ".locked")
            c["length_mm"] = sum(distance(a, z) for a, z in zip(c["xy"], c["xy"][1:])) * self.pitch
            self.conductors.append(c)

    def usable(self, xy):
        x, y = xy
        m = self.margin
        return m <= x < self.columns - m and m <= y < self.rows - m and not any(a[0] <= x <= b[0] and a[1] <= y <= b[1] for a, b, _ in self.keepouts)

    def pin_at(self, selector):
        if HOLE.fullmatch(selector):
            return point(selector)
        require("." in selector, f"invalid pin selector {selector}")
        ref, name = selector.split(".", 1)
        pins = [p for p in self.pins.values() if p.ref == ref and (p.number == name[1:] if name.startswith("#") else p.name == name)]
        require(len(pins) == 1, f"unknown/ambiguous pin {selector}")
        return pins[0].xy

    def feature_at(self, part_id, feature):
        """Exact declared footprint feature, rotated into the A1 mm frame.

        Missing mating geometry is not inferred from a body rectangle.
        """
        part = self.parts[part_id]
        data = part.footprint.get("features", {}).get(feature)
        require(isinstance(data, dict) and "x_mm" in data and "y_mm" in data, f"{part_id}: footprint feature {feature!r} has no declared point")
        local = (number(data["x_mm"], part_id + ".feature.x"), number(data["y_mm"], part_id + ".feature.y"))
        dx, dy = rotate(local, part.data.get("rotation", 0))
        ox, oy = point(part.data["hole"])
        result = dict(data, xy_mm=(ox * self.pitch + dx, oy * self.pitch + dy))
        if "direction" in data:
            require(isinstance(data["direction"], list) and len(data["direction"]) == 2, f"{part_id}: feature direction needs two numbers")
            result["direction"] = rotate(tuple(number(v, part_id + ".feature.direction") for v in data["direction"]), part.data.get("rotation", 0))
        return result

    def edge_distance(self, xy_mm, edges, reference="board_edge"):
        require(reference in ("board_edge", "physical_outline", "grid_boundary"), f"unsupported edge reference {reference!r}")
        require(isinstance(edges, list) and edges and set(edges) <= {"N", "E", "S", "W"}, "edges must be a nonempty N/E/S/W array")
        if reference == "grid_boundary":
            if not hasattr(self, "_grid_edges"):
                usable = [(x, y) for x in range(self.columns) for y in range(self.rows) if self.usable((x, y))]
                require(usable, "grid_boundary has no usable holes")
                x0, y0 = min(x for x, y in usable), min(y for x, y in usable)
                x1, y1 = max(x for x, y in usable), max(y for x, y in usable)
                rows = {"N": [(x, y) for x, y in usable if y == y0], "S": [(x, y) for x, y in usable if y == y1]}
                cols = {"W": [(x, y) for x, y in usable if x == x0], "E": [(x, y) for x, y in usable if x == x1]}
                self._grid_edges = {e: (tuple(v * self.pitch for v in min(points)), tuple(v * self.pitch for v in max(points))) for e, points in {**rows, **cols}.items()}
            segments = self._grid_edges
        else:
            x0, y0, x1, y1 = self.board_rect
            segments = dict(N=((x0, y0), (x1, y0)), E=((x1, y0), (x1, y1)), S=((x0, y1), (x1, y1)), W=((x0, y0), (x0, y1)))
        return min(segment_distance(xy_mm, xy_mm, *segments[e]) for e in edges)

    def wire_data(self):
        return {"schema_version": 1, "conductors": [{k: v for k, v in c.items() if k not in ("xy", "contacts", "length_mm")} for c in self.conductors]}


def write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
