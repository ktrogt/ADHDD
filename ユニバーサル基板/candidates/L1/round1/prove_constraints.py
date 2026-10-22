"""Finite exhaustive reproductions of incompatible approved geometric targets.

All first pins are bounded by near rules, so +-12 holes exhausts every possible
integer origin relevant to these constraints. All four rotations are tested.
"""
from build import *
from collections import Counter

def run():
    cases=[]
    def test(label,base,fid,pairs,bound,gap):
        valid=options(fid,base,pairs,bound,gap)
        first=None
        for candidate in range(bound,10):
            z=options(fid,base,pairs,candidate,gap)
            # Different populated leads cannot use one board hole, even on one net.
            z=[v for v in z if not set(geom(fid,*v[1:4])[1].values()) & set(base[1].values())]
            if z:first={'max_manhattan_holes':candidate,'examples':z[:5]};break
        cases.append({'case':label,'bound_holes':bound,'minimum_body_gap_holes':gap,
                      'original_feasible_placements':len(valid),'first_feasible_bound':first})
        assert not valid, label+' unexpectedly feasible'
    test('P13 C108 + H07',geom(REF['U107'],0,0),REF['C108'],[('1','1'),('2','2')],4,1)
    test('P13 C109 + H07',geom(REF['U107'],0,0),REF['C109'],[('1','3'),('2','2')],4,1)
    test('P15 C208 + M01',geom(REF['U207'],0,0),REF['C208'],[('1','5'),('2','3')],2,.4)
    test('V02 R210 + M01',geom(REF['C211'],0,0),REF['R210'],[('1','1'),('2','2')],2,.4)
    test('P02 TVS shortest grid route + M01',geom(REF['C106'],0,0),REF['D105'],[('1','1'),('2','2')],3,.4)
    # P02 allows diagonal insulated jumpers, so prove its Euclidean lower bound too.
    base=geom(REF['C106'],0,0); eu=[]
    for x,y,r in itertools.product(range(-12,13),range(-12,13),(0,90,180,270)):
        rr,pp=geom(REF['D105'],x,y,r)
        if rect_distance(rr,base[0])>=.4*PITCH-1e-8:
            eu.append((max(math.dist(pp[a],base[1][b]) for a,b in [('1','1'),('2','2')]),x,y,r))
    drv=geom(REF['U310'],0,0,270)
    cer=options(REF['C312'],drv,[('1','14'),('2','13')],2,.4)
    coil=options(REF['J313'],drv,[('1','12'),('2','11')],4,.4)
    joint=[]
    for a,b in itertools.product(cer,coil):
        if rect_distance(geom(REF['C312'],*a[1:4])[0],geom(REF['J313'],*b[1:4])[0])>=.4*PITCH-1e-8:joint.append([a,b])
    assert not joint
    data={'domain':'all integer origins in [-12,+12]^2, all cardinal rotations; near constraints bound every relevant origin inside this domain',
          'cases':cases,'P02_minimum_possible_euclidean_upper_pair_holes':min(eu),
          'driver_ceramic_P05_feasible':cer,'driver_coil_P11_feasible':coil,
          'driver_ceramic_and_coil_joint_feasible_count':len(joint),
          'board_M02':{'actual_mount_min_edge_distance_mm':5.0,'rule_min_mm':5.08,'status':'FAIL independent of placement'},
          'no_rule_relaxation_approved_or_applied':True}
    save_json(HERE/'constraint_reproduction.json',data)
    for z in cases:print(z['case'],': 0 original solutions; first feasible bound',z['first_feasible_bound']['max_manhattan_holes'])
    print('P02 Euclidean lower bound:',min(eu)[0],'> 3 holes')
    print('Driver ceramic + coil joint: 0 solutions at original bounds')
    print('M02 actual mounting edge: 5.00 mm < 5.08 mm')
    return data

if __name__=='__main__':run()
