"""F2 channel order permutations; no pin/net remapping."""
import sys, itertools, json, random, contextlib, io
from pathlib import Path
sys.dont_write_bytecode=True
import build as b
import route_local
from model import Project,save_json,point,hole
from verify import verify
H=Path(__file__).resolve().parent
base=json.loads((H/'placement.horizontal.json').read_text(encoding='utf-8'))
bestrec=json.loads((H/'best_route.json').read_text(encoding='utf-8'))
best=(len(bestrec['hardfail']),bestrec['jumpers'],bestrec['bare_bends'],bestrec['mm'])
records=[]; rng=random.Random(522)
positions=[(17,7),(34,7),(17,32),(34,32)]
for i,perm in enumerate(itertools.permutations(range(4))):
    pl=json.loads(json.dumps(base))
    for k,dest in enumerate(perm):
        src=positions[k]; target=positions[dest]; dx,dy=target[0]-src[0],target[1]-src[1]
        for ref in ('U'+str(310+10*k),'C'+str(311+10*k),'C'+str(312+10*k),'J'+str(313+10*k),'TP'+str(471+k)):
            x,y=point(pl['parts'][ref]['hole']); pl['parts'][ref]['hole']=hole((x+dx,y+dy))
    save_json(H/'placement.json',pl)
    for j in range(3):
        order=list(range(8))
        if j==1: order.reverse()
        if j==2: rng.shuffle(order)
        mode='inputs:'+','.join(map(str,order))
        with contextlib.redirect_stdout(io.StringIO()):route_local.build(mode)
        p=Project(H); report=verify(p); statuses={r['id']:r['status'] for r in report['rule_checks']}
        hardfail=[r['id'] for r in b.RULES['rules'] if r['severity']=='hard' and statuses[r['id']]=='FAIL']
        bends=sum(max(0,len(c['xy'])-2) for c in p.conductors if c['kind']=='bare')
        rec=dict(variant='F2_horizontal_channels',permutation=perm,mode=mode,hardfail=hardfail,jumpers=report['metrics']['jumpers'],bare_bends=bends,mm=report['metrics']['total_wire_mm'],score=report['metrics']['score'])
        records.append(rec); rank=(len(hardfail),rec['jumpers'],bends,rec['mm'])
        if rank<best:
            best=rank; save_json(H/'placement.best.json',pl);save_json(H/'wiring.best.json',p.wire_data());save_json(H/'best_route.json',rec)
            print('BEST',json.dumps(rec),flush=True)
    if i%6==0:print('permutation',i,'best',best,flush=True)
save_json(H/'channel_search.json',dict(records=records))
save_json(H/'placement.json',json.loads((H/'placement.best.json').read_text(encoding='utf-8')))
save_json(H/'wiring.json',json.loads((H/'wiring.best.json').read_text(encoding='utf-8')))
