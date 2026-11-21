"""The extraction of ONE grating-coupled interferometry (GCI) experiment from one chunk of text, derived from the GCI
grader's input form (``literature_gci_record.py``).

Same design as the SPR, ITC and BLI extractions and private to GCI: the grader's input form IS the extraction's answer
form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities,
units, facts and vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte
span, and a quote that does not occur in the chunk exactly once is refused.

Differences from the other types that come from the form: concentrations may be in pM, the surface mass (response
and immobilization level) is in pg/mm2, ng/mm2 or RU, the form has a chip type (a controlled list of chip surface
chemistries) and the GCI fit models, and a fact that repeated-pulse (waveRAPID) kinetics was used. Every number must
be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to
records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_gci_record import (
    CHIP_TYPES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
CHIP_TYPE = 'chip_type'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the interaction as the passage reports it (the kinetic fit, or the one KD the passage reports if it does not say how it was obtained).',
    'kd_steady_state': 'A KD the passage says came from a steady-state (equilibrium response) fit, when the passage also reports a kinetic one.',
    'kon': 'The association rate constant kon, in M^-1 s^-1.',
    'koff': 'The dissociation rate constant koff, in s^-1.',
    'response_max': 'The maximum binding response, the surface mass signal in pg/mm2, ng/mm2 or response units (RU).',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. An uncertainty reported for any other value, such as the steady-state KD, is not this field.',
    'immobilization_level': 'The amount of partner immobilized or captured on the chip surface, in pg/mm2, ng/mm2 or response units (RU).',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The analyte concentrations that were injected, as a list of numbers in one unit. A single concentration that the passage says was injected (once or in repeated pulses) is a list of one number.',
    SPREAD_KIND: 'What the reported KD uncertainty is.',
    FIT_MODEL: 'The model the passage says the sensorgrams were fitted with.',
    CHIP_TYPE: 'The kind of sensor chip (surface chemistry) the passage says the partner was immobilized or captured on.',
    'reference_channel_subtracted': 'Whether the passage says a reference channel (a channel without the immobilized partner, or with an unrelated one) was subtracted from the signal.',
    'double_referenced': 'Whether the passage says the data were double referenced (the reference channel and blank buffer injections both subtracted).',
    'bulk_solvent_corrected': 'Whether the passage says the bulk refractive-index or solvent (for example DMSO) effect was corrected, for example with solvent-correction injections.',
    'baseline_stable': 'Whether the passage says the baseline was stable (no significant drift).',
    'regeneration': 'Whether the passage says the chip surface was regenerated cleanly between cycles (yes), or says regeneration was incomplete or the surface was not restored (no). A passage that only says each surface was used once states neither: leave it unavailable.',
    'independent_channels_or_chips': 'Whether the passage says the replicates were run on independent channels or chips (separate surfaces or immobilizations).',
    'immobilized_partner_active': 'Whether the passage says the partner immobilized on the chip was shown to be active. It is stated only when the passage says that the immobilized partner of this experiment bound a known ligand or was shown to be active; a positive-control experiment with a different complex is not that statement: leave it unavailable.',
    'analyte_bivalent_or_oligomeric': 'Whether the passage says the analyte is bivalent or oligomeric.',
    'mass_transport_checked': 'Whether the passage says mass-transport limitation was checked or considered.',
    'nonspecific_binding_checked': 'Whether the passage says non-specific binding of the analyte to the chip surface (a surface without the immobilized partner) was checked.',
    'single_estimate_method': 'Whether the passage itself says that only one method (kinetic or steady-state) was used to estimate the KD (yes), or says that both were used (no). A passage that merely reports one KD does not say this: leave it unavailable.',
    'repeated_pulse_kinetics_used': 'Whether the passage says the kinetics were measured with repeated short analyte pulses of one concentration (the waveRAPID method). Answer no only if the passage says that method was not used; a passage that only describes another injection scheme states neither: leave it unavailable.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the spread kind,
    the fit model, the chip type, the facts."""
    return (*QUANTITIES, SERIES, SPREAD_KIND, FIT_MODEL, CHIP_TYPE, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(SPREAD_KINDS)} if name == SPREAD_KIND else
             {'enum': list(FIT_MODELS)} if name == FIT_MODEL else
             {'enum': list(CHIP_TYPES)} if name == CHIP_TYPE else
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
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The GCI record of ``literature_gci_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            SPREAD_KIND: choice(SPREAD_KIND), FIT_MODEL: choice(FIT_MODEL), CHIP_TYPE: choice(CHIP_TYPE),
            'choice_support': {name: answer[name]['support'] for name in (SPREAD_KIND, FIT_MODEL, CHIP_TYPE)},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
