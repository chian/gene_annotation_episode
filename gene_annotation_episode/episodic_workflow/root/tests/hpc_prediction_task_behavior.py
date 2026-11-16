"""Actual prediction operations through the selected task and its saved journal."""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from .hpc_prediction_behavior import PredictionBehavior


class PredictionTaskBehavior:
    module = PredictionBehavior.module
    setup = PredictionBehavior.setup

    def test_runtime_build_selects_declared_private_task(self, tmp_path, monkeypatch):
        _, _, binding, _, context = self.setup(tmp_path)
        runtime = self.module('runtime')
        registry = self.module('episode_bindings').EpisodeBindingRegistry((binding,))
        monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs: SimpleNamespace(episode_id=context.episode_id))
        monkeypatch.setattr(runtime, 'FeedbackEpisode', lambda grain, key, source, *args, **kwargs: source)
        workflow = SimpleNamespace(context=object(), grains={'hpc_prediction': object()},
            inprocess_completion_order=None, receipts=None, scientific_process_binding=None,
            episode_bindings=registry, contract_information_profile=lambda source: None,
            specialist=lambda source: binding, binding_context=lambda source: context,
            journal=SimpleNamespace(row=lambda *args: None, save=lambda *args: None),
            run_id='test-run', store=SimpleNamespace(transaction=nullcontext, db=SimpleNamespace(execute=lambda *args: None)),
            source_credit_view=lambda source: binding.credit_view(context, None),
            expose_assigned_job=lambda source: None, receive_tool_attributions=lambda *args, **kwargs: None,
            archive=SimpleNamespace(store=lambda value: value),
            launch_instructions=SimpleNamespace(materialize=lambda selected: None))
        # a103's Workflow.build reads self.legacy_parent_for_path (a103/runtime.py); bind the real method.
        if self.axis == 'a103':
            workflow.legacy_parent_for_path = lambda path: runtime.Workflow.legacy_parent_for_path(workflow, path)
        task = runtime.Workflow.build(workflow, 'hpc_prediction', 'prediction', 'Improve measured predictions',
            runtime._plain(context.scope), episode_assignment=runtime._plain(context.assignment))
        assert type(task) is binding.decision_source_type
        assert not isinstance(task, runtime.DecisionSource)
        assert task.episode_id == context.episode_id
        assert binding.state(context).read('entry:' + task.episode_id)['model_ref'] == 'reference_model'

    def test_private_task_keeps_original_exception_identities(self, tmp_path):
        _, _, binding, _, _ = self.setup(tmp_path)
        runtime = self.module('runtime')
        task = self.module(self.binding_path.replace('/', '.') + '.task')
        assignment = self.module(self.binding_path.replace('/', '.') + '.from_parent')
        assert task.WorkflowError is runtime.WorkflowError
        assert task.ValidationError is runtime.ValidationError
        assert task.ReportBoundaryError is runtime.ReportBoundaryError
        assert assignment.validate_schema is self.module('domain').validate_schema

    def task_fixture(self, tmp_path):
        c, parent, binding, owner, context = self.setup(tmp_path)
        runtime = self.module('runtime')
        task_type = getattr(binding, 'decision_source_type', runtime.DecisionSource)
        task = object.__new__(task_type)
        task.episode_id = context.episode_id
        task.path, task.scope = context.path, runtime._plain(context.scope)
        task.calls = 0
        task._execution_context = task._delivery_resolution_ref = None
        task.report_values, task.report_basis = {}, []
        task.interpret_schema = runtime._object({})
        task.last_outcome = task.last_outcome_index = task.feedback = None
        task.request = SimpleNamespace(
            goal=SimpleNamespace(as_record=lambda: {'objective': c['objective']}),
            message=SimpleNamespace(as_record=lambda: {'episode_assignment': context.assignment}),
            report_contract=None)
        task.checkpoint = lambda: None
        saved, executions, receipts, projections = {}, [], [], []

        async def execute(source, name, arguments, **kwargs):
            executions.append(kwargs['operation_key'])
            return await binding.execute(context, name, arguments, kwargs['operation_key'])

        async def unchanged_score(source, index, result):
            assert not hasattr(binding, 'automatic_score_judgments')
            return result

        def credit(source):
            value = binding.credit_view(context, None)
            projections.append(value)
            return value

        task.workflow = SimpleNamespace(
            run_id=context.run_id, execution_binding=None, inprocess_replay=None,
            pending_work=lambda source: {'version': 'pending_work_v2', 'captured_at': '2026-11-01T00:00:00+00:00', 'items': []},
            journal=SimpleNamespace(row=lambda table, episode, index: saved.get(index),
                save=lambda table, row: saved.__setitem__(row['decision_index'], deepcopy(row)),
                measure=lambda *args: nullcontext()), execute=execute,
            receive_native_outcome=lambda *args: None,
            receive_outcome=lambda source, selection, result, index: receipts.append((index, result['status'])),
            automatic_score_updates=unchanged_score, source_credit_view=credit,
            controller_value=lambda source, index, credit: {'index': index, 'credit': credit})
        return task, binding, context, runtime, c, saved, executions, receipts, projections

    def test_actual_multistep_work_credit_and_replay(self, tmp_path):
        task, binding, context, runtime, c, saved, executions, receipts, projections = self.task_fixture(tmp_path)
        fit = {'kind': 'tool', 'tool': 'hpc.model.fit',
               'arguments': {'training_ids': [row['id'] for row in c['history'][:6]]}}
        first = asyncio.run(task.execute(fit, 0))
        assert first['credit'] > 0
        invalid = {'kind': 'tool', 'tool': 'hpc.read', 'arguments': {'reference': 'missing'}}
        second = asyncio.run(task.execute(invalid, 1))
        assert second['credit'] == first['credit']
        assert task.last_outcome['status'] == 'invalid'
        assert runtime.observes_action_outcome('tool', 'invalid')
        assert asyncio.run(task.execute(fit, 0)) == first
        assert asyncio.run(task.execute(invalid, 1)) == second
        assert executions == ['test-run:prediction:0', 'test-run:prediction:1']
        assert receipts == [(0, 'completed'), (1, 'invalid')]
        assert len(projections) == 2
        assert json.loads(saved[1]['action']) == invalid
        assert json.loads(saved[1]['result'])['feedback']['code'] == 'unknown_hpc_evidence:missing'
        assert len(binding.state(context).records('model_choice')) == 1

    @pytest.mark.parametrize('status', ['failed', 'unavailable'])
    def test_returned_operational_failure_enters_original_progress(self, tmp_path, status):
        task, binding, context, runtime, _, saved, executions, receipts, projections = self.task_fixture(tmp_path)
        async def execute(source, name, arguments, **kwargs):
            executions.append(kwargs['operation_key'])
            return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'feedback': {'code': 'controlled_acquisition_failure'}}
        task.workflow.execute = execute
        selected = {'kind': 'tool', 'tool': 'hpc.queue.observe', 'arguments': {}}
        assert asyncio.run(task.execute(selected, 3)) == {'index': 3, 'credit': 0}
        assert asyncio.run(task.execute(selected, 3)) == {'index': 3, 'credit': 0}
        assert executions == ['test-run:prediction:3'] and receipts == [(3, status)]
        assert len(projections) == 1 and runtime.observes_action_outcome('tool', status)
        assert json.loads(saved[3]['result'])['status'] == status

    @pytest.mark.parametrize('selection', [
        {'kind': 'reason', 'commit': {}},
        {'kind': 'wait', 'condition': {}},
        {'kind': 'episode_child', 'role': 'launch', 'assignment': {}}])
    def test_unavailable_work_is_rejected_before_acquisition(self, tmp_path, selection):
        task, binding, context, runtime, *_ = self.task_fixture(tmp_path)
        effects = []
        task.record_effect = lambda index, state: effects.append((index, state))
        task.workflow.decision_exchanges = None
        task.workflow.permits_common_action = lambda source, kind: kind in binding.permitted_common_actions(context)
        task.workflow.selected = lambda *args: pytest.fail('Unavailable selection acquired a unit')
        schema = runtime._object({'selection': runtime._object({'kind': {'const': 'tool'},
            'tool': {'const': 'hpc.read'}, 'arguments': runtime._object({'reference': {'type': 'string'}})}),
            'report_update': runtime._object({})})
        assert task.apply_response({'selection': selection, 'report_update': {}}, 0, {}, schema) is None
        assert effects == [(0, 'rejected')] and task.feedback['status'] == 'invalid'

    def test_decision_summary_preserves_goal_model_and_actual_outcome(self, tmp_path):
        task, binding, context, runtime, c, *_ = self.task_fixture(tmp_path)
        previous = {'status': 'invalid', 'record_refs': [], 'feedback': {'code': 'unknown_model'}}
        task.last_outcome, task.last_outcome_index, task.feedback = previous, 2, previous['feedback']
        journal = SimpleNamespace(row=lambda *args: None, elapsed_view=lambda *args: {'elapsed_seconds': 7},
            db=SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: None)))
        task.workflow = SimpleNamespace(run_id='test-run', inprocess_replay=None, execution_binding=None,
            journal=journal, store=SimpleNamespace(read_snapshot=nullcontext, get=lambda ref: None),
            working_state=lambda source: {'records': []}, local_outcome_preview=lambda outcome, **kwargs: deepcopy(outcome),
            source_credit_view=lambda source: binding.credit_view(context, None), receipt_projection=lambda source: False,
            source_credit_binding=lambda source: {'kind': 'hpc_prediction'}, pending_work=lambda source: [],
            delivery_status=lambda episode: [], controller_binding={}, catalog=lambda *args, **kwargs: binding.catalog(context),
            knowledge=SimpleNamespace(context=lambda: {}), job_episode_options=lambda source: [],
            extra_report_sources=lambda source: binding.fact_sources(context.role), specialist=lambda source: binding,
            binding_context=lambda source: context, tools=object(), action_schema=lambda source: {},
            is_scientific_source=lambda source: False)
        shown, unit = [], object()
        async def call(state, schema):
            index = task.calls
            task.calls += 1
            shown.append(deepcopy(state))
            return {}, index, state, schema
        task.call, task.apply_response = call, lambda *args: unit
        view = SimpleNamespace(units_consumed=0, controller_state={}, child_reports=(),
                               model_inputs=lambda state, **kwargs: state)
        assert asyncio.run(task.next(view)) is unit
        state = shown[0]
        assert state['goal']['objective'] == c['objective']
        assert state['hpc_model_ref'] == 'reference_model'
        assert state['current_credit'] == 0 and state['hpc_credit'] == binding.credit_view(context, None)
        assert state['last_local_outcome'] == previous
        assert state['feedback'] == previous['feedback']
        assert state['hpc_available_training_ids'] == ['measurement-' + str(i) for i in range(1, 7)]

    def test_fresh_decision_keeps_prediction_history_and_exact_saved_input(self, tmp_path, monkeypatch):
        task, binding, context, runtime, _, *_ = self.task_fixture(tmp_path)
        work_report = self.module('episode_work_report')
        monkeypatch.setattr(work_report, 'completed_action_reports', lambda *args, **kwargs: {'actual_attempts': []})
        monkeypatch.setattr(work_report, 'requested_action_history', lambda *args, **kwargs: [{'tool': 'hpc.read', 'status': 'invalid'}])
        saved, sent = [], []
        response = {'selection': {'kind': 'tool', 'tool': 'hpc.read', 'arguments': {'reference': 'reference_model'}}, 'report_update': {}}
        async def complete(*args):
            sent.append(args)
            return deepcopy(response)
        task.workflow = SimpleNamespace(journal=SimpleNamespace(row=lambda *args: None,
            save=lambda table, row: saved.append((table, deepcopy(row))), measure=lambda *args: nullcontext()),
            contract_information_profile=lambda source: None, resource_context=lambda source: None,
            shared_information_context=lambda source: None,
            launch_instructions=SimpleNamespace(context=lambda: {}, materialize=lambda supplied: None, instructions=''),
            available_child_roles=lambda source: (), episode_bindings=SimpleNamespace(initial_decision_context=lambda context: {}),
            binding_context=lambda source: context, specialist=lambda source: binding, is_job_source=lambda source: False,
            execution_expectations=None, resource_estimator=None, native_estimation_context=lambda *args: None,
            native_event_information=None, permits_common_action=lambda source, kind: False,
            freeze_literature_numerical_contracts=lambda *args: None, decision_protocol=None, receipts=None,
            provider=SimpleNamespace(has_session=lambda *args: True, complete=complete),
            services=SimpleNamespace(instructions=lambda source, state: binding.instructions(context)))
        state = {**binding.decision_context(context, {}), 'current_credit': 0, 'visible_record_refs': [], 'pending_work': []}
        schema = runtime._object({'selection': runtime._object({'kind': {'const': 'tool'},
            'tool': {'const': 'hpc.read'}, 'arguments': runtime._object({'reference': {'type': 'string'}})}),
            'report_update': runtime._object({})})
        actual, index, shown, original = asyncio.run(task.call(state, schema))
        assert (actual, index, original) == (response, 0, schema)
        assert len(sent) == 1 and sent[0][2] == binding.instructions(context)
        assert shown['hpc_model_ref'] == 'reference_model'
        assert shown['requested_action_history'] == [{'tool': 'hpc.read', 'status': 'invalid'}]
        assert json.loads(saved[-1][1]['request'])['context'] == shown
        assert json.loads(saved[-1][1]['response']) == response
