"""Cross-check the proof's individual-part geometry against shared T6."""
import sys,random
sys.dont_write_bytecode=True
import r2_geometry as g
from model import hole,save_json
from verify import placement_drc
rng=random.Random(20261022);checked=0
for role in ['U','B','C','J']:
    ref=g.ROLE[role]
    for _ in range(100):
        x=rng.randrange(55);y=rng.randrange(40);r=rng.choice([0,90,180,270])
        shape=g.shape(role,x,y,r)
        pl={'schema_version':1,'parts':{ref:{'footprint':g.REF[ref],'hole':hole((x,y)),'rotation':r}}}
        p=g.P.clone(placement=pl,wiring={'schema_version':1,'conductors':[]})
        assert all(abs(a-b)<1e-8 for a,b in zip(shape['rect'],p.parts[ref].rect))
        assert set(shape['pads'])=={q.xy for q in p.pins.values()}|set(p.reserved_pads)
        actual=not any(i['severity']=='error' for i in placement_drc(p))
        assert actual==g.part_ok(shape),(role,x,y,r,actual)
        checked+=1
save_json(g.HERE/'out/r2_geometry_crosscheck.json',{'cases':checked,'result':'PASS','scope':'Proof rectangles, pad sets, body outline, pin/mount keepout admissibility agree with shared T6; packing certificate remains separate.'})
print('Geometry cross-check PASS',checked)
