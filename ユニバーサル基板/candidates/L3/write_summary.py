"""Write the concise final handoff from actual saved reports."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'out/report.json').read_text(encoding='utf-8'))
m=r['metrics'];e=json.loads((HERE/'out/extended_metrics.json').read_text(encoding='utf-8'))
s=json.loads((HERE/'out/solder_plan_validation.json').read_text(encoding='utf-8'))
hard=e['official_hard_rules'];soft=e['official_soft_rules']
vref=', '.join(f"{x['length_mm']:.2f}" for x in e['vref_branches'])
vm=', '.join(f"{x['vm_from_C106_mm']:.2f}" for x in e['power_paths'])
gg=', '.join(f"{x['gnd13_from_C106_mm']:.2f}" for x in e['power_paths'])
gauges='; '.join(f'{g}: {L:.2f}' for g,L in e['wire_length_by_gauge_mm'].items())
headline=(HERE/'out/verify.log').read_text(encoding='utf-8').splitlines()[0]
text=f'''**L3 / F3 — comparison candidate, 2026-10-22.** LVS passes, but the unchanged hard-rule audit fails. This candidate is **ineligible for build approval** until the owner resolves the footprint/rule conflicts and the unsupported checks in [constraints.md](constraints.md). No rule is waived in the saved report.

| Metric | Final result |
|---|---|
| LVS | PASS: 186/186 pins, 42 nets, 22 NC; seven reserved physical pads unwired |
| Hard audit, 61 rules | {hard.get('PASS',0)} PASS / {hard.get('FAIL',0)} FAIL / {hard.get('UNCHECKED',0)} UNCHECKED; plus two base BODY_OFFBOARD findings |
| Soft audit, 18 rules | {soft.get('PASS',0)} PASS / {soft.get('FAIL',0)} FAIL / {soft.get('UNCHECKED',0)} UNCHECKED |
| T7 emitted weighted soft penalty | {e['t7_known_weighted_soft_penalty']:.3f} known + {e['t7_unchecked_soft_bookkeeping_penalty']:.0f} UNCHECKED bookkeeping |
| Unmodified tool scalar score | {m['score']:,.3f} |
| Insulated jumpers / bare pieces / bridges | {e['wire_count']['jumper']} / {e['wire_count']['bare']} / 0; all on BOTTOM |
| Length | {m['total_wire_mm']:.2f} mm total; bare {m['wire_length_mm']['bare']:.2f}, insulated {m['wire_length_mm']['jumper']:.2f} |
| Length by gauge, mm | {gauges} |
| Bends | {e['bare_bends']} bare; {e['jumper_bends']} insulated |
| Longest IN route | {e['longest_IN']['net']}: {e['longest_IN']['length_mm']:.2f} mm, below 152.40 mm hard limit |
| VREF branches, CH1→4, mm | {vref}; strict star PASS |
| VM C106→VIN, CH1→4, mm | {vm} |
| GND C106→GND13, CH1→4, mm | {gg}; both GND star checks PASS |
| Used bounding box | {e['bbox_dimensions_mm'][0]:.2f} × {e['bbox_dimensions_mm'][1]:.2f} mm; nominal physical-board margins L/R 8.92/8.70, N/S 5.90/5.90 mm |
| Build effort | {m['conductors']} wire pieces; {s['recommended_joint_sites']} main-board solder/anchor sites in the practical schedule; {e['solder_sites_conservative_all_bare_pads']} if every conservative bare-contact pad is soldered |

T6 does not calculate a scalar using T7 per-rule weights. The table reports its unchanged scalar and, separately, the sum of the tool-emitted T7 penalties. Neither UNCHECKED nor a small soft score means acceptance. Detailed measurements are in [extended_metrics.json](out/extended_metrics.json).

The built floor plan keeps unrotated carriers in an east-side column, north→south **HDD4, HDD3, HDD2, HDD1**. VM/GND use 1.0 mm bare trunks beneath the removable modules, with AWG22 channel wiring. The identical right-hand 100 nF and XH3 pattern is retained on all four channels. Three 470 uF cans occupy the east inter-channel gaps; the north can is the west-side exception. Entry is north-central, converter NW, Pico SW with USB south, SmartNet south and STOP west near GP14–16. The divider is central. Three VREF spokes are bare and one insulated, with no shared branch copper beyond the root.

The important F3 deviations are the west-side north bulk capacitor, slightly inward coil connectors and north-central entry. They avoid overlap/heat conflicts. Bulk returns still need 9 holes on CH1–3 and 11 on CH4, exceeding P08/P09. OUT1 needs 5 holes, exceeding P11/P12=4. The outer carrier bodies exceed T6's virtual outline by 0.30 mm each; the nominal physical outline accommodates them. The pair proofs also show impossible original limits for TVS, converter capacitors, receiver bypass and lower-divider placement. [constraints.md](constraints.md) lists the necessary review decisions.

Nominal copper-wire surface gap is at least {e['copper_wire_surface_clearance_mm']:.2f} mm. The supplementary S01/S02 sampling estimates exceed their limits under the stated wire/pad diameters. Copper-only 20 °C drop estimates at an intentionally conservative 2.6 A on each full route are {e['copper_only_20C_drop_V']['positive_at_2p6A_max']:.4f} V positive and {e['copper_only_20C_drop_V']['return_at_2p6A_max']:.4f} V return; contacts, components and external harness are excluded. These calculations do not close the official UNCHECKED rules. Actual edge-feature insets, module grip, one-hole star terminations, 1.0 mm wire fit, solder fillets, thermal/noise performance and switch/connector ratings require review or measurements.

Assumptions: fixed 4.7 kohm initial VREF divider; all substitutions are exactly those in the approved footprints; no scaffold; no added electrical parts. Bare pieces are continuous wire. The practical solder plan fixes every component contact, wire end, bend and junction, with supports at most 8 holes apart and at least 10 mm bottom standoff. Its secondary terminal LVS passes when unsoldered intermediate pads are ignored. Allow roughly **4–7 hours** for wire preparation, main-board soldering and continuity inspection by a student experienced with soldering; module/adapter preparation and powered bring-up are additional. This is an estimate, not observed build time.

Exact verification output:

```text
{headline}
```

`ub.py render`, `wirelist` and `continuity` succeeded; the latter has 1,102 checks. [top.svg](out/top.svg), [bottom.svg](out/bottom.svg) and [overlay.svg](out/overlay.svg) were inspected through offline raster previews. The value-key/legend overlap was fixed by an 8 mm key shift; HDD channel names were added and substitution values corrected. Bottom is mirrored; every CSV uses TOP hole names. SVG scale remains 1:1, with its 20 mm calibration bar. Browser file-URL access was denied; no browser bypass or upload was used.

All requested artifacts are in `out/`, alongside the pin map, declared junctions, practical solder schedule, logs and supplemental evidence. Approved input hashes still match. See [README.md](README.md) for reproduction and [infeasibility.json](infeasibility.json) for the finite geometric proofs.
'''
(HERE/'summary.md').write_text(text,encoding='utf-8')
print('summary.md written')
