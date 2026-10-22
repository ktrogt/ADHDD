"""Round-2 concise report and final-file consistency evidence."""
import sys,json,csv,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parent.parent
sys.path.insert(0,str(B/'tools'))
from model import Project,load_json,save_json
from verify import verify
J=lambda path:json.loads(Path(path).read_text(encoding='utf-8'))
p=Project(H,board=load_json(B/'board.json'));r=load_json(H/'out/report.json');m=r['metrics'];e=J(H/'out/extended_metrics.json');s=J(H/'out/solder_plan_validation.json')
assert verify(p)==r
assert m['core_drc_errors']==0 and r['lvs_pass'] and m['hard_failed_rule_ids']==['P08','P09']
for source,target in [('board.json','board.json'),('design_rules_v0.2.json','design_rules.json'),('footprints_ub.json','footprints_ub.json'),('netlist_ub.csv','netlist.csv')]:assert (B/source).read_bytes()==(H/target).read_bytes()
vref=', '.join(f'{z:.2f}' for z in e['VREF_branches_CH1_to_4_mm'])
vm=', '.join(f"{z['VM_from_C106_mm']:.2f}" for z in e['power_paths']);gnd=', '.join(f"{z['GND13_from_C106_mm']:.2f}" for z in e['power_paths'])
gauges='; '.join(f'{k}: {v:.2f}' for k,v in e['wire_length_by_gauge_mm'].items())
tupletext='('+', '.join('true' if z is True else str(z) for z in m['comparison_tuple'])+')'
with (H/'out/continuity.csv').open(encoding='utf-8-sig',newline='') as f:ct=len(list(csv.DictReader(f)))
box=m['bbox_mm'];dimensions=(box[2]-box[0],box[3]-box[1])
proof=J(H/'out/r2_east_edge_certificate.json');assert proof['infeasible']
save_json(H/'infeasibility.json',{'round':2,'rules':'v0.2','east_edge_certificate':proof,'common_column_certificate':J(H/'out/r2_infeasibility_certificate.json'),
    'proposal':'Same 104708 turned portrait: four-channel packing found, not a routed layout and not adopted for the strict short-edge seed.'})
