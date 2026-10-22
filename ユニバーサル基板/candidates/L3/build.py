"""L3-only layout generator; approved inputs are copied verbatim, never edited."""
from pathlib import Path
import sys, json, shutil, hashlib, math, csv
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
sys.path.insert(0, str(BASE / 'tools'))
from model import Project, load_footprints, load_json, hole, point, rotate, rect_distance, save_json
from verify import placement_drc

def inputs():
    for src, dst in [('board.json','board.json'), ('footprints_ub.json','footprints_ub.json'),
                     ('netlist_ub.csv','netlist.csv'), ('design_rules.json','design_rules.json')]:
        shutil.copyfile(BASE/src,HERE/dst)
    save_json(HERE/'input_hashes.json', {s:hashlib.sha256((BASE/s).read_bytes()).hexdigest()
        for s in ['board.json','footprints_ub.json','netlist_ub.csv','design_rules.json','parts_fit.csv']})

F = load_footprints(BASE/'footprints_ub.json')
REF = F['ref_to_type']
def rect(ref,x,y,r):
    b=F['footprints'][REF[ref]]['body_mm']
    pts=[rotate((a,c),r) for a in [b['x'],b['x']+b['width']] for c in [b['y'],b['y']+b['height']]]
    return (x*2.54+min(a for a,b in pts),y*2.54+min(b for a,b in pts),x*2.54+max(a for a,b in pts),y*2.54+max(b for a,b in pts))
def pin(ref,n,x,y,r):
    p=next(p for p in F['footprints'][REF[ref]]['pins'] if p['number']==str(n))
    dx,dy=rotate((p['dx'],p['dy']),r)
    return x+dx,y+dy
def man(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])

def search_tile():
    # Interior representative; the first/last tiles are checked separately.
    x,y=43,11
    fixed=[('U310',x,y,0),('C312',x+7,y,90),('J313',x+8,y+2,90)]
    out=[]
    for r in [0,90,180,270]:
        for cx in range(x-5,55):
            for cy in range(y-7,y+8):
                ps=[pin('C311',n,cx,cy,r) for n in (1,2)]
                ds=[man(ps[0],(x+5,y)),man(ps[1],(x+5,y+1))]
                if max(ds)>6:continue
                cr=rect('C311',cx,cy,r)
                if min(cr[:2]) < -1.27 or cr[2]>54.5*2.54 or cr[3]>39.5*2.54:continue
                if any(rect_distance(cr,rect(a,b,c,d)) < (2.54 if a.startswith('U') else 1.016)-1e-7 for a,b,c,d in fixed):continue
                if any(rect_distance(cr,rect('U310',x,y+dy,0))<2.54-1e-7 for dy in [-11,11]):continue
                out.append((sum(ds),cx-x,cy-y,r,ds))
    print('BULK OPTIONS',sorted(out))

def tile_options(x=42,y=11,show=True):
    drs=[rect('U310',x,y+dy,0) for dy in [-11,0,11] if 0<=y+dy<=33]
    def opts(ref,pairs,limit,gap):
        found=[]
        for r in [0,90,180,270]:
            for cx in range(max(0,x-8),55):
                for cy in range(max(0,y-8),min(40,y+10)):
                    ds=[man(pin(ref,a,cx,cy,r),pin('U310',b,x,y,0)) for a,b in pairs]
                    if max(ds)>limit:continue
                    rr=rect(ref,cx,cy,r)
                    if rr[0]<-1.27 or rr[1]<-1.27 or rr[2]>54.5*2.54 or rr[3]>39.5*2.54:continue
                    if any(rect_distance(rr,z)<gap-1e-7 for z in drs):continue
                    found.append((sum(ds),cx,cy,r,rr))
        return sorted(found)
    caps=opts('C311',[(1,14),(2,13)],6,2.54)
    bp=opts('C312',[(1,14),(2,13)],2,1.016)
    conn=opts('J313',[(1,12),(2,11)],4,1.016)
    if x==42 and y==11: print('OPTIONS', 'bulk',[(a,b-x,c-y,d) for a,b,c,d,_ in caps], 'bypass',[(a,b-x,c-y,d) for a,b,c,d,_ in bp], 'coil',[(a,b-x,c-y,d) for a,b,c,d,_ in conn])
    result=[]
    for a in caps:
        for b in bp:
            if rect_distance(a[4],b[4])<1.016-1e-7:continue
            for c in conn:
                if min(rect_distance(a[4],c[4]),rect_distance(b[4],c[4]))<1.016-1e-7:continue
                result.append((a[0]+b[0]+c[0],a[:4],b[:4],c[:4]))
    if show:print('TILE',x,y,'independent',len(caps),len(bp),len(conn),'results',result[:10])
    return result

