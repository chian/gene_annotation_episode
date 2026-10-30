import json,time
from copy import deepcopy
import gene_annotation_episode.bvbrc_comparative_systems_returns as m
out={}
def measured(fn,n):
 start=time.perf_counter()
 result=None
 for _ in range(n): result=fn()
 return result,(time.perf_counter()-start)/n
before,t1=measured(m._fact_source_templates.__wrapped__,20)
after,t2=measured(m.comparative_systems_fact_sources,20)
assert before==after
mutated=m.comparative_systems_fact_sources()
first=next(iter(mutated))
mutated[first]['report_schema']['items']['properties'].clear()
assert m.comparative_systems_fact_sources()==before
out={'equality':True,'mutation_isolated':True,'runs_per_measurement':20,'uncached_template_construction_seconds':t1,'cached_detached_public_schema_seconds':t2,'byte_count':len(json.dumps(before,sort_keys=True)),'facts_or_authentication_cached':False}
print(json.dumps(out,indent=2))
