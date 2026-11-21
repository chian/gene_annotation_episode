"""The SEC (size-exclusion chromatography, with or without MALS) extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_sec_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_extraction import (
    CHOICES, COLUMN_TYPE, DETECTION, NOT_EXTRACTED, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import (
    COLUMN_TYPES, DETECTIONS, FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.sec_passages import (
    REAL, REAL_ALLOWED, REAL_COUNT, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_criteria import SEC_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_grader import CRITERIA, grade_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import sec_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the spread of the KD, the molar mass of the larger component
# alone, the elution volume of the later-eluting component, the flow rate, the temperature, the incubation, the single estimate method, and the choices are kept in the record
# for the reviewer. The injected volume, the column volume and the smaller component's mass are read (the load, the shift and the mass criteria declare them).
KEPT = {'kd_spread', 'component_mass_measured_larger', 'component_elution_volume_later', 'flow_rate', 'run_temperature', 'incubation_time',
        'single_estimate_method', *CHOICES}


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
    for record in (sec_cases.synthetic_record(), sec_cases.qualitative_record(), sec_cases.sparse_record(), sec_cases.real_record(), sec_cases.weak_complex_record()):
        grade_sec(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, COLUMN_TYPE, DETECTION, SPREAD_KIND, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form and len(form) == 35
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'support', 'reason'}
        assert field['properties']['support']['anyOf'][0]['enum'] == ['direct', 'implied', 'about_something_else'] and field['properties']['support']['anyOf'][1] == {'type': 'null'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == set(QUANTITIES)


def test_an_sec_has_an_apparent_kd_field_and_the_sec_items_but_no_other_binding_constant():
    names = set(field_names())
    assert not {'ki', 'ic50', 'ec50', 'bmax', 'kon', 'koff', 'concentration_series', 'fold_enrichment'} & names
    assert {'kd', 'kd_spread', 'complex_elution_volume', 'component_elution_volume_earlier', 'component_elution_volume_later', 'elution_volume_shift', 'complex_mass_measured', 'complex_mass_theoretical',
            'component_mass_measured_larger', 'component_mass_measured_smaller', 'stoichiometry_ratio', 'polydispersity', 'flow_rate', 'run_temperature', 'loaded_concentration', 'loaded_volume', 'column_volume',
            'salt_concentration', 'incubation_time', 'replicate_count', 'complex_peak_detected', 'components_run_alone', 'complex_peak_analysed_by_sds_page', 'free_peak_decreases_with_titration',
            'mals_mass_matches_complex', 'column_calibrated_with_standards', 'buffer_rules_out_resin_interaction', 'complex_stable_on_column', 'aggregation_absent', 'single_component_control_done',
            'independent_experiments', 'single_estimate_method'} <= names


def test_the_descriptions_keep_the_confusable_fields_apart_and_the_kd_is_the_experiments_own():
    meaning = extraction.MEANING
    assert 'previously reported property of the proteins' in meaning['kd'] and 'comes from another method' in meaning['kd'] and 'A concentration at which a complex was seen is not this field' in meaning['kd']
    assert 'is not a half-width' in meaning['kd_spread']
    assert 'A mass of a component alone' in meaning['complex_mass_measured'] and 'a mass the complex is expected to have are not this field' in meaning['complex_mass_measured']
    assert 'The theoretical mass of one component' in meaning['complex_mass_theoretical'] and 'you would have to add up' in meaning['complex_mass_theoretical']
    assert 'several concentrations or conditions without saying which one is the result' in meaning['component_mass_measured_larger']
    assert 'A shift you would have to calculate' in meaning['elution_volume_shift'] and 'a time is not offered' in meaning['complex_elution_volume']
    assert 'The ratio in which the proteins were mixed is not the stoichiometry of the complex' in meaning['stoichiometry_ratio']
    assert 'mg/mL' in meaning['loaded_concentration'] and 'unit_not_in_vocabulary' in meaning['loaded_concentration']
    assert 'A divalent cation' in meaning['salt_concentration'] and 'added to test its effect on the interaction' in meaning['salt_concentration']
    assert 'Fractions of one run' in meaning['replicate_count']
    assert 'A single peak, with no statement of aggregation or of a polydispersity, is not this fact' in meaning['aggregation_absent']
    assert 'Running each component alone is not this fact' in meaning['single_component_control_done']
    assert 'a peak that eluted earlier but that the passage ascribes to aggregation'.lower() in meaning['complex_peak_detected'].lower()


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((COLUMN_TYPE, COLUMN_TYPES), (DETECTION, DETECTIONS), (SPREAD_KIND, SPREAD_KINDS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['kd'] == ('pM', 'nM', 'uM', 'mM') and UNITS['complex_elution_volume'] == UNITS['elution_volume_shift'] == ('mL',) and UNITS['complex_mass_measured'] == ('kDa',)
    assert UNITS['flow_rate'] == ('mL/min',) and UNITS['loaded_concentration'] == ('nM', 'uM', 'mM') and UNITS['loaded_volume'] == ('uL', 'mL') and UNITS['stoichiometry_ratio'] == UNITS['polydispersity'] == ('ratio',)
    assert COLUMN_TYPES == ('superdex', 'superose', 'srt', 'other') and DETECTIONS == ('absorbance_280', 'absorbance_260', 'refractive_index', 'light_scattering', 'fluorescence', 'other')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the record keeps."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == KEPT


def test_the_criteria_read_only_extracted_fields():
    declared = {read.split('.')[-1] for criterion in SEC_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_sec(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')   # the grader records the numbers, the sheet side judges them
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['interaction'] == 'detected' and native['kd_nM'] == 200 and native['loaded_nM'] == 5000 and native['salt_mM'] == 150 and native['shift_ml'] == 1.3
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'an apparent KD of 200 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 24) + ' of the source', 'quote': 'an apparent KD of 200 nM'}
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS) and record['experiment_type'] == 'sec'
    assert (record['column_type'], record['detection'], record['spread_kind']) == ('superdex', 'light_scattering', 'standard_error')
    quantities = record['quantities']
    assert quantities['kd']['value'] == 200 and quantities['kd']['unit'] == 'nM' and quantities['kd_spread']['value'] == 20 and quantities['complex_elution_volume']['unit'] == 'mL'
    assert quantities['complex_mass_measured']['value'] == 52 and quantities['complex_mass_theoretical']['value'] == 54 and quantities['loaded_concentration']['unit'] == 'uM' and quantities['loaded_volume']['unit'] == 'uL'
    assert quantities['flow_rate']['unit'] == 'mL/min' and quantities['run_temperature']['value'] == 4 and quantities['polydispersity']['value'] == 1.02 and quantities['stoichiometry_ratio']['value'] == 1
    assert quantities['replicate_count']['value'] == 3 and quantities['incubation_time']['unit'] == 'min'
    assert all(item['answer'] == 'yes' for item in record['facts'].values())


def test_the_span_counts_bytes_not_characters():
    quote = 'and 4 °C'       # the degree sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'an apparent KD of 200 nM'       # the degree sign and the two micro signs before it are two bytes each
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 3 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote)
    quote = '5 µM each'       # the degree sign and the micro sign of '500 µL' before it, and its own micro sign, are two bytes each
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 2 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    assert len(REAL) == 2524 and len(REAL.encode()) > len(REAL) and 'Quaternary structure' not in REAL    # the real paragraph holds non-breaking spaces, the minus sign, the tilde operator and the plus-minus sign; the legend of Figure 4 is not in it
    quote = 'a measured molecular weight of 13.6\xa0± 0.2\xa0kDa'
    start, end = quote_span(REAL, quote)
    assert REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 3 and start == len(REAL[:REAL.index(quote)].encode())
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    assert [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point'] == ['complex_mass_measured', 'component_mass_measured_larger', 'stoichiometry_ratio']
    assert [name for name in QUANTITIES if record['quantities'][name]['status'] == 'unavailable' and record['quantities'][name]['reason'] != 'not_stated_in_passage'] == []
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['complex_peak_detected', 'components_run_alone', 'complex_peak_analysed_by_sds_page', 'complex_stable_on_column']
    assert (record['column_type'], record['detection'], record['spread_kind']) == (None, 'light_scattering', None)
    graded = grade_sec(record)
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['complex_peak_observed', 'components_alone', 'complex_composition', 'complex_stable_on_column']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert graded['native']['kd_nM'] is None and graded['native']['interaction'] == 'detected'
    assert record['quantities']['stoichiometry_ratio']['support'] == 'implied' and record['quantities']['complex_mass_measured']['support'] == 'direct' and record['quantities']['kd']['support'] is None
    assert record['facts']['complex_peak_detected']['support'] == 'direct' and record['choice_support'][DETECTION] == 'direct' and record['choice_support'][COLUMN_TYPE] is None
    assert graded['reasons']['elution_shift'] == 'elution_shift_not_given' and graded['reasons']['mals_mass'] == 'fact_unknown' and graded['reasons']['stoichiometry'] == 'no_apparent_kd_reported'
    assert set(REAL_STATED) == set(REAL_ALLOWED) < set(field_names())
    for name, (value, unit, _) in REAL_STATED.items():
        assert (value, unit) in REAL_ALLOWED[name]


def real_with_count():
    """The real answer that also states a number the paragraph does not give as a replicate count: the form can hold it, the real run must not state it."""
    return answer_from(REAL, {**REAL_STATED, 'replicate_count': REAL_COUNT})


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'kd', quote='an apparent KD of 250 nM'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(answer, twice)
    # a plain 'deg C' where the passage has the degree sign, and a Greek mu (U+03BC) where it has the micro sign (U+00B5), are not in the chunk
    with pytest.raises(ExtractionRefused, match='run_temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'run_temperature', quote='and 4 degC'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='loaded_volume:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'loaded_volume', quote='A 500 μL sample'), SYNTHETIC)
    # a plain space where the real paragraph has the non-breaking space is not in the chunk
    with pytest.raises(ExtractionRefused, match='component_mass_measured_larger:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'component_mass_measured_larger', quote='a measured molecular weight of 13.6 ± 0.2 kDa'), REAL)
    # a short quote that the real paragraph holds more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='replicate_count:quote_occurs_more_than_once'):
        validate_answer(real_with_count(), REAL)                                                            # the paragraph has 'Figure' many times
    with pytest.raises(ExtractionRefused, match='complex_peak_detected:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'complex_peak_detected', quote='the mixed sample'), REAL)      # 'the mixed sample' is also the start of 'the mixed samples'
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    for name, unit in (('kd', 'M'), ('kd_spread', 'percent'), ('complex_elution_volume', 'min'), ('complex_mass_measured', 'Da'), ('flow_rate', 'mL'), ('loaded_concentration', 'mg/mL'), ('loaded_volume', 'L'), ('salt_concentration', 'percent'),
                       ('incubation_time', 'days'), ('polydispersity', 'percent'), ('replicate_count', 'ratio')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, unit=unit), SYNTHETIC)
    for name, value in ((COLUMN_TYPE, 'sepharose'), (DETECTION, 'mass_spectrometry'), (SPREAD_KIND, 'range')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, value=value), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'complex_peak_detected', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'components_run_alone'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'ic50': {'status': 'unavailable', 'value': None, 'unit': None, 'quote': None, 'reason': 'not_stated_in_passage'}}, SYNTHETIC)   # an SEC has no IC50
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='polydispersity:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'polydispersity', value=-1.02), SYNTHETIC)


def test_a_field_is_stated_with_its_quote_or_unavailable_with_a_reason_and_nothing_else():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:stated_has_value_unit_quote_span_and_no_reason'):
        validate_answer(wrong(answer, 'kd', quote=None), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', reason='not_stated_in_passage'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None), SYNTHETIC)


def test_a_stated_field_needs_a_support_from_the_vocabulary_and_an_unavailable_one_has_none():
    answer = synthetic_answer()
    for name in ('kd', 'complex_mass_measured', COLUMN_TYPE, 'complex_peak_detected'):       # a quantity, a mass, a choice and a fact
        with pytest.raises(ExtractionRefused, match=name + ':stated_has_value_unit_quote_span_and_no_reason'):
            validate_answer(wrong(answer, name, support=None), SYNTHETIC)
        with pytest.raises(ExtractionRefused, match=name + '.support:schema'):
            validate_answer(wrong(answer, name, support='strong'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)      # support kept on an unavailable field
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: {key: value for key, value in item.items() if key != 'support'} if name == 'kd' else item for name, item in answer.items()}, SYNTHETIC)
    for support in ('direct', 'implied', 'about_something_else'):
        assert validate_answer(wrong(answer, 'kd', support=support), SYNTHETIC)


def test_the_record_carries_the_support_of_every_stated_value():
    answer = synthetic_answer()
    answer['kd']['support'], answer['complex_mass_measured']['support'], answer[COLUMN_TYPE]['support'] = 'implied', 'about_something_else', 'implied'
    answer['complex_peak_detected']['support'] = 'about_something_else'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['quantities']['complex_mass_measured']['support'] == 'about_something_else' and record['quantities']['kd_spread']['support'] == 'direct'
    assert record['facts']['complex_peak_detected']['support'] == 'about_something_else' and record['facts']['components_run_alone']['support'] == 'direct'
    assert record['choice_support'][COLUMN_TYPE] == 'implied' and record['choice_support'][DETECTION] == 'direct' and set(record['choice_support']) == set(CHOICES)
    blank = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert blank['quantities']['kd']['support'] is None and blank['facts']['complex_peak_detected']['support'] is None and set(blank['choice_support'].values()) == {None}
    assert grade_sec(record)['native']['support']['complex_peak_observed'] == ['about_something_else']      # the grader keeps it for the sheet


def test_every_synthetic_field_is_stated_so_the_test_passage_covers_the_whole_form():
    assert set(SYNTHETIC_STATED) == set(field_names())
    assert answer_from(SYNTHETIC, {})['kd']['status'] == 'unavailable'


def test_every_synthetic_quote_occurs_exactly_once_and_says_its_value():
    for name, (value, unit, quote) in SYNTHETIC_STATED.items():
        assert quote_span(SYNTHETIC, quote) is not None, name
    assert validate_answer(synthetic_answer(), SYNTHETIC)


def test_every_real_quote_occurs_exactly_once():
    for name, (value, unit, quote) in REAL_STATED.items():
        assert quote_span(REAL, quote) is not None, name


def test_other_units_of_the_vocabulary_are_accepted_and_reach_the_record():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 0.2, 'unit': 'uM'}
    answer['incubation_time'] = {**answer['incubation_time'], 'value': 0.5, 'unit': 'h'}
    answer['run_temperature'] = {**answer['run_temperature'], 'value': 277.15, 'unit': 'K'}
    answer['loaded_concentration'] = {**answer['loaded_concentration'], 'value': 5000, 'unit': 'nM'}
    answer['salt_concentration'] = {**answer['salt_concentration'], 'value': 0.15, 'unit': 'M'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'uM' and record['quantities']['run_temperature']['unit'] == 'K' and record['quantities']['salt_concentration']['unit'] == 'M'
    graded = grade_sec(record)
    assert graded['native']['kd_nM'] == pytest.approx(200.0) and graded['native']['loaded_nM'] == pytest.approx(5000.0) and graded['native']['salt_mM'] == pytest.approx(150.0)
