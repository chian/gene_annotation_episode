"""Strict structured-output transport of an action schema, for an episode without its own transport module.

The old runner's ``_action_generation_schema`` / ``_decode_recorded_action_response`` (shared
``task_action_contracts``) translated an episode's action schema into the provider's strict form and decoded
the response back. A101, A103, A104, A105, A106 and A108 carry their own copies
(``episode_support/model_exchange/<axis>/action_transport.py``); this is the same transport as a plain function
for the others (A102, A107, A110). Differences are parameters:

- ``open_records_as_text``: an object schema that declares no properties and is not closed travels as JSON
  text (the A103/A106 variant) instead of as an object (the A101/A104/A105/A108 variant);
- ``argument_transport_error``: the error raised when a tool branch declares ``x-argument-transport``, which
  this transport does not carry.

Strict provider output requires every property and has no ``const``: optional fields travel as nullable
members, ``const`` becomes a one-value ``enum``, and composed tool arguments and child assignments travel as
JSON text. ``decode_strict_output`` undoes exactly that representation; the episode then admits the decoded
value against its original schema.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from jsonschema import Draft202012Validator

from gene_annotation_episode.schema_support import _schema_nodes
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import parse_json_object

_COMPOSITION = {'allOf', 'anyOf', 'oneOf', '$ref', '$dynamicRef', '$recursiveRef'}
_DROPPED = ('uniqueItems', 'pattern', 'format', 'x-source', 'x-reference-namespace')
_FIRST = ('kind', 'type', 'view', 'tool', 'role', 'selection')
_INTERPRETATION = {'terms', 'source_subjects', 'hypotheses', 'assessments', 'annotation_updates'}
_INTERPRETATION_FIRST = ('structural_proposals', 'terms', 'source_subjects', 'contexts', 'observations',
                         'hypotheses', 'assessments', 'interpretation_accounts', 'annotation_updates')


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _json(value):
    return json.dumps(_plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False)


def _episode_assignment(schema):
    properties = schema.get('properties', {})
    kind, assignment = (properties.get(name) for name in ('kind', 'assignment'))
    return (isinstance(kind, dict) and kind.get('const') == 'episode_child' and isinstance(assignment, dict)
            and (assignment.get('type') == 'object' or bool(_COMPOSITION.intersection(assignment))))


def _tool_arguments(schema, argument_transport_error):
    properties = schema.get('properties', {})
    kind = properties.get('kind')
    if not isinstance(kind, dict) or kind.get('const') != 'tool' or 'arguments' not in properties:
        return False
    if 'x-argument-transport' in schema:
        raise ValueError(argument_transport_error)
    keywords = _COMPOSITION | {'if', 'then', 'else', 'dependentRequired', 'dependentSchemas', 'maxProperties'}
    return any(isinstance(node, dict) and keywords.intersection(node)
               for _, node in _schema_nodes(properties['arguments']))


def _open_object(schema):
    return (isinstance(schema, dict) and schema.get('type') == 'object' and 'properties' not in schema
            and schema.get('additionalProperties') is not False and not _COMPOSITION.intersection(schema))


def _check(open_records_as_text, argument_transport_error):
    if type(open_records_as_text) is not bool:
        raise TypeError('open_records_as_text_must_be_boolean')
    if type(argument_transport_error) is not str or not argument_transport_error:
        raise ValueError('argument_transport_error_required')


def strict_output_schema(schema, *, open_records_as_text, argument_transport_error):
    """The provider's strict structured-output form of an action schema."""
    _check(open_records_as_text, argument_transport_error)

    def translate(value):
        if isinstance(value, list):
            return [translate(item) for item in value]
        if not isinstance(value, dict):
            return value
        if open_records_as_text and _open_object(value):
            return {'type': 'string', 'description': ' '.join(filter(None, (
                value.get('description'), 'JSON encoding of this one JSON object. The host validates the decoded '
                'object against: ' + _json(value))))}
        if _episode_assignment(value):
            properties = value['properties']
            return translate({**value, 'properties': {**properties, 'assignment': {
                'type': 'string', 'description': 'JSON encoding of the exact parent-selected episode assignment. '
                'Preserve all supplied fields and values. Preserve omitted fields and explicit nulls. The host '
                'validates this complete original schema: ' + _json(properties['assignment'])}}})
        if _tool_arguments(value, argument_transport_error):
            properties = value['properties']
            return translate({**value, 'properties': {**properties, 'arguments': {
                'type': 'string', 'description': 'JSON encoding of the exact tool argument object. Preserve omitted '
                'fields and explicit nulls. The host validates this complete standalone JSON Schema before '
                'execution: ' + _json(properties['arguments'])}}})
        result = {key: _plain(item) for key, item in value.items() if key not in _DROPPED}
        for keyword in ('$defs', 'definitions', 'properties', 'patternProperties', 'dependentSchemas'):
            if isinstance(result.get(keyword), dict):
                result[keyword] = {name: translate(item) for name, item in result[keyword].items()}
        for keyword in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
            if isinstance(result.get(keyword), list):
                result[keyword] = [translate(item) for item in result[keyword]]
        for keyword in ('not', 'if', 'then', 'else', 'contains', 'propertyNames', 'items', 'additionalProperties',
                        'unevaluatedProperties', 'unevaluatedItems', 'additionalItems', 'contentSchema'):
            item = result.get(keyword)
            if isinstance(item, (dict, bool)):
                result[keyword] = translate(item)
            elif keyword == 'items' and isinstance(item, list):
                result[keyword] = [translate(child) for child in item]
        if 'const' in result:
            result['enum'] = [result.pop('const')]
        if 'enum' in result and 'type' not in result:
            literals = result['enum']
            if all(isinstance(item, str) for item in literals):
                result['type'] = 'string'
            elif all(type(item) is int for item in literals):
                result['type'] = 'integer'
        if result.get('type') == 'object':
            properties = result.get('properties', {})
            first = _INTERPRETATION_FIRST if _INTERPRETATION <= set(properties) else _FIRST
            properties = {key: properties[key] for key in (*(key for key in first if key in properties),
                                                           *(key for key in properties if key not in first))}
            required = set(value.get('required', []))
            result['properties'] = {key: item if key in required else {'anyOf': [item, {'type': 'null'}]}
                                    for key, item in properties.items()}
            result['required'] = list(properties)
        return result
    return translate(schema)


