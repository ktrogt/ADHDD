from common import *
from verify import placement_drc
from rules import evaluate

def seed():
 d=json.loads((HERE/'round1'/'placement.json').read_text(encoding='utf8'));parts=d['parts']
 def put(ref,x,y,r=0):parts[ref].update(hole=hole((x,y)),rotation=r)
 for ch,x in zip([4,3,2,1],[5,19,33,47]):
  b=300+ch*10
  for ref,xx,yy,r in [(f'U{b}',x,10,270),(f'C{b+1}',x-4,4,90),(f'C{b+2}',x-1,3,0),(f'J{b+3}',x+2,2,0),(f'TP{470+ch}',x+6,3,0)]:put(ref,xx,yy,r)
 for ref,x,y,r in [('U201',52,23,90),('C108',22,29,90),('C109',10,31,270),('D110',53,33,90),
                   ('J213',32,39,0),('R214',32,35,180),('R215',30,20,90),('R212',34,20,180),
                   ('TP461',24,33,0),('TP462',41,32,0),('TP464',26,30,0),('TP467',35,37,0),('TP468',28,23,0)]:put(ref,x,y,r)
 # Receiver sits below Pico, outside the north-facing GPIO fanout.
 for ref,x,y,r in [('J202',43,39,0),('J203',48,39,0),('U207',46,34,0),('C208',47,32,180),
                   ('R204',43,37,270),('R205',39,35,90),('D206',40,39,180)]:put(ref,x,y,r)
 d['candidate']='L1 round2';d['rules_version']='v0.2';d['nodes']['GND_LOGIC']='Q31'
 return d

def check(d,verbose=True):
 p=project(d,{'schema_version':1,'conductors':[]})
 issues=placement_drc(p)+evaluate(p,placement_only=True)
 bad=[i for i in issues if i['severity']=='error' and i.get('status')!='UNCHECKED']
 if verbose:
  for i in bad:print(i['code'],i['detail'])
 return bad

def receiver(d):
 # Search UART connector pair, buffer, bypass, and input resistor as a rigid group.
 ignored={'J202','J203','U207','C208','R204','R205','D206'}
 fixed=[(k,geom(v['footprint'],*point(v['hole']),v['rotation'])[0]) for k,v in d['parts'].items() if k not in ignored]
 def fit(ref,x,y,r,others):
  rr,pp=geom(REF[ref],x,y,r)
  if any(not(0<=a<55 and 0<=b<40) for a,b in pp.values()):return None
  if any(rect_distance(rr,z)<.4*PITCH-1e-7 for _,z in fixed+others):return None
  return rr,pp
 best=None
 for cy in [20,19,18,17,16,15,21,22,23,24]:
  for cr in [90,270,0,180]:
   c1=fit('J202',53,cy,cr,[]);c2=fit('J203',53,cy+5,cr,[])
   if not c1 or not c2 or rect_distance(c1[0],c2[0])<.4*PITCH:continue
   others=[('J202',c1[0]),('J203',c2[0])]
   for ux,uy,ur in itertools.product(range(43,53),range(cy-4,cy+8),[0,90,180,270]):
    u=fit('U207',ux,uy,ur,others)
    if not u:continue
    for rx,ry,rr in itertools.product(range(47,55),range(cy-2,cy+6),[0,90,180,270]):
     r=fit('R204',rx,ry,rr,others+[('U207',u[0])])
     if not r:continue
     if man(r[1]['1'],c1[1]['1'])>4 or man(r[1]['2'],u[1]['2'])>4:continue
     for dx,dy in [(1,-2),(3,4)]:
      off=rotate((dx,dy),ur);cx,yy,rot=ux+off[0],uy+off[1],(ur+180)%360
      cap=fit('C208',cx,yy,rot,others+[('U207',u[0]),('R204',r[0])])
      if not cap or max(man(cap[1]['1'],u[1]['5']),man(cap[1]['2'],u[1]['3']))>4:continue
      score=man(c1[1]['1'],r[1]['1'])+man(r[1]['2'],u[1]['2'])+man(u[1]['4'],(52,30))
      if best is None or score<best[0]:
       best=(score,[(ref,x,y,rot) for ref,x,y,rot in [('J202',53,cy,cr),('J203',53,cy+5,cr),('U207',ux,uy,ur),('R204',rx,ry,rr),('C208',cx,yy,rot)]])
       print('RECEIVER',best,flush=True)
       for ref,x,y,r in best[1]:d['parts'][ref].update(hole=hole((x,y)),rotation=r)
       return d
   if best and best[0]<8:break
  if best and best[0]<8:break
 assert best,'no receiver micro-layout'
 print('RECEIVER',best)
 for ref,x,y,r in best[1]:d['parts'][ref].update(hole=hole((x,y)),rotation=r)
 # R205/D206 lie alongside the RX-input node. Their exact routing is unrestricted.
 for ref,x,y,r in [('R205',44,18,0),('D206',44,16,0)]:d['parts'][ref].update(hole=hole((x,y)),rotation=r)
 return d

if __name__=='__main__':
 d=seed();save_json(HERE/'placement.r2.json',d);check(d)
