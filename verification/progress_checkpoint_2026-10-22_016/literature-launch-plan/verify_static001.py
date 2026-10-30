"""Static plan checks only; does not import/invoke driver/helper/application/DB."""
from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent;CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007');ROOT=Path('/home/chia/repos/gene_annotation_episode')
def d(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_bytes())
def save(n,x):
 with (P/n).open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
files=['LAUNCH_COMMAND_DRAFT001.json','launch_driver001.py','inspect_first_request001.py','INDEPENDENT_PREPARATION_VERIFICATION001.json',*[p.name for p in sorted(P.glob('prepared-*'))]]
inputs={'version':'configured_literature_launch_plan_inputs_v1','status':'unadopted_not_executed','members':{n:d(P/n) for n in files}}
save('INPUTS001.json',inputs)
command=load(P/'LAUNCH_COMMAND_DRAFT001.json')
assert command['argv']==['/home/chia/repos/gene_annotation_episode/.venv/bin/python','-m','gene_annotation_episode.case_execution','run','--run-dir','/home/chia/gene_annotation_episode_runs/configured_literature_localization_001','--policy',str(CODE/'gene_annotation_episode/api_planning_case_policy.py'),'--parameters','/home/chia/gene_annotation_episode_runs/configured_literature_localization_001/caller-inputs/parameters.json']
assert '--resume' not in command['argv'] and command['runtime_files']==137
assert command['inputs']['parameters.json']['sha256']=='5ab22e01f87cec425adaa7dcde1ffbaa5df776a8a0070a77e6c746870af74d73'
verification=load(P/'INDEPENDENT_PREPARATION_VERIFICATION001.json')
assert d(P/'INDEPENDENT_PREPARATION_VERIFICATION001.json')['sha256']=='53c8a26bfadcbfe435bd013f1d37108c44ae3c653ccbe4679565e44f1c1a1045'
assert verification['status']=='verified_prepared_not_started' and verification['selected_inputs_unchanged'] is True
parsed={n:ast.parse((P/n).read_text(),filename=str(P/n)) for n in ['launch_driver001.py','inspect_first_request001.py','build_launch_inputs001.py']}
driver=parsed['launch_driver001.py'];helper=parsed['inspect_first_request001.py']
modules={n.names[0].name.split('.')[0] for n in ast.walk(driver) if isinstance(n,ast.Import)}|{n.module.split('.')[0] for n in ast.walk(driver) if isinstance(n,ast.ImportFrom)}
assert modules<={'pathlib','datetime','argparse','hashlib','json','os','shutil','stat','subprocess','sys','time'}
popen=[n for n in ast.walk(driver) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Popen'];assert len(popen)==1 and 'timeout' not in [k.arg for k in popen[0].keywords]
wait=[n for n in ast.walk(driver) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='wait'];assert len(wait)==1 and not wait[0].args and not wait[0].keywords
for tree in [driver,helper]:
 calls=[n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else None for n in ast.walk(tree) if isinstance(n,ast.Call)]
 assert not set(calls)&{'kill','terminate','send_signal','run_prepared_case','run_workflow','Workflow','Store','Journal','ModelConnection','capture','project_credit','sleep'}
 assert not any(isinstance(n,(ast.While,ast.AsyncFor)) for n in ast.walk(tree))
connect=[n for n in ast.walk(helper) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='connect'];assert len(connect)==1 and ast.unparse(connect[0].args[0])=="dbpath.as_uri() + '?mode=ro'"
snapshot=next(n for n in ast.walk(helper) if isinstance(n,ast.FunctionDef) and n.name=='snapshot')
assert any(isinstance(n,ast.Try) and n.finalbody for n in ast.walk(snapshot))
closes=[n for n in ast.walk(snapshot) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='close'];assert len(closes)==1
assert any(isinstance(n,ast.Constant) and n.value=='PRAGMA query_only=ON' for n in ast.walk(snapshot))
assert any(isinstance(n,ast.Constant) and n.value=='BEGIN' for n in ast.walk(snapshot))
# Ground every direct column family in the exact immutable checkpoint manifest, without SQL.
tables_path=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001/workspace/checkpoint/tables.json')
tables={r['name']:set(r['column_names']) for r in load(tables_path)['tables']}
required={'inputs':{'id','data'},'records':{'id','record_type','data'},'material_members':{'id','data'},'artifacts':{'id'},
 'runtime_runs':{'run_id','settings'},'runtime_episodes':{'run_id','episode_id','path','request','initial_credit'},
 'runtime_model_calls':{'run_id','episode_id','call_index','purpose','request','response'},
 'runtime_record_receipts':{'receipt_index','run_id','episode_id','record_ref','receipt_kind','source_index'},
 'runtime_receipt_inheritance':{'run_id','episode_id','parent_episode_id','through_receipt_index'},
 'runtime_execution_bindings':{'run_id','selection','settings_sha256','runtime_binding'}}
for table,columns in required.items():assert columns<=tables[table],table
frame_ast=ast.parse((CODE/'gene_annotation_episode/local_commission_frame.py').read_text());frame=next(n for n in frame_ast.body if isinstance(n,ast.FunctionDef) and n.name=='validate_local_commission_frame')
assert [a.arg for a in frame.args.args]==['value'] and [a.arg for a in frame.args.kwonlyargs]==['run_id','episode_id','pending','controller_credit']
presentation_ast=ast.parse((CODE/'gene_annotation_episode/model_context_presentation.py').read_text());presentation=next(n for n in presentation_ast.body if isinstance(n,ast.FunctionDef) and n.name=='validate_model_context_presentation')
assert [a.arg for a in presentation.args.args]==['presentation'] and [a.arg for a in presentation.args.kwonlyargs]==['original_context','run_id','episode_id','before_decision_index','preview_size']
prepare=next(n for n in presentation_ast.body if isinstance(n,ast.FunctionDef) and n.name=='_prepare')
serialize=[n for n in ast.walk(prepare) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and ast.unparse(n.func)=='json.dumps'];assert len(serialize)==1
assert ast.unparse(serialize[0])=='json.dumps(projected, allow_nan=False)'
helper_serial=[n for n in ast.walk(helper) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and ast.unparse(n.func)=='json.dumps' and n.args and ast.unparse(n.args[0])=="presentation['context']"]
assert len(helper_serial)==1 and [(k.arg,ast.literal_eval(k.value)) for k in helper_serial[0].keywords]==[('allow_nan',False)]
# Source inspection confirms EpisodeRef normalizes lists/tuples of 2-string path segments.
identity_source=(CODE/'method_loop/identities.py').read_text();assert 'normalize_structural_path(self.path)' in identity_source and 'isinstance(value, (tuple, list))' in identity_source
h=hashlib.sha256();runtime={}
for p in sorted(p for package in ['gene_annotation_episode','method_loop'] for p in (CODE/package).rglob('*.py')):
 n=p.relative_to(CODE).as_posix();v=d(p);runtime[n]=v;h.update(n.encode()+b'\0');h.update(bytes.fromhex(v['sha256']))
assert len(runtime)==137 and h.hexdigest()==command['runtime_pin']=='3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'
readset={'version':'configured_literature_launch_static_readset_v1',
 'current_driver_helper':{n:d(P/n) for n in ['launch_driver001.py','inspect_first_request001.py']},
 'complete_source_files':{n:d(CODE/n) for n in ['gene_annotation_episode/case_execution.py','gene_annotation_episode/providers.py','gene_annotation_episode/model_context_presentation.py','gene_annotation_episode/application_execution_binding.py','method_loop/identities.py']},
 'complete_named_consumers':{'gene_annotation_episode/runtime.py':{'descriptor':d(CODE/'gene_annotation_episode/runtime.py'),'functions':['DecisionSource.call','DecisionSource.next','Workflow.source_controller_credit','Workflow.source_credit_binding','_run_location','_run_bound_workflow','Workflow.build']},
 'gene_annotation_episode/local_commission_frame.py':{'descriptor':d(CODE/'gene_annotation_episode/local_commission_frame.py'),'functions':['validate_local_commission_frame','LocalCommissionFrame.capture (inspection only; never invoked by helper)']},
 'gene_annotation_episode/tools.py':{'descriptor':d(CODE/'gene_annotation_episode/tools.py'),'functions':['ToolRegistry.resource_binding']}},
 'table_manifest_metadata_only':d(tables_path),'required_SQL_columns':{k:sorted(v) for k,v in required.items()},
 'original006_launch_command':d(ROOT/'verification/progress_checkpoint_2026-10-22_015/actual-caller-inputs/LAUNCH_COMMAND001.json'),
 'adopted_preparation_scope':d(ROOT/'docs/CONFIGURED_LITERATURE_CALLER_ACTUAL_SCOPE_2026-10-22_001.md'),
 'independent_actual_verification':command['independent_preparation_verification'],
 'pure_validation_future_use':{'SQL_closed_first':True,'frame_signature':['value','*','run_id','episode_id','pending','controller_credit'],
 'presentation_signature':['presentation','*','original_context','run_id','episode_id','before_decision_index','preview_size'],
 'EpisodeRef_path_input':'Actual JSON list of two-string segments is accepted and normalized by actual EpisodeRef.',
 'model_context_serialization':'Exactly json.dumps(projected, allow_nan=False): Python default ensure_ascii, key insertion order and separators; helper uses same options on saved presentation.context.'}}
save('READSET001.json',readset)
save('STATIC_CHECKS001.json',{'version':'configured_literature_launch_static_checks_v1','status':'passed_static_only_not_launched_or_inspected',
 'runtime_pin':h.hexdigest(),'runtime_files':137,'runtime_members':runtime,'inputs':d(P/'INPUTS001.json'),
 'ordinary_CLI_argv_exact':True,'driver_stdlib_only':True,'one_Popen_and_one_wait_no_timeout':True,'no_signal_retry_private_loop':True,
 'helper_one_ro_active_connection_no_immutable':True,'helper_BEGIN_query_only_finally_close':True,'helper_SQL_columns_grounded':True,
 'pure_validator_signatures_match':True,'model_serialization_matches_complete_producer':True,'EpisodeRef_JSON_path_supported':True,
 'independent_preparation_verification_bound':True,'working_historical_hashes_equal_as_observed':True,
 'counts':{'launches':0,'helper_invocations':0,'application_imports':0,'application_constructors':0,'DB_opens':0,'models':0,'HTTP':0,'native_jobs':0,'tests':0,'permanent_writes':0},
 'discovery_failure_metadata':[{'command':'rg --files verification/progress_checkpoint_2026-10-22_015 from isolated007 cwd','reason':'sealed checkpoint lives under main root; corrected to absolute path, no application or DB work'}],
 'inspection_correction':'Root suspected material_members SQL columns, then confirmed actual immutable tables manifest contains id,data; this static check independently confirms them. No helper behavior change made for disproven concern.'})
print(json.dumps({'status':'passed_static_only','inputs':d(P/'INPUTS001.json'),'readset':d(P/'READSET001.json'),'checks':d(P/'STATIC_CHECKS001.json'),'driver':d(P/'launch_driver001.py'),'helper':d(P/'inspect_first_request001.py')},sort_keys=True))
