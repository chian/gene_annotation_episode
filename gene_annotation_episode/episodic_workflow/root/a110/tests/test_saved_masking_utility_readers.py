"""Read-only selected boundaries; controlled masking custody, authentic utility bytes.

No native operation or excluded execute/prepare/publish method is invoked.
Each case retains snapshots and its actual failure under pytest's run-local tmp_path.
"""
from copy import deepcopy
from contextlib import closing, contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sqlite3
from types import MethodType, SimpleNamespace
import traceback

import pytest

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a110.'
FIXTURE = Path(__file__).parent / 'fixtures/masking_utility_saved_readers'
ASSETS_SHA = '4e63f6256a12a27737390e1f0d348f60cbc6e49c6904891e053f66a7af9ecb70'


def module(name):
    return importlib.import_module(PREFIX + name)


def historical(name):
    return module('library.received_execution_information.historical_' + name)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    assert not any(p.is_symlink() for p in (root, *root.parents))
    result = {}
    for path in root.rglob('*'):
        assert not path.is_symlink()
        if path.is_file():
            result[str(path.relative_to(root))] = sha(path.read_bytes())
        else:
            assert path.is_dir(), 'special_fixture_node'
    return result


def assets():
    raw = (FIXTURE / 'ASSETS.json').read_bytes()
    assert sha(raw) == ASSETS_SHA
    manifest = json.loads(raw)
    expected = {'ASSETS.json': ASSETS_SHA}
    for family in ('masking', 'utility'):
        root = Path(manifest[family + '_root'])
        for row in manifest[family]:
            expected[family + '/' + str(Path(row['path']).relative_to(root))] = row['sha256']
    assert inventory(FIXTURE) == expected
    return expected


def snapshot(db):
    """All raw tables/schema, with sqlite3.Row bypassed and BLOB bytes preserved."""
    cursor = db.cursor()
    cursor.row_factory = None
    schema = cursor.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
    def cell(value):
        if isinstance(value, bytes):
            return {'blob_hex': value.hex()}
        return value
    tables = {}
    for kind, name, _, _ in schema:
        if kind != 'table':
            continue
        quoted = '"' + name.replace('"', '""') + '"'
        rows = [[cell(value) for value in row] for row in cursor.execute('SELECT * FROM ' + quoted).fetchall()]
        tables[name] = sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, allow_nan=False))
    return {'schema': schema, 'tables': tables}


@pytest.fixture
def recorded(tmp_path):
    report = {'version': 'a110_saved_reader_boundary_observation_v1', 'claims': {
        'masking': 'controlled_host_custody_around_authentic_native_bytes',
        'utility': 'authentic_failed_native_capture_pure_validation_only',
        'full_host_restoration': False, 'native_execution': False}, 'failure': None}
    try:
        assets()
        yield tmp_path, report
    except BaseException as error:
        report['fixture_failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
                                     'message': str(error), 'traceback': traceback.format_exc()}
        raise
    finally:
        # pytest outcome is authoritative; this JSON is diagnostic evidence only.
        (tmp_path / 'reader-observation.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')


def observe(report, operation):
    try:
        result = operation()
        report['operation_returned'] = True
        return result
    except BaseException as error:
        report['failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
                             'message': str(error), 'traceback': traceback.format_exc()}
        raise


@contextmanager
def opened_store(path, report):
    store = module('state').Store(path)
    try:
        yield store
    finally:
        try:
            store.close()
            report['store_closed'] = True
        except BaseException as error:
            report['close_failure'] = {'type': type(error).__qualname__, 'message': str(error)}
            raise


