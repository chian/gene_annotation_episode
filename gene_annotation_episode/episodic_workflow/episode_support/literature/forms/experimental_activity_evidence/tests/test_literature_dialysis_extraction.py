"""The equilibrium dialysis / ultrafiltration extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_dialysis_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_extraction import (
    CHOICES, DETECTION, DEVICE, FIT_MODEL, NOT_EXTRACTED, SEPARATION, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import (
    DETECTIONS, DEVICE_TYPES, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SEPARATION_METHODS, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.dialysis_passages import (
    REAL, REAL_ALLOWED, REAL_COUNT, REAL_RESULT, REAL_RESULT_ALLOWED, REAL_RESULT_STATED, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, real_result_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_criteria import DIALYSIS_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import CRITERIA, grade_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import dialysis_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the spreads of the KD and the Ki, the membrane cutoff, the temperature, the pH, the volumes of the
# two chambers, the number of cells, the single estimate method, the concentration series (read as a top-level operand, not through quantities or facts) and the choices are kept in the record for the reviewer
# (or read by the converter).
KEPT = {'kd_spread', 'ki_spread', 'membrane_cutoff', 'run_temperature', 'buffer_ph', 'protein_chamber_volume', 'buffer_chamber_volume', 'technical_replicate_count', 'single_estimate_method', SERIES, *CHOICES}


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
    for record in (dialysis_cases.synthetic_record(), dialysis_cases.qualitative_record(), dialysis_cases.sparse_record(), dialysis_cases.real_record(), dialysis_cases.real_kd_record(), dialysis_cases.low_binding_record()):
        grade_dialysis(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, SEPARATION, DEVICE, DETECTION, SPREAD_KIND, FIT_MODEL, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form and len(form) == 46
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'support', 'reason'}
        assert field['properties']['support']['anyOf'][0]['enum'] == ['direct', 'implied', 'about_something_else'] and field['properties']['support']['anyOf'][1] == {'type': 'null'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == {*QUANTITIES, SERIES}


def test_the_form_has_the_kd_the_ki_and_the_bmax_as_separate_fields_and_the_fractions_as_four_fields():
    names = set(field_names())
    assert {'kd', 'ki', 'bmax', 'percent_bound', 'percent_unbound', 'fraction_bound', 'fraction_unbound', 'concentration_series', 'ligand_total_concentration', 'free_ligand_concentration', 'protein_concentration',
            'membrane_cutoff', 'equilibration_time', 'recovery', 'membrane_adsorption', 'volume_shift', 'separation_method', 'device_type', 'detection', 'fit_model', 'binding_detected', 'equilibrium_time_course_shown',
            'recovery_checked', 'adsorption_checked_and_corrected', 'volume_shift_corrected', 'ligand_stable', 'free_ligand_measured_directly', 'protein_retained', 'buffer_only_control_equal', 'protein_at_or_above_kd',
            'independent_experiments', 'single_estimate_method'} <= names
    assert not {'ic50', 'kon', 'koff', 'hill_slope', 'elution_volume_shift'} & names


def test_the_descriptions_keep_the_confusable_fields_apart_and_the_kd_is_the_experiments_own():
    meaning = extraction.MEANING
    assert 'known or previously reported property' in meaning['kd'] and 'from another method' in meaning['kd'] and 'An association constant Ka' in meaning['kd'] and 'a Ki, an IC50' in meaning['kd']
    assert 'is not a half-width' in meaning['kd_spread'] and 'belongs to the Ki, not to the KD' in meaning['ki_spread']
    assert 'A percent unbound' in meaning['percent_bound'] and 'A percent bound' in meaning['percent_unbound'] and 'A percent is not offered here' in meaning['fraction_bound'] and 'A percent is not offered here' in meaning['fraction_unbound']
    assert 'conditions without saying which one is the result' in meaning['percent_bound']
    assert 'A series of concentrations' in meaning['ligand_total_concentration'] and 'total minus the bound' in meaning['free_ligand_concentration'] and 'total minus the free' in meaning['bound_ligand_concentration']
    assert 'mg/mL' in meaning['protein_concentration'] and 'unit_not_in_vocabulary' in meaning['protein_concentration'] and 'stock solution' in meaning['protein_concentration']
    assert 'ligand-to-protein ratio is not a concentration' in meaning['ligand_range_lowest']
    assert 'the time allowed to reach equilibrium' in meaning['equilibration_time'] and 'hydration of the membrane' in meaning['equilibration_time']
    assert 'conductivity' in meaning['salt_concentration'] and 'phosphate-buffered saline with no concentration' in meaning['salt_concentration']
    assert 'not the volume of the protein stock' in meaning['protein_chamber_volume']
    assert 'A range of recoveries' in meaning['recovery'] and 'with no number' in meaning['membrane_adsorption']
    assert 'Independent experiments are not this field' in meaning['technical_replicate_count'] and 'Duplicate or triplicate cells' in meaning['replicate_count']
    assert 'A statement that the cell was kept for a time to reach equilibrium' in meaning['equilibrium_time_course_shown']
    assert 'only describes the method, with no result, does not state it' in meaning['binding_detected']
    assert 'only said to have been prepared, with no statement of its result' in meaning['buffer_only_control_equal']
    assert 'A linearised plot' in meaning['fit_model']
    assert 'includes the distinctive words of the one sentence' in meaning[DETECTION]
    assert 'Another method that the passage mentions for a different purpose' in meaning['single_estimate_method']


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((SEPARATION, SEPARATION_METHODS), (DEVICE, DEVICE_TYPES), (DETECTION, DETECTIONS), (SPREAD_KIND, SPREAD_KINDS), (FIT_MODEL, FIT_MODELS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert properties[SERIES]['properties']['value']['anyOf'][0] == {'type': 'array', 'items': {'type': 'number'}}
    assert UNITS['kd'] == UNITS['ki'] == ('pM', 'nM', 'uM', 'mM') and UNITS['membrane_cutoff'] == ('kDa',) and UNITS['percent_bound'] == UNITS['recovery'] == ('percent',) and UNITS['fraction_unbound'] == ('ratio',)
    assert UNITS['equilibration_time'] == ('min', 'h') and UNITS['buffer_ph'] == ('pH',) and UNITS['protein_chamber_volume'] == ('uL', 'mL') and UNITS['bmax'] == ('nM', 'uM', 'mM', 'ratio')
    assert SEPARATION_METHODS == ('equilibrium_dialysis', 'rapid_equilibrium_dialysis', 'ultrafiltration', 'ultracentrifugation')
    assert DETECTIONS == ('liquid_scintillation', 'lc_msms', 'fluorescence', 'absorbance', 'other') and FIT_MODELS == ('one_site', 'two_site', 'hill', 'other')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the record keeps."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == KEPT


def test_the_criteria_read_only_extracted_fields():
    declared = {read.split('.')[-1] for criterion in DIALYSIS_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_dialysis(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the sheet side judges the recorded numbers
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['interaction'] == 'detected' and native['kd_nM'] == 200 and native['ki_nM'] == 500 and native['protein_nM'] == 1000 and native['salt_mM'] == 150 and native['equilibration_h'] == 6
    assert native['bound_over_protein'] == pytest.approx(0.3) and native['protein_over_kd'] == pytest.approx(5.0) and native['concentration_count'] == 6
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'a KD of 200 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 14) + ' of the source', 'quote': 'a KD of 200 nM'}
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS) and record['experiment_type'] == 'dialysis'
    assert (record['separation_method'], record['device_type'], record['detection'], record['spread_kind'], record['fit_model']) == ('rapid_equilibrium_dialysis', 'red_device', 'lc_msms', 'standard_error', 'one_site')
    quantities = record['quantities']
    assert quantities['kd']['value'] == 200 and quantities['kd']['unit'] == 'nM' and quantities['bmax']['unit'] == 'ratio' and quantities['percent_bound']['value'] == 60 and quantities['fraction_unbound']['value'] == 0.4
    assert quantities['protein_concentration']['unit'] == 'uM' and quantities['membrane_cutoff']['value'] == 10 and quantities['buffer_ph']['unit'] == 'pH' and quantities['protein_chamber_volume']['unit'] == 'uL'
    assert quantities['recovery']['value'] == 95 and quantities['replicate_count']['value'] == 3 and quantities['technical_replicate_count']['value'] == 2 and quantities['titration_point_count']['value'] == 6
    assert record['concentration_series']['value'] == [50, 100, 200, 400, 800, 1600] and record['concentration_series']['unit'] == 'nM'
    assert all(item['answer'] == 'yes' for item in record['facts'].values())


def test_the_span_counts_bytes_not_characters():
    quote = 'at 37 °C'       # the degree sign is two bytes; the micro signs before it are two bytes each
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 3 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'PZ-2 at 1 µM'
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'the total volume in the dialysis cup was brought to 100 μL'
    start, end = quote_span(REAL, quote)
    assert REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1 and start == len(REAL[:REAL.index(quote)].encode())
    assert len(REAL.encode()) > len(REAL) and 'Strong binding' not in REAL and 'Blanks were prepared' in REAL and REAL.startswith('EqD experiments') and REAL.endswith('performed in duplicate.')
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraphs_state_only_what_they_state_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    assert [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point'] == ['membrane_cutoff', 'equilibration_time', 'buffer_ph', 'protein_chamber_volume', 'buffer_chamber_volume', 'technical_replicate_count']
    assert [name for name in QUANTITIES if record['quantities'][name]['status'] == 'unavailable' and record['quantities'][name]['reason'] != 'not_stated_in_passage'] == []
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['protein_retained']
    assert (record['separation_method'], record['device_type'], record['detection'], record['spread_kind'], record['fit_model']) == ('equilibrium_dialysis', 'dialysis_cup', None, None, None)
    graded = grade_dialysis(record)
    assert [name for name in graded['criteria'] if _criterion(graded, name)['status'] == 'supported'] == ['equilibrium', 'protein_retained']
    assert [name for name in graded['criteria'] if _criterion(graded, name)['status'] == 'conflicting'] == []
    assert graded['reasons']['equilibrium'] == 'equilibration_time_recorded_for_the_sheet' and graded['native']['interaction'] is None and graded['native']['kd_nM'] is None
    result = validate_answer(real_result_answer(), REAL_RESULT)
    kd_record = record_from_answer(result, REAL_RESULT, 0, 'exp', 'src', 'hyp')
    kd_graded = grade_dialysis(kd_record)
    assert kd_graded['native']['kd_nM'] == pytest.approx(97.0) and kd_graded['native']['interaction'] == 'detected' and kd_graded['native']['constant_name'] == 'kd'
    assert kd_record['choice_support'][SEPARATION] == 'implied' and kd_record['quantities']['kd']['support'] == 'direct' and kd_record['facts']['binding_detected']['support'] == 'direct'
    assert record['choice_support'][SEPARATION] == 'direct' and record['choice_support'][DEVICE] == 'direct' and record['choice_support'][DETECTION] is None
    assert record['quantities']['equilibration_time']['support'] == 'direct' and record['quantities']['kd']['support'] is None and record['concentration_series']['support'] is None
    assert set(REAL_STATED) == set(REAL_ALLOWED) < set(field_names()) and set(REAL_RESULT_STATED) == set(REAL_RESULT_ALLOWED) < set(field_names())
    for name, (value, unit, _) in REAL_STATED.items():
        assert (value, unit) in REAL_ALLOWED[name]
    for name, (value, unit, _) in REAL_RESULT_STATED.items():
        assert (value, unit) in REAL_RESULT_ALLOWED[name]


def real_with_count():
    """The real answer that also states a number the paragraphs do not give as a replicate count: the form can hold it, the real run must not state it."""
    return answer_from(REAL, {**REAL_STATED, 'replicate_count': REAL_COUNT})


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'kd', quote='a KD of 250 nM'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(answer, twice)
    # a plain 'deg C' where the passage has the degree sign, and a Greek mu (U+03BC) where it has the micro sign (U+00B5), are not in the chunk
    with pytest.raises(ExtractionRefused, match='run_temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'run_temperature', quote='at 37 degC'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='protein_chamber_volume:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'protein_chamber_volume', quote='The protein chamber held 100 μL'), SYNTHETIC)
    # a Latin micro sign where the real paragraph has the Greek mu is not in the chunk
    with pytest.raises(ExtractionRefused, match='protein_chamber_volume:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'protein_chamber_volume', quote='the total volume in the dialysis cup was brought to 100 µL'), REAL)
    # a short quote that the real paragraphs hold more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='replicate_count:quote_occurs_more_than_once'):
        validate_answer(real_with_count(), REAL)                                                            # the paragraphs have 'PFAS' many times
    with pytest.raises(ExtractionRefused, match='device_type:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'device_type', quote='dialysis cup'), REAL)                    # 'dialysis cup' names the device twice; 'A Slide-a-Lyzer mini dialysis cup' once
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    for name, unit in (('kd', 'M'), ('ki_spread', 'percent'), ('percent_bound', 'ratio'), ('fraction_bound', 'percent'), ('membrane_cutoff', 'Da'), ('equilibration_time', 'days'), ('buffer_ph', 'M'),
                       ('protein_concentration', 'mg/mL'), ('protein_chamber_volume', 'L'), ('salt_concentration', 'percent'), ('recovery', 'ratio'), ('replicate_count', 'ratio'), ('bmax', 'fmol/mg')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, unit=unit), SYNTHETIC)
    for name, value in ((SEPARATION, 'gel_filtration'), (DEVICE, 'plate'), (DETECTION, 'mass_spectrometry'), (SPREAD_KIND, 'range'), (FIT_MODEL, 'scatchard')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, value=value), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'binding_detected', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'protein_retained'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'ic50': {'status': 'unavailable', 'value': None, 'unit': None, 'quote': None, 'reason': 'not_stated_in_passage'}}, SYNTHETIC)   # a dialysis has no IC50
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='concentration_series.value:schema'):
        validate_answer(wrong(answer, SERIES, value=50), SYNTHETIC)                         # the series is a list
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='recovery:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'recovery', value=-95), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='concentration_series:number_must_be_above_zero'):
        validate_answer(wrong(answer, SERIES, value=[50, 0, 100]), SYNTHETIC)
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


def test_a_stated_field_needs_a_support_from_the_vocabulary_and_an_unavailable_one_has_none():
    answer = synthetic_answer()
    for name in ('kd', SERIES, SEPARATION, 'protein_retained'):       # a quantity, the series, a choice and a fact
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
    answer['kd']['support'], answer[SERIES]['support'], answer[SEPARATION]['support'] = 'implied', 'about_something_else', 'implied'
    answer['protein_retained']['support'] = 'about_something_else'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['concentration_series']['support'] == 'about_something_else' and record['quantities']['kd_spread']['support'] == 'direct'
    assert record['facts']['protein_retained']['support'] == 'about_something_else' and record['facts']['binding_detected']['support'] == 'direct'
    assert record['choice_support'][SEPARATION] == 'implied' and record['choice_support'][DEVICE] == 'direct' and set(record['choice_support']) == set(CHOICES)
    blank = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert blank['quantities']['kd']['support'] is None and blank['concentration_series']['support'] is None and blank['facts']['protein_retained']['support'] is None and set(blank['choice_support'].values()) == {None}
    assert grade_dialysis(record)['native']['support']['protein_retained'] == ['about_something_else']      # the grader keeps it for the sheet


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
    for name, (value, unit, quote) in REAL_RESULT_STATED.items():
        assert quote_span(REAL_RESULT, quote) is not None, name


def test_other_units_of_the_vocabulary_are_accepted_and_reach_the_record():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 0.2, 'unit': 'uM'}
    answer['equilibration_time'] = {**answer['equilibration_time'], 'value': 360, 'unit': 'min'}
    answer['run_temperature'] = {**answer['run_temperature'], 'value': 310.15, 'unit': 'K'}
    answer['protein_concentration'] = {**answer['protein_concentration'], 'value': 1000, 'unit': 'nM'}
    answer['salt_concentration'] = {**answer['salt_concentration'], 'value': 0.15, 'unit': 'M'}
    answer[SERIES] = {**answer[SERIES], 'value': [0.05, 0.1, 0.2, 0.4, 0.8, 1.6], 'unit': 'uM'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'uM' and record['quantities']['run_temperature']['unit'] == 'K' and record['quantities']['salt_concentration']['unit'] == 'M' and record[SERIES]['unit'] == 'uM'
    graded = grade_dialysis(record)
    assert graded['native']['kd_nM'] == pytest.approx(200.0) and graded['native']['protein_nM'] == pytest.approx(1000.0) and graded['native']['salt_mM'] == pytest.approx(150.0) and graded['native']['equilibration_h'] == pytest.approx(6.0)
    assert _criterion(graded, 'concentration_series')['status'] == 'supported'
