"""Lossless named-definition text for caller-supplied JSON contracts.

This module reads no source or registry and resolves no schema reference. Local
definition names only avoid repeating identical structures in the presentation.
The scientific schema and its host validation remain separate responsibilities.
"""
from collections.abc import Mapping
import hashlib
import json
import math
import re

from .boundary_validation import parse_json_value


class SchemaInformationError(ValueError):
    def __init__(self, code, field=None):
        self.code, self.field = code, field
        super().__init__(code + (':' + field if field else ''))


def _copy_json(value, *, field='schema', active=None):
    """Detach JSON values, permitting immutable host object/array equivalents."""
    active = set() if active is None else active
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise SchemaInformationError('nonfinite_json_value', field)
        return value
    if not isinstance(value, (Mapping, list, tuple)):
        raise SchemaInformationError('non_json_value', field)
    if id(value) in active:
        raise SchemaInformationError('cyclic_json_value', field)
    active.add(id(value))
    try:
        if isinstance(value, Mapping):
            if any(type(key) is not str for key in value):
                raise SchemaInformationError('nonstring_json_key', field)
            return {key: _copy_json(child, field=field + '.' + key, active=active)
                    for key, child in value.items()}
        return [_copy_json(child, field=f'{field}[{index}]', active=active)
                for index, child in enumerate(value)]
    finally:
        active.remove(id(value))


def _canonical(value, *, sorted_keys=False):
    return json.dumps(value, ensure_ascii=True, sort_keys=sorted_keys,
                      separators=(',', ':'), allow_nan=False)


def schema_fingerprint(value):
    """Fingerprint the finite detached JSON tree, preserving scalar types."""
    return hashlib.sha256(_canonical(_copy_json(value), sorted_keys=True).encode('ascii')).hexdigest()


def _literal(value):
    text = json.dumps(value, ensure_ascii=False, allow_nan=False)
    # A literal pipe cannot collide with a Markdown column. Unicode line
    # separators and lone surrogates likewise remain explicit scalar escapes.
    return ''.join('\\u%04x' % ord(char) if char == '|' or char in '\u0085\u2028\u2029'
                   or 0xD800 <= ord(char) <= 0xDFFF else char for char in text)


_MAGIC = 'Schema information'
_RULES = ('Local definitions retain every declared field, constraint and literal. '
          'A reference reuses its complete named structure. Literal scalar cells '
          'use explicit quoted-string, null, boolean or number spelling. '
          'Array positions preserve order; no schema reference is resolved.')
_HEADER = '| Field or position | Entry kind | Declared value or structure |'
_SEPARATOR = '| --- | --- | --- |'
_END = 'End schema information'
_DEFINITION = re.compile(r'Definition[1-9][0-9]*\Z')


def _named_graph(value):
    records, existing = [], {}
    def intern(item):
        if not isinstance(item, (dict, list)):
            return ('literal', item)
        key = _canonical(item)
        if key in existing:
            return ('reference', existing[key])
        name = 'Definition' + str(len(records) + 1)
        existing[key] = name
        record = {'name': name, 'kind': 'object' if isinstance(item, dict) else 'array'}
        records.append(record)
        pairs = item.items() if isinstance(item, dict) else enumerate(item)
        record['fields'] = [(key, intern(child)) for key, child in pairs]
        return ('reference', name)
    return intern(value), records


def render_schema_information(value, *, title):
    """Render all finite JSON content in complete deterministic typed tables."""
    if type(title) is not str or not title:
        raise SchemaInformationError('nonempty_information_title_required', 'title')
    try:
        root, records = _named_graph(_copy_json(value))
        shown_root = root[1] if root[0] == 'reference' else _literal(root[1])
        lines = [_MAGIC, 'Title: ' + _literal(title), 'Root: ' + root[0] + ' ' + shown_root, '', _RULES]
        for row in records:
            lines.extend(['', row['name'] + ' — ' + row['kind'], '', _HEADER, _SEPARATOR])
            if not row['fields']:
                lines.append('| (none) | empty | ' + row['kind'] + ' |')
            for key, (kind, value) in row['fields']:
                shown = value if kind == 'reference' else _literal(value)
                lines.append('| ' + _literal(key) + ' | ' + kind + ' | ' + shown + ' |')
        lines.extend(['', _END, ''])
        return '\n'.join(lines)
    except RecursionError as error:
        raise SchemaInformationError('recursive_information_structure') from error


