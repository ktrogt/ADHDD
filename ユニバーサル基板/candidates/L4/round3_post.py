"""Local conductor rip-up: insulate one blocker, make several jumpers bare."""
from round3_route import *
from quality_local import check_quiet
from collections import Counter

def state(p,w):
    q=p.clone(wiring=w);rr=Router(q)
    rr.out=copy.deepcopy(w['conductors']);rr.serial=500
    for c in q.conductors:
        grp=c.get('route_group',c['net'])
        for xy in c['contacts']:
            rr.occupied[xy].add(grp);rr.locations[grp].add(xy);rr.uf.union(c['contacts'][0],xy)
    return q,rr

def split(p,w):
    q=p.clone(wiring=w);counts=Counter(xy for c in q.conductors for xy in set(c['contacts']))
    pins={s.xy for s in q.pins.values()};out=[];serial=0
    for raw,c in zip(w['conductors'],q.conductors):
        if c['kind']!='bare' or c.get('branch','').startswith('DRIVER_CH') or c.get('branch') in ['VM_TRUNK','POWER_RETURN_TRUNK','INPUT_RETURN']:
            out.append(copy.deepcopy(raw));continue
        pts=c['contacts'];cuts=[i for i,xy in enumerate(pts) if i in [0,len(pts)-1] or xy in pins or counts[xy]>1]
        for a,b in zip(cuts,cuts[1:]):
            serial+=1;d=copy.deepcopy(raw);d['id']=f'R3S{serial:03d}';d['path']=[hole(x) for x in compress(pts[a:b+1])];out.append(d)
    return dict(schema_version=1,conductors=out,method='R3 split at solder junctions')

def bareify(p,w,seed):
    rng=random.Random(seed)
    ids=[c['id'] for c in w['conductors'] if c['kind']=='jumper'];rng.shuffle(ids)
    for cid in ids:
        source=next((c for c in w['conductors'] if c['id']==cid),None)
        if source is None:continue
        if source.get('branch','').startswith('DRIVER_CH'):continue
        remaining=dict(schema_version=1,conductors=[c for c in w['conductors'] if c['id']!=cid])
        q,rr=state(p,remaining);a,b=point(source['path'][0]),point(source['path'][-1])
        if rr.uf.find(a)==rr.uf.find(b):w=remaining;continue
        grp=source.get('route_group',source['net']);blocked=rr.blocked(grp,ends={a,b})
        path=astar(q,a,{b},blocked,.5)
        if path is None:continue
        direct=abs(a[0]-b[0])+abs(a[1]-b[1])
        if len(path)-1>direct+8:continue
        d=copy.deepcopy(source);d.update(kind='bare',side='bottom',type='tinned copper',path=[hole(x) for x in compress(path)])
        w=dict(schema_version=1,conductors=remaining['conductors']+[d])
    return w

def run(rounds=5):
    p=Project(HERE,placement=load_json(HERE/'r3_improved_placement.json'))
    w=split(p,load_json(HERE/'r3_improved_wiring.json'));best=tuple(load_json(HERE/'r3_improved_report.json')['metrics']['lexicographic_sort_key'])
    save_json(HERE/'r3_post_placement.json',p.placement)
    for rnd in range(rounds):
        improved=False
        # Include no blocker as a cheap first pass.
        candidates=[None]+[c['id'] for c in w['conductors'] if c['kind']=='bare' and not c.get('branch','').startswith('DRIVER_CH') and c.get('branch') not in ['VM_TRUNK','POWER_RETURN_TRUNK','INPUT_RETURN']]
        for it,cid in enumerate(candidates):
            trial=copy.deepcopy(w)
            if cid is not None:
                c=next(c for c in trial['conductors'] if c['id']==cid)
                c.update(kind='jumper',type='insulated copper')
            try:
                trial=bareify(p,trial,rnd*10000+it)
                q=p.clone(wiring=trial);r=verify(q);m=r['metrics'];key=tuple(m['lexicographic_sort_key'])
                if key<best and m['t7_soft_penalty']<=225.624726*1.1 and check_quiet(q,'S01')['planar_wire_and_body_pass'] and check_quiet(q,'S02')['planar_wire_and_body_pass']:
                    best=key;w=trial;improved=True
                    save_json(HERE/'r3_post_wiring.json',w);save_json(HERE/'r3_post_report.json',r)
                    print('POST BEST',rnd,it,cid,m['comparison_tuple'],flush=True)
                    break
            except Exception as e:print('POST ERR',rnd,it,str(e),flush=True)
        if not improved:break
    print('POST DONE',best,flush=True)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 5)
