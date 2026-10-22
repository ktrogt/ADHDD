"""Exact shared v0.2 CLI outputs, always using the approved shared board."""
import sys,subprocess,json
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;B=H.parent.parent;R=B.parent
results=[]
for command in ['verify','render','wirelist','continuity']:
    args=[sys.executable,'-X','utf8',str((B/'tools/ub.py').relative_to(R)),command,'--project',str(H.relative_to(R)),
        '--board',str((B/'board.json').relative_to(R)),'--rules',str((B/'design_rules_v0.2.json').relative_to(R))]
    z=subprocess.run(args,cwd=R,capture_output=True,encoding='utf-8')
    (H/'out'/f'{command}.log').write_text(z.stdout+z.stderr,encoding='utf-8')
    results.append({'command':command,'exit_code':z.returncode,'first_lines':z.stdout.splitlines()[:4]})
    print(command,z.returncode,'\n'.join(z.stdout.splitlines()[:3]))
(H/'out/commands.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
