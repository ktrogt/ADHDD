**L3 Round 2 / v0.2, 2026-10-22.** Read [summary.md](summary.md) and [constraints.md](constraints.md). Strict short-east-edge F3 cannot meet the hard rules; the exhaustive proof covers rotations and x-stagger. The current complete snapshot has LVS PASS, core DRC 0 and two hard FAIL IDs, P08/P09. A separate portrait packing proposal awaits supervisor direction.

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
