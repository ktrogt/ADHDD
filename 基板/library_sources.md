# T4 - Existing libraries for ADHDD (2026-10-21, final supervisor decisions)

All 80 original references now have existing-library selections. Manual downloads: **none**. Source counts: fusion_std32 / vendor0 / open_repo48 / user_download0 / none0. Decisions: use34 / use_with_mismatch46 / user_download0 / no_existing_library0. Four Pololu references each become two placed headers, so Fusion places84 component references.

No library content was authored or modified. Original `parts.csv` and `netlist_expected.csv` remain unchanged. All selected libraries are present under ignored `libs/`; no upload, purchase, login, terms acceptance, commit or push was performed. J101 remains the previously approved schematic-only proxy with a **PCB-stage HOLD**.

## User actions, in order

1. Import these **eight exact files** together: `libs/adafruit.lbr`, `libs/Capacitor.lbr`, `libs/Connector.lbr`, `libs/Development_Boards.lbr`, `libs/Diode.lbr`, `libs/IC_Logic.lbr`, `libs/Power_Symbols.lbr`, `libs/SparkFun-AnalogIC.lbr`. No manual component-site downloads are needed. `SparkFun-README-2012.txt` is the retained license/attribution notice, not an import file.
2. Fusion: **Show Data Panel -> target project/folder -> Upload -> Select Files -> select the eight .lbr files -> Upload**. Open schematic **Library Manager -> Hub Libraries**, enable **In Use**, then use the exact deviceset/device/package in `library_map.csv`. These are Autodesk's [local .lbr upload steps](https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECAD-IMPORT-FROM-LBR-TSK.htm) and [library-enabling workflow](https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECD-TUT-ECAD-MANAGE-LIBRARIES-TOP-LEVEL.htm). Existing managed Library.io assets should instead use the [managed-library migration workflow](https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECAD-IMPORT-LIB-CPT.htm).
3. Fusion agent: place/name/value parts per the map; apply the Pololu pin labels, F102 fuse annotation and U207 PWR gate below. Export/read back using the translation convention below and compare against **`netlist_expected_lib.csv`**, not the original CSV. Run `python check_lib_translation.py` from any working directory to verify the saved translation; `--write` regenerates only the translated CSV.

## Sources, licenses and exact snapshots

Retrieval date for every file: **2026-10-21**. All six Fusion standard files were copied byte-for-byte from the installed `Applications/Electron/LibEagle/examples/libraries/examples/` folder. The downloaded Adafruit and SparkFun libraries reproduce their upstream Git blob SHA-1 values; they are existing files, not extracted or rewritten devices. `libs/.gitignore` contains `*` and `!.gitignore`, excluding the third-party files from this public repository.

