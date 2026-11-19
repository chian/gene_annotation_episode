"""Closed typed parent forms.

This module adapts domain string types; it never assesses science.
Recorded fields bind to facts instead of asking a second model to compose them.
"""
from __future__ import annotations
from collections.abc import Mapping
from functools import lru_cache
import json
import math
import re
from jsonschema import Draft202012Validator, SchemaError



class ReportBoundaryError(ValueError):
    """A typed A108 form violates its closed schema."""

    def __init__(self, message: str, *, code='invalid_form', field=None):
        super().__init__(message)
        self.diagnostic = {'category': 'report_format', 'code': code, 'field': field}

CODE = re.compile('^[A-Za-z_][A-Za-z0-9_.:+/\\-]{0,127}$')
UNITS = {'dimensionless', 'fraction', 'percent', 'count', 'nt', 'aa', 'bits', 'seconds', 'bytes'}
REFERENCE_FORMATS = {'reference', 'identifier', 'accession'}
FORMATS = REFERENCE_FORMATS | {'unit', 'mathematical_expression', 'dna_sequence', 'protein_sequence', 'alignment_symbol', 'alignment_strand', 'structure_identifier', 'structure_residue_number', 'structure_insertion_code'}
KEYWORDS = {'type', 'properties', 'required', 'additionalProperties', 'items', 'minItems', 'maxItems', 'uniqueItems', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'enum', 'const', 'format', 'description', 'x-reference-namespace', 'x-source'}

def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value

def _finite(value, path='report'):
    if isinstance(value, float) and (not math.isfinite(value)):
        raise ReportBoundaryError('Non-finite report number', code='nonfinite_number', field=path)
    if isinstance(value, Mapping):
        for key, child in value.items():
            _finite(child, f'{path}.{key}')
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            _finite(child, f'{path}[{i}]')

def _schema_cacheable(value):
    """Only exact finite JSON content can use the compilation cache."""
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return True
    if kind is float:
        return math.isfinite(value)
    if kind is dict:
        return all((type(key) is str and _schema_cacheable(child) for key, child in value.items()))
    if kind is list:
        return all((_schema_cacheable(child) for child in value))
    return False

@lru_cache(maxsize=128)
def _compiled_schema_content(content):
    _compile_closed_schema(json.loads(content))

def validate_closed_schema(schema):
    """Compile a parent-chosen form and return its current detached tree."""
    schema = plain(schema)
    try:
        content = json.dumps(schema, separators=(',', ':'), allow_nan=False).encode('utf-8') if _schema_cacheable(schema) else None
    except (ValueError, TypeError, OverflowError, RecursionError):
        content = None
    if content is None:
        return _compile_closed_schema(schema)
    try:
        _compiled_schema_content(content)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return _compile_closed_schema(schema)
    return schema

