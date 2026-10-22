# Task L5 (owner: you, gpt-6-astra, max) — Final optimisation and quality pass of the ADHDD perfboard layout

You take over the best layout produced so far by other agents and turn it into the build-ready layout: more compact, fewer wires/jumpers, and checked for quality. Write only inside `ユニバーサル基板/candidates/L5/`.

## Read first
1. `ユニバーサル基板/BRIEF.md` (goal, scope = 54 refs, priorities, user's answers: single-sided board, mainly bare tinned wire on the bottom along the grid, insulated jumpers only where unavoidable, no scaffold).
2. `ユニバーサル基板/tools/README.md` — shared tool `tools/ub.py` (verify / route / optimize / render / wirelist). Always pass `--board ユニバーサル基板/board.json`. Python: `C:/Users/ktrog/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8`.
3. Rules: **`ユニバーサル基板/design_rules_v0.2.json`** (approved; amendments in its `amendments_v0_2` block) and the rationale in `design_rules.md`.
4. Inputs: `board.json` (秋月 104708, 55 × 40 holes, 155 × 114 mm), `footprints_ub.json`, `netlist_ub.csv`, `parts_fit.csv`.
5. **Starting point: `ユニバーサル基板/candidates/L4/`** (round 3, comparison tuple (true, 0, 0, 28, 219.03, 105, 3141.2 mm)). The other finalist was `candidates/L1/` ((true, 0, 0, 31, 218.58, 57, 3077.0 mm) — notably far fewer bends; study how it routes) — borrow any good idea from it. Earlier rounds: L1–L4 summaries in each folder (L2 = 2×2 and L3 = short-edge column were rejected; their proofs are informative).

## Objective (lexicographic, highest first)
1. LVS PASS, core DRC 0, **hard FAIL 0** under v0.2 (tool comparison tuple).
2. **Compactness — new, requested by the user.** The user noticed big empty areas and parts crowded at the top and bottom. Pull everything that is not an edge connector up next to the driver row: Pico, VREF divider, stop/FAULT parts, SmartNet receiver (buffer, 1 kΩ, pull-up, BAT43) and its connectors, regulator and entry power parts. Keep only connectors and the Pico USB at edges. The user chose to **keep the full board uncut** (all four mounting holes stay) and accept an empty southern part. Target: everything within the northern ≈ 26 rows if the rules allow; report the used row range. The aim is shorter wires: report max IN length, VREF branch lengths, power path lengths, total length — all should drop versus the base.
3. Insulated jumpers ≤ 20 (≤ 16 if reachable).
4. Soft penalty, bends, total length, number of wire pieces.

## Quality review and fixes (you are the last line before the student builds it)
Review and fix, or explicitly justify, each of these:
- Electrical: VREF and logic lines (SLEEP, FAULT, IN, UART) distance from coil OUT wires and XH3 connectors; ground return paths (power vs quiet, star roots); decoupling placement; TVS/entry loop; regulator caps.
- Thermal: spacing around Pololu carriers, MBR3045FCT (D103), polyfuse F102, regulator U107, electrolytics.
- Mechanical/access: USB plug + BOOTSEL, finger grip to pull the Pico and each carrier straight up, XH connectors mated from the top with cable exit room, DC-jack plug, panel-switch headers, probe pins reachable by a meter probe, M3 hardware keep-outs.
- Buildability: identical channel tiles; bare-wire runs that a student can lay straight (no long unsupported spans, anchors every ≤ 8 holes); no bare wire running right beside another net's pad without a free hole between where avoidable; sensible gauges (1.0 mm trunks, ≥ 0.6 mm channel branches, 0.5 mm signals; AWG24/26 insulated for jumpers); count solder joints and wire pieces.
- The UNCHECKED hard rules (≈ 23): verify as many as you can by your own geometric analysis (e.g. access corridors, keep-outs) and list the rest as build-time checks.
- Drawings: top / bottom (mirrored, clearly marked) / overlay must be readable printed on A4 (labels not overlapping, legend, hole coordinates on all four sides).

## Extra deliverables for the build documents (data and figures only — Claude writes the Japanese text)
- `build_steps.csv`: ordered build steps (step no., phase, what to do, part refs / wire ids, holes, wire type & cut length incl. allowance, side), phases: 1 sockets & low parts, 2 power trunks & local caps, 3 channel wiring (identical ×4), 4 control/logic wiring, 5 insulated jumpers, 6 connectors & probes, 7 checks.
- Stage figures: SVG (+ PNG) of the bottom view after phases 2, 3, 4, 5 so a student can follow progress.
- `continuity.csv` (keep the tool's) plus a short "must NOT beep" list for the power-on safety check (VM–GND, +5V–GND, +3V3–GND, VM–+5V, VM–+3V3, VIN_RAW–GND …).
- `summary.md` (English): base → L5 comparison table (tuple, used rows, jumpers, pieces, joints, lengths, IN/VREF/power path lengths), list of quality issues found and how each was fixed or justified, UNCHECKED list, remaining risks.

## Constraints / authority
- Do not modify shared files (BRIEF, tools/, design_rules*.json, board.json, footprints_ub.json, netlist_ub.csv, parts_fit.csv, 基板/) or other candidates' folders. Copy what you need into L5/. If the shared tool limits you, write local helper scripts in L5/ and report the limitation.
- Do not change the circuit or parts. If you believe a part or rule change would clearly improve the result, finish the best layout without it and then ask (QUESTIONS_FOR_CLAUDE) with the evidence.

## Verification
`ub.py verify` → paste the comparison tuple and key lines into summary.md; open every SVG/PNG you produce and fix overlaps.

## Budget
About 2 hours. Stop earlier if further gains are marginal.

## Allowed simplification to test (Claude's decision, conditional)
Round 3 showed that the free row under the modules cannot carry a logic bus because each carrier's logic-side GND pin (U3x0 pin 2, `GND@2`) needs a stem down to the power-GND trunk, crossing that row. Pololu describes the GND pins as "ground connection points for the motor and logic supplies" — on the carrier both GND pins are most likely the same copper. **First verify from Pololu's carrier schematic** (`https://www.pololu.com/file/0J1862/drv887x-single-brushed-dc-motor-driver-carrier-schematic.pdf`, download into a git-ignored folder in L5/, e.g. `_sources/` with a `*` .gitignore) or the dimension/pinout drawing that GND pin 2 and GND pin 13 are the same net on the carrier. **Only if verified**, you may leave `GND@2` unwired on the host (treat it like the DC-jack spare pad: reserved, internally connected through the carrier), using a local netlist/rules copy in L5/ that documents this exemption (G01 POWER_RETURN then lists only GND@13 for each carrier). Report the evidence and the jumper saving. If not verifiable, keep GND@2 wired.

---
## Protocol: asking Claude (your supervisor)
You are a sub-agent supervised by Claude. Claude owns the objective, priorities, and anything outside your decision authority.
If you hit a decision you are not authorized to make, or ambiguity where a wrong guess would waste significant work
(unclear requirement, conflicting constraints, missing spec value, destructive/irreversible action, invalidated assumption):
1. Do NOT guess. First finish any work that does not depend on the answer.
2. Then end your turn with this block at the very end of your final message:

QUESTIONS_FOR_CLAUDE
1. <question> | context: <what you found> | options: <A / B ...> | recommendation: <your pick and why>
END_QUESTIONS

Claude will reply in this same thread. For minor choices within your authority, decide yourself and list them under "Assumptions" in your report instead of asking.