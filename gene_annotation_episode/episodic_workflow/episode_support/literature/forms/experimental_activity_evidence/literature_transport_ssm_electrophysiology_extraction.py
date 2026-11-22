"""The extraction of ONE solid-supported membrane electrophysiology experiment (type 'transport_ssm_electrophysiology') from one chunk of text, derived
from the grader's input form (``literature_transport_ssm_electrophysiology_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_ssm_electrophysiology_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the two plain choices); the
converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_ssm_electrophysiology_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('sensor_count', 'preparation_count')

MEANING = {
    'km': 'The apparent Michaelis constant Km (also written K0.5, half-saturating concentration or apparent affinity) of the substrate that the passage derives from the peak current (or the charge) of the substrate concentration jumps, in a concentration unit.',
    'km_spread': 'The reported uncertainty of that Km (the number after a plus-minus sign, or a standard error, deviation or fit error), in the unit of the Km.',
    'fold_over_control': 'How many times larger the signal (peak current or charge) of the sensor with the transporter is than that of the paper\'s own control (a sensor with empty, protein-free liposomes, or a jump without substrate), when the passage gives it as a ratio or as a fold.',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'peak_current': 'The peak of the transient current after a substrate concentration jump, as the passage reports it (the size of the current without its sign), in pA, nA or uA.',
    'charge': 'The charge translocated after a substrate concentration jump (the integral of the transient current), as the passage reports it (without its sign), in pC, nC or uC.',
    'decay_time': 'The decay time constant of the transient current after the jump (the time in which the current falls to 1/e), in ms or s.',
    'jump_substrate_concentration': 'The substrate concentration of the jump at which the peak current or charge of this experiment was read (one concentration, not the whole series), in a concentration unit.',
    'sensor_count': 'The number of sensors (gold sensors, solid-supported membranes) on which the readings were made, as a whole number.',
    'preparation_count': 'The number of independent proteoliposome (or membrane) preparations used, as a whole number.',
    SERIES: 'The substrate concentrations of the jumps over which the peak current (or charge) was measured to give the Km, as a list of numbers in one unit.',
    'spread_kind': 'What the reported spreads (the uncertainties of the Km and of the fold) are.',
    'readout': 'What the stated Km or fold was derived from: the peak current of the transient, or the integrated charge.',
    'empty_liposome_sensor_done': 'Whether the passage says a control sensor with empty liposomes (without the protein, or an equivalent protein-free membrane preparation) was measured with the same jump.',
    'non_substrate_jump_done': 'Whether the passage says a jump with a non-substrate (an analogue or another molecule the protein does not transport) or a jump with buffer only gave no current, or a smaller one, on the sensor with the protein.',
    'buffer_jump_artefact_subtracted': 'Whether the passage says the solution-exchange artefact (the current of the jump itself, seen without transport) was measured and subtracted, or shown to be absent or small.',
    'solutions_matched_except_substrate': 'Whether the passage says the resting (non-activating) and the activating solutions were identical apart from the substrate (the same buffer, pH, ionic strength and ions), so that only the substrate changes in the jump.',
    'sensor_capacitance_stated': 'Whether the passage says the capacitance and the conductance of the sensor (the check of the solid-supported membrane) were measured or stated.',
    'same_sensor_reference_jump': 'Whether the passage says the peak currents were normalized to, or checked against, a reference jump (a standard substrate concentration) measured on the same sensor.',
    'blocker_control_done': 'Whether the passage says a known inhibitor or blocker of the transporter reduced or abolished the current.',
    'ion_substitution_done': 'Whether the passage says the coupling ion or another ion of the solutions was substituted (for example sodium replaced by lithium, potassium or choline) and the current changed or vanished.',
    'inactive_protein_control_done': 'Whether the passage says a catalytically inactive or mutant protein, or heat-inactivated protein, reconstituted in the same way, was measured and gave no current or a smaller one.',
    'electrogenic_transport_stated': 'Whether the passage says the transport of the substrate by this protein is electrogenic: that net charge moves across the membrane in the transport cycle, so that a transient current is expected.',
    'native_substrate': 'Whether the passage says the molecule of the jump is the native (natural, physiological) substrate of the protein, as opposed to an analogue or a surrogate.',
    'independent_sensors': 'Whether the passage says the readings were made on different, independent sensors (each with its own membrane), rather than repeated jumps on one sensor.',
    'independent_preparations': 'Whether the passage says the sensors came from independent preparations (separate reconstitutions or protein preparations).',
    'transport_detected_above_control': 'Whether the passage says the protein gave a transient current above the paper\'s own control: yes when it states a current (transport) was detected above the control or the noise, no only when it states that no current above the control or the noise was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices, the facts."""
    return (*QUANTITIES, SERIES, *CHOICES, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
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
        numbers = item['value'] if name == SERIES else [item['value']] if name in QUANTITIES else []
        if name == SERIES and not numbers:
            _refuse(name, 'series_is_empty')
        if any(number <= 0 for number in numbers):
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_transport_ssm_electrophysiology_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_ssm_electrophysiology', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
