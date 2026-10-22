"""Re-run shared CLI checks for the final L4 inputs (read-only shared inputs)."""
from build import *
import subprocess, hashlib
def main():
    out=HERE/'out';out.mkdir(exist_ok=True)
    commands=['verify','render','wirelist','continuity']
    results=[]
    for cmd in commands:
        argv=[sys.executable,'-X','utf8',str(BASE/'tools/ub.py'),cmd,'--project',str(HERE),'--board',str(BASE/'board.json'),'--rules',str(BASE/'design_rules_v0.2.json'),'--out',str(out)]
        r=subprocess.run(argv,capture_output=True,encoding='utf-8',cwd=BASE.parent)
        log=(r.stdout+r.stderr).replace(str(BASE.parent)+'\\','').replace(str(BASE.parent)+'/', '')
        (out/f'{cmd}.log').write_text(log,encoding='utf-8')
        public_args=[a.replace(str(BASE.parent)+'\\','').replace(str(BASE.parent)+'/', '') for a in argv[3:]]
        results.append(dict(command=cmd,argv=public_args,returncode=r.returncode))
        print(cmd,'exit',r.returncode, r.stdout.splitlines()[0] if r.stdout else r.stderr,flush=True)
    inputs={}
    for name in ['BRIEF.md','board.json','footprints_ub.json','netlist_ub.csv','parts_fit.csv','design_rules_v0.2.json','tools/ub.py','tools/model.py','tools/router.py','tools/t7_rules.py','tools/scoring.py','tools/verify.py']:
        inputs[name]=hashlib.sha256((BASE/name).read_bytes()).hexdigest()
    local={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['placement.json','wiring.json','routing_config.json','board.json','footprints_ub.json','netlist.csv','design_rules.json']}
    save_json(HERE/'input_manifest.json',dict(schema_version=1,date='2026-10-22',candidate='L4',shared_sha256=inputs,local_sha256=local,commands=results,shared_files_modified_by_this_task=False))
if __name__=='__main__':main()
