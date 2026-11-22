"""The extraction of ONE continuous coupled-enzyme assay (type 'coupled_enzyme') from one chunk of text, derived from the
grader's input form (``literature_coupled_enzyme_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupled_enzyme_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupled_enzyme_record import (
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
    'catalytic_efficiency': 'The catalytic efficiency kcat/Km (also written kcat/KM or the specificity constant) of the primary enzyme for the substrate, as the passage reports it, in M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1.',
    'catalytic_efficiency_spread': 'The reported uncertainty of the catalytic efficiency (the number after a plus-minus sign, or a standard error or deviation), in the unit of the catalytic efficiency.',
    'turnover': 'The turnover number kcat of the primary enzyme for the substrate, as the passage reports it, in s^-1 or min^-1. It is a rate per enzyme (or per active site), not a rate per mass of protein.',
    'turnover_spread': 'The reported uncertainty of the turnover number kcat, in the unit of the turnover number.',
    'specific_activity': 'The specific activity of the primary enzyme for the substrate as the passage reports it, a rate per mass of protein: in U/mg (one U is one umol per minute), umol/min/mg or nmol/min/mg.',
    'specific_activity_spread': 'The reported uncertainty of the specific activity, in the unit of the specific activity.',
    'rate_over_control': 'How many times larger the rate of the primary enzyme is than the rate of the paper\'s own control (a reaction without the primary enzyme, an inactive or heat-treated enzyme, or the reporter background), when the passage gives it as a ratio or as a fold.',
    'rate_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'km': 'The Michaelis constant Km (KM) of the primary enzyme for its substrate (not the Km of a coupling enzyme), as the passage reports it, in a concentration unit.',
    'primary_rate': 'The rate of the primary reaction in the reaction mixture, per volume of the mixture (not per mass of protein), as the passage reports it: in uM/min, mM/min, nM/min, U/mL or mU/mL (one U is one umol per minute).',
    'coupling_enzyme_activity': 'The activity of the coupling (auxiliary, helper or linking) enzyme that is added to turn the product of the primary reaction into the reporter signal, in the reaction mixture, in U/mL or mU/mL (one U is one umol per minute). When the passage names several coupling enzymes, the one with the lowest activity.',
    'coupling_excess': 'How many times larger the activity of the coupling enzyme is than the rate of the primary reaction, when the passage states that ratio (for example "the coupling enzymes were in 50-fold excess"), as a fold.',
    'lag_time': 'The lag of the coupled system: the time the reporter signal takes after the start of the reaction before it becomes linear (the lag phase, the delay before the steady rate), in s or min, when the passage gives it.',
    'rate_start_time': 'The time after the start of the reaction from which the rate was read (the start of the window the rate was taken from, for example "the rate was taken between 2 and 5 min": 2 min), in s or min.',
    'substrate_consumed_percent': 'The percent of the primary substrate that was consumed (converted) in the part of the reaction from which the rate was taken, when the passage says it (for example "less than 10% of the substrate was consumed").',
    'wavelength': 'The wavelength at which the reporter (for example NADH or NADPH) was read, in nm.',
    'extinction_coefficient': 'The extinction (molar absorption) coefficient of the reporter that the passage uses to turn the absorbance change into a concentration change (for example 6.22 mM^-1 cm^-1 for NADH at 340 nm), in M^-1 cm^-1 or mM^-1 cm^-1.',
    'absorbance_max': 'The highest absorbance reached in the measurement (for example the starting absorbance of the reporter), or the absorbance range the passage says was kept below (for example "absorbance below 1.5"), in absorbance units (AU).',
    'enzyme_mass': 'The molar mass of the primary enzyme (the subunit) that the passage gives, in kDa.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The primary-substrate concentrations of the saturation (Michaelis-Menten) curve over which the rate was measured, as a list of numbers in one unit.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the rate quantities) are.',
    'no_primary_enzyme_control': 'Whether the passage says a control without the primary enzyme (the complete reaction mixture with the coupling enzymes and the reporter but no primary enzyme, a buffer-only blank) was measured.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive primary enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured.',
    'no_substrate_control': 'Whether the passage says a control with the primary enzyme and the coupling system but without the primary substrate was measured.',
    'rate_proportional_to_enzyme': 'Whether the passage says the rate was shown to be proportional to (linear in) the amount of the primary enzyme.',
    'coupling_system_checked': 'Whether the passage says the coupling system was checked to respond at once and fully to the intermediate or product of the primary reaction (for example the product was added at the end of the run or in a separate run and the reporter signal followed immediately, or the rate did not change when more coupling enzyme was added).',
    'coupling_enzymes_unaffected': 'Whether the passage says the coupling enzymes were shown not to be affected by what was added or changed in the experiment (an effector, inhibitor, partner, test compound or a buffer change), for example by running the coupling system alone with it.',
    'lag_phase_excluded': 'Whether the passage says the rate was taken after the lag phase, from the linear steady part of the reporter signal.',
    'linear_progress_curve': 'Whether the passage says the rate was taken from the linear part of the progress curve (an initial rate).',
    'reporter_stoichiometry_stated': 'Whether the passage says how many molecules of the reporter (for example NADH) are consumed or formed per molecule of product of the primary reaction (for example "one NADH is oxidized per ADP formed"), as used to turn the reporter slope into the primary rate.',
    'active_site_concentration_determined': 'Whether the passage says the concentration of active enzyme (active sites) was determined, for example by an active-site titration, as opposed to taking the protein concentration as the enzyme concentration.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate substrate.',
    'purified_enzyme': 'Whether the passage says the primary enzyme was purified (as opposed to a cell lysate or extract).',
    'product_identified': 'Whether the passage says the product of the primary reaction was identified by another measurement (for example chromatography, mass spectrometry or NMR), not only through the coupling reaction.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'activity_detected_above_control': 'Whether the passage says the primary enzyme showed activity above the paper\'s own control: yes when it states activity was detected above the control or detection limit, no only when it states that no activity above the control or detection limit was detected.',
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
    """The record of ``literature_coupled_enzyme_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'coupled_enzyme', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
