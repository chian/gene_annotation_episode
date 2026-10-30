"""Review-only004 schema proposal; no production constructors are changed."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
import jsonschema
P=Path(__file__).parent
resources={k:json.loads((P/(k+'_SCHEMA_003.json')).read_text()) for k in ('SELECTION','EXTRACTION','CALCULATION_INPUTS','SHEET','COVARIANCE_DOCUMENT')}
definitions={}
for s in resources.values():
 for name,value in s.get('$defs',{}).items():
  assert name not in definitions or definitions[name]==value
  definitions[name]=deepcopy(value)
def obj(props):return dict(type='object',properties=props,required=list(props),additionalProperties=False)
def ref(name):return {'$ref':'#/$defs/'+name}
def nullable(schema):return {'anyOf':[schema,{'type':'null'}]}
definitions['coefficient_reading']=obj({'reading':ref('retained_number'),'source_context':ref('retained_witness')})
conversion=definitions['conversion_value']
conversion['properties']['coefficient_readings']=obj({r:nullable(ref('coefficient_reading')) for r in ('endpoint','common')})
conversion['required']=list(conversion['properties'])
manifest=[]
for name,source in resources.items():
 body={k:deepcopy(v) for k,v in source.items() if k!='$defs'}
 body['$id']=body['$id'].replace(':plan003:',':plan004:')
 if name=='EXTRACTION':body['properties']['version']['const']='a105_measurement_comparison_extraction_v2'
 if name=='CALCULATION_INPUTS':body['properties']['version']['const']='a105_measurement_comparison_calculation_inputs_v2'
 reached=set()
 def visit(value):
  if isinstance(value,dict):
   if '$ref' in value:
    key=value['$ref'].removeprefix('#/$defs/')
    if key not in reached:reached.add(key);visit(definitions[key])
   for k,v in value.items():
    if k!='$ref':visit(v)
  elif isinstance(value,list):
   for v in value:visit(v)
 visit(body)
 result={**body,'$defs':{k:definitions[k] for k in sorted(reached)}}
 jsonschema.Draft202012Validator.check_schema(result)
 path=P/(name+'_SCHEMA_004.json')
 if path.exists():raise RuntimeError('Refuse overwrite')
 raw=(json.dumps(result,indent=2)+'\n').encode();path.write_bytes(raw)
 manifest.append(dict(path=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(P/'COEFFICIENT_SCHEMA_PROPOSAL_MANIFEST_011.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Five standalone004 proposal schemas written; production constructors unchanged.')
