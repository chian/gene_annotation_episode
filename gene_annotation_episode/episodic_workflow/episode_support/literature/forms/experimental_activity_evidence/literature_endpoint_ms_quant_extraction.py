"""The extraction of ONE fixed-time enzyme reaction with mass-spectrometric product quantification (type 'endpoint_ms_quant') from one chunk of text,
derived from the grader's input form (``literature_endpoint_ms_quant_record.py``). DRAFT of 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_ms_quant_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

A share converted cannot exceed the whole: a stated conversion (the share converted, the share net of the control, the control's own share) is
refused above 100 percent or above 1 as a fraction, as a number at or under 0 is refused for every quantity.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_ms_quant_record import (
    FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('calibration_points', 'replicate_count')
# The quantities that are a share of the whole substrate, and the largest value each unit can take (FIXED_BY_DEFINITION: the whole is 100 percent or 1).
SHARES = ('conversion_fraction', 'conversion_difference', 'control_conversion')
WHOLE = {'percent': 100, 'fraction': 1}

MEANING = {
    'conversion_fraction': 'The share of the substrate that was converted at the end point, as the passage states it (the conversion, or the yield of the product over the starting substrate), in percent or as a fraction. It is NOT corrected by the paper\'s own control.',
    'conversion_fraction_spread': 'The reported uncertainty of that share converted (the number after a plus-minus sign, or a standard error or deviation), in the unit of the share.',
    'conversion_difference': 'The share of the substrate converted MINUS the share of the paper\'s own control (no enzyme, inactive enzyme or zero time), when the passage states that corrected value itself, in percent or as a fraction. Never work it out yourself.',
    'conversion_difference_spread': 'The reported uncertainty of that control-corrected share, in the unit of the corrected share.',
    'completion_time_ratio': 'How many times shorter the completion time of the test is than the reference completion time of the paper (a control, an earlier preparation or a wild type), when the passage states that ratio itself, as a fold.',
    'completion_time_ratio_spread': 'The reported uncertainty of that ratio, as a fold.',
    'completion_time': 'The time the reaction needed to reach the completion or the equilibrium the passage defines, in s, min or h. A bound such as "more than 18 h" is not a value of this field.',
    'completion_time_spread': 'The reported uncertainty of that completion time, in the unit of the completion time.',
    'endpoint_amount': 'The amount or the concentration of the product (or of the substrate left) the passage reports at the end point, in nM, uM or mM, or as an amount in pmol, nmol or umol.',
    'endpoint_amount_spread': 'The reported uncertainty of that amount or concentration, in the unit of the amount.',
    'control_conversion': 'The share of the substrate converted in the paper\'s own control (a reaction without the enzyme, with an inactive enzyme, or the sample taken at time zero), in percent or as a fraction, as the passage states it.',
    'substrate_initial': 'The initial amount or concentration of the substrate the share converted is taken from, in nM, uM or mM, or as an amount in pmol, nmol or umol.',
    'reaction_volume': 'The volume of the reaction mixture, in uL or mL.',
    'endpoint_time': 'The time after which the reaction was stopped and the product measured (the incubation time of the end point), in s, min or h.',
    'calibration_low': 'The lowest concentration of the calibration standards (the standard curve) the product was quantified against, in nM, uM or mM.',
    'calibration_high': 'The highest concentration of the calibration standards (the standard curve) the product was quantified against, in nM, uM or mM.',
    'calibration_points': 'The number of concentration levels of the calibration curve (a whole number).',
    'quantification_limit': 'The lowest concentration of the product the passage says can be quantified (the limit of quantification, LOQ or LLOQ), in nM, uM or mM.',
    'detection_limit': 'The lowest concentration of the product the passage says can be detected (the limit of detection, LOD), in nM, uM or mM.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the conversion, time and amount quantities) are.',
    'no_enzyme_control_done': 'Whether the passage says a control without the enzyme (a no-enzyme blank, or a buffer-only reaction) was run and analysed like the test.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run and analysed like the test.',
    'zero_time_sample_done': 'Whether the passage says a sample taken at time zero (or stopped at once) was analysed.',
    'enzyme_dependence_shown': 'Whether the passage says the product depends on the enzyme: it rises with the amount of enzyme, or is lost with an inactive mutant, a heat-treated enzyme or an inhibitor.',
    'internal_standard_used': 'Whether the passage says an internal standard (a stable-isotope-labelled or a structurally related compound added to every sample) was used for the mass-spectrometric quantification.',
    'matrix_matched_calibration': 'Whether the passage says the calibration standards were prepared in the matrix of the reaction (the same buffer, extract or quenched reaction mixture) rather than in plain solvent.',
    'authentic_standard_used': 'Whether the passage says the product was identified or quantified against an authentic (pure, commercial or synthesised) standard of the product.',
    'ms_ms_confirmation': 'Whether the passage says the product was confirmed by its fragmentation (MS/MS, MS2 or a selected transition).',
    'accurate_mass_match': 'Whether the passage says the measured mass of the product matched its calculated mass within a stated accuracy (an accurate-mass measurement).',
    'amounts_within_calibration_range': 'Whether the passage says the measured product amounts lay within the range of the calibration curve (interpolated), as opposed to outside it (extrapolated).',
    'reaction_stopped_before_analysis': 'Whether the passage says the reaction was stopped (quenched with acid or solvent, heated or filtered) at the end point before the sample was analysed.',
    'same_time_for_compared_arms': 'Whether the passage says the compared reactions (test and control, or the compared enzymes) were stopped and read at the same time.',
    'initial_substrate_determined': 'Whether the passage says the initial amount of the substrate was measured (for example by a sample at time zero) rather than taken from the nominal amount weighed or pipetted.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate or analogue.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate, an extract or whole cells).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated injections of one sample.',
    'conversion_detected_above_control': 'Whether the passage says conversion of the substrate was detected above the paper\'s own control: yes when it states that product or conversion was detected above the control or the detection limit, no only when it states that no conversion above the control or the detection limit was detected.',
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
    where the field has one; a share converted is not above the whole; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
        if name in SHARES and item['value'] > WHOLE[item['unit']]:
            _refuse(name, 'share_converted_is_above_the_whole')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_endpoint_ms_quant_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'endpoint_ms_quant', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
