**L3 / F3, 2026-10-22.** Start with [summary.md](summary.md). The current candidate is only `placement.json`, `wiring.json` and `out/`. It has exact LVS but is **not eligible under the unchanged hard rules**. The contradictory bounds and unsupported checks are detailed in [constraints.md](constraints.md).

All approved input copies are byte-for-byte copies. Their SHA-256 values are in `input_hashes.json`. Shared files and other candidates are not modified. `wiring.seed.json`, `wiring.best.json`, the search scripts and `variants/` are intermediate/reproduction material, not alternative approved build files.

Run from the repository root with:

```powershell
$l3python = 'C:/Users/ktrog/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $l3python -X utf8 ユニバーサル基板/candidates/L3/run_verification.py
& $l3python -X utf8 ユニバーサル基板/candidates/L3/annotate_svgs.py
& $l3python -X utf8 ユニバーサル基板/candidates/L3/raster_preview.py
& $l3python -X utf8 ユニバーサル基板/candidates/L3/audit_extra.py
& $l3python -X utf8 ユニバーサル基板/candidates/L3/solder_plan.py
& $l3python -X utf8 ユニバーサル基板/candidates/L3/reproduce_limits.py
& $l3python -X utf8 ユニバーサル基板/candidates/L3/write_summary.py
& $l3python -X utf8 ユニバーサル基板/candidates/L3/check_package.py
```

The first command invokes the exact shared `ub.py verify`, `render`, `wirelist` and `continuity` commands and records their exit codes/logs. Verify exit 1 is expected and must not be represented as success. `annotate_svgs.py` adds HDD channel names and an audit caption, then moves the part-value key down 8 mm to clear the long net legend; it preserves hole/wire geometry and 1:1 scale. PNGs are offline visual-QA previews of the SVG primitives. Browser file-URL access was denied, so no browser workaround or file upload was used.

To regenerate/search the placement, the ordered workflow is `build.py`, `search_routes.py --count 100`, then `finalize.py`, followed by the commands above. This overwrites only L3 working outputs. `finalize.py` is the cleanup step for a newly generated search result, not a command to run twice on the already-cleaned final file. The recorded final routing search is 200 trials over two VREF policies, with seed 73 / policy 1 selected lexicographically by known hard findings, jumpers, bare bends, length, pieces and known T7 soft penalty.

For assembly review, use the mirrored `out/bottom.svg` alongside `out/wirelist.csv`. Every hole name in every CSV remains TOP coordinates. `out/assembly_pin_map.csv` includes all 186 logical pins and seven reserved physical pads. `out/assembly_solder_sites.csv` and `out/wire_supports.csv` provide the smaller continuous-wire anchor schedule; the official wirelist retains the conservative all-contact pad list. `out/continuity.csv` is for an unpowered, discharged board before semiconductor/module insertion, as documented by T6.

The approved netlist numbers are logical identifiers. The extra pin map has separate physical numbers: J101 CENTER/SLEEVE/SWITCH are kit pads 4/1/3 (pad 2 reserved), D103 K/A are TO-220 pins 2/1 (pin 3 reserved), buffer logical VCC 5 is DIP pad 6 (pad 5 reserved), and each coil's logical OUT2 2 is XH physical pin 3 (centre pin 2 reserved). The square on the drawing denotes logical pin 1 or polarity, not necessarily the printed adapter number.
