"""Exact five original A106 role-read substitutions for body comparison only."""
import ast
from copy import deepcopy
import hashlib
from pathlib import Path


def expected_current_node(node, module, name):
    """Apply only five independently witnessed original role reads to the oracle."""
    node = deepcopy(node)
    original_path = Path(__file__).parents[2] / 'tests/fixtures/implicit_annotation_parent/runtime.py.source'
    raw = original_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'a98a5f609dce3f903817dc2d0a5ce468a85c40b0c1edd066645727e743fb1fd3'
    cls, = [n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == 'DecisionSource']
    originals = {n.name: n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    changed = 0
    if (module, name) == ('task_decision', 'call'):
        old, = [n for n in ast.walk(originals['call']) if isinstance(n, ast.If) and isinstance(n.test, ast.BoolOp)
                and ast.unparse(n.test) == "(row is None or row['response'] is None) and self.path[-1][0] == 'scientific_process'"]
        actual, = [n for n in node.body if isinstance(n, ast.If) and isinstance(n.test, ast.BoolOp)
                   and ast.unparse(n.test) == "(row is None or row['response'] is None) and True"]
        actual.test.values[1] = deepcopy(old.test.values[1]); changed = 1
    elif (module, name) == ('decision_inputs', 'decision_inputs'):
        for member in ('applies', 'capture'):
            old, = [n for n in ast.walk(originals['call']) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'binding.'+member]
            actual, = [n for n in ast.walk(node) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'binding.'+member]
            assert ast.unparse(actual.args[0]) == "'scientific_process'"
            assert ast.unparse(old.args[0]) == 'self.path[-1][0]'
            actual.args[0] = deepcopy(old.args[0]); changed += 1
    elif (module, name) == ('task', 'apply_response'):
        old, = [k for n in ast.walk(originals[name]) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'self.workflow.validate_report' for k in n.keywords if k.arg == 'grain']
        actual, = [k for n in ast.walk(node) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'self.workflow.validate_report' for k in n.keywords if k.arg == 'grain']
        assert ast.unparse(actual.value) == "'scientific_process'"
        actual.value = deepcopy(old.value); changed = 1
    elif (module, name) == ('task', 'execute'):
        old, = [n for n in ast.walk(originals[name]) if isinstance(n, ast.If) and ast.unparse(n.test) == "self.path[-1][0] == 'scientific_process'"]
        branch, = [n for n in node.body if isinstance(n, ast.If) and ast.unparse(n.test) == "old and old['result'] is not None"]
        assert ast.dump(branch.orelse[0], include_attributes=False) == ast.dump(old.body[0], include_attributes=False)
        branch.orelse[0] = deepcopy(old); changed = 1
    assert changed == {('task_decision','call'):1, ('decision_inputs','decision_inputs'):2,
                       ('task','apply_response'):1, ('task','execute'):1}.get((module,name),0)
    return node


