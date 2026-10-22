# ADHDD perfboard layout rules — proposal 0.1 (2026-10-22)

## Schema contract for T6

`design_rules.json` is the authoritative rule list. Status is `proposed`; Claude must approve it before it becomes the candidate acceptance policy. It does not modify the approved netlist, parts, or specification. All distances introduced here are project engineering proposals, not manufacturer-specified hole counts.

Top-level fields: `schema_version`, `status`, `date`, `units`, `inputs`, `scope`, `groups`, `nodes`, `branch_catalog`, `board_policy`, `sources`, `rule_types`, `rules`, `current_budget`, `manual_checks`, `floor_plans`, `assumptions`, `open_questions`. A rule contains `id`, `type`, `params`, `severity` (`hard` or `soft`), `weight` (positive only for soft rules; zero for hard), `stage`, `priority`, `rationale`, `source` (source-ID list), and `basis` (`approved_requirement`, `derived_target`, or `mixed`). Hard means reject the candidate if violated; it does not mean a number is a manufacturer limit. Missing data or an unsupported hard rule must be reported `UNCHECKED`, never silently passed. A placement-only candidate is provisional until routing, assembly, and bench checks are complete.

Coordinates are top view, columns A..Z, AA.. and rows 1.., with 2.54 mm pitch. Internally use zero-based x/y; rotations are clockwise in the top view. A pin is `REF.pin_number`, using `基板/parts.csv` local numbers, not IC package numbers. `@name` resolves a group from `groups`; `$name` resolves a physical junction from `nodes`. A node must have one declared board coordinate and its stated anchor pin connected there; it does not create a new electrical net. Part substitutions need an explicit logical-pin mapping; never guess from physical pin order.

Generic params (no implicit defaults):

| Type | Required params and check |
|---|---|
| `connectivity` | `netlist`, `parts`, `scope_id`, `require_exact`, `nc_policy`; compare only the declared scope, including logical NC pins. |
| `near` | `pairs:[{a,b}]`, `max_holes`, `metric:"manhattan_pin"`; **placement** pin-to-pin distance. Does not prove the routed wire is short. |
| `max_branch_length` | `pairs:[{a,b}]`, `max_holes`, `include_offboard`; length of the actual declared branch between each pair, in grid pitches, including vertical/insulated detours. `net` may be supplied as a consistency check. |
| `min_part_distance` | `a`, `b` (part/group selectors), `min_holes`, `metric:"body_edge_euclidean"`, `exclude_same`; minimum planar distance between actual body/socket envelopes. Group against itself means unique pairs. |
| `keep_apart` | `a_nets`, `b_nets`, `b_parts`, `min_holes`, `metric:"planar_edge"`, `terminal_exceptions:[{pin,radius_holes}]`; minimum wire-surface to wire/body distance on **either** side. All A vs B combinations apply. Exceptions cover only the named pin's terminal escape disk, not the rest of its net. |
| `on_edge` | `parts`, `edges` (any of N/E/S/W), `max_holes`, `feature` (`mating_face` or `usb_mouth`); distance from that feature to an allowed physical board edge. |
| `star` | `net`, `root`, `branches:[{id,endpoints}]`, `shared_segment_policy`, `max_shared_holes`; declare branch paths. `none` allows only the root junction in common. `within_branch_only` allows a trunk inside one branch but not between branches. |
| `trunk_gauge` | `nets`, `branch_ids`, `design_current_A`, `min_copper_mm2`, `recommended`, `max_drop_V`, `drop_scope`; check the smallest conductor on every selected segment, including off-board harness where stated. Gauge numbers are recommendations; copper area is the acceptance value. Component leads/contacts are verified separately. |
| `orientation` | `parts`, `mode` (`same_rotation` or `feature_faces_edge`), `feature`, `allowed_degrees`, `allowed_edges`; unused arrays are explicitly empty. Uses footprint feature vectors, never an assumed rectangle centre. |
| `accessible` | `targets`, `feature`, `clearance_holes`, `approach` (`top`, `outward`, or `two_sides`), `include_wires`; reserve a prism or outward corridor around the named footprint feature. `two_sides` requires two opposite free grip sides. |
| `group` | `parts`, `max_span_holes`, `metric:"pin_bbox_max_dimension"`; bounding box of all pins in the group. |
| `order` | `sequence`, `axis` (`either`, `x`, or `y`), `allow_reverse`; monotonic placement of functional block/part pin centroids. Soft only; electrical order still comes from the netlist. |
| `max_jumpers` | `max_count`, `count_policy:"insulated_point_to_point"`, `exclude_offboard`; count each insulated point-to-point on-board wire once, including a whole top-side bus if electrically continuous. |
| `routing` | `check` plus the explicitly documented check-specific params in the rule; checks bare crossings/clearance, paired paths, bend counts, straight power segments, or assembly support. |
| `mounting` | `count`, `hole_diameter_mm_min`, `hole_diameter_mm_max`, `hardware_keepout_radius_mm`, `routing_keepout_radius_mm`, `min_centre_to_board_edge_mm`, `include_both_sides`; mounting geometry is physical, independent of the perfboard grid. |

Distance conversion is `holes × 2.54 mm`, with no rounding down. `planar_edge` subtracts conductor radii; footprint envelopes include adapters and sockets. Mechanical clearances include top-side wires and bottom solder joints. The `near` metric is a placement filter; its paired `max_branch_length` rule is the routing limit. A `max_branch_length` failure cannot be cured by a placement-distance pass. Board-external cable length is excluded unless `include_offboard:true`. A component electrically in series (e.g. D110) is not a copper branch; lengths are listed separately on either side.

Soft score: for numeric upper/lower bounds, `weight × max(0, violation / bound)` summed over atomic pairs, with `bound=1` for counts whose bound is zero. Boolean violations score `weight` each. For hard rules, report every violating atomic pair, then reject; do not trade correctness for soft score. Ranking is lexicographic: hard-check status, safety/robustness soft score, buildability soft score, occupied board area, then estimated cost. Each rule has a `priority` matching that order. Report `UNCHECKED` rules separately from violations. Manual/bench checks use explicit signed-off evidence in the candidate manifest.


## Implementation and interpretation notes

`all_populated` is the explicit 52-ref group. Part selectors accept a single ref/group string or an array; expand groups recursively. `trunk_gauge.nets` **and** `branch_ids` select segments by intersection, not union. The candidate must annotate power-trunk taps and branch membership according to `branch_catalog`; a shared segment always receives the higher current/area requirement. A parallel alternate path does not excuse an undersized common segment. A branch must have no unnecessary closed wire loop: shortest-path length alone would overlook a long parallel detour. Star evaluation removes the declared physical root and checks that distinct declared branches have no other common nodes or electrical connection. Internal sharing within a multi-endpoint branch is allowed, as explicitly stated for G01/G02. G01's POWER_RETURN can be a heavy trunk or independent channel spokes; LOGIC_RETURN remains separate up to the entry junction. All host ground branches remain the **same approved GND net**. Carrier internal ground connections are retained; this is no split of the DRV8874 IC grounds.

The module's own copper and component routing are outside host-board distance checks; required conversion-board conductors count in local bypass/UART lengths. Bottom/top height does not waive `keep_apart` projected separation. Only named terminal escape disks are exempt, and they allow the FAULT wire to leave its pin by the shortest route away from OUT; they do not permit a long parallel run. Bare-to-bare crossings of different nets are forbidden. An exceptional insulated crossing must be short and approximately perpendicular; it remains a spacing violation requiring explicit review if it is outside the declared exceptions.

For feature-based checks, the footprint/candidate needs a USB mouth and axis, BOOTSEL region, mating/latch envelope, grip sides, and probe approach. If T5 has not supplied a feature, measure it or mark that check `UNCHECKED`. Do not substitute the module centre or a connector's outer body edge for its mating face. The physical board outline and real M3 locations override the ideal outer-hole half-pitch approximation. Maximum-length rules use actual conductor length, including non-planar jumpers; they exclude off-board harnesses unless stated.

T6 initially exposed a flat v1 format with `error/warning/info` and eight rule types. During this parallel task it added `tools/t7_rules.py`, which reads this full proposal and reports unsupported requirements as `UNCHECKED`; that is the preferred entry point. Feature geometry, conductor branch membership/size/drop and assembly evidence still need explicit checking. `design_rules_t6_subset.json` is an additional, explicitly **incomplete** legacy projection for body distances, necessary same-net branch-length checks and the driver portion of the VREF star. Its `uncovered_rule_ids`, `partially_covered_rule_ids` and manual checks must be reviewed; a subset pass is never full approval. The full `design_rules.json` remains authoritative. No T6 files were edited by T7.

## Numeric-target policy and electrical basis

The specified circuit is frozen. The updated `BRIEF` records the user's single-sided-board preference, bottom grid-aligned tinned-wire style, no reserved scaffold area, and no enclosure/size limit. It supersedes the old PCB manufacturing instructions: no mandatory 100 × 100 mm outline, no fictitious perfboard ground plane, no optional DNP scaffold. T5 determines the actual standard board and adopted physical parts. These are proposal 0.1 constraints for candidate comparison, not an approved construction drawing.

Verified source guidance is qualitative: short local supply loops, substantial power conductors, quiet routing and thermal room. The concrete 2/3/4-hole gaps, 2/6-hole capacitor leads, 4-hole OUT length, 40-hole VREF length and 60-hole PWM ceiling are T7 engineering targets. They should be tightened after real candidate routing where possible. They are not electromagnetic-compatibility or thermal guarantees. In particular a 62.5 kHz PWM signal still has fast edges; carrier frequency alone does not justify long wiring. No equal-length PWM or VREF requirement is introduced.

