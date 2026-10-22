from common import *
import route3_north2 as rt
best=tuple(json.loads((HERE/'round2/out/metrics.json').read_text(encoding='utf8'))['lexicographic_sort_key']);hist=[]
for mask in [15,0,1,2,4,8,3,5,6,7,9,10,11,12,13,14]:
 for s in range(1,int(sys.argv[1])+1):
  w,r=rt.make(s,False,mask,3);key=tuple(r['metrics']['lexicographic_sort_key']);hist.append({'mask':mask,'seed':s,'tuple':r['metrics']['comparison_tuple']})
  if key<best and key[4]<=242.64:
   best=key;save_json(HERE/'wiring.north2.json',w);save_json(HERE/'preview.north2.json',r);print('BEST NORTH2',mask,s,key,flush=True)
  if s%10==0:save_json(HERE/'search_north2_r3.json',hist);print('DONE',mask,s,flush=True)
