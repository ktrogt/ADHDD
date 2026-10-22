import build
from build import *
from model import rect_intersects
p=Project(HERE)
fixed=[z for k,z in p.parts.items() if k not in ['C106','D105','J104']]
blocked={q.xy for q in p.pins.values() if q.ref not in ['C106','D105','J104']}
def valid(ref,x,y,r):
    rr=rect(ref,x,y,r)
    if rr[0]<-1.27 or rr[1]<-1.27 or rr[2]>54.5*2.54 or rr[3]>39.5*2.54:return False
    if any(rect_distance(rr,z.rect)<1.016-1e-8 for z in fixed):return False
    ps=[pin(ref,z['number'],x,y,r) for z in F['footprints'][REF[ref]]['pins']]
    if any(not p.usable(q) or q in blocked for q in ps):return False
    if ref=='C106' and rect_distance(rr,p.parts['D103'].rect)<10.16-1e-8:return False
    return True
caps=[];heads=[];diodes=[]
for r in [0,90,180,270]:
 for x in range(27,38):
  for y in range(0,11):
   for ref,arr in [('C106',caps),('J104',heads),('D105',diodes)]:
    if ref=='J104' and y>2:continue
    if valid(ref,x,y,r):arr.append((x,y,r,rect(ref,x,y,r)))
results=[]
for c in caps:
 vm=pin('C106',1,*c[:3]);gnd=pin('C106',2,*c[:3])
 if man(gnd,p.pin_at('J101.SLEEVE'))>6:continue
 for h in heads:
  hv=pin('J104',2,*h[:3])
  if man(vm,hv)>6 or rect_distance(c[3],h[3])<1.016-1e-8:continue
  for d in diodes:
   ds=[man(pin('D105',1,*d[:3]),vm),man(pin('D105',2,*d[:3]),gnd)]
   if max(ds)>6 or man(pin('D105',1,*d[:3]),hv)>6:continue
   if min(rect_distance(d[3],c[3]),rect_distance(d[3],h[3]))<1.016-1e-8:continue
   coords=[pin(ref,n,*q[:3]) for ref,q,ns in [('C106',c,[1,2]),('J104',h,[1,2]),('D105',d,[1,2])] for n in ns]
   if len(set(coords))!=6:continue
   results.append((max(ds),sum(ds),c[:3],h[:3],d[:3],ds))
print('BEST ENTRY',len(results),sorted(results)[:25])
