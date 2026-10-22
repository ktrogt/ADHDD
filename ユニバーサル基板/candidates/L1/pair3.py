from common import *
from verify import verify
from detour3 import improve
D=json.loads((HERE/'round2/placement.json').read_text(encoding='utf8'));W=json.loads((HERE/'wiring.atomic_base.json').read_text(encoding='utf8'))
best=tuple(json.loads((HERE/'preview.atomic.json').read_text(encoding='utf8'))['metrics']['lexicographic_sort_key']);hist=[]
todo=sorted((z for z in json.loads((HERE/'search_pair_bounds.json').read_text(encoding='utf8'))['trials'] if z['bound']<27),key=lambda z:z['bound'])
for ii,z in enumerate(todo):
 cuts=set(z['cuts']);trial=copy.deepcopy(W);shift=[]
 for c in trial['conductors']:
  if c['id'] in cuts:
   c.update(kind='jumper',type='insulated copper',gauge={'1.0 mm':'AWG18','0.6 mm':'AWG22','0.51 mm':'AWG24','0.5 mm':'AWG24'}.get(c['gauge'],c['gauge']));c.pop('diameter_mm',None);c.pop('area_mm2',None);shift.append(c)
 trial['conductors']=[c for c in trial['conductors'] if c['id'] not in cuts]+shift
 r=verify(project(D,trial))
 if r['metrics']['comparison_tuple'][:3]!=[True,0,0]:continue
 ww,r,ev=improve(trial,D);key=tuple(r['metrics']['lexicographic_sort_key']);hist.append({**z,'tuple':r['metrics']['comparison_tuple'],'events':ev})
 if key<best and r['metrics']['t7_soft_penalty']<=242.639048:
  best=key;save_json(HERE/'wiring.pair.json',ww);save_json(HERE/'preview.pair.json',r);print('BEST PAIR',ii,z,key,flush=True)
 if ii%10==0:print('PAIR PROGRESS',ii,'/',len(todo),flush=True);save_json(HERE/'search_pairs_r3.json',hist)
save_json(HERE/'search_pairs_r3.json',hist);print('PAIR FINAL',best,flush=True)
