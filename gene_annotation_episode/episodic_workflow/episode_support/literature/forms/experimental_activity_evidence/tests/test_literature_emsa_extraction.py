"""The EMSA (electrophoretic mobility shift assay) extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_emsa_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_extraction import (
    CHOICES, COMPETITOR_TYPE, FIT_MODEL, GEL_TYPE, NOT_EXTRACTED, PROBE_LABEL, PROBE_TYPE, SPREAD_KIND, ExtractionRefused, answer_schema, field_names, quote_span,
    record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import (
    COMPETITOR_TYPES, FACTS, FIT_MODELS, GEL_TYPES, PREPARATION_KEYS, PROBE_LABELS, PROBE_TYPES, QUANTITIES, SPREAD_KINDS, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.emsa_passages import (
    REAL, REAL_ALLOWED, REAL_PERCENT, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_criteria import EMSA_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import CRITERIA, grade_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import emsa_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the spread of the KD, the probe length, the binding buffer
# (salt, magnesium, glycerol), the non-specific competitor amount, the temperature of the incubation, the gel percent and the run, the single estimate method, and the choices
# are kept in the record for the reviewer (or read by the converter).
KEPT = {'kd_spread', 'probe_length', 'salt_concentration', 'magnesium_concentration', 'glycerol_percent', 'nonspecific_competitor_amount', 'incubation_temperature', 'gel_percent',
        'run_time', 'run_voltage', 'run_temperature', 'single_estimate_method', *CHOICES}


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
    for record in (emsa_cases.synthetic_record(), emsa_cases.qualitative_record(), emsa_cases.sparse_record(), emsa_cases.real_record(), emsa_cases.multiple_species_record()):
        grade_emsa(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, PROBE_TYPE, PROBE_LABEL, GEL_TYPE, COMPETITOR_TYPE, SPREAD_KIND, FIT_MODEL, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form and len(form) == 44
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'support', 'reason'}
        assert field['properties']['support']['anyOf'][0]['enum'] == ['direct', 'implied', 'about_something_else'] and field['properties']['support']['anyOf'][1] == {'type': 'null'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == set(QUANTITIES)


def test_an_emsa_has_an_apparent_kd_field_and_the_emsa_items_but_no_other_binding_constant():
    names = set(field_names())
    assert not {'ki', 'ic50', 'ec50', 'bmax', 'kon', 'koff', 'concentration_series', 'fold_enrichment'} & names
    assert {'kd', 'kd_spread', 'fraction_shifted_highest', 'probe_concentration', 'probe_length', 'salt_concentration', 'magnesium_concentration', 'glycerol_percent', 'nonspecific_competitor_amount',
            'specific_competitor_excess', 'incubation_time', 'incubation_temperature', 'gel_percent', 'run_time', 'run_voltage', 'run_temperature', 'titration_point_count', 'shifted_species_count',
            'replicate_count', 'shift_detected', 'shift_abolished_by_specific_competitor', 'shift_not_abolished_by_nonspecific_competitor', 'mutant_probe_does_not_shift', 'probe_alone_lane_shown',
            'nonspecific_protein_control_done', 'free_probe_quantified', 'probe_at_or_below_kd', 'equilibrium_reached', 'supershift_confirms_protein_identity', 'protein_purified',
            'complex_survives_gel_run', 'protein_range_brackets_kd', 'independent_experiments', 'single_estimate_method'} <= names


def test_the_descriptions_keep_the_confusable_fields_apart_and_the_kd_is_the_experiments_own():
    meaning = extraction.MEANING
    assert 'cites as a known or previously reported property of the protein' in meaning['kd'] and 'IC50 or EC50 of a competitor are not this field' in meaning['kd']
    assert 'A confidence interval given as a lower and an upper limit is not a half-width' in meaning['kd_spread']
    assert 'excess of a non-specific or mutant competitor is not this field' in meaning['specific_competitor_excess']
    assert 'the amount of the unlabelled specific probe are not this field' in meaning['nonspecific_competitor_amount']
    assert 'gel or running buffer is not this field' in meaning['magnesium_concentration'] and 'storage buffer' in meaning['glycerol_percent']
    assert 'temperature of the gel run is not this field' in meaning['incubation_temperature'] and 'temperature of the binding reaction is not this field' in meaning['run_temperature']
    assert 'Lanes of one gel are not this field' in meaning['replicate_count']
    assert 'A label of the protein or of an antibody is not the label of the probe' in meaning[PROBE_LABEL]
    assert 'competition control' in meaning[COMPETITOR_TYPE] and 'is not this carrier' in meaning[COMPETITOR_TYPE]
    assert 'a name such as fragment, PCR product' in meaning[PROBE_TYPE]


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((PROBE_TYPE, PROBE_TYPES), (PROBE_LABEL, PROBE_LABELS), (GEL_TYPE, GEL_TYPES), (COMPETITOR_TYPE, COMPETITOR_TYPES), (SPREAD_KIND, SPREAD_KINDS), (FIT_MODEL, FIT_MODELS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['kd'] == UNITS['probe_concentration'] == UNITS['protein_concentration_lowest'] == ('pM', 'nM', 'uM', 'mM') and UNITS['probe_length'] == ('bp', 'nt')
    assert UNITS['run_voltage'] == ('V', 'V/cm') and UNITS['specific_competitor_excess'] == ('ratio',) and UNITS['nonspecific_competitor_amount'] == ('ng', 'ug')
    assert PROBE_TYPES == ('dsdna', 'ssdna', 'rna', 'other') and PROBE_LABELS == ('p32', 'fluorescent', 'biotin_chemiluminescence', 'infrared', 'other')
    assert FIT_MODELS == ('one_site', 'hill', 'quadratic', 'two_site', 'other') and GEL_TYPES == ('native_polyacrylamide', 'agarose', 'other')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the record keeps."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == KEPT


def test_the_criteria_read_only_extracted_fields():
    declared = {read.split('.')[-1] for criterion in EMSA_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_emsa(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the sheet side judges the recorded numbers
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['interaction'] == 'detected' and native['kd_nM'] == 20 and native['probe_nM'] == 0.5 and native['incubation_min'] == 30
    kd = record['quantities']['kd']
    span = record['spans'][kd['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'an apparent KD of 20 nM')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 23) + ' of the source', 'quote': 'an apparent KD of 20 nM'}
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS) and record['experiment_type'] == 'emsa'
    assert (record['probe_type'], record['probe_label'], record['gel_type'], record['nonspecific_competitor_type'], record['spread_kind'], record['fit_model']) == ('dsdna', 'p32', 'native_polyacrylamide', 'poly_dI_dC', 'standard_deviation', 'one_site')
    quantities = record['quantities']
    assert quantities['kd']['value'] == 20 and quantities['kd']['unit'] == 'nM' and quantities['kd_spread']['value'] == 2 and quantities['fraction_shifted_highest']['value'] == 92
    assert quantities['protein_concentration_lowest']['value'] == 1 and quantities['protein_concentration_highest']['value'] == 640 and quantities['probe_length']['unit'] == 'bp'
    assert quantities['run_voltage']['unit'] == 'V/cm' and quantities['run_temperature']['value'] == 4 and quantities['incubation_temperature']['value'] == 25 and quantities['specific_competitor_excess']['value'] == 100
    assert quantities['titration_point_count']['value'] == 11 and quantities['shifted_species_count']['value'] == 1 and quantities['replicate_count']['value'] == 3
    assert all(item['answer'] == 'yes' for item in record['facts'].values())


def test_the_span_counts_bytes_not_characters():
    quote = 'at 25 °C'       # the micro sign of '20 µl' is before it (two bytes); its own degree sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = 'an apparent KD of 20 nM'       # the micro sign and the two degree signs before it are two bytes each
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 3 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote)
    quote = '20 µl reaction'       # its own micro sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    assert len(REAL) == 910 and len(REAL.encode()) > len(REAL)    # the real paragraph holds the minus sign, the quotation marks and the plus-minus sign (several bytes each)
    quote = 'apparent Kd of 11 ± 0.2 nM'
    start, end = quote_span(REAL, quote)
    assert REAL.encode()[start:end].decode() == quote and end - start == len(quote) + 1 and start == len(REAL[:REAL.index(quote)].encode())
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    assert [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point'] == ['kd', 'kd_spread', 'specific_competitor_excess']
    assert [name for name in QUANTITIES if record['quantities'][name]['status'] == 'unavailable' and record['quantities'][name]['reason'] != 'not_stated_in_passage'] == []
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['shift_detected', 'shift_abolished_by_specific_competitor', 'shift_not_abolished_by_nonspecific_competitor', 'protein_purified']
    assert (record['probe_type'], record['probe_label'], record['gel_type'], record['nonspecific_competitor_type'], record['spread_kind'], record['fit_model']) == (None,) * 6
    graded = grade_emsa(record)
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['shift_observed', 'specific_competition', 'nonspecific_competition', 'protein_identity']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert graded['native']['kd_nM'] == 11 and graded['native']['interaction'] == 'detected'
    assert record['quantities']['kd']['support'] == 'direct' and record['facts']['shift_detected']['support'] == 'direct' and record['facts']['protein_purified']['support'] == 'direct'
    assert record['quantities']['kd_spread']['support'] == 'direct' and record['quantities']['replicate_count']['support'] is None and set(record['choice_support'].values()) == {None}
    assert graded['reasons']['probe_concentration'] == 'fact_unknown' and graded['reasons']['titration_points'] == 'titration_point_count_not_given' and graded['reasons']['single_complex'] == 'shifted_species_count_not_given'
    assert set(REAL_STATED) <= set(REAL_ALLOWED) < set(field_names())
    for name, (value, unit, _) in REAL_STATED.items():
        assert (value, unit) in REAL_ALLOWED[name]


def real_with_percent():
    """The real answer that also states a number the paragraph does not give as a shifted fraction: the form can hold it, the real run must not state it."""
    return answer_from(REAL, {**REAL_STATED, 'fraction_shifted_highest': REAL_PERCENT})


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'kd', quote='an apparent KD of 25 nM'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='kd:quote_occurs_more_than_once'):
        validate_answer(answer, twice)
    # a plain 'deg C' where the passage has the degree sign, and a Greek mu (U+03BC) where it has the micro sign (U+00B5), are not in the chunk
    with pytest.raises(ExtractionRefused, match='incubation_temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'incubation_temperature', quote='at 25 degC'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd_spread:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'kd_spread', quote='in each 20 μl reaction'), SYNTHETIC)
    # a plain '+/-' where the real paragraph has the plus-minus sign is not in the chunk
    with pytest.raises(ExtractionRefused, match='kd:quote_is_not_in_the_chunk'):
        validate_answer(wrong(real_answer(), 'kd', quote='apparent Kd of 11 +/- 0.2 nM'), REAL)
    # a short quote that the real paragraph holds more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='fraction_shifted_highest:quote_occurs_more_than_once'):
        validate_answer(real_with_percent(), REAL)                                                          # the paragraph has '(Figure 5' several times
    with pytest.raises(ExtractionRefused, match='shift_detected:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'shift_detected', quote='srn_9340P225'), REAL)                 # 'srn_9340P225' occurs several times
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    for name, unit in (('kd', 'M'), ('kd_spread', 'percent'), ('probe_concentration', 'ng'), ('probe_length', 'kb'), ('run_voltage', 'A'), ('incubation_time', 'days'), ('gel_percent', 'mM'), ('nonspecific_competitor_amount', 'mM'), ('specific_competitor_excess', 'percent'), ('titration_point_count', 'ratio')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, unit=unit), SYNTHETIC)
    for name, value in ((PROBE_TYPE, 'plasmid'), (PROBE_LABEL, 'gold'), (GEL_TYPE, 'sds_page'), (COMPETITOR_TYPE, 'bsa'), (SPREAD_KIND, 'range'), (FIT_MODEL, 'sigmoid')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, value=value), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'shift_detected', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'probe_alone_lane_shown'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'ic50': {'status': 'unavailable', 'value': None, 'unit': None, 'quote': None, 'reason': 'not_stated_in_passage'}}, SYNTHETIC)   # an EMSA has no IC50
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    for name in ('titration_point_count', 'shifted_species_count', 'replicate_count'):
        with pytest.raises(ExtractionRefused, match=name + '.value:schema'):
            validate_answer(wrong(answer, name, value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='kd:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'kd', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fraction_shifted_highest:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'fraction_shifted_highest', value=-92), SYNTHETIC)


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
    for name in ('kd', 'incubation_time', PROBE_TYPE, 'shift_detected'):       # a quantity, a time, a choice and a fact
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
    answer['kd']['support'], answer['kd_spread']['support'], answer[PROBE_TYPE]['support'] = 'implied', 'about_something_else', 'implied'
    answer['shift_detected']['support'] = 'about_something_else'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['support'] == 'implied' and record['quantities']['kd_spread']['support'] == 'about_something_else' and record['quantities']['incubation_time']['support'] == 'direct'
    assert record['facts']['shift_detected']['support'] == 'about_something_else' and record['facts']['protein_purified']['support'] == 'direct'
    assert record['choice_support'][PROBE_TYPE] == 'implied' and record['choice_support'][FIT_MODEL] == 'direct' and set(record['choice_support']) == set(CHOICES)
    blank = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert blank['quantities']['kd']['support'] is None and blank['facts']['shift_detected']['support'] is None and set(blank['choice_support'].values()) == {None}
    assert grade_emsa(record)['native']['support']['shift_observed'] == ['about_something_else']      # the grader keeps it for the sheet


def test_every_synthetic_field_is_stated_so_the_test_passage_covers_the_whole_form():
    assert set(SYNTHETIC_STATED) == set(field_names())
    assert answer_from(SYNTHETIC, {})['kd']['status'] == 'unavailable'


def test_every_synthetic_quote_occurs_exactly_once_and_says_its_value():
    for name, (value, unit, quote) in SYNTHETIC_STATED.items():
        assert quote_span(SYNTHETIC, quote) is not None, name
    assert validate_answer(synthetic_answer(), SYNTHETIC)


def test_other_units_of_the_vocabulary_are_accepted_and_reach_the_record():
    answer = synthetic_answer()
    answer['kd'] = {**answer['kd'], 'value': 0.02, 'unit': 'uM'}
    answer['incubation_time'] = {**answer['incubation_time'], 'value': 0.5, 'unit': 'h'}
    answer['incubation_temperature'] = {**answer['incubation_temperature'], 'value': 298.15, 'unit': 'K'}
    answer['run_voltage'] = {**answer['run_voltage'], 'value': 150, 'unit': 'V'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['kd']['unit'] == 'uM' and record['quantities']['incubation_temperature']['unit'] == 'K' and record['quantities']['run_voltage']['unit'] == 'V'
    graded = grade_emsa(record)
    assert graded['native']['kd_nM'] == pytest.approx(20.0) and graded['native']['incubation_min'] == pytest.approx(30.0)
