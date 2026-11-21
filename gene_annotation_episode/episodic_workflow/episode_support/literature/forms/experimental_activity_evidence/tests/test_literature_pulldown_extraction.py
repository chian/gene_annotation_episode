"""The pull-down / co-IP extraction is derived from the grader's input form: its answer schema has exactly the fields the form
(and so the grader) has, a valid answer becomes a record the grader accepts, and a quote that is not at its span is
refused. Deterministic: no model."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_pulldown_extraction as extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_extraction import (
    CAPTURE, CROSSLINKER, DETECTION, NOT_EXTRACTED, NUCLEASE, SOURCE, ExtractionRefused, answer_schema, field_names, quote_span, record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import (
    CAPTURE_FORMATS, CROSSLINKERS, DETECTION_METHODS, FACTS, NUCLEASE_TREATMENTS, PREPARATION_KEYS, PROTEIN_SOURCES, QUANTITIES, UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.pulldown_passages import (
    REAL, REAL_ALLOWED, REAL_FOLD, REAL_STATED, SYNTHETIC, SYNTHETIC_STATED, answer_from, real_answer, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_criteria import PULLDOWN_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import CRITERIA, grade_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import pulldown_cases

# What no grader criterion reads (the grader copies every quantity into its native values without reading it): the percent of the input recovered, the input
# fraction and the temperature of the incubation, the detection method, the way the bait is captured, the source of the prey, the nuclease named and the
# crosslinker are kept in the record for the reviewer.
KEPT = {'percent_input_recovered', 'input_fraction', 'incubation_temperature', DETECTION, CAPTURE, SOURCE, NUCLEASE, CROSSLINKER}


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
    for record in (pulldown_cases.synthetic_record(), pulldown_cases.sparse_record(), pulldown_cases.real_record()):
        grade_pulldown(Tracking(record, reads))
    return {name.split('.')[-1] for name in reads if name.startswith(('quantities.', 'facts.'))}


def test_the_schema_has_exactly_the_fields_of_the_form():
    schema = answer_schema()
    form = {*QUANTITIES, DETECTION, CAPTURE, SOURCE, NUCLEASE, CROSSLINKER, *FACTS}
    assert set(schema['properties']) == set(field_names()) == form and len(form) == 27
    assert schema['required'] == list(schema['properties']) and schema['additionalProperties'] is False
    assert NOT_EXTRACTED == ('preparations',) and len(PREPARATION_KEYS) == 3
    for name, field in schema['properties'].items():
        assert field['description'] and set(field['required']) >= {'status', 'value', 'quote', 'support', 'reason'}
        assert field['properties']['support']['anyOf'][0]['enum'] == ['direct', 'implied', 'about_something_else'] and field['properties']['support']['anyOf'][1] == {'type': 'null'}
        assert ('unit' in field['properties']) == (name in UNITS)
    assert set(extraction.MEANING) == set(field_names())
    assert set(UNITS) == set(QUANTITIES)


def test_a_pulldown_has_no_binding_constant_field_and_the_form_has_the_pulldown_items():
    names = set(field_names())
    assert not {'kd', 'ki', 'ic50', 'bmax', 'hill_slope', 'kon', 'koff', 'concentration_series'} & names
    assert {'fold_enrichment', 'percent_input_recovered', 'input_fraction', 'nacl_wash', 'detergent_wash', 'wash_count', 'incubation_time', 'incubation_temperature', 'replicate_count',
            'negative_control_done', 'prey_absent_in_negative_control', 'bait_minus_control_done', 'input_lane_shown', 'reciprocal_done', 'competition_disrupts_interaction',
            'interaction_survives_nuclease', 'direct_interaction_shown', 'endogenous_expression_levels', 'quantification_with_normalization', 'specificity_validated'} <= names


def test_the_fold_the_percent_of_the_input_and_the_input_fraction_are_separate_fields_that_exclude_each_other():
    meaning = extraction.MEANING
    assert 'A percent of the input, an intensity with no control' in meaning['fold_enrichment'] and 'A fold enrichment, a percent of the bait' in meaning['percent_input_recovered']
    assert 'A percent of the input that was recovered is not this field' in meaning['input_fraction']
    assert 'lysis buffer, of the binding buffer or of the elution buffer is not this field' in meaning['nacl_wash'] and 'lysis buffer alone' in meaning['detergent_wash']
    assert 'The number of independent experiments' in meaning['replicate_count'] or 'independent experiments the passage reports' in meaning['replicate_count']
    assert 'A pull-down from a lysate or extract, or a co-immunoprecipitation, does not state this' in meaning['direct_interaction_shown']
    assert 'Ethidium bromide is not a nuclease' in meaning[NUCLEASE]
    assert 'A control capture with an irrelevant tag or antibody is not this control' in meaning['bait_minus_control_done']


def test_the_vocabularies_are_the_forms_vocabularies():
    properties = answer_schema()['properties']
    for name, vocabulary in ((DETECTION, DETECTION_METHODS), (CAPTURE, CAPTURE_FORMATS), (SOURCE, PROTEIN_SOURCES), (NUCLEASE, NUCLEASE_TREATMENTS), (CROSSLINKER, CROSSLINKERS)):
        assert properties[name]['properties']['value']['anyOf'][0]['enum'] == list(vocabulary)
    for name, answers in FACTS.items():
        offered = properties[name]['properties']['value']['anyOf'][0]['enum']
        assert set(offered) == set(answers) - {'unknown', 'not_applicable'}
    for name in UNITS:
        assert properties[name]['properties']['unit']['anyOf'][0]['enum'] == list(UNITS[name])
    assert UNITS['nacl_wash'] == ('mM', 'M') and UNITS['fold_enrichment'] == ('ratio',) and UNITS['percent_input_recovered'] == UNITS['input_fraction'] == UNITS['detergent_wash'] == ('percent',)
    assert UNITS['incubation_time'] == ('s', 'min', 'h') and UNITS['incubation_temperature'] == ('C', 'K') and UNITS['wash_count'] == UNITS['replicate_count'] == ('count',)
    assert DETECTION_METHODS == ('western_blot', 'mass_spectrometry', 'fluorescence', 'autoradiography', 'other')
    assert CAPTURE_FORMATS == ('gst', 'his', 'strep', 'flag', 'ha', 'myc', 'antibody', 'biotin_streptavidin', 'other') and CROSSLINKERS == ('formaldehyde', 'dsp', 'other', 'none')


def test_the_grader_reads_exactly_the_fields_the_schema_asks_for():
    """Fails when the grader's form gains a field, or the grader stops reading one, without the extraction
    following: the fields the grader reads are the schema's, but for those only the record keeps."""
    reads = fields_the_grader_reads()
    assert reads <= set(field_names())
    assert set(field_names()) - reads == KEPT


