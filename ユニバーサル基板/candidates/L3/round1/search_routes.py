"""L3-only routing-order search, preserving original rules in every report."""
import sys,copy,json,argparse,collections,time
from pathlib import Path
sys.dont_write_bytecode=True
import route_candidate as rc
from model import Project,load_json,save_json,point,hole,compress
from verify import verify,summary,wiring_drc,extract
import router
HERE=rc.HERE

def variant_seed(v):
    w=load_json(HERE/'wiring.seed.json')
    if v==1:
        paths={3:[(43,17),(30,17),(30,23)],
               2:[(43,28),(31,28),(31,23),(30,23)],
               1:[(43,39),(30,39),(30,23)]}
        for c in w['conductors']:
            for ch,path in paths.items():
                if c['id']==f'VREF_CH{ch}':
                    c.update(kind='bare',path=[hole(z) for z in path],type='tinned copper')
    return w

def polish(w):
    # Short straight insulated wires; retain intentional FAULT escape bends.
    for c in w['conductors']:
        if c['kind']=='jumper' and not c['locked']:
            c['path']=[c['path'][0],c['path'][-1]]
        if c['kind']=='bare':
            # Remove collinear control vertices without changing solder contacts.
            c['path']=[hole(z) for z in compress([point(z) for z in c['path']])]
    return w

def rank(r,p):
    hard=sum(i['severity']=='error' and i.get('status')!='UNCHECKED' for i in r['issues'])
    bends=sum(max(0,len(c['xy'])-2) for c in p.conductors if c['kind']=='bare')
    soft=sum(i.get('t7_penalty',0) for i in r['issues'] if i['severity']=='warning' and i.get('status')!='UNCHECKED')
    return (hard,r['metrics']['jumpers'],bends,r['metrics']['total_wire_mm'],len(p.conductors),soft)

def main(count):
    original=Project(HERE)
    router.placement_drc=rc.gate
    best=None;log=[]
    for v in [0,1]:
        seeded=original.clone(wiring=variant_seed(v))
        bad=extract(seeded)[0]+wiring_drc(seeded,extract(seeded)[3])
        if bad:raise ValueError(bad)
        for n in range(count):
            config=copy.deepcopy(original.rules)
            remaining=[x for x in original.nets if x not in ['VM','GND','VREF']]
            rng=__import__('random').Random(n);rng.shuffle(remaining)
            config['router']={'power_nets':['VM','GND','VREF']+remaining,
                'power_gauge':'AWG26','signal_gauge':'AWG26','jumper_side':'bottom',
                'bend_penalty':[0.4,1.5,4][n%3]}
            w=router.route(seeded.clone(rules=config))
            for c in w['conductors']:
                if c['net'] in ['VIN_RAW','VIN_FUSED','VIN_PROT']:
                    c['gauge']='AWG20' if c['kind']=='jumper' else '1.0mm';c['branch_id']='ENTRY_SERIES'
            w=polish(w)
            p=original.clone(wiring=w);r=verify(p)
            if not r['lvs_pass']:raise ValueError('polish broke LVS')
            k=rank(r,p);log.append({'variant':v,'seed':n,'rank':k,'score':r['metrics']['score']})
            if best is None or k<best[0]:
                best=k,v,n,w,r
                print('BEST',v,n,k,flush=True)
                save_json(HERE/'wiring.best.json',w)
            if n%25==0:print('progress',v,n,flush=True)
    k,v,n,w,r=best
    save_json(HERE/'wiring.json',w)
    save_json(HERE/'out/route_search.json',{'trials':log,'best_variant':v,'best_seed':n,'rank':k,'objective':'known hard failures, jumpers, bare bends, length, pieces, T7 soft penalty; no rule changed'})
    save_json(HERE/'out/report.json',r);save_json(HERE/'out/metrics.json',r['metrics'])
    print('FINAL',summary(r),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--count',type=int,default=50)
    main(a.parse_args().count)
