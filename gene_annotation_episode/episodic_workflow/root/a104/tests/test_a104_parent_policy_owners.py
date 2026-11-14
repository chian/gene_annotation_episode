"""Focused moved-policy boundaries; accepted source87 controls are separate.

Real Store/Workflow/source constructors supply state. Declared callback ports
isolate the extracted assembly and admission points; no scientific/native
operation, whole workflow, or previous receipt transfer is claimed.
"""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from .test_a104_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, own, root,
)


@pytest.mark.parametrize('role', ('annotation', 'improvement', 'custom_annotation'))
def test_actual_parent_action_form_live_callbacks_and_exact_result(tmp_path, monkeypatch, role):
    runtime = own('runtime')
    class CustomWorkflow(runtime.Workflow): pass
    with actual_workflow(tmp_path, workflow_type=CustomWorkflow if role == 'custom_annotation' else None) as workflow:
        source = (root(workflow) if role != 'improvement' else workflow.build(
            'improvement', 'root', 'Existing improvement', workflow.store.validate_scope())).source
        # Supplied catalog/read ports avoid unrelated provider execution. The
        # original role/receipt/private binding policy still assembles the form.
        events = []
        original_object, original_json = runtime._object, runtime._json
        def object_port(value):
            events.append(('object', tuple(value)))
            return original_object(value)
        def json_port(value):
            events.append(('json', tuple(value)))
            return original_json(value)
        def catalog(scope, source=None):
            events.append(('catalog', scope, source.path))
            return []
        monkeypatch.setattr(runtime, '_object', object_port)
        monkeypatch.setattr(runtime, '_json', json_port)
        workflow.catalog = catalog
        results = []
        for function in (original_function('Workflow', 'action_schema'), runtime.Workflow.action_schema):
            events.clear()
            result = function(workflow, source)
            assert result['properties']['report_update'] == source.interpret_schema
            assert events[0][0] == 'object'
            assert sum(event[0] == 'json' for event in events) == 2
            results.append((result, deepcopy(events)))
        assert results[0] == results[1]
        forms = own('library.parent_task_report_forms')
        assert forms.form_inputs.__globals__ is forms.child_request_form.__globals__ is vars(runtime)


@pytest.mark.parametrize('value', (None, [], 'exception'), ids=('none', 'empty', 'failure'))
def test_restricted_catalog_preserves_opaque_return_and_callback_error(tmp_path, value):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        assert workflow.receipts is None
        events = []
        class CatalogError(Exception): pass
        def shared(selected):
            assert selected is source
            events.append('shared_information_catalog')
            if value == 'exception': raise CatalogError('original catalog port')
            return value
        workflow.shared_information_catalog = shared
        observations = []
        for function in (original_function('Workflow', 'catalog'), runtime.Workflow.catalog):
            events.clear()
            if value == 'exception':
                with pytest.raises(CatalogError, match='original catalog port') as error:
                    function(workflow, source.scope, source=source)
                result = (type(error.value), error.value.args)
            else:
                result = function(workflow, source.scope, source=source)
                assert result is value
            assert events == ['shared_information_catalog']
            observations.append((result, list(events)))
        assert observations[0] == observations[1]


@pytest.mark.parametrize('scientific', (False, True))
def test_shared_default_roles_exact_descriptor_and_live_configured_inputs(tmp_path, scientific):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        # These are explicit configuration ports at the original method. They
        # are not a newly admitted registry or executed Homology child.
        workflow.scientific_process_binding = object() if scientific else None
        workflow.job_episodes = SimpleNamespace(roles=('job_submission', 'job_monitoring', 'result_acquisition'))
        expected = original_function('Workflow', '_default_scientific_child_roles')(workflow)
        actual = workflow._default_scientific_child_roles()
        assert actual == expected
        assert ('improvement' in actual) is (not scientific)
        function = runtime.Workflow._default_scientific_child_roles
        assert function is own('library.unbound_child_action_options')._default_scientific_child_roles
        assert function.__globals__ is vars(runtime)
        assert function.__module__ == runtime.__name__
        assert function.__qualname__ == 'Workflow._default_scientific_child_roles'


@pytest.mark.parametrize('role,original', (('improvement', False), ('scientific_process', True)))
def test_parent_axis_choice_preserves_error_and_original_replay_flag(tmp_path, role, original):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        workflow.project_credit = SimpleNamespace(task_credit=True)
        # original=True must not inspect this selection; this is the original
        # saved-selection flag, not a bypass added by the extracted owner.
        selection = SimpleNamespace()
        outcomes = []
        for function in (original_function('Workflow', 'validate_child_choice'), runtime.Workflow.validate_child_choice):
            if role == 'improvement':
                with pytest.raises(ValueError, match='^annotation_root_commissions_evidence_axes$') as error:
                    function(workflow, source, role, selection=selection, original=original)
                result = (type(error.value), error.value.args)
            else:
                result = function(workflow, source, role, selection=selection, original=original)
                assert result is None
            outcomes.append(result)
        assert outcomes[0] == outcomes[1]


def test_original_execute_invalid_return_is_retained_before_provider(tmp_path):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        assert workflow.receipts is None
        results = []
        for function in (original_function('Workflow', 'execute'), runtime.Workflow.execute):
            result = asyncio.run(function(workflow, source, 'unavailable_original_operation', {},
                decision_index=0, operation_key='supplied-control-operation'))
            assert result == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                'result': None, 'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
            results.append(result)
        assert results[0] == results[1]
        # This direct return-boundary test does not claim acquisition/iteration.
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_observations').fetchone()
