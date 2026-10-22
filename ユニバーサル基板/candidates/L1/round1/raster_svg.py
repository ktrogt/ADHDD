"""Offline raster preview of the simple SVG subset emitted by tools/render.py.

Reads actual SVG elements; does not use a browser or external resources.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import xml.etree.ElementTree as ET
import math

HERE=Path(__file__).resolve().parent
S=9

def render(path):
    root=ET.parse(path).getroot()
    _,_,w,h=map(float,root.attrib['viewBox'].split())
    im=Image.new('RGB',(math.ceil(w*S),math.ceil(h*S)),'white'); d=ImageDraw.Draw(im)
    def n(el,key,default=0):return float(el.attrib.get(key,default))*S
    def col(v,default='black'):return default if not v or v.startswith('url(') else v
    def segment(a,b,fill,width,dash=None):
        if not dash:d.line([a,b],fill=fill,width=width);return
        length=math.dist(a,b)
        if not length:return
        t=0
        while t<length:
            end=min(t+dash[0],length)
            d.line([(a[0]+(b[0]-a[0])*t/length,a[1]+(b[1]-a[1])*t/length),(a[0]+(b[0]-a[0])*end/length,a[1]+(b[1]-a[1])*end/length)],fill=fill,width=width)
            t+=sum(dash)
    for el in root.iter():
        tag=el.tag.rsplit('}',1)[-1];a=el.attrib
        if tag in ['svg','g','title','desc','defs','pattern','path']:continue
        stroke=a.get('stroke');fill=a.get('fill','black');width=max(1,round(n(el,'stroke-width',.2)))
        if tag=='rect':
            box=[n(el,'x'),n(el,'y'),n(el,'x')+n(el,'width'),n(el,'y')+n(el,'height')]
            d.rectangle(box,fill=None if fill=='none' else col(fill,'#ffe5cf'),outline=stroke,width=width)
        elif tag=='circle':
            x,y,r=n(el,'cx'),n(el,'cy'),n(el,'r')
            d.ellipse([x-r,y-r,x+r,y+r],fill=None if fill=='none' else fill,outline=stroke,width=width)
        elif tag in ['line','polyline']:
            points=[(n(el,'x1'),n(el,'y1')),(n(el,'x2'),n(el,'y2'))] if tag=='line' else [tuple(float(v)*S for v in z.split(',')) for z in a['points'].split()]
            dash=[float(z)*S for z in a['stroke-dasharray'].split(',')] if 'stroke-dasharray' in a else None
            for b,c in zip(points,points[1:]):segment(b,c,stroke or fill,width,dash)
        elif tag=='text':
            font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if a.get('font-weight')=='bold' else 'C:/Windows/Fonts/arial.ttf',max(1,round(n(el,'font-size',1.8))))
            txt=''.join(el.itertext());anchor={'start':'ls','middle':'ms','end':'rs'}.get(a.get('text-anchor'),'ls')
            d.text((n(el,'x'),n(el,'y')),txt,font=font,fill=fill,anchor=anchor,stroke_width=round(n(el,'stroke-width')) if stroke else 0,stroke_fill=stroke)
    dest=path.with_suffix('.png');im.save(dest);print(dest)

if __name__=='__main__':
    for name in ['top','bottom','overlay']:render(HERE/'out'/f'{name}.svg')
