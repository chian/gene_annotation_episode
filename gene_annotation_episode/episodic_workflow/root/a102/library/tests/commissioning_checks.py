"""Paired A102 commissioning predicates over real private source/Store/Journal.

Configured-role, capability, credit and tool ports are explicitly supplied.
No child implementation, scientific operation or native process is executed.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

from ... import scientific_process_records as records
from .report_schema_checks import host, original, runtime, forbidden

SCHEMA = {'type': 'object', 'properties': {'credit': {'type': 'number', 'x-source': 'credit'}},
          'required': ['credit'], 'additionalProperties': False}


class BoundaryStop(Exception):
    pass


def error_record(error):
    return {'type': type(error).__name__, 'message': str(error)}


def paired(directory, scenario):
    results = []
    for old in (True, False):
        with host(directory / str(old), 'annotation') as value:
            workflow, source = value.workflow, value.source
            events = []
            def call(name, *args, **kwargs):
                method = original(name) if old else getattr(runtime.Workflow, name)
                result = method(workflow, *args, **kwargs)
                return asyncio.run(result) if asyncio.iscoroutine(result) else result
            def restricted(actual_workflow, actual):
                assert actual_workflow is workflow and actual is source
                events.append('root_classifier')
                return True
            with patch.object(runtime, 'restricted_root', restricted):
                if scenario == 'wait':
                    workflow.annotation_child_roles = ('literature',)
                    workflow.episode_bindings = SimpleNamespace(roles=('literature',),
                        for_child=lambda path, role: events.append('child_wait_declaration') or
                            SimpleNamespace(supports_wait=False))
                    workflow.specialist = forbidden
                    answer = call('permits_common_action', source, 'wait')
                    assert answer is False and events == ['child_wait_declaration']
                elif scenario == 'receipt':
                    workflow.specialist = forbidden
                    workflow.receipts = None
                    absent = call('permits_common_action', source, 'tool')
                    workflow.receipts = object()
                    present = call('permits_common_action', source, 'tool')
                    answer = absent, present
                    assert answer == (False, True) and events == ['root_classifier', 'root_classifier']
                elif scenario == 'declarations':
                    workflow.scientific_process_binding = None
                    workflow.job_episodes = SimpleNamespace(roles=('declared_job',))
                    workflow.episode_bindings = SimpleNamespace(entry_roles=('declared_private',), roles=())
                    first = call('_default_scientific_child_roles')
                    workflow.annotation_child_roles = ('declared_private',)
                    root = call('declared_child_roles', 'annotation', path=source.path)
                    improvement = call('declared_child_roles', 'improvement', path=(('improvement', 'declared'),))
                    workflow.scientific_process_binding = value.scientific
                    last = call('_default_scientific_child_roles')
                    answer = first, root, improvement, last
                    assert answer == (('improvement', 'declared_job', 'declared_private'),
                        ('declared_private',), ('improvement', 'declared_job', 'declared_private'),
                        ('declared_job', 'declared_private'))
                elif scenario == 'declaration_none':
                    workflow.episode_bindings = SimpleNamespace(roles=())
                    workflow._default_scientific_child_roles = forbidden
                    values = iter((('original_declaration',), None))
                    def changed_declaration(actual):
                        assert actual is workflow
                        events.append('declaration_read')
                        return next(values)
                    with patch.object(runtime.Workflow, 'annotation_child_roles',
                                      property(changed_declaration), create=True):
                        answer = call('declared_child_roles', 'annotation', path=source.path)
                    assert answer is None and events == ['declaration_read', 'declaration_read']
                elif scenario == 'late_filter':
                    workflow.declared_child_roles = lambda *args, **kwargs: events.append('declared') or ('improvement', 'scientific_process')
                    def allowed(context, capabilities):
                        events.append('allowed')
                        workflow.project_credit.task_credit = True
                        return ('improvement', 'scientific_process')
                    workflow.specialist = lambda actual: events.append('specialist') or SimpleNamespace(allowed_children=allowed)
                    with patch.object(workflow.services, 'capabilities', lambda: events.append('capabilities') or {}):
                        answer = call('available_child_roles', source)
                    assert answer == ('scientific_process',)
                    assert events == ['declared', 'specialist', 'capabilities', 'allowed']
                elif scenario in ('fresh_arm', 'replay_arm', 'wrong_arm'):
                    workflow.project_credit.task_credit = True
                    workflow.annotation_child_roles = None
                    selection = {'kind': 'episode_child', 'role': 'scientific_process', 'scope': deepcopy(source.scope),
                        'assignment': {'proposed_annotation_ref': 'controlled_annotation', 'selection': {
                            'version': records.SELECTION_VERSION, 'evidence_axis': {'option_id': 'controlled_axis'}}}}
                    arm = {'proposed_annotation_ref': 'controlled_annotation', 'axis': 'controlled_axis', 'scope': deepcopy(source.scope)}
                    def credit(actual):
                        events.append('credit_arms')
                        return {'credit': {'arms': [] if scenario == 'wrong_arm' else [arm]}}
                    workflow.source_credit_view = forbidden if scenario == 'replay_arm' else credit
                    try:
                        answer = call('validate_child_choice', source, 'scientific_process', selection=selection,
                                      original=scenario == 'replay_arm')
                    except ValueError as error:
                        assert scenario == 'wrong_arm'
                        answer = error_record(error)
                        assert str(error) == 'axis_assignment_requires_one_received_annotation_subject_scope'
                    else:
                        assert scenario != 'wrong_arm' and answer is None
                    assert events == ([] if scenario == 'replay_arm' else ['credit_arms'])
                elif scenario in ('catalog_none', 'catalog_wait'):
                    workflow.receipts = None if scenario == 'catalog_none' else object()
                    workflow.shared_information_catalog = lambda actual: events.append('shared_catalog') or (
                        None if scenario == 'catalog_none' else [{'name': 'controlled_information'}])
                    workflow.permits_common_action = lambda actual, action: events.append(('permission', action)) or True
                    with patch.object(runtime, '_wait_estimate_operation',
                                      lambda: events.append('wait_operation') or {'name': 'controlled_wait'}):
                        answer = call('catalog', source.scope, source)
                    assert answer == (None if scenario == 'catalog_none' else [
                        {'name': 'controlled_information'}, {'name': 'controlled_wait'}])
                elif scenario in ('execute_rejection', 'execute_lookup'):
                    workflow.receipts = None
                    def pending(actual, index):
                        events.append('lookup_port')
                        raise BoundaryStop('composition_lookup')
                    workflow.pending_contract_information = pending
                    try:
                        answer = call('execute', source, runtime.CONTRACT_INFORMATION_OPERATIONS[0], {},
                            decision_index=3, operation_key='controlled_operation',
                            _composition_lookup=scenario == 'execute_lookup')
                    except BoundaryStop as error:
                        assert scenario == 'execute_lookup'; answer = str(error)
                    else:
                        assert scenario == 'execute_rejection'
                        assert answer == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                            'result': None, 'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
                    assert events == (['root_classifier', 'lookup_port'] if scenario == 'execute_lookup' else ['root_classifier'])
                elif scenario in ('selected_fresh', 'selected_replay'):
                    selection = {'kind': 'tool', 'tool': 'unavailable_tool', 'arguments': {}}
                    workflow.permits_common_action = lambda *args: True
                    def catalog(*args, **kwargs):
                        events.append('fresh_catalog')
                        return []
                    workflow.catalog = forbidden if scenario == 'selected_replay' else catalog
                    def closed(*args):
                        events.append('after_original_root_guard')
                        raise BoundaryStop('saved_guard_passed')
                    workflow._closed_child_commission = closed
                    if scenario == 'selected_replay':
                        workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                            'decision_index': 3, 'action': json.dumps(selection),
                            'result': json.dumps({'status': 'completed'}), 'credit': None})
                    try:
                        call('selected', source, deepcopy(selection), 3)
                    except ValueError as error:
                        assert scenario == 'selected_fresh'; answer = error_record(error)
                        assert str(error) == 'action_not_available_to_episode'
                    except BoundaryStop as error:
                        assert scenario == 'selected_replay'; answer = str(error)
                    else:
                        raise AssertionError('original guard did not stop before acquisition')
                    assert events == (['root_classifier', 'fresh_catalog'] if scenario == 'selected_fresh' else
                        ['root_classifier', 'after_original_root_guard'])
                elif scenario == 'return_form':
                    workflow.receipts = None
                    workflow.project_credit.child_return_sources = lambda context, role: events.append('return_sources') or ('credit',)
                    workflow.project_credit.child_return_form = lambda context, role: events.append('return_form') or deepcopy(SCHEMA)
                    declared = call('root_child_return_sources', source, 'scientific_process')
                    form = json.loads(call('child_form_input', source, {}, 'scientific_process'))
                    initial = call('child_initial_report_input', source, {}, 'scientific_process')
                    before = list(events)
                    supplied = call('child_form_input', source, {'schema_json': 'supplied'}, 'scientific_process')
                    supplied_initial = call('child_initial_report_input', source, {'initial_report_json': 'original'}, 'scientific_process')
                    assert events == before
                    answer = declared, form, initial, supplied, supplied_initial
                    assert answer == (('credit',), SCHEMA, '{}', 'supplied', 'original')
                else:
                    raise AssertionError(scenario)
            results.append((answer, events))
    assert results[0] == results[1]
    return results[1]
