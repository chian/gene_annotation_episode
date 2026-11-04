"""Finish the retained NMF446 permission checks without replay or new work.

The original446 failure and its false flags remain immutable evidence. This
separately selected engineering verification uses its actual completed frames.
"""
import builtins
from copy import deepcopy
import hashlib
from importlib import import_module
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import stat

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest


F = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')
FINISH_ENV = 'HMMER_NATIVE_ORACLE_NMF_RETAINED_FINISH'
FAILED_PREFIX_SHA256 = '19f759d15f11875245c2ece6863e2fa31199bb6915f4827f1d7f76d3db2176a0'
FAILED_DATABASE_SHA256 = '78da3b5268596d6e051977aeca91672c156573e91cea518c50f4ec3c5a6053e2'
EMPTY_BACKEND_SHA256 = 'c748952c3a9c81d34d9549fe0f495fd451b558cb0167e6d46761f91c9e47297d'
CONTROL_NAMES = ('intent.json', 'receipt.json', 'handoff.json', 'observation.json',
    'native-snapshot.json', 'capture.json', 'worker-plan.json', 'worker-capture.json', 'worker-execution.json')


def _pin(path):
    path = Path(path)
    assert stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink()
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024): value.update(chunk)
    return dict(sha256=value.hexdigest(), size_bytes=path.stat().st_size, mode=stat.S_IMODE(path.stat().st_mode))


def _bundle(directory):
    return [dict(name=name, sha256=value['sha256'], size_bytes=value['size_bytes'])
        for name in ('state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm')
        if (path := directory / name).is_file() for value in [_pin(path)]]


def _files(directory):
    return {str(path.relative_to(directory)): _pin(path)
        for path in sorted(directory.rglob('*')) if path.is_file()}


