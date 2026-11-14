"""Actual private task/endpoint checks; controlled ports are declared below.

Reuse the required real Store/Journal/HPC-registry fixture. Only Results' target
and empty received set, the returned acquisition outcome and provider/service
callbacks are controlled. No target authentication or scientific run is claimed.
The selected-method fixture uses object.__new__ and copies controlled __dict__
state, bypassing the task constructor. A separate Workflow.build check invokes
the real selected constructor with declared identity/FeedbackEpisode ports.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import os
import sys
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.tests.launch_connected import LaunchConnectedChecks


def forbidden(*args, **kwargs):
    pytest.fail('private_task_refinement_crossed_native_or_network_port')


class PrivateTaskRefinementChecks:
    module = LaunchConnectedChecks.module
    connected = LaunchConnectedChecks.connected
    source = LaunchConnectedChecks.source
    workflow = LaunchConnectedChecks.workflow
    task = LaunchConnectedChecks.task

    @pytest.fixture(autouse=True)
    def no_external_execution(self, monkeypatch):
        monkeypatch.setattr('subprocess.Popen', forbidden)
        monkeypatch.setattr('socket.socket.connect', forbidden)
        monkeypatch.setattr('socket.socket.connect_ex', forbidden)

    @pytest.fixture
    def selected(self, connected, monkeypatch):
        v = connected
        role = 'launch' if self.binding_path.endswith('execution_job_submission') else 'results'
        if role == 'launch':
            context, binding = v.context, v.launch
        else:
            path = v.parent_context.path + (('results', 'child_9'),)
            episode_id = self.module('method_loop.identities').EpisodeRef(v.run_id, path).episode_id
            assignment = {'version': 'execution_results_assignment_v1',
                'handoff_ref': v.context.scope['subject_refs'][0],
                'selector': {'path': str((v.directory / 'controlled-result-workspace' / 'controlled-empty-results.txt').resolve()), 'offset': 0, 'limit': 4}}
            request = v.runtime._plain(v.context.request)
            request['message']['episode_assignment'] = assignment
            context = replace(v.context, role=role, path=path, episode_id=episode_id,
                assignment=assignment, request=request)
            v.journal.save('runtime_episodes', {'episode_id': episode_id,
                'path': v.runtime._json(path), 'request': v.runtime._json(request),
                'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
            binding = v.registry.for_path(path)
            target = {'resource_kind': 'local', 'assignment': {
                'workspace': str((v.directory / 'controlled-result-workspace').resolve()), 'requested_job': {}}}
            monkeypatch.setattr(binding, '_target', lambda *_: deepcopy(target))
            monkeypatch.setattr(binding, '_received', lambda *_args, **_kwargs:
                ({'known_record_refs': [], 'initial_known_record_refs': []}, {}, {}))
        assert binding.binding_path == self.binding_path
        v.contexts[context.episode_id] = context
        f = self.task(v)
        selected_type = getattr(binding, 'decision_source_type', v.runtime.DecisionSource)
        observed_phase = 'baseline' if selected_type is v.runtime.DecisionSource else 'connected'
        expected_phase = os.environ.get('GENE_PRIVATE_TASK_PHASE', observed_phase)
        assert expected_phase in {'baseline', 'connected'} and observed_phase == expected_phase
        if observed_phase == 'connected':
            assert selected_type.__module__ == binding.__module__.removesuffix('.episode') + '.task'
            assert selected_type.__name__ == ('LaunchTask' if role == 'launch' else 'ResultsTask')
        task = object.__new__(selected_type)
        task.__dict__.update(f.task.__dict__)
        task.__dict__.update(self.source(v, context).__dict__)
        f.task = task
        w = task.workflow
        w.decision_protocol = None
        w.native_event_information = None
        w.is_scientific_source = lambda source: v.runtime.Workflow.is_scientific_source(w, source)
        w.services = self.module('episode_services').WorkflowServices(w)
        def credit(source):
            assert source.episode_id == context.episode_id
            f.projections.append(source.episode_id)
            return binding.credit_view(context, None)
        w.source_credit_view = credit
        assert w.specialist(task) is binding
        assert w.is_job_source(task) is w.is_scientific_source(task) is False
        return SimpleNamespace(v=v, f=f, task=task, workflow=w, binding=binding,
            context=context, role=role, phase=observed_phase)

    def test_original_dynamic_presentation_and_saved_frame_state(self, selected):
        s = selected
        providers = self.module('providers')
        frames = self.module('decision_context')
        original = object.__new__(providers._SessionConnection)
        actual = object.__new__(providers._SessionConnection)
        original.scientific_prompt_states = {}
        actual.scientific_prompt_states = {}
        renderer = None
        if s.phase == 'connected':
            renderer = getattr(self.module(s.binding.binding_path + ('/task_presentation' if s.role == 'launch' else '/presentation')),
                'present_' + s.role + '_context')
            assert s.binding.decision_prompt_renderer is renderer
            assert renderer.presentation_protocol == 'episode_context_presentation_v1'
        key = (s.context.episode_id, s.role)
        instructions = 'Preserve the supplied operational context and original frame semantics.'

        def compare(context, expected_state, error=None):
            before = deepcopy(context)
            outcomes = []
            for provider, selected_renderer in ((original, None), (actual, renderer)):
                operand = deepcopy(context)
                if error is None:
                    outcomes.append(provider._presentation(*key, instructions, operand,
                        prompt_renderer=selected_renderer))
                else:
                    with pytest.raises(error) as caught:
                        provider._presentation(*key, instructions, operand,
                            prompt_renderer=selected_renderer)
                    outcomes.append((type(caught.value), str(caught.value)))
                assert operand == before
            assert context == before and outcomes[0] == outcomes[1]
            assert original.scientific_prompt_states == actual.scientific_prompt_states == expected_state
            return outcomes[0]

        raw = {'unrelated_context': {'value': 'kept exactly'}}
        assert compare(raw, {}) == (json.dumps(raw, allow_nan=False), instructions)
        first = {'hpc_execution_job': {'fixture_operand': 'original'}, 'counter': 1}
        second = {'hpc_execution_job': {'fixture_operand': 'updated'}, 'counter': 2}
        compare(frames.state_frame(first), {key: first})
        compare(frames.state_frame(second, first), {key: second})
        compare({'version': frames.VERSION, 'kind': 'decision_lookup_result',
            'result': {'fixture_lookup': 'retained'}}, {key: second})
        # Unrelated legacy input does not clear an earlier presentation state.
        assert compare(raw, {key: second}) == (json.dumps(raw, allow_nan=False), instructions)
        # An unrelated bootstrap does clear that state, without text rendering.
        plain_frame = frames.state_frame(raw)
        assert compare(plain_frame, {}) == (json.dumps(plain_frame, allow_nan=False), instructions)
        # A delta carrying a text task cannot invent its missing base state.
        compare(frames.state_frame(second, first), {}, TypeError)
        compare(frames.state_frame(first), {key: first})
        conflict = frames.state_frame(second, first)
        conflict['base_revision'] = 'not-the-retained-revision'
        compare(conflict, {key: first}, ValueError)


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
            # Observe the actual bound default service, which now legitimately
            # selects the source's own complete composer. A task-side bypass
            # makes no call to this original function with the foreign self.
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

    def test_outgoing_transmission_retains_original_object_and_validation_boundary(self, selected):
        s = selected
        supplied = {'deliberately': {'not': ['an admitted child assignment']}}
        before = s.v.store.db.total_changes
        if s.role == 'results':
            returned = s.v.parent.prepare_child_request(s.v.parent_context, 'results', supplied)
            if s.phase == 'connected':
                function = self.module(s.v.parent.binding_path + '/to_child_execution_result_acquisition').prepare_request
                assert function(s.v.parent_context, supplied) is supplied
        else:
            callback = getattr(s.binding, 'prepare_child_request', None)
            returned = supplied if callback is None else callback(s.context, 'launch_hpc', supplied)
            if s.phase == 'connected':
                for role, child in (('launch_local', 'local_job_execution'), ('launch_hpc', 'hpc_job_execution')):
                    function = self.module(self.binding_path + '/to_child_' + child).prepare_request
                    assert function(s.binding, s.context, supplied) is supplied
                if 'a110' == 'a107':
                    function = self.module(self.binding_path + '/to_child_api_job_execution').prepare_request
                    assert function(s.binding, s.context, supplied) is supplied
        assert returned is supplied
        assert s.v.store.db.total_changes == before


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
        form, schema = {}, {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
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

    @pytest.mark.parametrize('cached', [False, True])
    def test_actual_results_parent_receipt_preserves_original_generic_reads(self, selected, monkeypatch, cached):
        s, v = selected, selected.v
        if s.role != 'results':
            assert 'launch_hpc' in s.binding.child_roles('launch')
            return
        source, w = self.source(v, v.parent_context), self.workflow(v)
        w._receive_form = MethodType(v.runtime.Workflow._receive_form, w)
        original_generic = getattr(v.parent, 'child_report_receiver', None)
        original_progress = getattr(v.parent, 'receive_child_progress_for_role', None)
        # Planning may already have a generic allocation/prediction hook. Its
        # pre-cache reader is original behavior and must neither disappear nor
        # be duplicated by the new Results selector.
        expected_per_call = int(original_generic is not None) + (0 if cached else int(original_progress is not None))
        reader = self.module('delivery_counterpart')
        original_read = reader.child_role_for_delivery
        reads, progress, receipts, endpoints = [], [], [], []
        def read(*args):
            reads.append(args)
            return original_read(*args)
        monkeypatch.setattr(reader, 'child_role_for_delivery', read)
        w.progress_provider = SimpleNamespace(receive_form=lambda *args: progress.append(args))
        w.receipts = SimpleNamespace(receive=lambda *args, **kwargs: receipts.append((args, kwargs)))
        monkeypatch.setattr(self.module('episode_return_records').EpisodeReturnRecords,
            'recorded_admission_references', lambda *_: ['controlled-retained-reference'] if cached else None)
        monkeypatch.setattr(v.registry, 'received_form_references', lambda *_: [])
        if s.phase == 'connected':
            endpoint = self.module(v.parent.binding_path + '/from_child_execution_result_acquisition').receive_report
            selector = v.parent.execution_child_report_receiver
            def receive(*args, **kwargs):
                endpoints.append((args, kwargs)); return endpoint(*args, **kwargs)
            def choose(role):
                selected_endpoint = selector(role)
                assert role == 'results' and selected_endpoint is endpoint
                return receive
            monkeypatch.setattr(v.parent, 'execution_child_report_receiver', choose)
        form, schema = {}, {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
        def deliver(index, redelivery=False):
            action = {'kind': 'redeliver_report', 'delivery_ref': 'controlled-results-delivery'} if redelivery else {
                'kind': 'episode_child', 'role': 'results', 'assignment': v.runtime._plain(s.context.assignment), 'scope': source.scope}
            v.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index,
                'action': json.dumps(action), 'result': None, 'credit': None})
            v.journal.save('runtime_report_attempts', {'parent_episode_id': source.episode_id,
                'decision_index': index, 'delivery_ref': 'controlled-results-delivery', 'child_episode_id': s.context.episode_id,
                'contract': json.dumps(schema), 'form': json.dumps(form), 'failure': None})
            return v.runtime.Workflow.receive_form(w, source, form, schema, index,
                redelivery=redelivery, child_role='results')
        assert deliver(40) == (['controlled-retained-reference'] if cached else [])
        assert len(reads) == expected_per_call
        if cached:
            assert progress == receipts == []
        else:
            assert deliver(41, True) == []
            assert len(reads) == 2 * expected_per_call
            assert [args[-1] for args in progress] == [v.run_id + ':' + source.episode_id + ':' + str(i) + ':typed_form' for i in (40,41)]
            assert [kwargs for _, kwargs in receipts] == [{'kind': 'child_form', 'source_index': 40},
                {'kind': 'report_redelivery', 'source_index': 41}]
        assert len(endpoints) == ((1 if cached else 2) if s.phase == 'connected' else 0)
        calls, marker = [], object()
        def original_private_shape(current, admitted, form_schema, index, *, redelivery=False):
            calls.append((current, admitted, form_schema, index, redelivery)); return marker
        w._receive_form = original_private_shape
        assert deliver(42) is marker
        assert calls == [(source, form, schema, 42, False)]

    def test_actual_native_parent_requests_owns_original_admission(self, selected):
        s, v = selected, selected.v
        if s.role != 'launch':
            assert s.binding.child_roles('results') == ()
            return
        owner = self.module(v.native.binding_path + '/from_parent').NativeParentRequests
        for name in ('child_assignment_schema', 'assignment_schema', 'prepare_assignment'):
            assert getattr(v.native, name).__func__ is getattr(owner, name)
        incoming = v.native.child_assignment_schema(v.context, 'launch_hpc')
        assert incoming == {'type': 'object', 'enum': [v.plan['practical_assignment']]}
        prepared = deepcopy(v.plan['practical_assignment'])
        if s.phase == 'connected':
            prepared = s.binding.prepare_child_request(v.context, 'launch_hpc', prepared)
        else:
            assert getattr(s.binding, 'prepare_child_request', None) is None
        assert prepared == v.plan['practical_assignment']
        admitted = v.native.prepare_assignment(v.context, 'launch_hpc', prepared,
            v.context.scope, 'original-native-commission')
        assert admitted == v.plan['practical_assignment']
        with pytest.raises(ValueError, match='unknown_execution_episode_role'):
            v.native.assignment_schema('launch')
        with pytest.raises(ValueError, match='resource_child_role_owned_by_launch'):
            v.native.prepare_assignment(v.parent_context, 'launch_hpc', prepared,
                v.context.scope, 'wrong-original-parent')
        # The original frozen action-schema boundary owns this rejection;
        # the parent transmitter deliberately preserves the selected object.
        changed = deepcopy(prepared)
        changed['requested_job']['argv'].append('changed-job')
        with pytest.raises(ValueError):
            self.module('execution_contracts').checked(changed, incoming, 'changed_frozen_request')
        assert v.ledger.records('launch_commission') == []
        assert v.ledger.records('handoff') == []

    def test_hpc_and_native_descriptor_shapes_and_same_configuration(self, selected):
        s, v = selected, selected.v
        saved = s.binding.as_record()
        again = self.module(self.binding_path + '/episode').ExecutionEpisode(
            s.binding.services, **v.execution_options)
        assert again.as_record() == saved
        if s.phase == 'connected':
            fingerprint = saved['implementation_sha256']
            assert len(fingerprint) == 64 and set(fingerprint) <= set('0123456789abcdef')
        native = v.native.as_record()
        assert 'implementation_sha256' not in native
        restored_native = self.module(v.native.binding_path + '/episode').ExecutionEpisode(
            v.native.services, **v.execution_options)
        assert restored_native.as_record() == native

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

class TestPlanningLaunch(PrivateTaskRefinementChecks):
    binding_path = 'hpc_work_planning/execution_job_submission'
class TestAllocationLaunch(PrivateTaskRefinementChecks):
    binding_path = 'hpc_work_planning/hpc_allocation_execution/execution_job_submission'
class TestScientificPlanningLaunch(PrivateTaskRefinementChecks):
    binding_path = 'scientific_process/hpc_work_planning/execution_job_submission'
class TestScientificAllocationLaunch(PrivateTaskRefinementChecks):
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
class TestPlanningResults(PrivateTaskRefinementChecks):
    binding_path = 'hpc_work_planning/execution_result_acquisition'
class TestAllocationResults(PrivateTaskRefinementChecks):
    binding_path = 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
class TestScientificPlanningResults(PrivateTaskRefinementChecks):
    binding_path = 'scientific_process/hpc_work_planning/execution_result_acquisition'
class TestScientificAllocationResults(PrivateTaskRefinementChecks):
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
