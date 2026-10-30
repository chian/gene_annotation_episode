"""Read-only validation and token-free staging; no application imports or calls."""
from pathlib import Path
from contextlib import contextmanager
from collections import Counter
from datetime import datetime,timezone
from http.cookies import SimpleCookie
from urllib.parse import quote,quote_plus
import hashlib,json,sqlite3,re,shutil,os,sys,traceback
E=Path('/tmp/hmmer-reported-timing-service-verification-20261022-001')
W=Path('/tmp/hmmer-reported-timing-fixed-target-20261022-001')
O=Path('/tmp/hmmer-reported-timing-publication-20261022-001')
C=Path('/tmp/gene-annotation-hmmer-api-20261022-003')
PIN='cde521578e4531b93dcbe9e33eaf58881db867c0664c3cb9af93107d549e2623'
UNIT='logical_provider_job_reported_result';MEASURE='hmmer_reported_search_elapsed_seconds'
def load(p):return json.loads(p.read_bytes())
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(v):return sha(canon(v).encode())
def ensure(v,code):
    if not v:raise ValueError(code)
def inventory(root):
    return {str(p.relative_to(root)):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'mode':oct(p.stat().st_mode&0o777)} for p in sorted(root.rglob('*')) if p.is_file()}
@contextmanager
def ro(path):
    d=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=0);d.row_factory=sqlite3.Row
    try:
        d.execute('PRAGMA query_only=ON');d.execute('BEGIN');yield d;d.rollback()
    finally:d.close()
def rows(d,n):return [dict(r) for r in d.execute('SELECT * FROM '+n)]
def one(d,n):
    r=rows(d,n);ensure(len(r)==1,'one_'+n+'_required');return json.loads(r[0]['data'])
def artifact(ref):
    ensure(ref.startswith('artifact_'),'artifact_ref_required');name=ref[9:]
    body=(W/'artifacts'/name[:2]/name).read_bytes();ensure(sha(body)==name,'artifact_digest_mismatch');return body
# Extract private session values and common encodings in memory. No value is
# printed, saved in a derivative, or included in failure diagnostics.
secrets=set()
for p in W.rglob('*'):
    if not p.is_file() or p.name in {'state.sqlite3','state.sqlite3-wal','state.sqlite3-shm'}:continue
    raw=p.read_bytes()
    for match in re.finditer(rb'(?i)sessionid\s*=\s*([^;\s,"\\]+)',raw):
        value=match.group(1).decode('utf-8');secrets.add(value)
ensure(bool(secrets),'private_session_witness_required')
secret_forms=set()
for s in secrets:
    for v in (s,quote(s,safe=''),quote_plus(s,safe=''),json.dumps(s)[1:-1]):secret_forms.add(v.encode())
def safe(body):return not any(s in body for s in secret_forms)
def transport_object(v):
    if isinstance(v,dict):
        return any(str(k).lower() in {'transport','headers','response_headers','request_headers','cookie','cookies','set-cookie','authorization'} for k in v) or any(transport_object(x) for x in v.values())
    if isinstance(v,list):return any(transport_object(x) for x in v)
    return False
