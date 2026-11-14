"""A103 original/current late handoff policy with explicit boundary ports.

The fixture is A103's exact pre-split runtime source. Real current private task
classes supply nominal identity; their uninitialized instances and the explicit
workflow ports stop at the original initial-report callback. This exercises no
scientific/native dispatch, complete constructor or restored workflow.
"""
import ast
import builtins
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

from ... import runtime as RUNTIME
from .. import hpc_handoff_report_contract as POLICY
from ...tests.hierarchy_oracles import FIXTURES, DATA, compile_original

PACKAGE = __package__.removesuffix('.library.tests')
ORIGINAL = (FIXTURES / 'runtime_before.py.source').read_bytes()
assert hashlib.sha256(ORIGINAL).hexdigest() == DATA['runtime_sha256']
TREE = ast.parse(ORIGINAL)
WORKFLOW, = [node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == 'Workflow']
SELECTED, = [node for node in WORKFLOW.body if isinstance(node, ast.FunctionDef) and node.name == 'selected']
assert hashlib.sha256(ast.dump(SELECTED, include_attributes=False).encode()).hexdigest() == DATA['selected_AST']
GUARDS = []
for parent in ast.walk(SELECTED):
    for _, values in ast.iter_fields(parent):
        if isinstance(values, list):
            for index, node in enumerate(values[:-1]):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'hpc_launch':
                    GUARDS.append(values[index:index + 2])
GUARD, = GUARDS
assert hashlib.sha256(ast.dump(ast.Module(body=GUARD, type_ignores=[]), include_attributes=False).encode()).hexdigest() == DATA['guard_AST']


def original(node):
    return compile_original(node, DATA['originals']['runtime'], vars(RUNTIME))


ORIGINAL_SELECTED = original(SELECTED)
_guard = ast.parse('def original_guard(source, role, schema):\n    pass').body[0]
_guard.body = deepcopy(GUARD) + [ast.Return(value=ast.Name(id='hpc_launch', ctx=ast.Load()))]
ORIGINAL_GUARD = original(_guard)


@contextmanager
def restored_names():
    absent = object()
    names = ('any', 'ContractError', '__builtins__')
    saved = {key: vars(RUNTIME).get(key, absent) for key in names}
    cached = RUNTIME.Workflow.selected.__builtins__
    builtin_saved = {key: cached.get(key, absent) for key in ('any', 'ContractError')}
    try:
        yield cached
    finally:
        for key, value in saved.items():
            if value is absent:
                vars(RUNTIME).pop(key, None)
            else:
                vars(RUNTIME)[key] = value
        for key, value in builtin_saved.items():
            if value is absent:
                cached.pop(key, None)
            else:
                cached[key] = value


class LateContractError(Exception):
    pass


class ReachedInitial(Exception):
    pass


def outcome(call):
    try:
        return ('returned', call())
    except Exception as error:
        return ('raised', type(error), str(error), getattr(error, 'name', None))


def consumer(row):
    cls = getattr(import_module(row['module']), row['class'])
    value = object.__new__(cls)
    value.path = tuple(tuple(part) for part in row['path'])
    value.episode_id = 'controlled-parent'
    value.scope = 'controlled-scope'
    return value


def selected_observation(row, before, mode, *, custom=False):
    events = []
    source = consumer(row)
    if custom:
        source = SimpleNamespace(**vars(source))
    selection = {'kind': 'episode_child', 'role': row['role'], 'scope': source.scope, 'assignment': {}}
    schema = {'properties': {'handoff': {'x-source': 'execution_handoff_refs'}}} if mode == 'valid' else {'properties': {}}
    def journal(*args):
        events.append('journal')
        return None
    def expanded(*args):
        events.append('expanded')
        if mode == 'late_to_hpc':
            source.path = (('hpc', 'late'), ('launch', 'late')) if row['role'] == 'launch_hpc' else (('hpc', 'late'),)
        elif mode == 'late_away':
            source.path = (('annotation', 'late'),)
        vars(RUNTIME)['ContractError'] = LateContractError
        return schema, {'supplied': True}
    def required(*args):
        events.append('required')
        return ('required_control',) if mode == 'required_first' else ()
    def initial(*args):
        events.append('initial')
        raise ReachedInitial('original next callback reached')
    host = SimpleNamespace(annotation_child_roles=None, execution_binding=None,
        scientific_process_binding=None, inprocess_replay=None,
        journal=SimpleNamespace(row=journal), store=SimpleNamespace(validate_scope=lambda *args, **kwargs: source.scope),
        validate_child_choice=lambda *args, **kwargs: events.append('validate_choice'),
        permits_common_action=lambda *args: True, _closed_child_commission=lambda *args: None,
        expanded_contract_form=expanded, binding_context=lambda *args: 'controlled-context',
        episode_bindings=SimpleNamespace(for_child=lambda *args: SimpleNamespace(required_return_sources=required)),
        child_initial_report_input=initial)
    if mode == 'late_to_hpc':
        source.path = (('annotation', 'before'),)
    call = ORIGINAL_SELECTED if before else RUNTIME.Workflow.selected
    with restored_names():
        result = outcome(lambda: call(host, source, deepcopy(selection), 7))
    return result, events, source.path