def test_the_criteria_read_only_extracted_fields():
    declared = {read.split('.')[-1] for criterion in PULLDOWN_CRITERIA for read in criterion['reads']}
    assert declared <= set(field_names())


def test_a_correct_synthetic_answer_is_valid_and_becomes_a_record_the_grader_accepts():
    answer = validate_answer(synthetic_answer(), SYNTHETIC)
    record = record_from_answer(answer, SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    graded = grade_pulldown(record)
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'supported')      # the sheet side judges the recorded numbers
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['interaction'] == 'detected' and native['nacl_wash_mM'] == 300 and native['incubation_min'] == 120
    fold = record['quantities']['fold_enrichment']
    span = record['spans'][fold['source_refs'][0]]
    start = SYNTHETIC.encode().index(b'12-fold stronger than in the control')
    assert span == {'locator': 'bytes ' + str(5000 + start) + '-' + str(5000 + start + 36) + ' of the source', 'quote': '12-fold stronger than in the control'}
    assert record['preparations'] == dict.fromkeys(PREPARATION_KEYS) and record['experiment_type'] == 'pulldown'
    assert (record['detection_method'], record['capture_format'], record['protein_source'], record['nuclease_treatment'], record['crosslinker']) == ('western_blot', 'gst', 'cell_lysate', 'benzonase', 'none')
    quantities = record['quantities']
    assert quantities['fold_enrichment']['value'] == 12 and quantities['percent_input_recovered']['value'] == 4 and quantities['input_fraction']['value'] == 5
    assert quantities['nacl_wash']['value'] == 300 and quantities['nacl_wash']['unit'] == 'mM' and quantities['detergent_wash']['value'] == 0.1 and quantities['wash_count']['value'] == 4
    assert quantities['incubation_time']['value'] == 2 and quantities['incubation_time']['unit'] == 'h' and quantities['incubation_temperature']['value'] == 4 and quantities['replicate_count']['value'] == 3
    assert all(item['answer'] == 'yes' for item in record['facts'].values())


