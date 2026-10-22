"""Round-2 measurements, physical pin map and proposed clear grip patches."""
import sys,json,csv,math,hashlib
from pathlib import Path
from collections import Counter,defaultdict
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parent.parent
sys.path.insert(0,str(B/'tools'))
from model import Project,load_json,save_json,hole,write_csv,rect_intersects
from audit_extra import get_dist,point_rect
p=Project(H,board=load_json(B/'board.json'));r=json.loads((H/'out/report.json').read_text(encoding='utf-8'))
L=defaultdict(float)
for c in p.conductors:L[c['gauge']]+=c['length_mm']
bykind=Counter(c['kind'] for c in p.conductors)
vrefs=[];power=[];ins=[]
for ch in range(1,5):
    u=f'U{300+10*ch}'
    vrefs.append(get_dist(p,'VREF','C211.#1',u+'.#7'))
    power.append({'channel':ch,'VM_from_C106_mm':get_dist(p,'VM','C106.#1',u+'.#14'),'GND13_from_C106_mm':get_dist(p,'GND','C106.#2',u+'.#13')})
    for j,pp,dp in [(1,[4,6,9,11][ch-1],3),(2,[5,7,10,12][ch-1],4)]:ins.append({'net':f'HDD{ch}_IN{j}','length_mm':get_dist(p,f'HDD{ch}_IN{j}',f'U201.#{pp}',u+f'.#{dp}')})
maps={'J101':{'1':'4','2':'1','3':'3'},'D103':{'1':'2','2':'1'},'U207':{'1':'1','2':'2','3':'3','4':'4','5':'6'}}
maps.update({f'J{300+10*i+3}':{'1':'1','2':'3'} for i in range(1,5)})
rows=[{'ref':q.ref,'logical_pin':q.number,'physical_pin':maps.get(q.ref,{}).get(q.number,q.number),'pin_name':q.name,'net':q.net,'hole_TOP':hole(q.xy)} for q in p.pins.values()]
rows += [{'ref':v.split('.')[0],'logical_pin':'none','physical_pin':v.rsplit(':',1)[-1],'pin_name':v,'net':'RESERVED: no host wire','hole_TOP':hole(k)} for k,v in p.reserved_pads.items()]
write_csv(H/'out/assembly_pin_map.csv',['ref','logical_pin','physical_pin','pin_name','net','hole_TOP'],rows)
contact=defaultdict(list)
for c in p.conductors:
    for z in c['contacts']:contact[(c['net'],z)].append(c['id'])
write_csv(H/'out/junctions.csv',['net','hole_TOP','conductors'],[{'net':n,'hole_TOP':hole(z),'conductors':';'.join(v)} for (n,z),v in sorted(contact.items()) if len(v)>1])
grips=[]
for ref in ['U310','U320','U330','U340']:
    a,b,c,d=p.parts[ref].rect;mid=(a+c)/2
    for side,box in [('N',(mid-2.54,b-5.08,mid+2.54,b)),('S',(mid-2.54,d,mid+2.54,d+5.08))]:grips.append({'ref':ref,'side':side,'rect_A1_mm':box})
a,b,c,d=p.parts['U201'].rect;mid=(b+d)/2
for side,box in [('W',(a-5.08,mid-2.54,a,mid+2.54)),('E',(c,mid-2.54,c+5.08,mid+2.54))]:grips.append({'ref':'U201','side':side,'rect_A1_mm':box})
for box in grips:
    overlap=[ref for ref,part in p.parts.items() if ref!=box['ref'] and rect_intersects(box['rect_A1_mm'],part.rect)]
    box['other_body_overlaps']=overlap
    assert not overlap,(box,overlap)
save_json(H/'out/grip_review.json',{'status':'nominal planar patches clear; real finger/extraction test still UNCHECKED','patch_width_and_depth_mm':5.08,'vertical_clearance_required_mm':25,'all_wires_bottom':True,'patches':grips})
defs={x['id']:x for x in p.rules['rules']};hard=Counter(x['status'] for x in r['rule_checks'] if defs[x['id']]['severity']=='hard')
pins=set(q.xy for q in p.pins.values())|set(p.reserved_pads)
for c in p.conductors:pins.update(c['contacts'])
captured=json.loads((H/'input_hashes.json').read_text());actual={s:hashlib.sha256((B/s).read_bytes()).hexdigest() for s in captured}
e={'comparison_tuple':r['metrics']['comparison_tuple'],'hard_rule_status_counts':dict(hard),
    'wire_counts':dict(bykind),'wire_length_by_gauge_mm':{k:round(v,3) for k,v in L.items()},
    'bare_bends':sum(len(c['xy'])-2 for c in p.conductors if c['kind']=='bare'),'jumper_bends':sum(len(c['xy'])-2 for c in p.conductors if c['kind']=='jumper'),
    'VREF_branches_CH1_to_4_mm':vrefs,'power_paths':power,'IN_paths':ins,'longest_IN':max(ins,key=lambda z:z['length_mm']),
    'physical_component_pins_including_reserved':193,'conservative_solder_pad_locations':len(pins),
    'approved_inputs_unchanged':actual==captured,'hard_fail_list':r['metrics']['hard_failed_rule_ids'],
    'unchecked_hard_rules':r['metrics']['unchecked_hard_rules']}
save_json(H/'out/extended_metrics.json',e)
print(json.dumps(e,indent=2))