def masking_case(root, report):
    copied = root / 'masking'
    shutil.copytree(FIXTURE / 'masking', copied)
    database = copied / 'store/state.sqlite3'
    report['database_before_constructor_sha256'] = sha(database.read_bytes())
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        report['before_constructor'] = snapshot(db)
    store = module('state').Store(copied / 'store')
    try:
        report['after_constructor'] = snapshot(store.db)
        assert all(report['after_constructor']['tables'].get(name) == rows
                   for name, rows in report['before_constructor']['tables'].items()), 'constructor_changed_original_rows'
        assert all(row in report['after_constructor']['schema'] for row in report['before_constructor']['schema']), 'constructor_changed_original_schema'
        receipts = list((copied / 'run/execution-results').glob('*/native-blast-masking-actions/*/receipt.json'))
        path, = receipts
        body = json.loads(path.read_bytes())
        def read_target(reference, scope):
            assert reference == body['assignment']['handoff_ref']
            store.validate_scope(body['target']['scope'], parent_scope=module('communication').plain(scope))
            return deepcopy(body['target'])
        owner = SimpleNamespace(store=store, run_id=body['run_id'], directory=copied / 'run',
                                job_progress_provider=SimpleNamespace(targets=SimpleNamespace(read_target=read_target)))
        cls = historical('receiving_owner').HistoricalReceivedExecutionOwner
        owner._selected_result_action = MethodType(cls._selected_result_action, owner)
        reader = historical('native_blast_masking_results').NativeBLASTMaskingResults(owner)
        return store, reader, body, path.parent
    except BaseException as error:
        report['setup_failure'] = {'type': type(error).__qualname__, 'message': str(error), 'traceback': traceback.format_exc()}
        try:
            store.close()
            report['store_closed'] = True
        except BaseException as close_error:
            report['close_failure'] = {'type': type(close_error).__qualname__, 'message': str(close_error)}
        raise


@pytest.mark.parametrize('case', ['saved', 'missing_capture', 'race_after_gate', 'corrupt_artifact'])
def test_controlled_masking_saved_read_boundary(recorded, monkeypatch, case):
    root, report = recorded
    report['case'] = case
    def operation():
        store, reader, body, directory = masking_case(root, report)
        try:
            baseline = snapshot(store.db)
            run_before = inventory(reader.owner.directory)
            artifacts_before = inventory(store.path / 'artifacts')
            report['run_sha256_before'] = run_before
            report['artifact_sha256_before'] = artifacts_before
            report['artifact_sha256_before_reader'] = artifacts_before
            acquisition = historical('native_blast_masking_acquisition')
            def forbidden(*args, **kwargs):
                raise AssertionError('saved read entered original acquisition qualification')
            monkeypatch.setattr(acquisition, 'local_blast_masking_plan', forbidden)
            capture = directory / 'capture/capture.json'
            if case == 'missing_capture':
                capture.unlink()
            elif case == 'corrupt_artifact':
                digest = body['capture']['bundle_artifact_ref'].removeprefix('artifact_')
                (store.path / 'artifacts' / digest[:2] / digest).write_bytes(b'controlled corrupt retained bytes')
            elif case == 'race_after_gate':
                original_is_file = Path.is_file
                raced = []
                def remove_after_gate(path):
                    value = original_is_file(path)
                    if path == capture and value and not raced:
                        raced.append(str(path)); path.unlink()
                    return value
                monkeypatch.setattr(Path, 'is_file', remove_after_gate)
                report['controlled_race_schedule'] = 'remove copied capture immediately after successful is_file'
            def read():
                return reader.read_result(body['source_ref'], body['scope'])
            report['before_reader'] = snapshot(store.db)
            artifact_reader_before = inventory(store.path / 'artifacts')
            report['artifact_sha256_before_reader'] = artifact_reader_before
            if case == 'saved':
                assert read() == body
                assert [row['value']['value'] for row in body['quantities'] if row['quantity'] == 'masked_positions'] == [80, 0, 72]
                assert inventory(reader.owner.directory) == run_before
                assert inventory(store.path / 'artifacts') == artifacts_before
            elif case == 'missing_capture':
                with pytest.raises(ValueError, match='capture_receipt_missing'):
                    read()
            elif case == 'corrupt_artifact':
                with pytest.raises(ValueError, match='capture_artifact_measurement_conflict'):
                    read()
            else:
                with pytest.raises(AssertionError, match='saved read entered original acquisition qualification'):
                    read()
                assert raced == [str(capture)]
                report['original_fallback_boundary_reached'] = True
                report['fallback_qualification_or_acquisition_success_claimed'] = False
            assert snapshot(store.db) == baseline
            assert inventory(store.path / 'artifacts') == artifact_reader_before
            expected_run = dict(run_before)
            if case in {'missing_capture', 'race_after_gate'}:
                del expected_run[str(capture.relative_to(reader.owner.directory))]
            assert inventory(reader.owner.directory) == expected_run
        finally:
            try:
                report['after_reader'] = snapshot(store.db)
                report['run_sha256_after'] = inventory(reader.owner.directory)
                report['artifact_sha256_after'] = inventory(store.path / 'artifacts')
            finally:
                try:
                    store.close()
                    report['store_closed'] = True
                except BaseException as error:
                    report['close_failure'] = {'type': type(error).__qualname__, 'message': str(error)}
                    raise
    observe(report, operation)


