"""Finalize L1 locally: simplify redundant bare pieces, run the shared CLI,
improve SVG labels, and export supplementary T7/build metrics.
"""
from common import *
from model import path_points,compress
from verify import verify,net_graph,shortest
from collections import Counter,defaultdict
import subprocess,hashlib,xml.etree.ElementTree as ET

def simplify():
    p=Project(HERE);old=p.wire_data();before=verify(p)
    result=[];seen=set();removed=0
    for orig in old['conductors']:
        c=copy.deepcopy(orig)
        if c['kind']!='bare':result.append(c);continue
        pts=path_points([point(z) for z in c['path']])
        tag=(c['net'],c.get('routing_group'),c['gauge'],c['side'])
        def edge(a,b):return tag+tuple(sorted((a,b)))
        while len(pts)>1 and edge(pts[0],pts[1]) in seen:pts.pop(0)
        while len(pts)>1 and edge(pts[-2],pts[-1]) in seen:pts.pop()
        if len(pts)<2:removed+=1;continue
        c['path']=[hole(z) for z in compress(pts)]
        for a,b in zip(pts,pts[1:]):seen.add(edge(a,b))
        result.append(c)
    # Merge only collinear joins: same length, same bare bend count, fewer pieces.
    changed=True
    while changed:
        changed=False
        for i,a in enumerate(result):
            if a['kind']!='bare' or a['net'] in {'VREF','SLEEP','FAULT','SN_BUS','SN_RX_IN','SN_PU','UART_RX','ARM','ARM_SW'} or '_IN' in a['net']:continue
            for j in range(i+1,len(result)):
                b=result[j]
                if b['kind']!='bare' or any(a.get(k)!=b.get(k) for k in ['net','side','gauge','routing_group']):continue
                pa=[point(z) for z in a['path']];pb=[point(z) for z in b['path']]
                candidate=None
                for aa,bb in [(pa,pb),(pa,list(reversed(pb))),(list(reversed(pa)),pb),(list(reversed(pa)),list(reversed(pb)))]:
                    if aa[-1]!=bb[0]:continue
                    dx1=aa[-1][0]-aa[-2][0];dy1=aa[-1][1]-aa[-2][1]
                    dx2=bb[1][0]-bb[0][0];dy2=bb[1][1]-bb[0][1]
                    if dx1*dy2==dy1*dx2 and dx1*dx2+dy1*dy2>0:
                        pp=compress(aa+bb[1:]);contact=path_points(pp)
                        if len(contact)==len(set(contact)):candidate=pp;break
                if candidate is None:continue
                a['path']=[hole(z) for z in candidate];a['branch_ids']=sorted(set(a.get('branch_ids',[])+b.get('branch_ids',[])))
                result.pop(j);removed+=1;changed=True;break
            if changed:break
    # Remove redundant end-edges of exposed loops, without weakening LVS/stars.
    def cyclic_nets(data):
        q=p.clone(wiring={'schema_version':1,'conductors':data});bad=set()
        for net in q.nets:
            g=net_graph(q,net);todo=set(g);components=0
            while todo:
                components+=1;todo-=set(shortest(g,next(iter(todo))))
            if sum(len(v) for v in g.values())//2-len(g)+components>0:bad.add(net)
        return bad
    while cyclic_nets(result):
        targets=cyclic_nets(result);accepted=False
        for i,c in enumerate(result):
            if c['kind']!='bare' or c['net'] not in targets:continue
            pts=path_points([point(z) for z in c['path']])
            for shorter in [pts[1:],pts[:-1]]:
                trial=copy.deepcopy(result)
                if len(shorter)>1:trial[i]['path']=[hole(z) for z in compress(shorter)]
                else:trial.pop(i)
                tr=verify(p.clone(wiring={'schema_version':1,'conductors':trial}))
                if tr['metrics']['comparison_tuple'][:3]==[True,0,0] and len(cyclic_nets(trial))<len(targets):
                    result=trial;accepted=True;break
            if accepted:break
        if not accepted:raise ValueError('Exposed wire cycle requires manual pruning')
    final={k:v for k,v in p.wiring.items() if k!='conductors'};final['conductors']=result
    after=verify(p.clone(wiring=final))
    assert after['lvs_pass'] and before['lvs_pass']
    assert Counter((z['id'],z['status']) for z in before['rule_checks'])==Counter((z['id'],z['status']) for z in after['rule_checks'])
    assert after['metrics']['lexicographic_sort_key']<=before['metrics']['lexicographic_sort_key']
    save_json(HERE/'wiring.before_polish.json',p.wiring)
    save_json(HERE/'wiring.json',final)
    save_json(HERE/'out'/'wire_simplification.json',{'pieces_before':len(old['conductors']),'pieces_after':len(result),'pieces_saved':removed,'wire_mm_before':before['metrics']['total_wire_mm'],'wire_mm_after':after['metrics']['total_wire_mm'],'LVS_before_and_after':'PASS','hard_status_unchanged':True})

