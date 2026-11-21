"""The ITC extraction is derived from the ITC grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_itc_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_extraction import (
    NOT_EXTRACTED, SPREAD_KIND, TITRATION_MODE, ExtractionRefused, answer_schema, field_names, quote_span, record_from_answer,
    validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_record import (
    FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, TITRATION_MODES, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.itc_passages import (
    HSP90_HOP, HSP90_HOP_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, hsp90_hop_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import (
    CRITERIA, grade_itc)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import itc_cases

# What the ITC converter reads and no grader criterion does (literature_itc_converter.py: the effect's variance is
# built from the KD spread; the grader copies the spread kind into its native values for the converter), and the
# syringe concentration, which is part of the form and kept for the converter's and the reviewer's record.
READ_BY_THE_CONVERTER = {'kd_spread', 'syringe_concentration'}


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
    for record in (itc_cases.synthetic_record(), itc_cases.sparse_record(), itc_cases.hsp90_hop_record()):
        grade_itc(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))
            or name in (SPREAD_KIND, 'fit_model', TITRATION_MODE)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SPREAD_KIND, 'fit_model', TITRATION_MODE, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'reason'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == set(QUANTITIES)


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    assert properties[SPREAD_KIND]['properties']['value']['anyOf'][0]['enum'] == list(SPREAD_KINDS)
    assert properties['fit_model']['properties']['value']['anyOf'][0]['enum'] == list(FIT_MODELS)
    assert properties[TITRATION_MODE]['properties']['value']['anyOf'][0]['enum'] == list(TITRATION_MODES)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter reads."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_criteria import ITC_CRITERIA
    declared = {read.split('.')[-1] for criterion in ITC_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_itc(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the sheet side judges what the grader only recorded
    assert graded['native']['kd_nM'] == 20 and graded['native']['temperature_K'] == pytest.approx(298.15)
    assert graded['native']['c_value'] == pytest.approx(500)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 10) + ' of the source', 'quote': 'KD = 20 nM'}
    assert record['quantities']['enthalpy']['value'] == -50 and record['quantities']['entropy']['value'] == -20.3
    assert record['quantities']['temperature']['unit'] == 'C'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'itc' and record['fit_model'] == 'one_set_of_sites' and record['spread_kind'] == 'standard_deviation'
    assert record['facts']['buffer_matching']['answer'] == 'dialysed_together'


def test_the_span_counts_bytes_not_characters():
    start, end = quote_span(SYNTHETIC, 'ΔS = -20.3 J/mol/K')
    assert start > SYNTHETIC.index('ΔS = -20.3')       # the micro and degree signs and the deltas come before it
    assert SYNTHETIC.encode()[start:end].decode() == 'ΔS = -20.3 J/mol/K'
    assert end - start == len('ΔS = -20.3 J/mol/K') + 1
    start, end = quote_span(HSP90_HOP, 'KD = 0.578 ± 0.073 μM')    # thin spaces, plus-minus and mu: 2 bytes or 3 bytes each
    assert HSP90_HOP.encode()[start:end].decode().startswith('KD = 0.578')
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_a_negative_enthalpy_and_entropy_are_valid_and_a_negative_kd_is_not():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    assert answer['enthalpy']['value'] < 0 and answer['entropy']['value'] < 0
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(synthetic_answer(), 'kd', value=-20), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='temperature:temperature_must_be_above_absolute_zero'):
        validate_answer(wrong(synthetic_answer(), 'temperature', value=-300), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='temperature:temperature_must_be_above_absolute_zero'):
        validate_answer(wrong(synthetic_answer(), 'temperature', value=0, unit='K'), SYNTHETIC)


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(hsp90_hop_answer(), HSP90_HOP)
    record = record_from_answer(answer, HSP90_HOP, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['kd', 'kd_spread', 'stoichiometry', 'replicate_count']
    assert record['quantities']['enthalpy']['value'] is None and record['quantities']['enthalpy']['reason'] == 'not_stated_in_passage'
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['independent_titrations']
    graded = grade_itc(record)
    assert 'conflicting' not in {_criterion(graded, name)['status'] for name in CRITERIA}
    assert _criterion(graded, 'replicate_titrations_independent')['status'] == 'supported'
    assert set(HSP90_HOP_STATED) < set(field_names())


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
    # a quote with an ordinary space where the paper has a thin space is not in the chunk
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(hsp90_hop_answer(), 'kd', quote='KD = 0.578 ± 0.073 μM'), HSP90_HOP)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                     # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'enthalpy', unit='J/mol'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='made_up_model'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'buffer_matching', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'enthalpy'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='injection_count.value:schema'):
        validate_answer(wrong(answer, 'injection_count', value=20.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)


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
    for name in ('kd', 'buffer_matching', SPREAD_KIND):
        with pytest.raises(ExtractionRefused, match=name + ':stated_has_value_unit_quote_span_and_no_reason'):
            validate_answer(wrong(answer, name, support=None), SYNTHETIC)
        with pytest.raises(ExtractionRefused, match=name + r'\.support:schema'):
            validate_answer(wrong(answer, name, support='probably'), SYNTHETIC)
    for support in SUPPORT_VALUES:
        validate_answer(wrong(answer, 'kd', support=support), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)   # support left on an unavailable field
    with pytest.raises(ExtractionRefused, match='buffer_matching:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'buffer_matching', status='unavailable', value=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)
    assert all(item['support'] is None for item in answer_from(SYNTHETIC, {}).values())


def test_the_record_carries_the_support_of_each_stated_value():
    answer = synthetic_answer()
    answer['kd']['support'], answer['buffer_matching']['support'], answer[SPREAD_KIND]['support'] = 'implied', 'about_something_else', 'implied'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp_1', 'source_1', 'hypothesis_1')
    assert record['quantities']['kd']['support'] == 'implied' and record['quantities']['enthalpy']['support'] == 'direct'
    assert record['facts']['buffer_matching']['support'] == 'about_something_else' and record['facts']['baseline_corrected']['support'] == 'direct'
    assert record['choice_support'] == {'spread_kind': 'implied', 'fit_model': 'direct', 'titration_mode': 'direct'} and record['titration_mode'] == 'incremental'
    empty = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp_1', 'source_1', 'hypothesis_1')
    assert empty['quantities']['kd']['support'] is None and empty['facts']['buffer_matching']['support'] is None
    assert empty['choice_support'] == {'spread_kind': None, 'fit_model': None, 'titration_mode': None} and empty['titration_mode'] is None


def test_the_new_gap_fields_are_stated_in_the_synthetic_record_and_the_real_paragraph_states_none_of_them():
    record = record_from_answer(validate_answer(synthetic_answer(), SYNTHETIC), SYNTHETIC, 0, 'exp_1', 'source_1', 'hypothesis_1')
    assert record['quantities']['final_molar_ratio']['value'] == 2.0 and record['quantities']['final_molar_ratio']['unit'] == 'dimensionless'
    assert record['titration_mode'] == 'incremental' and record['facts']['enthalpy_buffer_ionization_corrected']['answer'] == 'no'
    assert graded_native(record)['final_ligand_over_kd'] == pytest.approx(2.0 * 500 / 1.0)
    real = record_from_answer(validate_answer(hsp90_hop_answer(), HSP90_HOP), HSP90_HOP, 0, 'exp', 'src', 'hyp')
    assert real['quantities']['final_molar_ratio']['status'] == 'unavailable' and real['titration_mode'] is None
    assert real['facts']['enthalpy_buffer_ionization_corrected']['answer'] == 'unknown'


def graded_native(record):
    return grade_itc(record)['native']
