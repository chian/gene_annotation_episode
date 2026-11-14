"""Actual commissioning-parent exchanges with the existing improvement child.

Authenticated original runtime fixtures remain shared axis test infrastructure.
Host construction/oracle primitives are supplied by the child owner's test helper.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch
from . import test_implicit_annotation_parent as original
from ..annotation_improvement.tests.host_checks import method, build, paired, owner_calls, SCHEMA, INITIAL


def exchange(workflow, parent_role, scenario, *, before, callback=None, custom=False):
    runtime = original.module('runtime')
    registry_type = original.module('episode_bindings').EpisodeBindingRegistry
    if custom:
        class CustomRegistry(registry_type): pass
        workflow.episode_bindings = CustomRegistry(())
    # Named external projection port isolates the typed boundary. The default
    # nested-projector error is retained in nested_refusal above.
    workflow.source_credit_view = lambda _source, **kw: {'credit': -0.25}
    call_build = method('Workflow', 'build') if before else runtime.Workflow.build
    parent = call_build(workflow, parent_role, 'parent', 'Original parent', workflow.store.validate_scope()).source
    if before:
        parent = original.original_source_class(runtime)(workflow, parent.path, parent.request, parent.scope)
    workflow.root_action_boundary = None
    events, owners, built = [], [], []
    active = {}
    expanded_error = RuntimeError('original expansion error')
    parse_error = RuntimeError('original live parser error')
    job_error = RuntimeError('original late job assignment error')
    def expanded(actual, selection, index, role):
        assert actual is parent
        active['selection'] = selection; events.append('expanded')
        if callback == 'expanded': selection['kind'] = 'episode_child'; events.append('expanded_kind')
        if scenario == 'expanded-error': raise expanded_error
        return deepcopy(SCHEMA), None
    def initial(actual, selection, role):
        events.append('initial')
        if callback == 'initial': selection['kind'] = 'job_child'; events.append('initial_kind')
        return json.dumps({'qualification': 'invented'} if scenario == 'initial-invalid' else INITIAL)
    workflow.expanded_contract_form = expanded
    workflow.child_initial_report_input = initial
    def resolver(*args, **kwargs):
        events.append(('resolver', kwargs.get('grain'))); return lambda *_: True
    def validate(value, scope, **kwargs): events.append(('validate', deepcopy(value), kwargs['grain']))
    workflow.resolver = resolver; workflow.validate_report = validate
    workflow.progress_provider = SimpleNamespace(receive_form=lambda *args: events.append(('progress', deepcopy(args))))
    def traced_build(*args, **kwargs):
        events.append('build')
        child = call_build(workflow, *args, **kwargs)
        built.append(child.request.as_record()); return child
    workflow.build = traced_build
    if callback == 'initial':
        def assign(store, role, selection, scope, **kwargs):
            assert store is workflow.store and selection is active['selection']
            events.append(('assign', role, selection['kind'], kwargs)); raise job_error
        workflow.job_episodes = SimpleNamespace(roles=(), assign=assign)
    async def unresolved(actual, view, **kwargs):
        assert actual is parent
        events.append('pending_resolution'); raise runtime.ReportDeliveryError(runtime.Record(parent.feedback))
    workflow.resolve_pending_deliveries = unresolved
    selection = {'kind': 'child', 'scope': deepcopy(parent.scope),
        'goal': 'Retain original recursive improvement', 'purpose': 'Typed unresolved qualification'}
    prefix = '' if parent_role == 'annotation' else 'annotation_improvement/'
    names = [(prefix+'to_child_annotation_improvement', 'prepare_request'), (prefix+'from_child_annotation_improvement', 'receive_report')]
    error = unit = returned = None; deliveries = []
    with ExitStack() as stack:
        stack.enter_context(owner_calls(names, owners))
        if scenario == 'mutable-global':
            def parse(*args): events.append('parser'); raise parse_error
            stack.enter_context(patch.object(runtime, 'parse_json_object', parse))
        if callback == 'contract':
            actual_contract = runtime.TypedReportContract
            def contract(*args, **kwargs):
                value = actual_contract(*args, **kwargs)
                active['selection']['kind'] = 'episode_child'; events.append('contract_kind'); return value
            stack.enter_context(patch.object(runtime, 'TypedReportContract', contract))
        call = method('Workflow', 'selected') if before else runtime.Workflow.selected
        try:
            unit = call(workflow, parent, deepcopy(selection), 7)
            if scenario.startswith(('return-', 'saved-')):
                values = [INITIAL if scenario in ('return-valid', 'saved-valid') else {'qualification': 'invented'}]
                if scenario.startswith('saved-'):
                    values.append({'qualification': 'invented'} if scenario == 'saved-valid' else INITIAL)
                for value in values:
                    try:
                        returned = asyncio.run(unit.synthesize_report(runtime.Record({'form': value}), None, unit.child.request))
                        deliveries.append(('returned', deepcopy(returned)))
                    except runtime.ReportDeliveryError as actual:
                        error = actual; deliveries.append(('failure', actual.feedback.as_record()))
        except Exception as actual:
            error = actual
    action = workflow.journal.row('runtime_actions', parent.episode_id, 7)
    attempts = [dict(row) for row in workflow.store.db.execute(
        'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
        (workflow.run_id, parent.episode_id))]
    if not before and not custom: assert owners and owners[0][1] == 'prepare_request'
    if before or custom: assert owners == []
    return {'events': events, 'owners': owners, 'built': built, 'deliveries': deliveries,
        'has_unit': unit is not None, 'returned': returned,
        'error': None if error is None else (type(error).__name__, str(error)),
        'parse_error': error is parse_error, 'expanded_error': error is expanded_error, 'job_error': error is job_error,
        'mutated_kind': active.get('selection', {}).get('kind'),
        'action': None if action is None else dict(action), 'attempts': attempts, 'feedback': parent.feedback}


def received(workflow, parent_role, *, before):
    runtime = original.module('runtime')
    _, source = build(workflow, parent_role, before=before)
    events, owners = [], []
    workflow.progress_provider = SimpleNamespace(receive_form=lambda *args: events.append(deepcopy(args)))
    call = method('Workflow', '_receive_form') if before else runtime.Workflow._receive_form
    prefix = '' if parent_role == 'annotation' else 'annotation_improvement/'
    with owner_calls([(prefix+'from_child_annotation_improvement', 'receive_report')], owners):
        result = call(workflow, source, deepcopy(INITIAL), deepcopy(SCHEMA), 9, redelivery=True, child_role='improvement')
    assert result == [] and len(events) == 1
    assert len(owners) == (0 if before else 1)
    return {'result': result, 'events': events, 'owners': owners}


def refused_choice(workflow, kind, *, before):
    runtime = original.module('runtime')
    _, source = build(workflow, 'annotation' if kind == 'scientific' else 'improvement', before=before)
    selection = {'kind': 'child', 'scope': source.scope, 'goal': 'Preserve actual unavailable route', 'purpose': 'No invented owner'}
    if kind == 'scientific':
        class EmptyCatalog:
            def as_record(self): return {'fixture': 'no scientific operations'}
            def headers(self): return ()
            resolve = staticmethod(original.forbidden)
        workflow.scientific_process_binding = original.module('scientific_process.episode').ScientificProcessEpisode(
            workflow.services, library=EmptyCatalog(), tool_library=EmptyCatalog(), child_roles=('scientific_process',))
    else:
        owner = original.constructed_entry(workflow, workflow.directory / 'entry', original.ROUTES[0])
        original.install_entry(workflow, owner)
        selection.update(kind='episode_child', role='launch', assignment={})
    events = []
    workflow.expanded_contract_form = lambda *a: events.append('expanded') or (deepcopy(SCHEMA), None)
    call = method('Workflow', 'selected') if before else runtime.Workflow.selected
    try: call(workflow, source, selection, 7)
    except (ValueError, LookupError) as error: result = (type(error).__name__, str(error))
    else: raise AssertionError('original unavailable route was admitted')
    expected = ('ValueError', 'scientific_child_requires_filled_process') if kind == 'scientific' else ('LookupError', 'episode_role_not_bound:improvement')
    assert result == expected
    assert events == ([] if kind == 'scientific' else ['expanded'])
    assert workflow.journal.row('runtime_actions', source.episode_id, 7) is None
    return {'error': result, 'events': events}


def custom_operand_order(workflow, operand, *, before):
    """Compare original callbacks before the real expansion error boundary.

    Custom string operands are passed unchanged to actual selected/validation.
    Only the supplied expansion callback stops this observation; no child job
    or scientific operation is acquired.
    """
    runtime = original.module('runtime')
    _, source = build(workflow, 'annotation', before=before)
    if operand == 'role':
        owner = original.constructed_entry(workflow, workflow.directory / 'entry', original.ROUTES[0])
        original.install_entry(workflow, owner)
    assert workflow.annotation_child_roles is None
    events, owners = [], []
    expansion_error = RuntimeError('authentic expansion callback boundary')
    actual_validation = workflow.validate_child_choice
    def validate_choice(*args, **kwargs):
        events.append('validate_child_choice')
        return actual_validation(*args, **kwargs)
    workflow.validate_child_choice = validate_choice
    def expanded(*args, **kwargs):
        events.append('expanded')
        raise expansion_error
    workflow.expanded_contract_form = expanded
    class TracedString(str):
        __hash__ = str.__hash__
        def __eq__(self, other):
            events.append(('custom_string_equal', str(self), str(other)))
            return str.__eq__(self, other)
    selection = {'kind': 'child', 'scope': deepcopy(source.scope),
        'goal': 'Original custom selection operand', 'purpose': 'Preserve callback order'}
    if operand == 'key':
        selection = {TracedString(key) if key == 'kind' else key: value
            for key, value in selection.items()}
    elif operand == 'kind':
        selection['kind'] = TracedString('child')
    else:
        assert operand == 'role'
        selection.update(kind='episode_child', role=TracedString('launch'), assignment={})
    callback = method('Workflow', 'selected') if before else runtime.Workflow.selected
    names = [('to_child_annotation_improvement', 'prepare_request')]
    with owner_calls(names, owners):
        try:
            callback(workflow, source, selection, 7)
        except RuntimeError as error:
            assert error is expansion_error
        else:
            raise AssertionError('original expansion error was not preserved')
    # Normalize only the observed copy, without looking up the custom key or
    # comparing a custom object after the actual call boundary.
    observed_selection = json.loads(json.dumps(selection))
    return {'events': tuple(events), 'owners': owners, 'selection': observed_selection,
        'original_error': True, 'action': workflow.journal.row('runtime_actions', source.episode_id, 7)}
