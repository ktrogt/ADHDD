# L1 round 3 - F1, approved rules v0.2

2026-10-22. Work and decisions are recorded here because the candidate scope permits writes only inside L1.

**LVS PASS; core DRC 0; hard FAIL IDs `[]`; ranking_pass true.** Jumpers remain **31**: the <=20 target (stretch <=16) was **not reached**. The selected tuple improves secondary metrics; no minimum-jumper proof is claimed. The complete previous state is preserved under `round2/`, alongside the existing `round1/` archive.

| Metric | Round 2 | Round 3 |
|---|---:|---:|
| Comparison tuple | `[true, 0, 0, 31, 220.580952, 78, 3158.323]` | **`[true, 0, 0, 31, 218.580952, 57, 3077.043]`** |
| Hard audit PASS / FAIL / UNCHECKED | 38 / 0 / 23 | **38 / 0 / 23** |
| Insulated jumpers | 31 | **31** |
| T7 soft penalty, evaluated portion | 220.580952 | **218.580952** |
| Native bends (all bare) | 78 | **57** |
| Total wire mm | 3158.323 | **3077.043** |
| Bare wire mm | 1864.360 | 1783.080 |
| Insulated wire mm | 1293.963 | 1293.963 |
| Wire pieces | 122 = 91 bare + 31 insulated | **126 = 95 bare + 31 insulated** |
| Bare straight spans | 169 | 152 |

Tuple order: LVS ok, core DRC errors, hard FAIL count, jumpers, T7 soft penalty, bends, total wire mm. Soft penalty falls 0.91%, length 2.57%, and native bends 26.92%. The trade-off is four additional wire pieces. Some bend reduction comes from cutting bent runs into simpler pieces; the straight-span count is also reported to make that visible. Collinear pieces were consolidated again before export. All 31 insulated wires retain their round-2 endpoints and gauges.

| Detail | Final value |
|---|---|
| Scope / LVS | 54 refs, 186/186 pins, 42 nets, 22 NC; exact approved CSV |
| Hard FAIL list | **`[]`** |
| Star audit | G01 / G02 / V01 PASS |
| Longest IN | HDD4_IN1: 94.834 mm |
| VREF root to CH1-4, mm | 64.758, 30.691, 20.320, 45.009 |
| J104 VM to CH1-4 VIN, mm | 142.240, 106.680, 71.120, 40.640 |
| J101 GND to CH1-4 GND13, mm | 154.940, 124.460, 88.900, 53.340 |
| J101 GND to CH1-4 GND2, mm | 147.320, 111.760, 76.200, 40.640 |
| Used bbox, grid-origin mm | (-2.760, 1.680) to (137.160, 102.460); **139.920 x 100.780 mm** |
| Bbox area / board | 14101.138 mm2 / real 155 x 114 mm; bodies pass 1 mm outline margin |
| Build effort | **126 wire pieces**, 252 wire ends + 193 component/adapter tails; **336 planned solder sites** |
| Conservative solder count | 803 pad sites if every modeled bare-wire contact is soldered |
| Tool generic legacy score | 3252014.054; retains UNCHECKED penalties, so the native tuple is used for selection |

Wire stock lengths exclude cutting/stripping allowance:

| Copper / gauge | Bare mm | Insulated mm |
|---|---:|---:|
| 1.0 mm | 337.820 | 0.000 |
| 0.6 mm | 297.180 | 0.000 |
| AWG22 | 0.000 | 38.100 |
| 0.5 mm | 322.580 | 0.000 |
| AWG18 | 0.000 | 30.900 |
| 0.51 mm | 825.500 | 0.000 |
| AWG24 | 0.000 | 1224.963 |

F1 as built is unchanged from round 2: identical 270-degree carriers, CH4/CH3/CH2/CH1 left to right along the north edge; each has its local bulk/ceramic capacitors, XH3 coil connector (centre NC) and CS probe. Pico has north-facing GP2-GP9 and east-facing USB; SmartNet/buffer is southeast, entry west, converter southwest, VREF central and stop header south. All 13 probes remain. No scaffold is fitted or reserved. Singleton expansion GPIO nets, ADC_VREF and VBUS have no host wires.

