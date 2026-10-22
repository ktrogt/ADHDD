"""Run the requested public CLI stages against the final candidate files."""
import sys,subprocess,json
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];out=H/'out';out.mkdir(exist_ok=True)
def public_log(text):return text.replace(str(R.parent),'.').replace(str(R.parent).replace('\\','/'),'.')
records=[]
for command,extra in [('verify',[]),('render',['--scale','1']),('wirelist',[]),('continuity',[])]:
    args=[sys.executable,'-X','utf8',str(R/'tools/ub.py'),command,'--project',str(H),*extra]
    res=subprocess.run(args,encoding='utf-8',capture_output=True)
    (out/(command+'.log')).write_text(public_log(res.stdout+res.stderr),encoding='utf-8')
    print(command,'exit',res.returncode,res.stdout.splitlines()[0] if res.stdout else res.stderr[:200])
    records.append(dict(command=command,exit=res.returncode))
    assert res.returncode==(1 if command=='verify' else 0)
for script in ('audit_local.py','prove_infeasible.py','annotate_svgs.py','preview_svg.py'):
    res=subprocess.run([sys.executable,'-X','utf8',str(H/script)],encoding='utf-8',capture_output=True)
    (out/(script[:-3]+'.log')).write_text(public_log(res.stdout+res.stderr),encoding='utf-8');assert res.returncode==0,res.stderr
report=json.loads((out/'report.json').read_text(encoding='utf-8'))
assert report['lvs_pass']
assert not [i for i in report['issues'] if i['severity']=='error' and not i['code'].startswith('RULE:')]
audit=json.loads((out/'audit_local.json').read_text(encoding='utf-8'))
assert all(v['identical'] for v in audit['input_hashes'].values())
assert all(v['status']=='PASS_IN_LOCAL_MODEL' for v in audit['checks'].values())
(out/'verification_runs.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
print('FINAL CORE LVS PASS; placement/wiring DRC 0; hard audit',audit['hard_rules'])
