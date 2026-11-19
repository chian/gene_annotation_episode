"""Synthetic structural boundaries through the real scalar readers."""
from copy import deepcopy

import pytest

from gene_annotation_episode.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.partner_presence_evidence.literature_assay_inputs import _Sources
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.literature_partner_source_fields import (
    convert_source_number, read_source_number, read_source_rate_unit, validate_source_spread_unit,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import partner_cells_schema



SOURCE = 'source_' + 'a' * 24
ARTIFACT = 'artifact_' + 'b' * 64
FORM = obj({'measurements': partner_cells_schema()})


def sources(text):
    return _Sources(lambda reference, representation: {'artifact_ref': ARTIFACT, 'content': text.encode()})


def witness(text, quote, *, reference=SOURCE):
    start = text.encode().index(quote.encode())
    return {'source_ref': reference, 'representation': 'original', 'start': start,
        'end': start + len(quote.encode()), 'quote': quote}


def selector(text, token, *, quote=None, reference=SOURCE):
    selected = witness(text, token if quote is None else quote, reference=reference)
    start = selected['quote'].index(token)
    return {'witness': selected, 'number_start': start, 'number_end': start + len(token)}


def number(text, token, *, role='rate', quote=None):
    return read_source_number(selector(text, token, quote=quote), sources=sources(text), role=role)


@pytest.mark.parametrize('text,token', [
    ('<table><tr><td>Partner</td><td>7</td></tr></table>', '7'),
    ('<TABLE><TR><TH>Partner</TH><TD class="rate">7</TD></TR></TABLE>', '7'),
    ('<table><tr><td>1</td><td>2</td></tr></table>', '1'),
    ('<table><tr><td>1</td><td>2</td></tr></table>', '2'),
    ('<p>Label</p><p>7</p>', '7'),
    ('<div>Label</div><div>7</div>', '7'),
    ('Label<br/>7<br/>9', '7'),
    ('Label<break/>7', '7'),
])
def test_structural_separators_do_not_join_adjacent_tokens(text, token):
    result = number(text, token)
    assert (result['raw_number'], result['value'], result['relation']) == (token, float(token), 'point')


@pytest.mark.parametrize('marker,relation', [('&lt;', 'lt'), ('&lt;=', 'le'), ('≤', 'le'),
    ('less than', 'lt'), ('at most', 'le')])
@pytest.mark.parametrize('separator', ['<br/>', '<p>', '<div>', '<em>'])
def test_same_cell_qualifiers_survive_structural_and_inline_markup(marker, relation, separator):
    text = '<table><tr><td>' + marker + (' ' if marker[-1:].isalpha() else '') + separator + '7</td></tr></table>'
    assert number(text, '7')['relation'] == relation


@pytest.mark.parametrize('text,role,code', [
    ('<td>not below<br/>7</td>', 'rate', 'negated_source_comparator_unsupported'),
    ('<td>above<br/>7</td>', 'rate', 'lower_bound_source_number_unsupported'),
    ('<td>about<br/>7</td>', 'rate', 'approximate_source_number_unsupported'),
    ('<td>SD=<br/>7</td>', 'rate', 'uncertainty_is_not_rate_point'),
    ('<td>±<br/>7</td>', 'rate', 'uncertainty_is_not_rate_point'),
    ('<td>CV=<br/>7</td>', 'spread', 'relative_spread_unit_unsupported'),
    ('<td>7<br/>%</td>', 'spread', 'relative_spread_unit_unsupported'),
    ('<td>from<br/>7 to 9</td>', 'rate', 'interval_source_number_unsupported'),
])
def test_structural_whitespace_does_not_erase_existing_scalar_guards(text, role, code):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, '7', role=role)
    assert caught.value.code == code


@pytest.mark.parametrize('text', ['<td>between<br>1 and<br>2 nM</td>',
    '<td>between 1<br>and 2 nM</td>', '<td>between<p>1 and<p>2 nM</td>'])
@pytest.mark.parametrize('token', ['1', '2'])
@pytest.mark.parametrize('role', ['rate', 'spread', 'condition'])
def test_structural_markup_does_not_manufacture_an_interval_scope_boundary(text, token, role):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, token, role=role)
    assert caught.value.code == 'interval_source_number_unsupported'


@pytest.mark.parametrize('text,token', [
    ('<em>1</em><b>2</b>', '1'), ('<em>1</em><b>2</b>', '2'),
    ('<td><em>1</em><b>2</b></td>', '2'),
    ('<td><em>1.</em><b>2</b></td>', '2'),
    ('<td><em>1.2</em><b>e-3</b></td>', '1.2'),
    ('<td><em>1.2e-</em><b>3</b></td>', '3'),
    ('<td><em>-</em><b>7</b></td>', '7'),
    ('<td><em>+</em><b>7</b></td>', '7'),
    ('<td>identifier<em>7</em></td>', '7'),
])
def test_inline_tags_cannot_manufacture_a_numeric_separator(text, token):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, token)
    assert caught.value.code == 'partial_source_numeric_token'


