"""Static checks only: no application imports, DB opens or preparation calls."""
from pathlib import Path
import ast,hashlib,json,tomllib
from jsonschema import Draft202012Validator,FormatChecker
P=Path(__file__).resolve().parent
ROOT=Path('/home/chia/repos/gene_annotation_episode');CAP=ROOT/'verification/progress_checkpoint_2026-10-22_015';CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
RUN='/home/chia/gene_annotation_episode_runs/configured_literature_localization_001'
def desc(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_text())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
m=load(P/'INPUTS001.json')
for n,d in m['members'].items():assert desc(P/n)==d,n
for n,d in m['source_provenance'].items():assert desc(CAP/n)==d,n
for p in P.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
schema=load(P/'SCHEMAS004.json');assert desc(P/'SCHEMAS004.json')['sha256']=='b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112'
request=load(P/'C_REQUEST001.json')
Draft202012Validator({'$ref':'#/$defs/request','$defs':schema['$defs']},format_checker=FormatChecker()).validate(request)
original=load(CAP/'actual-caller-inputs/C_SELECTION001.json')['arguments'];expected=dict(original);expected['destination_workspace']=RUN+'/workspace';assert request==expected
assert len(request['initial_known_record_refs'])==len(set(request['initial_known_record_refs']))==198
before=tomllib.loads((CAP/'actual-caller-inputs/config.toml').read_text());after=tomllib.loads((P/'config.toml').read_text())
def rebase(x):
 if isinstance(x,str):return x.replace('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001',RUN)
 if isinstance(x,list):return [rebase(v) for v in x]
 if isinstance(x,dict):return {k:rebase(v) for k,v in x.items()}
 return x
assert after==rebase(before)
template=load(P/'PARAMETER_TEMPLATE001.json');old=load(CAP/'actual-caller-inputs/parameters.json');expected=rebase(old)
del expected['policy']['scientific_progress']['initial_known_record_refs'];del expected['policy']['operational']['registry_ref']
expected['services']['source_directory']=str(CODE/'research/slotted_process_library/publications/2026-10-21-001')
expected['services']['public_search_registry']['registry_ref']='execution_registry_9d451c293fb649cea87d48ab2f5ea4d2'
assert template==expected
static=hashlib.sha256(canonical(template['policy'])).hexdigest();assert static=='dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1'
operator=ast.parse((P/'prepare_caller001.py').read_text())
called=[]
for node in ast.walk(operator):
 if isinstance(node,ast.Call):
  name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else None
  called.append(name)
assert not set(called)&{'run_prepared_case','run_workflow','Workflow','ModelConnection','Store','build_tools','execute','subprocess','Popen','complete'}
assert 'prepare_scientific_checkpoint_fork' in called and 'prepare_case_run' in called and 'create_policy' in called
# Calls are only parsed, never evaluated. Direct SQLite helper is used only on new inactive outputs.
new_sql_calls=[n for n in ast.walk(operator) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='new_database_counts']
assert len(new_sql_calls)==2
for node in new_sql_calls:assert 'RUN' in ast.unparse(node.args[0])
output=load(P/'OPERATOR_OUTPUT_SCHEMA001.json');Draft202012Validator.check_schema(output)
pub=load(P/'PUBLICATION_INPUTS001.json')
for n,d in pub['members'].items():assert desc(Path(pub['root'])/n)==d
h=hashlib.sha256();runtime={}
for p in sorted(p for package in ('gene_annotation_episode','method_loop') for p in (CODE/package).rglob('*.py')):
 d=desc(p);n=p.relative_to(CODE).as_posix();runtime[n]=d;h.update(n.encode()+b'\0');h.update(bytes.fromhex(d['sha256']))
assert len(runtime)==137 and h.hexdigest()==m['implementation_sha256']=='3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'
read_files=['scientific_checkpoint_fork.py','api_planning_case_policy.py','assembled_case_policy.py','case_execution.py','assembled_service_setup.py','independent_execution.py','tool_configuration.py']
readset={'version':'configured_literature_caller_preparation_readset_v1','complete_source_files':{n:desc(CODE/'gene_annotation_episode'/n) for n in read_files},
 'source_excerpt':{'domain.canonical':desc(CODE/'gene_annotation_episode/domain.py')},
 'normative_texts':{n:desc(ROOT/n) for n in ['AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/CONFIGURED_API_CALLER_ACTUAL_SCOPE_2026-10-22_001.md','docs/SCIENTIFIC_CHECKPOINT_CUSTODY_SCOPE_2026-10-22_001.md','docs/SCIENTIFIC_CHECKPOINT_CUSTODY_SCOPE_2026-10-22_002.md']},
 'immutable_goal':desc(Path('/home/chia/.codex/attachments/6c61440f-d223-4bea-91e3-6e4f7b2c5013/pasted-text-1.txt')),
 'prior_boundary_packet':desc(Path('/tmp/configured-literature-child-boundary-20261022-001-ltnixxu1/MANIFEST001.json')),
 'sealed_public_sources':m['source_provenance'],
 'historical_operator_read':desc(CAP/'root-operator/prepare_actual_custody001.py')}
checks={'version':'configured_literature_caller_static_checks_v1','status':'passed_static_only_not_executed',
 'implementation_sha256':h.hexdigest(),'runtime_file_count':137,'runtime_members':runtime,
 'closed_C_request_valid':True,'exact_original198_except_destination':True,'only_config_paths_rebased':True,
 'only_parameter_rebases_public_identity_and_two_deferred_fields':True,'static_policy_remainder_sha256':static,
 'operator_AST_parsed':True,'operator_app_calls_not_executed':True,'operator_forbidden_launch_calls_absent':True,
 'operator_direct_SQL_targets_only_new_inactive_outputs':True,'closed_operator_output_schema_valid':True,
 'input_manifest':desc(P/'INPUTS001.json'),'publication_member_count':len(pub['members']),
 'counts':{'application_imports':0,'application_constructors':0,'database_opens':0,'model_calls':0,'HTTP_calls':0,'native_calls':0,'C_calls':0,'P_calls':0,'tests':0,'permanent_writes':0},
 'discovery_failure_metadata':[{'command':'rg ... gene_annotation_episode/public_search.py ...','exit':2,'reason':'guessed module absent; actual tool_configuration.py read completely; no service construction or calls'}],
 'deferred_actual_outputs':['C result/receipt/newlineage IDs and byte hashes','fresh native registry ID','final parameters bytes/hash after inserting actual output refs/ID'],
 'unresolved_caller_operands':[],
 'external_prerequisites':['Root exact007 verification/release and adoption before operator invocation'],
 'scientific_or_numeric_adoption':False,'future_caller_created':False}
for n,x in [('READSET001.json',readset),('STATIC_CHECKS001.json',checks)]:
 with (P/n).open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'status':checks['status'],'input_manifest':desc(P/'INPUTS001.json'),'readset':desc(P/'READSET001.json'),'checks':desc(P/'STATIC_CHECKS001.json')},sort_keys=True))
