from round3_route import *
from collections import Counter
def main():
    p=Project(HERE);r=load_json(HERE/'out/report.json');m=r['metrics'];old=load_json(HERE/'round2/out/report.json')['metrics'];e=load_json(HERE/'out/extra_metrics.json')
    gauges=e['wire_length_by_diameter_and_kind_mm']
    gauge_rows='\n'.join(f"| {g} | {d.get('bare',0):.3f} | {d.get('jumper',0):.3f} | {sum(d.values()):.3f} |" for g,d in gauges.items())
    vref=' / '.join(f"{d['length_mm']:.3f}" for d in e['branch_lengths']['V04'])
    longest=max(e['branch_lengths']['S04'],key=lambda d:d['length_mm'])
    verify_lines='\n'.join((HERE/'out/verify.log').read_text('utf8').splitlines()[:3])
    text=f'''# L4 — F4, round 3 (2026-10-22)

**LVS PASS; core DRC 0; known hard FAIL 0.** Hard checks: **38 PASS / 23 UNCHECKED**. Final jumpers: **28**, improved from 30; the requested ≤20 / stretch ≤16 targets remain unmet. Soft penalty falls **2.92%**. The frozen round-2 inputs, outputs and helper snapshots are under [round2/](round2/), with `archive_hashes.json`.

## Round 2 → round 3

| Measure | Round 2 | Round 3 |
|---|---:|---:|
| LVS / core DRC / hard FAIL | PASS / 0 / 0 | PASS / 0 / 0 |
| T7 weighted soft penalty | 225.624726 | **{m['t7_soft_penalty']:.6f}** |
| Insulated jumpers | 30 | **28** (−6.67%) |
| Bare wire pieces / straight segments | 83 / 166 | **85 / 177** |
| Total wire pieces / wirelist steps | 113 | **113** |
| Bends, bare + insulated | 83 + 8 = 91 | **92 + 13 = 105** |
| Bare length, mm | 1836.420 | **1983.740** |
| Insulated length, mm | 1217.737 | **1157.506** |
| Total projected length, mm | 3054.157 | **3141.246** (+2.85%) |
| Estimated solder-pad locations | 372 | **388** |
| Longest IN line, mm | 121.920 | **111.760** |

Final tuple: **`(true, 0, 0, 28, 219.029964, 105, 3141.246)`**. Legacy `metrics.score` is **{m['score']:.3f}**, including UNCHECKED errors; use the T7 tuple for ranking. The soft score is partial: B03/B04/S03 have unchecked aspects. Known penalty terms are P07=128, P10=40, B06=37.5, B04=9, V05=2.24, S05=1.623298, B05=0.666667.

## Retained layout and actual changes

All **20 channel-tile part placements**, all four identical local wiring patterns, the bare 1.00 mm VM/GND trunks between socket rows, Pico placement, power entry, regulator, receiver and stop components remain as in round 2. The north row is CH4/CH3/CH2/CH1, all carriers 270°. Pico stays at BB20 / 90°, GPIO side north and USB east. Main VM is A7–AQ7; power GND is D8–AW8. All host wiring is on the bottom.

The four moved parts are the VREF block: **C211 Z13 / 90°, R209 X11 / 90°, R210 AB13 / 90°, TP466 AB11**. A better routing order makes one SLEEP connection bare. The regulator's VM feed is also bare. Its insulated ground return now follows that VM path with a roughly one-hole offset, rather than taking a direct diagonal: this preserves paired routing at the cost of five added ground-wire bends. The supplemental pairing check gives a conservative separation bound **{e['regulator_pairing']['conservative_upper_mm']:.3f} mm**, within 5.08 mm after the permitted terminal escapes. Shared B01 remains UNCHECKED.

| Supervisor idea | Result / reason for keeping or rejecting |
|---|---|
| One shared bus on row 9 | Tried SLEEP and PMODE. Three GND2 stems cross that row; insulating them erased the bus savings. Neither complete bus beat the final tuple. |
| FAULT on the power side / around the strip end | A straight row-6 bus passes within one hole of OUT pins, below the required clearance outside escape disks. A safe three-jumper diagonal chain plus an end detour was tried; its GP15 route created other crossings. Retained the four quiet fan-outs. |
| Central Pico, south USB; bare staggered IN | The best tested south-USB solution with hard FAIL 0 had 32 jumpers. West-USB explorations also conflicted with the 40-hole UART bound unless the receiver moved. Kept the better east-USB layout. |
| Bare VREF star | Tested positions and divider rotations, including a single-side source tap. Other-net jumpers erased the gain; the final true star has two insulated branches. Five branch groups share a four-direction root, so at least one jumper is needed somewhere in the complete star. |
| Regulator near entry | Relocation increased wiring conflicts or failed fit/thermal bounds. Kept U107 and retained the successful bare VM connection, with its paired insulated ground return. |

## Detailed metrics

Scope is **54 refs, 186 logical pins, 42 nets, 22 logical NC pins**, plus **7 reserved physical NC pads** with no host wiring. G01, G02 and V01 all **PASS**. XH3 centres remain unwired. Channel components/rotations and local capacitor/OUT/CS patterns are identical.

| Copper diameter | Bare mm | Insulated mm | Total mm |
|---|---:|---:|---:|
{gauge_rows}

Areas are 0.785 / 0.322 / 0.196 mm² for 1.00 / 0.64 / 0.50 mm copper. Trunks and VIN_RAW/FUSED/PROT use 1.00 mm; channel VM/GND/OUT branches and regulator/Pico supply/returns use 0.64 mm; signals use 0.50 mm.

- Longest IN: **HDD4_IN2, U201.12 → U340.4, {longest['length_mm']:.3f} mm = 44 holes**, below 60. Two IN lines remain bare; six use insulation.
- VREF branches CH1/2/3/4: **{vref} mm**; longest 33 holes, below 40. Exact branch details are in `out/extra_metrics.json`.
- VM J104.2 → VIN14, CH1/2/3/4: **154.940 / 119.380 / 83.820 / 58.420 mm**. GND J101.2 → GND13: **167.640 / 132.080 / 96.520 / 60.960 mm**. GND2 paths are 2.540 mm shorter. Panel and HDD harnesses are excluded.
- Regulator VM_ENTRY → VIN and GND_ENTRY → GND: **99.060 / 99.660 mm**, longer than round 2's 61.43 / 59.24 mm. They follow the same corridor; this is a jumper-count trade-off, not a short-loop improvement.
- Identical local lengths: 100 nF → VIN/GND **7.62/7.62 mm**; 470 µF → VIN/GND **12.70/15.24 mm**; OUT1/OUT2 → XH3 **7.62/10.16 mm**. TVS attachments **12.70 mm each**; converter cap attachments **15.24 mm each**; buffer bypass attachments **10.16 mm each**.
- Used bounding box **140.780 × 101.170 mm**, physical NW coordinates **(6.160, 6.610)–(146.940, 107.780) mm**, or **80.604%** of the 155 × 114 mm board. Tool `used_area_fraction=1.00347` uses grid area rather than physical-board area; it is not an off-board error.

## Verification and remaining review

Actual shared-CLI lines from [out/verify.log](out/verify.log):

```text
{verify_lines}
WIRE LIST: 113 steps
CONTINUITY: 1439 tests (bare board, power off)
```

`ranking_pass=true`, `hard_failed_rule_ids=[]`, `core_drc_errors=0`. The aggregate `verify` exit code remains **1** because all **32 error findings are UNCHECKED**; none is a measured hard FAIL. Render, wirelist and continuity exit 0. The 1439 continuity checks were generated, not physically executed.

UNCH ECKED hard IDs (23; spelling below is the tool's exact ID list):

`B01 B02 B07 C01 C02 C03 M02 M03 M04 M05 M06 M08 M10 M12 S01 S02 W01 W02 W03 W04 W05 W06 W07`.

These cover scope provenance / formed leads and solder clearance; hardware and USB/BOOTSEL/grip/latch/probe 3D access; missing J104/J213 mating-face coordinates; physical OUT separation; wire/contact/drop/off-board harness evidence; pairing and supports. Their full reasons remain in `out/report.json`. Soft UNCHECKED IDs: **B03, B04, S03**. No unchecked status was promoted to PASS.

Supplemental planar checks: S01 conservative spacing **6.578 mm** versus 5.08; S02 **13.318 mm** versus 7.62; bare-wire surface gap **1.540 mm**, excluding pads, formed leads, solder and insulation outside diameter. Top, mirrored bottom and overlay SVGs were opened through the offline XML raster preview and all three PNGs inspected. Each has 54 unique refdes labels and **zero font-box overlaps**. CSV hole identities are always TOP coordinates.

## Build effort and handoff

Estimate **113 wire pieces**, **193 physical component/NC-pin pads**, and about **388 distinct solder-pad locations** with support at ≤6-hole intervals (`out/solder_plan.csv`); soldering every traversed bare-wire land instead gives **879**. Allow roughly **4–7 hours** for forming, assembly and staged continuity checks. Lengths are projected paths; actual termination and wire-height allowances still need checking.

Build trunks and repeated channel blocks first, then quiet ground / bare signals, then insulated bottom jumpers. The wirelist's alphabetical order is not mandatory assembly order. Run continuity with power off **before population**; semiconductor/capacitor paths and the jack's internal spare ground invalidate simple post-population beep expectations.

The ≤20 target was not reached within the focused pass. The accepted trade-off is fewer jumpers and lower soft penalty, with 14 more bends, 2.85% more wire and a longer regulator input pair. Near-limit bypass/TVS routes still need actual lead-dress checks. Thick surface-laid trunk joints require supports; do not force 1.00 mm wire together with a lead into one 1.00 mm hole. Keep ≥10 mm underside standoff. Dry-fit connectors/modules/BOOTSEL and confirm coil AWG26 lead temperature, contacts, panel harness drop and all thermal/noise/stop tests.

Final inputs are `placement.json` and `routing_config.json`. Run **`round3_route.py`**, then `run_checks.py`, `quality_local.py` and the offline `raster_svg.py` preview. `route_local.py` also dispatches round-3 configurations correctly. Shared files and other candidates were not modified. `round2/archive_hashes.json` verifies the frozen snapshot; `input_manifest.json` records current input hashes and shared-tool commands. All other `r3_*` and search files are experiments, not additional construction versions.
'''
    text=text.replace('UNCH ECKED','UNCHECKED')
    (HERE/'summary.md').write_text(text,encoding='utf8')
if __name__=='__main__':main()
