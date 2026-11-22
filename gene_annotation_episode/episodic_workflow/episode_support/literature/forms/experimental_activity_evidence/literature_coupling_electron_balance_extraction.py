"""The extraction of ONE electron balance of a reaction (type 'coupling_electron_balance') from one chunk of text, derived from the grader's input
form (``literature_coupling_electron_balance_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_electron_balance_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices);
the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_electron_balance_record import (
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
    'productive_fraction': 'The share of the delivered electrons that was recovered in the product, as the passage states it as one number (electron recovery, electron balance, faradaic efficiency or coulombic efficiency of the product), as a fraction or in percent.',
    'productive_fraction_spread': 'The reported uncertainty of that share (the number after a plus-minus sign, or a standard error or deviation), in the unit of that share.',
    'electrons_delivered': 'The amount of electrons delivered to (or taken from) the reaction, as the passage states it: moles of electron equivalents (for example the reductant or the reduced donor consumed, in umol or mmol) or the charge passed (in C or mC). It is the amount for the same interval and vessel as the product.',
    'product_formed': 'The amount of the claimed product formed in that same reaction (for example the hydrogen or the reduced compound, in umol, nmol, pmol, mmol or mol), as an amount and not as a rate.',
    'electrons_per_product': 'The number of electrons the formation of one molecule of the product takes, as the passage states it for the reaction (for example 2 electrons per H2), in mol of electrons per mol of product.',
    'background_electrons': 'The electrons delivered (or the charge passed) in the control without the enzyme or catalyst, as the passage states it, in the unit of the electrons delivered.',
    'standard_recovery': 'The recovery of a known standard of the product (for example a known amount of hydrogen gas injected into the vessel and measured the same way) as the passage states it, as a fraction or in percent.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spread of the productive share is.',
    'delivery_kind': 'How the delivered electrons were counted: reductant_titration (a measured amount of a reductant or oxidant, such as dithionite or titanium citrate, added), electrolysis_charge (the charge passed at an electrode, bulk electrolysis or coulometry) or donor_oxidation (a reduced donor, such as NADH or a reduced viologen, whose consumption was followed).',
    'product_kind': 'What the electrons were recovered in: hydrogen (H2 gas), reduced_compound (a reduced organic or inorganic product) or oxidized_compound (an oxidised product).',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme or catalyst (a blank, a buffer-only or cell-free reaction) was run.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run.',
    'background_charge_subtracted': 'Whether the passage says the background (the charge or the donor oxidation of the control without the enzyme) was subtracted from, or accounted for in, the electrons delivered.',
    'delivery_calibrated': 'Whether the passage says the counting of the electrons delivered was calibrated or standardised (for example a standardised titrant, a calibrated coulometer or potentiostat, or the extinction coefficient and concentration of the donor determined).',
    'product_calibrated': 'Whether the passage says the measurement of the product was calibrated with a standard (for example a gas standard series for hydrogen, or a standard curve of the product).',
    'headspace_accounted': 'Whether the passage says the product in the gas phase and the dissolved product were both accounted for, or that the loss on sampling the headspace was corrected for.',
    'anaerobic_control': 'Whether the passage says the reaction was kept free of oxygen or of another electron acceptor, so the electrons could not go to it.',
    'mediator_bypass_excluded': 'Whether the passage says the electrons did not reach the product by a path that bypasses the enzyme (for example by the mediator dye alone, or by the electrode), for example by a control with the mediator and without the enzyme that gave no product.',
    'product_identified': 'Whether the passage says the product was chemically identified against an authentic standard (for example by retention time or by mass spectrometry), as opposed to being inferred from the loss of the donor.',
    'same_window': 'Whether the passage says the electrons delivered and the product were measured over the same time interval.',
    'same_reaction_mixture': 'Whether the passage says the electrons delivered and the product were measured in the same reaction vessel and from the same enzyme preparation.',
    'native_electron_carrier': 'Whether the passage says the electron donor or carrier is the natural one of the enzyme (for example NADH, ferredoxin or its physiological partner), as opposed to an artificial dye, a chemical reductant or an electrode.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'product_detected_from_electrons': 'Whether the passage says the product was formed from the delivered electrons: yes when it states the product was detected above the paper\'s own control or detection limit, no only when it states that no product (or none above the control or detection limit) was detected.',
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
    """The record of ``literature_coupling_electron_balance_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'coupling_electron_balance', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
