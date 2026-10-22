"""Round-2 handoff, assembly support sites and final artifact integrity checks."""
from common import *
from verify import verify
from collections import Counter
import hashlib,xml.etree.ElementTree as ET

def main():
 out=HERE/'out';p=project();r=json.loads((out/'report.json').read_text(encoding='utf8'));m=r['metrics'];x=json.loads((out/'metrics_extra.json').read_text(encoding='utf8'))
 fresh=verify(p)
 assert fresh['metrics']==m and m['comparison_tuple'][:3]==[True,0,0] and m['ranking_pass']
 assert not x['wire_graph_cycle_ranks_nonzero']
 sites={q.xy for q in p.pins.values()}|set(p.reserved_pads);support=[]
 for c in p.conductors:
  if c['kind']=='jumper':sites.update(c['contacts']);continue
  pts=c['contacts'];idx={0,len(pts)-1}|set(range(0,len(pts),8))
  idx.update(pts.index(z) for z in c['xy']);indices=sorted(idx);nodes=[pts[i] for i in indices];sites.update(nodes)
  support.append({'wire_id':c['id'],'net':c['net'],'support_holes':' '.join(hole(z) for z in nodes),'max_interval_holes':max(b-a for a,b in zip(indices,indices[1:]))})
 def csvout(name,fields,rows):
  with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 csvout('wire_support.csv',['wire_id','net','support_holes','max_interval_holes'],support)
 severity={q['id']:q['severity'] for q in p.rules['rules']}
 csvout('rule_audit.csv',['id','severity','type','status','findings','fail_findings','unchecked_findings'],[{**z,'severity':severity[z['id']]} for z in r['rule_checks']])
 csvout('pinmap.csv',['ref','number','name','net','hole'],[{'ref':q.ref,'number':q.number,'name':q.name,'net':q.net,'hole':hole(q.xy)} for q in sorted(p.pins.values(),key=lambda q:(q.ref,int(q.number)))])
 x.update(solder_sites_with_end_bend_8hole_support_plan=len(sites),supports_are_planned_not_physically_verified=True,
          comparison_tuple=m['comparison_tuple'],T7_soft_penalty=m['t7_soft_penalty'],T7_soft_penalty_complete=m['soft_penalty_complete'])
 save_json(out/'metrics_extra.json',x)
 def line(values):return ', '.join(f'{v:.3f}' for v in values)
 gauge='\n'.join(f"| {k} | {v.get('bare',0):.3f} | {v.get('jumper',0):.3f} |" for k,v in x['wire_by_gauge_mm'].items())
 vm=line(z['VM_from_J104_mm'] for z in x['power_paths']);g13=line(z['GND13_from_J101_mm'] for z in x['power_paths']);g2=line(z['GND2_from_J101_mm'] for z in x['power_paths'])
 vref=line(z['mm'] for z in x['VREF_branches']);bbox=m['bbox_mm'];width=bbox[2]-bbox[0];height=bbox[3]-bbox[1]
 unchecked=', '.join(z['id'] for z in m['unchecked_hard_rules']);tupletext=json.dumps(m['comparison_tuple'])
 summary=f'''# L1 round 2 — F1, approved rules v0.2

**LVS PASS; core DRC 0; hard FAIL IDs `[]`; ranking_pass true.** There are **{m['jumpers']} insulated jumpers**, versus 39 in round 1. The target <=16 was **not reached**; this is the best candidate found, not a proof of minimum wiring. Round-1 files are retained unchanged under `round1/`.

| Metric | Final result |
|---|---|
| Comparison tuple | **`{tupletext}`** |
| Tuple order | LVS ok, core DRC errors, hard FAIL IDs count, jumpers, T7 soft penalty, bends, wire mm |
| Scope | 54 refs, 186/186 pins, 42 nets, 22 NC; approved CSV byte-identical |
| Hard audit | **38 PASS / 0 FAIL / 23 UNCHECKED** |
| Star rules | G01 / G02 / V01 all PASS |
| Soft penalty | **{m['t7_soft_penalty']:.6f}**, evaluated portion; B03/B04/S03 remain incomplete |
| Wire pieces | **{m['conductors']}** = {x['bare_pieces']} bare + {m['jumpers']} insulated; no solder bridges |
| Bare straight segments / bends | {x['bare_straight_segments']} / {x['bare_bends']}; native total bends {m['bends']} |
| Total length | **{m['total_wire_mm']:.3f} mm** = {m['wire_length_mm']['bare']:.3f} bare + {m['wire_length_mm']['jumper']:.3f} insulated |
| Longest IN line | {x['longest_IN_line']['net']}, {x['longest_IN_line']['mm']:.3f} mm |
| VREF root → CH1–4, mm | {vref} |
| J104 VM → CH1–4 VIN, mm | {vm} |
| J101 GND → CH1–4 GND13, mm | {g13} |
| J101 GND → CH1–4 GND2, mm | {g2} |
| Used bbox, grid-origin mm | ({bbox[0]:.3f}, {bbox[1]:.3f})–({bbox[2]:.3f}, {bbox[3]:.3f}); **{width:.3f} × {height:.3f} mm** |
| Used bbox area | {m['used_bbox_area_mm2']:.3f} mm²; all bodies pass the real 155 × 114 mm outline with its 1 mm margin |
| Build effort | {m['conductors']} wire pieces; {x['wire_end_terminations']} wire ends + {x['component_and_adapter_tails']} component/adapter tails; **{len(sites)} planned solder sites** with end/bend/8-hole supports |
| Conservative contact count | {x['solder_sites_conservative_all_contacted_pads']} sites if every modeled contacted land is soldered |
| Connectivity checks | No shorts, opens, NC host wiring, floating conductors or remaining wire-graph cycles |

Stock lengths exclude cut/strip allowance:

| Copper / gauge | Bare mm | Insulated mm |
|---|---:|---:|
{gauge}

The native comparison tuple is authoritative for ranking. The CLI's legacy `passed`/exit code remains FAIL/1 solely because it emits UNCHECKED as error findings; this is accepted by the supervisor's v0.2 policy. `metrics.score` retains that legacy penalty and is not used instead of the tuple.

The layout retains F1's north driver row, central VREF and opposite control side. Carriers are identically rotated 270°, with **CH4, CH3, CH2, CH1 left to right**. Pico is now horizontal at 90°: GP2–GP9 faces north toward the drivers and USB reaches the east grid edge. SmartNet is below Pico, outside the PWM fanout. Entry remains west, converter southwest, stop header south. All 13 probes are fitted; no scaffold area is reserved. The five named expansion singleton nets, ADC_VREF and VBUS have no host wires.

Main VM/GND runs are bare 1.0 mm copper beneath the carriers at TOP rows 8/10; their common horizontal portions are two holes apart. Channel branches are >=0.6 mm. Routing VM taps around the left of each local ground branch removes the former bulk-cap ground jumpers while preserving all local length bounds. CH1, at the end of the trunks, also has a bare local GND tie and bare FAULT escape. Other channel wiring repeats the same pattern. The converter has a dedicated mostly bare, paired 0.51 mm feed/return; the short insulated return ending at U107.2 preserves G02. Pico ground rails are inside its socket rows. GND_ENTRY / GND_LOGIC / VREF_ROOT retain their approved anchors.

The selected wiring keeps the IN fanout insulated: alternatives with bare IN1 wires produced more crossings on shared logic nets. The final ARM/FAULT resistor placement allows both local signals to leave Pico on bare wires. No cross-branch ground shortcut through Pico or a carrier was introduced. Native hard audits stayed zero while varying net order, all 16 IN1 bare subsets and end-channel escapes; search records and earlier layouts are under `search_*.json` and `experiments/`. Duplicate copper and one small +3V3 loop were removed after routing.

**Unchecked hard IDs:** {unchecked}. These cover scope evidence, exposed/pad/solder clearance, mounting and access, unsupported header mating-face points, quiet/output separation, current/drop/harness and support evidence. M07/M09 and the declared XH edge points pass; M08 remains UNCHECKED for J104/J213's undeclared feature points. Soft UNCHECKED IDs are B03, B04 and S03. None was hidden or counted as a pass.

Build review still needs connector/USB/BOOTSEL/grip clearance, socket/adapter fit, solder/lead surface gaps, underside wire height and flex, thermal and noise tests, contact/drop measurements and panel/coil harness checks. The AWG26 precrimp coil leads follow approved v0.2 W07 and need the specified heat test. Use >=10 mm underside standoffs and the <=8-hole support plan in `wire_support.csv`. Wire endpoints are solder nodes; lay heavy wires against underside pads/tails rather than forcing multiple leads into one 1 mm hole. Assembly plus inspection is estimated at **6–10 hours**, excluding HDD/panel harnesses; this is an engineering estimate.

Verification used the shared board override on every CLI call:

```text
{(out/'verify.log').read_text(encoding='utf8').splitlines()[0]}
COMPARISON: {tupletext}
hard_failed_rule_ids: []
WIRE LIST: {m['conductors']} steps
CONTINUITY: 1290 tests (bare board, power off)
```

The three SVGs were opened through offline XML/raster previews and checked for labels, polarity/NC visibility and mirrored bottom coordinates. Final QA and hashes are in `out/render_qc.json` and `out/final_manifest.json`. The continuity CSV is for the wired bare board, with components/modules absent and capacitors discharged. Shared inputs/tools and other candidate folders were not changed.
'''
 (HERE/'summary.md').write_text(summary,encoding='utf8')
 counts={}
 for name in ['wirelist.csv','continuity.csv','netlist_actual.csv']:
  with (out/name).open(encoding='utf-8-sig',newline='') as f:counts[name]=len(list(csv.DictReader(f)))
 assert counts=={'wirelist.csv':m['conductors'],'continuity.csv':1290,'netlist_actual.csv':186}
 for name in ['top','bottom','overlay']:ET.parse(out/(name+'.svg'))
 if '--qa-confirmed' in sys.argv:
  qc=json.loads((out/'render_qc.json').read_text(encoding='utf8'));qc.update(status='VISUALLY INSPECTED: top, bottom, overlay',notes=['Actual 155x114 mm outline and physical mounting holes visible.','Bulk, converter, diode and XH captions moved away from own pads/NC crosses; C108/TP461 overlap fixed.','Bottom reads BC..A; coordinates in CSVs stay TOP.','Underside jumper stack/strain and real print scale remain build checks.'],svg_SHA256={n:hashlib.sha256((out/(n+'.svg')).read_bytes()).hexdigest() for n in ['top','bottom','overlay']});save_json(out/'render_qc.json',qc)
 mandatory=['placement.json','wiring.json','summary.md']+['out/'+n for n in ['top.svg','bottom.svg','overlay.svg','report.json','metrics.json','wirelist.csv','continuity.csv','netlist_actual.csv']]
 for name in mandatory:assert (HERE/name).stat().st_size>0
 save_json(out/'final_manifest.json',{'required_files_present':True,'fresh_verifier_matches_report':True,'comparison_tuple':m['comparison_tuple'],'ranking_pass':m['ranking_pass'],'hard_failed_rule_ids':m['hard_failed_rule_ids'],'CSV_rows':counts,'files_SHA256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in mandatory}})
 print('Round 2 summary/integrity:',m['comparison_tuple'],'planned solder sites',len(sites))

if __name__=='__main__':main()
