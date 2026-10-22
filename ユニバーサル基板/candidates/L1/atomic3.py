from common import *
from verify import verify
from detour import improve
from collections import Counter
D=json.loads((HERE/'round2/placement.json').read_text(encoding='utf8'))
W=json.loads((HERE/'round2/wiring.json').read_text(encoding='utf8'));R=verify(project(D,W));best=tuple(R['metrics']['lexicographic_sort_key'])
for name in ['wiring.ripup.json','wiring.ripup_late.json','wiring.atomic.json']:
 if (HERE/name).exists():
  w=json.loads((HERE/name).read_text(encoding='utf8'));r=verify(project(D,w));key=tuple(r['metrics']['lexicographic_sort_key'])
  if key<best:W=w;R=r;best=key
history=[]
for sweep in range(int(sys.argv[1]) if len(sys.argv)>1 else 2):
 initial=best;p=project(D,W);pinpoints={v.xy for v in p.pins.values()};count=Counter(q for c in p.conductors for q in set(c['contacts']))
 tasks=[]
 for c in W['conductors']:
  if c['kind']!='bare':continue
  pts=path_points([point(z) for z in c['path']]);cuts=[i for i,q in enumerate(pts) if i in [0,len(pts)-1] or q in pinpoints or count[q]>1]
  for a,b in zip(cuts,cuts[1:]):
   if b-a>1:tasks.append((c['id'],pts[a],pts[b]))
 for ii,(cid,src,dst) in enumerate(tasks):
  c=next((v for v in W['conductors'] if v['id']==cid and v['kind']=='bare'),None)
  if c is None:continue
  pts=path_points([point(z) for z in c['path']])
  if src not in pts or dst not in pts:continue
  a,b=pts.index(src),pts.index(dst)
  if b<=a:continue
  jumper=copy.deepcopy(c);jumper.update(kind='jumper',type='insulated copper',path=[hole(z) for z in compress(pts[a:b+1])],id=cid+'J'+str(sweep)+'_'+str(ii))
  jumper['gauge']={'1.0 mm':'AWG18','0.6 mm':'AWG22','0.51 mm':'AWG24','0.5 mm':'AWG24'}.get(c['gauge'],c['gauge']);jumper.pop('diameter_mm',None);jumper.pop('area_mm2',None)
  pieces=[]
  for tag,z in [('A',pts[:a+1]),('B',pts[b:])]:
   if len(z)>1:
    part=copy.deepcopy(c);part.update(id=cid+tag+str(sweep)+'_'+str(ii),path=[hole(q) for q in compress(z)]);pieces.append(part)
  trial=copy.deepcopy(W);trial['conductors']=[z for z in trial['conductors'] if z['id']!=cid]+pieces+[jumper]
  rr=verify(project(D,trial))
  if rr['metrics']['comparison_tuple'][:3]!=[True,0,0]:continue
  ww,rr,ev=improve(trial,D)
  key=tuple(rr['metrics']['lexicographic_sort_key']);history.append({'sweep':sweep,'id':cid,'from':hole(src),'to':hole(dst),'tuple':rr['metrics']['comparison_tuple'],'detours':ev})
  if key<best and rr['metrics']['t7_soft_penalty']<=242.639048:
   W=ww;R=rr;best=key;save_json(HERE/'wiring.atomic.json',W);save_json(HERE/'preview.atomic.json',R);print('BEST ATOMIC',sweep,ii,cid,hole(src),hole(dst),key,flush=True)
  if ii%10==0:print('ATOMIC PROGRESS',sweep,ii,'/',len(tasks),flush=True);save_json(HERE/'search_atomic.json',history)
 save_json(HERE/'search_atomic.json',history)
 if best==initial:break
print('ATOMIC FINAL',R['metrics']['comparison_tuple'],flush=True)
