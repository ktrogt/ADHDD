from layout5 import *

def search(count=100,start=0):
    pl=load_json(HERE/'placement.seed.json');p=project(pl)
    best=(999,)*7;log=[]
    if (HERE/'best_config.json').exists():
        best=tuple(load_json(HERE/'best_report.json')['metrics']['lexicographic_sort_key'])
    for seedno in range(start,start+count):
        rng=random.Random(seedno)
        order=['VREF','+3V3','SLEEP','FAULT','UART_RX','ARM','ARM_SW']+[f'HDD{i}_IN{j}' for i in range(1,5) for j in [1,2]]
        rng.shuffle(order)
        ground=['GND:REGULATOR_CAP_RETURN','GND:PICO_RETURN','GND:VREF_RETURN','GND:CONTROL_RETURN','GND:RECEIVER_RETURN'];rng.shuffle(ground)
        early=['VIN_RAW','VIN_FUSED','VIN_PROT','SN_BUS','SN_RX_IN','SN_PU'];rng.shuffle(early)
        priorities=rng.sample(order,rng.choice([0,4,8,15]))
        cfg=dict(seed=seedno,order=order,ground_order=ground,early_nets=early,priority_nets=priorities,force_jump_nets=rng.choice([[],['VIN_FUSED'],['VIN_PROT'],['VIN_FUSED','VIN_PROT'],['UART_RX'],['ARM_SW']]),bus=rng.choice(['SLEEP','+3V3',None]),fault_mode=rng.choice(['star','auto']),bend=rng.choice([.4,1,2,4]),islands=True,detour=rng.choice([8,14,22]))
        try:
            w=L5Router(p,cfg).route();r=verify(p.clone(wiring=w));m=r['metrics'];key=tuple(m['lexicographic_sort_key'])
            log.append(dict(seed=seedno,comparison_tuple=m['comparison_tuple']))
            if key<best:
                best=key
                for name,data in [('placement',pl),('wiring',w),('report',r),('config',cfg)]:save_json(HERE/f'best_{name}.json',data)
                print('BEST',seedno,m['comparison_tuple'],flush=True)
        except Exception as e:log.append(dict(seed=seedno,error=str(e)))
        if seedno%10==0:print('DONE',seedno,flush=True);save_json(HERE/f'search_{start}.json',log)
    save_json(HERE/f'search_{start}.json',log)
if __name__=='__main__':search(int(sys.argv[1]) if len(sys.argv)>1 else 100,int(sys.argv[2]) if len(sys.argv)>2 else 0)
