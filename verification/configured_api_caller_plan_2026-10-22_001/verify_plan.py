"""Offline planning checks only. No application imports or live paths created."""
from pathlib import Path
import hashlib,json,tomllib
from copy import deepcopy
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parent
load=lambda name:json.loads((ROOT/name).read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
schema=load('SCHEMAS.json')
Draft202012Validator.check_schema(schema)
old=load('ORIGINAL_CALLER_OPERANDS.json');config=load('PROPOSED_CALLER_CONFIGURATION.json')
parsed=tomllib.loads((ROOT/'PROPOSED_CALLER_CONFIG.toml').read_text());parsed['local_jobs']['wall_seconds']=None
assert parsed==config
for name,value in [('normalized_configuration',config),('api_registry',load('PROPOSED_API_REGISTRY.json')),('api_timing',load('PARAMETER_BLUEPRINT.json')['template']['services']['api_timing']),('planning_marker',load('PARAMETER_BLUEPRINT.json')['template']['services']['api_execution_planning'])]:
 Draft202012Validator(schema['$defs'][name]).validate(value)
parameters=load('PARAMETER_BLUEPRINT.json')['template'];dynamic=[('scientific_progress','initial_known_record_refs'),('operational','registry_ref')]
for section,key in dynamic:assert parameters['policy'][section][key] is None
errors=list(Draft202012Validator(schema['$defs']['configured_parameters']).iter_errors(parameters))
assert sorted(tuple(e.absolute_path) for e in errors)==[('policy','operational','registry_ref'),('policy','scientific_progress','initial_known_record_refs')]
static=deepcopy(old['parameters']['policy']);proposed=deepcopy(parameters['policy'])
for section,key in dynamic:static[section].pop(key);proposed[section].pop(key)
assert canonical(static)==canonical(proposed)
focus=load('FOCUS_PROVENANCE.json');before=(ROOT/'ORIGINAL_BOUND_FOCUS.txt').read_bytes();after=(ROOT/'PROPOSED_CALLER_FOCUS.txt').read_bytes()
assert len(before)==focus['original_bound_bytes'] and sha(before)==focus['original_bound_utf8_sha256']
assert len(after)==focus['proposed_bytes'] and sha(after)==focus['proposed_utf8_sha256']
assert after.replace(focus['replacement_sentence'].encode(),focus['removed_sentence'].encode())==before
assert not before.endswith(b'\n') and not after.endswith(b'\n')
readset=load('READSET.json')
for entry in readset['entries']:
 p=Path(entry['path']);b=p.read_bytes();assert len(b)==entry['bytes'] and sha(b)==entry['sha256'],p
result={'version':'configured_api_caller_planning_checks_v1','JSON_Schema_syntax':'pass','closed_static_subschemas':'pass','TOML_normalized_null_wall_matches_JSON':'pass','static_policy_canonical_identity':'pass','focus_exact_single_sentence_replacement':'pass','readset_source_identity':'pass','blueprint_expected_errors_only':['policy.operational.registry_ref requires actual NEW preparation','policy.scientific_progress.initial_known_record_refs requires verified actual C result/receipt'],'application_objects_constructed':0,'scientific_state_DB_opens':0,'model_HTTP_native_calls':0,'application_or_test_runs':0,'production_source_mutations':0,'actual_custody_or_launch_performed':False}
print(json.dumps(result,indent=2,sort_keys=True))
