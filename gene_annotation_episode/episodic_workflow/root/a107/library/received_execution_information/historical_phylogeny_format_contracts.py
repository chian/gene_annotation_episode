"""Pure validators for the frozen phylogeny stored-format contracts.

Validation does not authenticate custody or read source bytes. The byte readers
check their supplied digests. These checks establish closed shapes, native
token/value consistency and internal references for saved-object calculations.
The returned object is detached; callers' objects are never modified.
"""
from __future__ import annotations
from copy import deepcopy
import re
_LOCATION_KEYS = frozenset({'artifact', 'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive', 'xml_path'})
_COMPLETENESS = ('complete', 'partial', 'truncated', 'unknown')

def _fail(code):
    raise ValueError('phylogeny_' + code)

def _shape(value, keys, code):
    if type(value) is not dict or set(value) != set(keys):
        _fail(code)

def _text(value, *, nonempty=False):
    return type(value) is str and (bool(value) or not nonempty)

def _integer(value, minimum=0):
    return type(value) is int and value >= minimum

def _artifact(value):
    _shape(value, {'raw_artifact_ref', 'source_ref', 'sha256'}, 'artifact_invalid')
    if not _text(value['raw_artifact_ref'], nonempty=True) or not _text(value['source_ref'], nonempty=True) or (not _text(value['sha256'])) or (re.fullmatch('[0-9a-f]{64}', value['sha256']) is None):
        _fail('artifact_invalid')

def _location(value, *, artifact=None):
    _shape(value, _LOCATION_KEYS, 'source_location_invalid')
    _artifact(value['artifact'])
    if artifact is not None and value['artifact'] != artifact:
        _fail('source_artifact_conflict')
    present = False
    for start, end, minimum in (('byte_start_0based', 'byte_end_0based_exclusive', 0), ('line_start_1based', 'line_end_1based_inclusive', 1)):
        a, b = (value[start], value[end])
        if a is None and b is None:
            continue
        if not _integer(a, minimum) or not _integer(b, minimum) or b < a:
            _fail('source_location_invalid')
        present = True
    path = value['xml_path']
    if path is not None:
        if not _text(path, nonempty=True) or not path.startswith('/'):
            _fail('source_location_invalid')
        present = True
    if not present:
        _fail('source_location_missing')

def validate_alignment_document(value: dict) -> dict:
    """Validate actual rows, incomplete matrices and exact declared dimensions.

    In incomplete PHYLIP, observed_row_count counts rows of the declared length;
    all partially read rows still occur in rows. A null column count prevents
    treating an incomplete or unequal matrix as a complete population.
    """
    _shape(value, {'alignment_id', 'artifact', 'format', 'layout', 'id_rule', 'encoding', 'declared_row_count', 'declared_column_count', 'observed_row_count', 'observed_column_count', 'completeness', 'rows'}, 'alignment_shape_invalid')
    _artifact(value['artifact'])
    if value['alignment_id'] != value['artifact']['raw_artifact_ref'] + '#alignment':
        _fail('alignment_identity_invalid')
    if value['completeness'] not in _COMPLETENESS or value['encoding'] not in ('ascii', 'utf-8'):
        _fail('alignment_metadata_invalid')
    if value['format'] == 'aligned_fasta':
        if value['layout'] != 'fasta' or value['id_rule'] != 'first_whitespace_token' or value['declared_row_count'] is not None or (value['declared_column_count'] is not None):
            _fail('alignment_metadata_invalid')
    elif value['format'] == 'relaxed_phylip':
        if value['layout'] not in ('sequential', 'interleaved') or value['id_rule'] != 'full_phylip_label' or value['encoding'] != 'ascii' or (not _integer(value['declared_row_count'])) or (not _integer(value['declared_column_count'])):
            _fail('alignment_metadata_invalid')
    else:
        _fail('alignment_format_invalid')
    if type(value['rows']) is not list:
        _fail('alignment_rows_invalid')
    lengths = []
    for index, row in enumerate(value['rows']):
        _shape(row, {'row_index', 'raw_header', 'member_label', 'sequence', 'source_location'}, 'alignment_row_shape_invalid')
        if type(row['row_index']) is not int or row['row_index'] != index:
            _fail('row_index_invalid')
        if any((type(row[key]) is not str for key in ('raw_header', 'member_label', 'sequence'))):
            _fail('alignment_row_invalid')
        if value['encoding'] == 'ascii' and any((not row[key].isascii() for key in ('raw_header', 'member_label', 'sequence'))):
            _fail('alignment_encoding_conflict')
        if value['format'] == 'aligned_fasta':
            expected = row['raw_header'].split()
            if row['member_label'] != (expected[0] if expected else ''):
                _fail('alignment_label_conflict')
        elif row['raw_header'] != row['member_label'] or any((c.isspace() for c in row['member_label'])):
            _fail('alignment_label_conflict')
        _location(row['source_location'], artifact=value['artifact'])
        lengths.append(len(row['sequence']))
    nrows, columns = (value['observed_row_count'], value['observed_column_count'])
    if not _integer(nrows) or (columns is not None and (not _integer(columns))):
        _fail('alignment_dimensions_invalid')
    expected_rows = len(lengths) if value['format'] == 'aligned_fasta' else sum((x == value['declared_column_count'] for x in lengths))
    if nrows != expected_rows:
        _fail('alignment_row_count_conflict')
    if columns is not None:
        if any((x != columns for x in lengths)) or (not lengths and columns != 0):
            _fail('alignment_column_count_conflict')
        if value['format'] == 'relaxed_phylip' and (nrows != value['declared_row_count'] or columns != value['declared_column_count']):
            _fail('alignment_declared_dimensions_conflict')
        if not lengths and value['completeness'] != 'complete':
            _fail('alignment_empty_completeness_conflict')
    if value['completeness'] == 'complete':
        if columns is None or any((not row['member_label'] for row in value['rows'])):
            _fail('alignment_complete_dimensions_missing')
        if value['format'] == 'relaxed_phylip' and (len(lengths) != value['declared_row_count'] or nrows != len(lengths)):
            _fail('alignment_declared_dimensions_conflict')
    return deepcopy(value)
