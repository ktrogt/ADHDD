"""Candidate L2 local helpers; shared inputs/tools are read-only."""
import sys, json, shutil, math, itertools, random, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
from model import Project, save_json, rotate, hole, rect_distance, rect_intersects, point
from verify import verify, placement_drc
FPS=json.loads((ROOT/'footprints_ub.json').read_text(encoding='utf-8'))
RULES=json.loads((ROOT/'design_rules.json').read_text(encoding='utf-8'))

def geom(fpname, xy, r):
    f=FPS['footprints'][fpname]; x,y=xy
    pins={p['number']:(x+rotate((p['dx'],p['dy']),r)[0],y+rotate((p['dx'],p['dy']),r)[1]) for p in f['pins']}
    b=f['body_mm']; c=[rotate((a,d),r) for a in (b['x'],b['x']+b['width']) for d in (b['y'],b['y']+b['height'])]
    rect=(x*2.54+min(a for a,d in c),y*2.54+min(d for a,d in c),x*2.54+max(a for a,d in c),y*2.54+max(d for a,d in c))
    return pins,rect
def md(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
def choices(fp, pairs, gap_to=(), gap=1.016, n=15):
    out=[]
    for x,y,r in itertools.product(range(-n,n+1),range(-n,n+1),(0,90,180,270)):
        p,b=geom(fp,(x,y),r)
        if all(md(p[a],target)<=bound for a,target,bound in pairs) and all(rect_distance(b,t)>=gap-1e-8 for t in gap_to):
            out.append(((x,y,r),p,b))
    return out
def tile_probe():
    dp,db=geom('POLOLU4035_SOCKET_5H',(0,0),0)
    caps=choices('C100NF_1H',[('1',dp['14'],2),('2',dp['13'],2)],[db])
    cons=choices('COIL_XH3_OUTER',[('1',dp['12'],4),('2',dp['11'],4)],[db])
    combos=[(c[0],j[0],rect_distance(c[2],j[2])) for c in caps for j in cons if rect_distance(c[2],j[2])>=1.016-1e-8]
    result={'driver_rotation':0,'valid_caps':[c[0] for c in caps],'valid_connectors':[c[0] for c in cons],'valid_pairs':combos,
      'bounds':'M01 >=1.016mm; P05 <=2 Manhattan holes each; P11 <=4 Manhattan holes each. All integer origins in [-15,15]^2, all rotations. This contains every possible solution because P05/P11 bound pin1 distance.'}
    for lim in (5,6):
        cc=choices('COIL_XH3_OUTER',[('1',dp['12'],lim),('2',dp['11'],lim)],[db])
        result['pairs_if_P11_'+str(lim)]=[(c[0],j[0],round(rect_distance(c[2],j[2]),6)) for c in caps for j in cc if rect_distance(c[2],j[2])>=1.016-1e-8]
    save_json(HERE/'tile_feasibility.json',result)
    print(json.dumps(result,indent=2))

def feasibility():
    result={}
    for cr in (0,90,180,270):
        cp,cb=geom('CP470_D10_2H',(0,0),cr)
        result['TVS_bulk_rotation_'+str(cr)]={}
        for lim in (3,4,5,6):
            cc=choices('D_DO41_4H_D105',[('1',cp['1'],lim),('2',cp['2'],lim)],[cb],n=9)
            result['TVS_bulk_rotation_'+str(cr)][lim]=[c[0] for c in cc]
    up,ub=geom('M78AR05_SIP3',(0,0),0)
    for target in ('1','3'):
        result['regulator_cap_'+target]={}
        for lim in (4,5,6,7):
            cc=choices('CP100_D63_1H',[('1',up[target],lim),('2',up['2'],lim)],[ub],gap=2.54,n=10)
            result['regulator_cap_'+target][lim]=[c[0] for c in cc]
    vp,vb=geom('C220NF_2H',(0,0),0)
    result['R210_VREF']= [c[0] for c in choices('R_MFS25_3H',[('1',vp['1'],2),('2',vp['2'],2)],[vb],n=8)]
    up,ub=geom('AHC125_DIP6_DIRECT',(0,0),0)
    result['buffer_cap']=[c[0] for c in choices('C100NF_1H',[('1',up['5'],2),('2',up['3'],2)],[ub],n=8)]
    save_json(HERE/'feasibility.json',result)
    print(json.dumps(result,indent=2))

def part(ref,x,y,r=0,locked=False):
    return dict(footprint=FPS['ref_to_type'][ref],hole=hole((x,y)),rotation=r,locked=locked,substitution_approved=True,value=FPS['footprints'][FPS['ref_to_type'][ref]].get('part',ref))
def seed():
    bootstrap()
    ps={}
    def put(ref,x,y,r=0,locked=False): ps[ref]=part(ref,x,y,r,locked)
    for k,(x,y) in enumerate(((17,7),(34,7),(17,32),(34,32)),1):
        base=300+10*k
        put('U'+str(base),x,y,0,True)
        put('C'+str(base+1),x+5,y-5,90,True)
        put('C'+str(base+2),x+7,y,90,True)
        put('J'+str(base+3),x+8,y+3,90,True)
        put('TP'+str(470+k),x+7,y+7,0,True)
    put('U201',53,17,90,True)
    put('J101',5,23,90,True)
    put('C106',3,20,0,True)
    put('D105',2,16,0,True)
    put('J104',1,18,90,True)
    put('F102',4,6,0,True)
    put('D103',4,33,0,True)
    put('U107',13,23,0,True)
    put('C108',13,17,0,True)
    put('C109',15,29,180,True)
    put('D110',30,25,180)
    put('C211',24,21,0,True)
    put('R209',21,18,0)
    put('R210',23,24,0)
    put('TP466',22,21)
    put('U207',48,11,0,True)
    put('C208',48,8,0)
    put('J202',52,4,90,True)
    put('J203',52,8,90,True)
    put('R204',49,7,270)
    put('R205',44,10,0)
    put('D206',44,12,0)
    put('R212',35,16,0)
    put('J213',53,28,90,True)
    put('R214',50,28,180)
    put('R215',32,16,270)
    put('TP460',10,12)
    put('TP461',19,23)
    put('TP462',48,26)
    put('TP463',2,24)
    put('TP464',19,25)
    put('TP465',29,20)
    put('TP467',45,28)
    put('TP468',32,13)
    assert set(ps)==set(FPS['scope_refs']),set(FPS['scope_refs'])-set(ps)
    save_json(HERE/'placement.json',dict(schema_version=1,parts=ps))
    save_json(HERE/'wiring.json',dict(schema_version=1,conductors=[]))
    p=Project(HERE)
    nodes={k:hole(p.pin_at(v['anchor'].replace('.', '.#'))) for k,v in RULES['nodes'].items()}
    save_json(HERE/'placement.json',dict(schema_version=1,parts=ps,nodes=nodes))
    print('SEED',len(ps)); print('\n'.join(str(i) for i in placement_drc(p) if i['severity']=='error'))

def place_search(iterations=10000):
    """Local annealing for physical separation and closest possible bypass leads.
    Does not edit, waive or replace the official rules or verification.
    """
    p=Project(HERE); data=p.placement
    refs=list(data['parts']); pitch=2.54
    mutable=[r for r in refs if not data['parts'][r].get('locked')]
    # Preserve the floor-plan and carrier tiles. Only the small loose controls move.
    cache={}
    def geometry(ref,x,y,r):
        key=ref,x,y,r
        if key not in cache: cache[key]=geom(FPS['ref_to_type'][ref],(x,y),r)
        return cache[key]
    state={ref:(*point(a['hole']),a.get('rotation',0)) for ref,a in data['parts'].items()}
    near=[]; therm=[]
    groups=RULES['groups']
    def expand(s):
        if isinstance(s,list): return sum((expand(i) for i in s),[])
        if s=='all_populated': return refs
        if s.startswith('@'): return expand(groups[s[1:]])
        return [s]
    for rule in RULES['rules']:
        z=rule['params']
        if rule['type']=='near':
            for v in z['pairs']: near.append((v['a'],v['b'],z['max_holes'],100 if rule['severity']=='hard' else 2))
        if rule['type']=='min_part_distance' and rule['id']!='M01':
            for a in expand(z['a']):
                for b in expand(z['b']):
                    if a!=b: therm.append((a,b,z['min_holes']*pitch,1000 if rule['severity']=='hard' else 2))
    def score(st):
        g={ref:geometry(ref,*st[ref]) for ref in refs}; value=0
        def pin(sel):
            if sel.startswith('$'): sel=RULES['nodes'][sel[1:]]['anchor']
            a,b=sel.split('.'); return g[a][0][b]
        for a,b,bound,w in near:
            value+=w*max(0,md(pin(a),pin(b))-bound)**2
        for a,b,bound,w in therm: value+=w*max(0,bound-rect_distance(g[a][1],g[b][1]))**2
        for i,a in enumerate(refs):
            pa,ba=g[a]
            value+=100000*sum(max(0,z)**2 for z in (-1.27-ba[0],-1.27-ba[1],ba[2]-138.43,ba[3]-100.33))
            if any(not p.usable(q) for q in pa.values()): value+=1e6
            for b in refs[i+1:]:
                pb,bb=g[b]; dist=rect_distance(ba,bb)
                if rect_intersects(ba,bb):
                    depth=min(ba[2]-bb[0],bb[2]-ba[0],ba[3]-bb[1],bb[3]-ba[1])
                    value+=100000*(1+depth)**2
                else: value+=100000*max(0,1.016-dist)**2
                if set(pa.values())&set(pb.values()): value+=1e7
        # Secondary wire estimate attracts probe/loose parts to their nets.
        for ref in mutable:
            for pn,xy in g[ref][0].items():
                pin_obj=next(q for q in p.parts[ref].pins if q.number==pn)
                others=[g[q.ref][0][q.number] for q in p.pins.values() if q.net==pin_obj.net and q.ref!=ref and q.net!='NC']
                if others: value+=0.02*min(md(xy,q) for q in others)
        return value
    rng=random.Random(22); cur=score(state); best=cur; bst=dict(state); start=time.time()
    for it in range(iterations):
        ref=rng.choice(mutable); x,y,r=state[ref]; trial=dict(state)
        if rng.random()<0.15: nr=rng.choice((0,90,180,270)); nx,ny=x,y
        else:
            span=5 if rng.random()<0.1 else 1; nx=max(0,min(54,x+rng.randint(-span,span))); ny=max(0,min(39,y+rng.randint(-span,span))); nr=r
        trial[ref]=(nx,ny,nr); val=score(trial); temp=max(0.3,100*(1-it/iterations)**3)
        if val<cur or rng.random()<math.exp(max(-700,(cur-val)/temp)): state,cur=trial,val
        if cur<best: best=cur; bst=dict(state)
        if it%1000==0: print(it,round(cur,2),round(best,2),'seconds',round(time.time()-start,1),flush=True)
    for ref,(x,y,r) in bst.items(): data['parts'][ref].update(hole=hole((x,y)),rotation=r)
    save_json(HERE/'placement.json',data)
    print('BEST',best)
    print('\n'.join(str(i) for i in placement_drc(Project(HERE)) if i['severity']=='error'))

def bootstrap():
    for a,b in [('board.json','board.json'),('footprints_ub.json','footprints_ub.json'),('netlist_ub.csv','netlist.csv'),('design_rules.json','design_rules.json')]:
        shutil.copyfile(ROOT/a,HERE/b)

if __name__=='__main__':
    if sys.argv[1]=='tile': tile_probe()
    elif sys.argv[1]=='feasibility': feasibility()
    elif sys.argv[1]=='bootstrap': bootstrap()
    elif sys.argv[1]=='seed': seed()
    elif sys.argv[1]=='place': place_search(int(sys.argv[2]) if len(sys.argv)>2 else 10000)
