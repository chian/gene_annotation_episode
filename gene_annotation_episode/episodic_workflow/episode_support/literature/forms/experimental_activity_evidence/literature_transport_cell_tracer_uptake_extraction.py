"""The extraction of ONE whole-cell tracer uptake (or efflux) experiment (type 'transport_cell_tracer_uptake') from one chunk of text, derived from the
grader's input form (``literature_transport_cell_tracer_uptake_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_cell_tracer_uptake_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the two plain
choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_cell_tracer_uptake_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'km': 'The Michaelis constant Km (or the half-saturation constant K0.5, or the apparent affinity) of the uptake of the labelled substrate by the cells, as the passage reports it, in a concentration unit.',
    'km_spread': 'The reported uncertainty of the Km (the number after a plus-minus sign, or a standard error or deviation), in the unit of the Km.',
    'normalized_rate': 'The rate at which the cells take up (or release) the labelled substrate, per mass of the cells, as the passage reports it: in pmol/min/mg, nmol/min/mg or umol/min/mg. It is an initial velocity or uptake rate; an amount taken up at one time (for example "12 nmol/mg after 30 min") is an accumulated amount and not a rate, and a rate per cell or per 10^9 cells is not in the unit list.',
    'normalized_rate_spread': 'The reported uncertainty of that uptake rate, in the unit of the rate.',
    'fold_over_control': 'How many times larger the uptake of the cells that make the protein is than the uptake of the paper\'s own control cells (cells with the empty vector, the parent strain or a deletion strain), when the passage gives it as a ratio or as a fold (for example "6-fold over the empty vector").',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'time_window': 'The length of the uptake interval from which the reported rate was taken, or the time at which the uptake was stopped (for example "uptake was measured for 30 s" or "initial velocity over 120 s"), in s or min.',
    'specific_activity': 'The specific activity of the labelled substrate, which turns counts into an amount (for example 40 mCi/mmol), in mCi/mmol or Ci/mmol.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The substrate concentrations of the saturation (Michaelis-Menten) series over which the uptake rate was measured, as a list of numbers in one unit.',
    'spread_kind': 'What the reported spreads (the uncertainties of the Km, the rate and the fold) are.',
    'rate_basis': 'What the mass in the unit of the uptake rate is: the protein of the cells (mg protein) or their dry weight (mg dry weight).',
    'empty_vector_control_done': 'Whether the passage says control cells without the protein (cells with the empty vector, the parent strain or a deletion strain) were run in the same uptake experiment.',
    'zero_time_control_done': 'Whether the passage says a sample taken at time zero or kept on ice (the label that sticks to the cells and the filter without being transported) was measured and set aside.',
    'linear_interval_shown': 'Whether the passage says the uptake rate was taken from the linear part of the time course (an initial rate), for example that uptake was linear for the interval used.',
    'competitor_control_done': 'Whether the passage says the uptake of the label was reduced by an excess of the unlabelled substrate or by a competing compound (a competition control).',
    'energy_control_done': 'Whether the passage says the dependence of the uptake on an energy source or a gradient was tested, for example with an uncoupler, an inhibitor, energy-depleted cells or cells kept cold.',
    'label_identity_shown': 'Whether the passage says the label taken up by the cells was shown to be the unchanged substrate and not a metabolite of it (for example by chromatography of a cell extract).',
    'expression_confirmed': 'Whether the passage says the production of the protein in the cells was confirmed (for example by an immunoblot, a tag signal or a membrane fraction).',
    'viability_checked': 'Whether the passage says the viability or the membrane integrity of the cells was checked.',
    'native_substrate': 'Whether the passage says the labelled compound is the natural substrate itself, as opposed to an analogue or a surrogate of it.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, cultures or preparations) rather than repeated filters of one sample.',
    'uptake_detected_above_control': 'Whether the passage says the cells that make the protein took up (or released) the substrate above the paper\'s own control cells or background: yes when it states transport was detected above the control or background, no only when it states that no transport above the control or background was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the plain choices, the facts."""
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
    """The record of ``literature_transport_cell_tracer_uptake_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_cell_tracer_uptake', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
