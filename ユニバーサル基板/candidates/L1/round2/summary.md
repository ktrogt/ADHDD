# L1 round 2 — F1, approved rules v0.2

**LVS PASS; core DRC 0; hard FAIL IDs `[]`; ranking_pass true.** There are **31 insulated jumpers**, versus 39 in round 1. The target <=16 was **not reached**; this is the best candidate found, not a proof of minimum wiring. Round-1 files are retained unchanged under `round1/`.

| Metric | Final result |
|---|---|
| Comparison tuple | **`[true, 0, 0, 31, 220.580952, 78, 3158.323]`** |
| Tuple order | LVS ok, core DRC errors, hard FAIL IDs count, jumpers, T7 soft penalty, bends, wire mm |
| Scope | 54 refs, 186/186 pins, 42 nets, 22 NC; approved CSV byte-identical |
| Hard audit | **38 PASS / 0 FAIL / 23 UNCHECKED** |
| Star rules | G01 / G02 / V01 all PASS |
| Soft penalty | **220.580952**, evaluated portion; B03/B04/S03 remain incomplete |
| Wire pieces | **122** = 91 bare + 31 insulated; no solder bridges |
| Bare straight segments / bends | 169 / 78; native total bends 78 |
| Total length | **3158.323 mm** = 1864.360 bare + 1293.963 insulated |
| Longest IN line | HDD4_IN1, 94.834 mm |
| VREF root → CH1–4, mm | 64.758, 30.691, 20.320, 45.009 |
| J104 VM → CH1–4 VIN, mm | 162.560, 127.000, 91.440, 66.040 |
| J101 GND → CH1–4 GND13, mm | 154.940, 124.460, 88.900, 53.340 |
| J101 GND → CH1–4 GND2, mm | 147.320, 111.760, 76.200, 40.640 |
| Used bbox, grid-origin mm | (-2.760, 1.680)–(137.160, 102.460); **139.920 × 100.780 mm** |
| Used bbox area | 14101.138 mm²; all bodies pass the real 155 × 114 mm outline with its 1 mm margin |
| Build effort | 122 wire pieces; 244 wire ends + 193 component/adapter tails; **345 planned solder sites** with end/bend/8-hole supports |
| Conservative contact count | 834 sites if every modeled contacted land is soldered |
| Connectivity checks | No shorts, opens, NC host wiring, floating conductors or remaining wire-graph cycles |

Stock lengths exclude cut/strip allowance:

| Copper / gauge | Bare mm | Insulated mm |
|---|---:|---:|
| 1.0 mm | 353.060 | 0.000 |
| 0.6 mm | 337.820 | 0.000 |
| AWG22 | 0.000 | 38.100 |
| 0.5 mm | 436.880 | 0.000 |
| AWG18 | 0.000 | 30.900 |
| 0.51 mm | 736.600 | 0.000 |
| AWG24 | 0.000 | 1224.963 |

The native comparison tuple is authoritative for ranking. The CLI's legacy `passed`/exit code remains FAIL/1 solely because it emits UNCHECKED as error findings; this is accepted by the supervisor's v0.2 policy. `metrics.score` retains that legacy penalty and is not used instead of the tuple.

The layout retains F1's north driver row, central VREF and opposite control side. Carriers are identically rotated 270°, with **CH4, CH3, CH2, CH1 left to right**. Pico is now horizontal at 90°: GP2–GP9 faces north toward the drivers and USB reaches the east grid edge. SmartNet is below Pico, outside the PWM fanout. Entry remains west, converter southwest, stop header south. All 13 probes are fitted; no scaffold area is reserved. The five named expansion singleton nets, ADC_VREF and VBUS have no host wires.

Main VM/GND runs are bare 1.0 mm copper beneath the carriers at TOP rows 8/10; their common horizontal portions are two holes apart. Channel branches are >=0.6 mm. Routing VM taps around the left of each local ground branch removes the former bulk-cap ground jumpers while preserving all local length bounds. CH1, at the end of the trunks, also has a bare local GND tie and bare FAULT escape. Other channel wiring repeats the same pattern. The converter has a dedicated mostly bare, paired 0.51 mm feed/return; the short insulated return ending at U107.2 preserves G02. Pico ground rails are inside its socket rows. GND_ENTRY / GND_LOGIC / VREF_ROOT retain their approved anchors.

The selected wiring keeps the IN fanout insulated: alternatives with bare IN1 wires produced more crossings on shared logic nets. The final ARM/FAULT resistor placement allows both local signals to leave Pico on bare wires. No cross-branch ground shortcut through Pico or a carrier was introduced. Native hard audits stayed zero while varying net order, all 16 IN1 bare subsets and end-channel escapes; search records and earlier layouts are under `search_*.json` and `experiments/`. Duplicate copper and one small +3V3 loop were removed after routing.

**Unchecked hard IDs:** B01, B02, B07, C01, C02, C03, M02, M03, M04, M05, M06, M08, M10, M12, S01, S02, W01, W02, W03, W04, W05, W06, W07. These cover scope evidence, exposed/pad/solder clearance, mounting and access, unsupported header mating-face points, quiet/output separation, current/drop/harness and support evidence. M07/M09 and the declared XH edge points pass; M08 remains UNCHECKED for J104/J213's undeclared feature points. Soft UNCHECKED IDs are B03, B04 and S03. None was hidden or counted as a pass.

Build review still needs connector/USB/BOOTSEL/grip clearance, socket/adapter fit, solder/lead surface gaps, underside wire height and flex, thermal and noise tests, contact/drop measurements and panel/coil harness checks. The AWG26 precrimp coil leads follow approved v0.2 W07 and need the specified heat test. Use >=10 mm underside standoffs and the <=8-hole support plan in `wire_support.csv`. Wire endpoints are solder nodes; lay heavy wires against underside pads/tails rather than forcing multiple leads into one 1 mm hole. Assembly plus inspection is estimated at **6–10 hours**, excluding HDD/panel harnesses; this is an engineering estimate.

Verification used the shared board override on every CLI call:

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 32 errors, 48 warnings; 3158.3 mm wire, 31 jumpers; score 3252107.3
COMPARISON: [true, 0, 0, 31, 220.580952, 78, 3158.323]
hard_failed_rule_ids: []
WIRE LIST: 122 steps
CONTINUITY: 1290 tests (bare board, power off)
```

The three SVGs were opened through offline XML/raster previews and checked for labels, polarity/NC visibility and mirrored bottom coordinates. Final QA and hashes are in `out/render_qc.json` and `out/final_manifest.json`. The continuity CSV is for the wired bare board, with components/modules absent and capacitors discharged. Shared inputs/tools and other candidate folders were not changed.
