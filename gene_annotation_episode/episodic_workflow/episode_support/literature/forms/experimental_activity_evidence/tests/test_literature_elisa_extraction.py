"""The ELISA extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_elisa_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_extraction import (
    ASSAY_FORMAT, BLOCKING_AGENT, DETECTION_FORMAT, ENZYME_CONJUGATE, FIT_MODEL, NOT_EXTRACTED, READOUT_SIGNAL, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema,
    field_names, quote_span, record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_record import (
    ASSAY_FORMATS, BLOCKING_AGENTS, CHOICE_FIELDS, DETECTION_FORMATS, ENZYME_CONJUGATES, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, READOUT_SIGNALS, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.elisa_passages import (
    REAL, REAL_MAY_ALSO_STATE, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_grader import (
    CRITERIA, grade_elisa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import elisa_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the effect's
# variance is built from the spreads by the converter, and the coating concentration, the number of washes, the number of technical
# wells and the temperature are kept in the record for the reviewer, as are the choices that no criterion reads.
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'ki_spread', 'coating_concentration', 'wash_count', 'technical_replicate_count', 'temperature',
                                 SPREAD_KIND, DETECTION_FORMAT, READOUT_SIGNAL, ENZYME_CONJUGATE, BLOCKING_AGENT}


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
    for record in (elisa_cases.synthetic_record(), elisa_cases.sparse_record(), elisa_cases.real_record()):
        grade_elisa(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.')) or name in (ASSAY_FORMAT, FIT_MODEL, SERIES)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, ASSAY_FORMAT, DETECTION_FORMAT, SPREAD_KIND, FIT_MODEL, READOUT_SIGNAL, ENZYME_CONJUGATE, BLOCKING_AGENT, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'reason'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == {*QUANTITIES, SERIES}


def test_the_kd_the_ki_the_ec50_and_the_ic50_are_four_separate_fields_that_do_not_take_each_others_values():
    meaning = extraction.MEANING
    assert {'kd', 'ki', 'ec50', 'ic50'} <= set(field_names())
    assert 'EC50 or IC50 is not this field' in meaning['kd'] and 'IC50 is not this field' in meaning['ki']
    assert 'KD is not this field' in meaning['ec50'] and 'Ki or a KD is not this field' in meaning['ic50']


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((ASSAY_FORMAT, ASSAY_FORMATS), (DETECTION_FORMAT, DETECTION_FORMATS), (SPREAD_KIND, SPREAD_KINDS), (FIT_MODEL, FIT_MODELS),
                             (READOUT_SIGNAL, READOUT_SIGNALS), (ENZYME_CONJUGATE, ENZYME_CONJUGATES), (BLOCKING_AGENT, BLOCKING_AGENTS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['signal_maximum'] == ('OD',) and UNITS['coating_concentration'] == ('ng/mL', 'ug/mL') and UNITS['kd'] == UNITS['ic50'] == ('pM', 'nM', 'uM', 'mM')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter or the record keep."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER_OR_KEPT


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_criteria import ELISA_CRITERIA
    declared = {read.split('.')[-1] for criterion in ELISA_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_elisa(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # as the sheet judges what the grader recorded
    native = graded['native']
    assert native['kd_nM'] == 20 and native['ki_nM'] == 30 and native['ec50_nM'] == 28 and native['ic50_nM'] == 45 and native['constant_name'] == 'kd'
    assert native['signal_over_background'] == pytest.approx(20.0) and native['incubation_min'] == 90 and native['concentration_count'] == 12
    assert native['concentration_low_over_constant'] == pytest.approx(0.05) and native['concentration_high_over_constant'] == pytest.approx(102.4)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'apparent KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 19) + ' of the source', 'quote': 'apparent KD = 20 nM'}
    assert record['concentration_series']['value'][-1] == 2048 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'elisa' and record['fit_model'] == 'four_parameter_logistic' and record['spread_kind'] == 'standard_error'
    assert record['assay_format'] == 'saturation_titration' and record['detection_format'] == 'indirect' and record['readout_signal'] == 'absorbance'
    assert record['enzyme_conjugate'] == 'horseradish_peroxidase' and record['blocking_agent'] == 'bsa'
    assert record['quantities']['coating_concentration']['unit'] == 'ug/mL' and record['quantities']['coating_concentration']['value'] == 2
    assert record['quantities']['signal_maximum']['unit'] == 'OD' and record['quantities']['signal_background']['value'] == 0.06
    assert record['quantities']['technical_replicate_count']['value'] == 3 and record['quantities']['replicate_count']['value'] == 3
    assert record['quantities']['ic50']['value'] == 45 and record['quantities']['ec50']['value'] == 28 and record['quantities']['ki_spread']['value'] == 3


def test_the_span_counts_bytes_not_characters():
    quote = 'at 25 °C'       # nothing multi-byte before it; its own degree sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'at a concentration of 2 µg/mL'       # the degree sign before it is two bytes; its own micro sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    # the real paragraph has a thin space (U+2009, three bytes) between a number and its unit
    quote = '10 µg ml−1 VLDLR-ed'       # before it the thin space of '100 µl' (2 extra bytes), the micro sign of 'µl' (1) and the thin space of '2 mM' (2); its own two thin spaces (4), micro sign (1) and minus sign (U+2212, 2)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 5 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 7
    quote = 'overnight at 4 °C'       # before it the 5 extra bytes above and those of '10 µg ml−1' (2 + 1 + 2 + 2 = 7); its own thin space (2) and degree sign (1)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 12 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 3
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert set(stated) == {'coating_concentration', 'wash_count', 'incubation_time'}
    assert record['quantities']['coating_concentration']['value'] == 10 and record['quantities']['coating_concentration']['unit'] == 'ug/mL'
    assert record['quantities']['incubation_time']['value'] == 1 and record['quantities']['incubation_time']['unit'] == 'h' and record['quantities']['wash_count']['value'] == 3
    for name in ('kd', 'ki', 'ec50', 'ic50'):
        assert record['quantities'][name]['reason'] == 'not_stated_in_passage'                # the values are in the Results, not in this paragraph
    assert record['quantities']['temperature']['reason'] == 'not_stated_in_passage'          # 'room temperature' is not a number
    assert record['concentration_series']['status'] == 'unavailable'                          # 'different concentrations' is not a list
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['blank_subtracted']
    assert record['fit_model'] == '1:1' and record['readout_signal'] == 'absorbance' and record['blocking_agent'] == 'bsa' and record['enzyme_conjugate'] == 'horseradish_peroxidase'
    assert record['assay_format'] is None and record['detection_format'] is None and record['spread_kind'] is None
    graded = grade_elisa(record)
    judged = {name: _criterion(graded, name) for name in graded['criteria']}      # as the sheet judges what the grader recorded
    assert [name for name, item in judged.items() if item['status'] == 'supported'] == ['blank_subtraction']
    assert graded['reasons']['fit_model'] == 'model_stated_without_a_reported_constant'      # a model is supported only by a reported constant's span
    assert [name for name, item in judged.items() if item['status'] == 'conflicting'] == []
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and judged['equilibrium']['status'] == 'unknown' and graded['reasons']['concentration_series'] == 'constant_or_series_missing'
    assert graded['reasons']['signal_window'] == 'signal_or_background_not_given' and graded['native']['incubation_min'] == 60
    assert set(REAL_STATED) | REAL_MAY_ALSO_STATE < set(field_names())


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'kd', quote='apparent KD = 21 nM'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(answer, twice)
    # a Greek mu (U+03BC) where the passage has a micro sign (U+00B5), a hyphen-minus where it has a minus sign (U+2212) and a plain 'deg C'
    # where it has the degree sign are not in the chunk
    with pytest.raises(ExtractionRefused, match='coating_concentration:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'coating_concentration', quote='at a concentration of 2 μg/mL'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'temperature', quote='at 25 degC'), SYNTHETIC)
    for quote in ('10 μg ml−1 VLDLR-ed',      # a Greek mu
                  '10 µg ml-1 VLDLR-ed',      # a hyphen-minus
                  '10 µg ml−1 VLDLR-ed'):               # plain spaces where the paragraph has thin spaces
        with pytest.raises(ExtractionRefused, match='coating_concentration:quote_is_not_in_the_chunk'):
            validate_answer(wrong(real_answer(), 'coating_concentration', quote=quote), REAL)
    with pytest.raises(ExtractionRefused, match='incubation_time:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'incubation_time', quote='ligands Clu or RAP in blocking solution for 1 h'), REAL)
    # a short quote that the paragraph holds more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='wash_count:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'wash_count', quote='The plate was washed three times with'), REAL)
    with pytest.raises(ExtractionRefused, match='incubation_time:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'incubation_time', quote='incubated for 1 h at room temperature'), REAL)
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                       # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'ic50', unit='ug/mL'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'coating_concentration', unit='nM'), SYNTHETIC)  # a coating given in a molar unit is not offered
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'signal_maximum', unit='RLU'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'incubation_time', unit='days'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='stern_volmer'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ASSAY_FORMAT, value='direct_titration'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, DETECTION_FORMAT, value='competitive'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, BLOCKING_AGENT, value='gelatin'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'equilibrium_reached', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'ic50'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    for name in ('titration_point_count', 'technical_replicate_count', 'replicate_count', 'wash_count'):
        with pytest.raises(ExtractionRefused, match=name + '.value:schema'):
            validate_answer(wrong(answer, name, value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='signal_background:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'signal_background', value=-0.06), SYNTHETIC)
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
    answer['kd'] = {**answer['kd'], 'value': 0.02, 'unit': 'uM', 'quote': 'apparent KD = 20 nM'}
    answer['ic50'] = {**answer['ic50'], 'value': 45000, 'unit': 'pM'}
    answer['coating_concentration'] = {**answer['coating_concentration'], 'value': 2000, 'unit': 'ng/mL'}
    answer['incubation_time'] = {**answer['incubation_time'], 'value': 1.5, 'unit': 'h'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'uM' and record['quantities']['ic50']['unit'] == 'pM' and record['quantities']['coating_concentration']['unit'] == 'ng/mL'
    graded = grade_elisa(record)
    assert graded['native']['kd_nM'] == pytest.approx(20.0) and graded['native']['ic50_nM'] == pytest.approx(45.0) and graded['native']['incubation_min'] == pytest.approx(90.0)


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
    support = {'kd': 'implied', SERIES: 'implied', FIT_MODEL: 'about_something_else', ASSAY_FORMAT: 'implied', 'equilibrium_reached': 'implied', 'blank_subtracted': 'about_something_else'}
    answer = validate_answer(answer_from(SYNTHETIC, SYNTHETIC_STATED, support), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['concentration_series']['support'] == 'implied'
    assert record['quantities']['ic50']['support'] == 'direct'
    assert record['facts']['equilibrium_reached']['support'] == 'implied' and record['facts']['blank_subtracted']['support'] == 'about_something_else'
    assert record['facts']['saturation_reached']['support'] == 'direct'
    assert set(record['choice_support']) == set(CHOICE_FIELDS) == set(extraction.CHOICES)
    assert record['choice_support'][FIT_MODEL] == 'about_something_else' and record['choice_support'][ASSAY_FORMAT] == 'implied' and record['choice_support'][READOUT_SIGNAL] == 'direct'
    sparse = record_from_answer(validate_answer(real_answer(), REAL), REAL, 0, 'exp', 'src', 'hyp')
    assert sparse['quantities']['kd']['support'] is None and sparse['facts']['saturation_reached']['support'] is None
    assert sparse['choice_support'][DETECTION_FORMAT] is None and sparse['choice_support'][FIT_MODEL] == 'direct'
    assert grade_elisa(record)['native']['support']['fit_model'] == ['about_something_else', 'implied']      # the grader keeps the support of what a criterion reads, in the order of its reads
