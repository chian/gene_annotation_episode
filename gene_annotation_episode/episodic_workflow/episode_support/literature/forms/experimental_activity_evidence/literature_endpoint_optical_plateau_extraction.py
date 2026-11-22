"""The extraction of ONE reaction run to an optical plateau (type 'endpoint_optical_plateau') from one chunk of text, derived from the grader's input
form (``literature_endpoint_optical_plateau_record.py``). DRAFT 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand.
The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_optical_plateau_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model
and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread kind); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are
given by the caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_optical_plateau_record import (
    FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'conversion_percent': 'The share of the substrate that was converted when the signal reached its plateau, as the passage states it (for example "92% of the substrate was converted" or "conversion of 0.92"), in percent or as a fraction. Only a share of the substrate converted, not a share of a signal or of an enzyme activity.',
    'conversion_percent_spread': 'The reported uncertainty of that conversion (the number after a plus-minus sign, or a standard error or deviation), in the unit of the conversion.',
    'net_conversion_percent': 'The conversion at the plateau after the paper itself has subtracted its own control (the no-enzyme or inactive-enzyme control), when the passage states that corrected value (for example "net conversion of 88%"), in percent or as a fraction.',
    'net_conversion_percent_spread': 'The reported uncertainty of the control-corrected conversion, in the unit of that conversion.',
    'control_conversion': 'The conversion that the paper\'s own control (a reaction without the enzyme, or with an inactive enzyme) shows over the same time, as the passage states it (for example "the no-enzyme control showed 3% conversion"), in percent or as a fraction.',
    'product_amount': 'The amount of the product (or of the substrate used up) at the plateau, as a concentration the passage states, in nM, uM or mM. An amount in moles is not this field.',
    'product_amount_spread': 'The reported uncertainty of the product amount, in the unit of the product amount.',
    'time_to_plateau': 'The time the signal took to reach its plateau (the reaction to be complete), as one stated time (for example "the signal reached a plateau after 25 min"), in s, min or h. A bound such as "more than 2 h" or "within 30 min" is not a stated time.',
    'time_to_plateau_spread': 'The reported uncertainty of the time to the plateau, in the unit of that time.',
    'substrate_initial': 'The concentration of the substrate at the start of the reaction (the amount the conversion is taken from), in nM, uM or mM.',
    'signal_change_total': 'The final change of the signal of the test reaction from its start to the plateau, as the passage states it: in absorbance units (AU) for an absorbance reading, or in relative fluorescence units (RFU) for a fluorescence reading.',
    'signal_change_baseline': 'The change of the signal of the no-enzyme baseline over the same time (the drift of a reaction without the enzyme), in absorbance units (AU) or relative fluorescence units (RFU).',
    'signal_change_full': 'The signal change of the full-conversion reference: the same substrate amount converted completely (by excess enzyme or by a chemical reaction), or the signal of the same amount of free product or fluorophore, in absorbance units (AU) or relative fluorescence units (RFU).',
    'extinction_coefficient': 'The extinction (molar absorption) coefficient the passage uses to turn the absorbance change into a concentration, in M^-1 cm^-1 or mM^-1 cm^-1.',
    'path_length': 'The optical path length of the measurement (the cuvette or the liquid column in the plate), in cm or mm.',
    'wavelength': 'The wavelength at which the signal was read (for a fluorescence reading the emission wavelength), in nm.',
    'absorbance_max': 'The highest absorbance reached in the measurement, or the absorbance range the passage says was kept below (for example "absorbance below 1.0"), in absorbance units (AU).',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the conversion, the amount and the time) are.',
    'no_enzyme_control_done': 'Whether the passage says a control without the enzyme (a no-enzyme baseline or a buffer-only reaction) was measured.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured.',
    'control_read_over_same_time': 'Whether the passage says the control was followed over the same time as the reaction (the baseline was run as long as the test).',
    'full_conversion_reference_done': 'Whether the passage says a full-conversion reference was measured: the same substrate amount converted completely (by excess enzyme or a chemical reaction), or a standard of the free product or fluorophore, to give the signal change of complete conversion.',
    'plateau_stable': 'Whether the passage says the signal stayed constant after it reached its plateau (no further change was seen over a further stretch of time), so that the end point is a plateau and not a point on a slope.',
    'signal_in_linear_range': 'Whether the passage says the signal stayed in the range where the detector responds linearly to the concentration (for example an absorbance below the linear limit of the instrument, or a fluorescence below detector saturation).',
    'inner_filter_checked': 'Whether the passage says the inner-filter effect, quenching or absorbance of the substrate or other components at the read wavelength was checked or corrected at the substrate concentration used.',
    'enzyme_dependence_shown': 'Whether the passage says the signal change depends on the enzyme: it grows with the enzyme amount, or is lost with an inactive enzyme or an inhibitor.',
    'initial_substrate_determined': 'Whether the passage says the starting amount of the substrate (the denominator of the conversion) was measured, as opposed to taken from the weighed or nominal concentration.',
    'product_identified_by_standard': 'Whether the passage says the product behind the signal change was identified by another measurement (for example chromatography or mass spectrometry against an authentic standard).',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a chromogenic or fluorogenic surrogate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'conversion_detected_above_control': 'Whether the passage says the reaction converted substrate above the paper\'s own control: yes when it states a conversion or a signal change above the control or the detection limit was seen, no only when it states that no conversion or no signal change above the control or the detection limit was seen.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the spread kind, the facts."""
    return (*QUANTITIES, SPREAD_KIND, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(SPREAD_KINDS)} if name == SPREAD_KIND else
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
    """The record of ``literature_endpoint_optical_plateau_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'endpoint_optical_plateau', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
