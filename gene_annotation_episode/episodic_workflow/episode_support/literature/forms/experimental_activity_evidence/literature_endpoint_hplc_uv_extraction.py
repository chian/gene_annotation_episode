"""The extraction of ONE fixed-time enzyme reaction read by HPLC (type 'endpoint_hplc_uv') from one chunk of text, derived from the grader's input form
(``literature_endpoint_hplc_uv_record.py``). DRAFT of 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand.
The things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_hplc_uv_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the
model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the
converter judges it.

A percent of the substrate cannot be more than 100: a share above 100 (an HPLC reading of 102 percent yield, say) is refused as a value, and the model
answers that field unavailable. This is the planned case of the form, not a guard: the direction function of the class requires a fraction of at most 1.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``)
are given by the caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown
(None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_hplc_uv_record import (
    DETECTORS, FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
DETECTOR = 'detector'
# The plain choice fields and their fixed vocabularies (recorded for the reviewer; no criterion rests on a choice).
CHOICES = {SPREAD_KIND: SPREAD_KINDS, DETECTOR: DETECTORS}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('standard_curve_points', 'replicate_count', 'injection_replicates')
# The quantities that are a share of the substrate: a stated value is at most 100 percent.
SHARES = ('conversion_percent', 'net_conversion_percent', 'control_conversion_percent')
SHARE_MAXIMUM = 100   # FIXED_BY_DEFINITION: a share of the substrate cannot exceed the whole.

MEANING = {
    'conversion_percent': 'The percent of the initial substrate that was converted at the end point (the time the reaction was stopped), as the passage states it: percent conversion, or the percent yield of the product over the starting substrate. A number from above 0 to 100. It is not a rate and not the time the reaction needed. If the passage gives it only as a limit (for example less than 1 percent), it is not stated.',
    'conversion_spread': 'The reported uncertainty of the percent converted (the number after a plus-minus sign, or a standard error or deviation), in percent.',
    'net_conversion_percent': 'The percent converted over and above the paper\'s own control (the conversion with the enzyme minus the conversion in the no-enzyme or inactive-enzyme control), ONLY when the passage itself states this corrected value as one number above 0 and at most 100. Never work it out from two numbers.',
    'net_conversion_spread': 'The reported uncertainty of that control-corrected percent converted, in percent.',
    'control_conversion_percent': 'The percent of the substrate that was converted in the paper\'s own control in the same measurement (the reaction without the enzyme, or with an inactive or heat-treated enzyme), when the passage gives it as a number above 0 and at most 100. A control that showed no product is not a number: leave it unavailable.',
    'product_amount': 'The concentration of the product at the end point as the passage reports it (quantified by HPLC against a standard), in nM, uM or mM. Not an amount in moles, not a peak area and not a percent.',
    'product_amount_spread': 'The reported uncertainty of the product concentration, in the unit of the product concentration.',
    'substrate_initial': 'The concentration of the substrate at the start of the reaction (in the reaction mixture), in nM, uM or mM.',
    'endpoint_time': 'The time at which the reaction was stopped and sampled for the result (the incubation time of the end point), in s, min or h.',
    'enzyme_concentration': 'The concentration of the enzyme in the reaction, in nM, uM or mg/mL.',
    'standard_curve_low': 'The lowest concentration of the standard (calibration) curve of the authentic standard that the HPLC quantification used, in nM, uM or mM.',
    'standard_curve_high': 'The highest concentration of the standard (calibration) curve of the authentic standard that the HPLC quantification used, in nM, uM or mM.',
    'standard_curve_points': 'The number of different concentrations (calibration points) of the standard curve (a whole number).',
    'detection_limit': 'The detection limit or the quantification limit of the HPLC method for the product (or the substrate), as a concentration in nM, uM or mM.',
    'replicate_count': 'The number of replicate reactions (separate reaction mixtures) the passage reports for this result (a whole number).',
    'injection_replicates': 'The number of repeated injections of one and the same reaction sample onto the column, when the passage gives it (a whole number). Repeated injections are not replicate reactions.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the conversion and the product amount) are.',
    DETECTOR: 'How the peaks were detected: ultraviolet absorbance at one wavelength (uv), a diode array (diode_array), a refractive-index detector (refractive_index) or another detector (other).',
    'no_enzyme_control_done': 'Whether the passage says a control reaction without the enzyme (a no-enzyme blank, or buffer and substrate only) was run and analysed.',
    'inactive_enzyme_control_done': 'Whether the passage says a control reaction with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run and analysed.',
    'zero_time_sample_done': 'Whether the passage says a sample taken at time zero (or stopped before the enzyme could act) was analysed.',
    'enzyme_dependence_shown': 'Whether the passage says the conversion depends on the enzyme: it rises with the amount of enzyme, or falls with an inhibitor or an inactive mutant.',
    'authentic_standard_used': 'Whether the passage says the product peak was identified by comparison with an authentic standard of the product (the same retention time, or co-elution after adding the standard).',
    'peak_confirmed_by_second_method': 'Whether the passage says the product peak was confirmed by another method, such as mass spectrometry or NMR of the collected peak.',
    'substrate_loss_matches_product_gain': 'Whether the passage says the substrate lost equals the product gained (a mass balance that closes).',
    'reaction_stopped_before_analysis': 'Whether the passage says the reaction was stopped (quenched with acid, solvent or heat, or the enzyme removed) before the sample was analysed.',
    'same_time_for_compared_arms': 'Whether the passage says the compared reactions (test and control, or the compared enzymes) were stopped at the same time. Answer no only when the passage says the times differed.',
    'initial_substrate_determined': 'Whether the passage says the starting amount of the substrate was measured (for example by analysing the time-zero sample) rather than taken from the nominal recipe.',
    'both_species_quantified': 'Whether the passage says both the substrate and the product were quantified from the chromatograms.',
    'calibration_in_matrix': 'Whether the passage says the standard curve was prepared in the reaction buffer or matrix (matrix-matched), not in pure solvent.',
    'internal_standard_used': 'Whether the passage says an internal standard was added to the samples before injection.',
    'independent_replicates': 'Whether the passage says the replicates were independent reactions (different days, enzyme preparations or reaction mixtures) rather than repeated injections of one reaction.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to an analogue or surrogate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate, extract or whole cells).',
    'conversion_detected_above_control': 'Whether the passage says conversion was seen above the paper\'s own control or detection limit: yes when it states that product formation (or substrate loss) was detected above the control, no only when it states that no conversion above the control or the detection limit was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the plain choices, the facts."""
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
    occurs exactly once in ``chunk``; a number is above 0 (a share of the substrate also at most 100) and a stated value carries its unit
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
        if name in SHARES and item['value'] > SHARE_MAXIMUM:
            _refuse(name, 'a_share_of_the_substrate_is_at_most_100_percent', 'answer_unavailable_when_the_passage_gives_more')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_endpoint_hplc_uv_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'endpoint_hplc_uv', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
