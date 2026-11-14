"""Moved message boundaries with real Store, Journal, typed requests and forms.

These are finite callback controls. They do not claim that all child scientific
assignments were admitted or that a child/model/native workflow was executed.
The original full selected() callbacks are the independently compiled oracle.
"""
import ast
from contextlib import contextmanager
from copy import deepcopy
import inspect
from types import FunctionType, SimpleNamespace
import pytest

from .test_a104_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_node, own, root,
)

ROOT_ROUTES = (
    ('launch', 'execution_job_submission'), ('monitor', 'execution_progress_assessment'),
    ('results', 'execution_result_acquisition'), ('literature', 'published_evidence_assessment'),
    ('hpc', 'hpc_work_planning'), ('scientific_process', 'scientific_process'),
    ('job_launch', 'homology_job_submission'), ('job_monitor', 'homology_job_monitoring'),
    ('job_results', 'homology_result_acquisition'),
)
EDGES = tuple(('', role, home) for role, home in ROOT_ROUTES) + (
    ('scientific_process.', 'scientific_process', 'scientific_process'),
    ('scientific_process.', 'hpc', 'hpc_work_planning'),
)
EDGE_IDS = [prefix + 'parent->' + role for prefix, role, _ in EDGES]


def callback_oracle(name):
    selected = original_node('Workflow', 'selected')
    functions = {n.name: n for n in selected.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if name == 'prepare_parent_request':
        first, = [i for i, n in enumerate(selected.body) if isinstance(n, ast.Assign)
                  and ast.unparse(n.targets[0]) == 'role']
        last, = [i for i, n in enumerate(selected.body) if isinstance(n, ast.Assign)
                 and ast.unparse(n.targets[0]) == 'assignment']
        body = selected.body[first + 1:last + 1]
        signature = '(self, source, selection, index, scope, role)'
    elif name == 'admit_parent_return':
        body = functions['admitted_report'].body
        signature = '(self, source, child, index, schema, contract, result, request)'
    elif name == 'admit_parent_return_without_receipts':
        body = functions['report'].body[1:]
        signature = '(self, source, child, index, schema, contract, result, request)'
    elif name == 'receive_parent_child_failure':
        body = functions['failed_child'].body
        signature = '(self, source, selection, index, error)'
    else:
        raise AssertionError(name)
    fn, = ast.parse('def ' + name + signature + ': pass').body
    fn.body = deepcopy(body)
    runtime = own('runtime'); temporary = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), '<authenticated-original-selected-body>', 'exec'), temporary)
    compiled = temporary[name]
    return FunctionType(compiled.__code__, vars(runtime), name)


@contextmanager
def rollback_control(store):
    store.db.execute('SAVEPOINT parent_message_control')
    try:
        yield
    finally:
        store.db.execute('ROLLBACK TO parent_message_control')
        store.db.execute('RELEASE parent_message_control')


def incoming(prefix, home):
    return own(prefix + 'from_child_' + home)


def message_frame(workflow):
    runtime = own('runtime'); source = root(workflow).source
    schema = runtime._object({'unresolved': {'type': 'boolean'}})
    contract = runtime.TypedReportContract('Retain the unresolved engineering result', schema, lambda *_: False)
    goal = runtime.EpisodeGoal.child(source.request.goal, objective='Return the actual fixture form', result_contract=schema)
    request = runtime.EpisodeRequest(goal, runtime.Record({'scope': source.scope, 'initial_report': {'unresolved': True}}), contract)
    child_source = runtime._annotation_original_decision_source(workflow,
        (*source.path, ('improvement', 'typed-return')), request, source.scope)
    child = SimpleNamespace(source=child_source)
    selection = {'kind': 'child', 'role': 'improvement', 'scope': source.scope,
                 'goal': goal.objective, 'purpose': contract.decision}
    return source, child, schema, contract, request, selection


def save_action(workflow, source, selection, *, result=None):
    runtime = own('runtime')
    workflow.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': 0,
        'action': runtime._json(selection), 'result': None if result is None else runtime._json(result), 'credit': None})


