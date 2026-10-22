# L1 — F1 evaluation candidate (2026-10-22)

**LVS PASS; hard-rule acceptance FAIL. Not released for construction.** The approved envelopes and hard proximity targets are mutually incompatible. No rule or shared input was changed. See [blocking constraints](blocking_constraints.md) and the executable [reproduction](prove_constraints.py).

| Metric | Final result |
|---|---|
| Parts / logical pins / nets / NC | 54 / 186 / 42 / 22; exact approved CSV copy |
| LVS | PASS; no shorts, opens, NC wiring, floating conductors, or wire-graph cycles |
| Hard T7 rules | **27 PASS / 9 FAIL / 25 UNCHECKED** (61 total) |
| Additional core DRC | 1 BODY_OFFBOARD: C311, conservative grid envelope; nominal actual-board fit passes |
| Soft T7 rules | 9 PASS / 6 FAIL / 3 UNCHECKED |
| T7 weighted soft score, evaluated lower bound | **176.356546**; priority 2 = 160.981546, priority 3 = 15.375000 |
| Shared tool generic score | **5,854,351.219**; includes error/unchecked/provisional penalties |
| Insulated jumpers / bridges | **39 / 0**, all underside |
| Bare pieces / straight bare segments / bends | **86 / 173 / 87**; jumper bends 0 |
| Wire length | **3201.762 mm** = bare 1912.620 + insulated 1289.142 |
| Longest IN line | HDD1_IN1, **89.803 mm** (hard 152.4 mm passes; soft 88.9 mm slightly exceeded) |
| VREF root → driver, mm | CH1 45.009, CH2 14.811, CH3 30.691, CH4 64.758 |
| J104 VM → VIN, CH1–4, mm | 45.72, 81.28, 116.84, 152.40 |
| J101 GND → driver GND13, CH1–4, mm | 53.34, 88.90, 124.46, 160.02 |
| J101 GND → driver GND2, CH1–4, mm | 40.64, 76.20, 111.76, 147.32 |
| Used bbox, grid-origin mm | (-2.760, 1.680)–(137.160, 99.920): **139.920 × 98.240 mm**, 13745.741 mm² |
| Nominal actual board | 155 × 114 mm; body bbox (6.160, 9.150)–(145.110, 107.390) mm; origin remains derived |
| Build effort | **125 wire pieces**, 250 wire-end terminations + 193 component/adapter tails; 361 distinct solder sites with end/bend/8-hole supports; 863 if every modeled contact land is soldered |
| Continuity export | 1534 bare-board tests; modules/components absent and capacitors discharged |

Wire stock lengths exclude cut/strip allowance:

| Copper / gauge | Bare mm | Insulated mm |
|---|---:|---:|
| 1.0 mm | 375.920 | 0.000 |
| 0.6 mm | 193.040 | 0.000 |
| AWG22 | 0.000 | 102.606 |
| 0.5 mm | 657.860 | 0.000 |
| AWG18 | 0.000 | 30.900 |
| 0.51 mm | 685.800 | 0.000 |
| AWG24 | 0.000 | 1155.636 |

The shared T7 file contains no top-level tool `weights`; consequently `metrics.score` uses the CLI defaults. The separate T7 score above sums the CLI's weighted atomic soft findings. It is a **lower bound**, because three soft checks remain unimplemented; it must not be presented as a complete passing T7 ranking. Inputs and SHA256 hashes are recorded in `out/metrics_extra.json`.

## Floor plan and assumptions

CH1–4 run left to right along the north edge, all carriers at 270°. Every channel repeats its VIN/bulk/ceramic/OUT/CS pattern; coil XH3 centre pins remain unconnected. A continuous 1.0 mm VM trunk at row 8 and power-GND trunk at row 10 each has one bend and 2-hole separation. Channel bare branches are 0.6 mm; insulated channel returns are AWG22. Entry is west, converter southwest, Pico lower centre with USB south, SmartNet southeast, VREF centrally at AC16. Stop J213 is on the east edge; FAULT pull-up is beside Pico GP15. All 13 probes are populated.

GND_ENTRY, GND_LOGIC and VREF_ROOT are explicit physical junctions. **G01, G02 and V01 star checks PASS.** Separate paired AWG24 links feed/return the converter from entry; the quiet network does not return through the motor trunk. No parts or top-side jumpers cover modules. Off-board harnesses are not included in the CSV netlist model.

F1 deviations: entry is west-middle rather than NW because four full-width thermal channel tiles occupy the north band; stop is east rather than south to stay near its pull-down; channel pitch is 14 holes to retain carrier-to-can thermal clearance. C311 extends 1.49 mm beyond the tool's fictitious half-pitch edge, while remaining 6.16 mm inside the nominal real board. No electrical substitution beyond the approved T5 inputs was introduced.

## Trade-offs, risks and verification

The 39 insulated wires preserve the strict stars and cross the two power trunks and interleaved module/Pico pins. Bare wiring is 59.7% of total length and 68.8% of pieces. Long PWM jumpers, the central diagonal bundle and the weakly checked mechanical features make this an evaluation candidate, not a demonstrated optimum. The local search tested 100 orders in the final routing configuration (seed 38 selected), after earlier topology experiments; redundant overlaps and four pieces were removed without changing LVS or hard-rule statuses.

Provisional fit, solder surface clearance, connector/USB/grip access, off-board gauge/drop, thermal performance and 3D stacking remain unverified. The actual board mounting centres are 5.00 mm from edges versus M02's 5.08 mm target. Approved AWG26 precrimp coil leads conflict with W07's 0.28 mm² target. These need supervisor resolution. Wirelist endpoints are solder nodes: lay heavy wires against underside pads/tails; do not force multiple leads through a 1 mm hole. Use the planned <=8-hole supports and >=10 mm underside standoffs, then inspect flex/transport shorts. Estimated assembly and inspection: **6–10 hours**, engineering estimate excluding HDD/panel harness work.

Shared tool output (full log: `out/verify.log`):

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 58 errors, 50 warnings; 3201.8 mm wire, 39 jumpers; score 5854351.2
ERROR BODY_OFFBOARD: C311
ERROR RULE:P02: D105.1 -> $VM_ENTRY: 5.000 holes (max 3)
ERROR RULE:P05: C312.1 / U310.14: 3 holes > 2
ERROR RULE:P13: C108.1 / U107.1: 6 holes > 4
ERROR RULE:P15: C208.1 / U207.5: 4 holes > 2
ERROR RULE:V02: R210.1 / $VREF_ROOT: 3 holes > 2
WIRE LIST: 125 steps
CONTINUITY: 1534 tests (bare board, power off)
```

All three SVGs were parsed, locally rasterized and visually inspected. Ref labels were shifted off their own pads, polarity and XH centre NC marks; the bottom view is mirrored BC→A. See `out/render_qc.json`. No shared files, other candidate folders, purchases, uploads or public writes were made.
