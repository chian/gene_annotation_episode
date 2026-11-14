"""Direct annotation/scientific task checks, using actual controlled fixtures.

See DIRECT_TEST_PORTS.md. No annotation parent binding is invented. Selected
method checks bypass construction; the separate Workflow.build test does not.
No scientific action, provider transport, remote job, or full workflow is run.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
import json
import sys
from types import MethodType, SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.a110.tests.direct_private_tasks import DirectPrivateTaskFixture


def forbidden(*args, **kwargs):
    pytest.fail('direct_private_task_crossed_native_or_network_port')


class DirectPrivateTaskChecks(DirectPrivateTaskFixture):
    @pytest.fixture(autouse=True)
    def no_external_execution(self, monkeypatch):
        monkeypatch.setattr('subprocess.Popen', forbidden)
        monkeypatch.setattr('socket.socket.connect', forbidden)
        monkeypatch.setattr('socket.socket.connect_ex', forbidden)

    @pytest.mark.parametrize('inherited', [False, True])
    def test_actual_default_instruction_composition(self, selected, inherited):
        s = selected
        services = self.module('episode_services').WorkflowServices
        class InheritedDefault(services):
            pass
        s.workflow.services = (InheritedDefault if inherited else services)(s.workflow)
        context = {'tool_knowledge': {'fixture': 'declared'},
            'launch_instruction_library': {'fixture': 'declared'}}
        expected = self.module('runtime_prompt').instructions(s.task, deepcopy(context))
        before = deepcopy(context)
        assert s.task.instructions(context) == expected
        assert context == before

    @pytest.mark.parametrize('variant', ['function', 'method', 'spoofed_func', 'foreign_default'])
    def test_custom_instruction_callable_and_identity_are_preserved(self, selected, variant, monkeypatch):
        s = selected
        default = self.module('episode_services').WorkflowServices
        calls, marker, context = [], object(), {'custom': 'complete supplied context'}
        def custom(source, actual):
            calls.append((source, actual))
            return marker
        services = SimpleNamespace(instructions=custom)
        if variant == 'method':
            class CustomServices:
                def instructions(self, source, actual):
                    return custom(source, actual)
            services = CustomServices()
        elif variant == 'spoofed_func':
            custom.__func__ = default.instructions
        elif variant == 'foreign_default':
            foreign = default(s.workflow)
            services.instructions = foreign.instructions
        s.workflow.services = services
        expected = services.instructions(s.task, context)
        calls.clear()
        previous = sys.getprofile()
        if variant == 'foreign_default':
            # Observe the actual unchanged bound default service frame. The
            # service itself legitimately chooses a private task composer.
            def observed(frame, event, arg):
                if event == 'call' and frame.f_code is default.instructions.__code__ and frame.f_locals['self'] is foreign:
                    calls.append((frame.f_locals['source'], frame.f_locals['context']))
                if previous is not None: previous(frame, event, arg)
            sys.setprofile(observed)
        try:
            actual = s.task.instructions(context)
        finally:
            if variant == 'foreign_default': sys.setprofile(previous)
        if variant == 'foreign_default':
            assert actual == expected
            assert calls == [(s.task, context)]
            assert calls[0][0] is s.task and calls[0][1] is context
        else:
            assert actual is expected is marker
            assert calls == [(s.task, context)]
            assert calls[0][0] is s.task and calls[0][1] is context

    def test_workflow_build_invokes_actual_selected_task_constructor(self, selected, monkeypatch):
        s, v = selected, selected.v
        w = self.workflow(v)
        monkeypatch.setattr(v.runtime.Episode, 'identity',
            lambda *args, **kwargs: SimpleNamespace(episode_id=s.context.episode_id))
        monkeypatch.setattr(v.runtime, 'FeedbackEpisode',
            lambda grain, key, source, *args, **kwargs: source)
        w.context, w.grains = object(), {s.role: object()}
        w.inprocess_completion_order = None
        w.contract_information_profile = lambda source: None
        w.source_credit_view = lambda source: s.binding.credit_view(s.context, None)
        w.expose_assigned_job = lambda source: None
        w.archive = SimpleNamespace(store=lambda value: value)
        # The detached fixture request is incomplete. Build a fresh real
        # EpisodeRequest and persist its actual row through Workflow.build.
        with v.store.transaction():
            v.store.db.execute('DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (v.run_id, s.context.episode_id))
        built = v.runtime.Workflow.build(w, s.role, s.context.path[-1][1],
            'Retain original work and returned progress', v.runtime._plain(s.context.scope),
            parent_path=s.context.path[:-1], episode_assignment=v.runtime._plain(s.context.assignment))
        expected_type = getattr(s.binding, 'decision_source_type', v.runtime.DecisionSource)
        assert type(built) is expected_type
        assert built.workflow is w and built.path == s.context.path
        assert built.episode_id == s.context.episode_id and built.calls == 0
        assert built.report_values == {} and built.report_basis == []
        assert built.last_outcome is built.last_outcome_index is None
        assert built._execution_context is built._selection_view is None
        saved = v.journal.row('runtime_episodes', s.context.episode_id)
        assert json.loads(saved['request']) == v.runtime._plain(built.request.as_record())
        assert saved['state'] == 'active'

    def test_custom_instruction_exception_identity_is_preserved(self, selected):
        error = LookupError('controlled original custom service rejection')
        def rejected(*args):
            raise error
        selected.workflow.services = SimpleNamespace(instructions=rejected)
        with pytest.raises(LookupError) as observed:
            selected.task.instructions({'full': 'input'})
        assert observed.value is error

    @pytest.mark.parametrize('status', ['completed', 'invalid', 'failed', 'unavailable'])
    def test_returned_action_enters_original_observation_and_measurement_once(self, selected, status):
        s, calls = selected, []
        selection = {'kind': 'tool', 'tool': 'execution.capabilities' if selected.role == 'launch'
            else 'execution.results.status', 'arguments': {}}
        outcome = {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'result': None, 'feedback': {'category': 'controlled_acquisition_return', 'code': status}}
        async def acquisition(source, tool, arguments, **kwargs):
            calls.append((source, tool, arguments, kwargs['operation_key']))
            return deepcopy(outcome)
        s.workflow.execute = acquisition
        before = s.binding.credit_view(s.context, None)
        assert before['credit'] == 0
        measured = asyncio.run(s.task.execute(selection, 4))
        assert measured == {'index': 4, 'credit': before['credit']}
        saved = s.v.journal.row('runtime_actions', s.context.episode_id, 4)
        assert json.loads(saved['action']) == selection and json.loads(saved['result']) == outcome
        assert saved['credit'] == before['credit']
        assert calls == [(s.task, selection['tool'], {}, s.v.run_id + ':' + s.context.episode_id + ':4')]
        assert s.f.observations == [(4, outcome)] and s.f.projections == [s.context.episode_id]
        assert asyncio.run(s.task.execute(selection, 4)) == measured
        assert len(calls) == len(s.f.observations) == len(s.f.projections) == 1
        with pytest.raises(s.v.runtime.WorkflowError, match='reconstructed selected work changed'):
            asyncio.run(s.task.execute({**selection, 'arguments': {'changed': True}}, 4))
        assert len(calls) == len(s.f.observations) == len(s.f.projections) == 1

    def test_saved_wait_replay_keeps_original_measurement(self, selected):
        s = selected
        selection = {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
            'events': [], 'reconsider_at': '2026-10-30T00:00:00+00:00'}}
        outcome = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': None}
        s.v.journal.save('runtime_actions', {'episode_id': s.context.episode_id,
            'decision_index': 8, 'action': json.dumps(selection), 'result': json.dumps(outcome), 'credit': 7.5})
        s.workflow.perform_selected_wait = s.workflow.source_credit_view = forbidden
        s.workflow.last_observed_credit = s.workflow.automatic_score_updates = forbidden
        assert asyncio.run(s.task.execute(selection, 8)) == {'index': 8, 'credit': 7.5}
        assert s.task.last_outcome == outcome and s.task.last_outcome_index == 8
        assert s.f.observations == s.f.projections == []

    @pytest.mark.parametrize('job_overlap', [False, True])
    def test_dynamic_job_predicate_and_original_instruction_endpoint(self, selected, job_overlap):
        s, calls = selected, []
        def job_instruction(role):
            calls.append(role)
            return 'Original caller-supplied job instructions before specialist composition.'
        s.workflow.job_episodes = SimpleNamespace(roles=(s.role,) if job_overlap else (),
            instructions=job_instruction)
        assert s.workflow.is_job_source(s.task) is job_overlap
        assert s.workflow.is_scientific_source(s.task) is False
        context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
        expected = self.module('runtime_prompt').instructions(s.task, deepcopy(context))
        assert calls == ([s.role] if job_overlap else [])
        calls.clear()
        assert s.task.instructions(context) == expected
        assert calls == ([s.role] if job_overlap else [])

    def test_actual_direct_action_availability_keeps_reason_wait(self, selected, monkeypatch):
        s = selected
        actual = s.binding.permitted_common_actions(s.context)
        assert actual == (('tool', 'reason', 'child', 'wait', 'redeliver_report')
            if s.role == 'launch' else ('tool',))
        if s.role == 'results' and 'a110' == 'a107':
            monkeypatch.setattr(s.binding, '_target', lambda *_: {'resource_kind': 'api',
                'assignment': {'version': 'api_service_assignment_v1'}})
            assert s.binding.permitted_common_actions(s.context) == ('tool', 'wait')
        assert not any(role == 'hpc' for role, _ in s.context.path)
        if s.v.parent is None:
            assert s.workflow.specialist(self.source(s.v, s.v.parent_context)) is None
        else:
            assert s.v.parent.binding_path == 'scientific_process'

    @pytest.mark.parametrize('status', ['completed', 'invalid', 'failed', 'unavailable'])
    def test_direct_reason_return_preserves_actual_dispatch_and_measurement(self, selected, monkeypatch, status):
        s, calls = selected, []
        if s.role != 'launch':
            # Results does not advertise reasoning; verify the real permission
            # boundary instead of dispatching an unavailable synthetic action.
            assert 'reason' not in s.binding.permitted_common_actions(s.context)
            return
        selection = {'kind': 'reason', 'commit': {'interpretation_accounts': []}}
        result = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None}
        def returned(context, action, key):
            calls.append((context, action, key))
            return deepcopy(result)
        # Declared acquisition-return port. This is not scientific reasoning or
        # proof that the intentionally minimal commit passes action admission.
        monkeypatch.setattr(s.binding, 'execute_reasoning', returned, raising=False)
        measured = asyncio.run(s.task.execute(selection, 12))
        assert measured == {'index': 12, 'credit': s.binding.credit_view(s.context, None)['credit']}
        assert calls == [(s.context, selection, s.v.run_id + ':' + s.context.episode_id + ':12')]
        assert s.f.observations == [(12, result)] and s.f.projections == [s.context.episode_id]
        saved = s.v.journal.row('runtime_actions', s.context.episode_id, 12)
        assert json.loads(saved['action']) == selection and json.loads(saved['result']) == result
        assert saved['credit'] == measured['credit']
        assert asyncio.run(s.task.execute(selection, 12)) == measured and len(calls) == 1

    def test_direct_wait_returns_original_credit_without_fresh_projection(self, selected, monkeypatch):
        s, calls = selected, []
        if s.role == 'results' and 'a110' == 'a107':
            monkeypatch.setattr(s.binding, '_target', lambda *_: {'resource_kind': 'api',
                'assignment': {'version': 'api_service_assignment_v1'}})
        if 'wait' not in s.binding.permitted_common_actions(s.context):
            assert s.role == 'results' and 'a110' == 'a110'
            return
        selection = {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
            'events': [], 'reconsider_at': '2026-10-30T00:00:00+00:00'}}
        result = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': None}
        async def returned(source, condition, index):
            calls.append((source, condition, index))
            return deepcopy(result)
        s.workflow.perform_selected_wait = returned
        s.workflow.last_observed_credit = lambda source: 2.75
        s.workflow.source_credit_view = s.workflow.automatic_score_updates = forbidden
        assert asyncio.run(s.task.execute(selection, 15)) == {'index': 15, 'credit': 2.75}
        assert calls == [(s.task, selection['condition'], 15)]
        assert s.f.observations == [(15, result)] and s.f.projections == []
        saved = s.v.journal.row('runtime_actions', s.context.episode_id, 15)
        assert json.loads(saved['action']) == selection and json.loads(saved['result']) == result
        assert saved['credit'] == 2.75
        assert asyncio.run(s.task.execute(selection, 15)) == {'index': 15, 'credit': 2.75}
        assert len(calls) == 1

    def test_actual_parent_transmission_keeps_object_and_child_admission_boundary(self, selected):
        s = selected
        value = {'not_yet_admitted': {'retain': ['same object']}}
        before = s.v.store.db.total_changes
        if s.v.parent is None:
            # Existing annotation route has no callback; its narrow own-axis
            # runtime adapter selects this endpoint only after extraction.
            returned = value
            assert s.workflow.specialist(self.source(s.v, s.v.parent_context)) is None
        else:
            returned = s.v.parent.prepare_child_request(s.v.parent_context, s.role, value)
        assert returned is value
        if s.phase == 'connected':
            prefix = 'scientific_process/' if s.v.parent is not None else ''
            leaf = 'execution_job_submission' if s.role == 'launch' else 'execution_result_acquisition'
            function = self.module(prefix + 'to_child_' + leaf).prepare_request
            assert function(s.v.parent_context, value) is value
        assert s.v.store.db.total_changes == before
        with pytest.raises(ValueError):
            s.binding.prepare_assignment(s.v.parent_context, s.role, value, s.context.scope, 'invalid-direct-assignment')
        assert s.v.store.db.total_changes == before

    @pytest.mark.parametrize('cached', [False, True])
    def test_actual_direct_parent_receipt_route_and_redelivery(self, selected, monkeypatch, cached):
        s, v = selected, selected.v
        source, w = self.source(v, v.parent_context), self.workflow(v)
        progress, receipts = [], []
        form, schema = {}, {'type': 'object', 'properties': {}, 'additionalProperties': False}
        w.progress_provider = SimpleNamespace(receive_form=lambda *args: progress.append(args))
        w.receipts = SimpleNamespace(receive=lambda *args, **kwargs: receipts.append((args, kwargs)))
        w._receive_form = MethodType(v.runtime.Workflow._receive_form, w)
        counterpart_calls, endpoint_calls = [], []
        counterpart = self.module('delivery_counterpart')
        original_counterpart = counterpart.child_role_for_delivery
        def resolve_counterpart(*args):
            counterpart_calls.append(args)
            if cached:
                pytest.fail('cached_direct_receipt_added_counterpart_read')
            return original_counterpart(*args)
        monkeypatch.setattr(counterpart, 'child_role_for_delivery', resolve_counterpart)
        if s.phase == 'connected':
            prefix = 'scientific_process/' if v.parent is not None else ''
            leaf = 'execution_job_submission' if s.role == 'launch' else 'execution_result_acquisition'
            endpoint = self.module(prefix + 'from_child_' + leaf)
            original_endpoint = endpoint.receive_report
            def receive_endpoint(*args, **kwargs):
                endpoint_calls.append((args, kwargs))
                return original_endpoint(*args, **kwargs)
            monkeypatch.setattr(endpoint, 'receive_report', receive_endpoint)
            if v.parent is not None:
                # The scientific connector binds this actual function on import.
                owner = sys.modules[v.parent.execution_child_report_receiver.__module__]
                alias = 'receive_launch_report' if s.role == 'launch' else 'receive_results_report'
                assert getattr(owner, alias) is original_endpoint
                monkeypatch.setattr(owner, alias, receive_endpoint)
        def receive(index, **kwargs):
            if s.phase == 'connected': kwargs['child_role'] = s.role
            return v.runtime.Workflow.receive_form(w, source, form, schema, index, **kwargs)
        monkeypatch.setattr(self.module('episode_return_records').EpisodeReturnRecords,
            'recorded_admission_references', lambda *_: ['controlled-retained-reference'] if cached else None)
        # Receipt authentication is a declared port here; rows and counterpart
        # lookup, complete selected receiver, progress identity and replay are real.
        monkeypatch.setattr(v.registry, 'received_form_references', lambda *_: [])
        def save(index, redelivery=False):
            action = ({'kind': 'redeliver_report', 'delivery_ref': 'direct-delivery'} if redelivery
                else {'kind': 'episode_child', 'role': s.role,
                    'assignment': v.runtime._plain(s.context.assignment), 'scope': source.scope})
            v.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index,
                'action': json.dumps(action), 'result': None, 'credit': None})
            v.journal.save('runtime_report_attempts', {'parent_episode_id': source.episode_id,
                'decision_index': index, 'delivery_ref': 'direct-delivery',
                'child_episode_id': s.context.episode_id, 'contract': json.dumps(schema),
                'form': json.dumps(form), 'failure': None})
        save(20)
        actual = receive(20)
        assert actual == (['controlled-retained-reference'] if cached else [])
        if cached:
            assert progress == receipts == []
            assert counterpart_calls == []
        else:
            save(21, True)
            assert receive(21, redelivery=True) == []
            assert [args[-1] for args in progress] == [v.run_id + ':' + source.episode_id + ':' + str(index) + ':typed_form' for index in (20, 21)]
            assert [kwargs for _, kwargs in receipts] == [
                {'kind': 'child_form', 'source_index': 20}, {'kind': 'report_redelivery', 'source_index': 21}]
            assert len(counterpart_calls) == (2 if v.parent is not None else 0)
        assert len(endpoint_calls) == ((1 if cached else 2) if s.phase == 'connected' else 0)
        override_calls, marker = [], object()
        def original_private_shape(current, admitted, form_schema, decision_index, *, redelivery=False):
            override_calls.append((current, admitted, form_schema, decision_index, redelivery))
            return marker
        w._receive_form = original_private_shape
        assert receive(22) is marker
        assert override_calls == [(source, form, schema, 22, False)]

    @pytest.mark.parametrize('native_role,cached', [(role, cached)
        for role in (('launch_api', 'launch_local', 'launch_hpc') if 'a110' == 'a107' else ('launch_local', 'launch_hpc'))
        for cached in (False, True)])
    def test_actual_native_receipt_selector_keeps_original_cache_and_reads(self, selected, monkeypatch, native_role, cached):
        s, v = selected, selected.v
        if s.role != 'launch':
            assert s.binding.child_roles(s.role) == ()
            return
        source, w = self.source(v, s.context), self.workflow(v)
        w._receive_form = MethodType(v.runtime.Workflow._receive_form, w)
        child = v.registry.for_child(source.path, native_role)
        assert native_role in child.roles
        child_path = source.path + ((native_role, 'controlled-native-receipt'),)
        child_id = self.module('method_loop.identities').EpisodeRef(v.run_id, child_path).episode_id
        assert v.registry.for_path(child_path) is child
        # Native request/ancestor metadata is controlled; this is a receiver
        # dispatch check, not native admission, construction or execution.
        v.journal.save('runtime_episodes', {'episode_id': child_id, 'path': json.dumps(child_path),
            'request': v.runtime._json(v.native_context.request), 'initial_credit': 0,
            'state': 'active', 'completion': None, 'archive': None})
        progress, receipts, endpoints = [], [], []
        w.progress_provider = SimpleNamespace(receive_form=lambda *args: progress.append(args))
        w.receipts = SimpleNamespace(receive=lambda *args, **kwargs: receipts.append((args, kwargs)))
        monkeypatch.setattr(self.module('delivery_counterpart'), 'child_role_for_delivery', forbidden)
        monkeypatch.setattr(self.module('episode_return_records').EpisodeReturnRecords,
            'recorded_admission_references', lambda *_: ['controlled-retained-reference'] if cached else None)
        monkeypatch.setattr(v.registry, 'received_form_references', lambda *_: [])
        if s.phase == 'connected':
            suffix = native_role.removeprefix('launch_')
            endpoint = self.module(self.binding_path + '/from_child_' + suffix + '_job_execution')
            original = endpoint.receive_report
            def selected_receiver(*args, **kwargs):
                endpoints.append((args, kwargs))
                return original(*args, **kwargs)
            original_selector = s.binding.execution_child_report_receiver
            def select_receiver(role):
                chosen = original_selector(role)
                assert role == native_role and chosen is original
                return selected_receiver
            monkeypatch.setattr(s.binding, 'execution_child_report_receiver', select_receiver)
        form, schema = {}, {'type': 'object', 'properties': {}, 'additionalProperties': False}
        def deliver(index, redelivery=False):
            action = {'kind': 'redeliver_report', 'delivery_ref': 'controlled-native-delivery'} if redelivery else {
                'kind': 'episode_child', 'role': native_role, 'assignment': {}, 'scope': source.scope}
            v.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index,
                'action': json.dumps(action), 'result': None, 'credit': None})
            v.journal.save('runtime_report_attempts', {'parent_episode_id': source.episode_id,
                'decision_index': index, 'delivery_ref': 'controlled-native-delivery', 'child_episode_id': child_id,
                'contract': json.dumps(schema), 'form': json.dumps(form), 'failure': None})
            kwargs = {'redelivery': redelivery}
            if s.phase == 'connected': kwargs['child_role'] = native_role
            return v.runtime.Workflow.receive_form(w, source, form, schema, index, **kwargs)
        assert deliver(30) == (['controlled-retained-reference'] if cached else [])
        if cached:
            assert progress == receipts == []
        else:
            assert deliver(31, True) == []
            assert [args[-1] for args in progress] == [v.run_id + ':' + source.episode_id + ':' + str(index) + ':typed_form' for index in (30, 31)]
            assert [kwargs for _, kwargs in receipts] == [{'kind': 'child_form', 'source_index': 30},
                {'kind': 'report_redelivery', 'source_index': 31}]
        assert len(endpoints) == ((1 if cached else 2) if s.phase == 'connected' else 0)

    def test_actual_runtime_direct_transmission_precedes_original_child_admission(self, selected, monkeypatch):
        s, v, events, built = selected, selected.v, [], []
        w, source = self.workflow(v), self.source(v, v.parent_context)
        w.permits_common_action = lambda current, action: v.runtime.Workflow.permits_common_action(w, current, action)
        if v.parent is not None:
            # This ancestor is controlled metadata, not an admitted scientific
            # invocation. Only its invocation validation port is controlled;
            # real configured child roles and endpoint dispatch remain active.
            w.scientific_process_binding = v.parent
            monkeypatch.setattr(v.parent, 'validate_execution_context', lambda *_: None)
            monkeypatch.setattr(v.parent, 'validate_context', lambda *_: None)
            original_send = v.parent.prepare_child_request
            def send(*args):
                events.append('request')
                return original_send(*args)
            monkeypatch.setattr(v.parent, 'prepare_child_request', send)
        elif s.phase == 'connected':
            leaf = 'execution_job_submission' if s.role == 'launch' else 'execution_result_acquisition'
            endpoint = self.module('to_child_' + leaf)
            original_send = endpoint.prepare_request
            def send(*args):
                events.append('request')
                return original_send(*args)
            monkeypatch.setattr(endpoint, 'prepare_request', send)
        original_admit = s.binding.prepare_assignment
        def admit(parent, role, assignment, scope, key):
            events.append('admission')
            # Launch uses actual admission. Results target authentication is a
            # declared port because this fixture has no real external handoff.
            return (original_admit(parent, role, assignment, scope, key)
                if role == 'launch' else deepcopy(assignment))
        monkeypatch.setattr(s.binding, 'prepare_assignment', admit)
        schema = {'type': 'object', 'properties': {'completed': {'type': 'boolean',
            'x-source': 'execution_completed'}}, 'required': ['completed'], 'additionalProperties': False}
        w.expanded_contract_form = lambda *_: (schema, None)
        selection = {'kind': 'episode_child', 'role': s.role, 'scope': source.scope,
            'assignment': v.runtime._plain(s.context.assignment), 'goal': 'Original direct child work',
            'purpose': 'Receive its original incomplete status', 'schema_json': json.dumps(schema), 'initial_report_json': '{}'}
        proxy = SimpleNamespace(source=self.source(v, s.context))
        def build(*args, **kwargs):
            built.append((args, kwargs))
            return proxy
        w.build = build
        callbacks = []
        def retain_unit(child, credit, report, *args, **kwargs):
            callbacks.append(report)
            return child
        monkeypatch.setattr(v.runtime, 'TimedChildUnit', retain_unit)
        index = 3 if s.role == 'launch' else 9
        assert v.runtime.Workflow.selected(w, source, selection, index) is proxy
        assert events == (['request', 'admission'] if v.parent is not None or s.phase == 'connected' else ['admission'])
        assert built[0][0][0] == s.role and built[0][1]['parent_path'] == source.path
        assert built[0][1]['episode_assignment'] == selection['assignment']
        assert built[0][1]['contract'].schema == schema
        # Exercise the original authenticated report callback's role handoff.
        # Only semantic validation is a declared port; typed admission, saved
        # attempt, original transaction and selected full receiver remain real.
        w.validate_report = lambda *args, **kwargs: None
        w.save_attempt = lambda *args, **kwargs: v.runtime.Workflow.save_attempt(w, *args, **kwargs)
        w._receive_form = MethodType(v.runtime.Workflow._receive_form, w)
        delivered = []
        w.receive_form = MethodType(v.runtime.Workflow.receive_form, w)
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code is v.runtime.Workflow.receive_form.__code__ and frame.f_locals.get('self') is w:
                delivered.append(frame.f_locals.get('child_role'))
        form = {'completed': False}
        previous = sys.getprofile()
        try:
            sys.setprofile(profile)
            assert asyncio.run(callbacks[0](v.runtime.Record({'form': form}), None, proxy.source.request)) == form
        finally:
            sys.setprofile(previous)
        assert delivered == [s.role if s.phase == 'connected' else None]
        overrides = []
        def original_receive_shape(current, admitted, form_schema, decision_index, *, redelivery=False):
            overrides.append((current, admitted, form_schema, decision_index, redelivery))
            return []
        w.receive_form = original_receive_shape
        assert asyncio.run(callbacks[0](v.runtime.Record({'form': form}), None, proxy.source.request)) == form
        assert overrides == [(source, form, schema, index, False)]
        attempt = v.store.db.execute('SELECT child_episode_id FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (v.run_id, source.episode_id, index)).fetchone()
        assert attempt['child_episode_id'] == s.context.episode_id

    @pytest.mark.parametrize('declared', [False, True])
    def test_saved_provider_call_and_private_renderer_use_original_full_inputs(self, selected, declared):
        s, calls = selected, []
        s.task._model_snapshot = s.task._presented_conversation_key = None
        s.workflow.contract_information_profile = lambda source: None
        context = {'original_direct_assignment': s.v.runtime._plain(s.context.assignment),
            'original_scope': s.v.runtime._plain(s.context.scope)}
        schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
        saved = {'context': context, 'schema': schema}
        s.v.journal.save('runtime_model_calls', {'episode_id': s.context.episode_id, 'call_index': 0,
            'purpose': 'decision', 'request': json.dumps(saved), 'response': None})
        response = {'selection': {'kind': 'tool', 'tool': 'controlled', 'arguments': {}}, 'report_update': {}}
        async def complete(*args, **kwargs):
            calls.append((args, kwargs))
            return deepcopy(response)
        if declared:
            provider = object.__new__(self.module('providers').ModelConnection)
            provider.worker_lock = asyncio.Lock()
            provider.workers = {}
            # Existing-session port matches the original LaunchConnected fixture.
            provider.has_session = lambda *_: True
            provider._complete_serial = complete
            s.workflow.provider = provider
        else:
            s.workflow.provider = SimpleNamespace(has_session=lambda *_: True, complete=complete)
        returned = asyncio.run(s.task.call({'different_now': True}, {}))
        assert returned[0] == response and returned[2:] == (context, schema)
        assert calls[0][0] == (s.context.episode_id, 'REASONING', s.task.instructions(context), context, schema)
        expected = {'prompt_renderer': s.binding.decision_prompt_renderer} if declared and s.phase == 'connected' else {}
        assert calls[0][1] == expected
        s.task.calls = 0
        assert asyncio.run(s.task.call({'third_context': True}, {})) == returned
        assert len(calls) == 1
        original_provider = self.module('providers')._SessionConnection
        left = SimpleNamespace(scientific_prompt_states={})
        right = SimpleNamespace(scientific_prompt_states={})
        instructions = s.task.instructions(context)
        original = original_provider._presentation(left, s.context.episode_id, 'REASONING', instructions, deepcopy(context))
        if s.phase == 'connected':
            actual = original_provider._presentation(right, s.context.episode_id, 'REASONING', instructions,
                deepcopy(context), prompt_renderer=s.binding.decision_prompt_renderer)
            assert actual == original and left.scientific_prompt_states == right.scientific_prompt_states


class TestAnnotationLaunch(DirectPrivateTaskChecks):
    binding_path = 'execution_job_submission'
class TestScientificLaunch(DirectPrivateTaskChecks):
    binding_path = 'scientific_process/execution_job_submission'
class TestAnnotationResults(DirectPrivateTaskChecks):
    binding_path = 'execution_result_acquisition'
class TestScientificResults(DirectPrivateTaskChecks):
    binding_path = 'scientific_process/execution_result_acquisition'
