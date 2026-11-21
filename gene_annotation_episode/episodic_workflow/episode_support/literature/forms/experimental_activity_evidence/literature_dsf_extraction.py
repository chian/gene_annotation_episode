"""The extraction of ONE thermal shift (DSF / nanoDSF) experiment (a protein is heated while its unfolding is followed with a dye such as SYPRO Orange or by its intrinsic fluorescence; the melting temperature Tm is read from the curve, alone and with a ligand; the ligand-induced shift of the Tm, delta Tm, shows binding only indirectly; mostly qualitative, occasionally an apparent KD from a series of ligand concentrations) from one
chunk of text, derived from the grader's input form (``literature_dsf_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a thermal shift is mostly qualitative, so the KD and its spread are fields that are mostly
unavailable, and the shift itself is a fact. The reported numbers are the Tm of the protein alone and with the ligand, their signed difference (the one number that may be zero or negative), the spread of the Tm,
the Tagg of nanoDSF, the protein concentration, the lowest and the highest ligand concentration, their number and the ligand concentration at which the shift was read, the heating rate and the number of independent experiments; the readout, the way the Tm was read and
the spread kind are choices; and the facts are the controls and the results of this method (a shift, whether the scatter of the Tm is over independent experiments, the protein alone, the ligand alone with the dye, a clean sigmoidal melt curve, a series of ligand concentrations, a shift that grows
with the ligand concentration, independent experiments). Every number must be above 0 except the signed difference delta Tm. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the protein, the ligand and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dsf_record import (
    EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, QUANTITIES, READOUTS, SIGNED_QUANTITIES, SPREAD_KINDS, SUPPORTS, TM_METHODS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
READOUT = 'readout'
TM_METHOD = 'tm_method'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('ligand_concentration_count', 'replicate_count')
CHOICES = {READOUT: READOUTS, TM_METHOD: TM_METHODS, SPREAD_KIND: SPREAD_KINDS}

MEANING = {
    'kd': 'The apparent dissociation constant of the protein and the ligand, as the passage reports it under the name KD, Kd (dissociation constant) or an apparent KD or EC50 from the thermal shift experiment described in the passage (a fit of the Tm, or of the shift of the Tm, against a series of ligand concentrations). A constant that the passage cites as a known or previously reported property, or one that comes from another method (for example ITC, SPR or fluorescence polarization, which a passage on thermal shift may also mention, or a constant the passage says was determined elsewhere or earlier), rather than from the thermal shift experiment described, is not stated: leave it unavailable. A ligand concentration at which a shift was seen is not this field. When the passage gives constants for several ligands or conditions without saying which one is the result, leave it unavailable.',
    'kd_spread': 'The reported uncertainty of the constant given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value (for example the plus-minus of a Tm) is not this field.',
    'tm_apo': 'The melting temperature Tm (the midpoint of the unfolding transition), in degrees Celsius, of the protein alone, that is without the ligand (the reference, control or apo protein, in the same buffer), as the passage gives it as one number (a value given with a plus-minus is the number before it). The Tm of the protein with the ligand, a Tm of another protein or of a mutant, and several Tm values of the protein alone without a statement of which one is the reference, are not this field. A temperature in another unit is not offered: leave it unavailable with the reason unit_not_in_vocabulary.',
    'tm_ligand': 'The melting temperature Tm, in degrees Celsius, of the protein in the presence of the ligand whose binding the passage is about, as the passage gives it as one number (a value given with a plus-minus is the number before it). The Tm of the protein alone, a Tm of another protein or of a mutant, and several Tm values with the ligand (for example at several ligand concentrations) without a statement of which one is the result, are not this field. A temperature in another unit: leave it unavailable with the reason unit_not_in_vocabulary.',
    'delta_tm': 'The thermal shift: the change of the melting temperature of the protein caused by the ligand (delta Tm, Tm with the ligand minus Tm without), in degrees Celsius, as the passage states it as one number; a rise is positive, a fall is negative, and a statement of no change is 0. Give the value only when the passage itself states the shift (for example a shift of 4.5 °C, or a stabilisation by 3 °C, or a destabilisation by 2 °C, which is -2); do not subtract two Tm values yourself. When the passage gives several shifts (several ligand concentrations or ligands) without saying which one is the result, leave it unavailable.',
    'tm_spread': 'The reported scatter of the Tm over replicates, as a standard deviation, in degrees Celsius, as the passage gives it as one number (for example the plus-minus after a Tm that the passage says is a standard deviation of replicates). A standard error, a range and a confidence interval are not this field, and a plus-minus whose kind the passage does not state is not this field either.',
    'tagg_apo': 'The aggregation onset temperature Tagg of the protein alone (nanoDSF, from the scattering), in degrees Celsius, as the passage gives it as one number. A Tm is not a Tagg.',
    'tagg_ligand': 'The aggregation onset temperature Tagg of the protein with the ligand (nanoDSF, from the scattering), in degrees Celsius, as the passage gives it as one number. A Tm is not a Tagg.',
    'protein_concentration': 'The concentration of the protein in the thermal shift measurement, as the passage gives it as a molar concentration. A concentration in mass per volume (for example mg/mL) is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. The concentration of the ligand, of the dye and of a stock solution are not this field.',
    'ligand_concentration_lowest': 'The lowest concentration of the ligand in the thermal shift measurement, as the passage gives it as a molar concentration (the smallest one when several are given). A concentration in mass per volume is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one ligand concentration does not state a lowest one.',
    'ligand_concentration_highest': 'The highest concentration of the ligand in the thermal shift measurement, as the passage gives it as a molar concentration (the largest one when several are given). A concentration in mass per volume is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one ligand concentration does not state a highest one.',
    'ligand_concentration_count': 'The number of different ligand concentrations at which the thermal shift was measured, as the passage gives it as a whole number (for example a dilution series of eight concentrations). The number of replicates, of wells and of ligands is not this field.',
    'shift_ligand_concentration': 'The concentration of the ligand at which the stated thermal shift (or the Tm with the ligand) was measured, as the passage gives it as a molar concentration (for example a shift of 4 degrees with 50 uM ligand). Give it only when the passage ties one ligand concentration to the shift or to the Tm with the ligand; when the shift is given for a whole series of concentrations without saying which one is the result, or when no concentration is tied to it, leave it unavailable. A concentration in mass per volume is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. The lowest and the highest concentration of a series are other fields, even when one of them is also the concentration of the shift.',
    'heating_rate': 'The rate at which the sample was heated in the thermal shift measurement, as the passage gives it in degrees Celsius per minute (a rate in kelvin per minute is the same number; a rate in another unit, for example per hour or per second, is not offered: leave it unavailable with the reason unit_not_in_vocabulary). A temperature range and a ramp that is not a rate are not this field.',
    'replicate_count': 'The number of independent experiments the passage reports for the thermal shift (separate experiments on separate days or preparations, or independent runs reported as replicates), as a whole number. Wells of one plate and ligand concentrations of one series are not this field.',
    READOUT: 'How the passage says the unfolding was followed: with the dye SYPRO Orange (dye based DSF), label free by the intrinsic tryptophan and tyrosine fluorescence of the protein (nanoDSF), or with another dye. A passage that does not name the readout does not state it.',
    TM_METHOD: 'How the passage says the Tm was read from the melt curve: by a fit of a Boltzmann (two-state sigmoid) function, from the maximum of the first derivative, or otherwise. A program name alone does not state it unless the passage also names the way. The words must name the way themselves: a fit of a Boltzmann (two-state sigmoid) function, or the maximum (peak) of the first derivative as the Tm. The words inflection point, melting peak, or a derivative plot with no statement that the Tm is its maximum, do not say which way was used: leave it unavailable.',
    SPREAD_KIND: 'What the uncertainty given in the kd_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    'thermal_shift_observed': 'Whether the passage says that the ligand raised the melting temperature of the protein, that is stabilised it (yes), or says that the melting temperature did not change with the ligand (no). A fall of the melting temperature is neither: leave this unavailable. A shift seen with another method, and the binding of the ligand shown only by another method, are not this fact.',
    'protein_alone_control_done': 'Whether the passage says that the protein was also measured without the ligand in the same buffer (with the same amount of the solvent of the ligand, for example DMSO, as a vehicle control) as the reference of the shift (yes), or says that it was not (no).',
    'ligand_alone_control_done': 'Whether the passage says that the ligand was also measured with the dye but without the protein (or that its own fluorescence, quenching or binding to the dye was checked) and gave no signal of its own (yes), or says that it gave a signal of its own (no). The measurement of the protein alone is not this fact.',
    'melt_curve_sigmoidal': 'Whether the passage says that the melt curves were clean, sigmoidal with one unfolding transition and no high initial fluorescence or aggregation artefact (yes), or says that they were not (for example several transitions, a high initial fluorescence, a noisy or incomplete curve) (no). The mention of a melt curve with no statement about its shape does not state it.',
    'ligand_titration_measured': 'Whether the passage says that the thermal shift was measured at several ligand concentrations, as a concentration series or titration (yes), or says that only one ligand concentration was used (no).',
    'shift_dose_dependent': 'Whether the passage says that the shift of the melting temperature grew with the ligand concentration, as a concentration dependent or dose dependent shift (yes), or says that it did not (no). A shift seen at one concentration does not state it.',
    'tm_spread_over_independent_experiments': 'Whether the passage says that the scatter of the Tm given in the tm_spread field is the scatter between independent experiments (separate experiments, days or preparations) (yes), or says that it is only the scatter between wells, technical replicates or repeated scans of one plate or one sample (no). A scatter whose basis the passage does not say does not state it.',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days or preparations) rather than wells or runs of one sample (yes), or says that they were not (no).',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (readout, Tm method, spread kind), the facts."""
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
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': {**_nullable({'enum': list(SUPPORTS)}), 'description': SUPPORT_MEANING}, 'reason': _nullable({'enum': list(REASONS)})})
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
    occurs exactly once in ``chunk``; a number is above 0 (the signed thermal shift may be zero or negative) and a stated value carries its unit
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one
    carries none. Returns ``answer``."""
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
        if name in QUANTITIES and name not in SIGNED_QUANTITIES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_dsf_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
