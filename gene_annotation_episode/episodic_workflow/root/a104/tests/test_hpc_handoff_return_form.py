"""Original A104 handoff policy at eight private task-selection boundaries.

Actual Workflow/Store/Journal and actual private task classes are used. Source
state and child binding/contract ports are explicitly supplied; the positive
boundary stops before initial-report parsing, child preparation or acquisition.
This is not a native/HPC execution or whole-workflow restoration test.
"""
import ast
import builtins
from copy import deepcopy
import inspect
from types import FunctionType, SimpleNamespace

import pytest

from .test_a104_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, original_node, own,
)

ROUTES = (
    ('hpc_work_planning', 'HPCWorkTask', ('annotation', 'hpc'), 'launch'),
    ('hpc_work_planning/hpc_allocation_execution', 'HPCWorkTask', ('annotation', 'hpc', 'hpc_execution'), 'launch'),
    ('hpc_work_planning/execution_job_submission', 'LaunchTask', ('annotation', 'hpc', 'launch'), 'launch_hpc'),
    ('hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'LaunchTask', ('annotation', 'hpc', 'hpc_execution', 'launch'), 'launch_hpc'),
    ('scientific_process/hpc_work_planning', 'HPCWorkTask', ('annotation', 'scientific_process', 'hpc'), 'launch'),
    ('scientific_process/hpc_work_planning/hpc_allocation_execution', 'HPCWorkTask', ('annotation', 'scientific_process', 'hpc', 'hpc_execution'), 'launch'),
    ('scientific_process/hpc_work_planning/execution_job_submission', 'LaunchTask', ('annotation', 'scientific_process', 'hpc', 'launch'), 'launch_hpc'),
    ('scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'LaunchTask', ('annotation', 'scientific_process', 'hpc', 'hpc_execution', 'launch'), 'launch_hpc'),
)

class InitialReportBoundary(Exception): pass
class PortFailure(Exception): pass

def original_policy():
    runtime = own('runtime')
    method = original_node('Workflow', 'selected')
    assignment, = [node for node in ast.walk(method) if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'hpc_launch' for t in node.targets)]
    branch, = [node for node in ast.walk(method) if isinstance(node, ast.If)
               and isinstance(node.test, ast.BoolOp) and isinstance(node.test.values[0], ast.Name)
               and node.test.values[0].id == 'hpc_launch']
    fn = ast.parse('def original_handoff(source, role, schema):\n    pass\n').body[0]
    fn.body = [deepcopy(assignment), deepcopy(branch)]
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 '<authenticated-original-handoff-policy>', 'exec'), namespace)
    return FunctionType(namespace[fn.name].__code__, vars(runtime), fn.name)

def source_port(workflow, route, cls=None):
    home, class_name, roles, _ = route
    cls = cls or getattr(own(home.replace('/', '.') + '.task'), class_name)
    source = object.__new__(cls)
    source.workflow = workflow
    source.path = tuple((role, 'provided_' + str(index)) for index, role in enumerate(roles))
    source.scope = workflow.store.validate_scope()
    source.episode_id = 'provided_handoff_parent'
    return source

def selected_boundary(workflow, source, role, schema, monkeypatch, *, fail=None, required=()):
    runtime = own('runtime'); policy = own('library.hpc_handoff_return_form')
    original = original_function('Workflow', 'selected')
    results = []
    private_counts = []
    validator = policy.validate_hpc_handoff_return_form
    for method in (original, runtime.Workflow.selected):
        events = []; private_calls = []
        def contract(*args):
            events.append('expanded_contract')
            if fail == 'expanded': raise PortFailure('expanded')
            return schema, None
        def return_sources(context, requested):
            events.append(('required_return_sources', requested))
            if fail == 'required': raise PortFailure('required')
            return required
        def child(path, requested):
            events.append(('for_child', path, requested))
            return SimpleNamespace(required_return_sources=return_sources)
        def initial(*args):
            events.append('initial_report')
            raise InitialReportBoundary('before report parsing and child preparation')
        def private(*args):
            private_calls.append(True)
            return validator(*args)
        with monkeypatch.context() as patch:
            patch.setattr(workflow, 'validate_child_choice', lambda *a, **k: None)
            patch.setattr(workflow, 'permits_common_action', lambda *a: True)
            patch.setattr(workflow, '_closed_child_commission', lambda *a: None)
            patch.setattr(workflow, 'expanded_contract_form', contract)
            patch.setattr(workflow, 'binding_context', lambda _source: SimpleNamespace(role=_source.path[-1][0], path=_source.path))
            patch.setattr(workflow, 'episode_bindings', SimpleNamespace(for_child=child))
            patch.setattr(workflow, 'child_initial_report_input', initial)
            patch.setattr(policy, 'validate_hpc_handoff_return_form', private)
            try:
                method(workflow, source, {'kind':'episode_child','role':role,'scope':source.scope}, 0)
            except (InitialReportBoundary, PortFailure, runtime.ContractError) as error:
                result = (type(error), error.args)
            else:
                raise AssertionError('selected passed the supplied acquisition boundary')
        results.append((result, events)); private_counts.append(len(private_calls))
    assert results[0] == results[1]
    assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
    return results[1], private_counts

