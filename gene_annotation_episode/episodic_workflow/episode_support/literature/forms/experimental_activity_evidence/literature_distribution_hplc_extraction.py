"""The extraction of ONE HPLC product-distribution experiment (type 'distribution_hplc') from one chunk of text, derived from the grader's input form
(``literature_distribution_hplc_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by
hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_hplc_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices);
the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None). Which product the share is about (the record's partner) is an identity field given beside this answer, not a field of it.
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_hplc_record import (
    BOUNDED_SHARES, CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
WHOLE = {'fraction': 1.0, 'percent': 100.0}      # FIXED_BY_DEFINITION: the whole a share is a share of, in each of its units

MEANING = {
    'product_fraction': 'The share of ONE named product among all the products the reaction formed, as the passage states it, as a fraction or a percent (for example "the product made up 62% of the peak area"). It is the share of the product the passage is about, not of the substrate and not of the starting material; a share written for another product is not this field.',
    'product_fraction_spread': 'The reported uncertainty of that product share (the number after a plus-minus sign, or a standard deviation or error), in the unit of the share.',
    'product_fraction_ratio': 'The ratio of the product the passage is about to ONE other product or isomer, as the passage states it, as one number (a ratio written "a:b" is a divided by b, with the product the passage is about first; the ratio of 3 to 1 is 3).',
    'product_fraction_ratio_spread': 'The reported uncertainty of that product ratio, as a plain number.',
    'equilibrium_fraction': 'The share of ONE named species in the mixture at equilibrium (the reaction run until the composition no longer changed, or reached from both sides), as a fraction or a percent. A share of the products of a reaction that was stopped before equilibrium is not this field.',
    'equilibrium_fraction_spread': 'The reported uncertainty of that equilibrium share, in the unit of the share.',
    'equilibrium_ratio': 'The ratio at equilibrium of the species the passage is about to the species on the other side of the reaction, as one number (an equilibrium constant with a concentration unit is not this field).',
    'equilibrium_ratio_spread': 'The reported uncertainty of that equilibrium ratio, as a plain number.',
    'total_recovery': 'The total recovery (closure, mass balance) the passage reports: the sum of all the species that were quantified over the amount of substrate that was applied or started with, as a fraction or a percent (for example "recovery was 97%"). A sum that was only normalized to 100% is not a recovery.',
    'peak_resolution': 'The chromatographic resolution Rs the passage reports between the peak of the product the passage is about and its nearest neighbouring peak, as a plain number (for example "resolution of 1.8").',
    'detection_limit': 'The limit of detection the passage reports for a species in the chromatographic analysis, as a fraction or a percent of the total (for example "species below 0.5% would not be detected"). A limit of quantification, or a limit given as a concentration or an amount, is not this field.',
    'replicate_count': 'The number of independent replicate reactions the passage reports (a whole number). Repeated injections of one sample are not replicate reactions.',
    'spread_kind': 'What the reported spreads (the uncertainties of the shares and ratios) are: standard_deviation, standard_error, confidence_interval or range.',
    'fraction_basis': 'What the stated share is a share of: mole (a molar or amount share, from calibration), mass (a mass share) or peak_area (the raw share of the summed peak areas).',
    'detector': 'The kind of detector that read the chromatography: uv (single-wavelength ultraviolet or visible absorbance), diode_array, fluorescence, refractive_index, elsd (evaporative light scattering) or cad (charged aerosol).',
    'authentic_standard_for_each_species': 'Whether the passage says each species whose share is given was identified by comparison with an authentic standard (matching retention time, or spiking the sample with the standard).',
    'identity_confirmed_by_mass_or_nmr': 'Whether the passage says the identity of the product peak was confirmed by another method, such as mass spectrometry or NMR of the collected peak.',
    'response_factors_calibrated': 'Whether the passage says the detector response of each species was corrected (relative response factors, or the areas converted to amounts by calibration) so that the share is an amount share: yes when it says it was corrected, no only when it says the shares are uncorrected peak area percentages or equal response was assumed.',
    'calibration_curves_for_each_species': 'Whether the passage says a calibration (standard) curve was made for each species whose share is given.',
    'fractions_share_one_denominator': 'Whether the passage says the shares given were all taken over the same total (the same sum of species) in one chromatogram or one reaction.',
    'all_products_identified': 'Whether the passage says every peak (or all the material) in the chromatogram was assigned to a species or accounted for, with none left out of the total.',
    'peaks_resolved': 'Whether the passage says the product peaks were separated from their neighbours (baseline resolved).',
    'enzyme_removed_or_quenched_before_injection': 'Whether the passage says the reaction was stopped (quenched, acidified, heated, filtered or the enzyme removed) before the sample was injected.',
    'signals_within_calibration_range': 'Whether the passage says the measured peak areas lay within the range of the calibration curve.',
    'no_enzyme_control_done': 'Whether the passage says a control reaction without the enzyme was run and analysed in the same way.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run and analysed in the same way.',
    'products_stable_under_assay_and_workup': 'Whether the passage says the products were shown not to change, interconvert or degrade under the assay conditions and during sample work-up (for example the purified product was incubated and recovered unchanged).',
    'distribution_stable_over_time': 'Whether the passage says the composition (the shares) was the same at two or more times.',
    'approached_from_both_sides': 'Whether the passage says the same equilibrium composition was reached starting from the substrate and starting from the product.',
    'independent_replicates': 'Whether the passage says the replicates were independent reactions (different days, preparations or reaction mixtures) rather than repeated injections of one sample.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate substrate.',
    'claimed_product_detected': 'Whether the passage says the product it is about was found among the products: yes when it states the product was formed or detected, no only when it states that this product was not detected or not formed.',
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
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit where the field has one; a share of a whole is at most
    the whole (1 as a fraction, 100 as a percent); a stated field carries a support (direct, implied or about_something_else) and an unavailable one
    carries none. Returns ``answer``."""
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
        if name in QUANTITIES:
            if item['value'] <= 0:
                _refuse(name, 'number_must_be_above_zero')
            if name in BOUNDED_SHARES and item['value'] > WHOLE[item['unit']]:
                _refuse(name, 'share_is_above_the_whole')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_distribution_hplc_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'distribution_hplc', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
