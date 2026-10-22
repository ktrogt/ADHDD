# L4 — F4, round 2 (2026-10-22)

**Comparison-ready candidate:** LVS PASS, core DRC **0**, known hard FAIL **0**. Of 61 hard rules, **38 PASS / 23 UNCHECKED**. The jumper target is **not met: 30 versus 16**. UNCHECKED conditions still need supervisor / assembly review; this is not a fully validated construction release.

## Metrics

| Measure | Final value |
|---|---:|
| Scope | 54 refs; 186 logical pins; 42 nets; 22 logical NC pins |
| Additional reserved physical NC pads | 7, with no host wiring |
| LVS / core DRC / hard FAIL IDs | PASS / 0 / `[]` |
| T7 comparison tuple | `(true, 0, 0, 30, 225.624726, 91, 3054.157)` |
| T7 weighted soft penalty | **225.624726**, partial: B03/B04/S03 have unchecked aspects |
| Legacy `metrics.score` | 3255008.584; includes UNCHECKED errors, so not the ranking score |
| Insulated jumpers / solder bridges | 30 / 0 |
| Bare wire pieces / straight bare segments | 83 / 166 |
| Total wire pieces / tool wirelist steps | **113** |
| Bends | 91 total: 83 bare + 8 jumper |
| Bare / insulated / total projected length | 1836.420 / 1217.737 / **3054.157 mm** |
| Longest IN route | HDD4_IN2, U201.12 → U340.4: **121.920 mm = 48 holes**, limit 60 |
| VREF branches, CH1 / CH2 / CH3 / CH4 | 78.740 / 33.020 / 13.678 / 63.500 mm |
| Star rules G01 / G02 / V01 | PASS / PASS / PASS |
| Board bounding box used | **140.780 × 101.170 mm**; 80.604% of physical 155 × 114 mm board |
| Bounding box from physical NW corner | (6.160, 6.610) to (146.940, 107.780) mm |
| Continuity list | 1310 tests; generated, not physically executed |

`used_area_fraction=1.00347` in the shared metrics uses the **hole-grid area** as denominator. It does not indicate an off-board body; the physical-board fraction is 0.80604. All 54 body envelopes pass the shared real-outline/keep-out DRC.

Wire lengths by **copper diameter**, not insulation diameter:

| Diameter; copper area | Bare mm | Insulated mm | Total mm |
|---|---:|---:|---:|
| 1.00 mm; 0.785 mm² | 424.180 | 0 | 424.180 |
| 0.64 mm; 0.322 mm² | 574.040 | 342.262 | 916.302 |
| 0.50 mm; 0.196 mm² | 838.200 | 875.476 | 1713.676 |

Power shortest paths, using the shared metrics' default roots:

| Channel | J104.2 → VIN14, mm | J101.2 → power GND13, mm |
|---|---:|---:|
| CH1 | 154.940 | 167.640 |
| CH2 | 119.380 | 132.080 |
| CH3 | 83.820 | 96.520 |
| CH4 | 58.420 | 60.960 |

GND2 paths are 2.540 mm shorter. Removing the input return gives GND_ENTRY → GND13 lengths 152.400 / 116.840 / 81.280 / 45.720 mm. The regulator's direct VM feed is about 61.43 mm and its dedicated ground link is 59.24 mm. Panel-switch and HDD harness lengths are excluded.

All four channels have identical local paths: 100 nF → VIN/GND **7.62/7.62 mm**; 470 µF → VIN/GND **12.70/15.24 mm**; OUT1/OUT2 → XH3 **7.62/10.16 mm**. TVS attachments are 12.70 mm each. Converter capacitor attachments are 15.24 mm each; buffer bypass attachments are 10.16 mm each.

## F4 as built

- North long edge: **CH4, CH3, CH2, CH1** left to right; all carriers rotated **270°**. Local bulk capacitor, ceramic capacitor, coil XH3 and CS probe use the same pattern in every channel. XH3 centre pins remain unwired.
- VM runs along **A7–AQ7**; power GND along **D8–AW8**, between carrier socket rows. Main trunks and VIN_RAW/FUSED/PROT wires use 1.00 mm copper; channel VM/GND/OUT branches use 0.64 mm. Each channel has one short insulated ground crossing over VM.
- Pico is horizontal at **BB20, rotation 90°**, USB east. Its GP2–GP9 column faces north toward the IN pins. Channel order follows the fixed GPIO assignments. The short Pico GPIO spacing still requires a broad fan-out to the four carriers.
- DC entry and power-switch header are west; fuse and diode are southwest; regulator is lower centre. VREF source is **AB15**. Stop header is south; SmartNet input and buffer are southeast, below the USB end.
- All host wires, including insulated jumpers, are on the **bottom**. This leaves USB, BOOTSEL, connectors and module tops free of overlying wires.

**Deviation from the suggested buses:** FAULT uses four insulated fan-out wires from the local AF19–AI19 rail. Each first drops into the quiet signal corridor rather than following the coil-connector edge. A preliminary 27-jumper solution put FAULT too close to the coil side; it was rejected during visual review. The final choice uses three more jumpers to preserve that separation. VREF remains a true star, not a shared bus. Long VM/GND links to the regulator are an insulated pair.

## Verification evidence

Actual shared-CLI output, also in [out/verify.log](out/verify.log):

