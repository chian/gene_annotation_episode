"""Original provider lookup at actual private registered-task boundaries.

The real selected classes/functions run against explicit constructor, journal,
received-reference and pre-request ports. No model/native action or scientific
assessment is acquired. Original methods use the authentic live runtime dict.
"""
import ast
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import sys
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

PACKAGE = __package__.removesuffix('.library.tests')
AXIS = PACKAGE.rsplit('.', 1)[-1]
assert AXIS in ('a105', 'a108')
from ... import runtime as RUNTIME
DATA = json.loads((Path(__file__).parent / 'fixtures/registered_providers/consumers.json').read_text())
ORIGINAL = Path(__file__).parents[2] / 'tests/fixtures/implicit_annotation_parent/pre_split_runtime.py.source'
RAW = ORIGINAL.read_bytes()
assert hashlib.sha256(RAW).hexdigest() == DATA['original_runtime']['sha256']


def forbidden(*args, **kwargs):
    raise AssertionError('outside selected provider boundary')


def original_member(name):
    cls, = [node for node in ast.parse(RAW).body if isinstance(node, ast.ClassDef) and node.name == 'DecisionSource']
    value, = [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    return deepcopy(value)


def compile_original(node):
    namespace = dict(vars(RUNTIME))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(ORIGINAL), 'exec'), namespace)
    compiled = namespace[node.name]
    result = FunctionType(compiled.__code__, vars(RUNTIME), compiled.__name__,
                          compiled.__defaults__, compiled.__closure__)
    result.__kwdefaults__ = compiled.__kwdefaults__
    return result


def original(name):
    node = original_member(name)
    assert not node.decorator_list
    return compile_original(node)


def task_type(row):
    owner = import_module(row['module'])
    task = getattr(owner, row['task_class'])
    binding = getattr(import_module(row['episode_module']), row['episode_class'])
    assert binding.decision_source_type is task
    assert task.__module__ == row['module']
    return task


def observed(call, injected):
    try:
        return {'value': call(), 'error': None}
    except Exception as error:
        return {'value': None, 'error': [type(error).__name__, list(error.args), error is injected]}


def constructor_observation(row, before, fail, injected):
    task = task_type(row)  # finish importing the owner before rebinding
    events = []
    plain = RUNTIME._plain
    def late_plain(value):
        events.append(('plain', value))
        if fail:
            raise injected
        return plain(value)
    def identity(*args, **kwargs):
        events.append(('identity', args[1:], kwargs))
        RUNTIME._plain = late_plain
        return SimpleNamespace(episode_id='supplied-identity')
    workflow = SimpleNamespace(context=object(), grains={'selected': 'grain'})
    request = SimpleNamespace(message=RUNTIME.Record({'initial_report': {'qualification': 'unresolved'}}), report_contract=None)
    with patch.object(RUNTIME, 'Episode', SimpleNamespace(identity=identity)), patch.object(RUNTIME, '_plain', forbidden):
        def invoke():
            source = object.__new__(task)
            (original('__init__') if before else task.__init__)(source, workflow, (('selected', 'id'),), request, {'subject_refs': []})
            assert source.workflow is workflow and source.request is request
            return {key: value for key, value in vars(source).items() if key not in {'workflow', 'request'}}
        result = observed(invoke, injected)
    assert events and events[0][0] == 'identity'
    assert any(event[0] == 'plain' for event in events)
    return result, events


def reference_observation(row, before, fail, injected):
    task = task_type(row)
    events = []
    source = object.__new__(task)
    source.scope = {'subject_refs': []}
    source.workflow = SimpleNamespace(store=SimpleNamespace(get=forbidden, reference_subset=lambda refs, scope: refs))
    def references(value, lookup, *, reference_subset=None):
        events.append(('references', value, lookup is forbidden, reference_subset(['published:1'])))
        if fail:
            raise injected
        return ['published:1', 'published:1']
    exchanges = [{'lookup_result_recorded': True, 'lookup_result': {'records': [
        {'published_references': {'values': ['published:1']}}]}},
        {'lookup_result_recorded': False, 'lookup_result': {'records': [
            {'published_references': {'values': ['unreceived:must-not-enter']}}]}}]
    with patch.object(RUNTIME, '_references_in', references):
        function = original('interpretation_context') if before else task.interpretation_context
        result = observed(lambda: function(source, {'visible_record_refs': ['existing:1']}, exchanges), injected)
    assert len(events) == 1 and events[0][1] == {'record_refs': ['published:1']}
    return result, events


