**L2 / F2, round 2 — 2026-10-22, approved v0.2 rules.**

**LVS PASS; core DRC 0; hard FAIL list `[]`; `ranking_pass=true`.** All 54 refs are retained. Round 1 is preserved under `round1/`. Shared files were not edited. The local rule copy is byte-identical to `design_rules_v0.2.json`; every public CLI command uses `--board ユニバーサル基板/board.json`.

| Metric | Final result |
|---|---:|
| Comparison tuple | **`(true, 0, 0, 39, 234.178847, 109, 4064.79)`** |
| Hard rules | **38 PASS / 0 FAIL / 23 UNCHECKED** |
| LVS | 186/186 pins, 42 nets, 22 NC; 7 extra reserved pads unwired |
| Insulated jumpers | **39**, all on bottom; **target ≤16 not reached** |
| Bare pieces / bridges / total pieces | **70 / 0 / 109** |
| Wire length, bare / jumper / total | **1,805.94 / 2,258.85 / 4,064.79 mm** |
| Length by conductor size | 1.0 mm: **838.20**; 0.6 mm: **246.38**; AWG24: **365.76**; AWG26: **2,614.45 mm** |
| Bends, bare / jumper | **71 / 38**, total **109** |
| Longest IN path | **129.54 mm / 51 pitches**, hard maximum 60 pitches |
| T7 soft penalty | **234.178847**, partial; unchecked soft rules B03, B04, S03 |
| Legacy scalar score | 3,262,388.338; includes UNCHECKED findings, so use the comparison tuple |
| Used bbox, A1-relative mm | **(-1.37, -4.80)–(139.92, 102.46)**, **141.29 × 107.26 mm** |
| Physical board | **155 × 114 mm**, nominal grid origin (8.92, 7.47) mm |
| Build effort, estimate | **109 cut wires**, 193 component/extra-pad leads, **315 planned solder stations**; approximately **8–12 student-hours** before bench debugging |

The bbox extends into the approved real-board margins. The metric `used_area_fraction` uses the smaller grid-window denominator and is not a physical-board occupancy fraction. Wire lengths exclude stripping, slack, vertical detours and external harnesses. The conservative tool contact model has 814 unique pin/wire contact locations; the smaller support plan covers functional junctions, pins, bends and ≤8-pitch support intervals. Physical support and ≥10 mm bottom standoffs remain build checks.

| Channel / carrier | Position, pin 1 | VREF branch | VM: J104.2 → VIN | GND: J101.2 → GND13 / GND2 |
|---|---|---:|---:|---:|
| HDD1 / U310 | South-left, M34 | 88.90 mm | 347.98 mm | 261.62 / 274.32 mm |
| HDD2 / U320 | South-right, AF34 | 66.04 mm | 284.48 mm | 218.44 / 226.06 mm |
| HDD3 / U330 | East-middle, AS17 | 55.88 mm | 203.20 mm | 152.40 / 149.86 mm |
| HDD4 / U340 | East-north, AS6 | 63.50 mm | 154.94 mm | 160.02 / 157.48 mm |

**Floor plan and deviations.** F2 is folded onto the east and south perimeter: the former upper pair forms an east column, while the lower pair remains a south row. This is a departure from a strict rectangular 2 × 2; it satisfies both M08 and the unchanged hard M11 same-rotation rule. Every carrier remains rotation 0. The two south coil mating centres are 2 pitches from the south grid boundary; the two east centres are 2 pitches from east. SmartNet is on the south edge. Pico is A25/270°, USB west, with GP2–GP9 facing the driver field. USB mouth distance is approximately 0.539 pitch from the west grid boundary. Entry/protection occupies northwest, regulator north, VREF centrally, stop header east. No scaffold is fitted or reserved; all 13 probe pins remain.

GND_ENTRY is F8, GND_LOGIC T9 and VREF_ROOT AA19. G01/G02/V01 all PASS. The 1.0 mm motor distribution and 0.6 mm local branches retain explicit branch annotations; common switch/feed and shared south-return segments were upgraded to 1.0 mm. AWG24 feeds the converter/Pico, AWG26 the low-current logic. Represented onboard conductor areas satisfy the W01–W06 area minima; complete voltage-drop/contact/harness rules remain unchecked. One return trunk uses the free columns between the east carrier socket rows. Short and long insulated crossovers preserve star separation and exact NC isolation. Local channel patterns repeat where their different edge/cap envelopes permit.

**Trade-offs and remaining risks.** Jumper count improved from round-1's 41 to 39 while removing its M08 failure. Both Pico orientations, perimeter channel orders, routing-stage orders, bare-path retries and redundant-wire pruning were compared. Five final conversion orders converged to the same 39-jumper result; no global optimum is claimed. There are still long insulated spans, and only 44.4% of total wire length is bare despite 70/109 pieces being bare. This candidate should be compared against L1/L3 rather than treated as meeting the 16-jumper stretch target. Some CS probes are farther than the 3-pitch soft target. The longest power paths, real contact resistance, 3D wire layering, carrier grip, BOOTSEL/plug access, thermal margins and actual socket/adapter fit require review and bring-up tests.

The receiver was shifted one column away from HDD1's coil connector after a supplementary spacing check found a pin-level violation. Local nominal wire-surface checks now pass S01/S02 at **6.307 / 12.198 mm** minimum respectively, including the declared westward FAULT escapes. These checks do not override official UNCHECKED status or prove solder/lead tolerances. Some common VM/return runs are separated by more than the B01 two-pitch target; power-path pairing specifically needs Claude's visual review/redesign. Approved AWG26 off-board coil leads remain subject to the HDD heat test.

**UNCHECKED hard rules:** `B01, B02, B07, C01, C02, C03, M02, M03, M04, M05, M06, M08, M10, M12, S01, S02, W01, W02, W03, W04, W05, W06, W07`. M08's unknown portion is only the undeclared J104/J213 mating-face points; all declared coil/SmartNet features satisfy its distance bound. The 32 legacy error findings are exclusively UNCHECKED rule findings, not known hard violations. Claude's v0.2 policy accepts these for visual/build-time review. Assembly and bench evidence remains outstanding.

**Verification, final files:**

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 32 errors, 57 warnings; 4064.8 mm wire, 39 jumpers; score 3262388.3
COMPARISON: [true, 0, 0, 39, 234.178847, 109, 4064.79]
WIRE LIST: 109 steps
CONTINUITY: 1303 tests (bare board, power off)
```

The legacy exit code is 1 because of UNCHECKED findings; `ranking_pass` is true. `out/report.json`, `metrics.json`, `netlist_actual.csv`, `wirelist.csv`, `continuity.csv` and logs describe the same final placement/wiring. Continuity instructions are for the unpopulated wired board, power removed and capacitors discharged. `out/support.csv` and `part_values.csv` supplement the tool output.

All three SVGs were parsed, rendered offline and visually inspected. Each has 54 nonoverlapping refdes labels; bottom is mirrored. The shared tool supplies the physical board outline/M3 holes; a candidate-only USB arrow was added in the free margin. `*.tool.svg` preserves the unmodified tool drawings. PNG previews are supplemental. Browser file URLs were blocked in round 1; no browser workaround was used. Run `validate_final.py` with the required Python to regenerate verification, SVGs and CSVs without rerouting. `placement.json` and `wiring.json` are authoritative; routing scripts and `variants/` are exploratory history and must not be rerun blindly over the winner. Source hashes and nominal measurements are in `out/audit_local.json`.
