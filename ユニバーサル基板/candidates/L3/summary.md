L3 closed by Claude (2026-10-22): short-edge F3 infeasible (P08/P09 proof); long-edge variant duplicates F1/F4

**L3 Round 2 / v0.2, 2026-10-22 — strict F3 is infeasible.** Hard FAIL 0 cannot be reached with four channels at the short east edge. The exhaustive necessary-condition proof covers all carrier rotations and horizontal staggering. See [constraints.md](constraints.md). Per the supervisor's instruction, work stops at this proof and the best complete comparison snapshot; this is not an eligible build layout.

| Metric | Current v0.2 snapshot |
|---|---|
| Native comparison tuple | `(true, 0, 2, 38, 220.862152, 62, 3385.17)` |
| Tuple order | LVS, core DRC, hard FAIL IDs, jumpers, soft penalty, bends, length mm |
| LVS / core DRC | PASS: 186/186 pins, 42 nets, 22 NC / 0 errors |
| Hard FAIL list | **P08, P09**; 36 hard rules PASS, 23 UNCHECKED |
| Weighted soft penalty / legacy scalar | 220.862152 / 4256515.833 |
| Jumpers / bare pieces / bridges | 38 / 77 / 0, all BOTTOM |
| Wire pieces / length | 115 / 3385.17 mm |
| Length by gauge, mm | 1.0mm: 368.30; AWG24: 600.81; AWG20: 70.10; AWG26: 2023.38; AWG22: 322.58 |
| Bends | 62: 58 bare, 4 insulated |
| Longest IN | HDD4_IN1, 100.84 mm; hard limit 152.40 |
| VREF CH1→4, mm | 76.20, 48.26, 50.80, 55.94; V01 PASS |
| VM C106→VIN CH1→4, mm | 134.72, 106.78, 78.84, 50.90 |
| GND C106→GND13 CH1→4, mm | 119.38, 91.44, 63.50, 71.12; G01/G02 PASS |
| Used box | 139.92 × 103.39 mm, inside real 155 × 114 outline |
| Build effort | 294 solder/anchor sites, 115 continuous wire pieces; estimated 4–7 h plus module preparation/bench testing |

The built floor plan retains the east column, all carriers 0°, HDD4→HDD1 north to south. Pico is 180°, USB south, with its GP2–GP9 column eastward facing the drivers. VM/GND are 1.0 mm bare trunks under the carriers; channel branches/OUT wires use AWG22, quiet returns AWG24, logic AWG26. Three VREF spokes are bare, one insulated. Thirteen probes remain; scaffold GPIOs are unwired.

Compared with round 1, the strip moved one hole east so coil mating features pass M08 at 2 holes. Six-hole regulator-capacitor returns fix P14. The real-outline verifier gives core DRC 0 with no workaround. North C341 moved up one row. P08/P09 remain: CH1–3 bulk returns are 9 holes; north C341 has 9/10-hole distances. These are not waived. The 16-jumper target is not met; optimisation stops because the required packing is impossible.

The proof removes all other circuitry/routing. At 0°, east-compatible tiles allow origin columns 43–46 and rows 4–33 (0-based): 29 rows available versus 33 required by H01. At 270°, only column 48 and rows 11–36 work: 25 versus 30. At 90°/180° no isolated complete tile reaches E. At 0° the entire x-stagger range is narrower than the carrier body, so the same y-spacing bound still applies.

The smallest proposed scope change is to turn the same board 90° and use its long edge vertically. [portrait_geometry_only.json](proposals/portrait_geometry_only.json) has four feasible channel tiles under unchanged electrical bounds. It is not a routed substitute: in canonical coordinates it becomes a long-edge row and changes the assigned seed. A larger board is the alternative if the short-edge column must be kept.

UNCHECKED hard IDs for Claude's visual/build review: **B01, B02, B07, C01, C02, C03, M02, M03, M04, M05, M06, M08, M10, M12, S01, S02, W01–W07**. They concern power/harness/drop details, wire/pad/solder surfaces, hardware/access, scope provenance and assembly. M08's unknown portion is only the two headers with no mating point; known XH checks pass. Soft unknowns are **B03, B04, S03**; unknown portions add zero to native penalty. Full reasons remain in report.json.

Blue patches show clear nominal 5.08 mm finger areas: N/S per carrier, W/E at the Pico midpoint. Other bodies do not occupy them, and all wiring is below. Physical removal and 25 mm vertical finger clearance remain fit checks. Star-junction construction, 1 mm wire/hole fit, wire heights, strain relief, solder fillets, temperatures/noise and all bench checks are unmeasured. Initial VREF remains 4.7 kohm. The secondary 294-site solder plan preserves pin LVS with <=8-hole support gaps and >=10 mm bottom standoff.

Exact verify output:

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 42 errors, 52 warnings; 3385.2 mm wire, 38 jumpers; score 4256515.8
COMPARISON (LVS ok max; remaining fields min): [true, 0, 2, 38, 220.862152, 62, 3385.17]
```

Render, wirelist and continuity succeeded (1,023 continuity checks). Final TOP, mirrored BOTTOM and OVERLAY SVGs were opened through offline raster previews and inspected; labels/value key are readable. The real outline, mounting holes, channel names and grip areas are shown. Scale remains 1:1 with the 20 mm ruler; all CSV hole names are TOP coordinates. Round 1 is under [round1/](round1/); approved input hashes/copies match. No shared file or rule was edited.