Attach host VM to carrier **VIN pin 14**, not the unused carrier **VM pin 1**. Put the extra 100 nF first, directly across that channel's VIN14 and adjacent GND13; put its 470 µF beside the same pair. Keep OUT1/OUT2 as a paired local route to its connector. The carrier already implements the IC charge pump and IC ground-plane design; these rules do not propose reproducing that power stage on perfboard. [TI DRV8874](https://www.ti.com/lit/ds/symlink/drv8874.pdf), [Pololu #4035](https://www.pololu.com/product/4035).

The entry TVS and 470 µF remain on **switched VM**, after J104, as approved. “At entry” means physically grouped near the incoming supply and the switch header; moving them to VIN_RAW would change the circuit. The panel power-switch loop therefore belongs in the current/voltage-drop and wiring-inductance budget. The signal stop switch is a separate small-current harness; R214 stays on the board on its driver/SLEEP side.

Use one divider (R209/R210) and C211 at the central source. Four VREF wires start there; route each through the quiet interior and not along coil leads. The divider/filter return has its own local low-current branch. Connect the Pico ground socket pins and AGND33 into the local quiet network fed from the converter GND hub, with a dedicated link to input bulk negative. ADC_VREF35 stays NC; VREF here is the motor-current threshold and is not Pico ADC_VREF. Future ADC work should revisit grounding; no isolated analog-ground island is created. [Official pinout](https://datasheets.raspberrypi.com/pico/Pico-2-Pinout.pdf); the Pico datasheet pin/VSYS text was available only as primary-source search excerpts.

## Recommended floor plan and two alternatives

F1 is the first candidate to try. Treat all pictures below as block seeds, not hole coordinates or a fit claim. Begin with the roughly 155 × 115 mm board class mentioned previously; T5 may select another size. Mounting keepouts, plug envelopes, cap bodies and grip space must be present before any compaction.

```text
F1 — TOP VIEW; long edge north; not to scale
       coil4       coil3       coil2       coil1   (order is provisional)
  +----------------------------------------------------------+
  | entry    [driver+caps][driver+caps][driver+caps][driver+caps]|
  | J101     ========= paired VM / POWER GND trunk ===========|
  | F102 D103      logic-pin side / quiet signal corridor     |
  | J104    GND_ENTRY     central VREF divider + 220 nF        |
  |        5V regulator          stop / FAULT                 |
  |        + caps / D110         [Pico in sockets]            |
  |       power probes          [BOOTSEL clear]   CS local    |
  |                     SmartNet x2  USB  stop-header J213    |
  +----------------------------------------------------------+
                       south / cable access
```

The diode/PPTC spacing takes precedence over the compact drawing. Entry bulk/TVS attach at GND_ENTRY/VM_ENTRY; the drawing's trunk is a continuous heavy pair, while the converter/Pico return is a separate branch. Position each 470 µF and 100 nF beside that driver's VIN corner; never place them on top of a carrier or inside its grip zone. The central probe labels are VREF/SLEEP/FAULT; CS points sit individually by their carriers, not in a remote analogue bus. GP2–GP9 pin order may favour channel 1 at the opposite end of the row: retain the approved electrical assignments and label the physical order.

### F1 — Recommended: four channels along one long edge

Orientation: landscape; long edge is north; USB exits south.

| Functional block | Zone |
|---|---|
| entry | NW / west edge |
| regulator | west-middle / southwest, away from F102 and D103 |
| drivers | north band; identical rotation with OUT/VIN side facing north |
| coil_connectors | north edge, immediately outside each OUT pair |
| vref_parts | central quiet band just south of driver logic edges |
| stop_fault | central/south, near Pico GP14–GP16; J213 at south edge |
| U201 | lower centre; USB south, PWM side points toward driver routing corridor |
| smartnet | south edge beside Pico USB/UART end, separated from entry and coil exits |
| probes | power probes beside entry/converter; quiet probes beside Pico/divider; CS local to each channel |
| J104 | west edge at entry |

Reason: One repeatable channel row, one paired VM/GND trunk behind VIN corners, short output escape, and a quiet interior. VREF stars radiate from the centre. Choose left-to-right channel order after mapping actual Pico pin coordinates; fixed GP assignments must not change.

Check before adopting: Local bulk cans and M3 corners may widen channel pitch. A row plus edge-USB routing may miss soft PWM length targets. No board fit is claimed before T5/T6 placement.

### F2 — Alternative: 2 x 2 perimeter tiles, two north and two south

Orientation: landscape; all four carriers retain the same rotation with VIN/OUT column on east; connectors escape north/south.

| Functional block | Zone |
|---|---|
| entry | west-middle edge |
| drivers | two near north, two near south; central quiet corridor remains open |
| coil_connectors | north edge for top pair, south edge for bottom pair; each just outside its OUT corner |
| vref_parts | centre between four logic-side corners, outside output escape corridors |
| U201 | central east; USB east |
| smartnet | east edge beside Pico USB |
| regulator | west interior, away from D103/F102 |
| stop_fault | central quiet corridor; J213 east |
| J104 | west edge |
| probes | local to their respective blocks |

Reason: Short central control fanout and balanced VREF branches; two paired power spokes from entry serve north/south rows. Identical carrier rotation is retained, even though connector exit directions differ.

Check before adopting: Check the adopted connector envelopes carefully: both OUT-to-terminal branches still must be <=10.16 mm. A generic interior 2x2 with all coil connectors on one distant edge is ineligible. Corners, cans and USB can make the central corridor too small.

### F3 — Alternative: four vertical channels at the east edge

Orientation: portrait or landscape; original carrier top-view rotation with VIN/OUT on east.

| Functional block | Zone |
|---|---|
| entry | NE/east end of the power trunk, with F102 outside the carrier heat row |
| drivers | single N–S row along east edge |
| coil_connectors | east edge beside each OUT pair |
| vref_parts | middle of the board west of carrier logic pins |
| U201 | west side, USB north or south; PWM pins face the central quiet corridor where possible |
| smartnet | same quiet edge as Pico USB |
| regulator | NW, separated from the diode/PTC |
| stop_fault | near Pico GP14–GP16; J213 on quiet edge |
| J104 | entry edge |
| probes | local to their respective blocks |

Reason: Unrotated carrier labelling makes hand wiring easy; a straight N–S supply pair and local OUT exits remain possible.

Check before adopting: Four 17.8 mm bodies plus three 7.62 mm gaps already occupy about 94.06 mm before corner mounts and caps. Prefer a board whose long side is vertical; do not squeeze a 115 mm side if clearances fail.


## Current budget and conductor selection

Two operating scales must not be confused. The musical trial range is 50–200 mA **coil RMS**, with each HDD's sustained setting established by temperature tests. Sine peaks are √2 × RMS; 0.20 A RMS already needs 0.283 A peak and can clip at the initial nominal 0.27 A limit. An illustrative 5–37 Ω coil at 0.05–0.20 A RMS dissipates 0.0125–1.48 W. At about 11 V and allowing for driver loss/quiescent consumption this suggests roughly 5–150 mA average supply current per playing channel, but recirculation, waveform and real coil parameters matter. The 0.05–0.70 A musical whole-board estimate below is an allocation, **not a measured or guaranteed range**. [Spec 5.7](../HDD楽器_仕様書.md).

The wiring design envelope is much higher and may be sustained: four approximately 0.60 A coils, up to about 7 mA driver overhead each, and a 0.12 A converter input allocation give about 2.55 A, rounded to **2.6 A continuous**. With the initial 0.27 A limit, reserve **1.25 A** including overhead, instead of treating the spec's approximate 1.1 A as an exact total. A converter allocation of 0.20 A at 5 V gives 1 W; at 10.5 V and assumed 85% efficiency this is about 0.113 A including no-load consumption, rounded to 0.12 A. External Pico 3V3 logic is allocated 10 mA; this does not include RP2040's internal rail load. The 1 A regulator rating is not an external-load allocation.

“Peak” means repetitive motor/logic current when known. **Adapter startup peak, capacitor ripple current, PWM overshoot, and fault current are unbounded by this budget.** Five 470 µF capacitors alone total 2.35 mF; charging to 12 V requires about 28.2 mC and stores about 0.169 J, before other capacitors. Peak current depends on adapter impedance, leads, diode and PPTC. A hypothetical 1 ms charge would average about 28 A and a 10 ms charge about 2.8 A; these illustrate why 2.6 A must not be claimed as a startup ceiling. Measure with a current-limited supply and then the actual adapter. [TI bulk-capacitance guidance](https://www.ti.com/lit/ds/symlink/drv8874.pdf).

Conductor sizes below refer to copper, not insulation diameter or solder coating. Minimum main trunk is 0.50 mm² (0.8 mm solid, approximately AWG20); prefer **1.0 mm solid tinned copper** for straight power runs. Channel conductors: minimum **0.6 mm solid** (0.283 mm²), preferably AWG22 (about 0.326 mm²). Off-board wires are stranded and mechanically anchored. These sizes are engineering choices for this short board, not a general ampacity standard. Connector contacts, module sockets, adapter tails and switches need their own rating/temperature checks; do not cut down the original 1N5822 leads to force a fit.

The Alpha Wire 22 AWG example specifies 16.2 Ω/1000 ft at 20 °C, or 0.05315 Ω/m. For estimates use a rounded conservative 0.060 Ω/m for AWG22 and about 0.045 Ω/m for 0.50 mm² copper at warmer temperature; these are calculation allowances, not measured joints. At 2.6 A a 150 mm one-way 0.50 mm² run drops about 17.6 mV; two such runs drop 35.1 mV and dissipate about 91 mW total. At 0.61 A an AWG22 150 mm branch drops about 5.5 mV. Contacts and solder can dominate. Parallel thin wires are not the default substitute for one adequate trunk. [Alpha 3051](https://www.alphawire.com/products/wire/hook-up-wire/premium/3051), [conductor-size examples](https://www.alphawire.com/-/media/Project/AlphaWire/AlphaWire/Files/Brochures/AL_1998_HUWbro_web-12-2023.pdf?rev=79d6cabfc6834683a0ba2b57af729242).

Voltage-drop allowances are proposed acceptance budgets for **wiring and contacts**, except where a component drop is explicitly discussed. Do not count every row in series: the 12 V channel path uses the common series rows plus **one** channel feed/return. The sum is 0.13 V common positive (10+10+10+50+30+20 mV: last 20 mV is spare contact/joint margin), 0.03 V common GND (10+20 mV), and 0.04 V channel feed+return, totaling **0.20 V** from J101 to a driver and back. The external adapter cord precedes J101 and is measured separately. Coil cable has a separate **0.10 V loop** allowance. An AWG22 cable with 0.6 m of copper loop length drops about 21.6 mV at 0.6 A before contacts.

| Branch | Expected musical steady current | Continuous sizing / known repetitive peak | Conductor recommendation | Allowed wiring/contact drop |
|---|---|---|---|---|

| ENTRY_RAW: adapter centre/J101.1 → F102.1 | 0.05–0.7 A | 2.6 A / startup/fault unknown | Minimum 0.8 mm solid tinned copper / 0.50 mm2 / AWG20; prefer 1.0 mm solid; stranded AWG20 off-board | 0.01 V; wire/contact only; do not include component drops |
| ENTRY_FUSED: F102.2 → D103.2 (A) | 0.05–0.7 A | 2.6 A / startup/fault unknown | Minimum 0.8 mm solid tinned copper / 0.50 mm2 / AWG20; prefer 1.0 mm solid; stranded AWG20 off-board | 0.01 V; wire/contact only; do not include component drops |
| ENTRY_PROTECTED: D103.1 (K) → J104.1 | 0.05–0.7 A | 2.6 A / startup/fault unknown | Minimum 0.8 mm solid tinned copper / 0.50 mm2 / AWG20; prefer 1.0 mm solid; stranded AWG20 off-board | 0.01 V; wire/contact only; do not include component drops |
| POWER_SWITCH_HARNESS: J104.1 → panel power switch → J104.2 | 0.05–0.7 A | 2.6 A / startup/fault unknown | Minimum 0.8 mm solid tinned copper / 0.50 mm2 / AWG20; prefer 1.0 mm solid; stranded AWG20 off-board | 0.05 V; wire/contact only; do not include component drops |
| VM_TRUNK: J104.2 / C106.1 → furthest VM channel tap | 0.05–0.7 A | 2.6 A / startup/fault unknown | Minimum 0.8 mm solid tinned copper / 0.50 mm2 / AWG20; prefer 1.0 mm solid; stranded AWG20 off-board | 0.03 V; wire/contact only; do not include component drops |
| INPUT_RETURN: GND_ENTRY / C106.2 → J101.2 sleeve | 0.05–0.7 A | 2.6 A / startup/fault unknown | Minimum 0.8 mm solid tinned copper / 0.50 mm2 / AWG20; prefer 1.0 mm solid; stranded AWG20 off-board | 0.01 V; wire/contact only; do not include component drops |
| POWER_RETURN_TRUNK: furthest power-return tap → GND_ENTRY | 0.05–0.7 A | 2.6 A / startup/fault unknown | Minimum 0.8 mm solid tinned copper / 0.50 mm2 / AWG20; prefer 1.0 mm solid; stranded AWG20 off-board | 0.02 V; wire/contact only; do not include component drops |
| DRIVER_CH1_VM: VM trunk tap → U310.14 VIN | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way feed |
| DRIVER_CH1_GND: U310.13 and local U310.2/bulk/bypass negative → own power-trunk tap | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way return |
| DRIVER_CH1_OUT: U310.12/.11 OUT1/OUT2 → J313.1/.2 → HDD coil | 0.05–0.2 A_RMS | 0.6 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each on-board OUT conductor; cable loop separately <=0.10 V |
| DRIVER_CH2_VM: VM trunk tap → U320.14 VIN | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way feed |
| DRIVER_CH2_GND: U320.13 and local U320.2/bulk/bypass negative → own power-trunk tap | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way return |
| DRIVER_CH2_OUT: U320.12/.11 OUT1/OUT2 → J323.1/.2 → HDD coil | 0.05–0.2 A_RMS | 0.6 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each on-board OUT conductor; cable loop separately <=0.10 V |
| DRIVER_CH3_VM: VM trunk tap → U330.14 VIN | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way feed |
| DRIVER_CH3_GND: U330.13 and local U330.2/bulk/bypass negative → own power-trunk tap | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way return |
| DRIVER_CH3_OUT: U330.12/.11 OUT1/OUT2 → J333.1/.2 → HDD coil | 0.05–0.2 A_RMS | 0.6 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each on-board OUT conductor; cable loop separately <=0.10 V |
| DRIVER_CH4_VM: VM trunk tap → U340.14 VIN | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way feed |
| DRIVER_CH4_GND: U340.13 and local U340.2/bulk/bypass negative → own power-trunk tap | 0.005–0.15 A | 0.61 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each one-way return |
| DRIVER_CH4_OUT: U340.12/.11 OUT1/OUT2 → J343.1/.2 → HDD coil | 0.05–0.2 A_RMS | 0.6 A / 0.6 A | Minimum 0.6 mm solid / 0.283 mm2; prefer AWG22 / 0.326 mm2; stranded for cables | 0.02 V; each on-board OUT conductor; cable loop separately <=0.10 V |
| REGULATOR_VM: VM_ENTRY → U107.1; U107.2 → GND_ENTRY dedicated return | 0.025–0.06 A | 0.12 A / startup/fault unknown | 0.51 mm solid / AWG24 / about 0.20 mm2 | 0.03 V; feed plus dedicated return |
| PICO_5V: U107.3 +5V → D110 A2; D110 K1 → U201.39 VSYS; local quiet return | 0.05–0.1 A | 0.2 A / 0.2 A | 0.51 mm solid / AWG24 / about 0.20 mm2 | 0.05 V; feed plus quiet return, excluding D110 VF |
| LOGIC_3V3: U201.36 → receiver VCC, 4 PMODE pins, VREF divider and pull-ups; quiet returns | 0.0003–0.0025 A | 0.01 A / 0.01 A | 0.4 mm solid / 0.126 mm2 / AWG26 minimum; prefer 0.5 mm | 0.02 V; 3V3 external distribution plus its quiet return |
| VREF_RETURN: R210.2/C211.2 → GND_LOGIC | 5.8e-05–6.4e-05 A | 0.001 A / startup/fault unknown | 0.4–0.5 mm solid; mechanically secure | 0.001 V; DC divider-return wire only; driver-to-source ground difference separately measured |


**Ground row interpretation:** channel GND returns can carry large switching pulses even while average adapter current is small. Each carrier's two GND pins and local capacitors join locally, then return via its own tap/spoke on the heavy power branch. The quiet converter/Pico/divider branch joins only at entry. SmartNet GND belongs to the receiver/quiet network; never use the inter-instrument communication cable as the intended motor return. Probe grounds must distinguish power-entry and quiet ground during measurements; normal earth-referenced scope ground clips are all internally connected, so use a proper differential method to measure between two ground points without adding a new heavy return path.

**Component losses are additional:** using the 1N5822 0.525 V data-sheet point gives about 1.37 W at 2.6 A as a sizing estimate. The actual drop depends on temperature/current and the 3 A rating has specified lead-temperature conditions. MF-R300 initial 0.020–0.050 Ω gives about 0.052–0.130 V and 0.135–0.338 W at 2.6 A; its 0.080 Ω post-trip maximum gives 0.208 V / 0.541 W, not a prediction of hot operating resistance. Diode plus PPTC can heat the entry even when copper loss is small. At 40 °C the PPTC's 2.49 A hold is below the proposed 2.6 A load; spacing alone cannot make that operation valid. D110's forward drop is separate from the 50 mV 5 V wiring allowance; measure VSYS and keep it within 1.8–5.5 V. [Panjit diode](https://akizukidenshi.com/goodsaffix/1N5822.pdf), [Bourns MF-R](https://akizukidenshi.com/goodsaffix/mfr.pdf).

The 220 nF filter sees a divider Thévenin resistance of about 4.27 kΩ initially (47k || 4.7k), so a sound short return is more valuable than a very thick VREF wire. Initial reference is about 0.300 V and I_TRIP about 0.268 A using 450 µA/A × 2.49 kΩ; after 10k it is about 0.579 V / 0.517 A. A 10 mV unwanted reference/ground error shifts the trip by about 8.9 mA, or 3.3% of the initial setting. The 10 mV offset/ripple bench targets are engineering proposals. Test reference **at each driver's VREF relative to that driver's GND**, in addition to checking the divider source. A star by itself does not remove voltage drop in motor returns.

## Complete rule catalogue

Every numeric target below uses the schema's explicit units. `hard` means reject if violated, subject to Claude approval of this proposal. `soft Wn` gives its score weight. Source IDs link to the register; references to ENG mean the value itself is inferred. All routing geometry remains to be evaluated against real candidates.

### Connectivity

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| C01 / `connectivity` / **hard** | {"netlist":"基板/netlist_expected.csv","parts":"基板/parts.csv","scope_id":"main_minus_scaffold","require_exact":true,"nc_policy":"no_host_board_connection"} | A short/open, using carrier VM instead of VIN, or a bypassed isolation diode defeats the approved circuit. [BRIEF](#source-brief), [NET](#source-net); basis: approved_requirement. |
| C02 / `routing` / **hard** | {"check":"no_bare_crossings","nets":"all","same_net_junctions_must_be_declared":true,"through_hole_pad_connects_both_sides":true,"include_component_leads":true} | Every physical contact is an electrical junction; crossing layers at a plated pad can still short. [BRIEF](#source-brief), [ENG](#source-eng); basis: mixed. |
| C03 / `routing` / **hard** | {"check":"bare_clearance","nets":"all","min_surface_clearance_mm":0.5,"include_pads_leads_solder":true,"exclude_same_net":true} | A 0.5 mm physical margin allows for bent wire and solder spread at low voltage; it is a workmanship target. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |

### Mechanical access

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| M01 / `min_part_distance` / **hard** | all_populated ↔ all_populated; ≥0.4 holes / 1.016 mm body gap | Allow at least 1.016 mm between unrelated bodies/sockets; no stacking or hidden fouling. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| M02 / `mounting` / **hard** | {"count":4,"hole_diameter_mm_min":3.2,"hole_diameter_mm_max":3.5,"hardware_keepout_radius_mm":4.5,"routing_keepout_radius_mm":5.08,"min_centre_to_board_edge_mm":5.08,"include_both_sides":true} | Four M3 mounts need screw/washer/tool room and a copper-free margin; radii include holes, pads and bare wire. [SPEC](#source-spec), [ENG](#source-eng); basis: mixed. |
| M03 / `accessible` / **hard** | U201 usb_mouth; outward; 8 holes / 20.32 mm clearance; corridor width 12 mm | Reserve 20.32 mm outward cable/plug approach with at least 12 mm corridor width; actual plug may require more. [SPEC](#source-spec), [ENG](#source-eng); basis: mixed. |
| M04 / `accessible` / **hard** | U201 bootsel_button; top; 2 holes / 5.08 mm clearance; vertical 20 mm | BOOTSEL must be pressable with modules inserted; a 10.16 mm diameter free top approach is proposed. [SPEC](#source-spec), [ENG](#source-eng); basis: mixed. |
| M05 / `accessible` / **hard** | @socketed module_grip; two_sides; 2 holes / 5.08 mm clearance; vertical 25 mm | Socketed modules must lift out without bending nearby wires; reserve two opposite grip sides, with power removed. [BRIEF](#source-brief), [POLOLU](#source-pololu), [ENG](#source-eng); basis: mixed. |
| M06 / `accessible` / **hard** | J101, J202, J203, J104, J213, J313, J323, J333, J343 mating_and_latch; outward; 2 holes / 5.08 mm clearance; vertical 20 mm | Plugs, latch fingers and panel harnesses need a clear exit; include the actual T5 connector mating envelope. [BRIEF](#source-brief), [ENG](#source-eng); basis: mixed. |
| M07 / `on_edge` / **hard** | J101 mating_face ≤1 holes / 2.54 mm from one of N/E/S/W | Edge access keeps cable loads and connector manipulation outside the component field. [BRIEF](#source-brief), [ENG](#source-eng); basis: mixed. |
| M08 / `on_edge` / **hard** | J202, J203, J313, J323, J333, J343, J104, J213 mating_face ≤2 holes / 5.08 mm from one of N/E/S/W | Edge access keeps cable loads and connector manipulation outside the component field. [BRIEF](#source-brief), [ENG](#source-eng); basis: mixed. |
| M09 / `on_edge` / **hard** | U201 usb_mouth ≤2 holes / 5.08 mm from one of N/E/S/W | Keep the USB mouth within 5.08 mm of an edge while satisfying the full cable corridor. [SPEC](#source-spec), [ENG](#source-eng); basis: mixed. |
| M10 / `orientation` / **hard** | {"parts":["U201"],"mode":"feature_faces_edge","feature":"usb_axis","allowed_degrees":[0,90,180,270],"allowed_edges":["N","E","S","W"]} | USB must face the edge to which its unobstructed corridor exits. [SPEC](#source-spec), [ENG](#source-eng); basis: mixed. |
| M11 / `orientation` / **hard** | {"parts":["U310","U320","U330","U340"],"mode":"same_rotation","feature":"carrier_top_view","allowed_degrees":[0,90,180,270],"allowed_edges":[]} | Repeat identical socket/pin order on all four channels to reduce assembly mistakes; no mirrored carriers. [BRIEF](#source-brief), [NET](#source-net), [ENG](#source-eng); basis: mixed. |
| M12 / `accessible` / **hard** | @probe_required probe_tip; top; 1 holes / 2.54 mm clearance; vertical 20 mm | A probe must reach each labelled point without removing modules or contacting adjacent voltage nodes. [SPEC](#source-spec), [BRIEF](#source-brief), [ENG](#source-eng); basis: mixed. |
| M13 / `near` / **soft W3** | TP471.1 → U310.8; TP472.1 → U320.8; TP473.1 → U330.8; TP474.1 → U340.8; ≤3 holes / 7.62 mm Manhattan pin distance | Keep each CS probe local; the omitted ADC scaffold does not justify long floating analogue stubs. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |

### Thermal separation

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| H01 / `min_part_distance` / **hard** | @drivers ↔ @drivers; ≥3 holes / 7.62 mm body gap | At least 7.62 mm body-edge gap supports convection and module handling; verify temperature in the enclosure. [SPEC](#source-spec), [POLOLU](#source-pololu), [ENG](#source-eng); basis: derived_target. |
| H02 / `min_part_distance` / **soft W5** | @drivers ↔ @drivers; ≥4 holes / 10.16 mm body gap | Prefer 10.16 mm gaps where board area permits. [POLOLU](#source-pololu), [ENG](#source-eng); basis: derived_target. |
| H03 / `min_part_distance` / **hard** | D103 ↔ F102, C106, C108, C109, C311, C321, C331, C341; ≥4 holes / 10.16 mm body gap | Separate the roughly 1–1.4 W series diode from PPTC and electrolytic bodies by at least 10.16 mm. [SPEC](#source-spec), [DIODE](#source-diode), [BOURNS](#source-bourns), [ENG](#source-eng); basis: derived_target. |
| H04 / `min_part_distance` / **hard** | U107 ↔ F102; ≥3 holes / 7.62 mm body gap | Do not warm the temperature-sensitive PPTC with the switching regulator. [BOURNS](#source-bourns), [MINMAX](#source-minmax), [ENG](#source-eng); basis: derived_target. |
| H05 / `min_part_distance` / **hard** | @drivers ↔ F102; ≥4 holes / 10.16 mm body gap | Keep the PPTC outside the motor-driver heat zone. [BOURNS](#source-bourns), [POLOLU](#source-pololu), [ENG](#source-eng); basis: derived_target. |
| H06 / `min_part_distance` / **hard** | @drivers ↔ @electrolytics; ≥1 holes / 2.54 mm body gap | Leave at least 2.54 mm air gap; put local capacitors beside the VIN corner, not above a hot carrier. [SPEC](#source-spec), [POLOLU](#source-pololu), [ENG](#source-eng); basis: derived_target. |
| H07 / `min_part_distance` / **hard** | U107 ↔ C106, C108, C109; ≥1 holes / 2.54 mm body gap | Maintain a 2.54 mm body gap while keeping regulator capacitor leads short. [MINMAX](#source-minmax), [ENG](#source-eng); basis: derived_target. |

### Power entry and local loops

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| P01 / `near` / **hard** | D105.1 → J104.2; D105.2 → $GND_ENTRY; C106.1 → J104.2; J101.2 → $GND_ENTRY; ≤6 holes / 15.24 mm Manhattan pin distance | Keep the switched protection/bulk cluster physically at the supply entry; TVS remains on VM, after the panel switch. [SPEC](#source-spec), [NET](#source-net), [TVS](#source-tvs), [ENG](#source-eng); basis: derived_target. |
| P02 / `max_branch_length` / **hard** | D105.1 → $VM_ENTRY; D105.2 → $GND_ENTRY; ≤3 holes / 7.62 mm actual wire | Each TVS attachment is at most 7.62 mm of external conductor; long leads weaken the clamp through inductance. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [TVS](#source-tvs), [ENG](#source-eng); basis: derived_target. |
| P03 / `max_branch_length` / **hard** | J104.2 → $VM_ENTRY; J101.2 → $GND_ENTRY; ≤6 holes / 15.24 mm actual wire | Limit entry positive/return attachment to 15.24 mm each; no long spur from a distant trunk to the entry capacitor. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: derived_target. |
| P04 / `group` / **soft W3** | J101, F102, D103, J104, D105, C106; pin bounding-box maximum span ≤24 holes / 60.96 mm | Keep the entry circuitry in one 60.96 mm block without violating diode/PTC heat clearance. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| P05 / `near` / **hard** | C312.1 → U310.14; C312.2 → U310.13; C322.1 → U320.14; C322.2 → U320.13; C332.1 → U330.14; C332.2 → U330.13; C342.1 → U340.14; C342.2 → U340.13; ≤2 holes / 5.08 mm Manhattan pin distance | 100 nF terminals within 5.08 mm Manhattan distance of carrier VIN and adjacent power GND. [SPEC](#source-spec), [TI_DRV](#source-ti-drv), [POLOLU](#source-pololu), [ENG](#source-eng); basis: derived_target. |
| P06 / `max_branch_length` / **hard** | C312.1 → U310.14; C312.2 → U310.13; C322.1 → U320.14; C322.2 → U320.13; C332.1 → U330.14; C332.2 → U330.13; C342.1 → U340.14; C342.2 → U340.13; ≤2 holes / 5.08 mm actual wire | Limit each external 100 nF lead/wire path to 5.08 mm; the carrier already handles IC charge-pump bypassing. [SPEC](#source-spec), [TI_DRV](#source-ti-drv), [ENG](#source-eng); basis: derived_target. |
| P07 / `near` / **soft W8** | C312.1 → U310.14; C312.2 → U310.13; C322.1 → U320.14; C322.2 → U320.13; C332.1 → U330.14; C332.2 → U330.13; C342.1 → U340.14; C342.2 → U340.13; ≤1 holes / 2.54 mm Manhattan pin distance | Prefer directly adjacent holes (2.54 mm each external connection). [TI_DRV](#source-ti-drv), [ENG](#source-eng); basis: derived_target. |
| P08 / `near` / **hard** | C311.1 → U310.14; C311.2 → U310.13; C321.1 → U320.14; C321.2 → U320.13; C331.1 → U330.14; C331.2 → U330.13; C341.1 → U340.14; C341.2 → U340.13; ≤6 holes / 15.24 mm Manhattan pin distance | Keep both local 470 uF connections within 15.24 mm of VIN/GND; body clearance is evaluated separately. [SPEC](#source-spec), [TI_DRV](#source-ti-drv), [ENG](#source-eng); basis: derived_target. |
| P09 / `max_branch_length` / **hard** | C311.1 → U310.14; C311.2 → U310.13; C321.1 → U320.14; C321.2 → U320.13; C331.1 → U330.14; C331.2 → U330.13; C341.1 → U340.14; C341.2 → U340.13; ≤6 holes / 15.24 mm actual wire | Each bulk-capacitor connection is at most 15.24 mm and goes directly to its channel supply node. [SPEC](#source-spec), [TI_DRV](#source-ti-drv), [ENG](#source-eng); basis: derived_target. |
| P10 / `max_branch_length` / **soft W6** | C311.1 → U310.14; C311.2 → U310.13; C321.1 → U320.14; C321.2 → U320.13; C331.1 → U330.14; C331.2 → U330.13; C341.1 → U340.14; C341.2 → U340.13; ≤3 holes / 7.62 mm actual wire | Prefer 7.62 mm bulk connections when the can and grip clearances allow. [TI_DRV](#source-ti-drv), [ENG](#source-eng); basis: derived_target. |
| P11 / `near` / **hard** | U310.12 → J313.1; U310.11 → J313.2; U320.12 → J323.1; U320.11 → J323.2; U330.12 → J333.1; U330.11 → J333.2; U340.12 → J343.1; U340.11 → J343.2; ≤4 holes / 10.16 mm Manhattan pin distance | Each coil connector terminal is within 10.16 mm of its corresponding OUT pin. [SPEC](#source-spec), [TI_DRV](#source-ti-drv), [ENG](#source-eng); basis: derived_target. |
| P12 / `max_branch_length` / **hard** | U310.12 → J313.1; U310.11 → J313.2; U320.12 → J323.1; U320.11 → J323.2; U330.12 → J333.1; U330.11 → J333.2; U340.12 → J343.1; U340.11 → J343.2; ≤4 holes / 10.16 mm actual wire | Keep board-side OUT leads at most 10.16 mm each; output wiring stays at the perimeter. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [POLOLU_WIRE](#source-pololu-wire), [ENG](#source-eng); basis: derived_target. |
| P13 / `near` / **hard** | C108.1 → U107.1; C108.2 → U107.2; C109.1 → U107.3; C109.2 → U107.2; ≤4 holes / 10.16 mm Manhattan pin distance | Put the specified 100 uF input/output capacitors within 10.16 mm pin distance of the converter. [SPEC](#source-spec), [MINMAX](#source-minmax), [ENG](#source-eng); basis: derived_target. |
| P14 / `max_branch_length` / **hard** | C108.1 → U107.1; C108.2 → U107.2; C109.1 → U107.3; C109.2 → U107.2; ≤4 holes / 10.16 mm actual wire | Each converter capacitor attachment is at most 10.16 mm; this numeric limit is a perfboard proposal. [SPEC](#source-spec), [MINMAX](#source-minmax), [ENG](#source-eng); basis: derived_target. |
| P15 / `near` / **hard** | C208.1 → U207.5; C208.2 → U207.3; ≤2 holes / 5.08 mm Manhattan pin distance | Receiver bypass should be at its supply pins, including any SOT-23 adapter routing. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: derived_target. |
| P16 / `max_branch_length` / **hard** | C208.1 → U207.5; C208.2 → U207.3; ≤3 holes / 7.62 mm actual wire | Allow at most 7.62 mm including the SMD conversion board; use an adapter-local capacitor if necessary. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |

### Ground topology

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| G01 / `star` / **hard** | GND root $GND_ENTRY; POWER_RETURN: U310.13, U320.13, U330.13, U340.13, U310.2, U320.2, U330.2, U340.2, C311.2, C321.2, C331.2, C341.2, C312.2, C322.2, C332.2, C342.2; LOGIC_RETURN: $GND_LOGIC; TVS_RETURN: D105.2; INPUT_RETURN: J101.2; cross-branch shared conductor beyond root: 0 holes | Motor returns get their own heavy distribution branch; no driver return segment may lie in the converter/Pico/divider supply-return branch. [BRIEF](#source-brief), [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: mixed. |
| G02 / `star` / **hard** | GND root $GND_LOGIC; PICO_RETURN: U201.3, U201.8, U201.13, U201.18, U201.23, U201.28, U201.33, U201.38; VREF_RETURN: $VREF_GND, R210.2; RECEIVER_RETURN: U207.1, U207.3, C208.2, J202.2, J203.2; CONTROL_RETURN: R214.2; REGULATOR_CAP_RETURN: C108.2, C109.2; cross-branch shared conductor beyond root: 0 holes | Use a local low-current hub; connect AGND33 to this quiet Pico ground network, never use it as a motor-current return. [SPEC](#source-spec), [NET](#source-net), [PICO_PIN](#source-pico-pin), [PICO_DS](#source-pico-ds), [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: mixed. |
| G03 / `max_branch_length` / **hard** | U310.2 → U310.13; U320.2 → U320.13; U330.2 → U330.13; U340.2 → U340.13; ≤7 holes / 17.78 mm actual wire | Both carrier GND socket pins join locally in <=17.78 mm; never isolate the carrier signal GND from its power GND. [NET](#source-net), [TI_DRV](#source-ti-drv), [ENG](#source-eng); basis: derived_target. |

### VREF distribution

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| V01 / `star` / **hard** | VREF root $VREF_ROOT; VREF_CH1: U310.7; VREF_CH2: U320.7; VREF_CH3: U330.7; VREF_CH4: U340.7; VREF_SOURCE: R209.2, R210.1, TP466.1; cross-branch shared conductor beyond root: 0 holes | Four individual branches start at the divider/filter junction; a daisy chain makes later channels depend on earlier wiring joints. [SPEC](#source-spec), [BRIEF](#source-brief), [ENG](#source-eng); basis: approved_requirement. |
| V02 / `near` / **hard** | R209.2 → $VREF_ROOT; R210.1 → $VREF_ROOT; R210.2 → $VREF_GND; ≤2 holes / 5.08 mm Manhattan pin distance | The 220 nF filter and both divider junctions form one compact source; no ground detour through a channel. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |
| V03 / `max_branch_length` / **hard** | R209.2 → $VREF_ROOT; R210.1 → $VREF_ROOT; R210.2 → $VREF_GND; ≤2 holes / 5.08 mm actual wire | Limit each divider/filter junction attachment to 5.08 mm. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |
| V04 / `max_branch_length` / **hard** | $VREF_ROOT → U310.7; $VREF_ROOT → U320.7; $VREF_ROOT → U330.7; $VREF_ROOT → U340.7; ≤40 holes / 101.6 mm actual wire | A 101.6 mm absolute branch ceiling fits a central divider and avoids long high-impedance loops; it is not an EMI guarantee. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: derived_target. |
| V05 / `max_branch_length` / **soft W7** | $VREF_ROOT → U310.7; $VREF_ROOT → U320.7; $VREF_ROOT → U330.7; $VREF_ROOT → U340.7; ≤25 holes / 63.5 mm actual wire | Prefer branches <=63.5 mm; put the divider centrally behind the driver row. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |

### Control and communication

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| S01 / `keep_apart` / **hard** | VREF, SLEEP, FAULT, SN_BUS, SN_RX_IN, SN_PU, UART_RX, ARM, ARM_SW ↔ all OUT nets and coil connectors; ≥2 holes / 5.08 mm surface gap; exceptions: U310.9 escape ≤2 holes, U320.9 escape ≤2 holes, U330.9 escape ≤2 holes, U340.9 escape ≤2 holes | Keep sensitive/stop/receiver wires at least 5.08 mm from switched outputs and coil connector bodies; only the FAULT pin escape is exempt. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [POLOLU_WIRE](#source-pololu-wire), [ENG](#source-eng); basis: mixed. |
| S02 / `keep_apart` / **hard** | VREF ↔ all OUT nets and coil connectors; ≥3 holes / 7.62 mm surface gap; exceptions: none | Give the common current-limit reference at least 7.62 mm output separation with no long parallel run. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: mixed. |
| S03 / `keep_apart` / **soft W5** | VREF, SLEEP, FAULT, SN_BUS, SN_RX_IN, SN_PU, UART_RX, ARM, ARM_SW ↔ all OUT nets and coil connectors; ≥4 holes / 10.16 mm surface gap; exceptions: U310.9 escape ≤2 holes, U320.9 escape ≤2 holes, U330.9 escape ≤2 holes, U340.9 escape ≤2 holes | Prefer 10.16 mm between control wiring and OUT zones. [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: derived_target. |
| S04 / `max_branch_length` / **hard** | U201.4 → U310.3; U201.5 → U310.4; U201.6 → U320.3; U201.7 → U320.4; U201.9 → U330.3; U201.10 → U330.4; U201.11 → U340.3; U201.12 → U340.4; ≤60 holes / 152.4 mm actual wire | Cap each Pico GP2–GP9 PWM path at 152.4 mm on the chosen standard-size board; no external PWM harness. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [ENG](#source-eng); basis: derived_target. |
| S05 / `max_branch_length` / **soft W5** | U201.4 → U310.3; U201.5 → U310.4; U201.6 → U320.3; U201.7 → U320.4; U201.9 → U330.3; U201.10 → U330.4; U201.11 → U340.3; U201.12 → U340.4; ≤35 holes / 88.9 mm actual wire | Prefer PWM paths <=88.9 mm; match channel order to the physical Pico pin order. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |
| S06 / `max_branch_length` / **hard** | R214.1 → U201.21; R214.1 → U310.6; R214.1 → U320.6; R214.1 → U330.6; R214.1 → U340.6; R215.2 → U201.20; R215.2 → U310.9; R215.2 → U320.9; R215.2 → U330.9; R215.2 → U340.9; ≤80 holes / 203.2 mm actual wire | Bound on-board SLEEP/FAULT paths to 203.2 mm. No equal-length requirement; avoid perimeter detours. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |
| S07 / `near` / **hard** | R214.1 → J213.2; R215.2 → U201.20; ≤6 holes / 15.24 mm Manhattan pin distance | Put the external stop pull-down on the board at the bus origin; put FAULT pull-up near the Pico receiver. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |
| S08 / `max_branch_length` / **hard** | R214.1 → J213.2; ≤6 holes / 15.24 mm actual wire | The stop pull-down must remain on the driver side of an unplugged panel harness. [SPEC](#source-spec), [NET](#source-net), [ENG](#source-eng); basis: derived_target. |
| S09 / `near` / **hard** | J202.1 → J203.1; ≤6 holes / 15.24 mm Manhattan pin distance | Keep pass-through connectors together, before the receiver series resistor. [SPEC](#source-spec), [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| S10 / `near` / **hard** | J202.1 → R204.1; R204.2 → U207.2; ≤4 holes / 10.16 mm Manhattan pin distance | The series resistor and powered-off-tolerant receiver belong at the UART entry, not at the far end of a long bus stub. [SPEC](#source-spec), [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| S11 / `max_branch_length` / **hard** | J202.1 → R204.1; R204.2 → U207.2; ≤6 holes / 15.24 mm actual wire | Each UART receiver input attachment <=15.24 mm, including conversion-board conductors. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |
| S12 / `max_branch_length` / **hard** | U207.4 → U201.2; ≤40 holes / 101.6 mm actual wire | Keep buffered UART RX on-board and <=101.6 mm; route through the quiet corridor. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |
| S13 / `group` / **soft W4** | R204, R205, D206, U207, C208; pin bounding-box maximum span ≤12 holes / 30.48 mm | A <=30.48 mm receiver cluster remains easy to inspect and prevents a long unprotected stub. [SPEC](#source-spec), [ENG](#source-eng); basis: derived_target. |

### Conductor size and drop

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| W01 / `trunk_gauge` / **hard** | ENTRY_SERIES, POWER_SWITCH_HARNESS, VM_TRUNK; 2.6 A; copper ≥0.5 mm²; drop ≤0.13 V; Prefer solid tinned copper diameter 1.0 mm (0.785 mm2); minimum solid 0.8 mm (0.503 mm2) or insulated AWG20. Use stranded AWG20 for the panel harness. | Size every common supply conductor for 2.6 A continuously; the current is not restricted to a brief peak. [BRIEF](#source-brief), [SPEC](#source-spec), [ALPHA](#source-alpha), [ALPHA_SIZE](#source-alpha-size), [ENG](#source-eng); basis: mixed. |
| W02 / `trunk_gauge` / **hard** | INPUT_RETURN, POWER_RETURN_TRUNK; 2.6 A; copper ≥0.5 mm²; drop ≤0.03 V; Prefer diameter 1.0 mm tinned copper; minimum 0.8 mm or insulated AWG20. | The ground trunk has the same current duty as VM, including pulsed recirculation at local branches. [BRIEF](#source-brief), [SPEC](#source-spec), [ALPHA](#source-alpha), [ALPHA_SIZE](#source-alpha-size), [ENG](#source-eng); basis: mixed. |
| W03 / `trunk_gauge` / **hard** | DRIVER_CH1, DRIVER_CH2, DRIVER_CH3, DRIVER_CH4; 0.61 A; copper ≥0.28 mm²; drop ≤0.02 V; 0.6 mm solid tinned copper (0.283 mm2) minimum; prefer 0.64 mm / AWG22 (about 0.326 mm2). Coil cable AWG22 stranded, paired. | Each channel conductor must carry 0.6 A coil current plus driver overhead without relying on solder bridges. [BRIEF](#source-brief), [SPEC](#source-spec), [ALPHA](#source-alpha), [ALPHA_SIZE](#source-alpha-size), [ENG](#source-eng); basis: mixed. |
| W04 / `trunk_gauge` / **hard** | LOGIC_RETURN, REGULATOR_VM; 0.12 A; copper ≥0.2 mm²; drop ≤0.03 V; 0.51 mm / AWG24 copper or thicker; use a distinct pair to the entry. | Pico supply current is small but needs a dedicated return path isolated from motor trunk voltage drops. [BRIEF](#source-brief), [SPEC](#source-spec), [ALPHA](#source-alpha), [ALPHA_SIZE](#source-alpha-size), [ENG](#source-eng); basis: mixed. |
| W05 / `trunk_gauge` / **hard** | PICO_5V, PICO_RETURN; 0.2 A; copper ≥0.2 mm²; drop ≤0.05 V; 0.51 mm / AWG24 or thicker; keep D110 in series and pair with the quiet return. | Reserve 200 mA on the 5 V path; no optional pickup board or external 5 V load is included. [BRIEF](#source-brief), [SPEC](#source-spec), [ALPHA](#source-alpha), [ALPHA_SIZE](#source-alpha-size), [ENG](#source-eng); basis: mixed. |
| W06 / `trunk_gauge` / **hard** | LOGIC_3V3; 0.01 A; copper ≥0.12 mm²; drop ≤0.02 V; 0.4 mm solid tinned copper (0.126 mm2) or AWG26 minimum; 0.5 mm wire is easier to inspect. | The external 3V3 loads are small; reserve 10 mA including switching current and pull-ups. [BRIEF](#source-brief), [SPEC](#source-spec), [ALPHA](#source-alpha), [ALPHA_SIZE](#source-alpha-size), [ENG](#source-eng); basis: mixed. |
| W07 / `trunk_gauge` / **hard** | COIL_HARNESS; 0.6 A; copper ≥0.28 mm²; drop ≤0.1 V; AWG22 stranded copper pair; twist lightly and provide strain relief at the HDD fixed flex section. | External coil leads can dominate loop area and resistance; budget 100 mV for the cable and its contacts. [BRIEF](#source-brief), [SPEC](#source-spec), [ALPHA](#source-alpha), [ALPHA_SIZE](#source-alpha-size), [ENG](#source-eng); basis: mixed. |

### Hand construction and grouping

| ID / type / severity | Checkable target | Rationale and source |
|---|---|---|
| B01 / `routing` / **hard** | {"check":"paired_power_paths","pairs":[{"a":"VM","b":"GND","branch":"POWER_RETURN_TRUNK"},{"a":"VM","b":"GND","branch":"REGULATOR_VM"}],"max_centre_separation_holes":2,"preferred_surface":"bottom","terminal_escape_holes":3} | Run feed and its return alongside each other, <=5.08 mm centre separation outside terminal escapes. [SPEC](#source-spec), [TI_LAYOUT](#source-ti-layout), [POLOLU_WIRE](#source-pololu-wire), [ENG](#source-eng); basis: mixed. |
| B02 / `routing` / **hard** | {"check":"paired_outputs","channel_pairs":[{"a":"HDD1_OUT1","b":"HDD1_OUT2"},{"a":"HDD2_OUT1","b":"HDD2_OUT2"},{"a":"HDD3_OUT1","b":"HDD3_OUT2"},{"a":"HDD4_OUT1","b":"HDD4_OUT2"}],"max_centre_separation_holes":2,"terminal_escape_holes":3,"include_offboard":true} | Keep each bidirectional output pair together; the coil circuit is OUT1/OUT2, not OUT/GND. [NET](#source-net), [TI_LAYOUT](#source-ti-layout), [POLOLU_WIRE](#source-pololu-wire), [ENG](#source-eng); basis: mixed. |
| B03 / `routing` / **soft W6** | {"check":"straight_power_trunks","nets":["VM","GND"],"branch_ids":["VM_TRUNK","POWER_RETURN_TRUNK"],"max_bends_per_trunk":1,"preferred_surface":"bottom","material":"continuous_tinned_copper"} | Prefer one straight continuous underside run for each power trunk; avoid chains of tiny solder bridges. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B04 / `routing` / **soft W2** | {"check":"signal_bends","nets":["HDD1_IN1","HDD1_IN2","HDD2_IN1","HDD2_IN2","HDD3_IN1","HDD3_IN2","HDD4_IN1","HDD4_IN2","VREF","SLEEP","FAULT","SN_BUS","SN_RX_IN","SN_PU","UART_RX","ARM","ARM_SW"],"max_bends_per_branch":2,"preferred_surface":"bottom","preferred_material":"bare_tinned_wire_on_grid"} | Prefer simple grid-aligned bare signal runs; an insulated jumper is appropriate whenever a crossing is required. [BRIEF](#source-brief), [ADAFRUIT](#source-adafruit), [ENG](#source-eng); basis: derived_target. |
| B05 / `max_jumpers` / **soft W4** | {"max_count":24,"count_policy":"insulated_point_to_point","exclude_offboard":true} | Aim for <=24 insulated on-board wires, while allowing them whenever bare-wire safety or separation needs them. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B06 / `max_jumpers` / **soft W2** | {"max_count":16,"count_policy":"insulated_point_to_point","exclude_offboard":true} | A stretch target of <=16 may help compare otherwise equally safe candidates; it must not drive unsafe bare crossings. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B07 / `routing` / **hard** | {"check":"wire_support","nets":"all","max_unsupported_bare_span_holes":8,"allow_anchor_to_same_net_pad":true,"allow_nonconductive_support":true,"minimum_bottom_standoff_mm":10} | Support bare runs at least every 20.32 mm and keep the underside 10 mm above the mounting surface; inspect for flex shorts. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B08 / `order` / **soft W2** | {"sequence":["smartnet","U201","drivers","coil_connectors"],"axis":"either","allow_reverse":true} | Prefer visible input → control → drivers → edge outputs signal flow, allowing reverse/rotated floor plans. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B09 / `group` / **soft W3** | U310, C311, C312, J313, TP471; pin bounding-box maximum span ≤16 holes / 40.64 mm | Keep one channel in a <=40.64 mm tile for repeatable wiring and local probe access. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B10 / `group` / **soft W3** | U320, C321, C322, J323, TP472; pin bounding-box maximum span ≤16 holes / 40.64 mm | Keep one channel in a <=40.64 mm tile for repeatable wiring and local probe access. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B11 / `group` / **soft W3** | U330, C331, C332, J333, TP473; pin bounding-box maximum span ≤16 holes / 40.64 mm | Keep one channel in a <=40.64 mm tile for repeatable wiring and local probe access. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |
| B12 / `group` / **soft W3** | U340, C341, C342, J343, TP474; pin bounding-box maximum span ≤16 holes / 40.64 mm | Keep one channel in a <=40.64 mm tile for repeatable wiring and local probe access. [BRIEF](#source-brief), [ENG](#source-eng); basis: derived_target. |

## Assembly and bench evidence still required

These checks are part of acceptance but are not scored as automatic placement rules. Numeric targets introduced by T7 remain proposals.

| ID / stage | Required evidence | Rationale / sources |
|---|---|---|
| A00 / assembly / **hard** | Use the user-requested single-sided independent-pad board with bare wiring on the bottom. Do not reserve an area for omitted temperature/current/voltage scaffold. Use the real board pad connectivity and inspect jumpers at crossings. | The 2026-10-22 user answers added to BRIEF specify the construction method and no scaffold reservation. [BRIEF](#source-brief). |
| A01 / assembly / **hard** | Retain two sockets per Pico/carrier, components upward. Remove Pololu R2 and R4, retain R3; verify each module separately before insertion. Host-board carrier VM1 and IMODE10 remain NC. | An unmodified carrier can lift the common reference and defeat the intended current limit. [SPEC](#source-spec), [NET](#source-net), [POLOLU](#source-pololu). |
| A02 / assembly / **hard** | Actual J101, J104 contacts, panel power switch and harness must be rated >=3 A continuous at the intended ambient, with measured startup suitability. No solderless breadboard or unrated Dupont jumper in the common power path. | Wire size cannot compensate for an underspecified connector or contact. [BRIEF](#source-brief), [SPEC](#source-spec), [ENG](#source-eng). |
| A03 / assembly / **hard** | Use 35 V bulk/input electrolytics with polarity marked; do not add extra capacitors or change the approved nets. Total connected U107 output capacitance must remain <=470 uF, including downstream capacitance effective during startup. | Respect capacitor surge margin and converter startup capacitance limit. [SPEC](#source-spec), [MINMAX](#source-minmax), [TVS](#source-tvs). |
| A04 / assembly / **hard** | Respect T5 adapter/pin mappings and actual pad connectivity. Verify lead fit, solder area and strain relief; never force a 1.2–1.3 mm diode lead into a nominal 1 mm hole. Preserve NC holes on installed sockets. | Physical substitutions must not silently change electrical connectivity. [BRIEF](#source-brief), [NET](#source-net), [DIODE](#source-diode), [ENG](#source-eng). |
| A05 / assembly / **hard** | Label HDD1–4, OUT1/OUT2, VIN/GND, switch header net names, USB access, probe nets and module insertion orientation. Secure external cables independently of component leads; provide a clear gap above capacitor vents. | Hand-built transportable hardware needs inspectable orientation and mechanical support. [SPEC](#source-spec), [BRIEF](#source-brief), [ENG](#source-eng). |
| A06 / assembly / **hard** | Keep GP17, GP18, GP26–GP28 unconnected on the host board after scaffold removal. Keep U201.35 ADC_VREF and U201.40 VBUS NC; U201.33 AGND joins the local quiet GND network. | Leave the specified expansion pins free and preserve the approved power-ORing arrangement. [BRIEF](#source-brief), [NET](#source-net), [PICO_DS](#source-pico-ds). |
| A07 / assembly / **hard** | No bare live conductors, tall parts or extra wires above Pico/carriers; exclude only their required socket contacts. No component stacked over the diode or the converter. Insulate any intentional wire crossover fully and provide strain relief. | Heat escape, module removal and short inspection require accessible, unstacked construction. [BRIEF](#source-brief), [POLOLU](#source-pololu), [ENG](#source-eng). |
| T01 / bench / **hard** | Perform unpowered continuity/short checks, then regulator-only, Pico-only and one-carrier-at-a-time bring-up. Check +5V first; +3V3 is measurable only after Pico is inserted or USB-powered. | Avoid the literal v0.7 8.2 wording that asks to check 3V3 with Pico absent; 3V3 is generated on Pico. [SPEC](#source-spec), [NET](#source-net), [PICO_DS](#source-pico-ds). |
| T02 / bench / **hard** | At initial 4.7k divider setting, verify VREF approximately 0.30 V, unchanged by SLEEP, and approximately 0.27 A current limit in both directions on each carrier. Scope driver-local GND relative to VREF_GND and reference ripple. Proposed targets: |ground offset| <=10 mV and VREF ripple <=10 mV peak-to-peak; if exceeded, improve routing or obtain explicit review. | Low reference voltage makes millivolt-scale noise material. Geometric rules alone do not validate immunity. [SPEC](#source-spec), [TI_DRV](#source-ti-drv), [ENG](#source-eng). |
| T03 / bench / **hard** | Scope VM at the entry and furthest carrier and 3V3 during cold/hot repeated switching, four-channel playback and USB/adapter order tests. Measure charging current; verify no adapter hiccup or unwanted start and Pico VSYS always within 1.8–5.5 V. | The 2.35 mF bulk total has no bounded 2.6 A startup peak; TVS standoff and wiring inductance need a real supply test. [SPEC](#source-spec), [TI_DRV](#source-ti-drv), [TVS](#source-tvs), [PICO_DS](#source-pico-ds). |
| T04 / bench / **hard** | Log worst continuous current and enclosure air temperature at F102; at 40 C, 2.6 A exceeds MF-R300 2.49 A hold specification. Validate or derate operation; spacing is not a guarantee. Measure D103, PPTC, converter, carrier and coil temperatures until stable, at cold/hot startup and after transport. | The future 2.6 A operating allocation conflicts with the PPTC hold rating at 40 C; heat cannot be accepted from placement alone. [SPEC](#source-spec), [BOURNS](#source-bourns), [DIODE](#source-diode), [POLOLU](#source-pololu), [ENG](#source-eng). |
| T05 / bench / **hard** | With the real panel harness, confirm stop opening, re-closing without restart, watchdog, bad/lost UART and FAULT stop outputs in <=0.5 s. Observe IN/CS with a scope; retain GP16 as SLEEP sense. | The physical SLEEP bus and receiver must support the specified fail-safe tests, including noise near OUT wiring. [SPEC](#source-spec), [NET](#source-net). |
| T06 / bench / **hard** | At the worst approved load, measure common positive wire/contact drop <=0.13 V, common ground <=0.03 V and each selected driver feed/return <=0.02 V, so total J101-to-carrier supply loop wiring/contact loss <=0.20 V excluding F102/D103. Verify additional 5V and 3V3 branch budgets and cable-loop drop <=0.10 V. | Check actual joints and contacts, which ideal copper calculations omit. [SPEC](#source-spec), [ENG](#source-eng). |

## Assumptions and open questions

- Supervisor decision (Claude, 2026-10-22): proposal 0.1 is accepted as the rule basis for layout candidates. Claude may tighten individual numbers after reviewing real candidates. This approval supersedes the earlier pending-approval wording in this document; it does not change the circuit or approve a construction drawing.
- The updated BRIEF records the user preference: single-sided 2.54 mm isolated-pad board, mainly bottom-side tinned copper along the grid; insulated wires where crossings require them. Board outline, hole count, component envelopes and adapters come from T5. No standard board is declared to fit yet.
- Do not impose the obsolete 100 x 100 mm PCB quote limit. Start with the prior approximately 155 x 115 mm class, then optimise occupied area only after hard constraints pass.
- Only populated main-board parts and the practical probe set are required. The user explicitly requested no scaffold parts and no reserved scaffold area. TP464/TP465 may be retained as additional GND points; all other omissions are listed explicitly.
- Use the 4.7k lower divider resistor initially. Wire sizing reserves the later 10k / approximately 0.6 A-per-coil envelope, subject to temperature tests.
- Normal coil RMS 0.05–0.2 A is a trial range, not an approved sustained rating for any HDD; adapter current is neither coil RMS nor the sum of channel RMS.
- Peak charging and fault currents are unknown. Wire size is selected for low voltage drop and robust assembly, not certification to an installation wiring ampacity code.
- No extra capacitors on OUT, no IN-series resistors, no alternate buffer or connector electrical change, and no extra ground isolation is authorised by these rules.
- Signals may need insulated jumpers to satisfy the mandatory spacing and exact connectivity; jumper counts are soft targets.

Q1 resolved by Claude (2026-10-22): retain MF-R300 and the existing protection circuit. Initial operation uses the 4.7 kΩ VREF resistor (approximately 0.27 A per channel; approximately 1.25 A board budget), comfortably within the PPTC hold current. Moving to 10 kΩ (approximately 0.52 A per channel) is decided only after warm-condition measurements.

Operating note, not a layout rule: at ambient temperature ≥40 °C with all four channels at the 0.52 A ceiling, the polyfuse may trip. Claude accepts this as protective behaviour, not a design failure. The layout consequence is only to keep F102 away from D103, U107 and the carriers, as already required by H03–H05. No protection-circuit change or additional layout constraint is introduced; Q1 is closed.

Spec 8.2 also asks for a 3V3 check with Pico absent. This is physically unavailable in the current circuit; T01 records the operational correction (+5V before Pico, +3V3 after Pico) without editing the approved spec.

## Source register

Access date for web checks: **2026-10-22**. An opened manufacturer PDF hosted by Akizuki is treated as primary technical content. Search-excerpt-only Pico claims remain explicitly partial; do not promote them to full-document verification.

<a id="source-brief"></a>
- **BRIEF** — ADHDD perfboard BRIEF (`ユニバーサル基板/BRIEF.md`). Scope, priorities, shared conventions. Access: opened_local. Confidence: approved_task_input.
<a id="source-spec"></a>
- **SPEC** — HDD instrument specification v0.7 (`HDD楽器_仕様書.md`). 5.7; 6.1–6.9; 8.1–8.4. Access: opened_local. Confidence: approved_circuit_requirements; older PCB process superseded by BRIEF.
<a id="source-net"></a>
- **NET** — Approved logical parts and netlist (`基板/netlist_expected.csv`). original ref/pin_number columns. Access: opened_local. Confidence: approved_logical_connectivity; physical fit remains T5 scope.
<a id="source-ti-drv"></a>
- **TI_DRV** — [TI DRV8874 datasheet, SLVSF66A, Rev. A](https://www.ti.com/lit/ds/symlink/drv8874.pdf). 6.5 pp.5–7; 9.1 p.30; 10.1 p.31. Access: opened_primary. Confidence: verified_primary. Local bypass and bulk capacitors should be close; power conductors wide; IC grounds joined on the carrier. Bulk sizing needs system testing.
<a id="source-ti-layout"></a>
- **TI_LAYOUT** — [TI Best Practices for Board Layout of Motor Drivers, SLVA959B](https://www.ti.com/lit/an/slva959b/slva959b.pdf). 1.1 pp.3–4; 1.2.1–1.3 pp.5–7; 5 p.19; 6.3.2 pp.27–28. Access: opened_primary. Confidence: verified_primary. Shared impedance and nearby switching wires can disturb signals. Separate current paths and small high-current loops are useful.
<a id="source-pololu"></a>
- **POLOLU** — [Pololu #4035 DRV8874 carrier](https://www.pololu.com/product/4035). Using the motor driver; Pinout; Current limiting; Real-world power dissipation considerations. Access: opened_primary. Confidence: verified_primary. VIN is the recommended protected input; VM is downstream access. PWM adds heat; handling can burn. Carrier already contains the IC support components.
<a id="source-pololu-wire"></a>
- **POLOLU_WIRE** — [Pololu application note: Dealing with Motor Noise](https://www.pololu.com/docs/0J15/9). recommendations 2–4. Access: opened_primary. Confidence: verified_primary; wiring principle transferred from brushed motors to switched VCM wiring. Short paired/twisted motor leads, separation from signal wires, and local supply capacitance reduce interference. No capacitor across the VCM is proposed here.
<a id="source-minmax"></a>
- **MINMAX** — [MINMAX M78AR-1 datasheet, 2016-11-22 Rev.0](https://akizukidenshi.com/goodsaffix/m78ar-1.pdf). model table p.1; input notes and pin connections p.3; Technical Notes p.4. Access: opened_primary_manufacturer_pdf_on_store. Confidence: verified_primary. M78AR05-1: input 6.5–32 V, output 5 V/1 A, maximum output capacitance 470 uF. Input capacitor goes across input pins; ripple note places a low-ESR capacitor near the load. No numeric lead-distance limit is given.
<a id="source-pico-pin"></a>
- **PICO_PIN** — [Raspberry Pi Pico 1/Pico 2 official pinout](https://datasheets.raspberrypi.com/pico/Pico-2-Pinout.pdf). single-page pin drawing. Access: opened_primary; diagram cross-checked with indexed rendering and approved NET. Confidence: verified_primary_pin_labels.
<a id="source-pico-ds"></a>
- **PICO_DS** — [Raspberry Pi Pico datasheet](https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf). 2.1/2.2 pin descriptions pp.7–8; 4.5 Powering Pico p.20. Access: primary_search_excerpts_read; full PDF open failed (>10 MiB); direct download unavailable. Confidence: partial_primary_read_not_full_pdf. VSYS 1.8–5.5 V; external power via Schottky to VSYS allows USB power ORing. AGND is ADC reference ground; digital-ground connection is allowed when ADC performance is not critical. Recommended external 3V3 load below 300 mA.
<a id="source-bourns"></a>
- **BOURNS** — [Bourns MF-R PPTC datasheet, Rev.AG](https://akizukidenshi.com/goodsaffix/mfr.pdf). electrical table p.1; thermal derating p.3; trip curves p.4. Access: opened_primary_manufacturer_pdf_on_store. Confidence: verified_primary. MF-R300: 3 A hold at 23 C, 2.49 A at 40 C; initial resistance 0.020–0.050 ohm, post-trip R1 maximum 0.080 ohm. Trip is not instantaneous.
<a id="source-diode"></a>
- **DIODE** — [Panjit 1N5820–1N5822 datasheet, 2009-03-25](https://akizukidenshi.com/goodsaffix/1N5822.pdf). ratings/electrical characteristics p.1; derating and forward curves p.2. Access: opened_primary_manufacturer_pdf_on_store. Confidence: verified_primary. 1N5822: 3 A average under specified lead-temperature conditions; VF maximum 0.525 V at 3 A. Small perfboard solder pads do not reproduce the rating test conditions.
<a id="source-tvs"></a>
- **TVS** — [Panjit P4KE series datasheet, 2022-08-25 Rev.06](https://akizukidenshi.com/goodsaffix/P4KE.pdf). p.1 selection note; P4KE15A row p.2. Access: opened_primary_manufacturer_pdf_on_store. Confidence: verified_primary. P4KE15A: stand-off 12.8 V; breakdown 14.3–15.8 V; clamp 21.2 V at specified 20 A pulse. Wiring inductance can add overshoot.
<a id="source-alpha"></a>
- **ALPHA** — [Alpha Wire Premium 3051](https://www.alphawire.com/products/wire/hook-up-wire/premium/3051). Construction and Electrical Properties. Access: opened_primary. Confidence: verified_primary. 22 AWG tinned copper; nominal DCR 16.2 ohm/1000 ft at 20 C, equivalent to 0.05315 ohm/m. This is not an ampacity claim.
<a id="source-alpha-size"></a>
- **ALPHA_SIZE** — [Alpha Wire Hook-Up Wire Brochure, 2023](https://www.alphawire.com/-/media/Project/AlphaWire/AlphaWire/Files/Brochures/AL_1998_HUWbro_web-12-2023.pdf?rev=79d6cabfc6834683a0ba2b57af729242). 300 V PVC wire table p.5. Access: opened_primary. Confidence: verified_primary. Examples: 20 AWG about 0.51 mm2; solid 22 AWG 0.64 mm diameter / 0.32 mm2; solid 24 AWG 0.51 mm / 0.20 mm2. Stranded constructions differ.
<a id="source-adafruit"></a>
- **ADAFRUIT** — [Adafruit Pocket PiGRRL — Perma-Proto](https://learn.adafruit.com/pocket-pigrrl/perma-proto). Using Half-size Perma-Proto; planning and marking. Access: opened_primary. Confidence: verified_primary_example_not_ampacity_standard. Plan and mark a prototype board and its power rails. Perma-Proto has internally connected pads; the actual T5 board must have its own pad connectivity model.
<a id="source-eng"></a>
- **ENG** — T7 engineering proposals and calculations, 2026-10-22 (`ユニバーサル基板/design_rules.md`). Numeric-target policy, current budget, floor plans, and rule catalogue. Access: authored_analysis. Confidence: inferred_not_tested. All new clearances, wire areas, length limits, voltage-drop budgets, jumper counts, and floor-plan positions are proposed design targets requiring Claude review and physical verification.

## Validation and handoff

JSON parses; 79 unique rules (61 hard / 18 soft), 14 separate hard evidence checks, 23 current rows, and 52 required refs. All 141 explicit near/branch endpoint pairs were checked against approved pin numbers and same-net membership. Rule-specific required params, source IDs, star endpoint nets and branch IDs were validated. Approved parts/netlist/BRIEF hashes are in JSON; their contents were not edited.

| Type | Hard | Soft | Total |
|---|---:|---:|---:|
| `accessible` | 5 | 0 | 5 |
| `connectivity` | 1 | 0 | 1 |
| `group` | 0 | 6 | 6 |
| `keep_apart` | 2 | 1 | 3 |
| `max_branch_length` | 15 | 3 | 18 |
| `max_jumpers` | 0 | 2 | 2 |
| `min_part_distance` | 7 | 1 | 8 |
| `mounting` | 1 | 0 | 1 |
| `near` | 10 | 2 | 12 |
| `on_edge` | 3 | 0 | 3 |
| `order` | 0 | 1 | 1 |
| `orientation` | 2 | 0 | 2 |
| `routing` | 5 | 2 | 7 |
| `star` | 3 | 0 | 3 |
| `trunk_gauge` | 7 | 0 | 7 |

Read-only integration smoke check: T6 loaded/evaluated the full 79-rule policy and the 96-rule legacy subset against its development demo without input/schema exceptions. The full-policy placement check returned 37 UNCHECKED and 74 FAIL issue records; the legacy subset returned 63 placement violations. These are expected to be unresolved on that demo, which is not a compliant candidate. No T6 files or demo wiring were changed. This smoke check proves input compatibility only, not layout approval.

No candidate placement, physical board fit, electrical waveform or thermal test was performed by T7. Remaining actions: Claude approves/adjusts targets and Q1; T5 supplies adopted board/footprints/features; T6 evaluates full constraints or exposes every unsupported check; candidate agents generate F1/F2/F3 variants; assembly/bench evidence closes the remaining checks.
