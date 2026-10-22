**L3 hard-constraint findings, 2026-10-22.** These are comparisons against unchanged approved inputs. No relaxation is applied to `report.json`.

The shared tool reports 25 hard rules PASS, 11 FAIL and 25 UNCHECKED. Its 60 error findings comprise 33 failed rule instances, 25 unsupported checks, and two conservative body-boundary errors. LVS passes independently. All assembly and bench evidence remains outstanding.

**Footprint conflicts shared by the floor plans.** `reproduce_limits.py` enumerates every relevant integer placement and all four relative rotations using the approved bodies, pins and 1.016 mm M01 gap. The +/-13-hole search box contains every location that could satisfy these small distance bounds. Other board obstacles are removed in the pair proofs: failure in this easier problem is a necessary-condition obstruction, not a routing heuristic failure. Pin collisions are excluded. Results are in `infeasibility.json`.

| Rule combination | Approved bound | Necessary geometric lower bound | Current L3 route |
|---|---:|---:|---:|
| P02, TVS to C106, with M01 | 3 holes | 5 holes | 5 on both legs |
| P13 with H07, M78AR05-1 and 100 uF cans | 4 | 6 | 6 pin distance; P14 ground routes 8 |
| P15 with M01, DIP6 buffer and bypass | 2 | 4 | 4 pin distance; P16 maximum 4 |
| V02 with M01, lower divider and 220 nF | 2 | 3 | 3; V03 also 3 |
| P05=2 plus P11=4, carrier/bypass/XH3 | both | P11 must reach at least 5 if P05 stays 2 | OUT1 5, OUT2 2; P12 same |

The last proof includes the coil connector's reserved centre pad. With P05=2, the bypass has only one non-overlapping relative placement. Every connector placement satisfying P11=4 overlaps it. Merely moving the four channel blocks cannot solve this conflict.

**F3 packing and local bulk returns.** The unrotated carrier body is 18.38 mm high. H01 needs 7.62 mm between bodies, hence an integer origin pitch of at least 11 holes. Four origins span 33 holes; the total body envelope is 102.20 mm. T6 treats the 40-row board as 101.60 mm high, so this column cannot pass its boundary check. L3 puts the outer two bodies 0.30 mm beyond that virtual outline. Using the approved nominal 155 x 114 mm physical outline and grid origin, both retain 5.90 mm actual edge margin. This is calculated metadata, not a board measurement.

Three bulk capacitors sit east of the carriers in the inter-channel gaps: positive legs are 6 holes from VIN and returns are 9 holes from driver GND. Their whole routes are bare. At the north end, C341 remains west because there is no preceding gap: its pin distances are 10/11 holes and actual routes 9.055/11 holes. P08/P09 therefore still fail. Retaining this candidate requires pair-specific acceptance of 9-hole returns and the 11-hole north exception, or a changed board/floor plan. The 100 nF parts remain at 2 holes from both supply pins and pass P05/P06.

**Feature/access rules are not established by body fit.** T6 explicitly leaves these UNCHECKED. The board's physical margin lies outside its modelled hole-array outline. Using the nominal physical outline gives USB mouth inset 8.64 mm, DC mouth 8.74 mm, SmartNet mating points 10.01 mm, and coil mating points 15.09–16.54 mm. These exceed literal M07/M08/M09 distances. The owner must define whether “edge” means the usable grid edge or the actual board edge and whether a clear approach corridor is the acceptance criterion. They are not silently declared compliant here.

M02's mounting-centre requirement is 5.08 mm from an edge, while the approved board specifies 5.00 mm. The actual layout's nearest part and wire remain 9.33/11.75 mm from a mount centre, but this does not resolve the 0.08 mm intrinsic discrepancy. M05 also needs interpretation: east carrier-to-connector body gap is 1.089 mm, insufficient for a 5.08 mm W/E grip strip. N/S removal is proposed; body gaps there are 9.56 mm between modules, with 5.90 mm at the outer physical edges. No physical extraction trial was performed.

**Tool limitation and local workaround.** `tools/verify.py::placement_drc` ignores `width_mm`, `height_mm` and `grid_origin_mm`, as already documented in the approved board metadata. The standard router refuses the two BODY_OFFBOARD findings. `route_candidate.gate` excludes only those exact two findings during routing; the official verifier is subsequently run unchanged. No shared tool or rule file is edited. The complete report still fails.

T6 also does not implement a scalar score using T7 per-rule weights. Its documented scalar uses wire length, counts, area, error and warning weights. L3 reports that scalar and separately sums the tool-emitted `t7_penalty` values. Unsupported checks remain unsupported.

**Supplementary evidence, with limits.** `audit_extra.py` checks nominal physical outline/mount margins, reports copper-only resistance estimates and samples S01/S02 separation. Those separation estimates assume jumper OD <=1.6 mm and output pad OD <=1.8 mm, subtract a 0.125 mm sampling bound, and retain the exact FAULT terminal exception. They exclude manufacturing and solder tolerances and do not turn the official UNCHECKED results into PASS. `solder_plan.py` separately proves terminal LVS using only the recommended solder/anchor sites and continuous wire pieces, at maximum 8-hole support spacing.

The one-hole GND/VREF stars and 1.0 mm copper in nominal 1.0 mm holes need a physical termination/fit review. Multiple wire ends at a hub, socket extraction, connector latches, bottom wire heights, strain relief, contact ratings, solder fillets and all A/T bench checks remain review/assembly work. No purchase or electrical substitution is requested by this candidate.

External harness policy also needs reconciliation: `parts_fit.csv` approves the 131312 AWG26 precrimp coil lead with thermal testing, whereas W07 requires at least 0.28 mm² (AWG22 class). L3's board OUT wiring is AWG22. No external wire is represented or silently accepted as satisfying W07.
