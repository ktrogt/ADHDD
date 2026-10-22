from layout5 import *

def handseed():
    pl=seed()
    def put(r,x,y,rot=None):
        pl['parts'][r]['hole']=hole((x,y))
        if rot is not None:pl['parts'][r]['rotation']=rot
    put('U201',52,13)
    put('D103',15,13)
    put('R214',51,11,180)
    put('C211',27,16,90);put('R209',25,14,90);put('R210',29,16,90);put('TP466',29,14)
    put('R212',36,24,0);put('TP468',31,19)
    return update_nodes(pl)

def run(n=150,start=0):
    pl=handseed();p=project(pl);save_json(HERE/'hand_placement.json',pl)
    bad=findings(pl)
    if bad:print(bad);return
    best=(999,)*7;logs=[]
    if (HERE/'hand_report.json').exists():best=tuple(load_json(HERE/'hand_report.json')['metrics']['lexicographic_sort_key'])
    for s in range(start,start+n):
        rng=random.Random(s)
        order=['VREF','+3V3','SLEEP','FAULT','UART_RX','ARM','ARM_SW'];rng.shuffle(order)
        ground=['GND:REGULATOR_CAP_RETURN','GND:PICO_RETURN','GND:VREF_RETURN','GND:CONTROL_RETURN','GND:RECEIVER_RETURN'];rng.shuffle(ground)
        early=['VIN_RAW','VIN_FUSED','VIN_PROT','SN_BUS','SN_RX_IN','SN_PU'];rng.shuffle(early)
        cfg=dict(manual_in=True,order=order,ground_order=ground,early_nets=early,priority_nets=rng.sample(order,rng.choice([0,3,7])),bus=rng.choice(['SLEEP','+3V3']),fault_mode=rng.choice(['star','auto']),bend=rng.choice([.4,1,2]),force_jump_nets=rng.choice([[],['VIN_FUSED'],['VIN_PROT'],['VIN_FUSED','VIN_PROT'],['UART_RX']]))
        try:
            w=L5Router(p,cfg).route();r=verify(p.clone(wiring=w));m=r['metrics'];key=tuple(m['lexicographic_sort_key'])
            logs.append(dict(seed=s,tuple=m['comparison_tuple']))
            if key<best:
                best=key
                for k,v in [('wiring',w),('report',r),('config',cfg)]:save_json(HERE/f'hand_{k}.json',v)
                print('HAND BEST',s,m['comparison_tuple'],flush=True)
        except Exception as e:logs.append(dict(seed=s,error=str(e)))
        if s%20==0:print('HAND DONE',s,flush=True)
    save_json(HERE/f'hand_log_{start}.json',logs)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 150,int(sys.argv[2]) if len(sys.argv)>2 else 0)
