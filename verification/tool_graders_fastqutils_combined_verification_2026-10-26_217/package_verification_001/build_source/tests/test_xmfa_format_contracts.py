"""Saved-document relationships, detached validation, and no-I/O replay."""
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import xmfa_formats, xmfa_format_contracts
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
from gene_annotation_episode.xmfa_format_contracts import validate_xmfa_document, CALLER_ERROR_CODES


TEXT = ('#FormatVersion Mauve1\n#Sequence1File\tinput.fa\n#Sequence1Entry\t1\n'
        '>1:1-3 + retained comment\nAC\nG\n>2:0-0 -\n---\n=\n'
        '>1:4-5 -\nGT\n=')


def read(text=TEXT, encoding='ascii'):
    data = text.encode(encoding)
    artifact = {'raw_artifact_ref': 'native.xmfa', 'source_ref': 'supplied',
                'sha256': hashlib.sha256(data).hexdigest()}
    return parse_mauve_xmfa(data, artifact=artifact, dialect='mauve1', alphabet='dna', encoding=encoding)


def set_at(value, path, new):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = new


@pytest.mark.parametrize(('path', 'new'), [
    (['schema_version'], 'unknown'), (['document_id'], 'foreign'),
    (['dialect'], 'general'), (['alphabet'], 'rna'), (['encoding'], 'latin1'),
    (['completeness'], 'partial'), (['format_version_token'], None),
    (['metadata'], ()), (['blocks'], ()), (['unparsed'], ()),
    (['metadata', 0, 'metadata_index'], True), (['metadata', 1, 'metadata_index'], 7),
    (['metadata', 1, 'kind'], 'comment'), (['metadata', 1, 'value_token'], 'other.fa'),
    (['metadata', 1, 'member_number', 'value'], True),
    (['metadata', 2, 'integer_value', 'value'], 2),
    (['metadata', 2, 'integer_value', 'state'], 'incompatible'),
    (['metadata', 2, 'integer_value'], None),
    (['blocks', 0, 'block_index'], 1), (['blocks', 0, 'alignment_column_count'], 4),
    (['blocks', 0, 'alignment_column_count'], 3.0),
    (['blocks', 0, 'completeness'], 'unknown'), (['blocks', 0, 'terminated'], 1),
    (['blocks', 0, 'terminator_token'], None), (['blocks', 0, 'terminator_location'], None),
    (['blocks', 0, 'records'], []),
    (['blocks', 0, 'records', 0, 'record_index'], 1),
    (['blocks', 0, 'records', 0, 'sequence'], 'ATG'),
    (['blocks', 0, 'records', 0, 'sequence_parts'], ()),
    (['blocks', 0, 'records', 0, 'gapped_character_count'], 4),
    (['blocks', 0, 'records', 0, 'nongap_character_count'], 2),
    (['blocks', 0, 'records', 0, 'gapped_character_count'], True),
    (['blocks', 0, 'records', 0, 'span_matches_nongap'], 1),
    (['blocks', 0, 'records', 0, 'interval_0based_half_open'], [1, 4]),
    (['blocks', 0, 'records', 0, 'interval_0based_half_open'], (0, 3)),
    (['blocks', 0, 'records', 0, 'interval_0based_half_open'], [False, 3]),
    (['blocks', 0, 'records', 0, 'coordinate_state'], 'absent_zero'),
    (['blocks', 0, 'records', 0, 'sequence_state'], 'incompatible'),
    (['blocks', 0, 'records', 0, 'member_number', 'value'], 1.0),
    (['blocks', 0, 'records', 0, 'start_1based', 'raw_token'], '2'),
    (['blocks', 0, 'records', 0, 'start_1based', 'state'], 'failed'),
    (['blocks', 0, 'records', 0, 'strand'], '-'),
    (['blocks', 0, 'records', 0, 'comment_token'], 'changed'),
    (['blocks', 0, 'records', 1, 'interval_0based_half_open'], [0, 0]),
    (['blocks', 0, 'records', 1, 'sequence_state'], 'incompatible'),
])
def test_corrupt_saved_fields_are_rejected_with_finite_xmfa_errors(path, new):
    doc = read()['value']
    set_at(doc, path, new)
    with pytest.raises(ValueError) as error:
        validate_xmfa_document(doc)
    assert str(error.value).removeprefix('xmfa_') in CALLER_ERROR_CODES
    assert str(error.value).startswith('xmfa_')