def test_the_span_counts_bytes_not_characters():
    quote = 'for 2 h at 4 °C'       # nothing multi-byte before it except the micro sign of '50 µl'; its own degree sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 1 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    quote = '12-fold stronger than in the control'       # the micro sign and the degree sign before it are two bytes each
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) + 2 and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote)
    quote = '50 µl of glutathione beads'       # its own micro sign is two bytes
    start, end = quote_span(SYNTHETIC, quote)
    assert start == SYNTHETIC.index(quote) and SYNTHETIC.encode()[start:end].decode() == quote and end - start == len(quote) + 1
    assert len(REAL) == len(REAL.encode()) == 656    # the real paragraph is plain ASCII, so characters and bytes agree
    start, end = quote_span(REAL, 'Western blot analyses showed')
    assert (start, end) == (REAL.index('Western blot analyses showed'), REAL.index('Western blot analyses showed') + 28)
    assert quote_span(SYNTHETIC, 'not in the chunk') is None and quote_span(SYNTHETIC, '') is None


def test_the_real_paragraph_states_only_what_it_states_and_everything_else_stays_unavailable_and_unknown():
    answer = validate_answer(real_answer(), REAL)
    record = record_from_answer(answer, REAL, 100, 'exp', 'src', 'hyp')
    assert [name for name in QUANTITIES if record['quantities'][name]['status'] == 'point'] == []              # the paragraph has no number about the experiment
    for name in QUANTITIES:
        assert record['quantities'][name]['status'] == 'unavailable' and record['quantities'][name]['reason'] == 'not_stated_in_passage'
    assert [name for name, item in record['facts'].items() if item['answer'] != 'unknown'] == ['prey_detected_in_eluate', 'negative_control_done', 'prey_absent_in_negative_control', 'reciprocal_done', 'interaction_survives_nuclease']
    assert (record['detection_method'], record['capture_format'], record['protein_source'], record['nuclease_treatment'], record['crosslinker']) == ('western_blot', 'antibody', 'cell_lysate', 'benzonase', None)
    graded = grade_pulldown(record)
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['prey_in_eluate', 'negative_control', 'reciprocal', 'nuclease']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert graded['reasons']['wash_stringency'] == 'wash_stringency_not_given' and graded['reasons']['direct_interaction'] == 'direct_interaction_not_shown'
    assert graded['native']['interaction'] == 'detected'
    assert record['facts']['negative_control_done']['support'] == 'implied' and record['facts']['prey_detected_in_eluate']['support'] == 'direct' and record['facts']['input_lane_shown']['support'] is None
    assert record['choice_support'][CAPTURE] == 'direct' and record['choice_support'][CROSSLINKER] is None
    assert set(REAL_STATED) == set(REAL_ALLOWED) < set(field_names())
    for name, (value, unit, _) in REAL_STATED.items():
        assert (value, unit) in REAL_ALLOWED[name]


def real_with_fold():
    """The real answer that also states a number the paragraph does not give as a fold enrichment: the form can hold it, the real run must not state it."""
    return answer_from(REAL, {**REAL_STATED, 'fold_enrichment': REAL_FOLD})


def wrong(answer, name, **changes):
    answer = deepcopy(answer)
    answer[name].update(changes)
    return answer


