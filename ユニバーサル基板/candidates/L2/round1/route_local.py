"""L2 hand power seeds + branch-aware routing, using shared A* and verifier.
The canonical rule file remains unmodified; unresolved hard rules remain failures.
"""
import sys, json, itertools, math
from collections import defaultdict
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from model import Project, hole, point, compress, path_points, save_json, segment_distance, rect_distance
from router import astar, net_colour, route
from verify import verify, summary

class R:
    def __init__(self,p):
        self.p=p; self.cs=[]; self.used=defaultdict(set); self.quiet_cache={}
        def pinbranch(q):
            if q.net=='GND':
                if q.ref.startswith('U3') or q.ref in {'C311','C312','C321','C322','C331','C332','C341','C342'}: return 'POWER_RETURN'
                if q.ref=='C106': return 'ENTRY_ROOT'
                if q.ref in {'J101','TP463'}: return 'INPUT_RETURN'
                if q.ref=='D105': return 'TVS_RETURN'
                if q.ref=='U107': return 'LOGIC_FEED'
                if q.ref in {'C108','C109','TP464'}: return 'REGULATOR_CAP_RETURN'
                if q.ref=='U201': return 'PICO_RETURN'
                if q.ref in {'C211','R210','TP465'}: return 'VREF_RETURN'
                if q.ref in {'U207','C208','J202','J203'}: return 'RECEIVER_RETURN'
                if q.ref=='R214': return 'CONTROL_RETURN'
                raise ValueError(q.label)
            if q.net=='VREF':
                return 'VREF_CH'+str((int(q.ref[1:])-300)//10) if q.ref.startswith('U3') else 'VREF_ROOT' if q.ref=='C211' else 'VREF_SOURCE'
            return 'PIN'
        for q in p.pins.values(): self.used[q.xy].add((q.net if q.net!='NC' else 'NC:'+q.label,pinbranch(q)))
        for q,label in p.reserved_pads.items(): self.used[q].add(('NC:'+label,'PIN'))
    def add(self,net,path,branch,kind='bare',gauge=None):
        path=[point(q) if isinstance(q,str) else q for q in path]
        # A* paths consist of unit steps; collapse these for true bend accounting.
        if len(path)>2 and all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:])): path=compress(path)
        gauge=gauge or ('1.0mm' if net in {'VM','GND','VIN_RAW','VIN_FUSED','VIN_PROT'} else '0.6mm' if 'OUT' in net else 'AWG24' if net in {'+5V','VSYS'} else 'AWG26')
        contacts=[path[0],path[-1]] if kind=='jumper' else path_points(path)
        for xy in contacts:
            wrong={n for n,b in self.used[xy] if n!=net}
            if wrong: raise ValueError(f'{net}/{branch} at {hole(xy)} touches {wrong}')
        c=dict(id=f'L2_{len(self.cs)+1:03d}',net=net,kind=kind,side='bottom',path=[hole(q) for q in path],gauge=gauge,type='insulated copper' if kind=='jumper' else 'tinned copper',colour=net_colour(net),locked=True,branch_id=branch)
        self.cs.append(c)
        for xy in contacts: self.used[xy].add((net,branch))
        return set(contacts)
    def xy(self,s): return self.p.pin_at(s if '.#' in s or '.' not in s else s.split('.')[0]+'.#'+s.split('.')[1])
    def quiet_mask(self,net):
        quiet={'VREF','SLEEP','FAULT','SN_BUS','SN_RX_IN','SN_PU','UART_RX','ARM','ARM_SW'}
        if net not in quiet:return set()
        if net in self.quiet_cache:return self.quiet_cache[net]
        gap=3 if net=='VREF' else 2
        forbidden=set(); coils=[self.p.parts['J'+str(313+10*k)].rect for k in range(4)]
        outs=[(point(a),point(b)) for c in self.cs if '_OUT' in c['net'] for a,b in zip(c['path'],c['path'][1:])]
        fault=[self.xy(f'U{310+10*k}.9') for k in range(4)]
        for x in range(self.p.columns):
            for y in range(self.p.rows):
                q=(x,y)
                # 0.2mm quiet conductor radius + 0.3mm output conductor radius.
                if any(segment_distance(q,q,a,b)<gap+0.5/2.54-1e-8 for a,b in outs) or any(rect_distance((x*2.54,y*2.54,x*2.54,y*2.54),b)<gap*2.54+0.2-1e-8 for b in coils):forbidden.add(q)
        self.quiet_cache[net]=forbidden
        return forbidden
    def connect(self,net,root,targets,branch,star=False,gauge=None):
        root=self.xy(root) if isinstance(root,str) else root
        targets={self.xy(t) if isinstance(t,str) else t for t in targets}; tree={root}
        if net=='FAULT':
            escape={self.xy(f'U{310+10*k}.9'):(self.xy(f'U{310+10*k}.9')[0]-2,self.xy(f'U{310+10*k}.9')[1]) for k in range(4)}
            targets={escape.get(t,t) for t in targets}
        # Absorb preseeded conductors of this branch recursively.
        def absorb():
            while True:
                old=len(tree)
                for c in self.cs:
                    if c['net']==net and c['branch_id']==branch:
                        ps=[point(q) for q in c['path']]; points=set([ps[0],ps[-1]] if c['kind']=='jumper' else path_points(ps))
                        if points&tree: tree.update(points)
                if len(tree)==old: break
        absorb()
        targets-=tree
        while targets:
            quiet=self.quiet_mask(net); safe_tree=tree-quiet
            if not safe_tree:raise ValueError('no safe source tree '+net)
            _,source,near=min((abs(a[0]-b[0])+abs(a[1]-b[1]),a,b) for a in targets for b in safe_tree)
            blocked={xy for xy,tags in self.used.items() if any(n!=net or (star and b!=branch) for n,b in tags)}
            blocked=(blocked-tree)|quiet
            blocked.discard(source)
            # Existing roots may be shared by the declared star branches, only there.
            path=astar(self.p,source,safe_tree,blocked,0.65)
            direct=abs(source[0]-near[0])+abs(source[1]-near[1])
            limit=40 if net=='VREF' else 60 if '_IN' in net and net.startswith('HDD') else max(direct*1.6,direct+6) if quiet else float('inf')
            if path is None or len(path)-1>limit:
                # Insulated underside wire preserves branch topology at crossings.
                path=astar(self.p,source,{near},quiet-{source,near},0.65); kind='jumper'
                if path is None:raise ValueError(f'no quiet path {net}: {source} -> {near}')
            else: kind='bare'
            tree|=self.add(net,path,branch,kind,gauge)
            absorb()
            targets-=tree
        return tree

