"""Representation/closed-relationship/source-pin checks, not custody tests."""
from pathlib import Path
import hashlib
import json
import jsonschema
root=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(root/'CONTRACT007.md')=='48da8518ccd4509b9d2f28bccb771af92a088646f795e5db425e14aec9782be7'
assert sha(root/'SCHEMAS004.json')=='b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112'
assert sha(root/'CONTRACT004.md')=='4f28639c2c2f3be8cfc779d82c19507d3bab1cf4d71ce69319cde054a36425d6'
assert sha(root/'CONTRACT005.md')=='e606ec84f2233250704e4d08e2cfc60fab393859c278b10a8d8882c9048b69f2'
schemas=json.loads((root/'SCHEMAS004.json').read_text())
count=0
def visit(value):
    global count
    if isinstance(value,dict):
        if value.get('type')=='object':
            assert value.get('additionalProperties') is False
            assert set(value['required'])==set(value['properties'])
            count+=1
        for child in value.values():visit(child)
    elif isinstance(value,list):
        for child in value:visit(child)
for schema in schemas['$defs'].values():
    jsonschema.Draft202012Validator.check_schema(schema);visit(schema)
validator=jsonschema.Draft202012Validator(schemas['$defs']['failure'])
base={'version':'scientific_checkpoint_fork_failure_v1','code':'invalid_request','phase':'validate_request',
    'affected_refs':[],'staging_workspace':None,'published_workspace':None,'publication_state':'not_created',
    'source_unchanged':None,'cause':'contract_error','errno':None}
retained={**base,'code':'snapshot_mismatch','phase':'validate_snapshot','publication_state':'retained_stage',
    'staging_workspace':'/synthetic/stage','source_unchanged':True}
durability={**base,'code':'publication_failure','phase':'publish','publication_state':'published_durability_unconfirmed',
    'source_unchanged':True,'cause':'io_error'}
location={**durability,'publication_state':'published_location_unconfirmed','published_workspace':'/synthetic/moved/output',
    'cause':'contract_error'}
positives=[base,retained,durability,location,{**location,'published_workspace':None},{**retained,'staging_workspace':None}]
negatives=[{**base,'staging_workspace':'/synthetic/stage'},
    {**base,'published_workspace':'/synthetic/output'},
    {**retained,'staging_workspace':'relative'},
    {**retained,'published_workspace':'/synthetic/output'},
    {**durability,'cause':'contract_error'},
    {**location,'staging_workspace':'/synthetic/old-stage'},
    {**location,'code':'invalid_request'},
    {**location,'source_unchanged':None},
    {**location,'unknown':True}]
assert all(not list(validator.iter_errors(v)) for v in positives)
assert all(list(validator.iter_errors(v)) for v in negatives)
pins=json.loads((root/'CONSTRUCTOR_READPATHS.json').read_text())
for row in pins['files']:
    for item in row['witnesses']:
        raw=Path(item['path']).read_bytes()
        assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
print(json.dumps({'status':'final_schema_and_pin_guards_passed','schema_definitions':len(schemas['$defs']),
    'closed_object_schemas':count,'failure_representation_positive_examples':len(positives),
    'failure_representation_negative_examples':len(negatives),'constructor_source_files':4,'constructor_source_copies':12,
    'historical004005_contract_hashes_preserved':True,
    'application_imports':0,'scientific_DB_opens':0,'application_tests':0,'custody_implementations_or_forks':0},sort_keys=True))
