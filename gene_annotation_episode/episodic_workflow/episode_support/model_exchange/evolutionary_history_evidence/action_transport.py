"""A104's structured-output transport of an action schema to the model provider.

Moved from the shared root ``task_action_contracts`` (``_action_generation_schema``,
``_decode_action_response``) so the A104 decision source owns it. Strict
provider output requires every property and has no ``const``; optional fields
travel as nullable members and composed tool arguments or child assignments
travel as JSON text. ``decode_response`` undoes exactly that representation;
the host then validates the decoded selection against the original schema.
A104's tool registry declares no contract-argument transport, so a schema that
carries ``x-argument-transport`` is refused.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from jsonschema import Draft202012Validator

from gene_annotation_episode.schema_support import _schema_nodes

from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import parse_json_object
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.communication import plain

_COMPOSITION = {'allOf', 'anyOf', 'oneOf', '$ref', '$dynamicRef', '$recursiveRef'}


def _json(value):
    return json.dumps(plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False)


def _episode_assignment(schema):
    properties = schema.get('properties', {})
    kind, assignment = (properties.get(name) for name in ('kind', 'assignment'))
    return (isinstance(kind, dict) and kind.get('const') == 'episode_child' and isinstance(assignment, dict)
            and (assignment.get('type') == 'object' or bool(_COMPOSITION.intersection(assignment))))


def _tool_arguments(schema):
    """Composed tool inputs retain their own JSON reference/presence semantics."""
    properties = schema.get('properties', {})
    kind = properties.get('kind')
    if not isinstance(kind, dict) or kind.get('const') != 'tool' or 'arguments' not in properties:
        return False
    if 'x-argument-transport' in schema:
        raise ValueError('a104_tool_argument_transport_unsupported')
    keywords = _COMPOSITION | {'if', 'then', 'else', 'dependentRequired', 'dependentSchemas', 'maxProperties'}
    return any(isinstance(node, dict) and keywords.intersection(node)
               for _, node in _schema_nodes(properties['arguments']))


def generation_schema(schema):
    """The provider's strict structured-output form of an A104 action schema."""

    def translate(value):
        if isinstance(value, list):
            return [translate(item) for item in value]
        if not isinstance(value, dict):
            return value
        if _episode_assignment(value):
            properties = value['properties']
            return translate({**value, 'properties': {**properties, 'assignment': {
                'type': 'string', 'description': 'JSON encoding of the exact parent-selected episode assignment. '
                'Preserve all supplied fields and values. Preserve omitted fields and explicit nulls. The host '
                'validates this complete original schema: ' + _json(properties['assignment'])}}})
        if _tool_arguments(value):
            properties = value['properties']
            return translate({**value, 'properties': {**properties, 'arguments': {
                'type': 'string', 'description': 'JSON encoding of the exact tool argument object. Preserve omitted '
                'fields and explicit nulls. The host validates this complete standalone JSON Schema before '
                'execution: ' + _json(properties['arguments'])}}})
        result = {key: plain(item) for key, item in value.items()
                  if key not in ('uniqueItems', 'pattern', 'format', 'x-source', 'x-reference-namespace')}
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
            first = ('kind', 'type', 'view', 'tool', 'role', 'selection')
            if {'terms', 'source_subjects', 'hypotheses', 'assessments', 'annotation_updates'} <= set(properties):
                first = ('terms', 'source_subjects', 'contexts', 'observations',
                         'hypotheses', 'assessments', 'interpretation_accounts', 'annotation_updates')
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


def decode_response(value, schema):
    """Undo only the provider's optional-property and JSON-text representation.

    A null is removed only where the original contract made that field optional;
    required nulls remain invalid. Atomic assignment/argument objects keep every
    supplied value.
    """
    if not isinstance(schema, dict):
        return value
    if 'anyOf' in schema:
        if isinstance(value, Mapping):
            tagged = [option for option in schema['anyOf'] if _tagged(value, option)]
            if len(tagged) == 1:
                return decode_response(value, tagged[0])
        candidates = [decode_response(value, option) for option in schema['anyOf']]
        for candidate, option in zip(candidates, schema['anyOf']):
            if Draft202012Validator(option).is_valid(candidate):
                return candidate
        if isinstance(value, Mapping):
            tagged = [candidate for candidate, option in zip(candidates, schema['anyOf']) if _tagged(value, option)]
            if len(tagged) == 1:
                return tagged[0]
        return value
    if isinstance(value, dict) and schema.get('type') == 'object':
        required = set(schema.get('required', []))
        properties = schema.get('properties', {})
        encoded, encoded_assignment = _tool_arguments(schema), _episode_assignment(schema)
        return {key: ((parse_json_object(item) if isinstance(item, str) else item)
                      if (encoded and key == 'arguments') or (encoded_assignment and key == 'assignment')
                      else decode_response(item, properties.get(key, {})))
                for key, item in value.items()
                if not (key in properties and key not in required and item is None)}
    if isinstance(value, list) and schema.get('type') == 'array':
        return [decode_response(item, schema['items']) for item in value]
    return value


__all__ = ['decode_response', 'generation_schema']
