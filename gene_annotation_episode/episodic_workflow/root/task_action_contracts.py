"""Private root annotation task action contracts."""
from __future__ import annotations
from .composition_information import CONTRACT_ARGUMENT_TRANSPORT
from jsonschema import Draft202012Validator
from collections.abc import Mapping
from .task_values import _digest
from .task_values import _json
from .task_values import _plain
from dataclasses import field
from .boundary_validation import parse_json_object

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
_ASSIGNMENT_TRANSPORT = 'atomic_composed_episode_assignment_json_v1'

def _action_generation_schema(schema, *, _legacy_episode_assignments=False):
    """Translate action JSON Schema; unlike return forms it includes goal text.

    Goals and tool input contracts are instructions into an episode, not its
    child-to-parent communication channel. The closed-form guard still applies
    independently to every commissioned report and its actual returned payload.
    """

    def translate(value):
        if isinstance(value, list):
            return [translate(item) for item in value]
        if not isinstance(value, dict):
            return value
        if _json_episode_assignment(value, composed=not _legacy_episode_assignments):
            properties = value['properties']
            return translate({**value, 'properties': {**properties, 'assignment': {'type': 'string', 'description': 'JSON encoding of the exact parent-selected episode assignment. Preserve all supplied fields and values, including constraints, allocations, input versions and selections. Preserve omitted fields and explicit nulls. The host validates this complete original schema: ' + _json(properties['assignment'])}}})
        if _json_tool_arguments(value):
            properties = value['properties']
            requested_contract = value.get('x-argument-transport') == CONTRACT_ARGUMENT_TRANSPORT
            description = "JSON encoding of the exact tool argument object. Preserve omitted fields and explicit nulls. Request this operation's authoritative complete argument contract as information when needed. The host validates the original complete standalone schema before execution." if requested_contract else 'JSON encoding of the exact tool argument object. Preserve omitted fields and explicit nulls. The host validates this complete standalone JSON Schema before execution: ' + _json(properties['arguments'])
            transported = {key: item for key, item in value.items() if key != 'x-argument-transport'}
            transported = {**transported, 'properties': {**properties, 'arguments': {'type': 'string', 'description': description}}}
            return translate(transported)
        result = {key: _plain(item) for key, item in value.items() if key not in ('uniqueItems', 'pattern', 'format', 'x-source', 'x-reference-namespace', 'x-argument-transport')}
        for keyword in ('$defs', 'definitions', 'properties', 'patternProperties', 'dependentSchemas'):
            if isinstance(result.get(keyword), dict):
                result[keyword] = {name: translate(item) for name, item in result[keyword].items()}
        for keyword in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
            if isinstance(result.get(keyword), list):
                result[keyword] = [translate(item) for item in result[keyword]]
        for keyword in ('not', 'if', 'then', 'else', 'contains', 'propertyNames', 'items', 'additionalProperties', 'unevaluatedProperties', 'unevaluatedItems', 'additionalItems', 'contentSchema'):
            item = result.get(keyword)
            if isinstance(item, (dict, bool)):
                result[keyword] = translate(item)
            elif keyword == 'items' and isinstance(item, list):
                result[keyword] = [translate(child) for child in item]
        if 'const' in result:
            result['enum'] = [result.pop('const')]
        if 'enum' in result and 'type' not in result:
            literals = result['enum']
            if all((isinstance(item, str) for item in literals)):
                result['type'] = 'string'
            elif all((type(item) is int for item in literals)):
                result['type'] = 'integer'
        if result.get('type') == 'object':
            properties = result.get('properties', {})
            first = ('response_type', 'kind', 'type', 'view', 'tool', 'role', 'domain', 'source', 'operation', 'selection')
            if {'terms', 'source_subjects', 'hypotheses', 'assessments', 'annotation_updates'} <= set(properties):
                first = ('structural_proposals', 'terms', 'source_subjects', 'contexts', 'observations', 'hypotheses', 'assessments', 'interpretation_accounts', 'annotation_updates')
            properties = {key: properties[key] for key in (*(key for key in first if key in properties), *(key for key in properties if key not in first))}
            required = set(value.get('required', []))
            result['properties'] = {key: item if key in required else {'anyOf': [item, {'type': 'null'}]} for key, item in properties.items()}
            result['required'] = list(properties)
        return result
    return translate(schema)