def minimum_pair(a,b,pairs,gap=1.016):
    results=[]
    ar=rect(a,20,20,0)
    ap={pin(a,p['number'],20,20,0) for p in F['footprints'][REF[a]]['pins']}
    for r in [0,90,180,270]:
        for x in range(7,34):
            for y in range(7,34):
                if rect_distance(ar,rect(b,x,y,r))<gap-1e-8:continue
                bp={pin(b,p['number'],x,y,r) for p in F['footprints'][REF[b]]['pins']}
                if ap & bp:continue
                pp=[man(pin(a,pa,20,20,0),pin(b,pb,x,y,r)) for pa,pb in pairs]
                results.append((max(pp),sum(pp),x-20,y-20,r,pp))
    return sorted(results)

def infeasibility():
    proof={}
    for name,a,b,pairs,gap,bound in [
        ('P02 TVS to entry bulk','C106','D105',[(1,1),(2,2)],1.016,3),
        ('P13 input cap / H07','U107','C108',[(1,1),(2,2)],2.54,4),
        ('P13 output cap / H07','U107','C109',[(3,1),(2,2)],2.54,4),
        ('P15 buffer bypass','U207','C208',[(5,1),(3,2)],1.016,2),
        ('V02 lower divider','C211','R210',[(1,1),(2,2)],1.016,2),
    ]:
        rows=minimum_pair(a,b,pairs,gap)
        proof[name]={'fixed_part':a,'moving_part':b,'pairs':pairs,'body_gap_mm':gap,'required_max_holes':bound,'minimum_max_holes':rows[0][0],'best_examples':rows[:8]}
        print(name,rows[:3])
    proof['F3 vertical packing']={'driver_body_height_mm':18.38,'required_gap_mm':7.62,'minimum_integer_origin_pitch_holes':11,'minimum_occupied_height_mm':102.2,'tool_board_height_mm':101.6,'actual_board_height_mm':114.0}
    save_json(HERE/'infeasibility.json',proof)

def part_values():
    values={r['ref']:r['original_part'] for r in csv.DictReader((BASE/'parts_fit.csv').open(encoding='utf-8-sig',newline=''))}
    values.update({'J101':'105148 DC jack DIP kit','F102':'MF-R300 3 A',
        'D103':'MBR3045FCT, one anode only','J104':'POWER switch header',
        'C106':'470 uF / 35 V','C108':'100 uF / 35 V','C109':'100 uF / 35 V',
        'U201':'Raspberry Pi Pico, 2 x 20 socket','J202':'SmartNet XH2 IN','J203':'SmartNet XH2 THRU',
        'U207':'74AHC1G125 on 115520 DIP6','C208':'100 nF','R204':'1 kohm','R205':'10 kohm',
        'R209':'47 kohm','R210':'4.7 kohm initial','C211':'220 nF',
        'R212':'1 kohm','R214':'10 kohm','R215':'10 kohm','J213':'STOP switch header'})
    for ch in range(1,5):
        t=300+10*ch
        values[f'U{t}']=f'HDD{ch} Pololu4035, 2 x 7 socket'
        values[f'C{t+1}']='470 uF / 35 V'
        values[f'C{t+2}']='100 nF'
        values[f'J{t+3}']=f'HDD{ch} XH3, centre NC'
    for row in csv.DictReader((BASE/'netlist_ub.csv').open(encoding='utf-8-sig',newline='')):
        if row['ref'].startswith('TP'):values[row['ref']]='Probe pin: '+row['net']
    return values

