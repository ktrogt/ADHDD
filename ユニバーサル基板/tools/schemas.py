"""Generate JSON Schema files documenting the canonical v1 interfaces."""
from pathlib import Path

from model import save_json


def generate(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    string = {"type": "string", "minLength": 1}
    hole = {"type": "string", "pattern": "^[A-Z]+[1-9][0-9]*$"}
    positive = {"type": "number", "exclusiveMinimum": 0}
    nonnegative = {"type": "number", "minimum": 0}
    selectors = {"type": "array", "items": string, "minItems": 1}

    def obj(properties, required=(), **extra):
        return dict(type="object", properties=properties, required=list(required), **extra)

    def root(title, properties, required):
        return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": title, **obj({"schema_version": {"const": 1}, **properties}, ("schema_version", *required))}

    board = root("Perfboard board v1", dict(columns={"type": "integer", "minimum": 1}, rows={"type": "integer", "minimum": 1}, pitch_mm={"const": 2.54}, type={"enum": ["single_sided_independent", "double_sided_plated"], "default": "single_sided_independent"}, edge_margin_holes={"type": "integer", "minimum": 0, "default": 0}, body_clearance_mm={**nonnegative, "default": 0.5}, keepouts={"type": "array", "items": obj({"id": string, "from": hole, "to": hole}, ("from", "to"))}, provisional={"type": "boolean"}), ("columns", "rows", "pitch_mm"))
    board["properties"].update(outline_mm=obj({"width": positive, "height": positive}, ("width", "height")), grid_origin_mm=obj({"x": nonnegative, "y": nonnegative}, ("x", "y")), body_edge_margin_mm={**nonnegative, "default": 1.0})
    board["dependentRequired"] = {"outline_mm": ["grid_origin_mm"]}
    pin = obj(dict(number=string, name=string, dx={"type": "integer"}, dy={"type": "integer"}), ("number", "name", "dx", "dy"))
    fp = obj(dict(pins={"type": "array", "items": pin, "minItems": 1}, body_mm=obj(dict(x={"type": "number"}, y={"type": "number"}, width=positive, height=positive), ("x", "y", "width", "height")), height_mm=nonnegative, hot={"type": "boolean"}, polarity=obj({"pin": string, "label": string}, ("pin",)), provisional={"type": "boolean"}, notes={"type": "string"}), ("pins", "body_mm", "height_mm", "hot"))
    fp["properties"]["extra_pads"] = {"type": "array", "items": obj({"physical_pin": string, "dx": {"type": "integer"}, "dy": {"type": "integer"}, "net": {"const": "NC"}, "populate": {"type": "boolean"}}, ("dx", "dy", "net"))}
    fp["properties"]["requires_Claude_approval"] = {"type": "boolean"}
    fp["properties"]["features"] = {"type": "object", "description": "Point features used by on_edge need x_mm/y_mm relative to pin 1; direction is optional. Other feature records remain metadata."}
    footprints = root("Perfboard footprint library v1", {"footprints": {"type": "object", "additionalProperties": fp}}, ("footprints",))
    part = obj(dict(footprint=string, hole=hole, rotation={"enum": [0, 90, 180, 270], "default": 0}, locked={"type": "boolean", "default": False}, ref=string, value={"type": "string"}, pin_map={"type": "object", "additionalProperties": obj({"number": string, "name": string}, ("number", "name"))}), ("footprint", "hole"))
    part["properties"]["substitution_approved"] = {"type": "boolean", "default": False}
    placement = root("Perfboard placement v1", {"parts": {"type": "object", "additionalProperties": part}, "nodes": {"type": "object", "additionalProperties": {"oneOf": [hole, obj({"hole": hole}, ("hole",))]}}}, ("parts",))
    conductor = obj(dict(id=string, net=string, kind={"enum": ["bare", "bridge", "jumper"]}, side={"enum": ["top", "bottom"]}, path={"type": "array", "items": hole, "minItems": 2}, gauge=string, type=string, colour=string, area_mm2=positive, locked={"type": "boolean", "default": False}), ("net", "kind", "path"))
    wiring = root("Perfboard conductors v1", {"conductors": {"type": "array", "items": conductor}}, ("conductors",))
    common = dict(id=string, type=string, severity={"enum": ["error", "warning", "info"], "default": "error"}, enabled={"type": "boolean", "default": True}, rationale={"type": "string"}, source={"type": "array", "items": string}, original_rule_id=string, notes={"type": "string"})
    variants = {
        "min_part_distance": ({"a": selectors, "b": selectors, "min_mm": nonnegative}, ("a", "b", "min_mm")),
        "near_pin": ({"parts": selectors, "pin": string, "max_holes": nonnegative}, ("parts", "pin", "max_holes")),
        "max_net_length": ({"net": string, "max_mm": nonnegative}, ("net", "max_mm")),
        "max_branch_length": ({"net": string, "from": string, "to": selectors, "max_mm": nonnegative}, ("net", "from", "to", "max_mm")),
        "net_clearance": ({"a": selectors, "b": selectors, "min_holes": nonnegative}, ("a", "b", "min_holes")),
        "edge": ({"parts": selectors, "edge": {"enum": ["top", "bottom", "left", "right", "any"]}, "max_holes": nonnegative}, ("parts", "max_holes")),
        "star": ({"net": string, "root": string, "targets": {**selectors, "minItems": 2}}, ("net", "root", "targets")),
        "wire_gauge": ({"nets": selectors, "max_awg": nonnegative, "min_area_mm2": nonnegative, "current_a": nonnegative, "ampacity_a_per_mm2": positive}, ("nets",)),
    }
    rule_schema = []
    for kind, (properties, required) in variants.items():
        rule_schema.append(obj({**common, **properties, "type": {"const": kind}}, ("id", "type", *required), additionalProperties=False))
    router = obj(dict(power_nets=selectors, power_gauge=string, signal_gauge=string, bend_penalty=nonnegative, jumper_side={"enum": ["top", "bottom"]}, use_bridges={"type": "boolean"}, trunks={"type": "array", "items": obj({"id": string, "net": string, "path": {"type": "array", "items": hole, "minItems": 2}, "gauge": string}, ("net", "path"))}))
    router["properties"]["star_rule_ids"] = {"type": "array", "items": string, "uniqueItems": True}
    router["properties"]["stars"] = {"type": "array", "items": obj({"id": string, "net": string, "root": string, "branches": {"type": "array", "minItems": 2, "items": obj({"id": string, "endpoints": selectors}, ("endpoints",))}}, ("net", "root", "branches"))}
    rules = root("Perfboard generic rules v1 (T7 adapter documented separately)", dict(groups={"type": "object", "additionalProperties": selectors}, net_classes={"type": "object", "additionalProperties": selectors}, router=router, power_roots={"type": "object", "additionalProperties": string}, weights={"type": "object", "properties": {key: nonnegative for key in ("wire_mm", "jumpers", "bridges", "crossings", "area_mm2", "error", "warning", "info")}, "additionalProperties": False}, rules={"type": "array", "items": {"oneOf": rule_schema}}), ("rules",))
    for name, data in (("board", board), ("footprints", footprints), ("placement", placement), ("wiring", wiring), ("design_rules", rules)):
        save_json(directory / f"{name}.schema.json", data)
    (directory / "netlist.schema.md").write_text("# CSV netlist schema\n\nExactly these four unique header fields: `net,ref,pin_number,pin_name`. UTF-8 (BOM accepted). All fields except physical pin_number are nonempty strings. Each (ref,pin_name) and each nonempty (ref,pin_number) must be unique. NC is a separate disconnected state for each pin. Parsed by the approved 基板/compare_netlist.py read_rows(key='name'). Physical footprint pin numbers are required and must agree with any supplied CSV number.\n", encoding="utf-8")


if __name__ == "__main__":
    generate(Path(__file__).parent / "schemas")
