"""The extraction of ONE bio-layer interferometry (BLI) experiment from one chunk of text, derived from the BLI
grader's input form (``literature_bli_record.py``).

Same design as the SPR and ITC extractions and private to BLI: the grader's input form IS the extraction's answer
form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities,
units, facts and vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte
span, and a quote that does not occur in the chunk exactly once is refused.

Differences from SPR that come from the form: the response and the loading level are in nm, the dissociation time
may be in s or min, the fit R-squared must lie in (0, 1], and the form has a biosensor type (a controlled list of
sensor chemistries) and the BLI fit models. Every number must be above 0. Fields not extracted
(``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the
caller and the four preparation references (``preparations``) are references to records, which no passage states;
they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_record import (
    BIOSENSOR_TYPES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
BIOSENSOR_TYPE = 'biosensor_type'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
R_SQUARED = 'fit_r_squared'
R_SQUARED_MAX = 1   # an R-squared is a fraction of the variance: at most 1 (a definition)

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the interaction as the passage reports it (the kinetic fit, or the one KD the passage reports if it does not say how it was obtained).',
    'kd_steady_state': 'A KD the passage says came from a steady-state (equilibrium response) fit, when the passage also reports a kinetic one.',
    'kon': 'The association rate constant kon, in M^-1 s^-1.',
    'koff': 'The dissociation rate constant koff, in s^-1.',
    'response_max': 'The maximum binding response, the wavelength shift in nanometres (nm).',
    'kd_spread': 'The reported uncertainty of the KD (its standard error, standard deviation or confidence interval half-width), in a concentration unit.',
    'fit_r_squared': 'The R-squared (coefficient of determination) of the fit, a number between 0 and 1.',
    'loading_level': 'The amount of partner loaded on the sensor, the loading step response in nanometres (nm).',
    'dissociation_time': 'The length of the dissociation step (the time the sensors were in buffer after the analyte), in seconds or minutes.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'partner_mass': 'The molecular mass of the partner loaded on the sensor (the immobilized protein, not the analyte), in kDa.',
    'baseline_noise': 'The noise or drift of the signal (the baseline noise level) that the passage states, in nanometres (nm): the size of signal that cannot be told from the baseline.',
    SERIES: 'The analyte concentrations of the titration series that was measured, as a list of numbers in one unit.',
    SPREAD_KIND: 'What the reported KD uncertainty is.',
    FIT_MODEL: 'The model the passage says the sensorgrams were fitted with.',
    BIOSENSOR_TYPE: 'The kind of biosensor (sensor surface chemistry) the passage says the partner was loaded on.',
    'reference_sensor_subtracted': 'Whether the passage says a reference sensor (a sensor without the loaded partner, or a reference well) was subtracted from the signal.',
    'buffer_reference_subtracted': 'Whether the passage says a buffer-only reference (the loaded sensor in buffer, no analyte) was subtracted from the signal.',
    'baseline_stable': 'Whether the passage says the baseline was stable (no significant drift).',
    'loading_step_documented': 'Whether the passage describes the loading step of the partner onto the sensor (how much was loaded and for how long).',
    'regeneration': 'Whether the passage says the sensor surface was regenerated cleanly between cycles (yes), or says regeneration was incomplete or the surface was not restored (no). A passage that only says each sensor was used once states neither: leave it unavailable.',
    'independent_sensors': 'Whether the passage says the replicates were run on independent sensors (separate sensors or loadings).',
    'immobilized_partner_active': 'Whether the passage says the partner loaded on the sensor was shown to be active.',
    'analyte_bivalent_or_oligomeric': 'Whether the passage says the analyte is bivalent or oligomeric.',
    'avidity_rebinding_considered': 'Whether the passage says avidity or rebinding was considered (for example low loading used to avoid it).',
    'mass_transport_considered': 'Whether the passage says mass-transport limitation was considered.',
    'nonspecific_binding_checked': 'Whether the passage says non-specific binding of the analyte to a blank sensor (without the loaded partner) was checked.',
    'single_estimate_method': 'Whether the passage itself says that only one method (kinetic or steady-state) was used to estimate the KD (yes), or says that both were used (no). A passage that merely reports one KD does not say this: leave it unavailable.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the spread kind,
    the fit model, the biosensor type, the facts."""
    return (*QUANTITIES, SERIES, SPREAD_KIND, FIT_MODEL, BIOSENSOR_TYPE, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(SPREAD_KINDS)} if name == SPREAD_KIND else
             {'enum': list(FIT_MODELS)} if name == FIT_MODEL else
             {'enum': list(BIOSENSOR_TYPES)} if name == BIOSENSOR_TYPE else
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
    occurs exactly once in ``chunk``; a number is above 0 (an R-squared also at most 1) and a stated value carries its unit
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
    errors = sorted(Draft202012Validator(answer_schema()).iter_errors(answer), key=lambda error: list(error.path))
    if errors:
        _refuse('.'.join(str(part) for part in errors[0].path) or 'answer', 'schema', errors[0].message[:200])
    for name in field_names():
        item = answer[name]
        carried = ('value', 'quote', 'support') +(('unit',) if name in UNITS else ())
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
        if name == R_SQUARED and item['value'] > R_SQUARED_MAX:
            _refuse(name, 'r_squared_must_be_at_most_one')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The BLI record of ``literature_bli_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            SPREAD_KIND: choice(SPREAD_KIND), FIT_MODEL: choice(FIT_MODEL), BIOSENSOR_TYPE: choice(BIOSENSOR_TYPE),
            'choice_support': {name: answer[name]['support'] for name in (SPREAD_KIND, FIT_MODEL, BIOSENSOR_TYPE)},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
