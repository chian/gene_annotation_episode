"""Detached validation of retained BV-BRC MSA frequency tables.

These checks establish syntax and internal relationships, not external custody.
Unknown native protein spellings remain source tokens with an unresolved symbol.
No bytes are opened and no scientific calculation or acquisition is performed.
"""
from __future__ import annotations

from copy import deepcopy

from .bvbrc_alignment_values import document_id, native_number, validate_native_number
from .phylogeny_format_contracts import _artifact, _contained, _location


PROTEIN_SYMBOLS = dict(zip(
    ('Del', 'Ala', 'Cys', 'Asp', 'Glu', 'Phe', 'Gly', 'His', 'Ile', 'Lys',
     'Leu', 'Met', 'Asn', 'Pro', 'Gln', 'Arg', 'Ser', 'Thr', 'Val', 'Trp', 'Xaa', 'Tyr'),
    '-ACDEFGHIKLMNPQRSTVWXY'))
LAYOUTS = ('current_without_reference', 'current_with_reference')


def _require(ok, code):
    if not ok:
        raise ValueError('bvbrc_msa_' + code)


def _shape(value, keys, code):
    _require(type(value) is dict and set(value) == set(keys), code)


def _text(value, *, empty=False):
    _require(type(value) is str and (empty or bool(value)), 'text_invalid')


def _index(value):
    _require(type(value) is int and value >= 0, 'index_invalid')


def frequency_header(alphabet, layout):
    """The producer's four declared header layouts, in native field order."""
    _require(alphabet in ('dna', 'protein'), 'alphabet_invalid')
    _require(layout in LAYOUTS, 'layout_invalid')
    fields = ['Position in Alignment', 'Score', 'Consensus']
    fields += ['A', 'T', 'G', 'C', 'Deletion'] if alphabet == 'dna' else ['Detail']
    fields += ['Number of Sequences']
    if layout == 'current_with_reference':
        fields[1:1] = ['Position in Reference']
        fields[3:3] = ['Reference Character']
    return fields


def _number(value, *, row_location, artifact, encoding, integer=False, minimum=None):
    validate_native_number(value)
    _location(value['source_location'], artifact=artifact)
    _contained(value['source_location'], row_location)
    expected = native_number(value['raw_token'], source_location=value['source_location'],
                             integer=integer, minimum=minimum)
    _require(value == expected, 'native_number_semantics_conflict')
    if value['state'] == 'available' and integer:
        _require(type(value['value']) is int, 'native_integer_required')
    loc = value['source_location']
    if loc['byte_start_0based'] is not None:
        try:
            width = len(value['raw_token'].encode(encoding))
        except UnicodeError as error:
            raise ValueError('bvbrc_msa_encoding_conflict') from error
        _require(loc['byte_end_0based_exclusive'] - loc['byte_start_0based'] == width,
                 'native_token_location_conflict')


def validate_msa_frequency_table(value: dict) -> dict:
    """Validate and detach a table, retaining malformed numeric tokens and rows.

    row_index is the original zero-based data-row ordinal. A parser can omit a
    structurally unreadable row without renumbering the surviving records.
    Complete describes readable artifact syntax, not an authenticated job result.
    """
    _shape(value, {'table_id', 'artifact', 'alphabet', 'layout', 'encoding',
                  'header_tokens', 'completeness', 'rows'}, 'frequency_table_shape_invalid')
    _artifact(value['artifact'])
    _require(value['encoding'] in ('ascii', 'utf-8'), 'encoding_invalid')
    header = frequency_header(value['alphabet'], value['layout'])
    _require(value['header_tokens'] == header, 'native_header_conflict')
    _require(value['completeness'] in ('complete', 'partial', 'truncated', 'unknown'),
             'completeness_invalid')
    parameters = {key: value[key] for key in ('alphabet', 'layout', 'encoding')}
    _require(value['table_id'] == document_id('msa_frequency_table',
             artifact=value['artifact'], parameters=parameters), 'table_identity_conflict')
    _require(type(value['rows']) is list, 'rows_invalid')
    previous_index, previous_end = -1, None
    for row in value['rows']:
        _shape(row, {'row_index', 'source_location', 'alignment_position',
                     'reference_position', 'reference_character', 'score',
                     'consensus_token', 'n_sequences', 'dna_counts', 'protein_detail'},
               'frequency_row_shape_invalid')
        _index(row['row_index'])
        _require(row['row_index'] > previous_index, 'row_order_conflict')
        previous_index = row['row_index']
        _location(row['source_location'], artifact=value['artifact'])
        loc = row['source_location']
        if loc['line_start_1based'] is not None:
            _require(loc['line_start_1based'] == loc['line_end_1based_inclusive'] == row['row_index'] + 2,
                     'row_line_ordinal_conflict')
        if previous_end is not None and loc['byte_start_0based'] is not None:
            _require(loc['byte_start_0based'] >= previous_end, 'row_location_order_conflict')
        previous_end = loc['byte_end_0based_exclusive']
        def number(number_value, *, integer=False, minimum=None):
            _number(number_value, row_location=loc, artifact=value['artifact'],
                    encoding=value['encoding'], integer=integer, minimum=minimum)
        number(row['alignment_position'], integer=True, minimum=1)
        number(row['score'], minimum=0)
        number(row['n_sequences'], integer=True, minimum=0)
        _text(row['consensus_token'], empty=True)
        source_texts = [row['consensus_token']]
        if value['layout'] == 'current_with_reference':
            number(row['reference_position'], integer=True, minimum=1)
            _text(row['reference_character'], empty=True)
            source_texts.append(row['reference_character'])
        else:
            _require(row['reference_position'] is None and row['reference_character'] is None,
                     'reference_layout_conflict')
        if value['alphabet'] == 'dna':
            _require(row['protein_detail'] is None, 'alphabet_fields_conflict')
            _shape(row['dna_counts'], {'A', 'T', 'G', 'C', 'Deletion'}, 'dna_counts_shape_invalid')
            for count in row['dna_counts'].values():
                number(count, integer=True, minimum=0)
        else:
            _require(row['dna_counts'] is None and type(row['protein_detail']) is list,
                     'alphabet_fields_conflict')
            for entry in row['protein_detail']:
                _shape(entry, {'raw_token', 'raw_residue_token', 'symbol', 'count'},
                       'protein_detail_shape_invalid')
                _text(entry['raw_token'], empty=True)
                _text(entry['raw_residue_token'], empty=True)
                source_texts.extend((entry['raw_token'], entry['raw_residue_token']))
                number(entry['count'], integer=True, minimum=0)
                parts = entry['raw_token'].split('=', 1)
                _require(entry['raw_residue_token'] == parts[0], 'protein_residue_token_conflict')
                _require(entry['count']['raw_token'] == (parts[1] if len(parts) == 2 else ''),
                         'protein_count_token_conflict')
                expected_symbol = PROTEIN_SYMBOLS.get(parts[0]) if len(parts) == 2 else None
                _require(entry['symbol'] == expected_symbol, 'protein_symbol_conflict')
        try:
            for token in source_texts:
                token.encode(value['encoding'])
        except UnicodeError as error:
            raise ValueError('bvbrc_msa_encoding_conflict') from error
    return deepcopy(value)


__all__ = ['validate_msa_frequency_table']
