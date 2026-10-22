**T6 limitations encountered by L2, 2026-10-22.** No shared tool was edited.

The approved full-rule adapter `tools/t7_rules.py` deliberately returns UNCHECKED for 25 hard rules and three soft rules used here. This is a documented capability gap, not a newly discovered geometry-extraction bug. Consequently, an exit-0 full hard audit is unavailable even if every supported placement/path check is made to pass.

Reproduce using the required Python executable:

```powershell
python -X utf8 ユニバーサル基板/tools/ub.py verify --project ユニバーサル基板/candidates/L2
```

Hard UNCHECKED: C01, C02, C03, M02, M03, M04, M05, M06, M07, M08, M09, M10, M12, S01, S02, W01, W02, W03, W04, W05, W06, W07, B01, B02, B07. Soft UNCHECKED: S03, B03, B04. C01 is always UNCHECKED in the adapter even though this candidate's scoped CSV is byte-identical to the approved `netlist_ub.csv` and its core LVS passes.

Candidate-only workarounds provide **evidence without overriding that status**: `audit_local.py` checks nominal quiet-net surface separation, conductor areas by declared branch class, probe centre clearances, feature-to-real-board distances and input hashes. `out/support.csv` records a support plan. These do not certify contacts, solder blobs, off-board harnesses, thermal behaviour, mechanical grip, physical fit, 3D wire layering or bench tests.

The full T7 file contains per-rule soft weights but no top-level scalar score weights. `metrics.score` therefore uses the tool defaults. `out/audit_local.json` separately sums implemented atomic `t7_penalty` values by priority and excludes UNCHECKED findings from that known subtotal. It is not a complete T7 ranking.

The shared renderer shows the grid-window boundary, not the actual 155 × 114 mm outline. `annotate_svgs.py` adds the nominal physical outline, M3 holes and USB direction locally, shifts the legend to avoid the added outline and checks all 54 refdes labels per view. A browser file-URL attempt was rejected by browser security policy; `preview_svg.py` instead rasterizes the simple SVG vocabulary offline using preinstalled Pillow and Arial, with no browser or network access. Those PNGs were visually inspected. Main SVG geometry/text remains authoritative; the previews do not prove a browser's font/opacity rendering or print calibration.

The independent hard-rule contradictions are reproduced by `prove_infeasible.py`; they persist without any routing/tool limitation and therefore also require supervisor decisions. The task's authority boundary prohibits L2 from changing those shared rules or approved footprints.
