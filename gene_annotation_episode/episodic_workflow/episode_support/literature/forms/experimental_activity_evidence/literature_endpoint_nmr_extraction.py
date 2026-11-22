"""The extraction of ONE NMR end-point conversion experiment (type 'endpoint_nmr') from one chunk of text, derived from the grader's input form
(``literature_endpoint_nmr_record.py``). DRAFT, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_nmr_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

A share of the substrate cannot exceed the whole substrate: a stated conversion, control conversion, net conversion or detection limit above 100 percent (or above 1
as a fraction) is refused, so the model is asked again with the reason. This is a physical limit of the form, not a threshold of judgement.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_nmr_record import (
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
SHARES = ('conversion', 'control_conversion', 'net_conversion', 'detection_limit')   # a share of the substrate: at most the whole of it
WHOLE = {'percent': 100, 'fraction': 1}                                              # FIXED_BY_DEFINITION: the whole substrate in each unit

MEANING = {
    'conversion': 'The share of the substrate that was converted to product at the time the NMR spectrum was read (or when the reaction was complete), worked out from the integrals of the substrate and product signals and given in the passage as the conversion or the yield of the enzyme reaction: in percent, or as a fraction between 0 and 1. One value for the test reaction, not for a control.',
    'conversion_spread': 'The reported uncertainty of the conversion (the number after a plus-minus sign, or a standard error or deviation), in percent or as a fraction like the conversion.',
    'control_conversion': 'The conversion the passage reports for the paper\'s own control read at the same time (a reaction without the enzyme, or with an inactive or heat-treated enzyme), in percent or as a fraction.',
    'net_conversion': 'The conversion of the test reaction after the control was subtracted, when the passage itself states that corrected value (for example "net conversion" or "above the no-enzyme control"), in percent or as a fraction.',
    'product_concentration': 'The concentration of the product at the end point, as the passage reports it from the NMR integrals against an internal standard, in uM or mM.',
    'endpoint_time': 'The time at which the NMR spectrum was read, or at which the reaction was stopped before it was read (the incubation time of the end point), in s, min or h.',
    'acquisition_duration': 'How long the NMR spectrum took to record (the total acquisition time), in s, min or h, when the passage states it.',
    'relaxation_delay': 'The relaxation delay (recycle delay, d1) between the scans of the NMR experiment, in ms or s.',
    'longest_t1': 'The longest spin-lattice relaxation time T1 of the signals that were integrated, as the passage reports it, in ms or s.',
    'signal_to_noise': 'The signal-to-noise ratio of the NMR signal the conversion rests on (the weaker of the substrate and product signals), as a plain number: for example "S/N of 150:1" is 150.',
    'detection_limit': 'For a result stated as not detected: the smallest conversion the spectrum could have shown (the detection limit, or "below x percent"), in percent or as a fraction.',
    'replicate_count': 'The number of replicate reactions the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spread of the conversion is.',
    'no_enzyme_control': 'Whether the passage says a control reaction without the enzyme (the same substrate, buffer and time) was recorded by NMR.',
    'inactive_enzyme_control': 'Whether the passage says a control reaction with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was recorded by NMR.',
    'enzyme_dependence_shown': 'Whether the passage says the conversion depends on the enzyme: it rises with the amount of enzyme, or it is lost when the enzyme is inactivated, inhibited or removed. Answer no only when the passage says the conversion did not depend on the enzyme.',
    'product_signal_assigned': 'Whether the passage says the product signal was assigned by comparison with the spectrum of an authentic standard, by adding (spiking) the authentic compound, or by a stated further assignment (two-dimensional NMR or mass spectrometry).',
    'substrate_loss_matches_product_gain': 'Whether the passage says the loss of the substrate signal equals the gain of the product signal (the sum of the integrals stayed constant, or no other signal appeared).',
    'quantitative_acquisition': 'Whether the passage says the spectra were recorded under quantitative conditions: a relaxation delay long enough for the nuclei to relax between scans (for example five times T1) or a stated quantitative NMR protocol. Answer no only when the passage says a short delay or a non-quantitative acquisition was used.',
    'signals_resolved': 'Whether the passage says the substrate and product signals that were integrated are separate from each other and from the signals of the buffer, the protein and other compounds (no overlap). Answer no only when the passage says they overlapped.',
    'reaction_stopped_before_analysis': 'Whether the passage says the reaction was stopped (quenched, acidified, heat-inactivated, the enzyme removed or filtered) before the NMR spectrum was recorded, so that the stated time is the true end point. Answer no only when the passage says the spectrum was recorded while the reaction was still running.',
    'same_time_for_compared_arms': 'Whether the passage says the test reaction and its control or compared reaction were read at the same time point.',
    'initial_substrate_determined': 'Whether the passage says the initial amount of the substrate was measured by NMR (a spectrum recorded before the enzyme was added or at time zero), as opposed to taken from the amount weighed.',
    'both_species_integrated': 'Whether the passage says the conversion was taken from the integrals of both the substrate and the product signals of the same spectrum (for example product over substrate plus product).',
    'internal_standard_used': 'Whether the passage says an internal standard of known concentration (for example TSP, DSS, dioxane, maleic acid or an electronic reference) was used to quantify the integrals.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to an analogue or surrogate substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent reactions (different days, preparations or reaction mixtures) rather than repeated spectra of one reaction.',
    'conversion_detected_above_control': 'Whether the passage says conversion was detected above the paper\'s own control or detection limit: yes when it states that the product was detected above the control or detection limit, no only when it states that no product (no conversion) was detected above the control or detection limit.',
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
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit where the field has one; a share of the substrate is at most the
    whole substrate; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
            _refuse(name, 'a_share_of_the_substrate_cannot_exceed_the_whole', 'give_percent_up_to_100_or_a_fraction_up_to_1')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_endpoint_nmr_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'endpoint_nmr', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
