"""The extraction of ONE cofactor-consumption / identified-product coupling experiment (type 'coupling_cofactor_product') from one chunk of text, derived from the
grader's input form (``literature_coupling_cofactor_product_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_cofactor_product_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

The model states only what the passage states: it never works out a coupling percent, a ratio or an amount from other numbers (the converter derives the link
by exact arithmetic where the grader finds both sides and the coefficient stated), and a fact answers 'no' only when the passage says the thing was not done.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_cofactor_product_record import (
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
    'productive_fraction': 'The share of the consumed cofactor (NADH or NADPH) that ended in the claimed product, with the reaction\'s own coefficient applied, as the passage states it: the coupling, the coupling percent or the coupling efficiency, as a fraction or as a percent.',
    'productive_fraction_spread': 'The reported uncertainty of the stated coupling (the number after a plus-minus sign, or a standard error or deviation), in the unit of the stated coupling.',
    'stoichiometric_ratio': 'The moles of product formed per mole of cofactor consumed, as the passage states it (for example "0.8 mol of product per mol of NADH"), with no coefficient applied. It is a ratio, not a percent.',
    'stoichiometric_ratio_spread': 'The reported uncertainty of that product per cofactor, in mol per mol.',
    'cofactor_per_product': 'The moles of cofactor consumed per mole of product formed, as the passage states it (for example "1.3 NADPH were consumed per product"), the reverse way of stating the ratio. It is a measured number, not the reaction\'s own coefficient.',
    'stoichiometric_coefficient': 'The moles of cofactor the claimed reaction takes per mole of product according to the passage\'s own account of the reaction (for example 1 for a monooxygenase that uses one NADPH, 2 for a reaction that takes two NADPH). It is the reaction\'s stoichiometry, not a measured ratio.',
    'cofactor_consumed': 'The amount or concentration of cofactor (NADH or NADPH) consumed over the stated period of the reaction, as the passage reports it, in a concentration unit or an amount unit.',
    'product_formed': 'The amount or concentration of the claimed product formed over the stated period of the reaction (identified and counted by chromatography or mass spectrometry), as the passage reports it, in a concentration unit or an amount unit.',
    'cofactor_rate': 'The rate of cofactor consumption in the reaction (for example the NADPH oxidation rate from the absorbance loss at 340 nm), as the passage reports it, in one of the rate units.',
    'product_rate': 'The rate of formation of the claimed product in the reaction, as the passage reports it, in one of the rate units.',
    'no_substrate_cofactor_rate': 'The rate of cofactor consumption of the enzyme with NO substrate present (the uncoupled oxidation of the cofactor by the enzyme alone), as the passage reports it, in one of the rate units.',
    'extinction_coefficient': 'The extinction (molar absorption) coefficient the passage uses to turn the absorbance loss of the cofactor into an amount, in M^-1 cm^-1 or mM^-1 cm^-1.',
    'wavelength': 'The wavelength at which the absorbance of the cofactor was read, in nm.',
    'absorbance_max': 'The highest absorbance reached in the measurement, or the absorbance range the passage says was kept below (for example "initial absorbance of 1.0"), in absorbance units (AU).',
    'calibration_recovery': 'The recovery of a known amount of the product through the product measurement (a spiked or standard sample), as the percent the passage states.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the stated coupling) are.',
    'product_identified': 'Whether the passage says the product was identified chemically against an authentic standard or by a second method (co-elution with a standard, mass spectrometry, NMR), rather than assumed from the substrate or the cofactor loss.',
    'product_calibrated': 'Whether the passage says the amount of product was determined against a calibration with the authentic product (a standard series or curve of known amounts).',
    'same_mixture': 'Whether the passage says the cofactor consumption and the product were measured in the same reaction mixture (the same vessel, or samples taken from one reaction).',
    'same_window': 'Whether the passage says the cofactor consumption and the product refer to the same period of the reaction (the same time points).',
    'same_preparation': 'Whether the passage says both sides were measured with the same enzyme preparation.',
    'no_substrate_control': 'Whether the passage says the cofactor consumption of the enzyme was measured with no substrate present (the uncoupled oxidation of the cofactor).',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme (cofactor and substrate alone) was measured for the cofactor loss or the product.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured.',
    'background_subtracted': 'Whether the passage says the background cofactor oxidation (without enzyme, or without substrate) was subtracted from the cofactor consumption.',
    'byproduct_accounted': 'Whether the passage says the cofactor that did not end in the product was accounted for by a by-product it measured (for example hydrogen peroxide, superoxide or water), or says the uncoupled cofactor use was measured.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'coupled_product_detected': 'Whether the passage says the claimed product was formed above the paper\'s own control or detection limit in the reaction that consumed the cofactor: yes when it states the product was detected, no only when it states that no product above the control or detection limit was found.',
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
    """The record of ``literature_coupling_cofactor_product_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'coupling_cofactor_product', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
