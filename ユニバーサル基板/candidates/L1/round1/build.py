"""L1 local construction/search helper. Shared inputs/tools are read-only."""
from pathlib import Path
import sys, json, math, shutil, itertools, copy, csv
HERE=Path(__file__).resolve().parent
SHARED=HERE.parent.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(SHARED/'tools'))
from model import Project, load_footprints, hole, point, rotate, rect_distance, save_json
FP=load_footprints(SHARED/'footprints_ub.json')['footprints']
REF=json.loads((SHARED/'footprints_ub.json').read_text(encoding='utf8'))['ref_to_type']
PITCH=2.54

def geom(fid,x,y,rot=0):
    f=FP[fid]; r=f['body_mm']
    corners=[rotate((a,b),rot) for a in (r['x'],r['x']+r['width']) for b in (r['y'],r['y']+r['height'])]
    rect=(x*PITCH+min(a for a,b in corners), y*PITCH+min(b for a,b in corners), x*PITCH+max(a for a,b in corners), y*PITCH+max(b for a,b in corners))
    pins={p['number']:(x+rotate((p['dx'],p['dy']),rot)[0],y+rotate((p['dx'],p['dy']),rot)[1]) for p in f['pins']}
    return rect,pins
def man(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])

def seed():
    for src,dst in [('board.json','board.json'),('footprints_ub.json','footprints_ub.json'),('netlist_ub.csv','netlist.csv'),('design_rules.json','design_rules.json')]:
        shutil.copyfile(SHARED/src,HERE/dst)
    parts={}
    def put(ref,x,y,r=0):
        parts[ref]={'footprint':REF[ref],'hole':hole((x,y)),'rotation':r,'locked':True,'substitution_approved':True}
    for ch,x in zip([1,2,3,4],[5,19,33,47]):
        b=300+ch*10
        put(f'U{b}',x,10,270)
        put(f'C{b+1}',x-4,4,90)
        put(f'C{b+2}',x-1,3)
        put(f'J{b+3}',x+2,2)
        put(f'TP{470+ch}',x+6,3)
    for ref,x,y,r in [
        ('J101',5,20,90),('F102',9,23,90),('D103',12,15,0),('J104',0,13,0),
        ('D105',1,12,0),('C106',2,16,0),('U107',16,29,90),
        ('C108',15,24,0),('C109',15,36,0),('D110',22,37,180),
        ('U201',32,38,180),('J202',43,38,0),('J203',48,38,0),
        ('R204',43,35,270),('R205',42,30,270),('D206',42,25,0),
        ('U207',46,30,0),('C208',47,28,180),('R209',24,15,0),
        ('R210',27,17,0),('C211',28,15,0),('R212',39,19,0),
        ('J213',53,18,90),('R214',48,19,90),('R215',36,18,180),
        ('TP460',0,16,0),('TP461',21,34,0),('TP462',23,33,0),
        ('TP463',8,20,0),('TP464',22,31,0),('TP465',32,16,0),
        ('TP466',25,17,0),('TP467',46,17,0),('TP468',36,20,0),
    ]: put(ref,x,y,r)
    placement={'schema_version':1,'candidate':'L1','seed':'F1','parts':parts,
        'nodes':{'GND_ENTRY':'E17','VM_ENTRY':'C17','GND_LOGIC':'Q31','VREF_ROOT':'AC16','VREF_GND':'AE16'},
        'notes':'L1 evaluation candidate. Shared full T7 rules unchanged; known incompatible hard distances remain FAIL, not silently relaxed.'}
    save_json(HERE/'placement.json',placement)
    save_json(HERE/'wiring.json',{'schema_version':1,'conductors':[]})
    checkplace()

def checkplace():
    from verify import placement_drc
    from rules import evaluate
    p=Project(HERE)
    print('PARTS',len(p.parts),'PINS',len(p.pins))
    issues=placement_drc(p)+evaluate(p,placement_only=True)
    for i in issues:
        if i['severity']=='error' and i.get('status')!='UNCHECKED': print(i['code'],i['detail'])
    save_json(HERE/'placement_audit.json',issues)

def values():
    placement=json.loads((HERE/'placement.json').read_text(encoding='utf8'))
    with (SHARED.parent/'基板'/'parts.csv').open(encoding='utf-8-sig',newline='') as f:
        vals={r['ref']:r['value'] for r in csv.DictReader(f)}
    vals.update({'J101':'DC jack DIP kit','D103':'MBR3045FCT (one anode)','U207':'74AHC1G125 / DIP6'})
    for ch in range(1,5):vals[f'J{313+(ch-1)*10}']=f'XH3 HDD{ch}; middle NC'
    with (HERE/'netlist.csv').open(encoding='utf-8-sig',newline='') as f:
        for z in csv.DictReader(f):
            if z['ref'].startswith('TP'):vals[z['ref']]=z['net']+' probe'
    for ref,z in placement['parts'].items():z['value']=vals.get(ref,ref)
    save_json(HERE/'placement.json',placement)
