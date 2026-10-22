"""Local hand-routing plus branch-aware router; imports shared tools read-only."""
from build import *
from collections import defaultdict
from model import compress, path_points, distance
from router import astar, net_colour
from verify import UnionFind, net_graph, shortest

class Router:
    def __init__(self,p,config=None):
        self.p=p
        self.config=config or {}
        self.out=[]
        self.occupied=defaultdict(set)
        self.uf=UnionFind()
        self.locations=defaultdict(set)
        self.serial=0
        self.pin_groups={}
        self.allowed_roots=defaultdict(set)
        self.allowed_groups=defaultdict(set)
        def pins(group, selectors):
            for sel in selectors:
                q=p.pin_at(sel.replace('.', '.#') if sel.split('.')[-1].isdigit() else sel)
                self.pin_groups[q]=group
        # Each GND subtree is isolated from the others except at its declared hub.
        gspec=[r['params'] for r in p.rules['rules'] if r['id'] in ['G01','G02']]
        for spec in gspec:
            root=p.pin_at(p.rules['nodes'][spec['root'][1:]]['anchor'].replace('.', '.#'))
            for branch in spec['branches']:
                grp='GND:'+branch['id']
                ends=[]
                for sel in branch['endpoints']:
                    if sel.startswith('$'): sel=p.rules['nodes'][sel[1:]]['anchor']
                    ends.append(sel)
                pins(grp,ends)
                self.allowed_roots[grp].add(root)
        # The link belongs to G01's LOGIC_RETURN, and it touches the local hub.
        pins('GND:ENTRY',['C106.2'])
        pins('GND:LOGIC_RETURN',['U107.2'])
        pins('GND:TVS_RETURN',['TP463.1'])
        pins('GND:REGULATOR_CAP_RETURN',['TP464.1'])
        pins('GND:PICO_RETURN',['TP465.1'])
        # VREF star branches.
        vspec=next(r['params'] for r in p.rules['rules'] if r['id']=='V01')
        vr=p.pin_at('C211.P1')
        for b in vspec['branches']:
            grp='VREF:'+b['id'];pins(grp,b['endpoints']);self.allowed_roots[grp].add(vr)
        pins('VREF:ROOT',['C211.1'])
        for pin in p.pins.values():
            grp=self.pin_groups.get(pin.xy,pin.net) if pin.net in ['GND','VREF'] else pin.net
            if pin.net=='NC': grp='NC:'+pin.label
            self.occupied[pin.xy].add(grp)
            self.locations[grp].add(pin.xy)
            self.uf.find(pin.xy)
        for xy,label in p.reserved_pads.items(): self.occupied[xy].add('NC_EXTRA:'+label)

    def blocked(self,grp,ends=()):
        allowed={grp}
        roots=self.allowed_roots[grp]
        return {xy for xy,claims in self.occupied.items() if xy not in roots and xy not in ends and claims-allowed}

    def add(self,net,path,kind='bare',gauge=None,group=None,branch=None,cid=None):
        if isinstance(path[0],str): path=[point(s) for s in path]
        if len(path)<2 or path[0]==path[-1]: return
        grp=group or net
        contacts=path_points(path) if kind!='jumper' else [path[0],path[-1]]
        endpoint_hubs={q for q in [path[0],path[-1]] if self.occupied[q] and all(g.split(':')[0]==net for g in self.occupied[q])}
        bad=set(contacts)&self.blocked(grp,ends=self.allowed_roots[grp]|endpoint_hubs)
        if bad: raise ValueError(f'{net}/{grp} collides at {[hole(q) for q in sorted(bad)]}, {path}')
        self.serial+=1
        default_gauge='1.0mm' if net in ['VIN_RAW','VIN_FUSED','VIN_PROT'] else '0.64mm' if net in ['VM','GND','+5V','VSYS'] or '_OUT' in net else '0.5mm'
        self.out.append(dict(id=cid or f'L4W{self.serial:03d}',net=net,path=[hole(q) for q in path],kind=kind,side='bottom',gauge=gauge or default_gauge,type='tinned copper' if kind=='bare' else 'insulated copper',colour=net_colour(net),locked=True,branch=branch or grp,route_group=grp))
        for q in contacts:
            self.occupied[q].add(grp);self.locations[grp].add(q);self.uf.union(contacts[0],q)

    def connect(self,grp,source,goals,max_holes=None,force_bare=False):
        net=grp.split(':')[0]
        if isinstance(source,str): source=self.resolve(source)
        goals={self.resolve(q) if isinstance(q,str) else q for q in goals}
        goals={q for q in goals if q!=source}
        if not goals: return
        # Already connected -> no redundant closed wire loops.
        if any(self.uf.find(source)==self.uf.find(q) for q in goals): return
        blocked=self.blocked(grp,ends=goals|{source})
        path=None if net in self.config.get('force_jump_nets',[]) else astar(self.p,source,goals,blocked,self.config.get('bend',1.0))
        if path is not None and (max_holes is None or len(path)-1<=max_holes+1e-6):
            self.add(net,compress(path),'bare',group=grp);return
        if force_bare: raise ValueError(f'no bare {grp}: {hole(source)}')
        target=min(goals,key=lambda q:distance(q,source))
        self.add(net,[source,target],'jumper',group=grp)

    def resolve(self,sel):
        if sel.startswith('$'):sel=self.p.rules['nodes'][sel[1:]]['anchor']
        if '.' in sel:
            if sel.split('.')[-1].isdigit():sel=sel.replace('.','.#')
            return self.p.pin_at(sel)
        return point(sel)

    def join_group(self,grp,root=None):
        points=self.locations[grp]
        if not points:return
        root=self.resolve(root) if isinstance(root,str) else root
        root=root or (max(points) if grp in self.config.get('reverse_roots',[]) else min(points))
        while True:
            connected={q for q in points if self.uf.find(q)==self.uf.find(root)}
            left=points-connected
            if not left:return
            _,source,target=min((abs(a[0]-b[0])+abs(a[1]-b[1]),a,b) for a in left for b in connected)
            self.connect(grp,source,connected)

    def route(self):
        # Four exact repeated local channel patterns; heavy trunks below carriers.
        self.add('VM',[(0,6),(42,6)],gauge='1.0mm',branch='VM_TRUNK',cid='VM_TRUNK')
        self.add('GND',[(4,18),(3,18),(3,7),(48,7)],gauge='1.0mm',group='GND:POWER_RETURN',branch='POWER_RETURN_TRUNK',cid='GND_TRUNK')
        for ch,x in zip([4,3,2,1],[5,19,33,47]):
            b=f'DRIVER_CH{ch}'
            self.add('VM',[(x-5,6),(x-5,3),(x,3),(x,4)],branch=b)
            self.add('VM',[(x-1,2),(x-1,3)],branch=b)
            self.add('GND',[(x-4,5),(x+1,5),(x+1,2),(x,2)],group='GND:POWER_RETURN',branch=b)
            self.add('GND',[(x+1,5),(x+1,7)],'jumper',group='GND:POWER_RETURN',branch=b)
            self.add('GND',[(x+1,7),(x+1,9)],group='GND:POWER_RETURN',branch=b)
            self.add(f'HDD{ch}_OUT1',[(x+2,4),(x+2,1)],branch=b)
            self.add(f'HDD{ch}_OUT2',[(x+3,4),(x+3,2),(x+4,2),(x+4,1)],branch=b)
            self.add(f'HDD{ch}_CS',[(x+6,4),(x+6,2)])
        # Entry source and independent star returns.
        self.add('VM',[(2,6),(2,18)],gauge='1.0mm',branch='VM_TRUNK')
        self.add('VM',[(0,16),(2,16)],gauge='1.0mm',branch='ENTRY_SERIES')
        self.add('VM',[(1,14),(2,14)],gauge='1.0mm',branch='TVS_FEED')
        self.add('GND',[(4,18),(4,19),(2,19),(2,22)],gauge='1.0mm',group='GND:INPUT_RETURN',branch='INPUT_RETURN')
        self.add('GND',[(4,18),(4,14),(5,14),(5,12)],group='GND:TVS_RETURN',branch='TVS_RETURN')
        # Quiet Pico network inside the socket outline (bottom, no internal ties assumed).
        self.add('GND',[(36,22),(51,22)],group='GND:PICO_RETURN',gauge='0.64mm')
        for x in [36,41,46,51]:
            self.add('GND',[(x,19),(x,26)],group='GND:PICO_RETURN',gauge='0.64mm')
        self.add('GND',[(36,19),(36,17),(37,17)],group='GND:PICO_RETURN')
        if self.config.get('direct_regulator_feed',True):
            self.add('VM',[self.resolve('$VM_ENTRY'),self.resolve('U107.1')],'jumper',gauge='0.64mm',branch='REGULATOR_VM')
        if self.config.get('quiet_fault',False):
            self.add('FAULT',[(31,19),(31,18),(34,18),(34,19)])
            for source_x,x in zip([31,32,33,34],[5,19,33,47]):
                self.add('FAULT',[(source_x,18),(source_x,11),(x+5,11),(x+5,4)],'jumper',branch='FAULT_QUIET_FANOUT')
        for net in self.config.get('early_nets',[]):self.join_group(net)
        # All max-branch pairs before unconstrained long routes.
        skip={'P06','P09','P12','G03'}
        for rule in self.p.rules['rules']:
            if rule['type']!='max_branch_length' or rule['severity']!='hard' or rule['id'] in skip:continue
            if rule['id'] in ['S04','S06','V04']:continue
            for pair in rule['params']['pairs']:
                a,b=self.resolve(pair['a']),self.resolve(pair['b'])
                pin=next(q for q in self.p.pins.values() if q.xy==a)
                if pin.net in ['GND','VREF']:
                    # The group belonging to non-root terminal of the pair.
                    grp=self.pin_groups.get(a)
                    if grp in ['GND:ENTRY','GND:LOGIC_RETURN','VREF:ROOT']:grp=self.pin_groups.get(b,grp)
                else:grp=pin.net
                self.connect(grp,a,{b},rule['params']['max_holes'])
        # Ensure hierarchical ground links and each low-current subtree.
        self.connect('GND:LOGIC_RETURN','$GND_LOGIC',{'$GND_ENTRY'})
        for grp in ['GND:REGULATOR_CAP_RETURN','GND:PICO_RETURN','GND:VREF_RETURN','GND:CONTROL_RETURN','GND:RECEIVER_RETURN']:
            root=self.resolve('$GND_LOGIC')
            self.locations[grp].add(root)
            self.join_group(grp,root)
        # Net order is exposed so local reroutes can explore congestion cheaply.
        first=['HDD1_IN1','HDD1_IN2','HDD2_IN1','HDD2_IN2','HDD3_IN1','HDD3_IN2','HDD4_IN1','HDD4_IN2','+3V3','SLEEP','FAULT']
        first=self.config.get('order',['VREF']+first)
        for net in first+sorted(set(self.p.nets)-set(first)-{'GND','VREF'}):
            if net=='VREF':
                vr=self.resolve('$VREF_ROOT')
                for grp in ['VREF:VREF_SOURCE']+[f'VREF:VREF_CH{i}' for i in self.config.get('vref_order',[1,4,2,3])]:
                    self.locations[grp].add(vr);self.join_group(grp,vr)
            else:self.join_group(net)
        # Remaining probes on GND/entry are already included in their branch.
        for grp in ['GND:POWER_RETURN','GND:TVS_RETURN','GND:INPUT_RETURN']:self.join_group(grp)
        return dict(schema_version=1,conductors=self.out,method='L4 hand-seeded, branch-aware bottom-grid A*; insulated fallback')

def main():
    p=Project(HERE)
    cfg=json.loads((HERE/'routing_config.json').read_text('utf8')) if (HERE/'routing_config.json').exists() else {}
    if cfg.get('round')==3:
        from round3_route import R3Router
        router=R3Router(p,cfg)
    else:router=Router(p,cfg)
    wiring=router.route()
    p=p.clone(wiring=wiring)
    report=verify(p)
    save_json(HERE/'wiring.json',wiring)
    save_json(HERE/'local_report.json',report)
    print(summary(report));print(report['metrics']['comparison_tuple'])
    for i in report['issues']:
        if i['severity']=='error' and i.get('status')!='UNCHECKED':print(i['code'],i['detail'])

if __name__=='__main__':main()