def check_selected(mode):
    for row in DATA['consumers']:
        before = selected_observation(row, True, mode)
        after = selected_observation(row, False, mode)
        assert after == before
        result, events, _ = after
        assert events.index('expanded') < events.index('required')
        if mode in {'valid', 'late_away'}:
            assert result[1] is ReachedInitial and events[-1] == 'initial'
        else:
            assert result[1] is LateContractError and 'initial' not in events
            assert result[2] == ('child_return_requires_required_control' if mode == 'required_first' else 'hpc_launch_requires_original_handoff_fact_in_return_form')


def check_getter_identity_and_cached_builtins():
    for getter in (POLICY._get_any, POLICY._get_ContractError):
        assert getter.__globals__ is RUNTIME.Workflow.selected.__globals__
        assert getter.__builtins__ is RUNTIME.Workflow.selected.__builtins__
        assert getter.__builtins__ is ORIGINAL_GUARD.__builtins__ is ORIGINAL_SELECTED.__builtins__
    source = SimpleNamespace(path=(('hpc', 'one'),))
    with restored_names() as cached:
        vars(RUNTIME).pop('any', None)
        vars(RUNTIME)['__builtins__'] = {'any': lambda _: False, 'ContractError': RuntimeError}
        schema = {'properties': {'handoff': {'x-source': 'execution_handoff_refs'}}}
        assert ORIGINAL_GUARD(source, 'launch', schema) is True
        assert POLICY.validate_hpc_launch_report_contract(source, 'launch', schema) is True
        assert POLICY._get_any() is cached['any']


def ordered_name_observation(before):
    events = []
    native_any = builtins.any
    class Source:
        @property
        def path(self):
            events.append('path')
            vars(RUNTIME)['any'] = second_any
            return (('hpc', 'one'), ('launch', 'two'))
    class Schema(dict):
        def get(self, key, default=None):
            events.append('schema')
            vars(RUNTIME)['any'] = forbidden_any
            vars(RUNTIME)['ContractError'] = ValueError
            return super().get(key, default)
    def forbidden_any(values):
        raise AssertionError('callee was looked up after generator first iterable')
    def first_any(values):
        events.append('first_any')
        return native_any(values)
    def second_any(values):
        events.append('second_any')
        vars(RUNTIME)['ContractError'] = LateContractError
        return native_any(values)
    with restored_names():
        vars(RUNTIME)['any'] = first_any
        result = outcome(lambda: (ORIGINAL_GUARD if before else POLICY.validate_hpc_launch_report_contract)(Source(), 'launch_hpc', Schema(properties={})))
    return result, events


def check_ordered_name_loads():
    before, after = ordered_name_observation(True), ordered_name_observation(False)
    assert after == before
    assert after[0][1] is LateContractError
    assert after[1] == ['path', 'first_any', 'schema', 'second_any']


def missing_name_observation(before, name, fallback):
    events = []
    class Source:
        @property
        def path(self):
            events.append('path')
            return (('hpc', 'one'),)
    with restored_names() as cached:
        vars(RUNTIME).pop(name, None)
        if fallback:
            if name == 'ContractError':
                cached[name] = LateContractError
        else:
            cached.pop(name, None)
        result = outcome(lambda: (ORIGINAL_GUARD if before else POLICY.validate_hpc_launch_report_contract)(Source(), 'launch_hpc' if name == 'any' else 'launch', {'properties': {}}))
    return result, events


