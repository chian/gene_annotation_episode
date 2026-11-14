"""One existing recursive Scientific parent exchange through real task and typed-return owners.

Store, Journal, bindings, task constructors and selected() are real. Empty
catalogues and scientific preparation/credit are explicit supplied ports; no
model, scientific process, native job or full restoration is exercised.
"""
import asyncio
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
from unittest.mock import patch

from .. import runtime
from ..episode_bindings import EpisodeBindingRegistry, BindingContext
from ..episode_journal import Journal
from ..method_loop import Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain
from ..scientific_process.episode import ScientificProcessEpisode
from ..scientific_process.task import ScientificInvestigationTask
from ..state import Store
from .recursive_scientific_original import original_selected, original_method

ROLES = ('scientific_process',)
SCENARIOS = ('request-valid', 'initial-invalid', 'prepare-error', 'return-valid',
             'return-invalid', 'saved-valid', 'saved-failure', 'mutable-global')
SCHEMA = {'type': 'object', 'properties': {
    'qualification': {'type': 'string', 'const': 'unresolved'}},
    'required': ['qualification'], 'additionalProperties': False}
INITIAL = {'qualification': 'unresolved'}


def forbidden(*args, **kwargs):
    raise AssertionError('outside the controlled parent exchange')


class EmptyCatalog:
    def as_record(self):
        return {'boundary_fixture': 'no scientific options or tool execution'}

    def headers(self):
        return ()

    resolve = staticmethod(forbidden)


@contextmanager
def parent_host(directory):
    with Store(directory / 'store') as store:
        subject, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs']
        journal = Journal(store, 'a101-recursive-parent-exchange')
        services = SimpleNamespace(capabilities=lambda: (), model=forbidden,
                                   annotation_task_required=lambda: False)
        scientific = ScientificProcessEpisode(services, library=EmptyCatalog(),
            tool_library=EmptyCatalog(), child_roles=ROLES)
        grains = {role: Grain(role, 'original decision', 'typed return', forbidden)
                  for role in ROLES}
        tree = EpisodeTree(grains['scientific_process'], {
            grains['scientific_process']: tuple(grains.values())},
            self_nesting=('scientific_process',))
        yield SimpleNamespace(store=store, journal=journal, services=services,
            scientific=scientific, grains=grains,
            context=Context(tree=tree, run_id=journal.run_id), scope={'subject_refs': [subject]})


@contextmanager
def isolated_rows(host):
    class RestoreRows(Exception):
        pass
    try:
        with host.store.transaction():
            yield
            raise RestoreRows()
    except RestoreRows:
        pass


