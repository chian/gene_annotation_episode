"""The extraction of ONE MST (microscale thermophoresis) binding experiment (in solution, in capillaries) from one chunk of
text, derived from the MST grader's input form (``literature_mst_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP and FRET extractions and private to MST: the grader's input form IS the
extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``,
``validate_answer()``, ``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations
(its quantities, units, facts and vocabularies). The model gives only the quote of each stated field; code finds the
UTF-8 byte span, and a quote that does not occur in the chunk exactly once is refused.

Differences from the other types that come from the form: the signal is the change of the normalized fluorescence in
per mille (``fnorm_amplitude``) with its signal-to-noise, the form has the detected partner's fixed concentration, the
excitation and the infrared laser power in percent, the F-hot time, the number of titrant concentrations, a Ki and an
EC50 beside the KD, an assay format (direct titration or competition), the readout signal (thermophoresis, temperature
jump or initial fluorescence), the capillary type, the label type and the MST fit models. Every number must be above 0.
Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the three preparation references (``preparations``) are references to
records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_record import (
    ASSAY_FORMATS, CAPILLARY_TYPES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, LABEL_TYPES, PREPARATION_KEYS, QUANTITIES, READOUT_SIGNALS, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
ASSAY_FORMAT = 'assay_format'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
READOUT_SIGNAL = 'readout_signal'
CAPILLARY_TYPE = 'capillary_type'
LABEL_TYPE = 'label_type'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'titration_point_count')
CHOICES = {ASSAY_FORMAT: ASSAY_FORMATS, SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS, READOUT_SIGNAL: READOUT_SIGNALS, CAPILLARY_TYPE: CAPILLARY_TYPES, LABEL_TYPE: LABEL_TYPES}

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the binding partners, as the passage reports it from the dose response of a direct titration (a half-maximal binding concentration is this field only if the passage reports it as the KD).',
    'ki': 'The inhibition constant Ki of an unlabelled ligand that displaces the detected partner, as the passage reports it from a competition (displacement) experiment.',
    'ec50': 'The half-maximal effective concentration EC50 of the titration, as the passage reports it under that name.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable unless the passage gives the uncertainty as one number. An uncertainty reported for any other value is not this field.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable unless the passage gives the uncertainty as one number. An uncertainty reported for any other value is not this field.',
    'labelled_concentration': 'The concentration at which the detected partner (the labelled partner, or the partner detected through its own fluorescence) is held fixed in the measurement, as the passage states it. It is not a concentration of the titrant series.',
    'fnorm_amplitude': 'The size of the change of the normalized fluorescence Fnorm (the MST signal) between the unbound and the bound state, in per mille, as a positive number, as the passage gives it. A signal-to-noise ratio is not this field.',
    'signal_to_noise': 'The signal-to-noise ratio of the titration curve (the size of the binding signal over the noise), as the passage gives it. An amplitude alone is not this field.',
    'led_power': 'The excitation (LED) power of the instrument in percent, as the passage gives it as a number. A word such as low, medium or high is not a number.',
    'ir_laser_power': 'The infrared laser power that heats the sample, called the MST power, in percent, as the passage gives it as a number. A word such as low, medium or high is not a number.',
    'fhot_time': 'The time after the infrared laser is switched on at which the hot fluorescence F-hot is read (the start of the F-hot window).',
    'titration_point_count': 'The number of titrant concentrations of the series (the number of dilution steps or capillaries of the titration), as a whole number, when the passage gives it as a number.',
    'incubation_time': 'How long the samples were incubated before the read.',
    'temperature': 'The temperature at which the samples were incubated or measured, as a number.',
    'replicate_count': 'The number of replicate titrations the passage reports (a whole number).',
    SERIES: 'The titrant concentrations that were used, as a list of numbers in one unit (in a competition experiment, the competitor concentrations). A range with a first and a last concentration, or a number of points with a top concentration, is not a list.',
    ASSAY_FORMAT: 'Whether the experiment titrated the detected partner with its partner (direct titration) or displaced the detected partner with an unlabelled competitor (competition).',
    SPREAD_KIND: 'What the reported KD or Ki uncertainty is.',
    FIT_MODEL: 'The model the passage says the binding curve was fitted with: a one-site hyperbolic 1:1 model, a Hill model, a quadratic (tight-binding) model, a competitive-binding model, or another one.',
    READOUT_SIGNAL: 'What the passage says the binding signal is: the thermophoresis (the normalized fluorescence read some seconds after the infrared laser is switched on), the temperature jump (read within the first second after it is switched on), or the change of the initial fluorescence before heating. The words normalized fluorescence or Fnorm alone do not say which.',
    CAPILLARY_TYPE: 'The kind of capillary the samples were drawn into, as the passage names it. If the passage names more than one kind for the same capillaries, it does not say which one: leave the field unavailable.',
    LABEL_TYPE: 'How the detected partner is detected: a dye attached covalently through an NHS ester, a dye carried by a tris-NTA group on a His tag, a fluorescent protein fused to the partner, the partner\'s own intrinsic fluorescence without any label (label-free), or another way.',
    'initial_fluorescence_checked': 'Whether the passage says the initial fluorescence (the fluorescence before the infrared laser heats the sample) was examined across the titration for a change caused by the titrant, for example with the SD-test or by plotting it against the titrant concentration.',
    'initial_fluorescence_consistent': 'Whether the passage says the initial fluorescence did not change with the titrant concentration (or only within the tolerance, or that a change was shown to be binding) (yes), or says that it did change, a quenching or an enhancement by the titrant (no). A statement that the check was made, without its result, does not say this.',
    'fluorescence_intensity_in_range': 'Whether the passage says the fluorescence intensity of the samples was within the range the instrument reads reliably (yes), or outside it (no).',
    'aggregation_or_adsorption_checked': 'Whether the passage says aggregation of a partner, or its adsorption to the capillary wall, was checked, for example with the capillary scan or the shape of the fluorescence peak.',
    'detergent_or_carrier_in_buffer': 'Whether the passage says the buffer contained a detergent or a carrier protein (yes), or says it did not (no).',
    'labelled_partner_at_or_below_kd': 'Whether the passage says the concentration of the detected partner held fixed was at or below the KD (yes), or above the KD (no).',
    'tight_binding_considered': 'Whether the passage says depletion of the titrant by tight binding was considered or accounted for, for example by a quadratic fit (yes), or says it was not (no).',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when read, for example because the signal was stable over time (yes), or says it was not (no). An incubation time alone does not say this, a statement of what an incubation was meant to achieve (for example to allow or to ensure equilibrium) is not a statement that equilibrium was reached, and neither does a measured equilibration time or half-life unless the passage says the samples were read after it.',
    'labelling_does_not_alter_binding': 'Whether the passage says the label (dye, tag or fluorescent protein) was tested and did not change the binding (yes), or says it did (no).',
    'nonspecific_binding_checked': 'Whether the passage says non-specific signal was checked, for example with a non-binding mutant, an unrelated protein, or a sample without one partner.',
    'independent_titrations': 'Whether the passage says the replicates were independent titrations (separate dilution series or preparations).',
    'single_estimate_method': 'Whether the passage itself says that only one method (direct titration or competition) was used to estimate the affinity (yes), or says that both were used (no). A passage that merely reports one constant does not say this: leave it unavailable.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices
    (assay format, spread kind, fit model, readout signal, capillary type, label type), the facts."""
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
    """The MST record of ``literature_mst_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
