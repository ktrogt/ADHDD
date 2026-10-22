"""Supplementary measurements; never changes the official acceptance result."""
import sys,math,json,csv,re,hashlib
from pathlib import Path
from collections import defaultdict,Counter
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent
sys.path.insert(0,str(BASE/'tools'))
from model import Project,save_json,hole,segment_distance,rect_distance,write_csv,rotate,point
from verify import shortest,net_graph

def diameter(gauge):
    if gauge=='1.0mm':return 1.0
    m=re.fullmatch(r'AWG(\d+)',gauge)
    if not m:raise ValueError('unknown gauge '+gauge)
    return .127*92**((36-int(m[1]))/39)
def point_segment(q,a,b):
    u=(b[0]-a[0],b[1]-a[1]);d=u[0]**2+u[1]**2
    t=max(0,min(1,((q[0]-a[0])*u[0]+(q[1]-a[1])*u[1])/d)) if d else 0
    return math.dist(q,(a[0]+t*u[0],a[1]+t*u[1]))
def point_rect(q,r):return math.hypot(max(r[0]-q[0],q[0]-r[2],0),max(r[1]-q[1],q[1]-r[3],0))
def gauge_area(c):return math.pi*diameter(c['gauge'])**2/4
def resistance_graph(p,net):
    g=defaultdict(dict)
    for c in p.conductors:
        if c['net']!=net:continue
        if c['kind']=='jumper':pieces=[(c['contacts'][0],c['contacts'][-1],c['length_mm'])]
        else:pieces=[(a,b,p.pitch) for a,b in zip(c['contacts'],c['contacts'][1:])]
        for a,b,L in pieces:
            R=.01724*(L/1000)/gauge_area(c)
            g[a][b]=min(g[a].get(b,math.inf),R);g[b][a]=g[a][b]
    return g
def get_dist(p,net,a,b,resistance=False):
    graph=resistance_graph(p,net) if resistance else net_graph(p,net)
    return shortest(graph,p.pin_at(a)).get(p.pin_at(b))

