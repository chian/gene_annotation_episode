"""Run affected complete groups against a frozen candidate source closure."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import resource
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
CANDIDATE = OUT / 'candidate'
PYTHON = OUT.parent.parent / '.venv/bin/python'
GROUPS = [
    'test_bvbrc_proteome_document_selection.py', 'test_bvbrc_proteome_catalog_integration.py',
    'test_bvbrc_proteome_return_frames.py', 'test_bvbrc_proteome_tool_info.py',
    'test_bvbrc_proteome_bundle_contracts.py', 'test_bvbrc_proteome_bundle_resolution.py',
    'test_bvbrc_proteome_bundle_projection.py', 'test_bvbrc_proteome_submitted_parameters.py',
    'test_bvbrc_appservice_request_content.py', 'test_bvbrc_appservice_contracts.py',
    'test_bvbrc_appservice_bundle_values.py', 'test_bvbrc_appservice_adapter_binding.py',
    'test_bvbrc_proteome_returns.py', 'test_bvbrc_proteome_returns_original.py',
    'test_bvbrc_appservice_host.py', 'test_bvbrc_appservice_publication.py',
    'test_bvbrc_appservice_saved_results.py', 'test_communication.py',
    'test_execution_episodes_family.py', 'test_bvbrc_proteome_host_integration.py']


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def snapshot():
    return {str(p.relative_to(CANDIDATE)): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        'bytes': p.stat().st_size} for p in sorted(CANDIDATE.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

(OUT / 'final_test_tmp_002').mkdir(exist_ok=False)
runner_pin = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
before = snapshot()
environment = {'PYTHONPATH': str(CANDIDATE) + ':' + str(CANDIDATE / 'tests'),
    'PYTHONDONTWRITEBYTECODE': '1', 'PROTEOME_EXAMPLE_DIRECTORY': str(OUT / 'numerical_example_final_002')}
groups = {'core': [n for n in GROUPS if n != 'test_bvbrc_proteome_host_integration.py'],
          'host': ['test_bvbrc_proteome_host_integration.py']}
commands = {name: [str(PYTHON), '-m', 'pytest', '-q', *['tests/' + n for n in files],
    '--junitxml=' + str(OUT / ('TEST_013_' + name + '.xml')),
    '--basetemp=' + str(OUT / 'final_test_tmp_002' / name),
    '-o', 'cache_dir=' + str(OUT / ('final_pytest_cache_002_' + name))] for name, files in groups.items()}
started = timestamp()
write('TEST_013_BEFORE.json', {'timestamp_utc': started, 'cwd': str(CANDIDATE),
    'commands': commands, 'environment': environment, 'runner_sha256': runner_pin, 'files': before})
start = time.monotonic()
processes, streams, results = {}, {}, {}
for name, command in commands.items():
    streams[name] = (OUT / ('TEST_013_' + name + '.log')).open('w')
    processes[name] = subprocess.Popen(command, cwd=CANDIDATE, env={**os.environ, **environment},
        stdout=streams[name], stderr=subprocess.STDOUT)
for name, process in processes.items():
    results[name] = process.wait()
    streams[name].close()
after = snapshot()
changes = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
receipt = {'started_utc': started, 'finished_utc': timestamp(), 'elapsed_seconds': time.monotonic() - start,
    'commands': commands, 'environment': environment, 'cwd': str(CANDIDATE), 'returncodes': results,
    'source_changes_during_run': changes, 'files': after,
    'runner_before_sha256': runner_pin, 'runner_after_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'child_maximum_resident_set_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    'test_scratch_bytes': sum(p.stat().st_size for p in (OUT / 'final_test_tmp_002').rglob('*') if p.is_file())}
write('TEST_013_AFTER.json', receipt)
import xml.etree.ElementTree as ET
suites = ET.Element('testsuites')
for name in commands:
    path = OUT / ('TEST_013_' + name + '.xml')
    if path.exists():
        for suite in ET.parse(path).getroot(): suites.append(suite)
ET.ElementTree(suites).write(OUT / 'TEST_013.xml', encoding='utf-8', xml_declaration=True)
print(json.dumps({k:v for k,v in receipt.items() if k != 'files'}))
if changes or receipt['runner_after_sha256'] != runner_pin:
    raise SystemExit('candidate source closure changed during final verification')
raise SystemExit(max(results.values()))
