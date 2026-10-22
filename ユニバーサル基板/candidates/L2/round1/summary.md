**L2 / F2 — 2026-10-22. Electrical candidate only; NOT FOR BUILD.**

LVS passes exactly. A full hard-rule pass is impossible with the frozen inputs: five small combinations of approved envelopes and distance limits are mutually inconsistent. Exhaustive certificates are in `out/infeasibility.json`, reproduced by `prove_infeasible.py`. No rule, footprint, netlist or shared file was changed. Local copies of all four electrical/geometric inputs are byte-identical to the shared inputs; SHA-256 evidence is in `out/audit_local.json`.

| Metric | Final result |
|---|---:|
| LVS | **PASS**, 186/186 pins, 42 nets, 22 NC; 7 extra reserved pads also unwired |
| Core placement/wiring DRC | **0 errors** |
| Hard audit, 61 rules | **27 PASS / 9 FAIL / 25 UNCHECKED** |
| Soft audit, 18 rules | 9 PASS / 6 FAIL / 3 UNCHECKED |
| Canonical `ub.py metrics.score`, full T7 policy loaded | **4,956,893.145** |
| T7 engine-reported soft penalty subtotal, partial | **121.661** = safety 107.703 + buildability 13.958 |
| Insulated jumpers | **41**, all underside |
| Bare wire pieces / bridges | **79 / 0**; 150 straight bare legs |
| Total wire pieces / wirelist steps | **120** |
| Length, bare / insulated | **1,696.72 / 1,894.84 mm**; total **3,591.56 mm** |
| Length by gauge | 1.0 mm: 640.08; 0.6 mm: 327.66; AWG24: 416.56; AWG26: 2,207.26 mm |
| Bends, bare / insulated | **71 / 35** |
| Longest IN connection | **109.22 mm / 43 pitches**, hard ceiling 60 pitches |
| Used bounding box, relative to A1 | **(0, 0)–(137.16, 100.31) mm**, area 13,758.52 mm² |
| Board / model window | Physical 155 × 114 mm; tool grid window 139.70 × 101.60 mm |
| Build effort, estimate | 120 cut wires; 193 component/extra-pad leads; **315 planned solder stations**; approximately **8–12 student-hours**, before bench debugging |

Wire lengths are planar tool lengths, excluding stripping, vertical detours, slack and external harnesses. The conservative tool contact model has 772 unique pin/wire contact locations; soldering every listed contact is more work than the 315-station support plan. `out/support.csv` explicitly covers pins, wire junctions, bends and ≤8-pitch support intervals. Use ≥10 mm bottom standoffs. Physical support/assembly remains unverified.

The supplied T7 file has no top-level score weights. The tool's scalar score uses its reported default length/jumper/crossing/severity weights and includes UNCHECKED errors; it does **not** apply T7 rule weights to that scalar. Both the scalar and the separately accumulated engine `t7_penalty` values are reported. The latter includes partial per-conductor bend findings and is not a complete branch-level T7 ranking; unchecked conditions are not treated as passed.

| Channel | Position | VREF from C211.1 | VM: J104.2 → VIN | GND: J101.2 → GND13 / GND2 |
|---|---|---:|---:|---:|
| HDD1 / U310 | SE, AI33 | 68.58 mm | 129.54 mm | 134.62 / 142.24 mm |
| HDD2 / U320 | NW, R8 | 38.10 mm | 124.46 mm | 124.46 / 132.08 mm |
| HDD3 / U330 | NE, AI8 | 45.72 mm | 167.64 mm | 167.64 / 175.26 mm |
| HDD4 / U340 | SW, R33 | 60.96 mm | 86.36 mm | 91.44 / 99.06 mm |

**Floor plan as built.** Four identical rotation-0 carrier tiles retain the F2 2 × 2 arrangement. Each repeats its local bypass, bulk capacitor, output pair and CS probe pattern. Pico is BB18/90°, USB east; the divider is Y22; input and regulator occupy the west; SmartNet is at the northeast/east side; stop control is southeast. No scaffold is fitted or reserved. All 13 probe pins are retained.

