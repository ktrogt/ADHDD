"""Branch-aware L2 round-2 routing. All axes/placements remain TOP view."""
import sys,json,math,random,copy
from pathlib import Path
sys.dont_write_bytecode=True
import r2 as b
from model import Project,save_json,point,hole,rotate
from verify import verify,summary
from router import route,astar
from branch_router_r2 import R

def build(order=None,mode='signals',seed=0):
 p=b.project(wiring={'schema_version':1,'conductors':[]});r=R(p)
 for k in range(1,5):
  u=f'U{300+10*k}';x,y=p.pin_at(u+'.VM');vm='VM_TRUNK';gn='POWER_RETURN'
  def add(net,ps,branch,kind='bare',gauge='0.6mm'):r.add(net,[(x+a,y+d) for a,d in ps],branch,kind,gauge)
  bp=r.xy(f'C{301+10*k}.1')
  if bp==(x+9,y-2):
   add('VM',[(4,-2),(4,0),(5,0)],vm)
   add('VM',[(9,-2),(8,-2),(8,0),(5,0)],vm)
   add('GND',[(5,-2),(5,1)],gn,'jumper')
   add('GND',[(9,0),(9,1),(0,1)],gn)
   c=3
  else:
   add('VM',[(4,-5),(5,-5),(5,0)],vm)
   add('GND',[(4,-3),(4,1)],gn)
   add('GND',[(0,1),(7,1)],gn)
   if k==4:
    add('VM',[(5,0),(5,-1),(7,-1)],vm)
    add('GND',[(7,0),(7,1)],gn)
   else:add('VM',[(5,0),(7,0)],vm)
   c=2 if k==4 else 3
  add(f'HDD{k}_OUT1',[(5,2),(8,2),(8,c)],f'DRIVER_CH{k}') if c!=2 else add(f'HDD{k}_OUT1',[(5,2),(8,2)],f'DRIVER_CH{k}')
  if c==2:add(f'HDD{k}_OUT2',[(5,3),(6,3),(6,4),(8,4)],f'DRIVER_CH{k}')
  else:add(f'HDD{k}_OUT2',[(5,3),(6,3),(6,5),(8,5)],f'DRIVER_CH{k}')
  r.connect(f'HDD{k}_CS',f'U{300+10*k}.8',[f'TP{470+k}.1'],'CS_LOCAL')
  fx,fy=r.xy(f'U{300+10*k}.9');r.add('FAULT',[(fx,fy),(fx-2,fy)],'QUIET_FAULT')
 # Motor frame: return inside the carrier socket rows, feed along the south
 # bulk-capacitor row. Short insulated links cross the two-pitch power taps.
 r.add('GND',[(46,6),(46,17)],'POWER_RETURN','jumper','1.0mm')
 r.add('GND',[(46,17),(46,30)],'POWER_RETURN','jumper','1.0mm')
 r.add('GND',[(46,30),(37,30)],'POWER_RETURN',gauge='1.0mm')
 r.add('GND',[(37,30),(35,30)],'POWER_RETURN','jumper','0.6mm')
 r.add('GND',[(16,30),(18,30)],'POWER_RETURN','jumper','0.6mm')
 r.add('GND',[(18,30),(35,30)],'POWER_RETURN',gauge='1.0mm')
 r.add('GND',[(5,7),(5,8),(30,8),(30,13),(46,13)],'POWER_RETURN','jumper','1.0mm')
 r.add('VM',[(16,28),(35,28)],'VM_TRUNK',gauge='1.0mm')
 r.add('VM',[(49,5),(49,16)],'VM_TRUNK','jumper','1.0mm')
 # Local six-pitch regulator capacitor connections avoid dependence on later buses.
 for cap,pin in [('C108','1'),('C109','3')]:
  net='VM' if cap=='C108' else '+5V';a=r.xy(cap+'.1');z=r.xy('U107.'+pin)
  r.add(net,[a,(z[0],a[1]),z],'REGULATOR_VM' if cap=='C108' else 'PICO_5V',gauge='AWG24')
  ga,gz=r.xy(cap+'.2'),r.xy('U107.2')
  r.add('GND',[ga,gz],'REGULATOR_CAP_RETURN','bare' if ga[0]==gz[0] else 'jumper','AWG24')
 r.add('+5V',[(20,14),(20,15),(12,15)],'PICO_5V',gauge='AWG24')
 r.add('VSYS',[(8,15),(1,15),(1,17)],'PICO_5V',gauge='AWG24')
 r.add('+3V3',[(4,17),(4,16),(22,16),(22,17)],'LOGIC_3V3',gauge='AWG26')
 # Preserve the maximum five-pitch TVS loop before the general return tree.
 ga,gr=r.xy('D105.2'),r.xy('C106.2');va,vr=r.xy('D105.1'),r.xy('C106.1');j=r.xy('J101.2')
 r.add('GND',[ga,(ga[0],gr[1]),gr],'TVS_RETURN',gauge='1.0mm')
 r.add('VM',[va,(va[0],vr[1]),vr],'VM_TRUNK',gauge='1.0mm')
 r.add('GND',[j,(j[0],j[1]-1),(gr[0],j[1]-1),gr],'INPUT_RETURN','bare','1.0mm')
 # Hierarchical quiet returns: leave the converter's south and north free
 # grid exits for Pico and VREF respectively, with independent insulated feeds.
 r.add('GND',[(5,7),(19,7),(19,8)],'LOGIC_FEED','jumper','AWG24')
 r.add('GND',[(19,8),(19,13),(17,13),(17,17)],'PICO_RETURN','jumper','AWG24')
 r.add('GND',[(19,8),(28,8),(28,18)],'VREF_RETURN','jumper','AWG26')
 r.add('GND',[(28,18),(28,16)],'VREF_RETURN',gauge='AWG26')
 r.add('GND',[(28,18),(31,18)],'VREF_RETURN',gauge='AWG26')
 r.add('GND',[(19,2),(19,1),(15,1),(15,2)],'REGULATOR_CAP_RETURN',gauge='AWG24')
 r.add('GND',[(19,8),(25,8),(25,36)],'RECEIVER_RETURN','jumper','AWG26')
 r.add('GND',[(19,8),(52,8),(52,23)],'CONTROL_RETURN','jumper','AWG26')
 # Keep the stop header and local Pico sense connection on one short bare run.
 if p.parts['U201'].data['rotation']==180:r.add('SLEEP',[(0,22),(0,20),(3,20)],'QUIET_SLEEP_LOCAL',gauge='AWG26')
 else:r.connect('SLEEP','R214.1',['J213.2','U201.21'],'QUIET_SLEEP_LOCAL')
 # Pico GND spine inside its socket footprint, away from outward IN escapes.
 ox,oy=p.pin_at('U201.GP0');angle=p.parts['U201'].data['rotation']
 def tr(a,d):v=rotate((a,d),angle);return ox+v[0],oy+v[1]
 if angle==270:
  # Keep the interior signal escape field open. One insulated link joins the
  # two outside ground rails instead of four vertical bare partitions.
  r.add('GND',[(2,18),(17,18)],'PICO_RETURN',gauge='AWG24')
  r.add('GND',[(2,25),(17,25)],'PICO_RETURN',gauge='AWG24')
  for xx in (2,7,12,17):
   r.add('GND',[(xx,17),(xx,18)],'PICO_RETURN',gauge='AWG24')
   r.add('GND',[(xx,24),(xx,25)],'PICO_RETURN',gauge='AWG24')
  r.add('GND',[(17,18),(17,25)],'PICO_RETURN','jumper','AWG24')
 else:
  r.add('GND',[tr(3,2),tr(3,17)],'PICO_RETURN',gauge='AWG24')
  for yy in (2,7,12,17):
   r.add('GND',[tr(0,yy),tr(3,yy)],'PICO_RETURN',gauge='AWG24')
   r.add('GND',[tr(7,yy),tr(3,yy)],'PICO_RETURN',gauge='AWG24')
 # Buffer pattern: direct VCC bypass and one short insulated return.
 x,y=p.pin_at('U207./OE')
 r.add('GND',[(x,y),(x+1,y),(x+1,y+2),(x,y+2)],'RECEIVER_RETURN',gauge='AWG26')
 r.add('GND',[(x,y-2),(x,y+2)],'RECEIVER_RETURN','jumper','AWG26')
 r.add('GND',[(25,36),(25,39)],'RECEIVER_RETURN',gauge='AWG26')
 r.add('GND',[(25,39),(29,39)],'RECEIVER_RETURN','jumper','AWG26')
 r.add('+3V3',[(x+1,y-2),(x+2,y-2),(x+2,y),(x+3,y)],'LOGIC_3V3',gauge='AWG26')
 # Compact source island, keeping individual VREF branches independent.
 r.connect('VREF','C211.1',['R209.2','R210.1','TP466.1'],'VREF_SOURCE',star=True)
 r.add('ARM',[(18,24),(18,26),(22,26)],'QUIET_ARM',gauge='AWG26')
 idx=list(range(8)) if order is None else order
 rng=random.Random(seed)
 def signals():
  for i in idx:
   k,j=i//2+1,i%2+1;net=f'HDD{k}_IN{j}';qs=[q for q in p.pins.values() if q.net==net]
   r.connect(net,qs[0].xy,[qs[1].xy],'PWM')
 def quiet():
  for k in (1,2,3,4):r.connect('VREF','C211.1',[f'U{300+10*k}.7'],f'VREF_CH{k}',star=True)
  # Each long control spoke is bounded directly to its source resistor. A
  # nearest-neighbour tree can exceed the 80-hole limit at the far north tile.
  def direct(net,root,source,branch):
   a,z=r.xy(source) if isinstance(source,str) else source,r.xy(root)
   mask=r.quiet_mask(net)
   blocked={xy for xy,tags in r.used.items() if any(n!=net for n,br in tags)}|mask
   blocked-={a,z}
   path=astar(p,a,{z},blocked,.65)
   if path is None or len(path)>77:
    path=astar(p,a,{z},mask-{a,z},.65);kind='jumper'
   else:kind='bare'
   r.add(net,path,branch,kind,'AWG26')
  for k in (3,4,2,1):r.connect('SLEEP','R214.1',[f'U{300+10*k}.6'],'QUIET_SLEEP_LOCAL')
  r.connect('SLEEP','R214.1',['TP467.1'],'QUIET_SLEEP_LOCAL')
  r.connect('FAULT','R215.2',[f'U{300+10*k}.9' for k in range(1,5)]+['U201.20','TP468.1'],'QUIET_FAULT')
  qnets=[('SN_BUS','J202.1'),('SN_RX_IN','U207.2'),('SN_PU','R205.2'),('UART_RX','U207.4'),('ARM','U201.19'),('ARM_SW','R212.2')]
  if seed:rng.shuffle(qnets)
  for net,root in qnets:r.connect(net,root,[q.xy for q in p.pins.values() if q.net==net],'QUIET_'+net)
 def power():
  entry=r.xy('C106.2');logic=r.xy('U107.2')
  r.connect('GND',entry,[f'U{300+10*k}.13' for k in range(1,5)],'POWER_RETURN',star=True)
  r.connect('GND',entry,[logic],'LOGIC_FEED',star=True,gauge='AWG24')
  r.connect('GND',entry,['D105.2'],'TVS_RETURN',star=True)
  r.connect('GND',entry,['J101.2','TP463.1'],'INPUT_RETURN',star=True)
  branches=[('PICO_RETURN',[f'U201.{n}' for n in (3,8,13,18,23,28,33,38)],'AWG24'),('VREF_RETURN',['C211.2','R210.2','TP465.1'],'AWG26'),('RECEIVER_RETURN',['U207.1','U207.3','C208.2','J202.2','J203.2'],'AWG26'),('CONTROL_RETURN',['R214.2'],'AWG26'),('REGULATOR_CAP_RETURN',['C108.2','C109.2','TP464.1'],'AWG24')]
  if seed:rng.shuffle(branches)
  for branch,ends,gauge in branches:r.connect('GND',logic,ends,branch,star=True,gauge=gauge)
  r.connect('VM','C106.1',[f'U{300+10*k}.14' for k in range(1,5)],'VM_TRUNK')
  r.connect('VM','C106.1',['D105.1','J104.2','TP460.1','U107.1'],'REGULATOR_VM',gauge='AWG24')
  for net,root,ends in [('VIN_RAW','J101.1',['F102.1']),('VIN_FUSED','F102.2',['D103.2']),('VIN_PROT','D103.1',['J104.1'])]:r.connect(net,root,ends,'ENTRY_SERIES')
 stages={'signals':[signals,quiet,power],'power':[power,signals,quiet],'quiet':[quiet,signals,power],'powerquiet':[power,quiet,signals]}
 for stage in stages[mode]:stage()
 save_json(b.H/'wiring.json',dict(schema_version=1,conductors=r.cs))
 wiring=route(b.project())
 for c in wiring['conductors']:
  if not c.get('locked'):
   c['side']='bottom';c['gauge']='AWG24' if c['net'] in {'+5V','VSYS'} else 'AWG26'
 save_json(b.H/'wiring.json',wiring)
 # Repair only actual hard length failures, using short insulated links. The
 # original path is subsequently pruned if it becomes redundant.
 for attempt in range(2):
  q=b.project();report=verify(q);bad=set(report['metrics']['hard_failed_rule_ids']);added=0
  for rule in q.rules['rules']:
   if rule['id'] not in bad or rule['type']!='max_branch_length':continue
   for pair in rule['params']['pairs']:
    def xy(sel):
     if sel.startswith('$'):sel=q.rules['nodes'][sel[1:]]['anchor']
     return r.xy(sel)
    a,z=xy(pair['a']),xy(pair['b']);net=next(pin.net for pin in q.pins.values() if pin.xy==a)
    from verify import shortest,net_graph
    val=shortest(net_graph(q,net),a).get(z,float('inf'))/q.pitch
    if val<=rule['params']['max_holes']+1e-8:continue
    mask=r.quiet_mask(net)
    if net=='FAULT' and pair['b'].startswith('U3'):z=(z[0]-2,z[1])
    path=astar(q,a,{z},mask-{a,z},.6)
    if path is None:raise ValueError('length repair has no quiet path')
    wiring['conductors'].append(dict(id=f'FIX{attempt}_{added}',net=net,kind='jumper',side='bottom',path=[hole(t) for t in b.compress(path)],gauge='AWG26',type='insulated copper',locked=True,branch_id='LENGTH_REPAIR'))
    added+=1
  if not added:break
  save_json(b.H/'wiring.json',wiring)
 report=verify(b.project());print(summary(report));print('COMPARISON',report['metrics']['comparison_tuple']);print('HARD',report['metrics']['hard_failed_rule_ids'])
 return report
if __name__=='__main__':build(mode=sys.argv[1] if len(sys.argv)>1 else 'signals')
