"""L5-only compact placement and branch-aware routing. Shared inputs read-only."""
from build import *
from route_local import Router
from model import rotate, compress, path_points, segment_distance
from router import astar
from collections import defaultdict
import math

def initialize_exemption():
    rows=list(csv.DictReader((BASE/'netlist_ub.csv').open(encoding='utf-8-sig')))
    for r in rows:
        if r['ref'] in ['U310','U320','U330','U340'] and r['pin_number']=='2':r['net']='NC'
    with (HERE/'netlist.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    r=load_json(BASE/'design_rules_v0.2.json',(1,'adhdd-perfboard-rules/1.0'))
    r['rules']=[x for x in r['rules'] if x['id']!='G03']
    for x in r['rules']:
        if x['id']=='G01':
            b=next(b for b in x['params']['branches'] if b['id']=='POWER_RETURN')
            b['endpoints']=[e for e in b['endpoints'] if not (e.startswith('U3') and e.endswith('.2'))]
    r['L5_authorized_exception']={
        'source':'https://www.pololu.com/file/0J1862/drv887x-single-brushed-dc-motor-driver-carrier-schematic.pdf',
        'evidence':'2026-10-22: primary one-page schematic visually inspected using web PDF screenshot. Pin 2 on each 1x7 connector terminates on the identical ground symbol. These map to host U3x0.2 and U3x0.13.',
        'authority':'Task L5 conditional supervisor permission; not a circuit/part substitution',
        'host_netlist':'Only U310/320/330/340 pin 2 changed GND -> NC. All socket contacts remain present and reserved; GND2 is internally connected after carrier insertion.',
        'rules':'G01 POWER_RETURN removes four pin-2 endpoints. G03 host-board GND2-to-GND13 length requirement is discharged by the verified carrier copper; retained as a build-time carrier continuity test.',
        'limits':'PDF direct file download failed due network restriction; official PDF read and visually inspected through web tool. No unverified internal tie inferred for other parts.'}
    save_json(HERE/'design_rules.json',r)
    save_json(HERE/'source_evidence.json',r['L5_authorized_exception'])

def project(pl=None,w=None):
    return Project(HERE,board=load_json(BASE/'board.json'),placement=pl,wiring=w or {'schema_version':1,'conductors':[]})

def update_nodes(pl):
    p=project(pl)
    pl['nodes']={k:hole(p.pin_at(v['anchor'].replace('.', '.#'))) for k,v in p.rules['nodes'].items()}
    return pl

def seed():
    pl=load_json(BASE/'candidates/L4/placement.json');pl['candidate']='L5';pl['floor_plan']='compact northern strip';pl.pop('round',None)
    def put(r,x,y,rot=None):
        pl['parts'][r]['hole']=hole((x,y))
        if rot is not None:pl['parts'][r]['rotation']=rot
    put('U201',53,13,90)
    put('J101',5,18,90);put('C106',2,15,0);put('J104',0,13,270);put('D105',1,11,0)
    put('F102',8,25,0);put('D103',15,12,0)
    put('U107',18,20,90);put('C108',12,20,90);put('C109',24,22,270)
    put('D110',40,22,180)
    put('J202',54,23,90);put('J203',54,27,90);put('U207',46,25,270);put('C208',50,22,90)
    put('R204',52,25,180);put('R205',42,22,90);put('D206',44,25,270)
    put('C211',27,12,90);put('R209',25,10,90);put('R210',29,12,90)
    put('J213',54,11,180);put('R214',50,11,180);put('R212',39,11,0);put('R215',31,16,270)
    for ref,x,y in [('TP460',0,9),('TP461',27,23),('TP462',40,24),('TP463',6,12),('TP464',23,25),('TP465',32,22),('TP466',29,10),('TP467',45,11),('TP468',32,11)]:put(ref,x,y)
    return update_nodes(pl)

def findings(pl):
    p=project(pl)
    return [i for i in placement_drc(p)+evaluate(p,placement_only=True) if i['severity']=='error' and i.get('status')!='UNCHECKED']

class L5Router(Router):
    mask_cache=None
    def __init__(self,p,config=None):
        super().__init__(p,config)
        if L5Router.mask_cache is not None:
            self.masks=L5Router.mask_cache;return
        self.masks={}
        outs=[]
        for ch in range(1,5):
            x,y=point(p.placement['parts'][f'U{300+ch*10}']['hole'])
            outs += [((x+2,4),(x+2,1)),((x+3,4),(x+3,2)),((x+3,2),(x+4,2)),((x+4,2),(x+4,1))]
        rects=[p.parts[f'J{303+ch*10}'].rect for ch in range(1,5)]
        for net in ['VREF','SLEEP','FAULT','SN_BUS','SN_RX_IN','SN_PU','UART_RX','ARM','ARM_SW']:
            gap=3 if net=='VREF' else 2
            bad=set()
            for x in range(p.columns):
                for y in range(p.rows):
                    q=(x,y)
                    if net=='FAULT' and any(math.dist(q,self.resolve(f'U{300+ch*10}.9'))<=2 for ch in range(1,5)):continue
                    r=(x*p.pitch,y*p.pitch,x*p.pitch,y*p.pitch)
                    if any(segment_distance(q,q,a,b)<gap+.6/p.pitch for a,b in outs) or any(rect_distance(r,t)<gap*p.pitch+.3 for t in rects):bad.add(q)
            self.masks[net]=bad
        L5Router.mask_cache=self.masks

    def blocked(self,grp,ends=()):
        b=super().blocked(grp,ends)|self.masks.get(grp.split(':')[0],set()) if hasattr(self,'masks') else super().blocked(grp,ends)
        return b|{(x,y) for x in range(self.p.columns) for y in range(self.config.get('routing_rows',29),self.p.rows)}

    def join_group(self,grp,root=None):
        if not self.config.get('islands',True):return super().join_group(grp,root)
        pts=self.locations[grp]
        if not pts:return
        maxh=60 if '_IN' in grp else 80 if grp in ['SLEEP','FAULT'] else 40 if grp=='UART_RX' or grp.startswith('VREF:VREF_CH') else None
        while True:
            groups=defaultdict(set)
            for q in pts:groups[self.uf.find(q)].add(q)
            groups=list(groups.values())
            if len(groups)<2:return
            pairs=[]
            for i,a in enumerate(groups):
                for b in groups[:i]:pairs.append(min((abs(x[0]-y[0])+abs(x[1]-y[1]),x,y) for x in a for y in b))
            path=None
            for dist,a,b in (sorted(pairs) if grp.split(':')[0] not in self.config.get('force_jump_nets',[]) else []):
                path=astar(self.p,a,{b},self.blocked(grp,ends={a,b}),self.config.get('bend',1.5))
                if path is not None and (maxh is None or len(path)-1<=maxh) and len(path)-1<=dist+self.config.get('detour',18):break
                path=None
            if path is None:
                _,a,b=min(pairs);self.add(grp.split(':')[0],[a,b],'jumper',group=grp)
            else:self.add(grp.split(':')[0],compress(path),group=grp)

    def add(self,net,path,kind='bare',**kw):
        if isinstance(path[0],str):path=[self.resolve(z) for z in path]
        if kind=='jumper' and net in self.masks:
            if any((round(a[0]+(b[0]-a[0])*t/100),round(a[1]+(b[1]-a[1])*t/100)) in self.masks[net] for a,b in zip(path,path[1:]) for t in range(101)):
                path=astar(self.p,path[0],{path[-1]},self.masks[net],1.5)
                if path is None:raise ValueError('No quiet jumper '+net)
                path=compress(path)
        super().add(net,path,kind,**kw)

    def power(self):
        E=self.resolve('$GND_ENTRY');V=self.resolve('$VM_ENTRY')
        self.add('VM',[(0,6),(42,6)],gauge='1.0mm',branch='VM_TRUNK',cid='VM_TRUNK')
        self.add('GND',[E,(3,E[1]),(3,7),(48,7)],gauge='1.0mm',group='GND:POWER_RETURN',branch='POWER_RETURN_TRUNK',cid='GND_TRUNK')
        for ch in [1,2,3,4]:
            x=point(self.p.placement['parts'][f'U{300+ch*10}']['hole'])[0];b=f'DRIVER_CH{ch}'
            self.add('VM',[(x-5,6),(x-5,3),(x,3),(x,4)],branch=b)
            self.add('VM',[(x-1,2),(x-1,3)],branch=b)
            self.add('GND',[(x-4,5),(x+1,5),(x+1,2),(x,2)],group='GND:POWER_RETURN',branch=b)
            self.add('GND',[(x+1,5),(x+1,7)],'jumper',group='GND:POWER_RETURN',branch=b)
            self.add(f'HDD{ch}_OUT1',[(x+2,4),(x+2,1)],branch=b)
            self.add(f'HDD{ch}_OUT2',[(x+3,4),(x+3,2),(x+4,2),(x+4,1)],branch=b)
            self.add(f'HDD{ch}_CS',[(x+6,4),(x+6,2)])
        self.add('VM',[(V[0],6),V],gauge='1.0mm',branch='VM_TRUNK')
        # Star entry loops are separately routed under their exact hard limits.
        d=self.p.placement['parts']['U201'];o=point(d['hole'])
        def tr(q):
            a=rotate(q,d['rotation']);return o[0]+a[0],o[1]+a[1]
        self.add('GND',[tr((3,2)),tr((3,17))],group='GND:PICO_RETURN')
        for y in [2,7,12,17]:self.add('GND',[tr((0,y)),tr((7,y))],group='GND:PICO_RETURN')
        bus=self.config.get('bus','SLEEP')
        if bus:
            dx=5 if bus=='SLEEP' else 4
            self.add(bus,[(5+dx,8),(47+dx,8)],branch='UNDER_LOGIC_BUS')
            for x in [5,19,33,47]:self.add(bus,[(x+dx,8),(x+dx,9)],branch='UNDER_LOGIC_BUS')
        if self.config.get('manual_in'):
            for ch,y in [(4,12),(3,11),(2,10),(1,10)]:
                a=self.resolve(f'U{300+10*ch}.3');b=self.resolve(f'U201.{ {1:4,2:6,3:9,4:11}[ch]}')
                path=[a,(a[0],y),(b[0],y),b]
                path=[v for i,v in enumerate(path) if i==0 or v!=path[i-1]]
                self.add(f'HDD{ch}_IN1',compress(path),branch=f'IN1_CH{ch}')
                self.add(f'HDD{ch}_IN2',[self.resolve(f'U{300+10*ch}.4'),self.resolve(f'U201.{ {1:5,2:7,3:10,4:12}[ch]}')],'jumper',branch=f'IN2_CH{ch}')

    def route(self):
        self.power()
        if self.config.get('input_return_seed',True):
            self.add('GND',['C19','C18','E18','E16'],gauge='1.0mm',group='GND:INPUT_RETURN',branch='INPUT_RETURN')
        early=self.config.get('early_nets',['VIN_RAW','VIN_FUSED','VIN_PROT','SN_BUS','SN_RX_IN','SN_PU'])
        if self.config.get('early_before_caps',False):
            for net in early:self.join_group(net)
        # Local decoupling and protection loops are constrained before fanout.
        skip={'P06','P09','P12','S04','S06','V04'}
        for r in self.p.rules['rules']:
            if r['type']!='max_branch_length' or r['severity']!='hard' or r['id'] in skip:continue
            for pair in r['params']['pairs']:
                a,b=self.resolve(pair['a']),self.resolve(pair['b']);net=next(q.net for q in self.p.pins.values() if q.xy==a)
                grp=net
                if net in ['GND','VREF']:
                    grp=self.pin_groups.get(a)
                    if grp in ['GND:ENTRY','GND:LOGIC_RETURN','VREF:ROOT']:grp=self.pin_groups.get(b,grp)
                self.connect(grp,a,{b},r['params']['max_holes'])
        for net in self.config.get('priority_nets',[]):self.join_group(net)
        if not self.config.get('early_before_caps',False):
            for net in early:self.join_group(net)
        if self.config.get('fault_mode','star')=='star':
            root=self.resolve('R215.2')
            for x in [5,19,33,47]:self.add('FAULT',[(x+5,4),(x+5,11),root],'jumper',branch='FAULT_QUIET_FANOUT')
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
        return dict(schema_version=1,conductors=self.out,candidate='L5',method='Compact branch-aware bottom routing; carrier GND2 exemption')

def main():
    initialize_exemption()
    pl=seed();save_json(HERE/'placement.seed.json',pl)
    for i in findings(pl):print(i['code'],i['detail'])
    p=project(pl)
    for ref in ['U201','U107','U207','J101']:
        print(ref,'RECT',p.parts[ref].rect,'PINS',[(x.number,hole(x.xy),x.net) for x in p.parts[ref].pins])
    if not findings(pl):
        w=L5Router(p).route();r=verify(p.clone(wiring=w));save_json(HERE/'trial_report.json',r);save_json(HERE/'trial_wiring.json',w)
        print(r['metrics']['comparison_tuple']);print([(i['code'],i['detail']) for i in r['issues'] if i['severity']=='error' and i.get('status')!='UNCHECKED'])
if __name__=='__main__':main()
