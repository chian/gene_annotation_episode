"""The extraction of ONE gas-evolution end-point enzyme experiment (type 'endpoint_gas_evolution') from one chunk of text, derived from the grader's input
form (``literature_endpoint_gas_evolution_record.py``). DRAFT of 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_gas_evolution_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the
converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_gas_evolution_record import (
    FACTS, GAS_SPECIES, PREPARATION_KEYS, QUANTITIES, READOUT_METHODS, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
GAS_SPECIES_FIELD = 'gas_species'
READOUT_METHOD = 'readout_method'
# The plain choice fields and their fixed vocabularies (recorded for the reviewer; no criterion rests on a choice).
CHOICES = {SPREAD_KIND: SPREAD_KINDS, GAS_SPECIES_FIELD: GAS_SPECIES, READOUT_METHOD: READOUT_METHODS}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'conversion_percent': 'The percent of the theoretical gas yield (the share of the substrate that was turned into the gas) at the end point, as the passage states it for the test vessel, in percent. A yield stated as a percent of the theoretical, of the expected or of the stoichiometric amount counts; a percent of something else (of the headspace, of the total gas, of the control) does not.',
    'conversion_spread': 'The reported uncertainty of that percent of the theoretical yield (the number after a plus-minus sign, or a standard error or deviation), in percent.',
    'net_conversion_percent': 'The same percent of the theoretical gas yield MINUS the paper\'s own control (the no-enzyme or inactive-enzyme vessel), only when the passage states the control-corrected value itself, in percent. Never subtract two numbers yourself.',
    'net_conversion_spread': 'The reported uncertainty of the control-corrected percent of the theoretical yield, in percent.',
    'control_conversion_percent': 'The percent of the theoretical gas yield in the paper\'s own control vessel (without the enzyme or with an inactive enzyme), as the passage states it, in percent.',
    'gas_amount': 'The total amount of the gas formed in the closed vessel at the end point, as the passage states it for the test vessel (an amount of substance of the gas, not a rate, not a concentration in the headspace, not a percent, not a pressure), in nmol, umol or mmol.',
    'gas_amount_spread': 'The reported uncertainty of the gas amount of the test vessel, in the unit of the amount.',
    'control_gas_amount': 'The amount of the gas found in the paper\'s own control vessel (without the enzyme or with an inactive enzyme) at the same time, in nmol, umol or mmol.',
    'theoretical_yield': 'The amount of the gas the passage says would be formed if all the substrate were converted (the theoretical, expected or stoichiometric yield), in nmol, umol or mmol.',
    'headspace_volume': 'The volume of the gas phase (the headspace) of the closed vessel, in uL or mL.',
    'liquid_volume': 'The volume of the liquid reaction mixture in the closed vessel, in uL or mL.',
    'endpoint_time': 'The time of the reaction at which the headspace gas was read (the end point), in s, min or h.',
    'calibration_low': 'The smallest known gas amount of the calibration of the gas reading (the lowest standard), in nmol, umol or mmol.',
    'calibration_high': 'The largest known gas amount of the calibration of the gas reading (the highest standard), in nmol, umol or mmol.',
    'detection_limit': 'The detection limit or the quantification limit of the gas reading, as an amount of the gas, in nmol, umol or mmol.',
    'replicate_count': 'The number of replicate vessels or experiments the passage reports (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the percent and the gas amount) are.',
    GAS_SPECIES_FIELD: 'Which gas was measured: hydrogen (h2), carbon dioxide (co2), methane (ch4), nitrous oxide (n2o), oxygen (o2) or another gas (other).',
    READOUT_METHOD: 'How the gas was read: gas chromatography with a thermal-conductivity detector (gc_tcd), a flame-ionisation detector (gc_fid), an electron-capture detector (gc_ecd) or a mass spectrometer (gc_ms), manometry or a pressure transducer (manometry), or another way (other).',
    'no_enzyme_control_done': 'Whether the passage says a control vessel without the enzyme (substrate and everything else, no enzyme) was run and its gas read.',
    'inactive_enzyme_control_done': 'Whether the passage says a control vessel with an inactive enzyme (heat-denatured, boiled, a catalytically dead mutant or an inhibited enzyme) was run and its gas read.',
    'zero_time_sample_done': 'Whether the passage says the gas of the vessel was read at the start of the reaction (a zero-time sample), to show how much of the gas was there before the reaction.',
    'leak_control_done': 'Whether the passage says the tightness of the closed vessel was checked: a sealed vessel (a blank or a vessel with a known amount of the gas) was held for the same time and its gas did not change.',
    'enzyme_dependence_shown': 'Whether the passage says the gas formed depends on the enzyme: it rises with the amount of enzyme, or it is lost with an inactive enzyme, a mutant or an inhibitor.',
    'gas_identified_by_detector': 'Whether the passage says the gas was identified by the detector, as the retention time of a gas standard on the column, a mass spectrum, or a detector that answers to that gas only (not just a rise in pressure).',
    'calibration_gas_in_same_vessel': 'Whether the passage says the gas reading was calibrated with known amounts of the gas put into the same kind of vessel (the same vial, volume and stopper) and read the same way.',
    'dissolved_gas_accounted_for': 'Whether the passage says the part of the gas that stays dissolved in the liquid (or, for carbon dioxide, as bicarbonate) was counted: by a solubility calculation, by shaking until it was in equilibrium, or by releasing it with acid before the reading.',
    'same_time_for_compared_arms': 'Whether the passage says the compared vessels (test and control, or the compared enzymes) were read at the same time.',
    'initial_substrate_determined': 'Whether the passage says the amount of the substrate at the start (from which the theoretical yield is taken) was measured, and not only taken from the recipe.',
    'independent_replicates': 'Whether the passage says the replicates were independent vessels or experiments (different days, preparations or reaction mixtures) rather than repeated injections from one vessel.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to an artificial one.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate, an extract or whole cells).',
    'gas_detected_above_control': 'Whether the passage says the gas was formed above the paper\'s own control: yes when it states the gas was detected above the control or the detection limit, no only when it states that no gas above the control or the detection limit was detected.',
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
    """The record of ``literature_endpoint_gas_evolution_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'endpoint_gas_evolution', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