def finish_observation(row, before, mode, injected):
    task = task_type(row)
    events = []
    schema = {'type': 'object', 'properties': {
        'qualification': {'type': 'string', 'const': 'unresolved'},
        'credit': {'type': 'number', 'x-source': 'credit'}},
        'required': ['qualification', 'credit'], 'additionalProperties': False}
    contract = None if mode == 'untyped' else RUNTIME.TypedReportContract(
        'Retain the original finding', schema, lambda *args: True, lambda *args: None)
    source = object.__new__(task)
    source.episode_id = 'actual-private-source'
    source.request = SimpleNamespace(report_contract=contract)
    source.report_values = {'qualification': 'unresolved'}
    original_record, original_form = RUNTIME.Record, RUNTIME.form_with_facts
    class LateRecord(original_record):
        pass
    def record(value):
        events.append(('Record', value))
        return LateRecord(value)
    def late_form(*args):
        events.append('form_with_facts')
        return original_form(*args)
    def facts(*args, **kwargs):
        events.append('facts')
        RUNTIME.form_with_facts = late_form
        return {'credit': 0.25}
    def saved(*args):
        events.append(('row', args))
        return {'form': json.dumps({'qualification': 'unresolved', 'credit': 0.5})} if mode == 'saved' else None
    async def release(identity):
        events.append(('release', identity))
        RUNTIME.Record = record
    source.workflow = SimpleNamespace(
        source_credit_view=lambda value: {'credit': 0.25}, pending_handles=lambda value: [],
        episode_bindings=SimpleNamespace(current_report_facts=lambda context: {'own_fact': 'actual'}),
        binding_context=lambda value: SimpleNamespace(), release=release,
        journal=SimpleNamespace(row=saved, save=lambda *args: events.append(('save', args))), facts=facts)
    with patch.object(RUNTIME, 'Record', forbidden), patch.object(RUNTIME, 'form_with_facts', forbidden):
        def invoke():
            function = original('finish') if before else task.finish
            result = asyncio.run(function(source, {'ended_by': 'source_yielded'}))
            assert type(result) is LateRecord
            return result.as_record()
        result = observed(invoke, injected)
    assert result['error'] is None, result
    assert events[-2][0] == 'release' and events[-1][0] == 'Record'
    if mode == 'fresh':
        assert events[1:3] == ['facts', 'form_with_facts'] and events[3][0] == 'save'
    if mode == 'saved':
        assert all(event != 'facts' and (not isinstance(event, tuple) or event[0] != 'save') for event in events)
    return result, events


def check_tasks(boundary, option):
    for row in DATA['tasks']:
        injected = LookupError('original provider boundary failure')
        callback = {'constructor': constructor_observation, 'references': reference_observation,
                    'finish': finish_observation}[boundary]
        before = callback(row, True, option, injected)
        after = callback(row, False, option, injected)
        assert after == before, (row, before, after)
        if boundary != 'finish' and option:
            assert after[0]['error'] == ['LookupError', ['original provider boundary failure'], True]
        else:
            assert after[0]['error'] is None


def original_yield():
    node = original_member('exchange_decision')
    matches = []
    for candidate in ast.walk(node):
        if isinstance(candidate, ast.If) and len(candidate.orelse) >= 2:
            first, second = candidate.orelse[:2]
            if isinstance(first, ast.Assign) and ast.unparse(first.targets[0]) == 'parameters' and isinstance(second, ast.If):
                matches.append([first, second])
    body, = matches
    function = ast.parse('def original_yield(self, context, journal, index):\n    pass').body[0]
    function.body = deepcopy(body) + ast.parse('return table').body
    return compile_original(function)