@pytest.mark.parametrize('path', [
    [], ['artifact'], ['metadata', 0], ['metadata', 1, 'member_number'],
    ['metadata', 0, 'source_location'], ['blocks', 0],
    ['blocks', 0, 'records', 0], ['blocks', 0, 'records', 0, 'sequence_parts', 0],
    ['blocks', 0, 'records', 0, 'header_location'],
])
@pytest.mark.parametrize('mutation', ['extra', 'missing'])
def test_every_saved_record_is_closed(path, mutation):
    doc = read()['value']
    target = doc
    for key in path:
        target = target[key]
    if mutation == 'extra':
        target['unexpected'] = 'value'
    else:
        del target[next(iter(target))]
    with pytest.raises(ValueError, match='^xmfa_'):
        validate_xmfa_document(doc)


@pytest.mark.parametrize('bad', [None, [], 'document', 2, False])
def test_top_level_wrong_shape(bad):
    with pytest.raises(ValueError, match='^xmfa_document_shape_invalid$'):
        validate_xmfa_document(bad)


@pytest.mark.parametrize(('path', 'field', 'change'), [
    (['metadata', 0, 'source_location'], 'line_start_1based', 2),
    (['metadata', 0, 'source_location'], 'byte_start_0based', -1),
    (['metadata', 0, 'source_location'], 'xml_path', '/invented'),
    (['metadata', 0, 'source_location'], 'line_start_1based', None),
    (['blocks', 0, 'source_location'], 'byte_start_0based', 0),
    (['blocks', 0, 'source_location'], 'byte_end_0based_exclusive', 10000),
    (['blocks', 0, 'records', 0, 'source_location'], 'byte_end_0based_exclusive', 10000),
    (['blocks', 0, 'records', 0, 'source_location'], 'line_end_1based_inclusive', 8),
    (['blocks', 0, 'records', 0, 'header_location'], 'line_end_1based_inclusive', 99),
    (['blocks', 0, 'records', 0, 'sequence_parts', 0, 'source_location'], 'byte_end_0based_exclusive', 1000),
    (['blocks', 0, 'records', 0, 'sequence_parts', 0, 'source_location'], 'line_start_1based', 2),
    (['blocks', 0, 'records', 0, 'sequence_parts', 0, 'source_location'], 'artifact', {'raw_artifact_ref':'x', 'source_ref':'y', 'sha256':'0'*64}),
])
def test_locations_require_atomic_byte_width_containment_and_artifact_identity(path, field, change):
    doc = read()['value']
    set_at(doc, path + [field], change)
    with pytest.raises(ValueError, match='^xmfa_'):
        validate_xmfa_document(doc)


def test_shifted_numeric_location_is_rejected_even_inside_its_header():
    doc = read()['value']
    loc = doc['blocks'][0]['records'][0]['start_1based']['source_location']
    loc['byte_start_0based'] += 1
    loc['byte_end_0based_exclusive'] += 1
    with pytest.raises(ValueError, match='^xmfa_native_token_conflict$'):
        validate_xmfa_document(doc)


def test_record_order_cannot_change_even_after_indices_are_rewritten():
    doc = read()['value']
    rows = doc['blocks'][0]['records']
    rows.reverse()
    for index, row in enumerate(rows):
        row['record_index'] = index
    with pytest.raises(ValueError, match='^xmfa_'):
        validate_xmfa_document(doc)


def test_sequence_part_order_cannot_change_even_if_sequence_is_rewritten():
    doc = read()['value']
    row = doc['blocks'][0]['records'][0]
    row['sequence_parts'].reverse()
    row['sequence'] = 'GAC'
    with pytest.raises(ValueError, match='^xmfa_'):
        validate_xmfa_document(doc)


