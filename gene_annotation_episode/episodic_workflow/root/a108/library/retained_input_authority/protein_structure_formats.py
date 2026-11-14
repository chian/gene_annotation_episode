"""Lossless token/table readers for explicitly supplied PDB 3.x and CIF 1.x.

Original bytes are caller-retained. All rows, lexical spellings, byte spans,
models and alternatives survive; malformed content never becomes repaired atoms.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, DecimalException
import math
import re
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.protein_structure_contracts import NativeToken, NativeNumber, issue

def absent_token() -> NativeToken:
    return {'lexeme': None, 'text': None, 'syntax': 'absent', 'lexical_state': 'absent', 'span': None}

def token_text(token):
    return token['text'] if token['lexical_state'] == 'value' else None

def pdb_field(record, start, end) -> NativeToken:
    text = record['text'].rstrip('\r\n')
    if len(text) <= start:
        return absent_token()
    lexeme = text[start:end]
    offset = record['span']['start_0based']
    return {'lexeme': lexeme, 'text': lexeme, 'syntax': 'pdb_field', 'lexical_state': 'value' if lexeme.strip() else 'pdb_blank', 'span': {'start_0based': offset + len(text[:start].encode('utf-8')), 'end_exclusive': offset + len(text[:min(end, len(text))].encode('utf-8'))}}
_NUMBER = re.compile('^([+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))(?:\\((\\d+)\\))?([eE][+-]?\\d+)?$')
_NUMBER_AFTER_EXP = re.compile('^([+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))([eE][+-]?\\d+)\\((\\d+)\\)$')

def native_number(token: NativeToken) -> NativeNumber:
    value = None
    uncertainty = None
    state = 'missing' if token['lexical_state'] != 'value' else 'invalid'
    if state != 'missing':
        text = token['text'].strip() if token['syntax'] == 'pdb_field' else token['text']
        match = _NUMBER.fullmatch(text)
        if match:
            mantissa, digits, exponent = match.groups()
        else:
            match = _NUMBER_AFTER_EXP.fullmatch(text)
            if match:
                mantissa, exponent, digits = match.groups()
        if match and token['syntax'] == 'pdb_field' and (digits is not None):
            match = None
        if match:
            try:
                exponent_number = int((exponent or 'e0')[1:])
                exact_value = Decimal(mantissa).scaleb(exponent_number)
                value = float(exact_value)
                if digits is not None:
                    decimals = len(mantissa.split('.', 1)[1]) if '.' in mantissa else 0
                    exact_uncertainty = Decimal(digits).scaleb(exponent_number - decimals)
                    uncertainty = float(exact_uncertainty)
                if math.isfinite(value) and (not (value == 0 and Decimal(mantissa) != 0)) and (uncertainty is None or (math.isfinite(uncertainty) and (not (uncertainty == 0 and int(digits) != 0)))):
                    state = 'present'
                else:
                    value = uncertainty = None
            except (DecimalException, ValueError, OverflowError):
                value = uncertainty = None
    return {'token': deepcopy(token), 'value': value, 'state': state, 'embedded_standard_uncertainty': uncertainty}

def native_integer(token, *, positive=False):
    text = token_text(token)
    if text is None or re.fullmatch('[+-]?\\d+', text.strip()) is None:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return value if not positive or value > 0 else None

def _pdb_contexts(records):
    """Original model/TER context of every coordinate or uncertainty record."""
    current = None
    models, contexts, issues, segments = ([], {}, [], {})
    explicit_seen = False
    serials = set()
    for record in records:
        name = record['record_name']
        if name == 'MODEL':
            if current is not None:
                issues.append(issue('malformed_record', field='model_key'))
            token = pdb_field(record, 10, 14)
            serial = native_integer(token)
            model = {'ordinal_0based': len(models), 'native_serial_token': token, 'serial_state': 'explicit' if token['lexical_state'] == 'value' else 'missing'}
            if serial is None or serial in serials:
                issues.append(issue('conflicting_identity' if serial in serials else 'malformed_record', field='model_key'))
            if serial is not None:
                serials.add(serial)
            models.append(model)
            current, explicit_seen, segments = (model, True, {})
        elif name == 'ENDMDL':
            if current is None:
                issues.append(issue('malformed_record', field='model_key'))
            current, segments = (None, {})
        elif name in ('ATOM', 'HETATM', 'TER', 'ANISOU', 'SIGUIJ', 'SIGATM'):
            if current is None:
                current = {'ordinal_0based': len(models), 'native_serial_token': absent_token(), 'serial_state': 'implicit'}
                models.append(current)
                if explicit_seen:
                    issues.append(issue('malformed_record', field='model_key'))
            chain = pdb_field(record, 21, 22)['text']
            if chain is not None and len(chain) == 1:
                chain_key = {'namespace': 'pdb', 'chain_id': chain, 'ter_segment_ordinal_0based': segments.get(chain, 0)}
                contexts[record['record_key']] = (current, chain_key)
                if name == 'TER':
                    segments[chain] = segments.get(chain, 0) + 1
    if explicit_seen and current is not None and (current['serial_state'] != 'implicit'):
        issues.append(issue('malformed_record', field='model_key'))
    return (models, contexts, issues)

def pdb_residue_identity(record, file_sha256, context, *, record_class=None):
    number = native_integer(pdb_field(record, 22, 26))
    component = token_text(pdb_field(record, 17, 20))
    insertion = pdb_field(record, 26, 27)['text']
    if context is None or number is None or component is None or (insertion is None) or (len(insertion) != 1):
        return None
    model, chain = context
    return {'format': 'pdb_3x_text', 'position_key': {'namespace': 'pdb', 'file_sha256': file_sha256, 'block_ordinal_0based': None, 'model_key': deepcopy(model), 'chain_key': deepcopy(chain), 'residue_number': number, 'insertion_code': insertion}, 'record_class': record_class or record['record_name'], 'component_id': component.strip()}

def category_rows(parsed, block_ordinal, category):
    """All native rows for a category, with scalar fields joined only within a block."""
    if block_ordinal >= len(parsed['cif_blocks']):
        return []
    category = category.lower().rstrip('.') + '.'
    result, scalar, scalar_keys = ([], {}, [])
    for table in parsed['cif_blocks'][block_ordinal]['tables']:
        tags = [t['text'].lower() for t in table['tags']]
        columns = [(i, tag[len(category):]) for i, tag in enumerate(tags) if tag.startswith(category)]
        if not columns:
            continue
        for key, row in zip(table['row_keys'], table['rows']):
            values = {name: row[i] for i, name in columns}
            if table['form'] == 'scalar':
                scalar.update(values)
                scalar_keys.append(key)
            else:
                result.append((key, values))
    if scalar:
        result.insert(0, (scalar_keys[0], scalar))
    return result

def get_token(row, name):
    return row.get(name.lower(), absent_token())
