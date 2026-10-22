"""Round 3: fixed north tiles, movable Pico/power block and optional logic bus."""
from route_local import *
from model import rotate

class R3Router(Router):
    def transform_pico(self,q):
        d=self.p.placement['parts']['U201'];o=point(d['hole']);a=rotate(q,d['rotation'])
        return o[0]+a[0],o[1]+a[1]

    def power(self):
        self.add('VM',[(0,6),(42,6)],gauge='1.0mm',branch='VM_TRUNK',cid='VM_TRUNK')
        south=self.config.get('south_entry',False);westreg=self.config.get('west_reg',False)
        self.add('GND',[(1,7),(48,7)] if south else [(4,16),(3,16),(3,7),(48,7)] if westreg else [(4,18),(3,18),(3,7),(48,7)],gauge='1.0mm',group='GND:POWER_RETURN',branch='POWER_RETURN_TRUNK',cid='GND_TRUNK')
        bus=self.config.get('under_bus')
        for ch in [1,2,3,4]:
            x=point(self.p.placement['parts'][f'U{300+10*ch}']['hole'])[0]
            b=f'DRIVER_CH{ch}'
            self.add('VM',[(x-5,6),(x-5,3),(x,3),(x,4)],branch=b)
            self.add('VM',[(x-1,2),(x-1,3)],branch=b)
            self.add('GND',[(x-4,5),(x+1,5),(x+1,2),(x,2)],group='GND:POWER_RETURN',branch=b)
            self.add('GND',[(x+1,5),(x+1,7)],'jumper',group='GND:POWER_RETURN',branch=b)
            self.add('GND',[(x+1,7),(x+1,9)],'jumper' if bus and x+1>=9 else 'bare',group='GND:POWER_RETURN',branch=b)
            self.add(f'HDD{ch}_OUT1',[(x+2,4),(x+2,1)],branch=b)
            self.add(f'HDD{ch}_OUT2',[(x+3,4),(x+3,2),(x+4,2),(x+4,1)],branch=b)
            self.add(f'HDD{ch}_CS',[(x+6,4),(x+6,2)])
        if south:
            self.add('VM',[(0,6),(0,32),(6,32),(6,35)],gauge='1.0mm',branch='VM_TRUNK')
            self.add('VM',[(2,34),(6,34)],gauge='1.0mm',branch='TVS_FEED')
            self.add('GND',[(1,7),(1,10)],gauge='1.0mm',group='GND:POWER_RETURN',branch='POWER_RETURN_TRUNK')
            self.add('GND',[(1,10),(1,36)],'jumper',gauge='1.0mm',group='GND:POWER_RETURN',branch='POWER_RETURN_TRUNK')
            self.add('GND',[(1,36),(6,36),(6,37)],gauge='1.0mm',group='GND:POWER_RETURN',branch='POWER_RETURN_TRUNK')
            self.add('GND',[(6,37),(9,37),(9,38),(10,38)],gauge='1.0mm',group='GND:INPUT_RETURN',branch='INPUT_RETURN')
            self.add('GND',[(6,37),(6,38),(2,38)],group='GND:TVS_RETURN',branch='TVS_RETURN')
        elif westreg:
            self.add('VM',[(2,6),(2,16)],gauge='1.0mm',branch='VM_TRUNK')
            self.add('VM',[(1,11),(2,11)],gauge='1.0mm',branch='ENTRY_SERIES')
            self.add('VM',[(1,12),(2,12)],gauge='1.0mm',branch='TVS_FEED')
            self.add('GND',[(4,16),(4,17),(2,17),(2,19)],gauge='1.0mm',group='GND:INPUT_RETURN',branch='INPUT_RETURN')
            self.add('GND',[(4,16),(4,12),(5,12)],group='GND:TVS_RETURN',branch='TVS_RETURN')
        else:
            self.add('VM',[(2,6),(2,18)],gauge='1.0mm',branch='VM_TRUNK')
            self.add('VM',[(0,16),(2,16)],gauge='1.0mm',branch='ENTRY_SERIES')
            self.add('VM',[(1,14),(2,14)],gauge='1.0mm',branch='TVS_FEED')
            self.add('GND',[(4,18),(4,19),(2,19),(2,22)],gauge='1.0mm',group='GND:INPUT_RETURN',branch='INPUT_RETURN')
            self.add('GND',[(4,18),(4,14),(5,14),(5,12)],group='GND:TVS_RETURN',branch='TVS_RETURN')
        self.add('GND',[self.transform_pico((3,2)),self.transform_pico((3,17))],group='GND:PICO_RETURN')
        for y in [2,7,12,17]:self.add('GND',[self.transform_pico((0,y)),self.transform_pico((7,y))],group='GND:PICO_RETURN')
        self.connect('GND:PICO_RETURN','TP465.1',{f'U201.{i}' for i in [3,8,13,18,23,28,33,38]})
        if bus:
            dx=5 if bus=='SLEEP' else 4
            self.add(bus,[(5+dx,8),(47+dx,8)],branch='UNDER_LOGIC_BUS')
            for x in [5,19,33,47]:self.add(bus,[(x+dx,8),(x+dx,9)],branch='UNDER_LOGIC_BUS')
        if self.config.get('direct_regulator_feed',False):self.add('VM',[self.resolve('$VM_ENTRY'),self.resolve('U107.1')],'jumper',branch='REGULATOR_VM')

    def fault(self):
        mode=self.config.get('fault_mode','star')
        if mode=='auto':return
        if mode=='round2':
            self.add('FAULT',[(31,19),(31,18),(34,18),(34,19)])
            for source_x,x in zip([31,32,33,34],[5,19,33,47]):self.add('FAULT',[(source_x,18),(source_x,11),(x+5,11),(x+5,4)],'jumper',branch='FAULT_QUIET_FANOUT')
        elif mode=='star':
            source=self.resolve('R215.2')
            # Four independent pieces, kept on the quiet side of OUT after escape.
            for x in [5,19,33,47]:
                end=(x+5,4)
                self.add('FAULT',[end,(end[0],11),(source[0],11),source],'jumper',branch='FAULT_QUIET_FANOUT')
        elif mode=='diagonal_chain':
            for x in [5,19,33,47]:self.add('FAULT',[(x+5,4),(x+5,5),(x+7,5)],branch='FAULT_EDGE_ESCAPE')
            for x in [5,19,33]:self.add('FAULT',[(x+7,5),(x+16,7),(x+21,5)],'jumper',branch='FAULT_CHAIN')
            self.connect('FAULT',(54,5),{'R215.2'})
        elif mode=='row6':
            for x in [5,19,33,47]:self.add('FAULT',[(x+5,4),(x+5,5)],branch='FAULT_ROW6')
            self.join_group('FAULT')

    def route(self):
        self.power()
        if self.config.get('source_west',False):
            self.add('VREF',[(24,11),(24,14)],group='VREF:VREF_SOURCE')
            self.add('VREF',[(24,13),(25,13)],group='VREF:VREF_SOURCE')
            self.add('VREF',[(22,14),(24,14)],group='VREF:VREF_SOURCE')
        if '+3V3' in self.config.get('priority_nets',[]):self.connect('+3V3','C208.1',{'U207.5'},4)
        for net in self.config.get('priority_nets',[]):self.join_group(net)
        self.fault()
        for net in self.config.get('early_nets',[]):self.join_group(net)
        skip={'P06','P09','P12','G03','S04','S06','V04'}
        for rule in self.p.rules['rules']:
            if rule['type']!='max_branch_length' or rule['severity']!='hard' or rule['id'] in skip:continue
            for pair in rule['params']['pairs']:
                a,b=self.resolve(pair['a']),self.resolve(pair['b']);pin=next(q for q in self.p.pins.values() if q.xy==a)
                if pin.net in ['GND','VREF']:
                    grp=self.pin_groups.get(a)
                    if grp in ['GND:ENTRY','GND:LOGIC_RETURN','VREF:ROOT']:grp=self.pin_groups.get(b,grp)
                else:grp=pin.net
                self.connect(grp,a,{b},rule['params']['max_holes'])
        self.connect('GND:LOGIC_RETURN','$GND_LOGIC',{'$GND_ENTRY'})
        for grp in self.config.get('ground_order',['GND:REGULATOR_CAP_RETURN','GND:PICO_RETURN','GND:VREF_RETURN','GND:CONTROL_RETURN','GND:RECEIVER_RETURN']):
            root=self.resolve('$GND_LOGIC');self.locations[grp].add(root);self.join_group(grp,root)
        default=['VREF']+[f'HDD{i}_IN{j}' for i in [1,2,3,4] for j in [1,2]]+['+3V3','SLEEP','FAULT']
        first=self.config.get('order',default)
        for net in first+sorted(set(self.p.nets)-set(first)-{'GND','VREF'}):
            if net=='VREF':
                vr=self.resolve('$VREF_ROOT')
                for grp in ['VREF:VREF_SOURCE']+[f'VREF:VREF_CH{i}' for i in self.config.get('vref_order',[1,4,2,3])]:
                    self.locations[grp].add(vr);self.join_group(grp,vr)
            else:self.join_group(net)
        for grp in ['GND:POWER_RETURN','GND:TVS_RETURN','GND:INPUT_RETURN']:self.join_group(grp)
        if self.config.get('paired_regulator_return',False):
            for wire in self.out:
                if wire.get('route_group')=='GND:LOGIC_RETURN':
                    wire.update(path=['E19','C20','C25','K25','K23','Y23','Y31'],branch='LOGIC_RETURN',pair_with='REGULATOR_VM')
                if wire['net']=='VM' and wire['path']==['X25','X24','L24','L26','B26','B19','C19']:
                    wire.update(branch='REGULATOR_VM',pair_with='LOGIC_RETURN')
        return dict(schema_version=1,conductors=self.out,method='L4 round3 branch-aware bottom-grid routing',round=3)

