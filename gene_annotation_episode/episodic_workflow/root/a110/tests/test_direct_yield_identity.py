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

from gene_annotation_episode.episodic_workflow.root.a110.tests.test_direct_private_tasks import DirectPrivateTaskChecks


class YieldIdentityChecks:
    module = DirectPrivateTaskChecks.module
    connected = DirectPrivateTaskChecks.connected
    source = DirectPrivateTaskChecks.source
    workflow = DirectPrivateTaskChecks.workflow
    task = DirectPrivateTaskChecks.task
    no_external_execution = DirectPrivateTaskChecks.no_external_execution
    selected = DirectPrivateTaskChecks.selected

    def retain(self, selected, case, value, tmp_path):
        raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n'
        directory = Path(os.environ.get('GENE_DIRECT_YIELD_CAPTURE_DIR', str(tmp_path / 'yield-records')))
        directory.mkdir(parents=True, exist_ok=True)
        filename = self.binding_path.replace('/', '__') + '--' + case + '.json'
        if selected.phase == 'connected' and os.environ.get('GENE_DIRECT_YIELD_BASELINE_DIR'):
            original = Path(os.environ['GENE_DIRECT_YIELD_BASELINE_DIR']) / filename
            assert original.read_text() == raw
        with (directory / filename).open('x') as stream: stream.write(raw)

    def expected(self, method):
        return ('gene_annotation_episode.episodic_workflow.root.a110.'
            + self.binding_path.replace('/', '.') + '.yield_estimator.ExecutionEpisodeYield.' + method)

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



class TestAnnotationLaunch(YieldIdentityChecks):
    binding_path = 'execution_job_submission'
class TestScientificLaunch(YieldIdentityChecks):
    binding_path = 'scientific_process/execution_job_submission'
class TestAnnotationResults(YieldIdentityChecks):
    binding_path = 'execution_result_acquisition'
class TestScientificResults(YieldIdentityChecks):
    binding_path = 'scientific_process/execution_result_acquisition'
