"""L4/F4 generator and local experiments. Shared inputs are read-only."""
import sys, json, csv, copy, shutil, itertools, random, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE / 'tools'))
from model import Project, load_json, load_footprints, save_json, hole, point, rect_distance
from verify import placement_drc, verify, summary
from rules import evaluate

def initialize():
    for src, dst in [('board.json','board.json'), ('footprints_ub.json','footprints_ub.json'), ('netlist_ub.csv','netlist.csv'), ('design_rules_v0.2.json','design_rules.json')]:
        shutil.copyfile(BASE/src, HERE/dst)

def seed():
    f = load_footprints(BASE/'footprints_ub.json')
    placement = dict(schema_version=1, candidate='L4', floor_plan='F4', parts={})
    def put(ref, x, y, rotation=0):
        placement['parts'][ref] = dict(footprint=f['ref_to_type'][ref], hole=hole((x,y)), rotation=rotation, substitution_approved=True)
    # Power/output sides north; logic pins south. All channels identical.
    for ch,x in zip([4,3,2,1],[5,19,33,47]):
        d=300+ch*10
        put(f'U{d}',x,9,270)
        put(f'C{d+1}',x-4,3,90)
        put(f'C{d+2}',x-1,2)
        put(f'J{d+3}',x+2,1)
        put(f'TP{470+ch}',x+6,2)
    # GPIO side faces north, USB points east.
    put('U201',53,19,90)
    # Entry at west; heat-producing series diode in the southwest.
    put('J101',5,22,90)
    put('C106',2,18)
    put('J104',0,17,270)
    put('D105',1,14)
    put('F102',3,34)
    put('D103',14,36)
    # Regulator and local decoupling.
    put('U107',23,30)
    put('C108',23,24)
    put('C109',25,36,180)
    put('D110',52,28,180)
    # SmartNet at east, below Pico USB.
    put('J202',53,12,270)
    put('J203',53,16,270)
    put('U207',46,13)
    put('C208',49,17,180)
    put('R204',50,11,180)
    put('R205',43,11)
    put('D206',42,13)
    # Central VREF source.
    put('C211',27,14,90)
    put('R209',25,12,90)
    put('R210',29,14,90)
    # Control/stop on the lower edge near GP14-16.
    put('J213',34,39)
    put('R214',35,36,180)
    put('R212',33,32,90)
    put('R215',31,22,270)
    # Accessible probes, no spare scaffold.
    for ref,x,y in [('TP460',0,12),('TP461',29,35),('TP462',43,28),('TP463',5,12),('TP464',20,35),('TP465',37,17),('TP466',29,12),('TP467',37,36),('TP468',32,18)]: put(ref,x,y)
    p=Project(HERE, placement=placement, wiring={'schema_version':1,'conductors':[]})
    placement['nodes']={k:hole(p.pin_at(v['anchor'].replace('.', '.#'))) for k,v in p.rules['nodes'].items()}
    save_json(HERE/'placement.json', placement)
    save_json(HERE/'wiring.json', {'schema_version':1,'conductors':[]})

def placement_findings(p):
    return [i for i in placement_drc(p)+evaluate(p,placement_only=True) if i['severity']=='error' and i.get('status')!='UNCHECKED']

def inspect():
    p=Project(HERE)
    for i in placement_findings(p): print(i['code'],i['detail'])
    print('PLACEMENT errors',len(placement_findings(p)))

if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'inspect'
    if cmd=='seed':
        initialize(); seed()
    inspect()
