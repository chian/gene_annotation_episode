"""Actual own-role yield provenance and captured estimator replay checks.

Uses the retained private task fixture and its declared controlled Results
target/received ports. Completion verification, exhausted handoff receipts and
typed target/profile inputs below are controlled engineering operands. The
actual own binding yield factories, estimator, controller, serialization and
replay execute. No native/scientific completion or credit is asserted.
"""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.tests.test_private_task_refinement import PrivateTaskRefinementChecks


class YieldIdentityChecks:
    module = PrivateTaskRefinementChecks.module
    connected = PrivateTaskRefinementChecks.connected
    source = PrivateTaskRefinementChecks.source
    workflow = PrivateTaskRefinementChecks.workflow
    task = PrivateTaskRefinementChecks.task
    no_external_execution = PrivateTaskRefinementChecks.no_external_execution
    selected = PrivateTaskRefinementChecks.selected

    def retain(self, selected, case, value, tmp_path):
        raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n'
        directory = Path(os.environ.get('GENE_PRIVATE_YIELD_CAPTURE_DIR', str(tmp_path / 'yield-records')))
        directory.mkdir(parents=True, exist_ok=True)
        filename = self.binding_path.replace('/', '__') + '--' + case + '.json'
        if selected.phase == 'connected' and os.environ.get('GENE_PRIVATE_YIELD_BASELINE_DIR'):
            original = Path(os.environ['GENE_PRIVATE_YIELD_BASELINE_DIR']) / filename
            assert original.read_text() == raw
        with (directory / filename).open('x') as stream: stream.write(raw)

    def expected(self, method):
        return ('gene_annotation_episode.episodic_workflow.root.a110.'
            + self.binding_path.replace('/', '.') + '.yield.ExecutionEpisodeYield.' + method)

    def completion_context(self, s, index):
        unit = self.module('method_loop.identities').UnitRef(s.context.episode_id, index).as_record()
        proof = {'version': 'practical_completion_v1', 'run_id': s.v.run_id,
            'episode_id': s.context.episode_id, 'assignment_sha256': 'a' * 64,
            'endpoint': 'completed_job_outputs', 'operation_key': 'controlled-original-operation',
            'receipt_sha256': 'b' * 64, 'validation_keys': ['controlled_original_outputs']}
        return {'version': 'completed_action_estimation_context_v5',
            'current_completion_evidence': {'version': 'completed_action_evidence_v1',
                'run_id': s.v.run_id, 'episode_id': s.context.episode_id, 'unit_ref': unit,
                'original_decision_index': 7, 'action_kind': 'tool', 'received_record_refs': [],
                'received_progress_refs': [], 'progress_records': [], 'child_return': None,
                'unavailable_reasons': []},
            'practical_completion': {**proof, 'unit_ref': unit, 'action_index': 7}}

    @pytest.mark.parametrize('verified', [False, True])
    def test_actual_practical_record_and_captured_replay(self, selected, verified, monkeypatch, tmp_path):
        s, calls = selected, []
        def verification(context, proof):
            assert context is s.context
            calls.append(deepcopy(proof))
            return verified
        monkeypatch.setattr(s.binding, 'verify_completion', verification)
        estimator = s.binding.practical_estimator(s.context)
        expected = self.expected('practical_estimator.<locals>.<lambda>')
        assert estimator.as_record()['completion_verifier'] == expected
        numeric = self.module('numerical')
        context = self.completion_context(s, 1)
        original_context = deepcopy(context)
        records = []
        for repeat in range(2):
            # The second real controller reconstructs the same saved action
            # inputs. Signed corrections and original positions remain exact.
            controller = numeric.YieldController('controlled-original-yield', 0, 0,
                estimate_with_context=s.binding.practical_estimator(s.context))
            steps = [controller.observe('original-first', {'credit': 0, 'estimation_context': None}).as_record(),
                controller.observe('original-correction', {'credit': -.25, 'estimation_context': deepcopy(context)}).as_record()]
            assert controller.estimator.scores == (0, -.25)
            assert steps[-1]['estimate']['turns'] == 2
            if verified:
                assert steps[-1]['estimate']['provenance'] == estimator.as_record()
            records.append({'estimator': estimator.as_record(), 'steps': steps, 'state': controller.state().as_record()})
        assert records[0] == records[1] and context == original_context
        proof = {key: value for key, value in context['practical_completion'].items() if key not in {'unit_ref', 'action_index'}}
        assert calls == [proof, proof]
        self.retain(s, 'practical-' + str(verified), records[0], tmp_path)
        error = LookupError('controlled original completion verifier rejection')
        def rejected(*args): raise error
        monkeypatch.setattr(s.binding, 'verify_completion', rejected)
        with pytest.raises(LookupError) as observed:
            estimator((0, -.25), numeric.YieldParameters(), (None, context))
        assert observed.value is error

    @pytest.mark.parametrize('branch', ['finite_or_exhausted', 'typed_or_available'])
    def test_actual_role_controller_definition_and_captured_replay(self, selected, branch, monkeypatch, tmp_path):
        s = selected
        monkeypatch.setattr(s.binding, 'private_yield_binding', True)
        practical_type = self.module('practical_yield').PracticalYieldEstimator
        if s.role == 'launch':
            original = s.binding._launch(s.v.runtime._plain(s.context.assignment), scope=s.context.scope)
            eligible = {resource for resource in original['requests'] if s.binding._permitted(original, resource)}
            assert eligible
            classes = sorted(s.binding._request_yield_class(original['requests'][resource]) for resource in eligible)
            monkeypatch.setattr(s.binding, 'task_yield_profiles', {
                'launch:' + '+'.join(classes): {'cutoff': 0, 'parameters': {}}})
            handoffs = {'controlled-' + resource: {'resource_id': resource} for resource in eligible}
            selected_refs = list(handoffs) if branch == 'finite_or_exhausted' else []
            monkeypatch.setattr(s.binding, '_received', lambda context:
                ({'initial_known_record_refs': selected_refs}, handoffs, {}))
            monkeypatch.setattr(s.binding.job_progress_provider.targets, 'usable_handoff', lambda target: True)
        elif branch == 'finite_or_exhausted':
            monkeypatch.setattr(s.binding, 'task_yield_profiles', {
                'results:native_finite_local': {'cutoff': 0, 'parameters': {}}})
        else:
            monkeypatch.setattr(s.binding, '_target', lambda context:
                {'resource_kind': 'local'})
            monkeypatch.setattr(s.binding, '_selector', lambda assignment, target:
                {'version': 'controlled_selector_v1'})
            monkeypatch.setattr(s.binding, 'task_yield_profiles', {
                'results:typed_local_controlled_selector_v1': {'cutoff': 0, 'parameters': {}}})
        records = []
        for repeat in range(2):
            controller = s.binding.yield_controller(s.context, 0, 'controlled-original-role-yield')
            callback = controller.estimator.estimate_with_context if hasattr(controller.estimator, 'estimate_with_context') else None
            identity = None
            if s.role == 'launch' and branch == 'finite_or_exhausted':
                identity = callback.__module__ + '.' + callback.__qualname__
                assert identity == self.expected('_launch_yield_controller.<locals>.no_remaining_requests')
            elif s.role == 'results' and branch == 'finite_or_exhausted':
                identity = callback.__module__ + '.' + callback.__qualname__
                assert identity == self.expected('_results_yield_controller.<locals>.finite_result_yield')
                endpoints = [cell.cell_contents for cell in callback.__closure__
                    if isinstance(cell.cell_contents, practical_type)]
                endpoint, = endpoints
                assert endpoint.as_record()['completion_verifier'] == self.expected('_results_yield_controller.<locals>.<lambda>')
                identity = {'callback': identity, 'endpoint': endpoint.as_record()}
            elif s.role == 'results':
                assert isinstance(callback, practical_type)
                identity = callback.as_record()
                assert identity['completion_verifier'] == self.expected('_results_yield_controller.<locals>.<lambda>')
            initial = controller.state().as_record()
            step = controller.observe('original-unavailable', {'credit': 0, 'estimation_context': None}).as_record()
            records.append({'identity': identity, 'initial': initial, 'step': step, 'state': controller.state().as_record()})
        assert records[0] == records[1]
        self.retain(s, branch, records[0], tmp_path)


class TestPlanningLaunch(YieldIdentityChecks):
    binding_path = 'hpc_work_planning/execution_job_submission'
class TestAllocationLaunch(YieldIdentityChecks):
    binding_path = 'hpc_work_planning/hpc_allocation_execution/execution_job_submission'
class TestScientificPlanningLaunch(YieldIdentityChecks):
    binding_path = 'scientific_process/hpc_work_planning/execution_job_submission'
class TestScientificAllocationLaunch(YieldIdentityChecks):
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
class TestPlanningResults(YieldIdentityChecks):
    binding_path = 'hpc_work_planning/execution_result_acquisition'
class TestAllocationResults(YieldIdentityChecks):
    binding_path = 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
class TestScientificPlanningResults(YieldIdentityChecks):
    binding_path = 'scientific_process/hpc_work_planning/execution_result_acquisition'
class TestScientificAllocationResults(YieldIdentityChecks):
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
