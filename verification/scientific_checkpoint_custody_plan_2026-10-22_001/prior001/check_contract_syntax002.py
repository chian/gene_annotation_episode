"""Representation/readset checks only; no application imports, DBs or custody."""
from pathlib import Path
import hashlib
import json
import jsonschema

root = Path(__file__).resolve().parent
schemas = json.loads((root/'SCHEMAS002.json').read_text())
closed_objects = 0
def visit(value):
    global closed_objects
    if isinstance(value, dict):
        if value.get('type') == 'object':
            assert value.get('additionalProperties') is False
            assert set(value['required']) == set(value['properties'])
            closed_objects += 1
        for child in value.values():
            visit(child)
    elif isinstance(value, list):
        for child in value:
            visit(child)
for name, schema in schemas['$defs'].items():
    jsonschema.Draft202012Validator.check_schema(schema)
    visit(schema)
request = schemas['$defs']['request']
validator = jsonschema.Draft202012Validator(request)
assert list(validator.iter_errors({}))
example = {'source_workspace':'/synthetic/source', 'source_run_directory':'/synthetic/run',
    'source_implementation_root':'/synthetic/implementation', 'source_run_id':'run_'+'0'*32,
    'expected_source_implementation_sha256':'0'*64, 'expected_pending_request_sha256':'1'*64,
    'destination_workspace':'/synthetic/new', 'initial_known_record_refs':['input_'+'2'*24]}
assert not list(validator.iter_errors(example))
assert list(validator.iter_errors({**example, 'unknown':True}))
readset=json.loads((root/'READSET.json').read_text())
for item in readset['files']:
    raw=Path(item['path']).read_bytes()
    assert len(raw)==item['bytes']
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
inputs=json.loads((root/'INPUT_PROVENANCE.json').read_text())
for item in inputs['files']:
    raw=Path(item['path']).read_bytes()
    assert len(raw)==item['bytes']
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
digest=hashlib.sha256()
implementation=Path(readset['implementation_root'])
files=sorted(path for package in ('gene_annotation_episode','method_loop')
    for path in (implementation/package).rglob('*.py'))
for path in files:
    digest.update(str(path.relative_to(implementation)).encode()+b'\0')
    digest.update(hashlib.sha256(path.read_bytes()).digest())
assert digest.hexdigest()==readset['implementation_sha256']
print(json.dumps({'status':'representation_and_readset_checks_passed',
    'schema_definitions':len(schemas['$defs']), 'closed_object_schemas':closed_objects,
    'representation_examples':3, 'readset_members':len(readset['files']),
    'P002_input_members':len(inputs['files']), 'runtime_members':len(files),
    'runtime_pin':digest.hexdigest(), 'application_imports':0, 'DB_opens':0,
    'application_tests':0, 'custody_implementations_or_forks':0},sort_keys=True))
