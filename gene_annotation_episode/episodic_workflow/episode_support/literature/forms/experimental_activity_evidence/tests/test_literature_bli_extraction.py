"""The BLI extraction is derived from the BLI grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_bli_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_extraction import (
    BIOSENSOR_TYPE, NOT_EXTRACTED, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_record import (
    BIOSENSOR_TYPES, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.bli_passages import (
    REAL, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import (
    CRITERIA, grade_bli)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import bli_cases

# What the BLI converter reads and no grader criterion does: the effect's variance is built from the KD spread (the
# grader copies the spread kind into its native values for the converter). The biosensor type is read by the grader
# only to copy it into its native values for the reviewer and the sensor identity; no criterion judges it.
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread'}


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
    reads = set()
    for record in (bli_cases.synthetic_record(), bli_cases.sparse_record(), bli_cases.real_record()):
        grade_bli(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))
            or name in (SPREAD_KIND, 'fit_model', 'concentration_series', BIOSENSOR_TYPE)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, SPREAD_KIND, 'fit_model', BIOSENSOR_TYPE, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 4
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'reason'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == {*QUANTITIES, SERIES}


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    assert properties[SPREAD_KIND]['properties']['value']['anyOf'][0]['enum'] == list(SPREAD_KINDS)
    assert properties['fit_model']['properties']['value']['anyOf'][0]['enum'] == list(FIT_MODELS)
    assert properties[BIOSENSOR_TYPE]['properties']['value']['anyOf'][0]['enum'] == list(BIOSENSOR_TYPES)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter or the record keep."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER_OR_KEPT


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_criteria import BLI_CRITERIA
    declared = {read.split('.')[-1] for criterion in BLI_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_bli(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the sheet side judges what the grader only recorded
    assert graded['native']['kd_nM'] == 20 and graded['native']['kd_from_rates_nM'] == pytest.approx(20)
    assert graded['native']['concentration_count'] == 6
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 10) + ' of the source', 'quote': 'KD = 20 nM'}
    assert record['concentration_series']['value'] == [2, 6, 20, 60, 200, 600] and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'bli' and record['fit_model'] == '1:1' and record['spread_kind'] == 'standard_deviation' and record['biosensor_type'] == 'streptavidin'
    assert record['quantities']['dissociation_time']['unit'] == 's' and record['quantities']['response_max']['unit'] == 'nm'


def test_the_span_counts_bytes_not_characters():
    start, end = quote_span(SYNTHETIC, 'R² = 0.99')
    assert start > SYNTHETIC.index('R² = 0.99')          # the degree sign comes before it
    assert SYNTHETIC.encode()[start:end].decode() == 'R² = 0.99' and end - start == len('R² = 0.99') + 1
    start, end = quote_span(REAL, 'dissociation phase of 600 s')       # a thin space is three bytes
    assert REAL.encode()[start:end].decode() == 'dissociation phase of 600 s' and end - start == len('dissociation phase of 600 s') + 2
    start, end = quote_span(REAL, 'KD) of 9.29 μM')                      # the Greek mu is two bytes, and the paragraph also has a micro sign
    assert REAL.encode()[start:end].decode() == 'KD) of 9.29 μM'
    assert start > REAL.index('KD) of 9.29')                                    # the o-umlaut of 'Göttingen' comes before it
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['kd', 'dissociation_time', 'replicate_count']
    assert record['quantities']['koff']['value'] is None and record['quantities']['koff']['reason'] == 'not_stated_in_passage'
    assert record['concentration_series']['status'] == 'unavailable'      # 'six concentrations from 20 uM to 0 uM' is no list
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['nonspecific_binding_checked']
    assert record['spread_kind'] is None and record['fit_model'] is None and record['biosensor_type'] is None
    graded = grade_bli(record)
    assert 'conflicting' not in {_criterion(graded, name)['status'] for name in CRITERIA}
    assert _criterion(graded, 'nonspecific_binding_control')['status'] == 'supported'
    assert set(REAL_STATED) < set(field_names())


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'kd', quote='KD = 21 nM'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(answer, twice)
    # a quote with an ordinary space where the paper has a thin space, or a micro sign where it has a Greek mu, is not in the chunk
    with pytest.raises(ExtractionRefused, match='dissociation_time:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'dissociation_time', quote='dissociation phase of 600 s'), REAL)
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'kd', quote='KD) of 9.29 µM'), REAL)
    # a short quote that the paragraph holds twice is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'kd', quote='dissociation constant (KD)'), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                      # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'response_max', unit='RU'), SYNTHETIC)           # SPR units are not BLI units
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='1:1_langmuir'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, BIOSENSOR_TYPE, value='made_up_sensor'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'baseline_stable', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'koff'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=3.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fit_r_squared:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'fit_r_squared', value=-0.1), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fit_r_squared:r_squared_must_be_at_most_one'):
        validate_answer(wrong(answer, 'fit_r_squared', value=1.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='concentration_series:number_must_be_above_zero'):
        validate_answer(wrong(answer, SERIES, value=[2, 0, 20]), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='concentration_series:series_is_empty'):
        validate_answer(wrong(answer, SERIES, value=[]), SYNTHETIC)


def test_a_field_is_stated_with_its_quote_or_unavailable_with_a_reason_and_nothing_else():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:stated_has_value_unit_quote_span_and_no_reason'):
        validate_answer(wrong(answer, 'kd', quote=None), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', reason='not_stated_in_passage'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None), SYNTHETIC)


def test_every_synthetic_field_is_stated_so_the_test_passage_covers_the_whole_form():
    assert set(SYNTHETIC_STATED) == set(field_names())
    assert answer_from(SYNTHETIC, {})['kd']['status'] == 'unavailable'


SUPPORT_VALUES = ['direct', 'implied', 'about_something_else']


def test_every_field_of_the_schema_carries_a_support_with_the_three_values():
    for name, field in answer_schema()['properties'].items():
        assert 'support' in field['required'] and field['properties']['support']['anyOf'][0]['enum'] == SUPPORT_VALUES, name
        assert field['properties']['support']['anyOf'][1] == {'type': 'null'}


def test_a_stated_field_without_a_support_or_with_an_unknown_one_is_refused_and_an_unavailable_one_has_none():
    answer = synthetic_answer()
    for name in ('kd', 'regeneration', SPREAD_KIND, BIOSENSOR_TYPE):
        with pytest.raises(ExtractionRefused, match=name + ':stated_has_value_unit_quote_span_and_no_reason'):
            validate_answer(wrong(answer, name, support=None), SYNTHETIC)
        with pytest.raises(ExtractionRefused, match=name + r'\.support:schema'):
            validate_answer(wrong(answer, name, support='probably'), SYNTHETIC)
    for support in SUPPORT_VALUES:
        validate_answer(wrong(answer, 'kd', support=support), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)   # support left on an unavailable field
    with pytest.raises(ExtractionRefused, match='regeneration:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'regeneration', status='unavailable', value=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)
    assert all(item['support'] is None for item in answer_from(SYNTHETIC, {}).values())


def test_the_record_carries_the_support_of_each_stated_value():
    answer = synthetic_answer()
    answer['kd']['support'], answer['regeneration']['support'], answer[SPREAD_KIND]['support'] = 'implied', 'about_something_else', 'implied'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp_1', 'source_1', 'hypothesis_1')
    assert record['quantities']['kd']['support'] == 'implied' and record['quantities']['kon']['support'] == 'direct'
    assert record['facts']['regeneration']['support'] == 'about_something_else' and record['facts']['baseline_stable']['support'] == 'direct'
    assert record['choice_support'] == {'spread_kind': 'implied', 'fit_model': 'direct', 'biosensor_type': 'direct'}
    assert record['concentration_series']['support'] == 'direct'
    empty = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp_1', 'source_1', 'hypothesis_1')
    assert empty['quantities']['kd']['support'] is None and empty['facts']['regeneration']['support'] is None
    assert empty['choice_support'] == {'spread_kind': None, 'fit_model': None, 'biosensor_type': None}
