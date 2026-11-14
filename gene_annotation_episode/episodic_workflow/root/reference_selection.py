"""Private root annotation reference selection."""
from __future__ import annotations
from collections.abc import Mapping
from .communication import REFERENCE_FORMATS

def _references_in(value, record_lookup, *, forms=(), reference_subset=None):
    """Index visible semantic handles without loading source/artifact contents.

    Working state and host outcomes use declared reference positions; full
    record projections also carry id/record_type. Native payloads' untyped id
    fields and ordinary text are not semantic declarations. Direct-child form
    fields have parent-chosen names, so their admitted schema supplies the type.
    Indexed record lookups establish identity; archived contexts and referenced
    source/artifact contents are not loaded. Only existing handles enter it.
    """
    found, seen, records = ([], set(), {})

    def add(reference, record_type=None):
        if not isinstance(reference, str):
            return
        if reference not in records:
            try:
                records[reference] = record_lookup(reference)
            except (KeyError, ValueError):
                records[reference] = None
        record = records[reference]
        if not isinstance(record, Mapping) or record.get('id') != reference or record.get('record_type') == 'collection_member' or (record_type is not None and record.get('record_type') != record_type):
            return
        if reference not in seen:
            found.append(reference)
            seen.add(reference)

    def walk(item):
        if isinstance(item, Mapping):
            if isinstance(item.get('record_type'), str):
                add(item.get('id'), item['record_type'])
            for key, child in item.items():
                if key == 'ref' or key.endswith('_ref'):
                    add(child)
                elif key == 'dependencies' or key.endswith('_refs'):
                    if isinstance(child, (tuple, list)):
                        for reference in child:
                            add(reference)
                walk(child)
        elif isinstance(item, (tuple, list)):
            for child in item:
                walk(child)

    def form_references(item, schema):
        if isinstance(item, Mapping):
            for key, child in item.items():
                node = schema.get('properties', {}).get(key)
                if node is not None:
                    form_references(child, node)
        elif isinstance(item, (tuple, list)):
            node = schema.get('items')
            if node is not None:
                for child in item:
                    form_references(child, node)
        elif schema.get('format') in REFERENCE_FORMATS:
            add(item)
    walk(value)
    for payload, schema in forms:
        form_references(payload, schema)
    if reference_subset is None:
        return found
    admitted = set(reference_subset(found))
    return [ref for ref in found if ref in admitted]
