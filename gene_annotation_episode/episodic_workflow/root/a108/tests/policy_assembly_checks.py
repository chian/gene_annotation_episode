"""Finite own-axis schema/report ownership controls using permanent originals.

Real Store, Workflow, source classes and registry are retained. Scientific
context admission, reasoning/catalog work and provider execution are explicit
controlled ports; this is not scientific assessment or autonomous execution.
"""
import asyncio
from contextlib import ExitStack, contextmanager
from copy import copy, deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

from . import implicit_parent_checks as original
from . import improvement_parent_checks as improvement_checks


def source_for(workflow, home):
    if home == 'improvement':
        return improvement_checks.improvement(workflow).source
    annotation = original.root(workflow).source
    if home == 'annotation':
        return annotation
    if home == 'custom':
        class CustomAnnotation(type(annotation)):
            pass
        source = copy(annotation)
        source.__class__ = CustomAnnotation
        return source
    assert home == 'scientific'
    runtime = original.module('runtime')
    request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(annotation.request.goal,
        objective='Controlled schema interface', result_contract=original.SCHEMA),
        runtime.Record({'scope': annotation.scope, 'initial_report': original.INITIAL}))
    return original.module('scientific_process/task').ScientificTask(
        workflow, annotation.path + (('scientific_process', 'schema'),), request, annotation.scope)


def owners(name):
    modules = ('internal_summary', 'annotation_improvement/internal_summary',
               'library/scientific_action_schema') if name == 'action_schema' else (
               'to_parent', 'annotation_improvement/to_parent', 'library/recorded_report_fact_assembly')
    return [original.module(module) for module in modules]


def observe_owners(stack, name, observations):
    for module in owners(name):
        callback = getattr(module, name)
        def observed(*args, _callback=callback, **kwargs):
            observations.append(_callback.__module__)
            return _callback(*args, **kwargs)
        stack.enter_context(patch.object(module, name, observed))


def paired_schema(directory, home, *, late_job=False):
    runtime = original.module('runtime')
    results, actual_owners = [], []
    for old in (True, False):
        factories = original.connected_factories() if home == 'scientific' else ()
        roles = ('scientific_process', 'literature') if factories else None
        with original.actual_workflow(directory / str(old), factories=factories,
                                      annotation_child_roles=roles) as workflow, ExitStack() as stack:
            source = source_for(workflow, home)
            events, selected = [], []
            if home == 'scientific':
                binding = workflow.scientific_process_binding
                assert workflow.specialist(source) is binding
                stack.enter_context(patch.object(binding, 'validate_context',
                    lambda context: events.append(('context_port', context.role))))
            workflow.permits_common_action = lambda actual, action: events.append(('permits', action)) or action != 'wait'
            workflow.reasoning_action_schema = lambda actual: events.append('reason_schema') or {
                'type': 'object', 'properties': {'kind': {'const': 'reason'}}}
            workflow.root_child_return_sources = lambda actual, role: ()
            workflow.root_action_boundary = None
            workflow.is_job_source = lambda actual: events.append('job_before') or False
            workflow.job_episodes = None
            def catalog(scope, *, source):
                events.append('catalog')
                if late_job:
                    workflow.is_job_source = lambda actual: events.append('job_after') or True
                return ()
            workflow.catalog = catalog
            original_object = runtime._object
            def live_object(*args, **kwargs):
                events.append('live_runtime_object')
                result = original_object(*args, **kwargs)
                result['x-controlled-live-global'] = True
                return result
            # Import all new owners before replacing the original module global.
            # A static alias captured on import would fail this comparison.
            observe_owners(stack, 'action_schema', selected)
            stack.enter_context(patch.object(runtime, '_object', live_object))
            call = original.original_function('Workflow', 'action_schema') if old else runtime.Workflow.action_schema
            value = call(workflow, source)
            assert value['x-controlled-live-global'] is True
            if late_job:
                assert events.index('catalog') < events.index('job_after')
                assert not any(branch['properties']['kind'].get('const') in
                    ('child', 'episode_child', 'job_child', 'redeliver_report')
                    for branch in value['properties']['selection']['anyOf'])
            results.append((value, events))
            actual_owners.append(selected)
    assert results[0] == results[1]
    assert actual_owners[0] == []
    expected = {'annotation': 'internal_summary', 'improvement': 'annotation_improvement.internal_summary',
                'custom': 'library.scientific_action_schema', 'scientific': 'library.scientific_action_schema'}[home]
    assert actual_owners[1] == [original.PACKAGE + '.' + expected]
    return results[1]


