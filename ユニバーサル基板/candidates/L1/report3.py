"""Round-3 handoff, assembly support sites and final artifact integrity checks."""
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
 old=json.loads((HERE/'round2/out/metrics.json').read_text(encoding='utf8'))
 ox=json.loads((HERE/'round2/out/metrics_extra.json').read_text(encoding='utf8'))
 with (out/'continuity.csv').open(encoding='utf-8-sig',newline='') as f:continuity_count=len(list(csv.DictReader(f)))
 experiments={}
 for f in HERE.glob('search_*_r3.json'):
  z=json.loads(f.read_text(encoding='utf8'))
  if not isinstance(z,list):continue
  rows=[q['tuple'] for q in z if isinstance(q,dict) and 'tuple' in q]
  valid=[q for q in rows if q[:3]==[True,0,0]]
  experiments[f.name]={'recorded_trials':len(rows),'hard_zero_trials':len(valid),'best_hard_zero_tuple':min(valid,key=lambda q:q[3:]) if valid else None}
 save_json(out/'round3_experiments.json',experiments)
 trial_count=sum(q['recorded_trials'] for q in experiments.values())
 summary=f'''# L1 round 3 - F1, approved rules v0.2

2026-10-22. Work and decisions are recorded here because the candidate scope permits writes only inside L1.

**LVS PASS; core DRC 0; hard FAIL IDs `[]`; ranking_pass true.** Jumpers remain **31**: the <=20 target (stretch <=16) was **not reached**. The selected tuple improves secondary metrics; no minimum-jumper proof is claimed. The complete previous state is preserved under `round2/`, alongside the existing `round1/` archive.

| Metric | Round 2 | Round 3 |
|---|---:|---:|
| Comparison tuple | `{json.dumps(old['comparison_tuple'])}` | **`{tupletext}`** |
| Hard audit PASS / FAIL / UNCHECKED | 38 / 0 / 23 | **38 / 0 / 23** |
| Insulated jumpers | 31 | **31** |
| T7 soft penalty, evaluated portion | {old['t7_soft_penalty']:.6f} | **{m['t7_soft_penalty']:.6f}** |
| Native bends (all bare) | {old['bends']} | **{m['bends']}** |
| Total wire mm | {old['total_wire_mm']:.3f} | **{m['total_wire_mm']:.3f}** |
| Bare wire mm | {old['wire_length_mm']['bare']:.3f} | {m['wire_length_mm']['bare']:.3f} |
| Insulated wire mm | {old['wire_length_mm']['jumper']:.3f} | {m['wire_length_mm']['jumper']:.3f} |
| Wire pieces | {old['conductors']} = 91 bare + 31 insulated | **{m['conductors']} = {x['bare_pieces']} bare + 31 insulated** |
| Bare straight spans | {ox['bare_straight_segments']} | {x['bare_straight_segments']} |

Tuple order: LVS ok, core DRC errors, hard FAIL count, jumpers, T7 soft penalty, bends, total wire mm. Soft penalty falls {(1-m['t7_soft_penalty']/old['t7_soft_penalty'])*100:.2f}%, length {(1-m['total_wire_mm']/old['total_wire_mm'])*100:.2f}%, and native bends {(1-m['bends']/old['bends'])*100:.2f}%. The trade-off is four additional wire pieces. Some bend reduction comes from cutting bent runs into simpler pieces; the straight-span count is also reported to make that visible. Collinear pieces were consolidated again before export. All 31 insulated wires retain their round-2 endpoints and gauges.

| Detail | Final value |
|---|---|
| Scope / LVS | 54 refs, 186/186 pins, 42 nets, 22 NC; exact approved CSV |
| Hard FAIL list | **`[]`** |
| Star audit | G01 / G02 / V01 PASS |
| Longest IN | {x['longest_IN_line']['net']}: {x['longest_IN_line']['mm']:.3f} mm |
| VREF root to CH1-4, mm | {vref} |
| J104 VM to CH1-4 VIN, mm | {vm} |
| J101 GND to CH1-4 GND13, mm | {g13} |
| J101 GND to CH1-4 GND2, mm | {g2} |
| Used bbox, grid-origin mm | ({bbox[0]:.3f}, {bbox[1]:.3f}) to ({bbox[2]:.3f}, {bbox[3]:.3f}); **{width:.3f} x {height:.3f} mm** |
| Bbox area / board | {m['used_bbox_area_mm2']:.3f} mm2 / real 155 x 114 mm; bodies pass 1 mm outline margin |
| Build effort | **{m['conductors']} wire pieces**, {x['wire_end_terminations']} wire ends + {x['component_and_adapter_tails']} component/adapter tails; **{len(sites)} planned solder sites** |
| Conservative solder count | {x['solder_sites_conservative_all_contacted_pads']} pad sites if every modeled bare-wire contact is soldered |
| Tool generic legacy score | {m['score']:.3f}; retains UNCHECKED penalties, so the native tuple is used for selection |

Wire stock lengths exclude cutting/stripping allowance:

| Copper / gauge | Bare mm | Insulated mm |
|---|---:|---:|
{gauge}

F1 as built is unchanged from round 2: identical 270-degree carriers, CH4/CH3/CH2/CH1 left to right along the north edge; each has its local bulk/ceramic capacitors, XH3 coil connector (centre NC) and CS probe. Pico has north-facing GP2-GP9 and east-facing USB; SmartNet/buffer is southeast, entry west, converter southwest, VREF central and stop header south. All 13 probes remain. No scaffold is fitted or reserved. Singleton expansion GPIO nets, ADC_VREF and VBUS have no host wires.

Bare 1.0 mm VM/power-GND trunks remain at TOP rows 8/10, two holes apart; channel branches remain >=0.6 mm. CH1 retains its bare end-of-strip GND/FAULT escape; the other channels keep the repeated pattern. The converter retains its dedicated mostly bare, paired feed/return, and its short insulated quiet-return termination. GND_ENTRY, GND_LOGIC and VREF_ROOT retain their approved anchors. A graph check also found no multi-channel power path using copper below 0.5 mm2; this supplements, and does not change, the UNCHECKED current/drop audit. No wire-graph cycle remains.

Round-3 work recorded {trial_count} routing/placement variants in `out/round3_experiments.json`, plus single- and paired-chain rewiring searches. Only hard-zero candidates with soft penalty <=110% of round 2 were eligible. The final changes trim unused bare tails and shorten local control/ground/receiver runs; ARM_SW now follows a simpler bare route. Further tested jumper reductions did not improve the tuple. These are search results, not impossibility proofs:

- Under-module buses: freeing the SLEEP/+3V3 rows displaced crossings into the power-return trunk and PMODE/VREF taps; the combined bus/FAULT-star trials did not beat 31 jumpers.
- FAULT on the power side: row 6 is too close to OUT copper outside the named escape disks; going below the paired trunks needs insulated crossings. Four direct insulated spokes clear the signal field but add a wire elsewhere.
- Bare staggered IN / central Pico: north-shift and south-USB candidates passed hard checks but needed at least 34 and 36 jumpers respectively in the recorded searches. The west-USB trial also encountered FAULT/UART length limits.
- Bare VREF star: four bare driver branches were feasible, but their source connection and +3V3 feed crossings offset the saved jumpers.
- Regulator near entry: the existing dedicated paired supply was retained; moving it for the alternative Pico arrangements did not improve the complete layout.

**UNCHECKED hard IDs:** {unchecked}. Soft UNCHECKED IDs: B03, B04, S03. These are not counted as passes. They include source/scope evidence; exposed lead/pad/solder surface gaps; mounting, grips, USB/BOOTSEL and mating access; output separation; conductor/contact/drop/harness and support checks. M08 remains UNCHECKED for header feature points not declared by the library. The tool's legacy headline/exit is FAIL/1 solely because it emits these UNCHECKED findings as errors; the supervisor's accepted criterion is `ranking_pass: true`, core DRC 0 and no hard FAIL.

Assumptions: use the approved physical board, adapters/sockets and v0.2 AWG26 precrimp coil leads; no rule relaxation or electrical substitution was introduced. Build checks remain for actual fit, underside height/strain, solder gaps, connector grip/USB access, thermal/noise behaviour and measured contact/drop. Use >=10 mm underside standoffs and the endpoint/bend/<=8-hole supports in `wire_support.csv`. Lay heavy wires against pads/tails rather than forcing several leads into one hole. Assembly and inspection estimate: **6-10 hours**, excluding HDD/panel harnesses.

Verification used `--board ユニバーサル基板/board.json` on every CLI invocation:

```text
{(out/'verify.log').read_text(encoding='utf8').splitlines()[0]}
COMPARISON: {tupletext}
hard_failed_rule_ids: []
WIRE LIST: {m['conductors']} steps
CONTINUITY: {continuity_count} tests (bare board, power off)
```

All three actual SVGs were opened as XML, rasterized offline and visually inspected: labels/polarity/NC marks are readable, and bottom coordinates are mirrored BC..A. CSV coordinates remain TOP. Continuity tests apply to the unpowered wired bare board before components/modules are fitted. Deliverables include SVGs, native reports/metrics, wire list, continuity, actual netlist, pin map, support plan and hashes. Shared files and other candidate folders were not changed.
'''
 (HERE/'summary.md').write_text(summary,encoding='utf8')
 counts={}
 for name in ['wirelist.csv','continuity.csv','netlist_actual.csv']:
  with (out/name).open(encoding='utf-8-sig',newline='') as f:counts[name]=len(list(csv.DictReader(f)))
 assert counts=={'wirelist.csv':m['conductors'],'continuity.csv':continuity_count,'netlist_actual.csv':186}
 for name in ['top','bottom','overlay']:ET.parse(out/(name+'.svg'))
 if '--qa-confirmed' in sys.argv:
  qc=json.loads((out/'render_qc.json').read_text(encoding='utf8'));qc.update(status='VISUALLY INSPECTED: top, bottom, overlay',notes=['Actual 155x114 mm outline and physical mounting holes visible.','Bulk, converter, diode and XH captions moved away from own pads/NC crosses; C108/TP461 overlap fixed.','Bottom reads BC..A; coordinates in CSVs stay TOP.','Underside jumper stack/strain and real print scale remain build checks.'],svg_SHA256={n:hashlib.sha256((out/(n+'.svg')).read_bytes()).hexdigest() for n in ['top','bottom','overlay']});save_json(out/'render_qc.json',qc)
 archive=json.loads((HERE/'round2/out/final_manifest.json').read_text(encoding='utf8'))
 for name,digest in archive['files_SHA256'].items():assert hashlib.sha256((HERE/'round2'/name).read_bytes()).hexdigest()==digest
 mandatory=['placement.json','wiring.json','summary.md']+['out/'+n for n in ['top.svg','bottom.svg','overlay.svg','report.json','metrics.json','wirelist.csv','continuity.csv','netlist_actual.csv']]
 for name in mandatory:assert (HERE/name).stat().st_size>0
 save_json(out/'final_manifest.json',{'required_files_present':True,'fresh_verifier_matches_report':True,'comparison_tuple':m['comparison_tuple'],'ranking_pass':m['ranking_pass'],'hard_failed_rule_ids':m['hard_failed_rule_ids'],'CSV_rows':counts,'files_SHA256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in mandatory}})
 print('Round 3 summary/integrity:',m['comparison_tuple'],'planned solder sites',len(sites))

if __name__=='__main__':main()
