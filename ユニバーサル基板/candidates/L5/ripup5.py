from layout5 import *
from collections import Counter

def split(p,w):
    q=p.clone(wiring=w);counts=Counter(xy for c in q.conductors for xy in set(c['contacts']))
    pins={s.xy for s in q.pins.values()};out=[];serial=0
    for raw,c in zip(w['conductors'],q.conductors):
        if c['kind']!='bare' or c.get('branch','').startswith('DRIVER_CH') or c.get('branch') in ['VM_TRUNK','POWER_RETURN_TRUNK','INPUT_RETURN']:
            out.append(copy.deepcopy(raw));continue
        pts=c['contacts'];cuts=[i for i,xy in enumerate(pts) if i in [0,len(pts)-1] or xy in pins or counts[xy]>1]
        for a,b in zip(cuts,cuts[1:]):
            serial+=1;d=copy.deepcopy(raw);d['id']=f'L5S{serial:03d}';d['path']=[hole(x) for x in compress(pts[a:b+1])];out.append(d)
    return dict(schema_version=1,conductors=out)

def state(p,w):
    q=p.clone(wiring=w);rr=L5Router(q,{'routing_rows':29})
    rr.out=copy.deepcopy(w['conductors']);rr.serial=1000
    for c in q.conductors:
        grp=c.get('route_group',c['net'])
        for xy in c['contacts']:
            rr.occupied[xy].add(grp);rr.locations[grp].add(xy);rr.uf.union(c['contacts'][0],xy)
    return q,rr

def bareify(p,w,seed=0):
    ids=[c['id'] for c in w['conductors'] if c['kind']=='jumper' and not c.get('branch','').startswith('DRIVER_CH')]
    rng=random.Random(seed);rng.shuffle(ids)
    for cid in ids:
        source=next((c for c in w['conductors'] if c['id']==cid),None)
        if source is None:continue
        remaining=dict(schema_version=1,conductors=[c for c in w['conductors'] if c['id']!=cid])
        q,rr=state(p,remaining);a,b=point(source['path'][0]),point(source['path'][-1])
        if rr.uf.find(a)==rr.uf.find(b):w=remaining;continue
        grp=source.get('route_group',source['net']);blocked=rr.blocked(grp,ends={a,b})
        path=astar(q,a,{b},blocked,1.5)
        if path is None:continue
        direct=abs(a[0]-b[0])+abs(a[1]-b[1])
        if len(path)-1>direct+10:continue
        d=copy.deepcopy(source);d.update(kind='bare',side='bottom',type='tinned copper',path=[hole(x) for x in compress(path)])
        w=dict(schema_version=1,conductors=remaining['conductors']+[d])
    return w

def run(rounds=10):
    prefix='post' if (HERE/'post_wiring.json').exists() else 'best'
    pl=load_json(HERE/'best_placement.json');p=project(pl)
    w=split(p,load_json(HERE/f'{prefix}_wiring.json'));r=verify(p.clone(wiring=w))
    best=tuple(r['metrics']['lexicographic_sort_key']);logs=[]
    for rnd in range(rounds):
        improved=False
        candidates=[None]+[c['id'] for c in w['conductors'] if c['kind']=='bare' and not c.get('branch','').startswith('DRIVER_CH') and c.get('branch') not in ['VM_TRUNK','POWER_RETURN_TRUNK','INPUT_RETURN']]
        random.Random(rnd).shuffle(candidates)
        for it,cid in enumerate(candidates):
            trial=copy.deepcopy(w)
            if cid is not None:
                c=next(c for c in trial['conductors'] if c['id']==cid);c.update(kind='jumper',type='insulated copper')
            trial=bareify(p,trial,rnd*1000+it)
            try:
                r=verify(p.clone(wiring=trial));m=r['metrics'];key=tuple(m['lexicographic_sort_key'])
                if key[:4]<best[:4]:
                    best=key;w=trial;improved=True
                    save_json(HERE/'post_wiring.json',w);save_json(HERE/'post_report.json',r)
                    logs.append(dict(round=rnd,trial=it,blocker=cid,comparison=m['comparison_tuple']));save_json(HERE/'ripup_log.json',logs)
                    print('POST BEST',rnd,it,cid,m['comparison_tuple'],flush=True)
                    break
            # Equal-jumper wire trimming must not consume a whole search round.
            except Exception as e:print('ERROR',str(e),flush=True)
        print('ROUND',rnd,'improved',improved,flush=True)
        if not improved:break
    print('POST DONE',best,flush=True)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 10)
