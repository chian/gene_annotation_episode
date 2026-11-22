"""The extraction of ONE rapid chemical quench-flow enzyme experiment (type 'quench_flow') from one chunk of text, derived from the
grader's input form (``literature_quench_flow_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_quench_flow_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the two plain
choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_quench_flow_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('time_point_count', 'replicate_count')

MEANING = {
    'chemical_rate_constant': 'The observed first-order rate constant of the fast phase of the quenched time course (the burst or the single turnover), as the passage reports it (written k_obs, k_burst, k_chem, k_pol or kobs), in s^-1 or min^-1. It is a rate constant of one exponential phase, not the steady-state rate after the burst.',
    'chemical_rate_constant_spread': 'The reported uncertainty of that rate constant (the number after a plus-minus sign, or a standard error or deviation of the fit), in the unit of the rate constant.',
    'turnover': 'The steady-state turnover per enzyme (per active site) that the passage reports, the slow linear phase after the burst (written k_ss, k_cat or kcat), in s^-1 or min^-1. It is a rate per enzyme, not a rate per mass of protein.',
    'turnover_spread': 'The reported uncertainty of that steady-state turnover, in the unit of the turnover.',
    'burst_amplitude': 'The amplitude of the burst: the concentration of product made in the fast phase (the intercept of the slow linear phase, or the amplitude of the exponential), in nM, uM or mM.',
    'burst_amplitude_per_enzyme': 'The same burst amplitude given as moles of product per mole of enzyme (per active site), as a plain ratio (for example "0.9 per active site"), when the passage states it as such.',
    'enzyme_concentration': 'The concentration of the enzyme in the reaction after mixing (the concentration in the reaction, not the stock), in nM, uM or mM.',
    'substrate_concentration': 'The concentration of the substrate in the reaction after mixing (the concentration in the reaction, not the stock), in nM, uM or mM.',
    'shortest_time': 'The earliest time point of the time course: the shortest reaction time before the quench, in ms or s.',
    'longest_time': 'The latest time point of the time course: the longest reaction time before the quench, in ms or s.',
    'time_point_count': 'The number of different reaction times (time points) of the time course, a whole number.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the rate quantities) are.',
    'detection_method': 'How the product was separated and counted after the quench: radioactivity after separation (a radiolabelled substrate, separated by chromatography, a gel or a plate, then counted), chromatography (HPLC or another column with a UV or fluorescence detector), mass spectrometry, a gel or a thin-layer plate (stained or imaged), or another separation.',
    'zero_time_control': 'Whether the passage says a zero-time control was measured: the enzyme mixed with the quench before the substrate was added (a quench-before-mix or time-zero sample), to give the product present at time zero.',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme (the substrate alone, taken through the same mixing, quench and analysis) was measured.',
    'quench_stops_reaction': 'Whether the passage says the quench was shown to stop the reaction at once and completely (for example no product formed when the enzyme was mixed with the quench before the substrate, or no further product after the quench).',
    'enzyme_dependence_shown': 'Whether the passage says the product made, or the burst amplitude, was shown to increase in proportion to the enzyme concentration (measured at more than one enzyme concentration).',
    'product_identified': 'Whether the passage says the product was separated from the substrate and identified (for example by its retention time or position against a standard, or by its mass).',
    'product_quantified_against_standard': 'Whether the passage says the amount of product was calculated against a standard (a calibration curve, a known specific radioactivity or a known recovery of the product).',
    'single_turnover_conditions': 'Whether the passage says the reaction was run under single-turnover conditions: the enzyme in excess over the substrate, so that each substrate molecule reacts once.',
    'multiple_turnover_conditions': 'Whether the passage says the reaction was run under multiple-turnover conditions: the substrate in excess over the enzyme, so that a burst is followed by steady-state turnover.',
    'time_course_fitted': 'Whether the passage says the time course was fitted to an equation (a single exponential, a burst equation or a linear fit) by regression.',
    'active_site_concentration_determined': 'Whether the passage says the concentration of active enzyme (active sites) was determined, for example by an active-site titration or from the burst itself, as opposed to taking the protein concentration as the enzyme concentration.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to an analogue or a surrogate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated analyses of one reaction series.',
    'product_formed_above_control': 'Whether the passage says product was formed above the paper\'s own control (the zero-time or no-enzyme control): yes when it states product formed above the control or the detection limit, no only when it states that no product above the control or the detection limit was found.',
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
    """The record of ``literature_quench_flow_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'quench_flow', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