Bare 1.0 mm VM/power-GND trunks remain at TOP rows 8/10, two holes apart; channel branches remain >=0.6 mm. CH1 retains its bare end-of-strip GND/FAULT escape; the other channels keep the repeated pattern. The converter retains its dedicated mostly bare, paired feed/return, and its short insulated quiet-return termination. GND_ENTRY, GND_LOGIC and VREF_ROOT retain their approved anchors. A graph check also found no multi-channel power path using copper below 0.5 mm2; this supplements, and does not change, the UNCHECKED current/drop audit. No wire-graph cycle remains.

Round-3 work recorded 1541 routing/placement variants in `out/round3_experiments.json`, plus single- and paired-chain rewiring searches. Only hard-zero candidates with soft penalty <=110% of round 2 were eligible. The final changes trim unused bare tails and shorten local control/ground/receiver runs; ARM_SW now follows a simpler bare route. Further tested jumper reductions did not improve the tuple. These are search results, not impossibility proofs:

- Under-module buses: freeing the SLEEP/+3V3 rows displaced crossings into the power-return trunk and PMODE/VREF taps; the combined bus/FAULT-star trials did not beat 31 jumpers.
- FAULT on the power side: row 6 is too close to OUT copper outside the named escape disks; going below the paired trunks needs insulated crossings. Four direct insulated spokes clear the signal field but add a wire elsewhere.
- Bare staggered IN / central Pico: north-shift and south-USB candidates passed hard checks but needed at least 34 and 36 jumpers respectively in the recorded searches. The west-USB trial also encountered FAULT/UART length limits.
- Bare VREF star: four bare driver branches were feasible, but their source connection and +3V3 feed crossings offset the saved jumpers.
- Regulator near entry: the existing dedicated paired supply was retained; moving it for the alternative Pico arrangements did not improve the complete layout.

**UNCHECKED hard IDs:** B01, B02, B07, C01, C02, C03, M02, M03, M04, M05, M06, M08, M10, M12, S01, S02, W01, W02, W03, W04, W05, W06, W07. Soft UNCHECKED IDs: B03, B04, S03. These are not counted as passes. They include source/scope evidence; exposed lead/pad/solder surface gaps; mounting, grips, USB/BOOTSEL and mating access; output separation; conductor/contact/drop/harness and support checks. M08 remains UNCHECKED for header feature points not declared by the library. The tool's legacy headline/exit is FAIL/1 solely because it emits these UNCHECKED findings as errors; the supervisor's accepted criterion is `ranking_pass: true`, core DRC 0 and no hard FAIL.

Assumptions: use the approved physical board, adapters/sockets and v0.2 AWG26 precrimp coil leads; no rule relaxation or electrical substitution was introduced. Build checks remain for actual fit, underside height/strain, solder gaps, connector grip/USB access, thermal/noise behaviour and measured contact/drop. Use >=10 mm underside standoffs and the endpoint/bend/<=8-hole supports in `wire_support.csv`. Lay heavy wires against pads/tails rather than forcing several leads into one hole. Assembly and inspection estimate: **6-10 hours**, excluding HDD/panel harnesses.

Verification used `--board ユニバーサル基板/board.json` on every CLI invocation:

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 32 errors, 48 warnings; 3077.0 mm wire, 31 jumpers; score 3252014.1
COMPARISON: [true, 0, 0, 31, 218.580952, 57, 3077.043]
hard_failed_rule_ids: []
WIRE LIST: 126 steps
CONTINUITY: 1219 tests (bare board, power off)
```

All three actual SVGs were opened as XML, rasterized offline and visually inspected: labels/polarity/NC marks are readable, and bottom coordinates are mirrored BC..A. CSV coordinates remain TOP. Continuity tests apply to the unpowered wired bare board before components/modules are fitted. Deliverables include SVGs, native reports/metrics, wire list, continuity, actual netlist, pin map, support plan and hashes. Shared files and other candidate folders were not changed.
