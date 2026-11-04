"""Finite relative-signal prose reader over synthetic JATS fixtures only."""
from copy import deepcopy
from xml.sax.saxutils import escape

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_ratio_reader import read_jats_relative_percent


SOURCE = {"source_ref": "source_fixture", "artifact_ref": "artifact_fixture",
          "representation": "synthetic_fixture"}


def source(text, *, markup=False, prefix="", suffix=""):
    paragraph = text if markup else escape(text)
    return {**SOURCE, "xml": prefix + '<article><body><sec id="results"><title>Results</title>'
            + '<p>' + paragraph + '</p>' + suffix + '</sec></body></article>'}


def read(value, **kwargs):
    return read_jats_relative_percent(value, section_id="results", paragraph_index=0,
        expected_subject="Protein P", variant="A12G", reference_literal="tagged WT levels", **kwargs)


def test_one_comparison_preserves_source_literal_and_unknown_uncertainty_without_mutation():
    value = source('Protein P variants were produced at 64% (Protein P A12G) of tagged WT levels.')
    original = deepcopy(value)
    result = read(value)
    assert value == original
    assert result['subject'] == 'Protein P'
    assert result['variant'] == 'A12G'
    assert result['reference'] == 'tagged WT levels'
    observation, = result['observations']
    assert observation['value'] == .64
    assert observation['origin'] == 'synthetic'
    assert observation['uncertainty'] == {'kind':'unreported','magnitude':None,
        'count':None,'sampling_basis':'unspecified'}
    proof = observation['source']
    assert proof['section_id'] == 'results' and proof['paragraph_index'] == 0
    assert proof['paragraph_text'][proof['expression_start']:proof['expression_end']] == proof['expression']
    assert proof['expression'] == '64% (Protein P A12G)'
    result['observations'][0]['source']['paragraph_text'] = 'changed'
    assert value == original


@pytest.mark.parametrize('variant,expected', [('A12G',.64),('B25A',.48),('C30A',1.),('D42Stop',.96)])
def test_shared_comparison_reference_applies_to_the_printed_variant_list(variant,expected):
    value = source('Protein P variants were produced at 64% (P A12G), 48% (P B25A), '
                   '100% (P C30A) and 96% (P D42Stop) of tagged WT levels.')
    result = read_jats_relative_percent(value, section_id='results', paragraph_index=0,
        expected_subject='Protein P', variant=variant, reference_literal='tagged WT levels')
    assert result['observations'][0]['value'] == expected


@pytest.mark.parametrize('lexeme,expected', [('0',0),('112',1.12),('.64',.0064),
    ('+64',.64),('6.4e1',.64),('1e3',10.)])
def test_relative_percent_is_not_artificially_capped_at_one(lexeme,expected):
    assert read(source(f'Protein P was at {lexeme}% (P A12G) of tagged WT levels.'))['observations'][0]['value'] == expected


def test_inline_markup_and_unicode_offsets_preserve_only_direct_prose():
    value = source('µ Protein <italic>P</italic> was at 64% (<italic>P</italic> A12G) of tagged WT levels.'
        '<fig><caption><p>Protein P was at 99% (P A12G) of tagged WT levels. SD n=3.</p></caption></fig>', markup=True)
    row = read(value)['observations'][0]
    assert row['value'] == .64
    assert 'SD' not in row['source']['paragraph_text']
    assert row['uncertainty']['count'] is None
    assert row['source']['expression_start'] == row['source']['paragraph_text'].index('64%')


def test_section_direct_paragraph_index_excludes_nested_sections_and_figures():
    value = source('Protein P had no applicable percentage.',
        suffix='<fig><caption><p>Protein P at 70% (P A12G) of tagged WT levels.</p></caption></fig>'
        '<sec id="child"><p>Protein P at 80% (P A12G) of tagged WT levels.</p></sec>'
        '<p>Protein P at 64% (P A12G) of tagged WT levels.</p>')
    result = read_jats_relative_percent(value,section_id='results',paragraph_index=1,
        expected_subject='Protein P',variant='A12G',reference_literal='tagged WT levels')
    assert result['observations'][0]['value'] == .64
    with pytest.raises(ExperimentalContractError,match='direct_paragraph_unavailable'):
        read_jats_relative_percent(value,section_id='results',paragraph_index=2,
            expected_subject='Protein P',variant='A12G',reference_literal='tagged WT levels')


@pytest.mark.parametrize('text', [
    'Protein P was at 64% (P A12G). Another measurement was of tagged WT levels.',
    'Protein P was at 64% (P A12G)! It was of tagged WT levels.',
    'Protein P was at 64% (P A12G)? Of tagged WT levels.',
    'Protein P was at 64% (P A12G) of native WT levels and 48% (P B25A) of tagged WT levels.',
    'Protein P was at 64% (P A12G) of tagged WT levels_extra.',
    'Protein P was at 64% (P A12Gmore) of tagged WT levels.',
    'Protein P was at 64% (P XA12G) of tagged WT levels.',
    'Protein P was at 64% of tagged WT levels.',
    'Protein P was at sixty-four% (P A12G) of tagged WT levels.',
    'Protein P was at 1,064% (P A12G) of tagged WT levels.',
    'Protein P was at 64.0.5% (P A12G) of tagged WT levels.',
])
def test_unavailable_or_unrelated_references_are_not_silently_rebound(text):
    with pytest.raises(ExperimentalContractError,match='relative_percent_expression_unavailable'):
        read(source(text))


