**L3 / F3 — comparison candidate, 2026-10-22.** LVS passes, but the unchanged hard-rule audit fails. This candidate is **ineligible for build approval** until the owner resolves the footprint/rule conflicts and the unsupported checks in [constraints.md](constraints.md). No rule is waived in the saved report.

| Metric | Final result |
|---|---|
| LVS | PASS: 186/186 pins, 42 nets, 22 NC; seven reserved physical pads unwired |
| Hard audit, 61 rules | 25 PASS / 11 FAIL / 25 UNCHECKED; plus two base BODY_OFFBOARD findings |
| Soft audit, 18 rules | 7 PASS / 8 FAIL / 3 UNCHECKED |
| T7 emitted weighted soft penalty | 157.600 known + 13 UNCHECKED bookkeeping |
| Unmodified tool scalar score | 6,056,485.792 |
| Insulated jumpers / bare pieces / bridges | 35 / 80 / 0; all on BOTTOM |
| Length | 3405.39 mm total; bare 1686.56, insulated 1718.83 |
| Length by gauge, mm | 1.0mm: 462.28; AWG20: 30.59; AWG22: 325.26; AWG24: 608.43; AWG26: 1978.84 |
| Bends | 67 bare; 4 insulated |
| Longest IN route | HDD4_IN1: 98.93 mm, below 152.40 mm hard limit |
| VREF branches, CH1→4, mm | 73.66, 45.72, 48.26, 54.36; strict star PASS |
| VM C106→VIN, CH1→4, mm | 132.19, 104.25, 76.31, 48.37 |
| GND C106→GND13, CH1→4, mm | 116.84, 88.90, 60.96, 68.58; both GND star checks PASS |
| Used bounding box | 137.38 × 102.20 mm; nominal physical-board margins L/R 8.92/8.70, N/S 5.90/5.90 mm |
| Build effort | 115 wire pieces; 307 main-board solder/anchor sites in the practical schedule; 764 if every conservative bare-contact pad is soldered |

T6 does not calculate a scalar using T7 per-rule weights. The table reports its unchanged scalar and, separately, the sum of the tool-emitted T7 penalties. Neither UNCHECKED nor a small soft score means acceptance. Detailed measurements are in [extended_metrics.json](out/extended_metrics.json).

The built floor plan keeps unrotated carriers in an east-side column, north→south **HDD4, HDD3, HDD2, HDD1**. VM/GND use 1.0 mm bare trunks beneath the removable modules, with AWG22 channel wiring. The identical right-hand 100 nF and XH3 pattern is retained on all four channels. Three 470 uF cans occupy the east inter-channel gaps; the north can is the west-side exception. Entry is north-central, converter NW, Pico SW with USB south, SmartNet south and STOP west near GP14–16. The divider is central. Three VREF spokes are bare and one insulated, with no shared branch copper beyond the root.

The important F3 deviations are the west-side north bulk capacitor, slightly inward coil connectors and north-central entry. They avoid overlap/heat conflicts. Bulk returns still need 9 holes on CH1–3 and 11 on CH4, exceeding P08/P09. OUT1 needs 5 holes, exceeding P11/P12=4. The outer carrier bodies exceed T6's virtual outline by 0.30 mm each; the nominal physical outline accommodates them. The pair proofs also show impossible original limits for TVS, converter capacitors, receiver bypass and lower-divider placement. [constraints.md](constraints.md) lists the necessary review decisions.

Nominal copper-wire surface gap is at least 1.54 mm. The supplementary S01/S02 sampling estimates exceed their limits under the stated wire/pad diameters. Copper-only 20 °C drop estimates at an intentionally conservative 2.6 A on each full route are 0.0197 V positive and 0.0078 V return; contacts, components and external harness are excluded. These calculations do not close the official UNCHECKED rules. Actual edge-feature insets, module grip, one-hole star terminations, 1.0 mm wire fit, solder fillets, thermal/noise performance and switch/connector ratings require review or measurements.

Assumptions: fixed 4.7 kohm initial VREF divider; all substitutions are exactly those in the approved footprints; no scaffold; no added electrical parts. Bare pieces are continuous wire. The practical solder plan fixes every component contact, wire end, bend and junction, with supports at most 8 holes apart and at least 10 mm bottom standoff. Its secondary terminal LVS passes when unsoldered intermediate pads are ignored. Allow roughly **4–7 hours** for wire preparation, main-board soldering and continuity inspection by a student experienced with soldering; module/adapter preparation and powered bring-up are additional. This is an estimate, not observed build time.

Exact verification output:

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 60 errors, 52 warnings; 3405.4 mm wire, 35 jumpers; score 6056485.8
```

`ub.py render`, `wirelist` and `continuity` succeeded; the latter has 1,102 checks. [top.svg](out/top.svg), [bottom.svg](out/bottom.svg) and [overlay.svg](out/overlay.svg) were inspected through offline raster previews. The value-key/legend overlap was fixed by an 8 mm key shift; HDD channel names were added and substitution values corrected. Bottom is mirrored; every CSV uses TOP hole names. SVG scale remains 1:1, with its 20 mm calibration bar. Browser file-URL access was denied; no browser bypass or upload was used.

All requested artifacts are in `out/`, alongside the pin map, declared junctions, practical solder schedule, logs and supplemental evidence. Approved input hashes still match. See [README.md](README.md) for reproduction and [infeasibility.json](infeasibility.json) for the finite geometric proofs.
