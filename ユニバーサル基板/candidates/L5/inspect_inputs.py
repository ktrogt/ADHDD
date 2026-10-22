import sys, json, shutil, importlib.util, urllib.request
from pathlib import Path
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
BASE=HERE.parent.parent
for f in ['board.json','footprints_ub.json','netlist_ub.csv','design_rules_v0.2.json']:
    dst={'netlist_ub.csv':'netlist.csv','design_rules_v0.2.json':'design_rules.json'}.get(f,f)
    if not (HERE/dst).exists(): shutil.copyfile(BASE/f,HERE/dst)
for f in ['placement.json','wiring.json']:
    if not (HERE/f).exists(): shutil.copyfile(BASE/'candidates/L4'/f,HERE/f)
for m in ['fitz','PIL','cairosvg','pypdf','reportlab']: print(m,bool(importlib.util.find_spec(m)))
try:
    dest=HERE/'_sources/pololu.pdf'
    if not dest.exists():dest.write_bytes(urllib.request.urlopen('https://www.pololu.com/file/0J1862/drv887x-single-brushed-dc-motor-driver-carrier-schematic.pdf',timeout=20).read())
    import fitz
    doc=fitz.open(dest);doc[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(HERE/'_sources/pololu.png')
    print('downloaded/rendered',dest.stat().st_size)
except Exception as e:print(type(e).__name__,str(e))
r=json.loads((BASE/'design_rules_v0.2.json').read_text('utf-8-sig'))
print('AMENDMENTS',json.dumps(r.get('amendments_v0_2'),ensure_ascii=False))
for x in r['rules']: print(x['id'],x['type'],x['severity'],json.dumps(x.get('params'),ensure_ascii=False))
pl=json.loads((HERE/'placement.json').read_text('utf-8-sig'));print('PLACEMENT',[(r,d['hole'],d['rotation']) for r,d in pl['parts'].items()])