def _tags(option):
    fields = option.get('properties', {}) if isinstance(option, dict) else {}
    return {key: field for key, field in fields.items()
            if isinstance(field, dict) and ('const' in field or len(field.get('enum', [])) == 1)}


def _tagged(value, option):
    tags = _tags(option)
    return bool(tags) and all(key in value and Draft202012Validator(field).is_valid(value[key])
                              for key, field in tags.items())


def decode_strict_output(value, schema, *, open_records_as_text, argument_transport_error):
    """Undo only the strict-output representation of ``value`` for the original ``schema``.

    A null is removed only where the original contract made that field optional; required nulls remain
    invalid. Atomic assignment/argument objects keep every supplied value.
    """
    _check(open_records_as_text, argument_transport_error)

    def decode(item, form):
        if not isinstance(form, dict):
            return item
        if 'anyOf' in form:
            if isinstance(item, Mapping):
                tagged = [option for option in form['anyOf'] if _tagged(item, option)]
                if len(tagged) == 1:
                    return decode(item, tagged[0])
            candidates = [decode(item, option) for option in form['anyOf']]
            for candidate, option in zip(candidates, form['anyOf']):
                if Draft202012Validator(option).is_valid(candidate):
                    return candidate
            if isinstance(item, Mapping):
                tagged = [candidate for candidate, option in zip(candidates, form['anyOf']) if _tagged(item, option)]
                if len(tagged) == 1:
                    return tagged[0]
            return item
        if open_records_as_text and _open_object(form):
            return parse_json_object(item) if isinstance(item, str) else item
        if isinstance(item, dict) and form.get('type') == 'object':
            required = set(form.get('required', []))
            properties = form.get('properties', {})
            encoded = _tool_arguments(form, argument_transport_error)
            encoded_assignment = _episode_assignment(form)
            return {key: ((parse_json_object(child) if isinstance(child, str) else child)
                          if (encoded and key == 'arguments') or (encoded_assignment and key == 'assignment')
                          else decode(child, properties.get(key, {})))
                    for key, child in item.items()
                    if not (key in properties and key not in required and child is None)}
        if isinstance(item, list) and form.get('type') == 'array':
            return [decode(child, form['items']) for child in item]
        return item
    return decode(value, schema)


__all__ = ['decode_strict_output', 'strict_output_schema']
