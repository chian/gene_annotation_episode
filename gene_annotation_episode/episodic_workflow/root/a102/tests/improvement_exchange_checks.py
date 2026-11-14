"""Actual unregistered improvement boundaries with explicit external ports.

No Workflow initializer, model, native operation or complete restoration is
claimed. Store/Journal/Context/Task/selected/typed contract are actual owners.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
from unittest.mock import patch

from .. import runtime
from ..episode_bindings import EpisodeBindingRegistry
from ..task import AnnotationTask
from ..annotation_improvement.task import ImprovementTask
from ..annotation_improvement import child_message_owners
from .annotation_parent_exchange_checks import INITIAL, SCHEMA, forbidden, isolated_rows
from .annotation_parent_original_boundaries import original_method
from ..annotation_improvement.tests.improvement_host_checks import host_workflow


SCENARIOS = ('request-valid', 'initial-invalid', 'return-valid', 'return-invalid',
             'saved-valid', 'saved-failure', 'mutable-global', 'expanded-error')


def observe(host, parent_role, scenario, *, original=False, custom_registry=False,
            unsupported_registered=False, scientific_bound=False, late_kind=None):
    events, owners, built, deliveries = [], [], [], []
    workflow = host_workflow(host, events)
    class CustomRegistry(EpisodeBindingRegistry):
        @property
        def roles(self):
            events.append('custom_roles')
            return super().roles
    if unsupported_registered:
        from ..resource_work_submission.episode import ResourceEpisode
        registry = EpisodeBindingRegistry((ResourceEpisode(host.services),))
    else:
        registry = (CustomRegistry if custom_registry else EpisodeBindingRegistry)(())
    workflow.episode_bindings = registry
    if scientific_bound:
        from ..scientific_process.episode import ScientificProcessEpisode
        from .annotation_parent_exchange_checks import EmptyCatalog
        workflow.scientific_process_binding = ScientificProcessEpisode(host.services,
            library=EmptyCatalog(), tool_library=EmptyCatalog(), child_roles=('scientific_process',))
    workflow.root_action_boundary = None
    workflow.episode_branch_lifecycle = runtime.EPISODE_BRANCH_LIFECYCLE if scenario.startswith('saved-') else None
    path = (('annotation', 'parent'),) if parent_role == 'annotation' else (
        ('annotation', 'root'), ('improvement', 'parent'))
    request = runtime.EpisodeRequest(runtime.EpisodeGoal.root(objective='Actual conditional parent',
        result_contract=SCHEMA), runtime.Record({'scope': host.scope, 'initial_report': INITIAL}))
    task = runtime.DecisionSource if original else AnnotationTask if parent_role == 'annotation' else ImprovementTask
    source = task(workflow, path, request, host.scope)
    constructor_events = tuple(events)
    events.clear()
    parse_error = RuntimeError('original mutable parser object')
    expanded_error = RuntimeError('original expansion object')
    late_error = RuntimeError('actual late job assignment object')
    active_selection = {}
    def expanded(*args, **kwargs):
        events.append('expanded_form')
        active_selection['value'] = args[1]
        if late_kind == 'expanded':
            args[1]['kind'] = 'episode_child'
            events.append('expanded_mutated_episode_child')
        if scenario == 'expanded-error':
            raise expanded_error
        return deepcopy(SCHEMA), None
    def parse(*args, **kwargs):
        events.append('mutable_runtime_parser')
        raise parse_error
    def resolver(*args, **kwargs):
        events.append(('resolver', kwargs.get('grain')))
        return lambda *args: True
    def validate(value, scope, **kwargs):
        events.append(('validate_report', deepcopy(value), kwargs['grain']))
    def build(role, key, objective, scope, **kwargs):
        events.append('build')
        assert role == 'improvement'
        assert kwargs['job_assignment'] is kwargs['episode_assignment'] is kwargs['scientific_process'] is None
        child_request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(kwargs['parent'],
            objective=objective, result_contract=SCHEMA), runtime.Record({'scope': scope,
            'initial_report': kwargs['initial']}), kwargs['contract'])
        child_path = kwargs['parent_path'] + ((role, key),)
        child_task = runtime.DecisionSource if original else ImprovementTask
        child_source = child_task(workflow, child_path, child_request, scope)
        built.append({'path': child_path, 'request': child_request.as_record()})
        return runtime.Episode(host.grains[role], key, child_source, child_request, forbidden)
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
    def initial_input(actual, selected, selected_role):
        if late_kind == 'initial':
            selected['kind'] = 'job_child'
            events.append('initial_mutated_job_child')
        return json.dumps({'qualification': 'invented'} if scenario == 'initial-invalid' else INITIAL)
    workflow.child_initial_report_input = initial_input
    if late_kind == 'initial':
        def assign(store, selected_role, selected, scope, **kwargs):
            assert store is host.store and selected is active_selection['value']
            events.append(('actual_job_assign', selected_role, selected['kind'], kwargs))
            raise late_error
        workflow.job_episodes = SimpleNamespace(roles=(), assign=assign)
    workflow.build = build
    workflow.resolver = resolver
    workflow.validate_report = validate
    workflow.receive_form = receive
    workflow.source_credit_view = credit
    workflow.controller_value = lambda actual, index, value: runtime.Record({'original_credit': value})
    workflow.resolve_pending_deliveries = unresolved
    role = 'launch' if unsupported_registered else 'improvement'
    selection = {'kind': 'episode_child' if unsupported_registered else 'child',
        'scope': deepcopy(host.scope), 'goal': 'Original recursive improvement',
        'purpose': 'Typed unresolved qualification'}
    if unsupported_registered:
        selection.update(role=role, assignment={})
    nominal = (AnnotationTask if parent_role == 'annotation' else ImprovementTask)(workflow, path, request, host.scope)
    exchange = child_message_owners.exchange_for_child(workflow, nominal, role)
    assert (exchange is None) is (custom_registry or unsupported_registered or scientific_bound)
    assert events == [], 'nominal selector cannot call a registry/provider port'
    call = original_method('selected') if original else runtime.Workflow.selected
    error, returned, unit, replayed = None, None, None, None
    with ExitStack() as stack:
        if late_kind == 'contract':
            original_contract = runtime.TypedReportContract
            def contract(*args, **kwargs):
                value = original_contract(*args, **kwargs)
                active_selection['value']['kind'] = 'episode_child'
                events.append('contract_mutated_episode_child')
                return value
            stack.enter_context(patch.object(runtime, 'TypedReportContract', contract))
            if original:
                call = original_method('selected')
        if scenario == 'mutable-global':

            stack.enter_context(patch.object(runtime, 'parse_json_object', parse))
            if original:
                call = original_method('selected')
        if exchange is not None:
            for callback in exchange:
                def observed(*args, _callback=callback, **kwargs):
                    owners.append((_callback.__module__, _callback.__name__))
                    return _callback(*args, **kwargs)
                stack.enter_context(patch.object(import_module(callback.__module__), callback.__name__, observed))
        try:
            unit = call(workflow, source, deepcopy(selection), 7)
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
    return dict(events=events, owners=owners, built=built, deliveries=deliveries,
        constructor_events=constructor_events,
        error=None if error is None else (type(error).__name__, str(error)),
        parse_error=error is parse_error, expanded_error=error is expanded_error,
        late_error=error is late_error, mutated_kind=active_selection.get('value', {}).get('kind'),
        result=returned, replayed=replayed, action=None if action is None else dict(action),
        attempts=attempts, source_outcome=source.last_outcome, source_index=source.last_outcome_index,
        feedback=source.feedback, selection=selection, has_unit=unit is not None)


def paired(host, parent_role, scenario, **kwargs):
    with isolated_rows(host):
        old = observe(host, parent_role, scenario, original=True, **kwargs)
    with isolated_rows(host):
        new = observe(host, parent_role, scenario, original=False, **kwargs)
    assert {k: v for k, v in old.items() if k != 'owners'} == {k: v for k, v in new.items() if k != 'owners'}
    assert old['owners'] == []
    if any(value for name, value in kwargs.items() if name != 'late_kind'):
        assert new['owners'] == []
    else:
        assert new['owners'] and new['owners'][0][1] == 'prepare_request'
    return new
