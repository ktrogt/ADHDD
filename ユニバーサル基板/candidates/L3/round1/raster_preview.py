"""Offline raster preview for the exact simple SVG primitives emitted by T6.

No browser, network, file-URL access, or external converter is involved. Pillow
renders rect/line/polyline/circle/text, including dashes and label text strokes.
This is a visual-QA aid, not the manufacturing scale reference (SVG is that).
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import math
from PIL import Image,ImageDraw,ImageFont,ImageColor
HERE=Path(__file__).resolve().parent
S=8
FONT=Path('C:/Windows/Fonts')
def n(a,k,d=0):return float(a.get(k,d))
def col(s):return ImageColor.getrgb(s)
def raster(path):
    root=ET.parse(path).getroot();vb=[float(z) for z in root.attrib['viewBox'].split()]
    im=Image.new('RGB',(round(vb[2]*S),round(vb[3]*S)),'white')
    draw=ImageDraw.Draw(im)
    def xy(a,x,y):return n(a,x)*S,n(a,y)*S
    def stroke(a):return max(1,round(n(a,'stroke-width',.2)*S))
    def lines(points,a):
        colour=a.get('stroke','black');width=stroke(a)
        dash=a.get('stroke-dasharray')
        if dash:
            ds=[float(z)*S for z in dash.split(',')]
            for q,r in zip(points,points[1:]):
                length=math.dist(q,r);t=0
                while t<length:
                    z=min(t+ds[0],length)
                    draw.line([(q[0]+(r[0]-q[0])*t/length,q[1]+(r[1]-q[1])*t/length),(q[0]+(r[0]-q[0])*z/length,q[1]+(r[1]-q[1])*z/length)],fill=colour,width=width)
                    t+=sum(ds)
        else:draw.line(points,fill=colour,width=width,joint='curve')
    def visit(el):
        tag=el.tag.rsplit('}',1)[-1];a=el.attrib
        if tag in ['defs','desc','title']:return
        if tag in ['svg','g']:
            for q in el:visit(q)
            return
        if tag=='rect':
            x,y=xy(a,'x','y');w,h=n(a,'width')*S,n(a,'height')*S
            fill=a.get('fill');colour=None if fill in (None,'none') else '#fae1ca' if fill.startswith('url') else fill
            if colour and n(a,'fill-opacity',1)<1:
                rgb=col(colour);alpha=n(a,'fill-opacity',1)
                colour=tuple(round(alpha*z+(1-alpha)*255) for z in rgb)
            outline=None if a.get('stroke','none')=='none' else a['stroke']
            draw.rectangle([x,y,x+w,y+h],fill=colour,outline=outline,width=stroke(a))
            return
        if tag=='line':lines([xy(a,'x1','y1'),xy(a,'x2','y2')],a);return
        if tag=='polyline':
            ps=[tuple(float(c)*S for c in z.split(',')) for z in a['points'].split()]
            lines(ps,a);return
        if tag=='circle':
            x,y=xy(a,'cx','cy');r=n(a,'r')*S
            draw.ellipse([x-r,y-r,x+r,y+r],fill=None if a.get('fill','none')=='none' else a['fill'],outline=None if a.get('stroke','none')=='none' else a['stroke'],width=stroke(a));return
        if tag=='text':
            size=max(1,round(n(a,'font-size',1.8)*S))
            font=ImageFont.truetype(str(FONT/('arialbd.ttf' if a.get('font-weight')=='bold' else 'arial.ttf')),size)
            anchor={'middle':'ms','end':'rs'}.get(a.get('text-anchor'),'ls')
            draw.text(xy(a,'x','y'),el.text or '',fill=a.get('fill','#202a35'),font=font,anchor=anchor,
                      stroke_width=stroke(a) if 'stroke' in a else 0,stroke_fill=a.get('stroke','white'))
            return
        raise ValueError('unhandled SVG primitive: '+tag)
    visit(root)
    im.save(path.with_suffix('.png'))
    im.crop((round(12*S),round(12*S),round(160*S),round(122*S))).save(path.with_name(path.stem+'-board.png'))
    print(path.with_suffix('.png'))
if __name__=='__main__':
    for x in ['top','bottom','overlay']:raster(HERE/'out'/f'{x}.svg')
