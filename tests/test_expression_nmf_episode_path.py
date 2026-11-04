"""Actual selected NMF Workflow with supplied synthetic measurements.

Run only under490/run_checks.py. This verifies production execution and return
boundaries with scripted decisions; it is not a model or biological claim.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import math
import os
from pathlib import Path
import shutil
import socket
import sqlite3

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')


def deny(*args, **kwargs):
    raise AssertionError('saved calculation or closed replay attempted original native work, acquisition, or network')


@pytest.fixture(scope='module')
def connected_case(tmp_path_factory):
    directory = tmp_path_factory.mktemp('expression-nmf490')
    software = json.loads(Path(os.environ['NMF490_SOFTWARE']).read_text())
    evidence, patch = {}, pytest.MonkeyPatch()

    def before_saved(case):
        original, = F.worker_runs(directory)
        assert original['plan']['mode'] == 'native_result'
        evidence['original_worker'] = original
        evidence['sheet_file'] = deepcopy(case.sheet_file)
        evidence['sheet_bytes'] = case.store.get_artifact(case.sheet_file['artifact_ref'])
        evidence['observations'] = F.rows(case.store, 'runtime_observations')
        evidence['actions'] = [r for r in F.rows(case.store, 'runtime_actions') if r['result'] is not None]
        evidence['origins'] = case.owner.native_expression_nmf_returns.authenticate_received_saved_sheet(
            case.science_context, case.sheet_file)
        evidence['native_plans'] = {str(p): p.read_bytes() for p in case.workspace.rglob('expression-nmf-plan.json')}
        output, = [json.loads(row['result'])['result'] for row in evidence['actions']
            if json.loads(row['result']).get('result', {}).get('version') == 'native_expression_nmf_acquired_result_v1']
        evidence['original_receipt'] = output
        calculations = output['qualified_files']['calculations']
        evidence['calculations'] = json.loads(case.store.get_artifact(calculations['artifact_ref']))
        removed = []

        def remove(path, kind):
            if path.is_file():
                raw = path.read_bytes()
                path.unlink()
                removed.append({'kind': kind, 'path': str(path), 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()})

        def remove_artifact(file, kind):
            if file['artifact_ref'] != case.sheet_file['artifact_ref']:
                remove(case.store.path / 'artifacts' / file['sha256'][:2] / file['sha256'], kind)

        for spec in case.provider.plan['outputs']:
            remove(Path(case.provider.plan['attempt_directory']) / spec['relative_path'], 'native_scientific_copy')
        for row in output['capture']['files']:
            if row['retained'] is not None:
                remove_artifact(row['retained']['file'], 'captured_native_scientific_bytes')
        remove(Path(case.provider.plan['requested_job']['native_expression_nmf']['input']['path']), 'original_caller_matrix')
        for path in (Path(original['directory']) / 'native-inputs').iterdir():
            remove(path, 'original_worker_native_copy')
        for row in original['capture']['outputs']:
            if row['declared']['relative_path'] in {'sheet.json', 'calculations.json', 'projection.json'}:
                remove(Path(original['directory']) / row['declared']['relative_path'], 'original_worker_scientific_copy')
                if row['observed'] is not None:
                    remove_artifact(row['observed'], 'original_worker_retained_scientific_bytes')
        assert removed and all(not Path(row['path']).exists() for row in removed)
        assert len([r for r in removed if r['kind'] == 'native_scientific_copy']) == 5
        assert not Path(case.provider.plan['requested_job']['native_expression_nmf']['input']['path']).exists()
        evidence['removed'], evidence['dispatches'], evidence['lifecycle_accesses'] = removed, [], []
        from gene_annotation_episode import native_lifecycle
        actual_prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.expression_nmf_result_worker']
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan['mode'] == 'saved_sheet_recalculation'
            assert plan['selector']['saved_sheet_file'] == case.sheet_file
            assert 'original_plan' not in plan and 'capture' not in plan
            assert kwargs['policy'].to_dict() == F.POLICY
            evidence['dispatches'].append({'command': list(command), 'plan': deepcopy(plan)})
            return actual_prepare(command, **kwargs)

        patch.setattr(native_lifecycle, 'prepare_job', saved_worker_only)
        for name in ('start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
            original_function = getattr(native_lifecycle, name)

            def saved_lifecycle_only(handle, *args, _name=name, _function=original_function, **kwargs):
                assert str(handle.path) != case.provider.target['execution_id']
                assert handle.path.name == 'worker.handle.json'
                evidence['lifecycle_accesses'].append({'operation': _name, 'handle': str(handle.path)})
                return _function(handle, *args, **kwargs)

            patch.setattr(native_lifecycle, name, saved_lifecycle_only)
        patch.setattr('gene_annotation_episode.native_expression_nmf_results.capture_expression_nmf_native_files', deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)

    try:
        case = F.workflow_case(directory, software, before_saved=before_saved)
        case.saved_evidence = evidence
        F.write(directory / 'SAVED_CHECK.json', {k: v for k, v in evidence.items()
            if k not in {'sheet_bytes', 'native_plans', 'calculations'}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_selected_native_fit_and_independent_numbers_reach_requested_receiver(connected_case):
    case = connected_case
    assert {role: len(rows) for role, rows in case.by_role.items()} == {
        'annotation': 1, 'scientific_process': 1, 'launch': 1, 'launch_local': 1, 'results': 2}
    assert F.OPERATION not in case.tools.catalog()
    information, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert information['name'] == F.OPERATION and information['resources'] == 'local'
    assert information['description'] and information['instructions']
    assert case.provider.plan['requested_job']['native_expression_nmf'] == case.job
    assert case.provider.plan['policy'] == F.POLICY
    native_execution = json.loads((case.directory / 'native-lifecycle.json').read_text())
    assert native_execution['returncode'] == 0
    assert native_execution['metadata']['verified_cgroup'] == {'memory_max': 21474836480,
        'memory_swap_max': 0, 'runtime_max': 'infinity', 'kill_mode': 'control-group', 'oom_policy': 'kill'}
    assert case.job['parameters'] == {'rank': 2, 'random_state': 42, 'normalization': 'none', 'tol': .0001, 'max_iter': 1000}
    assert len(case.provider.native_bytes) == 5
    manifest = json.loads(case.provider.native_bytes['manifest'])
    sheet = json.loads(case.saved_evidence['sheet_bytes'])
    assert sheet['raw_matrix'] == sheet['fit_matrix'] == [[1, 2, 0], [0, 1, 3], [1, 3, 3]]
    assert [r['label'] for r in sheet['genes']] == ['g', 'g', 'g3']
    assert [r['key'] for r in sheet['genes']] == ['gene:0', 'gene:1', 'gene:2']
    assert [r['label'] for r in sheet['samples']] == ['A', 'B', 'B']
    assert [r['key'] for r in sheet['samples']] == ['sample:0', 'sample:1', 'sample:2']
    assert sheet['genes'][0]['metadata']['target_key'] == 'target0'
    assert sheet['genes'][1]['metadata']['target_key'] == 'target1'
    assert sheet['samples'][1]['metadata']['condition'] == 'condition1'
    assert sheet['samples'][2]['metadata']['condition'] == 'condition2'
    assert sheet['native_diagnostics']['fit_call_count'] == 1
    assert sheet['source']['kind'] == 'sklearn_fit'
    assert sheet['normalization'] == 'none' and sheet['raw_units'] == sheet['fit_units'] == 'counts'
    assert sheet['uncertainty'] is None
    X, W, H = sheet['fit_matrix'], sheet['W'], sheet['H']
    # Independent literal matrix arithmetic; do not call production calculators.
    predicted = [[sum(W[g][k] * H[k][s] for k in range(2)) for s in range(3)] for g in range(3)]
    residual = [[X[g][s] - predicted[g][s] for s in range(3)] for g in range(3)]
    sse = sum(value * value for row in residual for value in row)
    frobenius = math.sqrt(sse)
    calculation = case.saved_evidence['calculations']
    assert calculation['sse'] == pytest.approx(sse, rel=1e-12, abs=1e-20)
    assert calculation['frobenius_residual'] == pytest.approx(frobenius, rel=1e-12)
    assert calculation['rmse'] == pytest.approx(math.sqrt(sse / 9), rel=1e-12)
    assert any(value < 0 for row in residual for value in row)
    assert sheet['native_diagnostics']['reconstruction_err_'] == calculation['native_reconstruction_error']
    assert calculation['native_minus_calculated_frobenius'] == calculation['native_reconstruction_error'] - calculation['frobenius_residual']
    first, second = [value['nmf'][0] for value in case.returned]
    assert first['view'] == 'fit_diagnostics' and first['selector'] == F.selector()['projection']
    values = {row['field']: row for row in first['rows']}
    assert values['sse']['value'] == calculation['sse'] and values['sse']['units'] == 'counts^2'
    assert values['cell_count']['value'] == 9 and values['rmse']['denominator'] == 9
    assert values['frobenius_residual']['value'] == calculation['frobenius_residual']
    assert values['native_reconstruction_error']['value'] == sheet['native_diagnostics']['reconstruction_err_']
    assert values['fit_call_count']['value'] == 1
    assert second['view'] == 'residual_cells'
    assert (second['total_available_rows'], second['selected_row_count'], second['filtered_row_count'],
        second['row_offset'], second['returned_row_count'], second['has_more']) == (9, 4, 4, 1, 3, False)
    assert [(r['gene_position'], r['sample_position']) for r in second['rows']] == [(1, 1), (0, 2), (0, 1)]
    assert {r['gene_label'] for r in second['rows']} == {'g'}
    assert {r['sample_label'] for r in second['rows']} == {'B'}
    for row in second['rows']:
        g, s = row['gene_position'], row['sample_position']
        assert row['signed_residual'] == pytest.approx(residual[g][s], rel=1e-12, abs=1e-15)
    assert case.forwarded == {'nmf': [first, second]}
    assert case.owner.native_expression_nmf_returns.received_facts(case.root_context, case.parent_form) == {
        F.PROJECTION_SOURCE: [first, second]}
    assert all(form['completed'] and not form['failures'] for form in case.returned)
    F.write(case.directory / 'NUMERICAL_EXAMPLE.json', {'input': X, 'W': W, 'H': H,
        'independently_reconstructed': predicted, 'independent_residuals': residual,
        'independent_sse': sse, 'independent_frobenius_residual': frobenius,
        'native_reconstruction_error': calculation['native_reconstruction_error'],
        'calculated_frobenius_residual': calculation['frobenius_residual'], 'manifest_outcome': manifest['result']['outcome'],
        'returned': case.returned, 'forwarded': case.forwarded})


def test_saved_sheet_alone_preserves_authority_and_has_zero_new_acquisition(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    assert len(saved['dispatches']) == 1
    original, recalculated = [row['result'] for row in case.outcomes]
    assert original['acquired_population'] is not None
    assert recalculated['acquired_population'] is None
    assert all(recalculated[key] is None for key in ('observation', 'native', 'capture'))
    assert case.returned[0]['saved'] == case.returned[1]['saved'] == [saved['sheet_file']]
    assert case.store.get_artifact(saved['sheet_file']['artifact_ref']) == saved['sheet_bytes']
    # Saved recalculation may reproduce the same content-addressed derived
    # calculation file. Original inputs, factors and native copies stay absent.
    saved_worker, = [row for row in F.worker_runs(case.directory)
        if row['plan']['mode'] == 'saved_sheet_recalculation']
    derived = {row['observed']['sha256'] for row in saved_worker['capture']['outputs']
        if row['observed'] is not None and row['observed']['format'] in {
            'expression_nmf_calculations_v1', 'expression_nmf_result_view_v1'}}
    recreated = [row for row in saved['removed'] if Path(row['path']).exists()]
    assert all(row['kind'] == 'original_worker_retained_scientific_bytes'
        and row['sha256'] in derived for row in recreated)
    assert {str(p): p.read_bytes() for p in case.workspace.rglob('expression-nmf-plan.json')} == saved['native_plans']
    assert sorted(row['plan']['mode'] for row in F.worker_runs(case.directory)) == ['native_result', 'saved_sheet_recalculation']
    assert all(row in F.rows(case.store, 'runtime_observations') for row in saved['observations'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in saved['actions'])
    file = saved['sheet_file']
    assert case.owner.resolve_received_reference(case.scientific_context, file['artifact_ref'], 'artifact') is True
    assert case.owner.resolve_received_reference(case.root_context, file['artifact_ref'], 'artifact') is False
    with pytest.raises(ValueError, match='saved_sheet_not_received'):
        case.owner.native_expression_nmf_returns.authenticate_received_saved_sheet(case.root_context, file)
    assert all(access['handle'] != case.provider.target['execution_id'] for access in saved['lifecycle_accesses'])
    for row in F.worker_runs(case.directory):
        execution = json.loads((Path(row['directory']) / 'execution.json').read_bytes())
        assert execution['terminal'] and execution['quiescent'] and execution['returncode'] == 0
        assert execution['metadata']['verified_cgroup'] == {'memory_max': 21474836480,
            'memory_swap_max': 0, 'runtime_max': 'infinity', 'kill_mode': 'control-group', 'oom_policy': 'kill'}
        assert execution['intent']['source_pins'] and execution['intent']['runtime_files']
        assert execution['intent']['interpreter'] and execution['intent']['dependencies']


def test_actual_observations_exact_redelivery_and_practical_terminal_zero(connected_case):
    case = connected_case
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [r for r in F.rows(case.store, 'runtime_actions') if r['episode_id'] == context.episode_id]
        observations = [r for r in F.rows(case.store, 'runtime_observations') if r['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed']
        assert case.provider.turns[context.episode_id] == len(actions) + (context.role == 'scientific_process')
        if context.role in {'launch', 'launch_local', 'results'}:
            assert len(actions) == 1
            assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
            assert proof is not None and case.owner.verify_completion(context, proof)
    assert [F.history(row) for row in case.by_role['launch_local']] == [[7]]
    assert [F.history(row) for row in case.by_role['launch']] == [[3]]
    assert [F.history(row) for row in case.by_role['results']] == [[2], [0]]
    assert case.store.count('annotation') == 0
    attempts = [row for row in F.rows(case.store, 'runtime_report_attempts')
        if row['parent_episode_id'] == case.scientific_context.episode_id]
    originals = [row for row in attempts if row['child_episode_id'] == case.result_contexts[0].episode_id]
    assert len(originals) == 2 and originals[0]['form'] == originals[1]['form']
    assert all(row['failure'] is None for row in originals)


def test_closed_workflow_and_result_replay_performs_no_new_work(connected_case, monkeypatch):
    case = connected_case
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_expression_nmf_native_files', 'prepare_expression_nmf_result_worker'):
        monkeypatch.setattr('gene_annotation_episode.native_expression_nmf_results.' + name, deny)
    monkeypatch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    monkeypatch.setattr('socket.socket.connect_ex', deny)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed Workflow requested a new decision')
        async def release(self, episode_id):
            pass

    with Store(case.directory / 'state') as store:
        before = {table: F.rows(store, table) for table in F.TABLES}
        flow, _ = F.assemble(store, case.directory, NoNewDecisions(), case.configuration)
        owner = flow.episode_bindings.for_role('results')
        for context, original in zip(case.result_contexts, case.outcomes):
            restored = owner.native_expression_nmf_returns.context(context.episode_id)
            key = f'{F.RUN_ID}:{context.episode_id}:0'
            proof = owner.completion_for_action(restored, key)
            replay = asyncio.run(owner.execute(restored, 'execution.results.collect', {}, key))
            assert replay == {k: v for k, v in original.items() if k != 'pending_work_after_action'}
            assert owner.verify_completion(restored, proof)
        _, _, archive = asyncio.run(F.run_root(flow, case.configuration))
        assert archive == case.archive
        assert {table: F.rows(store, table) for table in F.TABLES} == before


def test_explicit_retained_closed_nmf_workflow_replays_without_fit_or_calculation(tmp_path, monkeypatch):
    """Reopen a separately pinned completed case, independently of connected_case."""
    from gene_annotation_episode import acquisition, expression_nmf_calculations as calculations
    from gene_annotation_episode import expression_nmf_result_views as projections
    from gene_annotation_episode import expression_nmf_result_worker as worker
    from gene_annotation_episode import expression_nmf_sheet as sheets
    from gene_annotation_episode import native_expression_nmf_driver as driver
    from gene_annotation_episode import native_expression_nmf_preparation as preparation
    from gene_annotation_episode import native_expression_nmf_results as native_results
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode.execution_progress import ExecutionTargetReader
    from gene_annotation_episode.tools import ToolRegistry

    environment = 'HMMER_NATIVE_ORACLE_NMF_RETAINED'
    selected = os.environ.get(environment + '_PROOF')
    if not selected:
        pytest.skip('requires an explicitly selected immutable completed NMF case')

    def pin(path):
        path = Path(path).resolve(strict=True)
        raw = path.read_bytes()
        return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

    def tree_pins(directory):
        return {str(path.relative_to(directory)): pin(path)
            for path in sorted(Path(directory).rglob('*')) if path.is_file()}

    def database_pins(directory):
        return [dict(name=name, sha256=value['sha256'], size_bytes=value['size_bytes'])
            for name in ('state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm')
            if (path := Path(directory) / name).is_file() for value in [pin(path)]]

    def all_rows(store):
        tables = [row[0] for row in store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if not row[0].startswith('sqlite_')]
        assert all(name.replace('_', '').isalnum() for name in tables)
        return {table: F.rows(store, table) for table in tables}

    def table_columns(store):
        return {name: [dict(row) for row in store.db.execute('PRAGMA table_info(' + name + ')')]
            for (name,) in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            if not name.startswith('sqlite_')}

    def unchanged_rows(before, after, before_columns, after_columns):
        additions = {'runtime_execution_file_capture_admissions', 'runtime_execution_file_captures',
            'runtime_flux_balance_request_bindings'}
        assert set(after) - set(before) <= additions and set(before) <= set(after)
        assert all(not after[name] for name in set(after) - set(before))
        for name, rows in before.items():
            columns, actual = before_columns[name], after_columns[name]
            extra = actual[len(columns):]
            assert actual[:len(columns)] == columns
            if extra:
                assert name == 'runtime_report_attempts' and extra == [dict(cid=len(columns),
                    name='report_contract_declaration', type='TEXT', notnull=0, dflt_value=None, pk=0)]
            keys = {row['name'] for row in columns}
            assert len(after[name]) == len(rows)
            assert [{key: value for key, value in row.items() if key in keys} for row in after[name]] == rows
            assert all(set(row) - keys == {column['name'] for column in extra}
                and all(row[column['name']] is None for column in extra) for row in after[name])

    output = tmp_path / 'NMF_RETAINED_REPLAY.json'
    audit = dict(version='expression_nmf_retained_closed_replay_v1', phase='selected', passed=False,
        original_authenticated=False, owned_database_cloned=False, closed_replay_verified=False,
        literal_results_verified=False, typed_parent_delivery_verified=False,
        saved_sheet_permissions_verified=False, histories_unchanged=False, originals_unchanged=False,
        forbidden_work_attempts=[], qualification=(
            'Historical completed local NMF Workflow replay only; no fit, saved calculation or new scientific claim.'))
    F.write(output, audit)
    store = None
    try:
        proof_path = Path(selected).resolve(strict=True)
        assert proof_path.name == 'CASE.json'
        original = proof_path.parent
        controls = {name: pin(original / name) for name in ('CASE.json', 'fixture-configuration.json', 'SAVED_CHECK.json')}
        for name, suffix in (('CASE.json', '_PROOF_SHA256'),
                ('fixture-configuration.json', '_CONFIGURATION_SHA256'), ('SAVED_CHECK.json', '_SAVED_CHECK_SHA256')):
            assert controls[name]['sha256'] == os.environ[environment + suffix]
        proof = json.loads(proof_path.read_bytes())
        configuration = json.loads((original / 'fixture-configuration.json').read_bytes())
        saved = json.loads((original / 'SAVED_CHECK.json').read_bytes())
        assert configuration['goal'] == F.TASK == proof['archive']['request']['goal']['objective']
        assert configuration['scope'] == proof['archive']['request']['message']['scope']
        assert configuration['scientific_binding']['version'] == 'scientific_process_episodes_v8'
        assert proof['archive']['run_id'] == F.RUN_ID
        assert proof['archive']['ended_by'] == 'yield_stop'
        assert proof['forwarded'] == dict(nmf=[form['nmf'][0] for form in proof['returned']])
        assert all(form['completed'] and not form['failures'] for form in proof['returned'])
        bundle = database_pins(original / 'state')
        bundle_digest = hashlib.sha256(F.canonical(bundle).encode('utf-8')).hexdigest()
        assert bundle_digest == os.environ[environment + '_SQLITE_PINS_SHA256']
        original_artifacts = tree_pins(original / 'state/artifacts')
        original_run = tree_pins(original / 'run')
        audit.update(original_authenticated=True, controls=controls, original_sqlite_bundle=bundle,
            original_sqlite_bundle_sha256=bundle_digest,
            recorded_scientific_binding=configuration['scientific_binding'])
        staging = tmp_path / 'sqlite-staging'
        staging.mkdir()
        for row in bundle:
            shutil.copyfile(original / 'state' / row['name'], staging / row['name'])
        assert database_pins(staging) == bundle
        owned = tmp_path / 'owned-retained-nmf'
        (owned / 'state').mkdir(parents=True)
        source_db, destination_db = sqlite3.connect(staging / 'state.sqlite3'), sqlite3.connect(owned / 'state/state.sqlite3')
        try:
            source_db.execute('PRAGMA query_only=ON')
            source_db.backup(destination_db)
        finally:
            destination_db.close(); source_db.close()
        shutil.copytree(original / 'state/artifacts', owned / 'state/artifacts')
        shutil.copytree(original / 'run', owned / 'run')
        audit['owned_database_cloned'] = True
        F.write(output, audit)
        store = Store(owned / 'state')
        before = all_rows(store)
        before_columns = table_columns(store)
        before_counts = {name: len(rows) for name, rows in before.items()}
        input_ref = saved['original_receipt']['native']['original_plan']['requested_job']['native_expression_nmf']['input']['artifact_ref']
        assert not (store.path / 'artifacts' / input_ref[9:11] / input_ref[9:]).exists()
        original_input = Path(saved['original_receipt']['native']['original_plan']['requested_job']['native_expression_nmf']['input']['path'])
        original_open, builtin_open, io_open, os_open = Path.open, __import__('builtins').open, __import__('io').open, os.open

        def forbidden(*args, **kwargs):
            audit['forbidden_work_attempts'].append(dict(argument_types=[type(value).__name__ for value in args]))
            raise AssertionError('retained NMF replay attempted fit, calculation, native work or network')

        def check_path(value, *, dir_fd=None):
            if isinstance(value, int): return
            path = Path(os.fsdecode(value))
            if not path.is_absolute():
                path = (Path(os.readlink('/proc/self/fd/' + str(dir_fd))) if dir_fd is not None else Path.cwd()) / path
            path = Path(os.path.normpath(path))
            if (path.is_relative_to(original) or path == original_input
                    or path == store.path / 'artifacts' / input_ref[9:11] / input_ref[9:]):
                audit['forbidden_work_attempts'].append(dict(path=str(path)))
                raise AssertionError('retained NMF replay reopened original files or input bytes')

        def checked_path(path, *args, **kwargs): check_path(path); return original_open(path, *args, **kwargs)
        def checked_builtin(path, *args, **kwargs): check_path(path); return builtin_open(path, *args, **kwargs)
        def checked_io(path, *args, **kwargs): check_path(path); return io_open(path, *args, **kwargs)
        def checked_os(path, flags, *args, **kwargs):
            check_path(path, dir_fd=kwargs.get('dir_fd')); return os_open(path, flags, *args, **kwargs)

        class NoNewDecisions:
            async def complete(self, *args, **kwargs): return forbidden(*args, **kwargs)
            async def release(self, episode_id): pass

        with monkeypatch.context() as guard:
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel'):
                guard.setattr(native_lifecycle, name, forbidden)
            for module, names in (
                (driver, ('run_expression_nmf', 'retain_expression_nmf_artifacts', 'execute_expression_nmf_plan')),
                (calculations, ('calculate_nmf_sheet', 'reconstruct_nmf', 'residual_measurements', 'component_measurements')),
                (sheets, ('load_expression_nmf_artifacts', 'populate_nmf_sheet')),
                (projections, ('project_nmf_result',)),
                (worker, ('execute_expression_nmf_worker', 'load_expression_nmf_artifacts',
                    'populate_nmf_sheet', 'calculate_nmf_sheet', 'project_nmf_result')),
                (preparation, ('prepare_expression_nmf_result_worker',)),
                (native_results, ('capture_expression_nmf_native_files', 'prepare_expression_nmf_result_worker')),
            ):
                for name in names: guard.setattr(module, name, forbidden)
            guard.setattr(native_results.NativeExpressionNMFResults, '_worker', forbidden)
            guard.setattr(ExecutionTargetReader, 'observe_target', forbidden)
            guard.setattr(acquisition.PublicClients, '_http', forbidden)
            guard.setattr(socket, 'create_connection', forbidden)
            guard.setattr(socket.socket, 'connect', forbidden)
            guard.setattr(socket.socket, 'connect_ex', forbidden)
            guard.setattr(ToolRegistry, '_source', forbidden)
            guard.setattr(Store, 'artifact', forbidden)
            guard.setattr(Path, 'open', checked_path)
            guard.setattr('builtins.open', checked_builtin)
            guard.setattr('io.open', checked_io)
            guard.setattr(os, 'open', checked_os)
            flow, _ = F.assemble(store, owned, NoNewDecisions(), configuration)
            owner = flow.episode_bindings.for_role('results')
            root, record, archive = asyncio.run(F.run_root(flow, configuration))
            assert archive == proof['archive']
            final = plain(asyncio.run(root.build_result(record)).as_record())
            assert final == dict(credit=0, pending_handles=[])
            audit.update(closed_replay_verified=True, archive=archive, final_result=final)
            contexts = {row['episode_id']: owner.native_expression_nmf_returns.context(row['episode_id'])
                for row in F.walk(archive)}
            science, = [context for context in contexts.values() if context.role == 'scientific_process']
            parent = contexts[archive['episode_id']]
            result_contexts = [contexts[row['episode_id']] for row in F.walk(archive)
                if contexts[row['episode_id']].role == 'results']
            actual_returned = []
            for context in result_contexts:
                key = f'{F.RUN_ID}:{context.episode_id}:0'
                action = flow.journal.row('runtime_actions', context.episode_id, 0)
                original_outcome = json.loads(action['result'])
                completion = owner.completion_for_action(context, key)
                repeated = asyncio.run(owner.execute(context, 'execution.results.collect', {}, key))
                assert repeated == {name: value for name, value in original_outcome.items() if name != 'pending_work_after_action'}
                assert completion is not None and owner.verify_completion(context, completion)
                actual_returned.append(json.loads(flow.journal.row('runtime_forms', context.episode_id)['form']))
            assert actual_returned == proof['returned']
            audit['literal_results_verified'] = True
            scientific_form = json.loads(flow.journal.row('runtime_forms', science.episode_id)['form'])
            assert scientific_form == proof['forwarded']
            parent_form = plain(science.request)['report_contract']['measurements']['schema']
            assert owner.native_expression_nmf_returns.received_facts(parent, parent_form) == {
                F.PROJECTION_SOURCE: proof['forwarded']['nmf']}
            audit['typed_parent_delivery_verified'] = True
            from test_expression_nmf_retained_finish import verify_retained_nmf_sheet_permissions
            permissions = verify_retained_nmf_sheet_permissions(flow=flow, owner=owner, science=science, parent=parent,
                result_contexts=result_contexts, configuration=configuration, saved=saved,
                monkeypatch=monkeypatch, forbidden=forbidden)
            audit.update(saved_sheet_permissions_verified=True, **permissions)
        unchanged_rows(before, all_rows(store), before_columns, table_columns(store))
        assert {name: len(rows) for name, rows in all_rows(store).items() if name in before_counts} == before_counts
        assert audit['forbidden_work_attempts'] == []
        assert {name: pin(original / name) for name in controls} == controls
        assert database_pins(original / 'state') == bundle
        assert tree_pins(original / 'state/artifacts') == original_artifacts and tree_pins(original / 'run') == original_run
        audit.update(histories_unchanged=True, originals_unchanged=True, passed=True, phase='verified',
            table_counts_before=before_counts, table_counts_after={name: len(rows) for name, rows in all_rows(store).items()})
    except BaseException as error:
        audit['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            try:
                audit['actual_table_counts'] = {name: len(rows) for name, rows in all_rows(store).items()}
            except BaseException as error:
                audit['history_capture_failure'] = dict(exception_type=type(error).__name__, message=str(error))
            finally: store.close()
            audit['owned_database'] = pin(store.path / 'state.sqlite3')
        F.write(output, audit)