b=load(E/'selected-binding.json');job=b['order']['job_ref'];registry=b['registry'];request=b['request'];seed=b['seed']
ensure(job=='provider_job_24b52ef96a8fee7bd0799340','selected_job_mismatch')
ensure(b['sources']['runtime_implementation_sha256']==PIN,'selected_pin_mismatch')
ensure(request['algorithm']=='phmmer' and request['database']=='pdb' and request['parameters']=={} and request['page_size']==2 and request['query_length']==253,'selected_search_mismatch')
ensure(request['subject_ref']==b['product_ref'] and request['sequence_sha256']==b['protein_sha256']=='f0cdd3744b5bc986fd574175ecb7155c0ed57c7749098f20300735a3c849560a','protein_identity_mismatch')
ensure(b['protein_length']==253 and len(artifact(b['product_record']['sequence_ref']))==253,'protein_length_mismatch')
ensure(sha(artifact(b['order']['query_fasta_ref']))==b['submitted_fasta_sha256']==request['query_sha256'],'submitted_fasta_mismatch')
ensure(json.loads(artifact(b['order']['request_ref']))==request and digest(request)==b['order']['request_sha256'],'request_identity_mismatch')
ensure(sha((W/'fixed-target-seed.json').read_bytes())==b['seed_receipt_sha256'] and load(W/'fixed-target-seed.json')==seed,'seed_receipt_mismatch')
ensure(seed['fixed_identity']['dna_length_nt']==762 and seed['fixed_identity']['protein_length_aa']==253 and seed['fixed_identity']['source_protein']=='P0AAW1','fixed_target_seed_mismatch')
ensure(seed['verification']['sqlite_reader_bookkeeping']['authoritative_bytes_unchanged'] and seed['verification']['sqlite_reader_bookkeeping']['observed_changes']==[],'seed_original_preservation_not_recorded')
ensure(b['translation_arguments']=={'cds':True,'code':11,'end':762,'frame':0,'start':0,'strand':'+','subject_ref':seed['fixed_identity']['target_ref']},'translation_operands_mismatch')
ensure(b['local_limits']=={'memory_bytes':21474836480,'scratch_bytes':4294967296,'wall_seconds':None} and b['client_binding']['transport_timeout_seconds']==90,'caller_limits_mismatch')
source_map=b['sources']['source_files'];source_hash=hashlib.sha256()
for name,expected in sorted(source_map.items()):
    raw=(C/name).read_bytes();ensure(sha(raw)==expected,'current_source_file_mismatch');source_hash.update(name.encode()+b'\0');source_hash.update(hashlib.sha256(raw).digest())
ensure(source_hash.hexdigest()==PIN,'source_map_pin_mismatch')
phases=[]
for p in sorted((E/'invocations').iterdir()):
    intent=load(p/'intent.json');guard=load(p/'sources-after.json')
    ensure(intent['sources']==b['sources'] and guard=={'identity':b['sources'],'unchanged':True},'phase_source_guard_mismatch')
    ensure(intent['script_sha256']==sha((E/'verify_hmmer_reported_timing.py').read_bytes()),'phase_script_hash_mismatch')
    ensure(not (p/'failure.json').exists(),'actual_phase_failure_present')
    result=load(p/'result.json')['result'];selected=result.get('outcome')
    if selected is not None:ensure(selected==load(p/'selected-outcome.json'),'selected_outcome_mismatch')
    phases.append({'directory':p.name,'intent':intent,'result':result,'outcome':selected})
