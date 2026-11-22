"""The extraction of ONE sampled reaction followed to a stated completion or equilibrium (type 'endpoint_time_course_completion') from one chunk of text, derived from the
grader's input form (``literature_endpoint_time_course_completion_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand. The things this
module offers are all derived from the form's own declarations (its quantities, units, choices, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered 'unavailable' with a reason (a
                        field the passage does not state is never guessed and never 0). A field that is stated carries its value and the quote that states it. The model gives
                        only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that occurs more than once must be made
                        longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_time_course_completion_record``), with the operand constructors of that
                        form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model and validated here;
an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller and
the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_time_course_completion_record import (
    COMPLETION_CRITERIA, DETECTION_METHODS, FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
COMPLETION_CRITERION = 'completion_criterion'
DETECTION_METHOD = 'detection_method'
CHOICES = {SPREAD_KIND: SPREAD_KINDS, COMPLETION_CRITERION: COMPLETION_CRITERIA, DETECTION_METHOD: DETECTION_METHODS}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'completion_time': 'The time at which the reaction reached the completion or equilibrium the passage states (for example no substrate left, the product no longer rising, the ratio of the species no longer changing), in s, min or h, as the passage gives it. When the passage gives only a bound ("more than 18 h", "less than 10 min"), give the number of the bound here and answer the fact completion_time_is_exact no.',
    'completion_time_spread': 'The reported uncertainty of the completion time (the number after a plus-minus sign, or a standard error or deviation), in s, min or h.',
    'reference_completion_time': 'The time at which the same completion or equilibrium was reached in the paper\'s reference arm (a control, an earlier or other preparation, the wild type, the reaction before a clean-up step), in s, min or h. When the passage gives only a bound for it, give the number of the bound and answer the fact reference_time_is_exact no.',
    'completion_time_ratio': 'How many times shorter the completion time of the enzyme the passage is about is than the completion time of the reference arm (the reference time over the test time, a value above 1 when the test is sooner), when the passage itself gives that ratio or fold. A bound ("more than 100-fold") is given as its number with the fact completion_time_ratio_is_exact answered no.',
    'completion_time_ratio_spread': 'The reported uncertainty of that ratio, as a fold.',
    'sampling_interval': 'The gap between the samples around the time of completion: the time between the last sample before the completion was seen and the sample that showed it, or the regular spacing of the samples, in s, min or h, when the passage gives it.',
    'enzyme_loading_test': 'The concentration of the enzyme in the reaction of the arm the completion time belongs to, in nM, uM or mg/mL.',
    'enzyme_loading_reference': 'The concentration of the enzyme in the reaction of the reference arm, in nM, uM or mg/mL.',
    'replicate_count': 'The number of independent time courses the passage reports for the result (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the completion time and of the ratio) are.',
    COMPLETION_CRITERION: 'What the passage calls complete: no substrate left (substrate_gone), the product no longer rising (product_plateau), a constant ratio of the species over later samples (ratio_constant), an equilibrium reached (equilibrium_reached), or another stated state (other_stated).',
    DETECTION_METHOD: 'How the course of the reaction was followed: NMR (nmr), chromatography of samples such as HPLC or TLC (chromatography), an optical signal such as absorbance or fluorescence (optical), mass spectrometry (mass_spectrometry), radioactivity (radiometric) or another method (other).',
    'completion_criterion_stated': 'Whether the passage says what state counted as complete or as equilibrium (for example "no substrate signal was left", "the ratio no longer changed").',
    'same_completion_criterion_in_arms': 'Whether the passage says the same completion or equilibrium state was used to read the completion time of the test arm and of the reference arm.',
    'samples_stopped_before_analysis': 'Whether the passage says each sample of the time course was stopped (quenched, heat-inactivated, acidified, frozen or the enzyme removed) before it was analysed, so that the sample shows the reaction at the time it was taken.',
    'no_enzyme_course_done': 'Whether the passage says a time course without the enzyme (substrate in the same buffer, followed for the same time) was measured.',
    'inactive_enzyme_course_done': 'Whether the passage says a time course with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured.',
    'enzyme_dependence_shown': 'Whether the passage says the time to completion depends on the enzyme: it is shorter with more enzyme, or the reaction does not complete with the inactive enzyme or in the presence of an inhibitor.',
    'contaminating_activity_examined': 'Whether the passage says it examined whether the activity belongs to the enzyme and not to a contaminating enzyme of the preparation (for example a second purification step, a catalytic mutant of the same preparation, an activity that follows the enzyme through chromatography).',
    'product_identified_by_standard': 'Whether the passage says the product was identified by an authentic standard or by an independent identification (a reference spectrum, a mass, a co-chromatography with the standard).',
    'substrate_loss_matches_product_gain': 'Whether the passage says the loss of the substrate matches the gain of the product (a mass balance).',
    'initial_substrate_determined': 'Whether the passage says the starting amount of the substrate was measured, as opposed to taking the nominal amount of the recipe.',
    'same_loading_in_arms': 'Whether the passage says the test arm and the reference arm had the same amount of enzyme.',
    'same_temperature_in_arms': 'Whether the passage says the test arm and the reference arm were run at the same temperature.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the time courses were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'completion_time_is_exact': 'Whether the completion time of the test arm is given as a value the passage measured (answer yes) or only as a bound such as "more than", "less than", "at least", "within", ">" or "<" (answer no).',
    'reference_time_is_exact': 'Whether the completion time of the reference arm is given as a value the passage measured (answer yes) or only as a bound such as "more than", "less than", "at least", "within", ">" or "<" (answer no).',
    'completion_time_ratio_is_exact': 'Whether the ratio of the two completion times is given as a value (answer yes) or only as a bound such as "more than 100-fold", ">" or "<" (answer no).',
    'conversion_detected_above_control': 'Whether the passage says the enzyme converted the substrate beyond the paper\'s own control: yes when it states that conversion or completion was observed above the control or detection limit, no only when it states that no conversion above the control or detection limit was observed.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices, the facts."""
    return (*QUANTITIES, *CHOICES, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(CHOICES[name])} if name in CHOICES else
             {'enum': list(STATABLE[name])})
    properties = {'status': {'enum': ['stated', 'unavailable']}, 'value': _nullable(value)}
    if name in UNITS:
        properties['unit'] = _nullable({'enum': list(UNITS[name])})
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': _nullable({'enum': list(SUPPORTS)}), 'reason': _nullable({'enum': list(REASONS)})})
    return {'type': 'object', 'additionalProperties': False, 'description': MEANING[name],
            'required': list(properties), 'properties': properties}


