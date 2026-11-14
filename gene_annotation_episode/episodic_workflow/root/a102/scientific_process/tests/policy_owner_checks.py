"""Exact original policy fixtures and explicit observation normalization."""
from importlib import import_module
import hashlib
import json
from pathlib import Path
from types import ModuleType

AXIS = 'a102'
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.' + AXIS


def original(name):
    base = Path(__file__).with_name('fixtures') / 'scientific_owner_placement'
    provenance = json.loads((base / 'provenance.json').read_text())
    raw = (base / (name + '.py.source')).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == provenance[name]['sha256']
    module = ModuleType(PACKAGE + '.scientific_process.tests._original_' + name)
    module.__package__ = PACKAGE
    module.__file__ = str(base / (name + '.py.source'))
    exec(compile(raw, module.__file__, 'exec', dont_inherit=True), vars(module))
    return module


def owner(name):
    return import_module(PACKAGE + '.scientific_process.' + name)


def observed(callback):
    try:
        value = callback()
    except Exception as error:
        return ('error', type(error), str(error), getattr(error, 'diagnostic', None),
                None if error.__cause__ is None else (type(error.__cause__), str(error.__cause__)))
    if hasattr(value, 'as_record'):
        return ('value', type(value), value.as_record())
    return ('value', value)


def paired(monkeypatch, original_module, current_module, scenario):
    results = []
    for module in (original_module, current_module):
        with monkeypatch.context() as patch:
            results.append(scenario(module, patch))
    assert results[0] == results[1]
    return results[1]


def root_projector_modules():
    """Read both actual caller maps and import their actual defining module.

    This verifies the changed dynamic module operand; it does not claim an
    executed Root return admission, Store transaction or scientific result.
    """
    import ast
    root = import_module('gene_annotation_episode.episodic_workflow.root')
    modules = []
    for filename in ('axis_return_admission.py', 'returns.py'):
        tree = ast.parse((Path(root.__file__).parent / filename).read_text())
        choices = [node for node in ast.walk(tree) if isinstance(node, ast.Dict)
            and any(isinstance(key, ast.Constant) and key.value == AXIS.upper() for key in node.keys)]
        mappings = []
        for choice in choices:
            try: mapping = ast.literal_eval(choice)
            except (ValueError, TypeError): continue
            if isinstance(mapping.get(AXIS.upper()), str) and '.scientific_process.' in mapping[AXIS.upper()]:
                mappings.append(mapping)
        assert len(mappings) == 1
        modules.append(import_module(mappings[0][AXIS.upper()], root.__name__))
    return modules
