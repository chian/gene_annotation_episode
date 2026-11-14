"""Shared original-source oracle for the 39 named private A101 task consumers.

Each actual case lives in its owner's tests. Namespace/body checks cover every
selected descriptor. Three source-group representatives exercise existing late
role inputs and report providers; Literature also checks its real registry and
credit-kind callback. These supplied ports do not run scientific work.
"""
import ast
import asyncio
from contextlib import nullcontext
from copy import deepcopy
from functools import lru_cache
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from types import FunctionType, MethodType, SimpleNamespace

from .. import runtime

PACKAGE = runtime.__name__.rsplit('.', 1)[0]
FIXTURE = Path(__file__).parent / 'fixtures/other_task_runtime_providers/originals.txt'
FIXTURE_SHA256 = '0decbfc54ebca85c2439834dd5342eb193b9c03578c237704115a0a7865463d0'


def shape(node):
    return ast.dump(node, include_attributes=False)


@lru_cache(maxsize=1)
def bundle():
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value = json.loads(raw)
    for row in value['sources'].values():
        assert hashlib.sha256(row['text'].encode()).hexdigest() == row['sha256']
    for row in value['baselines'].values():
        assert hashlib.sha256(row['text'].encode()).hexdigest() == row['sha256']
    return value


def owner(home, module):
    return importlib.import_module(PACKAGE + '.' + home.replace('/', '.') + '.' + module)


def original_node(home, module, name):
    row = bundle()['homes'][home]['modules'][module]
    text = bundle()['sources'][row['source_target']]['text']
    cls, = [n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == row['class']]
    node, = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return deepcopy(node)


def compile_original(node):
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(node)], type_ignores=[])), str(FIXTURE), 'exec'), namespace)
    parsed = namespace[node.name]
    result = FunctionType(parsed.__code__, vars(runtime), parsed.__name__, parsed.__defaults__)
    result.__kwdefaults__ = parsed.__kwdefaults__
    return result


def original(home, module, name):
    return compile_original(original_node(home, module, name))


def baseline_node(home, name):
    info = bundle()['homes'][home]
    text = bundle()['baselines'][info['original_runtime']]['text']
    cls, = [n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == 'DecisionSource']
    node, = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return deepcopy(node)


def current(home, module, name):
    return vars(getattr(owner(home, module), bundle()['homes'][home]['modules'][module]['class']))[name]


def before_current_role_correction(home, module, node):
    node = deepcopy(node)
    info = bundle()['homes'][home]
    path = shape(ast.parse('self.path[-1][0]', mode='eval').body)
    if module == 'decision_inputs' and node.name == 'decision_inputs':
        found = []
        for method in ('applies', 'capture'):
            call, = [n for n in ast.walk(node) if isinstance(n, ast.Call) and shape(n.func) == shape(ast.parse('binding.'+method, mode='eval').body)]
            assert shape(call.args[0]) == path
            found.append(call.args[0]); call.args[0] = ast.Constant(value=info['role'])
        planning, = [n for n in ast.walk(node) if isinstance(n, ast.Compare) and len(n.comparators) == 1 and shape(n.comparators[0]) == shape(ast.parse('binding.planning_roles', mode='eval').body)]
        assert shape(planning.left) == path
        found.append(planning.left); planning.left = ast.Constant(value=info['role'])
        assert len(found) == 3
    elif module == 'task' and node.name == 'apply_response':
        call, = [n for n in ast.walk(node) if isinstance(n, ast.Call) and shape(n.func) == shape(ast.parse('self.workflow.validate_report', mode='eval').body)]
        grain, = [k for k in call.keywords if k.arg == 'grain']
        assert shape(grain.value) == path; grain.value = ast.Constant(value=info['role'])
    elif module == 'decision_state' and info['family'] == 'literature':
        guard, = [n for n in ast.walk(node) if isinstance(n, ast.If) and shape(n.test) == shape(ast.parse('self.workflow.is_scientific_source(self)', mode='eval').body)]
        assert len(guard.body) == 1 and not guard.orelse
        class Before(ast.NodeTransformer):
            def visit_If(self, value):
                return guard.body if value is guard else self.generic_visit(value)
        node = Before().visit(node)
    return node


