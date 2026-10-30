"""Additive exact plugin-domain proposal; does not implement production calculations."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
import jsonschema
P=Path(__file__).parent
preserve={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir() if p.is_file() and ('001' in p.name or '002' in p.name)}
def read(n):return json.loads((P/n).read_text())
def write(n,v):
 p=P/n
 if p.exists():raise RuntimeError('Refuse to overwrite '+str(p))
 p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
domains=read('PLAN_DOMAINS_002.json')
domains['reasons']['domain'] += ['zero_plugin_difference_variance','combined_estimate_not_identified_by_plugin_covariance']
write('PLAN_DOMAINS_003.json',domains)
resources={}
for name in ('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET','COVARIANCE_DOCUMENT'):
 s=read(name+'_SCHEMA_002.json');s['$id']=s['$id'].replace(':plan002:',':plan003:')
 if 'domain_reasons' in s.get('$defs',{}):s['$defs']['domain_reasons']['items']['enum']=domains['reasons']['domain']
 jsonschema.Draft202012Validator.check_schema(s);resources[name]=s;write(name+'_SCHEMA_003.json',s)
source=read('SINGULAR_AND_PROTOCOL_PARTIAL_EXAMPLES_002.json')
examples=[]
for which in (0,1,2):
 e=deepcopy(source[which]);e['case']=e['case'].replace('singular_','plugin_singular_').replace('common_model_contradiction','common_estimate_nonidentification')
 e['calculation_input_summary']['covariance_status']='estimated'
 e['calculation_input_summary']['covariance_is_actual_selected_estimator_covariance_in_this_synthetic_model']=False
 e['calculation_input_summary']['covariance_role']='estimated_plugin_matrix_not_known_population_covariance'
 e['weight_allocation']='nonunique_plugin_weights'
 e['scientific_contradiction_inferred']=False
 e['actual_population_difference_variance']='unknown_from_zero_plugin_variance'
 for cell in e['expected_cells']:
  cell['contribution_key']='contribution_'+hashlib.sha256(e['case'].encode()).hexdigest()
  cell['uncertainty']['variance_status']='estimated'
  if cell['interpretation']=='protocol_difference_uncertainty_known_covariance':cell['interpretation']='protocol_difference_uncertainty_estimated_covariance'
  elif cell['interpretation']=='known_covariance_common_estimate':cell['interpretation']='estimated_covariance_plugin_common_estimate'
  name=cell['component']
  if name in ('standardized_difference','squared_standardized_difference'):
   cell['reasons']['domain']=['zero_plugin_difference_variance']
  elif name in ('weight_left','weight_right'):
   cell['reasons']['domain']=['nonunique_gls_weights']
  elif which==2 and name in ('combined_estimate','combined_variance','combined_standard_uncertainty'):
   cell['reasons']['domain']=['combined_estimate_not_identified_by_plugin_covariance']
 examples.append(e)
s=resources['SHEET'];cell_resource={'$schema':s['$schema'],'$defs':s['$defs'],**deepcopy(s['$defs']['cell'])}
for e in examples:
 for c in e['expected_cells']:jsonschema.Draft202012Validator(cell_resource).validate(c)
 assert all('inconsistent_deterministic_constraint' not in c['reasons']['domain'] for c in e['expected_cells'])
write('PLUGIN_SINGULAR_PARTIAL_EXAMPLES_003.json',examples)
assert all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in preserve.items())
write('PLUGIN_CORRECTION_CHECKS_003.json',{'all_original001_and002_hashes_unchanged':True,'preserved_files':len(preserve),'standalone_003_resources_metaschema_checked':list(resources),'expected_plugin_cells_validated':sum(len(e['expected_cells']) for e in examples),'zero_plugin_variance_used_as_population_constraint':False,'production_or_test_file_edit':False,'component_implementation_executed':False})
print('Additive003 reason domains and three plugin mathematical examples checked; all001/002 bytes retained.')