def answer_schema():
    """The JSON schema of an extraction answer: one object per field, named as in the form."""
    schema = {name: _field_schema(name) for name in field_names()}
    return {'type': 'object', 'additionalProperties': False, 'required': list(schema), 'properties': schema}


class ExtractionRefused(ValueError):
    """The answer does not satisfy the answer schema or a quote is not at its span."""


def _refuse(name, code, detail=None):
    raise ExtractionRefused(name + ':' + code + ('' if detail is None else ':' + str(detail)))


def quote_span(chunk, quote):
    """The (start, end) byte span of ``quote`` in ``chunk``, counted in UTF-8 bytes from the first byte of the chunk
    (end is the byte after the last). None unless the quote occurs exactly once."""
    at = chunk.find(quote)
    if not quote or at < 0 or chunk.find(quote, at + 1) >= 0:
        return None
    start = len(chunk[:at].encode('utf-8'))
    return start, start + len(quote.encode('utf-8'))


def _quote(name, item, chunk):
    if not item['quote'] or item['quote'] not in chunk:
        _refuse(name, 'quote_is_not_in_the_chunk')
    if quote_span(chunk, item['quote']) is None:
        _refuse(name, 'quote_occurs_more_than_once', 'make_the_quote_longer_so_it_occurs_once')


def validate_answer(answer, chunk):
    """Raise ``ExtractionRefused`` unless ``answer`` satisfies ``answer_schema()`` and every stated field's quote
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
    errors = sorted(Draft202012Validator(answer_schema()).iter_errors(answer), key=lambda error: list(error.path))
    if errors:
        _refuse('.'.join(str(part) for part in errors[0].path) or 'answer', 'schema', errors[0].message[:200])
    for name in field_names():
        item = answer[name]
        carried = ('value', 'quote', 'support') + (('unit',) if name in UNITS else ())
        if item['status'] == 'unavailable':
            if item['reason'] is None or any(item[key] is not None for key in carried):
                _refuse(name, 'unavailable_has_a_reason_and_nothing_else')
            continue
        if item['reason'] is not None or any(item[key] is None for key in carried):
            _refuse(name, 'stated_has_value_unit_quote_span_and_no_reason')
        if name in QUANTITIES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_endpoint_time_course_completion_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
    in its source: each quote's span is found in the chunk and recorded at its offset in the source. A value not stated is an
    'unavailable' operand with its reason, never 0; a fact not stated is 'unknown'."""
    spans, refs = {}, {}
    for name in field_names():
        if answer[name]['status'] == 'stated':
            refs[name] = 'span_' + name
            spans[refs[name]] = _span(chunk, chunk_offset, answer[name])

    def operand(name):
        item = answer[name]
        if item['status'] == 'unavailable':
            return unavailable(UNITS[name][0], name, item['reason'])
        return point(item['value'], item['unit'], name, [refs[name]], support=item['support'])

    def choice(name):
        return answer[name]['value'] if answer[name]['status'] == 'stated' else None

    return {'version': VERSION, 'experiment_type': 'endpoint_time_course_completion', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
