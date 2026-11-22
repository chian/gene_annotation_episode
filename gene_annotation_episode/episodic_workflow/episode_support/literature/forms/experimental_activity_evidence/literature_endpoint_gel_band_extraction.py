"""The extraction of ONE gel or TLC end-point conversion experiment (type 'endpoint_gel_band') from one chunk of text, derived from the
grader's input form (``literature_endpoint_gel_band_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_gel_band_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices);
the converter judges it.

Numbers: the three conversion quantities (the share converted, the share net of the control, the share in the control lane) may be 0 (no product
band) and may not exceed the whole substrate (100 percent, or 1 as a fraction); the spreads, the time and the count are above 0.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_gel_band_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
SHARES = ('conversion_percent', 'net_conversion_percent', 'control_conversion')     # a share of the substrate: 0 is a stated value, the whole substrate is the ceiling
SHARE_CEILING = {'percent': 100.0, 'fraction': 1.0}       # FIXED_BY_DEFINITION: the whole substrate

MEANING = {
    'conversion_percent': 'The share of the substrate that was converted to product at the end point in the test lane, as the passage states it (for example "62% of the substrate was cleaved", or a fraction such as 0.62). It is the product band over the substrate plus the product bands, or the loss of the substrate band, measured by densitometry or imaging. 0 is a stated value when the passage says no product band was seen and gives the value 0.',
    'conversion_spread': 'The reported uncertainty of that share (the number after a plus-minus sign, or a standard error or deviation), in the unit of the share.',
    'net_conversion_percent': 'The share of the substrate converted after the paper\'s own control (the no-enzyme or inactive-enzyme lane) was subtracted, ONLY when the passage states this corrected value itself. Never work it out by subtracting the control from the test.',
    'net_conversion_spread': 'The reported uncertainty of the control-corrected share, in the unit of that share.',
    'control_conversion': 'The share of the substrate that appears converted in the paper\'s own control lane (no enzyme, inactive enzyme, or the reaction without a required cofactor), as the passage states it; 0 is a stated value when the passage says the control lane shows no product.',
    'endpoint_time': 'The incubation time at the end of which the reaction was stopped and the gel or plate was loaded, in s, min or h (the single time point of the result, not the whole time course).',
    'replicate_count': 'The number of independent experiments (separate reactions and separate gels) the passage reports for the share (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the shares) are.',
    'fraction_defined_over': 'What the converted share is a fraction of: substrate_only (the loss of the substrate band against the substrate before the reaction), substrate_plus_product (the product band over the substrate and product bands of the same lane), or total_lane (the product band over all the bands of the lane).',
    'no_enzyme_lane_done': 'Whether the passage says a control lane or reaction without the enzyme (everything else the same, incubated like the test) was run.',
    'inactive_enzyme_lane_done': 'Whether the passage says a control lane with an inactive enzyme (a catalytic-site mutant, a heat-denatured or boiled enzyme) was run.',
    'zero_time_lane_done': 'Whether the passage says a lane of the substrate before the reaction (a zero-time or untreated substrate lane) was run, to show the substrate does not already hold the product.',
    'product_depends_on_active_enzyme': 'Whether the passage says the product band depended on the active enzyme: yes when it states the product was absent or much reduced with the inactive enzyme, with EDTA or a specific inhibitor, or without a required cofactor; no only when it states the product was also formed in such a control.',
    'band_identified_by_marker': 'Whether the passage says the product band was identified by running it against a size marker, an authentic product standard, or by another method (sequencing, mass spectrometry), as opposed to being only the band that appears when the substrate band shrinks.',
    'signal_within_linear_range': 'Whether the passage says the band signals were measured inside the linear range of the detection (an unsaturated exposure, a standard curve, a dilution series or a phosphorimager linear range).',
    'fraction_from_same_lane_bands': 'Whether the passage says the converted share was calculated from the bands of the same lane (the product over the substrate plus the product, or over the lane total), so that differences in loading cancel.',
    'reaction_stopped_before_loading': 'Whether the passage says the reaction was stopped (quenched, with EDTA, formamide or SDS loading buffer, heat, or acid) before the gel or plate was loaded, so that the incubation time is the time of the stop.',
    'same_time_for_compared_lanes': 'Whether the passage says the lanes that are compared (test and control, or the enzyme and its mutant) were incubated for the same time under the same conditions.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a model or surrogate substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures, separate gels) rather than repeated loadings or reads of one reaction.',
    'conversion_detected_above_control': 'Whether the passage says a product band (or a loss of the substrate band) was seen above the paper\'s own control lane: yes when it states the product was detected above the control or background, no only when it states that no product above the control or background was detected.',
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
    occurs exactly once in ``chunk``; a number is above 0 (a share of the substrate may be 0 and may not exceed the whole substrate) and a stated value
    carries its unit where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries
    none. Returns ``answer``."""
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
        if name in SHARES:
            if item['value'] < 0:
                _refuse(name, 'share_must_not_be_below_zero')
            if item['value'] > SHARE_CEILING[item['unit']]:
                _refuse(name, 'share_must_not_exceed_the_whole_substrate')
        elif name in QUANTITIES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_endpoint_gel_band_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'endpoint_gel_band', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