if __name__=='__main__':
    p=Project(HERE);r=json.loads((HERE/'out/report.json').read_text(encoding='utf-8'))
    definitions={x['id']:x for x in p.rules['rules']}
    hard=Counter(x['status'] for x in r['rule_checks'] if definitions[x['id']]['severity']=='hard')
    soft=Counter(x['status'] for x in r['rule_checks'] if definitions[x['id']]['severity']=='soft')
    lengths=defaultdict(float);by_kind=Counter();bare_bends=jump_bends=0
    solder=set(q.xy for q in p.pins.values())|set(p.reserved_pads)
    joints=defaultdict(list)
    for c in p.conductors:
        lengths[c['gauge']]+=c['length_mm'];by_kind[c['kind']]+=1
        bends=len(c['xy'])-2
        if c['kind']=='bare':bare_bends+=bends
        else:jump_bends+=bends
        solder.update(c['contacts'])
        for xy in c['contacts']:joints[(c['net'],xy)].append(c['id'])
    maps={'J101':{'1':'4','2':'1','3':'3'},'D103':{'1':'2','2':'1'},'U207':{'1':'1','2':'2','3':'3','4':'4','5':'6'}}
    maps.update({f'J{300+10*i+3}':{'1':'1','2':'3'} for i in range(1,5)})
    pin_rows=[dict(ref=q.ref,pin_number_logical=q.number,pin_number_physical=maps.get(q.ref,{}).get(q.number,q.number),pin_name=q.name,net=q.net,hole=hole(q.xy),footprint=p.parts[q.part].data['footprint']) for q in p.pins.values()]
    for xy,name in p.reserved_pads.items():pin_rows.append(dict(ref=name.split('.')[0],pin_number_logical='none',pin_number_physical=name.rsplit(':',1)[-1],pin_name=name,net='RESERVED: no host wire',hole=hole(xy),footprint='see T5'))
    write_csv(HERE/'out/assembly_pin_map.csv',['ref','pin_number_logical','pin_number_physical','pin_name','net','hole','footprint'],pin_rows)
    write_csv(HERE/'out/junctions.csv',['net','hole','conductor_ids'],[dict(net=net,hole=hole(xy),conductor_ids=';'.join(ids)) for (net,xy),ids in sorted(joints.items()) if len(ids)>1])
    inputs={name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in ['board.json','footprints_ub.json','netlist_ub.csv','design_rules.json','parts_fit.csv']}
    captured=json.loads((HERE/'input_hashes.json').read_text())
    sources_unchanged=inputs==captured
    longest=[];vref=[];power=[]
    for ch in range(1,5):
        u=f'U{300+10*ch}'
        for side,pico_pin,drv_pin in [(1,[4,6,9,11][ch-1],3),(2,[5,7,10,12][ch-1],4)]:
            L=get_dist(p,f'HDD{ch}_IN{side}',f'U201.#{pico_pin}',f'{u}.#{drv_pin}')
            longest.append(dict(net=f'HDD{ch}_IN{side}',length_mm=L))
        vref.append(dict(channel=ch,length_mm=get_dist(p,'VREF','C211.#1',f'{u}.#7')))
        power.append(dict(channel=ch,vm_from_C106_mm=get_dist(p,'VM','C106.#1',f'{u}.#14'),
            gnd13_from_C106_mm=get_dist(p,'GND','C106.#2',f'{u}.#13'),
            gnd2_from_C106_mm=get_dist(p,'GND','C106.#2',f'{u}.#2')))
    lengths={k:round(v,3) for k,v in sorted(lengths.items())}
    known_soft=sum(i.get('t7_penalty',0) for i in r['issues'] if i['severity']=='warning' and i.get('status')!='UNCHECKED')
    unchecked_soft=sum(i.get('t7_penalty',0) for i in r['issues'] if i['severity']=='warning' and i.get('status')=='UNCHECKED')
    # Copper-only route estimates; component/contact drops and offboard harness excluded.
    entry_R=sum(get_dist(p,n,a,b,True) for n,a,b in [('VIN_RAW','J101.#1','F102.#1'),('VIN_FUSED','F102.#2','D103.#2'),('VIN_PROT','D103.#1','J104.#1')])
    positive=[];returns=[]
    for ch in range(1,5):
        u=f'U{300+10*ch}'
        # Treat entire routed path as carrying 2.6 A: conservative vs branch sharing.
        positive.append(2.6*(entry_R+get_dist(p,'VM','J104.#2',f'{u}.#14',True)))
        returns.append(2.6*get_dist(p,'GND','J101.#2',f'{u}.#13',True))
    bare=[c for c in p.conductors if c['kind']!='jumper']
    clear=(math.inf,None)
    for i,a in enumerate(bare):
        for b in bare[i+1:]:
            if a['net']==b['net']:continue
            d=min(segment_distance(x,y,z,w)*p.pitch for x,y in zip(a['xy'],a['xy'][1:]) for z,w in zip(b['xy'],b['xy'][1:]))-(diameter(a['gauge'])+diameter(b['gauge']))/2
            if d<clear[0]:clear=(d,[a['id'],b['id']])
    gx=p.board['grid_origin_mm']['x'];gy=p.board['grid_origin_mm']['y']
    rects=[q.rect for q in p.parts.values()]+[(x*p.pitch,y*p.pitch,x*p.pitch,y*p.pitch) for c in p.conductors for x,y in c['xy']]
    box=[min(q[0] for q in rects),min(q[1] for q in rects),max(q[2] for q in rects),max(q[3] for q in rects)]
    actual=[box[0]+gx,box[1]+gy,box[2]+gx,box[3]+gy]
    # Sample <=0.25mm steps, subtract 0.125mm as a Lipschitz error bound.
    out_nets={f'HDD{i}_OUT{j}' for i in range(1,5) for j in [1,2]}
    out_wires=[c for c in p.conductors if c['net'] in out_nets]
    out_pins=[q for q in p.pins.values() if q.net in out_nets]
    coils=[p.parts[f'J{300+10*i+3}'].rect for i in range(1,5)]
    exceptions=[p.pin_at(f'U{300+10*i}.#9') for i in range(1,5)]
    sep={}
    for label,nets,except_fault in [('S01',{'VREF','SLEEP','FAULT','SN_BUS','SN_RX_IN','SN_PU','UART_RX','ARM','ARM_SW'},True),('S02',{'VREF'},False)]:
        best=(math.inf,None)
        for c in p.conductors:
            if c['net'] not in nets:continue
            radius=.8 if c['kind']=='jumper' else diameter(c['gauge'])/2
            for a,b in zip(c['xy'],c['xy'][1:]):
                L=math.dist(a,b)*p.pitch;steps=max(1,math.ceil(L/.25))
                for k in range(steps+1):
                    q=(a[0]+(b[0]-a[0])*k/steps,a[1]+(b[1]-a[1])*k/steps)
                    if except_fault and c['net']=='FAULT' and any(math.dist(q,ep)*p.pitch<5.08-1e-9 for ep in exceptions):continue
                    d=min([point_rect((q[0]*p.pitch,q[1]*p.pitch),z)-radius for z in coils]+[
                        math.dist(q,z.xy)*p.pitch-radius-.9 for z in out_pins]+[
                        point_segment(q,x,y)*p.pitch-radius-diameter(w['gauge'])/2 for w in out_wires for x,y in zip(w['xy'],w['xy'][1:])])
                    if d<best[0]:best=(d,c['id'])
        sep[label]={'sampled_minimum_surface_mm':round(best[0],3),'conservative_sample_bound_mm':round(best[0]-.125,3),'wire':best[1],
            'assumptions':'quiet jumper OD <=1.6mm; output pad OD <=1.8mm; exact 5.08mm FAULT exception circle; assembly tolerances excluded','status':'supplementary estimate, not a replacement for UNCHECKED'}
    features=[]
    for ref,feat in [('J101','mating_face'),('U201','usb_mouth')]+[(f'J{300+10*i+3}','mating_face') for i in range(1,5)]+[('J202','mating_face'),('J203','mating_face')]:
        part=p.parts[ref];f=part.footprint['features'][feat];dx,dy=rotate((f['x_mm'],f['y_mm']),part.data['rotation']);ox,oy=point(part.data['hole'])
        xx,yy=ox*p.pitch+gx+dx,oy*p.pitch+gy+dy
        features.append({'ref':ref,'feature':feat,'actual_point_mm':[xx,yy],
            'closest_actual_board_edge_mm':min(xx,yy,p.board['width_mm']-xx,p.board['height_mm']-yy)})
    mount_body=math.inf;mount_wire=math.inf
    for m in p.board['mounting_holes_mm']:
        q=(m['x'],m['y'])
        for part in p.parts.values():
            z=part.rect;mount_body=min(mount_body,point_rect(q,(z[0]+gx,z[1]+gy,z[2]+gx,z[3]+gy)))
        for c in p.conductors:
            for a,b in zip(c['xy'],c['xy'][1:]):
                aa=(a[0]*p.pitch+gx,a[1]*p.pitch+gy);bb=(b[0]*p.pitch+gx,b[1]*p.pitch+gy)
                mount_wire=min(mount_wire,point_segment(q,aa,bb))
    probe_access=[]
    for ref,part in p.parts.items():
        if not ref.startswith('TP'):continue
        xy=part.pins[0].xy;qq=(xy[0]*p.pitch,xy[1]*p.pitch)
        d,other=min((point_rect(qq,z.rect),name) for name,z in p.parts.items() if name!=ref)
        probe_access.append({'ref':ref,'nearest_other_body':other,'tip_axis_to_body_mm':d})
    data={'official_hard_rules':dict(hard),'official_soft_rules':dict(soft),'t7_known_weighted_soft_penalty':known_soft,
        't7_unchecked_soft_bookkeeping_penalty':unchecked_soft,'tool_score':r['metrics']['score'],
        'score_note':'T6 scalar uses default severity weights, not T7 per-rule weights. Both are reported; UNCHECKED is not PASS.',
        'wire_count':dict(by_kind),'wire_length_by_gauge_mm':lengths,'bare_bends':bare_bends,'jumper_bends':jump_bends,
        'longest_IN':max(longest,key=lambda z:z['length_mm']),'IN_paths':longest,'vref_branches':vref,'power_paths':power,
        'bbox_top_grid_mm':box,'bbox_actual_board_mm':actual,'bbox_dimensions_mm':[box[2]-box[0],box[3]-box[1]],
        'physical_board_margin_mm':{'left':actual[0],'top':actual[1],'right':p.board['width_mm']-actual[2],'bottom':p.board['height_mm']-actual[3]},
        'physical_component_pins_including_reserved':len(p.pins)+len(p.reserved_pads),'solder_sites_conservative_all_bare_pads':len(solder),
        'terminal_attachments_component_pins_plus_wire_ends':len(p.pins)+len(p.reserved_pads)+2*len(p.conductors),
        'copper_wire_surface_clearance_mm':round(clear[0],3),'closest_bare_pair':clear[1],
        'copper_only_20C_drop_V':{'positive_at_2p6A_max':max(positive),'return_at_2p6A_max':max(returns),'scope':'entire one-way route treated at full current; no contact, component or harness drops'},
        'signal_output_separation_estimates':sep,'actual_feature_insets':features,'probe_tip_planar_body_clearances':probe_access,
        'mount_min_body_centre_distance_mm':mount_body,'mount_min_wire_centre_distance_mm':mount_wire,
        'manual_access_notes':'Real-outline feature insets exceed literal M07/M08/M09 numerical limits. Driver east coil-body gap is 1.089mm, below 5.08mm W/E grip strip; N/S grip is proposed, not approved. Mount centres are 5.0mm from real edge vs M02 5.08mm.',
        'approved_inputs_hashes_unchanged':sources_unchanged}
    save_json(HERE/'out/extended_metrics.json',data)
    print(json.dumps(data,indent=2,ensure_ascii=False))
