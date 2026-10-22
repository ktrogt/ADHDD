# ADHDD schematic inputs - T1, 2026-10-21

Scope: specification v0.7 sections 6.1-6.9 only. Four sheets: 1 POWER, 2 CONTROL, 3 DRIVERS, 4 OPTIONAL. Pickup board, mounting holes, off-board HDD coils/NTCs/switches and cable-side connectors are excluded.

**Status: schematic baseline approved by Claude on 2026-10-21.** J101's logical terminals and connections are approved. Its physical footprint remains a PCB-stage hold and does not block schematic capture. Use `MJ179PH_PLACEHOLDER`, a clearly marked placeholder package with 3 pads named 1/2/3 and no claimed physical positions, drills or slots. Replace its pad/slot geometry before layout, using measurements of the real part or a detailed drawing. This is not a PCB production release. See the research log at `../参考/調査記録/12_2026-10-21_回路図の部品とピン配置.md`.

| File | Purpose |
|---|---|
| `parts.csv` | 80 schematic parts, exact unique symbol pin names, footprint IDs/details, store codes and sources. 54 populate=yes includes 13 bare test pads; 26 are DNP. |
| `netlist_expected.csv` | 252 external terminal rows, 50 named electrical nets, 22 individually disconnected NC terminals. Includes every DNP pin. |
| `compare_netlist.py` | Standard-library-only strict name, pin identity and connectivity partition comparison. |

`validate_inputs.py` checks inventory, coverage and non-NC net cardinality. `build_inputs.py` records the reproducible data construction and refuses to overwrite existing CSV outputs; it is not an approval mechanism.

Create symbols with `pins` names verbatim, including `/OE`, `/E`, and `GND@physical_number`. Passive and connector numbers are locally defined where the manufacturer does not number a terminal. The Pololu module uses a documented local counterclockwise 1-14 numbering, **not the DRV8874 IC pinout**; Claude visually verified its labelled top-view order. Use the top component view in `footprint_details`; do not mirror a bottom-view drawing. J101 uses approved logical 1=CENTER, 2=SLEEVE, 3=SWITCH in the placeholder package. Do not infer production geometry from that package.

The Pico and four Pololu parts each own their socket footprint. Do not add duplicate socket symbols to the electrical netlist. The internal components of a carrier/Pico are outside this comparison. Carrier R2 and R4 removal, with R3 retained, is an assembly requirement, not a change to the main-board CSV. The carrier's `VM` terminal is different from the main-board net `VM`; Claude approved leaving carrier `VM` and `IMODE` externally NC, with main-board VM feeding carrier `VIN`.

Sheet 4 numbering: U401/C402 are the mux/bypass capacitor; R403 is the UART bypass. For channel n, base=400+10*n: R(base+1)/C(base+1) are the CS filter, R(base+2)/C(base+2) the NTC divider/filter, J(base+3) the PH connector. R451/R452/C451 are VM sense. TP460-468 are common rails/control and three grounds; TP471-474 are CS1-4. DNP parts remain symbols, pads and separately named nets; do not electrically collapse a DNP resistor or connect its two pads together.

Export **actual schematic read-back**, not a copy of the expected file, as UTF-8 CSV with the same four columns. Include every terminal, including unconnected and DNP terminals. For `--key name`, the actual pin number may be blank; a supplied number must agree. Repeated ground pins must retain their unique names. Preserve exact net names across sheets.

```text
python compare_netlist.py --selftest
python validate_inputs.py
python compare_netlist.py netlist_expected.csv actual.csv --key number
python compare_netlist.py netlist_expected.csv actual.csv --key name
```

On this Windows host, the bundled interpreter is under `%USERPROFILE%/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` if Python is absent from PATH. Run from this folder, or supply full CSV paths.

Exit 0 means identical net names, pin identities and connectivity partitions; 1 means mismatch; 2 means invalid input. A renamed but electrically identical net fails the name check. Shorts and splits are detected independently of names. `NC` is a per-terminal disconnected state, never a global net: place no NC net labels or wires. An actual isolated pin should export as NC. If two otherwise unused pins are wired together, export their real shared net name (even an automatically generated one), never two NC rows. The exporter must inspect real wires/net objects for this reason.

The comparator validates schematic connectivity only. Physical pad mapping, footprint dimensions, electrical ratings, assembly modifications, ERC, placement and PCB routing require their own review. All chosen drills/pads/courtyards are recommendations; source facts and remaining assumptions are distinguished in the research log.
