"""Rebuild the selected round-2 candidate; output stays inside L1."""
from common import *
from layout2 import seed,check
from route2 import make
import subprocess

if __name__=='__main__':
 cfg=json.loads((HERE/'selection.json').read_text(encoding='utf8'))
 d=seed();assert not check(d,False);save_json(HERE/'placement.r2.json',d)
 w,r=make(cfg['seed'],False,cfg['bare_in1_mask'],cfg['edge_mode'])
 assert r['metrics']['comparison_tuple'][:3]==[True,0,0]
 save_json(HERE/'wiring.r2.json',w);save_json(HERE/'preview.r2.json',r)
 for name in ['finish2.py','polish_svg.py','raster_svg.py']:
  subprocess.run([sys.executable,'-X','utf8',str(HERE/name)],check=True)
 print('Inspect out/top.png, bottom.png and overlay.png, then run report2.py --qa-confirmed.')