def options(fid,base,pairs,bound,gap,extent=12):
    br,bp=base; out=[]
    for x,y,r in itertools.product(range(-extent,extent+1),range(-extent,extent+1),(0,90,180,270)):
        rr,pp=geom(fid,x,y,r)
        d=[man(pp[a],bp[b]) for a,b in pairs]
        if max(d)<=bound and rect_distance(br,rr)>=gap*PITCH-1e-6:
            out.append((sum(d),x,y,r,rect_distance(br,rr)/PITCH,d))
    return sorted(out)

def feasibility():
    drv=geom(REF['U310'],0,0,270)
    opts={}
    for ref,prs,bnd,gap in [('C312',[('1','14'),('2','13')],2,.4),('C311',[('1','14'),('2','13')],6,1),('J313',[('1','12'),('2','11')],4,.4)]:
        opts[ref]=options(REF[ref],drv,prs,bnd,gap)
        print(ref,len(opts[ref]),opts[ref][:18])
    reg=geom(REF['U107'],0,0)
    for ref,prs in [('C108',[('1','1'),('2','2')]),('C109',[('1','3'),('2','2')])]:
        z=options(REF[ref],reg,prs,4,1)
        print(ref,len(z),z[:12])
    combos=[]
    for a,b,c in itertools.product(opts['C312'],opts['C311'],opts['J313']):
        rec=[geom(REF[ref],*o[1:4])[0] for ref,o in zip(['C312','C311','J313'],[a,b,c])]
        if any(rect_distance(i,j)<.4*PITCH-1e-6 for i,j in itertools.combinations(rec,2)): continue
        # connector near north edge: row 2 origin means -2 here when driver VIN row4
        allr=[drv[0]]+rec
        bx=(min(r[0] for r in allr),min(r[1] for r in allr),max(r[2] for r in allr),max(r[3] for r in allr))
        combos.append((sum(o[0] for o in [a,b,c]),(bx[2]-bx[0])/PITCH,(bx[3]-bx[1])/PITCH,a,b,c))
    print('COMBOS',len(combos))
    for z in sorted(combos)[:25]: print(z)
    save_json(HERE/'feasibility.json',{'cap_ceramic':opts['C312'],'cap_bulk':opts['C311'],'connector':opts['J313'],'combinations':combos})
    for bound in range(5,9):
        print('REG bound',bound,'IN',options(REF['C108'],reg,[('1','1'),('2','2')],bound,1)[:4], 'OUT',options(REF['C109'],reg,[('1','3'),('2','2')],bound,1)[:4])
    opts['C312']=options(REF['C312'],drv,[('1','14'),('2','13')],3,.4)
    combos=[]
    for a,b,c in itertools.product(opts['C312'],opts['C311'],opts['J313']):
        rec=[geom(REF[ref],*o[1:4])[0] for ref,o in zip(['C312','C311','J313'],[a,b,c])]
        if any(rect_distance(i,j)<.4*PITCH-1e-6 for i,j in itertools.combinations(rec,2)): continue
        if c[3]!=0: continue
        allr=[drv[0]]+rec
        bx=(min(r[0] for r in allr),min(r[1] for r in allr),max(r[2] for r in allr),max(r[3] for r in allr))
        combos.append((sum(o[0] for o in [a,b,c]),(bx[2]-bx[0])/PITCH,(bx[3]-bx[1])/PITCH,a,b,c))
    print('RELAXED',len(combos))
    for z in sorted(combos)[:16]: print(z)
    for fid,base,prs,bnd,gap in [(REF['R210'],geom(REF['C211'],0,0),[('1','1'),('2','2')],2,.4),(REF['C208'],geom(REF['U207'],0,0),[('1','5'),('2','3')],2,.4)]:
        print('EXTRA',fid,options(fid,base,prs,bnd,gap))
        for bnd2 in range(bnd+1,bnd+4):
            zs=options(fid,base,prs,bnd2,gap)
            if zs:
                print('FIRST RELAX',bnd2,zs[:8]); break
    for bnd in range(3,7):
        zs=options(REF['D105'],geom(REF['C106'],0,0),[('1','1'),('2','2')],bnd,.4)
        print('TVS',bnd,len(zs),zs[:5])

if __name__=='__main__':
    {'seed':seed,'place':checkplace,'values':values,'feasibility':feasibility}.get(sys.argv[1] if len(sys.argv)>1 else 'feasibility',feasibility)()
