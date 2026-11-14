"""Exact beforeimage methods, with physical imports mapped after authentication.

Only module locations change in the retained original method. Its statements,
providers, private class selection, defaults and callbacks remain the original
oracle. Fixtures remain whole exact original bytes.
"""
import ast
from copy import deepcopy
import hashlib
from importlib import import_module
from importlib.util import resolve_name
import json
from pathlib import Path
from types import FunctionType

from .. import runtime
from .. import child_message_owners

PACKAGE = __package__.removesuffix('.tests')
FIXTURES = Path(__file__).parent / 'fixtures/hierarchy_exchange'
DATA = json.loads((FIXTURES / 'authority.json').read_text())


def mapped_module(name):
    old = PACKAGE + '.legacy_annotation'
    return PACKAGE + name[len(old):] if name == old or name.startswith(old + '.') else name


def original_tree(key):
    row = DATA['originals'][key]
    raw = (FIXTURES / row['fixture']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    return ast.parse(raw), row


def definition(key, class_name, function_name):
    tree, row = original_tree(key)
    body = tree.body
    if class_name is not None:
        cls, = [node for node in body if isinstance(node, ast.ClassDef) and node.name == class_name]
        body = cls.body
    node, = [node for node in body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name == function_name]
    qualified = function_name if class_name is None else class_name + '.' + function_name
    assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == row['definitions'][qualified]
    return deepcopy(node), row


def physical_imports(node, before_module):
    node = deepcopy(node)
    before_package = before_module.rpartition('.')[0]
    for item in ast.walk(node):
        if isinstance(item, ast.ImportFrom):
            absolute = resolve_name('.' * item.level + (item.module or ''), before_package) if item.level else item.module
            item.module, item.level = mapped_module(absolute), 0
        elif isinstance(item, ast.Import):
            for alias in item.names:
                mapped = mapped_module(alias.name)
                assert mapped == alias.name or alias.asname is not None
                alias.name = mapped
    return node


def compile_original(node, row, namespace):
    node = physical_imports(node, row['module'])
    scratch = dict(namespace)
    filename = str(FIXTURES / row['fixture'])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), filename, 'exec', dont_inherit=True), scratch)
    value = scratch[node.name]
    # Actual namespace objects remain live, including callback-time mutation.
    result = FunctionType(value.__code__, namespace, value.__name__, value.__defaults__, value.__closure__)
    result.__kwdefaults__ = value.__kwdefaults__
    return result


def original_selected():
    node, row = definition('runtime', 'Workflow', 'selected')
    return compile_original(node, row, vars(runtime))


def original_annotation_selector():
    node, row = definition('annotation_selector', None, 'exchange_for_child')
    return compile_original(node, row, vars(child_message_owners))


def original_resource_received(home):
    key = 'resource_received_' + ('nested' if home.startswith('scientific_process/') else 'root')
    node, row = definition(key, 'ResourceReceivedMessages', 'received_form_references')
    module = import_module(PACKAGE + '.' + home.replace('/', '.') + '.received_messages')
    return compile_original(node, row, vars(module))


def original_private_function(key, name):
    node, row = definition(key, None, name)
    module = import_module(mapped_module(row['module']))
    return compile_original(node, row, vars(module))
