"""The intrinsic fluorescence quenching extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_trp_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_extraction import (
    CHANGE_DIRECTION, FIT_MODEL, NOT_EXTRACTED, SERIES, SHIFT_DIRECTION, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_record import (
    CHANGE_DIRECTIONS, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SHIFT_DIRECTIONS, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.trp_passages import (
    REAL, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import (
    CRITERIA, grade_trp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import trp_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the effect's
# variance is built from the spread by the converter, and the emission wavelength, the emission shift, the temperature and the
# statement that only this method was used are kept in the record for the reviewer.
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'emission_wavelength', 'emission_shift', 'temperature', 'single_estimate_method'}


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
    for record in (trp_cases.synthetic_record(), trp_cases.sparse_record(), trp_cases.real_record()):
        grade_trp(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))
            or name in (SPREAD_KIND, FIT_MODEL, 'concentration_series', CHANGE_DIRECTION, SHIFT_DIRECTION)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, SPREAD_KIND, FIT_MODEL, CHANGE_DIRECTION, SHIFT_DIRECTION, *FACTS}
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
    assert properties[CHANGE_DIRECTION]['properties']['value']['anyOf'][0]['enum'] == list(CHANGE_DIRECTIONS)
    assert properties[SHIFT_DIRECTION]['properties']['value']['anyOf'][0]['enum'] == list(SHIFT_DIRECTIONS)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['ksv'] == ('M^-1',) and 'kd' in QUANTITIES and 'ksv' in QUANTITIES        # a Stern-Volmer constant has its own field and its own unit


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the converter or the record keep."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == READ_BY_THE_CONVERTER_OR_KEPT


def test_the_criteria_read_only_extracted_fields():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_criteria import TRP_CRITERIA
    declared = {read.split('.')[-1] for criterion in TRP_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_trp(record)
    # the grader records the numbers, the sheet judges them; the excitation wavelength has nothing in the record to be compared with
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')
    native = graded['native']
    assert native['kd_nM'] == 20 and native['protein_nM'] == 5 and native['protein_over_kd'] == pytest.approx(0.25) and native['excitation_nm'] == 295
    assert native['incubation_min'] == 5 and native['concentration_count'] == 12 and native['concentration_high_over_constant'] == pytest.approx(102.4)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 10) + ' of the source', 'quote': 'KD = 20 nM'}
    assert record['concentration_series']['value'][-1] == 2048 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'trp_quenching' and record['fit_model'] == 'quadratic' and record['spread_kind'] == 'standard_error'
    assert record['change_direction'] == 'quenching' and record['emission_shift_direction'] == 'blue'
    assert record['quantities']['ksv']['value'] == 20000 and record['quantities']['ksv']['unit'] == 'M^-1'     # kept apart from the KD
    assert record['quantities']['fluorescence_change']['unit'] == 'percent' and record['quantities']['fluorescence_change']['value'] == 40
    assert record['quantities']['ligand_absorbance']['unit'] == 'AU' and record['quantities']['ligand_absorbance']['value'] == 0.02
    assert record['quantities']['excitation_wavelength']['unit'] == 'nm' and record['quantities']['temperature']['unit'] == 'C'


def test_the_span_counts_bytes_not_characters():
    start, end = quote_span(SYNTHETIC, 'at 25 °C')       # nothing multi-byte before it; its own degree sign is two bytes
    assert start == SYNTHETIC.index('at 25 °C') and SYNTHETIC.encode()[start:end].decode() == 'at 25 °C' and end - start == len('at 25 °C') + 1
    quote = 'Ksv = 2.0 × 10^4 M−1'       # the degree sign before it is two bytes; its own multiplication sign is two bytes and its minus sign three
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 3
    quote = 'concentrations of test compounds (0–1000 nM)'       # an en dash (3 bytes) in the real paragraph
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    quote = 'using the equation derived from Liu et al. [39]:KD = [P]T (f − 1)'       # a minus sign (3 bytes) after two en dashes (6 bytes in all) before it
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 4 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 2
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['protein_concentration', 'excitation_wavelength', 'emission_wavelength', 'concentration_highest']
    assert record['quantities']['concentration_highest']['value'] == 1000 and record['quantities']['concentration_lowest']['reason'] == 'not_stated_in_passage'   # 0-1000 nM: the zero blank is no lowest concentration
    assert record['quantities']['kd']['value'] is None and record['quantities']['kd']['reason'] == 'not_stated_in_passage'
    assert record['concentration_series']['status'] == 'unavailable'                          # the compounds are given as a range, not a list
    assert record['quantities']['temperature']['reason'] == 'not_stated_in_passage'           # 'room temperature' is not a number
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == []
    assert record['fit_model'] is None and record['spread_kind'] is None and record['change_direction'] is None and record['emission_shift_direction'] is None
    graded = grade_trp(record)
    judged = {name: _criterion(graded, name) for name in CRITERIA}
    assert 'conflicting' not in {item['status'] for item in judged.values()}
    assert [name for name, item in judged.items() if item['status'] == 'supported'] == ['excitation_selectivity']          # 295 nm is the tryptophan-selective wavelength (the sheet judges it); the top of the range has no KD to be put over, so the series stays unknown
    assert graded['reasons']['protein_concentration'] == 'protein_or_kd_missing' and graded['reasons']['fit_model'] == 'fit_model_not_stated'
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
    # an ordinary hyphen where the paper has an en dash, or a hyphen-minus where it has a minus sign, is not in the chunk
    with pytest.raises(ExtractionRefused, match='protein_concentration:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'protein_concentration', quote='test compounds (0-1000 nM)'), REAL)
    with pytest.raises(ExtractionRefused, match='emission_wavelength:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'emission_wavelength', quote='(f - 1)'), REAL)
    # a short quote that the paragraph holds twice is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='excitation_wavelength:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'excitation_wavelength', quote='fluorescence'), REAL)
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                      # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'ksv', unit='nM'), SYNTHETIC)                    # a Stern-Volmer constant is not in concentration units
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fluorescence_change', unit='permille'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'excitation_wavelength', unit='um'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'ligand_absorbance', unit='percent'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='bivalent_analyte'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, CHANGE_DIRECTION, value='unchanged'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, SHIFT_DIRECTION, value='violet'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'equilibrium_reached', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'ksv'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='titration_point_count.value:schema'):
        validate_answer(wrong(answer, 'titration_point_count', value=12.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=3.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fluorescence_change:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'fluorescence_change', value=-1), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='ligand_absorbance:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'ligand_absorbance', value=0.0), SYNTHETIC)
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


def test_a_picomolar_a_micromolar_protein_and_a_time_unit_answer_are_in_the_vocabulary():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 94, 'unit': 'pM', 'quote': 'KD = 20 nM'}
    answer['protein_concentration'] = {**answer['protein_concentration'], 'value': 0.005, 'unit': 'uM'}
    answer['incubation_time'] = {**answer['incubation_time'], 'unit': 'h'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'pM' and record['quantities']['protein_concentration']['unit'] == 'uM' and record['quantities']['incubation_time']['unit'] == 'h'
    assert grade_trp(record)['native']['protein_nM'] == pytest.approx(5.0)


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
    assert record['choice_support'][FIT_MODEL] == 'about_something_else' and record['choice_support'][SPREAD_KIND] == 'direct'
    sparse = record_from_answer(validate_answer(real_answer(), REAL), REAL, 0, 'exp', 'src', 'hyp')
    assert sparse['quantities']['kd']['support'] is None and sparse['facts']['equilibrium_reached']['support'] is None and sparse['choice_support'][FIT_MODEL] is None