def test_interleaved_metadata_may_not_overlap_a_sequence_line():
    doc = read()['value']
    meta = doc['metadata'][1]
    loc = meta['source_location']
    row_loc = doc['blocks'][0]['records'][0]['sequence_parts'][0]['source_location']
    offset = row_loc['byte_start_0based'] - loc['byte_start_0based']
    for item in (loc, meta['member_number']['source_location']):
        item['byte_start_0based'] += offset
        item['byte_end_0based_exclusive'] += offset
        item['line_start_1based'] = item['line_end_1based_inclusive'] = row_loc['line_start_1based']
    with pytest.raises(ValueError, match='^xmfa_'):
        validate_xmfa_document(doc)


def test_unknown_version_cannot_reuse_previously_trusted_coordinates():
    doc = read()['value']
    doc['metadata'][0]['raw_line'] = '#FormatVersion Mauve2'
    doc['metadata'][0]['value_token'] = doc['format_version_token'] = 'Mauve2'
    with pytest.raises(ValueError, match='^xmfa_coordinate_state_conflict$'):
        validate_xmfa_document(doc)


def test_changed_native_header_is_rejected_by_redundant_token_check():
    doc = read()['value']
    doc['blocks'][0]['records'][0]['header_token'] = '>1:2-4 + retained comment'
    with pytest.raises(ValueError, match='^xmfa_native_token_conflict$'):
        validate_xmfa_document(doc)


def test_unparsed_references_and_closed_shape_are_checked():
    doc = read('garbage\n' + TEXT)['value']
    validate_xmfa_document(doc)
    for field, new in [('block_index', 0), ('record_index', 0), ('extra', 1)]:
        corrupt = deepcopy(doc)
        corrupt['unparsed'][0][field] = new
        with pytest.raises(ValueError, match='^xmfa_'):
            validate_xmfa_document(corrupt)


def document_with_referenced_unparsed(*, zero=False, terminated=True):
    # An alternate partial saved reader retained an unknown line separately.
    # This is a contract fixture, not output claimed for the current parser.
    source = ('#FormatVersion Mauve1\n>1:' + ('0-0' if zero else '1-2') + ' +\n'
              + ('-\n!\n-\n' if zero else 'A\n!\nC\n')
              + '>2:1-2 +\nAC\n' + ('=' if terminated else ''))
    doc = read(source)['value']
    row = doc['blocks'][0]['records'][0]
    part = row['sequence_parts'].pop(1)
    doc['unparsed'] = [{'raw_line': part['text'], 'source_location': part['source_location'],
                        'block_index': 0, 'record_index': 0}]
    row.update(sequence='--' if zero else 'AC', gapped_character_count=2,
               nongap_character_count=0 if zero else 2, sequence_state='dna_iupac',
               coordinate_state='incompatible', interval_0based_half_open=None,
               span_matches_nongap=True)
    doc['blocks'][0]['alignment_column_count'] = 2
    return doc


@pytest.mark.parametrize('zero', [False, True])
@pytest.mark.parametrize('terminated', [False, True])
def test_referenced_unparsed_contract_shapes_preserve_independent_rows(zero, terminated):
    doc = document_with_referenced_unparsed(zero=zero, terminated=terminated)
    assert validate_xmfa_document(json.loads(json.dumps(doc))) == doc
    assert doc['blocks'][0]['records'][1]['coordinate_state'] == 'present'
    assert doc['blocks'][0]['completeness'] == ('partial' if terminated else 'truncated')
    corrupt = deepcopy(doc)
    row = corrupt['blocks'][0]['records'][0]
    row['coordinate_state'] = 'absent_zero' if zero else 'present'
    row['interval_0based_half_open'] = None if zero else [0, 2]
    with pytest.raises(ValueError, match='^xmfa_coordinate_state_conflict$'):
        validate_xmfa_document(corrupt)


@pytest.mark.parametrize(('block_index', 'record_index'), [(None, 0), (1, 0), (-1, 0),
    (False, 0), (0, 7), (0, -1), (0, None), (None, None)])
def test_unparsed_references_cannot_escape_their_actual_containing_row(block_index, record_index):
    doc = document_with_referenced_unparsed()
    doc['unparsed'][0].update(block_index=block_index, record_index=record_index)
    with pytest.raises(ValueError, match='^xmfa_'):
        validate_xmfa_document(doc)


