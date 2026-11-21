"""The SPA extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_spa_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_extraction import (
    ASSAY_FORMAT, BEAD_TYPE, CAPTURE, COUNTER, FIT_MODEL, ISOTOPE, NOT_EXTRACTED, PREPARATION_TYPE, SERIES, SPREAD_KIND, ExtractionRefused, answer_schema,
    field_names, quote_span, record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_record import (
    ASSAY_FORMATS, BEAD_TYPES, CAPTURE_METHODS, COUNTERS, FACTS, FIT_MODELS, ISOTOPES, PREPARATION_KEYS, PREPARATION_TYPES, QUANTITIES, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.spa_passages import (
    REAL, REAL_ALLOWED, REAL_KD, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_grader import (
    CRITERIA, grade_spa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import spa_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the effect's
# variance is built from the spreads by the converter; the specific activity, the amounts of beads and of target, the counting
# efficiency, the number of technical wells, the temperature, the isotope, the bead type, the capture method, the kind of
# preparation, the counter and the statement that only this method was used are kept in the record for the reviewer. The settling
# time is copied into the grader's native values (settling_min), so the grader reads it, but no criterion judges it (the fact that
# the settling was controlled does).
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'ki_spread', 'specific_activity', 'bead_amount', 'bead_concentration', 'receptor_amount', 'counting_efficiency', 'technical_replicate_count', 'temperature', ISOTOPE, BEAD_TYPE, CAPTURE, PREPARATION_TYPE, COUNTER, SPREAD_KIND, 'single_estimate_method'}


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
    for record in (spa_cases.synthetic_record(), spa_cases.sparse_record(), spa_cases.real_record()):
        grade_spa(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.')) or name in (ASSAY_FORMAT, FIT_MODEL, SERIES)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, ASSAY_FORMAT, ISOTOPE, BEAD_TYPE, CAPTURE, PREPARATION_TYPE, COUNTER, SPREAD_KIND, FIT_MODEL, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form and len(form) == 48
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'support', 'reason'}
        assert field['properties']['support']['anyOf'][0]['enum'] == ['direct', 'implied', 'about_something_else'] and field['properties']['support']['anyOf'][1] == {'type': 'null'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == {*QUANTITIES, SERIES}


def test_the_form_has_no_filter_and_no_wash_items_and_has_the_bead_items():
    names = set(field_names())
    assert not {'filter_binding_checked', 'wash_dissociation_considered', 'separation_method'} & names
    assert {'bead_type', 'capture_method', 'bead_amount', 'bead_concentration', 'bead_only_fraction', 'bead_only_control_done', 'nonproximity_signal_checked', 'homogeneous_no_wash_format',
            'quench_interference_checked', 'bead_settling_controlled', 'counting_efficiency', 'settling_time', 'counter'} <= names


def test_the_kd_the_ki_and_the_ic50_are_separate_fields_that_do_not_take_each_others_values():
    meaning = extraction.MEANING
    assert {'kd', 'bmax', 'ki', 'ic50'} <= set(field_names())
    assert 'An IC50 or a Ki is not this field' in meaning['kd'] and 'An IC50 is not this field, a KD is not this field' in meaning['ki']
    assert 'Ki or a KD is not this field' in meaning['ic50']


def test_the_radioligand_concentration_the_series_ends_the_nonspecific_ligand_and_the_beads_are_separate_fields_that_exclude_each_other():
    meaning = extraction.MEANING
    assert 'a concentration used in a saturation series' in meaning['radioligand_concentration'] and 'competition is not this field' in meaning['radioligand_range_lowest']
    assert 'competition is not this field' in meaning['radioligand_range_highest']
    assert 'competitor of a competition curve, or of the radioligand, is not this field' in meaning['nonspecific_ligand_concentration']
    assert 'A concentration of the unlabelled ligand is not this field' in meaning['nonspecific_excess']
    assert 'do not convert it' in meaning['bead_amount'] and 'do not convert it' in meaning['bead_concentration'] and 'do not convert it' in meaning['receptor_amount']
    assert 'non-specific binding defined with an excess of unlabelled ligand' in meaning['bead_only_fraction']
    assert 'Non-specific binding defined with an excess of unlabelled ligand is not this control' in meaning['bead_only_control_done']


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((ASSAY_FORMAT, ASSAY_FORMATS), (ISOTOPE, ISOTOPES), (BEAD_TYPE, BEAD_TYPES), (CAPTURE, CAPTURE_METHODS), (PREPARATION_TYPE, PREPARATION_TYPES),
                             (COUNTER, COUNTERS), (SPREAD_KIND, SPREAD_KINDS), (FIT_MODEL, FIT_MODELS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['specific_activity'] == ('Ci/mmol',) and UNITS['bmax'] == ('fmol/mg', 'pmol/mg', 'sites/cell', 'nM') and UNITS['kd'] == UNITS['ic50'] == ('pM', 'nM', 'uM', 'mM')
    assert UNITS['percent_bound'] == UNITS['nonspecific_fraction'] == UNITS['bead_only_fraction'] == UNITS['counting_efficiency'] == ('percent',) and UNITS['hill_slope'] == UNITS['nonspecific_excess'] == ('ratio',)
    assert UNITS['bead_amount'] == ('ug', 'mg') and UNITS['bead_concentration'] == ('mg/mL',) and UNITS['settling_time'] == UNITS['incubation_time'] == ('s', 'min', 'h')
    assert ISOTOPES == ('tritium', 'iodine_125', 'sulfur_35', 'other') and BEAD_TYPES == ('ysi', 'pvt', 'other') and CAPTURE_METHODS == ('wga', 'streptavidin_biotin', 'metal_chelate', 'antibody', 'other')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter or the record keep."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER_OR_KEPT


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_criteria import SPA_CRITERIA
    declared = {read.split('.')[-1] for criterion in SPA_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_spa(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the sheet side judges the recorded numbers
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['kd_nM'] == 2.0 and native['ki_nM'] == 5.0 and native['ic50_nM'] == 7.5 and native['constant_name'] == 'kd'
    assert native['incubation_min'] == 120 and native['settling_min'] == 30 and native['concentration_count'] == 10 and native['nonspecific_excess_ratio'] == 500
    assert native['concentration_low_over_kd'] == pytest.approx(0.05) and native['concentration_high_over_kd'] == pytest.approx(25.6)
    assert native['radioligand_over_kd'] == pytest.approx(0.5) and native['calculated_ki_nM'] == pytest.approx(5.0)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'a KD = 2.0 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 13) + ' of the source', 'quote': 'a KD = 2.0 nM'}
    assert record['concentration_series']['value'][-1] == 51.2 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'spa' and record['fit_model'] == 'one_site' and record['spread_kind'] == 'standard_error'
    assert record['assay_format'] == 'saturation' and record['radioligand_isotope'] == 'tritium' and record['bead_type'] == 'ysi' and record['capture_method'] == 'metal_chelate'
    assert record['preparation_type'] == 'purified_protein' and record['counter'] == 'microbeta'
    assert record['quantities']['bmax']['unit'] == 'fmol/mg' and record['quantities']['bmax']['value'] == 1200 and record['quantities']['hill_slope']['value'] == 1.0
    assert record['quantities']['specific_activity']['unit'] == 'Ci/mmol' and record['quantities']['specific_activity']['value'] == 85
    assert record['quantities']['bead_amount']['unit'] == 'mg' and record['quantities']['bead_amount']['value'] == 2 and record['quantities']['bead_concentration']['unit'] == 'mg/mL'
    assert record['quantities']['receptor_amount']['unit'] == 'ug' and record['quantities']['receptor_amount']['value'] == 0.5 and record['quantities']['percent_bound']['value'] == 6
    assert record['quantities']['nonspecific_fraction']['value'] == 25 and record['quantities']['bead_only_fraction']['value'] == 8 and record['quantities']['counting_efficiency']['value'] == 32
    assert record['quantities']['radioligand_concentration']['value'] == 1 and record['quantities']['nonspecific_ligand_concentration']['value'] == 1000
    assert record['quantities']['radioligand_range_lowest']['value'] == 0.1 and record['quantities']['radioligand_range_highest']['value'] == 51.2
    assert record['quantities']['technical_replicate_count']['value'] == 3 and record['quantities']['replicate_count']['value'] == 3
    assert record['quantities']['ki']['value'] == 5.0 and record['quantities']['ki_spread']['value'] == 0.3 and record['quantities']['ic50']['value'] == 7.5


def test_the_span_counts_bytes_not_characters():
    quote = 'at 25 °C'       # nothing multi-byte before it; its own degree sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = '0.5 µg of receptor protein'       # the degree sign before it is two bytes; its own micro sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    # the real paragraph has micro signs, a multiplication sign, an en dash, a degree sign, a greater-or-equal sign and curly quotes
    quote = 'addition of 100 µM unlabeled leucine'       # nothing multi-byte before it; its own micro sign (1 extra byte)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'ligand depletion was avoided by maintaining ≥20-fold molar excess'       # the paragraph has micro signs, multiplication signs, an en dash and a micro sign before it
    start, end = quote_span(REAL, quote)
    assert start > REAL.index(quote) and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 2       # its own greater-or-equal sign is three bytes
    quote = 'incubated for ~16 hr at 4°C with gentle agitation'       # its own degree sign is two bytes
    start, end = quote_span(REAL, quote)
    assert start > REAL.index(quote) and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    assert len(REAL) == 2519 and len(REAL.encode()) == 2519 + sum(len(c.encode()) - 1 for c in REAL)
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['specific_activity', 'bead_concentration', 'nonspecific_ligand_concentration', 'incubation_time', 'temperature']
    assert record['quantities']['specific_activity']['value'] == 25 and record['quantities']['bead_concentration']['value'] == 1.25
    assert record['quantities']['nonspecific_ligand_concentration']['value'] == 100 and record['quantities']['nonspecific_ligand_concentration']['unit'] == 'uM'
    assert record['quantities']['incubation_time']['value'] == 16 and record['quantities']['incubation_time']['unit'] == 'h' and record['quantities']['temperature']['value'] == 4
    for name in ('kd', 'bmax', 'ki', 'ic50', 'hill_slope', 'radioligand_concentration', 'bead_amount', 'receptor_amount', 'percent_bound', 'nonspecific_fraction', 'nonspecific_excess', 'bead_only_fraction', 'settling_time', 'replicate_count'):
        assert record['quantities'][name]['reason'] == 'not_stated_in_passage'
    assert record['quantities']['receptor_amount']['status'] == 'unavailable'                   # '0.3 µg/ml protein' is a concentration, not an amount per well
    assert record['concentration_series']['status'] == 'unavailable'
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['nonspecific_binding_determined', 'ligand_depletion_checked']
    assert record['assay_format'] is None and record['fit_model'] is None and record['spread_kind'] is None
    assert (record['radioligand_isotope'], record['bead_type'], record['capture_method'], record['preparation_type'], record['counter']) == ('tritium', 'ysi', 'metal_chelate', 'purified_protein', 'microbeta')
    assert record['choice_support'][CAPTURE] == 'implied' and record['choice_support'][ISOTOPE] == 'direct' and record['choice_support'][FIT_MODEL] is None
    assert record['quantities']['temperature']['support'] == 'direct' and record['quantities']['kd']['support'] is None
    graded = grade_spa(record)
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['ligand_depletion', 'nonspecific_binding']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and graded['reasons']['radioligand_range'] == 'kd_or_series_missing' and graded['reasons']['competition_radioligand_level'] == 'radioligand_concentration_or_kd_not_given'
    assert graded['native']['kd_nM'] is None and graded['native']['incubation_min'] == 960
    assert set(REAL_STATED) <= set(REAL_ALLOWED) < set(field_names()) and set(REAL_ALLOWED) == set(REAL_STATED)
    for name, (value, unit, _) in REAL_STATED.items():
        assert (value, unit) in REAL_ALLOWED[name]


def real_with_kd():
    """The real answer that also states a '10× Kd' as a KD (not in the allowed set): the form can hold it, the real run must not state it."""
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
        validate_answer(wrong(answer, 'receptor_amount', quote='0.5 μg of receptor protein'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'temperature', quote='at 25 degC'), SYNTHETIC)
    # the real paragraph has a micro sign (U+00B5): a Greek mu (U+03BC) and a plain 'u' are not in the chunk, and neither is a degree sign written as a word
    for quote in ('addition of 100 μM unlabeled leucine', 'addition of 100 uM unlabeled leucine'):
        with pytest.raises(ExtractionRefused, match='nonspecific_ligand_concentration:quote_is_not_in_the_chunk'):
            validate_answer(wrong(answer_from(REAL, REAL_STATED), 'nonspecific_ligand_concentration', quote=quote), REAL)
    with pytest.raises(ExtractionRefused, match='temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer_from(REAL, REAL_STATED), 'temperature', quote='at 4 degC with gentle agitation'), REAL)
    # a short quote that the paragraph holds more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(wrong(real_with_kd(), 'kd', quote='10× Kd'), REAL)                 # the paragraph has '10× Kd' twice
    with pytest.raises(ExtractionRefused, match='bead_concentration:quote_occurs_more_than_once'):
        validate_answer(wrong(answer_from(REAL, REAL_STATED), 'bead_concentration', quote='YSi-Cu His-tag SPA beads'), REAL)     # the bead name occurs four times
    with pytest.raises(ExtractionRefused, match='specific_activity:quote_occurs_more_than_once'):
        validate_answer(wrong(answer_from(REAL, REAL_STATED), 'specific_activity', quote='(25 Ci/mmol)'), REAL)                 # 25 Ci/mmol occurs twice
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
        validate_answer(wrong(answer, 'receptor_amount', unit='mg/mL'), SYNTHETIC)      # a protein concentration is not an amount per well
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'bead_amount', unit='mg/mL'), SYNTHETIC)          # a bead concentration is not an amount per well
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'bead_concentration', unit='mg'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'bmax', unit='nmol/mg'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'bead_only_fraction', unit='ratio'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'incubation_time', unit='days'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'settling_time', unit='days'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='stern_volmer'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ASSAY_FORMAT, value='direct_titration'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ISOTOPE, value='3H'), SYNTHETIC)                  # the vocabulary word is 'tritium'
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, BEAD_TYPE, value='scintillant_plate'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, CAPTURE, value='ni_chelate'), SYNTHETIC)          # the vocabulary word is 'metal_chelate'
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, COUNTER, value='scintillation_counter'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'nonlinear_fit_used', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'ic50'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'separation_method': {'status': 'unavailable', 'value': None, 'quote': None, 'reason': 'not_stated_in_passage'}}, SYNTHETIC)   # an SPA has no separation
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
    with pytest.raises(ExtractionRefused, match='kd:stated_has_value_unit_quote_span_and_no_reason'):
        validate_answer(wrong(answer, 'kd', quote=None), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', reason='not_stated_in_passage'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'kd', status='unavailable', value=None, unit=None, quote=None), SYNTHETIC)


def test_a_stated_field_needs_a_support_from_the_vocabulary_and_an_unavailable_one_has_none():
    answer = synthetic_answer()
    for name in ('kd', 'ic50', ASSAY_FORMAT, 'nonlinear_fit_used'):                       # a quantity, a choice and a fact
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
    answer['kd']['support'], answer['bmax']['support'], answer[ASSAY_FORMAT]['support'] = 'implied', 'about_something_else', 'implied'
    answer['nonlinear_fit_used']['support'], answer[SERIES]['support'] = 'about_something_else', 'implied'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['quantities']['bmax']['support'] == 'about_something_else' and record['quantities']['ki']['support'] == 'direct'
    assert record['concentration_series']['support'] == 'implied' and record['facts']['nonlinear_fit_used']['support'] == 'about_something_else'
    assert record['choice_support'][ASSAY_FORMAT] == 'implied' and record['choice_support'][FIT_MODEL] == 'direct' and set(record['choice_support']) == {ASSAY_FORMAT, ISOTOPE, BEAD_TYPE, CAPTURE, PREPARATION_TYPE, COUNTER, SPREAD_KIND, FIT_MODEL}
    blank = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert blank['quantities']['kd']['support'] is None and blank['concentration_series']['support'] is None and blank['facts']['nonlinear_fit_used']['support'] is None
    assert set(blank['choice_support'].values()) == {None}
    assert grade_spa(record)['native']['support']['nonlinear_fit'] == ['about_something_else']      # the grader keeps it for the sheet


def test_every_synthetic_field_is_stated_so_the_test_passage_covers_the_whole_form():
    assert set(SYNTHETIC_STATED) == set(field_names())
    assert answer_from(SYNTHETIC, {})['kd']['status'] == 'unavailable'


def test_every_synthetic_quote_occurs_exactly_once_and_says_its_value():
    for name, (value, unit, quote) in SYNTHETIC_STATED.items():
        assert quote_span(SYNTHETIC, quote) is not None, name
    assert validate_answer(synthetic_answer(), SYNTHETIC)


def test_other_units_of_the_vocabulary_are_accepted_and_reach_the_record():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 0.002, 'unit': 'uM', 'quote': 'a KD = 2.0 nM'}
    answer['ic50'] = {**answer['ic50'], 'value': 7500, 'unit': 'pM'}
    answer['bmax'] = {**answer['bmax'], 'value': 1.2, 'unit': 'pmol/mg'}
    answer['receptor_amount'] = {**answer['receptor_amount'], 'value': 0.0005, 'unit': 'mg'}
    answer['bead_amount'] = {**answer['bead_amount'], 'value': 2000, 'unit': 'ug'}
    answer['incubation_time'] = {**answer['incubation_time'], 'value': 2, 'unit': 'h'}
    answer['settling_time'] = {**answer['settling_time'], 'value': 1800, 'unit': 's'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'uM' and record['quantities']['ic50']['unit'] == 'pM' and record['quantities']['bmax']['unit'] == 'pmol/mg' and record['quantities']['receptor_amount']['unit'] == 'mg'
    graded = grade_spa(record)
    assert graded['native']['kd_nM'] == pytest.approx(2.0) and graded['native']['ic50_nM'] == pytest.approx(7.5) and graded['native']['incubation_min'] == pytest.approx(120.0) and graded['native']['settling_min'] == pytest.approx(30.0)