log=(H/'out/verify.log').read_text(encoding='utf-8').splitlines()
summary=f'''**L3 Round 2 / v0.2, 2026-10-22 — strict F3 is infeasible.** Hard FAIL 0 cannot be reached with four channels at the short east edge. The exhaustive necessary-condition proof covers all carrier rotations and horizontal staggering. See [constraints.md](constraints.md). Per the supervisor's instruction, work stops at this proof and the best complete comparison snapshot; this is not an eligible build layout.

| Metric | Current v0.2 snapshot |
|---|---|
| Native comparison tuple | `{tupletext}` |
| Tuple order | LVS, core DRC, hard FAIL IDs, jumpers, soft penalty, bends, length mm |
| LVS / core DRC | PASS: 186/186 pins, 42 nets, 22 NC / 0 errors |
| Hard FAIL list | **P08, P09**; 36 hard rules PASS, 23 UNCHECKED |
| Weighted soft penalty / legacy scalar | {m['t7_soft_penalty']:.6f} / {m['score']:.3f} |
| Jumpers / bare pieces / bridges | {e['wire_counts']['jumper']} / {e['wire_counts']['bare']} / 0, all BOTTOM |
| Wire pieces / length | {m['conductors']} / {m['total_wire_mm']:.2f} mm |
| Length by gauge, mm | {gauges} |
| Bends | {m['bends']}: {e['bare_bends']} bare, {e['jumper_bends']} insulated |
| Longest IN | {e['longest_IN']['net']}, {e['longest_IN']['length_mm']:.2f} mm; hard limit 152.40 |
| VREF CH1→4, mm | {vref}; V01 PASS |
| VM C106→VIN CH1→4, mm | {vm} |
| GND C106→GND13 CH1→4, mm | {gnd}; G01/G02 PASS |
| Used box | {dimensions[0]:.2f} × {dimensions[1]:.2f} mm, inside real 155 × 114 outline |
| Build effort | {s['recommended_joint_sites']} solder/anchor sites, {m['conductors']} continuous wire pieces; estimated 4–7 h plus module preparation/bench testing |

The built floor plan retains the east column, all carriers 0°, HDD4→HDD1 north to south. Pico is 180°, USB south, with its GP2–GP9 column eastward facing the drivers. VM/GND are 1.0 mm bare trunks under the carriers; channel branches/OUT wires use AWG22, quiet returns AWG24, logic AWG26. Three VREF spokes are bare, one insulated. Thirteen probes remain; scaffold GPIOs are unwired.

Compared with round 1, the strip moved one hole east so coil mating features pass M08 at 2 holes. Six-hole regulator-capacitor returns fix P14. The real-outline verifier gives core DRC 0 with no workaround. North C341 moved up one row. P08/P09 remain: CH1–3 bulk returns are 9 holes; north C341 has 9/10-hole distances. These are not waived. The 16-jumper target is not met; optimisation stops because the required packing is impossible.

The proof removes all other circuitry/routing. At 0°, east-compatible tiles allow origin columns 43–46 and rows 4–33 (0-based): 29 rows available versus 33 required by H01. At 270°, only column 48 and rows 11–36 work: 25 versus 30. At 90°/180° no isolated complete tile reaches E. At 0° the entire x-stagger range is narrower than the carrier body, so the same y-spacing bound still applies.

The smallest proposed scope change is to turn the same board 90° and use its long edge vertically. [portrait_geometry_only.json](proposals/portrait_geometry_only.json) has four feasible channel tiles under unchanged electrical bounds. It is not a routed substitute: in canonical coordinates it becomes a long-edge row and changes the assigned seed. A larger board is the alternative if the short-edge column must be kept.

UNCHECKED hard IDs for Claude's visual/build review: **B01, B02, B07, C01, C02, C03, M02, M03, M04, M05, M06, M08, M10, M12, S01, S02, W01–W07**. They concern power/harness/drop details, wire/pad/solder surfaces, hardware/access, scope provenance and assembly. M08's unknown portion is only the two headers with no mating point; known XH checks pass. Soft unknowns are **{', '.join(m['unchecked_soft_rule_ids'])}**; unknown portions add zero to native penalty. Full reasons remain in report.json.

Blue patches show clear nominal 5.08 mm finger areas: N/S per carrier, W/E at the Pico midpoint. Other bodies do not occupy them, and all wiring is below. Physical removal and 25 mm vertical finger clearance remain fit checks. Star-junction construction, 1 mm wire/hole fit, wire heights, strain relief, solder fillets, temperatures/noise and all bench checks are unmeasured. Initial VREF remains 4.7 kohm. The secondary {s['recommended_joint_sites']}-site solder plan preserves pin LVS with <=8-hole support gaps and >=10 mm bottom standoff.

Exact verify output:

```text
{log[0]}
{log[1]}
```

Render, wirelist and continuity succeeded ({ct:,} continuity checks). Final TOP, mirrored BOTTOM and OVERLAY SVGs were opened through offline raster previews and inspected; labels/value key are readable. The real outline, mounting holes, channel names and grip areas are shown. Scale remains 1:1 with the 20 mm ruler; all CSV hole names are TOP coordinates. Round 1 is under [round1/](round1/); approved input hashes/copies match. No shared file or rule was edited.
'''
(H/'summary.md').write_text(summary,encoding='utf-8')
required=['placement.json','wiring.json','summary.md','constraints.md','README.md','infeasibility.json']+['out/'+x for x in ['top.svg','bottom.svg','overlay.svg','report.json','metrics.json','wirelist.csv','continuity.csv','netlist_actual.csv','r2_east_edge_certificate.json','r2_column_feasibility.json','extended_metrics.json','grip_review.json','assembly_pin_map.csv']]
ns={'s':'http://www.w3.org/2000/svg'}
for view in ['top','bottom','overlay']:
    root=ET.parse(H/'out'/f'{view}.svg').getroot();vb=list(map(float,root.get('viewBox').split()))
    assert abs(float(root.get('width').removesuffix('mm'))-vb[2])<1e-8 and abs(float(root.get('height').removesuffix('mm'))-vb[3])<1e-8
    assert len([z for z in root.findall('.//s:text',ns) if (z.text or '') in ['HDD1','HDD2','HDD3','HDD4']])==4
save_json(H/'out/package_check.json',{'package_consistency':'PASS','comparison_tuple':m['comparison_tuple'],'ranking_pass':m['ranking_pass'],
    'scope':'saved report matches inputs; exports and SVG scale/labels checked; infeasible hard rules not waived',
    'sha256':{f:hashlib.sha256((H/f).read_bytes()).hexdigest() for f in required}})
print('Round-2 handoff saved',m['comparison_tuple'])