def placement():
    p={};values=part_values()
    def put(ref,x,y,r=0):
        p[ref]={'footprint':REF[ref],'hole':hole((x,y)),'rotation':r,'locked':True,'value':values.get(ref,ref)}
    for ref,x,y,r in [
        ('J101',29,5,180),('F102',15,1,0),('D103',26,14,0),('J104',35,0,90),
        ('D105',34,1,180),('C106',33,5,180),('U107',11,12,0),
        ('C108',5,12,0),('C109',18,11,90),('D110',5,37,270),
        ('U201',14,38,180),('J202',19,38,0),('J203',23,38,0),
        ('U207',20,33,0),('C208',21,31,180),('R204',18,36,270),
        ('R205',25,30,0),('D206',28,32,0),('C211',30,23,0),
        ('R209',25,23,0),('R210',29,21,0),('J213',1,19,0),
        ('R214',4,19,90),('R212',5,17,180),('R215',18,20,180),
        ('TP460',36,6,0),('TP461',15,7,0),('TP462',17,23,0),
        ('TP463',12,17,0),('TP464',16,25,0),('TP465',34,24,0),
        ('TP466',27,25,0),('TP467',3,25,0),('TP468',18,18,0)
    ]:put(ref,x,y,r)
    for ch,y in [(4,0),(3,11),(2,22),(1,33)]:
        t=300+10*ch
        put(f'U{t}',43,y)
        if ch==4:put(f'C{t+1}',39,1,90)
        else:put(f'C{t+1}',51,y-3,0)
        put(f'C{t+2}',50,y,90)
        put(f'J{t+3}',52,y+3,180)
        if ch==1:put(f'TP{470+ch}',50,y+6)
        else:put(f'TP{470+ch}',48,y+8)
    result={'schema_version':1,'candidate':'L3','seed_floor_plan':'F3','parts':p,
        'nodes':{'GND_ENTRY':hole((31,5)),'VM_ENTRY':hole((33,5)),
                 'GND_LOGIC':hole((12,12)),'VREF_ROOT':hole((30,23)),
                 'VREF_GND':hole((32,23))}}
    save_json(HERE/'placement.json',result)
    save_json(HERE/'wiring.json',{'schema_version':1,'conductors':[]})
    pr=Project(HERE)
    print('PLACEMENT',len(pr.parts),'pins',len(pr.pins))
    print('DRC',placement_drc(pr))
    return pr

