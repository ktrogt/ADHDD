"""Round-2 best strict-F3 counterexample. Shared inputs remain immutable."""
import sys,json,copy,hashlib,shutil
from pathlib import Path
sys.dont_write_bytecode=True
import build
HERE=build.HERE;BASE=build.BASE
from model import Project,save_json,load_json,point,hole
from verify import placement_drc,extract,wiring_drc,verify,summary

if __name__=='__main__':
    for src,dst in [('board.json','board.json'),('design_rules_v0.2.json','design_rules.json'),('footprints_ub.json','footprints_ub.json'),('netlist_ub.csv','netlist.csv')]:shutil.copyfile(BASE/src,HERE/dst)
    p=build.placement();p=build.seed_wiring(p)
    pl=copy.deepcopy(p.placement)
    for ch,y in [(4,0),(3,11),(2,22),(1,33)]:
        for prefix,n in [('U',300+10*ch),('C',301+10*ch),('C',302+10*ch),('J',303+10*ch),('TP',470+ch)]:
            ref=f'{prefix}{n}';x,yy=point(pl['parts'][ref]['hole']);pl['parts'][ref]['hole']=hole((x+1,yy))
        pl['parts'][f'TP{470+ch}']['hole']=hole((51,y+6) if ch==1 else (49,y+8))
    pl['parts']['C341']['hole']=hole((40,0))
    pl.update(candidate='L3 round 2',rules_version='v0.2',status='strict F3 geometry infeasible; best complete counterexample')
    w=p.wire_data();cc=w['conductors'];by={c['id']:c for c in cc}
    for c in cc:
        if c['id'].startswith('CH'):
            c['path']=[hole((point(z)[0]+1,point(z)[1])) for z in c['path']]
    by['CH4_BULK_V']['path']=[hole((40,0)),hole((49,0))]
    by['CH4_BULK_G']['path']=[hole(z) for z in [(40,2),(41,2),(41,1),(47,1)]]
    for ch,y in [(4,0),(3,11),(2,22),(1,33)]:
        by[f'CH{ch}_CS']['path']=[hole((49,y+6)),hole((51,y+6) if ch==1 else (49,y+8))]
        by[f'VREF_CH{ch}']['path'][-1]=hole((44,y+6))
        by[f'FAULT_CH{ch}']['path']=[hole(z) for z in [(49,y+5),(45,y+5),(15,20)]]
    by['G_POWER_TRUNK']['path']=[hole(z) for z in [(47,1),(47,34)]]
    by['G_POWER_FEED']['path'][-1]=hole((47,8))
    by['V_POWER_TRUNK']['path']=[hole(z) for z in [(48,0),(48,33)]]
    by['V_TRUNK_LINK']['path'][-1]=hole((48,0))
    for name,path in [('REG_CIN_G',[(6,12),(12,12)]),('REG_COUT_G',[(18,12),(12,12)])]:
        by[name].update(kind='jumper',type='insulated copper',path=[hole(z) for z in path])
    save_json(HERE/'placement.json',pl);save_json(HERE/'wiring.json',w);save_json(HERE/'r2_seed.json',w)
    save_json(HERE/'input_hashes.json',{s:hashlib.sha256((BASE/s).read_bytes()).hexdigest() for s in ['board.json','footprints_ub.json','netlist_ub.csv','design_rules_v0.2.json','parts_fit.csv']})
    p=Project(HERE,board=load_json(BASE/'board.json'))
    print('core placement errors',[i for i in placement_drc(p) if i['severity']=='error'])
    ex=extract(p);print('seed wiring issues',ex[0]+wiring_drc(p,ex[3]))
