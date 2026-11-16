"""Private planning/allocation task dispatch, outcomes and original child/wait paths."""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from .hpc_planning_allocation_behavior import PlanningAllocationBehavior
from .hpc_prediction_inputs import recorded_queue


class PlanningAllocationTaskBehavior:
    module = PlanningAllocationBehavior.module
    setup = PlanningAllocationBehavior.setup

    def fixture(self, tmp_path):
        value = self.setup(tmp_path)
        binding, context = value.binding, value.context
        runtime = self.module('runtime')
        task_type = getattr(binding, 'decision_source_type', runtime.DecisionSource)
        task = object.__new__(task_type)
        task.episode_id, task.path, task.scope = context.episode_id, context.path, runtime._plain(context.scope)
        task.calls = 0
        task._execution_context = task._delivery_resolution_ref = None
        task.report_values, task.report_basis = {}, []
        task.interpret_schema = runtime._object({})
        task.last_outcome = task.last_outcome_index = task.feedback = None
        task.request = SimpleNamespace(goal=SimpleNamespace(as_record=lambda: {'objective': value.c['objective']}),
            message=SimpleNamespace(as_record=lambda: {'episode_assignment': context.assignment}), report_contract=None)
        task.checkpoint = lambda: None
        saved, executions, receipts, projections = {}, [], [], []
        async def execute(source, name, arguments, **kwargs):
            executions.append(kwargs['operation_key'])
            return await binding.execute(context, name, arguments, kwargs['operation_key'])
        async def unchanged_score(source, index, result):
            assert not hasattr(binding, 'automatic_score_judgments')
            return result
        def credit(source):
            result = binding.credit_view(context, None)
            projections.append(result)
            return result
        task.workflow = SimpleNamespace(run_id=context.run_id, execution_binding=None, inprocess_replay=None,
            pending_work=lambda source: {'version': 'pending_work_v2', 'captured_at': '2026-11-01T00:00:00+00:00', 'items': []},
            journal=SimpleNamespace(row=lambda table, episode, index=None: saved.get(index),
                save=lambda table, row: saved.__setitem__(row['decision_index'], deepcopy(row)), measure=lambda *args: nullcontext()),
            execute=execute, receive_native_outcome=lambda *args: None,
            receive_outcome=lambda source, selection, result, index: receipts.append((index, result['status'])),
            automatic_score_updates=unchanged_score, source_credit_view=credit,
            controller_value=lambda source, index, credit: {'index': index, 'credit': credit})
        return SimpleNamespace(value=value, task=task, runtime=runtime, saved=saved, executions=executions, receipts=receipts, projections=projections)

    def test_original_runtime_build_selects_this_binding_task(self, tmp_path, monkeypatch):
        v = self.setup(tmp_path)
        runtime = self.module('runtime')
        registry = self.module('episode_bindings').EpisodeBindingRegistry((v.binding,))
        monkeypatch.setattr(runtime.Episode, 'identity', lambda *a, **k: SimpleNamespace(episode_id=v.context.episode_id))
        monkeypatch.setattr(runtime, 'FeedbackEpisode', lambda grain, key, source, *a, **k: source)
        workflow = SimpleNamespace(context=object(), grains={self.role: object()},
            inprocess_completion_order=None, receipts=None, scientific_process_binding=None,
            episode_bindings=registry, contract_information_profile=lambda source: None,
            specialist=lambda source: v.binding, binding_context=lambda source: v.context,
            journal=SimpleNamespace(row=lambda *a: None, save=lambda *a: None), run_id='test-run',
            store=SimpleNamespace(transaction=nullcontext, db=SimpleNamespace(execute=lambda *a: None)),
            source_credit_view=lambda source: v.binding.credit_view(v.context, None),
            expose_assigned_job=lambda source: None, receive_tool_attributions=lambda *a, **k: None,
            archive=SimpleNamespace(store=lambda value: value), launch_instructions=SimpleNamespace(materialize=lambda value: None))
        # a103's Workflow.build reads self.legacy_parent_for_path (a103/runtime.py); bind the real method.
        # Selected by the runtime module, not self.axis: launch tests pass an adapter without an axis.
        if runtime.__name__ == 'gene_annotation_episode.episodic_workflow.root.a103.runtime':
            workflow.legacy_parent_for_path = lambda path: runtime.Workflow.legacy_parent_for_path(workflow, path)
        selected = runtime.Workflow.build(workflow, self.role, 'original-work', v.c['objective'],
            runtime._plain(v.context.scope), episode_assignment=runtime._plain(v.context.assignment))
        assert type(selected) is getattr(v.binding, 'decision_source_type', runtime.DecisionSource)
        assert selected.episode_id == v.context.episode_id
        if hasattr(v.binding, 'decision_source_type'):
            assert not isinstance(selected, runtime.DecisionSource)

    def test_actual_plan_invalid_outcome_and_completed_replay(self, tmp_path):
        f = self.fixture(tmp_path)
        q = f.value.ledger.put('queue', {'snapshot': recorded_queue(self.module('hpc_queue'))})
        plan = {'kind': 'tool', 'tool': 'hpc.plan', 'arguments': {'candidate_id': f.value.c['candidates'][0]['id'], 'model_ref': 'reference_model', 'queue_ref': q}}
        invalid = {'kind': 'tool', 'tool': 'hpc.read', 'arguments': {'reference': 'missing'}}
        for index, selection in enumerate((plan, invalid)):
            actual = asyncio.run(f.task.execute(selection, index))
            assert actual == {'index': index, 'credit': 0}
            assert asyncio.run(f.task.execute(selection, index)) == actual
        assert f.executions == [f'test-run:{f.task.episode_id}:{i}' for i in (0, 1)]
        assert f.receipts == [(0, 'completed'), (1, 'invalid')]
        assert len(f.projections) == 2 and len(f.value.ledger.records('plan')) == 1
        assert json.loads(f.saved[1]['action']) == invalid
        assert f.runtime.observes_action_outcome('tool', 'invalid')
        assert f.task.last_outcome['feedback']['code'] == 'unknown_hpc_evidence:missing'

    @pytest.mark.parametrize('status', ['failed', 'unavailable'])
    def test_returned_failure_keeps_original_progress_observation(self, tmp_path, status):
        f = self.fixture(tmp_path)
        async def execute(source, name, arguments, **kwargs):
            f.executions.append(kwargs['operation_key'])
            return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'feedback': {'code': 'controlled_failure'}}
        f.task.workflow.execute = execute
        selected = {'kind': 'tool', 'tool': 'hpc.queue.observe', 'arguments': {}}
        assert asyncio.run(f.task.execute(selected, 3)) == {'index': 3, 'credit': 0}
        assert asyncio.run(f.task.execute(selected, 3)) == {'index': 3, 'credit': 0}
        assert f.executions == [f'test-run:{f.task.episode_id}:3'] and f.receipts == [(3, status)]
        assert f.runtime.observes_action_outcome('tool', status) and len(f.projections) == 1
        assert json.loads(f.saved[3]['result'])['status'] == status

    def test_selected_wait_preserves_prior_credit_without_projection_or_repetition(self, tmp_path):
        f = self.fixture(tmp_path)
        f.value.ledger.accept('original-work', f.value.ledger.put('result', {'accepted': True}))
        calls = []
        async def wait(source, condition, index):
            calls.append((deepcopy(condition), index))
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': {'ready': True}}
        f.task.workflow.perform_selected_wait = wait
        f.task.workflow.last_observed_credit = lambda source: 10.
        selected = {'kind': 'wait', 'condition': {'original': 'condition'}}
        assert asyncio.run(f.task.execute(selected, 2)) == {'index': 2, 'credit': 10.}
        assert asyncio.run(f.task.execute(selected, 2)) == {'index': 2, 'credit': 10.}
        assert calls == [(selected['condition'], 2)] and f.executions == [] and f.projections == []
        assert f.receipts == [(2, 'completed')]
        assert f.value.binding.credit_view(f.value.context, None)['credit'] == 10.

    def test_ready_original_child_is_collected_before_another_decision(self, tmp_path):
        f = self.fixture(tmp_path)
        child, called = object(), []
        f.task._execution_context = SimpleNamespace(_ready_owned_child=lambda path: called.append(path) or child)
        view = SimpleNamespace(units_consumed=0)
        assert asyncio.run(f.task.next(view)) is child
        assert called == [f.task.path] and f.task.calls == 0 and f.executions == []

    def test_redelivery_rejects_changed_interpretation_before_acquisition(self, tmp_path):
        f = self.fixture(tmp_path)
        task, runtime = f.task, f.runtime
        task._delivery_resolution_ref = 'original-delivery'
        task.report_values = {'existing': 'kept'}
        effects = []
        task.record_effect = lambda index, state: effects.append((index, state))
        task.workflow.decision_exchanges = None
        task.workflow.permits_common_action = lambda *a: False
        task.workflow.selected = lambda *a: pytest.fail('Altered repair acquired a unit')
        schema = runtime._object({'selection': runtime._object({'kind': {'const': 'redeliver_report'}}),
            'report_update': runtime._object({'existing': {'type': 'string'}})})
        response = {'selection': {'kind': 'redeliver_report'}, 'report_update': {'existing': 'changed'}}
        assert task.apply_response(response, 0, {'visible_record_refs': []}, schema) is None
        assert effects == [(0, 'rejected')]
        assert task.feedback['detail'] == 'delivery_resolution_must_preserve_current_interpretation'
        assert task.report_values == {'existing': 'kept'}

    @pytest.mark.parametrize('knowledge,launch,native', [(False, False, False), (True, False, False), (False, True, True), (True, True, True)])
    def test_private_instructions_preserve_goal_selected_libraries_and_wait_guidance(self, tmp_path, knowledge, launch, native):
        f = self.fixture(tmp_path)
        runtime_prompt = self.module('runtime_prompt')
        task = f.task
        task.workflow.specialist = lambda source: f.value.binding
        task.workflow.binding_context = lambda source: f.value.context
        task.workflow.is_job_source = lambda source: False
        task.workflow.permits_common_action = lambda source, action: action in f.value.binding.permitted_common_actions(f.value.context)
        task.workflow.knowledge = SimpleNamespace(instructions='\nSelected knowledge.')
        task.workflow.launch_instructions = SimpleNamespace(instructions='\nSelected Launch instructions.')
        task.workflow.native_event_information = object() if native else None
        task.workflow.decision_protocol = None
        task.workflow.services = SimpleNamespace(instructions=runtime_prompt.instructions)
        context = {**({'tool_knowledge': {}} if knowledge else {}), **({'launch_instruction_library': {}} if launch else {})}
        assert task.instructions(context) == runtime_prompt.instructions(task, context)
        assert 'pending_child_delivery' in task.instructions(context)
        assert 'pending_child_' in task.instructions(context)
        if self.role == 'hpc_execution':
            assert 'Commission hpc_prediction only' not in task.instructions(context)

    @pytest.mark.parametrize('protocol', [None, 'decision_exchange_v1'])
    @pytest.mark.parametrize('declared', [False, True])
    def test_private_decision_dispatch_saved_replay_and_selected_presentation(self, tmp_path, protocol, declared):
        from .hpc_prediction_parent_exchange import PredictionReceiptDatabase
        f = self.fixture(tmp_path)
        task, binding, runtime = f.task, f.value.binding, f.runtime
        database = PredictionReceiptDatabase(tmp_path/'decision-journal.sqlite')
        journal = self.module('episode_journal').Journal(database, 'run')
        self.module('episode_completion').CompletionLedger(database, journal)
        exchanges = self.module('decision_exchanges').DecisionExchanges(journal)
        task.calls = 0
        task._model_snapshot = task._presented_conversation_key = None
        task.decision_inputs = lambda context, index, profile: context
        task.workflow.run_id = 'run'
        task.workflow.store = database
        task.workflow.journal = journal
        task.workflow.decision_exchanges = exchanges
        task.workflow.controller_binding = {}
        task.workflow.decision_protocol = protocol
        task.workflow.contract_information_profile = lambda source: None
        task.workflow.receipts = None
        task.workflow.available_child_roles = lambda source: ()
        task.workflow.scientific_library_available = lambda source: False
        task.workflow.specialist = lambda source: binding
        task.workflow.binding_context = lambda source: f.value.context
        task.workflow.is_job_source = lambda source: False
        task.workflow.permits_common_action = lambda source, action: action in binding.permitted_common_actions(f.value.context)
        task.workflow.native_event_information = None
        task.workflow.knowledge = SimpleNamespace(instructions='Selected knowledge.')
        task.workflow.launch_instructions = SimpleNamespace(instructions='Selected launch instructions.')
        if self.axis in ('a102', 'a103', 'a104'):
            task.workflow.services = self.module('episode_services').WorkflowServices(task.workflow)
        else:
            task.workflow.services = SimpleNamespace(
                instructions=lambda *args: pytest.fail('Private task selected axis instruction composer'),
                decision_exchange_instructions=lambda: self.module('decision_context').INSTRUCTIONS)
        state = {'hpc_commission': {'objective': f.value.c['objective']}, 'hpc_model_ref': 'model-original'}
        selection = {'kind': 'tool', 'tool': 'hpc.read', 'arguments': {'reference': 'model-original'}}
        response = {'selection': selection, 'report_update': {}}
        wire = {'response': {'response_type': 'select_action', **response}} if protocol else response
        calls = []
        async def complete(*args, **kwargs):
            calls.append((args, kwargs))
            return wire
        if declared and self.axis == 'a104':
            controlled = self.module('tests.provider_dispatch_fixtures')
            task.workflow.provider = controlled.controlled_serial_model(
                controlled.controlled_config(), tmp_path / 'controlled-provider', tmp_path, complete)
            task.workflow.provider.has_session = lambda *args: True
        elif declared:
            task.workflow.provider = SimpleNamespace(has_session=lambda *args: True,
                complete_with_presentation=complete, complete=lambda *args: pytest.fail('Private renderer was omitted'))
        else:
            task.workflow.provider = SimpleNamespace(has_session=lambda *args: True, complete=complete)
        schema = runtime._object({'selection': runtime._object({'kind': {'const': 'tool'},
            'tool': {'const': 'hpc.read'}, 'arguments': runtime._object({'reference': {'type': 'string'}})}),
            'report_update': runtime._object({})})
        try:
            assert asyncio.run(task.call(state, schema))[0] == response
            assert len(calls) == 1 and calls[0][0][:2] == (task.episode_id, 'REASONING')
            assert calls[0][1] == ({'prompt_renderer': binding.decision_prompt_renderer} if declared else {})
            presented = calls[0][0][3]
            if protocol:
                presented = runtime.apply_state_frame(None, presented)
                assert exchanges.rows(task.episode_id, 0)[0]['request']['instructions'] == calls[0][0][2]
            assert presented['hpc_model_ref'] == 'model-original'
            assert calls[0][0][2].startswith(binding.instructions(f.value.context))
            assert 'pending_child_delivery' in calls[0][0][2]
            saved = journal.row('runtime_model_calls', task.episode_id, 0)
            assert json.loads(saved['response']) == response
            task.calls = 0
            assert asyncio.run(task.call(state, schema))[0] == response and len(calls) == 1
            assert database.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        finally:
            database.db.close()
