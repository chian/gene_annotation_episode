"""Controlled original/current A103 report and action-assembly boundaries.

Real Store, Journal, typed contracts and private parent constructors are used.
Workflow initialization, scientific projection, tools and native operations are
outside this fixture. Supplied ports expose callback ordering and exact errors.
"""
import ast
import asyncio
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from pathlib import Path
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

from ... import runtime
from ...episode_bindings import EpisodeBindingRegistry
from ...episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a103.task import LegacyAnnotationTask
from ...legacy_improvement.task import LegacyImprovementTask
from ...method_loop import Context, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain
from ...scientific_process.episode import ScientificProcessEpisode
from ...scientific_process.task import ScientificProcessTask
from ...state import Store
from ..action_contracts import action_schema
from ..private_policy_call import invoke
from ..report_fact_assembly import facts


def forbidden(*args, **kwargs):
    raise AssertionError('outside the controlled report/schema boundary')


class EmptyCatalog:
    def as_record(self):
        return {'boundary_fixture': 'no scientific options or tool execution'}

    def headers(self):
        return ()

    resolve = staticmethod(forbidden)


def original(name):
    raw = (Path(__file__).parent / 'fixtures' / 'report_schema_ownership' /
           'original_functions.py.source').read_bytes()
    tree = ast.parse(raw)
    node, = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    temporary = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<retained-A103-original-' + name + '>', 'exec'), temporary)
    return FunctionType(temporary[name].__code__, runtime.__dict__, name)


@contextmanager
def host(directory, role):
    with Store(directory / 'store') as store:
        subject, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs']
        journal = Journal(store, 'a103-report-schema-boundary')
        services = SimpleNamespace(capabilities=lambda: (), model=forbidden,
            annotation_task_required=lambda: False)
        scientific = ScientificProcessEpisode(services, library=EmptyCatalog(),
            tool_library=EmptyCatalog(), child_roles=('scientific_process',))
        grain = Grain(role, 'original decision', 'typed report', forbidden)
        context = Context(tree=EpisodeTree(grain, {grain: ()}), run_id=journal.run_id)
        workflow = object.__new__(runtime.Workflow)
        scope = {'subject_refs': [subject]}
        values = dict(store=store, journal=journal, services=services, run_id=journal.run_id,
            context=context, grains={role: grain}, receipts=None, job_episodes=None,
            episode_bindings=EpisodeBindingRegistry((scientific,) if role == 'scientific_process' else ()),
            scientific_process_binding=scientific if role == 'scientific_process' else None,
            native_event_information=None, native_timing_information=None,
            project_annotation_score=None, resource_estimator=None,
            annotation_child_roles=None, root_action_boundary=None,
            project_credit=lambda *a, **k: 0.0)
        for name, value in values.items():
            setattr(workflow, name, value)
        schema = {'type': 'object', 'properties': {'credit': {'type': 'number', 'x-source': 'credit'}},
                  'required': ['credit'], 'additionalProperties': False}
        contract = runtime.TypedReportContract('Actual recorded credit only', schema, lambda *_: False)
        request = EpisodeRequest(EpisodeGoal.root(objective='Preserve original report/schema assembly',
            result_contract=schema), runtime.Record({'scope': scope, 'initial_report': {}}), contract)
        task = {'annotation': LegacyAnnotationTask, 'improvement': LegacyImprovementTask,
                'scientific_process': ScientificProcessTask}[role]
        source = task(workflow, ((role, 'parent'),), request, scope)
        journal.save('runtime_episodes', {'episode_id': source.episode_id,
            'path': runtime._json(source.path), 'request': runtime._json(request.as_record()),
            'initial_credit': 1.0, 'state': 'active', 'completion': None, 'archive': None})
        yield SimpleNamespace(workflow=workflow, source=source, scientific=scientific,
                              store=store, journal=journal, subject=subject)


@contextmanager
def isolated(value):
    class RestoreRows(Exception):
        pass
    try:
        with value.store.transaction():
            yield
            raise RestoreRows()
    except RestoreRows:
        pass