def check_missing_and_builtin_names():
    for name in ('any', 'ContractError'):
        for fallback in (False, True):
            before = missing_name_observation(True, name, fallback)
            after = missing_name_observation(False, name, fallback)
            assert after == before
            if not fallback:
                assert after[0][1] is NameError and after[0][3] == name
                if name == 'any':
                    assert after[1] == []  # callee lookup precedes first generator iterable
            elif name == 'ContractError':
                assert after[0][1] is LateContractError


def check_nominal_and_custom_fallback():
    for row in DATA['consumers']:
        value = consumer(row)
        assert POLICY.selected_hpc_launch_report_validator(value) is POLICY.validate_hpc_launch_report_contract
        before = selected_observation(row, True, 'missing', custom=True)
        assert selected_observation(row, False, 'missing', custom=True) == before
        cls = type(value)
        previous = cls.__dict__['_validate_hpc_launch_report_contract']
        class Descriptor:
            def __get__(self, *_):
                raise AssertionError('selector invoked replacement descriptor')
        try:
            setattr(cls, '_validate_hpc_launch_report_contract', Descriptor())
            assert POLICY.selected_hpc_launch_report_validator(value) is None
            assert selected_observation(row, False, 'missing') == selected_observation(row, True, 'missing')
        finally:
            setattr(cls, '_validate_hpc_launch_report_contract', previous)
    class Meta(type):
        def __getattribute__(self, name):
            raise AssertionError('selector invoked custom metaclass')
    class Custom(metaclass=Meta):
        pass
    assert POLICY.selected_hpc_launch_report_validator(object.__new__(Custom)) is None
    class ModuleMap(dict):
        def get(self, *_):
            raise AssertionError('selector invoked custom module-map lookup')
    modules = sys.modules
    try:
        sys.modules = ModuleMap()
        assert POLICY.selected_hpc_launch_report_validator(value) is None
    finally:
        sys.modules = modules


def check_custom_role_short_circuit():
    def observe(before):
        events = []
        class Role:
            def __eq__(self, other):
                events.append(('role', other))
                return False
        class Source:
            @property
            def path(self):
                raise AssertionError('false role must not read path')
        result = (ORIGINAL_GUARD if before else POLICY.validate_hpc_launch_report_contract)(Source(), Role(), {})
        return result, events
    assert observe(False) == observe(True) == (False, [('role', 'launch'), ('role', 'launch_hpc')])


def cold_entries(directory):
    directory.mkdir(parents=True)
    tree = Path(__file__).resolve().parents[6]
    assert (tree / 'gene_annotation_episode').is_dir()
    script = r'''
import importlib, json, pathlib, sys
paths, entry, package, tree = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3], pathlib.Path(sys.argv[4])
sys.path[:] = paths
assert package + '.runtime' not in sys.modules
importlib.import_module(entry)
runtime = importlib.import_module(package + '.runtime')
policy = importlib.import_module(package + '.library.hpc_handoff_report_contract')
assert policy._get_any.__globals__ is runtime.Workflow.selected.__globals__
assert policy._get_any.__builtins__ is runtime.Workflow.selected.__builtins__
assert policy._get_ContractError.__globals__ is runtime.Workflow.selected.__globals__
assert policy._get_ContractError.__builtins__ is runtime.Workflow.selected.__builtins__
origins = {}
for name, module in tuple(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.') or name == 'method_loop' or name.startswith('method_loop.'):
        path = pathlib.Path(module.__file__).resolve(strict=True)
        assert path.is_relative_to(tree), (name, str(path))
        origins[name] = str(path.relative_to(tree))
print(json.dumps({'entry': entry, 'same_namespace_object': True, 'origins': origins}, sort_keys=True))
'''
    entries = (PACKAGE + '.library.hpc_handoff_report_contract', DATA['consumers'][0]['module'])
    for index, entry in enumerate(entries):
        child = directory / str(index); child.mkdir()
        environment = dict(os.environ)
        for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONOPTIMIZE'):
            environment.pop(key, None)
        for key in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
            path = child / key.lower(); path.mkdir(); environment[key] = str(path)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        completed = subprocess.run([sys.executable, '-I', '-B', '-c', script, json.dumps(sys.path), entry, PACKAGE, str(tree)],
            cwd=child, env=environment, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        value = json.loads(completed.stdout)
        assert value['entry'] == entry and value['same_namespace_object'] is True and entry in value['origins']
        (child / 'cold-imports.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
