"""Round-2 branch-aware routing using the shared A* without changing tools.

Preserves the hand-seeded power distribution and separate hierarchical GND/VREF
branches. Every trial is checked by the updated canonical verifier and tuple.
"""
from common import *
from collections import defaultdict
from model import path_points, compress, distance
from router import astar, net_colour
from verify import verify, summary, UnionFind
import random, time

CU={'1.0 mm':math.pi/4,'0.6 mm':math.pi*.6**2/4,'0.51 mm':math.pi*.51**2/4,'0.5 mm':math.pi*.5**2/4}

def make(seed=1,write=True,bare_mask=15,edge_mode=0):
    p=project(json.loads((HERE/'placement.south.json').read_text(encoding='utf8')),{'schema_version':1,'conductors':[]})
    pin={f'{a.ref}.{a.number}':a.xy for a in p.pins.values()}
    E=pin['C106.2']; L=pin['U107.2']; V=pin['C211.1']
    labels={}; actual={}; endpoints=defaultdict(set); allowed=defaultdict(set)
    def assign(name,net,names,root=None):
        actual[name]=net
        for n in names: labels[n]=name; endpoints[name].add(pin[n])
        if root is not None: endpoints[name].add(root); allowed[name].add(root)
    gpower=[f'{ref}.{n}' for ref in ['U310','U320','U330','U340'] for n in ['2','13']]+[f'C{300+c*10+d}.2' for c in range(1,5) for d in [1,2]]
    assign('G_POWER','GND',gpower, E)
    assign('G_INPUT','GND',['J101.2','TP463.1'],E)
    assign('G_TVS','GND',['D105.2'],E)
    assign('G_LINK','GND',[],E); endpoints['G_LINK'].add(L); allowed['G_LINK'].add(L)
    assign('G_PICO','GND',[f'U201.{n}' for n in [3,8,13,18,23,28,33,38]]+['TP464.1'],L)
    assign('G_REF','GND',['C211.2','R210.2','TP465.1'],L)
    assign('G_RX','GND',['U207.1','U207.3','C208.2','J202.2','J203.2'],L)
    assign('G_CONTROL','GND',['R214.2'],L)
    assign('G_CAPS','GND',['C108.2','C109.2'],L)
    labels['C106.2']='ENTRY_ROOT'; actual['ENTRY_ROOT']='GND'
    labels['U107.2']='LOGIC_ROOT'; actual['LOGIC_ROOT']='GND'
    assign('V_SOURCE','VREF',['R209.2','R210.1','TP466.1'],V)
    for ch in range(1,5): assign(f'V_CH{ch}','VREF',[f'U{300+ch*10}.7'],V)
    labels['C211.1']='REF_ROOT'; actual['REF_ROOT']='VREF'
    for name,q in ((f'{a.ref}.{a.number}',a) for a in p.pins.values()):
        if name not in labels:
            lab=q.net if q.net!='NC' else 'NC:'+name
            labels[name]=lab;actual[lab]=q.net
            if q.net!='NC': endpoints[lab].add(q.xy)
    occ=defaultdict(set)
    for name,lab in labels.items(): occ[pin[name]].add(lab)
    for xy,name in p.reserved_pads.items():occ[xy].add('NC_EXTRA:'+name)
    wires=[]; ufs=defaultdict(UnionFind); locations=defaultdict(set)
    for lab,pts in endpoints.items(): locations[lab].update(pts)
    def add(lab,path,kind='bare',gauge='0.5 mm',branches=None):
        path=[pin[z] if isinstance(z,str) and '.' in z else point(z) if isinstance(z,str) else z for z in path]
        path=[q for i,q in enumerate(path) if i==0 or q!=path[i-1]]
        path=list(dict.fromkeys(path)) if kind=='jumper' else path
        if len(path)<2:return
        pts=[path[0],path[-1]] if kind=='jumper' else path_points(path)
        conflicts=[(hole(q),occ[q]-{lab}) for q in pts if occ[q]-{lab} and q not in allowed[lab]]
        if conflicts: raise ValueError(f'{lab} {kind} {path} CONFLICT {conflicts[:5]}')
        net=actual[lab]
        if kind=='jumper' and gauge in CU:
            gauge={'1.0 mm':'AWG18','0.6 mm':'AWG22','0.51 mm':'AWG24','0.5 mm':'AWG24'}[gauge]
        c={'id':f'L1W{len(wires)+1:03d}','net':net,'kind':kind,'side':'bottom','path':[hole(q) for q in compress(path) if q is not None],
           'gauge':gauge,'type':'insulated copper' if kind=='jumper' else 'tinned copper','colour':net_colour(net),
           'locked':True,'routing_group':lab,'branch_ids':branches or [lab]}
        if gauge in CU:c.update(area_mm2=CU[gauge],diameter_mm=float(gauge.split()[0]))
        wires.append(c)
        for q in pts:occ[q].add(lab);locations[lab].add(q);ufs[lab].union(pts[0],q)
    # Heavy paired trunks, one bend each, plus identical four-channel blocks.
    add('VM',[(2,16),(2,7)],gauge='1.0 mm',branches=['VM_TRUNK'])
    add('VM',[(0,7),(42,7)],gauge='1.0 mm',branches=['VM_TRUNK'])
    add('G_POWER',[E,(4,9),(42,9)],gauge='1.0 mm',branches=['POWER_RETURN_TRUNK'])
    add('G_POWER',[(42,9),(48,9)],gauge='0.6 mm',branches=['DRIVER_CH1'])
    for ch,x in zip([3,4,2,1],[5,19,33,47]):
        b=300+ch*10; bid=[f'DRIVER_CH{ch}']
        add('VM',[(x-5,7),(x-5,3),(x-1,3)],gauge='0.6 mm',branches=bid)
        add('VM',[(x-1,3),(x-1,5),(x,5)],gauge='0.6 mm',branches=bid)
        add('VM',[(x-4,4),(x-1,4)],gauge='0.6 mm',branches=bid)
        add('G_POWER',[(x+1,5),(x+1,10)],'bare' if ch==1 and edge_mode&1 else 'jumper','0.6 mm',bid)
        add('G_POWER',[(x+1,10),(x+1,9)],gauge='0.6 mm',branches=bid)
        add('G_POWER',[(x-4,6),(x+1,6),(x+1,5)],gauge='0.6 mm',branches=bid)
        add('G_POWER',[(x,3),(x+1,3),(x+1,5)],gauge='0.6 mm',branches=bid)
        add(f'HDD{ch}_OUT1',[(x+2,5),(x+2,2)],gauge='0.6 mm',branches=bid)
        add(f'HDD{ch}_OUT2',[(x+3,5),(x+3,3),(x+4,3),(x+4,2)],gauge='0.6 mm',branches=bid)
        add(f'HDD{ch}_CS',[(x+6,5),(x+6,3)],branches=[f'CS_CH{ch}'])
    # Protection entry and shortest local loops.
    add('VM',['D105.1',(1,16),'C106.1'],gauge='1.0 mm',branches=['VM_TRUNK'])
    add('G_TVS',['D105.2',(5,16),'C106.2'],gauge='1.0 mm',branches=['TVS_RETURN'])
    add('G_INPUT',['J101.2',(2,18),(4,18),'C106.2'],gauge='1.0 mm',branches=['INPUT_RETURN'])
    add('G_INPUT',['J101.2',(2,19),(8,19),'TP463.1'],gauge='1.0 mm',branches=['INPUT_RETURN'])
    add('VIN_RAW',['J101.1',(5,22),(9,22),'F102.1'],gauge='1.0 mm',branches=['ENTRY_SERIES'])
    add('VIN_FUSED',['F102.2',(10,25),(10,15),'D103.2'],gauge='1.0 mm',branches=['ENTRY_SERIES'])
    add('VIN_PROT',['D103.1','J104.1'],'jumper','1.0 mm',['ENTRY_SERIES'])
    # Regulator caps: opposed 0.51 mm positive feeds, independent cap returns.
    add('VM',['C108.1','U107.1'],gauge='0.51 mm',branches=['REGULATOR_VM'])
    add('G_CAPS',['C108.2','U107.2'],gauge='0.51 mm',branches=['REGULATOR_CAP_RETURN'])
    add('+5V',['C109.1','U107.3'],gauge='0.51 mm',branches=['PICO_5V'])
    add('G_CAPS',['C109.2','U107.2'],gauge='0.51 mm',branches=['REGULATOR_CAP_RETURN'])
    # Receiver decoupling and direct divider loops.
    add('+3V3',['C208.1',(49,32),'U207.5'],gauge='0.5 mm',branches=['LOGIC_3V3'])
    add('G_RX',['C208.2','U207.3'],'jumper','0.5 mm',['RECEIVER_RETURN'])
    add('G_RX',['U207.1',(47,34),(47,36),'U207.3'],gauge='0.51 mm',branches=['RECEIVER_RETURN'])
    add('SN_BUS',['R204.1','J202.1'])
    add('SN_RX_IN',['R204.2',(43,35),'U207.2'])
    add('V_SOURCE',['C211.1','R209.2','R210.1','TP466.1'],branches=['VREF_SOURCE'])
    add('G_REF',['C211.2','R210.2'],gauge='0.51 mm',branches=['VREF_RETURN'])
    add('G_REF',[(30,16),'TP465.1'],gauge='0.51 mm',branches=['VREF_RETURN'])
    # Dedicated paired regulator supply/return from entry, isolated from motor taps.
    add('VM',['C106.1',(0,16),(0,29),'U107.1'],gauge='0.51 mm',branches=['REGULATOR_VM'])
    add('G_LINK',['C106.2',(3,16),(3,17),(1,17),(1,28),(15,28)],gauge='0.51 mm',branches=['LOGIC_RETURN'])
    add('G_LINK',[(15,28),'U107.2'],'jumper','0.51 mm',['LOGIC_RETURN'])
    add('SLEEP',['R214.1',(41,35),'J213.2'])
    add('VM',['TP460.1','C106.1'],gauge='1.0 mm',branches=['VM_PROBE'])
    add('+5V',['U107.3','D110.2'],'jumper','0.51 mm',['PICO_5V'])
    # Pico south USB, GPIO column east; ground rails stay between its socket rows.
    add('G_REF',['U107.2','C211.2'],'jumper','0.51 mm',['VREF_RETURN'])
    add('G_CONTROL',['U107.2','R214.2'],'jumper','0.51 mm',['CONTROL_RETURN'])
    add('G_RX',['U107.2','U207.3'],'jumper','0.51 mm',['RECEIVER_RETURN'])
    add('G_PICO',['U107.2','TP464.1'],'jumper','0.51 mm',['PICO_RETURN'])
    add('G_PICO',['TP464.1',(26,27),(30,27)],gauge='0.51 mm',branches=['PICO_RETURN'])
    add('G_PICO',[(30,22),(30,37),(35,37),(35,22)],gauge='0.51 mm',branches=['PICO_RETURN'])
    for yy in [22,27,32,37]:
        add('G_PICO',[(36,yy),(35,yy)],gauge='0.51 mm',branches=['PICO_RETURN'])
        add('G_PICO',[(29,yy),(30,yy)],gauge='0.51 mm',branches=['PICO_RETURN'])
    for ch,x in zip([3,4,2,1],[5,19,33,47]):
        if ch==1 and edge_mode&2:add('FAULT',[(x+5,5),(x+5,6),(x+7,6),(x+7,19)],branches=[f'FAULT_CH{ch}'])
        else:add('FAULT',[(x+5,5),(x+7,19)],'jumper',branches=[f'FAULT_CH{ch}'])
    # Round 3: let both IN pins escape through the grid, then insulate only blocked islands.
    add('ARM',['U201.19',(39,21),'R212.1'])

    # Quiet nets must avoid OUT copper/connector envelopes even for insulated routes.
    from model import segment_distance
    outsegments=[(a,b) for c in wires if '_OUT' in c['net'] for a,b in zip([point(z) for z in c['path']],[point(z) for z in c['path']][1:])]
    outrects=[z.rect for z in p.parts.values() if z.id in ['J313','J323','J333','J343']]
    quiet={'VREF','SLEEP','FAULT','SN_BUS','SN_RX_IN','SN_PU','UART_RX','ARM','ARM_SW'}
    masks={}
    for net in quiet:
        gap=3 if net=='VREF' else 2
        bad=set()
        for xx in range(p.columns):
            for yy in range(p.rows):
                q=(xx,yy)
                exception=net=='FAULT' and any(distance(q,pin[f'U{300+i*10}.9'])<=2 for i in range(1,5))
                if exception:continue
                pr=(xx*PITCH,yy*PITCH,xx*PITCH,yy*PITCH)
                if any(segment_distance(q,q,a,b)<gap+.55/PITCH-1e-8 for a,b in outsegments) or any(rect_distance(pr,r)<gap*PITCH+.25-1e-8 for r in outrects):bad.add(q)
        masks[net]=bad

    def connect(lab,root=None,max_path=None,gauge=None):
        pts=locations[lab]
        if not pts:return
        root=root if root is not None else min(pts)
        gauge=gauge or ('0.51 mm' if lab.startswith('G_') or actual[lab] in ['VM','+5V','VSYS','+3V3'] else '0.5 mm')
        blocked={q for q,v in occ.items() if v-{lab} and q not in allowed[lab]}
        safety=masks.get(actual[lab],set())
        blocked|=safety
        # Join every geometrically reachable bare island BEFORE adding jumpers.
        # Root-first greedy routing otherwise misses cheap merges in other regions.
        from collections import deque
        region={}; serial=0
        for xx in range(p.columns):
            for yy in range(p.rows):
                q=(xx,yy)
                if q in region or q in blocked or not p.usable(q):continue
                serial+=1;todo=deque([q]);region[q]=serial
                while todo:
                    z=todo.popleft()
                    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                        t=(z[0]+dx,z[1]+dy)
                        if t not in region and t not in blocked and p.usable(t):region[t]=serial;todo.append(t)
        while True:
            groups=defaultdict(set)
            for z in pts:groups[ufs[lab].find(z)].add(z)
            groups=list(groups.values())
            if len(groups)<2:break
            pairs=[];possible=[]
            for i,a in enumerate(groups):
                for j,b in enumerate(groups[:i]):
                    pairs.append(min((man(x,y),x,y) for x in a for y in b))
                    viable=[(man(x,y),x,y) for x in a for y in b if region.get(x,-1)==region.get(y,-2)]
                    if viable:possible.append(min(viable))
            path=None
            for _,src,near in sorted(possible):
                trial=astar(p,src,{near},blocked,1.2)
                if trial is not None and (max_path is None or len(trial)-1<=max_path):path=trial;break
            kind='bare'
            if path is None:
                kind='jumper';_,src,near=min(pairs);path=[src,near]
                if any((round(src[0]+(near[0]-src[0])*t/100),round(src[1]+(near[1]-src[1])*t/100)) in safety for t in range(101)):
                    path=astar(p,src,{near},safety,2)
                    if path is None:raise ValueError('No quiet jumper corridor for '+lab)
            add(lab,compress(path),kind,gauge)
    # Anchor order is varied only within the quiet band; shared data never changes.
    rng=random.Random(seed)
    ground_order=['G_LINK','G_REF','G_PICO','G_RX','G_CONTROL']
    if seed>1:rng.shuffle(ground_order)
    for lab in ground_order:connect(lab,E if lab=='G_LINK' else L)
    # Remaining non-star nets use the same shared A*, shortest allowed bare trees.
    done=set(ground_order)|{'G_CAPS','G_POWER','G_INPUT','G_TVS','V_SOURCE'}|{f'V_CH{i}' for i in range(1,5)}
    other=[lab for lab in endpoints if lab not in done and actual[lab]!='NC']
    other += [f'V_CH{i}' for i in range(1,5)]
    ranks={'VM':0,'+5V':1,'VSYS':2,'SN_BUS':3,'SN_RX_IN':4,'UART_RX':5,'SLEEP':7,'FAULT':8,'+3V3':10}
    if seed==1:other.sort(key=lambda lab:(ranks.get(lab,6 if '_IN' in lab else 9),-len(endpoints[lab]),lab))
    else:
        rng.shuffle(other)
        other.sort(key=lambda lab:0 if actual[lab] in ['VM','+5V','VSYS'] else 1)
    for lab in other:
        limit=60 if '_IN' in lab else 80 if lab in ['SLEEP','FAULT'] else 40 if lab=='UART_RX' else None
        connect(lab,V if lab.startswith('V_CH') else None,40 if lab.startswith('V_CH') else limit)
    wiring={'schema_version':1,'conductors':wires,'candidate':'L1 round3','router':'local branch-aware A* using tools/router.py astar','seed':seed,'bare_in1_mask':bare_mask,'edge_mode':edge_mode}
    q=p.clone(wiring=wiring)
    report=verify(q)
    if not report['lvs_pass']:
        print(summary(report))
        for z in report['issues']:
            if z['code'].startswith('LVS:') or z['code'] in ['SHORT','WIRE_NET_MISMATCH','HOLE_NET_CONFLICT']:print(z)
        raise ValueError('LVS failed')
    if write:
        save_json(HERE/'wiring.r3.json',wiring)
        save_json(HERE/'preview.r3.json',report)
        print(summary(report))
        for z in report['issues']:
            if z['severity']=='error' and z.get('status')!='UNCHECKED': print(z['code'],z['detail'])
    return wiring,report

