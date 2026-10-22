# L1 round 3 - reproduction and review

The authoritative pair is `placement.json` + `wiring.json`. Use `out/report.json` and the native `out/metrics.json` comparison tuple. Previous states are preserved in `round2/` and `round1/`; experimental files are not construction instructions.

Run from the repository root. The rebuild command replaces generated **L1-only** files, so preserve any subsequent manual edits first. Pillow is used for offline preview PNGs; the shared CLI itself uses the standard library.

```powershell
$l1Python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/rebuild.py
# Inspect all three generated PNG/SVG views before confirming visual QA:
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/report3.py --qa-confirmed
```

`selection.json` records the frozen selected inputs and their hashes. `rebuild.py` checks those hashes and runs `finish3.py` on `placement.r3.json` / `wiring.r3.json`. The latter consolidates bare pieces and removes unused copper/loops, then invokes the shared CLI in verify, render, wirelist, continuity order. Every invocation passes **`--board ユニバーサル基板/board.json`**. `polish_svg.py` changes only generated text positions; it must run on freshly rendered SVGs. `raster_svg.py` opens the actual SVG XML and creates offline previews. `report3.py` freshly verifies the pair, checks round-2 archive hashes and writes the support/pin/rule CSVs, summary and manifest.

The expected tuple is `(true, 0, 0, 31, 218.580952, 57, 3077.043)`. The experiment index is `out/round3_experiments.json`. `ripup3_late.py` and `atomic3.py` produced the selected local bare-wire changes; the `route3_*` / `search3_*` helpers record rejected layout variants. The frozen selected inputs permit deterministic rebuilding without repeating those searches.

For an independent audit:

```powershell
& $l1Python -X utf8 ユニバーサル基板/tools/ub.py verify --project ユニバーサル基板/candidates/L1 --board ユニバーサル基板/board.json
```

The legacy CLI exit code is **1** because UNCHECKED findings remain. Acceptance for this round is `ranking_pass: true`, LVS PASS, core DRC 0 and `hard_failed_rule_ids: []`; the comparison tuple reports those explicitly. Re-running render alone restores the shared renderer's original captions, so reapply text polishing and repeat visual QA afterward.

`out/wire_support.csv` lists endpoint/bend/<=8-hole anchors. `out/pinmap.csv` gives all 186 pin holes, including NC. The continuity CSV is for the unpowered wired bare board before components/modules are fitted. Mechanical access, actual solder clearances, contact ratings/drop and thermal/noise performance remain the listed UNCHECKED/build checks.