def assert_private_owners(home):
    info = bundle()['homes'][home]
    checked = 0
    for module, row in info['modules'].items():
        imported = owner(home, module); cls = getattr(imported, row['class'])
        for name in row['methods']:
            function = vars(cls)[name]
            holder, = ast.parse('class _ExactIndent:\n' + inspect.getsource(function)).body
            node, = holder.body
            assert shape(before_current_role_correction(home, module, node)) == shape(original_node(home, module, name))
            assert function.__globals__ is vars(runtime)
            assert function.__module__ == imported.__name__ and function.__qualname__ == row['class']+'.'+name
            assert function.__code__.co_filename == imported.__file__ and function.__closure__ is None
            old = original(home, module, name)
            assert function.__defaults__ == old.__defaults__ and function.__kwdefaults__ == old.__kwdefaults__
            checked += 1
    assert checked == info['definition_count']
    task = getattr(owner(home, 'task'), info['source_class'])
    assert [base.__name__ for base in task.__bases__] == info['class_bases']
    assert task.finish is current(home, 'report_delivery', 'finish')
    assert task.__init__ is current(home, 'task_state', '__init__')
    assert task.call is current(home, 'task_decision', 'call')
    assert task.decision_inputs is current(home, 'decision_inputs', 'decision_inputs')
    declaration = getattr(owner(home, 'episode'), info['declaration_class'])
    assert declaration.decision_source_type is task and declaration.binding_path == home and info['role'] in declaration.roles
    composer = owner(home, 'task_instructions')
    assert task.instruction_composer is composer.instructions and composer.instructions.__globals__ is vars(composer)
    marker = object(); calls = []
    source = SimpleNamespace(workflow=SimpleNamespace(services=SimpleNamespace(instructions=lambda s, c: calls.append((s,c)) or marker)))
    context = object()
    assert task.instructions(source, context) is marker and calls == [(source, context)]


class ProviderFailure(Exception):
    pass


def assert_conversation_lookup(home, monkeypatch):
    """Only the original method's late builtin lookup, not a new provider API."""
    selected = current(home, 'task_decision', 'conversation_key')
    assert selected.__globals__ is vars(runtime)
    for outcome in ('returned', 'lookup_failure', 'callback_failure', 'absent'):
        def exercise(function):
            events = []
            provider = object()
            def wrong(*args):
                raise AssertionError('original_getattr_callee_reloaded_after_argument')
            class Workflow:
                @property
                def provider(self):
                    events.append('provider_argument')
                    runtime.getattr = wrong
                    return provider
            source = SimpleNamespace(workflow=Workflow(), episode_id='original-task')
            def callback(episode_id, role):
                assert (episode_id, role) == ('original-task', 'REASONING')
                events.append('callback')
                if outcome == 'callback_failure':
                    raise ProviderFailure('original_callback_failure')
                return ('same-conversation', 1)
            def lookup(value, name, default):
                assert value is provider and name == 'conversation_key' and default is None
                events.append('getattr')
                if outcome == 'lookup_failure':
                    raise ProviderFailure('original_lookup_failure')
                return None if outcome == 'absent' else callback
            with monkeypatch.context() as patch:
                patch.setattr(runtime, 'getattr', lookup, raising=False)
                try:
                    result = ('returned', function(source))
                except ProviderFailure as error:
                    result = (type(error), str(error))
            return result, events
        expected = exercise(original(home, 'task_decision', 'conversation_key'))
        assert exercise(selected) == expected
        assert expected[1] == (['provider_argument', 'getattr', 'callback'] if outcome in ('returned', 'callback_failure') else ['provider_argument', 'getattr'])


def assert_report_release(home, route, failure, monkeypatch):
    def exercise(function):
        events = []
        def record(value):
            events.append(('Record', value))
            if failure: raise ProviderFailure('late_record_failure')
            return {'record': value}
        def serialize(value): events.append(('_json', value)); return repr(value)
        def form(values, schema, facts):
            events.append(('form', values, schema, facts)); runtime._json = serialize
            return {'fresh': True}
        def row(*args):
            events.append(('row', args)); runtime.json = SimpleNamespace(loads=lambda value: events.append(('loads', value)) or {'saved': True})
            return {'form': 'saved-json'} if route == 'saved_form' else None
        def facts(source, completion_record): events.append(('facts', completion_record)); runtime.form_with_facts = form; return {'finding':'qualified'}
        async def release(episode_id):
            events.append(('release_enter', episode_id)); await asyncio.sleep(0)
            runtime.Record = record; events.append(('release_done', episode_id))
        workflow = SimpleNamespace(source_credit_view=lambda source:{'credit':.25}, pending_handles=lambda source:['pending'],
            episode_bindings=SimpleNamespace(current_report_facts=lambda context:{'qualified':'received'}), binding_context=lambda source:source,
            release=release, facts=facts, journal=SimpleNamespace(row=row, save=lambda *args:events.append(('save',args))))
        source = SimpleNamespace(workflow=workflow,episode_id='original-report',report_values={'unresolved':True},
            request=SimpleNamespace(report_contract=None if route=='uncontracted' else SimpleNamespace(schema={'type':'object'})))
        def early(*args,**kwargs): raise AssertionError('runtime_provider_read_too_early')
        with monkeypatch.context() as patch:
            for name in ('Record','_json','form_with_facts'): patch.setattr(runtime,name,early)
            patch.setattr(runtime,'json',SimpleNamespace(loads=early))
            try: result=('returned',asyncio.run(function(source,{'completion':'retained'})))
            except ProviderFailure as error: result=(type(error),str(error))
        return result,events
    expected=exercise(original(home,'report_delivery','finish'))
    assert exercise(current(home,'report_delivery','finish'))==expected
    assert expected[1][-2][0]=='release_done' and expected[1][-1][0]=='Record'


