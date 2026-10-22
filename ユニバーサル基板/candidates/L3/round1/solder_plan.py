"""Practical solder/anchor schedule, supplementary to conservative wirelist.

The official verifier contacts every pad under a bare wire. For assembly,
unpopulated intermediate pads need not be individually soldered if each
continuous wire is fixed at terminals, bends, junctions and <=8-hole intervals.
This schedule proves the same pin LVS even when all other contacts are ignored.
No official model, wiring or report is changed by this secondary proof.
"""
import sys,json
from pathlib import Path
from collections import defaultdict
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent
sys.path.insert(0,str(BASE/'tools'))
from model import Project,hole,save_json,write_csv,COMPARE
from verify import extract
p=Project(HERE)
why=defaultdict(set);claims=defaultdict(set)
for q in p.pins.values():why[q.xy].add('component '+q.label);claims[q.xy].add(q.net)
for xy,name in p.reserved_pads.items():why[xy].add('reserved physical lead: NO HOST WIRE');claims[xy].add('RESERVED')
contact=defaultdict(list)
for c in p.conductors:
    for xy in c['contacts']:contact[xy].append(c['id']);claims[xy].add(c['net'])
    for xy in [c['contacts'][0],c['contacts'][-1]]:why[xy].add('wire end')
    if c['kind']!='jumper':
        for xy in c['xy'][1:-1]:why[xy].add('bare bend')
for xy,ids in contact.items():
    if len(ids)>1:why[xy].add('wire junction')
anchors=set(why)
for c in p.conductors:
    if c['kind']=='jumper':continue
    indices=[i for i,xy in enumerate(c['contacts']) if xy in anchors]
    for a,b in zip(indices,indices[1:]):
        while b-a>8:
            a+=8;xy=c['contacts'][a];anchors.add(xy);why[xy].add('support <=8 holes')
max_span=0;rows=[]
for c in p.conductors:
    if c['kind']=='jumper':continue
    ii=[i for i,xy in enumerate(c['contacts']) if xy in anchors]
    max_span=max(max_span,max((b-a for a,b in zip(ii,ii[1:])),default=0))
    rows.append({'id':c['id'],'net':c['net'],'solder_or_anchor_holes_TOP':';'.join(hole(c['contacts'][i]) for i in ii),'max_gap_holes':max((b-a for a,b in zip(ii,ii[1:])),default=0)})
write_csv(HERE/'out/wire_supports.csv',['id','net','solder_or_anchor_holes_TOP','max_gap_holes'],rows)
write_csv(HERE/'out/assembly_solder_sites.csv',['hole_TOP','net','reason'],[
    {'hole_TOP':hole(xy),'net':';'.join(sorted(claims[xy])),'reason':'; '.join(sorted(why[xy]))} for xy in sorted(anchors,key=lambda q:(q[1],q[0]))])
q=p.clone()
for c in q.conductors:
    if c['kind']!='jumper':c['contacts']=[xy for xy in c['contacts'] if xy in anchors]
issues,actual,*_=extract(q);comparison=COMPARE.compare(q.expected,actual,'name')
result={'recommended_joint_sites':len(anchors),'max_supported_span_holes':max_span,
    'terminal_connectivity_LVS_pass':not issues and not comparison,'issues':issues,'comparison':comparison,
    'scope':'secondary continuous-wire/solder-contact plan only; original conservative report unchanged',
    'assembly':'minimum 10mm bottom standoff; immobilise every selected anchor; insulate full jumper lengths; unused intermediate pads still must remain free of other nets'}
save_json(HERE/'out/solder_plan_validation.json',result)
print(json.dumps(result,indent=2))
