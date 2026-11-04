"""Native official sidecar bytes plus explicitly synthetic format corruption."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.mauve_backbone_formats import parse_mauve_backbone, parse_mauve_bbcols
from gene_annotation_episode.mauve_backbone_contracts import (
    BACKBONE_DIALECT, BBCOLS_DIALECT, SIDECAR_NAMESPACE,
    validate_mauve_backbone_document, validate_mauve_bbcols_document,
)

NATIVE = Path(__file__).parents[1] / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'
HEADER = b'seq0_leftend\tseq0_rightend\tseq1_leftend\tseq1_rightend\n'


def artifact(data, name='synthetic-sidecar'):
    return {'raw_artifact_ref': 'fixture:' + name, 'source_ref': 'fixture-source:' + name,
        'sha256': hashlib.sha256(data).hexdigest()}


def backbone(data=None):
    if data is None:
        data = (NATIVE / 'separate.xmfa.backbone').read_bytes()
        name = 'official:separate.xmfa.backbone'
    else:
        name = 'synthetic:backbone'
    return parse_mauve_backbone(data, artifact=artifact(data, name), dialect=BACKBONE_DIALECT, encoding='ascii')


def bbcols(data=None):
    if data is None:
        data = (NATIVE / 'separate.xmfa.bbcols').read_bytes()
        name = 'official:separate.xmfa.bbcols'
    else:
        name = 'synthetic:bbcols'
    return parse_mauve_bbcols(data, artifact=artifact(data, name), dialect=BBCOLS_DIALECT, encoding='ascii')


def members(*indices):
    return [{'namespace': SIDECAR_NAMESPACE, 'index': i} for i in indices]


def selection(document, *, chosen=None, rows=None, threshold=1, denominator='none', fraction=False, all_rows=True):
    family = 'backbone' if 'columns' in document else 'bbcols'
    if chosen is None:
        chosen = members(0, 1, 2)
    value = {'schema_version': 'mauve_' + family + '_selection_v1',
        'document_id': document['document_id'], 'population_id': 'synthetic-explicit-selection',
        'members': chosen, 'row_indices': list(range(len(document['rows']))) if rows is None else rows,
        'minimum_selected_multiplicity': threshold,
        'population_scope': 'all_observed_document_rows' if all_rows else 'selected_rows', 'evidence': []}
    value['denominator' if family == 'backbone' else 'calculate_bound_block_fraction'] = denominator if family == 'backbone' else fraction
    return value


def assert_locations(document, data):
    def visit(value):
        if type(value) is dict:
            if 'source_location' in value:
                loc = value['source_location']
                assert loc['artifact'] == document['artifact']
                raw = next((value[k] for k in ('raw_line', 'raw_token') if k in value), None)
                if raw is not None:
                    assert data[loc['byte_start_0based']:loc['byte_end_0based_exclusive']].decode(document['encoding']) == raw
            for x in value.values(): visit(x)
        elif type(value) is list:
            for x in value: visit(x)
    visit(document)


def test_official_backbone_native_endpoints_and_bytes_match_receipt():
    raw = (NATIVE / 'separate.xmfa.backbone').read_bytes()
    receipts = json.loads((NATIVE.parent / 'SOURCE_RECEIPTS.json').read_text())
    receipt = next(r for r in receipts if r['path'] == 'native_examples/separate.xmfa.backbone')
    assert hashlib.sha256(raw).hexdigest() == receipt['sha256'] == '30e7ac0288891dcfa70acf61d1bf3beaf643d2a5da5ead2b60520a8f543807ea'
    result = backbone(); assert result['status'] == 'ok'
    doc = result['value']; assert_locations(doc, raw)
    assert [p['interval_0based_half_open'] for p in doc['rows'][0]['pairs']] == [[18, 50], [0, 31], None]
    assert [p['state'] for p in doc['rows'][0]['pairs']] == ['present', 'present', 'absent_zero']
    assert [p['strand'] for p in doc['rows'][1]['pairs']] == ['-', '+', '-']
    assert [p['native_left']['value'] for p in doc['rows'][1]['pairs']] == [-1, 32, -1]
    assert validate_mauve_backbone_document(doc) == doc


@pytest.mark.parametrize('endpoints,state,interval,strand', [
    (b'1\t1', 'present', [0, 1], '+'), (b'-1\t-1', 'present', [0, 1], '-'),
    (b'0\t0', 'absent_zero', None, None), (b'0\t1', 'incompatible', None, None),
    (b'1\t0', 'incompatible', None, None), (b'-1\t2', 'incompatible', None, None),
    (b'1\t-2', 'incompatible', None, None), (b'5\t2', 'incompatible', None, None),
    (b'-5\t-2', 'incompatible', None, None), (b'NaN\t2', 'incompatible', None, None),
    (b'1.5\t2', 'incompatible', None, None), (b'1e0\t2', 'incompatible', None, None),
    (b'1.0\t2', 'incompatible', None, None), (b'NA\t2', 'incompatible', None, None),
    (b'1', 'missing', None, None),
])
def test_endpoint_states_preserve_invalid_tokens(endpoints, state, interval, strand):
    raw = b'seq0_leftend seq0_rightend\n' + endpoints + b'\n'
    result = backbone(raw); doc = result['value']; pair = doc['rows'][0]['pairs'][0]
    assert (pair['state'], pair['interval_0based_half_open'], pair['strand']) == (state, interval, strand)
    assert pair['native_left']['raw_token'] == endpoints.split()[0].decode()
    assert result['status'] == ('ok' if state in ('present', 'absent_zero') else 'partial')
    assert_locations(doc, raw)


def test_one_incomplete_row_retains_unaffected_following_row_and_native_number():
    result = backbone(HEADER + b'1\n-1 -4 2 5\n')
    assert result['status'] == 'partial'
    first, second = result['value']['rows']
    assert first['pairs'][0]['native_left']['value'] == 1
    assert first['pairs'][0]['native_right'] is None
    assert second['completeness'] == 'complete'
    assert second['pairs'][1]['interval_0based_half_open'] == [1, 5]


def test_headers_use_labels_not_adjacency_and_preserve_intermediate_spelling():
    raw = b'seq_1_rightend seq_0_leftend seq_1_leftend seq_0_rightend\r\n9 -2 7 -5\r\n'
    doc = backbone(raw)['value']; assert_locations(doc, raw)
    assert [p['member_index_0based'] for p in doc['rows'][0]['pairs']] == [1, 0]
    assert [p['interval_0based_half_open'] for p in doc['rows'][0]['pairs']] == [[6, 9], [1, 5]]
    assert doc['columns'][0]['raw_token'] == 'seq_1_rightend'


@pytest.mark.parametrize('header', [b'seq0_leftend seq0_leftend seq0_rightend',
    b'seq0_leftend seq1_rightend', b'seqx_leftend seqx_rightend', b'seq0_leftend broken'])
def test_unresolved_header_never_chooses_arbitrary_pair(header):
    result = backbone(header + b'\n1 2 3\n')
    assert result['status'] == 'partial'
    assert all(p['state'] == 'incompatible' for p in result['value']['rows'][0]['pairs'])
    assert all(p['interval_0based_half_open'] is None for p in result['value']['rows'][0]['pairs'])


def test_extra_native_tokens_are_retained_and_diagnosed():
    raw = b'seq0_leftend seq0_rightend\n1 4 99 100\n'
    result = backbone(raw)
    assert result['status'] == 'partial'
    assert [x['raw_line'] for x in result['value']['rows'][0]['extra_tokens']] == ['99', '100']
    assert_locations(result['value'], raw)


@pytest.mark.parametrize('raw', [b'', b'\n\t\n', b'1 2 3 4\n', b'#FormatVersion Mauve1\n'])
def test_backbone_without_member_header_is_not_zero(raw):
    result = backbone(raw)
    assert result['status'] == 'invalid' and result['value'] is None


def test_header_only_has_unknown_scientific_population():
    assert backbone(HEADER)['value']['completeness'] == 'unknown'


@pytest.mark.parametrize('family', ['backbone', 'bbcols'])
@pytest.mark.parametrize('bad', ['wrong_bytes_type', 'bad_artifact', 'wrong_encoding', 'wrong_dialect'])
def test_caller_contract_errors_have_stable_prefix(family, bad):
    parser = parse_mauve_backbone if family == 'backbone' else parse_mauve_bbcols
    raw = HEADER if family == 'backbone' else b'0 1 4 0\n'
    args = {'artifact': artifact(raw), 'dialect': BACKBONE_DIALECT if family == 'backbone' else BBCOLS_DIALECT, 'encoding': 'ascii'}
    if bad == 'wrong_bytes_type': raw = raw.decode()
    elif bad == 'bad_artifact': args['artifact']['extra'] = True
    elif bad == 'wrong_encoding': args['encoding'] = 'utf-16'
    else: args['dialect'] = 'guess'
    with pytest.raises(ValueError, match='^mauve_' + family + '_'):
        parser(raw, **args)


@pytest.mark.parametrize('family', ['backbone', 'bbcols'])
def test_hash_and_encoding_data_failures_return_invalid(family):
    parser = parse_mauve_backbone if family == 'backbone' else parse_mauve_bbcols
    dialect = BACKBONE_DIALECT if family == 'backbone' else BBCOLS_DIALECT
    raw = b'\xff\n'; a = artifact(raw)
    result = parser(raw, artifact=a, dialect=dialect, encoding='ascii')
    assert result['value'] is None and result['diagnostics'][0]['code'].endswith('encoding_invalid')
    a['sha256'] = '0' * 64
    result = parser(raw, artifact=a, dialect=dialect, encoding='ascii')
    assert result['value'] is None and result['diagnostics'][0]['code'].endswith('digest_mismatch')


@pytest.mark.parametrize('change', ['extra_field', 'wrong_id', 'wrong_artifact', 'bad_location',
    'wrong_interval', 'wrong_strand', 'wrong_state', 'wrong_native_value', 'duplicate_row_index'])
def test_saved_backbone_document_corruption_is_rejected(change):
    doc = backbone()['value']; pair = doc['rows'][0]['pairs'][0]
    if change == 'extra_field': doc['confidence'] = 1
    elif change == 'wrong_id': doc['document_id'] = 'other'
    elif change == 'wrong_artifact': pair['source_location']['artifact']['sha256'] = '0' * 64
    elif change == 'bad_location': pair['source_location']['byte_start_0based'] = 0
    elif change == 'wrong_interval': pair['interval_0based_half_open'][0] = 19
    elif change == 'wrong_strand': pair['strand'] = '+'
    elif change == 'wrong_state': pair['state'] = 'absent_zero'
    elif change == 'wrong_native_value': pair['native_left']['value'] = -20
    else: doc['rows'][1]['row_index'] = 0
    with pytest.raises(ValueError, match='^mauve_backbone_'):
        validate_mauve_backbone_document(doc)


def test_saved_document_validation_is_detached_and_does_not_parse(monkeypatch):
    b = backbone()['value']; cols = bbcols()['value']; original = deepcopy(b)
    def forbidden(*args, **kwargs): raise AssertionError('native parser called')
    monkeypatch.setattr('gene_annotation_episode.mauve_backbone_formats.parse_mauve_backbone', forbidden)
    monkeypatch.setattr('gene_annotation_episode.mauve_backbone_formats.parse_mauve_bbcols', forbidden)
    result = validate_mauve_backbone_document(b)
    result['rows'].clear()
    assert b == original
    assert validate_mauve_bbcols_document(cols) == cols


def test_saved_backbone_cannot_reassign_endpoint_from_another_header_column():
    doc = backbone(b'seq0_leftend seq0_rightend seq1_leftend seq1_rightend\n1 5 2 6\n')['value']
    left = deepcopy(doc['rows'][0]['pairs'][1]['native_left'])
    pair = doc['rows'][0]['pairs'][0]
    pair.update(native_left=left, interval_0based_half_open=[1, 5])
    pair['source_location'] = deepcopy(doc['rows'][0]['source_location'])
    with pytest.raises(ValueError, match='mauve_backbone_'):
        validate_mauve_backbone_document(doc)


def test_saved_bbcols_cannot_swap_equal_valued_native_token_positions():
    doc = bbcols(b'0 1 1 0\n')['value']; row = doc['rows'][0]
    row['native_left_column_1based'], row['native_column_count'] = row['native_column_count'], row['native_left_column_1based']
    with pytest.raises(ValueError, match='mauve_bbcols_'):
        validate_mauve_bbcols_document(doc)


def test_native_integer_malformation_preserves_huge_exponent_without_large_integer_conversion():
    raw = b'1e99999999'
    b = backbone(b'seq0_leftend seq0_rightend\n' + raw + b' 2\n')
    cols = bbcols(b'0 1 ' + raw + b' 0\n')
    assert b['status'] == cols['status'] == 'partial'
    assert b['value']['rows'][0]['pairs'][0]['native_left']['raw_token'] == raw.decode()
    assert cols['value']['rows'][0]['native_column_count']['raw_token'] == raw.decode()


@pytest.mark.parametrize('family', ['backbone', 'bbcols'])
@pytest.mark.parametrize('bad', [None, [], True, 'record', 1, {'unexpected': 'field'}])
def test_document_shape_errors_always_raise_stable_value_error(family, bad):
    validator = validate_mauve_backbone_document if family == 'backbone' else validate_mauve_bbcols_document
    with pytest.raises(ValueError, match='^mauve_' + family + '_'):
        validator(bad)
