"""v0.2 router search, unchanged hard rules; no geometry-gate workaround."""
import sys,copy,json,random,argparse
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent
sys.path.insert(0,str(BASE/'tools'))
from model import Project,save_json,load_json,hole,point
from router import route
from verify import verify,summary,extract,wiring_drc
from finalize import straight

def seed(v):
    w=load_json(HERE/'r2_seed.json')
    if v:
        paths={3:[(44,17),(30,17),(30,23)],2:[(44,28),(31,28),(31,23),(30,23)],1:[(44,39),(30,39),(30,23)]}
        for c in w['conductors']:
            for ch,path in paths.items():
                if c['id']==f'VREF_CH{ch}':c.update(kind='bare',path=[hole(z) for z in path],type='tinned copper')
    return w
def cleanup(w):
    cc=w['conductors'];by={c['id']:c for c in cc}
    for c in cc:
        if c['kind']=='jumper' and not c.get('locked'):c['path']=[c['path'][0],c['path'][-1]]
        if c['net'] in ['VIN_RAW','VIN_FUSED','VIN_PROT']:c.update(gauge='AWG20' if c['kind']=='jumper' else '1.0mm',branch_id='ENTRY_SERIES')
    for ch in range(1,5):
        a=by[f'CH{ch}_VIN'];b=by[f'CH{ch}_BYPASS_V'];a['path']=[a['path'][0],b['path'][0]];cc.remove(b)
    by['REG_COUT_V']['path']=by['REG_COUT_V']['path'][:-1]
    by['SLEEP_STOP']['path']=[by['SLEEP_STOP']['path'][0],by['SLEEP_SENSE']['path'][-1]];cc.remove(by['SLEEP_SENSE'])
    for c in cc:c['path']=straight(c['path'])
    return w
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--count',type=int,default=50);args=ap.parse_args()
    p=Project(HERE,board=load_json(BASE/'board.json'));best=None;trials=[]
    for v in [0,1]:
        pp=p.clone(wiring=seed(v));ex=extract(pp);assert not ex[0]+wiring_drc(pp,ex[3])
        for n in range(args.count):
            cfg=copy.deepcopy(p.rules);nets=[n for n in p.nets if n not in ['VM','GND','VREF']];random.Random(n).shuffle(nets)
            cfg['router']={'power_nets':['VM','GND','VREF']+nets,'power_gauge':'AWG26','signal_gauge':'AWG26','jumper_side':'bottom','bend_penalty':[.4,1.5,4][n%3]}
            w=cleanup(route(pp.clone(rules=cfg)));q=p.clone(wiring=w);r=verify(q);key=r['metrics']['lexicographic_sort_key']
            assert r['lvs_pass']
            trials.append({'policy':v,'seed':n,'tuple':r['metrics']['comparison_tuple']})
            if best is None or key<best[0]:
                best=key,w,r,v,n;save_json(HERE/'wiring.json',w);print('BEST',v,n,r['metrics']['comparison_tuple'],flush=True)
            if n%25==0:print('progress',v,n,flush=True)
    _,w,r,v,n=best
    save_json(HERE/'wiring.json',w);save_json(HERE/'out/report.json',r);save_json(HERE/'out/metrics.json',r['metrics'])
    save_json(HERE/'out/r2_route_search.json',{'best_policy':v,'best_seed':n,'trials':trials})
    print('FINAL',summary(r));print(r['metrics']['comparison_tuple'])
