"""DRAFT: one explicitly requested, read-only first saved request proof.

Active SQLite uses mode=ro, query_only, BEGIN and finally-close, never immutable.
After close, only existing pure validators inspect detached saved JSON. No Store,
Workflow, capture, projector, backend, provider, native job, model or polling loop.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,sqlite3,sys
PLAN=Path(__file__).resolve().parent
CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
RUN=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')
PIN='3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'
OLD_RUN='run_a9cae64280ed405594a79255d659f917'

def now():return datetime.now(timezone.utc).isoformat()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def descriptor(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def read(p):return json.loads(p.read_bytes())
def runtime():
 h=hashlib.sha256();count=0
 for p in sorted(p for package in ('gene_annotation_episode','method_loop') for p in (CODE/package).rglob('*.py')):
  h.update(p.relative_to(CODE).as_posix().encode()+b'\0');h.update(hashlib.sha256(p.read_bytes()).digest());count+=1
 return {'sha256':h.hexdigest(),'file_count':count}
def save(out,n,x):
 b=x if isinstance(x,bytes) else canonical(x)+b'\n'
 with (out/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 (out/n).chmod(0o400)
 return descriptor(out/n)
def counts(db,run_id):
 return {name:db.execute('SELECT count(*) FROM '+name+' WHERE run_id=?',(run_id,)).fetchone()[0]
  for name in ['runtime_runs','runtime_episodes','runtime_actions','runtime_observations','runtime_model_calls']}

def snapshot():
 """No file hashes of an active main/WAL are treated as a SQL snapshot."""
 marker=RUN/'run.json'
 if not marker.is_file():return {'status':'not_yet_available','reason':'run_marker_not_visible'}
 manifest=read(marker);run_id=manifest['run_id']
 if run_id==OLD_RUN:raise ValueError('new_run_reuses_original_run_id')
 dbpath=RUN/'workspace/state.sqlite3'
 started=now();db=None
 try:
  db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)
  db.row_factory=sqlite3.Row
  db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  row=db.execute('SELECT * FROM runtime_runs WHERE run_id=?',(run_id,)).fetchone()
  if row is None:return {'status':'not_yet_available','reason':'new_runtime_row_not_visible','run_id':run_id}
  settings=json.loads(row['settings'])
  roots=[dict(r) for r in db.execute('SELECT * FROM runtime_episodes WHERE run_id=?',(run_id,)) if json.loads(r['path'])==[['annotation','root']]]
  if not roots:return {'status':'not_yet_available','reason':'root_not_visible','run_id':run_id}
  if len(roots)!=1:raise ValueError('new_root_identity_ambiguous')
  root=roots[0];episode_id=root['episode_id']
  first=db.execute('SELECT * FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=0',(run_id,episode_id)).fetchone()
  if first is None:return {'status':'not_yet_available','reason':'first_request_not_visible','run_id':run_id,'episode_id':episode_id}
  execution=db.execute('SELECT * FROM runtime_execution_bindings WHERE run_id=?',(run_id,)).fetchone()
  if execution is None:raise ValueError('execution_binding_row_missing')
  receipts=[dict(r) for r in db.execute('SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? ORDER BY receipt_index',(run_id,episode_id))]
  inherited=db.execute('SELECT * FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',(run_id,episode_id)).fetchone()
  missing=[];initial={r['record_ref'] for r in receipts if r['receipt_kind']=='initial'}
  selected=settings['scientific_knowledge']['initial_known_record_refs']
  for ref in sorted(set(selected)-initial):
   record=None
   for table in ['inputs','records','material_members']:
    found=db.execute('SELECT data FROM '+table+' WHERE id=?',(ref,)).fetchone()
    if found is not None:record=json.loads(found[0]);break
   if record is None:
    found=db.execute('SELECT id FROM artifacts WHERE id=?',(ref,)).fetchone()
    record=None if found is None else {'id':ref,'record_type':'artifact'}
   # Explicitly retain the existing paged-member exception; never fake receipt.
   missing.append({'reference':ref,'record_type':None if record is None else record['record_type']})
  native_initial=[r[0] for r in db.execute("SELECT receipts.record_ref FROM runtime_record_receipts receipts JOIN records record ON record.id=receipts.record_ref WHERE receipts.run_id=? AND receipts.episode_id=? AND receipts.receipt_kind='initial' AND record.record_type='native_execution' ORDER BY receipts.record_ref",(run_id,episode_id))]
  result={'status':'first_request_available','run_id':run_id,'episode_id':episode_id,
   'runtime_manifest':manifest,'settings':settings,'root':root,'first':dict(first),'execution_row':dict(execution),
   'receipt_inheritance':None if inherited is None else dict(inherited),
   'current_new_run_counts_at_snapshot':counts(db,run_id),'copied_old_run_counts_at_snapshot':counts(db,OLD_RUN),
   'initial_receipt_count':len(initial),'selected_initial_count':len(selected),'selected_initial_receipted_count':len(set(selected)&initial),
   'selected_not_in_initial_receipt_rows':missing,'initial_native_receipt_refs':native_initial,
   'transaction':{'database':str(dbpath),'uri_mode':'ro','query_only':True,'immutable':False,'explicit_begin':True,'read_started_at_utc':started}}
  return result
 finally:
  if db is not None:db.close()

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inspect',required=True,action='store_true');parser.add_argument('--output-directory',required=True,type=Path);args=parser.parse_args()
 out=args.output_directory.expanduser().absolute()
 for protected in [CODE,RUN,Path('/home/chia/repos/gene_annotation_episode')]:
  if out.is_relative_to(protected) or protected.is_relative_to(out):raise ValueError('proof_output_overlaps_authority')
 if any(p.is_symlink() for p in [out,*out.parents]):raise ValueError('proof_output_symlink')
 os.umask(0o077);out.mkdir(mode=0o700)
 started=now();sys.dont_write_bytecode=True
 try:
  command=read(PLAN/'LAUNCH_COMMAND_DRAFT001.json');inputs=read(PLAN/'INPUTS001.json')
  for n,d in inputs['members'].items():
   a=descriptor(PLAN/n)
   if any(a[k]!=d[k] for k in ['sha256','bytes']):raise ValueError('proof_packet_changed')
  before=runtime()
  if before!={'sha256':PIN,'file_count':137}:raise ValueError('proof_runtime_pin_changed')
  for key,expected in command['inputs'].items():
   # All pinned operands are immutable caller/receipt JSON/text, never active DB.
   a=descriptor(Path(expected['path']))
   if any(a[k]!=expected[k] for k in ['sha256','bytes']):raise ValueError('prepared_operand_changed:'+key)
  captured=snapshot();closed=now()
  if captured['status']!='first_request_available':
   save(out,'RESULT001.json',{**captured,'captured_at_utc':closed,'helper_not_polled_or_retried':True,'application_constructors':0,'scientific_or_model_calls':0})
   print(json.dumps({'status':captured['status'],'reason':captured['reason'],'output_directory':str(out)},sort_keys=True));return 0
  # The SQLite finally-close above completed before imports/pure validation.
  run_id=captured['run_id'];episode_id=captured['episode_id'];settings=captured['settings'];root=captured['root'];first=captured['first']
  case=read(RUN/'case-launch.json');policy=read(RUN/'policy-binding.json');binding=read(RUN/'episode-execution-binding.json');params=read(RUN/'caller-inputs/parameters.json');receipt=read(RUN/'workspace/scientific-checkpoint-fork.json')
  if captured['runtime_manifest']!={'run_id':run_id,**settings} or settings['directory']!=str(RUN):raise ValueError('saved_new_run_manifest_mismatch')
  if settings['goal']!=case['goal'] or json.loads(root['request'])['goal']['objective']!=settings['goal']:raise ValueError('new_root_goal_mismatch')
  if settings['problem']['id']!=receipt['fixed_identity']['problem_ref'] or settings['problem']['subject_refs']!=[receipt['fixed_identity']['target_ref']]:raise ValueError('new_root_fixed_target_mismatch')
  if policy['source_sha256']!='4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f' or policy['parameters']!=params:raise ValueError('saved_policy_operands_mismatch')
  if descriptor(RUN/policy['snapshot_file'])['sha256']!=policy['source_sha256']:raise ValueError('saved_policy_source_mismatch')
  if settings['scientific_knowledge']['initial_known_record_refs']!=sorted(set(receipt['initial_known_record_refs'])) or params['policy']['scientific_progress']['initial_known_record_refs']!=receipt['initial_known_record_refs']:raise ValueError('inherited200binding_mismatch')
  if settings['models']!=case['configuration']['models'] or settings['restoration']!=case['configuration']['restoration']:raise ValueError('model_or_presentation_operands_mismatch')
  if settings['tool_configuration']!=case['configuration'] or settings['job_episodes']['registry_configuration']!=case['registry_configuration']:raise ValueError('resource_operands_mismatch')
  if settings['initial_tool_resources']['local_jobs']!=case['configuration']['local_jobs']:raise ValueError('caller_native_limits_mismatch')
  identity={'policy_source_sha256':policy['source_sha256'],'policy_parameters_sha256':sha(json.dumps(params,sort_keys=True,separators=(',',':'),allow_nan=False).encode())}
  for name in ['credit','scientific_child_credit','controller','annotation_score']:
   if settings['binding_definitions'][name]!={**identity,'definition':policy['definitions'][name]}:raise ValueError('saved_binding_definition_mismatch:'+name)
  expected_args={'version':'episode_runtime_binding_v1','workspace':str(RUN/'workspace'),'run_directory':str(RUN),'kind':'fixed_case','tool_configuration':case['configuration'],
   'caller_binding_pins':{'case-launch.json':sha(canonical(case)),'policy-binding.json':sha(canonical(policy))}}
  expected_binding={'factory_module':'gene_annotation_episode.independent_execution','factory_name':'open_commission','arguments':expected_args,'implementation_sha256':PIN,'settings_sha256':sha(canonical(settings))}
  if binding!=expected_binding or json.loads(captured['execution_row']['runtime_binding'])!=binding:raise ValueError('fixed_case_execution_binding_mismatch')
  request_raw=first['request'].encode('utf-8');request=json.loads(first['request'])
  if first['purpose']!='decision' or request.get('version')!='runtime_model_call_request_v3':raise ValueError('first_v3_request_required')
  if set(request)!={'version','context','schema','model_presentation','local_commission_frame'}:raise ValueError('first_request_closed_shape_mismatch')
  context=request['context'];presentation=request['model_presentation'];frame=request['local_commission_frame']
  if 'local_commission_frame' in context or 'local_commission_frame' in presentation['context']:raise ValueError('saved_factual_frame_inside_model_context')
  sys.path.insert(0,str(CODE))
  from gene_annotation_episode.local_commission_frame import validate_local_commission_frame
  from gene_annotation_episode.model_context_presentation import validate_model_context_presentation
  from method_loop.identities import EpisodeRef
  for function,relative in [(validate_local_commission_frame,'gene_annotation_episode/local_commission_frame.py'),(validate_model_context_presentation,'gene_annotation_episode/model_context_presentation.py'),(EpisodeRef,'method_loop/identities.py')]:
   if Path(sys.modules[function.__module__].__file__).resolve()!=CODE/relative:raise ValueError('pure_validation_import_origin_mismatch')
  if EpisodeRef(run_id,json.loads(root['path'])).episode_id!=episode_id:raise ValueError('root_episode_identity_mismatch')
  validate_local_commission_frame(frame,run_id=run_id,episode_id=episode_id,pending=context.get('pending_work'),controller_credit=frame.get('controller_credit'))
  validate_model_context_presentation(presentation,original_context=context,run_id=run_id,episode_id=episode_id,before_decision_index=0,preview_size=settings['restoration']['preview_size'])
  if frame['controller_credit']!={'credit_kind':'scientific','credit_binding':context['credit_binding']}:raise ValueError('first_frame_controller_meaning_mismatch')
  rendered=json.dumps(presentation['context'],allow_nan=False).encode('utf-8')
  if sha(rendered)!=presentation['model_input_text_sha256'] or len(rendered)!=presentation['model_input_utf8_byte_count']:raise ValueError('model_presentation_serialization_mismatch')
  if runtime()!=before:raise ValueError('proof_source_changed')
  save(out,'FIRST_REQUEST_RAW001.json',request_raw)
  save(out,'FIRST_CONTEXT_DERIVED001.json',canonical(context));save(out,'FIRST_MODEL_CONTEXT_DERIVED001.json',canonical(presentation['context']))
  save(out,'LOCAL_COMMISSION_FRAME_DERIVED001.json',canonical(frame))
  save(out,'RUNTIME_SETTINGS001.json',canonical(settings))
  raw_history=context.get('waiting_support',{}).get('own_completed_action_history')
  model_history=presentation['context'].get('waiting_support',{}).get('own_completed_action_history')
  result={'version':'configured_literature_first_request_proof_v1','status':'first_request_verified','captured_at_utc':closed,
   'helper_started_at_utc':started,'run_id':run_id,'episode_id':episode_id,'root_path':json.loads(root['path']),
   'first_request':{'call_index':0,'response_available_at_snapshot':first['response'] is not None,'version':request['version'],'raw_sqlite_TEXT_utf8_sha256':sha(request_raw),'raw_utf8_bytes':len(request_raw)},
   'read_transaction':{**captured['transaction'],'connection_explicitly_closed_before_validation':True},
   'bindings':{'fixed_case_execution':binding,'policy_source_sha256':policy['source_sha256'],'parameters':descriptor(RUN/'caller-inputs/parameters.json'),
    'initial_known_ref_count':len(receipt['initial_known_record_refs']),'source_run_id_from_receipt':receipt['source']['run_id'],'source_implementation_sha256_from_receipt':receipt['source']['implementation_sha256'],
    'execution_implementation_sha256':PIN,'models':settings['models'],'restoration':settings['restoration'],'controller_input_parameters':params['policy']['controller'],
    'initial_tool_resources':settings['initial_tool_resources'],'native_registry_configuration':case['registry_configuration'],'public_search_registry':params['services']['public_search_registry']},
   'observed_initial_values':{'episode_initial_credit':root['initial_credit'],'first_context_credit':context.get('current_credit'),
    'first_context_controller':context.get('controller'),'first_context_monitoring_information_credit':context.get('monitoring_information_credit'),
    'first_context_investigation_progress':context.get('investigation_progress'),'annotation_score':context.get('annotation_score'),'annotation_evidence_vector':context.get('annotation_evidence_vector'),
    'raw_completed_own_history_count':None if raw_history is None else len(raw_history),'model_completed_own_history_count':None if model_history is None else len(model_history),
    'initial_receipt_count':captured['initial_receipt_count'],'selected_initial_count':captured['selected_initial_count'],'selected_initial_receipted_count':captured['selected_initial_receipted_count'],
    'selected_not_in_initial_receipt_rows':captured['selected_not_in_initial_receipt_rows'],'initial_native_receipt_refs':captured['initial_native_receipt_refs'],
    'receipt_inheritance':captured['receipt_inheritance']},
   'captured_frame':{'version':frame['version'],'population_status':frame['population_status'],'population_count':frame['population_count'],'commission_count':len(frame['commissions']),
    'outside_raw_context':True,'outside_saved_model_context':True,'pending_captured_at':frame['pending_captured_at'],'store_read_interval':frame['store_read_interval']},
   'provider_context_source_evidence':{'saved_model_presentation_validated_by_actual_pure_function':True,'saved_context_serialization_hash_verified':True,
    'meaning':'Runtime source selects this saved presentation.context for provider.complete; no private transport/event payload was inspected.'},
   'current_new_run_counts_at_snapshot':captured['current_new_run_counts_at_snapshot'],'copied_old_run_counts_at_snapshot':captured['copied_old_run_counts_at_snapshot'],
   'pure_validation_readset':{'functions':['gene_annotation_episode.local_commission_frame.validate_local_commission_frame','gene_annotation_episode.model_context_presentation.validate_model_context_presentation','method_loop.identities.EpisodeRef'],
    'actual_operands':{'run_id':run_id,'episode_id':episode_id,'pending_snapshot_sha256':sha(canonical(context.get('pending_work'))),'controller_credit_sha256':sha(canonical(frame.get('controller_credit'))),'before_decision_index':0,'preview_size':settings['restoration']['preview_size']},
    'files':{n:descriptor(CODE/n) for n in ['gene_annotation_episode/local_commission_frame.py','gene_annotation_episode/model_context_presentation.py','method_loop/identities.py']}},
   'helper_effects':{'application_constructors':0,'reader_captures':0,'credit_projections':0,'backend_provider_model_native_calls':0,'application_SQL_writes':0,'polling_or_retries':0},
   'limits':['Initial values are observed from the immutable saved call0, not manufactured expected credit/history.',
    'Current SQL counts can include work after call0 and are explicitly separate from its initial context.',
    'Normal readonly active-WAL SQLite reader bookkeeping is allowed; no zero-sidecar-byte-change claim.',
    'Provider delivery follows inspected source and saved serialization; no private provider logs or payload read.',
    'No useful scientific child return, later parent integration or whole-goal completion is established by this first-request proof.']}
  save(out,'RESULT001.json',result)
  print(json.dumps({'status':result['status'],'run_id':run_id,'episode_id':episode_id,'result':descriptor(out/'RESULT001.json')},sort_keys=True),flush=True)
  return 0
 except BaseException as error:
  failure={'version':'configured_literature_first_request_proof_failure_v1','status':'proof_unavailable','exception_type':type(error).__name__,'message':str(error),'captured_at_utc':now(),'automatic_retry':False,'source_or_state_repair':False}
  save(out,'FAILURE001.json',failure);print(json.dumps(failure,sort_keys=True),file=sys.stderr,flush=True);raise
if __name__=='__main__':raise SystemExit(main())
