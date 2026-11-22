"""The extraction of ONE planar lipid bilayer recording (type 'transport_planar_bilayer') from one chunk of text, derived from the
grader's input form (``literature_transport_planar_bilayer_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_planar_bilayer_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

Numbers: every number is above 0 except the two voltages (``SIGNED_QUANTITIES``: the holding voltage and the reversal potential), which keep
the sign the passage gives and may be zero or negative.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_planar_bilayer_record import (
    FACTS, PREPARATION_KEYS, QUANTITIES, SIGNED_QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('event_count', 'bilayer_count')

MEANING = {
    'unitary_conductance': 'The single-channel (unitary) conductance of the channel as the passage reports it, in pS or nS. It is the conductance already divided by the driving force (current over the holding voltage minus the reversal potential, or the slope of the single-channel current-voltage curve), not a current.',
    'unitary_conductance_spread': 'The reported uncertainty of the unitary conductance (the number after a plus-minus sign, or a standard error or deviation), in the unit of the unitary conductance.',
    'unitary_current': 'The size of the single-channel (unitary) current step as the passage reports it, in pA or nA, written without a sign (a current stated as -1.8 pA is 1.8 pA). Give it only when the passage states the voltage-dependent current of one channel, not the total current of a bilayer.',
    'baseline_noise': 'The root-mean-square (rms) noise of the current recording as the passage reports it, in pA or nA. Peak-to-peak noise is not rms noise: answer unavailable for a peak-to-peak value.',
    'holding_voltage': 'The voltage at which the unitary current was measured (the holding voltage or the applied potential), in mV, with the sign the passage gives it (for example -200 mV).',
    'reversal_potential': 'The reversal potential of the channel as the passage reports it (the voltage at which the current is zero), in mV, with the sign the passage gives it. A reversal potential stated as 0 mV is a stated value.',
    'permeability_ratio': 'The permeability ratio of two ions as the passage reports it, as a number above 1: the permeability of the more permeant ion over that of the less permeant ion (for example P_F/P_Cl stated as 100). If the passage gives it only as a bound ("more than 100"), give the bound. If the passage gives it the other way round (less permeant over more permeant), answer unavailable with the reason ambiguous_or_conflicting_in_passage.',
    'charge_rate': 'The charge carried by one channel per second as the passage reports it (the current divided by the elementary charge), in charges per second. A rate stated in ions per second is not this field.',
    'event_count': 'The number of single-channel events (openings, steps or insertion events) behind the stated unitary current or conductance, as a whole number.',
    'bilayer_count': 'The number of independent bilayers (separate bilayers, not events or sweeps of one bilayer) the passage reports, as a whole number.',
    SPREAD_KIND: 'What the reported spread of the unitary conductance is.',
    'protein_free_bilayer_control_done': 'Whether the passage says a bilayer without the protein (or with protein-free liposomes, or with the buffer and detergent only), recorded the same way, showed no channel events or current: yes when it says so; no only when it says the control was not done or that it did show channel-like events.',
    'bilayer_integrity_checked': 'Whether the passage says the bilayer was checked to be intact and stable before or during the recording (a high seal resistance or capacitance check, a quiet baseline without leak or spontaneous bursts).',
    'solutions_stated': 'Whether the passage states the salt or ion concentrations (or compositions) of the solutions on both sides of the bilayer.',
    'driving_force_corrected': 'Whether the passage says the conductance was worked out with the driving force removed, that is from the slope of the single-channel current-voltage curve or as the current over the holding voltage minus the reversal potential; no only when it says the conductance was taken as the current over the holding voltage alone.',
    'bi_ionic_gradient_done': 'Whether the passage says the reversal potential (or the current) was measured with two different ions, or two different salt concentrations, in the two chambers (a bi-ionic or salt-gradient condition).',
    'named_ion_preferred': 'Whether the passage says the channel prefers (is more permeable to) the ion or substrate that the passage is about, over the other ion it compared: yes when it says so; no only when it says the channel prefers the other ion.',
    'blocker_control_done': 'Whether the passage says a known blocker or inhibitor of the channel reduced or abolished the current: yes when it says so; no only when it says the control was not done or the blocker did not reduce the current.',
    'purified_protein': 'Whether the passage says the protein was purified before it was put into the bilayer (as opposed to a membrane preparation, an extract or a vesicle fraction).',
    'independent_bilayers': 'Whether the passage says the counted bilayers were independent recordings (separate bilayers, and where it says so separate protein preparations), not events or traces of one bilayer.',
    'transport_detected_above_control': 'Whether the passage says the channel showed current or channel events above the paper\'s own control (a bilayer without the protein): yes when it states current or events were detected only with the protein, above the control or the noise; no only when it states that no current or events above the control or noise were detected.',
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
    occurs exactly once in ``chunk``; a number is above 0 (except the two voltages) and a stated value carries its unit
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
        if name in QUANTITIES and name not in SIGNED_QUANTITIES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_transport_planar_bilayer_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_planar_bilayer', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
