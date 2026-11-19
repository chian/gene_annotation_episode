"""Fill and read a parent's JSON-Schema report form: the axis-free part of the old report helpers.

A parent requests a typed form as a closed JSON object schema (``ReportContract.measurements['schema']``). A
property carrying ``x-source`` is a recorded fact the child copies from its own facts; every other property is an
interpretation the child's model writes. These functions do only that mechanics; validating the schema and the
filled form (string formats, native fact validators, references) stays with the episode's own validator
(``episode_support.forms.<axis>.communication.validate_form`` where its axis has one).

* ``interpretation_schema(schema)``: the closed object schema of the interpretation properties only.
* ``form_with_facts(interpretations, schema, facts)``: the form, interpretations plus each ``x-source`` fact.
* ``reference_resolver(registry)``: ``resolve(value, namespace=None)`` over a namespace -> references mapping
  (for example ``Store.references(scope)``).
"""
from __future__ import annotations

from collections.abc import Mapping
import copy


def _properties(schema):
    if not isinstance(schema, Mapping) or schema.get('type') != 'object' \
            or not isinstance(schema.get('properties'), Mapping):
        raise ValueError('report_form_schema_must_be_an_object_schema_with_properties')
    return schema['properties']


def interpretation_schema(schema):
    """The closed object schema of the properties without ``x-source`` (all of them required)."""
    properties = {name: copy.deepcopy(dict(node)) for name, node in _properties(schema).items()
                  if not (isinstance(node, Mapping) and 'x-source' in node)}
    return {'type': 'object', 'additionalProperties': False, 'properties': properties, 'required': list(properties)}


def form_with_facts(interpretations, schema, facts):
    """Interpretations for exactly the non-recorded properties, plus each ``x-source`` property from ``facts``."""
    properties = _properties(schema)
    wanted = set(interpretation_schema(schema)['properties'])
    if not isinstance(interpretations, Mapping) or set(interpretations) != wanted:
        raise ValueError('report_form_interpretations_must_fill_exactly:' + ','.join(sorted(wanted)))
    if not isinstance(facts, Mapping):
        raise TypeError('report_form_facts_must_be_a_mapping')
    form = copy.deepcopy(dict(interpretations))
    for name, node in properties.items():
        if isinstance(node, Mapping) and 'x-source' in node:
            source = node['x-source']
            if source not in facts:
                raise ValueError('report_form_fact_source_unavailable:' + name + ':' + str(source))
            form[name] = copy.deepcopy(facts[source])
    return form


def reference_resolver(registry):
    """``resolve(value, namespace=None)``: whether ``value`` is a reference of ``namespace`` (or of any)."""
    if not isinstance(registry, Mapping):
        raise TypeError('reference_resolver_requires_a_namespace_mapping')
    held = {namespace: frozenset(values) for namespace, values in registry.items()}

    def resolve(value, namespace=None):
        if namespace is not None:
            return value in held.get(namespace, frozenset())
        return any(value in values for values in held.values())
    return resolve


__all__ = ['form_with_facts', 'interpretation_schema', 'reference_resolver']
