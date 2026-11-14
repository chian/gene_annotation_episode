"""Actual unregistered improvement boundaries against retained own-axis code."""
import asyncio
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
from unittest.mock import patch

from . import implicit_parent_checks as original

ROOT_BUILDER = original.root


def improvement(workflow, *, key='improvement', original_build=False, recursive=False,
                supplied_initial_credit=True):
    runtime = original.module('runtime')
    build = original.original_function('Workflow', 'build') if original_build else runtime.Workflow.build
    parent = ROOT_BUILDER(workflow, original=original_build)
    scope = parent.source.scope
    contract = runtime.TypedReportContract('Retain actual uncertainty', deepcopy(original.SCHEMA), lambda *args: True)
    # The original default rejects an undeclared nested credit projector. These
    # positive boundary fixtures explicitly supply only that contextual port
    # during construction; the real source_credit_view/projection machinery and
    # actual journal still execute. Restore the original selector immediately.
    original_selector = workflow.scientific_projector_for_context
    def contextual_projector(context):
        if context.role == 'improvement' and len(context.path) > 1:
            return workflow.project_credit
        return original_selector(context)
    credit_port = (patch.object(workflow, 'scientific_projector_for_context', contextual_projector)
                   if supplied_initial_credit else nullcontext())
    with credit_port:
        child = build(workflow, 'improvement', key, 'Existing iterative improvement', scope,
                      parent=parent.source.request.goal, parent_path=parent.source.path,
                      contract=contract, initial=deepcopy(original.INITIAL))
        if recursive:
            child = build(workflow, 'improvement', key + '_recursive', 'Existing recursive improvement', scope,
                          parent=child.source.request.goal, parent_path=child.source.path,
                          contract=contract, initial=deepcopy(original.INITIAL))
    assert workflow.scientific_projector_for_context == original_selector
    return child


