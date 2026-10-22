from layout5 import *

def variant2():
    pl=seed()
    def put(r,x,y,rot=None):
        pl['parts'][r]['hole']=hole((x,y))
        if rot is not None:pl['parts'][r]['rotation']=rot
    put('U107',23,19,0);put('C108',23,13,0);put('C109',25,25,180)
    put('C211',30,12,90);put('R209',28,10,90);put('R210',32,12,90);put('TP466',28,14)
    put('D103',15,13);put('R215',31,17,270);put('R212',30,22,270)
    put('TP464',19,24);put('TP461',28,25);put('TP465',32,24);put('TP468',31,18)
    return update_nodes(pl)

def run(n=300,start=0):
    initial=variant2();bad=findings(initial)
    if bad:print(bad);return
    best=(999,)*7;logs=[]
    if (HERE/'place_report.json').exists():best=tuple(load_json(HERE/'place_report.json')['metrics']['lexicographic_sort_key'])
    for s in range(start,start+n):
        rng=random.Random(s);pl=copy.deepcopy(initial)
        if s%5:
            groups=[['U107','C108','C109','TP464','TP461'],['C211','R209','R210','TP466'],['R215','TP468'],['F102'],['D103'],['R212'],['U201'],['TP465']]
            for group in groups:
                dx=rng.choice([-1,0,0,1]);dy=rng.choice([-1,0,0,1])
                if group==['U201']:dx=rng.choice([-1,0]);dy=0
                for ref in group:
                    x,y=point(pl['parts'][ref]['hole']);pl['parts'][ref]['hole']=hole((x+dx,y+dy))
            if findings(pl):continue
            p=project(pl)
            if any(pin.xy[1]>25 for pin in p.pins.values() if not pin.ref.startswith('J')):continue
            update_nodes(pl)
        p=project(pl)
        order=['VREF','+3V3','SLEEP','FAULT','UART_RX','ARM','ARM_SW']+[f'HDD{i}_IN{j}' for i in range(1,5) for j in [1,2]];rng.shuffle(order)
        ground=['GND:REGULATOR_CAP_RETURN','GND:PICO_RETURN','GND:VREF_RETURN','GND:CONTROL_RETURN','GND:RECEIVER_RETURN'];rng.shuffle(ground)
        early=['VIN_RAW','VIN_FUSED','VIN_PROT','SN_BUS','SN_RX_IN','SN_PU'];rng.shuffle(early)
        cfg=dict(order=order,ground_order=ground,early_nets=early,priority_nets=rng.sample(order,rng.choice([0,4,8])),bus=rng.choice(['SLEEP','+3V3',None]),fault_mode=rng.choice(['star','auto']),bend=rng.choice([.4,1,2]),force_jump_nets=rng.choice([[],['VIN_FUSED'],['VIN_PROT'],['UART_RX']]),islands=rng.choice([True,False]))
        try:
            w=L5Router(p,cfg).route();r=verify(p.clone(wiring=w));m=r['metrics'];key=tuple(m['lexicographic_sort_key'])
            logs.append(dict(seed=s,tuple=m['comparison_tuple']))
            if key<best:
                best=key
                for k,v in [('placement',pl),('wiring',w),('report',r),('config',cfg)]:save_json(HERE/f'place_{k}.json',v)
                print('PLACE BEST',s,m['comparison_tuple'],flush=True)
        except Exception as e:logs.append(dict(seed=s,error=str(e)))
        if s%20==0:print('PLACE DONE',s,flush=True);save_json(HERE/f'place_log_{start}.json',logs)
    save_json(HERE/f'place_log_{start}.json',logs)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 300,int(sys.argv[2]) if len(sys.argv)>2 else 0)