def test_a_quote_that_is_not_in_the_chunk_exactly_once_is_refused():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='fold_enrichment:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'fold_enrichment', quote='15-fold stronger than in the control'), SYNTHETIC)
    twice = SYNTHETIC + ' ' + SYNTHETIC
    with pytest.raises(ExtractionRefused, match='fold_enrichment:quote_occurs_more_than_once'):
        validate_answer(answer, twice)
    # a plain 'deg C' where the passage has the degree sign, and a Greek mu (U+03BC) where it has the micro sign (U+00B5), are not in the chunk
    with pytest.raises(ExtractionRefused, match='incubation_temperature:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'incubation_temperature', quote='for 2 h at 4 degC'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='wash_count:quote_is_not_in_the_chunk'):
        validate_answer(wrong(answer, 'wash_count', quote='50 μl of glutathione beads'), SYNTHETIC)
    # a short quote that the real paragraph holds more than once is refused, a longer one is accepted
    with pytest.raises(ExtractionRefused, match='fold_enrichment:quote_occurs_more_than_once'):
        validate_answer(wrong(real_with_fold(), 'fold_enrichment', quote='(Fig. 1A)'), REAL)                 # the paragraph has '(Fig. 1A)' three times
    with pytest.raises(ExtractionRefused, match='reciprocal_done:quote_occurs_more_than_once'):
        validate_answer(wrong(real_answer(), 'reciprocal_done', quote='Ku70/80'), REAL)                      # 'Ku70/80' occurs several times
    assert validate_answer(real_answer(), REAL)


def test_an_answer_outside_the_schema_is_refused():
    answer = synthetic_answer()
    for name, unit in (('nacl_wash', 'uM'), ('fold_enrichment', 'percent'), ('percent_input_recovered', 'ratio'), ('incubation_time', 'days'), ('incubation_temperature', 'F'), ('detergent_wash', 'mM'), ('wash_count', 'ratio')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, unit=unit), SYNTHETIC)
    for name, value in ((DETECTION, 'immunofluorescence'), (CAPTURE, 'protein_a'), (SOURCE, 'organoid'), (NUCLEASE, 'ethidium_bromide'), (CROSSLINKER, 'uv'), ('nuclease_treatment', 'dnase1')):
        with pytest.raises(ExtractionRefused, match='schema'):
            validate_answer(wrong(answer, name, value=value), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer(wrong(answer, 'reciprocal_done', value='unknown'), SYNTHETIC)  # 'unknown' is unavailable
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: value for name, value in answer.items() if name != 'input_lane_shown'}, SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'kd': {'status': 'unavailable', 'value': None, 'unit': None, 'quote': None, 'reason': 'not_stated_in_passage'}}, SYNTHETIC)   # a pull-down has no KD
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({**answer, 'free_text': 'a paragraph'}, SYNTHETIC)
    for name in ('wash_count', 'replicate_count'):
        with pytest.raises(ExtractionRefused, match=name + '.value:schema'):
            validate_answer(wrong(answer, name, value=2.5), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fold_enrichment:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'fold_enrichment', value=0), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='percent_input_recovered:number_must_be_above_zero'):
        validate_answer(wrong(answer, 'percent_input_recovered', value=-4), SYNTHETIC)


def test_a_field_is_stated_with_its_quote_or_unavailable_with_a_reason_and_nothing_else():
    answer = synthetic_answer()
    with pytest.raises(ExtractionRefused, match='fold_enrichment:stated_has_value_unit_quote_span_and_no_reason'):
        validate_answer(wrong(answer, 'fold_enrichment', quote=None), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fold_enrichment:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'fold_enrichment', status='unavailable', reason='not_stated_in_passage'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fold_enrichment:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'fold_enrichment', status='unavailable', value=None, unit=None, quote=None), SYNTHETIC)


