"""Exact six-site inverse for namespace checks of retained private bodies.

Consumers: provider18 assertions and its isolated cold probe. This normalizes
only the separate authenticated path restoration to compare with the retained
pre-restoration private fixture. Original path behavior has its own six tests.
"""
import ast
from copy import deepcopy


def before_path_restoration(module, name, node):
    node = deepcopy(node)
    shape = lambda value: ast.dump(value, include_attributes=False)
    path = ast.parse('self.path[-1][0]', mode='eval').body
    expected = ('task_decision', 'call'), ('decision_inputs', 'decision_inputs'), ('task', 'apply_response'), ('task', 'execute')
    if (module, name) not in expected:
        return node
    if (module, name) == ('task_decision', 'call'):
        test = ast.parse("(row is None or row['response'] is None) and self.path[-1][0] == 'scientific_process'", mode='eval').body
        guard, = [n for n in ast.walk(node) if isinstance(n, ast.If) and shape(n.test) == shape(test)]
        guard.test.values[1] = ast.Constant(value=True)
    elif module == 'decision_inputs':
        found = [n for n in ast.walk(node) if shape(n) == shape(path)]
        assert len(found) == 3
        applies, = [n for n in ast.walk(node) if isinstance(n, ast.Call) and shape(n.func) == shape(ast.parse('binding.applies', mode='eval').body)]
        capture, = [n for n in ast.walk(node) if isinstance(n, ast.Call) and shape(n.func) == shape(ast.parse('binding.capture', mode='eval').body)]
        planning, = [n for n in ast.walk(node) if isinstance(n, ast.Compare) and len(n.comparators) == 1 and shape(n.comparators[0]) == shape(ast.parse('binding.planning_roles', mode='eval').body)]
        assert applies.args[0] in found and capture.args[0] in found and planning.left in found
        applies.args[0] = ast.Constant(value='scientific_process')
        capture.args[0] = ast.Constant(value='scientific_process')
        planning.left = ast.Constant(value='scientific_process')
    elif name == 'apply_response':
        call, = [n for n in ast.walk(node) if isinstance(n, ast.Call) and shape(n.func) == shape(ast.parse('self.workflow.validate_report', mode='eval').body)]
        grain, = [k for k in call.keywords if k.arg == 'grain']
        assert shape(grain.value) == shape(path)
        grain.value = ast.Constant(value='scientific_process')
    else:
        test = ast.parse("self.path[-1][0] == 'scientific_process'", mode='eval').body
        guard, = [n for n in ast.walk(node) if isinstance(n, ast.If) and shape(n.test) == shape(test)]
        expected_call = ast.parse('self.workflow.scientific_process_binding.validate_execution_context(self.workflow.binding_context(self))').body[0]
        assert len(guard.body) == 1 and not guard.orelse and shape(guard.body[0]) == shape(expected_call)
        class Restore(ast.NodeTransformer):
            def visit_If(self, value):
                return guard.body if value is guard else self.generic_visit(value)
        node = Restore().visit(node)
    assert not any(shape(n) == shape(path) for n in ast.walk(node))
    return node