def update_nodes(p,pl):
    q=p.clone(placement=pl)
    pl['nodes']={k:hole(q.pin_at(v['anchor'].replace('.', '.#'))) for k,v in q.rules['nodes'].items()}
    return p.clone(placement=pl)

def vertical_seed(p,x=39):
    pl=copy.deepcopy(p.placement)
    def put(ref,x,y,rot=None):
        pl['parts'][ref]['hole']=hole((x,y))
        if rot is not None:pl['parts'][ref]['rotation']=rot
    put('U201',x,38,180)
    put('R215',x+2,22,270);put('TP468',x+2,17)
    put('R212',x+5,25,90)
    put('J213',x-10,39,0);put('R214',27,37,270)
    put('TP467',25,39);put('TP465',x-9,21);put('TP462',42,29);put('TP461',27,25)
    put('D110',29,32,90)
    return update_nodes(p,pl)

def horizontal_seed(p):
    pl=copy.deepcopy(p.placement)
    pl['parts']['R215'].update(hole=hole((34,17)),rotation=0)
    pl['parts']['TP465'].update(hole=hole((32,20)))
    return update_nodes(p,pl)

def west_seed(p):
    pl=copy.deepcopy(p.placement)
    # Same physical tiles, channel labels reversed to match west-USB pin order.
    for ch,x in zip([1,2,3,4],[5,19,33,47]):
        for ref,xy,rot in [(f'U{300+ch*10}',(x,9),270),(f'C{301+ch*10}',(x-4,3),90),(f'C{302+ch*10}',(x-1,2),0),(f'J{303+ch*10}',(x+2,1),0),(f'TP{470+ch}',(x+6,2),0)]:pl['parts'][ref].update(hole=hole(xy),rotation=rot)
    def put(ref,x,y,rot=None):
        pl['parts'][ref]['hole']=hole((x,y))
        if rot is not None:pl['parts'][ref]['rotation']=rot
    put('U201',1,20,270)
    put('J101',10,35,0);put('C106',6,35,90);put('J104',3,31,90);put('D105',2,34,90)
    put('F102',2,24,90);put('D103',38,32,0)
    put('U107',22,33,0);put('C108',22,27,0);put('C109',24,39,180)
    put('D110',1,11,0)
    put('R215',22,23,270);put('R212',19,21,90)
    for ref,x,y in [('TP460',0,10),('TP461',6,11),('TP462',9,11),('TP463',2,39),('TP464',18,33),('TP465',22,12),('TP468',24,20)]:put(ref,x,y)
    return update_nodes(p,pl)

