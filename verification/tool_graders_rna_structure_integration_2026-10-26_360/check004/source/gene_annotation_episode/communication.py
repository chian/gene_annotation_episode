"""Closed typed parent forms, adapted from the supplied method_loop boundary.

Sources: episodic_workflow/method_loop/communication.py and the restricted
schema guard in orbital_workflow/orbital_workflow/communication.py. This module
adapts domain string types and reference validation; it never assesses science.
Recorded fields bind to facts instead of asking a second model to compose them.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from functools import lru_cache
import json
import math
import re
from typing import Callable

from jsonschema import Draft202012Validator, SchemaError

from .form_reference_validation import form_reference_validation


class ReportBoundaryError(ValueError):
    def __init__(self, message: str, *, code="invalid_form", field=None):
        super().__init__(message)
        self.diagnostic = {"category": "report_format", "code": code, "field": field}


CODE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:+/\-]{0,127}$")
UNITS = {"dimensionless", "fraction", "percent", "count", "nt", "aa", "bits", "seconds", "bytes"}
REFERENCE_FORMATS = {"reference", "identifier", "accession"}
FORMATS = REFERENCE_FORMATS | {"unit", "mathematical_expression", "dna_sequence", "protein_sequence",
    "alignment_symbol", "alignment_strand", "structure_identifier", "structure_residue_number",
    "structure_insertion_code"}
KEYWORDS = {"type", "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
            "uniqueItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "enum", "const",
            "format", "description", "x-reference-namespace", "x-source"}


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def _finite(value, path="report"):
    if isinstance(value, float) and not math.isfinite(value):
        raise ReportBoundaryError("Non-finite report number", code="nonfinite_number", field=path)
    if isinstance(value, Mapping):
        for key, child in value.items():
            _finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            _finite(child, f"{path}[{i}]")


def _expression(value):
    try:
        tree = ast.parse(value, mode="eval")
    except (SyntaxError, ValueError):
        return False
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
               ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)
    functions = {"sqrt", "sin", "cos", "exp", "log", "abs"}
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            return False
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, float) or not math.isfinite(node.value)):
            return False
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in functions or node.keywords):
            return False
    return True


def _schema_cacheable(value):
    """Only exact finite JSON content can use the compilation cache."""
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return True
    if kind is float:
        return math.isfinite(value)
    if kind is dict:
        return all(type(key) is str and _schema_cacheable(child)
                   for key, child in value.items())
    if kind is list:
        return all(_schema_cacheable(child) for child in value)
    return False


@lru_cache(maxsize=128)
def _compiled_schema_content(content):
    # lru_cache retains successful calls only. This process-local grammar
    # verdict contains no payload, reference, possession or scientific fact.
    _compile_closed_schema(json.loads(content))


def validate_closed_schema(schema):
    """Compile a parent-chosen form and return its current detached tree."""
    schema = plain(schema)
    try:
        content = (json.dumps(schema, separators=(",", ":"), allow_nan=False).encode("utf-8")
                   if _schema_cacheable(schema) else None)
    except (ValueError, TypeError, OverflowError, RecursionError):
        content = None
    if content is None:
        return _compile_closed_schema(schema)
    try:
        _compiled_schema_content(content)
    except (ValueError, TypeError, OverflowError, RecursionError):
        # Preserve the original input's diagnostics, including unsupported
        # objects and failures that cannot be represented by the fast path.
        return _compile_closed_schema(schema)
    return schema


def _compile_closed_schema(schema):
    """Closed-form grammar plus exact registered facts; errors are never cached."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ReportBoundaryError(exc.message, code="invalid_schema") from exc

    native_blast_sources = None
    standard_blast_sources = None
    rna_structure_sources = None

    def check(node, path, depth=0):
        nonlocal native_blast_sources, standard_blast_sources, rna_structure_sources
        source = node.get("x-source") if isinstance(node, dict) else None
        if isinstance(source, str) and source.startswith("execution_rna_structure_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if rna_structure_sources is None:
                from .rna_structure_result_views import rna_structure_fact_sources
                rna_structure_sources = rna_structure_fact_sources()
            expected = rna_structure_sources.get(source, {}).get("report_schema")
            # Recorded RNA fields have exact units, nullable associations and
            # native labels. They do not grant a free-form model schema.
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: RNA fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution_blast_standard_database_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if standard_blast_sources is None:
                from .native_blast_standard_database_result_views import standard_blast_database_fact_sources
                standard_blast_sources = standard_blast_database_fact_sources()
            expected = standard_blast_sources.get(source, {}).get("report_schema")
            # These recorded contracts contain native strings, tagged identities,
            # tuples and numerical relationships outside the generic grammar.
            # Match the complete detached JSON tree, including scalar types;
            # Python equality alone would treat True, 1 and 1.0 as equal.
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: native BLAST fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution_blast_database_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if native_blast_sources is None:
                from .native_blast_database_result_views import native_blast_database_fact_sources
                native_blast_sources = native_blast_database_fact_sources()
            expected = native_blast_sources.get(source, {}).get("report_schema")
            # These recorded contracts contain native strings, tagged identities,
            # tuples and numerical relationships outside the generic grammar.
            # Match the complete detached JSON tree, including scalar types;
            # Python equality alone would treat True, 1 and 1.0 as equal.
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: native BLAST fact schema must match its registered source", code="invalid_schema")
            return
        if not isinstance(node, dict) or set(node) - KEYWORDS:
            raise ReportBoundaryError(f"{path}: unsupported schema keyword", code="invalid_schema")
        declared = node.get("type")
        kinds = set(declared) if isinstance(declared, list) else {declared}
        if not kinds or len(kinds - {"null"}) > 1 or not kinds <= {"object", "array", "number", "integer", "boolean", "null", "string"}:
            raise ReportBoundaryError(f"{path}: explicit single type required", code="invalid_schema")
        if "object" in kinds:
            props = node.get("properties")
            if not isinstance(props, dict) or node.get("additionalProperties") is not False or set(node.get("required", [])) != set(props):
                raise ReportBoundaryError(f"{path}: fields must be explicit, required and closed", code="open_object")
            for name, child in props.items():
                if not CODE.fullmatch(name):
                    raise ReportBoundaryError(f"{path}: invalid field name", code="invalid_schema")
                check(child, path + "." + name, depth + 1)
        elif "array" in kinds:
            if "items" not in node:
                raise ReportBoundaryError(f"{path}: arrays need item types", code="open_array")
            check(node["items"], path + "[]", depth + 1)
        elif "string" in kinds:
            literals = node.get("enum", [node["const"]] if "const" in node else None)
            if literals is not None:
                if not literals or any(v is not None and (not isinstance(v, str) or not CODE.fullmatch(v)) for v in literals):
                    raise ReportBoundaryError(f"{path}: string literals must be declared codes", code="unrestricted_string")
            elif node.get("format") not in FORMATS:
                raise ReportBoundaryError(f"{path}: strings need a declared semantic type", code="unrestricted_string")
        elif "format" in node:
            raise ReportBoundaryError(f"{path}: format only applies to strings", code="invalid_schema")
        for literal in node.get("enum", [node["const"]] if "const" in node else []):
            if isinstance(literal, (dict, list)):
                raise ReportBoundaryError(f"{path}: composite constants cannot bypass fields", code="invalid_schema")
        if "x-reference-namespace" in node and node.get("format") not in REFERENCE_FORMATS:
            raise ReportBoundaryError(f"{path}: reference namespace needs reference type", code="invalid_schema")
        if "x-source" in node and (not isinstance(node["x-source"], str) or not CODE.fullmatch(node["x-source"])):
            raise ReportBoundaryError(f"{path}: fact source must be a registered key", code="invalid_schema")
        if "x-source" in node and (path.count(".") != 1 or "[]" in path):
            raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ReportBoundaryError("Report must be a closed object", code="invalid_schema")
    check(schema, "report")
    _finite(schema)
    return schema


def validate_form(payload, schema, reference_resolver: Callable | None = None):
    with form_reference_validation():
        return _validate_form(payload, schema, reference_resolver)


def _validate_form(payload, schema, reference_resolver):
    schema = validate_closed_schema(schema)
    payload = plain(payload)
    _finite(payload)
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    if errors:
        error = errors[0]
        raise ReportBoundaryError(error.message, code=error.validator, field=".".join(map(str, error.absolute_path)))

    def visit(value, node, path):
        if value is None or not isinstance(node, dict):
            return
        # The full Draft validator has already checked the payload. Semantic
        # annotations still need every applicable branch as well as base fields;
        # a nullable/tagged branch must not bypass its actual reference resolver.
        for keyword in ("anyOf", "oneOf"):
            for branch in node.get(keyword, []):
                if Draft202012Validator(branch).is_valid(value):
                    visit(value, branch, path)
        for branch in node.get("allOf", []):
            visit(value, branch, path)
        if "if" in node:
            selected = "then" if Draft202012Validator(node["if"]).is_valid(value) else "else"
            if selected in node:
                visit(value, node[selected], path)
        if isinstance(value, dict):
            properties = node.get("properties", {})
            for key, child in value.items():
                if key in properties:
                    visit(child, properties[key], f"{path}.{key}")
        elif isinstance(value, list):
            if "x-unique-by" in node:
                seen = set()
                for i, child in enumerate(value):
                    identity = tuple(child[key] for key in node["x-unique-by"])
                    if identity in seen:
                        raise ReportBoundaryError(f"{path}[{i}]: duplicate recorded identity", code="duplicate_identity", field=f"{path}[{i}]")
                    seen.add(identity)
            prefix = node.get("prefixItems", [])
            for i, child in enumerate(value):
                if i < len(prefix):
                    visit(child, prefix[i], f"{path}[{i}]")
                elif "items" in node:
                    visit(child, node["items"], f"{path}[{i}]")
        elif isinstance(value, str):
            kind = node.get("format")
            if kind in REFERENCE_FORMATS:
                if reference_resolver is None or not reference_resolver(value, node.get("x-reference-namespace")):
                    raise ReportBoundaryError(f"{path}: reference is unavailable at this boundary", code="unknown_reference", field=path)
            elif kind == "unit" and value not in UNITS:
                raise ReportBoundaryError(f"{path}: unknown unit", code="unknown_unit", field=path)
            elif kind == "mathematical_expression" and not _expression(value):
                raise ReportBoundaryError(f"{path}: invalid expression", code="invalid_expression", field=path)
            elif kind == "dna_sequence" and not re.fullmatch(r"[ACGTRYSWKMBDHVNacgtryswkmbdhvn]+", value):
                raise ReportBoundaryError(f"{path}: invalid DNA sequence", code="invalid_sequence", field=path)
            elif kind == "protein_sequence" and not re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWYBXZJUO*]+", value):
                raise ReportBoundaryError(f"{path}: invalid protein sequence", code="invalid_sequence", field=path)
            elif kind == "alignment_symbol" and not re.fullmatch(r"[!-~]", value):
                raise ReportBoundaryError(f"{path}: invalid alignment symbol", code="invalid_alignment_symbol", field=path)
            elif kind == "alignment_strand" and value not in {"+", "-", "unknown"}:
                raise ReportBoundaryError(f"{path}: invalid alignment strand", code="invalid_alignment_strand", field=path)
            elif kind == "structure_identifier" and not re.fullmatch(r"[!-~]+", value):
                raise ReportBoundaryError(f"{path}: invalid structure identifier", code="invalid_structure_identifier", field=path)
            elif kind == "structure_residue_number" and not re.fullmatch(r"-?[0-9]+", value):
                raise ReportBoundaryError(f"{path}: invalid structure residue number", code="invalid_structure_residue_number", field=path)
            elif kind == "structure_insertion_code" and value != "" and not re.fullmatch(r"[!-~]+", value):
                raise ReportBoundaryError(f"{path}: invalid structure insertion code", code="invalid_structure_insertion_code", field=path)
    visit(payload, schema, "report")
    return payload


