"""Review checks only. No production component/test is imported or run."""
from pathlib import Path
import hashlib,json
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).parent
modules=['literature_partner_source_fields.py','literature_partner_defined_units.py','literature_rate_native_inputs.py','literature_rate_calculations.py','literature_rate_observation_inputs.py','literature_kinetic_inputs.py','literature_kinetic_calculations.py','literature_measurement_validation_inputs.py','literature_product_coupling_inputs.py','literature_product_coupling_calculations.py','literature_optical_inputs.py','literature_optical_calculations.py','literature_compiled_assay_inputs.py','literature_compiled_assay_calculations.py','literature_compiled_assay_prompt.py','literature_assay_inputs.py','literature_experimental_contracts.py']
def record(path):
 raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
manifest={'status': 'planning_only', 'original_paper_or_255_packet_read': False, 'complete_implementation_files_read': [record(ROOT / 'gene_annotation_episode' / f) for f in modules], 'partial_validator_mechanism_inspected': record(ROOT / 'gene_annotation_episode/domain.py'), 'production_test_files_created_or_modified_by_workload': False, 'actual_source_fixture_or_model_backed_run': False, 'component_implementation_executed': False}
schema_files=list(P.glob('*_SCHEMA_001.json'))
report={'schemas':[],'illustrations':[],'checks_are_proposal_shape_checks_only':True}
for f in schema_files:
 s=json.loads(f.read_text());jsonschema.Draft202012Validator.check_schema(s)
 nestedids=[];refs=[];unclosed=[]
 def walk(x,path=()):
  if isinstance(x,dict):
   if '$id' in x and path:nestedids.append(path)
   if '$ref' in x:refs.append(x['$ref'])
   if x.get('type')=='object' and x.get('additionalProperties') is not False:unclosed.append(path)
   for k,v in x.items():walk(v,path+(k,))
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,path+(i,))
 walk(s)
 assert not nestedids and not unclosed
 assert all(r.startswith('#/$defs/') and r[8:] in s['$defs'] for r in refs)
 report['schemas'].append({**record(f),'metaschema_valid':True,'standalone_local_resource_only':True,'all_object_shapes_closed':True})
for f in P.glob('*_ILLUSTRATION_001.json'):
 name=next(n for n in ('CALCULATION_INPUTS','EXTRACTION','SELECTION','SHEET') if '_'+n+'_ILLUSTRATION_' in f.name)
 schema=json.loads((P/(name+'_SCHEMA_001.json')).read_text());data=json.loads(f.read_text());jsonschema.Draft202012Validator(schema).validate(data)
 report['illustrations'].append({**record(f),'shape_valid':True,'origin':'hand_constructed_synthetic_plan_payload_not_component_execution'})
for f in P.glob('*_COVARIANCE_SOURCE_001.json'):
 jsonschema.Draft202012Validator(json.loads((P/'COVARIANCE_DOCUMENT_SCHEMA_001.json').read_text())).validate(json.loads(f.read_text()))
# Exact shape-state restrictions and component/formula binding are really enforced.
sheet=json.loads((P/'SYNTHETIC_KNOWN_COVARIANCE_SHEET_ILLUSTRATION_001.json').read_text());schema=json.loads((P/'SHEET_SCHEMA_001.json').read_text())
wrong=json.loads(json.dumps(sheet));wrong['cells'][0]['formula']='L-R'
assert not jsonschema.Draft202012Validator(schema).is_valid(wrong)
wrong=json.loads(json.dumps(sheet));wrong['cells'][0]['conditional_value']=5
assert not jsonschema.Draft202012Validator(schema).is_valid(wrong)
report['schema_negative_checks']=['component_formula_binding','populated_conditional_value_separation']
(P/'READ_AND_SCOPE_MANIFEST_001.json').write_text(json.dumps(manifest,indent=2)+'\n')
(P/'PLAN_SHAPE_CHECKS_001.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'standalone_schema_resources_checked': len(schema_files), 'hand_constructed_payloads_shape_checked': len(report['illustrations']), 'component_implementation_executed': False, 'production_or_test_edit': False}))
