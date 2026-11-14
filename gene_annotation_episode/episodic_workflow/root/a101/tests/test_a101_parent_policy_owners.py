"""Changed A101 policy boundaries on real parent state with explicit read ports.

The source233 predecessor is the installed epoch, not an unexamined older
runtime. These controls do not replay the accepted98/54 cohorts or execute a
scientific/native operation.
"""
import ast
import asyncio
from copy import deepcopy
import hashlib
from pathlib import Path
from types import FunctionType, SimpleNamespace

import pytest

from .test_a101_implicit_parent_protocol import actual_workflow, no_external_execution, own, root

ORACLES = {
    'runtime': ('a101_policy_original_runtime.txt', '233152da433ae7f3978f0e662c93437c8555afda35ff71d999769968e751e017'),
    'report': ('a101_policy_original_report_records.txt', '4b8c1c6fecae82f42eb4aacf5a747fc1f52f67bb3ba0c31604047b98af9c00bc'),
}


def policy_original(owner, name):
    filename, pin = ORACLES['runtime' if owner else 'report']
    path = Path(__file__).parent / 'fixtures' / 'source_request_assembly' / filename
    data = path.read_bytes(); assert hashlib.sha256(data).hexdigest() == pin
    node = ast.parse(data)
    if owner:
        node, = [n for n in node.body if isinstance(n, ast.ClassDef) and n.name == owner]
    node, = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    node = deepcopy(node); assert not node.decorator_list
    runtime = own('runtime'); scratch = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), 'exec'), scratch)
    original = scratch[name]
    bound = FunctionType(original.__code__, vars(runtime), original.__name__, original.__defaults__)
    bound.__kwdefaults__ = original.__kwdefaults__
    return bound


def check_parent_form_callbacks_and_complete_result(tmp_path, monkeypatch, role):
    runtime = own('runtime')
    class CustomWorkflow(runtime.Workflow): pass
    with actual_workflow(tmp_path, workflow_type=CustomWorkflow if role == 'custom_annotation' else None) as workflow:
        source = (root(workflow) if role != 'improvement' else workflow.build(
            'improvement', 'root', 'Existing iterative question', workflow.store.validate_scope())).source
        events = []
        original_object, original_json = runtime._object, runtime._json
        def object_port(value):
            events.append(('object', tuple(value))); return original_object(value)
        def json_port(value):
            events.append(('json', tuple(value))); return original_json(value)
        def catalog(scope, source=None):
            events.append(('catalog', scope, source.path)); return []
        monkeypatch.setattr(runtime, '_object', object_port)
        monkeypatch.setattr(runtime, '_json', json_port)
        workflow.catalog = catalog
        observations = []
        for function in (policy_original('Workflow', 'action_schema'), runtime.Workflow.action_schema):
            events.clear(); result = function(workflow, source)
            assert result['properties']['report_update'] == source.interpret_schema
            assert events[0][0] == 'object'
            assert sum(event[0] == 'json' for event in events) == 2
            observations.append((result, deepcopy(events)))
        assert observations[0] == observations[1]
        forms = own('library.child_report_forms')
        for name in ('annotation_report_example', 'interpretation_report_example', 'child_scope_schema', 'scientific_child_request_schema'):
            assert getattr(forms, name).__globals__ is vars(runtime)


@pytest.mark.parametrize('role', ('annotation', 'custom_annotation'))
def test_actual_parent_form_callbacks_and_complete_result(tmp_path, monkeypatch, role):
    check_parent_form_callbacks_and_complete_result(tmp_path, monkeypatch, role)


@pytest.mark.parametrize('value', (None, [], 'exception'), ids=('none', 'empty', 'failure'))
def test_root_catalog_keeps_opaque_return_and_error_order(tmp_path, value):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source; assert workflow.receipts is None
        events = []
        class CatalogError(Exception): pass
        def shared(selected):
            assert selected is source; events.append('shared_information_catalog')
            if value == 'exception': raise CatalogError('original catalogue port')
            return value
        workflow.shared_information_catalog = shared; observations = []
        for function in (policy_original('Workflow', 'catalog'), runtime.Workflow.catalog):
            events.clear()
            if value == 'exception':
                with pytest.raises(CatalogError, match='original catalogue port') as error:
                    function(workflow, source.scope, source=source)
                result = (type(error.value), error.value.args)
            else:
                result = function(workflow, source.scope, source=source); assert result is value
            assert events == ['shared_information_catalog']; observations.append((result, list(events)))
        assert observations[0] == observations[1]


