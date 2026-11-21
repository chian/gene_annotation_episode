"""The AlphaScreen extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_alpha_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_extraction import (
    ACCEPTOR_BEAD, ASSAY_FORMAT, DONOR_BEAD, FIT_MODEL, NOT_EXTRACTED, SERIES, SPREAD_KIND, TITRATION_DESIGN, ExtractionRefused, answer_schema, field_names,
    quote_span, record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_record import (
    ASSAY_FORMATS, BEAD_COATINGS, CHOICE_FIELDS, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, TITRATION_DESIGNS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.alpha_passages import (
    REAL, REAL_MAY_ALSO_STATE, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_grader import (
    CRITERIA, grade_alpha)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import alpha_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the effect's
# variance is built from the spreads by the converter, and the bead concentration, the plate format,
# the number of technical wells and the temperature are kept in the record for the reviewer, as are the choices that no
# criterion reads. (The two partner concentrations and the bead step are read by the grader: partner depletion and equilibrium.
# The titration design is read through choice_support, which this tracker does not see, so it stays in the set.)
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'ki_spread', 'bead_concentration', 'plate_well_count',
                                 'technical_replicate_count', 'temperature', SPREAD_KIND, TITRATION_DESIGN, DONOR_BEAD, ACCEPTOR_BEAD}


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
    for record in (alpha_cases.synthetic_record(), alpha_cases.sparse_record(), alpha_cases.real_record()):
        grade_alpha(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.')) or name in (ASSAY_FORMAT, FIT_MODEL, SERIES)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, ASSAY_FORMAT, TITRATION_DESIGN, DONOR_BEAD, ACCEPTOR_BEAD, SPREAD_KIND, FIT_MODEL, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form and len(form) == 38
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


def test_the_two_incubation_times_and_the_two_partner_concentrations_are_separate_fields_that_exclude_each_other():
    meaning = extraction.MEANING
    assert 'after the beads were added is not this field' in meaning['incubation_time'] and 'before the beads is not this field' in meaning['bead_incubation_time']
    assert 'tagged partner or of a competitor is not this field' in meaning['labelled_partner_concentration']
    assert 'labelled partner or of a competitor is not this field' in meaning['tagged_partner_concentration']


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((ASSAY_FORMAT, ASSAY_FORMATS), (TITRATION_DESIGN, TITRATION_DESIGNS), (DONOR_BEAD, BEAD_COATINGS), (ACCEPTOR_BEAD, BEAD_COATINGS),
                             (SPREAD_KIND, SPREAD_KINDS), (FIT_MODEL, FIT_MODELS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['signal_maximum'] == ('cps',) and UNITS['bead_concentration'] == ('ug/mL', 'mg/mL') and UNITS['kd'] == UNITS['ic50'] == ('pM', 'nM', 'uM', 'mM')
    assert UNITS['signal_to_background'] == UNITS['z_prime'] == ('ratio',)


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter or the record keep."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER_OR_KEPT


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_criteria import ALPHA_CRITERIA
    declared = {read.split('.')[-1] for criterion in ALPHA_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_alpha(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # as the sheet judges what the grader recorded
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['kd_nM'] == 20 and native['ki_nM'] == 30 and native['ec50_nM'] == 28 and native['ic50_nM'] == 45 and native['constant_name'] == 'kd'
    assert native['signal_over_background'] == 500 and native['incubation_min'] == 105 and native['concentration_count'] == 12      # 60 min + 45 min after the beads
    assert native['concentration_low_over_constant'] == pytest.approx(0.05) and native['concentration_high_over_constant'] == pytest.approx(102.4)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'apparent KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 19) + ' of the source', 'quote': 'apparent KD = 20 nM'}
    assert record['concentration_series']['value'][-1] == 2048 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'alphascreen' and record['fit_model'] == 'four_parameter_logistic' and record['spread_kind'] == 'standard_error'
    assert record['assay_format'] == 'saturation_titration' and record['titration_design'] == 'fixed_partner_titration'
    assert record['donor_bead'] == 'streptavidin' and record['acceptor_bead'] == 'nickel_chelate'
    assert record['quantities']['bead_concentration']['unit'] == 'ug/mL' and record['quantities']['bead_concentration']['value'] == 20
    assert record['quantities']['signal_maximum']['unit'] == 'cps' and record['quantities']['signal_background']['value'] == 900 and record['quantities']['z_prime']['value'] == 0.8
    assert record['quantities']['labelled_partner_concentration']['value'] == 5 and record['quantities']['tagged_partner_concentration']['value'] == 10
    assert record['quantities']['plate_well_count']['value'] == 384 and record['quantities']['bead_incubation_time']['value'] == 45
    assert record['quantities']['technical_replicate_count']['value'] == 3 and record['quantities']['replicate_count']['value'] == 3
    assert record['quantities']['ic50']['value'] == 45 and record['quantities']['ec50']['value'] == 28 and record['quantities']['ki_spread']['value'] == 3


def test_the_span_counts_bytes_not_characters():
    quote = 'at 25 °C'       # nothing multi-byte before it; its own degree sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'each bead kind at a final concentration of 20 µg/mL'       # the degree sign before it is two bytes; its own micro sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    # the real paragraph has a Greek mu (U+03BC, two bytes) in 'μg/ml' and an en dash (U+2013, three bytes) in 'H3(1–23)'
    quote = '17 μg/ml for both, acceptor- and donor beads'       # before it the mu of '25 μg/ml' (1 extra byte); its own mu (1)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 1 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'we conducted a matrix cross-titration of His-Spindlin1 and biotin-H3(1–23)K4me3'       # before it the two mu (1 + 1) and the en dash of the sentence before (2); its own en dash (2)
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 4 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['bead_concentration']
    assert record['quantities']['bead_concentration']['value'] == 17 and record['quantities']['bead_concentration']['unit'] == 'ug/mL'
    for name in ('kd', 'ki', 'ec50', 'ic50', 'signal_maximum', 'signal_background', 'signal_to_background', 'z_prime', 'incubation_time', 'bead_incubation_time', 'temperature', 'plate_well_count'):
        assert record['quantities'][name]['reason'] == 'not_stated_in_passage'
    assert record['quantities']['labelled_partner_concentration']['status'] == 'unavailable'     # chosen 'for subsequent experiments', not the cross-titration's own
    assert record['concentration_series']['status'] == 'unavailable'                          # a pretest of 'several dilutions' is not a list
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['hook_effect_handled']
    assert record['titration_design'] == 'cross_titration' and record['donor_bead'] == 'streptavidin' and record['acceptor_bead'] == 'nickel_chelate'
    assert record['assay_format'] is None and record['fit_model'] is None and record['spread_kind'] is None
    graded = grade_alpha(record)
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['hook_effect']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert graded['reasons']['equilibrium'] == 'fact_unknown' and graded['reasons']['concentration_series'] == 'constant_or_series_missing'
    assert graded['reasons']['signal_window'] == 'signal_window_not_given' and graded['native']['incubation_min'] is None
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
    # a Greek mu (U+03BC) where the passage has a micro sign (U+00B5), and a plain 'deg C' where it has the degree sign, are not in the chunk
    with pytest.raises(ExtractionRefused, match='bead_concentration:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'bead_concentration', quote='each bead kind at a final concentration of 20 μg/mL'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'temperature', quote='at 25 degC'), SYNTHETIC)
    # the real paragraph has the Greek mu and an en dash: a micro sign and a hyphen-minus are not in the chunk
    for quote in ('17 µg/ml for both, acceptor- and donor beads',      # a micro sign
                  '17 mg/ml for both, acceptor- and donor beads'):      # another unit
        with pytest.raises(ExtractionRefused, match='bead_concentration:quote_is_not_in_the_chunk'):
            validate_answer(wrong(real_answer(), 'bead_concentration', quote=quote), REAL)
    with pytest.raises(ExtractionRefused, match='titration_design:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), TITRATION_DESIGN, quote='we conducted a matrix cross-titration of His-Spindlin1 and biotin-H3(1-23)K4me3'), REAL)    # a hyphen-minus for the en dash
    # a short quote that the paragraph holds more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='donor_bead:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), DONOR_BEAD, quote='streptavidin donor beads'), REAL)
    with pytest.raises(ExtractionRefused, match='bead_concentration:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'bead_concentration', quote='μg/ml'), REAL)
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                       # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'ic50', unit='ug/mL'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'bead_concentration', unit='nM'), SYNTHETIC)      # a bead concentration given in a molar unit is not offered
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'signal_maximum', unit='RLU'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'z_prime', unit='OD'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'incubation_time', unit='days'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='stern_volmer'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ASSAY_FORMAT, value='direct_titration'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, TITRATION_DESIGN, value='matrix'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, DONOR_BEAD, value='gold'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'hook_effect_handled', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'ic50'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    for name in ('titration_point_count', 'technical_replicate_count', 'replicate_count', 'plate_well_count'):
        with pytest.raises(ExtractionRefused, match=name + '.value:schema'):
            validate_answer(wrong(answer, name, value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='signal_background:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'signal_background', value=-900), SYNTHETIC)
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
    answer['bead_concentration'] = {**answer['bead_concentration'], 'value': 0.02, 'unit': 'mg/mL'}
    answer['incubation_time'] = {**answer['incubation_time'], 'value': 1, 'unit': 'h'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'uM' and record['quantities']['ic50']['unit'] == 'pM' and record['quantities']['bead_concentration']['unit'] == 'mg/mL'
    graded = grade_alpha(record)
    assert graded['native']['kd_nM'] == pytest.approx(20.0) and graded['native']['ic50_nM'] == pytest.approx(45.0) and graded['native']['incubation_min'] == pytest.approx(105.0)


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
    support = {'kd': 'implied', SERIES: 'implied', FIT_MODEL: 'about_something_else', DONOR_BEAD: 'implied', 'equilibrium_reached': 'implied', 'counter_screen_done': 'about_something_else'}
    answer = validate_answer(answer_from(SYNTHETIC, SYNTHETIC_STATED, support), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['concentration_series']['support'] == 'implied'
    assert record['quantities']['ic50']['support'] == 'direct'
    assert record['facts']['equilibrium_reached']['support'] == 'implied' and record['facts']['counter_screen_done']['support'] == 'about_something_else'
    assert record['facts']['hook_effect_handled']['support'] == 'direct'
    assert set(record['choice_support']) == set(CHOICE_FIELDS) == set(extraction.CHOICES)
    assert record['choice_support'][FIT_MODEL] == 'about_something_else' and record['choice_support'][DONOR_BEAD] == 'implied' and record['choice_support'][ACCEPTOR_BEAD] == 'direct'
    sparse = record_from_answer(validate_answer(real_answer(), REAL), REAL, 0, 'exp', 'src', 'hyp')
    assert sparse['quantities']['kd']['support'] is None and sparse['facts']['counter_screen_done']['support'] is None
    assert sparse['choice_support'][FIT_MODEL] is None and sparse['choice_support'][DONOR_BEAD] == 'direct'
    assert grade_alpha(record)['native']['support']['fit_model'][0] == 'about_something_else'      # the grader keeps the support of what a criterion reads, in the order of its reads
