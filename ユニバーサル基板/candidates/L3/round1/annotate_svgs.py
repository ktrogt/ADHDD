"""L3-only SVG label additions; preserves every geometry and wire coordinate."""
import sys,json
from pathlib import Path
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent
sys.path.insert(0,str(BASE/'tools'))
from model import Project
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
p=Project(HERE)
for view in ['top','bottom','overlay']:
    path=HERE/'out'/f'{view}.svg';tree=ET.parse(path);root=tree.getroot()
    # T6's dense 42-net legend extends into the first two part-value rows.
    # Shift only the value key down; preserve the drawing's mm scale.
    if root.get('data-l3-values-shift-mm') is None:
        refs=tuple(ref+'  ' for ref in p.parts)
        for t in root.iter('{'+NS+'}text'):
            if (t.text or '').startswith('PART VALUES') or (t.text or '').startswith(refs):
                t.set('y',f"{float(t.get('y'))+8:.3f}")
            if t.text=='Square: pin 1 / polarity':t.text='Square: logical pin 1 / polarity'
        vb=[float(z) for z in root.get('viewBox').split()];vb[3]+=8
        root.set('viewBox',' '.join(f'{z:.3f}' for z in vb))
        root.set('height',f'{vb[3]:.3f}mm')
        root.set('data-l3-values-shift-mm','8')
        for q in list(root):
            if q.tag=='{'+NS+'}rect' and q.get('x')=='0' and q.get('y')=='0':q.set('height',str(vb[3]))
    for q in list(root):
        if q.get('id')=='L3-annotations':root.remove(q)
    g=ET.SubElement(root,'{'+NS+'}g',{'id':'L3-annotations','font-family':'Arial, sans-serif'})
    tx=ET.SubElement(g,'{'+NS+'}text',{'x':'16','y':'12','font-size':'1.65','fill':'#9f2222'})
    tx.text='L3 / F3 | LVS PASS | hard audit: 25 PASS / 11 FAIL / 25 UNCHECKED | all wiring BOTTOM'
    for ch in range(1,5):
        part=p.parts[f'U{300+10*ch}'];r=part.rect;cx=(r[0]+r[2])/2;cy=(r[1]+r[3])/2
        xx=16+p.columns*p.pitch-p.pitch/2-cx if view=='bottom' else 16+p.pitch/2+cx
        yy=16+p.pitch/2+cy+3
        t=ET.SubElement(g,'{'+NS+'}text',{'x':f'{xx:.3f}','y':f'{yy:.3f}','font-size':'1.55',
            'text-anchor':'middle','fill':'#334155','stroke':'#fffdf5','stroke-width':'0.5','paint-order':'stroke','font-weight':'bold'})
        t.text=f'HDD{ch}'
    tree.write(path,encoding='utf-8',xml_declaration=True)
