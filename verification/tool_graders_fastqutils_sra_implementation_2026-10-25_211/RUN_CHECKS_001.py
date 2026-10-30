from pathlib import Path
import datetime, hashlib, json, os, resource, subprocess, sys, time

root = Path(__file__).resolve().parent
candidate = root / 'candidate'
out = root / 'checks_001'
out.mkdir(exist_ok=False)
def snapshot():
    return {str(p.relative_to(candidate)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(candidate.rglob('*')) if p.is_file()
        and not {'__pycache__','.pytest_cache'} & set(p.parts) and p.suffix != '.pyc'}
before = snapshot()
(out/'source_before.json').write_text(json.dumps(before,indent=2)+'\n')
argv = [sys.executable, '-B', '-m', 'pytest', '-q',
    'tests/test_bvbrc_fastqutils_sra.py',
    'tests/test_bvbrc_fastqutils_report_formats.py',
    'tests/test_bvbrc_fastqutils_saved_form_evolution.py',
    '--junitxml='+str(out/'results.xml'), '-p','no:cacheprovider']
env = dict(os.environ, PYTHONPATH=str(candidate), PYTHONDONTWRITEBYTECODE='1')
start = time.monotonic()
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(20*1024**3,20*1024**3))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
with (out/'stdout.log').open('wb') as stdout, (out/'stderr.log').open('wb') as stderr:
    process = subprocess.run(argv,cwd=candidate,env=env,stdout=stdout,stderr=stderr,preexec_fn=limits)
after = snapshot()
(out/'source_after.json').write_text(json.dumps(after,indent=2)+'\n')
receipt = dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,
    exit_code=process.returncode,elapsed_seconds=time.monotonic()-start,
    source_file_count=len(before),changed_sources=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)),
    memory_limit_bytes=20*1024**3,scratch_limit_bytes=4*1024**3,wall_time_limit=None,
    live_BV_BRC_job=False,episode_Workflow_verified=False)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt));print((out/'stdout.log').read_text())
sys.exit(process.returncode or bool(receipt['changed_sources']))
