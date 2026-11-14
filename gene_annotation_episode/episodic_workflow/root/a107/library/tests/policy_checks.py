"""Actual parent/binding policy comparisons; only named external ports supplied.

Reusable control infrastructure for the standalone axis policy library. No
scientific calculation, native launch, provider model or child iterator runs.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

from ...tests import test_implicit_annotation_parent as original
from ...tests.scientific_parent_live_globals_checks import EmptyCatalog
from ...annotation_improvement.tests.host_checks import build


def oracle(name):
    runtime = original.module('runtime')
    value = original.original_function(runtime, 'Workflow', name)
    result = FunctionType(value.__code__, vars(runtime), value.__name__, value.__defaults__)
    result.__kwdefaults__ = value.__kwdefaults__
    return result


def scientific_binding(workflow):
    return original.module('scientific_process.episode').ScientificProcessEpisode(
        workflow.services, library=EmptyCatalog(), tool_library=EmptyCatalog(),
        child_roles=('scientific_process',))


def source_for(workflow, role):
    runtime = original.module('runtime')
    if role != 'scientific_process':
        _, source = build(workflow, role=role)
        return source, None
    binding = scientific_binding(workflow)
    original.install_entry(workflow, binding)
    workflow.grains[role] = runtime.Grain(role, 'Actual controlled scientific role',
        'Original typed result', original.forbidden)
    scope = workflow.store.validate_scope()
    request = runtime.EpisodeRequest(runtime.EpisodeGoal.root(
        objective='Observe real policy assembly without scientific execution', result_contract={}),
        runtime.Record({'scope': scope, 'initial_report': {}, 'episode_assignment': {}}), None)
    source = binding.decision_source_type(workflow, ((role, 'policy-parent'),), request, scope)
    workflow.journal.save('runtime_episodes', {'episode_id': source.episode_id,
        'path': runtime._json(source.path), 'request': runtime._json(request.as_record()),
        'initial_credit': 1.0, 'state': 'active', 'completion': None, 'archive': None})
    return source, binding


def action_observation(directory, role, scenario, *, before):
    runtime = original.module('runtime')
    with original.actual_workflow(directory) as workflow, ExitStack() as stack:
        source, binding = source_for(workflow, role)
        # This catalogue-boundary fixture supplies receipt availability. The
        # genuine annotation root filter otherwise excludes tools before the
        # intended catalogue callback; known() is the real BindingContext port.
        workflow.receipts = SimpleNamespace(known=lambda episode_id: ())
        events, owned = [], []
        marker = RuntimeError('original late action-form callback')
        target = ('action_policy' if role == 'annotation' else
                  'annotation_improvement.action_policy' if role == 'improvement' else
                  'library.workflow_report_action_policy')
        owner = original.module(target)
        genuine = owner.action_schema
        def observe(*args, **kwargs):
            owned.append((genuine.__module__, genuine.__name__))
            return genuine(*args, **kwargs)
        stack.enter_context(patch.object(owner, 'action_schema', observe))
        if binding is not None:
            # Genuine configured role/admission/schema methods run; only the
            # filled scientific context validator is an explicit supplied port.
            stack.enter_context(patch.object(binding, 'validate_context',
                lambda context: events.append(('filled_context', context.role))))
        def reasoning(actual, *args, **kwargs):
            assert actual is source; events.append('reasoning')
            return {'type': 'object', 'properties': {'kind': {'type': 'string', 'const': 'reason'}}}
        stack.enter_context(patch.object(workflow, 'reasoning_action_schema', reasoning))
        original_json = runtime._json
        stack.enter_context(patch.object(runtime, '_json', original_json))
        def catalog(scope, *, source):
            events.append('catalog')
            if scenario == 'late-binding':
                workflow.scientific_process_binding = object()
            if scenario == 'late-json-error':
                def reject(value):
                    events.append('late_json'); raise marker
                runtime._json = reject
            return [{'name': 'controlled.lookup', 'input_schema': {'type': 'object',
                'properties': {}, 'required': [], 'additionalProperties': False}}]
        stack.enter_context(patch.object(workflow, 'catalog', catalog))
        selected = oracle('action_schema') if before else runtime.Workflow.action_schema
        try:
            result = selected(workflow, source)
            outcome = ('returned', deepcopy(result))
        except RuntimeError as error:
            assert error is marker
            outcome = ('raised', type(error).__name__, str(error), error is marker)
        assert owned == ([] if before else [(runtime.__package__ + '.' + target, 'action_schema')])
        return {'events': events, 'outcome': outcome}


def report_observation(directory, role, scenario, *, before):
    runtime = original.module('runtime')
    with original.actual_workflow(directory) as workflow, ExitStack() as stack:
        source, binding = source_for(workflow, role)
        if binding is None:
            binding = scientific_binding(workflow)
            # The private owner must already be selected before the credit
            # callback changes the late Scientific identity predicate.
            assert workflow.scientific_process_binding is None
            stack.enter_context(patch.object(workflow, 'specialist', lambda actual: binding))
        events, owned = [], []
        marker = LookupError('original saved report read')
        owner = original.module('scientific_process.report_snapshot')
        library = original.module('library.workflow_report_action_policy')
        genuine = owner.complete_scientific_snapshot
        def snapshot(*args, **kwargs):
            owned.append(genuine.__module__)
            return genuine(*args, **kwargs)
        stack.enter_context(patch.object(owner, 'complete_scientific_snapshot', snapshot))
        stack.enter_context(patch.object(library, '_complete_scientific_snapshot', snapshot))
        actual_row = workflow.journal.row
        def row(table, *keys):
            if table == 'runtime_forms':
                events.append('saved_read')
                if scenario == 'saved-read-error': raise marker
            return actual_row(table, *keys)
        stack.enter_context(patch.object(workflow.journal, 'row', row))
        def credit(actual, **kwargs):
            assert actual is source; events.append(('credit', sorted(kwargs)))
            if role != 'scientific_process':
                events.append('late_scientific_identity')
                workflow.scientific_process_binding = binding
            return {'credit': 2.0}
        stack.enter_context(patch.object(workflow, 'source_credit_view', credit))
        stack.enter_context(patch.object(workflow, 'pending_handles', lambda actual: []))
        stack.enter_context(patch.object(workflow, 'source_controller_credit', lambda actual: 'supplied controller meaning'))
        stack.enter_context(patch.object(workflow.services, 'scientific_parent_invocation',
            lambda context: 'supplied original parent invocation', create=True))
        def projection(context, snapshot):
            events.append(('scientific_projection', deepcopy(snapshot)))
            return {'supplied_scientific_qualification': 'unresolved'}
        stack.enter_context(patch.object(binding, 'facts', projection))
        registry = workflow.episode_bindings
        stack.enter_context(patch.object(registry, 'current_report_facts',
            lambda context: events.append('saved_refresh') or {'supplied_current_view': 'unresolved'}))
        stack.enter_context(patch.object(registry, 'received_report_facts',
            lambda context, **kwargs: {'credit': 99.0} if scenario == 'received-conflict' else {}))
        workflow.project_annotation_score = None
        workflow.resource_estimator = None
        workflow.native_timing_information = None
        source.last_outcome = {'record_refs': [source.scope['subject_refs'][0]]}
        source.report_basis = []
        if scenario == 'saved':
            workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
                'facts': runtime._json({'credit': 2.0, 'interpretations': {'old': True}}), 'form': None})
            stack.enter_context(patch.object(workflow, 'source_credit_view', original.forbidden))
        completion = SimpleNamespace(ended_by='yielded', end_reason='original-controller', units_consumed=1)
        selected = oracle('facts') if before else runtime.Workflow.facts
        try:
            answer = selected(workflow, source, completion_record=completion)
            outcome = ('returned', deepcopy(answer))
        except (LookupError, ValueError) as error:
            if scenario == 'saved-read-error': assert error is marker
            else: assert scenario == 'received-conflict' and str(error) == 'received_report_fact_conflict'
            outcome = ('raised', type(error).__name__, str(error), error is marker)
        expected = [] if before or scenario in ('saved', 'saved-read-error') else [runtime.__package__ + '.scientific_process.report_snapshot']
        assert owned == expected
        return {'events': events, 'outcome': outcome}


def paired(tmp_path, observer, role, scenario):
    before = observer(tmp_path / 'original', role, scenario, before=True)
    current = observer(tmp_path / 'current', role, scenario, before=False)
    assert current == before
    return current


def actual_private_override(directory, kind):
    runtime = original.module('runtime')
    with original.actual_workflow(directory) as workflow, ExitStack() as stack:
        source, _ = source_for(workflow, 'annotation')
        events = []
        marker = LookupError('actual private task schema override')
        def override(actual):
            assert actual is source; events.append('override'); raise marker
        if kind == 'class':
            def selected(self, actual):
                assert self is workflow
                return override(actual)
            stack.enter_context(patch.object(runtime.Workflow, 'action_schema', selected))
        else:
            stack.enter_context(patch.object(workflow, 'action_schema', override))
        # Stop at the original schema call, before any provider call. Supplying
        # the summary input port does not replace the actual private next body.
        task = original.module('task')
        context_name = 'annotation_decision_snapshot' if original.AXIS == 'a107' else 'decision_snapshot'
        stack.enter_context(patch.object(task, context_name, lambda actual, view: {}))
        workflow.execution_binding = None
        workflow.inprocess_replay = None
        source._execution_context = None
        try:
            asyncio.run(source.next(SimpleNamespace(units_consumed=0)))
        except LookupError as error:
            assert error is marker
        else:
            raise AssertionError('private task bypassed the method override')
        assert events == ['override']
