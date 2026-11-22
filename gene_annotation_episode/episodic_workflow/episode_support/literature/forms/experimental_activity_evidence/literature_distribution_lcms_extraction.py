"""The extraction of ONE LC-MS or LC-MS/MS product-profile experiment (type 'distribution_lcms') from one chunk of text, derived from the grader's input form
(``literature_distribution_lcms_record.py``). DRAFT 2026-11-22, owner to confirm.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand. The things
this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered 'unavailable' with a
                        reason (a field the passage does not state is never guessed and never 0). A field that is stated carries its value and the quote that states
                        it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that occurs more than once must be
                        made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_lcms_record``), with the operand constructors of that form. The
                        quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Differences from the other types that come from the form: a share of a product is a number from 0 to 1 (unit fraction) or from 0 to 100 (unit percent), and 0 is
allowed for it (the passage states that the share is zero); every other number is above 0. The record has three plain choices (spread kind, what the share is a
share of, ionisation mode) and sixteen yes/no facts.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model and
validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the
caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_lcms_record import (
    EXPERIMENT_TYPE, FACTS, FRACTION_BASES, IONIZATION_MODES, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
FRACTION_BASIS = 'fraction_basis'
IONIZATION_MODE = 'ionization_mode'
CHOICES = {SPREAD_KIND: SPREAD_KINDS, FRACTION_BASIS: FRACTION_BASES, IONIZATION_MODE: IONIZATION_MODES}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
SHARE = 'product_fraction'
SHARE_LIMIT = {'fraction': 1, 'percent': 100}   # the largest share in each unit of the share; the smallest is 0 (stated as none of the products)

MEANING = {
    'product_fraction': 'The share of ONE product among the products of the reaction, as the passage gives it, for the product that is the partner of the target enzyme in this experiment (the product the experiment is about): the percent or the fraction of the summed ion signal or of the summed amount that this product makes (for example 62 percent of the product signal gives 62 with the unit percent, and 0.62 gives 0.62 with the unit fraction). It is the share among the PRODUCTS, not a conversion of the substrate and not a yield. Give 0 only when the passage itself states that the share of this product is zero. A share written for a product that is not the partner is not this field.',
    'product_fraction_spread': 'The reported uncertainty of that product share (the number after a plus-minus sign, or a standard error or deviation), in the unit of the product share.',
    'product_fraction_ratio': 'The ratio of the signal or amount of the product that is the partner of the target to that of ANOTHER product of the same reaction (for example a regio-isomer or a chain-length ratio), as one number above 0 with the partner in the numerator. A ratio written a:b is a divided by b (3:1 gives 3 and 1:4 gives 0.25); a ratio that does not give an exact number is unavailable. It is the same measurement as a share seen another way: give it only when the passage writes a ratio.',
    'product_fraction_ratio_spread': 'The reported uncertainty of that product ratio, as a plain number in the unit of the ratio.',
    'total_recovery': 'The total recovery or closure of the reaction that the passage gives: the sum of the species measured over the amount at the start (the mass balance), as a fraction or a percent. A share that is normalised to 100 percent is not a recovery.',
    'product_concentration': 'The concentration of the product that is the partner of the target in the measured sample, as the passage gives it, in nM, uM or mM (the product formed, not the substrate and not the standard).',
    'limit_of_quantification': 'The lower limit of quantification (LLOQ, LOQ) of the method for the product that is the partner of the target, as a concentration in nM, uM or mM, when the passage gives it. A limit of detection (LOD) is not this field.',
    'replicate_count': 'The number of independent replicate reactions the passage reports for this result (separate reaction mixtures or enzyme preparations, biological replicates), as a whole number. Repeated injections of one sample are not this field.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the share and the ratio) are: a standard error, a standard deviation or a confidence interval.',
    FRACTION_BASIS: 'What the product share is a share of, as the passage says it: mole (a molar or amount share, from calibration), ion_signal (a share of the summed ion signal, peak area of the extracted ion or of the monitored transition) or mass. A passage that does not say it does not state it.',
    IONIZATION_MODE: 'The ionisation polarity the passage names for the measurement: positive, negative or both (a method that uses both). A passage that does not name it does not state it.',
    'authentic_standard_for_each_species': 'Whether the passage says that the species whose shares are given were identified or quantified against authentic standards (pure reference compounds matched by retention time and by mass or fragment ions) (yes), or says that they were identified without standards (from the mass alone, from a library or by prediction) (no).',
    'calibrated_per_species': 'Whether the passage says that each species whose share is given was calibrated on its own (a calibration curve, a standard curve or a response factor for each species), so that the shares are amounts and not raw ion signals (yes), or says that the shares are raw ion signals or peak areas without per-species calibration, or that the same response was assumed for the species (no).',
    'isotope_labelled_internal_standard': 'Whether the passage says that a stable-isotope-labelled internal standard (13C, 15N or 2H labelled) of the product or products was added to the samples (yes), or says that no internal standard, or only an internal standard that is not isotope-labelled, was used (no).',
    'matrix_matched_calibration': 'Whether the passage says that the calibration standards were prepared in the same matrix as the samples (the reaction buffer, the stopped reaction mixture or a lysate without the product) (yes), or says that they were prepared in neat solvent (no).',
    'ion_suppression_checked': 'Whether the passage says that ion suppression or enhancement (the matrix effect) was evaluated, for example by post-column infusion, by comparing a spiked matrix sample with a neat solution, or by a matrix factor (yes), or says that it was not evaluated (no).',
    'signals_within_calibration_range': 'Whether the passage says that the measured signals or amounts fell within the range of the calibration curve, between the lowest and the highest calibrator (yes), or says that some were below the lowest or above the highest calibrator (no).',
    'fractions_share_one_denominator': 'Whether the passage says that the shares (or the ratio) it gives are all taken over the same stated total, for example the sum of the species measured in the same injection (yes), or says that they are normalised to different totals or to different injections (no).',
    'all_products_identified': 'Whether the passage says that every product peak or ion of the reaction was identified, so that no unassigned peak or mass was left out of the total (yes), or says that unidentified peaks or ions were left out (no).',
    'no_enzyme_control_done': 'Whether the passage says that a reaction without the enzyme (a no-enzyme blank or a buffer-only reaction) was run and analysed by the same LC-MS method (yes), or says that it was not (no).',
    'inactive_enzyme_control_done': 'Whether the passage says that a reaction with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run and analysed by the same LC-MS method (yes), or says that it was not (no).',
    'enzyme_removed_or_quenched_before_analysis': 'Whether the passage says that the reaction was stopped before the analysis (quenched with acid, organic solvent or heat, or the enzyme removed by filtration or precipitation) (yes), or says that it was not stopped (no).',
    'products_stable_under_assay_and_workup': 'Whether the passage says that the products were shown or stated to be stable (no interconversion, degradation or loss) during the reaction, the work-up and the wait in the autosampler (yes), or says that they were not stable (no).',
    'independent_replicates': 'Whether the passage says the replicates were independent reactions (different days, preparations or reaction mixtures) rather than repeated injections of one sample (yes), or says that they were not (no).',
    'purified_enzyme': 'Whether the passage says that the enzyme was purified (as opposed to a cell lysate or extract) (yes), or says that it was a lysate or extract (no).',
    'native_substrate': 'Whether the passage says that the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate substrate (yes), or says that it is a surrogate (no).',
    'claimed_product_detected': 'Whether the passage says that the product the experiment is about (the partner of the target) was detected among the products of the reaction (yes: it was formed, found or observed) or says that it was not detected (no: it was not found, or was below the detection limit). It is a statement of the passage about the presence of the product, not a share.',
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
    occurs exactly once in ``chunk``; a product share is from 0 to the largest share of its unit and every other number is above 0, and a stated value carries its unit
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
        if name == SHARE and not 0 <= item['value'] <= SHARE_LIMIT[item['unit']]:
            _refuse(name, 'share_must_be_from_0_to_its_largest', SHARE_LIMIT[item['unit']])
        if name in QUANTITIES and name != SHARE and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_distribution_lcms_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