def test_a_stated_field_needs_a_support_from_the_vocabulary_and_an_unavailable_one_has_none():
    answer = synthetic_answer()
    for name in ('fold_enrichment', 'incubation_time', DETECTION, 'reciprocal_done'):       # a quantity, a time, a choice and a fact
        with pytest.raises(ExtractionRefused, match=name + ':stated_has_value_unit_quote_span_and_no_reason'):
            validate_answer(wrong(answer, name, support=None), SYNTHETIC)
        with pytest.raises(ExtractionRefused, match=name + '.support:schema'):
            validate_answer(wrong(answer, name, support='strong'), SYNTHETIC)
    with pytest.raises(ExtractionRefused, match='fold_enrichment:unavailable_has_a_reason_and_nothing_else'):
        validate_answer(wrong(answer, 'fold_enrichment', status='unavailable', value=None, unit=None, quote=None, reason='not_stated_in_passage'), SYNTHETIC)      # support kept on an unavailable field
    with pytest.raises(ExtractionRefused, match='schema'):
        validate_answer({name: {key: value for key, value in item.items() if key != 'support'} if name == 'fold_enrichment' else item for name, item in answer.items()}, SYNTHETIC)
    for support in ('direct', 'implied', 'about_something_else'):
        assert validate_answer(wrong(answer, 'fold_enrichment', support=support), SYNTHETIC)


def test_the_record_carries_the_support_of_every_stated_value():
    answer = synthetic_answer()
    answer['fold_enrichment']['support'], answer['wash_count']['support'], answer[DETECTION]['support'] = 'implied', 'about_something_else', 'implied'
    answer['reciprocal_done']['support'] = 'about_something_else'
    record = record_from_answer(validate_answer(answer, SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['fold_enrichment']['support'] == 'implied' and record['quantities']['wash_count']['support'] == 'about_something_else' and record['quantities']['nacl_wash']['support'] == 'direct'
    assert record['facts']['reciprocal_done']['support'] == 'about_something_else' and record['facts']['input_lane_shown']['support'] == 'direct'
    assert record['choice_support'][DETECTION] == 'implied' and record['choice_support'][CAPTURE] == 'direct' and set(record['choice_support']) == {DETECTION, CAPTURE, SOURCE, NUCLEASE, CROSSLINKER}
    blank = record_from_answer(validate_answer(answer_from(SYNTHETIC, {}), SYNTHETIC), SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert blank['quantities']['fold_enrichment']['support'] is None and blank['facts']['reciprocal_done']['support'] is None and set(blank['choice_support'].values()) == {None}
    assert grade_pulldown(record)['native']['support']['reciprocal'] == ['about_something_else']      # the grader keeps it for the sheet


def test_every_synthetic_field_is_stated_so_the_test_passage_covers_the_whole_form():
    assert set(SYNTHETIC_STATED) == set(field_names())
    assert answer_from(SYNTHETIC, {})['fold_enrichment']['status'] == 'unavailable'


def test_every_synthetic_quote_occurs_exactly_once_and_says_its_value():
    for name, (value, unit, quote) in SYNTHETIC_STATED.items():
        assert quote_span(SYNTHETIC, quote) is not None, name
    assert validate_answer(synthetic_answer(), SYNTHETIC)


def test_other_units_of_the_vocabulary_are_accepted_and_reach_the_record():
    answer = synthetic_answer()
    answer['nacl_wash'] = {**answer['nacl_wash'], 'value': 0.3, 'unit': 'M'}
    answer['incubation_time'] = {**answer['incubation_time'], 'value': 120, 'unit': 'min'}
    answer['incubation_temperature'] = {**answer['incubation_temperature'], 'value': 277.15, 'unit': 'K'}
    assert validate_answer(answer, SYNTHETIC) is answer
    record = record_from_answer(answer, SYNTHETIC, 0, 'exp', 'src', 'hyp')
    assert record['quantities']['nacl_wash']['unit'] == 'M' and record['quantities']['incubation_temperature']['unit'] == 'K'
    graded = grade_pulldown(record)
    assert graded['native']['nacl_wash_mM'] == pytest.approx(300.0) and graded['native']['incubation_min'] == pytest.approx(120.0)
