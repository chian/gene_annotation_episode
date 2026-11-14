"""Original decision schema display for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.schema_information_text import render_schema_information
from gene_annotation_episode.schema_information_text import schema_fingerprint
from .decision_prompt_text import _rows
from .decision_prompt_text import _table


def _schema_rows(schema, path="return", presence="required"):
    """Explain actual declared fields without converting contracts to prose guesses.

    Unusual JSON-schema keywords remain explicit constraint rows; the separate
    output schema is still the authoritative response contract. No constraints
    are inferred or weakened for presentation.
    """
    if isinstance(schema, bool):
        yield path, presence, "any value" if schema else "no permitted value", ""
        return
    kind = schema.get("type", "declared value")
    if isinstance(kind, list):
        kind = " or ".join(kind)
    meaning = schema.get("description", "")
    if "x-source" in schema:
        meaning += ("; " if meaning else "") + "recorded fact from " + schema["x-source"]
    if "format" in schema:
        kind += "; " + schema["format"]
    if "x-reference-namespace" in schema:
        kind += " to " + schema["x-reference-namespace"]
    yield path, presence, kind, meaning
    special = {"type", "description", "properties", "required", "items", "anyOf", "oneOf",
        "allOf", "if", "then", "else", "not", "$defs", "definitions", "title", "$schema", "$id",
        "format", "x-source", "x-reference-namespace"}
    for name, value in schema.items():
        if name not in special:
            for field, literal in _rows(value, name):
                yield path, "constraint", field, literal
    for name, child in schema.get("properties", {}).items():
        yield from _schema_rows(child, path + "." + name,
            "required" if name in schema.get("required", ()) else "optional")
    if "items" in schema:
        yield from _schema_rows(schema["items"], path + "[]", "each item")
    for operator in ("anyOf", "oneOf", "allOf"):
        for index, branch in enumerate(schema.get(operator, ())):
            yield from _schema_rows(branch, f"{path} ({operator} {index + 1})", operator)
    for operator in ("if", "then", "else", "not"):
        if operator in schema:
            yield from _schema_rows(schema[operator], f"{path} ({operator})", operator)
    for field in ("$defs", "definitions"):
        for name, child in schema.get(field, {}).items():
            yield from _schema_rows(child, field + "/" + name, "definition")


def _schema(schema, path, *, named_definitions=False):
    if named_definitions:
        return render_schema_information(schema, title=path)
    return _table(("Field", "Presence", "Type or constraint", "Meaning or value"),
        _schema_rows(schema, path))


def _registered_return_schema_view(form, sources):
    """Project only exact supplied registered arrays whose values the host fills.

    The complete original schema remains the host contract. Unmatched schemas,
    caller-composed fields and constraints outside the registered item tree keep
    their complete presentation; source names alone never authorize projection.
    """
    shown = deepcopy(form)
    if not isinstance(shown, Mapping) or not isinstance(sources, Mapping):
        return shown
    for name, node in shown.get("properties", {}).items():
        if not isinstance(node, Mapping) or node.get("type") != "array":
            continue
        source = node.get("x-source")
        registered = sources.get(source) if isinstance(source, str) else None
        if not isinstance(registered, Mapping) or "report_schema" not in registered:
            continue
        if schema_fingerprint(node) != schema_fingerprint(registered["report_schema"]):
            continue
        shallow = {key: value for key, value in node.items() if key != "items"}
        meanings = [node.get("description", ""), "Automatically supplied recorded values.",
            registered.get("meaning", "")]
        shallow["description"] = " ".join(value for value in meanings if value)
        shown["properties"][name] = shallow
    return shown


def _operation_schema_view(schema):
    """Omit proven operation host content pins, retaining caller schema identities."""
    from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import macs2_peak_schema_view
    macs2 = macs2_peak_schema_view(schema)
    if macs2 is not None:
        return macs2
    prefixes = ("urn:gene-annotation:ordinary-fba-tool:", "urn:gene-annotation:ordinary-orf-tool:")
    if not isinstance(schema, Mapping):
        return schema
    prefix = next((value for value in prefixes if str(schema.get("$id", "")).startswith(value)), None)
    if prefix is None:
        return schema
    shown = {key: value for key, value in schema.items() if key != "$id"}
    if schema["$id"] != prefix + digest(shown):
        return schema
    def has_reference(value):
        if isinstance(value, Mapping):
            return bool({"$ref", "$dynamicRef", "$recursiveRef"}.intersection(value)) or any(
                has_reference(child) for child in value.values())
        return isinstance(value, (list, tuple)) and any(has_reference(child) for child in value)
    return schema if has_reference(shown) else shown


# These are host record envelope fields, not arbitrary parent context or result
# fields. Semantic references (including content-addressed artifact operands)
# remain exact when a selected read, reasoned commitment or form needs them.
