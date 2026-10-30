"""Verify the two-file return-order correction on a separately frozen candidate."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = HERE / 'combined_unit_001/candidate'
OUT = HERE / 'return_revision_002'
CANDIDATE = OUT / 'candidate'
OVERRIDES = ('gene_annotation_episode/bvbrc_fastqutils_returns.py', 'tests/test_bvbrc_fastqutils_returns.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


old = json.loads((HERE / 'combined_unit_001/source_before.json').read_text())
assert {name: sha(OLD / name) for name in old} == old
OUT.mkdir(exist_ok=False)
before = {}
for name in old:
    source = HERE / 'candidate' / name if name in OVERRIDES else OLD / name
    before[name] = sha(source)
    target = CANDIDATE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    assert sha(target) == before[name]
assert {name for name in old if before[name] != old[name]} == set(OVERRIDES)
save('source_before.json', before)
save('delta.json', [{'path': name, 'old_sha256': old[name], 'new_sha256': before[name]} for name in OVERRIDES])
command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(OUT / 'temporary'), '--junitxml=' + str(OUT / 'tests.xml'),
    'tests/test_bvbrc_fastqutils_returns.py', 'tests/test_bvbrc_fastqutils_tool_info.py']
save('command.json', {'argv': command, 'cwd': str(CANDIDATE)})
receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
    'source_count': len(before), 'no_wall_time_limit': True,
    'qualification': 'Actual pure return/schema and tool catalog checks; authenticated host/Workflow is separate.'}
clock = time.monotonic()
environment = dict(os.environ, PYTHONPATH=str(CANDIDATE), PYTHONDONTWRITEBYTECODE='1')
with (OUT / 'output.log').open('x') as stream:
    result = subprocess.run(command, cwd=CANDIDATE, env=environment, stdout=stream, stderr=subprocess.STDOUT, preexec_fn=limits)
after = {name: sha(CANDIDATE / name) for name in before}
save('source_after.json', after)
cases = []
for case in ET.parse(OUT / 'tests.xml').iter('testcase'):
    outcome = next((name for name in ('failure', 'error', 'skipped') if case.find(name) is not None), 'passed')
    cases.append({'classname': case.get('classname'), 'name': case.get('name'), 'outcome': outcome})
save('cases.json', cases)
receipt.update(exit_code=result.returncode, changed_sources=[name for name in before if before[name] != after[name]],
    case_counts={name: sum(row['outcome'] == name for row in cases) for name in ('passed', 'failure', 'error', 'skipped')},
    ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - clock,
    scratch_bytes=sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()))
receipt['passed'] = (result.returncode == 0 and not receipt['changed_sources'] and bool(cases)
    and all(row['outcome'] == 'passed' for row in cases) and receipt['scratch_bytes'] < 4 * 1024**3)
save('receipt.json', receipt)
print(json.dumps(receipt))
raise SystemExit(0 if receipt['passed'] else 1)