@pytest.mark.parametrize('route', ROUTES, ids=('hpc','allocation','hpc_launch','allocation_launch','scientific_hpc','scientific_allocation','scientific_hpc_launch','scientific_allocation_launch'))
@pytest.mark.parametrize('has_handoff', (False, True), ids=('missing','present'))
def test_eight_private_routes_preserve_original_selected_boundary(tmp_path, monkeypatch, route, has_handoff):
    runtime = own('runtime'); policy = own('library.hpc_handoff_return_form')
    with actual_workflow(tmp_path) as workflow:
        source = source_port(workflow, route)
        assert policy.private_handoff_validator(source) is policy.validate_hpc_handoff_return_form
        schema = {'type':'object','properties':{'facts':{'x-source':'execution_handoff_refs' if has_handoff else 'other'}}}
        (result, events), calls = selected_boundary(workflow, source, route[3], schema, monkeypatch)
        assert calls == [0, 1]
        assert events[0] == 'expanded_contract'
        assert events[2] == ('required_return_sources', route[3])
        if has_handoff:
            assert result[0] is InitialReportBoundary and events[-1] == 'initial_report'
        else:
            assert result == (runtime.ContractError, ('hpc_launch_requires_original_handoff_fact_in_return_form',))
            assert 'initial_report' not in events

@pytest.mark.parametrize('failed_port', ('expanded','required'))
def test_original_contract_callback_error_precedes_private_policy(tmp_path, monkeypatch, failed_port):
    with actual_workflow(tmp_path) as workflow:
        source = source_port(workflow, ROUTES[0])
        (result, events), calls = selected_boundary(workflow, source, 'launch', {'properties':{}}, monkeypatch, fail=failed_port)
        assert result == (PortFailure, (failed_port,)) and calls == [0, 0]
        assert 'initial_report' not in events

def test_original_required_return_error_precedes_private_handoff_error(tmp_path, monkeypatch):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = source_port(workflow, ROUTES[0])
        (result, events), calls = selected_boundary(workflow, source, 'launch', {'properties':{}}, monkeypatch, required=('required_fact',))
        assert result == (runtime.ContractError, ('child_return_requires_required_fact',))
        assert calls == [0, 0] and 'initial_report' not in events

def test_contract_error_is_resolved_after_schema_callback(monkeypatch):
    runtime = own('runtime'); current = own('library.hpc_handoff_return_form').validate_hpc_handoff_return_form
    class LateContractError(Exception): pass
    observations = []
    for fn in (original_policy(), current):
        events = []
        class Fact(dict):
            def get(self, key, default=None):
                events.append(('fact_get', key))
                runtime.ContractError = LateContractError
                return 'other'
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'ContractError', runtime.ContractError)
            with pytest.raises(LateContractError) as caught:
                fn(SimpleNamespace(path=(('hpc','owned'),)), 'launch', {'properties':{'fact':Fact()}})
        observations.append((events, caught.value.args))
    assert observations[0] == observations[1] == ([('fact_get','x-source')], ('hpc_launch_requires_original_handoff_fact_in_return_form',))

def test_schema_callback_failure_does_not_resolve_error_provider(monkeypatch):
    runtime = own('runtime'); current = own('library.hpc_handoff_return_form').validate_hpc_handoff_return_form
    for fn in (original_policy(), current):
        events = []
        class Schema:
            def get(self, *args):
                events.append('schema_get'); raise PortFailure('schema')
        def error_provider(*args):
            events.append('error_provider'); return RuntimeError(*args)
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'ContractError', error_provider)
            with pytest.raises(PortFailure, match='^schema$'):
                fn(SimpleNamespace(path=(('hpc','owned'),)), 'launch', Schema())
        assert events == ['schema_get']

