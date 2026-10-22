"""Reproducible R3 searches; accepts only lower tuples and <=10% soft increase."""
from round3_route import *
def run(n=400):
    root=Project(HERE);rng=random.Random(430031)
    seeds=[('horizontal',horizontal_seed(root))]+[(f'south-{x}',vertical_seed(root,x)) for x in [38,39,40]]
    best=tuple(load_json(HERE/'round2/out/report.json')['metrics']['lexicographic_sort_key'])
    loose=None
    for it in range(n):
        name,p=rng.choice(seeds)
        ins=[f'HDD{i}_IN{j}' for i in [1,2,3,4] for j in [1,2]];rng.shuffle(ins)
        groups=[[f'HDD{i}_IN{j}' for j in [1,2]] for i in [1,2,3,4]]+[['VREF'],['+3V3'],['SLEEP']];rng.shuffle(groups)
        vs=[1,2,3,4];rng.shuffle(vs)
        cfg=dict(priority_nets=ins if it%5 else [],under_bus=rng.choice([None,None,None,'SLEEP','+3V3']),fault_mode=rng.choice(['star','diagonal_chain']),early_nets=['SN_BUS','SN_RX_IN','SN_PU','VIN_RAW','VIN_FUSED','VIN_PROT'],force_jump_nets=rng.choice([[],['UART_RX']]),direct_regulator_feed=rng.choice([False,True]),order=sum(groups,[]),vref_order=vs,bend=rng.choice([.4,1,2]),reverse_roots=rng.sample(ins,rng.randrange(5)))
        try:
            w=R3Router(p,cfg).route();r=verify(p.clone(wiring=w));m=r['metrics'];key=tuple(m['lexicographic_sort_key'])
            if loose is None or key<loose:
                loose=key;save_result(p,w,r,cfg,prefix='r3_trialbest');print('TRIALBEST',it,name,m['comparison_tuple'],flush=True)
            if key<best and m['t7_soft_penalty']<=225.624726*1.1:
                best=key;save_result(p,w,r,cfg,prefix='r3_improved');print('ACCEPTED',it,name,m['comparison_tuple'],cfg,flush=True)
        except Exception as e:print('ERR',it,str(e),flush=True)
    print('DONE',best,'trial',loose,flush=True)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 400)
