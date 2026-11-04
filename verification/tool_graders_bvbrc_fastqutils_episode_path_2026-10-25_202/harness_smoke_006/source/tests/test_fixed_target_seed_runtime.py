"""Connected input-custody checks; no model, native job or scientific action.

The source witness is synthetic. Actual Store construction is confined to new
destinations. SQLite/source-byte witnesses are independently captured here;
the preparation helper's own equality booleans are not the assertion oracle.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote

import pytest

from gene_annotation_episode import materials
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.fixed_target_seed import FixedTargetSeedError, prepare_fixed_target_seed
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_fixed_target_seed import make_seed_witness
from test_runtime import FixtureController, ScriptedProvider


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def file_inventory(directory):
    result = {}
    for path in sorted(Path(directory).rglob('*')):
        if path.is_file():
            checksum = hashlib.sha256()
            with path.open('rb') as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    checksum.update(chunk)
            result[str(path.relative_to(directory))] = {'sha256': checksum.hexdigest(), 'size': path.stat().st_size}
    return result


def input_file_inventory(case):
    return {name: {'sha256': hashlib.sha256((Path(case) / name).read_bytes()).hexdigest(),
        'size': (Path(case) / name).stat().st_size} for name in ('case.json', 'target.fna', 'target.faa')}


def assert_source_preserved(before, after):
    """Apply the exact immutable SQLite-boundary amendment independently."""
    main, wal, shm = 'state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm'
    assert before[main] == after[main]
    assert {key: value for key, value in before.items() if key not in {wal, shm}} == {key: value for key, value in after.items() if key not in {wal, shm}}
    changes = []
    if wal in before:
        assert after.get(wal) == before[wal], 'existing WAL content must stay byte-identical'
    elif wal in after:
        assert after[wal] == {'sha256': hashlib.sha256(b'').hexdigest(), 'size': 0}
        changes.append('empty_wal_created')
    if shm in before:
        assert shm in after, 'existing SHM is not removed by preparation'
        if before[shm] != after[shm]:
            changes.append('shm_changed')
    elif shm in after:
        changes.append('shm_created')
    return {'main_database_before': before[main], 'main_database_after': after[main],
        'wal_before': before.get(wal), 'wal_after': after.get(wal),
        'shm_before': before.get(shm), 'shm_after': after.get(shm),
        'observed_changes': changes, 'authoritative_bytes_unchanged': True}


@contextmanager
def readonly(workspace):
    path = Path(workspace).resolve() / 'state.sqlite3'
    connection = sqlite3.connect('file:' + quote(str(path), safe='/') + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    connection.execute('BEGIN')
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def sql_inventory(workspace):
    # Whole-file digests establish unchanged bytes/rows. Fetch only schemas and
    # counts here; historical model/private-context columns are never selected.
    # Exact selected public intake rows are checked by intake_witness below.
    result = {}
    with readonly(workspace) as connection:
        tables = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        for table in tables:
            escaped = table['name'].replace('"', '""')
            count = connection.execute('SELECT count(*) FROM "' + escaped + '"').fetchone()[0]
            result[table['name']] = {'schema': table['sql'], 'count': count}
    return result


def intake_witness(workspace):
    """Follow existing record values from the single original problem.

    This resolver does not import application transfer/closure code, instantiate
    a source Store, interpret unrelated scientific records or read artifact JSON.
    The exact indexed parser rows are independently selected by original keys.
    """
    with readonly(workspace) as connection:
        problem = json.loads(connection.execute('SELECT data FROM problem WHERE singleton=1').fetchone()[0])
        assert len(problem['subject_refs']) == 1

        def resolve(reference):
            for table in ('inputs', 'records', 'material_members'):
                row = connection.execute('SELECT data FROM ' + table + ' WHERE id=?', (reference,)).fetchone()
                if row is not None:
                    return json.loads(row[0])
            row = connection.execute('SELECT * FROM artifacts WHERE id=?', (reference,)).fetchone()
            return None if row is None else {**dict(row), 'record_type': 'artifact'}

        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from strings(child)
            elif isinstance(value, list):
                for child in value:
                    yield from strings(child)

        closure, pending = {}, list(strings(problem))
        while pending:
            reference = pending.pop()
            if reference in closure:
                continue
            record = resolve(reference)
            if record is not None:
                closure[reference] = record
                pending.extend(strings(record))
        parse_keys = {closure[ref]['parse_key'] for ref in problem['initial_parse_refs']}
        available_tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        indexes = {}
        for table in ('material_members', 'material_errors', 'material_annotations', 'material_pack_chunks', 'material_name_counts'):
            rows = []
            if table in available_tables:
                for key in sorted(parse_keys):
                    rows.extend(dict(row) for row in connection.execute('SELECT * FROM ' + table + ' WHERE parse_key=?', (key,)))
            indexes[table] = sorted(rows, key=encoded)
        component_rows = []
        if 'material_component_spans' in available_tables:
            for member in indexes['material_members']:
                component_rows.extend(dict(row) for row in connection.execute('SELECT * FROM material_component_spans WHERE member_ref=?', (member['id'],)))
        indexes['material_component_spans'] = sorted(component_rows, key=encoded)
        root_rows = []
        for reference in sorted(closure):
            root_rows.extend(dict(row) for row in connection.execute('SELECT * FROM record_roots WHERE record_ref=?', (reference,)))
        indexes['record_roots'] = sorted(root_rows, key=encoded)
    artifacts = {}
    for reference, record in closure.items():
        if record['record_type'] == 'artifact':
            path = Path(workspace) / 'artifacts' / record['sha256'][:2] / record['sha256']
            content = path.read_bytes()
            assert len(content) == record['size']
            assert hashlib.sha256(content).hexdigest() == record['sha256']
            artifacts[reference] = content
    return {'problem': problem, 'records': closure, 'indexes': indexes, 'artifact_bytes': artifacts}


def assert_seed_matches(receipt, original, destination):
    assert set(receipt) == {'version', 'source', 'workspace', 'fixed_identity', 'input_files', 'intake_records', 'artifact_manifest', 'initial_known_record_refs', 'verification', 'exclusions'}
    assert receipt['version'] == 'fixed_target_seed_v1'
    assert receipt['workspace'] == str(Path(destination).resolve())
    assert json.loads((Path(destination) / 'fixed-target-seed.json').read_text()) == receipt
    actual = intake_witness(destination)
    assert actual == original
    expected_records = [{'reference': reference, 'record_type': record['record_type'], 'content_sha256': digest(record)} for reference, record in sorted(original['records'].items())]
    assert receipt['intake_records'] == expected_records
    expected_artifacts = [{key: record[key] for key in ('id', 'sha256', 'media_type', 'size')} for reference, record in sorted(original['records'].items()) if record['record_type'] == 'artifact']
    assert receipt['artifact_manifest'] == expected_artifacts
    with Store(destination) as store:
        resolved = {}
        for reference, record in original['records'].items():
            try:
                resolved[reference] = store.get(reference)
            except ContractError as error:
                # An indexed handle is custody even on implementations where
                # its dedicated reader, rather than Store.get, resolves it.
                assert str(error) == 'unknown_reference'
                assert record['record_type'] == 'collection_member'
        assert resolved == {ref: original['records'][ref] for ref in resolved}
    expected_refs = sorted(resolved)
    assert receipt['initial_known_record_refs'] == expected_refs
    assert len(expected_refs) == len(set(expected_refs))
    assert original['problem']['id'] not in expected_refs
    assert receipt['verification']['initial_known_record_ref_count'] == len(expected_refs)
    assert receipt['verification']['initial_known_record_refs_sha256'] == digest(expected_refs)
    for key in ('problem_equal', 'input_equal', 'intake_equal', 'artifact_bytes_equal', 'material_indexes_equal'):
        assert receipt['verification'][key] is True
    assert not any(receipt['verification']['excluded_record_counts'].values())
    assert not any(receipt['verification']['excluded_table_counts'].values())
    with Store(destination) as store:
        assert store.problem() == original['problem']
        assert {ref: store.get(ref) for ref in expected_refs} == resolved
        assert store.db.execute('SELECT count(*) FROM inputs').fetchone()[0] == 1
        types = {row[0] for row in store.db.execute('SELECT DISTINCT record_type FROM records')}
        assert types <= {'source', 'material', 'parse_attempt', 'collection'}
        tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not any(name.startswith(('runtime_', 'native_')) for name in tables)
        for table in ('current_revisions', 'proposals', 'reasoning_commits'):
            assert store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
    return actual


def emit_evidence(name, value):
    directory = os.environ.get('FIXED_TARGET_SEED_VERIFICATION_DIR')
    if directory:
        path = Path(directory) / (name + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def assert_failure(error, *, code, destination, staged):
    record = error.as_record()
    assert record == error.failure
    assert set(record) == {'version', 'code', 'affected_refs', 'staging_workspace'}
    assert record['version'] == 'fixed_target_seed_failure_v1'
    assert record['code'] == code
    assert isinstance(record['affected_refs'], list) and record['affected_refs']
    assert all(isinstance(ref, str) and ref for ref in record['affected_refs'])
    encoded(record)
    if staged:
        stage = Path(record['staging_workspace'])
        assert stage.is_absolute() and stage.is_dir()
        assert stage != Path(destination).resolve()
        assert not Path(destination).exists()
    else:
        assert record['staging_workspace'] is None
    return record


def test_full_intake_equality_preserves_source_and_omits_historical_rows(tmp_path, monkeypatch):
    witness = make_seed_witness(tmp_path / 'source')
    source = witness['source_workspace']
    # Inert synthetic historical identities, not executions or valid findings.
    with sqlite3.connect(source / 'state.sqlite3') as connection:
        connection.execute('CREATE TABLE runtime_runs(id TEXT PRIMARY KEY)')
        connection.execute("INSERT INTO runtime_runs VALUES('old_fixture_run')")
        connection.execute('CREATE TABLE native_fixture_history(id TEXT PRIMARY KEY)')
        connection.execute("INSERT INTO native_fixture_history VALUES('old_fixture_attempt')")
        for kind in ('assessment', 'native_execution'):
            record = {'id': kind + '_unconnected_fixture', 'record_type': kind, 'origin': 'tool'}
            connection.execute('INSERT INTO records VALUES(?,?,?,?)', (record['id'], kind, 'tool', encoded(record).decode()))
    connection.close()
    original = intake_witness(source)
    source_rows = sql_inventory(source)
    source_files = file_inventory(source)
    original_inputs = input_file_inventory(witness['case_directory'])
    original_init = Store.__init__

    def destination_only(self, path):
        assert Path(path).resolve() != source.resolve(), 'source Store construction is forbidden'
        return original_init(self, path)

    monkeypatch.setattr(Store, '__init__', destination_only)
    # New run descendants of the case are permitted; the original case/FASTA
    # paths remain scientific provenance rather than a destination ban.
    destination = witness['case_directory'] / 'runs' / 'new-fixture-run' / 'workspace'
    receipt = prepare_fixed_target_seed(case_directory=witness['case_directory'], source_workspace=source, destination_workspace=destination)
    after_helper_files = file_inventory(source)
    helper_bookkeeping = assert_source_preserved(source_files, after_helper_files)
    assert receipt['verification']['sqlite_reader_bookkeeping'] == helper_bookkeeping
    assert_seed_matches(receipt, original, destination)
    assert sql_inventory(source) == source_rows
    assert input_file_inventory(witness['case_directory']) == original_inputs
    complete_bookkeeping = assert_source_preserved(source_files, file_inventory(source))
    emit_evidence('synthetic-custody', {'receipt': receipt, 'source_before': source_rows, 'source_after': sql_inventory(source), 'source_preservation': complete_bookkeeping, 'input_file_pins': original_inputs, 'helper_reader_bookkeeping': helper_bookkeeping, 'intake_indexes_equal': True, 'unconnected_history_not_imported': True})


@pytest.mark.parametrize('kind', ['context', 'material'])
@pytest.mark.parametrize('damage', ['missing', 'corrupt'])
def test_missing_or_corrupt_required_source_bytes_remain_specific_failures(tmp_path, kind, damage):
    witness = make_seed_witness(tmp_path / 'source')
    source = witness['source_workspace']
    original = intake_witness(source)
    if kind == 'context':
        reference = original['problem']['caller_context_ref']
    else:
        material = original['records'][original['problem']['material_refs'][0]]
        reference = original['records'][material['source_ref']]['artifact_ref']
    artifact = original['records'][reference]
    path = source / 'artifacts' / artifact['sha256'][:2] / artifact['sha256']
    if damage == 'missing':
        path.unlink()
    else:
        path.write_bytes(b'incorrect immutable bytes')
    before_files, before_rows = file_inventory(source), sql_inventory(source)
    destination = tmp_path / 'refused-workspace'
    with pytest.raises(FixedTargetSeedError) as caught:
        prepare_fixed_target_seed(case_directory=witness['case_directory'], source_workspace=source, destination_workspace=destination)
    failure = assert_failure(caught.value, code='artifact_custody_failure', destination=destination, staged=False)
    assert reference in failure['affected_refs']
    assert sql_inventory(source) == before_rows
    preservation = assert_source_preserved(before_files, file_inventory(source))
    assert not destination.exists()
    emit_evidence('failure-' + kind + '-' + damage, {'failure': failure, 'source_preservation': preservation})


def test_parser_identity_drift_retains_failed_stage_without_replacing_target(tmp_path, monkeypatch):
    witness = make_seed_witness(tmp_path / 'source')
    source = witness['source_workspace']
    before_files, before_rows = file_inventory(source), sql_inventory(source)
    monkeypatch.setattr(materials, 'VERSION', materials.VERSION + '.fixture_changed_parser')
    destination = tmp_path / 'unpublished'
    with pytest.raises(FixedTargetSeedError) as caught:
        prepare_fixed_target_seed(case_directory=witness['case_directory'], source_workspace=source, destination_workspace=destination)
    failure = assert_failure(caught.value, code='intake_mismatch', destination=destination, staged=True)
    assert sql_inventory(source) == before_rows
    preservation = assert_source_preserved(before_files, file_inventory(source))
    assert (Path(failure['staging_workspace']) / 'state.sqlite3').is_file()
    emit_evidence('failure-parser-drift', {'failure': failure, 'source_preservation': preservation})


@pytest.mark.parametrize('shape,expected', [('directory', 'destination_exists'), ('file', 'destination_exists'), ('symlink', 'destination_invalid'), ('dangling_symlink', 'destination_invalid'), ('source_descendant', 'destination_overlap'), ('symlink_ancestor', 'destination_invalid')])
def test_existing_symlink_or_overlapping_destination_never_writes_source(tmp_path, shape, expected):
    witness = make_seed_witness(tmp_path / 'source')
    source, case = witness['source_workspace'], witness['case_directory']
    destination = tmp_path / 'destination'
    if shape == 'directory':
        destination.mkdir()
        (destination / 'caller-owned').write_text('retained')
    elif shape == 'file':
        destination.write_text('retained')
    elif shape == 'symlink':
        destination.symlink_to(source, target_is_directory=True)
    elif shape == 'dangling_symlink':
        destination.symlink_to(tmp_path / 'absent')
    elif shape == 'source_descendant':
        destination = source / 'new'
    else:
        link = tmp_path / 'linked-parent'
        link.symlink_to(tmp_path / 'source', target_is_directory=True)
        destination = link / 'new'
    before = file_inventory(tmp_path)
    with pytest.raises(FixedTargetSeedError) as caught:
        prepare_fixed_target_seed(case_directory=case, source_workspace=source, destination_workspace=destination)
    failure = assert_failure(caught.value, code=expected, destination=destination, staged=False)
    assert file_inventory(tmp_path) == before
    emit_evidence('failure-destination-' + shape, failure)


def test_initial_seed_receipts_exist_before_first_projection_without_actions(tmp_path):
    witness = make_seed_witness(tmp_path / 'source')
    destination = tmp_path / 'new-workspace'
    receipt = prepare_fixed_target_seed(case_directory=witness['case_directory'], source_workspace=witness['source_workspace'], destination_workspace=destination)
    sealed_refs = receipt['initial_known_record_refs']
    projections, controllers = [], []

    class RecordingProgress(ScientificFindingProgress):
        def __call__(self, store, scope, **kwargs):
            rows = store.db.execute('SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts ORDER BY record_ref').fetchall()
            expected = [ref for ref in sealed_refs if store.get(ref)['record_type'] != 'collection_member']
            assert [row['record_ref'] for row in rows] == expected
            assert all(row['receipt_kind'] == 'initial' and row['source_index'] is None for row in rows)
            assert list(kwargs['known_assessment_refs']) == []
            result = super().__call__(store, scope, known_assessment_refs=[])
            projections.append(result)
            return result

    def controller(path, initial):
        value = FixtureController(str(path), initial, 1)
        controllers.append(value)
        return value

    with Store(destination) as store:
        scorer = RecordingProgress(FindingProgressPolicy(7))  # Explicit fixture units only.
        provider = ScriptedProvider([])
        workflow = Workflow(store, ToolRegistry(store), provider, tmp_path / 'fixture-run', 'fixed-seed-fixture', controller, scorer, initial_known_record_refs=sealed_refs, episode_record_receipts=True, episode_binding_factories=())
        root = workflow.build('annotation', 'root', 'Check the supplied fixed target baseline', {'subject_refs': [receipt['fixed_identity']['target_ref']]})
        assert projections and projections[0]['credit'] == 0
        assert workflow.journal.row('runtime_episodes', root.source.episode_id)['initial_credit'] == 0
        assert workflow.source_credit_view(root.source)['credit'] == 0
        assert workflow.source_credit_view(root.source)['credit'] == 0
        assert all(value['retained_finding_count'] == 0 for value in projections)
        assert not controllers and not provider.contexts
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls', 'runtime_completion_slots'):
            assert store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
        assert receipt['verification']['initial_known_record_refs_sha256'] == digest(sealed_refs)
        evidence = {'seed_baseline_count': len(sealed_refs), 'seed_baseline_sha256': digest(sealed_refs), 'first_projection_after_initial_receipts': True, 'projection_credits': [value['credit'] for value in projections], 'completed_actions': 0, 'controller_observations': 0, 'model_calls': 0, 'native_jobs': 0}
    emit_evidence('runtime-baseline-order', evidence)