```text
FAIL; LVS PASS; 186/186 pins, 42 nets, 22 NC; 32 errors, 51 warnings; 3054.2 mm wire, 30 jumpers; score 3255008.6
COMPARISON (LVS ok max; remaining fields min): [true, 0, 0, 30, 225.624726, 91, 3054.157]
UNCHECKED hard rules (excluded from comparison failures): B01, B02, B07, C01, C02, C03, M02, M03, M04, M05, M06, M08, M10, M12, S01, S02, W01, W02, W03, W04, W05, W06, W07
WIRE LIST: 113 steps
CONTINUITY: 1310 tests (bare board, power off)
```

`verify` exits **1** because the legacy aggregate treats UNCHECKED hard findings as errors. `ranking_pass=true`, `hard_failed_rule_ids=[]`, and `core_drc_errors=0` are the round-2 acceptance fields. All 32 error findings are explicitly UNCHECKED; none is a measured hard FAIL. Render, wirelist and continuity commands exit 0.

UNCHECKED hard conditions, grouped without omissions:

| IDs | Remaining evidence |
|---|---|
| C01, C02, C03 | Scope provenance; declared/formed-lead junctions; actual pads, solder and surface clearance. Core hole-model LVS/crossing tests do pass. |
| M02, M03, M04, M05, M06, M08, M10, M12 | Mounting hardware; USB/BOOTSEL/grip/mating/probe access and heights; USB direction; J104/J213 lack declared mating-face coordinates. Known XH connector-edge distances pass. |
| S01, S02 | Full spacing including formed leads, insulation and assembly tolerances. Supplementary planar checks below support this placement. |
| W01, W02, W03, W04, W05, W06, W07 | Actual copper, contacts, per-branch current/drop, panel switch and coil harness. |
| B01, B02, B07 | Paired physical routing, off-board output pair, wire supports and underside clearance. |

Candidate-local checks in [out/extra_metrics.json](out/extra_metrics.json) do **not** override those statuses. Conservative sampled projected spacing bounds are **6.578 mm** for S01 (required 5.08) and **13.957 mm** for S02 (required 7.62), including the declared FAULT escape disks and connector body envelopes. Bare-wire surface separation alone is at least **1.540 mm**, excluding pads, leads and solder.

The actual top/bottom/overlay SVG files were opened by the local XML raster preview and their PNGs inspected. All 54 refdes labels appear once per view; the local font-box check finds **no label overlaps**. Coil values were corrected to the approved XH3 substitution. Bottom is mirrored; CSV hole names always remain TOP coordinates. Browser `file:` navigation was unavailable, so no browser-render claim is made.

## Build effort, trade-offs and risks

**Estimate:** 113 wire pieces, 193 physical component/NC-pin solder pads, about **372 distinct solder-pad locations** with supports at no more than six-hole intervals; see [out/solder_plan.csv](out/solder_plan.csv). Soldering every traversed bare-wire land instead gives an upper estimate of **823 pad locations**. Allow roughly **4–7 hours** for forming, assembly and staged continuity work; this is a planning estimate, not a timed build. Printed lengths are projected paths and exclude stripping, termination and height allowance.

Build heavy trunks/local channel wiring first; then quiet ground, bare signals, and underside insulated jumpers. Use [out/wirelist.csv](out/wirelist.csv) by wire ID; its alphabetical step order is not a required assembly order. Run the continuity list **before component population**, with power off. After population, component conduction and the DC-jack kit's internal spare-GND connection change beeper results.

- The 16-jumper target remains unmet. Several hundred deterministic routing-order/placement trials gave marginal later improvements, below 5%; no global optimum is claimed. The final layout prioritises the hard stars, repeatable channel blocks and quiet FAULT escape over a lower unchecked jumper count.
- The dominant soft costs are P07 **128**, P10 **40**, and B06 **43.75**. The conservative bodies force the local caps to the amended limits. P02/P06/P09/P14/P16 have little or no modelled length margin: verify actual lead dress and jumper height.
- Thick trunk junctions need an intentional underside solder/support technique. Do not force a 1.00 mm wire and a component lead together through a 1.00 mm hole. Surface-laid trunk joints and nonconductive supports must be dry-fitted; maintain at least 10 mm underside standoff.
- Dry-fit module grip, XH latches, USB cable, BOOTSEL and the close-tolerance D103/jack/buffer carriers. The tool's provisional-fit and 3D-access conditions remain open.
- Use approved AWG26 pre-crimped coil leads only within the approved current envelope; pair the two coil wires and measure lead/contact temperature and loop drop. Panel-switch contacts/harness and all thermal/noise/stop bench checks remain build-time requirements.

## Reproduction and assumptions

Shared files were read only. Local copies of board, footprints, netlist and v0.2 rules match the approved inputs; hashes and exact shared-CLI commands are in [input_manifest.json](input_manifest.json). `placement.json` and `routing_config.json` are the final inputs. Run `route_local.py` to regenerate wiring, then `run_checks.py` for verify/render/wirelist/continuity, `raster_svg.py out/top.svg out/bottom.svg out/overlay.svg` for offline previews, and `quality_local.py` for supplemental metrics. Use the Python executable specified in BRIEF, with `-X utf8`.

`build.py seed`, search scripts, `review/`, and `experiments/` are development material, not alternative approved construction files. No shared tool bug blocked this candidate. No rule relaxation or supervisor decision is requested; the documented UNCHECKED items follow the supplied round-2 review policy.
