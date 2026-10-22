"""Geometry-only portrait-board proposal, not an approved candidate override."""
import sys,copy,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
import r2_geometry as g
from model import save_json,Project,hole
HERE=g.HERE;BASE=g.BASE
if __name__=='__main__':
    r=json.loads((HERE/'out/r2_column_feasibility.json').read_text())
    cert=[]
    for a in r['rotation_stats']:
        candidates=[(int(x),max(ys)-min(ys),min(ys),max(ys)) for x,ys in a['origin_rows_by_column'].items() if ys]
        maximum=max(x[1] for x in candidates)
        cert.append({'rotation':a['rotation'],'max_feasible_origin_row_span_any_common_column':maximum,
            'minimum_four_carrier_origin_span':3*a['minimum_origin_pitch_holes'],
            'arithmetic_infeasible':maximum<3*a['minimum_origin_pitch_holes'],
            'columns_attaining_maximum':[x for x in candidates if x[1]==maximum]})
    assert all(x['arithmetic_infeasible'] for x in cert)
    save_json(HERE/'out/r2_infeasibility_certificate.json',{'scope':'exact common-x single column, all four carrier rotations; isolated 4-part channel tiles only; all other parts and routes removed',
        'rules_used':['M01','M08','M11','H01','H06','P05','P08','P11','board outline / pin / corner keepout rules'],
        'local_relative_patterns':234,'certificate':cert,
        'inputs_sha256':{s:hashlib.sha256((BASE/s).read_bytes()).hexdigest() for s in ['board.json','footprints_ub.json','design_rules_v0.2.json']}})
    # Only a changed view/orientation is proposed: same physical 104708 turned
    # 90 degrees, making its 55-hole edge vertical. This is outside the strict
    # short-east-edge F3 seed; never used by actual-candidate CLI verification.
    b=copy.deepcopy(g.P.board);b.update(columns=40,rows=55,width_mm=114.,height_mm=155.,
        outline_mm={'width':114.,'height':155.},grid_origin_mm={'x':7.47,'y':8.92})
    b['keepouts']=[{'id':n,'from':hole(a),'to':hole(z)} for n,a,z in [
        ('M3_NW_hardware',(0,0),(1,1)),('M3_NE_hardware',(38,0),(39,1)),
        ('M3_SW_hardware',(0,53),(1,54)),('M3_SE_hardware',(38,53),(39,54))]]
    b['mounting_holes_mm']=[{'id':n,'x':x,'y':y,'diameter':3.2} for n,x,y in [('M_NW',5,5),('M_NE',109,5),('M_SW',5,150),('M_SE',109,150)]]
    b['notes']='UNAPPROVED GEOMETRY PROPOSAL ONLY: same physical board turned portrait; not used for final-candidate verification.'
    g.P=Project(HERE,board=b)
    pats=[[g.shape(a['role'],a['x'],a['y'],a['r']) for a in t] for t in json.loads((HERE/'r2_local_patterns.json').read_text())]
    proposal=g.search(pats)
    (HERE/'proposals').mkdir(exist_ok=True)
    save_json(HERE/'proposals/portrait_geometry_only.json',proposal)
    print('PORTRAIT proposal only',json.dumps(proposal.get('solution')),flush=True)
