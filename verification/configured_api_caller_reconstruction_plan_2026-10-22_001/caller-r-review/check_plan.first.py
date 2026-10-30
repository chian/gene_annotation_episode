"""Representation and byte comparisons only; no application imports or DB opens."""
import hashlib
import json
from pathlib import Path
import tomllib
from jsonschema import Draft202012Validator

ROOT = Path('/tmp/configured-api-caller-plan-MDXd91Kz')
OUT = Path(__file__).parent
SOURCE = Path('/tmp/gene-annotation-model-context-20261022-005')
reads = {}
def read(path):
    data = path.read_bytes()
    reads[str(path)] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return data
def load(name):
    return json.loads(read(ROOT / name))
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

contract = read(ROOT / 'CONTRACT002.md')
errors = load('ERROR_CONTRACT.json')
assert hashlib.sha256(contract).hexdigest() == '9b5c17fd5a3d6126b2f0460670883cb35fa81d7f854b6b063ac8565050755ced'
assert reads[str(ROOT / 'ERROR_CONTRACT.json')]['sha256'] == '33391bed795eb98ecf83084a7ed3e40cbdc929cc9629515f6d2c47ec86ba140d'
schema = load('SCHEMAS.json')
Draft202012Validator.check_schema(schema)
blueprint = load('PARAMETER_BLUEPRINT.json')
parameters = blueprint['parameters']
original = load('ORIGINAL_CALLER_OPERANDS.json')
old_policy = json.loads(canonical(original['parameters']['policy']))
new_policy = json.loads(canonical(parameters['policy']))
for policy in [old_policy, new_policy]:
    policy['operational'].pop('registry_ref')
    policy['scientific_progress'].pop('initial_known_record_refs')
assert canonical(old_policy) == canonical(new_policy)
assert hashlib.sha256(canonical(old_policy).encode()).hexdigest() == 'dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1'
old_services = original['parameters']['services']
new_services = parameters['services']
assert set(new_services) - set(old_services) == {'public_search_registry', 'api_timing', 'api_execution_planning'}
for name in set(old_services) - {'source_directory', 'version'}:
    assert canonical(old_services[name]) == canonical(new_services[name]), name
assert parameters['policy']['operational']['registry_ref'] is None
assert parameters['policy']['scientific_progress']['initial_known_record_refs'] is None
param_validator = Draft202012Validator(schema['$defs']['configured_parameters'])
invalid_paths = sorted(list(error.absolute_path) for error in param_validator.iter_errors(parameters))
assert invalid_paths == [['policy', 'operational', 'registry_ref'],
                         ['policy', 'scientific_progress', 'initial_known_record_refs']]
configuration = load('PROPOSED_CALLER_CONFIGURATION.json')
Draft202012Validator(schema['$defs']['normalized_configuration']).validate(configuration)
toml = tomllib.loads(read(ROOT / 'PROPOSED_CALLER_CONFIG.toml').decode())
toml['local_jobs']['wall_seconds'] = None
assert canonical(toml) == canonical(configuration)
for name in ['executable', 'reference_database', 'local_jobs', 'max_cpu', 'models',
             'reference_records', 'reference_residues', 'resource_id', 'search_modes']:
    assert canonical(original['configuration'][name]) == canonical(configuration[name]), name
assert configuration['restoration'] == dict(preview_size=24, model_presentation='bounded_wait_history_v1')
binding = load('EXPECTED_PUBLIC_CLIENT_BINDING.json')
assert binding['implementation_sha256'] == hashlib.sha256(read(SOURCE / 'gene_annotation_episode/acquisition.py')).hexdigest()
assert hashlib.sha256(canonical(binding).encode()).hexdigest() == new_services['public_search_registry']['client_binding_sha256']
focus = load('FOCUS_PROVENANCE.json')
before = read(ROOT / 'ORIGINAL_BOUND_FOCUS.txt')
after = read(ROOT / 'PROPOSED_CALLER_FOCUS.txt')
assert len(before) == focus['original_bound_bytes'] == 1963
assert len(after) == focus['proposed_bytes'] == 2108
assert before.count(focus['removed_sentence'].encode()) == 1
assert before.replace(focus['removed_sentence'].encode(), focus['replacement_sentence'].encode()) == after
assert not before.endswith(b'\n') and not after.endswith(b'\n')
assert hashlib.sha256(before).hexdigest() == focus['original_bound_utf8_sha256']
assert hashlib.sha256(after).hexdigest() == focus['proposed_utf8_sha256']
for name in ['VERIFICATION_AND_LAUNCH_PLAN.md', 'ADOPTION_CONTENTS.json', 'FOCUS_MINIMAL.diff',
             'READSET.json', 'INPUT_IDENTITIES.json', 'PROPOSED_API_REGISTRY.json']:
    read(ROOT / name)
result = dict(status='representation_and_static_operand_comparisons_passed',
    policy_canonical_remainder_sha256='dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1',
    unresolved_blueprint_fields=invalid_paths, schema_definitions=len(schema['$defs']),
    focus_exact_single_replacement=True, service_common_operands_unchanged=True,
    native_and_model_operands_unchanged=True, toml_explicit_none_matches_declared_configuration=True,
    client_binding_offline_sha256=new_services['public_search_registry']['client_binding_sha256'],
    application_imports=0, database_opens=0, service_tool_model_native_calls=0,
    claim_limit='No actual factory, setup, reconstruction, C receipt, caller preparation or launch was executed.')
(OUT / 'CHECK_RESULT001.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
(OUT / 'INPUT_READSET001.json').write_text(json.dumps(reads, sort_keys=True, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
