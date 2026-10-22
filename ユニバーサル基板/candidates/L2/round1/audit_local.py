"""Additional transparent candidate measurements; never overrides ub.py audit."""
import sys,math,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from model import Project,save_json,segment_distance,rect_distance,rotate,hole
from verify import verify,net_graph,shortest

def radius(gauge):
    if gauge.endswith('mm'):return float(gauge[:-2])/2
    if gauge.startswith('AWG'):return .127*92**((36-int(gauge[3:]))/39)/2
    raise ValueError(gauge)
def clip(a,b,centres,rad):
    """Return segment pieces outside the union of specified escape disks."""
    pieces=[(a,b)]
    for cx,cy in centres:
        out=[]
        for u,v in pieces:
            dx,dy=v[0]-u[0],v[1]-u[1];aa=dx*dx+dy*dy
            if aa<1e-14:
                if math.hypot(u[0]-cx,u[1]-cy)>rad+1e-8:out.append((u,v))
                continue
            bb=2*((u[0]-cx)*dx+(u[1]-cy)*dy);cc=(u[0]-cx)**2+(u[1]-cy)**2-rad*rad
            disc=bb*bb-4*aa*cc;ts=[0.,1.]
            if disc>=0:ts+= [t for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)) if 0<t<1]
            ts.sort()
            for t0,t1 in zip(ts,ts[1:]):
                m=(t0+t1)/2
                if math.hypot(u[0]+m*dx-cx,u[1]+m*dy-cy)>rad+1e-8:
                    out.append(((u[0]+t0*dx,u[1]+t0*dy),(u[0]+t1*dx,u[1]+t1*dy)))
        pieces=out
    return pieces
def sdrect(a,b,r):
    if any(r[0]<=p[0]<=r[2] and r[1]<=p[1]<=r[3] for p in (a,b)):return 0.
    c=[(r[0],r[1]),(r[2],r[1]),(r[2],r[3]),(r[0],r[3])]
    return min(segment_distance(a,b,u,v) for u,v in zip(c,c[1:]+c[:1]))

