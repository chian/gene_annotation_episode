"""The FRET extraction is derived from the FRET grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_fret_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_extraction import (
    ASSAY_FORMAT, FIT_MODEL, LANTHANIDE, NOT_EXTRACTED, PAIR, PLATE_TYPE, SERIES, SERIES_FORMAT, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_record import (
    ASSAY_FORMATS, FACTS, FIT_MODELS, LANTHANIDES, PAIRS, PLATE_TYPES, PREPARATION_KEYS, QUANTITIES, SERIES_FORMATS, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.fret_passages import (
    REAL, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_grader import (
    CRITERIA, grade_fret)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import fret_cases

# What the FRET converter reads and no grader criterion does: the effect's variance is built from the two spreads, and the
# assay volume and the temperature are kept in the record for the reviewer (no criterion judges them; the grader copies
# every quantity into its native values without reading it).
READ_BY_THE_CONVERTER_OR_KEPT = {'kd_spread', 'ki_spread', 'assay_volume', 'temperature'}


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
    for record in (fret_cases.synthetic_record(), fret_cases.sparse_record(), fret_cases.real_record()):
        grade_fret(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))
            or name in (ASSAY_FORMAT, SERIES_FORMAT, SPREAD_KIND, FIT_MODEL, 'concentration_series', PLATE_TYPE, LANTHANIDE, PAIR)}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, SERIES, ASSAY_FORMAT, SERIES_FORMAT, SPREAD_KIND, FIT_MODEL, PLATE_TYPE, LANTHANIDE, PAIR, *FACTS}
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
    assert properties[PLATE_TYPE]['properties']['value']['anyOf'][0]['enum'] == list(PLATE_TYPES)
    assert properties[PAIR]['properties']['value']['anyOf'][0]['enum'] == list(PAIRS)
    assert properties[SERIES_FORMAT]['properties']['value']['anyOf'][0]['enum'] == list(SERIES_FORMATS)
    assert properties[LANTHANIDE]['properties']['value']['anyOf'][0]['enum'] == list(LANTHANIDES)
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
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_criteria import FRET_CRITERIA
    declared = {read.split('.')[-1] for criterion in FRET_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_fret(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the grader records the numbers, the sheet judges them
    native = graded['native']
    assert native['z_prime'] == pytest.approx(0.72) and native['koff_per_s'] == pytest.approx(0.0025) and native['donor_lanthanide'] == 'terbium' and native['series_format'] == 'direct_titration'
    assert record['donor_lanthanide'] == 'terbium' and record['series_format'] == 'direct_titration' and record['quantities']['koff']['unit'] == 'per_s' and record['quantities']['z_prime']['unit'] == 'ratio'
    assert native['kd_nM'] == 20 and native['ki_nM'] == 40 and native['ec50_nM'] == 31 and native['ic50_nM'] == 85
    assert native['ratio_fold'] == pytest.approx(4.0) and native['labelled_nM'] == 5 and native['delay_us'] == 100 and native['integration_us'] == 400
    assert native['concentration_count'] == 10 and native['concentration_high_over_constant'] == pytest.approx(100)
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'KD = 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 10) + ' of the source', 'quote': 'KD = 20 nM'}
    assert record['concentration_series']['value'][-1] == 2000 and record['concentration_series']['unit'] == 'nM'
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS)
    assert record['experiment_type'] == 'fret' and record['fit_model'] == 'quadratic' and record['spread_kind'] == 'standard_error'
    assert record['assay_format'] == 'direct_titration' and record['plate_type'] == 'white' and record['donor_acceptor_pair'] == 'lanthanide_with_organic_acceptor'
    assert record['quantities']['assay_volume']['unit'] == 'uL' and record['quantities']['temperature']['unit'] == 'C' and record['quantities']['delay_time']['unit'] == 'us'
    assert record['quantities']['ratio_maximum']['unit'] == 'ratio'


def test_the_span_counts_bytes_not_characters():
    start, end = quote_span(SYNTHETIC, 'a volume of 20 µL')
    assert start == SYNTHETIC.index('a volume of 20 µL') and SYNTHETIC.encode()[start:end].decode() == 'a volume of 20 µL' and end - start == len('a volume of 20 µL') + 1
    start, end = quote_span(SYNTHETIC, 'at 25 °C')       # the micro sign before it is two bytes
    assert start == SYNTHETIC.index('at 25 °C') + 1 and SYNTHETIC.encode()[start:end].decode() == 'at 25 °C' and end - start == len('at 25 °C') + 1
    start, end = quote_span(SYNTHETIC, 'a delay of 100 µs')       # the micro and degree signs before it are two bytes each, and its own micro sign too
    assert start == SYNTHETIC.index('a delay of 100 µs') + 2 and SYNTHETIC.encode()[start:end].decode() == 'a delay of 100 µs' and end - start == len('a delay of 100 µs') + 1
    quote = 'KD value of 20\xa0nM'       # a non-breaking space (2 bytes) inside the quote; an en dash (3 bytes) comes before it
    start, end = quote_span(REAL, quote)
    assert start == REAL.index(quote) + 2 and REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None
    assert quote_span(REAL, '95% CI 19–22\xa0nM') is not None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    stated = [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point']
    assert stated == ['kd', 'koff'] and record['quantities']['koff']['value'] == pytest.approx(0.00381) and record['quantities']['koff']['unit'] == 'per_s'      # the paragraph states the dissociation rate constant
    assert record['donor_lanthanide'] is None and record['series_format'] is None and record['quantities']['z_prime']['status'] == 'unavailable'
    assert record['quantities']['ki']['value'] is None and record['quantities']['ki']['reason'] == 'not_stated_in_passage'
    assert record['concentration_series']['status'] == 'unavailable'
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['time_resolved_read', 'indirect_labelling_used', 'labelling_does_not_alter_binding']
    assert record['spread_kind'] == 'confidence_interval' and record['assay_format'] == 'direct_titration'
    assert record['fit_model'] is None and record['plate_type'] is None and record['donor_acceptor_pair'] is None
    graded = grade_fret(record)
    judged = {name: _criterion(graded, name) for name in CRITERIA}
    assert 'conflicting' not in {item['status'] for item in judged.values()}
    assert [name for name, item in judged.items() if item['status'] == 'supported'] == ['labelling_scheme']
    assert graded['reasons']['time_gating'] == 'delay_not_stated'
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
    # an ordinary space where the paper has a non-breaking space, or a hyphen where it has an en dash, is not in the chunk
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'kd', quote='KD value of 20 nM'), REAL)
    with pytest.raises(ExtractionRefused, match='spread_kind:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), SPREAD_KIND, quote='95% CI 19-22\xa0nM'), REAL)
    # a short quote that the paragraph holds twice is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'kd', quote='KD'), REAL)
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'kd', unit='M'), SYNTHETIC)                      # a unit outside the vocabulary
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'ratio_maximum', unit='mP'), SYNTHETIC)          # an FP unit is not a FRET unit
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'delay_time', unit='s'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'fit_model', value='bivalent_analyte'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, PLATE_TYPE, value='made_up_plate'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, PAIR, value='quantum_dots'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, ASSAY_FORMAT, value='kinetic'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'equilibrium_reached', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'ki'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='replicate_count.value:schema'):
        validate_answer(wrong(answer, 'replicate_count', value=3.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='ratio_minimum:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'ratio_minimum', value=-1), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='ic50:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'ic50', value=0.0), SYNTHETIC)
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
    answer['delay_time'] = {**answer['delay_time'], 'value': 0.1, 'unit': 'ms'}
    answer['incubation_time'] = {**answer['incubation_time'], 'unit': 'h'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'pM' and record['quantities']['delay_time']['unit'] == 'ms' and record['quantities']['incubation_time']['unit'] == 'h'
    assert grade_fret(record)['native']['delay_us'] == pytest.approx(100.0)


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
    assert sparse['quantities']['ki']['support'] is None and sparse['facts']['equilibrium_reached']['support'] is None and sparse['choice_support'][FIT_MODEL] is None
