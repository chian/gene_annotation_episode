"""DRAFT: launch the ordinary prepared fixed-case CLI once, only after adoption.

Standard library only. No scientific loop, observer, policy, retry or signals.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,shutil,stat,subprocess,sys,time
PLAN=Path(__file__).resolve().parent
CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
RUN=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')
OUT=Path('/tmp/configured-literature-localization-launch-20261022-001')
PIN='3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'

def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(p.read_text())
def descriptor(p):
 for q in (p,*p.parents):
  if q.is_symlink():raise ValueError('symlink_path')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('regular_file_required')
  h=hashlib.sha256();size=0
  with os.fdopen(fd,'rb',closefd=False) as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b);size+=len(b)
  return {'path':str(p),'bytes':size,'sha256':h.hexdigest()}
 finally:os.close(fd)
def save(n,x):
 raw=(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 with (OUT/n).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 (OUT/n).chmod(0o400)
def runtime():
 h=hashlib.sha256();files=[]
 for p in sorted(p for package in ('gene_annotation_episode','method_loop') for p in (CODE/package).rglob('*.py')):
  value=descriptor(p);relative=p.relative_to(CODE).as_posix();files.append({'relative_path':relative,**value})
  h.update(relative.encode()+b'\0');h.update(bytes.fromhex(value['sha256']))
 return {'sha256':h.hexdigest(),'file_count':len(files),'files':files}
def process_identity(pid):
 # One immediate metadata read, never process control or a polling loop.
 try:
  body=Path('/proc/'+str(pid)+'/stat').read_text();fields=body.rsplit(')',1)[1].split()
  return {'pid':pid,'linux_start_ticks':int(fields[19]),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
 except (OSError,ValueError,IndexError):return {'pid':pid,'linux_start_ticks':None,'boot_id':None}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--launch',required=True,action='store_true');parser.parse_args()
 os.umask(0o077);OUT.mkdir(mode=0o700)
 child=None;phase='validate_prepared_operands';start=now();begin=time.monotonic()
 try:
  command=read(PLAN/'LAUNCH_COMMAND_DRAFT001.json');inputs=read(PLAN/'INPUTS001.json')
  for n,expected in inputs['members'].items():
   actual=descriptor(PLAN/n)
   if any(actual[k]!=expected[k] for k in ('sha256','bytes')):raise ValueError('launch_packet_changed:'+n)
  verification_path=Path(command['independent_preparation_verification']['path'])
  verification_witness=descriptor(verification_path)
  if any(verification_witness[k]!=command['independent_preparation_verification'][k] for k in ('sha256','bytes')):raise ValueError('independent_preparation_verification_changed')
  verification=read(verification_path)
  if verification['status']!='verified_prepared_not_started' or verification['source_pin']!={'sha256':PIN,'file_count':137} or verification['selected_inputs_unchanged'] is not True:raise ValueError('independent_preparation_verification_unavailable')
  before=runtime()
  if before['sha256']!=PIN or before['file_count']!=137:raise ValueError('runtime_pin_changed')
  for expected in command['inputs'].values():
   actual=descriptor(Path(expected['path']))
   if any(actual[k]!=expected[k] for k in ('sha256','bytes')):raise ValueError('prepared_operand_changed:'+expected['path'])
  expected=command['working_database_before_launch'];actual=descriptor(Path(expected['path']))
  if any(actual[k]!=expected[k] for k in ('sha256','bytes')):raise ValueError('prepared_working_database_changed')
  policy=CODE/'gene_annotation_episode/api_planning_case_policy.py'
  if descriptor(policy)['sha256']!=command['policy_source_sha256']:raise ValueError('factory_source_changed')
  if any((RUN/n).exists() for n in ['run.json','policy-binding.json','episode-execution-binding.json']):raise ValueError('new_run_already_started_or_partially_bound')
  if '--resume' in command['argv']:raise ValueError('resume_not_authorized')
  environment={**os.environ,**command['environment_overrides']}
  save('SOURCE_BEFORE001.json',before)
  save('LAUNCH_COMMAND001.json',{**command,'status':'actual_selected_launch','start_utc':start,
   'driver':descriptor(Path(__file__)),'input_manifest':descriptor(PLAN/'INPUTS001.json'),
   'environment':{'mode':'inherit_current_with_exact_explicit_overrides','overrides':command['environment_overrides'],
   'inherited_variable_names':sorted(os.environ),'effective_environment_sha256':hashlib.sha256(json.dumps(environment,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'credential_values_not_exported':True},
   'resolved_codex':shutil.which('codex',path=environment.get('PATH')),
   'stdout_path':str(OUT/'scientific001.stdout.log'),'stderr_path':str(OUT/'scientific001.stderr.log'),
   'automatic_retry':False,'cancellation_requested':False})
  phase='spawn_ordinary_cli'
  with (OUT/'scientific001.stdout.log').open('xb') as stdout,(OUT/'scientific001.stderr.log').open('xb') as stderr:
   child=subprocess.Popen(command['argv'],cwd=command['cwd'],env=environment,stdout=stdout,stderr=stderr,start_new_session=True)
   identity=process_identity(child.pid)
   save('PROCESS_STARTED001.json',{'started_at_utc':now(),'process':identity,'argv':command['argv'],'cwd':command['cwd'],
    'start_new_session':True,'meaning':'Ordinary fixed-case CLI process; no scientific action injected.'})
   print(json.dumps({'status':'ordinary_cli_started','process':identity,'evidence_directory':str(OUT)},sort_keys=True),flush=True)
   phase='wait_ordinary_cli'
   exit_code=child.wait()  # No timeout, retries, cancellation, private work or observation loop.
   stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
  after=runtime();save('SOURCE_AFTER001.json',after)
  result={'version':'configured_literature_launch_driver_result_v1','status':'ordinary_cli_exited','exit_code':exit_code,
   'start_utc':start,'end_utc':now(),'elapsed_seconds':time.monotonic()-begin,'process':identity,
   'runtime_inputs_unchanged':after==before,'stdout':descriptor(OUT/'scientific001.stdout.log'),'stderr':descriptor(OUT/'scientific001.stderr.log'),
   'scientific_completion':'not_inferred_from_exit','automatic_retry':False,'cancellation_requested':False}
  save('EXIT001.json',result);print(json.dumps(result,sort_keys=True),flush=True)
  return exit_code
 except BaseException as error:
  failure={'version':'configured_literature_launch_driver_failure_v1','phase':phase,'exception_type':type(error).__name__,
   'message':str(error),'captured_at_utc':now(),'process':None if child is None else process_identity(child.pid),
   'automatic_retry':False,'signals_sent':False,'child_left_independent':child is not None,
   'meaning':'Preserve logs/state. No cancellation/relaunch/fallback was performed.'}
  save('DRIVER_FAILURE001.json',failure)
  print(json.dumps(failure,sort_keys=True),file=sys.stderr,flush=True)
  raise
if __name__=='__main__':raise SystemExit(main())
