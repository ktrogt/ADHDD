from pathlib import Path
import sys,json,math,csv,itertools,copy,shutil
from functools import lru_cache
HERE=Path(__file__).resolve().parent
SHARED=HERE.parent.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(SHARED/'tools'))
from model import Project,load_footprints,hole,point,rotate,rect_distance,save_json,path_points,compress,distance
FP=load_footprints(SHARED/'footprints_ub.json')['footprints']
REF=json.loads((SHARED/'footprints_ub.json').read_text(encoding='utf8'))['ref_to_type']
PITCH=2.54
@lru_cache(maxsize=None)
def geom(fid,x,y,r=0):
 f=FP[fid];b=f['body_mm']; cs=[rotate((a,z),r) for a in [b['x'],b['x']+b['width']] for z in [b['y'],b['y']+b['height']]]
 return (x*PITCH+min(a for a,z in cs),y*PITCH+min(z for a,z in cs),x*PITCH+max(a for a,z in cs),y*PITCH+max(z for a,z in cs)),{p['number']:(x+rotate((p['dx'],p['dy']),r)[0],y+rotate((p['dx'],p['dy']),r)[1]) for p in f['pins']}
def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def project(placement=None,wiring=None):return Project(HERE,board=json.loads((SHARED/'board.json').read_text(encoding='utf8')),placement=placement,wiring=wiring)
