"""Run exact shared CLI against final files, keeping UTF-8 evidence locally."""
import sys,subprocess,json
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent;REPO=BASE.parent
results=[]
for command in ['verify','render','wirelist','continuity']:
    args=[sys.executable,'-X','utf8',str((BASE/'tools/ub.py').relative_to(REPO)),command,'--project',str(HERE.relative_to(REPO))]
    z=subprocess.run(args,cwd=REPO,capture_output=True,encoding='utf-8')
    (HERE/'out'/f'{command}.log').write_text(z.stdout+z.stderr,encoding='utf-8')
    results.append({'command':command,'exit_code':z.returncode,'first_line':z.stdout.splitlines()[0] if z.stdout else z.stderr})
    print(command,z.returncode,results[-1]['first_line'])
(HERE/'out/commands.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
