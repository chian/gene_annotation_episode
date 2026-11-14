"""Actual improvement task/state/report/continuation with explicit supplied ports."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from ... import runtime
from ..task import ImprovementTask
from ...episode_bindings import EpisodeBindingRegistry, BindingContext
from ...tests.annotation_parent_exchange_checks import INITIAL, SCHEMA, forbidden, isolated_rows
from ...tests.annotation_parent_original_boundaries import original_method


def host_workflow(host, events, *, custom=False):
    class CustomRegistry(EpisodeBindingRegistry):
        pass
    workflow = object.__new__(runtime.Workflow)
    values = dict(store=host.store, journal=host.journal, run_id=host.journal.run_id,
        context=host.context, grains=host.grains, services=host.services,
        episode_bindings=(CustomRegistry if custom else EpisodeBindingRegistry)(()),
        scientific_process_binding=None, job_episodes=None, annotation_child_roles=None,
        execution_binding=None, inprocess_replay=None, inprocess_completion_order=None,
        execution_handle=None, receipts=None, progress_provider=None,
        resource_estimator=None, project_annotation_score=None, native_timing_information=None,
        completed_action_inputs_version=None, wait_inputs_version=None,
        episode_branch_lifecycle=None, tools=SimpleNamespace(native_statistics=None),
        archive=SimpleNamespace(store=forbidden))
    for name, value in values.items():
        setattr(workflow, name, value)
    workflow.specialist = lambda source: None
    workflow.binding_context = lambda source: BindingContext(workflow.run_id, source.episode_id,
        source.path[-1][0], source.path, source.scope, {}, source.request.as_record())
    workflow.contract_information_profile = lambda source: None
    workflow.source_credit_view = lambda source, **kwargs: {'credit': -0.25}
    workflow.receive_tool_attributions = lambda *args, **kwargs: []
    workflow.expose_assigned_job = lambda source: None
    workflow.pending_handles = lambda source: []
    workflow.is_job_source = lambda source: False
    workflow.has_native_estimation = lambda: False
    async def release(episode_id):
        events.append(('release', episode_id))
    workflow.release = release
    return workflow


def build_host(host, workflow, *, original=False, contract=None):
    method = original_method('build') if original else runtime.Workflow.build
    episode = method(workflow, 'improvement', 'parent', 'Preserve the original improvement host',
        host.scope, initial=deepcopy(INITIAL), contract=contract)
    expected = runtime.DecisionSource if original or type(workflow.episode_bindings) is not EpisodeBindingRegistry else ImprovementTask
    assert type(episode.source) is expected
    assert episode.source.workflow is workflow
    assert episode.request.goal.as_record()['objective'] == 'Preserve the original improvement host'
    return episode


def build_observation(host, *, original=False, custom=False):
    events = []
    workflow = host_workflow(host, events, custom=custom)
    episode = build_host(host, workflow, original=original)
    source = episode.source
    fields = ('path', 'episode_id', 'calls', 'feedback', 'last_outcome', 'last_outcome_index',
        'report_values', 'report_basis', '_restored', '_unfinished_own_actions', '_source_revision',
        '_latest_effect_index', '_restored_source_state', '_model_snapshot',
        '_presented_conversation_key', '_selection_view', '_delivery_resolution_ref',
        '_execution_context', '_suspension_condition', '_inprocess_replay_ready', 'interpret_schema')
    state = {name: deepcopy(getattr(source, name)) for name in fields}
    restored = build_host(host, workflow, original=original)
    assert restored.request.as_record() == episode.request.as_record()
    return {'state': state, 'request': episode.request.as_record(), 'events': events,
        'row': dict(host.journal.row('runtime_episodes', source.episode_id))}


def action_observation(host, status, *, original=False):
    events = []
    workflow = host_workflow(host, events)
    source = build_host(host, workflow, original=original).source
    async def execute(actual, name, arguments, **kwargs):
        assert actual is source
        events.append(('execute', name, deepcopy(arguments), kwargs['operation_key']))
        return {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'result': {'supplied_result': status}, 'feedback': {'original_outcome': status}}
    async def score(actual, index, result):
        events.append(('automatic_score_port', index))
        return result
    workflow.execute = execute
    workflow.automatic_score_updates = score
    selection = {'kind': 'tool', 'tool': 'controlled.returned-unit', 'arguments': {}}
    first = asyncio.run(source.execute(deepcopy(selection), 4)).as_record()
    replay = asyncio.run(source.execute(deepcopy(selection), 4)).as_record()
    assert first == replay == {'credit': -0.25, 'estimation_action_index': 4}
    assert [event[0] for event in events].count('execute') == 1
    assert [event[0] for event in events].count('automatic_score_port') == 1
    row = dict(host.journal.row('runtime_actions', source.episode_id, 4))
    # Journal timing is genuine execution data, not a behavior-equality field.
    row.pop('timing', None)
    source._restored_source_state = {'last_outcome_index': 4, 'feedback': {'retained': status}}
    source.last_outcome = None
    source.restore_checkpoint()
    assert source.last_outcome['status'] == status and source._restored_source_state is None
    return {'first': first, 'replay': replay, 'action': row, 'events': events,
            'outcome': source.last_outcome, 'feedback': source.feedback}


def report_observation(host, mode, *, original=False):
    events = []
    workflow = host_workflow(host, events)
    schema = deepcopy(SCHEMA)
    schema['properties']['score'] = {'type': 'number', 'x-source': 'credit'}
    schema['required'].append('score')
    contract = None if mode == 'root' else runtime.TypedReportContract(
        'Preserve original qualification and factual credit', schema,
        lambda *args: True, lambda *args: None)
    source = build_host(host, workflow, original=original, contract=contract).source
    first = asyncio.run(source.finish(None)).as_record()
    second = asyncio.run(source.finish(None)).as_record()
    assert first == second
    row = host.journal.row('runtime_forms', source.episode_id)
    if mode == 'root':
        assert first == {'credit': -0.25, 'pending_handles': []} and row is None
    else:
        assert first == {'form': {**INITIAL, 'score': -0.25}}
        assert row is not None
        fresh = (original_method('facts') if original else runtime.Workflow.facts)(workflow, source)
        assert fresh['credit'] == -0.25 and 'interpretations' not in fresh
    assert len(events) == 2 and all(event[0] == 'release' for event in events)
    return {'result': first, 'row': None if row is None else dict(row), 'events': events}


def continuation_observation(host, task_aware, *, original=False):
    events = []
    workflow = host_workflow(host, events)
    source = build_host(host, workflow, original=original).source
    supplied = SimpleNamespace(epoch='original-supplied-controller')
    def factory(path, initial, **kwargs):
        context = kwargs.get('context')
        events.append((path, initial, {**kwargs, 'context': context.as_record()}
            if context is not None else kwargs))
        return supplied
    factory.requires_original_task = task_aware
    workflow.controller_factory = factory
    wrapper = (original_method('controller') if original else runtime.Workflow.controller)(workflow, source.path)
    assert wrapper.controller is supplied and wrapper.journal is host.journal
    assert wrapper.episode_id == source.episode_id and wrapper.epoch == supplied.epoch
    assert not wrapper.include_native and wrapper.capture_current_completion is None
    value = (original_method('controller_value') if original else runtime.Workflow.controller_value)(workflow, source, 4, -0.25).as_record()
    assert value == {'credit': -0.25, 'estimation_action_index': 4}
    observation = {'decision_index': 4, 'credit': {'credit': -0.25,
        'estimation_action_index': 4, 'original_saved_extension': 'retain exactly'}}
    host.journal.save('runtime_observations', {'episode_id': source.episode_id, 'unit_index': 0,
        'observation': runtime._json(observation)})
    restored = (original_method('controller_value') if original else runtime.Workflow.controller_value)(workflow, source, 4, 999).as_record()
    assert restored == observation['credit']
    return {'events': events, 'value': value, 'restored': restored}


def mutable_record_observation(host, *, original=False):
    events = []
    workflow = host_workflow(host, events)
    source = build_host(host, workflow, original=original).source
    error = RuntimeError('original live Record provider')
    def record(value):
        events.append(('mutable_record', deepcopy(value)))
        raise error
    with patch.object(runtime, 'Record', record):
        try:
            asyncio.run(source.finish(None))
        except RuntimeError as actual:
            assert actual is error
        else:
            raise AssertionError('live original Record provider was bypassed')
    assert [event[0] for event in events] == ['release', 'mutable_record']
    return events


def paired_host(host, callback, *args, **kwargs):
    with isolated_rows(host):
        before = callback(host, *args, original=True, **kwargs)
    with isolated_rows(host):
        after = callback(host, *args, original=False, **kwargs)
    assert before == after
    return after

def credit_observation(host, *, original=False):
    events, owners = [], []
    workflow = host_workflow(host, events)
    source = build_host(host, workflow, original=original).source
    projector = object()
    selected = {'credit': -0.375, 'actual_supplied_projection': 'unresolved'}
    def choose(context):
        assert context.episode_id == source.episode_id
        events.append('scientific_projector')
        return projector
    def arguments(actual):
        assert actual is source
        events.append('original_projection_arguments')
        return {'selected_original_refs': []}
    def project(actual, scope, **kwargs):
        assert actual is projector and scope is source.scope
        assert kwargs == {'selected_original_refs': []}
        events.append('actual_projection_port')
        return selected
    workflow.scientific_projector_for_context = choose
    workflow.projection_arguments = arguments
    workflow.projection_view = project
    from .. import credit
    original_owner = credit.credit_view
    def owner(*args, **kwargs):
        owners.append(True)
        return original_owner(*args, **kwargs)
    with patch.object(credit, 'credit_view', owner):
        result = (original_method('source_credit_view') if original else
            runtime.Workflow.source_credit_view)(workflow, source)
    assert result is selected and owners == ([] if original else [True])
    assert events == ['scientific_projector', 'original_projection_arguments', 'actual_projection_port']
    return {'result': result, 'events': events}


from contextlib import contextmanager
from ...state import Store
from ...episode_journal import Journal
from ...method_loop import Context, EpisodeTree, Grain


@contextmanager
def improvement_host(directory, *, root_role='improvement'):
    with Store(directory / 'store') as store:
        subject, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs']
        journal = Journal(store, 'a102-improvement-boundary')
        grains = {name: Grain(name, 'original decision', 'typed return', forbidden)
            for name in ('annotation', 'improvement')}
        children = {grains['improvement']: (grains['improvement'],)}
        if root_role == 'annotation':
            children[grains['annotation']] = (grains['improvement'],)
        tree = EpisodeTree(grains[root_role], children, self_nesting=('improvement',))
        services = SimpleNamespace(capabilities=lambda: (), model=forbidden,
            annotation_task_required=lambda: False, reference_in_scope=lambda *a: True)
        yield SimpleNamespace(store=store, journal=journal, services=services,
            grains=grains, context=Context(tree=tree, run_id=journal.run_id),
            scope={'subject_refs': [subject]})


def nested_continuation_observation(host, *, original=False):
    events = []
    workflow = host_workflow(host, events)
    method = original_method('build') if original else runtime.Workflow.build
    parent = method(workflow, 'annotation', 'root', 'Original parent', host.scope)
    contract = runtime.TypedReportContract('Unresolved original conclusion', deepcopy(SCHEMA), lambda *a: True)
    child = method(workflow, 'improvement', 'nested', 'Original nested task', host.scope,
        parent=parent.request.goal, parent_path=parent.source.path, contract=contract, initial=deepcopy(INITIAL))
    def factory(*args, **kwargs):
        events.append('factory')
        raise AssertionError('original unavailable task must reject before factory')
    factory.requires_original_task = True
    workflow.controller_factory = factory
    try:
        (original_method('controller') if original else runtime.Workflow.controller)(workflow, child.source.path)
    except ValueError as error:
        assert str(error) == 'scientific_continuation_task_not_declared:improvement'
    else:
        raise AssertionError('inherited unavailable task was silently accepted')
    assert events == []
    return child.request.as_record()
