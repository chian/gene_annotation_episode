"""Read-only leaf errors for the actual failed launch-local provider boundary."""
import json
import os
from pathlib import Path
import sqlite3
import sys

original = Path(os.environ['WORKFLOW451_ORIGINAL'])
sys.path.insert(0, str(original / 'source_snapshot'))
from importlib import import_module
from jsonschema import Draft202012Validator
from gene_annotation_episode.runtime import _action_generation_schema
F = import_module('verification.tool_graders_chromatin_workflow_2026-10-27_451.fixture_helpers')

directory = original / 'temporary/pytest/chromatin4510'
db = sqlite3.connect(f'file:{directory / "state/state.sqlite3"}?mode=ro', uri=True)
row = db.execute('SELECT request FROM runtime_model_calls ORDER BY rowid DESC LIMIT 1').fetchone()
request = json.loads(row[0])
db.close()
configuration = json.loads((directory / 'fixture-configuration.json').read_bytes())
context, original_schema = request['context'], request['schema']
schema = _action_generation_schema(original_schema)
raw = F.commission('launch_local', context['execution_assignment']['requests']['here'],
    configuration['scope'], F.HANDOFF_FORM,
    objective='Execute the exact supplied chromatin request on the configured local resource.')
converted = F.provider_value(raw, schema)


def leaves(error):
    if error.context:
        for child in error.context:
            yield from leaves(child)
    else:
        message = error.message
        if len(message) > 500:
            message = '<large instance omitted>; ' + message[-300:]
        yield {'validator': error.validator, 'instance_path': list(error.absolute_path),
            'schema_path': list(error.absolute_schema_path), 'message': message}


errors = [leaf for error in Draft202012Validator(schema).iter_errors(converted) for leaf in leaves(error)]
selected = schema['properties']['selection']
branches = []
for index, branch in enumerate(selected.get('anyOf', [])):
    role = branch.get('properties', {}).get('role', {})
    if role.get('const') != 'launch_local' and 'launch_local' not in role.get('enum', []):
        continue
    candidate = F.provider_value(raw['selection'], branch)
    branch_errors = [leaf for error in Draft202012Validator(branch).iter_errors(candidate) for leaf in leaves(error)]
    branches.append({'index': index, 'schema': branch, 'candidate': candidate, 'errors': branch_errors})
Path('selected-branches.json').write_text(json.dumps(branches, indent=2) + '\n')
result = {'original': str(original), 'provider_schema_rebuilt_with_actual_action_generation_schema': True,
    'original_domain_schema_valid': Draft202012Validator(original_schema).is_valid(raw),
    'complete_error_count': len(errors),
    'launch_local_branches': [{'index': branch['index'], 'errors': branch['errors']} for branch in branches],
    'all_leaf_errors': errors}
Path('LEAF_ERRORS.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'complete_error_count': len(errors), 'launch_local_branches': result['launch_local_branches']}, indent=2))
