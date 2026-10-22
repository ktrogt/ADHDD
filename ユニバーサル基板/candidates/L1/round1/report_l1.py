"""Human handoff and support-site estimates; all outputs stay in L1."""
from build import *
from model import path_points
from collections import Counter
import hashlib

def main():
    p=Project(HERE);out=HERE/'out'
    m=json.loads((out/'metrics.json').read_text(encoding='utf8'))
    x=json.loads((out/'metrics_extra.json').read_text(encoding='utf8'))
    r=json.loads((out/'report.json').read_text(encoding='utf8'))
    # Ends, bends, and <=8-hole intervals are explicit underside support sites.
    sites={z.xy for z in p.pins.values()}|set(p.reserved_pads);supportrows=[]
    for c in p.conductors:
        if c['kind']=='jumper':sites.update(c['contacts']);continue
        full=c['contacts'];idx={0,len(full)-1}|set(range(0,len(full),8))
        for q in c['xy']:idx.add(full.index(q))
        chosen=[full[i] for i in sorted(idx)];sites.update(chosen)
        supportrows.append({'wire_id':c['id'],'net':c['net'],'support_holes':' '.join(hole(q) for q in chosen),'max_interval_holes':max(b-a for a,b in zip(sorted(idx),sorted(idx)[1:]))})
    with (out/'wire_support.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['wire_id','net','support_holes','max_interval_holes']);writer.writeheader();writer.writerows(supportrows)
    x['solder_sites_with_end_bend_8hole_support_plan']=len(sites)
    x['supports_are_planned_not_physically_verified']=True
    save_json(out/'metrics_extra.json',x)
    qc=json.loads((out/'render_qc.json').read_text(encoding='utf8'))
    qc.update(status='VISUALLY INSPECTED: top, bottom, overlay',notes=[
        'Opened actual SVG XML and rasterized it locally without network access; inspected all three resulting PNGs.',
        'Shifted bulk/input/output capacitor, diode, converter and XH labels off their own pins; centre NC crosses remain visible.',
        'Bottom is mirrored BC..A; IDs stay readable and coordinates in CSVs remain TOP.',
        'Dense insulated routes in the central band remain a 3D assembly risk; SVG is a projection, not a stack-height proof.',
        'The conservative-grid C311 spill is deliberately visible, not clipped or hidden.'
    ],svg_SHA256={name:hashlib.sha256((out/(name+'.svg')).read_bytes()).hexdigest() for name in ['top','bottom','overlay']})
    save_json(out/'render_qc.json',qc)
    header=(out/'verify.log').read_text(encoding='utf8').splitlines()[0]
    gauge_rows='\n'.join('| '+k+' | '+f'{v.get("bare",0):.3f}'+' | '+f'{v.get("jumper",0):.3f}'+' |' for k,v in x['wire_by_gauge_mm'].items())
    vref=', '.join(f"CH{z['channel']} {z['mm']:.3f}" for z in x['VREF_branches'])
    vm=', '.join(f"{z['VM_from_J104_mm']:.2f}" for z in x['power_paths'])
    g13=', '.join(f"{z['GND13_from_J101_mm']:.2f}" for z in x['power_paths'])
    g2=', '.join(f"{z['GND2_from_J101_mm']:.2f}" for z in x['power_paths'])
    summary=f'''# L1 — F1 evaluation candidate (2026-10-22)

**LVS PASS; hard-rule acceptance FAIL. Not released for construction.** The approved envelopes and hard proximity targets are mutually incompatible. No rule or shared input was changed. See [blocking constraints](blocking_constraints.md) and the executable [reproduction](prove_constraints.py).

| Metric | Final result |
|---|---|
| Parts / logical pins / nets / NC | 54 / 186 / 42 / 22; exact approved CSV copy |
| LVS | PASS; no shorts, opens, NC wiring, floating conductors, or wire-graph cycles |
| Hard T7 rules | **27 PASS / 9 FAIL / 25 UNCHECKED** (61 total) |
| Additional core DRC | 1 BODY_OFFBOARD: C311, conservative grid envelope; nominal actual-board fit passes |
| Soft T7 rules | 9 PASS / 6 FAIL / 3 UNCHECKED |
| T7 weighted soft score, evaluated lower bound | **{x['T7_soft_score_evaluated_lower_bound']:.6f}**; priority 2 = {x['T7_soft_by_priority']['2']:.6f}, priority 3 = {x['T7_soft_by_priority']['3']:.6f} |
| Shared tool generic score | **{m['score']:,.3f}**; includes error/unchecked/provisional penalties |
| Insulated jumpers / bridges | **39 / 0**, all underside |
| Bare pieces / straight bare segments / bends | **86 / 173 / 87**; jumper bends 0 |
| Wire length | **{m['total_wire_mm']:.3f} mm** = bare {m['wire_length_mm']['bare']:.3f} + insulated {m['wire_length_mm']['jumper']:.3f} |
| Longest IN line | HDD1_IN1, **89.803 mm** (hard 152.4 mm passes; soft 88.9 mm slightly exceeded) |
| VREF root → driver, mm | {vref} |
| J104 VM → VIN, CH1–4, mm | {vm} |
| J101 GND → driver GND13, CH1–4, mm | {g13} |
| J101 GND → driver GND2, CH1–4, mm | {g2} |
| Used bbox, grid-origin mm | (-2.760, 1.680)–(137.160, 99.920): **139.920 × 98.240 mm**, {m['used_bbox_area_mm2']:.3f} mm² |
| Nominal actual board | 155 × 114 mm; body bbox (6.160, 9.150)–(145.110, 107.390) mm; origin remains derived |
| Build effort | **125 wire pieces**, 250 wire-end terminations + 193 component/adapter tails; {len(sites)} distinct solder sites with end/bend/8-hole supports; 863 if every modeled contact land is soldered |
| Continuity export | 1534 bare-board tests; modules/components absent and capacitors discharged |

Wire stock lengths exclude cut/strip allowance:

| Copper / gauge | Bare mm | Insulated mm |
|---|---:|---:|
{gauge_rows}

The shared T7 file contains no top-level tool `weights`; consequently `metrics.score` uses the CLI defaults. The separate T7 score above sums the CLI's weighted atomic soft findings. It is a **lower bound**, because three soft checks remain unimplemented; it must not be presented as a complete passing T7 ranking. Inputs and SHA256 hashes are recorded in `out/metrics_extra.json`.

## Floor plan and assumptions

CH1–4 run left to right along the north edge, all carriers at 270°. Every channel repeats its VIN/bulk/ceramic/OUT/CS pattern; coil XH3 centre pins remain unconnected. A continuous 1.0 mm VM trunk at row 8 and power-GND trunk at row 10 each has one bend and 2-hole separation. Channel bare branches are 0.6 mm; insulated channel returns are AWG22. Entry is west, converter southwest, Pico lower centre with USB south, SmartNet southeast, VREF centrally at AC16. Stop J213 is on the east edge; FAULT pull-up is beside Pico GP15. All 13 probes are populated.

GND_ENTRY, GND_LOGIC and VREF_ROOT are explicit physical junctions. **G01, G02 and V01 star checks PASS.** Separate paired AWG24 links feed/return the converter from entry; the quiet network does not return through the motor trunk. No parts or top-side jumpers cover modules. Off-board harnesses are not included in the CSV netlist model.

F1 deviations: entry is west-middle rather than NW because four full-width thermal channel tiles occupy the north band; stop is east rather than south to stay near its pull-down; channel pitch is 14 holes to retain carrier-to-can thermal clearance. C311 extends 1.49 mm beyond the tool's fictitious half-pitch edge, while remaining 6.16 mm inside the nominal real board. No electrical substitution beyond the approved T5 inputs was introduced.

## Trade-offs, risks and verification

The 39 insulated wires preserve the strict stars and cross the two power trunks and interleaved module/Pico pins. Bare wiring is 59.7% of total length and 68.8% of pieces. Long PWM jumpers, the central diagonal bundle and the weakly checked mechanical features make this an evaluation candidate, not a demonstrated optimum. The local search tested 100 orders in the final routing configuration (seed 38 selected), after earlier topology experiments; redundant overlaps and four pieces were removed without changing LVS or hard-rule statuses.

Provisional fit, solder surface clearance, connector/USB/grip access, off-board gauge/drop, thermal performance and 3D stacking remain unverified. The actual board mounting centres are 5.00 mm from edges versus M02's 5.08 mm target. Approved AWG26 precrimp coil leads conflict with W07's 0.28 mm² target. These need supervisor resolution. Wirelist endpoints are solder nodes: lay heavy wires against underside pads/tails; do not force multiple leads through a 1 mm hole. Use the planned <=8-hole supports and >=10 mm underside standoffs, then inspect flex/transport shorts. Estimated assembly and inspection: **6–10 hours**, engineering estimate excluding HDD/panel harness work.

Shared tool output (full log: `out/verify.log`):

```text
{header}
ERROR BODY_OFFBOARD: C311
ERROR RULE:P02: D105.1 -> $VM_ENTRY: 5.000 holes (max 3)
ERROR RULE:P05: C312.1 / U310.14: 3 holes > 2
ERROR RULE:P13: C108.1 / U107.1: 6 holes > 4
ERROR RULE:P15: C208.1 / U207.5: 4 holes > 2
ERROR RULE:V02: R210.1 / $VREF_ROOT: 3 holes > 2
WIRE LIST: 125 steps
CONTINUITY: 1534 tests (bare board, power off)
```

All three SVGs were parsed, locally rasterized and visually inspected. Ref labels were shifted off their own pads, polarity and XH centre NC marks; the bottom view is mirrored BC→A. See `out/render_qc.json`. No shared files, other candidate folders, purchases, uploads or public writes were made.
'''
    (HERE/'summary.md').write_text(summary,encoding='utf8')
    blocking='''# L1 blocking constraints — no relaxation applied

2026-10-22. These are conflicts between approved geometric inputs, not proposed circuit changes. Canonical `verify` remains FAIL. Re-run `prove_constraints.py` using the prescribed Python; it reads shared inputs and writes only L1/constraint_reproduction.json.

| Hard requirement | Reproduction / candidate | Smallest relevant adjustment for this build (pending Claude) |
|---|---|---|
| P05/P06 ceramic <=2 holes; M01 bodies >=0.4 hole; P11/P12 coil <=4 holes | At carrier rotation 270°, only one ceramic placement satisfies P05+M01, and only three connector placements satisfy P11+M01. None coexist at M01 clearance, even before adding the bulk can. | Ceramic placement and route bounds **3 holes**; keep coil <=4 and body clearance unchanged. |
| P13/P14 DC-DC caps <=4 holes; H07 can-to-converter >=1 hole | For either cap, no origin/rotation satisfies the adopted 18.42×16.10 mm converter envelope and H07 at P13=4 or 5. | Both cap placement/route bounds **6 holes**, or supervisor-corrected verified converter envelope. |
| P15 buffer bypass <=2 holes; M01 >=0.4 hole | No bypass placement works at 2 or 3; the DIP6 carrier envelope is 11×8 mm. | P15 **4 holes**, P16 **4 holes** (currently 3), or approved carrier/decoupling geometry correction. |
| V02/V03 R210/filter junction <=2 holes; M01 >=0.4 hole | A 3-hole resistor and 2-hole capacitor have no nonoverlapping two-end placement at bound 2. | Bound **3 holes for the offending R210 endpoint only**; other source/return links stay <=2. |
| P02 TVS-to-bulk shortest route <=3 holes; M01 >=0.4 hole | No solution even with diagonal insulated wires: the best possible Euclidean worst endpoint is sqrt(17)=4.123 holes. Minimum feasible Manhattan bound is 5. | Both routes **5 holes** for the all-bare candidate, or approved TVS/bulk lead-envelope correction. |
| Conservative board-edge model | Four identical thermal channel tiles need 14-hole pitch. Integer origins require first carrier x>=6 and final x<=47 under the model, but 6+3×14=48. Candidate starts x=5; C311 spills 1.49 mm beyond the fictitious edge. All pins remain valid; nominal real-board body clearance is positive. | Teach tooling the actual 155×114 mm outline / derived grid origin, then re-audit mounting, access and mechanical tolerance. Do not silently enlarge copied board.json. |
| M02 mounting centres >=5.08 mm from real board edge | Approved board drawing gives **5.00 mm**, independent of placement. | Accept the board's **5.00 mm nominal** or select a different board through the supervisor. |
| W07 coil harness copper >=0.28 mm² | Approved parts-fit record specifies AWG26 precrimp131312, approximately 0.129 mm². Harness is outside this layout model. | Supervisor reconciles the approved cable choice with W07; no different cable purchased/assumed. |

The first five geometric reproductions exhaust all four rotations and all integer origins in [-12,12]². Near limits bound every relevant first-pin origin inside this domain. The ceramic/coil coupling is tested at the F1 270° carrier orientation. The converter/buffer/divider/TVS conflicts are independent of translating or rotating the complete block, so moving them elsewhere on the board cannot solve them.

Tool limitations retained honestly:

- Full audit: 27 hard PASS, 9 hard FAIL, 25 hard UNCHECKED. Unsupported feature access, pad/lead/solder surface clearances, branch current/drop, off-board harnesses, supports and bench evidence cannot be made PASS by placement alone.
- C01 always reports scope provenance UNCHECKED; L1's netlist.csv is byte-identical to approved netlist_ub.csv, and its SHA256 is in metrics_extra.json.
- The CLI's default numerical score is not the T7 weighted/lexicographic score. T7 atomic penalties are exported separately, with unresolved soft checks explicitly excluded from its lower bound.
- The shared router rejects any BODY_OFFBOARD and does not preserve hierarchical GND/VREF stars. `route_l1.py` reuses its A* locally with separate branch occupancy; canonical verify remains authoritative and unmodified. `finish.py` removes duplicate/collinear wire pieces, invokes the prescribed CLI and moves SVG text only.

No source hashes, footprint envelopes, net assignments or hard rules were altered to hide these conditions. Claude must decide between corrected verified footprints, explicit numeric rule revisions, or a different board. Re-run all audits after any approved change.
'''
    (HERE/'blocking_constraints.md').write_text(blocking,encoding='utf8')
    print('summary and blockers written; support-plan sites',len(sites))

if __name__=='__main__':main()
