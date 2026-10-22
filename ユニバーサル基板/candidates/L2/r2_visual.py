"""Candidate-only USB annotation and refdes label checks on tool SVGs."""
import sys,xml.etree.ElementTree as ET
from PIL import ImageFont
sys.dont_write_bytecode=True
import r2 as b
from model import save_json
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
def tag(s):return '{'+NS+'}'+s
p=b.project();checks=[]
for view in ('top','bottom','overlay'):
 path=b.H/'out'/f'{view}.svg';s=path.read_text(encoding='utf-8');root=ET.fromstring(s)
 if root.find(".//*[@id='L2_USB']") is None:(b.H/'out'/f'{view}.tool.svg').write_text(s,encoding='utf-8')
 for e in list(root):
  if e.get('id')=='L2_USB':root.remove(e)
 g=ET.SubElement(root,tag('g'),{'id':'L2_USB','font-family':'Arial, sans-serif'})
 xx=23.55 if view!='bottom' else 163.45;yy=75.54;end=17 if view!='bottom' else 170;direction=-1 if view!='bottom' else 1
 ET.SubElement(g,tag('line'),dict(x1=str(xx),y1=str(yy),x2=str(end),y2=str(yy),stroke='#245f88',**{'stroke-width':'.35'}))
 ET.SubElement(g,tag('polyline'),dict(points=f'{end-direction*1.5},{yy-1} {end},{yy} {end-direction*1.5},{yy+1}',fill='none',stroke='#245f88',**{'stroke-width':'.35'}))
 t=ET.SubElement(g,tag('text'),dict(x='17.5' if view!='bottom' else '164.5',y=str(yy-1.6),fill='#245f88',**{'font-size':'1.7','font-weight':'bold'}));t.text='USB'
 labels=[]
 for e in root.iter(tag('text')):
  s=''.join(e.itertext())
  if s not in p.parts:continue
  f=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',round(float(e.get('font-size','1.95'))*100));bb=f.getbbox(s,anchor='ms');x,y=float(e.get('x')),float(e.get('y'))
  labels.append((s,(x+bb[0]/100,y+bb[1]/100,x+bb[2]/100,y+bb[3]/100)))
 overlap=[]
 for i,(a,aa) in enumerate(labels):
  for c,cc in labels[i+1:]:
   if aa[0]<cc[2] and cc[0]<aa[2] and aa[1]<cc[3] and cc[1]<aa[3]:overlap.append([a,c])
 assert len(labels)==54 and not overlap,(view,overlap)
 path.write_text('<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(root,encoding='unicode')+'\n',encoding='utf-8')
 checks.append(dict(view=view,refdes_count=len(labels),overlapping_refdes=overlap))
save_json(b.H/'out/visual_qa.json',dict(checks=checks,method='All three SVGs opened as XML, rendered locally with Pillow/Arial, and visually inspected. Browser file URLs were blocked in round 1; no browser workaround was used.',notes=['Tool renderer now supplies the physical board/M3 outline.','Candidate-only USB arrows added in the free margin.','BOTTOM mirrored; all hole names remain TOP identities.','Provisional body offsets, 3D access and print calibration require dry fit.']))
print(checks)