class OwnRole(str):
    """Same admitted role text; identity reveals a late read without foreign roles."""


def original_expectations(home):
    call=baseline_node(home,'call')
    assignment,=[n for n in ast.walk(call) if isinstance(n,ast.Assign) and shape(n.value)==shape(ast.parse('self.workflow.execution_expectations',mode='eval').body)]
    parent,=[n for n in ast.walk(call) if isinstance(n,ast.If) and assignment in n.orelse]
    index=parent.orelse.index(assignment); conditional=parent.orelse[index+1]
    assert ast.unparse(conditional.test)=='binding is not None and binding.applies(self.path[-1][0])'
    fn,=ast.parse('def original(self, context):\n    return context\n').body
    fn.body=[deepcopy(assignment),deepcopy(conditional),fn.body[0]]
    return compile_original(fn)


def assert_expectation_role(home,boundary):
    role=bundle()['homes'][home]['role']
    def exercise(function,complete):
        events=[]; late=OwnRole(role); source=SimpleNamespace(path=((role,'existing'),),scope='scope')
        class Roles:
            def __contains__(self,value): events.append(('planning_role',str(value),value is late)); return True
        class Binding:
            planning_roles=Roles()
            def applies(self,value):
                events.append(('applies',str(value),value is late))
                if boundary=='planning':source.path=((late,'existing'),)
                return boundary!='applies'
            def capture(self,value,**kwargs): events.append(('capture',str(value),value is late,kwargs)); return {'role':str(value),**kwargs}
        binding=Binding()
        def classes(store,scope):
            events.append(('planning',scope))
            if boundary=='capture':source.path=((late,'existing'),)
            return []
        class Workflow:
            @property
            def execution_expectations(self):
                events.append('binding')
                if boundary=='applies':source.path=((late,'existing'),)
                return binding
        workflow=Workflow();workflow.job_episodes=SimpleNamespace(jobs=SimpleNamespace(config={}),prospective_execution_classes=classes)
        workflow.store=object();workflow.resource_context=lambda source:None;workflow.shared_information_context=lambda source:None
        workflow.launch_instructions=SimpleNamespace(context=lambda:{},materialize=lambda value:None)
        workflow.available_child_roles=lambda source:();workflow.binding_context=lambda source:source
        workflow.episode_bindings=SimpleNamespace(initial_decision_context=lambda context:{})
        workflow.resource_estimator=None;workflow.native_estimation_context=lambda source,context:None
        workflow.native_event_information=None;workflow.permits_common_action=lambda source,action:False
        source.workflow=workflow;source.request=SimpleNamespace(message=SimpleNamespace(as_record=lambda:{'job_assignment':{'original':True}}))
        context={'launch_instruction_library':{},'pending_work':{},'literature_completed_work':{}}
        result=function(source,deepcopy(context),0,None) if complete else function(source,deepcopy(context))
        return result,events
    expected=exercise(original_expectations(home),False)
    assert exercise(current(home,'decision_inputs','decision_inputs'),True)==expected
    event=next(e for e in expected[1] if isinstance(e,tuple) and e[0]=={'applies':'applies','planning':'planning_role','capture':'capture'}[boundary])
    assert event[1:3]==(role,True)


