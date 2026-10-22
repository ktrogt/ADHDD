"""Read-only input/output consistency check; emits a local final-file manifest."""
import sys,json,csv,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent
sys.path.insert(0,str(BASE/'tools'))
from model import Project,save_json
from verify import verify
p=Project(HERE)
report=json.loads((HERE/'out/report.json').read_text(encoding='utf-8'))
assert verify(p)==report,'saved report does not match final inputs'
assert json.loads((HERE/'out/metrics.json').read_text())==report['metrics']
assert report['lvs_pass'] and not report['passed']
for src,dst in [('board.json','board.json'),('footprints_ub.json','footprints_ub.json'),('design_rules.json','design_rules.json'),('netlist_ub.csv','netlist.csv')]:
    assert (BASE/src).read_bytes()==(HERE/dst).read_bytes(),src+' differs'
for path,N in [('out/netlist_actual.csv',186),('out/wirelist.csv',len(p.conductors)),('out/continuity.csv',1102),('out/assembly_pin_map.csv',193)]:
    with (HERE/path).open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==N,path
assert all(c['side']=='bottom' for c in p.conductors)
ns={'s':'http://www.w3.org/2000/svg'};svgs={}
for view in ['top','bottom','overlay']:
    root=ET.parse(HERE/'out'/f'{view}.svg').getroot();svgs[view]=root
    vb=list(map(float,root.attrib['viewBox'].split()))
    assert abs(float(root.attrib['width'].removesuffix('mm'))-vb[2])<1e-6
    assert abs(float(root.attrib['height'].removesuffix('mm'))-vb[3])<1e-6
    assert root.attrib['data-l3-values-shift-mm']=='8'
    assert len([t for t in root.findall('.//s:text',ns) if (t.text or '') in ['HDD1','HDD2','HDD3','HDD4']])==4
    assert any(abs(float(l.get('x2'))-float(l.get('x1'))-20)<1e-6 and l.get('y1')==l.get('y2') for l in root.findall('.//s:line',ns))
def pin_circle(root,label):
    for c in root.findall('.//s:circle',ns):
        t=c.find('s:title',ns)
        if t is not None and (t.text or '').startswith(label+' #'):return c
    raise ValueError(label)
for label in ['U201.GP2','U310.VIN','J101.CENTER']:
    a=pin_circle(svgs['top'],label);b=pin_circle(svgs['bottom'],label)
    assert abs(float(a.get('cx'))+float(b.get('cx'))-(32+p.columns*p.pitch))<.002
    assert a.get('cy')==b.get('cy')
required=['placement.json','wiring.json','summary.md','constraints.md','README.md','input_hashes.json','infeasibility.json']+[
    'out/'+name for name in ['top.svg','bottom.svg','overlay.svg','report.json','metrics.json','wirelist.csv','continuity.csv','netlist_actual.csv','extended_metrics.json','assembly_pin_map.csv','assembly_solder_sites.csv','wire_supports.csv','solder_plan_validation.json','verify.log']]
manifest={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in required}
save_json(HERE/'out/package_check.json',{'package_consistency':'PASS','LVS':'PASS','hard_audit':'FAIL',
    'scope':'exact final report; immutable input copies; CSV counts; SVG 1:1 scale, 20mm ruler and mirrored pin coordinates',
    'manifest_sha256':manifest})
print('PACKAGE consistency PASS; final LVS PASS; hard-rule audit remains FAIL')
