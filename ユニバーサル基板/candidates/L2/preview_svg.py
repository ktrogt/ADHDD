"""Offline SVG previews for this tool's simple SVG vocabulary, using Pillow.
No browser/network/file-URL policy is involved. Source SVG remains the deliverable.
"""
import sys,math,re,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent
def preview(path):
    root=ET.parse(path).getroot(); vb=list(map(float,root.attrib['viewBox'].split())); scale=10
    im=Image.new('RGB',(round(vb[2]*scale),round(vb[3]*scale)),'white');d=ImageDraw.Draw(im)
    fonts={}
    def font(size,bold=False):
        k=size,bold
        if k not in fonts:fonts[k]=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',round(size*scale))
        return fonts[k]
    def color(c):return None if c in (None,'none') or c.startswith('url(') else c
    def line(points,fill,width,dash=None):
        if fill is None:return
        if not dash:d.line(points,fill=fill,width=max(1,round(width*scale)));return
        pat=[float(x)*scale for x in dash.split(',')]
        for a,b in zip(points,points[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);t=0;i=0
            while t<length:
                end=min(length,t+pat[i%len(pat)])
                if i%2==0:d.line([(a[0]+dx*t/length,a[1]+dy*t/length),(a[0]+dx*end/length,a[1]+dy*end/length)],fill=fill,width=max(1,round(width*scale)))
                i+=1;t=end
    for e in root.iter():
        tag=e.tag.rsplit('}',1)[-1];a=e.attrib
        if tag in {'svg','defs','pattern','title','desc'}:continue
        # Ignore hatch definitions, which are not direct SVG children.
        if tag not in {'rect','circle','line','polyline','text'}:continue
        fill=color(a.get('fill','black'));stroke=color(a.get('stroke'));width=float(a.get('stroke-width',1))
        xy=lambda k:float(a.get(k,0))*scale
        if tag=='rect':
            box=(xy('x'),xy('y'),xy('x')+xy('width'),xy('y')+xy('height'))
            dash=a.get('stroke-dasharray')
            d.rectangle(box,fill=fill,outline=None if dash else stroke,width=max(1,round(width*scale)))
            if dash:
                x0,y0,x1,y1=box;line([(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)],stroke,width,dash)
        elif tag=='circle':
            x,y,r=xy('cx'),xy('cy'),xy('r');d.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline=stroke,width=max(1,round(width*scale)))
        elif tag=='line':line([(xy('x1'),xy('y1')),(xy('x2'),xy('y2'))],stroke,width,a.get('stroke-dasharray'))
        elif tag=='polyline':
            ps=[tuple(float(c)*scale for c in p.split(',')) for p in a['points'].split()];line(ps,stroke,width,a.get('stroke-dasharray'))
        elif tag=='text':
            size=float(a.get('font-size',1.8));f=font(size,a.get('font-weight')=='bold');anchor={'middle':'ms','end':'rs'}.get(a.get('text-anchor'),'ls')
            text=''.join(e.itertext());d.text((xy('x'),xy('y')),text,font=f,fill=fill or 'black',anchor=anchor,stroke_width=round(width*scale) if stroke else 0,stroke_fill=stroke)
    out=path.with_suffix('.preview.png');im.save(out);print(out)
if __name__=='__main__':
    for v in ('top','bottom','overlay'):preview(H/'out'/f'{v}.svg')
