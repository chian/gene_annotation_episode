"""Finite original/current provider observations for actual private owners.

The retained oracles are exact own-axis method spans. Task classes and their
current mixins are real; workflow/journal/scientific/model ports are explicit.
These controls do not run a model, native operation, or complete workflow.
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

from ... import runtime as RUNTIME

PACKAGE = __package__.removesuffix('.library.tests')
AXIS = PACKAGE.rsplit('.', 1)[-1]
assert AXIS in ('a102', 'a103')
FIXTURES = Path(__file__).parent / 'fixtures/original_providers'
DATA = json.loads((FIXTURES / 'consumers.json').read_text())


def forbidden(*args, **kwargs):
    raise AssertionError('outside the selected provider boundary')


def namespace_for(kind):
    if kind == 'runtime':
        return RUNTIME
    if kind == 'providers':
        from ... import providers
        return providers
    assert kind == 'runtime_prompt'
    from ... import runtime_prompt
    return runtime_prompt


def oracle(row):
    saved = row['oracle']
    path = FIXTURES / saved['file']
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == saved['sha256']
    tree = ast.parse(raw)
    values = tree.body[0].body if isinstance(tree.body[0], ast.ClassDef) else tree.body
    node, = [value for value in values if isinstance(value, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert not node.decorator_list
    if saved.get('prefix') == 'build_request':
        # This is the original build's request-construction prefix, ending at
        # its own EpisodeRequest assignment, before task selection/activation.
        body = node.body[0].body if saved['request_assembler_branch'] else node.body
        stop, = [i for i, value in enumerate(body) if isinstance(value, ast.Assign)
                 and any(isinstance(name, ast.Name) and name.id == 'request' for name in value.targets)]
        node = deepcopy(node)
        node.body = deepcopy(body[:stop + 1]) + ast.parse('return path, goal, message, identity, request').body
    elif saved.get('prefix') == 'decision_state':
        blocks = [value for value in ast.walk(node) if isinstance(value, ast.With)
                  and ast.unparse(value.items[0].context_expr) == 'self.workflow.store.read_snapshot()']
        block, = blocks
        stop, = [i for i, value in enumerate(block.body) if isinstance(value, ast.Assign)
                 and any(isinstance(name, ast.Name) and name.id == 'basis' for name in value.targets)]
        body = deepcopy(block)
        body.body = body.body[:stop + 1]
        node = ast.parse('def original_decision_state(self, view):\n    pass').body[0]
        node.body = [body]
    namespace = namespace_for(row['namespace'])
    compiled_globals = dict(vars(namespace))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), 'exec'), compiled_globals)
    value = compiled_globals[node.name]
    result = FunctionType(value.__code__, vars(namespace), value.__name__, value.__defaults__, value.__closure__)
    result.__kwdefaults__ = value.__kwdefaults__
    return result


def current(row):
    value = import_module(row['module'])
    for name in row['definition'].split('.'):
        value = getattr(value, name)
    return value


def private_constructor_guard(row):
    saved = row['private_guard']
    path = FIXTURES / saved['file']
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == saved['sha256']
    node = ast.parse(raw).body[0].body[0]
    assert node.name == '__init__' and not node.decorator_list
    node.body = node.body[:saved['statements']]
    assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == saved['prefix_AST_sha256']
    # The prefix has its authentic relative imports and private type/path
    # checks. Its imported local names are unused by the generic tail; the
    # packager proves that separation rather than dropping those guards.
    namespace = import_module(row['module'])
    compiled_globals = dict(vars(namespace))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), 'exec'), compiled_globals)
    value = compiled_globals[node.name]
    return FunctionType(value.__code__, vars(namespace), value.__name__, value.__defaults__, value.__closure__)


def task(row):
    owner = import_module(row['task_module'])
    value = getattr(owner, row['task_class'])
    assert value.__module__ == row['task_module']
    assert getattr(value, row['definition'].split('.')[-1]) is current(row)
    return value


def observe(call, injected):
    try:
        return {'value': call(), 'error': None}
    except Exception as error:
        return {'value': None, 'error': [type(error).__name__, list(error.args), error is injected]}


def constructor(row, before, failure, injected, *, guard_case='admitted'):
    cls = task(row)  # Import before changing the authentic runtime namespace.
    events = []
    plain = RUNTIME._plain
    def late_plain(value):
        events.append(('plain', value))
        if failure:
            raise injected
        return plain(value)
    def identity(*args, **kwargs):
        events.append(('identity', args[1:], kwargs))
        RUNTIME._plain = late_plain
        return SimpleNamespace(episode_id='controlled-constructor-identity')
    path = (('selected', 'one'),)
    workflow = SimpleNamespace(context=object(), grains={'selected': 'actual-grain-port'})
    if 'private_guard' in row:
        guard = row['private_guard']
        role = guard['child_role']
        path = ((guard['parent_role'], 'parent'), (role, 'one'))
        owner = import_module(row['module'].rsplit('.', 1)[0] + '.episode')
        # Only exact class identity is consumed here. This explicit nominal
        # binding port is not a claim of configuration or native registry
        # construction; the real private task constructor and both actual
        # path validators remain under observation.
        binding = object.__new__(owner.HomologyEpisode)
        assert owner.HomologyEpisode.decision_source_type is cls
        if guard_case == 'path':
            path = ((role, 'one'),)
        elif guard_case == 'parent':
            path = (('unsupported', 'parent'), (role, 'one'))
        elif guard_case == 'binding':
            binding = SimpleNamespace()
        else:
            assert guard_case == 'admitted'
        def binding_for_path(value):
            events.append(('binding', value))
            return binding
        workflow.grains = {role: 'actual-grain-port'}
        workflow.job_episode_for_path = binding_for_path
    else:
        assert guard_case == 'admitted'
    request = SimpleNamespace(message=RUNTIME.Record({'initial_report': {}}), report_contract=None)
    with patch.object(RUNTIME, 'Episode', SimpleNamespace(identity=identity)), patch.object(RUNTIME, '_plain', forbidden):
        def call():
            source = object.__new__(cls)
            if before:
                if 'private_guard' in row:
                    private_constructor_guard(row)(source, workflow, path, request, {'subject_refs': []})
                oracle(row)(source, workflow, path, request, {'subject_refs': []})
            else:
                cls.__init__(source, workflow, path, request, {'subject_refs': []})
            assert source.workflow is workflow and source.request is request
            return {name: value for name, value in vars(source).items() if name not in {'workflow', 'request'}}
        value = observe(call, injected)
    if guard_case in ('path', 'parent'):
        assert events == []
    elif guard_case == 'binding':
        assert events == [('binding', path)]
    else:
        offset = 1 if 'private_guard' in row else 0
        if offset:
            assert events[0] == ('binding', path)
        assert events[offset][0] == 'identity' and events[offset + 1][0] == 'plain'
    return value, events


def references(row, before, failure, injected):
    source = object.__new__(task(row))
    source.scope = {'subject_refs': []}
    source.workflow = SimpleNamespace(store=SimpleNamespace(get=forbidden, reference_subset=lambda refs, scope: refs))
    events = []
    def provider(value, lookup, *, reference_subset=None):
        events.append((value, lookup is forbidden, reference_subset(['published:1'])))
        if failure:
            raise injected
        return ['published:1', 'published:1']
    exchanges = [{'lookup_result_recorded': True, 'lookup_result': {'records': [
        {'published_references': {'values': ['published:1']}}]}},
        {'lookup_result_recorded': False, 'lookup_result': {'records': [
            {'published_references': {'values': ['unreceived:excluded']}}]}}]
    with patch.object(RUNTIME, '_references_in', provider):
        result = observe(lambda: (oracle(row) if before else current(row))(
            source, {'visible_record_refs': ['existing:1']}, exchanges), injected)
    assert events == [({'record_refs': ['published:1']}, True, ['published:1'])]
    return result, events


def finish(row, before, mode, injected):
    source = object.__new__(task(row))
    events = []
    schema = {'type': 'object', 'properties': {'credit': {'type': 'number', 'x-source': 'credit'},
        'qualification': {'type': 'string', 'const': 'unresolved'}},
        'required': ['credit', 'qualification'], 'additionalProperties': False}
    contract = None if mode == 'untyped' else RUNTIME.TypedReportContract(
        'Retain original qualification', schema, lambda *args: True, lambda *args: None)
    source.episode_id = 'selected-private-source'
    source.request = SimpleNamespace(report_contract=contract)
    source.report_values = {'qualification': 'unresolved'}
    real_record, real_form = RUNTIME.Record, RUNTIME.form_with_facts
    class LateRecord(real_record):
        pass
    def record(value):
        events.append(('Record', value))
        return LateRecord(value)
    def form(*args):
        events.append('form_with_facts')
        return real_form(*args)
    def facts(*args, **kwargs):
        events.append('facts')
        RUNTIME.form_with_facts = form
        return {'credit': 0.25}
    def saved(*args):
        events.append(('row', args))
        return {'form': json.dumps({'qualification': 'unresolved', 'credit': 0.5})} if mode == 'saved' else None
    async def release(identity):
        events.append(('release', identity))
        RUNTIME.Record = record
    source.workflow = SimpleNamespace(source_credit_view=lambda value: {'credit': 0.25},
        pending_handles=lambda value: [], episode_bindings=SimpleNamespace(current_report_facts=lambda context: {'own_fact': 'actual'}),
        binding_context=lambda value: SimpleNamespace(), release=release,
        journal=SimpleNamespace(row=saved, save=lambda *args: events.append(('save', args))), facts=facts)
    with patch.object(RUNTIME, 'Record', forbidden), patch.object(RUNTIME, 'form_with_facts', forbidden):
        def call():
            result = asyncio.run((oracle(row) if before else current(row))(source, {'ended_by': 'source_yielded'}))
            assert type(result) is LateRecord
            return result.as_record()
        value = observe(call, injected)
    assert value['error'] is None
    assert events[-2][0] == 'release' and events[-1][0] == 'Record'
    if mode == 'fresh':
        assert events[1:3] == ['facts', 'form_with_facts'] and events[3][0] == 'save'
    if mode == 'saved':
        assert all(event != 'facts' and (not isinstance(event, tuple) or event[0] != 'save') for event in events)
    return value, events


def response(row, before, failure, injected):
    source = object.__new__(task(row))
    source.workflow = object()
    events = []
    class Validator:
        def __init__(self, schema):
            events.append(('validator', schema))
        def validate(self, value):
            events.append(('validate', value))
            if failure:
                raise injected
    def lookup(workflow, selected):
        assert workflow is source.workflow and selected is source
        events.append('lookup')
        # The callee was already read before argument evaluation. Preserve
        # that original timing, not a freshly classified call after this port.
        RUNTIME.Draft202012Validator = forbidden
        return {'supplied': 'lookup-contract'}
    body = {'response_type': 'request_context', 'lookup': {'original': 'request'}}
    with patch.object(RUNTIME, 'Draft202012Validator', Validator), patch.object(RUNTIME, 'composition_lookup_schema', lookup):
        value = observe(lambda: (oracle(row) if before else current(row))(source, {'response': body}), injected)
    assert events == ['lookup', ('validator', {'supplied': 'lookup-contract'}), ('validate', {'original': 'request'})]
    return value, events


def check_task_boundary(boundary, option):
    callback = {'constructor': constructor, 'references': references, 'finish': finish, 'response': response}[boundary]
    assert DATA[boundary]
    for row in DATA[boundary]:
        injected = LookupError('original provider boundary')
        previous = callback(row, True, option, injected)
        selected = callback(row, False, option, injected)
        assert selected == previous, (row['module'], row['definition'], previous, selected)
        if boundary != 'finish' and option:
            assert selected[0]['error'] == ['LookupError', ['original provider boundary'], True]
        else:
            assert selected[0]['error'] is None
        if boundary == 'constructor' and 'private_guard' in row:
            expected = {'path': ['ValueError', ['private_homology_task_path_required'], False],
                'parent': ['ValueError', ['private_legacy_' + row['private_guard']['parent_role'] + '_path_required'], False],
                'binding': ['TypeError', ['private_homology_task_binding_required'], False]}
            for guard_case, error in expected.items():
                previous = constructor(row, True, option, injected, guard_case=guard_case)
                selected = constructor(row, False, option, injected, guard_case=guard_case)
                assert selected == previous, (row['module'], guard_case, previous, selected)
                assert selected[0]['error'] == error


def check_prompt():
    for row in DATA['prompt']:
        selected = current(row)
        namespace = namespace_for('runtime_prompt')
        def run(before):
            events = []
            def specialist(source):
                events.append('specialist')
                namespace.REASONING_COMMIT_REQUIREMENT = 'late own-axis reason policy'
                return None
            workflow = SimpleNamespace(is_job_source=lambda source: False, specialist=specialist,
                permits_common_action=lambda source, role: events.append(('permits', role)) or role == 'reason',
                native_event_information=None, decision_protocol=None)
            source = SimpleNamespace(workflow=workflow, path=(('scientific_process', 'selected'),))
            with patch.object(namespace, 'INSTRUCTIONS', 'initial own-axis instructions'), patch.object(namespace, 'REASONING_COMMIT_REQUIREMENT', 'early reason policy'):
                value = (oracle(row) if before else selected)(source, {})
            assert 'late own-axis reason policy' in value and 'early reason policy' not in value
            return value, events
        assert run(False) == run(True), row


def check_presentation(failure):
    for row in DATA['presentation']:
        selected = current(row)
        namespace = namespace_for('providers')
        injected = LookupError('original presentation JSON port')
        def run(before):
            events = []
            def dumps(value, **kwargs):
                events.append(('json', dict(value), kwargs))
                if failure:
                    raise injected
                return json.dumps(dict(value), **kwargs)
            class Context(dict):
                def get(self, key, *args):
                    if key == 'version':
                        events.append('version')
                        namespace.json = SimpleNamespace(dumps=dumps)
                    return super().get(key, *args)
            connection = SimpleNamespace(scientific_prompt_states={})
            with patch.object(namespace, 'json', SimpleNamespace(dumps=forbidden)):
                value = observe(lambda: (oracle(row) if before else selected)(
                    connection, 'source', 'unclassified-provider-input', 'original instructions', Context({'untouched': 1})), injected)
            assert events[0] == 'version' and events[-1][0] == 'json'
            return value, events
        assert run(False) == run(True), row


def check_receipt():
    for row in DATA['receipt']:
        selected = current(row)
        injected = LookupError('received references provider')
        def run(before):
            events = []
            def references(*args, **kwargs):
                events.append(('references', kwargs['forms']))
                raise injected
            def progress(*args):
                events.append(('progress', args))
                RUNTIME._references_in = references
            source = SimpleNamespace(episode_id='actual-parent-port', scope={})
            workflow = SimpleNamespace(receipts=object(), is_job_source=lambda source: False,
                specialist=lambda source: None, progress_provider=SimpleNamespace(receive_form=progress),
                run_id='run', store=SimpleNamespace(get=forbidden))
            with patch.object(RUNTIME, '_references_in', forbidden):
                value = observe(lambda: (oracle(row) if before else selected)(
                    workflow, source, {'credit': 0.25}, {'type': 'object'}, 3, redelivery=True), injected)
            assert value['error'] == ['LookupError', ['received references provider'], True]
            assert events[0][0] == 'progress' and events[1][0] == 'references'
            return value, events
        assert run(False) == run(True), row


def check_inputs():
    for row in DATA['inputs']:
        selected = current(row)
        injected = LookupError('original received-reference boundary')
        def run(before):
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
                return {'actual': 'working-state-port'}
            source = SimpleNamespace(path=(('parent', 'one'), ('child', 'two')), episode_id='source', scope={},
                last_outcome=None, last_outcome_index=None, feedback=None,
                report_values={}, interpret_schema={'type': 'object'})
            source.workflow = SimpleNamespace(run_id='run', store=SimpleNamespace(read_snapshot=snapshot, get=forbidden),
                working_state=state, local_outcome_preview=lambda value, **kwargs: value,
                source_credit_view=lambda value: {'credit': 0.25},
                journal=SimpleNamespace(db=SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: None))))
            view = SimpleNamespace(child_reports=(), controller_state={'actual': 'controller'})
            with patch.object(RUNTIME, '_references_in', forbidden):
                value = observe(lambda: (oracle(row) if before else selected)(source, view), injected)
            assert value['error'] == ['LookupError', ['original received-reference boundary'], True]
            assert events[0:2] == ['read-enter', 'state'] and events[-1] == 'read-exit'
            return value, events
        assert run(False) == run(True), row


def check_wait():
    row, = DATA['wait']
    cls = task(row)
    def run(before):
        events = []
        class ReturnedWaitError(Exception):
            pass
        failure = ReturnedWaitError('actual wait port unavailable')
        source = object.__new__(cls)
        source.path = (('scientific_process', 'selected'),)
        source.episode_id = 'actual-private-source'
        source._inprocess_replay_ready = True
        @contextmanager
        def measure(*args):
            events.append(('measure-enter', args))
            try:
                yield
            finally:
                events.append('measure-exit')
        def feedback(error, **kwargs):
            events.append(('feedback', error is failure, kwargs))
            return {'status': 'failed', 'category': 'controlled-wait-port'}
        async def wait(selected, condition, index):
            assert selected is source
            events.append(('wait', condition, index))
            RUNTIME.EventTargetError = ReturnedWaitError
            RUNTIME._wait_target_feedback = feedback
            raise failure
        journal = SimpleNamespace(row=lambda *args: None, measure=measure,
            save=lambda *args: events.append(('save', args)))
        source.workflow = SimpleNamespace(journal=journal, run_id='run',
            scientific_process_binding=SimpleNamespace(validate_execution_context=lambda context: events.append('scientific-admission')),
            binding_context=lambda selected: SimpleNamespace(), perform_selected_wait=wait,
            execution_binding=None, inprocess_replay=None, wait_inputs_version=None, completed_action_inputs_version=None,
            receive_native_outcome=lambda selected, result, index: events.append(('native-outcome', result, index)),
            receive_outcome=lambda selected, choice, result, index: events.append(('outcome', choice, result, index)),
            last_observed_credit=lambda selected: 0.25,
            controller_value=lambda selected, index, credit: events.append(('controller', index, credit)) or credit)
        with patch.object(RUNTIME, 'EventTargetError', type('InitialWaitError', (Exception,), {})), patch.object(RUNTIME, '_wait_target_feedback', forbidden):
            value = observe(lambda: asyncio.run((oracle(row) if before else current(row))(
                source, {'kind': 'wait', 'condition': 'supplied-original-condition'}, 4)), failure)
        assert ('feedback', True, {'status': 'failed'}) in events
        assert source.last_outcome['status'] == 'failed' and source.last_outcome_index == 4
        assert any(isinstance(event, tuple) and event[0] == 'native-outcome' for event in events)
        return value, events, source.last_outcome
    assert run(False) == run(True)


def check_legacy_request(role):
    assert AXIS == 'a103'
    row = DATA['legacy_requests'][role]
    selected = current(row)
    def run(before):
        events = []
        real_record, real_request, real_goal = RUNTIME.Record, RUNTIME.EpisodeRequest, RUNTIME.EpisodeGoal
        contract = RUNTIME.TypedReportContract('Original child purpose',
            {'type': 'object', 'properties': {'credit': {'type': 'number', 'x-source': 'credit'}},
             'required': ['credit'], 'additionalProperties': False}, lambda *args: True, lambda *args: None)
        parent = None if role == 'annotation' else RUNTIME.EpisodeGoal.root(objective='original parent', result_contract={'role': 'annotation'})
        parent_path = () if parent is None else (('annotation', 'root'),)
        def root_goal(**kwargs):
            events.append('root-goal')
            return real_goal.root(**kwargs)
        def child_goal(parent, **kwargs):
            events.append('child-goal')
            return real_goal.child(parent, **kwargs)
        def request(*args):
            events.append('EpisodeRequest')
            return real_request(*args)
        def record(value):
            events.append(('Record', value))
            RUNTIME.EpisodeRequest = forbidden
            return real_record(value)
        def identity(*args, **kwargs):
            events.append(('identity', args[1:], kwargs))
            RUNTIME.Record = record
            RUNTIME.EpisodeRequest = request
            return SimpleNamespace(episode_id='controlled-original-identity')
        workflow = SimpleNamespace(inprocess_completion_order=None, context=object(), grains={role: 'original-grain'},
            scientific_process_binding=None, receipts=None)
        with patch.object(RUNTIME, 'EpisodeGoal', SimpleNamespace(root=root_goal, child=child_goal)), patch.object(RUNTIME, 'Episode', SimpleNamespace(identity=identity)), patch.object(RUNTIME, 'Record', forbidden), patch.object(RUNTIME, 'EpisodeRequest', forbidden):
            path, goal, message, value, result = (oracle(row) if before else selected)(workflow, role, 'one',
                'original objective', {'subject_refs': []}, parent=parent, parent_path=parent_path,
                contract=None if parent is None else contract, initial={})
        assert events[-1] == 'EpisodeRequest' and events[-2][0] == 'Record'
        assert events[0] == ('root-goal' if parent is None else 'child-goal')
        return path, goal.as_record(), message, value.episode_id, result.as_record(), events
    assert run(False) == run(True)


def cold_entry(directory, family):
    row = DATA['cold_entries'][family]
    directory.mkdir(parents=True)
    tree = Path(__file__).resolve().parents[6]
    assert (tree / 'gene_annotation_episode').is_dir()
    script = r'''
import importlib, json, pathlib, sys
paths, row, package, tree = json.loads(sys.argv[1]), json.loads(sys.argv[2]), sys.argv[3], pathlib.Path(sys.argv[4])
sys.path[:] = paths
assert package + '.' + row['namespace'] not in sys.modules
owner = importlib.import_module(row['module'])
namespace = importlib.import_module(package + '.' + row['namespace'])
assert getattr(owner, '_live_original_' + row['namespace']) is namespace
value = owner
for name in row['definition'].split('.'):
    value = getattr(value, name)
assert value.__module__ == row['module']
origins = {}
for name, module in tuple(sys.modules.items()):
    if (name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.')
            or name == 'method_loop' or name.startswith('method_loop.')):
        path = pathlib.Path(module.__file__).resolve(strict=True)
        assert path.is_relative_to(tree), (name, str(path))
        origins[name] = str(path.relative_to(tree))
print(json.dumps({'entry': row['module'], 'same_namespace_object': True, 'origins': origins}, sort_keys=True))
'''
    environment = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONOPTIMIZE'):
        environment.pop(key, None)
    for key in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
        path = directory / key.lower(); path.mkdir(); environment[key] = str(path)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    completed = subprocess.run([sys.executable, '-I', '-B', '-c', script, json.dumps(sys.path), json.dumps(row), PACKAGE, str(tree)],
        cwd=directory, env=environment, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    value = json.loads(completed.stdout)
    assert value['entry'] == row['module'] and value['same_namespace_object'] is True
    assert row['module'] in value['origins']
    (directory / 'cold-imports.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
