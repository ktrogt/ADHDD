"""Exhaustive local tile geometry and same-column four-tile packing, v0.2."""
import sys,json,math,time,itertools
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent
sys.path.insert(0,str(BASE/'tools'))
from model import Project,load_footprints,load_json,save_json,rotate,rect_distance,rect_intersects,point,hole
F=load_footprints(BASE/'footprints_ub.json');REF=F['ref_to_type'];P=Project(HERE,board=load_json(BASE/'board.json'))
PITCH=2.54
ROLE={'U':'U310','B':'C311','C':'C312','J':'J313'}
def shape(role,x,y,r):
    fp=F['footprints'][REF[ROLE[role]]]
    b=fp['body_mm'];corn=[rotate((a,c),r) for a in [b['x'],b['x']+b['width']] for c in [b['y'],b['y']+b['height']]]
    rect=(x*PITCH+min(a for a,b in corn),y*PITCH+min(b for a,b in corn),x*PITCH+max(a for a,b in corn),y*PITCH+max(b for a,b in corn))
    pins={}
    for q in fp['pins']:
        dx,dy=rotate((q['dx'],q['dy']),r);pins[q['number']]=(x+dx,y+dy)
    pads=set(pins.values())
    for q in fp.get('extra_pads',[]):
        dx,dy=rotate((q['dx'],q['dy']),r);pads.add((x+dx,y+dy))
    return {'role':role,'x':x,'y':y,'r':r,'rect':rect,'pins':pins,'pads':pads}
def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def compatible(a,b,driver_gap=7.62):
    if a['pads'] & b['pads']:return False
    d=driver_gap if a['role']==b['role']=='U' else 2.54 if set([a['role'],b['role']])=={'U','B'} else 1.016
    return rect_distance(a['rect'],b['rect'])>=d-1e-8
def part_ok(a):
    r=a['rect'];br=P.board_rect;m=P.board.get('body_edge_margin_mm',1)
    if r[0]<br[0]+m-1e-8 or r[1]<br[1]+m-1e-8 or r[2]>br[2]-m+1e-8 or r[3]>br[3]-m+1e-8:return False
    if any(not P.usable(z) for z in a['pads']):return False
    for x,z,_ in P.keepouts:
        k=((x[0]-.5)*PITCH,(x[1]-.5)*PITCH,(z[0]+.5)*PITCH,(z[1]+.5)*PITCH)
        if rect_intersects(r,k):return False
    return True
def edge(a):
    f=F['footprints'][REF[ROLE[a['role']]]]['features']['mating_face']
    dx,dy=rotate((f['x_mm'],f['y_mm']),a['r'])
    return P.edge_distance((a['x']*PITCH+dx,a['y']*PITCH+dy),['N','E','S','W'],'grid_boundary')/PITCH
def patterns():
    u=shape('U',0,0,0);opts={}
    for role,bound,pairs in [('B',6,[('1','14'),('2','13')]),('C',3,[('1','14'),('2','13')]),('J',5,[('1','12'),('2','11')])]:
        arr=[]
        for r in [0,90,180,270]:
            for x in range(-12,13):
                for y in range(-12,13):
                    a=shape(role,x,y,r)
                    if max(man(a['pins'][aa],u['pins'][bb]) for aa,bb in pairs)>bound:continue
                    if compatible(u,a):arr.append(a)
        opts[role]=arr
        print('independent',role,len(arr),flush=True)
    allp=[]
    for b in opts['B']:
        for c in opts['C']:
            if not compatible(b,c):continue
            for j in opts['J']:
                if compatible(b,j) and compatible(c,j):allp.append([u,b,c,j])
    print('joint relative patterns',len(allp),flush=True)
    return allp
def translated(pat,x,y,r):
    ans=[]
    for a in pat:
        dx,dy=rotate((a['x'],a['y']),r)
        ans.append(shape(a['role'],x+dx,y+dy,(a['r']+r)%360))
    return ans
def all_ok(tile):return all(part_ok(a) for a in tile) and edge(tile[3])<=2+1e-8
def tiles_compatible(a,b,gap):return all(compatible(x,y,gap) for x in a for y in b)
def serial(tile):return [{k:a[k] for k in ['role','x','y','r']} for a in tile]

def search(pats,gap=7.62):
    stats=[];solutions=[]
    for r in [0,90,180,270]:
        minpitch=math.ceil(((18.38 if r in [0,180] else 15.84)+gap)/PITCH-1e-8)
        maxcount=0;valid_total=0;bycolumn={}
        for x in range(P.columns):
            by_y={}
            for y in range(P.rows):
                # Driver placement is cheaper to reject before every tile pattern.
                if not part_ok(shape('U',x,y,r)):continue
                tt=[]
                for pat in pats:
                    tile=translated(pat,x,y,r)
                    if all_ok(tile):tt.append(tile)
                if tt:by_y[y]=tt;valid_total+=len(tt)
            bycolumn[x]=sorted(by_y)
            def dfs(chosen,ys):
                nonlocal maxcount
                maxcount=max(maxcount,len(chosen))
                if len(chosen)==4:
                    solutions.append({'rotation':r,'column':x,'tiles':[serial(t) for t in chosen]});return True
                for y in ys:
                    if chosen and y-chosen[-1][0]['y']<minpitch:continue
                    # Simple remaining-height bound.
                    if y+(3-len(chosen))*minpitch>max(by_y):continue
                    for t in by_y[y]:
                        if all(tiles_compatible(t,u,gap) for u in chosen):
                            if dfs(chosen+[t],[z for z in ys if z>y]):return True
                return False
            if by_y:dfs([],sorted(by_y))
            if solutions:return {'driver_gap_mm':gap,'rotation_stats':stats,'solution':solutions[0]}
        stats.append({'rotation':r,'minimum_origin_pitch_holes':minpitch,'valid_tile_placements':valid_total,'maximum_four_search_depth':maxcount,'origin_rows_by_column':bycolumn})
        print('rotation',r,'valid',valid_total,'max depth',maxcount,flush=True)
    return {'driver_gap_mm':gap,'rotation_stats':stats,'solution':None}

if __name__=='__main__':
    pats=patterns()
    save_json(HERE/'r2_local_patterns.json',[[{k:a[k] for k in ['role','x','y','r']} for a in t] for t in pats])
    results=search(pats)
    save_json(HERE/'out/r2_column_feasibility.json',results)
    print('STRICT',json.dumps(results.get('solution')),flush=True)
    if results['solution'] is None:
        relaxed=search(pats,7.02)
        save_json(HERE/'out/r2_column_gap7p02.json',relaxed)
        print('RELAXED',json.dumps(relaxed.get('solution')),flush=True)
