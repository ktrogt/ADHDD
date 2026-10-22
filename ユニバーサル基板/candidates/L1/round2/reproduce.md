# L1 round 2 — reproduction and review

The authoritative pair is `placement.json` + `wiring.json`. Use `out/report.json` and the native `out/metrics.json` comparison tuple. Round 1 is preserved in `round1/`; layouts in `experiments/` are historical trials, not construction instructions.

Run from the repository root. The rebuild command replaces generated **L1-only** files, so preserve any subsequent manual edits first. Pillow is used for offline preview PNGs; the shared CLI itself uses the standard library.

```powershell
$l1Python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/rebuild.py
# Inspect all three generated PNG/SVG views before confirming visual QA:
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/report2.py --qa-confirmed
```

`selection.json` records the deterministic routing parameters. `layout2.py` seeds the placement; `route2.py` uses the shared A* with separate GND/VREF routing groups and local prewires. `finish2.py` removes redundant exposed copper and loops, then invokes the shared CLI in verify → render → wirelist → continuity order. Every invocation passes **`--board ユニバーサル基板/board.json`**. `polish_svg.py` changes only generated text positions; it must run on freshly rendered SVGs. `raster_svg.py` opens the actual SVG XML and creates local previews without browser/network access.

For an independent audit:

```powershell
& $l1Python -X utf8 ユニバーサル基板/tools/ub.py verify --project ユニバーサル基板/candidates/L1 --board ユニバーサル基板/board.json
```

The legacy CLI exit code is **1** because UNCHECKED findings remain. Acceptance for this round is `ranking_pass: true`, LVS PASS, core DRC 0 and `hard_failed_rule_ids: []`; the comparison tuple reports those explicitly. Re-running render alone restores the shared renderer's original captions, so reapply text polishing and repeat visual QA afterward.

`out/wire_support.csv` lists endpoint/bend/<=8-hole anchors. `out/pinmap.csv` gives all 186 pin holes, including NC. The continuity CSV is for the unpowered wired bare board before components/modules are fitted. Mechanical access, actual solder clearances, contact ratings/drop and thermal/noise performance remain the listed UNCHECKED/build checks.
