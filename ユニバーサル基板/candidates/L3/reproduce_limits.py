"""Finite exhaustive counterexamples using the unchanged approved footprints.

All relative placements that could meet the tested small distance bounds lie
inside the enumerated +/-13-hole box. Whole-board restrictions are relaxed in
these pair tests; failure even here is therefore a necessary-condition proof.
"""
import sys,math,json
from pathlib import Path
sys.dont_write_bytecode=True
import build
from build import F,REF,rect,pin,man,rect_distance,HERE,BASE
from model import Project,save_json,point
from verify import placement_drc

def phys_pads(ref,x,y,r):
    from model import rotate
    fp=F['footprints'][REF[ref]]
    ps={pin(ref,p['number'],x,y,r) for p in fp['pins']}
    for q in fp.get('extra_pads',[]):
        dx,dy=rotate((q['dx'],q['dy']),r);ps.add((x+dx,y+dy))
    return ps

def channel_pair():
    x=y=20;u=rect('U310',x,y,0);up=phys_pads('U310',x,y,0)
    bypass=[];coils=[]
    for r in [0,90,180,270]:
        for xx in range(7,34):
            for yy in range(7,34):
                q=(xx,yy,r)
                for ref,arr,limit,pairs in [('C312',bypass,2,[(1,14),(2,13)]),('J313',coils,8,[(1,12),(2,11)])]:
                    ds=[man(pin(ref,a,*q),pin('U310',b,x,y,0)) for a,b in pairs]
                    if max(ds)>limit or rect_distance(u,rect(ref,*q))<1.016-1e-8:continue
                    if phys_pads(ref,*q)&up:continue
                    arr.append((q,ds,rect(ref,*q),phys_pads(ref,*q)))
    compatible=[]
    for b in bypass:
        for c in coils:
            if rect_distance(b[2],c[2])<1.016-1e-8 or b[3]&c[3]:continue
            compatible.append((max(c[1]),sum(c[1]),b[0],c[0],c[1]))
    compatible.sort()
    return {'bypass_max_holes':2,'coil_required_max_holes':4,'bypass_options':len(bypass),
        'compatible_coil_minimum_max_holes':compatible[0][0],
        'solutions_with_both_original_bounds':sum(c[0]<=4 for c in compatible),
        'best_examples':compatible[:8]}

if __name__=='__main__':
    build.infeasibility()
    proof=json.loads((HERE/'infeasibility.json').read_text(encoding='utf-8'))
    proof['P05 and P11 joint constraint']=channel_pair()
    p=Project(HERE)
    board=p.board;gx=board['grid_origin_mm']['x'];gy=board['grid_origin_mm']['y']
    modules={}
    for ref in ['U340','U310']:
        a,b,c,d=p.parts[ref].rect
        actual=(a+gx,b+gy,c+gx,d+gy)
        modules[ref]={'tool_rect_mm':p.parts[ref].rect,'actual_board_rect_mm':actual,
            'minimum_actual_edge_margin_mm':min(actual[0],actual[1],board['width_mm']-actual[2],board['height_mm']-actual[3])}
    proof['T6 boundary reproduction']={'official_findings':[i for i in placement_drc(p) if i['code']=='BODY_OFFBOARD'],
        'source':'tools/verify.py placement_drc computes +/-half-pitch board boundary and ignores width_mm,height_mm,grid_origin_mm',
        'tool_height_mm':p.rows*p.pitch,'approved_actual_height_mm':board['height_mm'],'modules':modules,
        'workaround':'route_candidate.gate excludes only these two findings during routing; official verify remains unchanged and fails closed'}
    proof['M02 board intrinsic conflict']={'required_min_mount_centre_edge_mm':5.08,'approved_board_actual_mm':5.0,
        'difference_mm':0.08,'status':'requires supervisor interpretation; not silently waived'}
    save_json(HERE/'infeasibility.json',proof)
    print('CHANNEL JOINT',proof['P05 and P11 joint constraint'])
    print('BODY BOUNDARY',modules)
