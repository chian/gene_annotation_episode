"""The extraction of ONE radiolabelled product-distribution experiment (type 'distribution_radio_tlc') from one chunk of text, derived from the
grader's input form (``literature_distribution_radio_tlc_record.py``). DRAFT 2026-11-22, built from the shape of literature_spectro_direct_extraction.py.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by
hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_radio_tlc_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the
model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the
converter judges it.

A share of the counts of a lane cannot be more than the whole lane: a stated ``product_fraction`` above 1 (as a fraction) or above 100 (as a percent)
is refused, so the model states it again from the passage (WHOLE is FIXED_BY_DEFINITION). Nothing else is bounded from above.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_radio_tlc_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
WHOLE = {'fraction': 1.0, 'percent': 100.0}   # FIXED_BY_DEFINITION: the whole lane, in each unit of a share.

MEANING = {
    'product_fraction': 'The share of the radioactive counts (or imaged signal) of the lane that lies in ONE named product: the product the identity block gives as the partner. Give it as the passage states it, as a fraction or as a percent of the labelled products (not of the substrate left, unless the passage gives that as the share of the product).',
    'product_fraction_spread': 'The reported uncertainty of that share (the number after a plus-minus sign, or a standard error or deviation), in the unit of the share.',
    'product_fraction_ratio': 'The ratio of the counts (or signal) of the product the identity block gives as the partner to the counts of one other species, as the passage writes it with the partner on top (a ratio written "a:b" is a divided by b). A plain number without a unit.',
    'product_fraction_ratio_spread': 'The reported uncertainty of that ratio, as a plain number.',
    'lane_recovery': 'The radioactivity found in all the spots, bands or fractions of the lane together, as a share of the radioactivity applied or loaded, when the passage says it (for example "about 95% of the applied radioactivity was recovered"), as a fraction or a percent.',
    'counts_background': 'The background counts (or imaged signal) beside the lane, measured on a blank region of the plate or lane or a blank fraction, in cpm (counts per minute), dpm (disintegrations per minute) or PSL (photostimulated luminescence of a phosphor imager).',
    'smallest_species_counts': 'The counts (or imaged signal) of the smallest species that the passage quantifies, in cpm, dpm or PSL: the same unit the background is given in.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the share and the ratio) are.',
    'label': 'The radioactive isotope of the labelled substrate that was counted or imaged.',
    'readout': 'How the label was read: counting by scintillation (of scraped spots or collected fractions), a phosphor imager, a flow detector on radio-HPLC, or film.',
    'cold_standards_co_run': 'Whether the passage says authentic unlabelled standards of the species were run on the same plate or column and visualized, so each labelled spot or peak was assigned by its position.',
    'label_retained_by_all_products': 'Whether the passage says the label stays on every product that is counted (the label is in a part of the substrate that every product keeps), so no product is invisible.',
    'fractions_share_one_denominator': 'Whether the passage says the shares are shares of the total counts (or total signal) of the same lane, so they are fractions of one whole.',
    'equal_label_per_molecule': 'Whether the passage says every counted species carries the same number of labelled atoms per molecule, so that equal counts mean equal amounts.',
    'detection_efficiency_matched': 'Whether the passage says the counts or signals of the species were corrected for differences in detection (quenching, self-absorption, imager response), or were shown not to differ.',
    'spots_resolved': 'Whether the passage says the spots, bands or peaks of neighbouring species were separated from each other (resolved, not overlapping).',
    'background_subtracted': 'Whether the passage says the background counts or signal were subtracted before the shares were worked out: yes when it says they were, no only when it says they were not.',
    'within_linear_range_of_imager': 'Whether the passage says the signal was within the linear range of the detector (the imaging plate or counter was not saturated).',
    'no_enzyme_lane_run': 'Whether the passage says a lane or reaction without the enzyme, incubated like the others, was run (a no-enzyme control).',
    'zero_time_lane_run': 'Whether the passage says a lane at time zero (the labelled substrate before the reaction, or stopped at once) was run.',
    'inactive_enzyme_lane_run': 'Whether the passage says a lane with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated lanes of one reaction.',
    'native_substrate': 'Whether the passage says the labelled substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate or analogue.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'claimed_product_detected': 'Whether the passage says the product the identity block gives as the partner was found among the labelled products: yes when it states that this product was formed or detected, no only when it states that this product was not found (not detected).',
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
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit
    where the field has one; a share is not above the whole lane; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
        if name == 'product_fraction' and item['value'] > WHOLE[item['unit']]:
            _refuse(name, 'share_is_above_the_whole_lane')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_distribution_radio_tlc_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'distribution_radio_tlc', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