def _read_literal(text):
    try:
        value = parse_json_value(text)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise SchemaInformationError('invalid_information_literal') from error
    if isinstance(value, (dict, list)) or _literal(value) != text:
        raise SchemaInformationError('noncanonical_information_literal')
    return value


def _read_entry(kind, value):
    if kind == 'reference' and _DEFINITION.fullmatch(value):
        return kind, value
    if kind == 'literal':
        return kind, _read_literal(value)
    raise SchemaInformationError('invalid_information_entry')


def parse_schema_information(text):
    """Recover the exact JSON tree from a complete canonical information text.

    This is a text-codec check, not scientific interpretation or authentication
    of an operation, source, original request or received child result.
    """
    if type(text) is not str:
        raise SchemaInformationError('information_text_required')
    lines = text.split('\n')
    if (len(lines) < 8 or lines[0] != _MAGIC or not lines[1].startswith('Title: ')
            or not lines[2].startswith('Root: ') or lines[3] != '' or lines[4] != _RULES):
        raise SchemaInformationError('invalid_information_document')
    title = _read_literal(lines[1][len('Title: '):])
    if type(title) is not str or not title:
        raise SchemaInformationError('nonempty_information_title_required', 'title')
    try:
        kind, value = lines[2][len('Root: '):].split(' ', 1)
    except ValueError as error:
        raise SchemaInformationError('invalid_information_root') from error
    root = _read_entry(kind, value)
    records, position = {}, 5
    while position < len(lines):
        if lines[position] != '' or position + 1 >= len(lines):
            raise SchemaInformationError('invalid_information_document')
        position += 1
        if lines[position] == _END:
            position += 1
            if position != len(lines) - 1 or lines[position] != '':
                raise SchemaInformationError('trailing_information_content')
            break
        heading = re.fullmatch(r'(Definition[1-9][0-9]*) — (object|array)', lines[position])
        if heading is None or heading[1] in records:
            raise SchemaInformationError('invalid_information_definition')
        name, shape = heading.groups()
        position += 1
        if lines[position:position + 3] != ['', _HEADER, _SEPARATOR]:
            raise SchemaInformationError('invalid_information_table')
        position += 3
        fields, empty = [], False
        while position < len(lines) and lines[position].startswith('| '):
            line = lines[position]
            if not line.endswith(' |'):
                raise SchemaInformationError('invalid_information_row')
            columns = line[2:-2].split(' | ')
            if len(columns) != 3:
                raise SchemaInformationError('invalid_information_row')
            key, kind, value = columns
            if kind == 'empty':
                if fields or empty or key != '(none)' or value != shape:
                    raise SchemaInformationError('invalid_empty_information_definition')
                empty = True
            else:
                if empty:
                    raise SchemaInformationError('invalid_empty_information_definition')
                key = _read_literal(key)
                if ((shape == 'object' and type(key) is not str)
                        or (shape == 'array' and (type(key) is not int or key != len(fields)))
                        or any(key == previous for previous, _ in fields)):
                    raise SchemaInformationError('invalid_information_field')
                fields.append((key, _read_entry(kind, value)))
            position += 1
        if not fields and not empty:
            raise SchemaInformationError('missing_information_rows')
        records[name] = (shape, fields)
    else:
        raise SchemaInformationError('incomplete_information_document')
    visiting, used = set(), set()
    def expand(entry):
        kind, value = entry
        if kind == 'literal':
            return value
        if value not in records or value in visiting:
            raise SchemaInformationError('unknown_or_cyclic_information_definition')
        visiting.add(value)
        used.add(value)
        shape, fields = records[value]
        try:
            pairs = [(key, expand(child)) for key, child in fields]
            return dict(pairs) if shape == 'object' else [child for _, child in pairs]
        finally:
            visiting.remove(value)
    try:
        result = expand(root)
        if used != set(records) or render_schema_information(result, title=title) != text:
            raise SchemaInformationError('noncanonical_information_document')
    except RecursionError as error:
        raise SchemaInformationError('recursive_information_structure') from error
    return result


__all__ = ['SchemaInformationError', 'schema_fingerprint',
           'render_schema_information', 'parse_schema_information']
