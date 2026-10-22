# Fusion Electronics recipe — ADHDD M0b

2026-10-21, Fusion 2705.1.25. **PARTIALLY PROVEN; STOPPED ON A ~2-MINUTE MCP HANG.**

## Current authority

Claude/user restored MCP schematic authoring. Use existing uploaded libraries only; no custom library. The XML-import plan is superseded. Old custom-library source files in tmp are obsolete and must not be used. Do not modify source libraries, T1/T4 CSVs, or the original unsaved Design document. That document may only be activated as the MCP starting/return context. One schematic sheet; no frames, title blocks, or block rectangles.

Approved inputs: `library_map.csv`, `library_sources.md`, `netlist_expected_lib.csv`. Translation checker passed: 84 placed refs, 248 symbol-pin rows, 255 pads, 24 NCs. M0b scope is R209 / R210 / C211 / R411 plus supply symbols.

## Proven call pattern

At entry the original unsaved Design was active, `activeCommand=SelectCommand`, `isDefaultCommand=true`, unmodified. The script activates the ADHDD schematic, executes commands, then reactivates the original Design. Never save/close/edit the original Design.

```python
import adsk.core, adsk.electron

def run(_context: str):
    app = adsk.core.Application.get()
    parking = app.activeDocument
    assert parking.objectType == 'adsk::fusion::FusionDocument'
    assert not parking.isSaved and not parking.isModified
    assert app.userInterface.activeCommand == 'SelectCommand'
    doc = next(d for d in app.documents if d.name == 'ADHDD_main_schematic')
    doc.activate()
    try:
        result = app.executeTextCommand('Electron.run ' + COMMAND)
        print(result)
        adsk.doEvents()
    finally:
        parking.activate()
    print(app.userInterface.activeCommand, parking.isModified)
```

Use a normal script, never `readOnly:true`, for this pattern. This is an authorized document activation, not a change to the original Design. `finally` cannot run while a native modal blocks the call, so it does NOT guarantee restoration after a hang.

**Measured synchronization:** `GRID INCH 0.1 OFF;` changed `grid.on` immediately to False; `GRID INCH 0.1 ON;` immediately restored True. Event pumping did not change either result. Grid distance=0.1, unit=3. Both commands together took 0.340 s. The first cloud ADD immediately increased parts from 0 to 1 before `doEvents`; it took 0.697 s. These two operations were synchronous to read-back; do not generalize to every EAGLE command.

Evidence/code: `tmp/m0b_grid_probe.py`, `tmp/m0b_place_first_resistor.py`, `tmp/m0b_successful_calls.json`.

## Existing cloud libraries — proven identity and USE

Project API ID:
`<PROJECT_ID_REDACTED>`

Folder `ADHDD` contains eight `.flbr` files. DataFile metadata matched Claude's inventory. Read-only inspection of Fusion's local library index showed all eight uploaded WIP libraries already `isused=1`, `downloaded=1`; library content was not modified. Same-name public libraries also exist, so use the uploaded WIP URN to avoid ambiguity.

M0b library identifiers:

```text
adafruit      <FUSION_FILE_URN_REDACTED>
Power_Symbols <FUSION_FILE_URN_REDACTED>
```

This command completed with the activation/return pattern:

```text
USE '<FUSION_FILE_URN_REDACTED>' '<FUSION_FILE_URN_REDACTED>';
```

Since both were already In Use, this proves the URN form returns successfully, not a 0-to-1 activation transition. Exact script: `tmp/m0b_use_cloud_libraries.py`. [USE documentation](https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECD-CLI-U.htm).

**Successful first placement:**

```text
ADD 'R-US_0204/7@<FUSION_FILE_URN_REDACTED>' 'R209' R270 (5.0 3.6);
```

Direct `fusion_mcp_electronics_read` returned:

```text
Part: R209, value="", object_id=114745
Instance: R209, sheet=1, x=5.0, y=3.6, angle=270, mirror=0, smashed=1
Library: adafruit, library_object_id=<FUSION_FILE_URN_REDACTED>, editable=0
```

`Part.device.libraryUrn` was empty, despite the library entity carrying the correct cloud ID. Do not use that one blank property to conclude a raw/local library was used. The electronics-read tool successfully read this schematic while the plain Design was active; verify the returned identities because that context behaviour is not guaranteed by the tool description.

Do not ADD from a raw `.lbr` file path: the earlier attempt caused `PlacePartWorker.cpp:23, assetAdded`. No raw-file ADD was attempted in M0b.

