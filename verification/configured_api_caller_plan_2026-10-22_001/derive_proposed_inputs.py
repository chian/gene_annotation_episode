"""Plan artifacts only: stdlib, original caller JSON and pinned source bytes.

No application imports, client/Store construction, state DB, model or transport.
"""
from pathlib import Path
from copy import deepcopy
import hashlib,json,uuid,tomllib
OUT=Path('/tmp/configured-api-caller-plan-MDXd91Kz')
CODE=Path('/tmp/gene-annotation-model-context-20261022-005')
FUTURE=Path('/tmp/gene-annotation-configured-caller-20261022-006')
RUN=Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
old=json.loads((OUT/'ORIGINAL_CALLER_OPERANDS.json').read_text())
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
configuration=deepcopy(old['configuration'])
configuration.update(workspace=str(RUN/'workspace'),history=str(RUN/'statistics/run_statistics.sqlite'),restoration={'preview_size':24,'model_presentation':'bounded_wait_history_v1'})
configuration['public']={**configuration.get('public',{}),'provider_access_dir':str(RUN/'public-access'),'transport_timeout_seconds':90}
configuration['local_tools']={**configuration.get('local_tools',{}),'minimap2_cache_dir':str(RUN/'derived-cache/minimap2'),'native_receipts_dir':str(RUN/'native-execution-receipts')}
client={'version':'hmmer_public_client_binding_v1','provider':'hmmer','implementation_sha256':hashlib.sha256((CODE/'gene_annotation_episode/acquisition.py').read_bytes()).hexdigest(),'transport_timeout_seconds':90,'submit_url_prefix':'https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/','status_url_prefix':'https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/','result_url_prefix':'https://www.ebi.ac.uk/Tools/hmmer/api/v1/result/'}
p=OUT/'PROPOSED_API_REGISTRY.json'
registry=json.loads(p.read_text()) if p.exists() else {'version':'public_search_registry_v1','registry_ref':'execution_registry_'+uuid.uuid4().hex,'resource_id':'hmmer-public-prechoice','provider':'hmmer','client_binding_sha256':sha(client)}
assert registry['client_binding_sha256']==sha(client)
monitor=old['parameters']['services']['monitoring_information_unit']
assert monitor==old['parameters']['policy']['monitoring']['information_unit']==1
binding={'version':'hmmer_api_timing_binding_v1','ledger_path':str(RUN/'statistics/api-timing.sqlite'),'history_path':configuration['history'],'resource_id':registry['resource_id'],'duration_measure':'hmmer_reported_search_elapsed_seconds','observation_unit':'logical_provider_job_reported_result','compatibility':'same_exposed_technical_configuration_unknown_remote_revision','monitoring_information_unit':monitor,'scope':'new_orders_in_this_bound_run'}
marker={'version':'hmmer_api_execution_planning_v1','callable':'execution.estimate','target':'public.hmmer.search'}
services={**deepcopy(old['parameters']['services']),'version':'assembled_case_api_prechoice_v1','source_directory':str(FUTURE/'research/slotted_process_library/publications/2026-10-21-001'),'public_search_registry':registry,'api_timing':binding,'api_execution_planning':marker}
parameters={'policy':deepcopy(old['parameters']['policy']),'services':services}
parameters['policy']['scientific_progress']['initial_known_record_refs']=None
parameters['policy']['operational']['registry_ref']=None
blueprint={'status':'planning_only_not_a_runnable_parameters_document','future_code_directory':str(FUTURE),'fixed_case_directory':old['fixed_identity']['case_dir'],'new_run_directory':str(RUN),'template':parameters,'unresolved_bindings':[{'parameter_path':['policy','scientific_progress','initial_known_record_refs'],'source':'verified C result.initial_known_record_refs == loaded canonical receipt.initial_known_record_refs; exact published C destination/fixed identity'},{'parameter_path':['policy','operational','registry_ref'],'source':'NEW prepare_case_run result.registry_configuration.registry_ref'}]}
for name,v in [('PROPOSED_CALLER_CONFIGURATION.json',configuration),('PROPOSED_API_REGISTRY.json',registry),('EXPECTED_PUBLIC_CLIENT_BINDING.json',client),('PARAMETER_BLUEPRINT.json',blueprint)]:
    (OUT/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def toml(v):
    if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
    if type(v) in (bool,int,float,list):return json.dumps(v,ensure_ascii=False,allow_nan=False)
    raise ValueError('Unsupported static proposed TOML value')
def tables(v,prefix=()):
    lines=[]
    if prefix:lines.append('['+'.'.join(prefix)+']')
    for k,value in sorted(v.items()):
        if not isinstance(value,dict) and value is not None:lines.append(k+' = '+toml(value))
    for k,value in sorted(v.items()):
        if isinstance(value,dict):lines.extend(['',*tables(value,(*prefix,k))])
    return lines
text='# Proposed only; never executed. Omitted TOML wall_seconds normalizes to null via actual LocalJobPolicy.\n'+'\n'.join(tables(configuration))+'\n'
(OUT/'PROPOSED_CALLER_CONFIG.toml').write_text(text)
parsed=tomllib.loads(text)
assert parsed['local_jobs']=={'memory_bytes':21474836480,'scratch_bytes':4294967296}
parsed['local_jobs']['wall_seconds']=None
assert parsed==configuration

ref={'type':'string','pattern':'^[a-z][a-z_]*_[a-f0-9]{24,64}$'}
def closed(fields):return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
def const(v):return {'const':v}
policy={k:const(v) for k,v in old['parameters']['policy'].items()}
policy['operational']=closed({k:(ref if k=='registry_ref' else const(v)) for k,v in old['parameters']['policy']['operational'].items()})
policy['scientific_progress']=closed({k:({'type':'array','minItems':1,'uniqueItems':True,'items':ref} if k=='initial_known_record_refs' else const(v)) for k,v in old['parameters']['policy']['scientific_progress'].items()})
params_schema=closed({'policy':closed(policy),'services':closed({k:const(v) for k,v in services.items()})})
configuration_schema=closed({k:const(v) for k,v in configuration.items()})
contract={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'configured_api_prechoice_case001_parameters_plan','$defs':{'configured_parameters':params_schema,'normalized_configuration':configuration_schema,'api_registry':closed({k:const(v) for k,v in registry.items()}),'api_timing':closed({k:const(v) for k,v in binding.items()}),'planning_marker':closed({k:const(v) for k,v in marker.items()})},'description':'Closed particular new caller profile; no scientific/controller numeric change. Only final inherited refs and fresh native registry reference require actual published C/preparation outputs. This schema is planning evidence, not production code.'}
(OUT/'SCHEMAS.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n')
policy_static=deepcopy(old['parameters']['policy']);policy_static['scientific_progress'].pop('initial_known_record_refs');policy_static['operational'].pop('registry_ref')
proposed_policy_static=deepcopy(parameters['policy']);proposed_policy_static['scientific_progress'].pop('initial_known_record_refs');proposed_policy_static['operational'].pop('registry_ref')
assert canonical(policy_static)==canonical(proposed_policy_static)
checks={'status':'stdlib_plan_derivation_only','old_policy_numeric_and_semantic_remainder_sha256':sha(policy_static),'new_policy_numeric_and_semantic_remainder_sha256':sha(proposed_policy_static),'models_unchanged':configuration['models']==old['configuration']['models'],'local_limits_unchanged':configuration['local_jobs']==old['configuration']['local_jobs'],'static_service_fields_unchanged':all(services[k]==v for k,v in old['parameters']['services'].items() if k not in ('version','source_directory')),'proposed_registry_ref':registry['registry_ref'],'expected_client_binding_sha256':sha(client),'TOML_normalizes_to_declared_JSON_configuration':parsed==configuration,'remaining_unresolved_parameter_paths':[v['parameter_path'] for v in blueprint['unresolved_bindings']],'new_paths_created':False,'public_service_verified':False,'application_objects_constructed':False}
(OUT/'DERIVATION_CHECKS.json').write_text(json.dumps(checks,indent=2,sort_keys=True)+'\n')
print(json.dumps(checks,indent=2))
