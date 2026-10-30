"""Actual ATAC child execution/returns; scripted decisions, synthetic BAMs.

Run only through478/run_checks.py. This verifies the production path and saved
recalculation, not an LLM annotation run or scientific model calibration.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_atac_episode_path_2026-10-27_478.fixture_helpers')


def deny(*args, **kwargs):
    raise AssertionError('saved calculation or closed replay attempted native work, acquisition, or network')


@pytest.fixture(scope='module')
def connected_case(tmp_path_factory):
    directory = tmp_path_factory.mktemp('atac478')
    template = json.loads(Path(os.environ['ATAC478_NATIVE_TEMPLATE']).read_text())
    evidence, patch = {}, pytest.MonkeyPatch()

    def before_saved(case):
        original, = F.worker_runs(directory)
        assert original['plan']['mode'] == 'native_result'
        evidence['original_worker'] = original
        evidence['bundle'] = deepcopy(case.bundle)
        files = [case.bundle['sheet'], *(row['file'] for row in case.bundle['tables'])]
        evidence['retained_bytes'] = {file['artifact_ref']: case.store.get_artifact(file['artifact_ref']) for file in files}
        evidence['observations'] = F.rows(case.store, 'runtime_observations')
        evidence['actions'] = [r for r in F.rows(case.store, 'runtime_actions') if r['result'] is not None]
        evidence['origins'] = case.owner.atac_returns.authenticate_received_saved_bundle(case.science_context, case.bundle)
        evidence['native_plans'] = {str(p): p.read_bytes() for p in case.workspace.rglob('atac-plan.json')}
        removed = []

        def remove(path, kind):
            if path.is_file():
                raw = path.read_bytes()
                path.unlink()
                removed.append({'kind': kind, 'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

        for spec in case.provider.plan['outputs']:
            if spec['role'] in {'bundle', 'seal', 'stdout', 'stderr', 'request_metadata', 'depth_selection'}:
                continue
            remove(Path(case.provider.plan['attempt_directory']) / spec['relative_path'], 'native_scientific_copy')
            raw = case.provider.native_bytes.get(spec['file_key'])
            if raw is not None:
                sha = hashlib.sha256(raw).hexdigest()
                if 'artifact_' + sha not in evidence['retained_bytes']:
                    remove(case.store.path / 'artifacts' / sha[:2] / sha, 'captured_native_scientific_bytes')
        for row in case.provider.plan['requested_job']['native_atac_differential']['input_bindings']:
            remove(Path(row['path']), 'original_caller_bam')
        for row in original['capture']['outputs']:
            if row['role'] in {'sheet', 'track_table', 'partitions', 'components', 'regions', 'calculations', 'projection'}:
                remove(Path(original['directory']) / row['capture']['declared']['relative_path'], 'original_worker_scientific_copy')
        assert removed and all(not Path(row['path']).exists() for row in removed)
        evidence['removed'], evidence['dispatches'] = removed, []
        from gene_annotation_episode import native_lifecycle
        actual_prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.atac_differential_result_worker']
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan['mode'] == 'saved_sheet_recalculation'
            assert plan['selector']['saved_sheet_bundle'] == case.bundle
            assert kwargs['policy'].to_dict() == F.POLICY
            evidence['dispatches'].append({'command': list(command), 'plan': deepcopy(plan)})
            return actual_prepare(command, **kwargs)

        patch.setattr(native_lifecycle, 'prepare_job', saved_worker_only)
        patch.setattr('gene_annotation_episode.native_atac_differential_results.capture_atac_native_files', deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)

    try:
        case = F.workflow_case(directory, template, before_saved=before_saved)
        case.saved_evidence = evidence
        F.write(directory / 'SAVED_CHECK.json', {k: v for k, v in evidence.items() if k not in {'retained_bytes', 'native_plans'}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_selected_tool_native_measurements_reach_exact_requested_receiver(connected_case):
    case = connected_case
    assert {role: len(rows) for role, rows in case.by_role.items()} == {
        'annotation': 1, 'scientific_process': 1, 'launch': 1, 'launch_local': 1, 'results': 2}
    assert F.OPERATION not in case.tools.catalog()
    information, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert information['name'] == F.OPERATION and information['resources'] == 'local'
    assert information['description'] and information['instructions']
    assert case.provider.plan['requested_job']['native_atac_differential'] == case.job
    assert case.provider.plan['policy'] == F.POLICY
    bundle = json.loads(case.provider.native_bytes['bundle'])
    assert [row['outcome'] for row in bundle['steps']] == ['succeeded'] * 3
    saved = case.saved_evidence['bundle']
    sheet = json.loads(case.saved_evidence['retained_bytes'][saved['sheet']['artifact_ref']])
    assert [row['count'] for row in sheet['depth_selection']['conditions']] == [100, 200]
    assert [row['rows']['row_count'] for row in sheet['tracks']] == [110, 35, 210, 69]
    assert [row['rows'][0]['display_score'] for row in sheet['narrowpeaks']] == [516, 1045]
    assert len(sheet['bam_references']) == 2
    first, second = [value['atac'][0] for value in case.returned]
    assert first['kind'] == 'native_peak_rows' and first['total_rows'] == 3
    assert {row['callpeak_run_key'] for row in first['rows']} == {'callpeak2'}
    assert {row['representation'] for row in first['rows']} == {'xls', 'narrowpeak', 'summit'}
    narrow, = [row['row'] for row in first['rows'] if row['representation'] == 'narrowpeak']
    assert (narrow['start0'], narrow['end0'], narrow['display_score']) == (2909, 3190, 1045)
    assert second['kind'] == 'derived_regions' and second['rows'] == [] and second['total_rows'] == 0
    assert second['parameters']['cutoff_log10_lr'] == 1000000
    assert case.forwarded == {'atac': [first, second]}
    assert case.owner.atac_returns.facts(case.root_context, case.parent_form) == {F.PROJECTION_SOURCE: [first, second]}
    assert all(form['completed'] for form in case.returned)


def test_received_saved_calculation_has_no_native_reacquisition_or_new_credit(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    assert len(saved['dispatches']) == 1
    original, recalculated = [row['result'] for row in case.outcomes]
    assert original['acquired_population'] is not None
    assert recalculated['acquired_population'] is None and recalculated['observation'] is None and recalculated['capture'] is None
    assert case.returned[0]['saved'] == case.returned[1]['saved'] == [saved['bundle']]
    assert all(case.store.get_artifact(ref) == raw for ref, raw in saved['retained_bytes'].items())
    assert all(not Path(row['path']).exists() for row in saved['removed'])
    assert {str(p): p.read_bytes() for p in case.workspace.rglob('atac-plan.json')} == saved['native_plans']
    assert sorted(row['plan']['mode'] for row in F.worker_runs(case.directory)) == ['native_result', 'saved_sheet_recalculation']
    assert all(row in F.rows(case.store, 'runtime_observations') for row in saved['observations'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in saved['actions'])
    for ref in saved['retained_bytes']:
        assert case.owner.resolve_received_reference(case.scientific_context, ref, 'artifact') is True
        assert case.owner.resolve_received_reference(case.root_context, ref, 'artifact') is False
    with pytest.raises(ValueError):
        case.owner.atac_returns.authenticate_received_saved_bundle(case.root_context, saved['bundle'])


def test_actual_turns_credit_and_terminal_expectations(connected_case):
    case = connected_case
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [r for r in F.rows(case.store, 'runtime_actions') if r['episode_id'] == context.episode_id]
        observations = [r for r in F.rows(case.store, 'runtime_observations') if r['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed'] == case.provider.turns[context.episode_id]
        if context.role in {'launch', 'launch_local', 'results'}:
            assert len(actions) == 1
            assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
            assert proof is not None and case.owner.verify_completion(context, proof)
    assert [F.history(row) for row in case.by_role['launch_local']] == [[7]]
    assert [F.history(row) for row in case.by_role['launch']] == [[3]]
    assert [F.history(row) for row in case.by_role['results']] == [[2], [0]]
    assert case.store.count('annotation') == 0


def test_closed_workflow_and_result_replay_performs_no_new_work(connected_case, monkeypatch):
    case = connected_case
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_atac_native_files', 'prepare_atac_result_worker'):
        monkeypatch.setattr('gene_annotation_episode.native_atac_differential_results.' + name, deny)
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
            restored = owner.atac_returns.context(context.episode_id)
            key = f'{F.RUN_ID}:{context.episode_id}:0'
            proof = owner.completion_for_action(restored, key)
            replay = asyncio.run(owner.execute(restored, 'execution.results.collect', {}, key))
            assert replay == {k: v for k, v in original.items() if k != 'pending_work_after_action'}
            assert owner.verify_completion(restored, proof)
        _, _, archive = asyncio.run(F.run_root(flow, case.configuration))
        assert archive == case.archive
        assert {table: F.rows(store, table) for table in F.TABLES} == before
