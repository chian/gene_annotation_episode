"""The record references a typed JSON form carries, found through its schema.

``form_references(value, schema, formats=('reference',))`` walks ``value`` alongside its closed JSON Schema and
returns, in first-seen order and without repeats, each string at a schema node whose ``format`` is one of
``formats``. ``properties``, ``items``, ``prefixItems``, ``allOf`` and the ``anyOf``/``oneOf`` branches the value
satisfies are followed; local ``$ref`` pointers (``#/$defs/...``) resolve inside ``schema``. The caller then keeps
only what its store admits for its scope (``Store.reference_subset(refs, scope)``). This is what a parent
receives from a child's typed return, or a child from its parent's assignment.
"""
from __future__ import annotations

from collections.abc import Mapping

from jsonschema import Draft202012Validator


def _resolve(root, node):
    pointer = node.get('$ref')
    if pointer is None:
        return node
    if not isinstance(pointer, str) or not pointer.startswith('#/'):
        raise ValueError('form_references_supports_local_refs_only:' + repr(pointer))
    target = root
    for token in pointer[2:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if not isinstance(target, Mapping) or token not in target:
            raise ValueError('form_references_unresolved_ref:' + pointer)
        target = target[token]
    return target


def form_references(value, schema, formats=('reference',)):
    """Every string of ``value`` typed with one of ``formats`` by ``schema`` (see the module docstring)."""
    if not isinstance(schema, Mapping):
        raise TypeError('form_references_requires_a_schema_object')
    if not isinstance(formats, (tuple, list, set, frozenset)) or not formats:
        raise ValueError('form_references_requires_formats')
    wanted, found = set(formats), {}

    def satisfied(branch, item):
        return Draft202012Validator(dict(branch, **{'$defs': schema.get('$defs', {})})).is_valid(item)

    def visit(item, node):
        if not isinstance(node, Mapping) or item is None:
            return
        node = _resolve(schema, node)
        for branch in node.get('allOf', ()):
            visit(item, branch)
        for keyword in ('anyOf', 'oneOf'):
            for branch in node.get(keyword, ()):
                if satisfied(_resolve(schema, branch), item):
                    visit(item, branch)
        if isinstance(item, str):
            if node.get('format') in wanted:
                found.setdefault(item, None)
        elif isinstance(item, Mapping):
            properties = node.get('properties', {})
            for key, child in item.items():
                if key in properties:
                    visit(child, properties[key])
        elif isinstance(item, (list, tuple)):
            prefix = node.get('prefixItems', ())
            for index, child in enumerate(item):
                if index < len(prefix):
                    visit(child, prefix[index])
                elif isinstance(node.get('items'), Mapping):
                    visit(child, node['items'])
    visit(value, schema)
    return list(found)


__all__ = ['form_references']
