"""Safe local cleanup: values, collinear vertices, duplicate copper and pieces."""
import sys,copy
from pathlib import Path
sys.dont_write_bytecode=True
import build
from model import Project,save_json,load_json,point,hole
from verify import verify,summary
HERE=build.HERE

def straight(path):
    result=[]
    for text in path:
        q=point(text)
        while len(result)>=2:
            a,b=result[-2:];u=(b[0]-a[0],b[1]-a[1]);v=(q[0]-b[0],q[1]-b[1])
            if u[0]*v[1]-u[1]*v[0] or u[0]*v[0]+u[1]*v[1]<=0:break
            result.pop()
        result.append(q)
    return [hole(z) for z in result]

if __name__=='__main__':
    p=Project(HERE)
    values=build.part_values()
    pl=copy.deepcopy(p.placement)
    for k,v in pl['parts'].items():v['value']=values[k]
    for ch,y in [(4,0),(3,11),(2,22)]:pl['parts'][f'TP{470+ch}']['hole']=hole((48,y+8))
    save_json(HERE/'placement.json',pl)
    w=p.wire_data();cs=w['conductors'];by={c['id']:c for c in cs}
    for ch,y in [(4,0),(3,11),(2,22)]:by[f'CH{ch}_CS']['path']=[hole((48,y+6)),hole((48,y+8))]
    for ch in range(1,5):
        a=by[f'CH{ch}_VIN'];b=by[f'CH{ch}_BYPASS_V']
        a['path']=[a['path'][0],b['path'][0]]
        cs.remove(b)
    by['REG_COUT_V']['path']=by['REG_COUT_V']['path'][:-1]
    by['REG_COUT_G']['path']=by['REG_COUT_G']['path'][:-1]
    by['SLEEP_STOP']['path']=[by['SLEEP_STOP']['path'][0],by['SLEEP_SENSE']['path'][-1]]
    cs.remove(by['SLEEP_SENSE'])
    for c in cs:c['path']=straight(c['path'])
    q=Project(HERE,wiring=w);r=verify(q)
    if not r['lvs_pass']:raise ValueError('cleanup failed LVS')
    save_json(HERE/'wiring.json',w)
    save_json(HERE/'out/cleanup.json',{'before_pieces':len(p.conductors),'after_pieces':len(q.conductors),
        'before_length_mm':sum(c['length_mm'] for c in p.conductors),
        'after_length_mm':sum(c['length_mm'] for c in q.conductors),
        'scope':'same contact graph: four channel feed/bypass wire merges, sleep merge, two duplicate legs removed, collinear vertices removed'})
    print(summary(r))
