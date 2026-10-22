"""Offline preview of the shared tool's simple SVG primitives using Pillow.
No browser, network, screenshots, or shared-tool modifications. SVG remains master.
"""
from pathlib import Path
import sys, math, re, xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

def raster(path,scale=8):
    root=ET.parse(path).getroot();vb=list(map(float,root.attrib['viewBox'].split()))
    img=Image.new('RGB',(math.ceil(vb[2]*scale),math.ceil(vb[3]*scale)),'white');d=ImageDraw.Draw(img)
    def v(e,k,default=0):return float(e.get(k,default))*scale
    def colour(x):return None if x in [None,'none'] else '#f1d8bb' if x.startswith('url(') else x
    def draw(e):
        tag=e.tag.split('}')[-1]
        if tag in ['defs','title','desc']:return
        a=e.attrib;fill=colour(a.get('fill'));stroke=colour(a.get('stroke'));sw=max(1,round(v(e,'stroke-width',.2)))
        if tag=='rect':d.rectangle((v(e,'x'),v(e,'y'),v(e,'x')+v(e,'width'),v(e,'y')+v(e,'height')),fill=fill,outline=stroke,width=sw)
        elif tag=='circle':
            x,y,r=v(e,'cx'),v(e,'cy'),v(e,'r');d.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline=stroke,width=sw)
        elif tag in ['line','polyline']:
            pts=[(v(e,'x1'),v(e,'y1')),(v(e,'x2'),v(e,'y2'))] if tag=='line' else [(float(x)*scale,float(y)*scale) for x,y in [p.split(',') for p in a['points'].split()]]
            if stroke:
                if 'stroke-dasharray' in a:
                    dash=list(map(float,re.split('[, ]+',a['stroke-dasharray'])));pos=0
                    for b,c in zip(pts,pts[1:]):
                        length=math.dist(b,c);s=0
                        while s<length:
                            t=min(s+dash[0]*scale,length)
                            d.line([(b[0]+(c[0]-b[0])*s/length,b[1]+(c[1]-b[1])*s/length),(b[0]+(c[0]-b[0])*t/length,b[1]+(c[1]-b[1])*t/length)],fill=stroke,width=sw)
                            s=t+dash[-1]*scale
                else:d.line(pts,fill=stroke,width=sw,joint='curve')
        elif tag=='text':
            font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if a.get('font-weight')=='bold' else 'C:/Windows/Fonts/arial.ttf',max(1,round(v(e,'font-size',1.8))))
            anchor={'start':'ls','middle':'ms','end':'rs'}.get(a.get('text-anchor','start'),'ls')
            d.text((v(e,'x'),v(e,'y')),e.text or '',font=font,anchor=anchor,fill=fill or '#202a35',stroke_width=sw if stroke else 0,stroke_fill=stroke)
        for child in e:draw(child)
    draw(root)
    output=Path(path).with_suffix('.png');img.save(output);return output
if __name__=='__main__':
    for name in sys.argv[1:]:print(raster(Path(name)))
