"""Original conditional host and typed exchanges, with named external ports.

Actual Workflow/Store/Journal/registry/source/request/contract owners are used.
The default nested projector refusal is tested separately. Exchange controls
supply a credit projection and stop before child iteration, model or native work.
"""
import asyncio
from contextlib import ExitStack, contextmanager, nullcontext
from copy import deepcopy
import json
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

from ...tests import test_implicit_annotation_parent as original

SCHEMA = {'type': 'object', 'properties': {'qualification': {'type': 'string',
          'enum': ['unresolved']}}, 'required': ['qualification'], 'additionalProperties': False}
INITIAL = {'qualification': 'unresolved'}


def method(owner, name):
    runtime = original.module('runtime')
    value = original.original_function(runtime, owner, name)
    live = FunctionType(value.__code__, vars(runtime), value.__name__, value.__defaults__)
    live.__kwdefaults__ = value.__kwdefaults__
    return live


def build(workflow, role='improvement', *, before=False, parent=None, key='parent', contract=None):
    runtime = original.module('runtime')
    call = method('Workflow', 'build') if before else runtime.Workflow.build
    options = ({'contract': contract} if contract is not None else {}) if parent is None else {'parent': parent.request.goal, 'parent_path': parent.path,
        'contract': contract or runtime.TypedReportContract('Retain unresolved qualification',
            deepcopy(SCHEMA), lambda *_: True), 'initial': deepcopy(INITIAL)}
    episode = call(workflow, role, key, 'Original conditional improvement',
                   workflow.store.validate_scope(), **options)
    source = episode.source
    if before:
        source = original.original_source_class(runtime)(workflow, source.path, source.request, source.scope)
    else:
        expected = original.module('episode').AnnotationTask if role == 'annotation' else original.module('annotation_improvement.task').ImprovementTask
        assert type(source) is expected
    return episode, source


def paired(tmp_path, observation, *args, **kwargs):
    values = []
    for before in (True, False):
        with original.actual_workflow(tmp_path / str(before)) as workflow:
            values.append(observation(workflow, *args, before=before, **kwargs))
    assert {k: v for k, v in values[0].items() if k != 'owners'} == {
        k: v for k, v in values[1].items() if k != 'owners'}
    return values


@contextmanager
def owner_calls(names, events):
    with ExitStack() as stack:
        for name, function in names:
            module = original.module(name)
            callback = getattr(module, function)
            def observe(*args, _callback=callback, **kwargs):
                events.append((_callback.__module__, _callback.__name__))
                return _callback(*args, **kwargs)
            stack.enter_context(patch.object(module, function, observe))
        yield


def construction(workflow, *, before):
    runtime = original.module('runtime')
    _, source = build(workflow, before=before)
    state = dict(vars(source))
    state.pop('workflow'); state.pop('request')
    first = dict(workflow.journal.row('runtime_episodes', source.episode_id))
    _, restored = build(workflow, before=before)
    assert restored.request.as_record() == source.request.as_record()
    assert dict(workflow.journal.row('runtime_episodes', source.episode_id)) == first
    call = method('Workflow', 'build') if before else runtime.Workflow.build
    try:
        call(workflow, 'improvement', 'parent', 'Different immutable goal', source.scope)
    except runtime.WorkflowError as error:
        assert str(error) == 'reconstructed immutable assignment differs'
        failure = str(error)
    else:
        raise AssertionError('changed saved request was admitted')
    return {'state': state, 'request': source.request.as_record(), 'row': first, 'error': failure}


def mutable_default(workflow, raises, *, before):
    runtime = original.module('runtime')
    original.module('annotation_improvement.episode')
    actual = runtime.DecisionSource
    error = RuntimeError('original mutable improvement default')
    events = []
    def replacement(*args, **kwargs):
        events.append('default')
        if raises:
            raise error
        return actual(*args, **kwargs)
    with patch.object(runtime, 'DecisionSource', replacement):
        call = method('Workflow', 'build') if before else runtime.Workflow.build
        try:
            episode = call(workflow, 'improvement', 'parent', 'Original mutable default', workflow.store.validate_scope())
        except RuntimeError as actual_error:
            assert actual_error is error and raises
            result = ('error', str(actual_error))
        else:
            assert not raises and type(episode.source) is actual
            result = ('value', episode.request.as_record())
    assert events == ['default']
    return {'events': events, 'result': result}


def nested_refusal(workflow, parent_role, *, before):
    runtime = original.module('runtime')
    _, parent = build(workflow, parent_role, before=before)
    try:
        build(workflow, before=before, parent=parent, key='nested')
    except ValueError as error:
        assert str(error) == 'scientific_task_credit_not_declared:improvement'
    else:
        raise AssertionError('default nested projector refusal disappeared')
    return {'error': 'scientific_task_credit_not_declared:improvement',
        'actions': [dict(row) for row in workflow.store.db.execute('SELECT * FROM runtime_actions')]}