def check_yield_rebinding(annotation_axes):
    for row in DATA['yield_consumers']:
        function = getattr(import_module(row['module']), 'decision_yield_table')
        def observe(before):
            events = []
            source = SimpleNamespace(workflow=SimpleNamespace(controller_binding=None, journal=object()), episode_id='yield-parent')
            context = {'current_credit': {'mode': 'annotation_axis_credit'} if annotation_axes else 0.25,
                       'controller': {'arms': [{'actual': 'saved'}]}}
            def table(journal, identity, *, before, parameters):
                events.append(('yield_table', journal is source.workflow.journal, identity, before, parameters))
                return {'version': 'supplied-original-yield', 'rows': []}
            def parameters(value):
                events.append('parameters')
                RUNTIME.yield_table = table
                return {'supplied': True}
            with patch.object(RUNTIME, '_category_yield_parameters', parameters), patch.object(RUNTIME, 'yield_table', forbidden):
                if before:
                    result = original_yield()(source, context, source.workflow.journal, 3)
                elif row['kind'] == 'scientific':
                    # Scientific callers compute the same original parameter
                    # expression before entering their standalone helper.
                    selected_parameters = RUNTIME._category_yield_parameters(source.workflow.controller_binding)
                    result = function(source, context, 3, selected_parameters)
                else:
                    result = function(source, context, source.workflow.journal, 3)
            return result, events
        assert observe(False) == observe(True), row


def check_request_rebinding():
    original_request = import_module(PACKAGE + '.tests.implicit_parent_checks').original_request
    for row in DATA['requests']:
        episode = getattr(import_module(row['episode_module']), row['episode_class'])
        parent = object.__new__(episode)
        function = parent.child_request_preparer(row['role'])
        assert function is import_module(row['module']).prepare_request
        injected = ValueError('late original JSON provider')
        def observe(before):
            events = []
            def parse(value):
                events.append(('parse', value))
                raise injected
            def expanded(*args):
                events.append('expanded')
                RUNTIME.parse_json_object = parse
                return {'type': 'object', 'properties': {}}, {'declared': 'original'}
            binding = SimpleNamespace(required_return_sources=lambda *args: ())
            workflow = SimpleNamespace(
                store=SimpleNamespace(validate_scope=lambda value, **kwargs: events.append('scope') or value),
                expanded_contract_form=expanded,
                episode_bindings=SimpleNamespace(for_child=lambda *args: events.append('binding') or binding),
                binding_context=lambda source: SimpleNamespace(),
                child_initial_report_input=lambda *args: events.append('initial') or '{}')
            source = SimpleNamespace(path=(('parent', 'one'),), scope={'subject_refs': []})
            selection = {'kind': 'episode_child', 'role': row['role'], 'scope': {'subject_refs': []}}
            with patch.object(RUNTIME, 'parse_json_object', forbidden):
                result = observed(lambda: (original_request() if before else function)(workflow, source, selection, 2), injected)
            assert result['error'] == ['ValueError', ['late original JSON provider'], True]
            return result, events
        assert observe(False) == observe(True), row


def check_wait_rebinding():
    owner = import_module(PACKAGE + '.scientific_process.waiting')
    method = original_member('execute')
    pieces = [node for node in ast.walk(method) if isinstance(node, ast.Try)
              and len(node.body) == 1 and isinstance(node.body[0], ast.Assign)
              and isinstance(node.body[0].value, ast.Await)
              and isinstance(node.body[0].value.value, ast.Call)
              and isinstance(node.body[0].value.value.func, ast.Attribute)
              and node.body[0].value.value.func.attr == 'perform_selected_wait']
    original_try, = pieces
    function = ast.parse('async def original_wait(self, selection, index):\n    pass').body[0]
    function.body = [deepcopy(original_try), *ast.parse('return result').body]
    baseline = compile_original(function)
    def observe(before):
        events = []
        class SuppliedWaitError(Exception):
            pass
        failure = SuppliedWaitError('actual wait port unavailable')
        async def wait(source, condition, index):
            events.append(('wait', condition, index))
            RUNTIME.EventTargetError = SuppliedWaitError
            RUNTIME._wait_target_feedback = lambda error, **kw: events.append(('feedback', error is failure, kw)) or {'status': 'failed'}
            raise failure
        source = SimpleNamespace(workflow=SimpleNamespace(perform_selected_wait=wait))
        with patch.object(RUNTIME, 'EventTargetError', type('BeforeError', (Exception,), {})), patch.object(RUNTIME, '_wait_target_feedback', forbidden):
            value = asyncio.run((baseline if before else owner.ScientificWaiting.perform_selected_wait)(source, {'condition': 'supplied'}, 4))
        return value, events
    assert observe(False) == observe(True)


