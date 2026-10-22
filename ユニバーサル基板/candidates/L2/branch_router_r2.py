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
        path=[q for i,q in enumerate(path) if i==0 or q!=path[i-1]]
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
            limit=40 if net=='VREF' else 60 if '_IN' in net and net.startswith('HDD') else 40 if net=='UART_RX' else 78 if net in {'SLEEP','FAULT'} else float('inf')
            if path is None or len(path)-1>limit:
                # Insulated underside wire preserves branch topology at crossings.
                path=astar(self.p,source,{near},quiet-{source,near},0.65); kind='jumper'
                if path is None:raise ValueError(f'no quiet path {net}: {source} -> {near}')
            else: kind='bare'
            tree|=self.add(net,path,branch,kind,gauge)
            absorb()
            targets-=tree
        return tree
