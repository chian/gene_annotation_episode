"""Actual bounded producer verification, separate from full Workflow delivery.

The selected practical-state fixture supplies ownership, never scientific
outputs. The original executable, parser, resource limits and retained output
bytes are real. Run only through the existing529 bounded verification runner.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_event_sheet import populate_fluorescence_sheet
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from gene_annotation_episode.native_fluorescence_contracts import (
    fluorescence_environment, requested_job_from_fluorescence,
    validate_fluorescence_manifest, validate_fluorescence_parsed_batch,
)
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.state import Store
from test_fluorescence_local_routing import SelectedState, target_identity
import fluorescence_workflow_support as F


@pytest.mark.parametrize('operation,parser', [
    ('perform_facs_cell_sorting', 'csv'),
    ('analyze_cytokine_production_in_cd4_tcells', 'table_snapshot'),
])
def test_actual_selected_producer_and_runtime_keep_original_event_values(tmp_path, monkeypatch,
        operation, parser):
    software = F.software_closure(tmp_path / 'software')
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    with Store(tmp_path / 'state') as store:
        job, raw = F.supplied_job(store, software, operation=operation, parser=parser)
        request = requested_job_from_fluorescence(job, environment=fluorescence_environment(
            software, attempt_directory=str(workspace / 'selected-context')))
        assignment = dict(version='practical_assignment_v1', assignment_id='native-runtime-check',
            resource_id='bounded-native', resource_kind='local', workspace=str(workspace),
            endpoint='usable_handoff', requested_job=request,
            progress_requirements=[dict(key='handoff', credit=1,
                predicate=dict(kind='requested_job_handoff'))], completion_keys=['handoff'],
            initial_context=dict(revision=0, cwd=str(workspace), environment={}),
            inventory_snapshot={}, constraints=dict(allocation=deepcopy(F.POLICY)))
        config = dict(kind='local', workspace=str(workspace), policy=deepcopy(F.POLICY),
            native_fluorescence=[dict(operation=operation, mode=job['mode'],
                parsers=[parser], software=software)])
        owner, state = LocalPracticalOperations(config), SelectedState(assignment)
        outcome, _ = owner._execute(state, 'practical.job.start', {}, 'selected-start')
        state.remember(outcome)
        execution = outcome['facts']['requested_job']['execution_id']
        handle = native_lifecycle.NativeJobHandle(Path(execution))
        completed = native_lifecycle.wait_job(handle)
        F.write(tmp_path / 'native-completion.json', dict(returncode=completed.returncode,
            metadata=completed.metadata, execution_id=execution))
        assert completed.returncode == 0, (completed.metadata, Path(execution).parent.joinpath('stderr.log').read_text())
        assert completed.metadata['verified_cgroup'] == F.LIMITS
        plan = owner._fluorescence_plan(assignment, execution,
            run_id=state.run_id, origin_episode_id=state.episode_id)
        assert plan['requested_job'] == request and plan['policy'] == F.POLICY
        paths = {row['role']: Path(plan['attempt_directory']) / row['relative_path']
            for row in plan['outputs']}
        manifest = validate_fluorescence_manifest(json.loads(paths['manifest'].read_bytes()),
            original_plan=plan)
        assert not manifest['failures']
        parsed = []
        for i in range(2):
            assert paths[f'event_input:{i}'].read_bytes() == raw
            batch_raw = paths[f'event_batch:{i}'].read_bytes()
            batch = validate_fluorescence_parsed_batch(json.loads(batch_raw),
                original_plan=plan, input_index=i)
            assert batch_raw == core.canonical(batch) + b'\n'
            assert [event['values'][0]['measurement']['value'] for event in batch['parse']['events']] == F.VALUES
            assert batch['parse']['source']['extent'] == 'complete'
            assert batch['parse']['sample'] == job['inputs'][i]['sample']
            parsed.append(batch['parse'])
        sheet = populate_fluorescence_sheet(parsed, **job['definitions'])
        components = calculate_fluorescence_sheet(sheet, parameters=job['parameters'])
        projected = project_fluorescence_result(sheet, components, selection=F.selector()['selection'])
        assert [row['value'] for row in projected['rows']] == [8, 5, .625, 62.5, 165, 150] * 2
        assert all(row in components['cells'] for row in projected['rows'])
        F.write(tmp_path / 'native-numerical-check.json', dict(plan=plan, manifest=manifest,
            sheet=sheet, calculations=components, projection=projected))

        def no_new_reservation(*args, **kwargs):
            pytest.fail('observing the selected completed handle attempted new work')

        monkeypatch.setattr(native_lifecycle, 'prepare_job', no_new_reservation)
        observed = owner.observe_execution(assignment, execution, **target_identity(state, plan))
        assert observed['state'] == 'completed' and observed['result_available']
        for selected in ('practical.job.start', 'practical.job.status', 'practical.job.collect'):
            again, _ = owner._execute(state, selected, {}, 'later-selected-observation')
            assert again['facts']['requested_job']['execution_id'] == execution
            assert again['native_outcome']['attempt_operation_key'] == 'selected-start'
        window = owner.read_output(assignment, execution, path=str(paths['manifest']),
            offset=0, limit=4096, **target_identity(state, plan))
        assert window['returned_bytes'] == min(4096, paths['manifest'].stat().st_size)
        assert state.receipts() == [{'outcome': outcome}]