def report_observation(value, scenario, *, prior):
    workflow, source = value.workflow, value.source
    events = []
    marker = RuntimeError('original callback identity')
    selected = original('facts') if prior else facts
    source.last_outcome, source.report_basis = {'record_refs': [value.subject]}, []
    record = SimpleNamespace(ended_by='source_failed', end_reason=None,
                             units_consumed=1, controller_state=None)
    registry = workflow.episode_bindings
    def credit(actual, **kwargs):
        assert actual is source
        events.append(('credit', sorted(kwargs)))
        return {'credit': 2.0}
    def pending(actual):
        assert actual is source
        events.append('pending')
        return []
    def projection(context, snapshot):
        events.append(('scientific_projection', deepcopy(snapshot)))
        return {'controlled_scientific_qualification': 'unresolved'}
    def current(context):
        events.append('current_saved_view')
        return {'controlled_current_view': 'unresolved'}
    def received(context, *, completion_snapshot=None):
        events.append(('received', deepcopy(completion_snapshot)))
        return {'credit': 99.0} if scenario == 'received-conflict' else {}
    async def release(identity):
        assert identity == source.episode_id
        events.append('release')
    def annotate(scope, *, source):
        events.append('annotation_projection')
        return {'annotation_score': 0.0, 'proposed_annotations': [], 'annotation_comparisons': []}
    def forecasts(*args, **kwargs):
        events.append('late_forecasts')
        return ['controlled-retained-forecast']
    with isolated(value), ExitStack() as stack:
        stack.enter_context(patch.object(workflow, 'source_credit_view', credit))
        stack.enter_context(patch.object(workflow, 'pending_handles', pending))
        stack.enter_context(patch.object(workflow, 'release', release))
        stack.enter_context(patch.object(registry, 'current_report_facts', current))
        stack.enter_context(patch.object(registry, 'received_report_facts', received))
        stack.enter_context(patch.object(workflow, 'source_controller_credit', lambda actual: 'original supplied credit meaning'))
        stack.enter_context(patch.object(value.scientific, 'facts', projection))
        stack.enter_context(patch.object(workflow.services, 'scientific_parent_invocation',
            lambda context: 'original-parent-invocation', create=True))
        if scenario == 'saved':
            value.journal.save('runtime_forms', {'episode_id': source.episode_id,
                'facts': runtime._json({'credit': 2.0, 'interpretations': {'qualification': 'unresolved'}}),
                'form': None})
            stack.enter_context(patch.object(workflow, 'source_credit_view', forbidden))
        if scenario == 'late-provider':
            def event_facts(context):
                events.append('native_event_callback')
                workflow.project_annotation_score = object()
                workflow.resource_estimator = object()
                runtime.recorded_forecasts = forecasts
                return {'controlled_native_event': 'unavailable'}
            stack.enter_context(patch.object(workflow, 'project_annotation_score', None))
            stack.enter_context(patch.object(workflow, 'resource_estimator', None))
            stack.enter_context(patch.object(runtime, 'recorded_forecasts', forbidden))
            stack.enter_context(patch.object(workflow, 'annotation_context', annotate))
            stack.enter_context(patch.object(workflow, 'native_event_information', SimpleNamespace(facts=event_facts)))
        if scenario == 'provider-error':
            def reject(context):
                events.append('native_event_error')
                raise marker
            stack.enter_context(patch.object(workflow, 'native_event_information', SimpleNamespace(facts=reject)))
        try:
            if scenario == 'private-finish':
                stack.enter_context(patch.object(runtime.Workflow, 'facts', selected))
                answer = asyncio.run(source.finish(record)).as_record()
                saved = value.journal.row('runtime_forms', source.episode_id)
                answer = {'answer': answer, 'saved_facts': runtime.json.loads(saved['facts']),
                          'saved_form': runtime.json.loads(saved['form'])}
            else:
                answer = selected(workflow, source, completion_record=record)
            outcome = ('returned', deepcopy(answer))
        except (ValueError, RuntimeError) as error:
            outcome = ('raised', type(error).__name__, str(error), error is marker)
    return {'events': events, 'outcome': outcome}


def schema_observation(value, scenario, *, prior):
    workflow, source = value.workflow, value.source
    events = []
    marker = RuntimeError('original late schema provider')
    selected = original('action_schema') if prior else action_schema
    def reason(actual, *args, **kwargs):
        assert actual is source
        events.append('reason_schema')
        return {'type': 'object', 'properties': {'kind': {'type': 'string', 'const': 'reason'}}}
    def catalog(scope, *, source):
        events.append('catalog')
        if scenario == 'late-binding':
            workflow.scientific_process_binding = object()
        if scenario == 'late-json-error':
            def reject(value):
                events.append('late_json')
                raise marker
            runtime._json = reject
        return [{'name': 'controlled.lookup', 'input_schema': {'type': 'object', 'properties': {},
                 'required': [], 'additionalProperties': False}}]
    with ExitStack() as stack:
        stack.enter_context(patch.object(workflow, 'reasoning_action_schema', reason))
        stack.enter_context(patch.object(workflow, 'catalog', catalog))
        stack.enter_context(patch.object(workflow, 'scientific_process_binding', None))
        stack.enter_context(patch.object(runtime, '_json', runtime._json))
        try:
            result = selected(workflow, source)
            outcome = ('returned', result)
        except RuntimeError as error:
            outcome = ('raised', type(error).__name__, str(error), error is marker)
    return {'events': events, 'outcome': outcome}


def paired(value, observer, scenario):
    before = observer(value, scenario, prior=True)
    after = observer(value, scenario, prior=False)
    assert after == before
    return after
