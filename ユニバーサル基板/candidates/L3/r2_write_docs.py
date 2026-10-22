"""Write the Round-2 decision evidence and current reproduction instructions."""
from pathlib import Path
H=Path(__file__).resolve().parent
(H/'constraints.md').write_text('''**Round 2 / v0.2: short-east-edge F3 is geometrically infeasible (2026-10-22).** This proof uses the amended rules and updated real outline. It does not reuse the obsolete round-1 boundary argument. The complete comparison snapshot has LVS PASS, core DRC 0 and only P08/P09 as known hard FAIL IDs. It is not an eligible build layout.

`r2_geometry.py` enumerates the 470 uF, 100 nF and XH3 relative locations around a carrier, allowing all relative rotations. It applies M01, H06, P05=3, P08=6, P11=5, pin collisions and the reserved connector centre pad. There are 25 independent bulk placements, 10 bypass placements, 13 connector placements and 234 mutually compatible complete patterns. The +/-12-hole search box contains every origin allowed by these pin-distance bounds; each part's pin 1 is its origin.

Every pattern is placed at every usable carrier origin in the 55 x 40 grid, in all four carrier rotations. The physical outline with 1 mm body margin, pin validity, explicit corner keep-outs and exact grid-boundary mating point are checked. Other circuitry, probe pins, wires, grip and noise conditions are omitted. This is an easier problem than the full board, so failure is a necessary-condition proof independent of routing.

`r2_east_proof.py` then requires every coil mating face to be within 2 holes of E, as assigned by F3. It allows horizontal staggering wherever any complete tile is feasible.

| Carrier rotation | Feasible origin columns (0-based) | Feasible origin rows | Available row span | H01-required span for four |
|---|---|---|---:|---:|
| 0 deg | 43-46 | 4-33 | 29 | 33 |
| 90 deg | No complete east-edge tile | - | - | - |
| 180 deg | No complete east-edge tile | - | - | - |
| 270 deg | 48 only | 11-36 | 25 | 30 |

At 0 degrees, the possible horizontal stagger is only 3 holes = 7.62 mm, less than the carrier width 15.84 mm. Every carrier x-envelope therefore overlaps every other one. H01 requires the separation in y: ceil((18.38+7.62)/2.54)=11 holes between origins, hence 33 for four origins, exceeding 29. At 270 degrees, the sole feasible column gives ceil((15.84+7.62)/2.54)=10-hole pitch, hence 30, exceeding 25. M11 forbids mixing rotations. Neither carrier rotation nor a small x-stagger fixes F3.

The more permissive common-x test allowing coil exits on any edge also fails: maximum origin row spans are 29/27/29/27 for rotations 0/90/180/270, versus required 33/30/33/30. Reducing H01 alone to 7.02 mm was tested and still did not produce four complete tiles. No relaxation is applied to the current candidate.

Machine evidence: [east-edge certificate](out/r2_east_edge_certificate.json), [common-column certificate](out/r2_infeasibility_certificate.json), and [complete origin census](out/r2_column_feasibility.json). The certificates record input hashes. Reproduce with r2_geometry.py, r2_proposal.py, then r2_east_proof.py. Shared files are never edited.

**Proposed minimum scope change:** turn the same physical 104708 board 90 degrees and use the 55-hole long edge vertically. This changes no part or electrical bound. A four-channel geometry solution exists in the 40 x 55 portrait frame: origins (28,4), (28,15), (28,26), (28,37), all 0 degrees. [portrait_geometry_only.json](proposals/portrait_geometry_only.json) includes all local parts and cross-channel checks. This is a packing proposal, not a complete routed 54-part alternative.

Transforming it back to the approved canonical 55 x 40 coordinates gives a row along an original long edge. That changes the assigned short-east-edge seed, so it is not silently substituted. If the short-edge column must be retained, a larger board is needed: the 0-degree case alone needs at least 44 rows (first origin >=4, 33 rows between four origins, plus 6-row pin span). A real larger board would also need outline/hardware validation; none is selected or purchased.

**Current snapshot:** the channel strip moved one hole east, making the coil features pass M08 at exactly 2 holes. Direct 6-hole regulator-capacitor returns fix P14. The real-outline verifier gives core DRC 0 without a router workaround. North C341 moved up one row, reducing its distances to 9/10 holes. Other bulk positive legs are at 6 holes but returns remain 9. P08/P09 are still failed, not waived.

For M05 review, blue patches show two nominal 5.08 x 5.08 mm finger areas per module: N/S of each carrier and W/E at the Pico midpoint. No other body occupies those patches; all wires are below. Physical extraction, 25 mm vertical finger clearance, latch access, 1 mm wire/hole fit, star-junction construction, jumper heights, solder geometry, temperatures/noise and bench checks remain unmeasured.
''',encoding='utf-8')
(H/'README.md').write_text('''**L3 Round 2 / v0.2, 2026-10-22.** Read [summary.md](summary.md) and [constraints.md](constraints.md). Strict short-east-edge F3 cannot meet the hard rules; the exhaustive proof covers rotations and x-stagger. The current complete snapshot has LVS PASS, core DRC 0 and two hard FAIL IDs, P08/P09. A separate portrait packing proposal awaits supervisor direction.

Current files are placement.json, wiring.json, design_rules.json and out/. The rules copy is byte-identical to shared design_rules_v0.2.json. Round 1 is retained under round1/. Retired mixed outputs are under r2_work/. Old helper scripts are history/internal dependencies, not current entry points.

From the repository root, use the Python executable specified in BRIEF, with -X utf8, and run these L3 scripts in order:

1. r2_outputs.py — exact shared verify/render/wirelist/continuity, always with --board ユニバーサル基板/board.json and --rules ユニバーサル基板/design_rules_v0.2.json.
2. r2_extra.py and solder_plan.py — measurements, physical pin map, clear nominal grip patches and the continuous-wire solder/support schedule.
3. r2_svg_labels.py and raster_preview.py — channel names, audit caption, grip patches and offline SVG previews.
4. r2_handoff.py — summary and final-file consistency record.

Verify exit 1 and hard FAIL 2 are intentional blocker evidence. UNCHECKED checks are excluded from comparison failures per Claude's round-2 policy, and listed in the summary. To rebuild the snapshot first run r2_build.py then r2_route.py --count 50. The selected route policy/seed is 1/14 among 100 trials. Hand-designed GND/VREF stars are preserved; the updated standard router uses no geometry-gate monkeypatch.

For the packing proof, run r2_geometry.py, r2_proposal.py, r2_east_proof.py. The portrait proposal is geometry-only and never overrides the approved board used to verify the current snapshot. In canonical coordinates it uses a long edge and changes the seed.

All CSV hole names are TOP coordinates. bottom.svg is mirrored. assembly_pin_map.csv separates logical/physical pins for the jack kit, MBR3045FCT, DIP6 buffer and outer-pin XH3. assembly_solder_sites.csv and wire_supports.csv provide a smaller continuous-wire anchor schedule with secondary terminal LVS; the official wirelist remains conservative. Continuity tests apply to an unpowered, discharged bare board before inserting semiconductor modules.

SVGs use the real outline and mounting holes. Added labels and blue grip patches preserve scale/geometry. The exact SVG files are opened and rasterised locally with Pillow for inspection; the earlier browser file-URL denial is not bypassed. Print at actual size and measure the 20 mm calibration bar. No physical build or powered test is claimed.
''',encoding='utf-8')
print('Round-2 decision documents written')