def paired_fallback_facts(directory, *, saved=False):
    runtime = original.module('runtime')
    results, actual_owners = [], []
    for old in (True, False):
        with original.actual_workflow(directory / str(old)) as workflow, ExitStack() as stack:
            source = source_for(workflow, 'custom')
            source.report_basis, source.last_outcome = [], None
            completion = SimpleNamespace(ended_by='controller', end_reason='controlled yield', units_consumed=2)
            events, selected = [], []
            observe_owners(stack, 'facts', selected)
            if saved:
                workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
                    'facts': json.dumps({'credit': 0.25, 'interpretations': {'old': 'context'}}), 'form': None})
                workflow.episode_bindings.current_report_facts = lambda context: events.append('current_facts') or {
                    'current_marker': 'actual late callback'}
                workflow.source_credit_view = original.forbidden
                workflow.pending_handles = original.forbidden
            else:
                workflow.specialist = lambda actual: None
                workflow.is_job_source = lambda actual: False
                def credit(actual):
                    events.append('credit')
                    workflow.is_job_source = lambda actual: True
                    return {'credit': 0.375}
                workflow.source_credit_view = credit
                workflow.pending_handles = lambda actual: events.append('pending') or ['owned-pending']
                workflow.native_timing_information = None
                workflow.resource_estimator = None
                workflow.project_annotation_score = None
                workflow.job_episodes = SimpleNamespace(facts=lambda actual, **kwargs:
                    events.append('late_job_facts') or {'job_marker': 'late original branch'})
                workflow.episode_bindings.received_report_facts = (lambda context, **kwargs:
                    events.append('received_facts') or {'received_marker': 'original receipt port'})
                original_yield = runtime.closing_yield
                def live_yield(record):
                    events.append('live_closing_yield')
                    return original_yield(record)
                stack.enter_context(patch.object(runtime, 'closing_yield', live_yield))
            call = original.original_function('Workflow', 'facts') if old else runtime.Workflow.facts
            value = call(workflow, source, completion_record=completion)
            assert 'interpretations' not in value
            if saved:
                assert events == ['current_facts'] and value['current_marker'] == 'actual late callback'
            else:
                assert value['job_marker'] == 'late original branch'
                assert events.index('credit') < events.index('late_job_facts') < events.index('received_facts')
                assert 'live_closing_yield' in events
            results.append((value, events)); actual_owners.append(selected)
    assert results[0] == results[1] and actual_owners[0] == []
    assert actual_owners[1] == [original.PACKAGE + '.library.recorded_report_fact_assembly']
    return results[1]