def interpretation_schema(schema):
    """Recorded fields are not requested from a model."""
    schema = validate_closed_schema(schema)
    props = {name: node for name, node in schema["properties"].items() if "x-source" not in node}
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


def generation_schema(schema):
    schema = validate_closed_schema(schema)
    def translate(node):
        if not isinstance(node, dict):
            return node
        node = dict(node)
        if "properties" in node:
            node["properties"] = {name: translate(child) for name, child in node["properties"].items()}
        for keyword in ("anyOf", "oneOf", "allOf", "prefixItems"):
            if keyword in node:
                node[keyword] = [translate(child) for child in node[keyword]]
        for keyword in ("items", "not", "if", "then", "else"):
            if keyword in node:
                node[keyword] = translate(node[keyword])
        kind = node.pop("format", None)
        node.pop("x-reference-namespace", None)
        node.pop("x-source", None)
        node.pop("x-unique-by", None)
        node.pop("uniqueItems", None)
        if kind == "unit" and "enum" not in node:
            node["enum"] = sorted(UNITS) + ([None] if "null" in node.get("type", []) else [])
        if "const" in node:
            node["enum"] = [node.pop("const")]
        return node
    return translate(schema)


def form_with_facts(interpretations, schema, facts):
    schema = validate_closed_schema(schema)
    allowed = set(interpretation_schema(schema)["properties"])
    if not isinstance(interpretations, Mapping) or set(interpretations) != allowed:
        raise ReportBoundaryError("Interpretations must fill exactly the non-recorded fields", code="interpretation_fields")
    result = dict(interpretations)
    for name, node in schema["properties"].items():
        if "x-source" in node:
            key = node["x-source"]
            if key not in facts:
                raise ReportBoundaryError("Recorded fact source unavailable", code="unknown_fact", field=name)
            result[name] = plain(facts[key])
    return result


def reference_resolver(registry):
    """Create a resolver from live namespace -> actual semantic references."""
    def resolve(value, namespace=None):
        if namespace is not None:
            return value in registry.get(namespace, ())
        return any(value in values for values in registry.values())
    return resolve
