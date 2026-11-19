"""Which Store records a value names and which are visible under a scope: plain functions over the run's Store.

Which records an episode holds is not decided here: the runner keeps custody (``episode_runtime`` ``Custody``,
given to every tool as ``records``; see ``docs/axis_restructure_20261117/carry_over_guide/README.md``, section 3e). These functions answer Store
questions only: the record handles a value or typed form names (``references_in``), visibility of a reference
under a scope (``reference_in_scope``, ``read_record_in_scope``). No episode's role, axis, prompt or settings is
inside; what differs between episodes is a parameter.
"""
from __future__ import annotations

from collections.abc import Mapping
from gene_annotation_episode.domain import ContractError

# Record kinds the Store treats as a subject (Store.subjects / query_records(kind='subject')).
SUBJECT_KINDS = frozenset({'input', 'feature', 'product', 'read_subject'})


def _lookup(store, reference, cache):
    if reference not in cache:
        cache[reference] = store.get(reference) if store.holds(reference) else None
    return cache[reference]


def references_in(value, store, scope, *, reference_formats, forms=()):
    """Existing record handles that ``value`` and the typed ``forms`` name, visible under ``scope``.

    ``value`` is walked for declared reference positions: ``ref`` / ``*_ref`` scalars, ``*_refs`` /
    ``dependencies`` arrays, and ``id`` of a full record projection (a mapping carrying ``record_type``, which
    must match the stored record's type). Each ``(payload, schema)`` in ``forms`` contributes its scalar leaves
    whose JSON-schema node has a ``format`` in ``reference_formats`` (a direct child's form has parent-chosen
    field names, so its admitted schema supplies the type). Text that names no stored record, and collection
    members, are not handles. The handles found are kept in first-appearance order and limited to those
    ``Store.reference_subset`` admits under ``scope``.
    """
    formats = frozenset(reference_formats)
    found, records = {}, {}

    def add(reference, record_type=None):
        if not isinstance(reference, str) or reference in found:
            return
        record = _lookup(store, reference, records)
        if (not isinstance(record, Mapping) or record.get('id', reference) != reference
                or record.get('record_type') == 'collection_member'
                or (record_type is not None and record.get('record_type') != record_type)):
            return
        found[reference] = None

    def walk(item):
        if isinstance(item, Mapping):
            if isinstance(item.get('record_type'), str):
                add(item.get('id'), item['record_type'])
            for key, child in item.items():
                if key == 'ref' or key.endswith('_ref'):
                    add(child)
                elif key == 'dependencies' or key.endswith('_refs'):
                    if isinstance(child, (list, tuple)):
                        for reference in child:
                            add(reference)
                walk(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                walk(child)

    def form_references(item, schema):
        if not isinstance(schema, Mapping):
            raise ContractError('references_in_form_schema_must_be_a_mapping')
        if isinstance(item, Mapping):
            for key, child in item.items():
                node = schema.get('properties', {}).get(key)
                if node is not None:
                    form_references(child, node)
        elif isinstance(item, (list, tuple)):
            node = schema.get('items')
            if node is not None:
                for child in item:
                    form_references(child, node)
        elif schema.get('format') in formats:
            add(item)

    walk(value)
    for payload, schema in forms:
        form_references(payload, schema)
    admitted = set(store.reference_subset(list(found), scope))
    return [ref for ref in found if ref in admitted]


def reference_in_scope(store, reference, scope, namespace=None):
    """Whether ``reference`` is a stored record visible under ``scope`` of kind ``namespace``.

    ``namespace=None`` accepts any kind; ``'subject'`` accepts any subject kind; any other namespace must equal
    the stored ``record_type``.
    """
    if type(reference) is not str or not reference:
        return False
    if not store.reference_subset([reference], scope):
        return False
    kind = store.get(reference)['record_type']
    return namespace is None or namespace == kind or (namespace == 'subject' and kind in SUBJECT_KINDS)


def read_record_in_scope(store, reference, scope, namespace=None):
    """The stored record ``reference`` when :func:`reference_in_scope`; otherwise raise ``reference_not_in_scope``."""
    if not reference_in_scope(store, reference, scope, namespace):
        raise ContractError('reference_not_in_scope', detail={'reference': reference, 'namespace': namespace})
    return store.get(reference)


__all__ = ['SUBJECT_KINDS', 'read_record_in_scope', 'reference_in_scope', 'references_in']
