"""Independently frozen FastqUtils scientific, return and library verification."""
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
ORIGINAL = HERE / 'candidate'
EVIDENCE = HERE / 'combined_unit_001'
CANDIDATE = EVIDENCE / 'candidate'
EVIDENCE.mkdir(exist_ok=False)
CANDIDATE.mkdir()
TESTS = tuple('tests/test_bvbrc_fastqutils_' + name + '.py' for name in (
    'contracts', 'sequence_formats', 'alignment_formats', 'sequence_calculators',
    'report_formats', 'report_calculators', 'metadata', 'projection', 'provider', 'returns', 'tool_info'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def excluded(path):
    rel = path.relative_to(ORIGINAL)
    return ('__pycache__' in rel.parts or '.pytest_cache' in rel.parts
        or str(rel) == 'tests/test_bvbrc_fastqutils_episode_flow.py'
        or str(rel).startswith('tests/fixtures/bvbrc_fastqutils/integration/'))


source_paths = [p for name in ('gene_annotation_episode', 'method_loop', 'tests')
    for p in (ORIGINAL / name).rglob('*') if p.is_file() and not excluded(p)]
source_paths += [ORIGINAL / name for name in ('pyproject.toml', 'README.md') if (ORIGINAL / name).is_file()]
assert sum(p.stat().st_size for p in source_paths) < 4 * 1024**3
before = {str(path.relative_to(ORIGINAL)): sha(path) for path in sorted(source_paths)}
for name, expected in before.items():
    source, destination = ORIGINAL / name, CANDIDATE / name
    assert sha(source) == expected, name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    assert sha(destination) == expected, name
save('source_before.json', before)
save('copy_contract.json', {'origin': str(ORIGINAL), 'source_count': len(before),
    'excluded_unrelated_work': ['tests/test_bvbrc_fastqutils_episode_flow.py', 'tests/fixtures/bvbrc_fastqutils/integration/', '__pycache__', '.pytest_cache'],
    'purpose': 'No mutable concurrent host tests are consumed by these eleven scoped test files.'})


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


started = time.monotonic()
argv = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(EVIDENCE / 'temporary'), '--junitxml=' + str(EVIDENCE / 'tests.xml'), *TESTS]
command = {'argv': argv, 'cwd': str(CANDIDATE), 'started_at': datetime.now(timezone.utc).isoformat(),
    'no_wall_time_limit': True, 'ram_limit_bytes': 20 * 1024**3, 'single_file_limit_bytes': 4 * 1024**3,
    'qualification': 'Actual parsers/calculators and pure saved-return/catalog consumers; controlled/synthetic data. Actual full custody/Workflow and live service are separate.'}
save('command.json', command)
env = dict(os.environ, PYTHONPATH=str(CANDIDATE), PYTHONDONTWRITEBYTECODE='1')
with (EVIDENCE / 'output.log').open('w') as log:
    result = subprocess.run(argv, cwd=CANDIDATE, env=env, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
after = {name: sha(CANDIDATE / name) for name in before}
save('source_after.json', after)
changed = [name for name in before if before[name] != after[name]]
cases = []
if (EVIDENCE / 'tests.xml').is_file():
    for case in ET.parse(EVIDENCE / 'tests.xml').iter('testcase'):
        outcome = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
        cases.append({'classname': case.get('classname'), 'name': case.get('name'), 'outcome': outcome})
save('cases.json', cases)
receipt = {**command, 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - started,
    'ended_at': datetime.now(timezone.utc).isoformat(), 'source_count': len(before), 'changed_sources': changed,
    'case_counts': {key: sum(c['outcome'] == key for c in cases) for key in ('passed', 'failure', 'error', 'skipped')},
    'scratch_bytes': sum(p.stat().st_size for p in EVIDENCE.rglob('*') if p.is_file())}
receipt['passed'] = (result.returncode == 0 and not changed and bool(cases)
    and all(c['outcome'] == 'passed' for c in cases) and receipt['scratch_bytes'] < 4 * 1024**3)
save('receipt.json', receipt)
print(json.dumps(receipt))
print((EVIDENCE / 'output.log').read_text()[-8000:])
raise SystemExit(0 if receipt['passed'] else 1)
