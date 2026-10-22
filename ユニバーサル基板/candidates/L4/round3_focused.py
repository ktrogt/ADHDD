from round3_route import *
def run(n=500):
    base=Project(HERE);rng=random.Random(43321)
    cfg0=json.loads((HERE/'routing_config.json').read_text('utf8'));cfg0.update(fault_mode='round2',direct_regulator_feed=False)
    w=R3Router(base,cfg0).route();r=verify(base.clone(wiring=w));best=tuple(r['metrics']['lexicographic_sort_key']);save_result(base,w,r,cfg0,prefix='r3_improved')
    print('BASE',r['metrics']['comparison_tuple'],flush=True)
    for it in range(n):
        pl=copy.deepcopy(base.placement)
        rootx,rooty=rng.choice(range(22,33)),rng.choice(range(10,17))
        if it%5==0:rootx,rooty=27,14
        for ref in ['R209','R210','C211','TP466']:
            x,y=point(pl['parts'][ref]['hole']);pl['parts'][ref]['hole']=hole((x+rootx-27,y+rooty-14))
        if it%3:pl['parts']['TP466']['hole']=hole((rootx-2,rooty+3))
        if it%2:pl['parts']['TP465']['hole']=hole(rng.choice([(32,24),(32,17),(30,18),(37,17)]))
        p=update_nodes(base,pl)
        if placement_findings(p):continue
        cfg=copy.deepcopy(cfg0)
        cfg['force_jump_nets']=rng.choice([['UART_RX','HDD4_IN1'],['UART_RX'],['UART_RX','HDD1_IN1'],[]])
        cfg['bend']=rng.choice([.4,1,2])
        vs=[1,2,3,4];rng.shuffle(vs);cfg['vref_order']=vs
        groups=[[f'HDD{i}_IN{j}' for j in [1,2]] for i in [1,2,3,4]]+[['VREF'],['+3V3'],['SLEEP']]
        rng.shuffle(groups)
        for g in groups:
            if rng.random()<.5:g.reverse()
        if it%4:cfg['order']=sum(groups,[])
        cfg['reverse_roots']=rng.sample(['SLEEP','+3V3'],rng.randrange(3))
        try:
            w=R3Router(p,cfg).route();r=verify(p.clone(wiring=w));key=tuple(r['metrics']['lexicographic_sort_key'])
            if key<best and r['metrics']['t7_soft_penalty']<=225.624726*1.1:
                best=key;save_result(p,w,r,cfg,prefix='r3_improved');print('BEST',it,rootx,rooty,r['metrics']['comparison_tuple'],cfg,flush=True)
        except Exception as ex:print('ERR',it,str(ex),flush=True)
    print('DONE',best,flush=True)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 500)
