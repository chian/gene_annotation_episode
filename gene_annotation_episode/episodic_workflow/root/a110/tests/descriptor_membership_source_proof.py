"""Finite AST proof for an explicitly recorded descriptor source-list successor.

No application imports, descriptor evaluation or filesystem lookup is performed.
Callers separately authenticate the exact source epochs and recorded path custody.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import hashlib


def dump(node):
    return ast.dump(node, include_attributes=False)


def literal_groups(method):
    result = []
    for statement in method.body:
        if not isinstance(statement, ast.Expr):
            continue
        call = statement.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name) and call.func.value.id == 'sources'
                and call.func.attr == 'update' and len(call.args) == 1 and not call.keywords):
            continue
        value = call.args[0]
        if not isinstance(value, ast.DictComp) or len(value.generators) != 1:
            continue
        generator = value.generators[0]
        if not isinstance(generator.target, ast.Name) or generator.ifs or generator.is_async:
            continue
        name = generator.target.id
        if not (isinstance(value.key, ast.Name) and value.key.id == name
                and isinstance(value.value, ast.BinOp) and isinstance(value.value.op, ast.Div)
                and isinstance(value.value.left, ast.Name) and value.value.left.id == 'axis'
                and isinstance(value.value.right, ast.Name) and value.value.right.id == name):
            continue
        if not isinstance(generator.iter, ast.Tuple):
            continue
        names = ast.literal_eval(generator.iter)
        assert all(isinstance(item, str) and item.endswith('.py') for item in names)
        assert len(set(names)) == len(names)
        result.append(generator.iter)
    return result


def restore_exact_membership(method, account, expected_before_sha256):
    """Restore only authenticated direct source-update tuple operands.

    Equality of the restored complete method AST retains every digest, payload,
    configuration, statement, expression, comparison and evaluation boundary.
    """
    assert isinstance(method, ast.FunctionDef) and method.name == 'as_record'
    assert dump(method) == account['method_AST_after']
    assert hashlib.sha256(account['method_AST_before'].encode()).hexdigest() == expected_before_sha256
    assert account['whole_byte_inverse'] is True
    assert account['original_digest_and_configuration_and_nonmembership_AST_preserved'] is True
    restored = deepcopy(method)
    groups = literal_groups(restored)
    used = set()
    for change in account['groups']:
        before, after = change['before'], change['after']
        assert before != after and len(set(before)) == len(before) and len(set(after)) == len(after)
        assert all(isinstance(name, str) and name.endswith('.py') for name in before + after)
        removed = {name for name in before if name not in after}
        added = {name for name in after if name not in before}
        assert [name for name in before if name not in removed] == [name for name in after if name not in added]
        matches = [(index, group) for index, group in enumerate(groups) if list(ast.literal_eval(group)) == after]
        assert len(matches) == 1 and matches[0][0] not in used
        index, group = matches[0]
        used.add(index)
        group.elts = [ast.Constant(value=name) for name in before]
    assert used, 'a descriptor successor must record an actual tuple change'
    assert dump(restored) == account['method_AST_before'], 'descriptor_nonmembership_AST_changed'
    return restored
