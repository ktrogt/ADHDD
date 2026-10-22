"""Meaningful adversarial regression tests, using only unittest and stdlib."""
from __future__ import annotations

import copy
import csv
import io
import unittest
from pathlib import Path

from documents import continuity, wirelist
from model import COMPARE, Project, column, point, save_json, write_csv
from optimize import optimize
from router import route
from rules import evaluate
from verify import UnionFind, verify


def fixture():
    board = dict(schema_version=1, columns=8, rows=8, pitch_mm=2.54, type="single_sided_independent", edge_margin_holes=0, body_clearance_mm=0.2, keepouts=[])
    footprints = dict(schema_version=1, footprints={"PIN": dict(pins=[dict(number="1", name="P", dx=0, dy=0)], body_mm=dict(x=-0.5, y=-0.5, width=1, height=1), height_mm=2, hot=False)})
    locations = {"P1": "B3", "P2": "G3", "P3": "D1", "P4": "D7", "P5": "B6", "P6": "G6", "N1": "H8"}
    placement = dict(schema_version=1, parts={ref: dict(footprint="PIN", hole=xy, rotation=0, locked=False, value="test pad") for ref, xy in locations.items()})
    expected = {(ref, "P"): dict(net=net, ref=ref, pin_number="1", pin_name="P") for ref, net in zip(locations, ("A", "A", "B", "B", "C", "C", "NC"))}
    wires = [dict(id="A1", net="A", kind="bare", side="bottom", path=["B3", "G3"], gauge="AWG26"), dict(id="B1", net="B", kind="jumper", side="top", path=["D1", "D7"], gauge="AWG26"), dict(id="C1", net="C", kind="bare", side="bottom", path=["B6", "G6"], gauge="AWG26")]
    wiring = dict(schema_version=1, conductors=wires)
    rules = dict(schema_version=1, rules=[])
    return Project(Path(__file__).parent / "fixtures" / "faults", board=board, footprints=footprints, placement=placement, wiring=wiring, rules=rules, expected=expected)


def codes(p):
    return {i["code"] for i in verify(p)["issues"]}


