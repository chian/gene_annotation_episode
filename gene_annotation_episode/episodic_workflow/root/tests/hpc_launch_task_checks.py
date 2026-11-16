"""Private Launch task and message checks using retained HPC contracts/assets.

Actual Store, Journal, plan, binding and runtime boundaries use controlled
provider, child-construction and receipt ports; no native job is executed.
"""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import commission, resources, recorded_queue
from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior


class LaunchTaskChecks:
    role = 'launch'

    def module(self, name):
        return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+self.axis+'.'+name.replace('/', '.'))

    @pytest.fixture
    def launch_case(self, tmp_path):
        parent_home = self.binding_path.rsplit('/', 1)[0]
        owner_home = parent_home.removesuffix('/hpc_allocation_execution')
        c, r = commission(), resources()
        run_id = 'test-run'
        Context = self.module('episode_bindings').BindingContext
        EpisodeRef = self.module('method_loop.identities').EpisodeRef
        services = SimpleNamespace(annotation_task_required=lambda: False)
        with self.module('state').Store(tmp_path/'store') as store:
            problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
            scope = {'subject_refs': problem['subject_refs']}
            journal = self.module('episode_journal').Journal(store, run_id)
            options = dict(store=store, run_id=run_id, directory=tmp_path,
                resources=r, commissions={'commission': c})
            owner_binding = self.module(owner_home+'/episode').HPCEpisode(services, **options)
            path = ((('scientific_process', 'science'),) if owner_home.startswith('scientific_process/')
                    else (('annotation', 'root'),))+(('hpc', 'parent'),)
            owner = Context(run_id, EpisodeRef(run_id, path).episode_id, 'hpc', path,
                scope, {'commission_id': 'commission'}, {})
            owner_binding.initialize(owner)
            if parent_home == owner_home:
                parent, parent_context = owner_binding, owner
            else:
                parent = self.module(parent_home+'/episode').HPCEpisode(services, **options)
                child_path = path+(('hpc_execution', 'allocation'),)
                parent_context = replace(owner, role='hpc_execution', path=child_path,
                    episode_id=EpisodeRef(run_id, child_path).episode_id,
                    assignment={'commission_id': 'commission', 'owner_episode_id': owner.episode_id})
                parent.initialize(parent_context)
            ledger = parent.state(parent_context)
            qref = ledger.put('queue', {'snapshot': recorded_queue(self.module('hpc_queue'))})
            outcome = asyncio.run(parent.execute(parent_context, 'hpc.plan',
                {'candidate_id': c['candidates'][0]['id'], 'model_ref': 'reference_model',
                 'queue_ref': qref}, 'original-launch-test-plan'))
            assert outcome['status'] == 'completed'
            plan = ledger.read(outcome['result']['plan_ref'])
            execution_options = dict(store=store, run_id=run_id, directory=tmp_path,
                resources=r, initial_information={}, tool_registry=None,
                handoff_unit=1., acquired_record_unit=1., log_window_bytes=1024,
                log_roles=('stdout', 'stderr'))
            binding = self.module(self.binding_path+'/episode').ExecutionEpisode(services, **execution_options)
            native = self.module(self.binding_path+'/hpc_job_execution/episode').ExecutionEpisode(services, **execution_options)
            launch_path = parent_context.path+(('launch', 'child_3'),)
            context = replace(parent_context, role='launch', path=launch_path,
                episode_id=EpisodeRef(run_id, launch_path).episode_id,
                assignment=plan['launch_assignment'])
            request = {'message': {'scope': dict(context.scope), 'episode_assignment': plan['launch_assignment']}}
            context = replace(context, request=request)
            runtime = self.module('runtime')
            for item in (owner, parent_context, context):
                journal.save('runtime_episodes', {'episode_id': item.episode_id,
                    'path': runtime._json(item.path), 'request': runtime._json(item.request),
                    'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
            value = SimpleNamespace(c=c, parent=parent, parent_context=parent_context,
                owner=owner, owner_binding=owner_binding, binding=binding, context=context,
                native=native, plan=plan, ledger=ledger, store=store, journal=journal,
                execution_options=execution_options, services=services)
            yield value

    def task_case(self, value, tmp_path):
        # Reuse the existing iterator/recording fixture with this real Launch
        # binding and context; no copy of a different binding's implementation.
        adapter = SimpleNamespace(setup=lambda path: value, module=self.module)
        return PlanningAllocationTaskBehavior.fixture(adapter, tmp_path)

    def case_registry(self, value):
        bindings = [value.owner_binding]
        if value.parent is not value.owner_binding:
            bindings.append(value.parent)
        if self.binding_path.startswith('scientific_process/'):
            bindings.insert(0, self.module('scientific_process.episode').ScientificProcessEpisode(
                SimpleNamespace(protein_structure_reference_access=lambda *args: None),
                library=SimpleNamespace(as_record=lambda: {}, headers=lambda: []),
                tool_library=SimpleNamespace(as_record=lambda: {}),
                child_roles=('scientific_process', 'hpc')))
        bindings.extend((value.binding, value.native))
        return self.module('episode_bindings').EpisodeBindingRegistry(bindings)

    @pytest.fixture
    def launch_exchange(self, launch_case, monkeypatch):
        value, runtime = launch_case, self.module('runtime')
        EpisodeRef = self.module('method_loop.identities').EpisodeRef
        path = value.context.path+(('launch_hpc', 'child_3'),)
        assignment = value.native.prepare_assignment(value.context, 'launch_hpc',
            deepcopy(value.plan['practical_assignment']), value.context.scope, 'native-original')
        context = replace(value.context, role='launch_hpc', path=path,
            episode_id=EpisodeRef(value.context.run_id, path).episode_id, assignment=assignment,
            request={'message': {'scope': runtime._plain(value.context.scope), 'episode_assignment': assignment}})
        value.journal.save('runtime_episodes', {'episode_id': context.episode_id,
            'path': runtime._json(path), 'request': runtime._json(context.request),
            'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        value.native.initialize(context)
        definitions = value.native.fact_sources('launch_hpc')
        schema = runtime._object({'handoffs': deepcopy(definitions['execution_handoff_refs']['report_schema']),
            'completed': {'type': 'boolean', 'x-source': 'execution_completed'}})
        facts = value.native.facts(context, {})
        form = {'handoffs': facts['execution_handoff_refs'], 'completed': facts['execution_completed']}
        value.native.validate_report(context, form, schema)
        value.journal.save('runtime_forms', {'episode_id': context.episode_id,
            'facts': runtime._json(facts), 'form': runtime._json(form)})
        registry = self.case_registry(value)
        receipts, progress, attributions, cache_reads = [], [], [], []
        cache = {'references': None}
        def recorded(records, context, admitted, contract, index):
            cache_reads.append(index)
            return cache['references']
        monkeypatch.setattr(self.module('episode_return_records').EpisodeReturnRecords,
                            'recorded_admission_references', recorded)
        source = SimpleNamespace(episode_id=value.context.episode_id, path=value.context.path,
            scope=runtime._plain(value.context.scope), _delivery_resolution_ref=None)
        workflow = SimpleNamespace(store=value.store, journal=value.journal, run_id=value.context.run_id,
            receipts=SimpleNamespace(receive=lambda *args, **kwargs: receipts.append((args, kwargs))),
            progress_provider=SimpleNamespace(receive_form=lambda *args: progress.append(args)),
            specialist=lambda current: value.binding, binding_context=lambda current: value.context,
            is_job_source=lambda current: False, episode_bindings=registry,
            native_timing_information=None, job_episodes=None,
            receive_tool_attributions=lambda *args, **kwargs: attributions.append((args[1], kwargs)) or [])
        def save_attempt(index, *, child_id=None, redelivery=False):
            action = ({'kind': 'redeliver_report', 'delivery_ref': 'original-native-delivery'}
                if redelivery else {'kind': 'episode_child', 'role': 'launch_hpc'})
            value.journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': index, 'action': runtime._json(action), 'result': None, 'credit': None})
            value.journal.save('runtime_report_attempts', {'parent_episode_id': source.episode_id,
                'decision_index': index, 'delivery_ref': 'original-native-delivery',
                'child_episode_id': child_id or context.episode_id, 'contract': '{}',
                'form': runtime._json(form), 'failure': None})
        save_attempt(3)
        return SimpleNamespace(value=value, runtime=runtime, native_context=context, schema=schema,
            form=form, source=source, workflow=workflow, receipts=receipts, progress=progress,
            attributions=attributions, cache=cache, cache_reads=cache_reads, save_attempt=save_attempt)

    def test_actual_runtime_build_selects_private_launch_task(self, launch_case, tmp_path, monkeypatch):
        adapter = SimpleNamespace(setup=lambda path: launch_case, module=self.module, role='launch')
        PlanningAllocationTaskBehavior.test_original_runtime_build_selects_this_binding_task(adapter, tmp_path, monkeypatch)

    def test_returned_outcomes_and_saved_replay_preserve_actual_payload(self, launch_case, tmp_path):
        f = self.task_case(launch_case, tmp_path)
        tool = launch_case.binding.catalog(launch_case.context)[0]['name']
        for index, arguments in enumerate(({}, {'unrequested': True})):
            selection = {'kind': 'tool', 'tool': tool, 'arguments': arguments}
            value = asyncio.run(f.task.execute(selection, index))
            assert asyncio.run(f.task.execute(selection, index)) == value
            assert json.loads(f.saved[index]['action']) == selection
            result = json.loads(f.saved[index]['result'])
            assert result['status'] == ('completed' if index == 0 else 'invalid')
            assert f.runtime.observes_action_outcome('tool', result['status'])
            assert f.task.last_outcome == result
        assert len(f.executions) == len(f.receipts) == len(f.projections) == 2
        assert f.receipts == [(0, 'completed'), (1, 'invalid')]

    @pytest.mark.parametrize('status', ('failed', 'unavailable'))
    def test_returned_failure_keeps_one_original_observation(self, launch_case, tmp_path, status):
        f = self.task_case(launch_case, tmp_path)
        payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
                   'result': {'original_resource': launch_case.plan['practical_assignment']['resource_id']},
                   'feedback': {'code': 'controlled_execution_failure'}}
        async def execute(source, name, arguments, **kwargs):
            f.executions.append(kwargs['operation_key'])
            return deepcopy(payload)
        f.task.workflow.execute = execute
        selected = {'kind': 'tool', 'tool': launch_case.binding.catalog(launch_case.context)[0]['name'], 'arguments': {}}
        actual = asyncio.run(f.task.execute(selected, 4))
        assert asyncio.run(f.task.execute(selected, 4)) == actual
        assert json.loads(f.saved[4]['result']) == {**payload,
            'pending_work_after_action': f.task.workflow.pending_work(f.task)}
        assert f.receipts == [(4, status)] and len(f.executions) == len(f.projections) == 1

    def test_pending_original_child_and_changed_redelivery(self, launch_case, tmp_path):
        f = self.task_case(launch_case, tmp_path)
        adapter = SimpleNamespace(fixture=lambda path: f)
        PlanningAllocationTaskBehavior.test_ready_original_child_is_collected_before_another_decision(adapter, tmp_path)
        PlanningAllocationTaskBehavior.test_redelivery_rejects_changed_interpretation_before_acquisition(adapter, tmp_path)

    def test_original_launch_actions_keep_wait_with_hpc_parent(self, launch_case):
        assert launch_case.binding.permitted_common_actions(launch_case.context) == ('tool', 'child', 'redeliver_report')
        assert 'wait' in launch_case.parent.permitted_common_actions(launch_case.parent_context)
        assert launch_case.binding.binding_path == self.binding_path

    @pytest.mark.parametrize('kind', ('wait', 'reason'))
    @pytest.mark.parametrize('status', ('completed', 'failed'))
    def test_original_saved_action_keeps_result_and_credit_outside_fresh_schema(self, launch_case, tmp_path, kind, status):
        f = self.task_case(launch_case, tmp_path)
        selected = ({'kind': 'wait', 'condition': {'original_condition': 'retained'}} if kind == 'wait'
            else {'kind': 'reason', 'commit': {'original_commit': 'retained'}})
        payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'result': {'original_saved_outcome': kind}, 'feedback': None,
            'pending_work_after_action': f.task.workflow.pending_work(f.task)}
        f.saved[9] = {'episode_id': f.task.episode_id, 'decision_index': 9,
            'action': f.runtime._json(selected), 'result': f.runtime._json(payload), 'credit': 7.25}
        assert kind not in launch_case.binding.permitted_common_actions(launch_case.context)
        if kind == 'wait' and status == 'failed':
            with pytest.raises(f.runtime.ActionFailure):
                asyncio.run(f.task.execute(selected, 9))
        else:
            assert asyncio.run(f.task.execute(selected, 9)) == {'index': 9, 'credit': 7.25}
        assert json.loads(f.saved[9]['action']) == selected
        assert json.loads(f.saved[9]['result']) == payload
        assert f.executions == f.receipts == f.projections == []

    def test_original_unfinished_wait_returns_through_existing_outcome_path(self, launch_case, tmp_path):
        f = self.task_case(launch_case, tmp_path)
        selected = {'kind': 'wait', 'condition': {'original_condition': 'retained'}}
        f.saved[6] = {'episode_id': f.task.episode_id, 'decision_index': 6,
            'action': f.runtime._json(selected), 'result': None, 'credit': None}
        waits = []
        async def wait(source, condition, index):
            waits.append((deepcopy(condition), index))
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                'result': {'original_condition_ready': True}}
        f.task.workflow.perform_selected_wait = wait
        f.task.workflow.last_observed_credit = lambda source: 4.5
        assert asyncio.run(f.task.execute(selected, 6)) == {'index': 6, 'credit': 4.5}
        assert asyncio.run(f.task.execute(selected, 6)) == {'index': 6, 'credit': 4.5}
        assert waits == [(selected['condition'], 6)]
        assert f.receipts == [(6, 'completed')] and f.executions == f.projections == []

    def test_named_native_request_preserves_original_hpc_plan(self, launch_case):
        value = launch_case
        original = deepcopy(value.plan['practical_assignment'])
        prepare = getattr(value.binding, 'prepare_child_request', None)
        prepared = original if prepare is None else prepare(value.context, 'launch_hpc', original)
        assert prepared == original and original == value.plan['practical_assignment']
        # This real admission retains the separately baselined singleton parent
        # contract failure until its explicit regression repair is integrated.
        admitted = value.native.prepare_assignment(value.context, 'launch_hpc', prepared,
            value.context.scope, 'original-native-request')
        assert admitted == original

    @pytest.mark.parametrize('child_name', ('api_job_execution', 'local_job_execution', 'hpc_job_execution'))
    def test_native_parent_contract_does_not_admit_parent_as_own_role(self, launch_case, child_name):
        value = launch_case
        child = self.module(self.binding_path+'/'+child_name+'/episode').ExecutionEpisode(
            value.services, **value.execution_options)
        assert child._launch(deepcopy(value.plan['launch_assignment'])) == value.plan['launch_assignment']
        with pytest.raises(ValueError, match='unknown_execution_episode_role'):
            child.assignment_schema('launch', internal=True)

    def test_runtime_commission_calls_launch_request_before_native_admission(self, launch_case, monkeypatch):
        value, runtime = launch_case, self.module('runtime')
        registry = self.case_registry(value)
        scope = runtime._plain(value.context.scope)
        source = SimpleNamespace(episode_id=value.context.episode_id, path=value.context.path,
            scope=scope, _delivery_resolution_ref=None,
            request=SimpleNamespace(goal=runtime.EpisodeGoal.root(objective=value.c['objective'], result_contract={})))
        selected = {'kind': 'episode_child', 'role': 'launch_hpc', 'scope': scope,
            'assignment': deepcopy(value.plan['practical_assignment']),
            'goal': 'Prepare the original frozen native job', 'purpose': 'Return its original receiving handle'}
        value.journal.save('runtime_actions', {'episode_id': source.episode_id,
            'decision_index': 3, 'action': runtime._json(selected), 'result': None, 'credit': None})
        events, built = [], []
        prepare = getattr(value.binding, 'prepare_child_request', None)
        if prepare is not None:
            def request(*args):
                events.append('parent_request')
                return prepare(*args)
            monkeypatch.setattr(value.binding, 'prepare_child_request', request)
        admit = value.native.prepare_assignment
        def admission(*args):
            events.append('child_admission')
            return admit(*args)
        monkeypatch.setattr(value.native, 'prepare_assignment', admission)
        EpisodeRef = self.module('method_loop.identities').EpisodeRef
        child_path = source.path + (('launch_hpc', 'child_3'),)
        child = SimpleNamespace(source=SimpleNamespace(
            episode_id=EpisodeRef(value.context.run_id, child_path).episode_id,
            path=child_path, scope=scope))
        child_context = None
        def build(*args, **kwargs):
            nonlocal child_context
            built.append((args, kwargs))
            child_context = replace(value.context, role='launch_hpc', path=child_path,
                episode_id=child.source.episode_id, assignment=kwargs['episode_assignment'],
                request={'message': {'scope': scope,
                    'episode_assignment': kwargs['episode_assignment']}})
            return child
        def binding_context(current):
            if current is source:
                return value.context
            assert current is child.source and child_context is not None
            return child_context
        def permits(current, action):
            if current is source:
                return action == 'child'
            return action in value.native.permitted_common_actions(binding_context(current))
        schema = runtime._object({'handoffs': deepcopy(value.native.fact_sources('launch_hpc')[
            'execution_handoff_refs']['report_schema'])})
        workflow = SimpleNamespace(store=value.store, journal=value.journal, run_id=value.context.run_id,
            episode_bindings=registry, specialist=lambda current: value.binding,
            binding_context=binding_context,
            annotation_child_roles=None, execution_binding=None, inprocess_replay=None,
            scientific_process_binding=None,
            validate_child_choice=lambda *args, **kwargs: None,
            permits_common_action=permits,
            _closed_child_commission=lambda *args: None,
            expanded_contract_form=lambda *args: (schema, None),
            child_initial_report_input=lambda *args: '{}',
            services=SimpleNamespace(capabilities=lambda: {}),
            launch_instructions=SimpleNamespace(materialize=lambda *args: None),
            build=build, resolver=lambda *args, **kwargs: lambda *args: True)
        monkeypatch.setattr(runtime, 'TimedChildUnit', lambda child, *args, **kwargs: child)
        assert runtime.Workflow.selected(workflow, source, selected, 3) is child
        assert events == (['parent_request', 'child_admission'] if prepare is not None else ['child_admission'])
        assert built[0][0][:3] == ('launch_hpc', 'child_3', selected['goal'])
        assert built[0][1]['episode_assignment'] == selected['assignment']
        assert built[0][1]['parent_path'] == value.context.path
        assert built[0][1]['contract'].schema == schema
        assert registry.for_path(child_context.path) is value.native
        assert child_context.role == 'launch_hpc'

    def test_typed_native_report_receipt_redelivery_keeps_original_credit(self, launch_exchange):
        v = launch_exchange
        assert v.form == {'handoffs': [], 'completed': False}
        with pytest.raises(ValueError, match='execution_report_disagrees_with_recorded_facts'):
            v.value.native.validate_report(v.native_context, {**v.form, 'completed': True}, v.schema)
        before = v.value.binding.credit_view(v.value.context, None)
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 3) == []
        v.save_attempt(7, redelivery=True)
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 7, redelivery=True) == []
        assert v.value.binding.credit_view(v.value.context, None) == before
        assert [kwargs for _, kwargs in v.receipts] == [
            {'kind': 'child_form', 'source_index': 3}, {'kind': 'report_redelivery', 'source_index': 7}]
        assert v.cache_reads == [3]
        assert [args[-1] for args in v.progress] == [
            f'{v.workflow.run_id}:{v.source.episode_id}:3:typed_form',
            f'{v.workflow.run_id}:{v.source.episode_id}:7:typed_form']

    def test_named_native_receipt_reuses_original_admission(self, launch_exchange, monkeypatch):
        v = launch_exchange
        receiver_for_role = getattr(v.value.binding, 'child_report_receiver', None)
        calls = []
        if receiver_for_role is not None:
            receiver = receiver_for_role('launch_hpc')
            def selected(role):
                assert role == 'launch_hpc'
                def receive(*args, **kwargs):
                    calls.append((args[4], kwargs))
                    return receiver(*args, **kwargs)
                return receive
            monkeypatch.setattr(v.value.binding, 'child_report_receiver', selected)
        v.cache['references'] = ['source_original_native_receipt']
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 3) == v.cache['references']
        assert v.receipts == v.progress == v.attributions == []
        assert calls == ([(3, {'redelivery': False})] if receiver_for_role is not None else [])

    def test_native_redelivery_rejects_different_original_launch(self, launch_exchange):
        v = launch_exchange
        changed = v.source.path[:-1]+(('launch', 'different-original-launch'), ('launch_hpc', 'child_3'))
        v.value.journal.save('runtime_episodes', {'episode_id': 'wrong-native-child',
            'path': v.runtime._json(changed), 'request': '{}', 'initial_credit': 0,
            'state': 'yielded', 'completion': None, 'archive': None})
        v.save_attempt(7, child_id='wrong-native-child', redelivery=True)
        with pytest.raises(v.runtime.WorkflowError, match='original_delivery_parent_conflict'):
            v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 7, redelivery=True)
        assert v.receipts == v.progress == []

    @pytest.mark.parametrize('field', ('resource_id', 'workspace', 'resource_kind'))
    def test_mutated_native_request_rejected_before_native_execution(self, launch_case, field):
        original = deepcopy(launch_case.plan['practical_assignment'])
        original[field] = '__changed_original_'+field+'__'
        prepare = getattr(launch_case.binding, 'prepare_child_request', None)
        with pytest.raises((ValueError, TypeError)):
            prepared = original if prepare is None else prepare(launch_case.context, 'launch_hpc', original)
            launch_case.native.prepare_assignment(launch_case.context, 'launch_hpc', prepared,
                launch_case.context.scope, 'changed-native-request')

    def test_dependent_descriptors_read_complete_final_launch_files(self, launch_case):
        first = launch_case.parent.as_record()
        assert first == launch_case.parent.as_record()
        assert launch_case.owner_binding.as_record()['configuration']['resources'] == resources()
        if hasattr(launch_case.binding, 'decision_source_type'):
            directory = Path(importlib.import_module(type(launch_case.binding).__module__).__file__).parent
            assert (directory/'task.py').is_file()
            assert (directory/'from_child_hpc_job_execution.py').is_file()

    @pytest.mark.parametrize('protocol', (None, 'decision_exchange_v1'))
    @pytest.mark.parametrize('declared_renderer', (False, True))
    def test_fresh_and_saved_decision_keep_full_launch_payload(self, launch_case, tmp_path, protocol, declared_renderer):
        f = self.task_case(launch_case, tmp_path)
        task, binding, runtime = f.task, launch_case.binding, f.runtime
        journal = launch_case.journal
        exchanges = self.module('decision_exchanges').DecisionExchanges(journal)
        task.calls = 0
        task._model_snapshot = task._presented_conversation_key = None
        task.decision_inputs = lambda context, index, profile: context
        task.workflow.store, task.workflow.journal = launch_case.store, journal
        task.workflow.decision_exchanges = exchanges
        task.workflow.controller_binding = {}
        task.workflow.decision_protocol = protocol
        task.workflow.contract_information_profile = lambda source: None
        task.workflow.receipts = None
        task.workflow.available_child_roles = lambda source: ()
        task.workflow.scientific_library_available = lambda source: False
        task.workflow.specialist = lambda source: binding
        task.workflow.binding_context = lambda source: launch_case.context
        task.workflow.is_job_source = lambda source: False
        task.workflow.permits_common_action = lambda source, action: action in binding.permitted_common_actions(launch_case.context)
        task.workflow.native_event_information = None
        # This dispatch test supplies the captured decision input directly.
        # Registry ownership has its separate full-family boundary baseline.
        task.workflow.resource_context = lambda source: None
        task.workflow.shared_information_context = lambda source: None
        task.workflow.episode_bindings = SimpleNamespace(initial_decision_context=lambda context: {})
        task.workflow.pending_work = lambda source: []
        task.workflow.execution_expectations = None
        task.workflow.resource_estimator = None
        task.workflow.native_estimation_context = lambda source, context: None
        task.workflow.freeze_literature_numerical_contracts = lambda *args: None
        task.workflow.knowledge = SimpleNamespace(instructions='Selected knowledge.')
        task.workflow.launch_instructions = SimpleNamespace(instructions='Selected launch instructions.',
            context=lambda: {}, materialize=lambda selection: None)
        private = hasattr(binding, 'decision_source_type')
        # A private task asks the real instruction service, which dispatches to the task's own
        # declared composer (episode_services.WorkflowServices.instructions).
        task.workflow.services = self.module('episode_services').WorkflowServices(task.workflow)
        if private:
            assert type(task).instruction_composer is self.module(self.binding_path+'/instructions').instructions
        state = {'hpc_execution_job': deepcopy(launch_case.plan),
                 'execution_assignment': deepcopy(launch_case.plan['launch_assignment'])}
        tool = binding.catalog(launch_case.context)[0]['name']
        response = {'selection': {'kind': 'tool', 'tool': tool, 'arguments': {}}, 'report_update': {}}
        wire = {'response': {'response_type': 'select_action', **response}} if protocol else response
        calls = []
        async def complete(*args, **kwargs):
            calls.append((args, kwargs))
            return deepcopy(wire)
        task.workflow.provider = SimpleNamespace(has_session=lambda *args: True, complete=complete)
        if declared_renderer:
            task.workflow.provider.complete_with_presentation = complete
        schema = runtime._object({'selection': runtime._object({'kind': {'const': 'tool'},
            'tool': {'const': tool}, 'arguments': runtime._object({})}), 'report_update': runtime._object({})})
        assert asyncio.run(task.call(state, schema))[0] == response
        assert len(calls) == 1
        # The renderer keyword is asserted only for a103, where a103/tests/launch_task_checks.py
        # states the same contract for this binding. a102's Launch task presents HPC contexts
        # through the provider's own path (its decision_provider.py) and no a102 test states that.
        if self.axis == 'a103':
            assert calls[0][1] == ({'prompt_renderer': binding.decision_prompt_renderer}
                if private and declared_renderer else {})
        presented = runtime.apply_state_frame(None, calls[0][0][3]) if protocol else calls[0][0][3]
        assert presented['hpc_execution_job'] == state['hpc_execution_job']
        assert presented['execution_assignment'] == state['execution_assignment']
        assert calls[0][0][2].startswith(binding.instructions(launch_case.context))
        saved = journal.row('runtime_model_calls', task.episode_id, 0)
        assert json.loads(saved['response']) == response
        task.calls = 0
        assert asyncio.run(task.call(state, schema))[0] == response
        assert len(calls) == 1
        assert launch_case.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
