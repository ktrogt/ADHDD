# Development demo scope — 2026-10-22

NOT A PRODUCTION LAYOUT. All footprints and board dimensions are provisional.
Source: 基板/parts.csv and 基板/netlist_expected.csv (read-only).
Scope: populate=yes; scaffold/DNP omitted. Reduced probes: TP460..TP463, TP466..TP468, TP471..TP474.
No component-internal continuity is assumed (including module GND pins).
SOT23-5 U207 uses a hypothetical grid adapter; J101 contact positions are placeholders;
JST 2.50/3.96 mm pitches are snapped and NOT a confirmed fit. D103 lead/hole fit is unverified.
This demo verifies tool connectivity, not this physical design's fitness or noise/thermal behaviour.

## Intentional netlist scope changes

- U201.GP17: MUX_S0 -> NC (removed scaffold)
- U201.GP18: MUX_S1 -> NC (removed scaffold)
- U201.GP26: VM_SENSE -> NC (removed scaffold)
- U201.GP27: I_SENSE -> NC (removed scaffold)
- U201.GP28: T_SENSE -> NC (removed scaffold)

Omitted refs: U401, C402, R403, C411, R411, C412, R412, J413, C421, R421, C422, R422, J423, C431, R431, C432, R432, J433, C441, R441, C442, R442, J443, C451, R451, R452, TP464, TP465
