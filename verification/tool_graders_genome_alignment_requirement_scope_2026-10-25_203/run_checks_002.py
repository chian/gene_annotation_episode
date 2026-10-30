"""Run unchanged checks in the isolated candidate and preserve their evidence."""
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
CANDIDATE = OWN / sys.argv[1]
OUTPUT = OWN / sys.argv[2]
OUTPUT.mkdir(exist_ok=False)
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TMPDIR'] = str(OUTPUT)
sys.dont_write_bytecode = True
os.chdir(CANDIDATE)
sys.path.insert(0, str(CANDIDATE))
import pytest


def write(name, value):
    with (OUTPUT / name).open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def size():
    return sum(p.stat().st_size for p in OWN.rglob('*') if p.is_file())


scratch_before = size()
assert scratch_before < 4 * 1024**3
allow_loopback = any('test_bvbrc_genome_alignment_episode_flow.py' in arg for arg in sys.argv[3:])
original_connect = socket.socket.connect


def bounded_connect(sock, address):
    if sock.family in (socket.AF_INET, socket.AF_INET6):
        assert allow_loopback and address[0] == '127.0.0.1', ('unrequested network access', address)
    return original_connect(sock, address)


socket.socket.connect = bounded_connect
outcomes, native_captures = [], []


class Evidence:
    def pytest_runtest_logreport(self, report):
        outcomes.append({'nodeid': report.nodeid, 'when': report.when, 'outcome': report.outcome,
            'seconds': report.duration})

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        result = yield
        driver = item.funcargs.get('driver')
        if result.excinfo is not None or driver is None or not hasattr(driver, 'sheet'):
            return
        stem = 'native_%03d' % len(native_captures)
        # Read-only snapshots of objects already produced by the actual test.
        for label in ('body', 'sheet', 'components'):
            write(stem + '_' + label + '.json', getattr(driver, label))
        forms = [dict(row) for row in driver.store.db.execute('SELECT * FROM runtime_forms')]
        write(stem + '_runtime_forms.json', forms)
        native_captures.append({'nodeid': item.nodeid, 'stem': stem, 'format': driver.fmt,
            'native_artifact': driver.native['value']['artifact'] if hasattr(driver, 'native') else None})


started = datetime.now(timezone.utc)
start = time.perf_counter()
arguments = ['-q', '-p', 'no:cacheprovider', *sys.argv[3:],
    '--basetemp=' + str(OUTPUT / 'temporary'), '--junitxml=' + str(OUTPUT / 'tests.xml')]
with (OUTPUT / 'output.log').open('x') as log, redirect_stdout(log), redirect_stderr(log):
    code = pytest.main(arguments, plugins=[Evidence()])
write('test_outcomes.json', outcomes)
write('native_captures.json', native_captures)
scratch_after = size()
receipt = {'candidate': str(CANDIDATE), 'pytest_arguments': arguments,
    'started_at': started.isoformat(), 'finished_at': datetime.now(timezone.utc).isoformat(),
    'seconds': time.perf_counter() - start, 'exit_code': int(code),
    'memory_limit_bytes': 20 * 1024**3, 'scratch_limit_bytes': 4 * 1024**3,
    'single_file_limit_bytes': 4 * 1024**3, 'wall_time_limit': None,
    'scratch_before_bytes': scratch_before, 'scratch_after_bytes': scratch_after,
    'network_scope': 'controlled 127.0.0.1 HTTP only' if allow_loopback else 'AF_INET and AF_INET6 connections forbidden',
    'instrumentation': 'Pytest outcome records and read-only snapshots of completed driver fixtures; no scientific or custody implementation replaced.'}
write('receipt.json', receipt)
for path in OUTPUT.rglob('*'):
    if path.is_file():
        path.chmod(0o444)
assert scratch_after < 4 * 1024**3
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(int(code))