## Stop point and uncertainty

The next normal script (`tmp/m0b_pending_parts_batch.py`) did not return within approximately two minutes. Its sequence was:

1. VALUE R209=47k.
2. ADD/value R210=4.7k; ADD/value C211=220nF/50V; ADD/value R411=100k.
3. ADD SUP_3V3 from +3.3V; override value to +3V3; ADD two GND symbols.
4. Return to the original Design, then save the schematic.

The call returned no script output before the waiting cell was terminated. **The exact failing command, which steps completed, current active document, and save outcome are unknown.** Terminating the caller does not prove cancellation inside Fusion. No subsequent Fusion calls were made. Do not replay this batch after recovery: inspect actual parts/values/instances first and issue only missing work, one new operation per call until verified.

No net wires, labels, title or DNP metadata were submitted in that batch. No ERC, PNG, PDF or final save-state verification was completed. No `netlist_actual_m0b.csv` was fabricated from the expected data. `tmp/netlist_expected_m0b.csv` contains the eight approved rows and is ready for comparison after actual read-back.

## Layout and pending checks

Read from the approved library snapshots (read-only):

- R-US_ / 0204/7: symbol pins 1=(-0.2,0), 2=(+0.2,0) in inches. At R270 pin1 is above and pin2 below. Refdes/value become independent attributes (`smashed=1` was observed).
- C-US / 050-035X075: vertical at R0; pin1=(0,+0.1), pin2=(0,-0.2).
- +3.3V supply: connection at symbol origin; GND connection at origin+(0,+0.1). VALUE override must be verified by actual net names.
- Supplied help supports `MOVE R209>NAME (x y);` and `ROTATE =R0 R209>NAME;` for independent text. These text adjustments are not tested yet.

Planned centres: R209=(5.0,3.6), R210=(5.0,2.6), C211=(6.2,2.7). VREF at y=3.1, separate T-junctions at x=5.0 and x=6.2, label to the right. +3V3 origin=(5.0,4.0), GND origins=(5.0,2.1)/(6.2,2.1). Header text `CURRENT LIMIT (VREF, common)` above. R411=(5.5,0.8), horizontal, labels HDD1_CS left / HDD1_CS_F right; title with `(OPTIONAL - DNP)` and visible DNP next to the unchanged value 100k. These are plans, not completed wiring.

Remaining checklist after recovery:

1. Obtain the warning text (including file/line/condition); user dismisses it and leaves the original Design active. Read actual state without touching `EcadDesign.board` (known `boardLink` error when no PCB exists).
2. Inspect pending changes; set/test VALUE separately. Complete parts and verify cloud library identity. Save only ADHDD documents once the safe save call is proven.
3. Add orthogonal NET wires and junctions, labels and plain block text; reposition names/values horizontally. Verify +3V3/GND override semantics.
4. DNP: test a visible DNP attribute and an ASSEMBLED variant with `R411 NOPOPULATE`; verify native population/BOM behaviour rather than relying on text. Return to default variant before further ADD/VALUE operations.
5. Read Net/Segment/PinRef/Part/Instance/Pin/Contact through `fusion_mcp_electronics_read`. Export actual four-ref/eight-pin CSV; supply symbols excluded. Compare by name (numbers too if available) against `tmp/netlist_expected_m0b.csv` using `compare_netlist.py`.
6. Run ERC, read checked state and errors; export unique native PNG >=150 dpi (prefer 300) and PDF into `schematic/`. Inspect PNG. Save schematic/container if changed; verify saved flags; leave original Design active and unmodified.

## M1 proposal (only after M0b approval)

Build POWER left, CONTROL centre, DRIVERS right as a 2x2 array, OPTIONAL and TEST POINTS below. Allocate block origins on 0.1-in grid, calculate transformed pin endpoints from the selected existing symbols, and route through separate orthogonal T-joins. Use labels at block boundaries and horizontal smashed text with reserved whitespace.

First validate one command family per call; only then batch a few proven operations. After every block check ref/value/package/gate inventory, exact pin-to-net assignments and geometric grid/crossings; save before proceeding. For U207 invoke PWR explicitly. Pico uses RPI_PICO/_H with merged GND pad-list and separate AGND. Pololu uses two numbered headers per carrier with per-pin signal annotations. Apply approved F102 proxy/fuse text and connector reversal rules verbatim. Check full 84-ref/248-row `netlist_expected_lib.csv`, including NC and DNP terminals, before visual review. Respect the unresolved J101 PCB footprint hold.
