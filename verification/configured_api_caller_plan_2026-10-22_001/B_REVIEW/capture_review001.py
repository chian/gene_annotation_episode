"""Capture independent static review evidence; no application imports or DBs."""
from pathlib import Path
import hashlib
import json
import jsonschema

root=Path(__file__).resolve().parent
p=Path('/tmp/configured-api-caller-plan-MDXd91Kz')
implementation=Path('/tmp/gene-annotation-model-context-20261022-005')
c=Path('/tmp/scientific-checkpoint-custody-contract-20261022-002-hb8UUg')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def witness(path):
    raw=path.read_bytes();return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def dump(name,value):
    with (root/name).open('x') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
assert witness(p/'CONTRACT002.md')['sha256']=='9b5c17fd5a3d6126b2f0460670883cb35fa81d7f854b6b063ac8565050755ced'
assert witness(p/'ERROR_CONTRACT.json')['sha256']=='33391bed795eb98ecf83084a7ed3e40cbdc929cc9629515f6d2c47ec86ba140d'
inputs=[witness(p/name) for name in ('CONTRACT.md','CONTRACT002.md','ERROR_CONTRACT.json',
    'SCHEMAS.json','VERIFICATION_AND_LAUNCH_PLAN.md','PARAMETER_BLUEPRINT.json',
    'ORIGINAL_CALLER_OPERANDS.json','PROPOSED_CALLER_CONFIGURATION.json','EXPECTED_PUBLIC_CLIENT_BINDING.json')]
inputs += [witness(c/name) for name in ('CONTRACT007.md','SCHEMAS004.json','VERIFICATION_PLAN003.md')]
dump('INPUT_PINS001.json',{'status':'planning_only_exact_review_inputs','files':inputs})
readset={
    'assembled_case_policy.py':'Complete005 module read; exact API_VERSION/common-fields projection and deferred units.',
    'assembled_service_setup.py':'Complete005 module read; real timing-planning preattachment/full-map/estimator/ledger/ports/planner freeze.',
    'resource_service_setup.py':'Complete005 module read; actual native/API adapter/shared owner setup and delayed operational unit constructor.',
    'episode_application_services.py':'Complete005 module read; factory identity and actual_tool_registry_v1 protocol.',
    'case_execution.py':'Complete module inspected in004, unchanged005 source hash; complete _load_policy/prepared_case_bindings/current run parameter consumers reread.',
    'independent_execution.py':'Complete module inspected during004; current exact known make_runtime_binding/_check_bindings/open_commission paths reread.',
    'runtime.py':'Complete affected setup inputs/call/compose and initial-list/new-run/readout paths reread; complete runtime previously inspected in004 ownership,005presentation separately retained.',
    'api_timing_records.py':'Complete pure ApiTimingBinding/as_record/from_record reread, no ledger constructed.',
    'resource_estimation.py':'Complete B-owned module inspected004; current with_reported_results/as_record/from_record reread.',
    'api_execution_planning.py':'Complete B-owned module inspected004; current constructor/owner/registry/as_record methods reread.',
    'tools.py':'Complete affected actual registry binding/schema inspected004; current bind_api_execution_planner reread.',
    'public_search_operations.py':'Complete affected describe_hmmer_client_binding/hmmer_client_binding_sha256/digest paths reread; no client created.',
    'providers.py':'Complete ModelConnection and _SessionConnection constructor/entry/complete/release paths reread; transport is lazy at complete.',
    'episode_progress_credit.py':'Complete005 module read; exact bool-rejecting ProgressInformationCredit constructor.',
    'resource_operational_credit.py':'Complete operational projection inspected earlier; complete constructor and unit validation reread.',
    'investigation_policy.py':'Complete module read in preceding custody planning; unchanged exact policy/list/controller consumers retained.',
    'episode_receipts.py':'Complete module read in preceding custody planning; unchanged forward-ref/initial baseline semantics.',
    'native_timing_information.py':'Complete module read in preceding custody planning; old attempt baselines remain separate.',
    'investigation_progress.py':'Complete affected projector read in preceding custody planning; old current findings initial baseline.',
    'tool_configuration.py':'Actual timeout/source configuration read path inspected; explicit90 matches existingdefault.',
    'acquisition.py':'Raw source file hash read for client descriptor; no acquisition method invoked. Complete affected PublicClients constructor/default timeout path read; unrelated provider methods not audited.',
}
files=[]
for name,read in readset.items():files.append({**witness(implementation/'gene_annotation_episode'/name),'inspection':read})
for name in ('AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md'):
    files.append({**witness(Path('/home/chia/repos/gene_annotation_episode')/name),
        'inspection':'Complete instructions read in current/custody/API004 task chain; unchanged hashes retained, no code edits.'})
