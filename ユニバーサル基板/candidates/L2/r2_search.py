"""Routing order comparisons for the current L2 placement."""
import sys,json,random,contextlib,io,time
sys.dont_write_bytecode=True
import r2 as b, r2_route
from model import save_json
from verify import verify
def search(n=64):
 rng=random.Random(20261022);records=[];best=None;start=time.time()
 for it in range(n):
  order=list(range(8)) if it==0 else list(range(7,-1,-1)) if it==1 else rng.sample(range(8),8)
  mode=['signals','power','quiet','powerquiet'][it%4];seed=0 if it<4 else rng.randrange(100000)
  try:
   with contextlib.redirect_stdout(io.StringIO()):rep=r2_route.build(order,mode,seed)
  except (ValueError,TypeError) as e:
   records.append(dict(i=it,error=str(e)));continue
  m=rep['metrics'];rank=m['lexicographic_sort_key'];rec=dict(i=it,mode=mode,order=order,seed=seed,tuple=m['comparison_tuple'],rank=rank)
  records.append(rec)
  if best is None or rank<best:
   best=rank;save_json(b.H/'wiring.best.json',b.project().wire_data());save_json(b.H/'best.json',rec);save_json(b.H/'placement.best.json',b.project().placement)
   print('BEST',rec,flush=True)
  if it%8==0:print('iteration',it,'seconds',round(time.time()-start,1),'best',best,flush=True)
 save_json(b.H/'routing_search.json',dict(records=records))
 save_json(b.H/'wiring.json',json.loads((b.H/'wiring.best.json').read_text(encoding='utf-8')))
if __name__=='__main__':search(int(sys.argv[1]) if len(sys.argv)>1 else 64)