@pytest.mark.parametrize('prefix', ['<','≤','>=','≥','~','≈','approximately ','about ',
    'less than ','greater than ','at least ','at most ','10 to ','between 10 and ','10–',
    'more than ','fewer than ','up to ','roughly ','around ','between ','from ','not at ',
    'between 10% and '])
def test_censored_or_approximate_percentage_is_not_an_exact_point(prefix):
    with pytest.raises(ExperimentalContractError,match='censored_or_approximate_percent'):
        read(source(f'Protein P was at {prefix}64% (P A12G) of tagged WT levels.'))


@pytest.mark.parametrize('qualifier', ['or less','or more','at most','at least'])
def test_post_label_bound_is_not_an_exact_point(qualifier):
    with pytest.raises(ExperimentalContractError,match='censored_or_approximate_percent'):
        read(source(f'Protein P was at 64% (P A12G) {qualifier} of tagged WT levels.'))


@pytest.mark.parametrize('qualifier', ['± 3%', '+/- 3%', '(SD 3%)', ', SEM 2%,'])
def test_explicit_local_uncertainty_is_not_silently_reported_as_unreported(qualifier):
    with pytest.raises(ExperimentalContractError,match='relative_percent_uncertainty_unsupported'):
        read(source(f'Protein P was at 64% (P A12G) {qualifier} of tagged WT levels.'))


@pytest.mark.parametrize('lexeme,code', [('-1','nonnegative_relative_percent_required'),
    ('−1','nonnegative_relative_percent_required'),('1e400','finite_number_required'),
    ('1e-400','numerical_model_range'),('1e-322','numerical_model_range')])
def test_invalid_or_nonrepresentable_numbers_return_structured_failure(lexeme,code):
    with pytest.raises(ExperimentalContractError,match=code):
        read(source(f'Protein P was at {lexeme}% (P A12G) of tagged WT levels.'))


def test_repeated_comparative_sentences_are_ambiguous_even_with_equal_values():
    value=source('Protein P was at 64% (P A12G) of tagged WT levels. '
                 'Protein P was again at 64% (P A12G) of tagged WT levels.')
    with pytest.raises(ExperimentalContractError,match='ambiguous_relative_percent_expression'):
        read(value)


def test_two_matching_references_in_one_sentence_are_ambiguous():
    value=source('Protein P was at 64% (P A12G) of tagged WT levels and another fraction of tagged WT levels.')
    with pytest.raises(ExperimentalContractError,match='ambiguous_comparison_reference'):
        read(value)


def test_missing_subject_does_not_select_another_nearby_name():
    with pytest.raises(ExperimentalContractError,match='subject_not_in_selected_prose'):
        read(source('Protein PP was at 64% (P A12G) of tagged WT levels.'))


@pytest.mark.parametrize('index',[True,False,-1,1.5,None,'0'])
def test_paragraph_index_must_be_nonnegative_integer(index):
    with pytest.raises(ExperimentalContractError,match='nonnegative_paragraph_index_required'):
        read_jats_relative_percent(source('Protein P'),section_id='results',paragraph_index=index,
            expected_subject='Protein P',variant='A12G',reference_literal='tagged WT levels')


@pytest.mark.parametrize('xml,code', [
    ('<article>','malformed_jats'),
    ('<book><sec id="results"><p>Protein P</p></sec></book>','jats_article_required'),
    ('<article><sec id="results"/><sec id="results"/></article>','unique_section_required'),
    ('<article><p id="results">Protein P</p></article>','unique_section_required'),
    ('<!DOCTYPE article [<!ENTITY x "64">]><article/>','xml_declarations_not_supported'),
])
def test_xml_and_selector_errors_are_explicit(xml,code):
    with pytest.raises(ExperimentalContractError,match=code):
        read({**SOURCE,'xml':xml})


@pytest.mark.parametrize('declaration', [
    '<!DOCTYPE article PUBLIC "synthetic JATS" "https://invalid.example/no-fetch.dtd">',
    '<!DOCTYPE article SYSTEM "file:///missing/no-fetch.dtd">',
])
def test_external_jats_declaration_is_inert(declaration):
    value=source('Protein P was at 64% (P A12G) of tagged WT levels.',prefix=declaration)
    assert read(value)['observations'][0]['value'] == .64


@pytest.mark.parametrize('mutation', [
    lambda x:x.update(unexpected=True),
    lambda x:x.pop('artifact_ref'),
    lambda x:x.update(representation='unknown'),
    lambda x:x.update(xml=b'<article/>'),
])
def test_closed_source_contract_rejects_unsupported_input(mutation):
    value=source('Protein P was at 64% (P A12G) of tagged WT levels.')
    mutation(value)
    with pytest.raises(ExperimentalContractError):
        read(value)


def test_primary_source_origin_is_reported_not_synthetic_or_graph_derived():
    value=source('Protein P was at 64% (P A12G) of tagged WT levels.')
    value['representation']='primary_jats'
    assert read(value)['observations'][0]['origin']=='reported'
