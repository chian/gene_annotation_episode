from pathlib import Path
import sys,json,math
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
OUT=Path(__file__).resolve().parent;PIN=OUT/'pin_001'
sys.dont_write_bytecode=True;sys.path[:0]=[str(PIN),str(PIN/'tests')]
from test_literature_compiled_assay_185 import setup,with_covariance,populate,add_source,extraction
from gene_annotation_episode.literature_assay_storage import LiteratureAssayRepository
from gene_annotation_episode.literature_compiled_assay_inputs import ROLES,NS_ASSAY
from gene_annotation_episode.domain import canonical
results={}
store,ctx,args,_=setup(OUT/'oracle_correlated_001')
with store:
 ctx,args,data=with_covariance(store,ctx,args)
 # A shared synthetic source of noise plus distinct noise: D + b*b^T.
 b=[.1,.02,.005,.03,-.02,.01];diag=[.01,.001,.0001,.003,.002,.002]
 data['covariance']=[[b[i]*b[j]+(diag[i] if i==j else 0) for j in range(6)] for i in range(6)]
 ref=add_source(store,canonical(data),'root_synthetic_correlated_joint_covariance',[args['source_ref']]);ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,ref));args['covariance_source_ref']=ref
 _,_,saved=populate(store,ctx,args,'root-correlated')
 with localcontext() as dc:
  dc.prec=80
  x=[Decimal(str(saved['extraction']['operands'][r]['value'])) for r in ROLES];h=Decimal('1e-20')
  def fn(v):
   q,g,k,E,u,z=v
   return (q-g)*z/(k*E*u)
  J=[]
  for i in range(6):
   hi=list(x);lo=list(x);hi[i]+=h;lo[i]-=h
   J.append((fn(hi)-fn(lo))/(2*h))
  expected=sum(J[i]*Decimal(str(data['covariance'][i][j]))*J[j] for i in range(6) for j in range(6))+Decimal('.001')
  actual=saved['sheet']['cells']['effect_variance']['value']
  assert math.isclose(actual,float(expected),rel_tol=1e-12)
  assert math.isclose(saved['sheet']['cells']['corrected_activity']['value'],float(fn(x)),rel_tol=1e-14)
  results['correlated']={'finite_difference_precision_digits':80,'h':str(h),'J':[str(x) for x in J],'expected_variance':str(expected),'actual_variance':actual,'nonzero_offdiagonal_entries':sum(data['covariance'][i][j]!=0 for i in range(6) for j in range(6) if i!=j)}
 assert len(store.list('observation'))==0
store,ctx,args,outputs=setup(OUT/'oracle_alias_001')
with store:
 ordinary=deepcopy(outputs['assay']['arguments']);ordinary['primitives']['g']=deepcopy(ordinary['primitives']['q'])
 out=LiteratureAssayRepository(store,ctx.run_id).populate(ctx,ordinary,'root-aliased-source');ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
 for role,name in [('q','net_rate'),('g','contaminant_rate')]:args['operands'][role]={'namespace':NS_ASSAY,'sheet_ref':out['result']['sheet_ref'],'component':name}
 ctx,args,data=with_covariance(store,ctx,args)
 data['covariance']=[[.04 if i<2 and j<2 else .001 if i==j else 0 for j in range(6)] for i in range(6)]
 ref=add_source(store,canonical(data),'root_synthetic_same_measurement_covariance',[args['source_ref']]);ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,ref));args['covariance_source_ref']=ref
 _,_,saved=populate(store,ctx,args,'root-alias')
 c=saved['sheet']['cells'];assert c['corrected_activity']['value']==0
 assert math.isclose(c['effect_variance']['value'],.001,rel_tol=1e-14)
 assert saved['extraction']['operands']['q']['quantity_key']==saved['extraction']['operands']['g']['quantity_key']
 assert len(store.list('observation'))==0
 results['same_measurement_alias']={'mean':0,'variance':c['effect_variance']['value'],'meaning':'q-g cancels the same source measurement; only stipulated distinct residual remains; synthetic mathematical covariance control, not two independent experiments'}
results['scope']='Two independent numerical/dependence probes on frozen185 code using synthetic sources only; not original-paper reliability or adequacy.'
with (OUT/'ROOT_NUMERICAL_ORACLE_001.json').open('x') as f:json.dump(results,f,indent=2);f.write('\n')
print(json.dumps(results,indent=2))