def west_reg_seed(p):
    pl=copy.deepcopy(p.placement)
    def put(ref,x,y,rot=None):
        pl['parts'][ref]['hole']=hole((x,y))
        if rot is not None:pl['parts'][ref]['rotation']=rot
    for ref in ['J101','C106','D105']:
        x,y=point(pl['parts'][ref]['hole']);put(ref,x,y-2)
    put('J101',5,19,90);put('J104',0,11,0);put('TP460',0,9)
    put('U107',1,32,90);put('C108',2,27,180);put('C109',7,34,270)
    put('D103',16,33)
    put('TP461',8,36);put('TP464',10,32);put('TP463',6,14)
    return update_nodes(p,pl)

def save_result(p,w,r,cfg,prefix='r3_best'):
    for nm,data in [('placement',p.placement),('wiring',w),('report',r),('config',cfg)]:save_json(HERE/f'{prefix}_{nm}.json',data)

def main():
    p=Project(HERE)
    cfg=json.loads((HERE/'routing_config.json').read_text('utf8'))
    w=R3Router(p,cfg).route();r=verify(p.clone(wiring=w))
    save_json(HERE/'wiring.json',w);save_json(HERE/'local_report.json',r)
    print(summary(r));print(r['metrics']['comparison_tuple'])
if __name__=='__main__':main()
