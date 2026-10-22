from common import *
from collections import defaultdict,Counter,deque
from model import segment_distance
from verify import verify
from detour import improve
D=json.loads((HERE/'round2/placement.json').read_text(encoding='utf8'));W=json.loads((HERE/'round2/wiring.json').read_text(encoding='utf8'));p=project(D,W)
pinpoints={v.xy for v in p.pins.values()};ct=Counter(q for c in p.conductors for q in set(c['contacts']));new=[]
for c in W['conductors']:
 if c['kind']=='jumper':new.append(c);continue
 pts=path_points([point(z) for z in c['path']]);cuts=[i for i,q in enumerate(pts) if i in [0,len(pts)-1] or q in pinpoints or ct[q]>1]
 for a,b in zip(cuts,cuts[1:]):
  v=copy.deepcopy(c);v.update(id='A'+str(len(new)),path=[hole(q) for q in compress(pts[a:b+1])]);new.append(v)
W={**W,'conductors':new};p=project(D,W)
roots={}
for node,labs in [('GND_ENTRY',['G_POWER','G_INPUT','G_TVS','G_LINK']),('GND_LOGIC',['G_LINK','G_PICO','G_REF','G_RX','G_CONTROL','G_CAPS']),('VREF_ROOT',['V_SOURCE','V_CH1','V_CH2','V_CH3','V_CH4'])]:roots[point(D['nodes'][node])]=set(labs)
occ=defaultdict(set);loc=defaultdict(set);actual={};fixed=defaultdict(set)
for q in p.pins.values():
 labs={c.get('routing_group',c['net']) for c in p.conductors if q.xy in c['contacts'] and c['net']==q.net}
 fixed[q.xy].update(labs or {q.net if q.net!='NC' else 'NC:'+q.label})
for xy,label in p.reserved_pads.items():fixed[xy].add('NC:'+label)
for c in p.conductors:
 lab=c['routing_group'];actual[lab]=c['net']
 for q in c['contacts']:occ[q].add(c['id']);loc[lab].add(q)
byid={c['id']:c for c in p.conductors};out=[(a,b) for c in p.conductors if '_OUT' in c['net'] for a,b in zip(c['xy'],c['xy'][1:])];rects=[v.rect for k,v in p.parts.items() if k in ['J313','J323','J333','J343']];faults=[q.xy for q in p.pins.values() if q.ref.startswith('U3') and q.number=='9'];masks={}
for net in {'VREF','SLEEP','FAULT','SN_BUS','SN_RX_IN','SN_PU','UART_RX','ARM','ARM_SW'}:
 gap=3 if net=='VREF' else 2;bad=set()
 for x,y in itertools.product(range(p.columns),range(p.rows)):
  q=(x,y)
  if net=='FAULT' and any(distance(q,f)<=2 for f in faults):continue
  pr=(x*PITCH,y*PITCH,x*PITCH,y*PITCH)
  if any(segment_distance(q,q,a,b)<gap+.56/PITCH-1e-8 for a,b in out) or any(rect_distance(pr,r)<gap*PITCH+.26 for r in rects):bad.add(q)
 masks[net]=bad
usable={q for q in itertools.product(range(p.columns),range(p.rows)) if p.usable(q)}
neighbors={q:[z for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)] if (z:=(q[0]+dx,q[1]+dy)) in usable] for q in usable}
jlabs={c['routing_group'] for c in p.conductors if c['kind']=='jumper'}
def bound(cuts):
 changed={byid[c]['routing_group'] for c in cuts};labs=jlabs|changed;score=0
 for lab in labs:
  blocked=set(masks.get(actual[lab],set()));goals=set()
  for q,ids in occ.items():
   labsq={byid[c]['routing_group'] for c in ids if c not in cuts or q in [byid[c]['xy'][0],byid[c]['xy'][-1]]}|fixed[q]
   if labsq-{lab} and lab not in roots.get(q,set()):blocked.add(q)
   if lab in labsq or lab in roots.get(q,set()):goals.add(q)
  free=usable-blocked;regions=0
  while goals:
   start=next(iter(goals));todo=[start];seen={start};regions+=1
   while todo:
    z=todo.pop()
    for q in neighbors[z]:
     if q in free and q not in seen:seen.add(q);todo.append(q)
   goals-=seen;free-=seen
  score+=max(0,regions-1)
  if not cuts:print('LAB BOUND',lab,regions-1,sum(c['kind']=='jumper' and c['routing_group']==lab for c in p.conductors),flush=True)
 return score
baseline=bound(set());print('BASE BOUND',baseline,flush=True)
