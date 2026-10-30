"""One actual readonly-source custody call; no model, prepare or episode launch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path('/home/chia/repos/gene_annotation_episode')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-006')
PLAN = ROOT / 'verification/configured_api_caller_plan_2026-10-22_001'
CPLAN = ROOT / 'verification/scientific_checkpoint_custody_plan_2026-10-22_001'
SOURCE = ROOT / 'cases/gene_001/runs/configured_development_002'
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
PIN = '209ff0d8ca80a6ee2a592f997933115e2f688f8ccc90e6db35e40146dabb613f'
OLD_PIN = 'a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a'
OLD_RUN = 'run_a9cae64280ed405594a79255d659f917'
PENDING = '21e2407799ae840e2192619396d1c74ee823fc445dab2a13aab5e940816ad16c'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def witness(path):
    if not path.exists():
        return None
    assert not path.is_symlink() and path.is_file()
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'sha256': sha(body)}


def pin(root):
    digest = hashlib.sha256()
    files = sorted(path for package in ('gene_annotation_episode', 'method_loop')
                   for path in (root / package).rglob('*.py'))
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode() + b'\0')
        digest.update(bytes.fromhex(witness(path)['sha256']))
    return digest.hexdigest(), len(files)


def save(path, value):
    with path.open('xb') as stream:
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o400)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def require_passing_xml(path, count):
    cases = list(ET.parse(path).iter('testcase'))
    assert len(cases) == count
    assert all(not any(case.find(kind) is not None
                       for kind in ('failure', 'error', 'skipped')) for case in cases)
    return witness(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--join-xml', type=Path, required=True)
    parser.add_argument('--corrected-c-xml', type=Path, required=True)
    args = parser.parse_args()
    # These are operator input checks, not runtime scientific gates.
    joined = require_passing_xml(args.join_xml, 1)
    corrected = require_passing_xml(args.corrected_c_xml, 5)
    worker_dir = Path('/tmp/configured-caller-root-006-worker-001')
    worker = json.loads((worker_dir / 'RESULTS001.json').read_text())
    assert worker['exit_code'] == 0 and worker['runtime_pin'] == PIN
    assert worker['inputs_unchanged'] is True
    worker_xml = require_passing_xml(worker_dir / 'worker001.xml', 1)
    assert pin(CODE) == (PIN, 136) and pin(ROOT) == (OLD_PIN, 122)
    assert witness(CODE / 'gene_annotation_episode/scientific_checkpoint_fork.py')['sha256'] == '166d459b38295ab4003ebe39babd22184a96482dba5146b3b2479291ebd423ab'
    manifest_path = PLAN / 'MANIFEST_FINAL.json'
    assert witness(manifest_path)['sha256'] == 'b7b2f62aa19399207fa31741f3f7a5eba740fd1556623b3424305ffa901b64fd'
    for member in json.loads(manifest_path.read_text())['members']:
        actual = witness(PLAN / member['path'])
        assert actual['sha256'] == member['sha256'] and actual['bytes'] == member['bytes']
    schema_path = CPLAN / 'SCHEMAS004.json'
    assert witness(schema_path)['sha256'] == 'b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112'
    schema = json.loads(schema_path.read_text())
    def validate(value, name):
        Draft202012Validator({'$ref': '#/$defs/' + name, '$defs': schema['$defs']},
                            format_checker=FormatChecker()).validate(value)

    assert RUN.parent.is_dir() and not RUN.exists() and not RUN.is_symlink()
    assert not any(path.is_symlink() for path in (RUN.parent, *RUN.parent.parents))
    database = SOURCE / 'workspace/state.sqlite3'
    guards = {str(path): witness(path) for base in
              (database, SOURCE / 'native-jobs/jobs.sqlite')
              for path in (base, Path(str(base) + '-wal'), Path(str(base) + '-shm'))}
    assert all(value is None or value['bytes'] == 0
               for path, value in guards.items() if path.endswith('-wal'))
    connection = sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        rows = connection.execute('SELECT run_id,settings FROM runtime_runs').fetchall()
        assert len(rows) == 1 and rows[0][0] == OLD_RUN
        settings = json.loads(rows[0][1])
        inherited_original = settings['scientific_knowledge']['initial_known_record_refs']
        selected = sorted(set(inherited_original) | {row[0] for table in ('inputs', 'records')
                          for row in connection.execute('SELECT id FROM ' + table)})
        pending = connection.execute('SELECT request FROM runtime_model_calls WHERE response IS NULL').fetchall()
        assert len(pending) == 1 and sha(pending[0][0].encode()) == PENDING
        counts = {table: connection.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                  for table in ('runtime_runs', 'runtime_episodes', 'runtime_actions',
                                'runtime_observations', 'runtime_model_calls')}
        assert counts == {'runtime_runs': 1, 'runtime_episodes': 1,
                          'runtime_actions': 179, 'runtime_observations': 175,
                          'runtime_model_calls': 180}
    finally:
        connection.close()
    assert guards == {path: witness(Path(path)) for path in guards}
    RUN.mkdir(mode=0o700)
    parent_fd = os.open(RUN.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    inputs = RUN / 'caller-inputs'
    inputs.mkdir(mode=0o700)
    arguments = {'source_workspace': str(SOURCE / 'workspace'),
                 'source_run_directory': str(SOURCE), 'source_implementation_root': str(ROOT),
                 'source_run_id': OLD_RUN, 'expected_source_implementation_sha256': OLD_PIN,
                 'expected_pending_request_sha256': PENDING,
                 'destination_workspace': str(RUN / 'workspace'),
                 'initial_known_record_refs': selected}
    save(inputs / 'C_SELECTION001.json', {'arguments': arguments,
         'meaning': 'All committed inputs/records plus every explicitly inherited original input.',
         'source_database_guards': guards, 'source_runtime_counts': counts,
         'execution_implementation_pin': PIN, 'engineering_checks': {
             'joined_xml': joined, 'corrected_c_xml': corrected, 'worker_xml': worker_xml},
         'actual_scope': witness(ROOT / 'docs/CONFIGURED_API_CALLER_ACTUAL_SCOPE_2026-10-22_001.md'),
         'operator_script': witness(Path(__file__).resolve())})
    from gene_annotation_episode import scientific_checkpoint_fork as custody
    assert Path(custody.__file__).resolve() == CODE / 'gene_annotation_episode/scientific_checkpoint_fork.py'
    arguments['initial_known_record_refs'] = tuple(selected)
    try:
        result = custody.prepare_scientific_checkpoint_fork(**arguments)
    except custody.ScientificCheckpointForkError as error:
        save(inputs / 'C_FAILURE001.json', error.as_record())
        raise
    save(inputs / 'C_RESULT001.json', result)
    validate(result, 'result')
    descriptor = result['receipt']
    receipt_path = Path(descriptor['path'])
    actual_receipt = witness(receipt_path)
    assert actual_receipt['sha256'] == descriptor['sha256']
    assert actual_receipt['bytes'] == descriptor['bytes']
    receipt = json.loads(receipt_path.read_text())
    validate(receipt, 'receipt')
    assert receipt['destination_workspace'] == str(RUN / 'workspace')
    assert receipt['source']['run_id'] == OLD_RUN
    assert receipt['source']['implementation_sha256'] == OLD_PIN
    assert receipt['source']['pending']['request_raw_utf8_sha256'] == PENDING
    assert receipt['caller_initial_known_record_refs'] == selected
    assert result['initial_known_record_refs'] == receipt['initial_known_record_refs']
    assert result['initial_known_record_refs'] == sorted(set(selected) | set(result['lineage_source_refs'].values()))
    assert guards == {path: witness(Path(path)) for path in guards}
    assert pin(CODE) == (PIN, 136) and pin(ROOT) == (OLD_PIN, 122)
    save(inputs / 'C_OPERATOR_VERIFICATION001.json', {
         'status': 'actual_custody_published_verified', 'source_database_guards_unchanged': True,
         'old_runtime_counts': counts, 'caller_selected_refs': len(selected),
         'final_inherited_refs': len(result['initial_known_record_refs']),
         'result': witness(inputs / 'C_RESULT001.json'), 'receipt': actual_receipt,
         'execution_implementation_pin': PIN, 'new_runs_prepared': 0,
         'new_episodes_or_observations': 0, 'model_http_native_calls': 0})
    print(json.dumps({'status': result['status'], 'workspace': result['destination_workspace'],
                      'inherited_refs': len(result['initial_known_record_refs']),
                      'original_counts_unchanged': counts,
                      'new_scientific_run_started': False}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