def _rows(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    assert all(name.replace('_', '').isalnum() for name in names)
    return {name: sorted((dict(row) for row in store.db.execute('SELECT * FROM ' + name)), key=canonical)
        for name in names}


def _schema(store):
    return [dict(row) for row in store.db.execute(
        'SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')]


def _empty_backend(directory):
    """Inspect only the owned copy of the actual empty446 backend journal."""
    path = directory / 'executions.sqlite'
    db = sqlite3.connect('file:' + str(path.resolve(strict=True)) + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    try:
        schema = [dict(row) for row in db.execute(
            'SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')]
        tables = {row['name'] for row in schema if row['type'] == 'table'}
        assert tables == {'commissions', 'returns', 'events', 'sqlite_sequence', 'native_targets', 'native_publications'}
        rows = {name: [dict(row) for row in db.execute('SELECT * FROM ' + name)] for name in sorted(tables)}
        assert all(value == [] for value in rows.values())
        return dict(schema=schema, rows=rows)
    finally:
        db.close()


def _frame_origins(owner, science, sheet):
    """Derive contribution order from actual admitted typed-return frames."""
    records, origins, frames = owner.native_expression_nmf_returns, [], []
    attempts = records.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
        'AND parent_episode_id=? AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index',
        (science.run_id, science.episode_id)).fetchall()
    for attempt in attempts:
        child, form, schema = records._attempt(science, attempt['decision_index'])
        values = records._values(form, schema)
        if not any(canonical(row) == canonical(sheet) for row in values.get(F.SAVED_SOURCE, [])):
            continue
        assert child.role == 'results' and owner.native_expression_nmf_results.applies(child)
        outcomes = []
        for row in records.db.execute('SELECT decision_index,action,result FROM runtime_actions '
                'WHERE run_id=? AND episode_id=? ORDER BY decision_index', (science.run_id, child.episode_id)):
            action = json.loads(row['action'])
            if action != dict(kind='tool', tool='execution.results.collect', arguments={}) or row['result'] is None:
                continue
            outcome = json.loads(row['result'])
            if outcome.get('status') != 'completed': continue
            receipt = outcome['result']
            if any(canonical(value) == canonical(sheet) for value in receipt['facts'][F.SAVED_SOURCE]):
                assert canonical(receipt['qualified_files']['sheet']) == canonical(sheet)
                assert receipt['intent']['episode_id'] == child.episode_id
                assert receipt['intent']['operation_key'] == f'{science.run_id}:{child.episode_id}:{row["decision_index"]}'
                outcomes.append(receipt)
        assert len(outcomes) == 1
        receipt, = outcomes
        if child.episode_id not in origins: origins.append(child.episode_id)
        frames.append(dict(decision_index=attempt['decision_index'], delivery_ref=attempt['delivery_ref'],
            child_episode_id=child.episode_id, mode=receipt['intent']['assignment']['selector']['mode'],
            operation_key=receipt['intent']['operation_key'],
            form_sha256=digest(form), schema_sha256=digest(schema)))
    return tuple(origins), frames


def verify_retained_nmf_sheet_permissions(*, flow, owner, science, parent, result_contexts,
        configuration, saved, monkeypatch, forbidden):
    """Check current contribution origins separately from the saved-input cutoff."""
    sheet, records = saved['sheet_file'], owner.native_expression_nmf_returns
    expected, frames = _frame_origins(owner, science, sheet)
    native_frames = list(dict.fromkeys(frame['child_episode_id'] for frame in frames
        if frame['mode'] == 'native_result'))
    saved_frames = list(dict.fromkeys(frame['child_episode_id'] for frame in frames
        if frame['mode'] == 'saved_sheet_recalculation'))
    assert native_frames == saved['origins'] and len(native_frames) == len(saved_frames) == 1
    assert expected == tuple([*native_frames, *saved_frames])
    current = records.authenticate_received_saved_sheet(science, sheet)
    assert current == expected
    frozen_origins = []
    for context in result_contexts:
        if plain(context.assignment)['selector']['mode'] != 'saved_sheet_recalculation': continue
        assert context.episode_id in saved_frames
        actual = records.authenticate_received_saved_sheet(context, sheet)
        assert actual == tuple(saved['origins'])
        action = flow.journal.row('runtime_actions', context.episode_id, 0)
        receipt = json.loads(action['result'])['result']
        expected_originals = [dict(episode_id=episode_id, operation_key=f'{context.run_id}:{episode_id}:0')
            for episode_id in saved['origins']]
        assert receipt['original_origins'] == expected_originals
        manifest = plain(context.request)['message']['knowledge_inheritance']
        indexes = [row['decision_index'] for row in manifest['received_report_prefix']['attempts']]
        assert indexes == [0, 1, 2]
        assert all(frame['decision_index'] < 3 for frame in frames if frame['child_episode_id'] in actual)
        frozen_origins.append(dict(episode_id=context.episode_id, origins=list(actual),
            input_prefix_decision_indices=indexes, original_origins=deepcopy(receipt['original_origins'])))
    assert len(frozen_origins) == 1
    science_known, parent_known = (set(flow.receipts.known(context.episode_id)) for context in (science, parent))
    assert set(configuration['initial_refs']) <= parent_known
    assert sheet['artifact_ref'] in science_known and sheet['artifact_ref'] not in parent_known
    assert owner.resolve_received_reference(science, sheet['artifact_ref'], 'artifact') is True
    assert owner.resolve_received_reference(parent, sheet['artifact_ref'], 'artifact') is False
    with pytest.raises(ValueError, match='saved_sheet_not_received'):
        records.authenticate_received_saved_sheet(parent, sheet)
    # Baseline caller Files remain admitted. Their already removed bytes are
    # not reopened to turn a metadata permission check into a new data read.
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    admission = EpisodeReturnRecords(flow.store, parent.run_id, failure_prefix='nmf_finish_')
    for reference in configuration['initial_refs']:
        assert owner.resolve_received_reference(parent, reference, 'artifact') is not False
        assert admission.file_admission_before(parent, reference, 'artifact', reference, 0)['baseline'] is True
    protected = {file['artifact_ref'] for role, file in saved['original_receipt']['qualified_files'].items()
        if file is not None and role != 'sheet'} - set(configuration['initial_refs'])
    assert protected.isdisjoint(parent_known | science_known)
    with monkeypatch.context() as no_private:
        no_private.setattr(flow.store, 'get_artifact', forbidden)
        for reference in sorted(protected | {sheet['artifact_ref']}):
            result, path = owner.services.read_received_molecular_input(parent, reference, 'artifact', file_format='binary')
            assert result['input'] is None and path is None and result['failure'] is not None
    return dict(permission_qualification=(
        'Current science sees both actual contributing Results; saved Results sees its original frozen native-only input prefix. '
        'The saved sheet is admitted to science only; original caller File grants remain intact. No File body is read.'),
        parent_initial_refs=configuration['initial_refs'], science_saved_sheet=sheet,
        unreceived_derived_files=sorted(protected), origin_frames=frames,
        science_current_origins=list(current), saved_context_origins=frozen_origins)


def test_retained_completed_nmf_replay_finishes_origin_permissions_without_replay(tmp_path, monkeypatch):
    selected = os.environ.get(FINISH_ENV + '_PROOF')
    if not selected: pytest.skip('requires explicitly pinned preserved446 completed replay prefix')
    output = tmp_path / 'NMF_RETAINED_PERMISSION_FINISH.json'
    audit = dict(version='expression_nmf_retained_permission_finish_v1', phase='selected', passed=False,
        qualification='Finish-only metadata verification after preserved446 late assertion; no root replay or new scientific work.',
        forbidden_work_attempts=[])
    F.write(output, audit)
    store = None
    def forbidden(*args, **kwargs):
        audit['forbidden_work_attempts'].append(dict(argument_types=[type(value).__name__ for value in args]))
        raise AssertionError('NMF finish attempted replay, decision, grant, publication, File body or scientific work')
    try:
        proof_path = Path(selected).resolve(strict=True)
        assert _pin(proof_path)['sha256'] == os.environ[FINISH_ENV + '_PROOF_SHA256'] == FAILED_PREFIX_SHA256
        proof = json.loads(proof_path.read_bytes())
        assert proof['version'] == 'expression_nmf_retained_closed_replay_v1' and proof['passed'] is False
        assert proof['phase'] == 'selected' and proof['failure']['exception_type'] == 'AssertionError'
        assert all(proof[key] is True for key in ('original_authenticated', 'owned_database_cloned',
            'closed_replay_verified', 'literal_results_verified', 'typed_parent_delivery_verified'))
        assert proof['saved_sheet_permissions_verified'] is False and proof['forbidden_work_attempts'] == []
        source_db_path = Path(proof['owned_database']['path']).resolve(strict=True)
        source_owned, source_case = source_db_path.parent.parent, source_db_path.parent.parent.parent
        assert source_db_path == source_owned / 'state/state.sqlite3'
        assert _pin(source_case / 'NMF_RETAINED_REPLAY.json')['sha256'] == FAILED_PREFIX_SHA256
        bundle = _bundle(source_owned / 'state')
        assert bundle == [dict(name='state.sqlite3', sha256=FAILED_DATABASE_SHA256, size_bytes=43622400)]
        assert digest(bundle) == os.environ[FINISH_ENV + '_SQLITE_PINS_SHA256']
        assert proof['owned_database']['sha256'] == FAILED_DATABASE_SHA256
        controls = proof['controls']
        for value in controls.values():
            assert _pin(value['path'])['sha256'] == value['sha256']
            assert _pin(value['path'])['size_bytes'] == value['size_bytes']
        original = Path(controls['CASE.json']['path']).resolve(strict=True).parent
        assert _bundle(original / 'state') == proof['original_sqlite_bundle']
        saved = json.loads(Path(controls['SAVED_CHECK.json']['path']).read_bytes())
        configuration = json.loads(Path(controls['fixture-configuration.json']['path']).read_bytes())
        original_case = json.loads(Path(controls['CASE.json']['path']).read_bytes())
        assert configuration['goal'] == F.TASK == proof['archive']['request']['goal']['objective']
        assert proof['archive'] == original_case['archive'] and proof['final_result'] == dict(credit=0, pending_handles=[])
        source_files, original_files = _files(source_case), _files(original)
        staging, owned = tmp_path / 'sqlite-staging', tmp_path / 'owned-finish'
        staging.mkdir(); (owned / 'state').mkdir(parents=True)
        for row in bundle: shutil.copy2(source_owned / 'state' / row['name'], staging / row['name'])
        assert _bundle(staging) == bundle
        staged_db = sqlite3.connect(staging / 'state.sqlite3')
        destination = sqlite3.connect(owned / 'state/state.sqlite3')
        try:
            staged_db.execute('PRAGMA query_only=ON'); staged_db.backup(destination)
        finally:
            destination.close(); staged_db.close()
        for name in ('archive', 'scientific-process-library', 'scientific-tool-library', 'tool-knowledge', 'launch-instructions'):
            path = source_owned / 'run' / name
            if path.is_dir(): shutil.copytree(path, owned / 'run' / name)
        source_backend, backend = source_owned / 'run/episode-execution', owned / 'run/episode-execution'
        assert {path.name for path in source_backend.iterdir()} == {'executions.sqlite', 'archives'}
        assert list((source_backend / 'archives').iterdir()) == []
        assert _pin(source_backend / 'executions.sqlite') == dict(
            sha256=EMPTY_BACKEND_SHA256, size_bytes=65536, mode=0o644)
        shutil.copytree(source_backend, backend)
        assert _pin(backend / 'executions.sqlite') == _pin(source_backend / 'executions.sqlite')
        before_backend = _empty_backend(backend)
        from gene_annotation_episode import acquisition, native_lifecycle
        from gene_annotation_episode import expression_nmf_calculations as calculations
        from gene_annotation_episode import expression_nmf_result_views as projections
        from gene_annotation_episode import expression_nmf_result_worker as worker
        from gene_annotation_episode import expression_nmf_sheet as sheets
        from gene_annotation_episode import native_expression_nmf_driver as driver
        from gene_annotation_episode import native_expression_nmf_preparation as preparation
        from gene_annotation_episode import native_expression_nmf_results as native_results
        from gene_annotation_episode.episode_receipts import EpisodeReceipts
        from gene_annotation_episode.execution_progress import ExecutionTargetReader
        from gene_annotation_episode.runtime import Workflow
        from gene_annotation_episode.state import Store
        from gene_annotation_episode.tools import ToolRegistry
        from method_loop.archive import ArchivedRecord
        store = Store(owned / 'state')
        for row in store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? "
                "AND json_extract(action,'$.tool')='execution.results.collect' ORDER BY rowid", (F.RUN_ID,)):
            receipt = json.loads(row['result'])['result']; intent = receipt['intent']
            relative = Path('execution-results') / digest([F.RUN_ID, intent['episode_id']]) / \
                'native-expression-nmf-actions' / digest(intent['operation_key'])
            source_action, target_action = source_owned / 'run' / relative, owned / 'run' / relative
            target_action.mkdir(parents=True)
            for name in CONTROL_NAMES:
                if (source_action / name).is_file(): shutil.copy2(source_action / name, target_action / name)
            shutil.copy2(source_action.parent.parent / 'assignment.json', target_action.parent.parent / 'assignment.json')
        before, before_schema = _rows(store), _schema(store)
        assert {name: len(rows) for name, rows in before.items()} == proof['actual_table_counts']
        assert not any((store.path / 'artifacts').rglob('*'))
        before_files = _files(owned / 'run')
        path_open, builtin_open, io_open, os_open = Path.open, builtins.open, io.open, os.open
        def check_path(value, *, dir_fd=None):
            if isinstance(value, int): return
            path = Path(os.fsdecode(value))
            if not path.is_absolute():
                path = (Path(os.readlink('/proc/self/fd/' + str(dir_fd))) if dir_fd is not None else Path.cwd()) / path
            path = Path(os.path.normpath(path))
            if (path.is_relative_to(original) or path.is_relative_to(source_case)
                    or path.is_relative_to(store.path / 'artifacts')): forbidden(str(path))
        def checked_path(path, *args, **kwargs): check_path(path); return path_open(path, *args, **kwargs)
        def checked_builtin(path, *args, **kwargs): check_path(path); return builtin_open(path, *args, **kwargs)
        def checked_io(path, *args, **kwargs): check_path(path); return io_open(path, *args, **kwargs)
        def checked_os(path, flags, *args, **kwargs):
            check_path(path, dir_fd=kwargs.get('dir_fd')); return os_open(path, flags, *args, **kwargs)
        class NoDecisions:
            async def complete(self, *args, **kwargs): return forbidden(*args, **kwargs)
            async def release(self, episode_id): pass
        with monkeypatch.context() as guard:
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel'):
                guard.setattr(native_lifecycle, name, forbidden)
            for module, names in ((driver, ('run_expression_nmf', 'retain_expression_nmf_artifacts', 'execute_expression_nmf_plan')),
                    (calculations, ('calculate_nmf_sheet', 'reconstruct_nmf', 'residual_measurements', 'component_measurements')),
                    (sheets, ('load_expression_nmf_artifacts', 'populate_nmf_sheet')),
                    (projections, ('project_nmf_result',)),
                    (worker, ('execute_expression_nmf_worker', 'load_expression_nmf_artifacts', 'populate_nmf_sheet',
                        'calculate_nmf_sheet', 'project_nmf_result')),
                    (preparation, ('prepare_expression_nmf_result_worker',)),
                    (native_results, ('capture_expression_nmf_native_files', 'prepare_expression_nmf_result_worker'))):
                for name in names: guard.setattr(module, name, forbidden)
            guard.setattr(native_results.NativeExpressionNMFResults, '_worker', forbidden)
            guard.setattr(ExecutionTargetReader, 'observe_target', forbidden)
            guard.setattr(acquisition.PublicClients, '_http', forbidden)
            guard.setattr(socket, 'create_connection', forbidden)
            guard.setattr(socket.socket, 'connect', forbidden)
            guard.setattr(socket.socket, 'connect_ex', forbidden)
            guard.setattr(ToolRegistry, '_source', forbidden)
            guard.setattr(ToolRegistry, '_put', forbidden)
            guard.setattr(ToolRegistry, '_save', forbidden)
            guard.setattr(ToolRegistry, '_execute_operation_async', forbidden)
            guard.setattr(ToolRegistry, '_sequence_worker_async', forbidden)
            guard.setattr(Store, 'artifact', forbidden)
            guard.setattr(Store, 'get_artifact', forbidden)
            guard.setattr(EpisodeReceipts, 'receive', forbidden)
            guard.setattr(Workflow, 'build', forbidden)
            guard.setattr(F, 'run_root', forbidden)
            guard.setattr(Path, 'open', checked_path)
            guard.setattr(builtins, 'open', checked_builtin)
            guard.setattr(io, 'open', checked_io)
            guard.setattr(os, 'open', checked_os)
            flow, _ = F.assemble(store, owned, NoDecisions(), configuration)
            assert _rows(store) == before and _schema(store) == before_schema
            assert _empty_backend(backend) == before_backend
            assert _files(owned / 'run') == before_files
            store.db.execute('PRAGMA query_only=ON')
            owner = flow.episode_bindings.for_role('results')
            contexts = {record['episode_id']: owner.native_expression_nmf_returns.context(record['episode_id'])
                for record in F.walk(proof['archive'])}
            parent = contexts[proof['archive']['episode_id']]
            science, = [context for context in contexts.values() if context.role == 'scientific_process']
            result_contexts = [context for context in contexts.values() if context.role == 'results']
            row = flow.journal.row('runtime_episodes', parent.episode_id)
            assert row['state'] == 'yielded' and json.loads(row['completion']) == dict(actions=1, ended_by='yield_stop')
            archive = json.loads(row['archive'])
            assert ArchivedRecord(owned / 'run/archive' / archive['file'], archive['sha256'], archive['index_sha256']).load() == proof['archive']
            permissions = verify_retained_nmf_sheet_permissions(flow=flow, owner=owner, science=science, parent=parent,
                result_contexts=result_contexts, configuration=configuration, saved=saved,
                monkeypatch=monkeypatch, forbidden=forbidden)
            assert _rows(store) == before and _schema(store) == before_schema
            assert _files(owned / 'run') == before_files
            assert _empty_backend(backend) == before_backend
        assert _files(source_case) == source_files and _files(original) == original_files
        assert audit['forbidden_work_attempts'] == []
        audit.update(phase='verified', passed=True, source_prefix=dict(path=str(proof_path), sha256=FAILED_PREFIX_SHA256),
            preserved_failed_flags={key: proof[key] for key in ('passed', 'saved_sheet_permissions_verified',
                'histories_unchanged', 'originals_unchanged')}, source_sqlite_bundle=bundle,
            table_counts={name: len(rows) for name, rows in before.items()},
            all_rows_unchanged=True, owned_control_files_and_modes_unchanged=True,
            copied_backend_journal=dict(sha256=EMPTY_BACKEND_SHA256, size_bytes=65536,
                table_counts={name: len(rows) for name, rows in before_backend['rows'].items()},
                schema_and_rows_unchanged=True),
            original446_files_and_modes_unchanged=True, original490_files_and_modes_unchanged=True,
            new_decisions=0, root_replays=0, new_native_or_workers=0, new_publications_or_grants=0, **permissions)
    except BaseException as error:
        audit['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            store.close()
            audit['owned_database'] = _pin(store.path / 'state.sqlite3')
        F.write(output, audit)
