"""Run only the authorized seven original cases; retain exact source and outcomes."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import socket
import sys
import time

OWN = Path(__file__).resolve().parent
CANDIDATE = OWN / 'composition_candidate'
OUTPUT = OWN / 'composition_checks_001'
OUTPUT.mkdir(exist_ok=False)
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TMPDIR'] = str(OUTPUT)
sys.dont_write_bytecode = True
os.chdir(CANDIDATE)
sys.path.insert(0, str(CANDIDATE))
sys.path.insert(0, str(CANDIDATE / 'tests'))
SELECTED = [
    'tests/test_form_reference_validation.py::test_public_genome_resolvers_reuse_facts_but_preserve_possession_and_semantics',
    'tests/test_bvbrc_genome_alignment_episode_flow.py',
]
EXPECTED = json.loads((OWN / 'COMPOSITION_SOURCE_BEFORE_001.json').read_text())


def write(name, value):
    with (OUTPUT / name).open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def snapshot():
    return {name: hashlib.sha256((CANDIDATE / name).read_bytes()).hexdigest() for name in EXPECTED}


def scratch():
    return sum(p.stat().st_size for p in OWN.rglob('*') if p.is_file())


original_connect = socket.socket.connect


def bounded_connect(sock, address):
    if sock.family in (socket.AF_INET, socket.AF_INET6):
        assert address[0] == '127.0.0.1', ('unrequested network access', address)
    return original_connect(sock, address)


socket.socket.connect = bounded_connect
import pytest
outcomes = []


def event(**value):
    value['at'] = datetime.now(timezone.utc).isoformat()
    with (OUTPUT / 'test_events.jsonl').open('a') as stream:
        stream.write(json.dumps(value) + '\n')


class Evidence:
    def pytest_collection_finish(self, session):
        items = [item.nodeid for item in session.items]
        write('collected.json', items)
        assert len(items) == 7, items

    def pytest_runtest_logstart(self, nodeid, location):
        event(event='started', nodeid=nodeid)

    def pytest_runtest_logreport(self, report):
        row = {'nodeid': report.nodeid, 'when': report.when, 'outcome': report.outcome,
               'seconds': report.duration}
        outcomes.append(row)
        event(event='report', **row)
        assert scratch() < 4 * 1024**3


arguments = ['-vv', '-p', 'no:cacheprovider', *SELECTED,
    '--basetemp=' + str(OUTPUT / 'temporary'), '--junitxml=' + str(OUTPUT / 'tests.xml')]
start = time.perf_counter()
before = snapshot()
assert before == EXPECTED
write('source_before.json', before)
write('process.json', {'argv': sys.argv, 'pid': os.getpid(), 'executable': sys.executable,
    'cwd': str(Path.cwd()), 'started_at': datetime.now(timezone.utc).isoformat(),
    'pytest_arguments': arguments, 'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
scratch_before = scratch()
assert scratch_before < 4 * 1024**3
with (OUTPUT / 'output.log').open('x') as log, redirect_stdout(log), redirect_stderr(log):
    code = pytest.main(arguments, plugins=[Evidence()])
after = snapshot()
write('source_after.json', after)
write('test_outcomes.json', outcomes)
origins = {}
for name, module in tuple(sys.modules.items()):
    if name.split('.')[0] in {'gene_annotation_episode', 'method_loop'} and getattr(module, '__file__', None):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(CANDIDATE), (name, path)
        origins[name] = str(path.relative_to(CANDIDATE))
write('package_origins.json', origins)
receipt = {'exit_code': int(code), 'seconds': time.perf_counter() - start,
    'completed_at': datetime.now(timezone.utc).isoformat(), 'candidate': str(CANDIDATE),
    'source_paths': len(before), 'frozen_source_unchanged': before == after,
    'memory_limit_bytes': 20 * 1024**3, 'scratch_limit_bytes': 4 * 1024**3,
    'scratch_before_bytes': scratch_before, 'scratch_after_bytes': scratch(), 'wall_time_limit': None,
    'network_scope': 'Only the existing Workflow fixture controlled 127.0.0.1 HTTP; host test blocks live transport',
    'new_native_execution': False, 'new_live_bvbrc': False,
    'instrumentation': 'Pytest reporting and source/package-origin snapshots only; unchanged original tests and production.'}
write('receipt.json', receipt)
assert before == after
assert receipt['scratch_after_bytes'] < 4 * 1024**3
for path in OUTPUT.iterdir():
    if path.is_file():
        path.chmod(0o444)
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(int(code))
