"""The extraction of ONE two-electrode voltage clamp experiment on Xenopus oocytes (type 'transport_oocyte_two_electrode') from one chunk of text, derived from the
grader's input form (``literature_transport_oocyte_two_electrode_record.py``). DRAFT of 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The four things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_oocyte_two_electrode_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices);
the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_oocyte_two_electrode_record import (
    CHOICES, EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('oocyte_count', 'batch_count')

MEANING = {
    'km': 'The apparent Km of the substrate-induced current (also written KM, K0.5, K1/2 or the half-saturating substrate concentration), as the passage reports it for the oocytes with the protein, in a concentration unit. An IC50 or Ki of an inhibitor is not a Km.',
    'km_spread': 'The reported uncertainty of that Km (the number after a plus-minus sign, or a standard error or deviation), in the unit of the Km.',
    'fold_over_control': 'How many times larger the substrate-induced current of the oocytes with the protein is than that of the paper\'s own control oocytes (injected with water or not injected), when the passage gives it as a ratio or as a fold.',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'current': 'The size of the substrate-induced current (the change of the current of the same oocyte from before the substrate to during it) of the oocytes with the protein, as the passage reports it, in nA or uA. Give its size, not its sign; the direction goes in current_direction.',
    'control_current': 'The size of the substrate-induced current of the paper\'s own control oocytes (injected with water or not injected) under the same conditions as the current, in nA or uA.',
    'substrate_concentration': 'The substrate concentration at which the current (or the fold over the control) was measured (a single concentration of the experiment, not the whole series), in a concentration unit.',
    'oocyte_count': 'The number of oocytes recorded for the result (the n of the mean), as a whole number, when the passage says it counts oocytes.',
    'batch_count': 'The number of independent batches of oocytes (oocytes of different donor frogs, or injected on different occasions) over which the result was repeated, as a whole number.',
    SERIES: 'The substrate concentrations of the concentration-response (saturation) curve over which the current was measured, as a list of numbers in one unit.',
    'spread_kind': 'What the reported spreads (the uncertainties of the Km and of the fold) are.',
    'current_direction': 'The direction of the substrate-induced current as the passage states it: inward or outward.',
    'uninjected_control_done': 'Whether the passage says oocytes injected with water (or not injected) from the same batch were recorded in the same way as the oocytes with the protein.',
    'control_shows_no_substrate_current': 'Whether the passage says the control oocytes (injected with water or not injected) showed no substrate-induced current, or none above the noise.',
    'same_oocyte_baseline_done': 'Whether the passage says the substrate-induced current was measured as the change from the current of the same oocyte before the substrate was added (the oocyte is its own baseline).',
    'leak_subtracted': 'Whether the passage says the leak current or the baseline current was subtracted, or that oocytes with a large or unstable leak (holding) current were excluded.',
    'non_substrate_gives_no_current': 'Whether the passage says a molecule that is not the substrate (an analogue or an unrelated compound), applied in the same way to oocytes with the protein, gave no current or a much smaller one: yes when it says so, no only when it says such a molecule gave a current like the substrate\'s.',
    'ion_dependence_shown': 'Whether the passage says the current, or its reversal voltage, changed when an ion was replaced or its concentration was changed: yes when it says it changed, no only when it says it did not.',
    'substrate_uptake_confirmed': 'Whether the passage says the movement of the substrate itself into (or out of) the oocytes was measured as well (by a labelled tracer or a chemical analysis) and was above the control: yes when it says so, no only when it says no movement of the substrate was found.',
    'inactive_mutant_gives_no_current': 'Whether the passage says an inactive mutant of the protein, or an unrelated protein, expressed in oocytes in the same way gave no current: yes when it says so, no only when it says it gave a current like the protein\'s.',
    'expression_confirmed': 'Whether the passage says the expression of the protein in the oocytes, or its presence at the oocyte surface, was shown (a blot, surface labelling or a fluorescent fusion).',
    'holding_voltage_stated': 'Whether the passage states the voltage at which the oocytes were held while the substrate-induced current was measured.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the protein, as opposed to an analogue or a surrogate.',
    'independent_batches': 'Whether the passage says the experiments were repeated on independent batches of oocytes (oocytes from different donor frogs or injected on different occasions) rather than on oocytes of one batch only.',
    'transport_detected_above_control': 'Whether the passage says the protein showed a substrate-induced current above the paper\'s own control oocytes: yes when it states a current was detected above the control or the detection limit, no only when it states that no current above the control or detection limit was detected.',
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
    """The record of ``literature_transport_oocyte_two_electrode_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