def observe(host, role, scenario, *, original=False, custom_registry=False):
    events, owners, built, deliveries = [], [], [], []

    class CustomRegistry(EpisodeBindingRegistry):
        @property
        def roles(self):
            events.append('custom_roles')
            return super().roles

    registry = (CustomRegistry if custom_registry else EpisodeBindingRegistry)(
        (host.scientific,))
    workflow = object.__new__(runtime.Workflow)
    for name, value in dict(store=host.store, journal=host.journal, run_id=host.journal.run_id,
            services=host.services, grains=host.grains, context=host.context,
            episode_bindings=registry, annotation_child_roles=ROLES,
            scientific_process_binding=host.scientific, execution_binding=None,
            inprocess_replay=None, receipts=None, root_action_boundary=None,
            job_episodes=SimpleNamespace(assign=forbidden), wait_inputs_version=None,
            completed_action_inputs_version=None,
            episode_branch_lifecycle=runtime.EPISODE_BRANCH_LIFECYCLE
                if scenario.startswith('saved-') else None).items():
        setattr(workflow, name, value)
    path = (('scientific_process', 'parent'),)
    request = EpisodeRequest(EpisodeGoal.root(objective='Preserve the actual parent exchange',
        result_contract=SCHEMA), runtime.Record({'scope': host.scope, 'initial_report': INITIAL}))
    source = ScientificInvestigationTask(workflow, path, request, host.scope)
    binding_context = lambda actual: BindingContext(host.journal.run_id, actual.episode_id,
        actual.path[-1][0], actual.path, actual.scope, {}, actual.request.as_record())
    injected = RuntimeError('original supplied preparation failure')
    parse_failure = RuntimeError('original mutable runtime parser failure')
    expanded_failure = RuntimeError('original expanded-form failure')
    prepared_assignment = {'boundary_assignment': 'original supplied scientific preparation'}
    prepared_process = {'boundary_process': 'original supplied scientific preparation'}
    def expanded(*args, **kwargs):
        events.append('expanded_form')
        if scenario == 'expanded-error':
            raise expanded_failure
        return deepcopy(SCHEMA), None
    def prepare(context, actual_role, assignment, scope, key, **kwargs):
        events.append(('prepare_invocation', actual_role, deepcopy(assignment), deepcopy(scope), key, deepcopy(kwargs)))
        assert context.episode_id == source.episode_id
        if scenario == 'prepare-error':
            raise injected
        return {'assignment': prepared_assignment, 'scientific_process': prepared_process}
    def parse(*args, **kwargs):
        events.append('mutable_runtime_parser')
        raise parse_failure
    def build(actual_role, key, objective, scope, **kwargs):
        events.append('build')
        assert actual_role == role and kwargs['job_assignment'] is None
        if role == 'scientific_process':
            assert kwargs['episode_assignment'] is prepared_assignment
            assert kwargs['scientific_process'] is prepared_process
        child_request = EpisodeRequest(EpisodeGoal.child(kwargs['parent'], objective=objective,
            result_contract=SCHEMA), runtime.Record({'scope': scope, 'initial_report': kwargs['initial'],
            'episode_assignment': kwargs['episode_assignment']}), kwargs['contract'])
        child_path = kwargs['parent_path'] + ((actual_role, key),)
        task = ScientificInvestigationTask
        child_source = task(workflow, child_path, child_request, scope)
        built.append({'path': child_path, 'request': child_request.as_record(),
            'assignment': kwargs['episode_assignment'], 'process': kwargs['scientific_process']})
        return Episode(host.grains[actual_role], key, child_source, child_request, forbidden)
    def receive(actual, form, schema, index, **kwargs):
        assert actual is source
        events.append(('receive_form', deepcopy(form), index, kwargs))
        return []
    def credit(actual):
        assert actual is source
        events.append('original_credit_port')
        return {'credit': 0.375}
    async def unresolved(actual, view, **kwargs):
        assert actual is source
        events.append(('original_pending_resolution', kwargs))
        raise runtime.ReportDeliveryError(runtime.Record(source.feedback))
    workflow.validate_child_choice = lambda *a, **kw: events.append('validate_child_choice')
    workflow.permits_common_action = lambda *a: a[-1] != 'wait'
    workflow._closed_child_commission = lambda *a: None
    workflow.expanded_contract_form = expanded
    workflow.child_initial_report_input = lambda *a: json.dumps(
        {'qualification': 'invented'} if scenario == 'initial-invalid' else INITIAL)
    workflow.binding_context = binding_context
    workflow.specialist = lambda actual: host.scientific
    workflow.available_child_roles = lambda actual: ROLES
    workflow.launch_instructions = SimpleNamespace(materialize=lambda value: events.append(('materialize', value)))
    workflow.build = build
    workflow.resolver = lambda *a, **kw: (lambda *a: True)
    workflow.validate_report = lambda value, scope, **kw: events.append(('validate_report', deepcopy(value), kw['grain']))
    workflow.is_job_source = lambda *a: False
    workflow.receive_form = receive
    workflow.source_credit_view = credit
    workflow.controller_value = lambda actual, index, value: runtime.Record({'original_credit': value})
    workflow.resolve_pending_deliveries = unresolved
    assignment = {'launch_instructions': None}
    if scenario.startswith('typed-'):
        def progress(*args):
            events.append(('typed_progress', deepcopy(args)))
            if scenario == 'typed-error':
                raise injected
        def receipt(*args, **kwargs):
            events.append(('typed_receipt', deepcopy(args), deepcopy(kwargs)))
        def attributions(*args, **kwargs):
            events.append(('typed_attributions', args[1], deepcopy(kwargs)))
            return []
        workflow.progress_provider = SimpleNamespace(receive_form=progress)
        workflow.receipts = SimpleNamespace(receive=receipt) if scenario == 'typed-redelivery' else None
        workflow.native_timing_information = None
        workflow.receive_tool_attributions = attributions
        workflow.receive_form = runtime.Workflow.receive_form.__get__(workflow)
        if original:
            workflow._receive_form = original_method('_receive_form').__get__(workflow)
    selection = {'kind': 'episode_child', 'role': role, 'scope': deepcopy(host.scope),
        'goal': 'Original child objective', 'purpose': 'Typed unresolved qualification', 'assignment': assignment}
    from ..scientific_process import child_message_owners
    exchange = child_message_owners.exchange_for_child(workflow, source, role)
    assert (exchange is None) is custom_registry
    assert events == [], 'private selection cannot call registry or provider ports early'
    original_for_child = registry.for_child
    def for_child(*args, **kwargs):
        events.append('for_child')
        return original_for_child(*args, **kwargs)
    call = original_selected() if original else runtime.Workflow.selected
    error, returned, unit, replayed = None, None, None, None
    with ExitStack() as stack:
        stack.enter_context(patch.object(registry, 'for_child', for_child))
        stack.enter_context(patch.object(host.scientific, 'prepare_invocation', prepare))
        stack.enter_context(patch.object(host.scientific, 'validate_execution_context',
            lambda context: events.append('validate_execution_context')))
        if scenario == 'mutable-global':
            # The original oracle is loaded before patching; refresh its globals
            # just as its original module global lookup occurs at invocation.
            stack.enter_context(patch.object(runtime, 'parse_json_object', parse))
            if original:
                call = original_selected()
        if exchange is not None:
            for callback in exchange:
                def observed(*args, _callback=callback, **kwargs):
                    owners.append((_callback.__module__, _callback.__name__))
                    return _callback(*args, **kwargs)
                stack.enter_context(patch.object(import_module(callback.__module__), callback.__name__, observed))
        try:
            unit = call(workflow, source, deepcopy(selection), 7)
            if scenario.startswith('typed-'):
                returned = workflow.receive_form(source, deepcopy(INITIAL), deepcopy(SCHEMA), 7,
                    redelivery=scenario == 'typed-redelivery')
            if scenario.startswith(('return-', 'saved-')):
                values = [INITIAL if scenario in ('return-valid', 'saved-valid') else {'qualification': 'invented'}]
                if scenario.startswith('saved-'):
                    values.append({'qualification': 'invented'} if scenario == 'saved-valid' else INITIAL)
                for value in values:
                    try:
                        returned = asyncio.run(unit.synthesize_report(runtime.Record({'form': value}), None, unit.child.request))
                        deliveries.append({'returned': deepcopy(returned)})
                    except runtime.ReportDeliveryError as failed:
                        error = failed
                        deliveries.append({'failure': failed.feedback.as_record()})
                if error is not None:
                    returned = unit.receive_failure(error).as_record()
                    events.append('replay_begin')
                    replay = call(workflow, source, deepcopy(selection), 7)
                    replayed = replay.extract(None).as_record()
        except Exception as caught:
            error = caught
        action = host.journal.row('runtime_actions', source.episode_id, 7)
        attempts = [dict(row) for row in host.store.db.execute(
            'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
            (host.journal.run_id, source.episode_id))]
    return SimpleNamespace(events=events, owners=owners, built=built, deliveries=deliveries,
        error=None if error is None else (type(error).__name__, str(error)), injected=error is injected,
        parse_failure=error is parse_failure, expanded_failure=error is expanded_failure,
        result=returned, replayed=replayed, action=None if action is None else dict(action), attempts=attempts,
        source_outcome=source.last_outcome, source_index=source.last_outcome_index,
        feedback=source.feedback, selection=selection, has_unit=unit is not None)


def paired(host, role, scenario, *, custom_registry=False):
    with isolated_rows(host):
        old = observe(host, role, scenario, original=True, custom_registry=custom_registry)
    with isolated_rows(host):
        new = observe(host, role, scenario, original=False, custom_registry=custom_registry)
    fields = ('events', 'built', 'deliveries', 'error', 'injected', 'parse_failure', 'expanded_failure',
        'result', 'replayed', 'action', 'attempts', 'source_outcome', 'source_index', 'feedback', 'selection', 'has_unit')
    assert {name: getattr(old, name) for name in fields} == {name: getattr(new, name) for name in fields}
    assert old.owners == []
    if custom_registry:
        assert new.owners == []
    else:
        assert new.owners and new.owners[0][1] == 'prepare_request'
    return new
