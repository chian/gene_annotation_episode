"""The extraction of ONE oxygen-electrode enzyme assay (type 'oxygen_electrode') from one chunk of text, derived from the
grader's input form (``literature_oxygen_electrode_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_oxygen_electrode_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain
choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_oxygen_electrode_record import (
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
    'catalytic_efficiency': 'The catalytic efficiency kcat/Km (also written kcat/KM or the specificity constant) of the enzyme for the substrate, as the passage reports it, in M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1.',
    'catalytic_efficiency_spread': 'The reported uncertainty of the catalytic efficiency (the number after a plus-minus sign, or a standard error or deviation), in the unit of the catalytic efficiency.',
    'turnover': 'The turnover number kcat of the enzyme for the substrate, as the passage reports it, in s^-1 or min^-1. It is a rate per enzyme (or per active site), not a rate per mass of protein.',
    'turnover_spread': 'The reported uncertainty of the turnover number kcat, in the unit of the turnover number.',
    'specific_activity': 'The specific activity of the enzyme as the passage reports it, a rate of oxygen uptake or oxygen evolution per mass of protein: in U/mg (one U is one umol per minute), umol/min/mg or nmol/min/mg (for example umol O2 per minute per mg of protein). A rate with no amount of protein (nmol O2 per minute, uM per minute) is not a specific activity.',
    'specific_activity_spread': 'The reported uncertainty of the specific activity, in the unit of the specific activity.',
    'rate_over_control': 'How many times larger the rate of oxygen uptake (or evolution) with the enzyme is than the rate of the paper\'s own control (a no-enzyme or substrate-only blank, an inactive or heat-treated enzyme, or the reaction without the enzyme), when the passage gives it as a ratio or as a fold.',
    'rate_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'km': 'The Michaelis constant Km (KM) of the enzyme for the substrate (not for oxygen), as the passage reports it, in a concentration unit.',
    'substrate_concentration': 'The substrate concentration at which the rate was measured (a single concentration of the reaction, not the whole series), in a concentration unit.',
    'enzyme_concentration': 'The concentration of the enzyme in the reaction in which the rate was measured, in nM or uM.',
    'oxygen_consumed_percent': 'The percent of the dissolved oxygen that was consumed (or, for an enzyme that gives off oxygen, produced over the starting oxygen) in the part of the trace from which the rate was taken, when the passage says it (for example "less than 10% of the oxygen was consumed").',
    'starting_oxygen': 'The concentration of dissolved oxygen in the chamber at the start of the measurement, in a concentration unit (for example the air-saturated value the passage states, such as 258 uM at 25 degrees C).',
    'oxygen_km': 'The Michaelis constant of the enzyme for oxygen (the apparent Km for O2), as the passage reports it, in a concentration unit.',
    'enzyme_mass': 'The molar mass of the enzyme (the subunit) that the passage gives, in kDa.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The substrate concentrations of the saturation (Michaelis-Menten) curve over which the oxygen rate was measured, as a list of numbers in one unit.',
    'spread_kind': 'What the reported spreads (the uncertainties of the rate quantities) are.',
    'sensor_kind': 'The oxygen sensor of the measurement: a Clark-type (polarographic) electrode, an optical oxygen sensor (optode), or a high-resolution respirometer (for example an Oroboros oxygraph).',
    'oxygen_change': 'Whether the enzyme reaction takes oxygen up (consumption, as an oxidase or oxygenase does) or gives oxygen off (evolution, as a catalase or a water-oxidizing enzyme does) in the measurement.',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme (a substrate-only or buffer-only chamber, to see the drift of the oxygen signal and the autoxidation of the substrate) was measured.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured.',
    'no_substrate_control': 'Whether the passage says a control with the enzyme and without the substrate was measured.',
    'electrode_calibrated': 'Whether the passage says the oxygen sensor was calibrated (for example against air-saturated buffer and a zero-oxygen point such as sodium dithionite or nitrogen).',
    'rate_proportional_to_enzyme': 'Whether the passage says the oxygen rate was shown to be proportional to (linear in) the amount of enzyme.',
    'oxygen_use_coupled': 'Whether the passage says the oxygen use was shown to belong to the claimed reaction: oxygen uptake tied to the formation of the product or the loss of the substrate (a stoichiometry of oxygen to product, or a parallel measurement of the product), or the fate of the oxygen tested (for example with catalase or superoxide dismutase).',
    'product_identified': 'Whether the passage says the product of the reaction was identified by another measurement (for example chromatography, mass spectrometry or NMR).',
    'linear_oxygen_trace': 'Whether the passage says the rate was taken from the linear part of the oxygen trace (an initial rate).',
    'active_site_concentration_determined': 'Whether the passage says the concentration of active enzyme (active sites) was determined, for example by an active-site titration, as opposed to taking the protein concentration as the enzyme concentration.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate or a general electron donor.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate, a membrane preparation, isolated mitochondria or whole cells).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or chamber fillings) rather than repeated reads of one mixture.',
    'oxygen_change_detected_above_control': 'Whether the passage says the enzyme changed the oxygen in the chamber (took oxygen up or gave it off) above the paper\'s own control: yes when it states oxygen uptake or evolution was detected above the control or the drift, no only when it states that no oxygen change above the control or the drift was detected.',
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
    """The record of ``literature_oxygen_electrode_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'oxygen_electrode', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
