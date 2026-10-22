"""Rebuild the frozen round-3 selection; every write stays inside L1."""
from common import *
from verify import verify
import hashlib,subprocess

if __name__=='__main__':
 cfg=json.loads((HERE/'selection.json').read_text(encoding='utf8'))
 for name,digest in cfg['selected_input_SHA256'].items():
  assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
 d=json.loads((HERE/cfg['placement_source']).read_text(encoding='utf8'))
 w=json.loads((HERE/cfg['wiring_source']).read_text(encoding='utf8'))
 assert verify(project(d,w))['metrics']['comparison_tuple'][:3]==[True,0,0]
 for name in ['finish3.py','power_gauge_audit.py','polish_svg.py','raster_svg.py']:
  subprocess.run([sys.executable,'-X','utf8',str(HERE/name)],check=True)
 assert verify(project())['metrics']['comparison_tuple']==cfg['selected_tuple']
 print('Inspect all three SVG/PNG views, then run report3.py --qa-confirmed.')
