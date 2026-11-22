"""The extraction of ONE patch-clamp experiment on cells (type 'transport_patch_clamp') from one chunk of text, derived from the grader's input form
(``literature_transport_patch_clamp_record.py``). DRAFT 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_patch_clamp_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the two plain
choices); the converter judges it.

Signed numbers: a number must be above 0, except the three voltages of SIGNED_QUANTITIES, which keep their sign (a reversal potential of -35 mV is -35
and 0 mV is possible).

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_patch_clamp_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SIGNED_QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('cell_count', 'batch_count')

MEANING = {
    'unitary_conductance': 'The conductance of ONE channel as the passage reports it (a single-channel conductance, from single-channel openings or from the slope of a single-channel current-voltage curve), in pS or nS. A whole-cell conductance, a current or a current density is not a unitary conductance.',
    'unitary_conductance_spread': 'The reported uncertainty of the unitary conductance (the number after a plus-minus sign, or a standard error or deviation), in the unit of the unitary conductance.',
    'charge_rate': 'The elementary charges that pass per second through ONE channel or transporter, as the passage states it (charges per second), when the passage gives it; a number of ions per second counts only when the passage says each ion carries one charge.',
    'charge_rate_spread': 'The reported uncertainty of that charge rate, in charges/s.',
    'fold_over_control': 'How many times larger the current (or the current density, or the peak current) of the cells that make the protein is than that of the paper\'s own control (untransfected cells, empty-vector cells, or the same cells before the substrate was applied), when the passage gives it as a ratio or as a fold.',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'holding_voltage': 'The voltage (membrane potential) at which the current or the conductance was taken, in mV, with its sign (for example -60 mV is -60).',
    'reversal_potential': 'The measured reversal potential of the current, in mV, with its sign (the voltage at which the current changes direction, as the passage states it).',
    'nernst_potential': 'The equilibrium (Nernst) potential of the ion that the passage tests as the carrier of the current, calculated for the recording solutions, as the passage states it, in mV, with its sign. Not the measured reversal potential.',
    'series_resistance': 'The series (access) resistance of the whole-cell recording, as the passage states it (for example "series resistance below 10 MOhm"), in MOhm.',
    'seal_resistance': 'The resistance of the seal between the pipette and the membrane, as the passage states it (for example "seal resistance above 1 GOhm"), in MOhm or GOhm.',
    'cell_count': 'The number of cells (or patches) the result is taken from (a whole number): the n of the recordings, not the number of sweeps or traces.',
    'batch_count': 'The number of independent transfections, cultures or cell preparations those cells came from (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the conductance, the charge rate and the fold) are.',
    'patch_configuration': 'The recording configuration the passage states: whole_cell, inside_out, outside_out or cell_attached.',
    'untransfected_control_done': 'Whether the passage says cells that do not make the protein (untransfected, mock-transfected or empty-vector cells, or the parent cell line) were recorded the same way.',
    'inactive_mutant_control_done': 'Whether the passage says a non-conducting or inactive form of the protein (a pore or substrate-site mutant) was recorded the same way.',
    'substrate_free_control_done': 'Whether the passage says the current was recorded without the substrate, agonist or driving gradient, or before it was applied, in the same cells.',
    'ion_substitution_done': 'Whether the passage says an ion of the bath or pipette solution was replaced and the current or its reversal potential was examined.',
    'blocker_control_done': 'Whether the passage says a blocker or inhibitor of the protein was applied to the current.',
    'series_resistance_compensated': 'Whether the passage says the series resistance was compensated (electronically, partly or fully): yes when it says so, no only when it says the series resistance was not compensated.',
    'leak_subtracted': 'Whether the passage says the leak current was subtracted or corrected.',
    'driving_force_corrected': 'Whether the passage says the conductance was taken from the slope of the current-voltage curve or as the current divided by the voltage minus the reversal potential, that is corrected for the driving force.',
    'single_channel_resolved': 'Whether the passage says single-channel events (single openings) were resolved in the recording.',
    'independent_preparations': 'Whether the passage says the cells came from independent transfections, cultures or preparations (different days or dishes) rather than from one dish.',
    'native_substrate': 'Whether the passage says the substrate or ion that was applied or carried the current is the native (natural, physiological) one, as opposed to an analogue or a surrogate.',
    'transport_detected_above_control': 'Whether the passage says the protein showed a current (transport) above the paper\'s own control: yes when it states the current was detected above the control cells or baseline, no only when it states that no current above the control was detected.',
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
    occurs exactly once in ``chunk``; a number is above 0 (a voltage of SIGNED_QUANTITIES keeps its sign) and a stated value carries its unit
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
    """The record of ``literature_transport_patch_clamp_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_patch_clamp', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
