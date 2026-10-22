from common import *
import route3_bus as rt
best=tuple(json.loads((HERE/'round2/out/metrics.json').read_text(encoding='utf8'))['lexicographic_sort_key']);hist=[]
for s in range(1,int(sys.argv[1])+1):
 w,r=rt.make(s,False,0,3);key=tuple(r['metrics']['lexicographic_sort_key']);hist.append({'seed':s,'tuple':r['metrics']['comparison_tuple']})
 if key<best and key[4]<=242.64:
  best=key;save_json(HERE/'wiring.bus.json',w);save_json(HERE/'preview.bus.json',r);print('BEST BUS',s,key,flush=True)
 if s%10==0:save_json(HERE/'search_bus_r3.json',hist);print('DONE',s,flush=True)
