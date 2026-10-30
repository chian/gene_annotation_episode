"""Capture one authorized preparation invocation; never retry it."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,time
OUT=Path(__file__).resolve().parent
ROOT=Path('/home/chia/repos/gene_annotation_episode')
CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
PLAN=Path('/tmp/configured-literature-caller-plan-20261022-001-vujlt8m4')
SCOPE=ROOT/'docs/CONFIGURED_LITERATURE_CALLER_ACTUAL_SCOPE_2026-10-22_001.md'
def desc(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(n,x):
 b=(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 with (OUT/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 (OUT/n).chmod(0o400)
assert desc(SCOPE)['sha256']=='81543967a4f5e85490c8f3fb92ee36e7491f46a4206c928ae01f79b86af7ab38'
assert desc(PLAN/'prepare_caller001.py')['sha256']=='4969578178bbffc23e042e0cff35cd4b64a9baa655398f7940464b7651136573'
manifest=json.loads((PLAN/'MANIFEST_FINAL001.json').read_text())
assert desc(PLAN/'MANIFEST_FINAL001.json')['sha256']=='d1a696d49123fbf6363f8cb9bb46a7dc2fc413ba06b1f9f9f9e81947a51f06ad'
for n,d in manifest['members'].items():assert desc(PLAN/n)==d,n
argv=['env','PYTHONDONTWRITEBYTECODE=1','PYTHONPATH='+str(CODE),'/home/chia/repos/gene_annotation_episode/.venv/bin/python',str(PLAN/'prepare_caller001.py'),'--prepare']
environment=dict(os.environ)
effective={**environment,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(CODE)}
start=datetime.now(timezone.utc).isoformat();began=time.monotonic()
save('START001.json',{'version':'actual_preparation_invocation_v1','argv':argv,'cwd':str(CODE),
 'environment':{'mode':'inherit_current_environment_with_adopted_env_overrides',
 'explicit_overrides':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(CODE)},
 'inherited_variable_names':sorted(environment),
 'effective_environment_sha256':hashlib.sha256(json.dumps(effective,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'credential_values_not_exported':True},
 'start_utc':start,'scope':desc(SCOPE),'operator':desc(PLAN/'prepare_caller001.py'),'packet_manifest':desc(PLAN/'MANIFEST_FINAL001.json'),
 'stdout_path':str(OUT/'preparation001.stdout.log'),'stderr_path':str(OUT/'preparation001.stderr.log'),
 'attempt_number':1,'automatic_retry':False})
print('Authorized preparation invocation started; logs: '+str(OUT),flush=True)
with (OUT/'preparation001.stdout.log').open('xb') as stdout,(OUT/'preparation001.stderr.log').open('xb') as stderr:
 completed=subprocess.run(argv,cwd=CODE,env=environment,stdout=stdout,stderr=stderr,check=False)
 stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
end=datetime.now(timezone.utc).isoformat()
result={'version':'actual_preparation_invocation_result_v1','start_utc':start,'end_utc':end,'elapsed_seconds':time.monotonic()-began,
 'exit_code':completed.returncode,'argv':argv,'cwd':str(CODE),'stdout':desc(OUT/'preparation001.stdout.log'),
 'stderr':desc(OUT/'preparation001.stderr.log'),'operator_after':desc(PLAN/'prepare_caller001.py'),
 'packet_manifest_after':desc(PLAN/'MANIFEST_FINAL001.json'),'attempt_number':1,'automatic_retry':False}
save('INVOCATION_RESULT001.json',result)
print(json.dumps(result,sort_keys=True),flush=True)
raise SystemExit(completed.returncode)