@pytest.mark.parametrize('role,path,any_calls', (
    ('monitor', (), 0),
    ('launch', (('annotation','root'),), 0),
    ('launch_hpc', (('annotation','root'),('launch','child')), 1),
    ('launch_hpc', (('annotation','root'),('hpc','parent'),('launch','child')), 2),
), ids=('unrelated_role','non_hpc_launch','no_hpc_ancestor','hpc_ancestor'))
def test_original_short_circuit_and_live_any_lookup(monkeypatch, role, path, any_calls):
    runtime = own('runtime'); current = own('library.hpc_handoff_return_form').validate_hpc_handoff_return_form
    observations = []
    for fn in (original_policy(), current):
        events = []
        class Schema:
            def get(self, key, default=None):
                events.append(('schema_get',key)); return {'fact':{'x-source':'execution_handoff_refs'}}
        def any_port(values):
            events.append('any'); return builtins.any(values)
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'any', any_port, raising=False)
            assert fn(SimpleNamespace(path=path), role, Schema()) is None
        assert events.count('any') == any_calls
        assert sum(isinstance(e,tuple) for e in events) == (1 if any_calls==2 else 0)
        observations.append(events)
    assert observations[0] == observations[1]

@pytest.mark.parametrize('custom', ('subclass','instance_override','class_override','module_rebound','custom_getattribute','dictionary_subclass','metaclass'))
def test_custom_and_rebound_sources_keep_literal_fallback(tmp_path, monkeypatch, custom):
    runtime=own('runtime'); policy=own('library.hpc_handoff_return_form')
    module=own('hpc_work_planning.task'); cls=module.HPCWorkTask
    class CustomDictionary(dict):
        def get(self,*args): raise AssertionError('new dictionary callback')
    class CustomMeta(type):
        @property
        def __mro__(self): raise AssertionError('new metaclass callback')
    with actual_workflow(tmp_path) as workflow, monkeypatch.context() as patch:
        if custom=='subclass': cls=type('CustomTask',(cls,),{})
        if custom=='custom_getattribute':
            cls=type('CustomTask',(cls,),{'__getattribute__':lambda self,name: object.__getattribute__(self,name)})
        if custom=='metaclass': cls=CustomMeta('CustomTask',(cls,),{})
        source=source_port(workflow,ROUTES[0],cls)
        if custom=='instance_override': source.child_return_form_policy=object()
        if custom=='class_override': patch.setattr(cls,'child_return_form_policy',object())
        if custom=='module_rebound': patch.setattr(module,'HPCWorkTask',object())
        if custom=='dictionary_subclass': source.__dict__=CustomDictionary(vars(source))
        assert policy.private_handoff_validator(source) is None
        (result,events),calls=selected_boundary(workflow,source,'launch',{'properties':{}},patch)
        assert calls==[0,0]
        assert result==(runtime.ContractError,('hpc_launch_requires_original_handoff_fact_in_return_form',))
        assert 'initial_report' not in events

def test_original_body_live_namespace_and_literal_custom_fallback():
    runtime=own('runtime'); policy=own('library.hpc_handoff_return_form')
    assert policy.validate_hpc_handoff_return_form.__globals__ is vars(runtime)
    assert policy.private_handoff_validator.__globals__ is vars(policy)
    current,=ast.parse(inspect.getsource(policy.validate_hpc_handoff_return_form)).body
    original=original_node('Workflow','selected')
    assignment,=[n for n in ast.walk(original) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='hpc_launch' for t in n.targets)]
    branch,=[n for n in ast.walk(original) if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.values[0],ast.Name) and n.test.values[0].id=='hpc_launch']
    assert [ast.dump(n) for n in current.body]==[ast.dump(assignment),ast.dump(branch)]
    selected=ast.parse('class Selected:\n'+inspect.getsource(runtime.Workflow.selected)).body[0].body[0]
    fallback,=[n for n in ast.walk(selected) if isinstance(n,ast.If) and ast.dump(n.test)==ast.dump(ast.parse('_hpc_handoff_policy is None',mode='eval').body)]
    assert [ast.dump(n) for n in fallback.body]==[ast.dump(assignment),ast.dump(branch)]

def test_later_builtins_replacement_preserves_original_captured_lookup(monkeypatch):
    runtime = own('runtime')
    current = own('library.hpc_handoff_return_form').validate_hpc_handoff_return_form
    # Construct the original function before replacing the globals entry.
    # FunctionType captures builtins at creation, as the original module does.
    original = original_policy()
    captured = runtime.Workflow.selected.__builtins__
    assert original.__builtins__ is current.__builtins__ is captured
    events = []
    def replaced_any(values):
        events.append('new builtins mapping used')
        raise AssertionError('later builtins mapping replaced captured original')
    with monkeypatch.context() as patch:
        patch.delattr(runtime, 'any', raising=False)
        patch.setattr(runtime, '__builtins__', {'any': replaced_any})
        for function in (original, current):
            assert function(SimpleNamespace(path=(('hpc','owned'),)), 'launch',
                {'properties': {'fact': {'x-source':'execution_handoff_refs'}}}) is None
            assert function.__builtins__ is captured
    assert events == []
