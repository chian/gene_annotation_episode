"""The MST extraction is derived from the MST grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_mst_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_extraction import (
    ASSAY_FORMAT, CAPILLARY_TYPE, FIT_MODEL, LABEL_TYPE, NOT_EXTRACTED, READOUT_SIGNAL, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_record import (
    ASSAY_FORMATS, CAPILLARY_TYPES, FACTS, FIT_MODELS, LABEL_TYPES, PREPARATION_KEYS, QUANTITIES, READOUT_SIGNALS, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.mst_passages import (
    REAL, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_grader import (
    CRITERIA, grade_mst)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import mst_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the effect's
# variance is built from the two spreads by the converter, and the two powers, the temperature and the buffer additive are kept
# in the record for the reviewer.
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'ki_spread', 'led_power', 'ir_laser_power', 'temperature', 'detergent_or_carrier_in_buffer'}


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
    for record in (mst_cases.synthetic_record(), mst_cases.sparse_record(), mst_cases.real_record()):
        grade_mst(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))
            or name in (ASSAY_FORMAT, SPREAD_KIND, FIT_MODEL, 'concentration_series', READOUT_SIGNAL, CAPILLARY_TYPE, LABEL_TYPE)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, ASSAY_FORMAT, SPREAD_KIND, FIT_MODEL, READOUT_SIGNAL, CAPILLARY_TYPE, LABEL_TYPE, *FACTS}
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
    assert properties[ASSAY_FORMAT]['properties']['value']['anyOf'][0]['enum'] == list(ASSAY_FORMATS)
    assert properties[SPREAD_KIND]['properties']['value']['anyOf'][0]['enum'] == list(SPREAD_KINDS)
    assert properties[FIT_MODEL]['properties']['value']['anyOf'][0]['enum'] == list(FIT_MODELS)
    assert properties[READOUT_SIGNAL]['properties']['value']['anyOf'][0]['enum'] == list(READOUT_SIGNALS)
    assert properties[CAPILLARY_TYPE]['properties']['value']['anyOf'][0]['enum'] == list(CAPILLARY_TYPES)
    assert properties[LABEL_TYPE]['properties']['value']['anyOf'][0]['enum'] == list(LABEL_TYPES)
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
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_criteria import MST_CRITERIA
    declared = {read.split('.')[-1] for criterion in MST_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_mst(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')
    native = graded['native']
    assert native['kd_nM'] == 20 and native['ki_nM'] == 40 and native['ec50_nM'] == 31
    assert native['labelled_nM'] == 5 and native['labelled_over_kd'] == pytest.approx(0.25) and native['fhot_s'] == pytest.approx(1.5) and native['incubation_min'] == 15
    assert native['concentration_count'] == 12 and native['concentration_high_over_constant'] == pytest.approx(102.4)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 10) + ' of the source', 'quote': 'KD = 20 nM'}
    assert record['concentration_series']['value'][-1] == 2048 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'mst' and record['fit_model'] == 'quadratic' and record['spread_kind'] == 'standard_error'
    assert record['assay_format'] == 'direct_titration' and record['readout_signal'] == 'thermophoresis' and record['capillary_type'] == 'hydrophilic' and record['label_type'] == 'covalent_nhs_dye'
    assert record['quantities']['fnorm_amplitude']['unit'] == 'permille' and record['quantities']['fnorm_amplitude']['value'] == 12
    assert record['quantities']['fhot_time']['unit'] == 's' and record['quantities']['temperature']['unit'] == 'C' and record['quantities']['led_power']['unit'] == 'percent'
    assert record['quantities']['fnorm_noise']['unit'] == 'permille' and record['quantities']['fnorm_noise']['value'] == 0.7
    assert record['quantities']['signal_to_noise']['unit'] == 'ratio' and record['quantities']['titration_point_count']['value'] == 12


def test_the_span_counts_bytes_not_characters():
    start, end = quote_span(SYNTHETIC, 'at 25 °C')       # the micro sign before it is two bytes
    assert start == SYNTHETIC.index('at 25 °C') + 1 and SYNTHETIC.encode()[start:end].decode() == 'at 25 °C' and end - start == len('at 25 °C') + 1
    quote = 'The change of Fnorm was 12 ‰'       # the micro and degree signs before it are two bytes each; its own per-mille sign is three bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 2 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    quote = 'a concentration range from 100 μM to 3.05 nM'       # a right single quotation mark (3 bytes) comes before it; its own mu is two bytes
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 2 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None
    assert quote_span(REAL, 'following the manufacturer’s protocol') is not None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['labelled_concentration', 'led_power', 'incubation_time', 'replicate_count']
    assert record['quantities']['kd']['value'] is None and record['quantities']['kd']['reason'] == 'not_stated_in_passage'
    assert record['quantities']['ir_laser_power']['reason'] == 'not_stated_in_passage'      # 'medium MST power' is not a number
    assert record['concentration_series']['status'] == 'unavailable'                          # the ligand series is a range, not a list
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['detergent_or_carrier_in_buffer']
    assert record['fit_model'] == '1:1' and record['label_type'] == 'covalent_nhs_dye'
    assert record['assay_format'] is None and record['spread_kind'] is None and record['readout_signal'] is None and record['capillary_type'] is None
    graded = grade_mst(record)
    judged = {name: _criterion(graded, name) for name in CRITERIA}
    assert 'conflicting' not in {item['status'] for item in judged.values()}
    assert [name for name, item in judged.items() if item['status'] == 'supported'] == []      # the 1:1 model is stated but no constant is reported: it has no span to rest on
    assert graded['reasons']['fit_model'] == 'model_stated_without_a_reported_constant'
    assert graded['reasons']['labelling_scheme'] == 'label_not_shown_harmless' and graded['reasons']['labelled_concentration'] == 'labelled_or_kd_missing'
    assert graded['reasons']['readout_window'] == 'readout_signal_not_stated' and graded['native']['incubation_min'] == 10
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
    # an ordinary u where the paper has a Greek mu, or a straight apostrophe where it has a right single quotation mark, is not in the chunk
    with pytest.raises(ExtractionRefused, match='led_power:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'led_power', quote='range from 100 uM to 3.05 nM'), REAL)
    with pytest.raises(ExtractionRefused, match='label_type:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), LABEL_TYPE, quote="following the manufacturer's protocol"), REAL)
    # a short quote that the paragraph holds twice is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='label_type:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), LABEL_TYPE, quote='NHS-RED'), REAL)
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                      # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fnorm_amplitude', unit='percent'), SYNTHETIC)    # the Fnorm change is in per mille
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'signal_to_noise', unit='permille'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fhot_time', unit='min'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'ir_laser_power', unit='mW'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='bivalent_analyte'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, READOUT_SIGNAL, value='soret'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, CAPILLARY_TYPE, value='glass'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, LABEL_TYPE, value='quantum_dots'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ASSAY_FORMAT, value='kinetic'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'equilibrium_reached', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'ki'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='titration_point_count.value:schema'):
        validate_answer(wrong(answer, 'titration_point_count', value=12.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=3.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fnorm_amplitude:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'fnorm_amplitude', value=-1), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='ec50:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'ec50', value=0.0), SYNTHETIC)
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


def test_a_picomolar_a_millisecond_and_a_time_unit_answer_are_in_the_vocabulary():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 94, 'unit': 'pM', 'quote': 'KD = 20 nM'}
    answer['fhot_time'] = {**answer['fhot_time'], 'value': 1500, 'unit': 'ms'}
    answer['incubation_time'] = {**answer['incubation_time'], 'unit': 'h'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'pM' and record['quantities']['fhot_time']['unit'] == 'ms' and record['quantities']['incubation_time']['unit'] == 'h'
    assert grade_mst(record)['native']['fhot_s'] == pytest.approx(1.5)


def test_the_schema_has_a_support_field_with_the_three_values_on_every_field():
    for name, field in answer_schema()['properties'].items():
        assert 'support' in field['required']
        assert field['properties']['support']['anyOf'][0]['enum'] == ['direct', 'implied', 'about_something_else']


def test_a_stated_field_needs_a_support_from_the_vocabulary_and_an_unavailable_one_has_none():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:stated_has_value_unit_quote_span_and_no_reason'):
        validate_answer(wrong(answer, 'kd', support=None), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd.support:schema'):
        validate_answer(wrong(answer, 'kd', support='strong'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)
    for support in ('direct', 'implied', 'about_something_else'):
        assert validate_answer(wrong(answer, 'kd', support=support), SYNTHETIC)


def test_the_record_carries_the_support_of_every_stated_value():
    supports = {'kd': 'implied', 'incubation_time': 'about_something_else', 'equilibrium_reached': 'implied', FIT_MODEL: 'about_something_else', SERIES: 'implied'}
    answer = validate_answer(answer_from(SYNTHETIC, SYNTHETIC_STATED, supports), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['quantities']['incubation_time']['support'] == 'about_something_else'
    assert record['quantities']['replicate_count']['support'] == 'direct' and record['concentration_series']['support'] == 'implied'
    assert record['facts']['equilibrium_reached']['support'] == 'implied' and record['facts']['tight_binding_considered']['support'] == 'direct'
    assert record['choice_support'][FIT_MODEL] == 'about_something_else' and record['choice_support'][ASSAY_FORMAT] == 'direct'
    sparse = record_from_answer(validate_answer(real_answer(), REAL), REAL, 0, 'exp', 'src', 'hyp')
    assert sparse['quantities']['ki']['support'] is None and sparse['facts']['equilibrium_reached']['support'] is None and sparse['choice_support'][ASSAY_FORMAT] is None