def result_observation(callback, workflow, source, child, schema, contract, result, request):
    runtime = own('runtime')
    try:
        returned = callback(workflow, source, child, 0, schema, contract, result, request)
        outcome = ('returned', returned)
    except runtime.ReportDeliveryError as error:
        outcome = ('ReportDeliveryError', error.feedback.as_record())
    attempts = [dict(row) for row in workflow.store.db.execute(
        'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
        (workflow.run_id, source.episode_id))]
    return outcome, attempts


@pytest.mark.parametrize('edge', EDGES, ids=EDGE_IDS)
def test_each_private_endpoint_uses_actual_original_runtime_namespace(edge):
    prefix, _, home = edge; runtime = own('runtime')
    outgoing, returning = own(prefix + 'to_child_' + home), incoming(prefix, home)
    for module, names in ((outgoing, ('prepare_parent_request',)),
            (returning, ('admit_parent_return', 'admit_parent_return_without_receipts', 'receive_parent_child_failure'))):
        for name in names:
            fn = getattr(module, name)
            assert fn.__globals__ is vars(runtime)
            assert inspect.getsourcefile(fn) == module.__file__
            assert fn.__code__.co_name == name


@pytest.mark.parametrize('edge', EDGES, ids=EDGE_IDS)
def test_each_moved_preparation_preserves_first_actual_error_boundary(tmp_path, edge):
    prefix, role, home = edge
    class OriginalPreparationError(Exception): pass
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source; events = []
        selection = {'kind': 'job_child' if role.startswith('job_') else 'episode_child', 'role': role}
        def expanded(actual_source, actual_selection, index, actual_role):
            assert actual_source is source and actual_selection is selection and index == 0 and actual_role == role
            events.append('original_expanded_contract_form')
            raise OriginalPreparationError('original declared form boundary')
        workflow.expanded_contract_form = expanded
        for fn in (callback_oracle('prepare_parent_request'), own(prefix + 'to_child_' + home).prepare_parent_request):
            events.clear()
            with pytest.raises(OriginalPreparationError, match='original declared form boundary'):
                fn(workflow, source, selection, 0, source.scope, role)
            assert events == ['original_expanded_contract_form']
        assert workflow.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0


@pytest.mark.parametrize('edge', EDGES, ids=EDGE_IDS)
def test_each_fresh_return_matches_original_typed_admission_and_saved_attempt(tmp_path, edge):
    prefix, _, home = edge; runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source, child, schema, contract, request, selection = message_frame(workflow)
        observations = []
        for fn in (callback_oracle('admit_parent_return'), incoming(prefix, home).admit_parent_return):
            with rollback_control(workflow.store):
                save_action(workflow, source, selection)
                result = runtime.Record({'form': {'unresolved': True}})
                observed = result_observation(fn, workflow, source, child, schema, contract, result, request)
                assert observed[0] == ('returned', ({'unresolved': True}, []))
                assert len(observed[1]) == 1 and observed[1][0]['failure'] is None
                observations.append(observed)
        assert observations[0] == observations[1]


