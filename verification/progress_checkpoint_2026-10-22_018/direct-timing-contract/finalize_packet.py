from pathlib import Path
import hashlib,json,os,stat
from jsonschema import Draft202012Validator
root=Path('/tmp/direct-hmmer-timing-contract-R-20261022-hci0ry6b')
base=Path('/tmp/gene-annotation-configured-caller-20261022-007')
def write(name,value):
    p=root/name
    with p.open('x') as f: json.dump(value,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
def obj(properties): return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}
def const(v): return {'const':v}
def ref(v): return {'$ref':'#/$defs/'+v}
def nullable(v): return {'anyOf':[v,{'type':'null'}]}
s={'type':'string','minLength':1}; sha={'type':'string','pattern':'^[0-9a-f]{64}$'}; absolute={'type':'string','pattern':'^/'}
mode={'version':'ordinary_hmmer_reported_timing_v1','tools':['public.hmmer.search','public.hmmer.collect'],'collect':'registered_only_no_registration','page':'legacy_fresh_get','protocol':'existing_remote_search_protocol','key_version':'ordinary_hmmer_protocol_key_v1'}
d={}
d['membership']=obj({'version':const('public_search_order_membership_v1'),'job_ref':s,'registry_ref':s,'state':{'enum':['unregistered','registered','unavailable','conflict']},'code':nullable(s)})
d['membership']['oneOf']=[{'properties':{'state':const(state),'code':const(code)}} for state,code in [('unregistered',None),('registered',None),('unavailable','unknown_job'),('unavailable','public_search_storage_unavailable'),('conflict','public_search_registration_incomplete'),('conflict','identity_conflict')]]
d['failure']=obj({'code':s,'native_code':nullable(s),'phase':s,'submission_outcome':nullable(s),'prerequisite':nullable(s),'retry_after_seconds':nullable({'type':'number'}),'http_status':nullable({'type':'integer'}),'diagnostic_ref':nullable(s),'response_snapshot_ref':nullable(s),'affected_refs':{'type':'array','items':s},'partial_record_refs':{'type':'array','items':s}})
d['status_receipt']=obj({'version':const('public_search_operation_v1'),'receipt_ref':s,'operation_key':s,'selection_sha256':sha,'operation':const('status'),'registry_ref':s,'job_ref':s,'provider':const('hmmer'),'request_sha256':sha,'observed_at':s,'outcome':{'enum':['completed','failed']},'state':s,'provider_chronology':const('unknown'),'remote_id':nullable(s),'snapshot_ref':nullable(s),'result_ready':nullable({'type':'boolean'}),'result_cached':{'type':'boolean'},'result_snapshot_refs':{'type':'array','items':s},'failure':nullable(ref('failure'))})
d['status_receipt']['$comment']='Exact existing 19-field receipt; structural mirror only. Existing public read_operation and requested job/key/selection identity checks remain authoritative. No field added or coerced.'
d['status_read']=obj({'version':const('public_search_status_read_v1'),'origin':{'enum':['worker_dispatched','capture_reused','receipt_reused','no_capture']},'receipt':ref('status_receipt')})
d['direct_mode']=obj({k:const(v) for k,v in mode.items()})
d['registry']=obj({'version':const('public_search_registry_v1'),'registry_ref':s,'resource_id':s,'provider':const('hmmer'),'client_binding_sha256':sha})
d['timing_binding']=obj({'version':const('hmmer_api_timing_binding_v1'),'ledger_path':absolute,'history_path':absolute,'resource_id':s,'duration_measure':const('hmmer_reported_search_elapsed_seconds'),'observation_unit':const('logical_provider_job_reported_result'),'compatibility':const('same_exposed_technical_configuration_unknown_remote_revision'),'monitoring_information_unit':{'type':'number','exclusiveMinimum':0},'scope':const('new_orders_in_this_bound_run')})
d['ledger']=obj({'version':const('api_timing_ledger_v1'),'run_id':s,'store_path':absolute,'registry':ref('registry'),'binding':ref('timing_binding')})
d['estimator']=obj({'version':const('resource_tool_duration_estimator_v3'),'method':const('exact_class_current_condition_successful_duration_mean'),'reported_result_method':const('exact_exposed_configuration_current_condition_reported_duration_mean_v1')})
d['planner']=obj({'version':const('hmmer_api_execution_planner_v1'),'ledger':ref('ledger'),'resource_estimator':ref('estimator'),'callable':const('execution.estimate'),'target':const('public.hmmer.search'),'preparation_version':const('hmmer_request_preparation_v1'),'implementation_sha256':sha,'preparation_sha256':sha})
d['reader']=obj({'version':const('api_reported_timing_fact_reader_v1'),'ledger':ref('ledger')})
d['direct_binding']=obj({'version':const('ordinary_hmmer_reported_timing_binding_v1'),'configuration':ref('direct_mode'),'planner':ref('planner'),'reader':ref('reader'),'poll_interval_seconds':{'type':'number','minimum':0},'implementation_sha256':sha})
d['key_operands']=obj({'registry_ref':s,'job_ref':s,'parent_operation_key':s,'operation':{'enum':['submit','status','result','recover_submission']},'ordinal':{'type':'integer','minimum':0},'page':nullable({'type':'integer','minimum':1}),'page_size':nullable({'type':'integer','minimum':1})})
d['key_operands']['oneOf']=[{'properties':{'operation':{'enum':['submit','recover_submission']},'ordinal':const(0),'page':const(None),'page_size':const(None)}},{'properties':{'operation':const('status'),'page':const(None),'page_size':const(None)}},{'properties':{'operation':const('result'),'ordinal':const(0),'page':const(1),'page_size':{'type':'integer','minimum':1}}}]
d['key_operands']['$comment']='Python API additionally requires exact int (not bool), strings stripped/no controls; pure helper validates before canonicalization. Key is ordinary-hmmer-v1:<fullSHA256>:<operation>:<ordinal>:<page-or->:<size-or->.'
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:gene-annotation:direct-hmmer-timing-ports:1','$comment':'Adopted CONTRACT001 port shapes. Cross-record exact original identities, same-instance owners, finite-number/nonbool validation and operation semantics are mandatory in CONTRACT001; schema does not infer provenance or authorize work.','oneOf':[ref('membership'),ref('status_read'),ref('direct_mode'),ref('direct_binding')],'$defs':d}
Draft202012Validator.check_schema(schema)
write('PORT_SCHEMAS001.json',schema)
checks=[]
for st,co in [('unregistered',None),('registered',None),('unavailable','unknown_job'),('unavailable','public_search_storage_unavailable'),('conflict','public_search_registration_incomplete'),('conflict','identity_conflict')]:
    v={'version':'public_search_order_membership_v1','job_ref':'job_fixture','registry_ref':'registry_fixture','state':st,'code':co}
    Draft202012Validator(schema).validate(v); checks.append({'case':'membership_'+st+'_'+str(co),'expected':'valid'})
