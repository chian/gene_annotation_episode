"""The radioligand extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_radioligand_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_extraction import (
    ASSAY_FORMAT, FIT_MODEL, ISOTOPE, NOT_EXTRACTED, PREPARATION_TYPE, SEPARATION, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema, field_names,
    quote_span, record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_record import (
    ASSAY_FORMATS, CHOICE_FIELDS, FACTS, FIT_MODELS, ISOTOPES, PREPARATION_KEYS, PREPARATION_TYPES, QUANTITIES, SEPARATION_METHODS, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.radioligand_passages import (
    REAL, REAL_KD, REAL_MAY_ALSO_STATE, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import (
    CRITERIA, grade_radioligand)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import radioligand_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the effect's
# variance is built from the spreads by the converter; the specific activity, the amount of receptor, the number of technical tubes,
# the temperature, the isotope, the kind of preparation and the statement that only this method was used are kept in the record
# for the reviewer.
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'ki_spread', 'specific_activity', 'receptor_amount', 'technical_replicate_count', 'temperature', ISOTOPE, PREPARATION_TYPE, SPREAD_KIND, 'single_estimate_method'}


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
    for record in (radioligand_cases.synthetic_record(), radioligand_cases.sparse_record(), radioligand_cases.real_record()):
        grade_radioligand(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.')) or name in (ASSAY_FORMAT, FIT_MODEL, SEPARATION, SERIES)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, ASSAY_FORMAT, ISOTOPE, SEPARATION, PREPARATION_TYPE, SPREAD_KIND, FIT_MODEL, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form and len(form) == 42
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'reason'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == {*QUANTITIES, SERIES}


def test_the_kd_the_ki_and_the_ic50_are_separate_fields_that_do_not_take_each_others_values():
    meaning = extraction.MEANING
    assert {'kd', 'bmax', 'ki', 'ic50'} <= set(field_names())
    assert 'An IC50 or a Ki is not this field' in meaning['kd'] and 'An IC50 is not this field, a KD is not this field' in meaning['ki']
    assert 'Ki or a KD is not this field' in meaning['ic50']


def test_the_radioligand_concentration_the_series_ends_and_the_nonspecific_ligand_are_separate_fields_that_exclude_each_other():
    meaning = extraction.MEANING
    assert 'a concentration used in a saturation series' in meaning['radioligand_concentration'] and 'competition is not this field' in meaning['radioligand_range_lowest']
    assert 'competition is not this field' in meaning['radioligand_range_highest']
    assert 'competitor of a competition curve, or of the radioligand, is not this field' in meaning['nonspecific_ligand_concentration']
    assert 'A concentration of the unlabelled ligand is not this field' in meaning['nonspecific_excess']
    assert 'percent of non-specific' not in meaning['percent_bound'] and 'non-specific binding' in meaning['percent_bound']


def test_the_fields_added_for_the_grader_gaps_are_in_the_form_and_say_what_to_quote():
    meaning = extraction.MEANING
    assert {'dissociation_rate', 'nonspecific_ligand_kd'} <= set(QUANTITIES) and {'depletion_corrected', 'nonspecific_ligand_is_unlabelled_radioligand'} <= set(FACTS)
    assert UNITS['dissociation_rate'] == ('1/s', '1/min', '1/h') and UNITS['nonspecific_ligand_kd'] == UNITS['kd']
    assert 'A half-life' in meaning['dissociation_rate'] and 'ITS OWN Kd' in meaning['nonspecific_excess'] and 'of that ligand itself' in meaning['nonspecific_ligand_kd']
    assert 'avoided or small' in meaning['depletion_corrected'] and 'cold' in meaning['nonspecific_ligand_is_unlabelled_radioligand']
    for name in ('dissociation_rate', 'nonspecific_ligand_kd', 'depletion_corrected', 'nonspecific_ligand_is_unlabelled_radioligand'):
        assert name in SYNTHETIC_STATED and SYNTHETIC_STATED[name][2] in SYNTHETIC and SYNTHETIC.count(SYNTHETIC_STATED[name][2]) == 1 and name not in REAL_STATED
    record = record_from_answer(validate_answer(synthetic_answer(), SYNTHETIC), SYNTHETIC, 0, 'exp_1', 'source_1', 'hypothesis_1')
    assert record['quantities']['dissociation_rate']['value'] == 0.2 and record['quantities']['dissociation_rate']['unit'] == '1/min'
    assert record['quantities']['nonspecific_ligand_kd']['value'] == 2.0 and record['facts']['depletion_corrected']['answer'] == 'yes'
    assert record['facts']['nonspecific_ligand_is_unlabelled_radioligand']['answer'] == 'yes'
    native = grade_radioligand(record)['native']
    assert native['nonspecific_excess_ratio'] == 500 and native['depletion_corrected'] == 'yes'      # the stated fold wins; the correction fact is recorded with the percent bound


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((ASSAY_FORMAT, ASSAY_FORMATS), (ISOTOPE, ISOTOPES), (SEPARATION, SEPARATION_METHODS), (PREPARATION_TYPE, PREPARATION_TYPES),
                             (SPREAD_KIND, SPREAD_KINDS), (FIT_MODEL, FIT_MODELS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['specific_activity'] == ('Ci/mmol',) and UNITS['bmax'] == ('fmol/mg', 'pmol/mg', 'sites/cell', 'nM') and UNITS['kd'] == UNITS['ic50'] == ('pM', 'nM', 'uM', 'mM')
    assert UNITS['percent_bound'] == UNITS['nonspecific_fraction'] == ('percent',) and UNITS['hill_slope'] == UNITS['nonspecific_excess'] == ('ratio',)
    assert ISOTOPES == ('tritium', 'iodine_125', 'sulfur_35', 'phosphorus_32', 'other')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter or the record keep."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER_OR_KEPT


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_criteria import RADIOLIGAND_CRITERIA
    declared = {read.split('.')[-1] for criterion in RADIOLIGAND_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_radioligand(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # as the sheet judges what the grader recorded
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['kd_nM'] == 2.0 and native['ki_nM'] == 5.0 and native['ic50_nM'] == 7.5 and native['constant_name'] == 'kd'
    assert native['incubation_min'] == 60 and native['concentration_count'] == 10 and native['nonspecific_excess_ratio'] == 500
    assert native['concentration_low_over_kd'] == pytest.approx(0.05) and native['concentration_high_over_kd'] == pytest.approx(25.6)
    assert native['radioligand_over_kd'] == pytest.approx(0.5) and native['calculated_ki_nM'] == pytest.approx(5.0)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'a KD = 2.0 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 13) + ' of the source', 'quote': 'a KD = 2.0 nM'}
    assert record['concentration_series']['value'][-1] == 51.2 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'radioligand' and record['fit_model'] == 'one_site' and record['spread_kind'] == 'standard_error'
    assert record['assay_format'] == 'saturation' and record['radioligand_isotope'] == 'tritium' and record['separation_method'] == 'filtration' and record['preparation_type'] == 'membrane'
    assert record['quantities']['bmax']['unit'] == 'fmol/mg' and record['quantities']['bmax']['value'] == 1200 and record['quantities']['hill_slope']['value'] == 1.0
    assert record['quantities']['specific_activity']['unit'] == 'Ci/mmol' and record['quantities']['specific_activity']['value'] == 85
    assert record['quantities']['receptor_amount']['unit'] == 'ug' and record['quantities']['percent_bound']['value'] == 6 and record['quantities']['nonspecific_fraction']['value'] == 25
    assert record['quantities']['radioligand_concentration']['value'] == 1 and record['quantities']['nonspecific_ligand_concentration']['value'] == 1000
    assert record['quantities']['radioligand_range_lowest']['value'] == 0.1 and record['quantities']['radioligand_range_highest']['value'] == 51.2
    assert record['quantities']['technical_replicate_count']['value'] == 3 and record['quantities']['replicate_count']['value'] == 3
    assert record['quantities']['ki']['value'] == 5.0 and record['quantities']['ki_spread']['value'] == 0.3 and record['quantities']['ic50']['value'] == 7.5


def test_the_span_counts_bytes_not_characters():
    quote = 'at 25 °C'       # nothing multi-byte before it; its own degree sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = '20 µg of membrane protein'       # the degree sign before it is two bytes; its own micro sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    # the real paragraph has a thin space (U+2009, three bytes) between each number and its unit
    quote = 'known KD value of the radiolabel (0.076 nM)'       # nothing multi-byte before it; its own thin space (2 extra bytes)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    quote = 'known specific activity of the radiolabel (2200 Ci/mmol)'       # before it the thin space of '0.076 nM' (2 extra bytes); its own (2)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 2 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    quote = 'constraints for the radiolabel concentration (0.1 nM)'       # before it the thin spaces of '0.076 nM', '2200 Ci/mmol' and '1 mg/mL' (6 extra bytes); its own (2)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 6 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['specific_activity', 'radioligand_concentration']
    assert record['quantities']['kd']['reason'] == 'not_stated_in_passage'                       # the 'known' KD of the radiolabel is cited, not measured
    assert record['quantities']['specific_activity']['value'] == 2200 and record['quantities']['specific_activity']['unit'] == 'Ci/mmol'
    assert record['quantities']['radioligand_concentration']['value'] == 0.1
    for name in ('bmax', 'ki', 'ic50', 'hill_slope', 'receptor_amount', 'percent_bound', 'nonspecific_fraction', 'nonspecific_excess', 'incubation_time', 'temperature', 'replicate_count'):
        assert record['quantities'][name]['reason'] == 'not_stated_in_passage'
    assert record['quantities']['receptor_amount']['status'] == 'unavailable'                   # '1 mg/mL' is a protein concentration, not an amount per assay
    assert record['concentration_series']['status'] == 'unavailable'
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['nonlinear_fit_used']
    assert record['assay_format'] is None and record['fit_model'] is None and record['radioligand_isotope'] is None and record['separation_method'] is None and record['preparation_type'] is None
    graded = grade_radioligand(record)
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['nonlinear_fit']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert graded['reasons']['equilibrium'] == 'fact_unknown' and graded['reasons']['radioligand_range'] == 'kd_or_series_missing' and graded['reasons']['competition_radioligand_level'] == 'radioligand_concentration_or_kd_not_given'
    assert graded['native']['kd_nM'] is None and graded['native']['incubation_min'] is None
    assert set(REAL_STATED) | REAL_MAY_ALSO_STATE < set(field_names())


def real_with_kd():
    """The real answer that also states the cited KD (not in the allowed set): the form can hold it, the real run must not state it."""
    return answer_from(REAL, {**REAL_STATED, 'kd': REAL_KD})


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'kd', quote='a KD = 2.1 nM'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(answer, twice)
    # a Greek mu (U+03BC) where the passage has a micro sign (U+00B5), and a plain 'deg C' where it has the degree sign, are not in the chunk
    with pytest.raises(ExtractionRefused, match='receptor_amount:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'receptor_amount', quote='20 μg of membrane protein'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'temperature', quote='at 25 degC'), SYNTHETIC)
    # the real paragraph has a thin space between a number and its unit: an ordinary space is not in the chunk
    for quote in ('known KD value of the radiolabel (0.076 nM)',      # an ordinary space
                  'known KD value of the radiolabel (0.76 nM)'):   # another number
        with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
            validate_answer(wrong(real_with_kd(), 'kd', quote=quote), REAL)
    # a short quote that the paragraph holds more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(wrong(real_with_kd(), 'kd', quote='KD'), REAL)
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(wrong(real_with_kd(), 'kd', quote='(0.076 nM)'), REAL)          # the same number twice: 'known KD value of the radiolabel (0.076 nM)' and 'KD (0.076 nM)'
    assert validate_answer(real_answer(), REAL) and validate_answer(real_with_kd(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                       # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'ic50', unit='ug'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'specific_activity', unit='TBq/mmol'), SYNTHETIC)  # a specific activity in becquerel is not offered
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'receptor_amount', unit='mg/mL'), SYNTHETIC)      # a protein concentration is not an amount per assay
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'bmax', unit='nmol/mg'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'percent_bound', unit='ratio'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'incubation_time', unit='days'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='stern_volmer'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ASSAY_FORMAT, value='direct_titration'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ISOTOPE, value='3H'), SYNTHETIC)                  # the vocabulary word is 'tritium'
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, SEPARATION, value='gel_filtration'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'nonlinear_fit_used', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'ic50'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    for name in ('titration_point_count', 'technical_replicate_count', 'replicate_count'):
        with pytest.raises(ExtractionRefused, match=name + '.value:schema'):
            validate_answer(wrong(answer, name, value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='percent_bound:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'percent_bound', value=-6), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='concentration_series:number_must_be_above_zero'):
        validate_answer(wrong(answer, SERIES, value=[2, 0, 20]), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='concentration_series:series_is_empty'):
        validate_answer(wrong(answer, SERIES, value=[]), SYNTHETIC)


def test_a_field_is_stated_with_its_quote_or_unavailable_with_a_reason_and_nothing_else():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:stated_has_value_unit_quote_support_and_no_reason'):
        validate_answer(wrong(answer, 'kd', quote=None), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', reason='not_stated_in_passage'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None), SYNTHETIC)


def test_every_synthetic_field_is_stated_so_the_test_passage_covers_the_whole_form():
    assert set(SYNTHETIC_STATED) == set(field_names())
    assert answer_from(SYNTHETIC, {})['kd']['status'] == 'unavailable'


def test_other_units_of_the_vocabulary_are_accepted_and_reach_the_record():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 0.002, 'unit': 'uM', 'quote': 'a KD = 2.0 nM'}
    answer['ic50'] = {**answer['ic50'], 'value': 7500, 'unit': 'pM'}
    answer['bmax'] = {**answer['bmax'], 'value': 1.2, 'unit': 'pmol/mg'}
    answer['receptor_amount'] = {**answer['receptor_amount'], 'value': 0.02, 'unit': 'mg'}
    answer['incubation_time'] = {**answer['incubation_time'], 'value': 1, 'unit': 'h'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'uM' and record['quantities']['ic50']['unit'] == 'pM' and record['quantities']['bmax']['unit'] == 'pmol/mg' and record['quantities']['receptor_amount']['unit'] == 'mg'
    graded = grade_radioligand(record)
    assert graded['native']['kd_nM'] == pytest.approx(2.0) and graded['native']['ic50_nM'] == pytest.approx(7.5) and graded['native']['incubation_min'] == pytest.approx(60.0)


SUPPORT_VALUES = ['direct', 'implied', 'about_something_else']


def test_every_field_carries_a_support_with_the_three_values():
    for name, field in answer_schema()['properties'].items():
        assert list(field['properties']).count('support') == 1 and 'support' in field['required']
        assert field['properties']['support']['anyOf'][0]['enum'] == SUPPORT_VALUES and field['properties']['support']['anyOf'][1] == {'type': 'null'}


def test_a_stated_field_without_support_an_unknown_support_or_support_on_an_unavailable_field_is_refused():
    answer = synthetic_answer()
    for name in ('kd', FIT_MODEL, 'equilibrium_reached', SERIES):
        with pytest.raises(ExtractionRefused, match=name + ':stated_has_value_unit_quote_support_and_no_reason'):
            validate_answer(wrong(answer, name, support=None), SYNTHETIC)
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, support='probably'), SYNTHETIC)
    unavailable = wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None, support=None, reason='not_stated_in_passage')
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(unavailable, 'kd', support='direct'), SYNTHETIC)
    assert validate_answer(unavailable, SYNTHETIC)


def test_the_record_carries_the_support_of_every_stated_field():
    support = {'kd': 'implied', SERIES: 'implied', FIT_MODEL: 'about_something_else', SEPARATION: 'implied', 'equilibrium_reached': 'implied', 'ligand_depletion_checked': 'about_something_else'}
    answer = validate_answer(answer_from(SYNTHETIC, SYNTHETIC_STATED, support), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['concentration_series']['support'] == 'implied'
    assert record['quantities']['ic50']['support'] == 'direct'
    assert record['facts']['equilibrium_reached']['support'] == 'implied' and record['facts']['ligand_depletion_checked']['support'] == 'about_something_else'
    assert record['facts']['filter_binding_checked']['support'] == 'direct'
    assert set(record['choice_support']) == set(CHOICE_FIELDS) == set(extraction.CHOICES)
    assert record['choice_support'][FIT_MODEL] == 'about_something_else' and record['choice_support'][SEPARATION] == 'implied' and record['choice_support'][ASSAY_FORMAT] == 'direct'
    real = record_from_answer(validate_answer(real_answer(), REAL), REAL, 0, 'exp', 'src', 'hyp')
    assert real['quantities']['radioligand_concentration']['support'] == 'implied' and real['quantities']['specific_activity']['support'] == 'direct'
    assert real['quantities']['kd']['support'] is None and real['facts']['equilibrium_reached']['support'] is None and real['facts']['nonlinear_fit_used']['support'] == 'direct'
    assert real['choice_support'][FIT_MODEL] is None
    assert grade_radioligand(record)['native']['support']['replicates'][0] is not None      # the grader keeps the support of what a criterion reads
