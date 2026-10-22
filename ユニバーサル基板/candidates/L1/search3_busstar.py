from common import *
import route3_busstar as rt
best=tuple(json.loads((HERE/'round2/out/metrics.json').read_text(encoding='utf8'))['lexicographic_sort_key']);hist=[]
for mask in [15,0,1,2,4,8,3,5,6,7,9,10,11,12,13,14]:
 for s in range(1,int(sys.argv[1])+1):
  w,r=rt.make(s,False,mask,3);key=tuple(r['metrics']['lexicographic_sort_key']);hist.append({'mask':mask,'seed':s,'tuple':r['metrics']['comparison_tuple']})
  if key<best and key[4]<=242.64:
   best=key;save_json(HERE/'wiring.busstar.json',w);save_json(HERE/'preview.busstar.json',r);print('BEST BUSSTAR',mask,s,key,flush=True)
  if s%10==0:save_json(HERE/'search_busstar_r3.json',hist);print('DONE',mask,s,flush=True)