def test_block_only_unparsed_is_valid_between_record_ranges():
    doc = read('#FormatVersion Mauve1\n>1:1-2 +\nAC\n!\n>2:1-2 +\nAC\n=')['value']
    row = doc['blocks'][0]['records'][0]
    part = row['sequence_parts'].pop()
    doc['unparsed'] = [{'raw_line': '!', 'source_location': part['source_location'],
                        'block_index': 0, 'record_index': None}]
    row.update(sequence='AC', gapped_character_count=2, nongap_character_count=2,
               coordinate_state='present', interval_0based_half_open=[0, 2],
               span_matches_nongap=True, sequence_state='dna_iupac')
    last = row['sequence_parts'][-1]['source_location']
    for key in ('byte_end_0based_exclusive', 'line_end_1based_inclusive'):
        row['source_location'][key] = last[key]
    doc['blocks'][0]['alignment_column_count'] = 2
    assert validate_xmfa_document(doc) == doc
    doc['blocks'][0]['completeness'] = 'complete'
    with pytest.raises(ValueError, match='^xmfa_completeness_conflict$'):
        validate_xmfa_document(doc)


def test_unterminated_block_end_is_last_real_atomic_source_location():
    doc = read(TEXT[:-1])['value']
    assert doc['completeness'] == 'truncated'
    doc['blocks'][-1]['source_location']['byte_end_0based_exclusive'] += 1000
    with pytest.raises(ValueError, match='^xmfa_source_text_location_conflict$'):
        validate_xmfa_document(doc)


@pytest.mark.parametrize('text', [TEXT, '#FormatVersion Mauve1\n',
    '#FormatVersion Future\n>1:1-1 +\nA\n=',
    '#FormatVersion Mauve1\n>1:1-3 +\nA.\n',
    '#FormatVersion Mauve1\n>malformed\nACT\n='])
def test_json_roundtrip_validation_returns_detached_document(text):
    doc = read(text)['value']
    saved = json.loads(json.dumps(doc, allow_nan=False))
    snapshot = deepcopy(saved)
    validated = validate_xmfa_document(saved)
    assert validated == saved == snapshot and validated is not saved
    validated['metadata'][0]['source_location']['artifact']['source_ref'] = 'changed copy'
    assert saved == snapshot


def test_parser_and_saved_validator_run_with_io_network_native_and_dynamic_imports_disabled(monkeypatch):
    # Acquire/serialize fixtures before disabling all side-effect entrypoints.
    data = TEXT.encode()
    artifact = {'raw_artifact_ref': 'native.xmfa', 'source_ref': 'supplied',
                'sha256': hashlib.sha256(data).hexdigest()}
    saved = json.loads(json.dumps(read()['value']))
    def forbidden(*args, **kwargs):
        raise AssertionError('I/O, acquisition, native execution, or model import was attempted')
    with monkeypatch.context() as patch:
        patch.setattr(xmfa_formats, 'parse_mauve_xmfa', forbidden)
        for obj, name in [(builtins, 'open'), (io, 'open'), (os, 'open'), (os, 'system'),
                          (Path, 'open'), (Path, 'read_text'), (Path, 'read_bytes'),
                          (socket, 'socket'), (socket, 'create_connection'),
                          (subprocess, 'Popen'), (subprocess, 'run'),
                          (subprocess, 'check_output'), (builtins, '__import__')]:
            patch.setattr(obj, name, forbidden)
        parsed = parse_mauve_xmfa(data, artifact=artifact, dialect='mauve1', alphabet='dna', encoding='ascii')
        assert parsed['value'] == saved
        assert validate_xmfa_document(saved) == saved


def test_validation_never_uses_text_parser_or_mutates_saved_values(monkeypatch):
    saved = json.loads(json.dumps(read()['value']))
    snapshot = deepcopy(saved)
    monkeypatch.setattr(xmfa_formats, 'parse_mauve_xmfa', lambda *a, **k: pytest.fail('parser replay'))
    validated = xmfa_format_contracts.validate_xmfa_document(saved)
    assert validated == snapshot and saved == snapshot
