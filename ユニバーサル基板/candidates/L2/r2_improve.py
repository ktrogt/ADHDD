"""Compare saved round-2 candidates, prune loops and retry bare paths."""
import sys,json,copy,time,math,random
from pathlib import Path
from collections import defaultdict
sys.dont_write_bytecode=True
import r2 as b
from model import save_json,point,hole,compress
from verify import verify,placement_drc,extract,wiring_drc
from router import astar
from branch_router_r2 import R
def core(p):
 e,actual,components,contacts,uf=extract(p)
 return not any(i['severity']=='error' for i in e+wiring_drc(p,contacts)) and not b.Project.__module__ is None and len({actual[k]['net'] for k,v in actual.items() if v['net']!='NC'})==len(p.nets)
def good(p):
 r=verify(p);return r if r['metrics']['ranking_pass'] else None
def improve(name,pl,w,strategy='length'):
 p=b.project(placement=pl,wiring=w);base=good(p)
 if not base: print(name,'initial not ranking-pass',flush=True);return None
 print(name,'start',base['metrics']['comparison_tuple'],flush=True)
 changed=True;removed=0;converted=0
 while changed:
  changed=False
  for c in sorted(w['conductors'],key=lambda c:(c['kind']!='jumper',-len(c['path']))):
   test=dict(schema_version=1,conductors=[q for q in w['conductors'] if q['id']!=c['id']])
   pp=b.project(placement=pl,wiring=test)
   if not core(pp):continue
   rr=good(pp)
   if rr and rr['metrics']['lexicographic_sort_key']<base['metrics']['lexicographic_sort_key']:
    w=test;p=pp;base=rr;changed=True;removed+=1;break
 # Bare retry uses complete final occupancy and canonical hard-rule verification.
 choices=[c for c in w['conductors'] if c['kind']=='jumper']
 if strategy=='signal':choices.sort(key=lambda c:(c['net'] in {'GND','VM','VIN_RAW','VIN_FUSED','VIN_PROT'},-len(c['path'])))
 elif strategy=='quiet':choices.sort(key=lambda c:(c['net'] not in {'SLEEP','FAULT','VREF','UART_RX','SN_BUS','SN_RX_IN','SN_PU'},-len(c['path'])))
 elif strategy.startswith('random'):random.Random(int(strategy[6:])).shuffle(choices)
 else:choices.sort(key=lambda c:-sum(b.md(point(a),point(z)) for a,z in zip(c['path'],c['path'][1:])))
 for c in choices:
  pp=b.project(placement=pl,wiring=w);a,z=point(c['path'][0]),point(c['path'][-1]);net=c['net']
  blocked={q.xy for q in pp.pins.values() if q.net!=net}|set(pp.reserved_pads)
  for v in pp.conductors:
   if v['net']!=net:blocked.update(v['contacts'])
  r=R(pp);r.cs=pp.wire_data()['conductors'];mask=r.quiet_mask(net);blocked|=mask;blocked-={a,z}
  path=astar(pp,a,{z},blocked,.75)
  if path is None:continue
  trial=copy.deepcopy(w)
  cc=next(q for q in trial['conductors'] if q['id']==c['id']);cc.update(kind='bare',side='bottom',type='tinned copper',path=[hole(q) for q in compress(path)])
  rr=good(b.project(placement=pl,wiring=trial))
  if rr and rr['metrics']['lexicographic_sort_key']<base['metrics']['lexicographic_sort_key']:
   w=trial;base=rr;converted+=1;print(name,'bare',c['id'],base['metrics']['comparison_tuple'],flush=True)
 # Retry redundant wires after conversions; no change outside this candidate.
 for c in list(w['conductors']):
  test=dict(schema_version=1,conductors=[q for q in w['conductors'] if q['id']!=c['id']]);pp=b.project(placement=pl,wiring=test)
  if not core(pp):continue
  rr=good(pp)
  if rr and rr['metrics']['lexicographic_sort_key']<base['metrics']['lexicographic_sort_key']:w=test;base=rr;removed+=1
 v=b.H/'variants'/('improved_'+name);v.mkdir(parents=True,exist_ok=True)
 save_json(v/'placement.json',pl);save_json(v/'wiring.json',w);save_json(v/'report.json',base)
 print(name,'end',base['metrics']['comparison_tuple'],'removed',removed,'converted',converted,flush=True)
 return pl,w,base
def main():
 cases=[]
 for name in ('fold_vertical','fold_horizontal','compact_before_manual','before_supply_compaction'):
  v=b.H/'variants'/name
  if v.exists():cases.append((name,b.load_json(v/'placement.json'),b.load_json(v/'wiring.json')))
 cases.append(('current',b.project().placement,b.project().wire_data()))
 if (b.H/'placement.best.json').exists():cases.append(('search_best',b.load_json(b.H/'placement.best.json'),b.load_json(b.H/'wiring.best.json')))
 winner=None
 for name,pl,w in cases:
  result=improve(name,pl,w)
  if result and (winner is None or result[2]['metrics']['lexicographic_sort_key']<winner[2]['metrics']['lexicographic_sort_key']):winner=result;save_json(b.H/'pruning_winner.json',dict(name=name,tuple=result[2]['metrics']['comparison_tuple']))
 assert winner
 save_json(b.H/'placement.json',winner[0]);save_json(b.H/'wiring.json',winner[1]);print('WINNER',winner[2]['metrics']['comparison_tuple'])
if __name__=='__main__':main()
