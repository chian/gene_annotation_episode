"""The FCS extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_fcs_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_extraction import (
    DIFFUSION_MODEL, FIT_MODEL, NOT_EXTRACTED, READOUT_SIGNAL, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import (
    DIFFUSION_MODELS, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, READOUT_SIGNALS, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.fcs_passages import (
    REAL, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import (
    CRITERIA, grade_fcs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import fcs_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the effect's
# variance is built from the spread by the converter, and the structure parameter, the brightness, the laser power, the
# temperature and the statement that only this method was used are kept in the record for the reviewer.
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'structure_parameter', 'brightness', 'laser_power', 'temperature', 'single_estimate_method'}


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
    for record in (fcs_cases.synthetic_record(), fcs_cases.sparse_record(), fcs_cases.real_record()):
        grade_fcs(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))
            or name in (SPREAD_KIND, FIT_MODEL, 'concentration_series', DIFFUSION_MODEL, READOUT_SIGNAL)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, SPREAD_KIND, FIT_MODEL, DIFFUSION_MODEL, READOUT_SIGNAL, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'reason'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == {*QUANTITIES, SERIES}


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    assert properties[SPREAD_KIND]['properties']['value']['anyOf'][0]['enum'] == list(SPREAD_KINDS)
    assert properties[FIT_MODEL]['properties']['value']['anyOf'][0]['enum'] == list(FIT_MODELS)
    assert properties[DIFFUSION_MODEL]['properties']['value']['anyOf'][0]['enum'] == list(DIFFUSION_MODELS)
    assert properties[READOUT_SIGNAL]['properties']['value']['anyOf'][0]['enum'] == list(READOUT_SIGNALS)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['free_diffusion_coefficient'] == ('um2/s',) and UNITS['particle_number'] == ('molecules',) and UNITS['free_diffusion_time'] == ('us', 'ms')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter or the record keep."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER_OR_KEPT


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_criteria import FCS_CRITERIA
    declared = {read.split('.')[-1] for criterion in FCS_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_fcs(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # as the sheet judges what the grader recorded
    native = graded['native']
    assert native['kd_nM'] == 20 and native['labelled_nM'] == 2 and native['labelled_over_kd'] == pytest.approx(0.1) and native['particle_number'] == 0.8
    assert native['diffusion_ratio'] == pytest.approx(1.8) and native['expected_diffusion_ratio'] == pytest.approx(6 ** (1 / 3))
    assert native['incubation_min'] == 20 and native['acquisition_total_s'] == 150 and native['concentration_count'] == 10
    assert native['concentration_high_over_constant'] == pytest.approx(50.0)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 10) + ' of the source', 'quote': 'KD = 20 nM'}
    assert record['concentration_series']['value'][-1] == 1000 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'fcs' and record['fit_model'] == 'quadratic' and record['spread_kind'] == 'standard_error'
    assert record['diffusion_model'] == 'two_component' and record['readout_signal'] == 'diffusion_time'
    assert record['quantities']['free_diffusion_time']['unit'] == 'us' and record['quantities']['free_diffusion_time']['value'] == 60
    assert record['quantities']['bound_diffusion_coefficient']['unit'] == 'um2/s' and record['quantities']['bound_diffusion_coefficient']['value'] == 156
    assert record['quantities']['particle_number']['unit'] == 'molecules' and record['quantities']['mass_ratio']['value'] == 6
    assert record['quantities']['laser_power']['unit'] == 'uW' and record['quantities']['brightness']['unit'] == 'kHz' and record['quantities']['temperature']['unit'] == 'C'
    assert record['quantities']['measurement_repeat_count']['value'] == 5 and record['quantities']['fraction_bound_maximum']['unit'] == 'percent'


def test_the_span_counts_bytes_not_characters():
    start, end = quote_span(SYNTHETIC, 'at 25 °C')       # nothing multi-byte before it; its own degree sign is two bytes
    assert start == SYNTHETIC.index('at 25 °C') and SYNTHETIC.encode()[start:end].decode() == 'at 25 °C' and end - start == len('at 25 °C') + 1
    quote = 'a laser power of 5 µW at the sample'       # the degree sign before it is two bytes; its own micro sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'D = 280 µm²/s'       # before it: the degree sign, the micro sign of 5 µW and the micro sign of 60 µs; its own micro sign and superscript two are two bytes each
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 3 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    quote = 'D = 156 µm²/s'       # before it also the micro sign and the superscript two of 280 µm²/s and the micro sign of 108 µs
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 6 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    quote = 'comparing the apparent τD obtained by the fit'       # a Greek tau (2 bytes) in the real paragraph before it and its own
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 1 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'KD = 5 ± 1 nM'       # two taus before it; its own plus-minus sign is two bytes
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 2 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['kd', 'kd_spread', 'labelled_concentration']
    assert record['quantities']['kd']['value'] == 5 and record['quantities']['labelled_concentration']['unit'] == 'pM'
    assert record['quantities']['free_diffusion_time']['reason'] == 'not_stated_in_passage'      # the times are in the preceding paragraph
    assert record['concentration_series']['status'] == 'unavailable'                             # the c-Met is given as a range, not a list
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == []
    assert record['fit_model'] is None and record['spread_kind'] is None                         # 'a simple binding model' is not named; the kind of '± 1' is not stated
    assert record['diffusion_model'] == 'one_component' and record['readout_signal'] == 'diffusion_time'
    graded = grade_fcs(record)
    judged = {name: _criterion(graded, name) for name in graded['criteria']}      # as the sheet judges what the grader recorded
    assert [name for name, item in judged.items() if item['status'] == 'supported'] == ['labelled_over_kd']
    assert [name for name, item in judged.items() if item['status'] == 'conflicting'] == ['labelled_range']
    assert [name for name, item in judged.items() if item['status'] == 'not_applicable'] == ['crosstalk']
    assert graded['reasons']['diffusion_model'] == 'one_component_needs_free_and_bound_reference_values' and graded['reasons']['fit_model'] == 'fit_model_not_stated'
    assert graded['reasons']['labelled_range'] == 'labelled_concentration_recorded_for_the_sheet' and graded['reasons']['concentration_series'] == 'kd_or_series_missing'
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
    # a Greek mu (U+03BC) where the passage has a micro sign (U+00B5), a plain 'um2' where it has a micro sign and a superscript two, a
    # plus-minus replaced by '+/-' and a Latin t for a Greek tau are not in the chunk
    with pytest.raises(ExtractionRefused, match='laser_power:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'laser_power', quote='a laser power of 5 μW at the sample'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='free_diffusion_coefficient:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'free_diffusion_coefficient', quote='D = 280 um2/s'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'kd', quote='KD = 5 +/- 1 nM'), REAL)
    with pytest.raises(ExtractionRefused, match='readout_signal:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'readout_signal', quote='comparing the apparent tD obtained by the fit'), REAL)
    # a short quote that the paragraph holds twice is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='labelled_concentration:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'labelled_concentration', quote='fluorescent'), REAL)
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                      # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'free_diffusion_time', unit='s'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'free_diffusion_coefficient', unit='cm2/s'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'laser_power', unit='percent'), SYNTHETIC)       # a power in percent of the maximum is not this field
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'brightness', unit='nM'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='stern_volmer'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, DIFFUSION_MODEL, value='three_component'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, READOUT_SIGNAL, value='anisotropy'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'equilibrium_reached', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'mass_ratio'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='titration_point_count.value:schema'):
        validate_answer(wrong(answer, 'titration_point_count', value=12.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='measurement_repeat_count.value:schema'):
        validate_answer(wrong(answer, 'measurement_repeat_count', value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=3.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='particle_number:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'particle_number', value=-0.8), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='mass_ratio:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'mass_ratio', value=0.0), SYNTHETIC)
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


def test_a_picomolar_a_micromolar_labelled_partner_a_millisecond_time_and_a_milliwatt_power_are_in_the_vocabulary():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 94, 'unit': 'pM', 'quote': 'KD = 20 nM'}
    answer['labelled_concentration'] = {**answer['labelled_concentration'], 'value': 0.002, 'unit': 'uM'}
    answer['free_diffusion_time'] = {**answer['free_diffusion_time'], 'value': 0.06, 'unit': 'ms'}
    answer['bound_diffusion_time'] = {**answer['bound_diffusion_time'], 'value': 0.108, 'unit': 'ms'}
    answer['laser_power'] = {**answer['laser_power'], 'value': 0.005, 'unit': 'mW'}
    answer['measurement_time'] = {**answer['measurement_time'], 'value': 0.5, 'unit': 'min'}
    answer['incubation_time'] = {**answer['incubation_time'], 'unit': 'h'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'pM' and record['quantities']['free_diffusion_time']['unit'] == 'ms' and record['quantities']['laser_power']['unit'] == 'mW'
    graded = grade_fcs(record)
    assert graded['native']['labelled_nM'] == pytest.approx(2.0) and graded['native']['diffusion_ratio'] == pytest.approx(1.8) and graded['native']['acquisition_total_s'] == pytest.approx(150.0)


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
    support = {'kd': 'implied', 'labelled_concentration': 'about_something_else', SERIES: 'implied', FIT_MODEL: 'about_something_else', DIFFUSION_MODEL: 'implied',
               'equilibrium_reached': 'implied', 'single_estimate_method': 'about_something_else'}
    answer = validate_answer(answer_from(SYNTHETIC, SYNTHETIC_STATED, support), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['quantities']['labelled_concentration']['support'] == 'about_something_else'
    assert record['quantities']['free_diffusion_time']['support'] == 'direct' and record['concentration_series']['support'] == 'implied'
    assert record['facts']['equilibrium_reached']['support'] == 'implied' and record['facts']['single_estimate_method']['support'] == 'about_something_else'
    assert record['facts']['triplet_state_modelled']['support'] == 'direct'
    assert set(record['choice_support']) == set(extraction.CHOICES)
    assert record['choice_support'] == {SPREAD_KIND: 'direct', FIT_MODEL: 'about_something_else', DIFFUSION_MODEL: 'implied', READOUT_SIGNAL: 'direct'}
    sparse = record_from_answer(validate_answer(real_answer(), REAL), REAL, 0, 'exp', 'src', 'hyp')
    assert sparse['quantities']['free_diffusion_time']['support'] is None and sparse['facts']['triplet_state_modelled']['support'] is None
    assert sparse['choice_support'] == {SPREAD_KIND: None, FIT_MODEL: None, DIFFUSION_MODEL: 'direct', READOUT_SIGNAL: 'direct'}
    assert grade_fcs(record)['native']['support']['fit_model'] == ['about_something_else']      # the grader keeps the support of what a criterion reads
