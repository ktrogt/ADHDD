"""Regenerate final round-2 evidence, always using the shared physical board."""
import sys,subprocess,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[1];OUT=H/'out';OUT.mkdir(exist_ok=True)
def public(s):return s.replace(str(ROOT.parent),'.')
runs=[]
for cmd,extra in [('verify',[]),('render',['--scale','1']),('wirelist',[]),('continuity',[])]:
 args=[sys.executable,'-X','utf8',str(ROOT/'tools/ub.py'),cmd,'--project',str(H),'--board',str(ROOT/'board.json'),'--rules',str(H/'design_rules.json'),*extra]
 res=subprocess.run(args,capture_output=True,encoding='utf-8');(OUT/(cmd+'.log')).write_text(public(res.stdout+res.stderr),encoding='utf-8')
 print(cmd,res.returncode,'\n'.join(res.stdout.splitlines()[:3]));runs.append(dict(command=cmd,returncode=res.returncode))
 assert res.returncode in ((0,1) if cmd=='verify' else (0,))
report=json.loads((OUT/'report.json').read_text(encoding='utf-8'))
assert report['metrics']['ranking_pass'] and not report['metrics']['hard_failed_rule_ids']
for script in ('audit_local.py','r2_visual.py','preview_svg.py'):
 res=subprocess.run([sys.executable,'-X','utf8',str(H/script)],capture_output=True,encoding='utf-8');(OUT/(script[:-3]+'.log')).write_text(public(res.stdout+res.stderr),encoding='utf-8');assert res.returncode==0,res.stderr
audit=json.loads((OUT/'audit_local.json').read_text(encoding='utf-8'));assert all(v['identical'] for v in audit['input_hashes'].values())
assert all(v['status']=='PASS_IN_LOCAL_MODEL' for v in audit['checks'].values())
(OUT/'verification_runs.json').write_text(json.dumps(runs,indent=2)+'\n',encoding='utf-8')
print('FINAL',report['metrics']['comparison_tuple'])
