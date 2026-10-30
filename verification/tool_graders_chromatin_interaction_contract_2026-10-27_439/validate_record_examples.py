"""Document/schema verification only. No native parser or calculator imports."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parent
def no_constant(token): raise ValueError("nonfinite_json:"+token)
def no_duplicate(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise ValueError("duplicate_json_key:"+k)
        result[k]=v
    return result
def read(path): return json.loads(path.read_text(),parse_constant=no_constant,object_pairs_hook=no_duplicate)
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
schema=read(ROOT/"RECORD_SCHEMA.json"); defs=schema['$defs']
Draft202012Validator.check_schema(schema)
def walk(value):
    if isinstance(value,dict):
        yield value
        for x in value.values(): yield from walk(x)
    elif isinstance(value,list):
        for x in value: yield from walk(x)
for node in walk(schema):
    if node.get('type')=='object': assert node.get('additionalProperties') is False
    if '$ref' in node:
        assert node['$ref'].startswith('#/$defs/') and node['$ref'][8:] in defs
examples=read(ROOT/"WORKED_RECORDS.json")
assert set(examples)=={'record_type','identities','records'}
assert examples['record_type']=='synthetic_hand_worked_contract_records_not_native_runs'
assert 'no corresponding Store registrations' in examples['identities']
validators={name:Draft202012Validator({'$defs':defs,'$ref':'#/$defs/'+name}) for name in defs}
indexed={}
for example in examples['records']:
    assert set(example)=={'example_key','schema_definition','record'}
    assert example['example_key'] not in indexed
    indexed[example['example_key']]=example
    errors=sorted(validators[example['schema_definition']].iter_errors(example['record']),key=lambda e:str(list(e.absolute_path)))
    if errors:
        raise AssertionError(example['example_key']+': '+str(list(errors[0].absolute_path))+': '+errors[0].message[:1500])
    for node in walk(example['record']):
        if set(node)=={'artifact_ref','sha256','size_bytes','format'}:
            assert node['artifact_ref']=='artifact_'+node['sha256']
def rec(key): return indexed[key]['record']
for label in ['raw','weighted','insulation','partial']:
    sheet,components=rec(label+'.sheet'),rec(label+'.components')
    h=hashlib.sha256(canonical(sheet)).hexdigest()
    assert components['source_sheet_sha256']==h
    files=[t['file'] for t in sheet['data_tables'] if t['file'] is not None]
    assert components['table_identities']==files
    mode=components['contact'] or components['insulation']
    assert mode['source_sheet_sha256']==h and mode['table_identities']==files
    assert mode['normalization']==components['parameters']['normalization']
    assert mode['populations'][0]['source_table_keys']==[t['table_key'] for t in sheet['data_tables'] if t['file'] is not None]
    assert sheet['request']==rec(label+'.request')
    assert len(rec(label+'.tables')['populations'][0]['bins'])==sheet['populations'][0]['bin_count']
    assert len(rec(label+'.tables')['populations'][0]['contacts'])==sheet['populations'][0]['raw_cell_population']['validated_observed_row_count']
    assert rec(label+'.extraction')['table_drafts']==[{k:v for k,v in t.items() if k!='file'} for t in sheet['data_tables']]
for example in examples['records']:
    if example['schema_definition']!='RequestedProjection': continue
    name=example['example_key'].removesuffix('.projection'); projection=example['record']; selector=rec(name+'.selector')
    assert projection['kind']==selector['projection']['kind']
    assert projection['requested_fields']==selector['projection']['fields']
    assert projection['parameters']==selector['parameters']
    for row in projection['rows']:
        assert set(row['fields'])==set(projection['requested_fields'])
        assert row['population_key'] in selector['population_keys']
        for value in row['fields'].values(): assert value['population_key']==row['population_key']
    if projection['page']:
        assert projection['page']['returned_count']==len(projection['rows'])
for p in [rec('handoff.native_worker_plan'),rec('handoff.saved_worker_plan')]:
    assert p['mode']==p['selector']['mode']
saved=rec('handoff.saved_worker_plan')
assert {k for k in saved}=={'version','mode','directory','sheet_bundle','selector'}
assert saved['sheet_bundle']['sheet']['file']==saved['selector']['saved_sheet_bundle']['sheet']
assert [x['file'] for x in saved['sheet_bundle']['tables']]==saved['selector']['saved_sheet_bundle']['tables']

# Negative type/closure checks only: no claims about native or biological validity.
negative=[]
v=deepcopy(rec('raw.request'));v['invented_field']=1;negative.append(('ChromatinRequest',v))
v=deepcopy(rec('raw.sheet'));del v['native']['chromosomes'];negative.append(('ContactSheet',v))
v=deepcopy(rec('missing_matrix.failure'));v['code']='made_up_failure';negative.append(('Failure',v))
v=deepcopy(rec('raw.components'));v['contact']['populations'][0]['counts']['requested_pair_count']['value']=1.5;negative.append(('ChromatinComponents',v))
v=deepcopy(rec('raw.selector'));v['projection']['fields']=['confidence'];negative.append(('ResultSelector',v))
v=deepcopy(rec('raw.selector'));v['saved_sheet_bundle']=rec('handoff.saved_worker_plan')['selector']['saved_sheet_bundle'];negative.append(('ResultSelector',v))
v=deepcopy(rec('genuine_zero.raw_value'));v['value']=None;negative.append(('Measurement',v))
v=deepcopy(rec('raw.tables'));v['populations'][0]['contacts'][0]['value']={'value':0,'state':'native_nan'};negative.append(('ContactTableFixture',v))
v=deepcopy(rec('raw.projection'));v['rows'][0]['fields']['invented']=0;negative.append(('RequestedProjection',v))
for name,value in negative: assert not validators[name].is_valid(value),name

sources=read(ROOT/"SOURCE_FILES.json"); verified_sources=0
for source in sources['sources']:
    if source['path'] is None: continue
    data=(ROOT/source['path']).read_bytes()
    assert len(data)==source['size_bytes'] and hashlib.sha256(data).hexdigest()==source['sha256']
    verified_sources+=1
report={"record_type":"planning_document_validation_not_scientific_verification","schema_definitions":len(defs),"positive_complete_records":len(examples['records']),"negative_schema_checks":len(negative),"retained_source_hashes_verified":verified_sources,"cross_record_checks":["canonical_sheet_digest","table_identity_order","source_table_key_membership","request_sheet_equality","row_count_extent_for_worked_complete_cases","extraction_descriptor_equality","selector_projection_field_equality","population_foreign_keys","saved_bundle_only_plan","native_file_artifact_digest_relation"],"native_parser_executed":False,"scientific_calculator_executed":False,"native_format_fixture_created":False,"live_workflow_verified":False,"symbolic_fixture_identity_warning":examples['identities'],"status":"passed"}
Path('validation.json').write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
