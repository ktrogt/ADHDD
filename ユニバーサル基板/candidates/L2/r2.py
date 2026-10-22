"""L2 round 2 geometry, construction and local search. Shared files read-only."""
import sys,json,math,itertools,random,time,csv,copy
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from model import Project,load_json,save_json,rotate,hole,point,rect_distance,rect_intersects,path_points,compress
from verify import verify,placement_drc,net_graph,shortest
FPS=json.loads((H/'footprints_ub.json').read_text(encoding='utf-8'));FP=FPS['footprints']
RULES=load_json(H/'design_rules.json',('adhdd-perfboard-rules/1.0',));BOARD=load_json(ROOT/'board.json')
def project(**kwargs):return Project(H,board=BOARD,**kwargs)
def md(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def geom(fpname,xy=(0,0),r=0):
 f=FP[fpname];x,y=xy
 pins={p['number']:(x+rotate((p['dx'],p['dy']),r)[0],y+rotate((p['dx'],p['dy']),r)[1]) for p in f['pins']}
 b=f['body_mm'];cs=[rotate((xx,yy),r) for xx in (b['x'],b['x']+b['width']) for yy in (b['y'],b['y']+b['height'])]
 rect=x*2.54+min(a for a,b in cs),y*2.54+min(b for a,b in cs),x*2.54+max(a for a,b in cs),y*2.54+max(b for a,b in cs)
 extra={(x+rotate((p['dx'],p['dy']),r)[0],y+rotate((p['dx'],p['dy']),r)[1]) for p in f.get('extra_pads',[])}
 return dict(fp=fpname,xy=xy,r=r,pins=pins,rect=rect,pads=set(pins.values())|extra)
def candidates(fp,targets,gap=[]):
 out=[]
 for x,y,r in itertools.product(range(-10,16),range(-10,16),(0,90,180,270)):
  a=geom(fp,(x,y),r)
  if all(md(a['pins'][pn],p)<=n for pn,p,n in targets) and all(rect_distance(a['rect'],b['rect'])>=d-1e-8 and not(a['pads']&b['pads']) for b,d in gap):out.append(a)
 return out
def tile_enum():
 d=geom('POLOLU4035_SOCKET_5H');p=d['pins']
 caps=candidates('C100NF_1H',[('1',p['14'],3),('2',p['13'],3)],[(d,1.016)])
 coils=candidates('COIL_XH3_OUTER',[('1',p['12'],5),('2',p['11'],5)],[(d,1.016)])
 bulks=candidates('CP470_D10_2H',[('1',p['14'],6),('2',p['13'],6)],[(d,2.54)])
 combos=[]
 for c,j,b in itertools.product(caps,coils,bulks):
  if all(rect_distance(a['rect'],z['rect'])>=1.016-1e-8 and not(a['pads']&z['pads']) for a,z in [(c,j),(c,b),(j,b)]):
   for y0 in range(0,34):
    pads=d['pads']|c['pads']|j['pads']|b['pads']
    if min(y for x,y in pads)+y0<0 or max(y for x,y in pads)+y0>39:continue
    v=rotate((2.54,0),j['r']);cy=y0+j['xy'][1]+v[1]/2.54
    north=cy; south=39-cy
    if min(north,south)<=2+1e-8:combos.append(dict(cap=[*c['xy'],c['r']],coil=[*j['xy'],j['r']],bulk=[*b['xy'],b['r']],driver_y=y0,edge='N' if north<=2 else 'S'))
 out=dict(cap_count=len(caps),coil_count=len(coils),bulk_count=len(bulks),NS_candidates=combos)
 save_json(H/'tile_search.json',out);print(json.dumps(out,indent=2))
def put(ref,x,y,r=0,locked=True,value=None):
 return dict(footprint=FPS['ref_to_type'][ref],hole=hole((x,y)),rotation=r,locked=locked,substitution_approved=True,value=value or FP[FPS['ref_to_type'][ref]].get('part',ref))
def seed():
 ps={}
 def add(ref,x,y,r=0):ps[ref]=put(ref,x,y,r)
 # Fold F2's upper pair onto the east edge, retaining identical carrier rotation.
 # CH1/2 serve the south pair, CH3/4 the east pair, following Pico GP2..GP9.
 for k,(x,y,edge) in enumerate([(12,33,'S'),(31,33,'S'),(44,16,'E'),(44,5,'E')],1):
  n=300+10*k;add(f'U{n}',x,y)
  if edge=='E':
   if k==4:
    add(f'C{n+1}',x+4,y-5,90);add(f'C{n+2}',x+7,y-1,90);add(f'J{n+3}',x+8,y+2,90)
   else:
    add(f'C{n+1}',x+9,y-2,90);add(f'C{n+2}',x+4,y-2);add(f'J{n+3}',x+8,y+3,90)
   add(f'TP{470+k}',x+7,y+6 if k==4 else y+8)
  else:
   add(f'C{n+1}',x+4,y-5,90);add(f'C{n+2}',x+7,y,90);add(f'J{n+3}',x+8,y+3,90)
   add(f'TP{470+k}',21 if k==1 else x+11,34 if k==1 else y+6)
 for ref,x,y,r in [
 ('U201',10,39,180),('J101',5,12,90),('F102',13,1,0),('D103',4,1,0),('J104',1,7,90),('D105',2,5,0),('C106',3,9,0),
 ('U107',18,16,0),('C108',13,15,90),('C109',25,15,90),('D110',18,25,0),
 ('C211',23,22,0),('R209',19,21,0),('R210',22,24,0),('U207',25,34,0),('C208',26,32,180),
 ('J202',23,39,0),('J203',27,39,0),('R204',23,37,270),('R205',26,31,0),('D206',29,29,180),
 ('R215',12,21,270),('R214',0,22,90),('J213',0,19,90),('R212',14,22,270),
 ('TP460',8,10,0),('TP461',24,12,0),('TP462',1,35,0),('TP463',8,12,0),('TP464',20,11,0),
 ('TP465',28,22,0),('TP466',24,20,0),('TP467',1,27,0),('TP468',9,18,0)]:add(ref,x,y,r)
 assert set(ps)==set(FPS['scope_refs'])
 pl=dict(schema_version=1,parts=ps);save_json(H/'placement.json',pl);save_json(H/'wiring.json',dict(schema_version=1,conductors=[]))
 p=project();pl['nodes']={k:hole(p.pin_at(v['anchor'].replace('.', '.#'))) for k,v in RULES['nodes'].items()};save_json(H/'placement.json',pl)
 p=project();issues=placement_drc(p)
 from rules import evaluate
 issues+=evaluate(p,placement_only=True)
 print('\n'.join(i['code']+': '+i['detail'] for i in issues if i['severity']=='error' and i.get('status')!='UNCHECKED'))
 print('seeded',len(ps),'parts')
if __name__=='__main__':
 if sys.argv[1]=='tiles':tile_enum()
 elif sys.argv[1]=='seed':seed()