def build(mode='base'):
    mode,_,order=mode.partition(':')
    paired=mode.startswith('paired-'); mode=mode.removeprefix('paired-')
    p=Project(HERE,wiring={'schema_version':1,'conductors':[]}); r=R(p)
    for k in range(1,5):
        u='U'+str(300+10*k); x,y=p.pin_at(u+'.VM'); vm='VM_TRUNK'; gn='POWER_RETURN'
        r.add('VM',[(x+4,y-5),(x+5,y-5),(x+5,y)],vm,gauge='0.6mm')
        r.add('VM',[(x+5,y),(x+7,y)],vm,gauge='0.6mm')
        r.add('GND',[(x,y+1),(x+7,y+1)],gn,gauge='0.6mm')
        r.add('GND',[(x+4,y-3),(x+4,y+1)],gn,gauge='0.6mm')
        r.add(f'HDD{k}_OUT1',[(x+5,y+2),(x+8,y+2),(x+8,y+3)],'DRIVER_CH'+str(k),gauge='0.6mm')
        r.add(f'HDD{k}_OUT2',[(x+5,y+3),(x+6,y+3),(x+6,y+5),(x+8,y+5)],'DRIVER_CH'+str(k),gauge='0.6mm')
        r.add(f'HDD{k}_CS',[(x+5,y+6),(x+5,y+7),(x+7,y+7)],'CS_LOCAL')
    # Local regulator bypass pair. Ground branches are kept separate until U107.2.
    r.add('VM',[r.xy('C108.1'),r.xy('U107.1')],'REGULATOR_VM',gauge='AWG24')
    ca,uo=r.xy('C109.1'),r.xy('U107.3')
    r.add('+5V',[ca,uo] if ca[0]==uo[0] or ca[1]==uo[1] else [ca,(uo[0],ca[1]),uo],'PICO_5V',gauge='AWG24')
    r.add('GND',[r.xy('C108.2'),r.xy('U107.2')],'REGULATOR_CAP_RETURN',gauge='AWG24')
    r.add('GND',[r.xy('C109.2'),r.xy('U107.2')],'REGULATOR_CAP_RETURN','jumper','AWG24')
    if paired:
        # Two paired 1mm motor-power spokes: north rows 1/2, south rows 26/27.
        # Coordinates below are zero-based. Each local feed crosses its return
        # trunk using one short 0.6mm insulated two-pitch link.
        r.add('VM',[(3,20),(3,19),(10,19),(10,0),(38,0)],'VM_TRUNK')
        r.add('VM',[(3,20),(3,21),(10,21),(10,27),(38,27)],'VM_TRUNK')
        r.add('GND',[(5,20),(11,20)],'POWER_RETURN')
        r.add('GND',[(11,1),(11,26)],'POWER_RETURN')
        r.add('GND',[(11,1),(37,1)],'POWER_RETURN')
        r.add('GND',[(11,26),(37,26)],'POWER_RETURN')
        for k in range(1,5):
            x,y=p.pin_at('U'+str(300+10*k)+'.VM')
            if y<20:
                r.add('VM',[(x+4,y-5),(x+4,y-7)],'VM_TRUNK','jumper','0.6mm')
                r.add('GND',[(x+4,y-3),(x+3,y-3),(x+3,y-6)],'POWER_RETURN',gauge='0.6mm')
            else:r.add('GND',[(x+4,y-3),(x+4,y-6)],'POWER_RETURN','jumper','0.6mm')
        r.add('VM',[(3,20),(2,20),(2,16)],'VM_TRUNK')
        r.add('VM',[(1,19),(2,19)],'VM_TRUNK')
        r.add('VM',[(10,19),(13,19)],'REGULATOR_VM','jumper','AWG24')
        r.add('GND',[(5,20),(14,20),(14,23)],'LOGIC_FEED','jumper','AWG24')
        r.add('GND',[(5,20),(6,20),(6,16)],'TVS_RETURN','jumper','1.0mm')
        r.add('GND',[(5,20),(5,23),(2,23)],'INPUT_RETURN','jumper','1.0mm')
        r.add('GND',[(2,23),(1,23),(1,30)],'INPUT_RETURN')
        # The SIP converter has VM/+5V immediately either side of its GND pin.
        # Only its south grid exit is free, so use it for the quiet divider return;
        # three insulated spokes carry the other independent quiet branches.
        r.add('GND',[(14,23),(14,24),(26,24),(26,min(21,r.xy('R210.2')[1]))],'VREF_RETURN',gauge='AWG26')
        r.add('GND',[(26,23),(29,23)],'VREF_RETURN',gauge='AWG26')
        r.add('GND',[(14,18),(19,18)],'REGULATOR_CAP_RETURN',gauge='AWG24')
        r.add('GND',[(14,23),(14,24),(36,24)],'PICO_RETURN','jumper','AWG24')
        r.add('GND',[(14,23),(49,23),(49,13)],'RECEIVER_RETURN','jumper','AWG26')
        r.add('GND',[(14,23),(50,23),(50,26)],'CONTROL_RETURN','jumper','AWG26')
    # Quiet return bus inside the Pico socket envelope; signal pins escape outward.
    pp=p.parts['U201']; angle=pp.data.get('rotation',0)
    if angle==90:
        r.add('GND',[(36,20),(51,20)],'PICO_RETURN',gauge='AWG24')
        for xx in (36,41,46,51):
            r.add('GND',[(xx,17),(xx,20)],'PICO_RETURN',gauge='AWG24')
            r.add('GND',[(xx,24),(xx,20)],'PICO_RETURN',gauge='AWG24')
    elif angle==0:
        x,y=p.pin_at('U201.GP0')
        r.add('GND',[(x+3,y+2),(x+3,y+17)],'PICO_RETURN',gauge='AWG24')
        for yy in (y+2,y+7,y+12,y+17):
            r.add('GND',[(x,yy),(x+3,yy)],'PICO_RETURN',gauge='AWG24')
            r.add('GND',[(x+7,yy),(x+3,yy)],'PICO_RETURN',gauge='AWG24')
    # Compact receiver wiring pattern: use a short insulated capacitor return
    # because the input pin lies between OE/GND and the capacitor negative.
    x,y=p.pin_at('U207./OE')
    r.add('GND',[(x,y),(x+1,y),(x+1,y+2),(x,y+2)],'RECEIVER_RETURN',gauge='AWG26')
    r.add('GND',[(x,y-2),(x,y+2)],'RECEIVER_RETURN','jumper','AWG26')
    if paired:
        r.add('GND',[(x+3,y-2),(x,y-2)],'RECEIVER_RETURN','jumper','AWG26')
        r.add('GND',[(x+3,y-6),(x+4,y-6),(x+4,y-2),(x+3,y-2)],'RECEIVER_RETURN',gauge='AWG26')
    r.add('+3V3',[(x+1,y-2),(x+2,y-2),(x+2,y),(x+3,y)],'LOGIC_3V3',gauge='AWG26')
    r.add('SN_RX_IN',[(x,y-3),(x-1,y-3),(x-1,y+1),(x,y+1)],'RECEIVER_SIGNAL')
    r.add('SN_BUS',[(x+3,y-7),(x+2,y-7),(x+2,y-3),(x+3,y-3)],'RECEIVER_SIGNAL')
    r.add('SN_BUS',[(x+2,y-7),(x,y-7),(x,y-6)],'RECEIVER_SIGNAL')
    r.connect('UART_RX','U207.4',['U201.2'],'UART_LOCAL')
    # Short source leads have priority over the four separate VREF spokes.
    root=r.xy('C211.1'); a,b=root
    r.add('VREF',[(a,b),(a,b-1),(a-1,b-1)],'VREF_SOURCE')
    if r.xy('R210.1')==(a-1,b-2):
        r.add('VREF',[(a-1,b-1),(a-1,b-2)],'VREF_SOURCE')
        r.add('VREF',[(a-1,b-2),(a-1,b-4),(a,b-4)],'VREF_SOURCE')
    else:
        r.add('VREF',[(a,b-1),(a,b-2)],'VREF_SOURCE')
        r.add('VREF',[(a-1,b+2),(a,b+2),(a,b)],'VREF_SOURCE')
    # Named terminal exceptions: leave every FAULT pin two holes west, away
    # from the nearby OUT2 trace. All subsequent FAULT paths use the full mask.
    for k in range(4):
        fx,fy=r.xy(f'U{310+10*k}.9')
        r.add('FAULT',[(fx,fy),(fx-2,fy)],'QUIET_FAULT')
    if mode in {'inputs','controls'}:
        indices=[int(i) for i in order.split(',')] if order else range(8)
        for i in indices:
            k,j=i//2+1,i%2+1
            net=f'HDD{k}_IN{j}'; pins=[q for q in p.pins.values() if q.net==net]
            r.connect(net,pins[0].xy,[pins[1].xy],'PWM')
    if mode=='controls':
        for net in ('SLEEP','FAULT','+3V3','ARM','ARM_SW'):
            pins=[q for q in p.pins.values() if q.net==net]
            r.connect(net,pins[0].xy,[q.xy for q in pins[1:]],'CONTROL')
    # VREF first, before power trees can obstruct the central quiet corridor.
    for k in range(1,5): r.connect('VREF','C211.1',[f'U{300+10*k}.7'],'VREF_CH'+str(k),star=True)
    r.connect('VREF','C211.1',['R209.2','R210.1','TP466.1'],'VREF_SOURCE',star=True)
    # Complete all sensitive signals with projected output/connector exclusion.
    for net,root in [('SLEEP','U201.21'),('FAULT','R215.2'),('SN_RX_IN','U207.2'),('SN_PU','R205.2'),('ARM','U201.19'),('ARM_SW','R212.2')]:
        r.connect(net,root,[q.xy for q in p.pins.values() if q.net==net],'QUIET_'+net)
    # G01: all four motor returns share a heavy tree, separate from quiet feed.
    entry=r.xy('C106.2'); logic=r.xy('U107.2')
    if not paired:
        r.connect('GND',entry,[f'U{300+10*k}.13' for k in range(1,5)],'POWER_RETURN',star=True)
        r.connect('GND',entry,[logic],'LOGIC_FEED',star=True,gauge='AWG24')
        r.connect('GND',entry,['D105.2'],'TVS_RETURN',star=True)
        r.connect('GND',entry,['J101.2','TP463.1'],'INPUT_RETURN',star=True)
    # G02: independent quiet branches at converter GND.
    pico=[f'U201.{n}' for n in (3,8,13,18,23,28,33,38)]
    r.connect('GND',logic,pico,'PICO_RETURN',star=True,gauge='AWG24')
    r.connect('GND',logic,['C211.2','R210.2','TP465.1'],'VREF_RETURN',star=True,gauge='AWG26')
    r.connect('GND',logic,['U207.1','U207.3','C208.2','J202.2','J203.2'],'RECEIVER_RETURN',star=True,gauge='AWG26')
    r.connect('GND',logic,['R214.2'],'CONTROL_RETURN',star=True,gauge='AWG26')
    r.connect('GND',logic,['C108.2','C109.2','TP464.1'],'REGULATOR_CAP_RETURN',star=True,gauge='AWG24')
    # Switched motor supply tree, then input and converter feed.
    if not paired:r.connect('VM','C106.1',[f'U{300+10*k}.14' for k in range(1,5)],'VM_TRUNK')
    r.connect('VM','C106.1',['D105.1','J104.2','TP460.1'],'VM_TRUNK')
    r.connect('VM','C106.1',['U107.1'],'REGULATOR_VM',gauge='AWG24')
    for net,root,ends in [('VIN_RAW','J101.1',['F102.1']),('VIN_FUSED','F102.2',['D103.2']),('VIN_PROT','D103.1',['J104.1'])]:
        r.connect(net,root,ends,'ENTRY_SERIES')
    save_json(HERE/'wiring.json',{'schema_version':1,'conductors':r.cs})
    # Shared router completes all other nets while preserving every power/star seed.
    p=Project(HERE); wiring=route(p)
    for c in wiring['conductors']:
        if not c.get('locked'):
            c['side']='bottom'
            c['gauge']='AWG24' if c['net'] in {'+5V','VSYS'} else 'AWG26'
    save_json(HERE/'wiring.json',wiring)
    print(summary(verify(Project(HERE))))

if __name__=='__main__': build(sys.argv[1] if len(sys.argv)>1 else 'base')
