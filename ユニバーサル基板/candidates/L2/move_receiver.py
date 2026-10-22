"""Move the receiver one column right to clear the adjacent coil envelope."""
import sys,copy,json
sys.dont_write_bytecode=True
import r2 as b
from model import save_json,point,hole,compress
from branch_router_r2 import R
from verify import verify
def main():
 p=b.project();v=b.H/'variants/pre_receiver_clearance';v.mkdir(exist_ok=True)
 save_json(v/'placement.json',p.placement);save_json(v/'wiring.json',p.wire_data())
 pl=copy.deepcopy(p.placement)
 for ref,x,y,r in [('U207',26,34,0),('C208',27,32,180),('R204',24,37,270),('R205',27,31,0)]:pl['parts'][ref].update(hole=hole((x,y)),rotation=r)
 cs=[]
 for c in p.wire_data()['conductors']:
  if c['net'] in {'SN_RX_IN','SN_PU'}:continue
  ps=[point(q) for q in c['path']]
  if c['net']=='GND':
   if (25,34) in ps and (25,36) in ps:ps=[(x+1,y) for x,y in ps]
   elif c['kind']=='jumper' and set((ps[0],ps[-1]))=={(25,32),(25,36)}:ps=[(x+1,y) for x,y in ps]
  if c['net']=='+3V3':
   if c['id']=='L2W062':ps=[(27,32),(28,32),(28,34),(29,34),(30,34),(30,37),(31,37)]
   elif c['kind']=='bare' and ps[0]==(26,32) and ps[-1]==(28,34):ps=[(x+1,y) for x,y in ps]
   else:
    if ps[0]==(26,32):ps=[(27,32),(27,ps[1][1])]+ps[1:]
    if ps[-1]==(26,32):ps=ps[:-1]+[(27,ps[-2][1]),(27,32)]
  if c['net']=='SN_BUS':
   if ps[0]==(23,37):ps[0]=(24,37)
   if ps[-1]==(23,37):ps[-1]=(24,37)
  if c['net']=='UART_RX':
   if ps[0]==(28,36):ps=[(29,36)]+ps
   if ps[-1]==(28,36):ps=ps+[(29,36)]
  ps=[q for i,q in enumerate(ps) if i==0 or q!=ps[i-1]]
  if len(ps)>1:c['path']=[hole(q) for q in ps];cs.append(c)
 cs.append(dict(id='RXGND_LINK',net='GND',kind='bare',side='bottom',path=['Z37','AA37'],gauge='AWG26',locked=True,branch_id='RECEIVER_RETURN',branch_ids=['RECEIVER_RETURN','LOGIC_3V3']))
 cs.append(dict(id='RX3V3_TAP',net='+3V3',kind='bare',side='bottom',path=['AD38','AE38'],gauge='AWG26',locked=True,branch_id='LOGIC_3V3',branch_ids=['LOGIC_3V3']))
 pp=b.project(placement=pl,wiring=dict(schema_version=1,conductors=cs));r=R(pp);r.cs=cs
 for c in pp.conductors:
  for xy in c['contacts']:r.used[xy].add((c['net'],c.get('branch_id','SIGNAL')))
 r.add('SN_RX_IN',[(24,34),(25,34),(25,35),(26,35)],'QUIET_SN_RX_IN',gauge='AWG26')
 r.connect('SN_RX_IN','U207.2',['R205.1'],'QUIET_SN_RX_IN')
 r.connect('SN_PU','R205.2',['D206.1'],'QUIET_SN_PU')
 w=dict(schema_version=1,conductors=r.cs);rep=verify(b.project(placement=pl,wiring=w))
 print(rep['metrics']['comparison_tuple'])
 print([(i['code'],i['detail']) for i in rep['issues'] if i['severity']=='error' and i.get('status')!='UNCHECKED'][:8])
 assert rep['metrics']['ranking_pass']
 save_json(b.H/'placement.json',pl);save_json(b.H/'wiring.json',w)
if __name__=='__main__':main()
