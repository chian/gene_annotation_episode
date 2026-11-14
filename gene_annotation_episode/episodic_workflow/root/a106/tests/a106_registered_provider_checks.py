"""Named A106 registered-task provider and callback boundary oracles.

Each behavioral case belongs to the private home that invokes this helper.
The retained fixture contains exact before sources, original same-axis runtime
sources and current source accounts. Engineering cutoff ports do not acquire
children, perform scientific work or establish restoration of a full Workflow.
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
FIXTURE = Path(__file__).parent / 'fixtures/registered_provider_originals/originals.txt'
FIXTURE_SHA256 = '6f8256caae6be5c4d9760f51a88bfe448204565a1bdfc6dd0e2eb2d8bcc5332e'


def shape(node):
    return ast.dump(node, include_attributes=False)


@lru_cache(maxsize=1)
def bundle():
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value = json.loads(raw)
    for row in value['sources'].values():
        assert hashlib.sha256(row['before_text'].encode()).hexdigest() == row['before_sha256']
        assert hashlib.sha256(row['after_text'].encode()).hexdigest() == row['after_sha256']
    for row in value['baselines'].values():
        assert hashlib.sha256(row['text'].encode()).hexdigest() == row['sha256']
    return value


def owner(home, module):
    return importlib.import_module(PACKAGE + '.' + home.replace('/', '.') + '.' + module)


def node_from(text, class_name, name):
    tree = ast.parse(text)
    scope = tree if class_name is None else next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    node, = [n for n in scope.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return deepcopy(node)


def original_node(home, module, name):
    info = bundle()['homes'][home]['modules'][module]
    return node_from(bundle()['sources'][info['target']]['before_text'], info['class'], name)


def compile_original(node, namespace=None):
    scratch = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(node)], type_ignores=[])), str(FIXTURE), 'exec'), scratch)
    parsed = scratch[node.name]
    function = FunctionType(parsed.__code__, vars(runtime) if namespace is None else namespace, parsed.__name__, parsed.__defaults__)
    function.__kwdefaults__ = parsed.__kwdefaults__
    return function


def original(home, module, name, lexical=False):
    return compile_original(original_node(home, module, name), vars(owner(home, module)) if lexical else None)


def baseline_node(home, name):
    info = bundle()['homes'][home]
    return node_from(bundle()['baselines'][info['original_runtime']]['text'], 'DecisionSource', name)


def current(home, module, name):
    imported = owner(home, module)
    cls = bundle()['homes'][home]['modules'][module]['class']
    return vars(imported)[name] if cls is None else vars(getattr(imported, cls))[name]


def assert_private_owners(home, monkeypatch):
    info = bundle()['homes'][home]
    count = 0
    for module, row in info['modules'].items():
        imported = owner(home, module)
        for record in row['functions']:
            name = record['name']
            function = current(home, module, name)
            inspected = inspect.getsource(function)
            if row['class'] is None:
                node, = ast.parse(inspected).body
            else:
                holder, = ast.parse('class _ExactIndent:\n' + inspected).body
                node, = holder.body
            expected = node_from(bundle()['sources'][row['target']]['after_text'], row['class'], name)
            assert shape(node) == shape(expected)
            mixed = bool(record['private_global_reads'])
            assert function.__globals__ is (vars(imported) if mixed else vars(runtime))
            qualified = name if row['class'] is None else row['class'] + '.' + name
            assert function.__module__ == imported.__name__ and function.__qualname__ == qualified
            assert function.__code__.co_filename == imported.__file__ and function.__closure__ is None
            before = original(home, module, name)
            assert function.__defaults__ == before.__defaults__ and function.__kwdefaults__ == before.__kwdefaults__
            for private, witness in record['private_global_reads'].items():
                assert witness['module'] == 'decision_presentation' and witness['level'] == 1
                assert vars(imported)[private] is vars(owner(home, 'decision_presentation'))[private]
            count += 1
        for getter_name, global_name in row['getter_global_names'].items():
            getter = vars(imported)[getter_name]
            assert getter.__globals__ is vars(runtime) and getter.__closure__ is None
            assert getter.__code__.co_names == (global_name,)
    assert count == info['definition_count']
    task = getattr(owner(home, 'task'), info['task_class'])
    assert [base.__name__ for base in task.__bases__] == info['task_bases']
    for module, method in (('report_delivery', 'finish'), ('task_state', '__init__'), ('task_decision', 'call'), ('decision_inputs', 'decision_inputs')):
        assert getattr(task, method) is current(home, module, method)
    declaration = getattr(owner(home, 'episode'), info['declaration_class'])
    assert declaration.decision_source_type is task and declaration.binding_path == home and info['role'] in declaration.roles
    composer = owner(home, 'task_instructions')
    assert task.instruction_composer is composer.instructions and composer.instructions.__globals__ is vars(composer)
    marker = object(); calls = []
    source = SimpleNamespace(workflow=SimpleNamespace(services=SimpleNamespace(instructions=lambda s, c: calls.append((s, c)) or marker)))
    context = object()
    assert task.instructions(source, context) is marker and calls == [(source, context)]
    assert_conversation_lookup(home, monkeypatch)


class BoundaryStop(Exception):
    pass


def assert_conversation_lookup(home, monkeypatch):
    def exercise(function, fail):
        events = []
        def callback(episode_id, role):
            events.append(('callback', episode_id, role))
            if fail:
                raise BoundaryStop('original_callback_error')
            return 'existing-conversation'
        provider = SimpleNamespace(conversation_key=callback)
        def first_getattr(value, name, default):
            events.append(('getattr', value is provider, name, default))
            return callback
        def wrong(*args):
            raise AssertionError('callee_resolved_after_provider_argument')
        class Workflow:
            @property
            def provider(self):
                events.append('provider_argument')
                runtime.getattr = wrong
                return provider
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'getattr', first_getattr, raising=False)
            try:
                result = function(SimpleNamespace(workflow=Workflow(), episode_id='original-task'))
            except BoundaryStop as error:
                result = (type(error), str(error))
        return result, events
    for fail in (False, True):
        expected = exercise(original(home, 'task_decision', 'conversation_key'), fail)
        assert exercise(current(home, 'task_decision', 'conversation_key'), fail) == expected
        assert expected[1][0] == 'provider_argument' and expected[1][1][0] == 'getattr'


def assert_report_release(home, route, failure, monkeypatch):
    def exercise(function):
        events = []
        def late_record(value):
            events.append(('Record', value))
            if failure:
                raise BoundaryStop('late_record_failure')
            return {'record': value}
        def serialize(value):
            events.append(('_json', value)); return repr(value)
        def form(values, schema, facts):
            events.append(('form', values, schema, facts)); runtime._json = serialize
            return {'fresh': True}
        def row(*args):
            events.append(('row', args))
            runtime.json = SimpleNamespace(loads=lambda value: events.append(('loads', value)) or {'saved': True})
            return {'form': 'saved-json'} if route == 'saved_form' else None
        def facts(source, completion_record):
            events.append(('facts', completion_record)); runtime.form_with_facts = form
            return {'finding': 'qualified'}
        async def release(episode_id):
            events.append(('release_enter', episode_id)); await asyncio.sleep(0)
            runtime.Record = late_record; events.append(('release_done', episode_id))
        workflow = SimpleNamespace(source_credit_view=lambda source: {'credit': .25}, pending_handles=lambda source: ['pending'],
            episode_bindings=SimpleNamespace(current_report_facts=lambda context: {'qualified': 'received'}),
            binding_context=lambda source: source, release=release, facts=facts,
            journal=SimpleNamespace(row=row, save=lambda *args: events.append(('save', args))))
        source = SimpleNamespace(workflow=workflow, episode_id='original-task', report_values={'unresolved': True},
            request=SimpleNamespace(report_contract=None if route == 'uncontracted' else SimpleNamespace(schema={'type': 'object'})))
        def early(*args, **kwargs):
            raise AssertionError('provider_read_before_original_callback')
        with monkeypatch.context() as patch:
            for name in ('Record', '_json', 'form_with_facts'):
                patch.setattr(runtime, name, early)
            patch.setattr(runtime, 'json', SimpleNamespace(loads=early))
            try:
                result = ('returned', asyncio.run(function(source, {'completion': 'retained'})))
            except BoundaryStop as error:
                result = (type(error), str(error))
        return result, events
    expected = exercise(original(home, 'report_delivery', 'finish'))
    assert exercise(current(home, 'report_delivery', 'finish')) == expected
    assert expected[1][-2][0] == 'release_done' and expected[1][-1][0] == 'Record'


def input_workflow():
    return SimpleNamespace(resource_context=lambda source: None, shared_information_context=lambda source: None,
        launch_instructions=SimpleNamespace(context=lambda: {}, materialize=lambda value: None),
        available_child_roles=lambda source: (), binding_context=lambda source: source,
        episode_bindings=SimpleNamespace(initial_decision_context=lambda context: {}),
        resource_estimator=None, native_estimation_context=lambda source, context: None,
        permits_common_action=lambda source, action: False, execution_expectations=None)


def original_child_information(home):
    call = baseline_node(home, 'call')
    branch, = [n for n in ast.walk(call) if isinstance(n, ast.If) and shape(n.test) == shape(ast.parse('self.workflow.available_child_roles(self)', mode='eval').body)]
    node, = ast.parse('def child_information(self, context, index, profile):\n    pass').body
    node.body = [branch]
    return compile_original(node)


def assert_mixed_callee_order(home, mode, monkeypatch):
    def exercise(function):
        events = []; armed = False
        def chosen(*args):
            events.append('chosen_provider')
            raise BoundaryStop('original_selected_provider')
        def wrong(*args):
            raise AssertionError('late_argument_replaced_original_callee')
        workflow = input_workflow()
        def available(source):
            nonlocal armed
            events.append('available'); armed = True
            if mode == 'missing':
                del runtime.child_option_information
            else:
                runtime.child_option_information = chosen
            return ('existing-child',)
        workflow.available_child_roles = available
        class Source:
            request = SimpleNamespace(message=SimpleNamespace(as_record=lambda: {}))
            @property
            def workflow(self):
                nonlocal armed
                if armed:
                    armed = False; events.append('workflow_argument')
                    if mode == 'argument_rebind':
                        runtime.child_option_information = wrong
                return workflow
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'child_option_information', wrong)
            try:
                function(Source(), {}, 0, None)
            except (BoundaryStop, NameError) as error:
                result = (type(error), str(error))
            else:
                raise AssertionError('provider_boundary_not_reached')
        return result, events
    expected = exercise(original_child_information(home))
    assert exercise(current(home, 'decision_inputs', 'decision_inputs')) == expected
    assert expected[1] == (['available'] if mode == 'missing' else ['available', 'workflow_argument', 'chosen_provider'])


def assert_mixed_builtin_and_private_helper(home, shadow, monkeypatch):
    events = []
    imported = owner(home, 'decision_inputs')
    workflow = input_workflow()
    def private(source, context, index):
        events.append(('private', index, context['supplied']))
        raise BoundaryStop('private_completed_work')
    def wrong(*args, **kwargs):
        raise AssertionError('wrong_namespace_supplier')
    def runtime_set(value):
        events.append(('runtime_set', value))
        return set(value)
    def supplied(context):
        events.append('initial_context')
        if shadow:
            runtime.set = runtime_set
        else:
            patch.delattr(runtime, 'set')
        imported.prepare_completed_work = private
        return {'supplied': 'original'}
    workflow.episode_bindings.initial_decision_context = supplied
    source = SimpleNamespace(workflow=workflow, request=SimpleNamespace(message=SimpleNamespace(as_record=lambda: {})))
    with monkeypatch.context() as patch:
        patch.setattr(runtime, 'set', wrong, raising=False)
        patch.setattr(runtime, 'prepare_completed_work', wrong, raising=False)
        patch.setattr(imported, 'set', wrong, raising=False)
        patch.setattr(imported, 'prepare_completed_work', wrong)
        try:
            current(home, 'decision_inputs', 'decision_inputs')(source, {}, 7, None)
        except BoundaryStop as error:
            assert str(error) == 'private_completed_work'
        else:
            raise AssertionError('private_helper_not_reached')
    expected = ['initial_context']
    if shadow:
        expected.append(('runtime_set', {'supplied': 'original'}))
    expected.append(('private', 7, 'original'))
    assert events == expected


def assert_private_exchange_helper(home, monkeypatch):
    imported = owner(home, 'task_decision')
    def exercise(function):
        events = []
        def private(source, context, journal, index):
            events.append(('private_table', index)); raise BoundaryStop('private_yield_table')
        def rows(*args):
            events.append('rows'); imported.decision_yield_table = private
            return []
        def wrong(*args, **kwargs):
            raise AssertionError('private_table_resolved_in_runtime')
        source = SimpleNamespace(episode_id='source', workflow=SimpleNamespace(decision_exchanges=SimpleNamespace(rows=rows), journal=object()))
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'decision_yield_table', wrong, raising=False)
            patch.setattr(imported, 'decision_yield_table', wrong)
            try:
                asyncio.run(function(source, {}, {}, 4, {}))
            except BoundaryStop as error:
                result = (type(error), str(error))
            else:
                raise AssertionError('private_table_boundary_not_reached')
        return result, events
    expected = exercise(original(home, 'task_decision', 'exchange_decision', lexical=True))
    assert exercise(current(home, 'task_decision', 'exchange_decision')) == expected
    assert expected[1] == ['rows', ('private_table', 4)]


class OwnRole(str):
    """Same admitted text; identity exposes the original late operand read."""


def original_expectations(home):
    call = baseline_node(home, 'call')
    branch, = [n for n in call.body if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == 'row']
    index, = [i for i, n in enumerate(branch.orelse) if isinstance(n, ast.Assign) and shape(n.value) == shape(ast.parse('self.workflow.execution_expectations', mode='eval').body)]
    node, = ast.parse('def expectations(self, context):\n    return context').body
    node.body = deepcopy(branch.orelse[index:index + 2]) + node.body
    return compile_original(node)


def assert_expectation_role(home, boundary):
    role = bundle()['homes'][home]['role']
    def exercise(function, complete):
        late = OwnRole(role); events = []
        source = SimpleNamespace(path=((role, 'existing'),), request=SimpleNamespace(message=SimpleNamespace(as_record=lambda: {})))
        def applies(value):
            events.append(('applies', str(value), value is late))
            if boundary == 'applies':
                raise BoundaryStop('original_applies')
            source.path = ((late, 'existing'),)
            return True
        def capture(value):
            events.append(('capture', str(value), value is late)); raise BoundaryStop('original_capture')
        binding = SimpleNamespace(applies=applies, capture=capture)
        class Workflow:
            @property
            def execution_expectations(self):
                events.append('binding')
                if boundary == 'applies':
                    source.path = ((late, 'existing'),)
                return binding
        workflow = Workflow()
        for name, value in vars(input_workflow()).items():
            if name != 'execution_expectations':
                setattr(workflow, name, value)
        source.workflow = workflow
        context = {'pending_work': {}, 'literature_completed_work': {}}
        try:
            function(source, deepcopy(context), 0, None) if complete else function(source, deepcopy(context))
        except BoundaryStop as error:
            result = (type(error), str(error))
        else:
            raise AssertionError('expectation_boundary_not_reached')
        return result, events
    expected = exercise(original_expectations(home), False)
    assert exercise(current(home, 'decision_inputs', 'decision_inputs'), True) == expected
    assert expected[1][-1] == (boundary, role, True)


def assert_report_grain(home, monkeypatch):
    role = bundle()['homes'][home]['role']; marker = object()
    def exercise(function):
        events = []; late = OwnRole(role)
        source = SimpleNamespace(path=((role, 'existing'),), scope='scope', episode_id='source', _delivery_resolution_ref=None,
            report_values={}, interpret_schema={'type': 'object', 'properties': {'ready': {'type': 'boolean'}}, 'required': ['ready'], 'additionalProperties': False})
        def message():
            events.append('assignment'); source.path = ((late, 'existing'),)
            return {'job_assignment': {'original': True}}
        def validate(value, scope, **kwargs):
            events.append(('validate', str(kwargs['grain']), kwargs['grain'] is late)); assert kwargs['source'] is source
            raise BoundaryStop('original_report_argument_boundary')
        source.request = SimpleNamespace(message=SimpleNamespace(as_record=message))
        source.record_effect = lambda *args: None
        source.workflow = SimpleNamespace(journal=SimpleNamespace(row=lambda *args: None), decision_exchanges=None,
            permits_common_action=lambda source, action: False, execution_binding=None, selected=lambda *args: marker,
            resolver=lambda *args, **kwargs: lambda ref: True, validate_report=validate)
        with monkeypatch.context() as patch:
            patch.setattr(runtime, '_decode_recorded_action_response', lambda response, *args, **kwargs: response)
            try:
                function(source, {'selection': {'kind': 'tool'}, 'report_update': {'ready': True}}, 0, {'visible_record_refs': []}, {'properties': {'selection': {'type': 'object'}}})
            except BoundaryStop as error:
                result = (type(error), str(error))
            else:
                raise AssertionError('report_argument_boundary_not_reached')
        return result, events
    expected = exercise(compile_original(baseline_node(home, 'apply_response')))
    assert exercise(current(home, 'task', 'apply_response')) == expected
    assert expected[-1] == ['assignment', ('validate', role, True)]


def assert_private_credit_presentation(home, monkeypatch):
    imported = owner(home, 'decision_state')
    def exercise(function):
        events = []
        def private(*args):
            events.append('private_credit_state'); raise BoundaryStop('private_credit_presentation')
        def credit(source):
            events.append('credit_view'); imported.present_credit_state = private
            return {'credit': .25}
        def wrong(*args, **kwargs):
            raise AssertionError('private_summary_resolved_in_runtime')
        workflow = SimpleNamespace(store=SimpleNamespace(read_snapshot=lambda: nullcontext()),
            working_state=lambda source: {}, local_outcome_preview=lambda *args, **kwargs: None,
            journal=SimpleNamespace(db=SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: None))),
            source_credit_view=credit, run_id='run')
        source = SimpleNamespace(workflow=workflow, episode_id='source', last_outcome=None, last_outcome_index=None, feedback=None)
        with monkeypatch.context() as patch:
            patch.setattr(imported, 'present_credit_state', wrong)
            patch.setattr(runtime, 'present_credit_state', wrong, raising=False)
            try:
                function(source, SimpleNamespace())
            except BoundaryStop as error:
                result = (type(error), str(error))
            else:
                raise AssertionError('private_credit_boundary_not_reached')
        return result, events
    expected = exercise(original(home, 'decision_state', 'decision_state', lexical=True))
    assert exercise(current(home, 'decision_state', 'decision_state')) == expected
    assert expected[1] == ['credit_view', 'private_credit_state']


def assert_literature_context_guard(home, failure, monkeypatch):
    info = bundle()['homes'][home]
    assert info['family'] == 'literature'
    original_next = baseline_node(home, 'next')
    snapshot, = [n for n in ast.walk(original_next) if isinstance(n, ast.With) and ast.unparse(n.items[0].context_expr) == 'self.workflow.store.read_snapshot()']
    node, = ast.parse('def original(self, view):\n    return context').body
    node.body = [snapshot, node.body[0]]
    def exercise(function):
        events = []
        binding = getattr(owner(home, 'episode'), info['declaration_class'])(SimpleNamespace())
        registry = runtime.EpisodeBindingRegistry((binding,))
        source = SimpleNamespace(path=((info['role'], 'existing'),), episode_id='source', scope='scope', last_outcome=None, last_outcome_index=None,
            feedback=None, report_values={}, report_basis=[], interpret_schema={'type': 'object', 'properties': {}},
            request=SimpleNamespace(goal=SimpleNamespace(as_record=lambda: {}), report_contract=None))
        workflow = SimpleNamespace(episode_bindings=registry, run_id='run', store=SimpleNamespace(read_snapshot=lambda: nullcontext(), get=lambda reference: None),
            journal=SimpleNamespace(db=SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: None)), elapsed_view=lambda *args: {}),
            working_state=lambda source: {}, local_outcome_preview=lambda *args, **kwargs: None, source_credit_view=lambda source: {'credit': .25},
            receipt_projection=lambda source: False, source_credit_binding=lambda source: {}, pending_work=lambda source: {},
            delivery_status=lambda *args: [], controller_binding={}, catalog=lambda *args, **kwargs: {}, knowledge=SimpleNamespace(context=lambda: {}),
            job_episode_options=lambda source: None, extra_report_sources=lambda source: {})
        workflow.specialist = MethodType(runtime.Workflow.specialist, workflow)
        workflow.is_scientific_source = MethodType(runtime.Workflow.is_scientific_source, workflow)
        def annotation(*args, **kwargs):
            events.append('annotation_context'); raise BoundaryStop('original_annotation_context')
        workflow.annotation_context = annotation
        source.workflow = workflow
        old_kind = binding.credit_kind; old_path = registry.for_path
        def model_inputs(value, **kwargs):
            events.append('model_inputs')
            def path(value):
                events.append('registry_for_path'); return old_path(value)
            def kind(value):
                events.append(('credit_kind', value)); result = old_kind(value)
                events.append(('validated_role', result))
                if failure:
                    raise BoundaryStop('original_late_credit_kind_failure')
                return result
            registry.for_path = path; binding.credit_kind = kind
            return value
        view = SimpleNamespace(child_reports=(), controller_state={}, model_inputs=model_inputs)
        try:
            function(source, view)
        except BoundaryStop as error:
            result = (type(error), str(error))
        else:
            raise AssertionError('original_context_boundary_not_reached')
        return result, events
    expected = exercise(compile_original(node))
    assert exercise(current(home, 'decision_state', 'decision_state')) == expected
    assert expected[1][:4] == ['model_inputs', 'registry_for_path', ('credit_kind', info['role']), ('validated_role', 'scientific')]
    assert ('annotation_context' in expected[1]) is (not failure)