def paired_late_scientific_snapshot(directory, home):
    """Late binding replacement reaches the one private Scientific enrichment.

    The supplied binding's projection/invocation/credit callbacks are controlled;
    authentic journal initial credit and complete original snapshot order run.
    """
    runtime = original.module('runtime')
    results, actual_owners = [], []
    enrichment_owner = original.module('scientific_process/report_snapshot')
    for old in (True, False):
        with original.actual_workflow(directory / str(old)) as workflow, ExitStack() as stack:
            source = source_for(workflow, home)
            source.report_basis, source.last_outcome = [], None
            completion = SimpleNamespace(ended_by='controller', end_reason='controlled yield', units_consumed=2)
            events, selected, enriched = [], [], []
            observe_owners(stack, 'facts', selected)
            original_enrich = enrichment_owner.enrich_report_snapshot
            def observed(*args):
                enriched.append('scientific_private_snapshot')
                return original_enrich(*args)
            stack.enter_context(patch.object(enrichment_owner, 'enrich_report_snapshot', observed))
            workflow.specialist = lambda actual: None
            workflow.is_job_source = lambda actual: False
            workflow.native_timing_information = None
            workflow.resource_estimator = None
            workflow.project_annotation_score = None
            workflow.pending_handles = lambda actual: events.append('pending') or []
            workflow.source_credit_view = lambda actual: events.append('credit') or {'credit': 0.375}
            workflow.source_controller_credit = lambda actual: events.append('controller_credit') or 0.125
            stack.enter_context(patch.object(workflow.services, 'scientific_parent_invocation',
                lambda context: events.append('parent_invocation') or 'controlled_original_invocation'))
            def project(context, snapshot):
                events.append(('typed_projection_port', deepcopy(snapshot)))
                assert snapshot['controller_credit'] == 0.125
                assert snapshot['credit'] == 0.375
                assert snapshot['parent_invocation_ref'] == 'controlled_original_invocation'
                assert snapshot['initial_credit'] == workflow.journal.row(
                    'runtime_episodes', source.episode_id)['initial_credit']
                return {'projected_marker': 'controlled Scientific projection'}
            late_binding = SimpleNamespace(facts=project)
            prior_snapshot = workflow.store.read_snapshot
            @contextmanager
            def read_snapshot():
                events.append('snapshot_entry')
                with prior_snapshot():
                    workflow.scientific_process_binding = late_binding
                    workflow.specialist = lambda actual: late_binding
                    yield
            workflow.store.read_snapshot = read_snapshot
            workflow.episode_bindings.received_report_facts = (lambda context, **kwargs:
                events.append('received_facts') or {'received_marker': 'original receipt port'})
            call = original.original_function('Workflow', 'facts') if old else runtime.Workflow.facts
            value = call(workflow, source, completion_record=completion)
            assert value['projected_marker'] == 'controlled Scientific projection'
            assert events.index('snapshot_entry') < events.index('credit') < events.index('controller_credit')
            assert events.index('controller_credit') < events.index('parent_invocation') < events.index('received_facts')
            results.append((value, events)); actual_owners.append((selected, enriched))
    assert results[0] == results[1] and actual_owners[0] == ([], [])
    expected = {'annotation': 'to_parent', 'improvement': 'annotation_improvement.to_parent',
                'custom': 'library.recorded_report_fact_assembly'}[home]
    assert actual_owners[1] == ([original.PACKAGE + '.' + expected], ['scientific_private_snapshot'])
    return results[1]


def private_next_override(directory, home, placement):
    """Actual private next reaches the unchanged dynamic Workflow method lookup.

    The snapshot and provider call are controlled ports. The provider sentinel
    stops before any selected action; this does not claim model execution.
    """
    runtime = original.module('runtime')
    with original.actual_workflow(directory) as workflow, ExitStack() as stack:
        source = source_for(workflow, home)
        task_module = original.module('task' if home == 'annotation' else 'annotation_improvement/task')
        snapshot_name = 'annotation_decision_snapshot' if home == 'annotation' else 'improvement_decision_snapshot'
        stack.enter_context(patch.object(task_module, snapshot_name,
            lambda actual, view: {'explicit_snapshot_port': home}))
        workflow.inprocess_replay = workflow.execution_binding = None
        source._execution_context = None
        events, marker = [], {'controlled_schema_override': placement}
        def overridden(actual):
            assert actual is source
            events.append('workflow_override')
            return marker
        if placement == 'instance':
            stack.enter_context(patch.object(workflow, 'action_schema', overridden))
        else:
            assert placement == 'class'
            def class_override(actual_workflow, actual):
                assert actual_workflow is workflow
                return overridden(actual)
            stack.enter_context(patch.object(runtime.Workflow, 'action_schema', class_override))
        for module in owners('action_schema'):
            stack.enter_context(patch.object(module, 'action_schema', original.forbidden))
        class ProviderStop(Exception):
            pass
        async def provider(context, schema):
            assert context == {'explicit_snapshot_port': home} and schema is marker
            events.append('provider_port')
            raise ProviderStop
        stack.enter_context(patch.object(source, 'call', provider))
        try:
            asyncio.run(source.next(SimpleNamespace(units_consumed=0)))
        except ProviderStop:
            pass
        else:
            raise AssertionError('controlled provider sentinel was not reached')
        assert events == ['workflow_override', 'provider_port']
        assert list(workflow.store.db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=?',
                                             (workflow.run_id, source.episode_id))) == []
