"""The extraction of ONE fluorescence polarization / anisotropy (FP/FA) binding experiment from one chunk of text,
derived from the FP grader's input form (``literature_fp_record.py``).

Same design as the SPR, ITC, BLI and GCI extractions and private to FP: the grader's input form IS the extraction's
answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities,
units, facts and vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte
span, and a quote that does not occur in the chunk exactly once is refused.

Differences from the other types that come from the form: the polarization ends are in mP or r, the form has a
tracer concentration, a total-intensity change (percent), an assay volume, an incubation time and a temperature, a
competition inhibition constant Ki beside the KD, an assay format (direct titration or competition), a plate type and
the FP fit models. Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references
(``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller and the three preparation references
(``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fp_record import (
    ASSAY_FORMATS, CHOICES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, INTENSITY_DIRECTIONS, PLATE_TYPES, PREPARATION_KEYS, QUANTITIES, SERIES_KINDS, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
INTENSITY_DIRECTION = 'intensity_change_direction'
SERIES_KIND = 'series_kind'
SERIES = 'concentration_series'
ASSAY_FORMAT = 'assay_format'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
PLATE_TYPE = 'plate_type'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the tracer with its partner, as the passage reports it from a direct titration of the tracer (a half-maximal binding concentration is this field only if the passage reports it as the KD).',
    'ki': 'The inhibition constant Ki of an unlabelled ligand that displaces the tracer, as the passage reports it from a competition (displacement) experiment. An IC50 is not this field.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. An uncertainty reported for any other value is not this field.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. An uncertainty reported for any other value is not this field.',
    'ic50': 'The half-inhibition concentration IC50 of the unlabelled competitor in a competition (displacement) experiment, as the passage reports it. A Ki or a KD is not this field.',
    'signal_noise': 'The reported noise of the polarization reads, in mP only: the standard deviation (or standard error) of replicate polarization readings of the free or the bound tracer, or of the wells at one concentration. An uncertainty of the KD or Ki is not this field, and a noise given in anisotropy r is unavailable with the reason unit_not_in_vocabulary.',
    'tracer_concentration': 'The concentration of the fluorescently labelled tracer (probe) held fixed in the assay.',
    'signal_minimum': 'The polarization or anisotropy of the free tracer (the lowest end of the titration curve), in mP or as an anisotropy r.',
    'signal_maximum': 'The polarization or anisotropy of the fully bound tracer (the plateau at the top of the titration curve), in mP or as an anisotropy r.',
    'total_intensity_change': 'The size of the relative change, in percent, of the tracer total fluorescence intensity when it binds (a positive number whether the intensity rises or falls).',
    'assay_volume': 'The volume of one assay sample as read, in uL or mL.',
    'incubation_time': 'How long the samples were incubated before the polarization was read.',
    'temperature': 'The temperature at which the samples were incubated or read.',
    'replicate_count': 'The number of replicate titrations the passage reports (a whole number).',
    SERIES: 'The titrant concentrations that were used, as a list of numbers in one unit (in a competition experiment, the competitor concentrations).',
    INTENSITY_DIRECTION: 'Whether the passage says the total fluorescence intensity of the tracer rose (increase) or fell (decrease, for example quenching) when it bound. The quote must itself say the direction; a size alone does not.',
    SERIES_KIND: 'Whether the listed concentrations are those of the partner titrated into the tracer (titrant) or those of the unlabelled competitor in a competition (competitor).',
    ASSAY_FORMAT: 'Whether the experiment titrated the tracer with its partner (direct titration) or displaced the tracer with an unlabelled competitor (competition).',
    SPREAD_KIND: 'What the reported KD or Ki uncertainty is.',
    FIT_MODEL: 'The model the passage says the binding curve was fitted with: a one-site hyperbolic 1:1 model, a Hill model, a quadratic (tight-binding) model, a competitive-binding model, or another one.',
    PLATE_TYPE: 'The kind of plate or cell the polarization was read in.',
    'tracer_at_or_below_kd': 'Whether the passage says the tracer concentration was at or below the KD (yes), or above the KD (no). The quote must itself compare the tracer concentration with the KD in words; a tracer concentration given alone, or one you compare with a KD from elsewhere, does not state this.',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when read, for example because the signal was stable over time (yes), or says it was not (no). An incubation time alone does not say this.',
    'tight_binding_considered': 'Whether the passage says tracer depletion or tight binding was considered or accounted for, for example by a quadratic fit (yes), or says it was not (no).',
    'intensity_change_checked': 'Whether the passage says a change of the tracer total fluorescence intensity on binding was checked or corrected for (yes), or says it was not (no).',
    'free_probe_baseline_measured': 'Whether the passage says the polarization of the free tracer (tracer alone in buffer) was measured as the baseline.',
    'nonspecific_binding_checked': 'Whether the passage says non-specific binding of the tracer (for example to an unrelated protein, or to the plate without the partner) was checked.',
    'unlabelled_competitor_displaces': 'Whether the passage says an excess of unlabelled ligand displaced the bound tracer (yes), or did not (no).',
    'surface_adsorption_prevented': 'Whether the passage says adsorption to tubes or plates was prevented, for example by detergent, carrier protein or non-binding plates (yes), or says that no such measure was taken (no). A passage that only mentions adsorption as a possible or actual loss of material says nothing about whether a preventive measure was taken: leave it unavailable.',
    'independent_titrations': 'Whether the passage says the replicates were independent titrations (separate dilution series or preparations).',
    'single_estimate_method': 'Whether the passage itself says that only one method (direct titration or competition) was used to estimate the affinity (yes), or says that both were used (no). A passage that merely reports one constant does not say this: leave it unavailable.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the assay format,
    the spread kind, the fit model, the plate type, the facts."""
    return (*QUANTITIES, SERIES, ASSAY_FORMAT, SPREAD_KIND, FIT_MODEL, PLATE_TYPE, INTENSITY_DIRECTION, SERIES_KIND, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(ASSAY_FORMATS)} if name == ASSAY_FORMAT else
             {'enum': list(SPREAD_KINDS)} if name == SPREAD_KIND else
             {'enum': list(FIT_MODELS)} if name == FIT_MODEL else
             {'enum': list(PLATE_TYPES)} if name == PLATE_TYPE else
             {'enum': list(INTENSITY_DIRECTIONS)} if name == INTENSITY_DIRECTION else
             {'enum': list(SERIES_KINDS)} if name == SERIES_KIND else
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
    """The FP record of ``literature_fp_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            ASSAY_FORMAT: choice(ASSAY_FORMAT), SPREAD_KIND: choice(SPREAD_KIND), FIT_MODEL: choice(FIT_MODEL), PLATE_TYPE: choice(PLATE_TYPE),
            INTENSITY_DIRECTION: choice(INTENSITY_DIRECTION), SERIES_KIND: choice(SERIES_KIND),
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
