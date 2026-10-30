"""One frozen combined-source detached check and immediate fixture retention."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET

CODE = Path('/tmp/gene-annotation-configured-caller-20261022-006')
MAIN = Path('/home/chia/repos/gene_annotation_episode')
PYTHON = MAIN / '.venv/bin/python'
HERE = Path(__file__).parent
NODE = ('tests/test_api_planning_case_reconstruction.py::'
        'test_new_policy_detached_forecast_return_and_parent_receipt')


def witness(path):
    body = path.read_bytes()
    return {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def capture(expected_pin):
    baseline_path = CODE / 'GENERATION_BASELINE_006.json'
    assert witness(baseline_path)['sha256'] == '5ba160e1bcbdb14c08b5a929015143b7bd1d316eedc5dd2d239b5f45c6ab644e'
    baseline = json.loads(baseline_path.read_text())
    guards = {}
    for group in ('files', 'static_assets', 'instructions'):
        for relative, expected in baseline[group].items():
            actual = witness(CODE / relative)
            assert all(actual[key] == expected[key] for key in actual), (group, relative)
            guards[relative] = actual
    runtime = sorted(p for package in ('gene_annotation_episode', 'method_loop')
                     for p in (CODE / package).rglob('*.py'))
    digest = hashlib.sha256()
    for path in runtime:
        relative = path.relative_to(CODE).as_posix()
        actual = guards[relative] = witness(path)
        digest.update(relative.encode() + b'\0' + bytes.fromhex(actual['sha256']))
    assert len(runtime) == 136 and digest.hexdigest() == expected_pin
    for relative, expected in {
        'tests/test_api_planning_case_policy.py': '7f6a2b561bc6c6c870db1f5ea05d9875828cb351db3487220fd994049abafb70',
        'tests/test_api_planning_case_reconstruction.py': '5dc046f9ab18ef576e61ec20b67a35cd94752416447f3670085e13b722d1c7bc',
    }.items():
        actual = guards[relative] = witness(CODE / relative)
        assert actual['sha256'] == expected
    original = hashlib.sha256()
    original_files = sorted(p for package in ('gene_annotation_episode', 'method_loop')
                            for p in (MAIN / package).rglob('*.py'))
    for path in original_files:
        original.update(path.relative_to(MAIN).as_posix().encode() + b'\0')
        original.update(bytes.fromhex(witness(path)['sha256']))
    assert len(original_files) == 122
    assert original.hexdigest() == 'a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a'
    return {'runtime_pin': digest.hexdigest(), 'runtime_files': len(runtime),
            'original_runtime_pin': original.hexdigest(), 'original_runtime_files': 122,
            'baseline_source_tests': 348, 'baseline_static_assets': 319,
            'baseline_normative_inputs': 8, 'files': guards,
            'unselected_C_and_JOIN_tests_are_not_pinned_dependencies': True,
            'scientific_database_opens': 0}


def preserve(source):
    destination = HERE / 'FIXTURES001'
    destination.mkdir()
    rows, aliases = {}, {}
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source).as_posix()
        if path.is_symlink():
            aliases[relative] = os.readlink(path)
            continue
        if not path.is_file():
            continue
        before = path.stat()
        actual = witness(path)
        target = destination / 'raw-tree' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        after = path.stat()
        assert before.st_size == after.st_size == actual['bytes']
        assert before.st_mtime_ns == after.st_mtime_ns
        assert stat.S_IMODE(before.st_mode) == stat.S_IMODE(after.st_mode)
        assert witness(path) == witness(target) == actual
        assert target.stat().st_mtime_ns == before.st_mtime_ns
        assert stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(before.st_mode)
        rows[relative] = {**actual, 'mode': f'{stat.S_IMODE(before.st_mode):04o}',
                          'mtime_ns': before.st_mtime_ns}
    membership = {p.relative_to(source).as_posix() for p in source.rglob('*')
                  if p.is_file() and not p.is_symlink()}
    assert rows and set(rows) == membership
    record = {'source': str(source), 'files': rows,
              'file_count': len(rows), 'total_bytes': sum(r['bytes'] for r in rows.values()),
              'pytest_alias_symlinks_not_followed': aliases,
              'source_and_copy_membership_hash_size_mode_mtime_equal': True,
              'databases_opened': 0,
              'limit': 'Scripted engineering fixture; no relocated resumability claim.'}
    save('PRESERVATION001.json', record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-pin', required=True)
    args = parser.parse_args()
    before = capture(args.expected_pin)
    save('INPUTS_BEFORE001.json', before)
    basetemp = Path('/tmp/configured-caller-root-006-worker-' + uuid.uuid4().hex)
    assert not basetemp.exists()
    command = [str(PYTHON), '-m', 'pytest', '-p', 'no:cacheprovider', NODE, '-q',
               '--basetemp=' + str(basetemp), '--junitxml=' + str(HERE / 'worker001.xml')]
    environment = os.environ.copy()
    environment.update(PYTHONDONTWRITEBYTECODE='1',
                       PYTHONPATH=str(CODE / 'tests') + ':' + str(CODE))
    save('COMMAND001.json', {'argv': command, 'cwd': str(CODE),
         'environment_overrides': {key: environment[key]
                                   for key in ('PYTHONDONTWRITEBYTECODE', 'PYTHONPATH')},
         'basetemp': str(basetemp)})
    started = time.monotonic()
    with (HERE / 'worker001.log').open('xb') as stream:
        process = subprocess.run(command, cwd=CODE, env=environment,
                                 stdout=stream, stderr=subprocess.STDOUT)
    elapsed = time.monotonic() - started
    # Retain every actual fixture before inspecting result summaries.
    retained = preserve(basetemp)
    after = capture(args.expected_pin)
    save('INPUTS_AFTER001.json', after)
    assert before == after
    cases = []
    if (HERE / 'worker001.xml').is_file():
        for case in ET.parse(HERE / 'worker001.xml').iter('testcase'):
            cases.append({'name': case.attrib['name'],
                          'classname': case.attrib.get('classname'),
                          'seconds': case.attrib.get('time'),
                          'failures': len(case.findall('failure')),
                          'errors': len(case.findall('error')),
                          'skipped': len(case.findall('skipped'))})
    result = {'version': 'combined006_detached_worker_check_v1',
              'exit_code': process.returncode, 'elapsed_seconds': elapsed,
              'runtime_pin': args.expected_pin, 'cases': cases,
              'inputs_unchanged': True, 'retained_files': retained['file_count'],
              'retained_bytes': retained['total_bytes'],
              'actual_model_calls': 0, 'actual_scientific_runs': 0,
              'scope': 'Same already reviewed scripted detached node, final combined136 source.'}
    save('RESULTS001.json', result)
    print(json.dumps(result, sort_keys=True), flush=True)
    assert process.returncode == 0 and len(cases) == 1
    assert not any(cases[0][key] for key in ('failures', 'errors', 'skipped'))


if __name__ == '__main__':
    main()
