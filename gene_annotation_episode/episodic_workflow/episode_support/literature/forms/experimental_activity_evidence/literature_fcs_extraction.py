"""The extraction of ONE fluorescence correlation spectroscopy (FCS, or dual-colour FCCS) binding titration from one chunk
of text, derived from the grader's input form (``literature_fcs_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST and Trp extractions and private to this method: the grader's input form IS the
extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused. Each stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well
its quote supports it): required when stated, None when unavailable; the record keeps it and the converter turns it into a degree.

Differences from the other types that come from the form: the signal is the diffusion of the labelled partner (the free and the
bound diffusion times and coefficients, the fraction bound at the top of the titration, the brightness), the labelled partner is
the one held at a constant low concentration and its particle number in the confocal volume is a field, the calibration of the
confocal volume (the structure parameter) and the mass ratio of the complex are fields, the model of the correlation curves and
the readout (a diffusion time, a diffusion coefficient, a brightness or the cross-correlation of two colours) are choices, and the
facts are the controls of this method (volume calibration, triplet state, fixing of the free time, brightness, cross-talk,
background, aggregates, photobleaching and saturation, surface adsorption, labelling, a non-binding control). Every number must
be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the three preparation references (``preparations``) are references to records,
which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import (
    CHOICE_FIELDS, DIFFUSION_MODELS, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, READOUT_SIGNALS, SPREAD_KINDS, UNITS, VERSION, fact, point, unavailable)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
DIFFUSION_MODEL = 'diffusion_model'
READOUT_SIGNAL = 'readout_signal'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'titration_point_count', 'measurement_repeat_count')
CHOICES = {SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS, DIFFUSION_MODEL: DIFFUSION_MODELS, READOUT_SIGNAL: READOUT_SIGNALS}

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the two partners, as the passage reports it from the titration. A diffusion time, a half-maximal concentration or a value the passage does not call the dissociation constant is not this field.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'labelled_concentration': 'The concentration at which the fluorescently labelled partner, the one whose diffusion is measured, is held constant in the measurement, as the passage states it. It is not a concentration of the titrated partner.',
    'free_diffusion_time': 'The diffusion time of the free labelled partner (measured alone, or fully unbound), as the passage gives it. An apparent diffusion time of a mixture, or a diffusion time of the complex, is not this field.',
    'free_diffusion_time_spread': 'The reported uncertainty of the diffusion time of the free labelled partner given in the free_diffusion_time field (a standard deviation, standard error or the \u00b1 value of repeated measurements), as one number in a unit of time, when the passage gives it. An uncertainty reported for any other value (the KD, the diffusion time of the complex, an apparent time) is not this field.',
    'bound_diffusion_time': 'The diffusion time of the labelled partner in its fully bound complex (at a saturating concentration of the titrated partner), as the passage gives it. An apparent diffusion time of a mixture, or a diffusion time of the free labelled partner, is not this field.',
    'free_diffusion_coefficient': 'The diffusion coefficient of the free labelled partner (measured alone, or fully unbound), as the passage gives it. A diffusion coefficient of the complex is not this field.',
    'bound_diffusion_coefficient': 'The diffusion coefficient of the labelled partner in its fully bound complex (at a saturating concentration of the titrated partner), as the passage gives it. A diffusion coefficient of the free labelled partner is not this field.',
    'fraction_bound_maximum': 'The largest fraction of the labelled partner that is reported bound, at the highest concentration of the titrated partner, as a percentage, as the passage gives it as a number. A statement that the fraction bound grows or saturates is not a number.',
    'particle_number': 'The average number of fluorescent molecules in the confocal detection volume (the number of particles N, or the inverse of the correlation amplitude), as the passage gives it as a number.',
    'detection_volume': 'The effective confocal detection volume, as the passage gives it as a number in femtolitres (a volume given in cubic micrometres is the same number in femtolitres). A beam waist or a radius is not a volume: do not calculate it.',
    'structure_parameter': 'The structure parameter of the confocal detection volume (the ratio of its axial to its lateral radius, also called kappa or S), as the passage gives it as a number.',
    'mass_ratio': 'The ratio of the molecular mass of the complex to the molecular mass of the free labelled partner, only when the passage itself gives that ratio as a number. Two masses given separately, or a statement that one partner is larger than the other, are not this field: do not calculate it.',
    'brightness': 'The molecular brightness, the number of photon counts per second per molecule, as the passage gives it for the labelled partner. A total count rate of a sample is not this field.',
    'laser_power': 'The laser power at the sample, as the passage gives it in a unit of power. A power given as a percentage of the maximum is not this field.',
    'measurement_time': 'The duration of one measurement (one acquisition) of one sample, as the passage gives it. A total over several repetitions is not this field.',
    'measurement_repeat_count': 'The number of repeated measurements of the same sample (a whole number) that were taken and averaged or compared, when the passage gives it as a number. The number of independent titrations is not this field.',
    'titration_point_count': 'The number of concentrations of the titrated partner of the series (the number of samples of the titration), as a whole number, when the passage gives it as a number.',
    'incubation_time': 'How long the samples were left after mixing before the measurement.',
    'temperature': 'The temperature at which the measurements were made, as a number.',
    'replicate_count': 'The number of replicate titrations the passage reports (a whole number).',
    SERIES: 'The concentrations of the titrated partner that were used, as a list of numbers in one unit. A range with a first and a last concentration, or a number of points with a top concentration, is not a list.',
    SPREAD_KIND: 'What the reported KD uncertainty is.',
    FIT_MODEL: 'The model the passage names in words as the one the binding curve (the fraction bound or the signal against the titrant concentration) was fitted with: a one-site 1:1 model, a Hill model, a quadratic (tight-binding) model, or another named one. A model the passage only calls simple, an equation that is only written out, or the model of the correlation curves is not this field: do not work out the model from the form of an equation.',
    DIFFUSION_MODEL: 'The model the passage names in words as the one the correlation curves were fitted with: one diffusing component (a single species, which gives an apparent time), two components (a free and a bound species), anomalous diffusion, or another named one. The model of the binding curve is not this field.',
    READOUT_SIGNAL: 'What the passage says changes with the titrated partner and is used to read the binding: the diffusion time (or the fraction bound calculated from it), the diffusion coefficient, the molecular brightness, or the amplitude of the cross-correlation of two colours.',
    'confocal_volume_calibrated': 'Whether the passage says the confocal detection volume was calibrated, for example with a reference dye of known diffusion coefficient (yes), or says it was not (no).',
    'triplet_state_modelled': 'Whether the passage says the triplet state (or other photophysical dark state) of the dye was included in the fit of the correlation curves (yes), or says it was not (no).',
    'free_diffusion_time_fixed': 'Whether the passage says that in the fit of two species the diffusion time of the free labelled partner was fixed to the value measured for the free labelled partner (yes), or says it was fitted freely (no).',
    'brightness_change_accounted': 'Whether the passage says that a difference between the brightness of the complex and of the free labelled partner was measured and taken into account in the fraction bound (yes), or says it was not (no).',
    'crosstalk_corrected': 'Whether the passage says the spectral cross-talk (bleed-through) between the two colour channels was corrected in a cross-correlation measurement (yes), or says it was not (no).',
    'background_corrected': 'Whether the passage says the background (dark counts, buffer or uncorrelated light) was measured and corrected for in the correlation curves (yes), or says it was not (no).',
    'aggregates_checked': 'Whether the passage says aggregates or bright outliers in the fluorescence trace were checked for, removed or excluded (yes), or says they were not (no).',
    'photobleaching_or_saturation_checked': 'Whether the passage says photobleaching or saturation of the dye was checked or avoided, for example with a series of laser powers or with a stable count rate over time (yes), or says it was not (no). Stating the laser power used is not such a statement.',
    'surface_adsorption_prevented': 'Whether the passage says adsorption of the molecules to the chamber surface was prevented, for example with a passivated chamber, a carrier protein or a detergent (yes), or says it was not (no).',
    'labelling_does_not_alter_binding': 'Whether the passage says the fluorescent label does not alter the binding, for example because a labelled and an unlabelled partner gave the same affinity (yes), or says it does (no).',
    'nonbinding_control_done': 'Whether the passage says the labelled partner was also exposed to a partner that does not bind it, or a non-binding variant of the labelled partner was exposed to the titrated one, and no change was seen (yes), or says it was not (no).',
    'labelled_partner_at_or_below_kd': 'Whether the passage says the concentration of the labelled partner held constant was at or below the KD (yes), or above the KD (no).',
    'tight_binding_considered': 'Whether the passage itself says depletion of the free titrated partner by tight binding was considered or accounted for, for example by a quadratic fit (yes), or says it was not (no). An equation that contains total concentrations is not such a statement: do not work it out from the form of an equation.',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when measured, for example because the signal was stable over time (yes), or says it was not (no). An incubation time alone does not say this, and a statement of what an incubation was meant to achieve (for example to allow or to ensure equilibrium) is not a statement that equilibrium was reached.',
    'independent_titrations': 'Whether the passage says the replicates were independent titrations (separate dilution series or preparations).',
    'single_estimate_method': 'Whether the passage itself says that the affinity was estimated only by this correlation spectroscopy titration (yes), or says that another method was also used for it (no). A passage that merely reports one constant does not say this: leave it unavailable.',
    'binding_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the experiment showed that the two partners bind (a longer diffusion time of the labelled partner on adding the other, a cross-correlation between the two labelled partners, a reported binding constant, or the plain statement that one binds the other as measured by FCS); no when it says the experiment showed no binding (no change of the diffusion time or no cross-correlation, "did not bind", "no detectable binding"). A passage that only describes how the experiment was done, or names the method without its result, does not state this.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices
    (spread kind, fit model, diffusion model, readout signal), the facts."""
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
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': _nullable({'enum': list(SUPPORTS)}),
                       'reason': _nullable({'enum': list(REASONS)})})
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
    where the field has one. Returns ``answer``."""
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
            _refuse(name, 'stated_has_value_unit_quote_support_and_no_reason')
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
    """The record of ``literature_fcs_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            'choice_support': {name: answer[name]['support'] if answer[name]['status'] == 'stated' else None for name in CHOICE_FIELDS},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