The 1.0 mm motor supply/return pair runs north on K1–AM1 / L2–AL2 and south on K28–AM28 / L27–AL27, fed by west spokes. Individual channel wires are 0.6 mm. The converter has a separate AWG24 supply/return pair. GND_ENTRY is F21, GND_LOGIC O24 and VREF_ROOT Y22. The three required GND/VREF star checks pass. Branch/current classes are annotated in `wiring.json`; represented onboard copper areas satisfy W01–W06, while contacts, voltage drop and external W07 remain unproved.

**Deviations and trade-offs.** Coil connectors are local, top-mating connectors on each tile's east side, rather than true north/south edge exits. Their physical-edge distances are 35.41 mm north and 15.09 mm south. The Pico USB mouth is 10.09 mm from the true east edge; J101 is 10.19 mm from west; SmartNet faces are 14.00 mm from east. These do not meet the literal feature-edge limits and are not waived. The 7.47 mm minimum grid border already makes M08's 5.08 mm physical-edge limit impossible for the approved vertical XH mating centres, independent of F2.

Paired power and quiet output exclusions take precedence over the earlier 34-jumper experiment. The final layout uses 79/120 bare pieces, but only 47.2% of total length is bare; reducing the long insulated spans remains desirable. The final routing-order search examined 56 paired-power variants and improved jumper count by less than 5%; no global optimum is claimed. All eight OUT runs are bare. S01/S02 supplementary nominal surface checks pass at minimum 6.682 / 12.101 mm respectively, including the declared two-pitch westward FAULT escapes. These are local-model evidence, not official T7 PASS results.

**Unresolved hard contradictions — no relaxation adopted.**

| Rules | Frozen maximum | Smallest demonstrated feasible placement distance |
|---|---:|---:|
| P02 TVS ↔ entry bulk, with M01 | 3 pitches | 5 |
| P11/P12 OUT, with M01 and P05 | 4 | 5 |
| P13/P14 regulator capacitors, with H07 | 4 | 6 |
| P15/P16 buffer bypass, with M01 | 2 / 3 | 4 / 4 |
| V02/V03 lower-divider resistor, with M01 | 2 | 3 |

The U107 footprint explicitly reserves a conservative 18.42 × 16.1 mm union, although its metadata gives actual body size 11.5 × 7.55 mm with an unverified offset. A supervisor-approved footprint refinement may be preferable to relaxing P13/P14. In addition, M02 requests ≥5.08 mm mounting-edge distance, whereas approved M3 centres are nominally 5.00 mm from the board edges. Feature access, module grip, 3D jumper stacking, solder clearance, real adapter fit, external harness ratings and the 14 assembly/bench evidence checks remain unresolved. None was silently certified.

**Verification evidence.** The requested public CLI commands ran against the final files. `verify` returns 1 because hard audit fails; render/wirelist/continuity return 0. Its key lines are:

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 49 errors, 52 warnings; 3591.6 mm wire, 41 jumpers; score 4956893.1
WIRE LIST: 120 steps
CONTINUITY: 1432 tests (bare board, power off)
```

All 49 errors are rule findings: 24 atomic failures across the nine rules above, plus 25 UNCHECKED conditions. There are 22 provisional-footprint warnings. `out/verify.log`, `report.json`, `metrics.json`, `wirelist.csv`, `continuity.csv` and `netlist_actual.csv` are retained. Continuity instructions apply before components are fitted, with power removed and capacitors discharged.

**Visual check and reproducibility.** All three SVGs were opened as XML, rendered offline and visually inspected at readable size; all 54 refdes labels have nonoverlapping Arial text boxes. Bottom is mirrored. The local-file browser action was blocked, so offline previews were used without a browser workaround. Final SVGs add the nominal physical board/M3 outline and USB arrow; unmodified tool SVGs are retained as `*.tool.svg`. PNG previews are supplementary. Run `validate_final.py` with the required Python to regenerate verification and all views; it does not reroute. `route_local.py paired-inputs:2,7,0,3,4,5,6,1` followed by `finish_candidate.py` reproduces the routing/cleanup from the supplied final placement. Frozen circuit values, substitutions and scope were assumed exactly as supplied; new measurements and effort estimates are engineering calculations, not bench observations.
