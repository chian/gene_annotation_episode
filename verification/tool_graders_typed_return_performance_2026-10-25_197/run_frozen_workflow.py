"""Run the three root-authorized existing tests against frozen197, without shims."""
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

OWN = Path(__file__).resolve().parent
CANDIDATE = OWN / 'candidate'
OUTPUT = Path(sys.argv[1]).resolve()
assert OUTPUT.parent == OWN and OUTPUT.is_dir()
os.chdir(CANDIDATE)
sys.path.insert(0, str(CANDIDATE))
sys.path.insert(0, str(CANDIDATE / 'tests'))
sys.dont_write_bytecode = True

EXPECTED_SOURCE = json.loads((OWN / 'source_after.json').read_text())
EXPECTED_PINS = {
    'bvbrc_proteome_bundle_adapter': '4a38563301a75481c9fc8cfcde77e0a09b9d8e08f3c0562e9635c18692e44a20',
    'bvbrc_proteome_bundle_adapter_v2': '7dbdd8cfbc5193d149af6bfd314e0199ff074a1d671a39e1395a785b22b10ce9',
    'bvbrc_comparative_systems_bundle_adapter': '0faeb6e2419a17f4a56161e47fa8dd5da3704558cedb326eeb2b2762c49cb2f2',
}
SELECTED = [
    'tests/test_bvbrc_proteome_directional_episode_path.py',
    'tests/test_bvbrc_comparative_systems_episode_flow.py::test_actual_selected_tool_shared_workflow_native_publication_and_typed_parent_return',
]


def write(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2) + '\n')


def snapshot():
    return {name: hashlib.sha256((CANDIDATE / name).read_bytes()).hexdigest()
            for name in EXPECTED_SOURCE}


def event(**value):
    value['at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (OUTPUT / 'test_events.jsonl').open('a') as stream:
        stream.write(json.dumps(value) + '\n')


def package_origins():
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name.split('.')[0] in {'gene_annotation_episode', 'method_loop'}:
            path = getattr(module, '__file__', None)
            if path:
                path = Path(path).resolve()
                assert path.is_relative_to(CANDIDATE), (name, str(path))
                origins[name] = str(path.relative_to(CANDIDATE))
    return origins


class Evidence:
    def pytest_collection_finish(self, session):
        items = [item.nodeid for item in session.items]
        assert len(items) == 3, items
        write('collected.json', items)
        write('package_origins_before.json', package_origins())

    def pytest_runtest_logstart(self, nodeid, location):
        event(event='started', nodeid=nodeid)

    def pytest_runtest_logreport(self, report):
        event(event='report', nodeid=report.nodeid, phase=report.when,
              outcome=report.outcome, duration_seconds=report.duration)


write('process.json', {'pid': os.getpid(), 'ppid': os.getppid(), 'argv': sys.argv,
    'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'cwd': str(Path.cwd()), 'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'no_write_shim': False, 'selected_tests': SELECTED})
before = snapshot()
write('source_before.json', before)
assert before == EXPECTED_SOURCE, 'Candidate differs from the approved frozen manifest'
pins = {}
for name, expected in EXPECTED_PINS.items():
    module = importlib.import_module('gene_annotation_episode.' + name)
    assert Path(module.__file__).resolve().is_relative_to(CANDIDATE)
    pins[name] = module.implementation_sha256()
    assert pins[name] == expected, (name, pins[name], expected)
write('asserted_pins.json', pins)
import pytest
arguments = ['-vv', '-p', 'no:cacheprovider', *SELECTED,
    '--basetemp=' + str(OUTPUT / 'temporary'), '--junitxml=' + str(OUTPUT / 'tests.xml')]
write('pytest_arguments.json', arguments)
try:
    result = pytest.main(arguments, plugins=[Evidence()])
finally:
    after = snapshot()
    write('source_after.json', after)
    write('package_origins_after.json', package_origins())
    assert after == before, 'Frozen source changed during Workflow verification'
write('pytest_exit.json', {'exit_code': int(result)})
raise SystemExit(result)