def original_input_prefix():
    node = original_member('next')
    blocks = [item for item in ast.walk(node) if isinstance(item, ast.With)
              and ast.unparse(item.items[0].context_expr) == 'self.workflow.store.read_snapshot()']
    block, = blocks
    ends = [index for index, item in enumerate(block.body) if isinstance(item, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'basis' for target in item.targets)]
    end, = ends
    block.body = block.body[:end + 1]
    function = ast.parse('def original_input_prefix(self, view):\n    pass').body[0]
    function.body = [block]
    return compile_original(function)


def check_input_rebinding():
    for row in DATA['inputs']:
        function = import_module(row['module']).build_decision_inputs
        injected = LookupError('original received-reference boundary')
        def observe(before):
            events = []
            @contextmanager
            def snapshot():
                events.append('read-enter')
                try:
                    yield
                finally:
                    events.append('read-exit')
            def references(value, *args, **kwargs):
                events.append(('references', value, kwargs['forms']))
                raise injected
            def state(source):
                events.append('state')
                RUNTIME._references_in = references
                return {'actual': 'state'}
            source = SimpleNamespace(path=(('parent', 'one'), ('child', 'two')), episode_id='source', scope={},
                last_outcome=None, last_outcome_index=None, feedback=None,
                report_values={'qualification': 'unresolved'}, interpret_schema={'actual': 'interpretation'})
            source.workflow = SimpleNamespace(run_id='run',
                store=SimpleNamespace(read_snapshot=snapshot, get=forbidden),
                working_state=state, local_outcome_preview=lambda value, **kwargs: value,
                source_credit_view=lambda value: {'credit': 0.25},
                journal=SimpleNamespace(db=SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: None))))
            view = SimpleNamespace(child_reports=(), controller_state={'actual': 'controller'})
            with patch.object(RUNTIME, '_references_in', forbidden):
                if before:
                    call = lambda: original_input_prefix()(source, view)
                elif row['kind'] == 'scientific':
                    call = lambda: function(source, view)
                else:
                    call = lambda: function(source, view, None)
                result = observed(call, injected)
            assert result['error'] == ['LookupError', ['original received-reference boundary'], True]
            return result, events
        assert observe(False) == observe(True), row


def cold_entry(directory, family):
    row, = [row for row in DATA['cold_entries'] if row['family'] == family]
    directory.mkdir(parents=True)
    tree = Path(__file__).resolve().parents[6]
    assert (tree / 'gene_annotation_episode').is_dir()
    script = r'''
import importlib, json, pathlib, sys
paths, row, package, tree = json.loads(sys.argv[1]), json.loads(sys.argv[2]), sys.argv[3], pathlib.Path(sys.argv[4])
sys.path[:] = paths
assert package + '.runtime' not in sys.modules
owner = importlib.import_module(row['module'])
runtime = importlib.import_module(package + '.runtime')
assert owner._original_runtime is runtime
for name in row['definitions']:
    assert getattr(owner, name).__module__ == row['module']
origins = {}
for name, module in tuple(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.'):
        path = pathlib.Path(module.__file__).resolve(strict=True)
        assert path.is_relative_to(tree), (name, str(path))
        origins[name] = str(path.relative_to(tree))
print(json.dumps({'entry': row['module'], 'same_runtime_object': True, 'origins': origins}, sort_keys=True))
'''
    environment = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONOPTIMIZE'):
        environment.pop(key, None)
    for key in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
        path = directory / key.lower(); path.mkdir(); environment[key] = str(path)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    completed = subprocess.run([sys.executable, '-I', '-B', '-c', script, json.dumps(sys.path),
        json.dumps(row), PACKAGE, str(tree)], cwd=directory, env=environment,
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    value = json.loads(completed.stdout)
    assert value['entry'] == row['module'] and value['same_runtime_object'] is True
    assert row['module'] in value['origins']
    (directory / 'cold-imports.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
