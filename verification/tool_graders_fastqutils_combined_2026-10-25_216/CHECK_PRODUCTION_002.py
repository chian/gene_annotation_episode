"""Focused shared-consumer regression checks on the applied checkout."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import resource
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / 'production_checks_002'
RUN.mkdir()
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TMPDIR'] = str(RUN)
os.chdir(ROOT)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (RUN / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


tests = ['tests/test_api_service_result_ordering.py']
application = json.loads((HERE / 'PRODUCTION_APPLICATION_001.json').read_bytes())
before = {r['path']: sha(ROOT / r['path']) for r in application['applied_files']}
assert all(before[r['path']] == r['after_sha256'] for r in application['applied_files'])
before[tests[0]] = sha(ROOT / tests[0])
args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(RUN / 'tmp'),
        '--junitxml', str(RUN / 'results.xml'), *tests]
save('command.json', dict(argv=args, cwd=str(ROOT), executable=sys.executable,
    application_receipt_sha256=sha(HERE / 'PRODUCTION_APPLICATION_001.json'),
    memory_limit_bytes=20 * 1024**3, scratch_limit_bytes=4 * 1024**3, wall_time_limit=None))
save('source_before.json', before)
save('started.json', dict(pid=os.getpid(), started_at=datetime.now(timezone.utc).isoformat()))
start = time.monotonic()
import pytest
with (RUN / 'stdout.log').open('x') as stdout, (RUN / 'stderr.log').open('x') as stderr:
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = int(pytest.main(args))
after = {name: sha(ROOT / name) for name in before}
save('source_after.json', after)
origins = {}
for name, module in sorted(sys.modules.items()):
    if name.split('.')[0] in ('gene_annotation_episode', 'method_loop'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(ROOT / name.split('.')[0]), (name, path)
        origins[name] = dict(path=str(path), sha256=sha(path))
save('actual_imports.json', origins)
cases = list(ET.parse(RUN / 'results.xml').iter('testcase'))
changed = [p for p in before if before[p] != after[p]]
scratch = sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file())
passed = code == 0 and not changed and scratch <= 4 * 1024**3
record = dict(passed=passed, exit_code=code, tests=len(cases),
    failures=sum(c.find('failure') is not None for c in cases),
    errors=sum(c.find('error') is not None for c in cases),
    skipped=sum(c.find('skipped') is not None for c in cases),
    changed_sources=changed, inspected_applied_paths=len(before),
    imported_application_and_loop_modules=len(origins),
    elapsed_seconds=time.monotonic()-start, max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    scratch_bytes=scratch, live_service_run=False, full_SAMstat_Workflow_proof=False,
    scope="rerun_all_six_cases_in_the_only_changed_test_module",
    prior_receipt_sha256=sha(HERE / "production_checks_001/receipt.json"),
    runtime_source_changed_for_fix=False)
save('receipt.json', record)
print(json.dumps(record, sort_keys=True))
raise SystemExit(0 if passed else 1)
