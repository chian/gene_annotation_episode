"""PROPOSED preparation only. Run only after root adopts the exact scope/bytes.

Creates a fresh C custody workspace and ordinary fixed-case prepared caller.
Never runs an episode, provider/model, public request or native program. No retry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tomllib

PLAN=Path(__file__).resolve().parent
CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
RUN=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')
EVIDENCE=Path('/tmp/configured-literature-localization-preparation-20261022-001')
PIN='3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'
POLICY=CODE/'gene_annotation_episode/api_planning_case_policy.py'
POLICY_SHA='4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f'
C_SHA='166d459b38295ab4003ebe39babd22184a96482dba5146b3b2479291ebd423ab'
SCHEMA_SHA='b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112'

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
 def pairs(items):
  x={}
  for k,v in items:
   if k in x:raise ValueError('duplicate_json_key')
   x[k]=v
  return x
 return json.loads(p.read_bytes(),object_pairs_hook=pairs,
  parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite_json')))
def no_links(p):
 for q in (p,*p.parents):
  if q.is_symlink():raise ValueError('symlink_path')
 if p.absolute()!=p.resolve():raise ValueError('noncanonical_path')
def witness(p):
 if not os.path.lexists(p):return None
 no_links(p)
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode):raise ValueError('regular_file_required')
  h=hashlib.sha256();size=0
  with os.fdopen(fd,'rb',closefd=False) as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b);size+=len(b)
  return {'path':str(p),'sha256':h.hexdigest(),'bytes':size}
 finally:os.close(fd)
def matches(p,d):
 a=witness(p)
 if a is None or any(a[k]!=d[k] for k in ('sha256','bytes')):raise ValueError('file_witness_mismatch:'+str(p))
 return a
def save(p,x):
 b=x if isinstance(x,bytes) else canonical(x)+b'\n'
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(d)
 finally:os.close(d)
 return witness(p)
def implementation(root):
 h=hashlib.sha256();members={}
 for p in sorted(p for package in ('gene_annotation_episode','method_loop') for p in (root/package).rglob('*.py')):
  d=witness(p);n=p.relative_to(root).as_posix();members[n]=d
  h.update(n.encode()+b'\0');h.update(bytes.fromhex(d['sha256']))
 return {'sha256':h.hexdigest(),'file_count':len(members),'members':members}
def source_guard(arguments,expected):
 root=Path(arguments['source_implementation_root']);ws=Path(arguments['source_workspace']);directory=Path(arguments['source_run_directory'])
 paths=set(Path(row['source_path']) for row in expected['source_authorities'])
 for base in (ws/'state.sqlite3',directory/'native-jobs/jobs.sqlite'):
  paths.update((base,Path(str(base)+'-wal'),Path(str(base)+'-shm')))
 for parent in (ws/'artifacts',):
  no_links(parent)
  for p in parent.rglob('*'):
   no_links(p)
   if p.is_file():paths.add(p)
   elif not p.is_dir():raise ValueError('unexpected_source_artifact_node')
 case=Path(next(row['source_path'] for row in expected['source_authorities'] if row['checkpoint_relative_path']=='checkpoint/authority/case/case.json')).parent
 if (case/'evidence-refs.json').is_file():paths.add(case/'evidence-refs.json')
 return {'implementation':implementation(root),'files':{str(p):witness(p) for p in sorted(paths)}}
def check_source_guard(g,arguments,expected):
 if g['implementation']['sha256']!=arguments['expected_source_implementation_sha256'] or g['implementation']['file_count']!=122:raise ValueError('source_implementation_mismatch')
 for d in [expected['source_database'],expected['source_native_database'],*expected['source_authorities']]:
  p=d.get('source_path',d.get('path'));a=g['files'][p]
  if a is None or any(a[k]!=d[k] for k in ('sha256','bytes')):raise ValueError('original_source_authority_mismatch:'+p)
 for p,d in g['files'].items():
  if p.endswith('-wal') and d is not None and d['bytes']!=0:raise ValueError('nonempty_source_wal')
def validate(schema,value,kind):
 from jsonschema import Draft202012Validator,FormatChecker
 Draft202012Validator({'$ref':'#/$defs/'+kind,'$defs':schema['$defs']},format_checker=FormatChecker()).validate(value)
def workspace_member(path):
 p=RUN/'workspace'/path;no_links(p)
 if not p.is_relative_to(RUN/'workspace'):raise ValueError('receipt_path_outside_workspace')
 return p

def verify_c(result,arguments,expected,schema):
 validate(schema,result,'result')
 if result['destination_workspace']!=str(RUN/'workspace') or result['status']!='published':raise ValueError('unexpected_c_result')
 rp=Path(result['receipt']['path'])
 if rp!=RUN/'workspace/scientific-checkpoint-fork.json':raise ValueError('receipt_path_mismatch')
 matches(rp,result['receipt']);r=read(rp);validate(schema,r,'receipt')
 if r['destination_workspace']!=str(RUN/'workspace') or r['fixed_identity']!=expected['fixed_identity']:raise ValueError('custody_identity_mismatch')
 src=r['source']
 for key,operand in [('workspace','source_workspace'),('run_directory','source_run_directory'),('implementation_root','source_implementation_root'),('run_id','source_run_id'),('implementation_sha256','expected_source_implementation_sha256')]:
  if src[key]!=arguments[operand]:raise ValueError('source_receipt_identity_mismatch')
 if src['pending']['request_raw_utf8_sha256']!=arguments['expected_pending_request_sha256'] or src['counts']!=expected['source_counts']:raise ValueError('source_pending_or_counts_mismatch')
 selected=arguments['initial_known_record_refs'];final=result['initial_known_record_refs'];lineage=result['lineage_source_refs']
 if len(selected)!=198 or len(set(selected))!=198 or len(final)!=200 or len(set(final))!=200:raise ValueError('initial_reference_count_mismatch')
 if r['caller_initial_known_record_refs']!=selected or r['initial_known_record_refs']!=final:raise ValueError('receipt_initial_reference_mismatch')
 if final!=sorted(set(selected)|set(lineage.values())) or len(set(lineage.values()))!=2 or set(lineage.values())&set(selected):raise ValueError('lineage_union_mismatch')
 if lineage!={'index':r['lineage']['index_source_ref'],'observations':r['lineage']['observation_source_ref']}:raise ValueError('lineage_identity_mismatch')
 if sha(canonical(final))!=r['initial_known_record_refs_sha256']:raise ValueError('initial_reference_hash_mismatch')
 if r['preserved_counts']!=expected['preserved_counts'] or not all(r['verification'].values()):raise ValueError('custody_verification_mismatch')
 for k in ['database','table_manifest','artifact_manifest','committed_reference_manifest']:
  d=r['checkpoint'][k];matches(workspace_member(d['path']),d)
  if any(d[x]!=expected['checkpoint_descriptors'][k][x] for x in ('sha256','bytes')):raise ValueError('checkpoint_differs_from_sealed_source')
 for key,d in [('implementation_file_manifest',src['implementation_file_manifest'])]:matches(workspace_member(d['path']),d)
 if any(src['implementation_file_manifest'][x]!=expected['source_implementation_manifest'][x] for x in ('sha256','bytes')):raise ValueError('old_source_file_manifest_mismatch')
 for row in src['authority_files']:matches(workspace_member(row['checkpoint_relative_path']),row)
 if src['authority_files']!=expected['source_authorities']:raise ValueError('source_authority_list_mismatch')
 committed=read(workspace_member(r['checkpoint']['committed_reference_manifest']['path']));validate(schema,committed,'committed_reference_manifest')
 old={row['reference'] for row in committed['records']}
 if len(old)!=193 or not old<=set(selected):raise ValueError('committed_baseline_incomplete')
 native={row['reference'] for row in committed['records'] if row['record_type']=='native_execution'}
 if native!=set(expected['original_native_receipts']):raise ValueError('inherited_native_baseline_mismatch')
 artifacts=read(workspace_member(r['checkpoint']['artifact_manifest']['path']));validate(schema,artifacts,'artifact_manifest')
 for row in artifacts['artifacts']:matches(workspace_member(row['relative_path']),row)
 def lineage_artifact(ref):
  if not ref.startswith('artifact_') or len(ref)!=73:raise ValueError('lineage_artifact_identity_mismatch')
  checksum=ref[9:];p=workspace_member('artifacts/'+checksum[:2]+'/'+checksum)
  if witness(p)['sha256']!=checksum:raise ValueError('lineage_artifact_hash_mismatch')
  return p
 index=read(lineage_artifact(r['lineage']['index_artifact_ref']));validate(schema,index,'observation_index')
 stream=lineage_artifact(r['lineage']['observation_artifact_ref']).read_bytes()
 if index['record_count']!=175 or len(index['rows'])!=175 or index['observation_source_ref']!=lineage['observations'] or index['observation_artifact_ref']!=r['lineage']['observation_artifact_ref']:raise ValueError('lineage_index_mismatch')
 if sha(stream)!=index['observation_artifact_sha256'] or len(stream)!=index['observation_artifact_bytes']:raise ValueError('lineage_stream_mismatch')
 next_offset=0
 for row in index['rows']:
  start=row['raw_text_utf8_offset'];end=start+row['raw_text_utf8_bytes']
  if start!=next_offset or sha(stream[start:end])!=row['raw_text_utf8_sha256'] or row['delimiter_bytes']!=1 or row['delimiter_hex']!='0a' or stream[end:end+1]!=b'\n':raise ValueError('lineage_raw_row_mismatch')
  next_offset=end+1
 if next_offset!=len(stream):raise ValueError('lineage_trailing_bytes')
 db=workspace_member(r['checkpoint']['database']['path']);working=RUN/'workspace/state.sqlite3'
 if (db.stat().st_dev,db.stat().st_ino)==(working.stat().st_dev,working.stat().st_ino):raise ValueError('database_copies_share_inode')
 matches(working,r['workspace_database_at_publication'])
 return r,{'committed_refs':len(old),'native_receipts':sorted(native),'selected_refs':198,'final_refs':200,
 'receipt':witness(rp),'checkpoint':witness(db),'working_database_publication_hash_checked_before_prepare':True}

def new_database_counts(path,tables):
 wal=witness(Path(str(path)+'-wal'))
 if wal is not None and wal['bytes']!=0:raise ValueError('new_database_nonempty_wal')
 db=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
 try:
  db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  return {table:db.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0] for table in tables}
 finally:db.close()

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true',required=True);parser.parse_args()
 sys.dont_write_bytecode=True
 os.umask(0o077)
 no_links(EVIDENCE);EVIDENCE.mkdir(mode=0o700)
 phase='validate_inputs';before=None;arguments=expected=None;failure=None
 try:
  manifest=read(PLAN/'INPUTS001.json')
  for n,d in manifest['members'].items():matches(PLAN/n,d)
  current=implementation(CODE)
  if current['sha256']!=PIN or current['file_count']!=137:raise ValueError('execution_implementation_mismatch')
  if witness(POLICY)['sha256']!=POLICY_SHA or witness(CODE/'gene_annotation_episode/scientific_checkpoint_fork.py')['sha256']!=C_SHA:raise ValueError('producer_source_mismatch')
  arguments=read(PLAN/'C_REQUEST001.json');expected=read(PLAN/'EXPECTED_HANDOFF001.json');schema=read(PLAN/'SCHEMAS004.json')
  if witness(PLAN/'SCHEMAS004.json')['sha256']!=SCHEMA_SHA:raise ValueError('custody_schema_mismatch')
  validate(schema,arguments,'request')
  if arguments['destination_workspace']!=str(RUN/'workspace'):raise ValueError('destination_operand_mismatch')
  publication=read(PLAN/'PUBLICATION_INPUTS001.json')
  for n,d in publication['members'].items():matches(Path(publication['root'])/n,d)
  no_links(RUN)
  if not RUN.parent.is_dir() or os.path.lexists(RUN):raise ValueError('new_run_directory_required')
  phase='source_before_guard';before=source_guard(arguments,expected);check_source_guard(before,arguments,expected)
  save(EVIDENCE/'SOURCE_BEFORE001.json',before)
  RUN.mkdir(mode=0o700)
  parent_fd=os.open(RUN.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(parent_fd)
  finally:os.close(parent_fd)
  inputs=RUN/'caller-inputs';inputs.mkdir(mode=0o700)
  save(inputs/'OPERATOR_INPUTS001.json',{'input_manifest':witness(PLAN/'INPUTS001.json'),'operator':witness(Path(__file__)),
   'argv':sys.argv,'cwd':str(Path.cwd()),'execution_implementation_sha256':PIN,'model_http_native_calls':0})
  for n in ['C_REQUEST001.json','config.toml','focus.txt','PARAMETER_TEMPLATE001.json','EXPECTED_HANDOFF001.json','SCHEMAS004.json']:
   save(inputs/n,(PLAN/n).read_bytes())
  phase='custody'
  sys.path.insert(0,str(CODE))
  from gene_annotation_episode import scientific_checkpoint_fork as custody
  if Path(custody.__file__).resolve()!=CODE/'gene_annotation_episode/scientific_checkpoint_fork.py':raise ValueError('wrong_c_module')
  kwargs=dict(arguments);kwargs['initial_known_record_refs']=tuple(kwargs['initial_known_record_refs'])
  try:result=custody.prepare_scientific_checkpoint_fork(**kwargs)
  except custody.ScientificCheckpointForkError as e:
   save(inputs/'C_FAILURE001.json',e.as_record());raise
  save(inputs/'C_RESULT001.json',result)
  phase='verify_custody';receipt,c_check=verify_c(result,arguments,expected,schema)
  save(inputs/'C_VERIFICATION001.json',c_check)
  after_c=source_guard(arguments,expected);save(EVIDENCE/'SOURCE_AFTER_C001.json',after_c)
  if after_c!=before:raise ValueError('source_changed_after_custody')
  phase='prepare_case'
  from gene_annotation_episode.case_execution import prepare_case_run
  from gene_annotation_episode.api_planning_case_policy import create_policy
  configuration=tomllib.loads((inputs/'config.toml').read_text());focus=(inputs/'focus.txt').read_text()
  prepared=prepare_case_run(Path(manifest['case_directory']),RUN,configuration,focus=focus)
  save(inputs/'PREPARE_RESULT001.json',prepared)
  if prepared!=read(RUN/'case-launch.json') or prepared['focus']!=focus or prepared['configuration']['workspace']!=str(RUN/'workspace'):raise ValueError('prepared_caller_mismatch')
  if any(prepared[k]!=receipt['fixed_identity'][k] for k in ['target_ref','problem_ref']) or prepared['target_sequence_sha256']!=receipt['fixed_identity']['target_sequence_sha256']:raise ValueError('prepared_fixed_target_mismatch')
  phase='derive_parameters';parameters=read(inputs/'PARAMETER_TEMPLATE001.json')
  parameters['policy']['scientific_progress']['initial_known_record_refs']=list(result['initial_known_record_refs'])
  native_ref=prepared['registry_configuration']['registry_ref']
  if native_ref in {expected['retained_active_native_registry_ref'],read(Path(arguments['source_run_directory'])/'native-jobs/configuration.json')['registry_ref']}:raise ValueError('native_registry_not_fresh')
  parameters['policy']['operational']['registry_ref']=native_ref
  remainder=json.loads(json.dumps(parameters['policy']));del remainder['scientific_progress']['initial_known_record_refs'];del remainder['operational']['registry_ref']
  if sha(canonical(remainder))!=expected['static_policy_remainder_sha256']:raise ValueError('numerical_policy_changed')
  if parameters['services']['public_search_registry']['registry_ref']==expected['retained_active_public_registry_ref'] or parameters['services']['public_search_registry']['registry_ref']!=manifest['public_search_registry_ref']:raise ValueError('public_registry_identity_mismatch')
  save(inputs/'parameters.json',parameters)
  phase='validate_policy';policy=create_policy(parameters)
  if policy.initial_known_record_refs!=result['initial_known_record_refs'] or policy.episode_record_receipts is not True or policy.episode_service_inputs!='actual_tool_registry_v1':raise ValueError('policy_inherited_binding_mismatch')
  if (RUN/'run.json').exists() or (RUN/'policy-binding.json').exists() or (RUN/'episode-execution-binding.json').exists():raise ValueError('unexpected_runtime_binding_before_launch')
  counts=new_database_counts(RUN/'native-jobs/jobs.sqlite',['orders','handoffs','samples'])
  if counts!={'orders':0,'handoffs':0,'samples':0}:raise ValueError('preparation_created_native_work')
  scientific=new_database_counts(RUN/'workspace/state.sqlite3',['runtime_runs','runtime_episodes','runtime_actions','runtime_observations','runtime_model_calls'])
  wanted={'runtime_runs':1,'runtime_episodes':1,'runtime_actions':179,'runtime_observations':175,'runtime_model_calls':180}
  if scientific!=wanted:raise ValueError('preparation_created_runtime_work')
  matches(RUN/'workspace/checkpoint/state.sqlite3',receipt['checkpoint']['database'])
  if implementation(CODE)!=current:raise ValueError('execution_source_changed')
  phase='source_after_guard';after=source_guard(arguments,expected);save(EVIDENCE/'SOURCE_AFTER_PREPARE001.json',after)
  if after!=before:raise ValueError('source_changed_after_prepare')
  output={'version':'configured_literature_localization_preparation_result_v1','status':'prepared_not_started',
   'run_directory':str(RUN),'workspace':str(RUN/'workspace'),'execution_implementation_sha256':PIN,
   'custody_result':witness(inputs/'C_RESULT001.json'),'receipt':witness(RUN/'workspace/scientific-checkpoint-fork.json'),
   'case_launch':witness(RUN/'case-launch.json'),'parameters':witness(inputs/'parameters.json'),
   'working_database_after_prepare':witness(RUN/'workspace/state.sqlite3'),
   'config':witness(inputs/'config.toml'),'focus':witness(inputs/'focus.txt'),'policy_source':witness(POLICY),
   'native_registry_ref':native_ref,'public_search_registry_ref':manifest['public_search_registry_ref'],
   'inherited_refs':200,'source_guards_unchanged':True,'native_registry_counts':counts,'preserved_old_runtime_counts':scientific,
   'new_scientific_runs_started':0,'model_http_native_calls':0,
   'limits':['preparation_only','working_publication_hash_is_historical_after_prepare','no_new_baseline_credit_projected',
   'no_policy_binding_or_execution_binding_created_until_ordinary_future_run','no_child_or_parent_scientific_behavior_demonstrated']}
  validate(read(PLAN/'OPERATOR_OUTPUT_SCHEMA001.json'),output,'result')
  save(inputs/'PREPARATION_RESULT001.json',output);save(EVIDENCE/'RESULTS001.json',output)
  print(json.dumps(output,sort_keys=True),flush=True)
 except BaseException as e:
  failure={'version':'configured_literature_localization_preparation_failure_v1','phase':phase,
   'exception_type':type(e).__name__,'message':str(e),'source_unchanged':None,'source_guard_error_type':None,
   'run_directory':str(RUN),'preserve_partial':True,'automatic_retry':False,'model_http_native_calls':0}
  if before is not None and arguments is not None and expected is not None:
   try:
    after=source_guard(arguments,expected);save(EVIDENCE/'SOURCE_AFTER_FAILURE001.json',after);failure['source_unchanged']=after==before
   except BaseException as guard_error:failure['source_guard_error_type']=type(guard_error).__name__
  validate(read(PLAN/'OPERATOR_OUTPUT_SCHEMA001.json'),failure,'failure')
  save(EVIDENCE/'FAILURE001.json',failure)
  print(json.dumps(failure,sort_keys=True),file=sys.stderr,flush=True)
  raise

if __name__=='__main__':main()
