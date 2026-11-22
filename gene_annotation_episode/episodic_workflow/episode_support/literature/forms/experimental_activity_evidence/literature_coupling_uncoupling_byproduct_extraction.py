"""The extraction of ONE by-product (uncoupling) assay of a coupled reaction (type 'coupling_uncoupling_byproduct') from one chunk of text, derived from the
grader's input form (``literature_coupling_uncoupling_byproduct_record.py``). DRAFT 2026-11-22, copied from the shape of literature_spectro_direct_extraction.py.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_uncoupling_byproduct_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices);
the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_uncoupling_byproduct_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'productive_fraction': 'The share of the consumed cofactor (for example NADPH) that ended in the claimed product, as the passage states it (also written the coupling, the coupling efficiency or the productive fraction), as a fraction or a percent. It is the product side of the cofactor, not the by-product side.',
    'productive_fraction_spread': 'The reported uncertainty of that productive fraction (the number after a plus-minus sign, or a standard error or deviation), in the unit of the productive fraction.',
    'uncoupled_fraction': 'The share of the consumed cofactor whose electrons ended as the by-product (hydrogen peroxide, superoxide) instead of the product, as the passage states it (also written the uncoupling, the uncoupled fraction or the peroxide shunt), as a fraction or a percent.',
    'uncoupled_fraction_spread': 'The reported uncertainty of that uncoupled fraction, in the unit of the uncoupled fraction.',
    'byproduct_per_cofactor': 'The moles of by-product (hydrogen peroxide or superoxide) formed per mole of cofactor consumed, as the passage states it as a ratio (for example 0.35 H2O2 per NADPH), in mol per mol. A share written as a percent of the cofactor belongs in the uncoupled fraction, not here.',
    'byproduct_per_cofactor_spread': 'The reported uncertainty of the by-product formed per cofactor consumed, in mol per mol.',
    'byproduct_coefficient': 'The moles of by-product that one mole of cofactor gives when the cofactor is wholly uncoupled, only when the passage says it (for example one hydrogen peroxide per NADPH, or two superoxide per NADPH), in mol per mol.',
    'blank_percent_of_signal': 'The by-product signal of the blank without the enzyme (or the reagent blank) as a percent of the signal of the complete reaction, when the passage says it (for example "the blank was below 5% of the signal").',
    'standard_recovery': 'The recovery of a known amount of by-product (for example hydrogen peroxide) added to the complete reaction mixture, as a percent or a fraction, when the passage says it.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the fractions and of the ratio) are.',
    'byproduct_species': 'Which by-product the passage measured: hydrogen_peroxide or superoxide.',
    'detection_reagent': 'How the by-product was read: amplex_red_peroxidase (Amplex Red with horseradish peroxidase), xylenol_orange (ferrous oxidation, FOX), cytochrome_c (reduction of cytochrome c, with or without superoxide dismutase), catalase_oxygen_return (oxygen released on adding catalase) or other_reagent.',
    'no_enzyme_control': 'Whether the passage says a blank without the enzyme was measured for the by-product (and the cofactor loss).',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured, or that free metal or heme alone does not make the by-product.',
    'no_substrate_control': 'Whether the passage says the by-product and the cofactor use were also measured with the enzyme and without the substrate.',
    'catalase_control': 'Whether the passage says the by-product signal was removed by catalase (hydrogen peroxide) when catalase was added.',
    'sod_control': 'Whether the passage says the by-product signal was removed by superoxide dismutase (superoxide), for example a cytochrome c reduction that superoxide dismutase inhibits.',
    'reductant_interference_excluded': 'Whether the passage says the by-product reagent was checked against other components of the reaction that give a signal by themselves (a reducing agent such as DTT, ascorbate or a thiol, the cofactor, the substrate or the test compound).',
    'byproduct_not_consumed': 'Whether the passage says the by-product was not lost in the reaction mixture during the measurement (for example that added hydrogen peroxide was not degraded by the enzyme or the buffer in the same time).',
    'standard_series': 'Whether the passage says a standard series of known amounts of the by-product (for example hydrogen peroxide) was measured in the reaction buffer to calibrate the signal.',
    'uncoupling_routes_accounted': 'Whether the passage says the by-product accounts for all the cofactor that did not go to the product (for example that the product and the hydrogen peroxide together account for all the NADPH consumed, or that no water-forming route was found).',
    'product_measured_too': 'Whether the passage says the product of the claimed reaction was also identified and measured in the same experiment as the by-product.',
    'same_mixture': 'Whether the passage says the cofactor use and the by-product were measured in the same reaction mixture.',
    'same_window': 'Whether the passage says the cofactor use and the by-product were measured over the same time window.',
    'same_preparation': 'Whether the passage says the cofactor use and the by-product were measured with the same enzyme preparation.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate or a non-native substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate, extract or membrane fraction).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'coupled_product_detected_above_control': 'Whether the passage says product formation coupled to the cofactor use was detected above the paper\'s own control or detection limit: yes when it states the product was formed (the reaction was coupled, at least in part), no only when it states that no product was formed above the control or detection limit (the cofactor use was wholly uncoupled).',
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
    """The record of ``literature_coupling_uncoupling_byproduct_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'coupling_uncoupling_byproduct', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
