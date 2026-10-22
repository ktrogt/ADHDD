"""Compare orders after locking the paired power distribution and quiet returns."""
import sys,json,random,contextlib,io,itertools
from pathlib import Path
sys.dont_write_bytecode=True
import build as b,route_local
from model import Project,save_json,point,hole
from verify import verify
H=Path(__file__).resolve().parent
base=json.loads((H/'placement.json').read_text(encoding='utf-8'))
save_json(H/'placement.paired.json',base)
positions=[(17,7),(34,7),(17,32),(34,32)]
current=[positions.index(point(base['parts']['U'+str(310+10*k)]['hole'])) for k in range(4)]
rng=random.Random(1907);records=[];best=None
for it in range(56):
    pl=json.loads(json.dumps(base))
    perm=current[:] if it<24 else rng.sample(range(4),4)
    for k,dest in enumerate(perm):
        src=positions[current[k]];target=positions[dest];dx,dy=target[0]-src[0],target[1]-src[1]
        for ref in ('U'+str(310+10*k),'C'+str(311+10*k),'C'+str(312+10*k),'J'+str(313+10*k),'TP'+str(471+k)):
            x,y=point(pl['parts'][ref]['hole']);pl['parts'][ref]['hole']=hole((x+dx,y+dy))
    save_json(H/'placement.json',pl)
    order=rng.sample(range(8),8)
    if it==0:order=[2,7,0,1,6,5,4,3]
    mode=('paired-base' if it==1 else 'paired-controls' if it%3==0 else 'paired-inputs')+':'+','.join(map(str,order))
    with contextlib.redirect_stdout(io.StringIO()):route_local.build(mode)
    p=Project(H);report=verify(p);status={r['id']:r['status'] for r in report['rule_checks']}
    hardfail=[r['id'] for r in b.RULES['rules'] if r['severity']=='hard' and status[r['id']]=='FAIL']
    bends=sum(max(0,len(c['xy'])-2) for c in p.conductors if c['kind']=='bare')
    rec=dict(variant='F2_paired',permutation=perm,mode=mode,hardfail=hardfail,jumpers=report['metrics']['jumpers'],bare_bends=bends,mm=report['metrics']['total_wire_mm'],score=report['metrics']['score'])
    records.append(rec);rank=(len(hardfail),rec['jumpers'],bends,rec['mm'])
    if best is None or rank<best:
        best=rank;save_json(H/'placement.paired-best.json',pl);save_json(H/'wiring.paired-best.json',p.wire_data());save_json(H/'best_paired.json',rec)
        print('BEST',json.dumps(rec),flush=True)
    if it%8==0:print('iteration',it,'best',best,flush=True)
save_json(H/'paired_search.json',dict(records=records))
save_json(H/'placement.json',json.loads((H/'placement.paired-best.json').read_text(encoding='utf-8')))
save_json(H/'wiring.json',json.loads((H/'wiring.paired-best.json').read_text(encoding='utf-8')))