def assert_report_grain(home,monkeypatch):
    role=bundle()['homes'][home]['role'];marker=object()
    def exercise(function):
        events=[];late=OwnRole(role)
        source=SimpleNamespace(path=((role,'existing'),),scope='scope',episode_id='source',_delivery_resolution_ref=None,report_values={},
            interpret_schema={'type':'object','properties':{'ready':{'type':'boolean'}},'required':['ready'],'additionalProperties':False})
        def message():events.append('assignment');source.path=((late,'existing'),);return {'job_assignment':{'original':True}}
        def validate(value,scope,**kwargs):events.append(('validate_report',str(kwargs['grain']),kwargs['grain'] is late));assert kwargs['source'] is source
        source.request=SimpleNamespace(message=SimpleNamespace(as_record=message));source.record_effect=lambda *args:None
        source.workflow=SimpleNamespace(journal=SimpleNamespace(row=lambda *args:None),decision_exchanges=None,permits_common_action=lambda source,action:False,
            execution_binding=None,selected=lambda *args:marker,resolver=lambda *args,**kwargs:lambda ref:True,validate_report=validate)
        with monkeypatch.context() as patch:
            patch.setattr(runtime,'_decode_recorded_action_response',lambda response,*args,**kwargs:response)
            result=function(source,{'selection':{'kind':'tool'},'report_update':{'ready':True}},0,{'visible_record_refs':[]},{'properties':{'selection':{'type':'object'}}})
        return result is marker,source.report_values,source.report_basis,source.feedback,events
    expected=exercise(compile_original(baseline_node(home,'apply_response')))
    assert exercise(current(home,'task','apply_response'))==expected
    assert expected[-1]==['assignment',('validate_report',role,True)]


class ContextBoundary(Exception):
    pass


def assert_literature_context_guard(home,failure,monkeypatch):
    info=bundle()['homes'][home];assert info['family']=='literature'
    original_next=baseline_node(home,'next')
    snapshot,=[n for n in ast.walk(original_next) if isinstance(n,ast.With) and ast.unparse(n.items[0].context_expr)=='self.workflow.store.read_snapshot()']
    fn,=ast.parse('def original(self, view):\n    return context\n').body;fn.body=[snapshot,fn.body[0]]
    def exercise(function):
        events=[];binding=getattr(owner(home,'episode'),info['declaration_class'])(SimpleNamespace())
        registry=runtime.EpisodeBindingRegistry((binding,))
        source=SimpleNamespace(path=((info['role'],'existing'),),episode_id='source',scope='scope',last_outcome=None,last_outcome_index=None,
            feedback=None,report_values={},report_basis=[],interpret_schema={'type':'object','properties':{}},request=SimpleNamespace(goal=SimpleNamespace(as_record=lambda:{}),report_contract=None))
        workflow=SimpleNamespace(episode_bindings=registry,run_id='run',store=SimpleNamespace(read_snapshot=lambda:nullcontext(),get=lambda reference:None),
            journal=SimpleNamespace(db=SimpleNamespace(execute=lambda *args:SimpleNamespace(fetchone=lambda:None)),elapsed_view=lambda *args:{}),
            working_state=lambda source:{},local_outcome_preview=lambda *args,**kwargs:None,source_credit_view=lambda source:{'credit':.25},
            receipt_projection=lambda source:False,source_credit_binding=lambda source:{},pending_work=lambda source:{},delivery_status=lambda *args:[],controller_binding={},
            catalog=lambda *args,**kwargs:{},knowledge=SimpleNamespace(context=lambda:{}),job_episode_options=lambda source:None,extra_report_sources=lambda source:{})
        workflow.specialist=MethodType(runtime.Workflow.specialist,workflow)
        workflow.is_scientific_source=MethodType(runtime.Workflow.is_scientific_source,workflow)
        def annotation(*args,**kwargs):events.append('annotation_context');raise ContextBoundary('original_annotation_boundary')
        workflow.annotation_context=annotation;source.workflow=workflow
        before_kind=binding.credit_kind;before_path=registry.for_path
        def model_inputs(value,**kwargs):
            events.append('model_inputs')
            def path(value):events.append('registry_for_path');return before_path(value)
            def kind(value):
                events.append(('credit_kind',value));result=before_kind(value)
                events.append(('validated_role',result))
                if failure:raise ProviderFailure('late_credit_kind_failure')
                return result
            registry.for_path=path;binding.credit_kind=kind
            return value
        view=SimpleNamespace(child_reports=(),controller_state={},model_inputs=model_inputs)
        try:function(source,view)
        except (ProviderFailure,ContextBoundary) as error:result=(type(error),str(error))
        else:raise AssertionError('original_context_boundary_not_reached')
        return result,events
    expected=exercise(compile_original(fn))
    assert exercise(current(home,'decision_state','decision_state'))==expected
    assert expected[1][:4]==['model_inputs','registry_for_path',('credit_kind',info['role']),('validated_role','scientific')]
    assert ('annotation_context' in expected[1]) is (not failure)
