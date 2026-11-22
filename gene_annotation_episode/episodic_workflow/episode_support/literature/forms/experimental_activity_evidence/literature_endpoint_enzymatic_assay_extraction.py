"""The extraction of ONE end-point determination with a second enzyme (type 'endpoint_enzymatic_assay') from one chunk of text, derived from the
grader's input form (``literature_endpoint_enzymatic_assay_record.py``). DRAFT (2026-11-22), owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_enzymatic_assay_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_enzymatic_assay_record import (
    FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'standard_series_points')
AT_MOST_ONE = ('standard_curve_r_squared',)   # R squared is a share of the variance: a stated value above 1 is refused, not read

MEANING = {
    'conversion_percent': 'The share of the substrate that the first enzyme converted by the end point, for the test reaction, as the passage states it, as a percent or as a fraction between 0 and 1. Give it only when the number is the share converted (not the share left over, not a yield of some other compound, not a rate).',
    'conversion_percent_spread': 'The reported uncertainty of that share converted (the number after a plus-minus sign, or a standard error or deviation), in the unit of the share.',
    'net_conversion_percent': 'The share of the substrate converted by the first enzyme AFTER the passage\'s own control (a reaction without the enzyme, with an inactive enzyme, or at time zero) has been subtracted, when the passage states that corrected value itself, as a percent or as a fraction between 0 and 1.',
    'net_conversion_percent_spread': 'The reported uncertainty of that control-corrected share converted, in the unit of the share.',
    'product_amount': 'The amount or concentration of the product that the first enzyme formed by the end point (not the substrate that is left), as measured with the second enzyme, in nM, uM, mM or in pmol, nmol, umol.',
    'product_amount_spread': 'The reported uncertainty of that product amount, in the unit of the product amount.',
    'reaction_volume': 'The volume of the reaction mixture of the first enzyme (the reaction in which the product formed), in uL or mL, when the passage states it.',
    'substrate_initial': 'The concentration of the substrate of the first enzyme at the start of its reaction, as the passage reports it, in nM, uM or mM. It is the amount the share converted is taken from.',
    'endpoint_time': 'The time after the start of the first enzyme\'s reaction at which it was stopped or read for the end point, in s, min or h.',
    'second_enzyme_incubation': 'How long the sample was incubated with the second enzyme (and its reporter reagents) before the end-point signal was read, in s, min or h.',
    'standard_series_low': 'The lowest amount or concentration of the standard series of the measured analyte that was run through the second-enzyme assay, in nM, uM, mM or in pmol, nmol, umol.',
    'standard_series_high': 'The highest amount or concentration of the standard series of the measured analyte that was run through the second-enzyme assay, in nM, uM, mM or in pmol, nmol, umol.',
    'standard_series_points': 'The number of different standard amounts or concentrations in the standard series (repeats of one standard are not counted), a whole number.',
    'standard_curve_r_squared': 'The R squared (coefficient of determination) of the standard curve, a number between 0 and 1. A correlation coefficient r that is not squared is not this field.',
    'read_amount': 'The amount or concentration of the analyte in the sample as it was read against the standard series (after any dilution of the sample), in nM, uM, mM or in pmol, nmol, umol, when the passage states it.',
    'detection_limit': 'The detection limit (the smallest analyte the second-enzyme assay tells from the blank) that the passage states, as a concentration in nM, uM or mM.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the conversion and the amount) are.',
    'no_enzyme_control': 'Whether the passage says a reaction mixture without the first enzyme (a no-enzyme blank) was carried through the same end-point measurement.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive first enzyme (heat-denatured, boiled or a catalytically dead mutant) was carried through the same end-point measurement.',
    'zero_time_sample': 'Whether the passage says a sample taken at time zero of the first reaction (before any conversion) was measured.',
    'reaction_stopped_before_analysis': 'Whether the passage says the first reaction was stopped (quenched, heat-inactivated, acidified, filtered) before the second-enzyme measurement, so the time of the end point is the real one.',
    'same_time_for_compared_arms': 'Whether the passage says the compared reactions (test and control, or the compared enzymes) were stopped or read at the same time.',
    'standard_series_through_second_enzyme': 'Whether the passage says the standard series of the analyte was run through the same second-enzyme assay as the samples.',
    'read_amount_within_standard_series': 'Whether the passage says the measured amounts fell within the range of the standard series (or its linear range): yes when it says so, no only when it says they fell outside it.',
    'matrix_matched_standards': 'Whether the passage says the standards were prepared in the reaction buffer or the reaction matrix of the samples (not in water).',
    'spike_recovery_done': 'Whether the passage says a known amount of the analyte was added to the reaction mixture or the sample and recovered (a spike or recovery test).',
    'second_enzyme_specificity_checked': 'Whether the passage says it was checked that the second enzyme does not act on the original substrate, on the test compound or on other components of the mixture (or states the second enzyme is specific for the analyte and shows it).',
    'reporter_conversion_complete': 'Whether the passage says the second reaction went to completion (the signal reached a plateau, or enough second enzyme and cofactor were added for complete conversion of the analyte).',
    'initial_substrate_determined': 'Whether the passage says the amount of substrate at the start was measured (for example in a zero-time sample), as opposed to taking the nominal concentration.',
    'product_confirmed_independently': 'Whether the passage says the product was also identified or measured by another method (for example chromatography, mass spectrometry or NMR).',
    'substrate_loss_matches_product_gain': 'Whether the passage says the substrate that disappeared matches the product that appeared (a mass balance).',
    'enzyme_dependence_shown': 'Whether the passage says the conversion depended on the first enzyme in a way that shows the enzyme made it: it rose with the amount of enzyme or the time, or it fell with an inhibitor or an inactive mutant.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the first enzyme, as opposed to a surrogate.',
    'purified_enzyme': 'Whether the passage says the first enzyme was purified (as opposed to a cell lysate, an extract or whole cells).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'conversion_detected_above_control': 'Whether the passage says conversion by the first enzyme was seen above the paper\'s own control: yes when it states conversion was detected above the control or the blank, no only when it states that no conversion above the control, the blank or the detection limit was detected.',
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
    occurs exactly once in ``chunk``; a number is above 0 (R squared also at most 1) and a stated value carries its unit
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
        if name in AT_MOST_ONE and item['value'] > 1:
            _refuse(name, 'number_must_be_at_most_one')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_endpoint_enzymatic_assay_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'endpoint_enzymatic_assay', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