@pytest.mark.parametrize('role', ['rate', 'spread', 'condition'])
@pytest.mark.parametrize('text,token', [
    ('<td>-<br>7</td>', '7'), ('<td>+<break/>7</td>', '7'),
    ('<td>−<em><br/></em>7</td>', '7'),
    ('<td>1e<br>-3</td>', '-3'), ('<td>1E<break/>+3</td>', '+3'),
    ('<td>1.2e<br>-3</td>', '-3'),
    ('<td>1<em>e</em><br>-3</td>', '-3'),
    ('<td>1<br><em>e</em>-3</td>', '1'),
    ('<td><em>1.</em><b>2e</b><br>-3</td>', '-3'),
    ('<td>1<br><em>.</em>2</td>', '1'),
    ('<td>1<br>.2</td>', '1'), ('<td>1<br>.2</td>', '.2'),
    ('<td>1.<br>2</td>', '1.'), ('<td>1.<br>2</td>', '2'),
    ('<td>1<br>e-3</td>', '1'),
])
def test_soft_breaks_cannot_hide_numeric_sign_decimal_or_exponent_edges(text, token, role):
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, token, role=role)
    assert caught.value.code == 'partial_source_numeric_token'


@pytest.mark.parametrize('text,token', [
    ('<td>Label<br>7</td>', '7'), ('<td>Rate<br>7</td>', '7'),
    ('<td>e<br>7</td>', '7'), ('<td>1<br>2</td>', '1'),
    ('<td>Rat<em>e</em><br>7</td>', '7'),
    ('<td>1<br>2</td>', '2'), ('<td>-</td><td>7</td>', '7'),
    ('<td>1e</td><td>-3</td>', '-3'),
    ('<td>1</td><td>.2</td>', '.2'),
    ('<td>- <br>7</td>', '7'), ('<td>1e <br>-3</td>', '-3'),
    ('<td>1<br>Example</td>', '1'),
])
def test_soft_break_guard_preserves_independent_tokens_and_real_whitespace(text, token):
    assert number(text, token)['value'] == float(token)


def test_plusminus_spread_across_a_soft_break_retains_its_allowed_role():
    text = '<td>Mean 7 +/-<br>1</td>'
    assert number(text, '1', role='spread')['value'] == 1
    with pytest.raises(ExperimentalContractError) as caught:
        number(text, '1')
    assert caught.value.code == 'uncertainty_is_not_rate_point'


def test_real_whitespace_and_utf8_source_custody_are_preserved():
    text = 'µ<table><tr><td>Label</td><td><em>1</em> <b>2</b></td></tr></table>'
    selected = selector(text, '2', quote='<b>2</b>')
    original = deepcopy(selected)
    result = read_source_number(selected, sources=sources(text), role='rate')
    assert selected == original
    assert result['selector']['witness'] == {**selected['witness'], 'artifact_ref': ARTIFACT}
    assert result['selector']['witness']['start'] == text.encode().index(b'<b>2</b>')
    assert result['value'] == 2


@pytest.mark.parametrize('raw', ['nmol/min/mg', 'nmol<br/>min<sup>−1</sup> mg<sup>−1</sup>'])
def test_complete_units_in_adjacent_table_cells_keep_their_own_lexical_edges(raw):
    text = '<table><tr><td>Label</td><td>' + raw + '</td><td>per_min</td></tr></table>'
    result = read_source_rate_unit(witness(text, raw), sources=sources(text))
    assert (result['canonical_unit'], result['multiplier']) == ('pmol/min/mg', 1000)
    assert result['raw_unit'] == raw


@pytest.mark.parametrize('raw', ['<td>nmol/min/mg</td>',
    '<TH class="unit">nmol/min/mg</TH>',
    '<td data-label="rate">nmol min<sup>−1</sup> mg<sup>−1</sup></td>',
    '<table><tr><td>nmol<br/>min<sup>−1</sup> mg<sup>−1</sup></td></tr></table>'])
def test_one_complete_unit_can_retain_its_single_cell_wrapper(raw):
    unit = read_source_rate_unit(witness(raw, raw), sources=sources(raw))
    assert (unit['canonical_unit'], unit['multiplier']) == ('pmol/min/mg', 1000)
    observed = number('Rate 0.005', '0.005')
    assert convert_source_number(observed, unit) == 5


@pytest.mark.parametrize('raw', ['nmol</td><td>/min/mg', 'nmol</th><th>/min/mg',
    'nmol</td></tr><tr><td>/min/mg'])
def test_selected_unit_cannot_be_fabricated_by_joining_table_fields(raw):
    text = '<table><tr><td>' + raw + '</td></tr></table>'
    with pytest.raises(ExperimentalContractError) as caught:
        read_source_rate_unit(witness(text, raw), sources=sources(text))
    assert caught.value.code == 'unsupported_source_rate_unit'


def test_spread_unit_scanning_does_not_join_table_cells_or_ignore_same_cell_units():
    for text, expected in [
        ('<td>58</td><td>nmol/min/mg</td><td>pmol/min/mg</td>', None),
        ('<td>58 nmol</td><td>/min/mg</td><td>pmol/min/mg</td>', 'unsupported_explicit_spread_unit'),
        ('<td>58 nmol<br/>min<sup>−1</sup> mg<sup>−1</sup></td><td>pmol/min/mg</td>', 'source_spread_unit_mismatch'),
    ]:
        source = sources(text)
        n = read_source_number(selector(text, '58'), sources=source, role='spread')
        unit = read_source_rate_unit(witness(text, 'pmol/min/mg'), sources=source)
        if expected is None:
            assert validate_source_spread_unit(n, unit, sources=source) is None
        else:
            with pytest.raises(ExperimentalContractError) as caught:
                validate_source_spread_unit(n, unit, sources=source)
            assert caught.value.code == expected
