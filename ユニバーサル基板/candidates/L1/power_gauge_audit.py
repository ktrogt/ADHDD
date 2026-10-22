"""Supplementary tree-path gauge audit, without claiming ampacity/drop approval."""
from common import *
from verify import net_graph,verify
from collections import defaultdict,deque

def main():
 p=project();r=verify(p)
 assert r['metrics']['comparison_tuple'][:3]==[True,0,0]
 audits=[]
 for net,numbers,node in [('VM',['14'],'VM_ENTRY'),('GND',['2','13'],'GND_ENTRY')]:
  root=point(p.placement['nodes'][node]);g=net_graph(p,net)
  areas={};gauges={};users=defaultdict(set)
  for c in p.conductors:
   if c['net']!=net:continue
   area=c.get('area_mm2')
   if area is None:
    awg=int(c['gauge'][3:]);area=math.pi/4*(.127*92**((36-awg)/39))**2
   pts=c['xy'] if c['kind']=='jumper' else c['contacts']
   pairs=[(pts[0],pts[-1])] if c['kind']=='jumper' else zip(pts,pts[1:])
   for a,b in pairs:
    key=tuple(sorted((a,b)))
    if area>=areas.get(key,0):areas[key]=area;gauges[key]=c['gauge']
  seen={root};prev={};todo=deque([root])
  while todo:
   q=todo.popleft()
   for z in g[q]:
    if z not in seen:seen.add(z);prev[z]=q;todo.append(z)
  for ch in range(1,5):
   for number in numbers:
    q=next(q.xy for q in p.pins.values() if q.ref==f'U{300+10*ch}' and q.number==number)
    while q!=root:
     a=prev[q];users[tuple(sorted((a,q)))].add(ch);q=a
  shared={key:chs for key,chs in users.items() if len(chs)>1}
  undersized=[{'a':hole(a),'b':hole(b),'channels':sorted(chs),'gauge':gauges[a,b]} for (a,b),chs in users.items() if areas[a,b] < (.5 if len(chs)>1 else .25)-1e-8]
  assert not undersized,undersized
  assert all(gauges[key]=='1.0 mm' for key in shared)
  audits.append({'net':net,'root':hole(root),'multi_channel_edges':len(shared),'multi_channel_gauges':sorted({gauges[key] for key in shared}),'minimum_multi_channel_area_mm2':round(min(areas[key] for key in shared),6),'minimum_motor_path_area_mm2':round(min(areas[key] for key in users),6),'undersized_edges':undersized})
 data={'status':'PASS: modeled tree-path conductor sizes only','does_not_clear_unchecked_W_rules':True,'scope':'Entry root to each carrier VIN14 / both GND pins; a channel counts once on shared edges. Contacts, actual voltage drop, temperature and off-board harness remain build checks.','paths':audits}
 save_json(HERE/'out/power_gauge_audit.json',data)
 print('Power gauge paths: shared motor edges all 1.0 mm; branches >=0.25 mm2.')

if __name__=='__main__':main()