@pytest.mark.parametrize('scenario', ('invalid', 'saved', 'saved_failure', 'frozen_redelivery'))
def test_scientific_return_preserves_saved_failure_and_redelivery_order(tmp_path, scenario):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source, child, schema, contract, request, selection = message_frame(workflow)
        observations = []
        old_receive = workflow.receive_form; calls = []
        def receive(parent, form, original_schema, index, **kwargs):
            calls.append((deepcopy(form), deepcopy(original_schema), index, kwargs))
            return old_receive(parent, form, original_schema, index, **kwargs)
        workflow.receive_form = receive
        class UnreadableResult:
            def as_record(self): raise AssertionError('saved outcome reread new result')
        for fn in (callback_oracle('admit_parent_return'), incoming('scientific_process.', 'scientific_process').admit_parent_return):
            with rollback_control(workflow.store):
                calls.clear()
                save_action(workflow, source, selection, result={'delivery_resolution_index': 5} if scenario == 'frozen_redelivery' else None)
                delivery = 'delivery_' + runtime._digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': 0})[:24]
                if scenario != 'invalid':
                    kwargs = {'failure': workflow.delivery_feedback(delivery, runtime.ReportBoundaryError('saved invalid form', code='invalid_schema'))} if scenario == 'saved_failure' else {'form': {'unresolved': True}}
                    workflow.save_attempt(source.episode_id, 5 if scenario == 'frozen_redelivery' else 0,
                        delivery, child.source.episode_id, contract, **kwargs)
                result = runtime.Record({'form': {}}) if scenario == 'invalid' else UnreadableResult()
                observed = result_observation(fn, workflow, source, child, schema, contract, result, request)
                if scenario in ('invalid', 'saved_failure'):
                    assert observed[0][0] == 'ReportDeliveryError' and calls == []
                else:
                    assert observed[0] == ('returned', ({'unresolved': True}, []))
                    assert len(calls) == 1 and calls[0][2:] == ((5, {'redelivery': True}) if scenario == 'frozen_redelivery' else (0, {'redelivery': False}))
                observations.append((observed, deepcopy(calls)))
        assert observations[0] == observations[1]


@pytest.mark.parametrize('valid', (True, False))
def test_scientific_nonreceipt_return_retains_typed_failure_and_save_order(tmp_path, valid):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source, child, schema, contract, request, selection = message_frame(workflow)
        observations = []
        for fn in (callback_oracle('admit_parent_return_without_receipts'), incoming('scientific_process.', 'hpc_work_planning').admit_parent_return_without_receipts):
            with rollback_control(workflow.store):
                save_action(workflow, source, selection)
                result = runtime.Record({'form': {'unresolved': True} if valid else {}})
                observed = result_observation(fn, workflow, source, child, schema, contract, result, request)
                assert observed[0][0] == ('returned' if valid else 'ReportDeliveryError')
                assert len(observed[1]) == 1
                observations.append(observed)
        assert observations[0] == observations[1]


@pytest.mark.parametrize('report_error', (False, True))
def test_scientific_child_failure_keeps_original_action_credit_and_feedback(tmp_path, report_error):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source, _, _, _, _, selection = message_frame(workflow); observations = []
        error = runtime.ReportBoundaryError('original malformed return', code='invalid_form', field='unresolved') if report_error else RuntimeError('original child failure')
        for fn in (callback_oracle('receive_parent_child_failure'), incoming('scientific_process.', 'scientific_process').receive_parent_child_failure):
            with rollback_control(workflow.store):
                value = fn(workflow, source, selection, 0, error)
                row = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
                assert runtime.json.loads(row['result'])['status'] == 'failed' and row['credit'] is not None
                assert source.last_outcome_index == 0 and source.feedback['exception_type'] == type(error).__name__
                assert ('report_boundary' in source.feedback) == report_error
                observations.append((value.as_record(), row, deepcopy(source.feedback)))
        assert observations[0] == observations[1]


@pytest.mark.parametrize('owner', ('workflow', 'registry', 'source'))
def test_nominal_state_rejects_custom_dictionary_without_early_callbacks(tmp_path, owner):
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        value = {'workflow': workflow, 'registry': workflow.episode_bindings, 'source': source}[owner]
        calls = []
        class CustomDictionary(dict):
            def get(self, *args): calls.append('get'); raise AssertionError('early getter')
            def __contains__(self, key): calls.append('contains'); raise AssertionError('early membership')
        original = object.__getattribute__(value, '__dict__')
        object.__setattr__(value, '__dict__', CustomDictionary(original))
        try:
            assert own('episode').is_annotation_parent(workflow, source) is False
            assert calls == []
        finally:
            object.__setattr__(value, '__dict__', original)


def test_optional_message_selector_does_not_compare_custom_selection_keys(tmp_path):
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source; calls = []
        class Key:
            def __hash__(self): return hash('kind')
            def __eq__(self, other): calls.append(other); raise AssertionError('early equality')
        selection = {Key(): 'episode_child'}
        assert own('child_message_owners').parent_exchange(workflow, source, selection, 'monitor') is None
        assert calls == []
