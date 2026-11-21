"""The model endpoint's rules for the strict output schema of a model request, as an offline check for tests.

``ModelProvider`` itself checks only that the schema is a JSON Schema of an object
(``ModelProvider._check_arguments``); the endpoint behind it (the Codex app-server, strict structured output) then
refuses a schema that breaks its own rules with HTTP 400 at the first model call, and refuses an input text over its
limit. ``violations`` names every such break of a strict schema without asking the model, so a test can assert an
episode's decision request before a real run meets it. ``admitted_by_provider`` runs the provider's own check.

The rules, and what each rests on:

- ``array_without_items``: recorded rejection ("array schema must define items", the A101 head, 19 November 2026);
- ``keyword_not_taken:allOf``, ``enum_value_not_scalar``: recorded rejections (``invalid_json_schema`` for an
  embedded ``allOf`` and for an object-valued ``enum``; ``docs/EVIDENCE_AXIS_LEDGER.md``, 5 and 6 November 2026);
- ``object_not_closed``, ``property_not_required``, ``required_names_no_property``, ``root_not_an_object``,
  ``schema_without_type``, ``empty_enum``, ``empty_union``, the other ``keyword_not_taken:<keyword>``,
  ``reference_not_local``: the endpoint's published rules for strict structured output (every object closed with
  every property required; a root object that is not a union; ``anyOf`` the only composition; a type on every
  schema, which an ``enum`` stands in for: the endpoint accepted typeless enums in the recorded runs). No request
  that breaks one of these was ever sent from this repository, so none is recorded as refused;
- ``too_many_properties``, ``nested_too_deep``, ``too_many_enum_values``, ``names_too_long``, ``enum_too_long``: the
  endpoint's published size limits (``LIMITS``). Not observed here either: the largest schema the endpoint accepted
  in the recorded runs has 168 properties, 129 enum values and 6 levels;
- ``INPUT_CHARACTERS``: recorded rejection of an input text (``input_too_large``, ``max_chars`` 1048576).

Every rule was run over the 1675 requests the endpoint accepted in this repository's recorded real runs
(``runs/*/tmp/*/model_calls*/call-*/request.json`` with a ``response.json``, 54 distinct schemas, 19 November
2026) and none of them breaks one.
"""
import json

from gene_annotation_episode.model_provider import ModelProvider

INPUT_CHARACTERS = 1048576
LIMITS = {'properties': 5000, 'nesting': 10, 'enum_values': 1000, 'name_characters': 120000,
          'large_enum_values': 250, 'large_enum_characters': 15000}
NOT_TAKEN = ('allOf', 'oneOf', 'not', 'if', 'then', 'else', 'dependentRequired', 'dependentSchemas',
             'patternProperties', 'propertyNames', 'unevaluatedProperties', 'unevaluatedItems', 'prefixItems',
             'contains', 'minContains', 'maxContains', 'minProperties', 'maxProperties', 'additionalItems')
DEFINITIONS = ('$defs', 'definitions')


def pointer(path):
    return '/' + '/'.join(str(part) for part in path)


def children(schema, path):
    """The subschemas of one schema, with the path of each and whether it is one level of nesting deeper."""
    for keyword in (*DEFINITIONS, 'properties'):
        for name, child in schema.get(keyword, {}).items():
            yield (*path, keyword, name), child, keyword == 'properties'
    for index, child in enumerate(schema.get('anyOf', [])):
        yield (*path, 'anyOf', index), child, False
    if isinstance(schema.get('items'), dict):
        yield (*path, 'items'), schema['items'], True


def violations(schema):
    """Every rule of the endpoint the strict ``schema`` breaks, as ``(schema path, rule)`` in schema order."""
    found = []
    counted = {'properties': 0, 'enum_values': 0, 'name_characters': 0, 'nesting': 0}
    if schema.get('type') != 'object' or 'anyOf' in schema:
        found.append((pointer(()), 'root_not_an_object'))

    def visit(node, path, depth):
        counted['nesting'] = max(counted['nesting'], depth)
        for keyword in NOT_TAKEN:
            if keyword in node:
                found.append((pointer(path), 'keyword_not_taken:' + keyword))
        if '$ref' in node:
            if not any(node['$ref'].startswith('#/' + keyword + '/') for keyword in DEFINITIONS) and node['$ref'] != '#':
                found.append((pointer(path), 'reference_not_local'))
        elif 'anyOf' in node:
            if not node['anyOf']:
                found.append((pointer(path), 'empty_union'))
        elif 'type' not in node and 'enum' not in node:
            found.append((pointer(path), 'schema_without_type'))
        kinds = node.get('type', [])
        kinds = [kinds] if isinstance(kinds, str) else kinds
        if 'array' in kinds and not isinstance(node.get('items'), dict):
            found.append((pointer(path), 'array_without_items'))
        if 'object' in kinds:
            properties = node.get('properties', {})
            if node.get('additionalProperties') is not False:
                found.append((pointer(path), 'object_not_closed'))
            required = node.get('required', [])
            if set(properties) - set(required):
                found.append((pointer(path), 'property_not_required'))
            if set(required) - set(properties):
                found.append((pointer(path), 'required_names_no_property'))
            counted['properties'] += len(properties)
            counted['name_characters'] += sum(len(name) for name in properties)
        for keyword in DEFINITIONS:
            counted['name_characters'] += sum(len(name) for name in node.get(keyword, {}))
        if 'enum' in node:
            values = node['enum']
            texts = [value for value in values if isinstance(value, str)]
            if not values:
                found.append((pointer(path), 'empty_enum'))
            if any(isinstance(value, (dict, list)) for value in values):
                found.append((pointer(path), 'enum_value_not_scalar'))
            counted['enum_values'] += len(values)
            counted['name_characters'] += sum(len(value) for value in texts)
            if len(values) > LIMITS['large_enum_values'] and \
                    sum(len(value) for value in texts) > LIMITS['large_enum_characters']:
                found.append((pointer(path), 'enum_too_long'))
        if isinstance(node.get('const'), str):
            counted['name_characters'] += len(node['const'])
        for child_path, child, deeper in children(node, path):
            visit(child, child_path, depth + deeper)

    visit(schema, (), 0)
    for name, rule in (('properties', 'too_many_properties'), ('nesting', 'nested_too_deep'),
                       ('enum_values', 'too_many_enum_values'), ('name_characters', 'names_too_long')):
        if counted[name] > LIMITS[name]:
            found.append((pointer(()), rule + ':' + str(counted[name])))
    return found


def measures(schema):
    """The sizes the endpoint limits, for a report: properties, nesting, enum values, name characters."""
    counted = {'properties': 0, 'enum_values': 0, 'nesting': 0}

    def visit(node, depth):
        counted['nesting'] = max(counted['nesting'], depth)
        counted['properties'] += len(node.get('properties', {}))
        counted['enum_values'] += len(node.get('enum', []))
        for _, child, deeper in children(node, ()):
            visit(child, depth + deeper)

    visit(schema, 0)
    return {**counted, 'schema_characters': len(json.dumps(schema))}


def admitted_by_provider(request, directory):
    """Run the provider's own check of a model request (its role, instructions, context and output schema) and
    return the input text and the schema it would send; the model is not asked."""
    provider = ModelProvider({'connection': {'command': ['codex', 'app-server', '--stdio']},
                              request.role: {'model': 'offline', 'reasoning_effort': 'offline'}},
                             directory, directory.parent)
    return provider._check_arguments('offline', request.role, request.instructions, request.context,
                                     request.output_schema)
