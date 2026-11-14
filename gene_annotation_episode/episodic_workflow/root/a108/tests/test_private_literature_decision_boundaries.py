"""Real private next/call/exchange boundaries with controlled engineering ports.

The reusable real Store/Journal contains an explicitly synthetic invalid prior
tool result with zero credit. No scientific finding, support, grader or action
completion is manufactured. A sentinel admission port stops AFTER the actual
decision response is persisted, before acquiring the proposed engineering intent.
"""
import asyncio
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from types import MethodType, SimpleNamespace

import pytest

from .test_private_literature_boundaries import AXIS, HOMES


def module(name):
    return import_module(AXIS + '.' + name)


@pytest.fixture(scope='module')
def decision_store(tmp_path_factory):
    with module('state').Store(tmp_path_factory.mktemp('literature-decisions') / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        journal = module('episode_journal').Journal(store, 'engineering-decision-boundaries')
        exchanges = module('decision_exchanges').DecisionExchanges(journal)
        yield store, journal, exchanges


def make_control(decision_store, home, node_id, protocol, root_shape, *, error_at=None):
    store, journal, exchanges = decision_store
    runtime = module('runtime')
    Binding = import_module(AXIS + '.' + home + '.episode').LiteratureEpisode
    source = object.__new__(Binding.decision_source_type)
    episode_id = 'engineering_' + sha256(node_id.encode()).hexdigest()[:24]
    source.episode_id = episode_id
    source.path = ((Binding.roles[0], episode_id),)
    source.scope = store.validate_scope()
    source.calls = 1
    source._execution_context = None
    source._model_snapshot = None
    source._presented_conversation_key = None
    source._delivery_resolution_ref = None
    source.report_values = {'inspection_status': False}
    source.report_basis = []
    source.interpret_schema = {'type': 'object', 'properties': {'inspection_status': {'type': 'boolean'}},
                               'required': ['inspection_status'], 'additionalProperties': False}
    source.request = SimpleNamespace(
        goal=SimpleNamespace(as_record=lambda: {'objective': 'Engineering decision-boundary inspection'}),
        report_contract=SimpleNamespace(decision='Retain the engineering status without scientific interpretation',
                                        schema=deepcopy(source.interpret_schema)),
        message=SimpleNamespace(as_record=lambda: {'episode_assignment': {}}))
    original_outcome = {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
        'feedback': {'category': 'engineering_fixture', 'code': 'original_invalid_input'},
        'result': {'engineering_only': True, 'science_attempted': False}}
    source.last_outcome = deepcopy(original_outcome)
    source.last_outcome_index = 0
    source.feedback = source.last_outcome['feedback']
    with store.transaction():
        journal.save('runtime_actions', {'episode_id': episode_id, 'decision_index': 0,
            'action': json.dumps({'kind': 'tool', 'tool': 'engineering.fixture', 'arguments': {}}),
            'result': json.dumps(original_outcome), 'credit': 0.0})
    original_action = journal.row('runtime_actions', episode_id, 0)
    selected_response = {'selection': {'kind': 'engineering_intent'},
                         'report_update': deepcopy(source.report_values)}
    schema = {'type': 'object', 'properties': {
        'selection': {'type': 'object', 'properties': {'kind': {'const': 'engineering_intent'}},
                      'required': ['kind'], 'additionalProperties': False},
        'report_update': deepcopy(source.interpret_schema)},
        'required': ['selection', 'report_update'], 'additionalProperties': False}
    credit = {'mode': 'annotation_axis_credit', 'arms': []} if root_shape else 0.0
    error = RuntimeError('original controlled ' + str(error_at) + ' failure')
    trace = {'provider': [], 'instructions': [], 'projector': [], 'admission': [], 'working_state': 0}

    def projector(actual_store, scope, **arguments):
        assert actual_store is store and scope == source.scope and not arguments
        trace['projector'].append((scope, arguments))
        return {'credit': deepcopy(credit), 'a101_sheet': {'engineering_only': True}}

    def instructions(actual, context):
        assert actual is source
        trace['instructions'].append(deepcopy(context))
        if error_at == 'service':
            raise error
        return 'Exact caller-owned engineering instructions'

    async def complete(episode, role, actual_instructions, context, output_schema):
        trace['provider'].append((episode, role, actual_instructions, deepcopy(context), deepcopy(output_schema)))
        if error_at == 'provider':
            raise error
        if protocol == 'exchange':
            return {'response': {'response_type': 'select_action', **deepcopy(selected_response)}}
        return deepcopy(selected_response)

    def working_state(actual):
        assert actual is source
        trace['working_state'] += 1
        return {'engineering_inputs': []}

    def preview(value, *, decision_index):
        assert value == original_outcome and decision_index == 0
        return {**deepcopy(value), 'feedback': {'category': 'engineering_fixture', 'code': 'presented_invalid_input'}}

    workflow = SimpleNamespace(store=store, journal=journal, run_id=journal.run_id,
        inprocess_replay=None, execution_binding=None, decision_exchanges=exchanges,
        decision_protocol=runtime.DECISION_EXCHANGE_PROTOCOL if protocol == 'exchange' else None,
        provider=SimpleNamespace(complete=complete),
        services=SimpleNamespace(instructions=instructions, decision_exchange_instructions=lambda: 'Original exchange contract'),
        working_state=working_state, local_outcome_preview=preview,
        is_job_source=lambda _: False, specialist=lambda _: None,
        is_scientific_source=lambda _: True,
        binding_context=lambda actual: SimpleNamespace(path=actual.path, scope=actual.scope, received_record_refs=()),
        project_credit=projector, projection_arguments=lambda _: {},
        native_timing_information=lambda actual_store, scope, **kwargs: {
            'monitoring_information_credit': 2.0,
            'monitoring_information_binding': {'kind': 'engineering_duration_metadata'}},
        native_timing_arguments=lambda _: {},
        source_credit_binding=lambda _: {'kind': 'engineering_projector'},
        annotation_context=lambda scope, source: {'engineering_annotation_context': 'metadata only'},
        pending_work=lambda _: [], delivery_status=lambda _: [], controller_binding={},
        catalog=lambda *args, **kwargs: [], knowledge=SimpleNamespace(context=lambda: {}),
        job_episode_options=lambda _: None, permits_common_action=lambda *args: args[-1] != 'wait',
        tools=SimpleNamespace(), extra_report_sources=lambda _: {}, action_schema=lambda _: deepcopy(schema),
        contract_information_profile=lambda _: None, resource_context=lambda _: None,
        shared_information_context=lambda _: None,
        launch_instructions=SimpleNamespace(context=lambda: {}, materialize=lambda _: None),
        available_child_roles=lambda _: (),
        episode_bindings=SimpleNamespace(initial_decision_context=lambda _: {}),
        execution_expectations=None, resource_estimator=None,
        native_estimation_context=lambda *args: None,
        freeze_literature_numerical_contracts=lambda *args: None,
        receipts=None, history_preview=lambda *args, **kwargs: [],
        scientific_library_available=lambda _: False)
    # These are the actual original dispatch/projection methods, including the
    # supported injected root path and native supplemental information branch.
    for name in ('scientific_projector_for_context', 'projection_view', 'source_credit_view', 'receipt_projection'):
        setattr(workflow, name, MethodType(getattr(runtime.Workflow, name), workflow))
    source.workflow = workflow
    assert workflow.scientific_projector_for_context(workflow.binding_context(source)) is projector
    marker = object()

    def stop_before_acquisition(response, index, actual_context, actual_schema):
        trace['admission'].append((deepcopy(response), index, deepcopy(actual_context), deepcopy(actual_schema)))
        return marker

    source.apply_response = stop_before_acquisition
    view = SimpleNamespace(units_consumed=0, child_reports=(),
        controller_state={'arms': [], 'scores': [], 'decision': {'stop': False}},
        model_inputs=lambda values, *, reports: values)
    return SimpleNamespace(source=source, view=view, trace=trace, marker=marker, error=error,
        original_action=original_action, original_outcome=original_outcome, response=selected_response,
        schema=schema, credit=credit, journal=journal, exchanges=exchanges, store=store)


def assert_no_acquired_work(control):
    task = control.source
    assert control.journal.row('runtime_actions', task.episode_id, 0) == control.original_action
    assert control.journal.row('runtime_actions', task.episode_id, 1) is None
    assert control.store.db.execute('SELECT count(*) FROM runtime_actions WHERE run_id=? AND episode_id=?',
        (control.journal.run_id, task.episode_id)).fetchone()[0] == 1
    assert control.store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=? AND episode_id=?',
        (control.journal.run_id, task.episode_id)).fetchone()[0] == 0
    assert task.last_outcome == control.original_outcome and task.last_outcome_index == 0
    assert task.feedback is task.last_outcome['feedback']


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('protocol', ['direct', 'exchange'])
@pytest.mark.parametrize('root_shape', [False, True])
def test_actual_private_decision_boundary_and_saved_replay(decision_store, request, home, protocol, root_shape):
    control = make_control(decision_store, home, request.node.nodeid, protocol, root_shape)
    task = control.source
    assert asyncio.run(task.next(control.view)) is control.marker
    assert len(control.trace['provider']) == len(control.trace['instructions']) == len(control.trace['projector']) == 1
    assert control.trace['working_state'] == 1
    response, index, context, schema = control.trace['admission'][0]
    assert response == control.response and index == 1 and schema == control.schema
    assert context['current_credit'] == control.credit
    assert context['monitoring_information_credit'] == 2.0
    assert context['monitoring_information_binding'] == {'kind': 'engineering_duration_metadata'}
    assert context['last_local_outcome']['status'] == 'invalid'
    assert context['feedback']['code'] == 'presented_invalid_input'
    assert context['engineering_annotation_context'] == 'metadata only'
    assert '_completed_work_axis_results' not in context
    if root_shape:
        assert 'completed_action_reports' not in context
    else:
        report, = context['completed_action_reports']
        assert report['original_decisions'] == [0]
        assert report['recorded_outcome']['status'] == 'invalid'
        assert report['credit_receipts'] == []
    provider = control.trace['provider'][0]
    assert provider[0:2] == (task.episode_id, 'REASONING')
    assert provider[2].startswith('Exact caller-owned engineering instructions')
    if protocol == 'exchange':
        row, = control.exchanges.rows(task.episode_id, 1)
        yields = row['request']['restoration']['snapshot']['action_yields']
        if root_shape:
            assert yields == {'version': 'annotation_axis_yield_table_v1', 'rows': [],
                'forecast_unit': 'another_whole_axis_invocation', 'source': 'actual_root_controller'}
        else:
            assert yields['completion_count_basis'] == 'saved_own_controller_observations'
            assert yields['yield_basis'] == 'saved_signed_marginal_credit_excluding_inherited_baseline'
            row_yield, = yields['rows']
            assert row_yield['completed_actions'] == 0 and row_yield['total_yield'] == 0.0
            assert row_yield['attempted_uncompleted'] == 1
        assert provider[3]['kind'] == 'decision_bootstrap'
        assert provider[3]['fields']['action_yields'] == yields
    saved = control.journal.row('runtime_model_calls', task.episode_id, 1)
    assert json.loads(saved['response']) == control.response
    assert_no_acquired_work(control)
    # Re-enter the original next/call path at the same saved logical decision.
    # No fresh state, custom projector, service instruction or provider call.
    task.calls = 1
    assert asyncio.run(task.next(control.view)) is control.marker
    assert control.journal.row('runtime_model_calls', task.episode_id, 1) == saved
    assert len(control.trace['provider']) == len(control.trace['instructions']) == len(control.trace['projector']) == 1
    assert control.trace['working_state'] == 1
    assert control.trace['admission'][1] == control.trace['admission'][0]
    assert_no_acquired_work(control)