def cli():
    records=[]
    for command in ['verify','render','wirelist','continuity']:
        args=[sys.executable,'-X','utf8',str(SHARED/'tools'/'ub.py'),command,'--project',str(HERE.relative_to(SHARED)),'--board',str(SHARED/'board.json')]
        cp=subprocess.run(args,cwd=SHARED,capture_output=True,text=True,encoding='utf8',env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'})
        (HERE/'out'/f'{command}.log').write_text(cp.stdout+cp.stderr,encoding='utf8')
        records.append({'command':command,'exit_code':cp.returncode})
        print(command,cp.returncode,cp.stdout.splitlines()[0] if cp.stdout else cp.stderr)
        assert cp.returncode==(1 if command=='verify' else 0)
    save_json(HERE/'out'/'verification_commands.json',records)

def extras():
    p=Project(HERE);r=json.loads((HERE/'out'/'report.json').read_text(encoding='utf8'))
    req={z['id']:z for z in p.rules['rules']}
    statuses=Counter((req[z['id']]['severity'],z['status']) for z in r['rule_checks'])
    soft=defaultdict(float)
    for z in r['issues']:
        if z['code'].startswith('RULE:') and z['severity']=='warning' and z.get('status')!='UNCHECKED':soft[str(z.get('priority'))]+=z.get('t7_penalty',0)
    lengths=defaultdict(lambda:defaultdict(float))
    for z in p.conductors:lengths[z['gauge']][z['kind']]+=z['length_mm']
    def pin(ref,num):return next(z.xy for z in p.pins.values() if z.ref==ref and z.number==str(num))
    def length(net,a,b):return round(shortest(net_graph(p,net),a)[b],3)
    ins=[];vref=[];power=[]
    for ch,pn in [(1,4),(2,6),(3,9),(4,11)]:
        for suffix in [0,1]:ins.append({'net':f'HDD{ch}_IN{suffix+1}','mm':length(f'HDD{ch}_IN{suffix+1}',pin('U201',pn+suffix),pin(f'U{300+ch*10}',3+suffix))})
        vref.append({'channel':ch,'mm':length('VREF',pin('C211',1),pin(f'U{300+ch*10}',7))})
        power.append({'channel':ch,'VM_from_J104_mm':length('VM',pin('J104',2),pin(f'U{300+ch*10}',14)),
                      'GND13_from_J101_mm':length('GND',pin('J101',2),pin(f'U{300+ch*10}',13)),
                      'GND2_from_J101_mm':length('GND',pin('J101',2),pin(f'U{300+ch*10}',2))})
    contacts={z.xy for z in p.pins.values()}|set(p.reserved_pads)
    for z in p.conductors:contacts.update(z['contacts'])
    footprints=[z.rect for z in p.parts.values()]
    origin=p.board['grid_origin_mm'];physical=(min(z[0] for z in footprints)+origin['x'],min(z[1] for z in footprints)+origin['y'],max(z[2] for z in footprints)+origin['x'],max(z[3] for z in footprints)+origin['y'])
    physical_ok=all(z[0]+origin['x']>=0 and z[1]+origin['y']>=0 and z[2]+origin['x']<=155 and z[3]+origin['y']<=114 for z in footprints)
    cycles={}
    for net in p.nets:
        graph=net_graph(p,net);vertices=set(graph);edges=sum(len(x) for x in graph.values())//2
        # Count graph components, not relying on declared wire net connectivity.
        components=0;pending=set(vertices)
        while pending:
            components+=1;root=next(iter(pending));seen=set(shortest(graph,root));pending-=seen
        if edges-len(vertices)+components:cycles[net]=edges-len(vertices)+components
    sourcefiles=['board.json','footprints_ub.json','netlist_ub.csv','parts_fit.csv','design_rules_v0.2.json','design_rules.md','BRIEF.md']
    manifest={name:hashlib.sha256((SHARED/name).read_bytes()).hexdigest() for name in sourcefiles}
    copies={'board.json':'board.json','footprints_ub.json':'footprints_ub.json','netlist.csv':'netlist_ub.csv','design_rules.json':'design_rules_v0.2.json'}
    for local,src in copies.items():assert hashlib.sha256((HERE/local).read_bytes()).hexdigest()==manifest[src]
    def bends(c):
        vectors=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(c['xy'],c['xy'][1:])]
        return sum(a[0]*b[1]!=a[1]*b[0] or a[0]*b[0]+a[1]*b[1]<0 for a,b in zip(vectors,vectors[1:]))
    data={'hard_rule_counts':{status:statuses['hard',status] for status in ['PASS','FAIL','UNCHECKED']},
          'soft_rule_counts':{status:statuses['soft',status] for status in ['PASS','FAIL','UNCHECKED']},
          'T7_soft_score_evaluated_lower_bound':round(sum(soft.values()),6),'T7_soft_by_priority':dict(soft),
          'tool_generic_score':r['metrics']['score'],'tool_generic_score_note':'Use native comparison_tuple for ranking; metrics.score retains legacy UNCHECKED/error penalties.',
          'bare_pieces':sum(z['kind']=='bare' for z in p.conductors),'bare_straight_segments':sum(1+bends(z) for z in p.conductors if z['kind']=='bare'),
          'bare_bends':sum(bends(z) for z in p.conductors if z['kind']=='bare'),'jumper_bends':sum(bends(z) for z in p.conductors if z['kind']=='jumper'),
          'wire_by_gauge_mm':{k:{a:round(b,3) for a,b in v.items()} for k,v in lengths.items()},
          'IN_lines':ins,'longest_IN_line':max(ins,key=lambda z:z['mm']),'VREF_branches':vref,'power_paths':power,
          'solder_sites_conservative_all_contacted_pads':len(contacts),'component_and_adapter_tails':len(p.pins)+len(p.reserved_pads),
          'wire_end_terminations':2*len(p.conductors),'wire_pieces':len(p.conductors),
          'body_bbox_on_nominal_actual_board_mm':[round(v,3) for v in physical],'bodies_fit_nominal_155x114_board':physical_ok,
          'physical_origin_is_derived_not_metrologically_verified':True,'wire_graph_cycle_ranks_nonzero':cycles,
          'input_SHA256':manifest,'local_approved_copies_byte_identical':True}
    save_json(HERE/'out'/'metrics_extra.json',data)
    return data

if __name__=='__main__':
    (HERE/'out').mkdir(exist_ok=True)
    for src,dst in [('board.json','board.json'),('footprints_ub.json','footprints_ub.json'),('netlist_ub.csv','netlist.csv'),('design_rules_v0.2.json','design_rules.json')]:shutil.copyfile(SHARED/src,HERE/dst)
    d=json.loads((HERE/'placement.r2.json').read_text(encoding='utf8'))
    d['notes']='Round 2 F1: Pico GPIO faces drivers, USB east, receiver southeast; approved v0.2 rules. Exact stars preserved. UNCHECKED requires supervisor/build review.'
    save_json(HERE/'placement.json',d)
    shutil.copyfile(HERE/'wiring.r2.json',HERE/'wiring.json')
    simplify();cli();extras()