def _json_episode_assignment(schema, *, composed=True):
    properties = schema.get('properties', {})
    kind, assignment = (properties.get(name) for name in ('kind', 'assignment'))
    return isinstance(kind, dict) and kind.get('const') == 'episode_child' and isinstance(assignment, dict) and (assignment.get('type') == 'object' or (composed and bool({'allOf', 'anyOf', 'oneOf', '$ref', '$dynamicRef', '$recursiveRef'}.intersection(assignment))))

def _json_tool_arguments(schema):
    """Composed inputs retain their own JSON reference/presence semantics."""
    properties = schema.get('properties', {})
    kind = properties.get('kind')
    if not isinstance(kind, dict) or kind.get('const') != 'tool' or 'arguments' not in properties:
        return False
    if 'x-argument-transport' in schema:
        if schema['x-argument-transport'] != CONTRACT_ARGUMENT_TRANSPORT or not isinstance(properties['arguments'], dict) or properties['arguments'].get('type') != 'object':
            raise ValueError('unsupported_tool_argument_transport')
        return True
    from gene_annotation_episode.schema_support import _schema_nodes
    keywords = {'allOf', 'anyOf', 'oneOf', '$ref', '$dynamicRef', '$recursiveRef', 'if', 'then', 'else', 'dependentRequired', 'dependentSchemas', 'maxProperties'}
    return any((isinstance(node, dict) and keywords.intersection(node) for _, node in _schema_nodes(properties['arguments'])))

def _decode_action_response(value, schema, *, _legacy_episode_assignments=False):
    """Undo only the provider's optional-property representation.

    Strict structured output represents absent optional fields as null. A null
    is removed only where the original host contract made that field optional;
    required nulls remain invalid. Atomic assignment/argument objects preserve
    every supplied value. Historical expanded assignments use their original
    decoder only through explicit recorded-transport/selection verification.
    """

    def decode(item, contract):
        return _decode_action_response(item, contract, _legacy_episode_assignments=_legacy_episode_assignments)
    if not isinstance(schema, dict):
        return value
    if 'anyOf' in schema:
        if isinstance(value, Mapping):
            tagged = []
            for option in schema['anyOf']:
                fields = option.get('properties', {}) if isinstance(option, dict) else {}
                tags = {key: field for key, field in fields.items() if isinstance(field, dict) and ('const' in field or len(field.get('enum', [])) == 1)}
                if tags and all((key in value and Draft202012Validator(field).is_valid(value[key]) for key, field in tags.items())):
                    tagged.append(option)
            if len(tagged) == 1:
                return decode(value, tagged[0])
        candidates = [decode(value, option) for option in schema['anyOf']]
        for candidate, option in zip(candidates, schema['anyOf']):
            if Draft202012Validator(option).is_valid(candidate):
                return candidate
        tagged = []
        if isinstance(value, Mapping):
            for candidate, option in zip(candidates, schema['anyOf']):
                fields = option.get('properties', {}) if isinstance(option, dict) else {}
                tags = {key: field for key, field in fields.items() if isinstance(field, dict) and ('const' in field or len(field.get('enum', [])) == 1)}
                if tags and all((key in value and Draft202012Validator(field).is_valid(value[key]) for key, field in tags.items())):
                    tagged.append(candidate)
        if len(tagged) == 1:
            return tagged[0]
        return value
    if isinstance(value, dict) and schema.get('type') == 'object':
        required = set(schema.get('required', []))
        properties = schema.get('properties', {})
        encoded = _json_tool_arguments(schema)
        encoded_assignment = _json_episode_assignment(schema, composed=not _legacy_episode_assignments)
        return {key: (parse_json_object(item) if isinstance(item, str) else item) if encoded and key == 'arguments' or (encoded_assignment and key == 'assignment') else decode(item, properties.get(key, {})) for key, item in value.items() if not (key in properties and key not in required and (item is None))}
    if isinstance(value, list) and schema.get('type') == 'array':
        return [decode(item, schema['items']) for item in value]
    return value

