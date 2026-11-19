"""JSON Schema traversal shared by host and provider transport."""

def _schema_nodes(schema, path=()):
    """Visit schema locations, without treating const/enum literals as schemas."""
    yield path, schema
    if not isinstance(schema, dict):
        return
    for name in ("$defs", "definitions", "properties", "patternProperties", "dependentSchemas"):
        children = schema.get(name, {})
        if isinstance(children, dict):
            for key, child in children.items():
                yield from _schema_nodes(child, (*path, name, key))
    for name in ("allOf", "anyOf", "oneOf", "prefixItems"):
        children = schema.get(name, [])
        if isinstance(children, list):
            for index, child in enumerate(children):
                yield from _schema_nodes(child, (*path, name, index))
    for name in ("not", "if", "then", "else", "contains", "propertyNames", "items",
                 "additionalProperties", "unevaluatedProperties", "unevaluatedItems",
                 "additionalItems", "contentSchema"):
        child = schema.get(name)
        if isinstance(child, (dict, bool)):
            yield from _schema_nodes(child, (*path, name))
        elif name == "items" and isinstance(child, list):
            for index, item in enumerate(child):
                yield from _schema_nodes(item, (*path, name, index))


