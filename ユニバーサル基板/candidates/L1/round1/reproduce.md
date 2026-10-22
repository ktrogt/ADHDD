# Reproducing L1

Run from the repository root with the Python interpreter specified in BRIEF. Every command below writes only inside L1. The first command resets L1's generated placement/wiring, so preserve any subsequent local edits first.

```powershell
$l1Python = 'C:/Users/ktrog/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/build.py seed
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/build.py values
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/route_l1.py 38
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/finish.py
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/raster_svg.py
& $l1Python -X utf8 ユニバーサル基板/candidates/L1/prove_constraints.py
```

Open and inspect all three PNG/SVG views before running `report_l1.py`, which records that visual inspection and writes the handoff/support plan. The original final candidate was inspected on 2026-10-22.

The shared CLI is invoked by `finish.py` in this order: verify → render → wirelist → continuity. Its verify exit code **1 is expected**, because the canonical hard audit fails. No rules are disabled. `finish.py` changes generated SVG text positions after rendering; rerendering with the bare shared CLI will restore its original overlapping labels until this local postprocessor is rerun.

`routing_search.json` records the final 100-order search; seed 38 was selected by known hard findings, then jumpers, bare-bend/length cost and piece count. `wiring.before_polish.json` is the seed result before redundant exposed copper was removed. `wiring.v1.json` is an obsolete experiment for an older placement and must not be used with the final placement.

The raw tool score uses default CLI weights. T7 weighted soft atomics, unresolved rule counts, gauge lengths, signal/power distances and fit assumptions are in `out/metrics_extra.json`. The authoritative connectivity pair is always **placement.json + wiring.json**, and its canonical audit is **out/report.json**.