def connected(directory, parent_kind, scenario, *, old, custom_registry=False):
    """Real selected TimedChildUnit, actual report contract and original journal.

    Child execution and numerical credit are explicitly controlled ports. The
    original scope/resolver/semantic initial report path still executes.
    """
    runtime = original.module('runtime')
    events, owners, built = [], [], []
    with original.actual_workflow(directory) as workflow:
        source = (ROOT_BUILDER(workflow, original=old).source if parent_kind == 'annotation'
                  else improvement(workflow, original_build=old).source)
        if custom_registry:
            registry = workflow.episode_bindings
            class CustomRegistry(type(registry)):
                @property
                def roles(self):
                    events.append('custom_registry_roles')
                    return super().roles
            workflow.episode_bindings = CustomRegistry(registry._bindings)
        workflow.episode_branch_lifecycle = runtime.EPISODE_BRANCH_LIFECYCLE if scenario == 'saved-return' else None
        workflow.receipts = None
        workflow.wait_inputs_version = None
        workflow.completed_action_inputs_version = None
        workflow.root_action_boundary = None
        workflow.validate_child_choice = lambda *args, **kwargs: events.append('validate_child_choice')
        workflow.permits_common_action = lambda *args: args[-1] != 'wait'
        workflow._closed_child_commission = lambda *args: None
        original_assignment = {'original_job_assignment': 'actual late callback result'}
        def expanded(actual_source, selection, index, role):
            events.append('expanded_form')
            if scenario == 'late-job-kind':
                assert selection['kind'] == 'child'
                selection['kind'] = 'job_child'
                def assign(store, actual_role, actual_selection, scope, **kwargs):
                    assert actual_role == 'improvement' and actual_selection['kind'] == 'job_child'
                    events.append('late_job_assignment')
                    return original_assignment
                workflow.job_episodes = SimpleNamespace(roles=(), assign=assign)
            return deepcopy(original.SCHEMA), None
        workflow.expanded_contract_form = expanded
        workflow.child_initial_report_input = lambda *args: json.dumps(original.INITIAL)
        def resolver(*args, **kwargs):
            events.append(('resolver', kwargs.get('grain')))
            return lambda *args: True
        workflow.resolver = resolver
        workflow.validate_report = lambda value, scope, **kwargs: events.append(('validate_report', deepcopy(value)))
        workflow.source_credit_view = lambda actual: events.append('original_credit') or {'credit': 0.375}
        workflow.controller_value = lambda actual, index, value: runtime.Record({'original_credit': value})
        workflow.receive_form = lambda actual, form, schema, index, **kwargs: events.append(
            ('receive_form', deepcopy(form), index, kwargs)) or []
        def build(role, key, objective, scope, **kwargs):
            events.append('build')
            assert role == 'improvement'
            assert kwargs['episode_assignment'] is kwargs['scientific_process'] is None
            assert kwargs['job_assignment'] is (original_assignment if scenario == 'late-job-kind' else None)
            request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(kwargs['parent'],
                objective=objective, result_contract=original.SCHEMA),
                runtime.Record({'scope': scope, 'initial_report': kwargs['initial']}), kwargs['contract'])
            path = kwargs['parent_path'] + ((role, key),)
            cls = runtime.DecisionSource if old else original.module('annotation_improvement/task').ImprovementTask
            child_source = cls(workflow, path, request, scope)
            built.append({'path': path, 'request': request.as_record(), 'job_assignment': kwargs['job_assignment']})
            return runtime.Episode(workflow.grains[role], key, child_source, request, original.forbidden)
        workflow.build = build
        selection = {'kind': 'child', 'scope': deepcopy(source.scope),
            'goal': 'Original iterative child objective',
            'purpose': 'Retain an unresolved qualification',
            'schema_json': json.dumps(original.SCHEMA),
            'initial_report_json': json.dumps(original.INITIAL)}
        # Observe the actual current endpoint definitions even for the original
        # comparison. The authentic original code must never call those owners.
        prefix = '' if parent_kind == 'annotation' else 'annotation_improvement/'
        outgoing = original.module(prefix + 'to_child_annotation_improvement')
        incoming = original.module(prefix + 'from_child_annotation_improvement')
        callbacks = (outgoing.prepare_request, incoming.admit_return, incoming.admit_unowned_return)
        events.clear()
        with ExitStack() as stack:
            for callback in callbacks:
                def observed(*args, _callback=callback, **kwargs):
                    owners.append((_callback.__module__, _callback.__name__))
                    return _callback(*args, **kwargs)
                stack.enter_context(patch.object(import_module(callback.__module__), callback.__name__, observed))
            call = original.original_function('Workflow', 'selected') if old else runtime.Workflow.selected
            unit = call(workflow, source, deepcopy(selection), 7)
            form = {'qualification': 'invented'} if scenario == 'invalid-return' else original.INITIAL
            failure = None
            try:
                result = asyncio.run(unit.synthesize_report(runtime.Record({'form': form}), None, unit.child.request))
                if scenario == 'saved-return':
                    assert asyncio.run(unit.synthesize_report(runtime.Record({'form': form}), None,
                                                             unit.child.request)) == result
            except runtime.ReportDeliveryError as error:
                failure = original.error_record(error)
                result = unit.receive_failure(error).as_record()
            action = dict(workflow.journal.row('runtime_actions', source.episode_id, 7))
            attempts = [dict(row) for row in workflow.store.db.execute(
                'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
                (workflow.run_id, source.episode_id))]
        return {'events': events, 'owners': owners, 'built': built, 'action': action,
                'attempts': attempts, 'result': result, 'failure': failure,
                'last_outcome': source.last_outcome, 'last_outcome_index': source.last_outcome_index,
                'feedback': source.feedback}


def paired_connected(directory, parent_kind, scenario, *, custom_registry=False):
    before = connected(directory / 'old', parent_kind, scenario, old=True, custom_registry=custom_registry)
    after = connected(directory / 'new', parent_kind, scenario, old=False, custom_registry=custom_registry)
    assert {k: v for k, v in before.items() if k != 'owners'} == {k: v for k, v in after.items() if k != 'owners'}
    assert before['owners'] == []
    assert bool(after['owners']) is (not custom_registry)
    return after
