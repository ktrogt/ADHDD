"""Reproducible route-order search restricted to candidate L4."""
from route_local import *
def run(count=200):
    p=Project(HERE)
    rng=random.Random(4404)
    best=None
    groups=[[f'HDD{i}_IN{j}' for j in [1,2]] for i in [1,2,3,4]]+[['VREF'],['+3V3'],['SLEEP'],['FAULT']]
    for iteration in range(count):
        shuffled=copy.deepcopy(groups);rng.shuffle(shuffled)
        for group in shuffled:
            if rng.random()<.5:group.reverse()
        vref_order=[1,2,3,4];rng.shuffle(vref_order)
        cfg=dict(order=sum(shuffled,[]),vref_order=vref_order,bend=rng.choice([0.4,1.0,2.0]))
        try:
            w=Router(p,cfg).route();r=verify(p.clone(wiring=w));m=r['metrics']
            key=tuple(m['lexicographic_sort_key'])
            if best is None or key<best:
                best=key
                save_json(HERE/'wiring.best.json',w);save_json(HERE/'best_report.json',r);save_json(HERE/'best_config.json',cfg)
                print(iteration,m['comparison_tuple'],cfg,flush=True)
        except Exception as ex:print('ERR',iteration,str(ex),flush=True)
    print('DONE',best,flush=True)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 200)
