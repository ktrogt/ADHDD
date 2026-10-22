# BRIEF — ADHDD main board on a universal (perf) board

Internal brief for agents (English). Written by Claude (supervisor), 2026-10-22. Read this first.

## Background
- ADHDD: a musical instrument that drives the voice-coil actuators of 4 hard disks. One Raspberry Pi Pico + 4 Pololu #4035 (DRV8874 carrier) boards, 12 V adapter, SmartNet UART input. Spec: `HDD楽器_仕様書.md` v0.7, chapter 6 (Japanese).
- The user decided (2026-10-22) to build the main board by hand on a **universal board (perfboard, 2.54 mm grid)** instead of ordering a PCB. A PCB/Fusion attempt was abandoned; its data is reused.
- Parts should be bought from shops with a physical store in Akihabara (秋月電子通商, 千石電商 preferred). Existing BOM with store codes: `部品表.md` §2. Older Akihabara research: `秋葉原パーツ購入リスト.md`, `参考/調査記録/09`, `10`.

## Approved data (read-only — do not edit)
- `基板/parts.csv` — 80 parts with verified pinouts, physical data (`footprint_details`: pitch, lead diameter, body size, sources) and `populate` (yes / DNP).
- `基板/netlist_expected.csv` — the approved netlist (`net,ref,pin_number,pin_name`; NC = unconnected).
- `基板/compare_netlist.py` — netlist comparison (`--key name|number`, `--selftest`).
- `参考/調査記録/12_2026-10-21_回路図の部品とピン配置.md` — sources for pinouts. Pololu #4035 pin order verified by Claude on Pololu's labelled photo: left column top→bottom VM, GND, EN/IN1, PH/IN2, PMODE, SLEEP, VREF; right column top→bottom VIN, GND, OUT1, OUT2, IMODE, FAULT, CS; columns 12.70 mm apart (5 holes).

## Circuit scope for the perfboard (Claude's decision, may be revised)
- = spec v0.7 main board **minus the optional "scaffold" (DNP) parts**: U401 (74HC4052), C402, R403 (0 Ω bypass), R411–R442 / C411–C442 / J413–J443 (CS filters, NTC dividers, NTC connectors), R451/R452/C451 (VM sense). Keep those GPIOs free (GP17, GP18, GP26–GP28) so they can be added later with wires.
- Keep the receive buffer U207 (74AHC1G125, SOT-23-5) — how to mount it on a perfboard is decided after research (conversion board vs. through-hole alternative with power-off-tolerant input).
- Test points (TP460–TP474 in parts.csv) become "probe points" (e.g. single header pins or exposed wire loops) — the layout may implement a reduced, practical set: VM, +5V, +3V3, GND, VREF, SLEEP, FAULT, HDD1–4_CS.
- Power switch and stop switch are off-board panel toggles connected through 2-pin headers (J104, J213).
- Part substitutions for perfboard fit (connectors, diode lead size, DC jack…) come from task T5 and need Claude's approval when they change anything electrical.

## User's answers (2026-10-22)
- No size constraint (no enclosure yet) → choose a standard 秋月/千石 universal board with comfortable margins.
- Wiring style: **single-sided board, mainly tinned copper wire (スズメッキ線) on the bottom along the grid**; insulated jumpers only where crossings are unavoidable.
- Scaffold (temperature/current/voltage sensing) is **not mounted and no area is reserved**; only keep the GPIOs free.

## Priorities (objective, highest first)
1. **Correct connectivity**: the built wiring realises exactly the approved netlist (scope above) — no shorts, no opens. Machine-checked.
2. **Safety & robustness**: wire sizes match currents (12 V trunk up to ~2.6 A total; each driver ≤ ~0.6 A); power and ground distributed from the input point (star / trunk without shared narrow returns); 470 µF + 100 nF right at each Pololu VIN/GND; TVS close to the input; VREF distributed in a star and kept away from coil OUT wires and connectors; SLEEP/FAULT/UART also away from OUT; heat sources (Pololu boards, 1N5822, DC-DC) spaced and not next to electrolytics/polyfuse.
3. **Easy to build by hand**: few wires, few insulated jumpers, no crossings of bare wires, short runs, every instruction expressible as hole coordinates (column letter + row number), connectors on board edges, Pico USB connector and BOOTSEL button reachable, Pololu boards and Pico removable (sockets).
4. **Compact**: fits a standard Akizuki/Sengoku universal board with comfortable margins.
5. **Availability/cost**: parts from 秋月/千石 when possible.

## Shared conventions
- Folder for all perfboard work: `ユニバーサル基板/`. Internal files may be English. User-facing Japanese documents are written by Claude.
- Python is not on PATH: `C:/Users/ktrog/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` (stdlib only unless stated).
- Hole coordinates: columns A, B, C… (left→right, top view), rows 1, 2, 3… (top→bottom, top view). Bottom-view drawings are mirrored left↔right and must say so.
- This repository is PUBLIC: no personal data; third-party downloaded files go under a git-ignored folder.
- Never: purchase, log in / create accounts, delete or overwrite approved files, contact anyone.
