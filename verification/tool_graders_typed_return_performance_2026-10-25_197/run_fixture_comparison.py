"""Run the five original fixture-blocked cases on an exact owned comparison tree."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

OWN = Path(__file__).resolve().parent
TREE = OWN / 'fixture_comparison_candidate'
OUTPUT = Path(sys.argv[1]).resolve()
assert OUTPUT.parent == OWN and OUTPUT.is_dir()
EXPECTED = json.loads((OWN / 'fixture_comparison_manifest.json').read_text())
TARGETS = [
    'tests/test_bvbrc_alignment_returns.py::test_retained_native_requested_values_survive_the_closed_return_contract[native_msa]',
    'tests/test_bvbrc_alignment_returns.py::test_retained_native_requested_values_survive_the_closed_return_contract[native_metacats]',
    'tests/test_bvbrc_alignment_returns.py::test_retained_native_requested_values_survive_the_closed_return_contract[native_xmfa]',
    'tests/test_bvbrc_alignment_returns.py::test_saved_return_does_no_io_parsing_or_scientific_recalculation',
    'tests/test_bvbrc_minhash_return_boundaries.py::test_own_and_received_boundary_rejects_wrong_context_and_fabricated_source',
]

def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def manifest(name):
    actual = {path: hashlib.sha256((TREE / path).read_bytes()).hexdigest() for path in EXPECTED}
    save(name, actual)
    assert actual == EXPECTED

def origins(name):
    result = {}
    for key, module in list(sys.modules.items()):
        if key.split('.')[0] not in {'gene_annotation_episode', 'method_loop'}:
            continue
        path = getattr(module, '__file__', None)
        if path:
            result[key] = str(Path(path).resolve())
            assert Path(path).resolve().is_relative_to(TREE), (key, path)
    save(name, result)

def event(value):
    with (OUTPUT / 'test_events.jsonl').open('a') as stream:
        stream.write(json.dumps({**value, 'at': datetime.now(timezone.utc).isoformat()}) + '\n')

class Evidence:
    def pytest_collection_finish(self, session):
        nodes = [item.nodeid for item in session.items]
        save('collected.json', nodes)
        assert nodes == TARGETS
        origins('package_origins_before.json')

    def pytest_runtest_logstart(self, nodeid, location):
        event({'event': 'started', 'nodeid': nodeid})

    def pytest_runtest_logreport(self, report):
        event({'event': 'report', 'nodeid': report.nodeid, 'phase': report.when,
            'outcome': report.outcome, 'duration_seconds': report.duration})

manifest('source_before.json')
os.chdir(TREE)
sys.path[:] = [str(TREE)] + [path for path in sys.path if path != str(OWN / 'candidate') and path != str(TREE)]
os.environ['PYTHONPATH'] = str(TREE)
save('process.json', {'pid': os.getpid(), 'ppid': os.getppid(), 'cwd': str(TREE),
    'started_at': datetime.now(timezone.utc).isoformat(),
    'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
import pytest
arguments = ['-vv', '-p', 'no:cacheprovider', *TARGETS,
    '--basetemp=' + str(OUTPUT / 'temporary'), '--junitxml=' + str(OUTPUT / 'tests.xml')]
save('pytest_arguments.json', arguments)
try:
    result = int(pytest.main(arguments, plugins=[Evidence()]))
    save('pytest_exit.json', {'exit_code': result, 'finished_at': datetime.now(timezone.utc).isoformat()})
finally:
    manifest('source_after.json')
    origins('package_origins_after.json')
sys.exit(result)