def changed(p, attribute, fn):
    value = copy.deepcopy(getattr(p, attribute))
    fn(value)
    return p.clone(**{attribute: value})


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()

    def test_valid_insulated_crossing_does_not_short(self):
        report = verify(self.p)
        self.assertTrue(report["passed"], report["issues"])
        self.assertTrue(report["lvs_pass"])

    def test_open(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"].pop())
        self.assertIn("LVS:SPLIT", codes(p))
        self.assertFalse(verify(p)["lvs_pass"])

    def test_grid_crossing(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][1].update(kind="bare", side="bottom"))
        self.assertTrue({"SHORT", "BARE_CROSSING", "HOLE_NET_CONFLICT", "LVS:MERGED"} <= codes(p))

    def test_bare_through_wrong_pin(self):
        p = changed(self.p, "placement", lambda v: v["parts"]["P3"].update(hole="D3"))
        p = changed(p, "wiring", lambda v: v["conductors"][1].update(path=["D3", "D7"]))
        self.assertIn("SHORT", codes(p))

    def test_bare_overlap(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"].append(dict(id="B2", net="B", kind="bare", path=["C3", "E3"])))
        self.assertIn("BARE_CROSSING", codes(p))

    def test_jumper_interior_hole_is_insulated(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][1].update(path=["D1", "D3", "D7"]))
        self.assertTrue(verify(p)["lvs_pass"])

    def test_jumper_endpoint_connects(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][1].update(path=["D3", "D7"]))
        self.assertIn("SHORT", codes(p))

    def test_nc_stub_even_no_other_pin(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"].append(dict(id="NCSTUB", net="A", kind="jumper", path=["H8", "H7"])))
        self.assertIn("NC_CONNECTED", codes(p))

    def test_nc_to_nc(self):
        rows = copy.deepcopy(self.p.expected)
        rows[("P6", "P")]["net"] = "NC"
        p = self.p.clone(expected=rows)
        p = changed(p, "wiring", lambda v: (v["conductors"].pop(), v["conductors"].append(dict(id="NC2", net="A", kind="jumper", path=["G6", "H8"]))))
        self.assertIn("NC_CONNECTED", codes(p))

    def test_labels_do_not_make_connectivity(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"].pop())
        p = changed(p, "wiring", lambda v: v["conductors"].extend([dict(id="CS1", net="C", kind="bare", path=["B6", "C6"]), dict(id="CS2", net="C", kind="bare", path=["F6", "G6"])]))
        self.assertIn("LVS:SPLIT", codes(p))

    def test_wrong_wire_label(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][0].update(net="B"))
        self.assertIn("WIRE_NET_MISMATCH", codes(p))

    def test_unknown_wire_net(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][0].update(net="TYPO"))
        self.assertIn("UNKNOWN_WIRE_NET", codes(p))

    def test_missing_physical_pin(self):
        p = changed(self.p, "placement", lambda v: v["parts"].pop("P1"))
        self.assertIn("LVS:MISSING", codes(p))

    def test_unknown_pin_name(self):
        p = changed(self.p, "placement", lambda v: v["parts"]["P1"].update(pin_map={"1": dict(number="1", name="WRONG")}))
        self.assertTrue({"LVS:MISSING", "LVS:UNKNOWN_PIN"} <= codes(p))

    def test_wrong_number_same_name(self):
        p = changed(self.p, "placement", lambda v: v["parts"]["P1"].update(pin_map={"1": dict(number="2", name="P")}))
        self.assertIn("LVS:PIN_ID_MISMATCH", codes(p))

    def test_hole_collision(self):
        p = changed(self.p, "placement", lambda v: v["parts"]["P2"].update(hole="B3"))
        self.assertIn("PIN_COLLISION", codes(p))

    def test_offboard(self):
        p = changed(self.p, "placement", lambda v: v["parts"]["P2"].update(hole="Z30"))
        self.assertIn("PIN_OFFBOARD_OR_KEEPOUT", codes(p))

    def test_keepout(self):
        p = changed(self.p, "board", lambda v: v["keepouts"].append(dict(id="mount", **{"from": "C3", "to": "D3"})))
        self.assertIn("WIRE_OFFBOARD_OR_KEEPOUT", codes(p))

    def test_jumper_crosses_keepout(self):
        p = changed(self.p, "board", lambda v: v["keepouts"].append(dict(id="mount", **{"from": "D4", "to": "D4"})))
        self.assertIn("WIRE_KEEPOUT", codes(p))

    def test_top_bare_on_single_rejected(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][0].update(side="top"))
        self.assertIn("UNSUPPORTED_TOP_EXPOSED", codes(p))

    def test_double_sided_plated_is_not_two_isolated_layers(self):
        p = changed(self.p, "board", lambda v: v.update(type="double_sided_plated"))
        p = changed(p, "wiring", lambda v: v["conductors"][1].update(kind="bare", side="top"))
        self.assertTrue({"SHORT", "PLATED_HOLE_SHORT"} <= codes(p))

    def test_floating_wire(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"].append(dict(id="FLOAT", net="A", kind="bare", path=["A8", "B8"])))
        self.assertIn("FLOATING_CONDUCTOR", codes(p))

    def test_extra_physical_pad_must_remain_nc(self):
        p = changed(self.p, "footprints", lambda v: v["footprints"]["PIN"].update(extra_pads=[dict(physical_pin="unused", dx=0, dy=-1, net="NC")]))
        p = changed(p, "wiring", lambda v: v["conductors"][0].update(path=["B3", "B2", "G2", "G3"]))
        self.assertIn("EXTRA_PAD_CONNECTED", codes(p))
        self.assertFalse(verify(p)["lvs_pass"])

    def test_bridge_non_adjacent_rejected(self):
        with self.assertRaises(ValueError):
            changed(self.p, "wiring", lambda v: v["conductors"][0].update(kind="bridge"))

    def test_diagonal_bare_rejected(self):
        with self.assertRaises(ValueError):
            changed(self.p, "wiring", lambda v: v["conductors"][0].update(path=["B3", "G4"]))

    def test_duplicate_pin_rejected(self):
        with self.assertRaises(ValueError):
            changed(self.p, "placement", lambda v: v["parts"].update(DUP=dict(v["parts"]["P1"], ref="P1")))

    def test_body_clearance(self):
        p = changed(self.p, "footprints", lambda v: v["footprints"]["PIN"]["body_mm"].update(width=14))
        self.assertIn("BODY_OVERLAP", codes(p))

    def test_same_net_no_wire_single_terminal_is_valid(self):
        expected = {("P1", "P"): self.p.expected[("P1", "P")]}
        placement = dict(schema_version=1, parts={"P1": self.p.placement["parts"]["P1"]})
        p = self.p.clone(placement=placement, expected=expected, wiring=dict(schema_version=1, conductors=[]))
        self.assertTrue(verify(p)["lvs_pass"])

    def test_coordinate_roundtrip(self):
        for x in (0, 25, 26, 51, 52, 701, 702):
            self.assertEqual(point(column(x) + "12"), (x, 11))

    def test_rotation_and_split_socket_pin_mapping(self):
        fp = copy.deepcopy(self.p.footprints)
        fp["footprints"]["PAIR"] = dict(pins=[dict(number="1", name="ONE", dx=0, dy=0), dict(number="2", name="TWO", dx=1, dy=0)], body_mm=dict(x=-0.5, y=-0.5, width=3.54, height=1), height_mm=2, hot=False)
        placement = copy.deepcopy(self.p.placement)
        placement["parts"]["P1"].update(footprint="PAIR", rotation=90, pin_map={"1": dict(number="1", name="P"), "2": dict(number="2", name="SECOND")})
        expected = copy.deepcopy(self.p.expected)
        expected[("P1", "SECOND")] = dict(net="NC", ref="P1", pin_number="2", pin_name="SECOND")
        p = self.p.clone(footprints=fp, placement=placement, expected=expected)
        self.assertEqual(p.pins[("P1", "SECOND")].xy, (1, 3))
        self.assertTrue(verify(p)["lvs_pass"])
        placement["parts"]["P1_L"] = placement["parts"].pop("P1")
        placement["parts"]["P1_L"]["ref"] = "P1"
        q = self.p.clone(footprints=fp, placement=placement, expected=expected)
        self.assertTrue(verify(q)["lvs_pass"])

    def test_invalid_numbers(self):
        for value in (True, -1, float("nan"), "8"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                changed(self.p, "board", lambda v: v.update(columns=value))

    def test_union_find_large_chain_no_recursion_limit(self):
        uf = UnionFind()
        for x in range(5000, 0, -1):
            uf.union((x, 0), (x - 1, 0))
        self.assertEqual(uf.find((5000, 0)), (0, 0))


class RuleAndRoutingTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()

    def rule(self, **r):
        return self.p.clone(rules=dict(schema_version=1, rules=[dict(id="test", severity="error", **r)]))

    def test_unknown_rule_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate(self.rule(type="not_implemented"))

    def test_unknown_selector_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate(self.rule(type="edge", parts=["MISSPELL"], max_holes=2))

    def test_near_pin(self):
        self.assertTrue(evaluate(self.rule(type="near_pin", parts=["P2"], pin="P1.P", max_holes=1)))

    def test_min_body_distance(self):
        self.assertTrue(evaluate(self.rule(type="min_part_distance", a=["P1"], b=["P2"], min_mm=20)))

    def test_net_length(self):
        self.assertTrue(evaluate(self.rule(type="max_net_length", net="A", max_mm=1)))

    def test_branch_length_actual_detour(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][0].update(kind="jumper", path=["B3", "A3", "A2", "G2", "G3"]))
        p = p.clone(rules=dict(schema_version=1, rules=[dict(id="length", type="max_branch_length", net="A", **{"from": "P1.P", "to": ["P2.P"]}, max_mm=14)]))
        self.assertTrue(evaluate(p))

    def test_branch_open(self):
        p = self.rule(type="max_branch_length", net="A", **{"from": "P1.P", "to": ["P2.P"]}, max_mm=100)
        p = changed(p, "wiring", lambda v: v["conductors"].pop(0))
        self.assertTrue(evaluate(p))

    def test_clearance_includes_jumper_projection(self):
        self.assertTrue(evaluate(self.rule(type="net_clearance", a=["A"], b=["B"], min_holes=1)))

    def test_gauge(self):
        self.assertTrue(evaluate(self.rule(type="wire_gauge", nets=["A"], max_awg=20, min_area_mm2=0.5)))

    def test_edge(self):
        self.assertTrue(evaluate(self.rule(type="edge", parts=["P1"], edge="right", max_holes=1)))

    def test_star_shared_trunk_rejected(self):
        p = self.p.clone(expected={k: dict(v, net="A" if v["net"] == "C" else v["net"]) for k, v in self.p.expected.items()})
        p = changed(p, "wiring", lambda v: (v["conductors"][2].update(net="A"), v["conductors"].append(dict(id="BR", net="A", kind="bare", path=["G3", "G6"]))))
        p = p.clone(rules=dict(schema_version=1, rules=[dict(id="star", type="star", net="A", root="P1.P", targets=["P2.P", "P6.P"])]))
        self.assertTrue(evaluate(p))

    def test_router_lvs_and_determinism(self):
        a, b = route(self.p), route(self.p)
        self.assertEqual(a, b)
        self.assertTrue(verify(self.p.clone(wiring=a))["lvs_pass"])

    def test_router_preserves_locked_wire(self):
        p = changed(self.p, "wiring", lambda v: v["conductors"][1].update(locked=True))
        wiring = route(p)
        self.assertEqual(wiring["conductors"][0], p.wire_data()["conductors"][1])
        self.assertTrue(verify(p.clone(wiring=wiring))["lvs_pass"])

    def test_router_jumper_fallback_barrier(self):
        p = changed(self.p, "wiring", lambda v: (v["conductors"].clear(), v["conductors"].append(dict(id="BARRIER", net="B", kind="bare", path=["D1", "D8"], locked=True, gauge="AWG26"))))
        result = route(p)
        self.assertGreaterEqual(result["router_stats"]["jumper_fallbacks"], 1)
        self.assertTrue(verify(p.clone(wiring=result))["lvs_pass"])

    def test_t7_numeric_pin_near_and_unchecked(self):
        p = self.p.clone(rules=dict(schema_version="adhdd-perfboard-rules/1.0", rules=[dict(id="NEAR", type="near", severity="hard", params=dict(pairs=[dict(a="P1.1", b="P2.1")], max_holes=1, metric="manhattan_pin")), dict(id="UNKNOWN", type="accessible", severity="hard", params={})]))
        report = verify(p)
        self.assertFalse(report["passed"])
        self.assertEqual({r["id"]: r["status"] for r in report["rule_checks"]}, {"NEAR": "FAIL", "UNKNOWN": "UNCHECKED"})
        self.assertTrue(report["lvs_pass"])

    def test_t7_subset_missing_policy_never_passes(self):
        p = self.p.clone(rules=dict(schema_version=1, rules=[], uncovered_rule_ids=["C03"]))
        report = verify(p)
        self.assertFalse(report["passed"])
        self.assertEqual(report["unchecked_rules"], 1)

    def test_optimizer_deterministic_and_locked(self):
        p = changed(self.p, "placement", lambda v: v["parts"]["P1"].update(locked=True))
        a, sa = optimize(p, iterations=50, seed=7)
        b, sb = optimize(p, iterations=50, seed=7)
        self.assertEqual(a, b)
        self.assertEqual(sa, sb)
        self.assertEqual(a["parts"]["P1"], p.placement["parts"]["P1"])
        self.assertLessEqual(sa["final_estimate_score"], sa["initial_estimate_score"])


class OutlineAndScoringTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()

    def physical(self, p=None, **extra):
        return changed(p or self.p, "board", lambda b: b.update(outline_mm=dict(width=30, height=30), grid_origin_mm=dict(x=5, y=5), **extra))

    def t7(self, rules, p=None):
        return (p or self.p).clone(rules=dict(schema_version="adhdd-perfboard-rules/1.0", rules=rules))

    def test_outline_accepts_body_outside_grid(self):
        p = changed(self.p, "footprints", lambda f: f["footprints"]["PIN"]["body_mm"].update(y=-2))
        self.assertIn("BODY_OFFBOARD", codes(p))
        self.assertNotIn("BODY_OFFBOARD", codes(self.physical(p)))

    def test_outline_default_one_mm_margin_and_override(self):
        p = changed(self.p, "footprints", lambda f: f["footprints"]["PIN"]["body_mm"].update(y=-4.5))
        self.assertIn("BODY_OFFBOARD", codes(self.physical(p)))
        self.assertNotIn("BODY_OFFBOARD", codes(self.physical(p, body_edge_margin_mm=0)))

    def test_outline_keeps_hole_limits_and_hardware_keepouts(self):
        p = self.physical()
        p = changed(p, "placement", lambda v: v["parts"]["N1"].update(hole="I8"))
        self.assertIn("PIN_OFFBOARD_OR_KEEPOUT", codes(p))
        p = changed(self.physical(), "board", lambda v: v.update(keepouts=[dict(id="hardware", **{"from": "B3", "to": "B3"})]))
        self.assertTrue({"BODY_KEEPOUT", "PIN_OFFBOARD_OR_KEEPOUT"} <= codes(p))

    def test_width_height_metadata_does_not_change_legacy(self):
        p = changed(self.p, "board", lambda b: b.update(width_mm=100, height_mm=100, grid_origin_mm=dict(x=30, y=30)))
        self.assertEqual(p.body_allowed_rect, self.p.body_allowed_rect)
        self.assertEqual(codes(p), codes(self.p))

    def test_outline_requires_valid_origin(self):
        with self.assertRaises(ValueError):
            changed(self.p, "board", lambda b: b.update(outline_mm=dict(width=30, height=30)))
        with self.assertRaises(ValueError):
            self.physical(body_edge_margin_mm=100)

    def test_on_edge_grid_reference_and_default_physical(self):
        p = changed(self.physical(), "footprints", lambda f: f["footprints"]["PIN"].update(features=dict(mating_face=dict(x_mm=0, y_mm=0))))
        rule = dict(id="M07", type="on_edge", severity="hard", weight=0, params=dict(parts=["P3"], edges=["N"], max_holes=0.1, feature="mating_face", reference="grid_boundary"))
        self.assertFalse(evaluate(self.t7([rule], p)))
        rule["params"].pop("reference")
        findings = evaluate(self.t7([rule], p))
        self.assertEqual(findings[0]["status"], "FAIL")
        self.assertEqual(findings[0]["reference"], "board_edge")

    def test_missing_edge_feature_is_unchecked(self):
        rule = dict(id="M07", type="on_edge", severity="hard", params=dict(parts=["P3"], edges=["N"], max_holes=2, feature="mating_face", reference="grid_boundary"))
        self.assertEqual(evaluate(self.t7([rule]))[0]["status"], "UNCHECKED")

    def test_partial_edge_data_does_not_hide_real_failure(self):
        fp = copy.deepcopy(self.p.footprints)
        fp["footprints"]["FEATURE"] = copy.deepcopy(fp["footprints"]["PIN"])
        fp["footprints"]["FEATURE"]["features"] = dict(mating_face=dict(x_mm=0, y_mm=0))
        p = self.p.clone(footprints=fp)
        p = changed(p, "placement", lambda v: v["parts"]["P1"].update(footprint="FEATURE"))
        rule = dict(id="M08", type="on_edge", severity="hard", params=dict(parts=["P1", "P2"], edges=["N"], max_holes=0.1, feature="mating_face", reference="grid_boundary"))
        report = verify(self.t7([rule], p))
        self.assertEqual(report["rule_checks"][0]["status"], "FAIL")
        self.assertEqual(report["metrics"]["hard_fail_count"], 1)
        self.assertEqual(report["metrics"]["unchecked_hard_count"], 0)
        self.assertEqual(report["metrics"]["partially_unchecked_hard_count"], 1)

    def test_feature_rotation_and_grid_margin(self):
        p = changed(self.p, "footprints", lambda f: f["footprints"]["PIN"].update(features=dict(mating_face=dict(x_mm=2.54, y_mm=0, direction=[0, -1]))))
        p = changed(p, "placement", lambda v: v["parts"]["P1"].update(rotation=90))
        self.assertEqual(p.feature_at("P1", "mating_face")["xy_mm"], (2.54, 7.62))
        self.assertEqual(p.feature_at("P1", "mating_face")["direction"], (1, 0))
        p = changed(p, "board", lambda b: b.update(edge_margin_holes=1))
        self.assertEqual(p.edge_distance((2.54, 2.54), ["N"], "grid_boundary"), 0)

    def test_grid_boundary_uses_first_usable_row(self):
        p = changed(self.p, "board", lambda b: b.update(keepouts=[dict(id="reserved-row", **{"from": "A1", "to": "H1"})]))
        self.assertEqual(p.edge_distance((5.08, 2.54), ["N"], "grid_boundary"), 0)
        self.assertEqual(p.edge_distance((5.08, 0), ["N"], "grid_boundary"), 2.54)

    def test_physical_outline_svg_uses_real_dimensions(self):
        import xml.etree.ElementTree as ET
        from render import drawing
        p = self.physical()
        top = ET.fromstring(drawing(p, "top")[0])
        bottom = ET.fromstring(drawing(p, "bottom")[0])
        ns = {"s": "http://www.w3.org/2000/svg"}
        board = next(r for r in top.findall(".//s:rect", ns) if r.attrib.get("x") == "16.0" and r.attrib.get("y") == "16.0")
        self.assertEqual((float(board.attrib["width"]), float(board.attrib["height"])), (30, 30))
        a_top = next(t for t in top.findall(".//s:text", ns) if t.text == "A")
        a_bottom = next(t for t in bottom.findall(".//s:text", ns) if t.text == "A")
        self.assertEqual(float(a_top.attrib["x"]), 21)
        self.assertEqual(float(a_bottom.attrib["x"]), 41)

    def test_accessible_uses_per_part_approach_and_stays_unchecked(self):
        rule = dict(id="M06", type="accessible", severity="hard", params=dict(targets=["P1", "P2", "P3"], feature="mating_and_latch", approach="two_sides", approach_by_part=dict(P1="top", P2="outward")))
        findings = evaluate(self.t7([rule]))
        self.assertEqual({f["part"]: f["approach"] for f in findings}, dict(P1="top", P2="outward", P3="two_sides"))
        self.assertTrue(all(f["status"] == "UNCHECKED" for f in findings))

    def test_weighted_soft_normalised_atomic_penalties(self):
        rules = [dict(id="soft", type="near", severity="soft", weight=10, params=dict(pairs=[dict(a="P1.1", b="P2.1"), dict(a="P5.1", b="P6.1")], max_holes=2, metric="manhattan_pin")), dict(id="unknown", type="accessible", severity="soft", weight=999, params=dict(targets=["P1"], approach="top", feature="probe_tip"))]
        report = verify(self.t7(rules))
        self.assertEqual(report["metrics"]["t7_soft_penalty"], 30)
        self.assertEqual(report["metrics"]["hard_fail_count"], 0)
        self.assertEqual(report["metrics"]["t7_soft_penalty_by_rule"], {"soft": 30})
        self.assertEqual(report["metrics"]["unchecked_soft_rule_ids"], ["unknown"])
        self.assertFalse(report["metrics"]["soft_penalty_complete"])

    def test_weighted_soft_lower_bound(self):
        rule = dict(id="gap", type="min_part_distance", severity="soft", weight=10, params=dict(a="P1", b="P2", min_holes=10, metric="body_edge_euclidean", exclude_same=True))
        penalty = verify(self.t7([rule]))["metrics"]["t7_soft_penalty"]
        self.assertAlmostEqual(penalty, 5.393701, places=6)

    def test_unchecked_hard_not_failure_but_legacy_result_preserved(self):
        rule = dict(id="missing", type="accessible", severity="hard", params=dict(targets=["P1"], approach="top", feature="probe_tip"))
        report = verify(self.t7([rule]))
        self.assertFalse(report["passed"])
        self.assertEqual(report["metrics"]["comparison_tuple"][:3], [True, 0, 0])
        self.assertEqual(report["metrics"]["unchecked_hard_count"], 1)
        self.assertTrue(report["metrics"]["ranking_pass"])

    def test_hard_fail_count_is_rules_not_pairs(self):
        rule = dict(id="near", type="near", severity="hard", params=dict(pairs=[dict(a="P1.1", b="P2.1"), dict(a="P5.1", b="P6.1")], max_holes=1, metric="manhattan_pin"))
        self.assertEqual(verify(self.t7([rule]))["metrics"]["hard_fail_count"], 1)

    def test_comparison_sort_lvs_first_and_actual_bends(self):
        valid = verify(self.p)["metrics"]
        bad = verify(changed(self.p, "wiring", lambda v: v["conductors"].pop()))["metrics"]
        self.assertLess(valid["lexicographic_sort_key"], bad["lexicographic_sort_key"])
        p = changed(self.p, "wiring", lambda v: v["conductors"][1].update(path=["D1", "D2", "D7"]))
        self.assertEqual(verify(p)["metrics"]["bends"], 0)
        p = changed(self.p, "wiring", lambda v: v["conductors"][1].update(path=["D1", "E1", "E7", "D7"]))
        self.assertEqual(verify(p)["metrics"]["bends"], 2)


class HierarchicalStarRoutingTests(unittest.TestCase):
    def project(self):
        p = fixture()
        expected = {k: dict(v, net="A" if v["net"] == "C" else v["net"]) for k, v in p.expected.items()}
        expected[("P7", "P")] = dict(net="A", ref="P7", pin_number="1", pin_name="P")
        placement = copy.deepcopy(p.placement)
        placement["parts"]["P7"] = dict(footprint="PIN", hole="H5", rotation=0, locked=False)
        placement["nodes"] = dict(ROOT="B3", CHILD="G3")
        specs = [dict(id="TOP", type="star", severity="hard", weight=0, params=dict(net="A", root="$ROOT", branches=[dict(id="DIRECT", endpoints=["P5.1"]), dict(id="CHILD", endpoints=["$CHILD"])], shared_segment_policy="within_branch_only", max_shared_holes=0)), dict(id="CHILD", type="star", severity="hard", weight=0, params=dict(net="A", root="$CHILD", branches=[dict(id="ONE", endpoints=["P6.1"]), dict(id="TWO", endpoints=["P7.1"])], shared_segment_policy="within_branch_only", max_shared_holes=0))]
        rules = dict(schema_version="adhdd-perfboard-rules/1.0", nodes=dict(ROOT=dict(net="A", anchor="P1.1"), CHILD=dict(net="A", anchor="P2.1")), router=dict(star_rule_ids=["TOP", "CHILD"]), rules=specs)
        return p.clone(placement=placement, expected=expected, rules=rules)

    def test_hierarchical_stars_preserved_and_deterministic(self):
        p = self.project()
        wiring = route(p)
        self.assertEqual(wiring, route(p))
        report = verify(p.clone(wiring=wiring))
        self.assertTrue(report["passed"], report["issues"])
        self.assertTrue(report["lvs_pass"])
        self.assertEqual(wiring["router_stats"]["star_conductors"], 4)
        self.assertTrue(any(c["kind"] == "bare" for c in wiring["conductors"] if c.get("star_rule")))

    def test_preserved_star_net_requires_explicit_clear(self):
        p = self.project()
        p = changed(p, "wiring", lambda v: (v["conductors"].clear(), v["conductors"].append(dict(id="LOCKED", net="A", kind="jumper", path=["B3", "G3"], locked=True))))
        with self.assertRaisesRegex(ValueError, "no preserved/pre-routed conductors"):
            route(p)

    def test_conflicting_star_partition_rejected(self):
        p = self.project()
        p = changed(p, "rules", lambda r: r["rules"][1]["params"]["branches"][0].update(endpoints=["P5.1", "P6.1"]))
        with self.assertRaisesRegex(ValueError, "star partitions"):
            route(p)

    def test_canonical_flat_star_and_unlisted_terminal(self):
        p = self.project()
        rules = dict(schema_version=1, router=dict(star_rule_ids=["A_STAR"]), rules=[dict(id="A_STAR", type="star", net="A", root="P1.P", targets=["P2.P", "P5.P"])])
        p = p.clone(rules=rules)
        report = verify(p.clone(wiring=route(p)))
        self.assertTrue(report["passed"], report["issues"])

    def test_undefined_named_hub_is_not_guessed(self):
        p = changed(self.project(), "placement", lambda v: v["nodes"].pop("CHILD"))
        with self.assertRaisesRegex(ValueError, "declarations are required"):
            route(p)


def write_fixtures():
    p = fixture()
    p.directory.mkdir(parents=True, exist_ok=True)
    for filename, data in (("board.json", p.board), ("footprints.json", p.footprints), ("placement.json", p.placement), ("design_rules.json", p.rules), ("wiring.valid.json", p.wire_data())):
        save_json(p.directory / filename, data)
    write_csv(p.directory / "netlist.csv", COMPARE.COLUMNS, p.expected.values())
    bad = copy.deepcopy(p.wire_data())
    bad["conductors"][1].update(kind="bare", side="bottom")
    bad["conductors"].pop()
    save_json(p.directory / "wiring.json", bad)
    (p.directory / "README.md").write_text("# Deliberate faults\n\n`wiring.json`: A and B bare wires cross at D3 (short); C has no wire (open).\n`wiring.valid.json`: insulated B crossing, all nets connected, NC H8 isolated.\nRun ub.py verify --project tools/fixtures/faults: expected exit 1, SHORT + BARE_CROSSING + LVS:SPLIT.\n", encoding="utf-8")


def run():
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        write_fixtures()
    return result.wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
