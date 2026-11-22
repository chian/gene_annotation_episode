"""The extraction of ONE oxygen-uptake-with-product coupling experiment (type 'coupling_oxygen_product') from one chunk of text, derived from the grader's input
form (``literature_coupling_oxygen_product_record.py``). DRAFT 2026-11-22 for the owner to correct; nothing was run.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand. The three
things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered 'unavailable' with a
                        reason (a field the passage does not state is never guessed and never 0). A field that is stated carries its value and the quote that
                        states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that occurs more than once must be
                        made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_oxygen_product_record``), with the operand constructors of that
                        form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model and
validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread kind); the converter judges it.

A number must be above 0 (the form's rule): a share the passage gives as zero (for example no peroxide detected) is not a number of this form; the passage's
statement that peroxide was accounted for goes to the fact ``peroxide_accounted``.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the
caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_oxygen_product_record import (
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
    'productive_fraction': 'The share of the consumed oxygen that ends in the claimed product, as the passage states it (the coupling, the coupling efficiency, the productive fraction, the percent of the oxygen used for product formation), as a fraction or a percent.',
    'productive_fraction_spread': 'The reported uncertainty of that productive fraction (the number after a plus-minus sign, or a standard error or deviation), in the unit of the productive fraction.',
    'stoichiometric_ratio': 'The moles of the claimed product formed per mole of oxygen consumed, as the passage states it (product per O2, written as a ratio such as 0.98 or 1:1 read as 1), in mol/mol or as a fraction.',
    'stoichiometric_ratio_spread': 'The reported uncertainty of that product-per-oxygen ratio, in the unit of the ratio.',
    'oxygen_per_product': 'The moles of oxygen consumed per mole of the claimed product formed, when the passage states the ratio this way round (O2 per product, for example 1.02 O2 consumed per product formed), in mol/mol.',
    'stoichiometric_coefficient': 'The paper\'s own account of the reaction: the moles of oxygen the reaction consumes per mole of the claimed product (for example 1 when the reaction equation shows one O2 for one product), as the passage states it for the reaction, not measured in this experiment, in mol/mol.',
    'oxygen_consumed': 'The net amount of oxygen consumed over the interval of the experiment (after subtracting the control), as a concentration (nM, uM, mM) or an amount (pmol, nmol, umol).',
    'product_formed': 'The net amount of the claimed product formed over the interval of the experiment (after subtracting the control), as a concentration (nM, uM, mM) or an amount (pmol, nmol, umol).',
    'oxygen_rate': 'The rate of oxygen consumption of the reaction (the slope of the oxygen trace), in a concentration per time, an amount per time or an amount per time per mass of protein.',
    'product_rate': 'The rate of formation of the claimed product, in a concentration per time, an amount per time or an amount per time per mass of protein.',
    'oxygen_window': 'The length of the interval over which the oxygen consumption was measured (the part of the oxygen trace used), in s, min or h.',
    'product_window': 'The length of the interval over which the product was formed before it was sampled and measured (the reaction time at which the product amount was taken), in s, min or h.',
    'air_saturated_oxygen': 'The oxygen concentration of air-saturated buffer that the passage gives for the calibration of the electrode or optode (for example 240 uM at 30 degrees C), in uM or mM.',
    'drift_percent': 'The drift of the oxygen signal of the electrode without reaction (the baseline drift, or the oxygen rate of a control without the enzyme), as a percent of the oxygen consumption rate of the reaction, when the passage states it as a percent.',
    'no_substrate_oxygen_percent': 'The oxygen consumption of the reaction with the enzyme but without the substrate (the uncoupled or substrate-independent oxygen uptake), as a percent of the oxygen consumption with the substrate, when the passage states it as a percent.',
    'peroxide_percent_of_oxygen': 'The hydrogen peroxide formed, as a percent of the oxygen consumed, when the passage states it as a percent.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the productive fraction and of the product-per-oxygen ratio) are.',
    'electrode_calibrated': 'Whether the passage says the oxygen electrode or optode was calibrated (with air-saturated buffer and a zero-oxygen point such as dithionite or nitrogen).',
    'drift_subtracted': 'Whether the passage says the baseline drift of the oxygen signal was measured and subtracted from the rate.',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme (a no-enzyme blank, or a buffer-only reaction) was measured for the oxygen consumption or the product.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured.',
    'no_substrate_control': 'Whether the passage says a control with the enzyme and without the substrate was measured for the oxygen consumption, and that its uptake was subtracted or set aside.',
    'peroxide_accounted': 'Whether the passage says the oxygen that went to hydrogen peroxide was accounted for: by catalase (oxygen returned on adding catalase), by a measurement of hydrogen peroxide, or by stating that none formed. Answer no only when the passage says peroxide was not measured or not accounted for.',
    'product_identified': 'Whether the passage says the product was identified chemically (against an authentic standard, by mass spectrometry, NMR or co-elution), rather than inferred from the oxygen consumption.',
    'product_calibrated': 'Whether the passage says the product was quantified with a calibration (a standard curve or standard series of the authentic compound).',
    'same_vessel': 'Whether the passage says the oxygen consumption and the product were measured in the same reaction vessel or mixture (the product sampled from the electrode chamber), as opposed to parallel reactions.',
    'same_window': 'Whether the passage says the oxygen consumption and the product were measured over the same time interval of the reaction.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate or analogue.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'coupling_detected_above_control': 'Whether the passage says that product formation coupled to oxygen consumption was detected: yes when it states that the enzyme formed the product while consuming oxygen above the paper\'s own control or detection limit, no only when it states that no product (or no oxygen-linked product) was detected above the control or detection limit.',
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
    """The record of ``literature_coupling_oxygen_product_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'coupling_oxygen_product', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