def _recorded_action_generation_schema(generated, schema):
    """Match only the current and immediately preceding assignment transports."""
    return _same_action_schema_required_members(generated, _action_generation_schema(schema)) or _same_action_schema_required_members(generated, _action_generation_schema(schema, _legacy_episode_assignments=True))

def _recorded_assignment_transport(saved):
    """Validate the private current-generator proof without inferring old data."""
    if 'assignment_transport' not in saved:
        return False
    if saved['assignment_transport'] != {'version': _ASSIGNMENT_TRANSPORT, 'action_schema_sha256': _digest(saved['schema'])}:
        raise ValueError('original_assignment_transport_mismatch')
    return True

def _same_action_schema_required_members(left, right):
    """Only schema required-member order is lost by markerless serialization."""
    from gene_annotation_episode.schema_support import _schema_nodes

    def normalized(value):
        value = _plain(value)
        for _, node in _schema_nodes(value):
            if not isinstance(node, dict) or 'required' not in node:
                continue
            members = node['required']
            if not isinstance(members, list) or any((type(member) is not str for member in members)) or len(set(members)) != len(members):
                return None
            node['required'] = sorted(members)
        return _json(value)
    original = normalized(left)
    return original is not None and original == normalized(right)

def _decode_recorded_action_response(value, schema, *, recorded_selection=None, exchanges=(), exchange_schema=None, unproven_replay=False):
    """Preserve an authoritative old selection without guessing absent values.

    A completed/selected action proves its entire original normalized selection.
    Before admission, an immutable matching exchange proves the original wire
    representation. The compatibility branch deliberately retains the old
    decoder, including its limits; it does not repair historical scientific data.
    """
    decoded = _decode_action_response(value, schema)
    if not isinstance(decoded, dict):
        return decoded

    def without_transport_proof():
        if unproven_replay:
            historical = _decode_action_response(value, schema, _legacy_episode_assignments=True)
            if _json(historical.get('selection')) != _json(decoded.get('selection')):
                raise ValueError('original_assignment_transport_unavailable')
        return decoded
    if recorded_selection is not None:
        if _json(decoded.get('selection')) == _json(recorded_selection):
            return decoded
        historical = _decode_action_response(value, schema, _legacy_episode_assignments=True)
        if _json(historical.get('selection')) == _json(recorded_selection):
            return historical
        raise ValueError('original_action_response_selection_mismatch')
    if not exchanges:
        return without_transport_proof()
    selected_schema = _object({'response_type': {'type': 'string', 'const': 'select_action'}, **schema['properties']})
    selected_schema['required'] = ['response_type', *schema['required']]
    if exchange_schema is not None:
        original = exchange_schema.get('properties', {}).get('response', {}).get('anyOf', [])
        if len(original) != 2 or _json(original[1]) != _json(selected_schema):
            raise ValueError('original_action_exchange_schema_mismatch')
    for row in exchanges:
        if not row.get('response_recorded') or not isinstance(row.get('response'), dict):
            continue
        original = row.get('response', {}).get('response', {})
        if not isinstance(original, dict) or original.get('response_type') != 'select_action' or _json(original) != _json({'response_type': 'select_action', **value}):
            continue
        generated = row['request'].get('output_schema', {})
        if exchange_schema is not None:
            if _same_action_schema_required_members(generated, _action_generation_schema(exchange_schema)):
                return decoded
            if _same_action_schema_required_members(generated, _action_generation_schema(exchange_schema, _legacy_episode_assignments=True)):
                return _decode_action_response(value, schema, _legacy_episode_assignments=True)
            continue
        alternatives = generated.get('properties', {}).get('response', {}).get('anyOf', [])
        if len(alternatives) == 2:
            if _same_action_schema_required_members(alternatives[1], _action_generation_schema(selected_schema)):
                return decoded
            if _same_action_schema_required_members(alternatives[1], _action_generation_schema(selected_schema, _legacy_episode_assignments=True)):
                return _decode_action_response(value, schema, _legacy_episode_assignments=True)
    return without_transport_proof()
