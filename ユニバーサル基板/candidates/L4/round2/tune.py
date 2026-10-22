"""Candidate-local placement / routing experiments, seed 4404."""
from route_local import *

def save_best(p,w,r,cfg,name='tuned'):
    for suffix,data in [('placement',p.placement),('wiring',w),('report',r),('config',cfg)]:save_json(HERE/f'{name}_{suffix}.json',data)

def run(n=200):
    rng=random.Random(4422)
    p0=Project(HERE,placement=load_json(HERE/'tuned_placement.json'))
    best=tuple(load_json(HERE/'tuned_report.json')['metrics']['lexicographic_sort_key'])
    bestcfg=json.loads((HERE/'tuned_config.json').read_text('utf8'))
    for it in range(n):
        pl=copy.deepcopy(p0.placement)
        dx,dy=rng.choice(range(-6,7)),rng.choice(range(-2,6))
        for ref in ['R209','R210','C211','TP466']:
            x,y=point(pl['parts'][ref]['hole']);pl['parts'][ref]['hole']=hole((x+dx,y+dy))
        q=p0.clone(placement=pl)
        pl['nodes']={k:hole(q.pin_at(v['anchor'].replace('.', '.#'))) for k,v in q.rules['nodes'].items()}
        q=p0.clone(placement=pl)
        if placement_findings(q):continue
        groups=[[f'HDD{i}_IN{j}' for j in [1,2]] for i in [1,2,3,4]]+[['VREF'],['+3V3'],['SLEEP'],['FAULT']]
        rng.shuffle(groups)
        for g in groups:
            if rng.random()<.5:g.reverse()
        vs=[1,2,3,4];rng.shuffle(vs)
        cfg=dict(force_jump_nets=['UART_RX'],early_nets=['SN_BUS','SN_RX_IN','SN_PU'],order=sum(groups,[]),vref_order=vs,bend=rng.choice([0.4,1.,2.]))
        if it%4==0:cfg.update({k:v for k,v in bestcfg.items() if k not in ['vref_offset']})
        w=Router(q,cfg).route();r=verify(q.clone(wiring=w));key=tuple(r['metrics']['lexicographic_sort_key'])
        if key<best:
            best=key;bestcfg=cfg;save_best(q,w,r,cfg)
            print('BEST',it,(dx,dy),r['metrics']['comparison_tuple'],cfg,flush=True)
    print('DONE',best,flush=True)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 200)