def seed_wiring(p):
    from router import net_colour
    from verify import verify, extract, wiring_drc
    wires=[]
    def add(name,net,path,kind='bare',gauge='AWG22',branch=None):
        coords=[point(z) if isinstance(z,str) else z for z in path]
        wires.append(dict(id=name,net=net,kind=kind,side='bottom',path=[hole(z) for z in coords],
            gauge=gauge,type='insulated copper' if kind=='jumper' else 'tinned copper',
            colour=net_colour(net),locked=True,branch_id=branch or name))
    # Entry topology: the four return branches meet only at C106 negative.
    add('G_INPUT','GND',[(29,2),(30,2),(30,5),(31,5)],gauge='1.0mm',branch='INPUT_RETURN')
    add('G_TVS','GND',[(30,1),(31,1),(31,5)],gauge='1.0mm',branch='TVS_RETURN')
    add('G_POWER_FEED','GND',[(31,5),(31,6),(32,6),(32,8),(46,8)],gauge='1.0mm',branch='POWER_RETURN_TRUNK')
    add('G_POWER_TRUNK','GND',[(46,1),(46,34)],gauge='1.0mm',branch='POWER_RETURN_TRUNK')
    add('G_LOGIC_FEED','GND',[(31,5),(12,12)],'jumper','AWG24','LOGIC_RETURN')
    add('V_ENTRY','VM',[(33,5),(33,1),(35,1)],gauge='1.0mm',branch='VM_TRUNK')
    add('V_TRUNK_LINK','VM',[(35,1),(47,0)],'jumper','AWG20','VM_TRUNK')
    add('V_POWER_TRUNK','VM',[(47,0),(47,33)],gauge='1.0mm',branch='VM_TRUNK')
    add('V_PROBE','VM',[(36,6),(36,5),(33,5)],gauge='AWG26')
    # Identical local channel power/output pattern (top bulk is offset one row).
    for ch,y in [(4,0),(3,11),(2,22),(1,33)]:
        pref=f'CH{ch}_';by=max(1,y);branch=f'DRIVER_CH{ch}'
        add(pref+'VIN','VM',[(47,y),(48,y)],branch=branch)
        if ch==4:
            add(pref+'BULK_V','VM',[(39,by),(48,y)],'jumper','AWG22',branch)
            ground=[(39,by+2),(40,by+2),(40,y+1),(46,y+1)]
            add(pref+'BULK_G','GND',ground,branch=branch)
        else:
            add(pref+'BULK_V','VM',[(51,y-3),(51,y-2),(48,y-2),(48,y)],branch=branch)
            add(pref+'BULK_G','GND',[(53,y-3),(53,y+1),(48,y+1)],branch=branch)
            add(pref+'LEFT_G','GND',[(43,y+1),(46,y+1)],branch=branch)
        add(pref+'GND_RIGHT','GND',[(48,y+1),(46,y+1)],'jumper','AWG22',branch)
        add(pref+'BYPASS_V','VM',[(50,y),(48,y)],branch=branch)
        add(pref+'BYPASS_G','GND',[(50,y+1),(48,y+1)],branch=branch)
        add(pref+'OUT1',f'HDD{ch}_OUT1',[(48,y+2),(52,y+2),(52,y+3)],branch=branch)
        add(pref+'OUT2',f'HDD{ch}_OUT2',[(48,y+3),(50,y+3)],branch=branch)
        if ch==1:cs_path=[(48,y+6),(50,y+6)]
        else:cs_path=[(48,y+6),(48,y+8)]
        add(pref+'CS',f'HDD{ch}_CS',cs_path,gauge='AWG26')
    # Converter: separate quiet return hub, caps are never used as motor returns.
    add('REG_VM','VM',[(33,5),(11,12)],'jumper','AWG24','REGULATOR_VM')
    add('REG_CIN_V','VM',[(5,12),(11,12)],'jumper','AWG24','REGULATOR_VM')
    add('REG_CIN_G','GND',[(6,12),(6,11),(12,11),(12,12)],gauge='AWG24',branch='REGULATOR_CAP_RETURN')
    add('REG_COUT_G','GND',[(18,12),(18,13),(12,13),(12,12)],gauge='AWG24',branch='REGULATOR_CAP_RETURN')
    add('REG_COUT_V','+5V',[(18,11),(13,11),(13,12)],gauge='AWG24',branch='PICO_5V')
    add('FIVEV_FEED','+5V',[(13,12),(13,10),(0,10),(0,33),(5,33)],gauge='AWG24',branch='PICO_5V')
    add('FIVEV_PROBE','+5V',[(13,10),(15,10),(15,7)],gauge='AWG24')
    add('VSYS_FEED','VSYS',[(5,37),(7,37)],gauge='AWG24',branch='PICO_5V')
    # Pico ground comb, independent of the receiver/divider/control returns.
    add('PICO_RETURN_FEED','GND',[(12,12),(10,21)],'jumper','AWG24','PICO_RETURN')
    add('PICO_GND_SPINE','GND',[(10,21),(10,36)],gauge='AWG24',branch='PICO_RETURN')
    for y in [21,26,31,36]:
        add(f'PICO_GND_{y}','GND',[(7,y),(14,y)],gauge='AWG24',branch='PICO_RETURN')
    add('PICO_GND_PROBE','GND',[(14,26),(16,26),(16,25)],gauge='AWG24',branch='PICO_RETURN')
    add('GND_HUB_PROBE','GND',[(12,12),(12,17)],gauge='AWG24')
    add('CONTROL_GND','GND',[(12,12),(4,22)],'jumper','AWG24','CONTROL_RETURN')
    # Divider source: source copper is a fifth branch; four channel wires end at root.
    add('VREF_GND_FEED','GND',[(12,12),(32,23)],'jumper','AWG24','VREF_RETURN')
    add('VREF_LOWER_GND','GND',[(32,21),(32,23),(32,24),(34,24)],gauge='AWG26',branch='VREF_RETURN')
    add('VREF_SOURCE','VREF',[(30,23),(28,23),(28,25),(27,25)],gauge='AWG26',branch='VREF_SOURCE')
    add('VREF_LOWER_TOP','VREF',[(29,21),(29,23)],gauge='AWG26',branch='VREF_SOURCE')
    for ch,y in [(4,0),(3,11),(2,22),(1,33)]:
        add(f'VREF_CH{ch}','VREF',[(30,23),(43,y+6)],'jumper','AWG26',f'VREF_CH{ch}')
    # Receiver local return and bus; carrier pad 5 remains reserved/unwired.
    add('RX_GND_FEED','GND',[(12,12),(20,35)],'jumper','AWG24','RECEIVER_RETURN')
    add('RX_GND_LOCAL','GND',[(20,31),(20,33)],gauge='AWG26',branch='RECEIVER_RETURN')
    add('RX_GND_OE','GND',[(20,33),(20,35)],'jumper','AWG26','RECEIVER_RETURN')
    add('RX_GND_J202','GND',[(20,35),(20,38)],gauge='AWG26',branch='RECEIVER_RETURN')
    add('RX_GND_J203','GND',[(20,36),(24,36),(24,38)],gauge='AWG26',branch='RECEIVER_RETURN')
    add('RX_BYPASS_V','+3V3',[(21,31),(23,33)],'jumper','AWG26','LOGIC_3V3')
    add('SN_BUS','SN_BUS',[(19,38),(19,39),(23,39)],gauge='AWG26')
    add('SN_J203','SN_BUS',[(23,38),(23,39)],gauge='AWG26')
    add('SN_SERIES','SN_BUS',[(19,38),(19,36),(18,36)],gauge='AWG26')
    add('RX_INPUT','SN_RX_IN',[(25,30),(25,32),(21,32),(21,34),(20,34)],gauge='AWG26')
    add('RX_SERIES','SN_RX_IN',[(18,33),(18,34),(20,34)],gauge='AWG26')
    add('RX_PULLUP','SN_PU',[(28,30),(28,32)],gauge='AWG26')
    add('UART_ESCAPE','UART_RX',[(23,35),(18,37)],'jumper','AWG26')
    add('UART_PICO','UART_RX',[(18,37),(14,37)],gauge='AWG26')
    # Stop path remains local at the west quiet edge.
    add('ARM_PICO','ARM',[(14,20),(13,20),(13,18),(5,18),(5,17)],gauge='AWG26')
    add('ARM_SW','ARM_SW',[(2,17),(1,17),(1,19)],gauge='AWG26')
    add('SLEEP_STOP','SLEEP',[(2,19),(4,19)],gauge='AWG26')
    add('SLEEP_PROBE','SLEEP',[(3,19),(3,25)],gauge='AWG26')
    add('SLEEP_SENSE','SLEEP',[(4,19),(7,19)],gauge='AWG26')
    add('FAULT_PICO','FAULT',[(15,20),(15,19),(14,19)],gauge='AWG26')
    add('FAULT_PROBE','FAULT',[(18,18),(15,18),(15,19)],gauge='AWG26')
    for ch,y in [(4,0),(3,11),(2,22),(1,33)]:
        add(f'FAULT_CH{ch}','FAULT',[(48,y+5),(44,y+5),(15,20)],'jumper','AWG26')
    result={'schema_version':1,'conductors':wires,'notes':'Locked F3 power, GND branches and VREF star. No approved rules altered.'}
    save_json(HERE/'wiring.seed.json',result)
    save_json(HERE/'wiring.json',result)
    pp=p.clone(wiring=result)
    issues=extract(pp)[0]+wiring_drc(pp,extract(pp)[3])
    print('SEED',len(wires),'wires; issues',issues)
    return pp

if __name__=='__main__':
    inputs()
    infeasibility()
    pr=placement()
    seed_wiring(pr)