def run():
    p=Project(HERE);report=verify(p);out=HERE/'out';out.mkdir(exist_ok=True)
    lengths=defaultdict(float);pieces=Counter();bends=Counter()
    for c in p.conductors:
        lengths[c['gauge']]+=c['length_mm'];pieces[c['kind']]+=1
        bends[c['kind']]+=sum(abs((b[0]-a[0])*(c0[1]-b[1])-(b[1]-a[1])*(c0[0]-b[0]))>1e-8 for a,b,c0 in zip(c['xy'],c['xy'][1:],c['xy'][2:]))
    g={net:net_graph(p,net) for net in p.nets}
    def pathlength(net,a,b):return round(shortest(g[net],p.pin_at(a)).get(p.pin_at(b),float('inf')),3)
    inp=[dict(net=f'HDD{k}_IN{j}',length_mm=pathlength(f'HDD{k}_IN{j}',f'U201.GP{2*k+j-1}',f'U{300+10*k}.IN{j}')) for k in range(1,5) for j in (1,2)]
    vrefs={f'U{300+10*k}.VREF':pathlength('VREF','C211.P1',f'U{300+10*k}.VREF') for k in range(1,5)}
    soft=defaultdict(float)
    for issue in report['issues']:
        if issue['severity']=='warning' and issue.get('status')!='UNCHECKED' and 't7_penalty' in issue:soft[issue.get('priority','unspecified')]+=issue['t7_penalty']
    hard={r['id'] for r in p.rules['rules'] if r['severity']=='hard'}
    hc=Counter(r['status'] for r in report['rule_checks'] if r['id'] in hard)
    pins={q.xy for q in p.pins.values()};contacts={xy for c in p.conductors for xy in c['contacts']}
    # Exact centre-line segment checks with wire radii and declared FAULT disks.
    checks={}
    for rid in ('S01','S02'):
        rule=next(r for r in p.rules['rules'] if r['id']==rid);pr=rule['params'];fail=[];minimum=float('inf')
        targets=[c for c in p.conductors if c['net'] in pr['b_nets']]
        rects=[(ref,tuple(q/p.pitch for q in p.parts[ref].rect)) for ref in pr['b_parts']]
        escape=[p.pin_at(v['pin'].replace('.', '.#')) for v in pr['terminal_exceptions']]
        sources=[(c['id'],c['net'],a,b,radius(c['gauge'])) for c in p.conductors if c['net'] in pr['a_nets'] for a,b in zip(c['xy'],c['xy'][1:])]
        sources +=[(q.label,q.net,q.xy,q.xy,.453) for q in p.pins.values() if q.net in pr['a_nets']]
        for cid,net,a,b,rad in sources:
            for aa,bb in clip(a,b,escape if net=='FAULT' else [],2):
                tests=[]
                for c in targets:
                    tests.append((c['id'],min(segment_distance(aa,bb,u,v) for u,v in zip(c['xy'],c['xy'][1:]))*p.pitch-rad-radius(c['gauge'])))
                for ref,rect in rects:tests.append((ref,sdrect(aa,bb,rect)*p.pitch-rad))
                other,value=min(tests,key=lambda t:t[1]);minimum=min(minimum,value)
                if value<pr['min_holes']*p.pitch-1e-6:fail.append(dict(a=cid,b=other,surface_mm=round(value,5),required_mm=pr['min_holes']*p.pitch))
        checks[rid]=dict(status='FAIL' if fail else 'PASS_IN_LOCAL_MODEL',min_surface_mm=round(minimum,5),violations=fail)
    physical=[];ox,oy=p.board['grid_origin_mm']['x'],p.board['grid_origin_mm']['y'];W,H=p.board['width_mm'],p.board['height_mm']
    for part in p.parts.values():
        for name in ('mating_face','usb_mouth'):
            f=part.footprint.get('features',{}).get(name)
            if not f:continue
            v=rotate((f['x_mm'],f['y_mm']),part.data.get('rotation',0));origin=part.pins[0].xy
            x,y=ox+origin[0]*p.pitch+v[0],oy+origin[1]*p.pitch+v[1]
            physical.append(dict(ref=part.ref,feature=name,physical_xy_mm=[round(x,3),round(y,3)],nearest_edge_mm=round(min(x,y,W-x,H-y),3)))
    hashes={}
    for a,b in [('board.json','board.json'),('footprints_ub.json','footprints_ub.json'),('design_rules.json','design_rules.json'),('netlist_ub.csv','netlist.csv')]:
        digest=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
        hashes[a]=dict(shared_sha256=digest(ROOT/a),candidate_sha256=digest(HERE/b),identical=digest(ROOT/a)==digest(HERE/b))
    gauge_checks={}
    for rule in p.rules['rules']:
        if rule['type']!='trunk_gauge':continue
        pr=rule['params'];cs=[c for c in p.conductors if c['net'] in pr['nets'] and set(c.get('branch_ids',[c.get('branch_id')]))&set(pr['branch_ids'])]
        areas=[math.pi*radius(c['gauge'])**2 for c in cs]
        gauge_checks[rule['id']]=dict(status='UNCHECKED_NO_OFFBOARD_HARNESS' if not cs else 'PASS_FOR_REPRESENTED_ONBOARD_WIRES' if min(areas)>=pr['min_copper_mm2']-1e-8 else 'FAIL',selected_conductors=len(cs),min_area_mm2=round(min(areas),6) if areas else None,required_area_mm2=pr['min_copper_mm2'],excluded='Contacts, off-board wires, voltage drop and ambient/startup behaviour are not proved by this area comparison.')
    probe_gaps={}
    for ref,part in p.parts.items():
        if not ref.startswith('TP'):continue
        q=part.pins[0].xy;rect=(q[0]*p.pitch,q[1]*p.pitch,q[0]*p.pitch,q[1]*p.pitch)
        other,gap=min(((r,rect_distance(rect,part2.rect)) for r,part2 in p.parts.items() if r!=ref),key=lambda z:z[1])
        probe_gaps[ref]=dict(nearest_other_body=other,centre_to_body_mm=round(gap,4),one_pitch_planar_clearance=gap>=p.pitch-1e-8)
    data=dict(hard_rules=dict(hc),soft_t7_penalty_by_priority=dict(soft),soft_t7_penalty=sum(soft.values()),length_mm_by_gauge={k:round(v,3) for k,v in lengths.items()},pieces=dict(pieces),bends=dict(bends),input_lines=inp,longest_IN_mm=max(i['length_mm'] for i in inp),vref_branches_mm=vrefs,wire_solder_locations=len(contacts),pin_locations=len(pins),unique_solder_locations=len(pins|contacts),conductor_end_joints=2*len(p.conductors),checks=checks,features_physical=physical,input_hashes=hashes,mounting_min_centre_edge_mm=min(min(m['x'],m['y'],W-m['x'],H-m['y']) for m in p.board['mounting_holes_mm']),notes=['Local supplementary measurements do not change official ub.py status.','Surface audit uses nominal conductor radii and .453mm socket-pin circumscribed radius; pads, solder blobs and 3D wire heights remain unproved.','Solder locations count every exposed touched land, following the conservative tool contact model; actual intermediate support soldering needs a build plan.'])
    data['onboard_area_checks']=gauge_checks;data['probe_point_checks']=probe_gaps
    save_json(out/'audit_local.json',data)
    print(json.dumps({k:data[k] for k in ('hard_rules','soft_t7_penalty','pieces','bends','longest_IN_mm','vref_branches_mm')}));print({k:(v['status'],v['min_surface_mm'],len(v['violations'])) for k,v in checks.items()})

if __name__=='__main__':run()
