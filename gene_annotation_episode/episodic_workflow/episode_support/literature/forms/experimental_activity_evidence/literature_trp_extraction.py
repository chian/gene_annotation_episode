"""The extraction of ONE intrinsic tryptophan (and tyrosine) fluorescence quenching / enhancement binding titration from one chunk
of text, derived from the grader's input form (``literature_trp_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET and MST extractions and private to this method: the grader's input form IS the
extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: the signal is the fractional change of the protein's own
fluorescence (``fluorescence_change`` in percent, with its direction), the excitation and the emission wavelengths and an
emission shift are fields, the protein is the partner held at a constant concentration, the ligand's absorbance and the added
volume are fields (the inner-filter effect and the dilution), a Stern-Volmer constant Ksv is a field kept apart from the KD, and
the facts are the controls of this method (inner-filter correction, dilution correction, buffer blank, ligand-only control,
non-binding protein control, free-tryptophan or NATA control, saturation, static quenching, photobleaching). Every number must
be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the three preparation references (``preparations``) are references to records,
which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_record import (
    CHANGE_DIRECTIONS, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SHIFT_DIRECTIONS, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
CHANGE_DIRECTION = 'change_direction'
SHIFT_DIRECTION = 'emission_shift_direction'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'titration_point_count')
CHOICES = {SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS, CHANGE_DIRECTION: CHANGE_DIRECTIONS, SHIFT_DIRECTION: SHIFT_DIRECTIONS}

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the protein and the ligand, as the passage reports it from the saturable change of the protein\'s fluorescence with the ligand concentration. A Stern-Volmer constant, a quenching constant or a half-maximal concentration is not this field unless the passage reports it as the KD.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable unless the passage gives the uncertainty as one number. An uncertainty reported for any other value is not this field.',
    'ksv': 'The Stern-Volmer quenching constant Ksv (the slope of the Stern-Volmer plot, a quenching efficiency), as the passage gives it, in inverse molar units. It is not a dissociation constant and is never put in the kd field.',
    'protein_concentration': 'The concentration at which the protein whose fluorescence is read is held constant in the measurement, as the passage states it. It is not a concentration of the ligand series.',
    'excitation_wavelength': 'The wavelength at which the sample was excited, as one number in nm, as the passage gives it.',
    'emission_wavelength': 'The single wavelength at which the emission was read for the titration (the emission maximum, or the fixed wavelength used for the fit), as one number in nm. A scanned range with a first and a last wavelength is not this field.',
    'emission_shift': 'The size of the shift of the emission maximum caused by the ligand, in nm, as a positive number, as the passage gives it as a number. Its direction is not part of this field.',
    'fluorescence_change': 'The size of the change of the protein\'s fluorescence between the free protein and the saturated complex (or at the highest ligand concentration), in percent, as a positive number, as the passage gives it. Its direction is not part of this field.',
    'ligand_absorbance': 'The absorbance of the ligand (or of the sample with the ligand) at the excitation or at the emission wavelength, at the highest ligand concentration used, as a number in absorbance units, as the passage gives it. If the passage gives several, the largest. A statement that the absorbance was small, negligible or low is not a number.',
    'added_volume_fraction': 'The total volume of ligand solution added during the titration, as a percentage of the starting volume of the protein sample, as the passage gives it as a number.',
    'titration_point_count': 'The number of ligand concentrations of the series (the number of additions or of samples of the titration), as a whole number, when the passage gives it as a number.',
    'concentration_lowest': 'The lowest ligand concentration of the titration, as one number, when the passage states the series as a range or gives its lowest concentration (for example "from 5 nM to 500 nM"). A range that starts at 0 (a blank without ligand) has no lowest concentration above 0: leave it unavailable. It is not a protein concentration.',
    'concentration_highest': 'The highest ligand concentration of the titration, as one number, when the passage states the series as a range or gives its highest concentration (for example "up to 1000 nM" or "0-1000 nM"). It is not a protein concentration.',
    'incubation_time': 'How long the sample was left after each addition (or in each sample) before the fluorescence was read.',
    'temperature': 'The temperature at which the fluorescence was measured, as a number.',
    'replicate_count': 'The number of replicate titrations the passage reports (a whole number).',
    SERIES: 'The ligand concentrations that were used, as a list of numbers in one unit. A range with a first and a last concentration, or a number of points with a top concentration, is not a list: give its ends in concentration_lowest and concentration_highest.',
    SPREAD_KIND: 'What the reported KD uncertainty is.',
    FIT_MODEL: 'The model the passage names in words as the one the titration curve was fitted with: a one-site hyperbolic 1:1 model, a Hill model, a quadratic (tight-binding) model, the Stern-Volmer equation, or another named one. An equation that is only written out, without the passage naming the model, is not this field: do not work out the model from the form of an equation.',
    CHANGE_DIRECTION: 'Whether the passage reports, as a result, that the ligand lowered the protein\'s fluorescence (quenching) or raised it (enhancement). The name of the assay or of the method (for example a quenching assay) is not such a report.',
    SHIFT_DIRECTION: 'Whether the passage says the emission maximum moved to shorter wavelengths (blue shift) or to longer wavelengths (red shift) on binding. A statement that the emission maximum did not move is neither.',
    'inner_filter_corrected': 'Whether the passage says the fluorescence was corrected for the inner-filter effect, that is for absorption of the excitation or emission light by the ligand (yes), for example with an absorbance-based formula or with a titration of free tryptophan or N-acetyl-tryptophanamide, or says it was not corrected (no).',
    'ligand_absorbance_negligible': 'Whether the passage says the ligand did not absorb, or absorbed only negligibly, at the excitation and emission wavelengths (yes), or says it did absorb there (no).',
    'dilution_corrected': 'Whether the passage says the fluorescence was corrected for the dilution of the protein by the added ligand (yes), or says it was not (no).',
    'buffer_blank_subtracted': 'Whether the passage says the fluorescence of the buffer (the blank) was subtracted (yes), or says it was not (no).',
    'ligand_only_control_measured': 'Whether the passage says the fluorescence of the ligand alone, without the protein, was measured under the same conditions (yes), or says it was not (no). A statement about the ligand and the protein together is not this.',
    'nonbinding_control_done': 'Whether the passage says the ligand was also tested on a protein that does not bind it, or on a variant of the protein that does not bind it, to show the signal is specific (yes), or says it was not (no).',
    'trp_analogue_control_done': 'Whether the passage says a free tryptophan, a free tyrosine or N-acetyl-tryptophanamide (NATA) solution was titrated with the ligand as a control (yes), or says it was not (no).',
    'signal_localised_to_binding_site': 'Whether the passage says the fluorescence change comes from a tryptophan (or tyrosine) at or near the binding site, for example because a variant lacking that residue gives no change or because the residue lies in the site (yes), or says it does not (no).',
    'signal_saturates': 'Whether the passage says the fluorescence change levelled off (saturated) at high ligand concentration (yes), or says it did not saturate (no).',
    'quenching_is_static': 'Whether the passage says the quenching is static, that is due to the formation of a complex (yes), or says it is dynamic or collisional (no).',
    'photobleaching_checked': 'Whether the passage says photobleaching of the protein during the measurement was checked or was avoided, for example with a time scan or a protein-only control titrated with buffer (yes), or says it was not (no).',
    'protein_at_or_below_kd': 'Whether the passage says the protein concentration held constant was at or below the KD (yes), or above the KD (no).',
    'tight_binding_considered': 'Whether the passage itself says depletion of the free ligand by tight binding was considered or accounted for, for example by a quadratic fit (yes), or says it was not (no). An equation that contains total concentrations is not such a statement: do not work it out from the form of an equation.',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when read, for example because the signal was stable over time (yes), or says it was not (no). An incubation time alone does not say this, and a statement of what an incubation was meant to achieve (for example to allow or to ensure equilibrium) is not a statement that equilibrium was reached.',
    'independent_titrations': 'Whether the passage says the replicates were independent titrations (separate dilution series or preparations).',
    'single_estimate_method': 'Whether the passage itself says that the affinity was estimated only by this fluorescence titration (yes), or says that another method was also used for it (no). A passage that merely reports one constant does not say this: leave it unavailable.',
    'binding_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the experiment showed that the two partners bind (a change of the intrinsic tryptophan fluorescence on titration (quenching or a shift of the emission), a reported binding constant, or the plain statement that one binds the other as measured by tryptophan fluorescence quenching); no when it says the experiment showed no binding (no change of the intrinsic fluorescence on titration, "did not bind", "no detectable binding"). A passage that only describes how the experiment was done, or names the method without its result, does not state this.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices
    (spread kind, fit model, change direction, emission shift direction), the facts."""
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
    """The record of ``literature_trp_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
