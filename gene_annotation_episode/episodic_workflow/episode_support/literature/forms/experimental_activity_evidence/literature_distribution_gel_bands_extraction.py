"""The extraction of ONE electrophoretic product-distribution experiment (type 'distribution_gel_bands') from one chunk of text, derived from the grader's input form
(``literature_distribution_gel_bands_record.py``). DRAFT 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand. The things
this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered 'unavailable' with a reason (a
                        field the passage does not state is never guessed and never 0). A field that is stated carries its value and the quote that states it. The model gives
                        only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that occurs more than once must be made
                        longer so it points to one place). A share, a conversion and a detection limit cannot be more than the whole (100 percent).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_gel_bands_record``), with the operand constructors of that form. The
                        quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model and validated
here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the
caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_gel_bands_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
# A share of a whole cannot exceed the whole: 1 as a fraction, 100 as a percent (FIXED_BY_DEFINITION).
SHARES = ('product_fraction', 'substrate_conversion', 'minor_species_detection_limit')
WHOLE = {'fraction': 1, 'percent': 100}

MEANING = {
    'product_fraction': 'The share of ONE named product among all the products of the reaction, read from the band or peak intensities of one lane or one electropherogram (for example "the +1 product was 62% of the cleaved material", or the share of one cleavage site among all the cleavage sites), as a fraction or a percent. Only a share of products among themselves, not the share of the substrate that was converted and not a share of the starting material.',
    'product_fraction_spread': 'The reported uncertainty of that share (the number after a plus-minus sign, or a standard error or deviation), in the unit of the share.',
    'product_fraction_ratio': 'The ratio of the share of the named product to the share of one other product of the same reaction (for example a ratio of two cleavage sites, or of a longer to a shorter fragment), as a plain number. The named product is the numerator: a ratio written a:b is a divided by b. Answer unavailable with the reason ambiguous_or_conflicting_in_passage when the passage does not make clear which product is the first.',
    'product_fraction_ratio_spread': 'The reported uncertainty of that ratio, as a plain number.',
    'total_recovery': 'How much of the signal of the lane (or of the input) the counted bands account for, as the passage states it (for example "the products and the remaining substrate accounted for 95% of the lane signal"), as a fraction or a percent. Not 100 percent merely because the shares were normalized to sum to 100 percent.',
    'substrate_conversion': 'The share of the substrate that was converted (cut, cleaved, consumed) in the reaction whose lane was read, as a fraction or a percent (for example "about 20% of the substrate was cleaved").',
    'minor_species_detection_limit': 'The smallest share of the lane, as a fraction or a percent, that the passage says a band could be detected or quantified at (a detection limit or a quantification limit of the gel, the label or the imager; for example "bands down to 1% of the lane were detectable").',
    'replicate_count': 'The number of replicate reactions the passage reports for the stated share (a whole number). Lanes of one gel loaded from one reaction are not replicates.',
    'spread_kind': 'What the reported spreads are.',
    'labelling': 'How the products were made visible: end_labelled (one radioactive or fluorescent label on one end of each molecule), uniformly_labelled (label incorporated along the whole molecule), stained (a dye stain such as ethidium, SYBR or Coomassie) or fluorescent_tag (a fluorescent label read by a capillary or gel scanner that is not an end label).',
    'size_markers_run': 'Whether the passage says a size marker, a ladder, a sequencing ladder or a standard of known fragment sizes was run beside the products to assign each band or peak to a length or site.',
    'bands_resolved': 'Whether the passage says the bands or peaks of the products were resolved from their neighbours (separated well enough to be read one by one, single-nucleotide resolution for a sequencing-type gel). Answer no only when it says neighbouring bands overlapped or could not be separated.',
    'end_labelled_so_equal_response': 'Whether the passage says each product molecule carries one label (a 5\' or 3\' end label, or one fluorophore per molecule), so that the signal per molecule is the same for products of different lengths.',
    'response_corrected_for_length': 'Whether the passage says the band signals were corrected for the different response of different fragments (for example stain intensity normalized to fragment length or to mass), or for different label content.',
    'all_bands_in_denominator': 'Whether the passage says every product band or peak of the lane was counted in the total the shares are taken of (no band, smear or peak left out). Answer no only when it says some bands, peaks or unassigned signal were left out of the total.',
    'within_linear_range': 'Whether the passage says the signals were within the linear range of the stain, the label or the imager (not saturated, not at the background), or that the amounts loaded were chosen to be in that range.',
    'reaction_quenched_before_loading': 'Whether the passage says the reaction was stopped (quenched, heat-inactivated, denatured with formamide or loading dye, the enzyme removed) before the products were loaded on the gel or injected.',
    'background_subtracted': 'Whether the passage says the background of the lane or of the gel was subtracted from the band signals.',
    'no_enzyme_lane': 'Whether the passage says a lane of the substrate incubated without the enzyme (a no-enzyme control, a buffer-only incubation) was run beside the reaction.',
    'substrate_only_lane': 'Whether the passage says a lane of the substrate alone, not incubated or not treated (the starting material), was run beside the reaction to show what the substrate preparation itself contains.',
    'inactive_enzyme_lane': 'Whether the passage says a lane of the reaction with an inactive enzyme (a heat-denatured enzyme or a catalytically dead mutant) was run beside the reaction.',
    'primary_products_only': 'Whether the passage says the reaction was kept to single-hit conditions, so that each substrate molecule was cut at most once and the bands are primary products rather than products of a second cut. Answer no only when it says secondary cleavage or further processing of the products took place.',
    'independent_replicates': 'Whether the passage says the replicates were independent reactions (different days, preparations or reaction mixtures) rather than the same reaction loaded in several lanes.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a synthetic model substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'claimed_product_detected': 'Whether the passage says the named product was found among the products of the reaction: yes when it states the product was formed or detected, no only when it states that the product was not found or not detected.',
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
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit where the field has one; a share, a conversion and a
    detection limit are at most the whole; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
            _refuse(name, 'share_must_be_at_most_the_whole')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_distribution_gel_bands_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
    in its source: each quote's span is found in the chunk and recorded at its offset in the source. A value not stated is an
    'unavailable' operand with its reason, never 0; a fact not stated is 'unknown'; a choice not stated is None."""
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

    return {'version': VERSION, 'experiment_type': 'distribution_gel_bands', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
