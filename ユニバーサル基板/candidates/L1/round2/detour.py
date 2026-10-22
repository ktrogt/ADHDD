"""Replace insulated edges by feasible bare detours, preserving all hard checks.

Stars remain separate routing groups. Existing same-group trees are rejoined
only once, so a replacement does not introduce a gratuitous wire loop.
"""
from common import *
from collections import defaultdict
from router import astar
from verify import verify,UnionFind
from model import segment_distance
import random

def improve(wiring,placement,order_seed=0):
 p=project(placement,wiring);initial=verify(p);assert initial['metrics']['comparison_tuple'][:3]==[True,0,0]
 wires=copy.deepcopy(wiring['conductors']);events=[]
 pin_groups={}
 for q in p.pins.values():
  labs={c.get('routing_group',c['net']) for c in p.conductors if q.xy in c['contacts'] and c['net']==q.net}
  pin_groups[q.xy]=labs or {q.net if q.net!='NC' else 'NC:'+q.label}
 roots={}
 for name,labs in [('GND_ENTRY',['G_POWER','G_INPUT','G_TVS','G_LINK']),('GND_LOGIC',['G_LINK','G_PICO','G_REF','G_RX','G_CONTROL','G_CAPS']),('VREF_ROOT',['V_SOURCE','V_CH1','V_CH2','V_CH3','V_CH4'])]:
  roots[point(placement['nodes'][name])]=set(labs)
 quiet={'VREF','SLEEP','FAULT','SN_BUS','SN_RX_IN','SN_PU','UART_RX','ARM','ARM_SW'};masks={}
 out=[(a,b) for c in p.conductors if '_OUT' in c['net'] for a,b in zip(c['xy'],c['xy'][1:])]
 rects=[v.rect for k,v in p.parts.items() if k in ['J313','J323','J333','J343']]
 faults=[q.xy for q in p.pins.values() if q.ref.startswith('U3') and q.number=='9']
 for net in quiet:
  gap=3 if net=='VREF' else 2;bad=set()
  for x,y in itertools.product(range(p.columns),range(p.rows)):
   q=(x,y)
   if net=='FAULT' and any(distance(q,f)<=2 for f in faults):continue
   pr=(x*PITCH,y*PITCH,x*PITCH,y*PITCH)
   if any(segment_distance(q,q,a,b)<gap+.56/PITCH-1e-8 for a,b in out) or any(rect_distance(pr,r)<gap*PITCH+.26 for r in rects):bad.add(q)
  masks[net]=bad
 todo=[c['id'] for c in wires if c['kind']=='jumper']
 if order_seed:random.Random(order_seed).shuffle(todo)
 for cid in todo:
  old=next((c for c in wires if c['id']==cid),None)
  if old is None:continue
  lab=old.get('routing_group',old['net']);s,t=point(old['path'][0]),point(old['path'][-1])
  occ=defaultdict(set);uf=UnionFind();loc=set()
  for xy,labs in pin_groups.items():occ[xy].update(labs)
  for xy,label in p.reserved_pads.items():occ[xy].add('NC_EXTRA:'+label)
  for c in wires:
   if c['id']==cid:continue
   cc=[point(c['path'][0]),point(c['path'][-1])] if c['kind']=='jumper' else path_points([point(z) for z in c['path']])
   group=c.get('routing_group',c['net'])
   for q in cc:occ[q].add(group)
   if group==lab:
    loc.update(cc)
    for q in cc:uf.union(cc[0],q)
  loc.update([s,t]);groups=defaultdict(set)
  for q in loc:groups[uf.find(q)].add(q)
  aa,bb=groups[uf.find(s)],groups[uf.find(t)]
  replacement=None
  if uf.find(s)!=uf.find(t):
   blocked={q for q,labs in occ.items() if labs-{lab} and lab not in roots.get(q,set())}|masks.get(old['net'],set())
   trials=sorted(aa,key=lambda q:min(man(q,z) for z in bb))[:12]
   paths=[]
   for src in trials:
    path=astar(p,src,bb,blocked|(aa-{src}),1.2)
    if path:paths.append(path)
   if not paths:continue
   path=min(paths,key=lambda z:(len(z),len(compress(z))))
   replacement=copy.deepcopy(old);replacement['kind']='bare';replacement['type']='tinned copper';replacement['path']=[hole(q) for q in compress(path)]
   gauge={'AWG18':'1.0 mm','AWG22':'0.6 mm','AWG24':'0.51 mm'}.get(replacement['gauge'],replacement['gauge'])
   replacement['gauge']=gauge
   if gauge.endswith(' mm'):
    dia=float(gauge.split()[0]);replacement.update(diameter_mm=dia,area_mm2=math.pi*dia*dia/4)
  trial=[replacement if c['id']==cid else c for c in wires if c['id']!=cid or replacement is not None]
  candidate={**wiring,'conductors':trial};r=verify(project(placement,candidate))
  if r['metrics']['comparison_tuple'][:3]==[True,0,0]:
   before=sum(c['kind']=='jumper' for c in wires);wires=trial
   events.append({'id':cid,'net':old['net'],'from':old['path'],'to':replacement['path'] if replacement else 'removed redundant edge','jumpers_before':before,'tuple_after':r['metrics']['comparison_tuple']})
 outw={**wiring,'conductors':wires,'detour_order_seed':order_seed};r=verify(project(placement,outw))
 return outw,r,events

if __name__=='__main__':
 w=json.loads((HERE/'wiring.r2.json').read_text(encoding='utf8'));d=json.loads((HERE/'placement.r2.json').read_text(encoding='utf8'))
 best=None;history=[]
 for seed in range(int(sys.argv[1]) if len(sys.argv)>1 else 1):
  ww,r,ev=improve(w,d,seed);key=tuple(r['metrics']['lexicographic_sort_key']);history.append({'seed':seed,'tuple':r['metrics']['comparison_tuple'],'events':ev})
  print('DETOUR',seed,r['metrics']['comparison_tuple'],[z['id'] for z in ev],flush=True)
  if best is None or key<best:
   best=key;save_json(HERE/'wiring.detour.json',ww);save_json(HERE/'preview.detour.json',r)
  save_json(HERE/'detour_search.json',history)