@pytest.mark.parametrize('case', ['saved', 'corrupt_artifact', 'relabel_output'])
def test_authentic_utility_failed_capture_pure_read_boundary(recorded, monkeypatch, case):
    root, report = recorded
    report['case'] = case
    def operation():
        records = {name: json.loads((FIXTURE / 'utility' / (name + '.json')).read_bytes())
                   for name in ('capture', 'prepared', 'publication')}
        capture, prepared, output = (records[key] for key in ('capture', 'prepared', 'publication'))
        acquisition = historical('native_blast_utility_acquisition')
        publication = historical('native_blast_utility_result_publication')
        with opened_store(root / 'utility-store', report) as store:
            for path in sorted((FIXTURE / 'utility/artifacts').iterdir()):
                assert store.artifact(path.read_bytes()) == 'artifact_' + path.name
            assert store.put('source', acquisition._source_payload(capture), origin='tool')['id'] == capture['source_ref']
            baseline = snapshot(store.db)
            artifacts_before = inventory(store.path / 'artifacts')
            report['before_reader'] = baseline
            report['artifact_sha256_before'] = artifacts_before
            report['artifact_sha256_before_reader'] = artifacts_before
            def forbidden(*args, **kwargs):
                raise AssertionError('pure saved validation entered original acquisition')
            monkeypatch.setattr(acquisition, '_capture_file', forbidden)
            monkeypatch.setattr(acquisition, 'local_blast_utility_plan', forbidden)
            try:
                if case == 'corrupt_artifact':
                    digest = capture['bundle_artifact_ref'].removeprefix('artifact_')
                    (store.path / 'artifacts' / digest[:2] / digest).write_bytes(b'controlled corrupt retained bytes')
                    artifacts_before = inventory(store.path / 'artifacts')
                    report['artifact_sha256_before_reader'] = artifacts_before
                    with pytest.raises(ValueError, match='capture_artifact_measurement_conflict'):
                        acquisition._validate_saved(store, capture)
                elif case == 'relabel_output':
                    capture['artifacts'][-1]['original_path'] = '/unselected/output'
                    with pytest.raises(ValueError, match='capture_artifact_association_conflict'):
                        acquisition._validate_saved(store, capture)
                else:
                    assert 'output_completeness_basis' not in capture['original_bundle']
                    assert {row['completeness'] for row in capture['original_bundle']['artifacts']} == {'partial'}
                    assert acquisition._validate_saved(store, capture) == capture
                    assert publication.validate_prepared_utility_result(store, prepared) == prepared
                    assert publication.validate_utility_publication(store, source_ref=capture['source_ref'], prepared=prepared,
                        selector=output['selector'], publication=output) == output
                    assert json.loads(store.get_artifact(prepared['result_artifact_ref']))['original_outcome']['returncode'] == 1
                    assert inventory(store.path / 'artifacts') == artifacts_before
                assert snapshot(store.db) == baseline
                assert inventory(store.path / 'artifacts') == artifacts_before
            finally:
                report['after_reader'] = snapshot(store.db)
                report['artifact_sha256_after'] = inventory(store.path / 'artifacts')
    observe(report, operation)
