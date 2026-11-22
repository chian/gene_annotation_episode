"""The extraction of ONE gas-chromatography product distribution (type 'distribution_gc': the products of an enzyme reaction, volatile or
derivatized, separated on a gas chromatograph and read by a flame-ionization detector or a mass spectrometer; the area of each product peak over the
area of all product peaks is that product's share) from one chunk of text, derived from the grader's input form
(``literature_distribution_gc_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_gc_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_gc_record import (
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
    'product_fraction': 'The share of ONE named product among all the products the reaction formed, as the passage reports it (for example the peak area percent of that product over all product peaks, or its relative abundance in the product spectrum), as a fraction or a percent. The product it is about is the partner of the experiment. It is not the share of the substrate converted and not the share of one peak among all peaks including the solvent.',
    'product_fraction_spread': 'The reported uncertainty of that product share (the number after a plus-minus sign, or a standard error or deviation), in the unit of the product share.',
    'product_fraction_ratio': 'The ratio of the share of that product (the partner) to the share of ONE other named product of the same reaction, as a number, when the passage gives it as a ratio (for example 3:1 is 3). The product the partner is on top: if the passage writes the other product first, the ratio is ambiguous and unavailable.',
    'product_fraction_ratio_spread': 'The reported uncertainty of that ratio, as a number.',
    'identified_area_fraction': 'The part of the total peak area (all peaks of the chromatogram) that was assigned to identified compounds (for example "identified compounds made up 96.4% of the total area"), as a fraction or a percent.',
    'minimum_integrated_share': 'The smallest share of the total peak area that the passage says it integrated, reported or could detect (a detection limit or the smallest peak area percent counted), as a fraction or a percent. A limit given in an amount (for example ng) and not as a share is in a unit the field does not offer.',
    'extraction_recovery': 'The share of the product, or of a standard added to the reaction, that was found again after the extraction or sampling step (the recovery), as a fraction or a percent.',
    'retention_index_observed': 'The retention index (Kovats index or linear retention index, a number such as 1032) the passage measured for the product on its column.',
    'retention_index_reference': 'The retention index of the same compound that the passage compares its measured one with (the value of a library, a database or the literature, or of an authentic standard), as a number.',
    'replicate_count': 'The number of replicate reactions the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the product share and of the ratio) are.',
    'identified_by_standard': 'Whether the passage says the product (the partner) was identified by comparing it with an authentic standard (the retention time, the retention index or the mass spectrum of a pure compound run on the same column).',
    'identified_by_library_match': 'Whether the passage says the product was identified by comparing its mass spectrum with a library (for example NIST or Wiley) or its retention index with published values.',
    'quantified_by_flame_ionization': 'Whether the passage says the shares were taken from the areas of a flame-ionization detector (FID).',
    'quantified_by_mass_spectrometry': 'Whether the passage says the shares were taken from the areas of a mass spectrometer (total ion current or extracted ion).',
    'response_factors_calibrated': 'Whether the passage says the peak areas were corrected for the response of each compound (response factors, calibration curves or an internal standard for each compound): yes when it says so, no only when it says the shares are raw peak area percentages that were not corrected.',
    'all_peaks_in_denominator': 'Whether the passage says the share is taken over all the product peaks, with no unassigned or unidentified product peak left out of the total: yes when it says so, no only when it says peaks were left out of the total.',
    'injector_stability_checked': 'Whether the passage says it was checked that the product is not changed in the hot injector or on the column (for example a standard of the product was injected, or a cooler injector or on-column injection gave the same result).',
    'products_stable_under_assay_and_workup': 'Whether the passage says the products were shown to stay unchanged during the enzyme reaction, the quenching and the extraction (no rearrangement, degradation or loss afterwards).',
    'no_enzyme_control_done': 'Whether the passage says a control extract without the enzyme (a no-enzyme blank, substrate and buffer only) was run and analysed in the same way.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (heat-treated or boiled enzyme, a catalytically dead mutant, or an extract of cells with an empty vector) was run and analysed in the same way.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate or analogue substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent reactions (different days, preparations or reaction mixtures) rather than repeated injections of one extract.',
    'claimed_product_detected': 'Whether the passage says the product (the partner) was found among the products of the reaction: yes when it states the product was formed or detected, no only when it states that the product was not detected or not formed.',
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
    """The record of ``literature_distribution_gc_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'distribution_gc', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