@pytest.mark.parametrize('scientific', (False, True))
def test_default_roles_preserve_public_descriptor_and_configured_reads(tmp_path, scientific):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        # Explicit configuration values for the original policy method only;
        # this is not construction/execution of a new Homology binding family.
        workflow.scientific_process_binding = object() if scientific else None
        workflow.job_episodes = SimpleNamespace(roles=('job_submission', 'job_monitoring', 'result_acquisition'))
        expected = policy_original('Workflow', '_default_scientific_child_roles')(workflow)
        assert workflow._default_scientific_child_roles() == expected
        assert ('improvement' in expected) is (not scientific)
        function = runtime.Workflow._default_scientific_child_roles
        assert function is own('library.unbound_child_action_options')._default_scientific_child_roles
        assert function.__globals__ is vars(runtime)
        assert (function.__module__, function.__qualname__) == (runtime.__name__, 'Workflow._default_scientific_child_roles')


@pytest.mark.parametrize('role,original', (('improvement', False), ('scientific_process', True)))
def test_axis_admission_preserves_original_replay_flag_and_error(tmp_path, role, original):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source; workflow.project_credit = SimpleNamespace(task_credit=True)
        selection = SimpleNamespace(); observations = []
        for function in (policy_original('Workflow', 'validate_child_choice'), runtime.Workflow.validate_child_choice):
            if role == 'improvement':
                with pytest.raises(ValueError, match='^annotation_root_commissions_evidence_axes$') as error:
                    function(workflow, source, role, selection=selection, original=original)
                result = (type(error.value), error.value.args)
            else:
                result = function(workflow, source, role, selection=selection, original=original)
                assert result is None
            observations.append(result)
        assert observations[0] == observations[1]


@pytest.mark.parametrize('restricted', (False, True))
def test_required_child_sources_preserve_bound_callback_and_alias(tmp_path, restricted):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source; events = []
        if not restricted: workflow.root_action_boundary = None
        def supplied(context, role):
            events.append((context.episode_id, role)); return ['credit']
        workflow.project_credit = SimpleNamespace(child_return_sources=supplied)
        observations = []
        for function in (policy_original('Workflow', 'root_child_return_sources'), runtime.Workflow.root_child_return_sources):
            events.clear(); result = function(workflow, source, 'scientific_process')
            assert result == (('credit',) if restricted else ())
            assert events == ([(source.episode_id, 'scientific_process')] if restricted else [])
            observations.append((result, list(events)))
        assert observations[0] == observations[1]
        function = runtime.Workflow.root_child_return_sources
        assert function is own('action_admission').root_child_return_sources
        assert function.__globals__ is vars(runtime)
        assert (function.__module__, function.__qualname__) == (runtime.__name__, 'Workflow.root_child_return_sources')


@pytest.mark.parametrize('state', ('unavailable', 'available', 'saved'))
def test_selected_root_replay_gate_before_original_acquisition(tmp_path, state):
    runtime = own('runtime')
    with actual_workflow(tmp_path, receipts=True) as workflow:
        source = root(workflow).source
        selection = {'kind': 'tool', 'tool': 'supplied.original.tool', 'arguments': {}}
        if state == 'saved':
            workflow.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': 0,
                'action': runtime._json(selection), 'result': runtime._json({'status': 'completed'}), 'credit': None})
        events = []
        class ReachedOriginalBoundary(Exception): pass
        def catalog(scope, source=None):
            events.append('catalog')
            if state == 'saved': raise AssertionError('saved original action must bypass current catalogue')
            return [{'name': selection['tool']}] if state == 'available' else []
        def boundary(*args):
            events.append('closed_child_boundary'); raise ReachedOriginalBoundary('before acquire')
        workflow.catalog = catalog; workflow._closed_child_commission = boundary
        original_row = workflow.journal.row
        def row(table, *args):
            if table == 'runtime_actions': events.append('saved_action_row')
            return original_row(table, *args)
        workflow.journal.row = row; observations = []
        for function in (policy_original('Workflow', 'selected'), runtime.Workflow.selected):
            events.clear()
            expected = ValueError if state == 'unavailable' else ReachedOriginalBoundary
            with pytest.raises(expected) as error: function(workflow, source, selection, 0)
            assert str(error.value) == ('action_not_available_to_episode' if state == 'unavailable' else 'before acquire')
            assert events == (['saved_action_row', 'catalog'] if state == 'unavailable' else
                ['saved_action_row', 'catalog', 'closed_child_boundary'] if state == 'available' else
                ['saved_action_row', 'closed_child_boundary'])
            observations.append((type(error.value), error.value.args, list(events)))
        assert observations[0] == observations[1]
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_observations').fetchone()


def test_original_invalid_execute_result_before_provider_is_unchanged(tmp_path):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source; assert workflow.receipts is None
        results = []
        for function in (policy_original('Workflow', 'execute'), runtime.Workflow.execute):
            result = asyncio.run(function(workflow, source, 'unavailable_original_operation', {},
                decision_index=0, operation_key='declared-control-operation'))
            assert result == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
            results.append(result)
        assert results[0] == results[1]
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_observations').fetchone()

