"""The spectro_direct extraction is derived from the grader's input form: its answer schema has exactly the fields the form (and so the grader) has, a valid
answer becomes a record the grader accepts, and a quote that is not at its span is refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spectro_direct_extraction as extraction
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spectro_direct_extraction import (
    NOT_EXTRACTED, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span, record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spectro_direct_record import (
    FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.spectro_direct_passages import (
    REAL, REAL_ALLOWED, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_converter import _criterion, convert_spectro_direct
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_grader import CRITERIA, grade_spectro_direct

# What the converter reads and no grader criterion does: the effect quantities, their spreads and the enzyme mass (the grader copies every quantity into its native values).
READ_BY_THE_CONVERTER = {'catalytic_efficiency', 'catalytic_efficiency_spread', 'turnover', 'turnover_spread', 'specific_activity', 'specific_activity_spread', 'rate_over_control',
                         'rate_over_control_spread', 'enzyme_mass'}


class Tracking(dict):
    """A dict that records the keys read by subscript, as the grader reads a record."""

    def __init__(self, items, reads, path=''):
        super().__init__({key: Tracking(value, reads, path + key + '.') if isinstance(value, dict) and key in ('quantities', 'facts') else value
                          for key, value in items.items()})
        self.reads, self.path = reads, path

    def __getitem__(self, key):
        self.reads.add(self.path + key)
        return super().__getitem__(key)


def fields_the_grader_reads():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import spectro_direct_cases
    reads = set()
    for record in (spectro_direct_cases.synthetic_record(), spectro_direct_cases.real_record(), spectro_direct_cases.sparse_record()):
        grade_spectro_direct(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.')) or name in (SERIES, SPREAD_KIND)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, SPREAD_KIND, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 4
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'reason'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    assert properties[SPREAD_KIND]['properties']['value']['anyOf'][0]['enum'] == list(SPREAD_KINDS)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction following."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_criteria import SPECTRO_DIRECT_CRITERIA
    declared = {read.split('.')[-1] for criterion in SPECTRO_DIRECT_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_every_criterion_is_decided_supported():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_spectro_direct(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the sheet side judges what the grader only recorded
    converted = convert_spectro_direct(graded)
    assert converted['extraction']['quantities']['effect']['value'] == 500000 and converted['enzyme_mass_g_per_mol'] == 48000
    kcat = record['quantities']['turnover']
    span = record['spans'][kcat['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'kcat was 20 s^-1')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 16) + ' of the source', 'quote': 'kcat was 20 s^-1'}
    assert record['concentration_series']['value'] == [10, 20, 50, 100, 200, 500, 1000] and record['spread_kind'] == 'standard_error'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS) and record['facts']['no_enzyme_control']['answer'] == 'yes'


def test_the_span_counts_bytes_not_characters():
    start, end = quote_span(SYNTHETIC, 'ε = 6.22 mM^-1 cm^-1')
    assert start > SYNTHETIC.index('ε = 6.22')   # '°' comes before it and takes two bytes
    assert SYNTHETIC.encode()[start:end].decode() == 'ε = 6.22 mM^-1 cm^-1'
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states():
    for name, (value, unit, quote) in REAL_STATED.items():
        assert (value, unit) in REAL_ALLOWED[name] and quote_span(REAL, quote) is not None
    record = record_from_answer(validate_answer(real_answer(), REAL), REAL, 0, 'exp', 'src', 'hyp')
    assert {name for name in QUANTITIES if record['quantities'][name]['status'] == 'point'} == set(REAL_STATED)
    assert record['quantities']['km']['reason'] is None and record['quantities']['wavelength']['reason'] == 'not_stated_in_passage'
    assert all(item['answer'] == 'unknown' for item in record['facts'].values()) and record['spread_kind'] is None
    graded = grade_spectro_direct(record)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'unknown'}
    assert set(REAL_ALLOWED) == {'km', 'turnover', 'turnover_spread'}


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='km:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'km', quote='Km = 41 µM'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='quote_occurs_more_than_once'):
        validate_answer(answer, twice)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'km', unit='M'), SYNTHETIC)                 # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'turnover', unit='h^-1'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'native_substrate', value='unknown'), SYNTHETIC)   # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'km'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=3.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='km:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'km', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='concentration_series:series_is_empty'):
        validate_answer(wrong(answer, SERIES, value=[]), SYNTHETIC)


def test_a_field_is_stated_with_its_quote_or_unavailable_with_a_reason_and_nothing_else():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='km:stated_has_value_unit_quote_span_and_no_reason'):
        validate_answer(wrong(answer, 'km', quote=None), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='km:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'km', status='unavailable', reason='not_stated_in_passage'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='km:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'km', status='unavailable', value=None, unit=None, quote=None), SYNTHETIC)


def test_every_synthetic_field_is_stated_so_the_test_passage_covers_the_whole_form():
    assert set(SYNTHETIC_STATED) == set(field_names())
    assert answer_from(SYNTHETIC, {})['km']['status'] == 'unavailable'
    for name, (value, unit, quote) in SYNTHETIC_STATED.items():
        assert quote_span(SYNTHETIC, quote) is not None, name      # every quote occurs once


SUPPORT_VALUES = ['direct', 'implied', 'about_something_else']


def test_every_field_of_the_schema_carries_a_support_with_the_three_values():
    for name, field in answer_schema()['properties'].items():
        assert 'support' in field['required'] and field['properties']['support']['anyOf'][0]['enum'] == SUPPORT_VALUES, name
        assert field['properties']['support']['anyOf'][1] == {'type': 'null'}


def test_a_stated_field_without_a_support_or_with_an_unknown_one_is_refused_and_an_unavailable_one_has_none():
    answer = synthetic_answer()
    for name in ('km', 'purified_enzyme', SPREAD_KIND):
        with pytest.raises(ExtractionRefused, match=name + ':stated_has_value_unit_quote_span_and_no_reason'):
            validate_answer(wrong(answer, name, support=None), SYNTHETIC)
        with pytest.raises(ExtractionRefused, match=name + r'\.support:schema'):
            validate_answer(wrong(answer, name, support='probably'), SYNTHETIC)
    for support in SUPPORT_VALUES:
        validate_answer(wrong(answer, 'km', support=support), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='km:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'km', status='unavailable', value=None, unit=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)   # support left on an unavailable field
    assert all(item['support'] is None for item in answer_from(SYNTHETIC, {}).values())


def test_the_record_carries_the_support_of_each_stated_value():
    answer = synthetic_answer()
    answer['km']['support'], answer['purified_enzyme']['support'], answer[SPREAD_KIND]['support'] = 'implied', 'about_something_else', 'implied'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['km']['support'] == 'implied' and record['facts']['purified_enzyme']['support'] == 'about_something_else'
    assert record['choice_support'] == {SPREAD_KIND: 'implied'} and record['quantities']['turnover']['support'] == 'direct'
    unstated = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert unstated['quantities']['km']['support'] is None and unstated['facts']['purified_enzyme']['support'] is None and unstated['choice_support'] == {SPREAD_KIND: None}