def returned_outcome(workflow, status, *, before):
    runtime = original.module('runtime')
    _, source = build(workflow, before=before)
    events = []
    workflow.journal.measure = lambda *_: nullcontext()
    result = {'status': status, 'record_refs': [], 'changed_record_refs': [],
              'feedback': {'status': status, 'category': 'supplied_original_outcome'}}
    workflow.execute = lambda *a, **kw: events.append('execute') or deepcopy(result)
    workflow.receive_native_outcome = lambda *a: events.append('native_custody')
    workflow.receive_outcome = lambda *a: events.append('outcome_custody')
    async def score(_source, _index, value):
        events.append('score'); return value
    workflow.automatic_score_updates = score
    workflow.pending_work = lambda _source: []
    workflow.controller_value = lambda _source, index, credit: {'index': index, 'credit': credit}
    selection = {'kind': 'tool', 'tool': 'controlled.returned_unit', 'arguments': {}}
    values = []
    for _ in range(2):
        try:
            values.append(('returned', asyncio.run(source.execute(deepcopy(selection), 4))))
        except runtime.ActionFailure as error:
            values.append(('raised', original.failure(error)))
    assert values[0] == values[1]
    assert events.count('execute') == 1 and events.count('score') == 1
    assert source.last_outcome['status'] == status and source.last_outcome_index == 4
    return {'values': values, 'events': events, 'feedback': source.feedback,
        'last_outcome': source.last_outcome,
        'row': dict(workflow.journal.row('runtime_actions', source.episode_id, 4))}


def report(workflow, mode, *, before):
    runtime = original.module('runtime')
    events = []
    contract = None if mode == 'root' else runtime.TypedReportContract(
        'Actual typed improvement report', deepcopy(SCHEMA), lambda *_: True)
    _, source = build(workflow, before=before, contract=contract)
    workflow.pending_handles = lambda _source: []
    async def release(episode_id): events.append(('release', episode_id))
    workflow.release = release
    if mode != 'root':
        source.report_values = deepcopy(INITIAL)
    if mode == 'saved':
        workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
            'facts': runtime._json({'credit': 17, 'interpretations': {'old': True}}),
            'form': runtime._json(INITIAL)})
    value = asyncio.run(source.finish(None)).as_record()
    again = asyncio.run(source.finish(None)).as_record()
    assert value == again and len(events) == 2
    if mode != 'root': assert value == {'form': INITIAL}
    row = workflow.journal.row('runtime_forms', source.episode_id)
    return {'value': value, 'events': events, 'row': None if row is None else dict(row)}


def continuation(workflow, nested, *, before):
    runtime = original.module('runtime')
    _, parent = build(workflow, before=before)
    source = parent
    if nested:
        workflow.source_credit_view = lambda _source, **kw: {'credit': -0.25}
        _, source = build(workflow, before=before, parent=parent, key='nested')
    events = []
    supplied = SimpleNamespace(epoch='actual-supplied-controller')
    def factory(path, initial, **kwargs):
        context = kwargs.get('context')
        events.append((path, initial, {**kwargs, 'context': context.as_record()} if context else kwargs))
        return supplied
    factory.requires_original_task = True
    workflow.controller_factory = factory
    workflow.has_native_estimation = lambda: False
    call = method('Workflow', 'controller') if before else runtime.Workflow.controller
    try:
        value = call(workflow, source.path)
    except ValueError as error:
        assert nested and str(error) == 'scientific_continuation_task_not_declared:improvement'
        result = ('error', str(error)); assert events == []
    else:
        assert not nested and value.controller is supplied and value.journal is workflow.journal
        assert value.episode_id == source.episode_id
        result = ('wrapper', value.episode_id, value.include_native)
    return {'result': result, 'events': events}


def credit(workflow, *, before):
    runtime = original.module('runtime')
    _, source = build(workflow, before=before)
    projector = object(); events = []
    workflow.scientific_projector_for_context = lambda context: events.append(('projector', context.as_record())) or projector
    workflow.projection_arguments = lambda actual: events.append(('arguments', actual.episode_id)) or {'selected': 'original'}
    def projection(actual, scope, **kwargs):
        assert actual is projector
        events.append(('projection', scope, kwargs)); return {'credit': -0.375}
    workflow.projection_view = projection
    call = method('Workflow', 'source_credit_view') if before else runtime.Workflow.source_credit_view
    value = call(workflow, source)
    assert value == {'credit': -0.375}
    return {'value': value, 'events': events}


def live_report(workflow, *, before):
    runtime = original.module('runtime')
    original.module('annotation_improvement.to_parent')
    _, source = build(workflow, before=before)
    events = []; error = RuntimeError('actual mutable report Record')
    async def release(episode_id): events.append(('release', episode_id))
    workflow.release = release; workflow.pending_handles = lambda _: []
    def record(value): events.append(('record', deepcopy(value))); raise error
    with patch.object(runtime, 'Record', record):
        call = method('DecisionSource', 'finish') if before else type(source).finish
        try: asyncio.run(call(source, None))
        except RuntimeError as actual: assert actual is error
        else: raise AssertionError('mutable original Record was bypassed')
    assert [event[0] for event in events] == ['release', 'record']
    return {'events': events}


def instructions(workflow, *, before):
    prompt = original.module('runtime_prompt'); owner = original.module('annotation_improvement.instructions')
    _, source = build(workflow, before=before)
    workflow.native_event_information = None
    events = []
    class Jobs:
        @property
        def roles(self): events.append('job_roles'); return ('improvement',)
        def instructions(self, role): events.append(('job_instructions', role)); return 'Actual supplied improvement job instructions'
    workflow.job_episodes = Jobs()
    specialist = SimpleNamespace(instructions=lambda context: events.append('specialist_instructions') or 'Actual supplied specialist instructions')
    workflow.specialist = lambda actual: events.append('specialist') or specialist
    workflow.permits_common_action = lambda actual, kind: events.append(('permits', kind)) or kind == 'reason'
    with patch.object(prompt, 'REASONING_COMMIT_REQUIREMENT', 'Actual rebound reasoning requirement'):
        value = (prompt.instructions if before else owner.instructions)(source, {})
    assert value.startswith('Actual supplied improvement job instructions\nActual supplied specialist instructions\nActual rebound reasoning requirement')
    return {'value': value, 'events': events}

