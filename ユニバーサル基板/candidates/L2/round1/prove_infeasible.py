"""Small exhaustive, translation-independent certificates for frozen hard rules.
Uses the exact approved footprint rectangles, integer grid and 90-degree rotations.
No shared input is changed. No relaxation is adopted by this script.
"""
import sys,json,itertools,math
from pathlib import Path
sys.dont_write_bytecode=True
import build as b
from model import save_json,rect_distance
H=Path(__file__).resolve().parent
def valid(fp,pairs,rects,gap):
    cs=b.choices(fp,pairs,rects,gap,n=15)
    # All populated and extra pads must also remain physically distinct.
    return cs
def main():
    results=[]
    # C100n at VIN/GND plus local coil connector; rotations of the entire tile
    # preserve integer grid, Manhattan bounds and Euclidean rectangle distances.
    dp,db=b.geom('POLOLU4035_SOCKET_5H',(0,0),0)
    caps=valid('C100NF_1H',[('1',dp['14'],2),('2',dp['13'],2)],[db],1.016)
    joins=valid('COIL_XH3_OUTER',[('1',dp['12'],4),('2',dp['11'],4)],[db],1.016)
    combos=[(c,j) for c in caps for j in joins if rect_distance(c[2],j[2])>=1.016-1e-8 and not(set(c[1].values())&set(j[1].values()))]
    assert len(caps)==1 and len(joins)==3 and not combos
    j5=valid('COIL_XH3_OUTER',[('1',dp['12'],5),('2',dp['11'],5)],[db],1.016)
    count5=sum(rect_distance(c[2],j[2])>=1.016-1e-8 for c in caps for j in j5)
    results.append(dict(rules=['M01','P05','P11'],status='UNSAT',cap_placements=[c[0] for c in caps],connector_placements=[c[0] for c in joins],valid_combinations=len(combos),combinations_if_P11_5=count5,minimal_max_output_distance_holes=5,explanation='All four global tile rotations are equivalent under lattice rotation. P12 cannot be shorter than P11 Manhattan distance.'))
    # TVS / entry can: cap can have any orientation.
    tvs=[]
    for cr in (0,90,180,270):
        cp,cb=b.geom('CP470_D10_2H',(0,0),cr)
        counts={lim:len(valid('D_DO41_4H_D105',[('1',cp['1'],lim),('2',cp['2'],lim)],[cb],1.016)) for lim in (3,4,5)}
        assert counts[3]==counts[4]==0 and counts[5]>0
        tvs.append(dict(cap_rotation=cr,counts=counts))
    results.append(dict(rules=['M01','P02'],status='UNSAT',orientations=tvs,minimal_max_pin_distance_holes=5,explanation='A routed branch cannot be shorter than the Manhattan distance of its endpoints.'))
    up,ub=b.geom('M78AR05_SIP3',(0,0),0)
    reg={}
    for label,target in [('C108','1'),('C109','3')]:
        counts={lim:len(valid('CP100_D63_1H',[('1',up[target],lim),('2',up['2'],lim)],[ub],2.54)) for lim in (4,5,6)}
        assert counts[4]==counts[5]==0 and counts[6]>0
        reg[label]=counts
    results.append(dict(rules=['H07','P13','P14'],status='UNSAT',counts=reg,minimal_max_pin_distance_holes=6,explanation='U107 approved rectangle is a conservative union, 18.42 x 16.1mm; its metadata separately states actual body 11.5 x 7.55mm and unverified offset. Refining that approved footprint requires supervisor action.'))
    up,ub=b.geom('AHC125_DIP6_DIRECT',(0,0),0)
    counts={lim:len(valid('C100NF_1H',[('1',up['5'],lim),('2',up['3'],lim)],[ub],1.016)) for lim in (2,3,4)}
    assert counts[2]==counts[3]==0 and counts[4]>0
    results.append(dict(rules=['M01','P15','P16'],status='UNSAT',counts=counts,minimal_max_pin_distance_holes=4))
    cp,cb=b.geom('C220NF_2H',(0,0),0)
    counts={lim:len(valid('R_MFS25_3H',[('1',cp['1'],lim),('2',cp['2'],lim)],[cb],1.016)) for lim in (2,3)}
    assert counts[2]==0 and counts[3]>0
    results.append(dict(rules=['M01','V02','V03'],status='UNSAT',counts=counts,minimal_max_pin_distance_holes=3,explanation='Counts at relaxed distance include positions that may need additional pin-collision filtering. UNSAT at bound 2 is already proved even without that extra restriction; final L2 uses a collision-free distance-3 witness.'))
    board=json.loads((b.ROOT/'board.json').read_text(encoding='utf-8'))
    edge=min(board['edge_offsets_mm'].values())
    results.append(dict(rules=['M08'],status='UNSAT_WITH_PHYSICAL_BOARD_FEATURES',min_possible_feature_edge_mm=edge,required_max_mm=5.08,explanation='Approved vertical XH mating-face centres lie inside the convex hull of their used pins. All pins lie on the 55x40 grid, whose closest physical edge offset is 7.47mm. Thus the <=5.08mm physical-edge condition cannot hold even before body/keepout restrictions.'))
    results.append(dict(rules=['M02'],status='UNSAT_WITH_PHYSICAL_BOARD_GEOMETRY',actual_mount_edge_mm=5.0,required_min_mm=5.08,explanation='All four approved M3 centres are nominally 5mm from the true board edges. The policy minimum is 5.08mm.'))
    save_json(H/'out/infeasibility.json',dict(model='Exact frozen JSON rectangles; no component overlap/stacking; integer grid; all 90-degree rotations',search_origin_range=[-15,15],completeness='Every searched part has pin1 at its origin; the pin1 Manhattan constraints place every possible solution strictly inside the enumerated range. Global 90-degree rotations preserve all involved metrics.',certificates=results))
    print('\n'.join('/'.join(r['rules'])+': '+r['status'] for r in results))
if __name__=='__main__':main()
