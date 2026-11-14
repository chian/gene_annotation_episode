"""Existing annotation construction and original late callback preservation."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from . import implicit_parent_checks as check


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', check.forbidden)
    monkeypatch.setattr('socket.socket.connect', check.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', check.forbidden)


@pytest.mark.parametrize('job_provider', (False, True))
def test_actual_unregistered_annotation_constructor_preserves_original_identity_and_job_reads(tmp_path, job_provider):
    runtime = check.module('runtime')
    observations = []
    for old in (True, False):
        events = []
        class JobPorts:
            def recover_statistics(self):
                events.append('recover_statistics')
            @property
            def roles(self):
                events.append('job_roles')
                return ('controlled_job',)
            def fact_sources(self, role):
                return {}
        with check.actual_workflow(tmp_path / str(old), job_episodes=JobPorts() if job_provider else None) as workflow:
            events.clear()
            episode = check.root(workflow, original=old)
            source = episode.source
            expected = runtime.DecisionSource if old else check.module('task').AnnotationTask
            assert type(source) is expected
            assert isinstance(source, runtime.DecisionSource)
            assert workflow.specialist(source) is None
            row = dict(workflow.journal.row('runtime_episodes', source.episode_id))
            assert row['state'] == 'active'
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            observations.append((source.episode_id, source.path, source.request.as_record(),
                                 row, list(events)))
    assert observations[0] == observations[1]


def test_actual_saved_root_reconstruction_and_mismatch(tmp_path):
    runtime = check.module('runtime')
    with check.actual_workflow(tmp_path) as workflow:
        original = check.root(workflow, original=True)
        before = dict(workflow.journal.row('runtime_episodes', original.source.episode_id))
        current = check.root(workflow)
        assert current.source.episode_id == original.source.episode_id
        assert current.source.request.as_record() == original.source.request.as_record()
        assert dict(workflow.journal.row('runtime_episodes', current.source.episode_id)) == before
        for call in (check.original_function('Workflow', 'build'), runtime.Workflow.build):
            with pytest.raises(runtime.WorkflowError, match='reconstructed immutable assignment differs'):
                call(workflow, 'annotation', 'root', 'Changed goal', current.source.scope)


def test_custom_workflow_keeps_original_source_fallback(tmp_path):
    runtime = check.module('runtime')
    class Custom(runtime.Workflow):
        pass
    with check.actual_workflow(tmp_path, workflow_class=Custom) as workflow:
        assert type(check.root(workflow).source) is runtime.DecisionSource


@pytest.mark.parametrize('scenario', ('ordinary', 'late-job', 'late-specialist', 'conflict'))
def test_private_fresh_report_preserves_actual_late_predicates_and_conflict(tmp_path, scenario):
    value, events = check.paired_report(tmp_path, scenario)
    assert events[0] == 'snapshot'
    assert events.count('credit') == events.count('received_facts') == 1
    if scenario == 'late-job':
        assert value['job_marker'] == 'original late job body'
    elif scenario == 'late-specialist':
        assert value['specialist_marker'] == 'original late body'
    elif scenario == 'conflict':
        assert value['error'][2] == 'received_report_fact_conflict'
    else:
        assert value['credit'] == 0.375 and value['pending_handles'] == ['owned-pending']


def test_private_saved_report_retains_original_refresh_and_removes_interpretations(tmp_path):
    value, events = check.paired_report(tmp_path, 'saved', saved=True)
    assert value == {'credit': 0.25, 'current_report_marker': 'authenticated current callback'}
    assert events == ['current_report_facts']


@pytest.mark.parametrize('saved_form', (False, True))
def test_private_finish_retains_original_release_and_saved_form_order(tmp_path, saved_form):
    observations = []
    runtime = check.module('runtime')
    for old in (True, False):
        with check.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.root(workflow).source
            events = []
            async def release(identity):
                assert identity == source.episode_id
                events.append('release')
            workflow.release = release
            if saved_form:
                source.request = runtime.EpisodeRequest(source.request.goal, source.request.message,
                    runtime.TypedReportContract('saved report', deepcopy(check.SCHEMA), lambda *a: True))
                workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
                    'facts': json.dumps({'credit': 0.25}), 'form': json.dumps({'old': 'saved form'})})
                workflow.facts = check.forbidden
            else:
                workflow.source_credit_view = lambda actual: events.append('credit') or {'credit': 0.375}
                workflow.pending_handles = lambda actual: events.append('pending') or []
                workflow.episode_bindings.current_report_facts = lambda context: events.append('current') or {'marker': 'context'}
            call = check.original_function('DecisionSource', 'finish') if old else type(source).finish
            result = asyncio.run(call(source, SimpleNamespace()))
            observations.append((result.as_record(), events))
    assert observations[0] == observations[1]
    assert observations[1][1] == (['release'] if saved_form else ['credit', 'pending', 'current', 'release'])


def test_private_controller_reads_rebound_runtime_global_after_factory(tmp_path, monkeypatch):
    runtime = check.module('runtime')
    original_context = runtime.ExecutionContextController
    observations = []
    for old in (True, False):
        with monkeypatch.context() as patch, check.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.root(workflow).source
            events = []
            def context(*args, **kwargs):
                events.append('late_context')
                return original_context(*args, **kwargs)
            def factory(path, initial):
                events.append('factory')
                patch.setattr(runtime, 'ExecutionContextController', context)
                numerical = check.module('numerical')
                return numerical.YieldController('preserved-controller', initial, 0.5,
                    numerical.YieldParameters(uncertainty_alpha=0.05))
            workflow.controller_factory = factory
            call = check.original_function('Workflow', 'controller') if old else runtime.Workflow.controller
            result = call(workflow, source.path)
            assert type(result) is original_context
            observations.append((result.episode_id, result.controller.initial_credit, events))
    assert observations[0] == observations[1]
    assert observations[1][2] == ['factory', 'late_context']


def test_private_instructions_preserve_late_job_specialist_and_text_provider(tmp_path, monkeypatch):
    observations = []
    prompt = check.module('runtime_prompt')
    for old in (True, False):
        with monkeypatch.context() as patch, check.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.root(workflow).source
            # A105 initializes this port. A108's authentic constructor omits it,
            # although its original prompt reads it; supply only that optional
            # fixture port, equally before both original/current invocations.
            if check.AXIS == 'a108':
                assert not hasattr(workflow, 'native_event_information')
                workflow.native_event_information = None
            else:
                assert workflow.native_event_information is None
            events = []
            def specialist_text(context):
                events.append('late_specialist_text')
                patch.setattr(prompt, 'REASONING_COMMIT_REQUIREMENT', 'late original reasoning text')
                return 'late original specialist text'
            late = SimpleNamespace(instructions=specialist_text, replaces_default_instructions=False)
            def job_text(role):
                assert role == 'annotation'
                events.append('late_job_text')
                workflow.specialist = lambda actual: events.append('late_specialist_lookup') or late
                return 'late original job text'
            def is_job(actual):
                assert actual is source
                events.append('is_job_source')
                workflow.job_episodes = SimpleNamespace(instructions=job_text)
                return True
            workflow.is_job_source = is_job
            workflow.job_episodes = SimpleNamespace(instructions=check.forbidden)
            workflow.specialist = check.forbidden
            workflow.permits_common_action = lambda actual, action: events.append(('permits', action)) or action == 'reason'
            result = (check.original_instructions()(source, {}) if old else source.instructions({}))
            observations.append((result, events))
    assert observations[0] == observations[1]
    assert observations[1][0].startswith('late original job text\nlate original specialist text\nlate original reasoning text\n')
    assert observations[1][1] == ['is_job_source', 'late_job_text', 'late_specialist_lookup',
                                  'late_specialist_text', ('permits', 'reason'), ('permits', 'wait')]


@pytest.mark.parametrize('home', ('scientific_process', 'published_evidence_assessment'))
@pytest.mark.parametrize('redelivery', (False, True))
def test_existing_scientific_receiver_uses_late_original_global_and_provider(home, redelivery, tmp_path, monkeypatch):
    runtime = check.module('runtime')
    observations = []
    for old in (True, False):
        with monkeypatch.context() as patch, check.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.root(workflow).source
            events = []
            workflow.receipts = SimpleNamespace(known=lambda *a, **kw: (),
                receive=lambda *args, **kwargs: events.append(('receive', deepcopy(args), kwargs)))
            workflow.is_job_source = lambda actual: False
            workflow.native_timing_information = None
            refs = [source.scope['subject_refs'][0]]
            def references(*args, **kwargs):
                events.append('late_references')
                return list(refs)
            def progress(*args):
                events.append('progress')
                patch.setattr(runtime, '_references_in', references)
                if check.AXIS == 'a105':
                    workflow.specialist = lambda actual: SimpleNamespace(
                        receive_child_result=lambda *a: events.append('late_provider') or [])
            workflow.progress_provider = SimpleNamespace(receive_form=progress)
            workflow.episode_bindings.received_form_references = lambda *a: events.append('registry_receive') or []
            workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': 3, 'action': json.dumps({'role': 'scientific_process'}),
                'result': None, 'credit': None})
            records = check.module('episode_return_records').EpisodeReturnRecords
            patch.setattr(records, 'recorded_admission_references', lambda *a: None)
            call = (check.original_function('Workflow', '_receive_form', receiving_tail=True)
                    if old else check.module('scientific_process/from_child_' + home).receive_report)
            value = call(workflow, source, {}, {'type': 'object', 'properties': {}}, 3, redelivery=redelivery)
            observations.append((value, events))
    assert observations[0] == observations[1]
    assert observations[1][0]
    assert observations[1][1][:2] == ['progress', 'late_references']
    assert observations[1][1][2] == ('late_provider' if check.AXIS == 'a105' else 'registry_receive')


@pytest.mark.parametrize('home', ('scientific_process', 'published_evidence_assessment'))
@pytest.mark.parametrize('scenario', ('late-parser', 'late-validator-error'))
def test_existing_scientific_outgoing_reads_original_runtime_after_contract_callback(tmp_path, home, scenario):
    result, error, events = check.paired_outgoing(tmp_path, home, scenario)
    assert events[:3] == ['expanded_form', 'late_parse', 'late_validate']
    if scenario == 'late-validator-error':
        assert result is None and error[2] == 'original late validator result'
        assert events == ['expanded_form', 'late_parse', 'late_validate']
    else:
        assert error is None and result['initial'] == check.INITIAL
        if check.AXIS == 'a105' and home == 'published_evidence_assessment':
            assert events[3:] == ['materialize', 'late_assignment_provider', 'prepare_assignment']


@pytest.mark.parametrize('edge', check.EDGES)
@pytest.mark.parametrize('scenario', ('valid-return', 'invalid-return', 'saved-return'))
def test_four_actual_parent_edges_preserve_typed_return_and_saved_or_failure_custody(tmp_path, edge, scenario):
    observed = check.paired_exchange(tmp_path, edge, scenario)
    assert len(observed['attempts']) == 1
    assert 'expanded_form' in observed['events'] and 'build' in observed['events']
    if scenario == 'invalid-return':
        assert observed['failure'] is not None
        assert observed['last_outcome_index'] == 7
        assert observed['action']['credit'] == 0.375
        assert observed['action']['result'] is not None
    else:
        assert observed['failure'] is None and observed['result'] == check.INITIAL


@pytest.mark.parametrize('edge', check.EDGES)
def test_custom_registry_fallback_retains_original_callback_order(tmp_path, edge):
    observed = check.paired_exchange(tmp_path, edge, 'valid-return', custom_registry=True)
    assert observed['owners'] == []
    assert 'custom_registry_roles' in observed['events']


@pytest.mark.parametrize('operand', ('role-map', 'role-key', 'path-key', 'role-values',
                                   'parent-path', 'parent-name', 'selection-map', 'provider-type'))
def test_added_cached_selectors_do_not_probe_custom_callbacks(tmp_path, operand):
    events = []
    def unexpected(*args, **kwargs):
        events.append('unexpected_custom_probe')
        raise AssertionError('new selector invoked a custom callback')
    class CustomDict(dict):
        get = __getitem__ = __iter__ = __contains__ = unexpected
    class CustomText(str):
        __eq__ = unexpected
        __hash__ = str.__hash__
    class CustomList(list):
        __iter__ = __len__ = __getitem__ = unexpected
    class CustomTuple(tuple):
        __iter__ = __len__ = __getitem__ = __bool__ = unexpected
    class ProviderMeta(type):
        __eq__ = unexpected
    class CustomProvider(metaclass=ProviderMeta):
        pass
    with check.actual_workflow(tmp_path) as workflow:
        source = check.root(workflow).source
        episode = check.module('episode')
        selectors = check.module('child_message_owners')
        registry = workflow.episode_bindings
        if operand == 'role-map':
            registry._by_role = CustomDict()
        elif operand == 'role-key':
            registry._by_role = {CustomText('scientific_process'): []}
        elif operand == 'path-key':
            registry._by_path = {CustomText('scientific_process'): object()}
        elif operand == 'role-values':
            registry._by_role = {'scientific_process': CustomList()}
        elif operand == 'parent-path':
            assert episode.selects_annotation_parent(workflow, 'annotation', CustomTuple(), None) is False
        elif operand == 'parent-name':
            assert episode.selects_annotation_parent(workflow, CustomText('annotation'), (), None) is False
        elif operand == 'selection-map':
            assert selectors.nominal_episode_child(CustomDict(kind='episode_child')) is False
            assert selectors.nominal_episode_child({'kind': CustomText('episode_child')}) is False
        elif operand == 'provider-type':
            provider = CustomProvider()
            workflow.scientific_process_binding = provider
            registry._by_role = {'scientific_process': [provider]}
            registry._by_path = {'scientific_process': provider}
        if operand in ('role-map', 'role-key', 'path-key', 'role-values', 'provider-type'):
            assert selectors.exchange_for_parent(workflow, source, 'scientific_process') is None
        assert events == []
