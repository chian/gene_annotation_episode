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
