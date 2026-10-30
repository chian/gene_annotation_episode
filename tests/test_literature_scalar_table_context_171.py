"""Synthetic field-boundary and genuine-interval contrasts; no paper data."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_source_fields import read_source_number


def selected(text, token, *, occurrence=0, full_witness=False):
    offset = -1
    for _ in range(occurrence + 1):
        offset = text.index(token, offset + 1)
    left = 0 if full_witness else offset
    quote = text if full_witness else token
    return {'witness': {'source_ref': 'source_synthetic_table_context_171',
        'representation': 'original', 'start': len(text[:left].encode('utf-8')),
        'end': len(text[:left + len(quote)].encode('utf-8')), 'quote': quote},
        'number_start': offset - left, 'number_end': offset - left + len(token)}


def scalar(text, token, *, role='condition', occurrence=0, full_witness=False):
    selection = selected(text, token, occurrence=occurrence, full_witness=full_witness)
    before = deepcopy(selection)
    content = text.encode('utf-8')
    artifact = 'artifact_' + hashlib.sha256(content).hexdigest()
    sources = _Sources(lambda *_: {'artifact_ref': artifact, 'content': content})
    value = read_source_number(selection, sources=sources, role=role)
    assert selection == before
    assert value['selector']['witness']['quote'] == selection['witness']['quote']
    assert value['selector']['witness']['artifact_ref'] == artifact
    return value


def test_minimal_separate_signed_cell_is_not_nominal_interval():
    text = '<table><tr><td>10</td><td>-2 ± 0.2</td></tr></table>'
    assert scalar(text, '10')['value'] == 10
    assert scalar(text, '-2')['value'] == -2
    assert scalar(text, '0.2', role='spread')['value'] == .2


@pytest.mark.parametrize('left,right,closing', [
    ('<td>', '</td><td>', '</td>'), ('<th>', '</th><td>', '</td>'),
    ('<td>', '</td></tr><tr><td>', '</td>'),
    ('<TH class="nominal">', '</TH><TD class="measured">', '</TD>'),
    ('<td><em>', '</em></td><td><strong>', '</strong></td>'),
])
@pytest.mark.parametrize('minus', ['-', '−'])
@pytest.mark.parametrize('full_witness', [False, True])
def test_distinct_structural_fields_preserve_signed_points(left, right, closing, minus, full_witness):
    text = '<table><tr>' + left + '10' + right + minus + '2' + closing + '</tr></table>'
    assert scalar(text, '10', full_witness=full_witness)['relation'] == 'point'
    value = scalar(text, minus + '2', full_witness=full_witness)
    assert (value['value'], value['raw_number'], value['relation']) == (-2, minus + '2', 'point')


@pytest.mark.parametrize('body', ['10–20', '10—20', '10-20', '10−20', '10 to 20',
    '<em>10</em>–<strong>20</strong>', '10<br/>–20', '10–<br/>20'])
@pytest.mark.parametrize('token', ['10', '20'])
def test_actual_intervals_in_one_field_reject_both_endpoints(body, token):
    with pytest.raises(ExperimentalContractError, match='interval_source_number_unsupported'):
        scalar('<table><tr><td>' + body + '</td></tr></table>', token)


@pytest.mark.parametrize('body,token', [
    ('-<br/>2', '2'), ('−<br/>2', '2'), ('+<br/>2', '2'),
    ('.<br/>2', '2'), ('1<br/>.2', '1'), ('1<br/>.2', '.2'),
    ('1.2<br/>e-3', '1.2'), ('1.2e-<br/>3', '3'),
    ('<em>-</em><strong>2</strong>', '2'), ('-2', '2'),
    ('10</td><td>-2', '2'),
])
def test_clipped_sign_decimal_exponent_remain_rejected(body, token):
    with pytest.raises(ExperimentalContractError, match='partial_source_numeric_token'):
        scalar('<td>' + body + '</td>', token)


@pytest.mark.parametrize('body,role,code', [
    ('about<br/>2', 'condition', 'approximate_source_number_unsupported'),
    ('not below<br/>2', 'rate', 'negated_source_comparator_unsupported'),
    ('above<br/>2', 'condition', 'lower_bound_source_number_unsupported'),
    ('between<br/>2 and 3', 'condition', 'interval_source_number_unsupported'),
    ('from<br/>2 to 3', 'condition', 'interval_source_number_unsupported'),
    ('LOD<br/>2', 'rate', 'untyped_limit_source_number'),
    ('±<br/>2', 'rate', 'uncertainty_is_not_rate_point'),
])
def test_qualifier_guards_are_not_trimmed_by_numeric_field_fix(body, role, code):
    with pytest.raises(ExperimentalContractError) as caught:
        scalar('<td>' + body + '</td><td>-5</td>', '2', role=role)
    assert caught.value.code == code


@pytest.mark.parametrize('marker,relation', [('&lt;', 'lt'), ('≤', 'le'), ('at most ', 'le')])
def test_upper_limit_role_and_exact_bound_survive(marker, relation):
    text = '<td>' + marker + '<br/>2</td><td>-5</td>'
    assert scalar(text, '2', role='rate')['relation'] == relation
    for role in ('condition', 'spread'):
        with pytest.raises(ExperimentalContractError, match='plain_source_point_required'):
            scalar(text, '2', role=role)


def test_repeated_cells_preserve_actual_selected_offsets_and_source_bytes():
    text = '<table><tr><td>10</td><td>-2</td><td>10</td><td>−2</td></tr></table>'
    first = scalar(text, '10')
    second = scalar(text, '10', occurrence=1)
    assert first['value'] == second['value'] == 10
    assert first['selector']['witness']['start'] != second['selector']['witness']['start']
    assert first['selector']['witness']['artifact_ref'] == second['selector']['witness']['artifact_ref']


@pytest.mark.parametrize('text', ['<td>10–20</td><td>-2</td>',
    '<td>-2</td><td>10–20</td>', '<td>10 to 20</td><td>-2</td>'])
def test_neighbor_field_does_not_excuse_interval_in_selected_field(text):
    with pytest.raises(ExperimentalContractError, match='interval_source_number_unsupported'):
        scalar(text, '10')


def test_encoded_literal_tags_are_not_fabricated_as_inline_markup():
    text = '<td>10 &lt;b&gt;-&lt;/b&gt; 20</td>'
    # The literal angle-bracket text is not HTML formatting around a dash.
    # Decoding before recognizing actual tags would manufacture an interval.
    assert scalar(text, '10')['relation'] == 'point'
    # Its literal trailing '>' remains visible to the unchanged bound guard.
    with pytest.raises(ExperimentalContractError, match='lower_bound_source_number_unsupported'):
        scalar(text, '20')
