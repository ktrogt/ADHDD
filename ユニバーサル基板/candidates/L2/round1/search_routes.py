"""Compare local routing orders, with canonical rules intact."""
import sys, contextlib, io, random, json, time
from pathlib import Path
sys.dont_write_bytecode=True
import build as b
import route_local
from model import Project, save_json
from verify import verify
from collections import Counter
HERE=Path(__file__).resolve().parent
rng=random.Random(723)
records=[]; best=None
for variant in ('horizontal','vertical'):
    pl=json.loads((HERE/f'placement.{variant}.json').read_text(encoding='utf-8'))
    save_json(HERE/'placement.json',pl)
    for it in range(24):
        order=list(range(8))
        if it==1: order.reverse()
        elif it>1: rng.shuffle(order)
        mode=('base' if it==0 else 'controls' if it%3==0 else 'inputs')+':'+','.join(map(str,order))
        with contextlib.redirect_stdout(io.StringIO()): route_local.build(mode)
        p=Project(HERE); report=verify(p)
        status={r['id']:r['status'] for r in report['rule_checks']}
        hardfail=[r['id'] for r in b.RULES['rules'] if r['severity']=='hard' and status[r['id']]=='FAIL']
        bends=sum(max(0,len(c['xy'])-2) for c in p.conductors if c['kind']=='bare')
        rec=dict(variant=variant,mode=mode,hardfail=hardfail,jumpers=report['metrics']['jumpers'],bare_bends=bends,mm=report['metrics']['total_wire_mm'],score=report['metrics']['score'])
        records.append(rec)
        rank=(len(hardfail),rec['jumpers'],bends,rec['mm'])
        if best is None or rank<best:
            best=rank; save_json(HERE/'placement.best.json',pl);save_json(HERE/'wiring.best.json',p.wire_data());save_json(HERE/'best_route.json',rec)
            print('BEST',json.dumps(rec),flush=True)
        if it%6==0: print(variant,it,'current',rank,flush=True)
save_json(HERE/'routing_search.json',dict(records=records))
save_json(HERE/'placement.json',json.loads((HERE/'placement.best.json').read_text(encoding='utf-8')))
save_json(HERE/'wiring.json',json.loads((HERE/'wiring.best.json').read_text(encoding='utf-8')))