| Source / files | URL / license |
| --- | --- |
| Fusion: Capacitor, Connector, Development_Boards, Diode, IC_Logic, Power_Symbols | Installed Autodesk distribution. No independent open-source grant identified in these XML files; preserve notices and do not infer redistribution rights. [Autodesk library overview](https://help.autodesk.com/view/fusion360/ENU/?contextId=ECD-LIBRARIES). |
| Adafruit: `adafruit.lbr` | [Repository/publisher description](https://github.com/adafruit/Adafruit-Eagle-Library), [raw file](https://raw.githubusercontent.com/adafruit/Adafruit-Eagle-Library/master/adafruit.lbr). Publisher declares public-domain release, noting EAGLE/microbuilder ancestry. Original author notices retained. Git blob `a5caac9b3653dc2213adef6faa7ed1d953c7ee36`. |
| SparkFun: `SparkFun-AnalogIC.lbr` | [Pinned original file](https://raw.githubusercontent.com/sparkfun/SparkFun-Eagle-Libraries/8d7ddd7deac8a9e7cbd330806d4e778d93e080b1/SparkFun-AnalogIC.lbr), commit `8d7ddd7deac8a9e7cbd330806d4e778d93e080b1` (2012-01-17). Git blob `9661abe214c373c82a9ec289cd8235e626dd36d4`. **CC BY-SA3.0**, per the [same commit's README](https://raw.githubusercontent.com/sparkfun/SparkFun-Eagle-Libraries/8d7ddd7deac8a9e7cbd330806d4e778d93e080b1/README), retained locally verbatim as `SparkFun-README-2012.txt`. This historical license is not the current repository's4.0 notice. |

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `adafruit.lbr` | 3508703 | `3d2af8aa33f0629a2b5c75b7fac3f5a1775724983b71f44c05028fa264d0e99e` |
| `Capacitor.lbr` | 132227 | `a2ca8866f712705052a6e4bb44e183e9d7234d64cb377a3a4985d879dc5be502` |
| `Connector.lbr` | 810680 | `6e559a2445a0d9a84a3d4d14ab1e693fbf3578cce9e46a1a07d6456ff940c8a4` |
| `Development_Boards.lbr` | 231956 | `849fec07c6a47d43a7b020e9882cc21654d31ca4b739b6be61d609b297fbb81b` |
| `Diode.lbr` | 196858 | `66b4bba8ba41e88f3b487500bccfca41c2910348c679172fe5b0b2ca55647de5` |
| `IC_Logic.lbr` | 289141 | `808589af1600fe2647208ba49c0e5008f97a8fbb2f4c7ff9b7e97dfeb8984fb9` |
| `Power_Symbols.lbr` | 60538 | `47c8a99f482aae76d7a2118b67310aab166436f9e2e767b0bfb6768f690bee97` |
| `SparkFun-AnalogIC.lbr` | 154325 | `2f2c6b24d9d05a4f8b3e47580f60e59d92fc430defe7642781d74f83354a51ff` |
| `SparkFun-README-2012.txt` (notice only) | 1416 | `5f533f13501cc8f7d2b1ca2e7c68af1146ecbe3c19648da945a6042df26452fc` |

The installed39 example libraries include the six standard names above, with `urn:adsk.eagle` component/footprint identifiers. Autodesk identifies maintained default collections in the [EAGLE PCB / Fusion Electronics folders](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Is-there-a-set-of-generic-or-default-electronic-libraries-in-Fusion.html). **The current cloud revisions were not inspected in Library Manager**: a matching name alone does not prove identical pads. Upload these snapshots for reproducibility, or recheck online component connections before substituting a cloud revision.

## Placement decisions and physical differences

`library_map.csv` retains one row per original reference. Empty `device` is the actual unnamed EAGLE variant. Dimensions below and in the CSV are mm. `use` means the symbol/lands fit the stated family; recommended drills/pads in T1 were design recommendations, not a demand for identical CAD geometry. All numerical deviations remain in `footprint_check`. Geometry-based fit conclusions are calculations, not measurements. Automatic pad diameters depend on final-board DRC.

| References | Selected existing device and capture/layout instructions |
| --- | --- |
| U310/U320/U330/U340 | **Claude approved** two `Connector / PINHD-1X7 / <empty> / 1X07` per carrier. Ref e.g. **U310A=LEFT**, **U310B=RIGHT**, both gateA. Header pins1..7 top-to-bottom: A=VM,GND,EN/IN1,PH/IN2,PMODE,SLEEP,VREF; B=VIN,GND,OUT1,OUT2,IMODE,FAULT,CS. Add visible Pololu signal text at each pin. Rotate both270deg and place package origins12.70 apart with pin1 rows aligned; lock relative position. Drill1.016 vs recommended1.10; reserve carrier15.2x17.8 and sockets. VM(A1)/IMODE(B5) NC; both grounds connected; remove carrierR2/R4,keepR3. Stock PINHD-2X7 has wrong row spacing. |
| U201 | **Claude approved** `Development_Boards / RPI_PICO / _H / PI_PICO_H` for readability. Correct2.54 pitch/17.78 row spacing, drill1.0, perimeter1..40. Extra SWCLK/D1 and SWDIO/D3 NC; D2 is joined to GND by the library and explicitly accepted. Seven perimeter GND terminals merge to the single symbol pinGND; AGND remains a separate symbol pin on the GND net. No custom library or split Pico references. Reserve actual21x51 body, sockets and USB clearance. |
| U107 | Adafruit `78* / T / TO220H`, gateA1, VIN->VI->pad1, GND->GND->2, VOUT->VO->3. Inline2.54 pitch, drill1.1176. Maximum lead0.75x0.55 has diagonal0.9301, leaving0.1875 diametral clearance. Readable regulator symbol, actual VALUE=M78AR05-1. Ignore TO220 outline; reserve actual11.5x7.55x10.2 and copy module body offset from the manufacturer's BOTTOM VIEW at layout. |
| U401 | **Pinned2012** SparkFun `74HC4052 / DIP / DIL16`, gateG$1. Correct2.54 pitch/7.62 rows and all16 pad assignments. /E->INH6 (HIGH disables), S0->A10, S1->B9. Actual VALUE=TC74HC4052AP. Drill0.8128 vs T1 recommendation1.0: smaller standard DIP holes require finished-hole/actual-lead fit confirmation before PCB release; reserve real19.25x6.4/maxL19.75 body. **Current** SparkFun-IC-Logic offers this device only in SO16, so do not replace the pinned file with it. |
| F102 | Existing standard `Connector / 2828XX-2 / 282837-2 / TERMBLK_508-2N`, gateG$1, generic two-terminal symbol/lands. Pitch5.08 is within MF-R3005.1+/-0.7; drill1.20 exceeds lead0.81 by0.39. This uses the supervisor's permission for an existing two-pin radial device with matching lands. **Label visibly `PTC FUSE / MF-R300`**, retain refF102 and value3A hold/30V; this is not a terminal-block purchase. Ignore terminal-block outline; reserve actual12x3/H18.3, clear of hot diode. Current SparkFun PPTC_PTH drill0.8 was rejected. |
| J101 | `Connector / PJ-102AH`, center1/sleeve2/sleeve-switch3 (NC). Keep MJ-179PH value. **Schematic-only proxy; its slots are not the real MJ-179PH footprint. Existing PCB-stage HOLD remains.** |
| JST PH | Adafruit `JST_2PIN / -THM / JST-PH-2-THM`, 4UCon surrogate. **SENSOR->symbol2->pad1; GND->symbol1->pad2.** The reversal is intentional. Pitch2.0, drill0.8, body6.0x4.5 vs JST5.9x4.5. Confirm actual key/orientation and fit at layout. |
| U207 | `IC_Logic / 74*1G125 / SOT23-5`, A.OE/I/O map pads1/2/4; **INVOKE PWR** for GND3/VCC5. Actual VALUE=74AHC1G125W5-7. The standard SOT25 land dimensions differ from T1's recommendation; exact coordinates are in CSV. |
| Passives/test pads | Use actual purchased values and envelopes. Diode C means cathode; electrolytic octagonal negative pad is not a positive pin1 mark. D110's generic silk and C108/C109's generic height understate the real envelopes. Bare test pads are1.016 drill/D2.54 instead of1.0/D2.5. Details for every ref remain in CSV. |

## Translated netlist contract

`netlist_expected_lib.csv` is the Fusion read-back comparison target, with columns `net,ref,pin_number,pin_name`.

- `ref`: placed reference, e.g. U310A/U310B. Each Pololu CSV-map target is fully qualified, e.g. `VM:U310A.1`, so its chosen numeric library pin is unambiguous.
- `pin_name`: actual library **symbol pin** name, not the original signal label. Example: PH physical pad1 is symbol2; diode cathode is C; U107 input is VI.
- `pin_number`: exact device XML **connect/@pad** string. Normally this is one actual package pad name. For Pico GND, it is the one field `3 8 13 18 23 28 38 D2`, preserving every pad attached to the single symbol pin. The read-back exporter must aggregate that symbol pin once in this same XML pad-list order, rather than emit seven duplicate GND rows or select one arbitrary pad.
- Seven original Pico GND rows become one library pin on the common GND net; the checker asserts every merged source was on GND. AGND is separate. The approved extra D1/D3 library pins each get an NC row; D2 is included in the GND pad-list. NC remains a per-pin disconnected state, never a shared electrical net.
- Supply symbols are excluded. Totals: **252 original terminals ->248 symbol-pin rows**, **84 placed refs**, **255 actual copper pads** (252 original plus3 approved debug pads), **24 NC rows** (22 original plus2 debug).

`check_lib_translation.py` checks the approved input hashes, all eight library hashes, every symbol/connect/package pad, exact80-reference/map coverage, every original terminal, unchanged nets, the independently defined physical pin-number convention, allowed Pico merging/extras and all placed library pins. It checks the saved translation by both number and name, rejects five deliberate error cases in memory, and runs `compare_netlist.py netlist_expected_lib.csv netlist_expected_lib.csv` as requested. No source CSV or library is written; optional `--write` writes only the translated CSV.

```text
python check_lib_translation.py
python compare_netlist.py netlist_expected_lib.csv FUSION_READBACK.csv
```

The checker proves the translation, not that an as-yet-unplaced Fusion schematic matches it. Fusion import/placement/ERC and final-board DRC/physical fit were not performed by T4.

## Supply symbols

Use `Power_Symbols.lbr`, unnamed device, no package. All four selected devices have observed `uservalue=yes`, `allow_supply_override=yes` and a `sup` pin; no library edit is needed.

| Required net | Existing deviceset/default pin | Exact name exists? | Instance VALUE |
| --- | --- | --- | --- |
| VM | +V / +V | NoVM deviceset among49 checked | VM |
| +5V | +5V / +5V | Yes | +5V |
| +3V3 | +3.3V / +3.3V | No;+3.3V and3V3 are different names | +3V3 |
| GND | GND / GND | Yes | GND |

Set VALUE at placement or in instance properties; with no override, the default supply pin name applies. Autodesk describes [value-based supply selection](https://forums.autodesk.com/t5/fusion-electronics-forum/override-supply-value/td-p/13963410) and the [override property](https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECD-PWR-SUPPLY-CMPNT-TSK.htm). Verify actual net NAME/label, including the plus sign. Instance reference NAME is not the supply net name. Recheck after library updates because Autodesk has documented a [supply-value display reset](https://forums.autodesk.com/t5/fusion-electronics-forum/power-supply-symbol-randomly-changes-back-to-original-library/td-p/14041127); the installed UI version was not tested here.

Assumptions: exact generic symbol artwork/body/3D differences are accepted under the supervisor's stated priorities; actual body envelopes govern layout. The F102 annotation makes its generic two-terminal symbol explicit. The original purchased parts and all original net assignments are preserved. Remaining physical checks concern actual fit/fabrication, not further library authoring or component downloads.
