"""Strengthen F3 certificate: all coil mating faces on E; allow x staggering."""
import sys,json,math,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
import r2_geometry as g
from model import rotate,save_json
H=g.HERE
r=json.loads((H/'out/r2_column_feasibility.json').read_text())
pats=[[g.shape(a['role'],a['x'],a['y'],a['r']) for a in t] for t in json.loads((H/'r2_local_patterns.json').read_text())]
result=[]
for stat in r['rotation_stats']:
    rotation=stat['rotation'];by={};total=0
    for xx,ys in stat['origin_rows_by_column'].items():
        x=int(xx);allowed=set()
        for y in ys:
            for pat in pats:
                tile=g.translated(pat,x,y,rotation);j=tile[3]
                feature=g.F['footprints'][g.REF[g.ROLE['J']]]['features']['mating_face']
                dx,dy=rotate((feature['x_mm'],feature['y_mm']),j['r'])
                d=g.P.edge_distance((j['x']*2.54+dx,j['y']*2.54+dy),['E'],'grid_boundary')/2.54
                if d>2+1e-8:continue
                if g.all_ok(tile):allowed.add(y);total+=1
        if allowed:by[x]=sorted(allowed)
    if by:
        xmin,xmax=min(by),max(by);ymin=min(min(z) for z in by.values());ymax=max(max(z) for z in by.values())
        width=15.84 if rotation in [0,180] else 18.38
        all_x_overlap=(xmax-xmin)*2.54<width-1e-8
        needed=3*stat['minimum_origin_pitch_holes']
        data={'rotation':rotation,'origin_columns':[xmin,xmax],'origin_rows':[ymin,ymax],
            'origin_rows_by_column':by,'feasible_origin_row_span':ymax-ymin,'required_four_origin_row_span':needed,
            'all_carrier_x_envelopes_overlap_even_with_stagger':all_x_overlap,
            'infeasible':all_x_overlap and ymax-ymin<needed,'valid_tile_count':total}
    else:data={'rotation':rotation,'valid_tile_count':0,'infeasible':True,'reason':'No locally feasible four-part tile has its coil mating point within 2 holes of E.'}
    result.append(data);print(data,flush=True)
assert all(z['infeasible'] for z in result)
save_json(H/'out/r2_east_edge_certificate.json',{'scope':'F3 four channels with all coil mating faces at east edge; same carrier rotation; arbitrary carrier x stagger is allowed within all enumerated feasible placements',
    'certificate':result,'infeasible':True,'inputs_sha256':{s:hashlib.sha256((g.BASE/s).read_bytes()).hexdigest() for s in ['board.json','footprints_ub.json','design_rules_v0.2.json']},
    'relaxations_in_proof':'Pico, entry, regulator, all other control parts, probe pins, wire routing, grip and signal/output separations omitted; omitting these only makes packing easier'})