for st,co in [('unregistered','unknown_job'),('registered','identity_conflict'),('conflict',None),('unavailable',None)]:
    v={'version':'public_search_order_membership_v1','job_ref':'job_fixture','registry_ref':'registry_fixture','state':st,'code':co}
    assert list(Draft202012Validator(schema).iter_errors(v)); checks.append({'case':'membership_'+st+'_'+str(co),'expected':'invalid'})
Draft202012Validator(schema).validate(mode)
assert list(Draft202012Validator(schema).iter_errors({**mode,'extra':True}))
checks += [{'case':'exact_direct_mode','expected':'valid'},{'case':'extra_direct_mode_field','expected':'invalid'}]
write('SCHEMA_CHECKS001.json',{'version':'direct_hmmer_plan_schema_checks_v1','kind':'stdlib/static schema authoring check; no application import or runtime verification','checks':checks,'schema_valid':True,'receipt_named_field_count':len(d['status_receipt']['properties'])})
handoffs={'version':'direct_hmmer_exact_owner_handoffs_v1','status':'root has adopted CONTRACT001; no implementation by this author yet','contract_sha256':'7192312bc549d6fab55d619406f7548b25d34a75ee59ec1959bbf5de4cfbe034','count_clarification':'CONTRACT001 calls the original receipt 20-field; actual read_operation enumerates 19 named fields. PORT_SCHEMAS001 preserves those exact19 unchanged; this is a count-only correction.','constants':{'DIRECT_MODE':mode,'DIRECT_BINDING_VERSION':'ordinary_hmmer_reported_timing_binding_v1','KEY_VERSION':'ordinary_hmmer_protocol_key_v1'},'A':{'files':['public_search_operations.py'],'exports':['ProviderJobOperations.classify_order(self, job_ref: str) -> dict','ProviderJobOperations.status_once_with_origin(self, job_ref: str, *, operation_key: str) -> dict'],'schema_definitions':['membership','status_read'],'constraints':'Same _observe branch authority; old receipt unchanged; readonly membership and all partial/corrupt classifications per CONTRACT001.'},'B':{'files':['direct_hmmer_timing.py (new)','tools.py'],'exports':['DirectHmmerTiming(planner: ApiExecutionPlanner, *, reader: ApiReportedTimingFactReader)','DirectHmmerTiming.as_record() -> dict','DirectHmmerTiming.validate_registry(tool_registry: ToolRegistry) -> None','DirectHmmerTiming.acquire(tool: str, arguments: dict, *, scope: dict, operation_key: str) -> DirectHmmerAcquisition','direct_operation_key(*, registry_ref: str, job_ref: str, parent_operation_key: str, operation: str, ordinal: int, page: int | None, page_size: int | None) -> str','ToolRegistry.bind_api_direct_hmmer_timing(binding) -> DirectHmmerTiming'],'schema_definitions':['direct_mode','direct_binding','key_operands'],'carrier_fields':['snapshot','failure','api_timing_disposition','api_timing_refs','provider_operation_refs'],'same_owner_attributes':['planner','reader'],'constraints':'No new timing/scoring records; original provider result publication via existing ordinary importer. B exposes actual DirectHmmerTiming.planner and .reader for C ownership checks; planner already exposes .ports and .timing.'},'C':{'files':['assembled_service_setup.py','resource_service_setup.py','hmmer_resource_adapter.py','episode_services.py','episode_composition.py','api_planning_case_policy.py'],'factory':'bind_assembled_services_with_public_search_timing_planning_direct','caller_services_version':'assembled_case_api_prechoice_direct_timing_v1','adapter_version':'hmmer_service_resource_adapter_v4','new_optional_forward_operand':'api_direct_timing=None','adapter_extra_field':'ordinary_hmmer_timing','constraints':'Construct actual same planner/ports/ledger/reader/direct; attach before catalog freeze; reconstruct replacement handles and require complete equal records; v1-v3 and absent caller marker unchanged.'},'root':{'production_files':[],'tests':'actual Workflow receipt/union/failure cuts/future explicit APIforecast and actual fixed_case detached worker after coherent freeze'},'existing_definitions':'registry/timing_binding/ledger/estimator/planner/reader are structural mirrors of existing as_record; actual from_record/type/current-owner checks remain authoritative, no second schema or changed semantics.'}
write('HANDOFFS001.json',handoffs)
old=json.loads((root/'DRAFT_READSET001.json').read_text())
scopes={
'public_search_operations.py':'complete actual module; order/open/inspect/read_operation/read_snapshot/select/claim/submit/recover/_observe/status/result and receipt/capture branches',
'provider_jobs.py':'complete actual module, especially RemoteSearches.search/collect/page, job identity, submit/status/result protocol and original sleeps',
'assembled_service_setup.py':'complete module; all legacy/API timing/planning factories and common bind order',
'api_planning_case_policy.py':'complete module; strict finite JSON, fields/units/base policy projection, uninvoked actual setup and saved definition',
'resource_service_setup.py':'complete module; actual adapter forwarding and registry/client/map identity',
'hmmer_resource_adapter.py':'complete actual adapter behavior in preceding integration read; constructor/as_record/prepare/catalog/acquire/results/current decision context rechecked for this contract',
'episode_composition.py':'complete composition/reconstruction module; v1-v3 API re-open and replacement handles/reader selection rechecked',
'episode_services.py':'complete existing services API; public_search_ports, planner attachment, reference/receipt qualification',
'episode_application_services.py':'complete module; actual-tool-registry setup argument ownership and saved service definition',
'api_execution_planning.py':'complete existing planner in prior implementation/review; constructor/owner/as_record/input/result validation and actual ports rechecked here',
'api_timing_information.py':'complete existing reader/received union in prior implementation/review; exact reader.as_record and publication/scope validation rechecked here',
'api_timing_records.py':'complete existing ledger in previous custody boundary read; exact owner/as_record/receive_result/disposition types rechecked here',
'api_reported_statistics.py':'complete existing typed reported-result statistics in previous integration review; unchanged reuse only',
'run_statistics.py':'typed reported-result identities/export/compatible-class support consumers; unchanged, not new numerical law',
'resource_estimation.py':'actual v3 as_record/with_reported_results and estimate_reported_context unchanged consumers',
'case_execution.py':'actual _load_policy/PolicyBindings/prepared_case_bindings/load saved case paths; no new format needed',
'assembled_case_policy.py':'complete base caller validation/setup factory and exact base services projection',
'independent_execution.py':'actual _check_bindings/reconstruct_worker/known-worker paths and exact services/estimator/map/parameters/source pin checks',
'application_execution_binding.py':'complete actual worker/runtime descriptor binding in prior reconstruction review; current source unchanged',
'episode_journal.py':'saved original own decisions/outcomes and replay early-return consumers; unchanged',
'scientific_tool_library.py':'complete freeze/map validation and actual retrieval-catalog shape; no new capability outside actual map',
'scientific_process_setup.py':'complete actual scientific setup builder and its service forwarding',
'hmmer_request_preparation.py':'complete shared selected-operand preparation; no inferred algorithm/database/query length',
'hmmer_resource_information.py':'actual public registry/selection/result/publication definitions; ordinary importer intentionally separate',
'tools.py':'constructor/resource_binding/catalog/bind/execute_async/_execute_operation_async/_acquire_async public HMMER/_perform/_save/ordinary importer complete affected methods; whole170KB file is hashed, unrelated tool branches not newly audited',
'runtime.py':'complete affected DecisionSource.execute admission/replay and Workflow received union/own explicit proposal/working-state/facts consumers from prior integration; whole271KB file hashed, no proposed change',
'acquisition.py':'actual SourceSnapshot/AcquisitionError/HMMER client submit/status/result/metadata and HTTP structured errors; unrelated acquisition sources not reaudited',
'state.py':'actual read_snapshot/get_artifact/transaction public read paths and source/artifact registration consumers; unrelated Store operations not reaudited',
'domain.py':'actual canonical/json_value/identity/scope helpers and reference contracts; unrelated scientific types not reaudited',
'tool_configuration.py':'complete actual client binding descriptor and normalized finite configuration'}
files=[]
for p,desc in old['files'].items():
    b=Path(p).read_bytes(); st=Path(p).stat(); assert hashlib.sha256(b).hexdigest()==desc['sha256']
    name=Path(p).name
    extent=scopes.get(name,'complete normative text or sealed prior plan read in this task/prior continuous task; exact unchanged bytes verified')
    files.append({'path':p,**desc,'semantic_extent':extent,'hash_verified_final':True})
write('READSET_FINAL001.json',{'version':'direct_hmmer_semantic_readset_v1','source_basis':str(base),'runtime_pin':'3805ed95de6e84ac90e31fe89ee07621822a316f766cc72764154b7205ba81e3','semantic_read_scope':'Affected complete implementation methods and original public producer/consumer paths; hashing a module is not a claim to newly audit unrelated methods. Prior continuous-task reads are identified.','files':files,'application_imports':0,'database_opens':0,'network_calls':0,'model_calls':0,'native_jobs':0,'source_edits':0})
write('RESULTS_FINAL001.json',{'version':'direct_hmmer_contract_packet_v1','status':'code-ready exact contracts; implementation awaits root explicit frozen008 workload handoff','contract_sha256':handoffs['contract_sha256'],'schema_check_count':len(checks),'runtime_tests_run':0,'source_and_database_changes':0,'preserved_original_members':['SCOPE001.json','CONTRACT001.md','DRAFT_READSET001.json'],'known_limit':'Current-evidence membership cannot distinguish wholly erased registration evidence; fallback collect cannot register or export typed timing.','count_only_correction':handoffs['count_clarification'],'no_unresolved_numerical_choice':True})
print('packet content ready')
