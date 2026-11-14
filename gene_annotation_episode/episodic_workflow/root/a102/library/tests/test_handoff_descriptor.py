"""Actual four HPC descriptor maps depend on their private handoff policy bytes."""
import ast
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
import shutil
from types import FunctionType, SimpleNamespace

import pytest

PACKAGE = __package__.removesuffix('.library.tests')
POLICY = 'library/hpc_handoff_report_contract.py'
HOMES = ('hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
         'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')


@pytest.mark.parametrize('home', HOMES)
def test_actual_handoff_library_bytes_change_only_implementation(home, tmp_path):
    module = import_module(PACKAGE + '.' + home.replace('/', '.') + '.binding_record')
    function = module.HPCBindingRecord.as_record
    module_path = Path(module.__file__).resolve(strict=True)
    axis = Path(__file__).resolve().parents[2]
    assert module_path == axis / home / 'binding_record.py'
    tree = ast.parse(module_path.read_bytes())
    cls, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HPCBindingRecord']
    method, = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'as_record']
    operands = ast.literal_eval(method.body[3].value.args[0].generators[0].iter)
    assert operands.count(POLICY) == 1 and operands[-1] == POLICY
    # Keep the complete actual own-file set and every original literal operand.
    # All mutation is confined to this pytest-owned temporary source copy.
    members = {str(path.relative_to(axis)): path for path in sorted(module_path.parent.glob('*.py'))}
    members.update({name: axis / name for name in operands})
    copied_axis = tmp_path / 'axis'
    for name, original in members.items():
        destination = copied_axis / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
        assert destination.read_bytes() == original.read_bytes()
    namespace = dict(function.__globals__)
    namespace['__file__'] = str(copied_axis / home / 'binding_record.py')
    copied_method = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
    copied_method.__kwdefaults__ = function.__kwdefaults__
    configuration = SimpleNamespace(resources={'actual_port': {'kind': 'metadata_only'}},
        commissions={'selected': 'supplied'}, memory=None, private_yield_binding=False)
    before = copied_method(configuration)
    expected = {name: hashlib.sha256((copied_axis / name).read_bytes()).hexdigest() for name in members}
    assert before['implementation_sha256'] == module.hpc_queue.digest(expected)
    unchanged = {key: deepcopy(value) for key, value in before.items() if key != 'implementation_sha256'}
    original_policy = (copied_axis / POLICY).read_bytes()
    (copied_axis / POLICY).write_bytes(original_policy + b'\n# isolated descriptor source operand observation\n')
    after = copied_method(configuration)
    assert after['implementation_sha256'] != before['implementation_sha256']
    assert {key: value for key, value in after.items() if key != 'implementation_sha256'} == unchanged
    expected[POLICY] = hashlib.sha256((copied_axis / POLICY).read_bytes()).hexdigest()
    assert after['implementation_sha256'] == module.hpc_queue.digest(expected)
    (copied_axis / POLICY).write_bytes(original_policy)
    assert copied_method(configuration) == before
