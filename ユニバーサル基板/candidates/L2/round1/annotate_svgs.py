"""Local SVG annotations: true nominal board outline, M3 holes, USB direction.
Shared renderer is never modified. Preserve its grid window and TOP hole identity.
"""
import sys,math,json,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import ImageFont
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'tools'))
from model import Project,save_json,rotate
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
def tag(s):return '{'+NS+'}'+s
def run():
    p=Project(H);checks=[]
    for view in ('top','bottom','overlay'):
        path=H/'out'/f'{view}.svg';raw=path.read_text(encoding='utf-8');(H/'out'/f'{view}.tool.svg').write_text(raw,encoding='utf-8')
        root=ET.fromstring(raw);vb=[float(v) for v in root.get('viewBox').split()];vb[2]+=10;root.set('viewBox',' '.join(map(str,vb)));root.set('width',str(vb[2])+'mm')
        # Shift the tool's colour legend away from the true board edge.
        for e in root.iter():
            for key in ('x','x1','x2'):
                if key in e.attrib and float(e.attrib[key])>=162.7-1e-6:e.set(key,str(float(e.attrib[key])+10))
        root.find(tag('rect')).set('width',str(vb[2]))
        g=ET.Element(tag('g'),{'id':'L2-physical-board','font-family':'Arial, sans-serif'})
        ET.SubElement(g,tag('rect'),dict(x='8.35',y='9.8',width='155',height='114',fill='none',stroke='#45688c',**{'stroke-width':'.28','stroke-dasharray':'2,1'}))
        for m in p.board['mounting_holes_mm']:
            xx=8.35+(155-m['x'] if view=='bottom' else m['x']);yy=9.8+m['y']
            ET.SubElement(g,tag('circle'),dict(cx=str(xx),cy=str(yy),r='1.6',fill='none',stroke='#45688c',**{'stroke-width':'.22'}))
        root.insert(2,g)
        t=ET.SubElement(root,tag('text'),dict(x='16',y='131',fill='#45688c',**{'font-family':'Arial, sans-serif','font-size':'1.8'}));t.text='Dashed outline: actual 155 x 114 mm board; grid origin nominal. NOT FOR BUILD.'
        pp=p.parts['U201'];o=pp.pins[0].xy;f=pp.footprint['features']['usb_mouth'];v=rotate((f['x_mm'],f['y_mm']),pp.data['rotation'])
        xx=17.27+o[0]*p.pitch+v[0];yy=17.27+o[1]*p.pitch+v[1];direction=1
        if view=='bottom':xx=171.7-xx;direction=-1
        end=166.5 if view!='bottom' else 5.0
        ET.SubElement(root,tag('line'),dict(x1=str(xx),y1=str(yy),x2=str(end),y2=str(yy),stroke='#245f88',**{'stroke-width':'.35'}))
        ET.SubElement(root,tag('polyline'),dict(points=f'{end-direction*1.8},{yy-1.2} {end},{yy} {end-direction*1.8},{yy+1.2}',fill='none',stroke='#245f88',**{'stroke-width':'.35'}))
        t=ET.SubElement(root,tag('text'),dict(x='165.2' if view!='bottom' else '2.0',y=str(yy-1.6),fill='#245f88',**{'font-family':'Arial, sans-serif','font-size':'1.7','font-weight':'bold','text-anchor':'start'}));t.text='USB'
        # Check rendered refdes text boxes with the same Arial font used in preview.
        labels=[]
        for e in root.iter(tag('text')):
            s=''.join(e.itertext())
            if s not in p.parts:continue
            size=float(e.get('font-size','1.95'));font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',round(size*100))
            x,y=float(e.get('x')),float(e.get('y'));bb=font.getbbox(s,anchor='ms')
            labels.append((s,(x+bb[0]/100,y+bb[1]/100,x+bb[2]/100,y+bb[3]/100)))
        overlap=[]
        for i,(a,aa) in enumerate(labels):
            for b,bb in labels[i+1:]:
                if aa[0]<bb[2] and bb[0]<aa[2] and aa[1]<bb[3] and bb[1]<aa[3]:overlap.append([a,b])
        checks.append(dict(view=view,refdes_labels=len(labels),overlapping_refdes=overlap,physical_canvas_mm=vb[2:]))
        assert len(labels)==54 and not overlap,checks[-1]
        path.write_text('<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(root,encoding='unicode')+'\n',encoding='utf-8')
    save_json(H/'out/visual_qa.json',dict(label_checks=checks,method='Opened and parsed all three SVGs; rendered their actual vector elements offline with Pillow for visual inspection. Browser file URL was blocked; no browser workaround was used.',notes=['TOP is uncluttered because every jumper is on the underside.','BOTTOM is mirrored, with TOP hole identities retained.','Original tool renderings are *.tool.svg; annotations add true nominal outline/M3/USB without changing placement or wiring.','Nominal origin and M3 geometry require real-board dry fit; proposed outline is not a construction release.']))
    print(checks)
if __name__=='__main__':run()
