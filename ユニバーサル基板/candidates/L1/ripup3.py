from common import *
from verify import verify
from detour import improve
import time
D=json.loads((HERE/'round2/placement.json').read_text(encoding='utf8'))
W=json.loads((HERE/'round2/wiring.json').read_text(encoding='utf8'))
R=verify(project(D,W));best=tuple(R['metrics']['lexicographic_sort_key']);history=[]
if (HERE/'wiring.ripup.json').exists():
 w=json.loads((HERE/'wiring.ripup.json').read_text(encoding='utf8'));r=verify(project(D,w))
 if tuple(r['metrics']['lexicographic_sort_key'])<best:W=w;R=r;best=tuple(r['metrics']['lexicographic_sort_key'])
for sweep in range(int(sys.argv[1]) if len(sys.argv)>1 else 2):
 initial=best
 ids=[c['id'] for c in W['conductors'] if c['kind']=='bare']
 for ii,cid in enumerate(ids):
  trial=copy.deepcopy(W);c=next((c for c in trial['conductors'] if c['id']==cid),None)
  if c is None or c['kind']!='bare':continue
  c['kind']='jumper';c['type']='insulated copper';c['gauge']={'1.0 mm':'AWG18','0.6 mm':'AWG22','0.51 mm':'AWG24','0.5 mm':'AWG24'}.get(c['gauge'],c['gauge']);c.pop('diameter_mm',None);c.pop('area_mm2',None)
  rr=verify(project(D,trial))
  if rr['metrics']['comparison_tuple'][:3]!=[True,0,0]:continue
  ww,rr,ev=improve(trial,D)
  key=tuple(rr['metrics']['lexicographic_sort_key'])
  history.append({'sweep':sweep,'converted':cid,'tuple':rr['metrics']['comparison_tuple'],'detours':ev})
  if key<best and rr['metrics']['t7_soft_penalty']<=242.639048:
   W=ww;R=rr;best=key;save_json(HERE/'wiring.ripup.json',W);save_json(HERE/'preview.ripup.json',R);print('BEST RIPUP',sweep,cid,key,flush=True)
  if ii%10==0:save_json(HERE/'search_ripup.json',history);print('PROGRESS',sweep,ii,flush=True)
 save_json(HERE/'search_ripup.json',history)
 if best==initial:break
print('FINAL',R['metrics']['comparison_tuple'],flush=True)
