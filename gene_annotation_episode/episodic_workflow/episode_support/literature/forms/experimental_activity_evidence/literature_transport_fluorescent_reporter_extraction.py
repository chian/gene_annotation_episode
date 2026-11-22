"""The extraction of ONE fluorescent-reporter transport experiment in cells (type 'transport_fluorescent_reporter', class transport_response) from one
chunk of text, derived from the grader's input form (``literature_transport_fluorescent_reporter_record.py``). DRAFT of 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_fluorescent_reporter_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_fluorescent_reporter_record import (
    FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'fold_over_control': 'How many times larger the fluorescence signal (its slope or its change) of the cells with the studied transporter is than that of the paper\'s own control (untransfected cells, empty-vector cells, the parent or a knockout strain, or the same cells before the substrate was added), when the passage gives it as a ratio or as a fold.',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the control (the number after a plus-minus sign, or a standard error or deviation), as a fold.',
    'km': 'The Km (K0.5, or the half-maximal concentration of the signal, EC50) of the transported substrate, as the passage reports it for this transporter, in a concentration unit.',
    'km_spread': 'The reported uncertainty of the Km, in a concentration unit.',
    'substrate_concentration': 'The concentration of the substrate, the fluorescent analogue or the dye at which the signal was measured (a single concentration of the experiment, not the whole series), in a concentration unit.',
    'z_prime_factor': 'The Z\' factor (Z-prime) of the assay as the passage reports it, a number without a unit that says how well the signal of the cells with the transporter is separated from that of the control cells.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The substrate concentrations of the concentration-response (saturation) curve over which the signal was measured, as a list of numbers in one unit.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the fold and of the Km) are.',
    'untransfected_control_done': 'Whether the passage says control cells without the studied transporter (untransfected cells, cells with an empty vector, the parent strain or a knockout) were measured in the same way.',
    'no_substrate_control_done': 'Whether the passage says a control without the substrate or fluorescent molecule (a buffer-only or vehicle addition, or cells without the dye) was measured in the same way.',
    'background_fluorescence_subtracted': 'Whether the passage says the background or the autofluorescence (of unlabelled cells, of the medium or of the cell-free wells) was measured and subtracted.',
    'signal_drift_controlled': 'Whether the passage says the drift of the signal from photobleaching or from leakage of the dye out of the cells was measured or corrected (for example a dye-loaded control without substrate followed over the same time).',
    'indicator_calibrated': 'Whether the passage says the indicator or sensor was calibrated (a standard curve, or high and low standards, or a saturating and a zero concentration with an ionophore) so that the signal can be read as a concentration.',
    'analogue_is_native_substrate': 'Whether the passage says what is read is the native (natural) substrate or ion itself, for example a sensor or indicator of that substrate: yes when it says so, no only when it says the fluorescent molecule is an analogue, a labelled derivative or a surrogate ion (for example a fluorescent glucose analogue, or thallium for potassium).',
    'competitor_control_done': 'Whether the passage says the signal was reduced by an excess of the unlabelled natural substrate, by a competitor or by a specific inhibitor of the transporter.',
    'indicator_specificity_shown': 'Whether the passage says the indicator or sensor was shown to respond to the transported substrate or ion and not to others (for example to other ions, to pH or to metabolites).',
    'expression_confirmed': 'Whether the passage says the expression or the membrane insertion of the studied transporter in the cells was confirmed (for example by a blot, a tag, an antibody or its fluorescence).',
    'cells_intact_checked': 'Whether the passage says the viability or the membrane integrity of the cells was checked (for example by a viability dye, release of a cytoplasmic marker or retention of a dye).',
    'linear_interval_shown': 'Whether the passage says the signal was taken from the linear or early part of its time course (an initial rate), or that the time course was shown to be linear over the interval used.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, cultures or transfections) rather than repeated wells of one preparation.',
    'transport_detected_above_control': 'Whether the passage says the studied protein showed transport above the paper\'s own control: yes when it states that uptake, efflux or a signal was detected above the control cells, no only when it states that no transport above the control or the detection limit was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the spread kind, the facts."""
    return (*QUANTITIES, SERIES, SPREAD_KIND, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
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
    """The record of ``literature_transport_fluorescent_reporter_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_fluorescent_reporter', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
