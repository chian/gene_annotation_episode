"""A103 private scripted action, transport and archive fixture helpers."""
import json
from jsonschema import Draft202012Validator

HANDOFF_FORM = {"type": "object", "additionalProperties": False, "properties": {
    "completed": {"type": "boolean", "x-source": "execution_completed"},
    "references": {"type": "array", "uniqueItems": True, "items": {"type": "string", "format": "reference",
        "x-reference-namespace": "execution_handoff"}, "x-source": "execution_handoff_refs"}},
    "required": ["completed", "references"]}

def action(name, arguments=None):
    return {"selection": {"kind": "tool", "tool": name, "arguments": arguments or {}}, "report_update": {}}


def commission(role, assignment, scope, form, *, objective):
    return {"selection": {"kind": "episode_child", "role": role,
        "goal": objective, "scope": scope,
        "purpose": "Return the requested typed facts with their original numerical meanings and custody.",
        "assignment": assignment, "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}


def provider_value(value, schema):
    """Use the actual provider's existing JSON-object transport contract."""
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            candidate = provider_value(value, branch)
            if Draft202012Validator(branch).is_valid(candidate):
                return candidate
        return value
    if schema.get("type") == "string" and isinstance(value, dict) and schema.get("description", "").startswith("JSON encoding"):
        return json.dumps(value)
    if schema.get("type") == "object" and isinstance(value, dict):
        result = dict(value)
        for name, field in schema.get("properties", {}).items():
            if name in result:
                result[name] = provider_value(result[name], field)
            elif name in schema.get("required", []) and Draft202012Validator(field).is_valid(None):
                result[name] = None
        return result
    if isinstance(value, list) and "items" in schema:
        return [provider_value(item, schema["items"]) for item in value]
    return value


def walk(record):
    yield record
    for unit in record["units"]:
        if unit.get("child") is not None:
            yield from walk(unit["child"])


def history(record):
    return [unit["controller_step"]["marginal_credit"] for unit in record["units"]]

