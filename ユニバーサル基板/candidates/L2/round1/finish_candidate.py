"""Candidate-only cleanup, value annotation and physical wire-branch manifest."""
import sys,json,csv,math,copy
from pathlib import Path
from collections import defaultdict
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'tools'))
from model import Project,save_json,hole,point,path_points,compress
from verify import verify
from audit_local import radius

def run():
    p=Project(H);before=verify(p);w=p.wire_data();save_json(H/'wiring.before_cleanup.json',w)
    # Correct component values are from the frozen BOM; adopted substitutions
    # remain those explicitly supplied by the approved perfboard footprint input.
    with (R.parent/'基板/parts.csv').open(encoding='utf-8-sig',newline='') as f:parts={r['ref']:r for r in csv.DictReader(f)}
    pl=p.placement
    vals=[]
    for ref,a in pl['parts'].items():
        value=parts[ref]['value']
        if ref=='J101':value='DC jack DIP kit 105148'
        elif ref=='D103':value='MBR3045FCT; A2 unused'
        elif ref=='U201':value='Raspberry Pi Pico + sockets'
        elif ref=='U207':value='74AHC1G125 / DIP6 carrier'
        elif ref.startswith('U3'):value=f'HDD{(int(ref[1:])-300)//10} DRV8874 + sockets'
        elif ref.startswith('J3'):value=f'HDD{(int(ref[1:])-303)//10} XH3 outer pins 1/3'
        elif ref=='J104':value='POWER: VIN_PROT / VM'
        elif ref=='J213':value='STOP: ARM_SW / SLEEP'
        elif ref.startswith('TP'):value='1-pin probe: '+p.parts[ref].pins[0].net
        a['value']=value
        vals.append(dict(ref=ref,value=value,approved_bom_value=parts[ref]['value'],adopted_footprint=a['footprint'],hole=a['hole'],rotation=a['rotation']))
    save_json(H/'placement.json',pl)
    # Attribute individual channel segments separately from the 2.6A common
    # trunks. Keep star membership as an additional, independent annotation.
    for c in w['conductors']:
        old=c.get('branch_id','UNASSIGNED')
        c.setdefault('branch_id','PICO_5V' if c['net'] in {'+5V','VSYS'} else 'LOGIC_3V3' if c['net']=='+3V3' else 'SIGNAL_'+c['net'])
        if old=='POWER_RETURN':c['star_branch_id']='POWER_RETURN';c['branch_id']='POWER_RETURN_TRUNK'
        if old=='LOGIC_FEED':c['star_branch_id']='LOGIC_RETURN';c['branch_id']='LOGIC_RETURN'
        if c['gauge']=='0.6mm' and c['net'] in {'VM','GND'}:
            xy=[point(q) for q in c['path']]
            u=min((q.ref for q in p.pins.values() if q.ref.startswith('U3')),key=lambda ref:min(abs(a[0]-b.xy[0])+abs(a[1]-b.xy[1]) for a in xy for b in p.parts[ref].pins if b.net==c['net']))
            c['branch_id']='DRIVER_CH'+str((int(u[1:])-300)//10)
        c['branch_ids']=[c['branch_id']]
        if c['net']=='+3V3' or (c['net']=='GND' and old in {'VREF_RETURN','RECEIVER_RETURN','CONTROL_RETURN'}):c['branch_ids'].append('LOGIC_3V3')
    # Remove duplicate physical bare edges. Thick common trunks retain ownership.
    owned=set();runs={}
    for i in sorted(range(len(w['conductors'])),key=lambda i:(-radius(w['conductors'][i]['gauge']),i)):
        c=w['conductors'][i]
        if c['kind']!='bare':runs[i]=[c];continue
        ps=path_points([point(q) for q in c['path']]);chunks=[];chunk=[]
        for a,b in zip(ps,ps[1:]):
            edge=c['net'],*sorted((a,b))
            if edge in owned:
                if chunk:chunks.append(chunk);chunk=[]
            else:
                owned.add(edge)
                if not chunk:chunk=[a,b]
                else:chunk.append(b)
        if chunk:chunks.append(chunk)
        runs[i]=[]
        for j,chunk in enumerate(chunks):
            v=copy.deepcopy(c);v['path']=[hole(q) for q in compress(chunk)];v['source_ids']=[c['id']];runs[i].append(v)
    wires=[c for i in range(len(w['conductors'])) for c in runs[i]]
    # Merge only when no additional bend is introduced and no loop is created.
    changed=True
    while changed:
        changed=False
        for i,a in enumerate(wires):
            if a['kind']!='bare':continue
            aa=path_points([point(q) for q in a['path']])
            for j in range(i+1,len(wires)):
                b=wires[j]
                if any(a.get(k)!=b.get(k) for k in ('kind','net','gauge','side','branch_id')):continue
                bb=path_points([point(q) for q in b['path']]);common=set(aa)&set(bb)
                if len(common)!=1:continue
                q=next(iter(common))
                if q not in (aa[0],aa[-1]) or q not in (bb[0],bb[-1]):continue
                u=aa if aa[-1]==q else aa[::-1];v=bb if bb[0]==q else bb[::-1]
                da=(u[-1][0]-u[-2][0],u[-1][1]-u[-2][1]);db=(v[1][0]-v[0][0],v[1][1]-v[0][1])
                if da!=db:continue
                a['path']=[hole(q0) for q0 in compress(u+v[1:])];a['source_ids']=a.get('source_ids',[a['id']])+b.get('source_ids',[b['id']]);wires.pop(j);changed=True;break
            if changed:break
    for i,c in enumerate(wires,1):c['source_ids']=c.get('source_ids',[c['id']]);c['id']=f'L2W{i:03d}'
    save_json(H/'wiring.json',dict(schema_version=1,conductors=wires))
    p=Project(H);after=verify(p)
    assert before['lvs_pass'] and after['lvs_pass']
    oldstatus={r['id']:r['status'] for r in before['rule_checks']};newstatus={r['id']:r['status'] for r in after['rule_checks']}
    assert all(oldstatus[r['id']]==newstatus[r['id']] for r in p.rules['rules'] if r['severity']=='hard')
    out=H/'out';out.mkdir(exist_ok=True)
    with (out/'part_values.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(vals[0]));writer.writeheader();writer.writerows(vals)
    # Build-support plan: pin junctions, bare-wire junctions/corners/endpoints,
    # and at most eight pitches between support joints on an exposed wire.
    contacts=defaultdict(set)
    for c in p.conductors:
        for q in c['contacts']:contacts[q].add(c['id'])
    pins={q.xy for q in p.pins.values()};rows=[];anchors=set(pins)|set(p.reserved_pads)
    for c in p.conductors:
        ps=c['contacts'];must={0,len(ps)-1}
        if c['kind']=='bare':
            must|={i for i,q in enumerate(ps) if q in pins or len(contacts[q])>1}
            must|={i for i in range(1,len(ps)-1) if (ps[i][0]-ps[i-1][0],ps[i][1]-ps[i-1][1])!=(ps[i+1][0]-ps[i][0],ps[i+1][1]-ps[i][1])}
            for a,b in zip(sorted(must),sorted(must)[1:]):must.update(range(a+8,b,8))
        for i in sorted(must):
            q=ps[i];anchors.add(q);rows.append(dict(wire=c['id'],net=c['net'],hole=hole(q),kind=c['kind'],reason='pin' if q in pins else 'junction' if len(contacts[q])>1 else 'endpoint/bend/support'))
    with (out/'support.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    save_json(out/'cleanup.json',dict(before=before['metrics'],after=after['metrics'],recommended_unique_solder_stations=len(anchors),physical_expected_pins=len(p.pins),extra_reserved_leads=len(p.reserved_pads),wire_pieces=len(p.conductors),support_rows=len(rows),note='No netlist/rule/board/footprint change. Only values, branch metadata, duplicate bare edges and collinear wire pieces changed.'))
    print('CLEANUP',len(w['conductors']),'->',len(wires),'wire mm',before['metrics']['total_wire_mm'],'->',after['metrics']['total_wire_mm'],'solder stations',len(anchors))

if __name__=='__main__':run()