files.append({**witness(Path('/home/chia/.codex/attachments/6c61440f-d223-4bea-91e3-6e4f7b2c5013/pasted-text-1.txt')),
    'inspection':'Complete immutable goal read; no mutation.'})
dump('B_READSET001.json',{'status':'static_read_only_no_application_constructed',
    'implementation_root':str(implementation),'files':files,
    'limits':'No original scientific DB, target sequence, provider event or actual history was opened; original metadata is from supplied P/C/root artifacts.'})
schemas=json.loads((p/'SCHEMAS.json').read_text())
for schema in schemas['$defs'].values():jsonschema.Draft202012Validator.check_schema(schema)
blue=json.loads((p/'PARAMETER_BLUEPRINT.json').read_text())['template']
validator=jsonschema.Draft202012Validator(schemas['$defs']['configured_parameters'])
assert list(validator.iter_errors(blue))
filled=json.loads(canonical(blue))
filled['policy']['scientific_progress']['initial_known_record_refs']=['input_'+'0'*24]
filled['policy']['operational']['registry_ref']='execution_registry_'+'1'*32
assert not list(validator.iter_errors(filled))
orig=json.loads((p/'ORIGINAL_CALLER_OPERANDS.json').read_text())['parameters']['policy']
def remainder(value):
    value=json.loads(canonical(value));del value['operational']['registry_ref']
    del value['scientific_progress']['initial_known_record_refs'];return value
original_rest=canonical(remainder(orig));proposed_rest=canonical(remainder(blue['policy']))
assert original_rest==proposed_rest
static_sha=hashlib.sha256(original_rest.encode()).hexdigest()
assert static_sha=='dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1'
binding=json.loads((p/'EXPECTED_PUBLIC_CLIENT_BINDING.json').read_text())
assert binding['implementation_sha256']==witness(implementation/'gene_annotation_episode'/'acquisition.py')['sha256']
binding_sha=hashlib.sha256(canonical(binding).encode()).hexdigest()
assert binding_sha==blue['services']['public_search_registry']['client_binding_sha256']
assert binding['transport_timeout_seconds']==90
dump('CHECKS001.json',{'status':'representation_static_identity_checks_passed',
    'schema_definitions':len(schemas['$defs']),'blueprint_nulls_rejected':True,
    'only_two_synthetic_field_substitutions_schema_valid':True,
    'static_policy_remainder_sha256':static_sha,'public_client_descriptor_sha256':binding_sha,
    'successful_custody_descriptor_verified_by_read_only_contract_trace':True,
    'application_imports':0,'scientific_database_opens':0,'application_tests':0,
    'factory_implementation_or_calls':0,'custody_forks':0,'HTTP_model_native_calls':0,
    'limits':'Schema/static comparisons do not prove the unimplemented factory, actual setup, filesystem path identity, reconstruction or launch.'})
print(json.dumps({'status':'static_review_checks_passed','schema_definitions':len(schemas['$defs']),
    'input_files':len(inputs),'readset_files':len(files),'application_imports':0,'scientific_database_opens':0,
    'application_tests':0},sort_keys=True))
