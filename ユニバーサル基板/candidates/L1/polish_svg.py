"""Text-only SVG fixes for L1 round 2; does not alter placement or wiring."""
from common import *
import xml.etree.ElementTree as ET
ET.register_namespace('','http://www.w3.org/2000/svg')
NS='{http://www.w3.org/2000/svg}'

def main():
 p=project();records=[]
 for view in ['top','bottom','overlay']:
  path=HERE/'out'/f'{view}.svg';tree=ET.parse(path);root=tree.getroot();g=root.find(NS+'g')
  def xy(x,y):return (16+p.board_rect[2]-x*PITCH if view=='bottom' else 16-p.board_rect[0]+x*PITCH,16-p.board_rect[1]+y*PITCH)
  rows={'C106':17.5,'C108':33.2,'C109':32.2,'D103':14.2,'U107':27.5}
  for ch in range(1,5):rows[f'C{300+ch*10+1}']=5.5;rows[f'J{300+ch*10+3}']=3.1
  rows.update(J202=40.1,J203=40.1)
  for t in root.iter(NS+'text'):
   ref=t.text or ''
   if ref in rows:
    old=dict(t.attrib);newy=xy(0,rows[ref])[1];t.set('y',f'{newy:.3f}')
    records.append({'view':view,'ref':ref,'old':old,'new':dict(t.attrib)})
    if ref=='C108':
     t.set('x',f'{xy(21,33.2)[0]:.3f}')
     a=xy(22,29.5);b=(float(t.get('x')),newy-.5)
     ET.SubElement(g,NS+'line',{'x1':str(a[0]),'y1':str(a[1]),'x2':str(b[0]),'y2':str(b[1]),'stroke':'#697586','stroke-width':'0.15'})
   elif ref=='D110':
    old=dict(t.attrib);a=xy(55.5,35);t.set('x',f'{a[0]:.3f}');t.set('y',f'{a[1]:.3f}')
    centre=xy(53,35)
    ET.SubElement(g,NS+'line',{'x1':str(centre[0]),'y1':str(centre[1]),'x2':str(a[0]),'y2':str(a[1]-.5),'stroke':'#697586','stroke-width':'0.15'})
    records.append({'view':view,'ref':ref,'old':old,'new':dict(t.attrib)})
   elif ref=='U201':t.set('font-size','2.4')
   if ref.isalpha() and len(ref)==2 and ref in [hole((x,0))[:-1] for x in range(26,55)]:t.set('font-size','1.45')
  if view=='top':
   for label,x,y in [('USB >',49.6,26.5),('BOOTSEL end',48.5,28.2)]:
    q=xy(x,y);ET.SubElement(g,NS+'text',{'x':f'{q[0]:.3f}','y':f'{q[1]:.3f}','font-size':'1.55','text-anchor':'middle','fill':'#344054'}).text=label
  tree.write(path,encoding='utf-8',xml_declaration=True)
 save_json(HERE/'out'/'render_qc.json',{'method':'actual SVG XML opened and rendered offline by raster_svg.py; no browser/network required','labels_adjusted':records,'status':'PENDING visual inspection','bottom_view':'BC..A mirrored; CSV hole names remain TOP'})
 print('SVG reference labels moved off polarity/pad/NC marks.')

if __name__=='__main__':main()