@pytest.mark.parametrize('home', [HOMES[0], HOMES[-1]])
@pytest.mark.parametrize('error_at', ['service', 'provider'])
def test_actual_decision_propagates_original_controlled_exception(decision_store, request, home, error_at):
    control = make_control(decision_store, home, request.node.nodeid, 'direct', False, error_at=error_at)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(control.source.next(control.view))
    assert caught.value is control.error
    assert len(control.trace['instructions']) == 1
    assert len(control.trace['provider']) == (1 if error_at == 'provider' else 0)
    assert control.trace['admission'] == []
    pending = control.journal.row('runtime_model_calls', control.source.episode_id, 1)
    assert pending['response'] is None
    assert_no_acquired_work(control)


@pytest.mark.parametrize('home', [HOMES[0], HOMES[-1]])
def test_delivery_context_branch_and_saved_identity_guard(decision_store, request, home):
    control = make_control(decision_store, home, request.node.nodeid, 'direct', False)
    task = control.source
    deliveries = []

    def resolution(actual, delivery_ref, context):
        assert actual is task
        deliveries.append((delivery_ref, deepcopy(context)))
        return {**context, 'pending_child_delivery': {'delivery_ref': delivery_ref}}, deepcopy(control.schema)

    task.workflow.delivery_resolution_inputs = resolution
    assert asyncio.run(task.next(control.view, delivery_ref='engineering_delivery_original')) is control.marker
    assert len(deliveries) == 1
    assert control.trace['admission'][0][2]['pending_child_delivery'] == {'delivery_ref': 'engineering_delivery_original'}
    saved = control.journal.row('runtime_model_calls', task.episode_id, 1)
    task.calls = 1
    with pytest.raises(module('runtime').WorkflowError, match='restored_delivery_resolution_identity_conflict') as caught:
        asyncio.run(task.next(control.view, delivery_ref='engineering_delivery_changed'))
    assert type(caught.value) is module('runtime').WorkflowError
    assert len(deliveries) == len(control.trace['provider']) == 1
    assert control.journal.row('runtime_model_calls', task.episode_id, 1) == saved
    assert_no_acquired_work(control)
