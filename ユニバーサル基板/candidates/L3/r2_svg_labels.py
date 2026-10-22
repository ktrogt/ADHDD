"""Round-2 labels and planar grip-review patches on unchanged tool geometry."""
import sys,json,xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parent.parent
sys.path.insert(0,str(B/'tools'))
from model import Project,load_json
p=Project(H,board=load_json(B/'board.json'));m=json.loads((H/'out/metrics.json').read_text())
grips=json.loads((H/'out/grip_review.json').read_text())['patches']
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
W=p.board_rect[2]-p.board_rect[0];gx=-p.board_rect[0];gy=-p.board_rect[1]
for view in ['top','bottom','overlay']:
    path=H/'out'/f'{view}.svg';tree=ET.parse(path);root=tree.getroot()
    for q in list(root):
        if q.get('id')=='L3-R2-annotations':root.remove(q)
    for t in root.iter('{'+NS+'}text'):
        if t.text=='Square: pin 1 / polarity':t.text='Square: logical pin 1 / polarity'
    g=ET.SubElement(root,'{'+NS+'}g',{'id':'L3-R2-annotations','font-family':'Arial, sans-serif'})
    t=ET.SubElement(g,'{'+NS+'}text',{'x':'16','y':'12','font-size':'1.65','fill':'#a02222'});t.text=f"L3 R2 / F3 | LVS PASS | core DRC 0 | hard FAIL: P08, P09 | {m['jumpers']} jumpers | BOTTOM wiring"
    if view!='bottom':
        for box in grips:
            a,b,c,d=box['rect_A1_mm'];ET.SubElement(g,'{'+NS+'}rect',{'x':f'{16+gx+a:.3f}','y':f'{16+gy+b:.3f}',
                'width':f'{c-a:.3f}','height':f'{d-b:.3f}','fill':'#dbeafe','fill-opacity':'0.28','stroke':'#2563eb','stroke-width':'0.12','stroke-dasharray':'0.6,0.4'})
        t=ET.SubElement(g,'{'+NS+'}text',{'x':'16','y':'141.2','font-size':'1.6','fill':'#1d4ed8'});t.text='Blue patches: proposed finger access (TOP); physical removal still requires review.'
    for ch in range(1,5):
        a,b,c,d=p.parts[f'U{300+10*ch}'].rect;cx=(a+c)/2;cy=(b+d)/2
        xx=16+W-gx-cx if view=='bottom' else 16+gx+cx
        t=ET.SubElement(g,'{'+NS+'}text',{'x':f'{xx:.3f}','y':f'{16+gy+cy+3:.3f}','font-size':'1.55','text-anchor':'middle','fill':'#334155','stroke':'#fffdf5','stroke-width':'0.5','paint-order':'stroke','font-weight':'bold'});t.text=f'HDD{ch}'
    tree.write(path,encoding='utf-8',xml_declaration=True)