def _compile_closed_schema(schema):
    """Closed-form grammar plus exact registered facts; errors are never cached."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ReportBoundaryError(exc.message, code='invalid_schema') from exc

    def check(node, path, depth=0):
        source = node.get('x-source') if isinstance(node, dict) else None
        if source in {'literature_a108_grading_cells', 'literature_a108_aggregation_cells'}:
            if depth != 1:
                raise ReportBoundaryError(f'{path}: fact bindings apply to whole top-level fields', code='invalid_schema')
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import grading_cells_schema
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_aggregation_storage import aggregation_cells_schema
            registered = grading_cells_schema if source == 'literature_a108_grading_cells' else aggregation_cells_schema
            if not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False) != json.dumps(registered(), sort_keys=True, allow_nan=False):
                raise ReportBoundaryError(f'{path}: A108 numerical fact schema must match its registered source', code='invalid_schema')
            return
        if not isinstance(node, dict) or set(node) - KEYWORDS:
            raise ReportBoundaryError(f'{path}: unsupported schema keyword', code='invalid_schema')
        declared = node.get('type')
        kinds = set(declared) if isinstance(declared, list) else {declared}
        if not kinds or len(kinds - {'null'}) > 1 or (not kinds <= {'object', 'array', 'number', 'integer', 'boolean', 'null', 'string'}):
            raise ReportBoundaryError(f'{path}: explicit single type required', code='invalid_schema')
        if 'object' in kinds:
            props = node.get('properties')
            if not isinstance(props, dict) or node.get('additionalProperties') is not False or set(node.get('required', [])) != set(props):
                raise ReportBoundaryError(f'{path}: fields must be explicit, required and closed', code='open_object')
            for name, child in props.items():
                if not CODE.fullmatch(name):
                    raise ReportBoundaryError(f'{path}: invalid field name', code='invalid_schema')
                check(child, path + '.' + name, depth + 1)
        elif 'array' in kinds:
            if 'items' not in node:
                raise ReportBoundaryError(f'{path}: arrays need item types', code='open_array')
            check(node['items'], path + '[]', depth + 1)
        elif 'string' in kinds:
            literals = node.get('enum', [node['const']] if 'const' in node else None)
            if literals is not None:
                if not literals or any((v is not None and (not isinstance(v, str) or not CODE.fullmatch(v)) for v in literals)):
                    raise ReportBoundaryError(f'{path}: string literals must be declared codes', code='unrestricted_string')
            elif node.get('format') not in FORMATS:
                raise ReportBoundaryError(f'{path}: strings need a declared semantic type', code='unrestricted_string')
        elif 'format' in node:
            raise ReportBoundaryError(f'{path}: format only applies to strings', code='invalid_schema')
        for literal in node.get('enum', [node['const']] if 'const' in node else []):
            if isinstance(literal, (dict, list)):
                raise ReportBoundaryError(f'{path}: composite constants cannot bypass fields', code='invalid_schema')
        if 'x-reference-namespace' in node and node.get('format') not in REFERENCE_FORMATS:
            raise ReportBoundaryError(f'{path}: reference namespace needs reference type', code='invalid_schema')
        if 'x-source' in node and (not isinstance(node['x-source'], str) or not CODE.fullmatch(node['x-source'])):
            raise ReportBoundaryError(f'{path}: fact source must be a registered key', code='invalid_schema')
        if 'x-source' in node and (path.count('.') != 1 or '[]' in path):
            raise ReportBoundaryError(f'{path}: fact bindings apply to whole top-level fields', code='invalid_schema')
    if not isinstance(schema, dict) or schema.get('type') != 'object':
        raise ReportBoundaryError('Report must be a closed object', code='invalid_schema')
    check(schema, 'report')
    _finite(schema)
    return schema

def interpretation_schema(schema):
    """Recorded fields are not requested from a model."""
    schema = validate_closed_schema(schema)
    props = {name: node for name, node in schema['properties'].items() if 'x-source' not in node}
    return {'type': 'object', 'additionalProperties': False, 'properties': props, 'required': list(props)}

def generation_schema(schema):
    schema = validate_closed_schema(schema)

    def translate(node):
        if not isinstance(node, dict):
            return node
        node = dict(node)
        if 'properties' in node:
            node['properties'] = {name: translate(child) for name, child in node['properties'].items()}
        for keyword in ('anyOf', 'oneOf', 'allOf', 'prefixItems'):
            if keyword in node:
                node[keyword] = [translate(child) for child in node[keyword]]
        for keyword in ('items', 'not', 'if', 'then', 'else'):
            if keyword in node:
                node[keyword] = translate(node[keyword])
        kind = node.pop('format', None)
        node.pop('x-reference-namespace', None)
        node.pop('x-source', None)
        node.pop('x-unique-by', None)
        node.pop('uniqueItems', None)
        if kind == 'unit' and 'enum' not in node:
            node['enum'] = sorted(UNITS) + ([None] if 'null' in node.get('type', []) else [])
        if 'const' in node:
            node['enum'] = [node.pop('const')]
        return node
    return translate(schema)