ensure(len(phases)==13,'thirteen_explicit_phases_required')
reports=[v for v in phases if v['intent']['arguments']['phase']=='timing-report']
ensure(len(reports)==4,'four_timing_reports_required')
initial=reports[0]['outcome'];later=[v['outcome'] for v in reports[1:]]
ensure(initial['reported_result_count']==initial['native_attempt_count']==0 and initial['timing_source_refs']==[] and initial['api_execution_measurements']==[],'initial_empty_history_mismatch')
initial_snapshot=initial['expectation_capture']['snapshots'][0]
ensure(initial_snapshot['data']['history_through_sequence']==0 and initial_snapshot['data']['statistics']==[],'initial_snapshot_not_empty')
ensure(initial['forecast'][0]['status']=='no_matching_history' and initial['forecast'][0]['reported_result_support']=={'reported_result_count':0} and initial['forecast'][0]['expected_total_seconds'] is None,'initial_forecast_mismatch')
with ro(W/'state.sqlite3') as d:
    tables={r[0] for r in d.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    ensure(not any(n.startswith('runtime_') for n in tables),'runtime_tables_present')
    records={r['id']:json.loads(r['data']) for r in d.execute('SELECT id,data FROM records')}
    counts=dict(Counter(v['record_type'] for v in records.values()))
    ensure(not any(counts.get(n,0) for n in ('hypothesis','assessment','annotation','interpretation_account','native_execution')),'scientific_or_native_record_present')
    ensure(one(d,'public_search_orders')==b['order'] and one(d,'public_search_order_scopes')==b['order_scope'] and one(d,'public_search_registries')==registry,'original_order_binding_mismatch')
    ensure(records[b['product_ref']]==b['product_record'],'actual_product_record_mismatch')
    artifact_rows=rows(d,'artifacts')
    for r in artifact_rows:ensure(len(artifact(r['id']))==r['size'] and sha(artifact(r['id']))==r['sha256'],'artifact_metadata_mismatch')
    provider=rows(d,'provider_jobs');ensure(len(provider)==1 and provider[0]['id']==job and provider[0]['state']=='returned' and provider[0]['error_code'] is None,'provider_job_state_mismatch')
    ensure(json.loads(provider[0]['request'])==request,'provider_request_mismatch');remote=provider[0]['remote_id']
    operations={r['id']:json.loads(r['data']) for r in d.execute('SELECT id,data FROM public_search_operations')}
    ensure(len(operations)==5 and len(rows(d,'public_search_claims'))==1 and len(rows(d,'public_search_selections'))==5,'provider_operation_count_mismatch')
    ensure(all(v['job_ref']==job and v['registry_ref']==registry['registry_ref'] and v['remote_id']==remote and v['request_sha256']==b['order']['request_sha256'] and v['outcome']=='completed' and v['failure'] is None for v in operations.values()),'operation_qualification_mismatch')
    submit=[v for v in operations.values() if v['operation']=='submit'];ensure(len(submit)==1,'one_original_submit_required');submit=submit[0]
    ensure(submit['receipt_ref']=='provider_operation_108552079e6545474a0b84b7' and submit['observed_at']=='2026-10-22T07:30:22.356238+00:00','original_submit_timestamp_mismatch')
    submit_phases=[v['outcome'] for v in phases if v['intent']['arguments']['phase']=='submit_once'];ensure(submit_phases==[submit,submit],'submission_replay_not_original_receipt')
    status=[v for v in operations.values() if v['operation']=='status'];ensure(len(status)==1 and status[0]['state']=='SUCCESS','actual_success_status_missing')
    result_rows=rows(d,'public_search_results');ensure({(r['page'],r['page_size']) for r in result_rows}=={(1,2),(2,2)},'page_selector_coverage_mismatch')
    snapshots={ref:json.loads(artifact(v['snapshot_ref'])) for ref,v in operations.items()}
    manifests=list((W/'public-search-http-captures').glob('*/manifest.json'));ensure(len(manifests)==4,'four_selected_http_captures_required')
    capture_summary=[]
    for p in manifests:
        v=load(p);body=(p.parent/v['snapshot']['content_file']).read_bytes()
        ensure(v['job_ref']==job and v['registry_ref']==registry['registry_ref'] and sha(body)==v['snapshot']['content_sha256'] and len(body)==v['snapshot']['content_bytes'],'capture_entity_mismatch')
        receipt=next(x for x in operations.values() if x['operation_key']==v['operation_key'])
        snapshot=snapshots[receipt['receipt_ref']]
        ensure(artifact(snapshot['content_ref'])==body and snapshot['retrieved_at']==v['snapshot']['retrieved_at'],'snapshot_capture_mismatch')
        ensure(receipt['selection_sha256']==v['selection_sha256'],'selected_capture_identity_mismatch')
        capture_summary.append({'operation':v['operation'],'operation_key':v['operation_key'],'receipt_ref':receipt['receipt_ref'],'observed_at':receipt['observed_at'],'retrieved_at':snapshot['retrieved_at'],'entity_sha256':sha(body),'entity_bytes':len(body),'private_capture_manifest':str(p)})
    original_results={r['page']:operations[r['receipt_ref']] for r in result_rows}
    cached=next(v['outcome'] for v in phases if v['intent']['arguments']['operation_key'].endswith(':cached-page-1'))
    ensure(cached['snapshot_ref']==original_results[1]['snapshot_ref'] and cached['receipt_ref']!=original_results[1]['receipt_ref'],'cached_page_original_capture_mismatch')
    ensure(len({x['snapshot_ref'] for x in operations.values()})==4,'cached_read_added_capture')
    publications=rows(d,'public_search_publications');ensure(len(publications)==2,'two_publications_required')
    publication_summary=[]
    for r in publications:
        published=json.loads(r['data']);v=published['result'];page=v['page'];receipt=original_results[page]
        ensure(v['acquisition_receipt_ref']==receipt['receipt_ref'] and v['page_size']==2 and not v['projection_failures'],'biological_publication_mismatch')
        proof=records[v['publication_ref']];body=json.loads(artifact(proof['artifact_ref']))
        ensure(body['publication_rows']==v['publication_rows'] and body['source_ref']==v['source_ref'] and body['job_ref']==job and body['request_sha256']==b['order']['request_sha256'],'publication_proof_mismatch')
        ensure(body['selector']=={'version':'public_search_result_selector_v1','provider':'hmmer','first_page':page,'last_page':page,'page_size':2},'publication_selector_mismatch')
        native=json.loads(artifact(snapshots[receipt['receipt_ref']]['content_ref']));hits=native['result']['hits']
        refs={row['hit_ordinal']:row['record_ref'] for row in v['publication_rows'] if row['record_type']=='reference'}
        for row in v['publication_rows']:
            rec=records[row['record_ref']];idx=row['hit_ordinal'];dom=row['domain_ordinal']
            ensure(row['record_ref'] in published['record_refs'] and row['source_ref']==rec['source_ref']==v['source_ref'] and row['job_ref']==job and row['acquisition_receipt_ref']==receipt['receipt_ref'] and 0<=idx<len(hits),'publication_row_identity_mismatch')
            ensure(row['record_type']==rec['record_type'],'publication_record_type_mismatch')
            if rec['record_type']=='reference':ensure(dom is None,'reference_domain_ordinal_mismatch')
            else:ensure(dom is not None and 0<=dom<len(hits[idx].get('domains',[])) and rec['subject_refs']==[b['product_ref']] and rec['source_subject_refs']==[refs[idx]],'observation_witness_mismatch')
        source=records[v['source_ref']]
        publication_summary.append({'page':page,'page_count':v['page_count'],'record_ref_count':len(published['record_refs']),'row_witness_count':len(v['publication_rows']),'reference_witness_count':len(refs),'observation_witness_count':sum(x['record_type']=='observation' for x in v['publication_rows']),'hit_count':len(hits),'domain_counts':[len(h.get('domains',[])) for h in hits],'projection_failure_count':len(v['projection_failures']),'publication_ref':v['publication_ref'],'source_ref':v['source_ref'],'source_version':source['version']})
    ensure({r['page_count'] for r in publication_summary}=={2},'provider_two_page_count_mismatch')
    ensure(len(rows(d,'tool_operations'))==1 and len(rows(d,'reasoning_commits'))==0,'unexpected_tool_or_reasoning_work')
    store_export={'version':'actual_service_logical_store_export_v1','records':list(records.values()),'inputs':[json.loads(r['data']) for r in rows(d,'inputs')],'problem':json.loads(rows(d,'problem')[0]['data']),'artifact_metadata':artifact_rows,'orders':[b['order']],'order_scopes':[b['order_scope']],'registries':[registry],'claims':[json.loads(r['data']) for r in rows(d,'public_search_claims')],'operations':list(operations.values()),'results':result_rows,'publications':[{'operation_key':r['operation_key'],'data':json.loads(r['data']),'signature':json.loads(r['signature'])} for r in publications],'provider_job':{k:provider[0][k] for k in ('id','operation_key','state','remote_id','error_code')},'provider_request':request,'omitted_provider_snapshot_columns':['submission','latest_status','result'],'tool_operations':[{**r,'arguments':json.loads(r['arguments']),'scope':json.loads(r['scope']),'result':json.loads(r['result'])} for r in rows(d,'tool_operations')]}
with ro(E/'api-timing.sqlite3') as d:
    owner=one(d,'api_timing_bindings');order=one(d,'api_timing_orders');intent=one(d,'api_timing_submission_intents');submission=one(d,'api_timing_submission_bindings');witness=one(d,'api_timing_measurements');exported=one(d,'api_timing_export_dispositions')
    ensure(owner==b['timing_ledger'],'timing_owner_mismatch')
    ensure(order['job_ref']==job and order['request_sha256']==b['order']['request_sha256'] and order['scope']==b['scope'],'timing_order_mismatch')
    ensure(submission['submission_receipt_ref']==submit['receipt_ref'] and submission['submission_operation_key']==submit['operation_key'] and submission['observed_at']==submit['observed_at'] and submission['remote_id']==remote and submission['intent_state']=='matched','winning_submit_binding_mismatch')
    ensure(intent['submission_operation_key']==submit['operation_key'] and intent['intent_ref']==submission['intent_ref']==witness['intent_ref'] and intent['order_binding_ref']==order['binding_ref']==witness['order_binding_ref'],'winning_intent_mismatch')
    start=intent['start_context'];ensure(start['condition_capture']=='captured_before_submission' and start['condition_ref'] is None and witness['start_context']==start,'known_original_start_mismatch')
    ensure(witness['submission_binding_ref']==submission['binding_ref'] and witness['acquisition_receipt_ref']==original_results[1]['receipt_ref'] and witness['snapshot_ref']==original_results[1]['snapshot_ref'] and witness['observed_at']==original_results[1]['observed_at'],'first_witness_custody_mismatch')
    for page,receipt in original_results.items():
        stats=json.loads(artifact(snapshots[receipt['receipt_ref']]['content_ref']))['result']['stats'];database=stats['database'];database=database.get('id') if isinstance(database,dict) else database
        ensure(stats['id']==remote and stats['algo']=='phmmer' and database=='pdb' and stats['elapsed']==witness['elapsed_seconds'],'reported_page_duration_identity_mismatch')
    ensure(witness['elapsed_seconds']==0.22888848185539246 and witness['duration_measure']==MEASURE and witness['observation_unit']==UNIT,'named_duration_mismatch')
    ensure(exported['state']=='recorded' and exported['code'] is None,'typed_export_unavailable')
    ledger_export={'version':'actual_service_logical_timing_ledger_export_v1','tables':{n:rows(d,n) for n in ['api_timing_bindings','api_timing_orders','api_timing_submission_intents','api_timing_submission_bindings','api_timing_measurements','api_timing_export_dispositions']}}
with ro(E/'reported-statistics.sqlite3') as d:
    statistic=one(d,'reported_result_statistics');scope=one(d,'execution_classes');sr=rows(d,'reported_result_statistics')[0]
    ensure(len(rows(d,'run_statistics'))==0 and len(rows(d,'execution_conditions'))==0,'native_or_condition_row_unexpected')
    identity={'version':'hmmer_reported_result_observation_v1','registry_ref':registry['registry_ref'],'remote_id':remote,'observation_unit':UNIT};observation=digest(identity)
    ensure(statistic['observation_sha256']==observation==exported['observation_sha256'] and witness['measurement_ref']=='api_reported_duration_'+observation,'logical_result_identity_mismatch')
    ensure(statistic['source_sha256']==digest(witness) and statistic['observed_at']==witness['observed_at'] and statistic['elapsed_seconds']==witness['elapsed_seconds'] and statistic['condition_ref'] is None and sr['condition_state']=='unspecified','typed_statistic_first_witness_mismatch')
    ensure(scope==start['execution_class'] and sr['class_ref']==start['execution_class_ref']==exported['execution_class_ref']=='execution_class_'+digest(scope),'typed_class_mismatch')
    ensure(scope['phase']=='remote_protein_homology_search' and scope['backend']=='https' and scope['query_residues']==253 and scope['reference_state']=='unknown' and scope['duration_measure']==MEASURE,'remote_class_qualification_mismatch')
    ensure(all(scope[k] is None for k in ('implementation_sha256','memory_bytes','scratch_bytes','cpu_threads','reference_residues','reference_records','wall_seconds')),'invented_remote_operands')
    snapshots={r['id']:json.loads(r['data']) for r in rows(d,'expectation_snapshots')};ensure(len(snapshots)==2 and snapshots[initial_snapshot['ref']]==initial_snapshot['data'],'original_expectation_snapshot_changed')
    for value in later:
        ensure(value['reported_result_count']==1 and value['native_attempt_count']==0 and value['timing_source_refs']==['source_0b67cd939f50d78539ced326'],'repeated_result_count_or_source_changed')
        forecast=value['forecast'][0];fact=value['api_execution_measurements'][0]
        ensure(forecast['status']=='available' and forecast['reported_result_support']=={'reported_result_count':1} and forecast['successful_duration_samples']==1 and forecast['expected_total_seconds']==witness['elapsed_seconds'] and forecast['outcome_support'] is None and forecast['job_ref'] is None and forecast['sample_ref'] is None and forecast['elapsed_seconds'] is None and forecast['timing_relation']=='unknown','reported_forecast_support_mismatch')
        ensure(fact=={'receipt_ref':'source_0b67cd939f50d78539ced326','job_ref':job,'duration_measure':MEASURE,'observation_unit':UNIT,'elapsed_seconds':witness['elapsed_seconds'],'observed_at':witness['observed_at']},'actual_reader_fact_mismatch')
    history_export={'version':'actual_service_logical_reported_history_export_v1','tables':{n:rows(d,n) for n in ['execution_classes','execution_conditions','reported_result_statistics','run_statistics','expectation_snapshots']}}
source=records['source_0b67cd939f50d78539ced326'];body=json.loads(artifact(source['artifact_ref']))
ensure(body=={'version':'api_reported_timing_source_v1','run_id':owner['run_id'],'scope':b['scope'],'subject_ref':b['product_ref'],'witness':witness},'timing_source_body_mismatch')
payload={k:v for k,v in source.items() if k not in {'id','record_type','origin'}}
ensure(source['id']=='source_'+digest({'origin':'tool','record':payload})[:24] and source['origin']=='tool' and source['provider']=='episode.hmmer_reported_timing' and source['retrieved_at']==witness['observed_at'] and source['text_ref'] is None and source['request_ref'] is None and source['operand_refs']==[b['product_ref']],'timing_source_metadata_mismatch')
# Seed references remain concrete in the new workspace; original canonical
# source preservation is attested by the copied receipt, never re-opened here.
ensure(len(seed['intake_records'])==len(seed['initial_known_record_refs'])==11,'seed_reference_count_mismatch')
for r in seed['artifact_manifest']:ensure(len(artifact(r['id']))==r['size'] and sha(artifact(r['id']))==r['sha256'],'seed_artifact_mismatch')
S=O/'staged';ensure(not S.exists(),'stage_must_be_new');S.mkdir(mode=0o700)
def put(relative,data):
    body=data if isinstance(data,bytes) else (json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    ensure(safe(body),'session_material_in_staged_output');p=S/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
copy_map=[];omissions=[]
for root,label in ((E,'phase-evidence'),(W,'workspace')):
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(root);raw=p.read_bytes();reason=None
        if '.sqlite3' in p.name:reason='raw_database_or_SQLite_bookkeeping_omitted'
        elif p.name=='manifest.json' and 'public-search-http-captures' in p.parts:reason='raw_transport_capture_manifest_omitted'
        elif 'locks' in p.parts:reason='local_lock_bookkeeping_omitted'
        elif '__pycache__' in p.parts:reason='syntax_bytecode_cache_omitted'
        elif not safe(raw):reason='credential_bearing_original_omitted'
        else:
            try:v=json.loads(raw)
            except (ValueError,UnicodeError):v=None
            if transport_object(v):reason='raw_transport_snapshot_metadata_omitted'
        mapping={'private_path':str(p),'sha256':sha(raw),'bytes':len(raw)}
        if reason:omissions.append({**mapping,'reason':reason})
        else:
            name=str(Path(label)/rel);put(name,raw);copy_map.append({**mapping,'published_path':name,'representation':'exact_original_bytes'})
put('logical/store.json',store_export);put('logical/timing-ledger.json',ledger_export);put('logical/reported-history.json',history_export)
put('logical/timing-source.json',{'record':source,'body':body});put('logical/first-witness.json',witness)
put('ORIGINAL_TO_PUBLIC.json',{'version':'credential_free_original_mapping_v1','copied_originals':copy_map,'omitted_originals':omissions,'redacted_derivatives':[],'custody_limit':'Partial token-free derivative; original references to omitted databases/transport artifacts remain unchanged and do not fully resolve in this publication.'})
phase_summary=[{'directory':v['directory'],'arguments':v['intent']['arguments'],'selected_at':v['intent']['selected_at'],'source_pin':PIN,'script_sha256':v['intent']['script_sha256']} for v in phases]
summary={'version':'actual_reported_timing_read_only_checks_v1','validated_at':datetime.now(timezone.utc).isoformat(),'source_pin':PIN,'source_file_count':len(source_map),'script_sha256':sha((E/'verify_hmmer_reported_timing.py').read_bytes()),'phase_count':13,'actual_phase_failure_count':0,'fixed_identity':seed['fixed_identity'],'product_ref':b['product_ref'],'request':request,'request_sha256':b['order']['request_sha256'],'submitted_fasta_sha256':b['submitted_fasta_sha256'],'registry':registry,'job_ref':job,'remote_id':remote,'original_submit_receipt':submit,'first_witness':witness,'export':exported,'initial_snapshot_ref':initial_snapshot['ref'],'initial_snapshot_history_through_sequence':0,'final_forecast':later[-1]['forecast'][0],'operation_receipt_count':5,'submission_claim_count':1,'selected_http_capture_count':4,'physical_request_or_attempt_count':'unknown','captures':sorted(capture_summary,key=lambda r:r['observed_at']),'biological_publications':sorted(publication_summary,key=lambda r:r['page']),'record_counts':counts,'ordinary_record_count':len(records),'artifact_count':len(artifact_rows),'native_statistic_count':0,'reported_statistic_count':1,'timing_source_count':1,'phase_arguments':phase_summary,'copied_original_file_count':len(copy_map),'omitted_original_file_count':len(omissions),'raw_originals_rewritten':False,'publication_application_calls':0,'publication_HTTP_calls':0,'publication_model_calls':0,'publication_native_calls':0,'scientific_interpretation_or_credit':'not_assigned_or_established','session_scan':{'actual_private_session_value_count':len(secrets),'scanned_forms_count':len(secret_forms),'value_disclosure':False,'staged_match_count':0},'limits':['provider-reported search interval only','remote build/allocation/corpus release/sizes unknown','queue/HTTP time/turnaround unknown','no episode/controller/configured-model science demonstration','no server-side physical request/retry/reliability count']}
put('CHECKS.json',summary)
post={str(p):inventory(p) for p in (E,W)};pre=load(O/'PRIVATE_BEFORE.json');changed=[];added=[]
for root,items in pre.items():
    for name,meta in items.items():
        ensure(name in post[root] and post[root][name]==meta,'preexisting_private_file_changed');
    for name,meta in post[root].items():
        if name not in items:added.append({'private_path':str(Path(root)/name),**meta})
put('WORKING_CUSTODY.json',{'preexisting_files_unchanged':True,'changed_preexisting_files':changed,'new_files_after_read_only_inspection':added,'reader':'sqlite3 mode=ro/query_only=ON, short read transactions','bookkeeping_limit':'SQLite may create WAL/SHM readers; no original sidecars were cleaned or checkpointed.'})
# Recheck all staged outputs only against in-memory private values/forms.
ensure(all(safe(p.read_bytes()) for p in S.rglob('*') if p.is_file()),'final_stage_session_scan_failed')
(O/'PRIVATE_AFTER.json').write_text(json.dumps(post,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('phase_count','source_pin','source_file_count','operation_receipt_count','selected_http_capture_count','reported_statistic_count','native_statistic_count','timing_source_count','ordinary_record_count','artifact_count','copied_original_file_count','omitted_original_file_count','session_scan')},sort_keys=True,indent=2))
print(json.dumps({'publications':summary['biological_publications'],'new_bookkeeping_files':added},sort_keys=True,indent=2))
