"""Supplemental candidate QA. Does not change the shared rule status."""
from route_local import *
from model import segment_distance
from collections import Counter,defaultdict
import math,re,xml.etree.ElementTree as ET
from PIL import ImageFont

def radius(c):return float(re.fullmatch(r'([0-9.]+)mm',c['gauge'])[1])/2
def pd(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def rect_pd(pt,r):
    return math.hypot(max(r[0]-pt[0],pt[0]-r[2],0),max(r[1]-pt[1],pt[1]-r[3],0))
def check_quiet(p,rid):
    rule=next(r['params'] for r in p.rules['rules'] if r['id']==rid)
    outs=[c for c in p.conductors if c['net'] in rule['b_nets']]
    rects=[p.parts[n].rect for n in rule['b_parts']]
    exceptions=[(Router(p).resolve(e['pin']),e['radius_holes']) for e in rule['terminal_exceptions']]
    minimum=float('inf');where=None
    for c in p.conductors:
        if c['net'] not in rule['a_nets']:continue
        for a,b in zip(c['xy'],c['xy'][1:]):
            n=max(1,math.ceil(distance(a,b)/.05))
            for k in range(n+1):
                q=(a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n)
                if any(distance(q,e)<=r+1e-8 for e,r in exceptions):continue
                gap=min([pd(q,x,y)*p.pitch-radius(c)-radius(o) for o in outs for x,y in zip(o['xy'],o['xy'][1:])]+[rect_pd((q[0]*p.pitch,q[1]*p.pitch),r)-radius(c) for r in rects])
                if gap<minimum:minimum=gap;where=dict(wire=c['id'],net=c['net'],grid_xy=q)
    # Distance is 1-Lipschitz; subtract a full sample interval, also covering the
    # first unsampled point immediately outside a terminal exception disk.
    return dict(sample_interval_mm=.127,sampled_min_surface_mm=round(minimum,3),conservative_bound_mm=round(minimum-.127,3),required_mm=rule['min_holes']*p.pitch,planar_wire_and_body_pass=minimum-.127>=rule['min_holes']*p.pitch,worst=where,excludes='actual solder, exposed formed leads, z-height, insulation OD and assembly tolerances')

def main():
    p=Project(HERE);m=json.loads((HERE/'out/metrics.json').read_text('utf8'));helper=Router(p)
    gauges=defaultdict(lambda:defaultdict(float))
    for c in p.conductors:gauges[c['gauge']][c['kind']]+=c['length_mm']
    joints={q.xy for q in p.pins.values()};contact=Counter(q for c in p.conductors if c['kind']=='bare' for q in set(c['contacts']))
    for c in p.conductors:
        joints.update([c['xy'][0],c['xy'][-1]])
        if c['kind']=='bare':joints.update(c['xy']);joints.update(c['contacts'][::6])
    joints.update(q for q,n in contact.items() if n>1)
    rows=[dict(hole=hole(q),component_pin=any(s.xy==q for s in p.pins.values()),note='joint/end/bend or support at <=6-hole intervals') for q in sorted(joints,key=lambda q:(q[1],q[0]))]
    rows.extend(dict(hole=hole(q),component_pin=True,note='Physical reserved pin only; NO host wire: '+label) for q,label in sorted(p.reserved_pads.items()))
    with (HERE/'out/solder_plan.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['hole','component_pin','note']);writer.writeheader();writer.writerows(rows)
    label_audit={}
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',1950)
    for view in ['top','bottom','overlay']:
        root=ET.parse(HERE/'out'/f'{view}.svg').getroot();labels=[]
        for e in root.iter():
            if e.tag.endswith('}text') and e.text in p.parts and e.get('font-weight')=='bold':
                x,y=float(e.get('x')),float(e.get('y'));width=font.getlength(e.text)/1000
                labels.append((e.text,(x-width/2-.3,y-1.95-.3,x+width/2+.3,y+.3)))
        overlap=[(a[0],b[0]) for i,a in enumerate(labels) for b in labels[i+1:] if a[1][0]<b[1][2] and b[1][0]<a[1][2] and a[1][1]<b[1][3] and b[1][1]<a[1][3]]
        label_audit[view]=dict(labels=len(labels),unique_refs=len(set(a[0] for a in labels)),overlap_pairs=overlap,svg_parse=True)
    bare=[c for c in p.conductors if c['kind']=='bare']
    bare_gap=min(segment_distance(a,b,c,d)*p.pitch-radius(x)-radius(y) for i,x in enumerate(bare) for y in bare[i+1:] if x['net']!=y['net'] for a,b in zip(x['xy'],x['xy'][1:]) for c,d in zip(y['xy'],y['xy'][1:]))
    pairs={}
    for rid in ['V04','S04','P02','P03','P06','P09','P12','P14','P16']:
        rule=next(r for r in p.rules['rules'] if r['id']==rid);rr=[]
        for pair in rule['params']['pairs']:
            a,b=helper.resolve(pair['a']),helper.resolve(pair['b']);net=next(q.net for q in p.pins.values() if q.xy==a)
            rr.append(dict(**pair,length_mm=round(shortest(net_graph(p,net),a)[b],3)))
        pairs[rid]=rr
    extra=dict(schema_version=1,wire_length_by_diameter_and_kind_mm={g:{k:round(v,3) for k,v in kinds.items()} for g,kinds in gauges.items()},bare_wire_pieces=len(bare),bare_straight_segments=sum(len(c['xy'])-1 for c in bare),bare_bends=sum(len(c['xy'])-2 for c in bare),estimated_distinct_solder_pads=len(joints)+len(p.reserved_pads),component_solder_pads=len(p.pins)+len(p.reserved_pads),conservative_every_contact_solder_pads=len({q.xy for q in p.pins.values()}|{q for c in p.conductors for q in c['contacts']})+len(p.reserved_pads),solder_estimate_method='component pins, NC physical pins, conductor ends, wire junctions, bends and support every six grid steps',minimum_bare_wire_surface_gap_mm=round(bare_gap,3),minimum_bare_gap_excludes_pads_leads_and_solder=True,quiet_checks={rid:check_quiet(p,rid) for rid in ['S01','S02']},svg_label_audit=label_audit,branch_lengths=pairs,bbox_physical_mm=[round(m['bbox_mm'][i]+[8.92,7.47,8.92,7.47][i],3) for i in range(4)],physical_board_area_fraction=round(m['used_bbox_area_mm2']/(155*114),5),tool_rule_status_unchanged=True)
    save_json(HERE/'out/extra_metrics.json',extra)
    print(json.dumps({k:v for k,v in extra.items() if k!='branch_lengths'},indent=2))
if __name__=='__main__':main()
