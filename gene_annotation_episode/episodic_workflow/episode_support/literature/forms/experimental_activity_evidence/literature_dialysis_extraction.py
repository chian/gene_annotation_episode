"""The extraction of ONE equilibrium dialysis / ultrafiltration binding experiment (a ligand and a protein are separated from each other's bound form across a semipermeable membrane: equilibrium dialysis, rapid equilibrium dialysis, ultrafiltration, ultracentrifugation; the free and the total ligand concentration are measured; the result is a fraction bound or a percent unbound, or a KD and Bmax from a saturation series, or a Ki) from one
chunk of text, derived from the grader's input form (``literature_dialysis_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA and SEC extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a dialysis result is a fraction bound or a percent unbound at one or more concentrations, or a KD and a Bmax from a saturation series, or a Ki
(separate fields), so the KD, the Ki and the fractions are fields that are often unavailable and the binding itself is a fact. The reported numbers are the fractions (percent bound, percent unbound, fraction bound, fraction unbound),
the total, the free and the bound ligand concentration of a reading, the protein concentration, the lowest and the highest concentration of a saturation series (and the list of its concentrations and their number), the cutoff of the membrane, the time to
equilibrium, the temperature, the pH and the salt of the buffer, the volumes of the two chambers, the recovery, the adsorption to the membrane and the device, the volume shift, and the number of cells and of independent experiments;
the separation method, the device, the detection method, the spread kind and the fit model are choices; and the facts are the controls and the results of this method (binding observed, an equilibrium time course, a mass balance, adsorption
checked and corrected, the volume shift corrected, a stable ligand, a free ligand measured directly, a protein that stays behind the membrane, a buffer-only control, a protein concentration at or above the KD, independent experiments, one estimate method).
Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller, and the ligand, the protein and the dataset
(``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import (
    DETECTIONS, DEVICE_TYPES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SEPARATION_METHODS, SPREAD_KINDS, SUPPORTS, UNITS,
    VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SEPARATION = 'separation_method'
DEVICE = 'device_type'
DETECTION = 'detection'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'titration_point_count', 'technical_replicate_count')
CHOICES = {SEPARATION: SEPARATION_METHODS, DEVICE: DEVICE_TYPES, DETECTION: DETECTIONS, SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS}

MEANING = {
    'kd': 'The equilibrium dissociation constant of the protein and the ligand, as the passage reports it under the name KD or Kd (dissociation constant) from the separation experiment described in the passage (equilibrium dialysis, ultrafiltration or ultracentrifugation, for example from a series of ligand concentrations in which the bound ligand is plotted against the free ligand). A KD that the passage cites as a known or previously reported property, or that comes from another method (for example fluorescence, calorimetry or surface plasmon resonance) or from a simulation, rather than from the separation experiment described, is not stated: leave it unavailable. An association constant Ka (a reciprocal concentration), a Ki, an IC50 and a concentration at which binding was seen are not this field. When the passage gives KD values for several proteins, ligands or conditions without saying which one is the result, leave it unavailable.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'bmax': 'The maximal number of binding sites, as the passage reports it under the name Bmax (or maximal binding, binding capacity or number of binding sites per protein), either as a concentration or as moles of ligand per mole of protein (a ratio). A value that is not the number of sites (for example a percent bound, a protein concentration or a total ligand concentration) is not this field.',
    'ki': 'The inhibition constant Ki of an unlabelled competitor, as the passage reports it under that name from a competition experiment in which the competitor lowered the binding of the ligand in the separation experiment. An IC50 is not this field, a KD is not this field, and a value is not a Ki unless the passage calls it one. When the passage gives several Ki values for different competitors or conditions without saying which one is the result, leave it unavailable.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. It belongs to the Ki, not to the KD. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'percent_bound': 'The percent of the total ligand that was bound to the protein, as the passage gives it as a percent bound (or percent binding) for the experiment described. A percent unbound, a fraction, a percent of specific binding, a percent of inhibition, a percent you would have to calculate, and percent bound values for several concentrations or conditions without saying which one is the result are not this field.',
    'percent_bound_spread': 'The standard deviation of the percent bound given in the percent_bound field, between the cells or the independent experiments, in percentage points, when the passage gives it as one number for the experiment described. A standard error, a confidence interval, a range, the spread of any other value (the KD, the recovery) and the spread of a percent unbound are not this field.',
    'detection_lloq': 'The lower limit of quantification (LLOQ, the lowest concentration the detector measures with acceptable accuracy and precision) of the method that measured the ligand concentration in the chambers, as the passage gives it as a molar concentration (a limit in mass per volume is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it). A limit of detection (LOD), the lowest point of a calibration curve that the passage does not call a limit of quantification, and the limit of a method that measured the protein are not this field.',
    'percent_unbound': 'The percent of the total ligand that was free (not bound to the protein), as the passage gives it as a percent unbound or percent free for the experiment described. A percent bound, a fraction, a percent you would have to calculate, and percent unbound values for several concentrations or conditions without saying which one is the result are not this field.',
    'fraction_bound': 'The fraction of the total ligand that was bound to the protein, as the passage gives it as a number between 0 and 1 under a name such as fraction bound. A percent is not offered here (answer in the percent field), and neither is a fraction you would have to calculate or a fraction given for several conditions without saying which one is the result.',
    'fraction_unbound': 'The fraction of the total ligand that was free (not bound to the protein), as the passage gives it as a number between 0 and 1 under a name such as fraction unbound or fu. A percent is not offered here (answer in the percent field), and neither is a fraction you would have to calculate or a fraction given for several conditions without saying which one is the result.',
    'ligand_total_concentration': 'The total concentration of the ligand (free plus bound) at which one reading of the fraction bound or of the free ligand was made, as the passage gives it as a molar concentration for the experiment described. A series of concentrations, the lowest or the highest of a series, a concentration of the protein and a concentration given for several readings without saying which one is the result are not this field.',
    'free_ligand_concentration': 'The concentration of the free ligand that was measured on the side of the membrane without protein, as the passage gives it as a molar concentration for one reading. A free concentration you would have to calculate as the total minus the bound, and a total concentration, are not this field.',
    'bound_ligand_concentration': 'The concentration of the ligand that was bound to the protein, as the passage gives it as one molar concentration for one reading. A bound concentration you would have to calculate as the total minus the free, and a total or a free concentration, are not this field.',
    'protein_concentration': 'The concentration of the protein in the chamber that held it, as the passage gives it as a molar concentration (a concentration in mass per volume, for example mg/mL, is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it). The concentration of a stock solution before it was diluted into the chamber, a concentration of the ligand and protein concentrations given for several experiments without saying which one is the result are not this field.',
    'ligand_range_lowest': 'The lowest total ligand concentration of a series of concentrations (a saturation series or a titration), when the passage gives the series as a range with a first and a last concentration or names its lowest concentration. A ligand-to-protein ratio is not a concentration.',
    'ligand_range_highest': 'The highest total ligand concentration of a series of concentrations (a saturation series or a titration), when the passage gives the series as a range with a first and a last concentration or names its highest concentration. A ligand-to-protein ratio is not a concentration.',
    'titration_point_count': 'The number of ligand concentrations of the series (or of competitor concentrations of a competition), as a whole number, when the passage gives it as a number. The number of cells of one experiment and a list of ratios that you would have to count are not this field.',
    'membrane_cutoff': 'The molecular weight cutoff of the semipermeable membrane (the size above which molecules are retained), as the passage gives it in kilodaltons (a 10K MWCO membrane is 10 kDa). The mass of the protein and the mass of the ligand are not this field.',
    'equilibration_time': 'How long the dialysis cell (or the ultrafiltration or the ultracentrifugation) was kept before the free and the bound ligand were measured, that is the time allowed to reach equilibrium, as the passage gives it as one time. A time of a sampling series, of an incubation of the protein before the dialysis, of the hydration of the membrane, of a centrifugation, of a chromatographic run, and a range of times that were only tried, are not this field.',
    'run_temperature': 'The temperature at which the dialysis (or the ultrafiltration or the ultracentrifugation) was run, as a number. A passage that says only room temperature does not state it, and the temperature of a storage or of the detector is not this field.',
    'buffer_ph': 'The pH of the buffer in which the protein and the ligand were dialysed, as a number. The pH of another solution (a stock, a mobile phase of a chromatography) is not this field.',
    'salt_concentration': 'The concentration of monovalent salt (for example NaCl or KCl) in the buffer of the dialysis, as the passage gives it in millimolar or molar. A buffer named only as phosphate-buffered saline with no concentration, a conductivity, the concentration of a buffer substance such as phosphate or Tris, and the salt of a protein storage buffer are not this field.',
    'protein_chamber_volume': 'The volume of the solution in the chamber (cup, cassette, cell, well or filter) that held the protein, as the passage gives it in microlitres or millilitres: the final volume in that chamber, not the volume of the protein stock that was added to it. The volume of the other chamber and the total volume of the device are not this field.',
    'buffer_chamber_volume': 'The volume of the solution on the other side of the membrane from the protein (the buffer, the dialysate or the external solution), as the passage gives it in microlitres or millilitres. The volume of the chamber with the protein is not this field.',
    'recovery': 'The percent of the total ligand put into the device that was recovered from both chambers together (the recovery or mass balance), as the passage gives it as one percent for the experiment described. A range of recoveries, a recovery given for several conditions without saying which one is the result, a recovery of a sample preparation or of an analytical method, and a statement that there was no loss without a number are not this field.',
    'membrane_adsorption': 'The percent of the ligand that bound to the membrane and the device (nonspecific binding of the ligand to the membrane, the cup or the tube), as the passage gives it as one percent. A statement that no binding or no sorption was seen, with no number, is not this field.',
    'volume_shift': 'The percent by which the volume of the protein chamber changed during the dialysis (volume shift or volume gain), as the passage gives it as one percent. A statement that the volume was or was not corrected, with no number, is not this field.',
    'technical_replicate_count': 'The number of cells, cups, wells or tubes of one experiment per condition (duplicates, triplicates), as a whole number when the passage gives it as a count of that kind. Independent experiments are not this field.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days or preparations), as a whole number. Duplicate or triplicate cells of one experiment and ligand concentrations of one series are not this field.',
    SERIES: 'The total ligand concentrations of a saturation series that were used, as a list of numbers in one unit. A range with a first and a last concentration, a number of points with a top concentration, and a list of ligand-to-protein ratios are not a list of concentrations.',
    SEPARATION: 'How the free ligand was separated from the bound ligand, as the passage states it: equilibrium dialysis (a dialysis cell, cup, cassette or tubing), rapid equilibrium dialysis (the RED device or a rapid equilibrium dialysis plate), ultrafiltration (a centrifugal filter that presses the free ligand through a membrane) or ultracentrifugation. A filtration or a column used only to prepare a sample is not this field. When the passage describes several separation methods without saying which one the result comes from, leave it unavailable.',
    DEVICE: 'The device or cell that held the sample, as the passage names it: a RED device (rapid equilibrium dialysis device), a Dianorm cell, a dialysis cassette (for example a Slide-A-Lyzer cassette), a dialysis cup or mini dialysis unit, a centrifugal spin filter, or another device. A device that the passage mentions only for another purpose is not this field.',
    DETECTION: 'How the concentration of the ligand was measured in the samples of the chambers, as the passage states it: liquid scintillation counting (radioactivity), LC-MS/MS (liquid chromatography with tandem mass spectrometry), fluorescence, absorbance (UV-Vis spectrophotometry), or another method. A method used to measure the protein concentration is not this field. When the passage names several, give the one on which the ligand concentrations of this experiment were read. The quote must be the words that name the method, copied exactly from the passage; the name of a method usually occurs several times in a passage, so take a quote that includes the distinctive words of the one sentence that names it, and check that it occurs once.',
    SPREAD_KIND: 'What the uncertainty given in the kd_spread or the ki_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    FIT_MODEL: 'The model the passage names in words as the one the binding data were fitted with: a one-site (single-site) binding model, a two-site binding model, a model with a free Hill slope, or another named model. A linearised plot (a double-reciprocal plot or a Scatchard plot) is a way of plotting, not a model name: leave it unavailable. A model the passage only calls simple, and an equation that is only written out, are not this field: do not work out the model from the form of an equation. A name that joins two model names names more than one model: leave it unavailable.',
    'binding_detected': 'Whether the passage says that the protein bound the ligand in the experiment described: a measurable fraction of the ligand was bound, the free ligand concentration was lower than the total concentration, or binding was observed (yes), or says that no binding was seen, for example that the concentrations on the two sides were equal (no). A passage that only describes the method, with no result, does not state it, and neither does a binding that the passage shows only with another method or reports as known from earlier work.',
    'equilibrium_time_course_shown': 'Whether the passage says that equilibrium was shown to be reached, for example by sampling the chambers over time until the concentrations stopped changing, or by a time course of the free ligand (yes), or says that equilibrium was not reached (no). A statement that the cell was kept for a time to reach equilibrium, or a time alone, is what was meant to be done and does not say that equilibrium was shown: it does not state this fact.',
    'recovery_checked': 'Whether the passage says that the recovery (mass balance) of the ligand from both chambers was measured or checked (yes), or says that it was not (no). The recovery of a sample preparation or of an analytical method is not this fact.',
    'adsorption_checked_and_corrected': 'Whether the passage says that the binding of the ligand to the membrane or the device was measured (for example with a control without protein) and corrected for or found to be negligible (yes), or says that it was not checked (no). A passage that only says the device was made of a low-binding material does not state it.',
    'volume_shift_corrected': 'Whether the passage says that a Donnan effect, an osmotic flow or a volume shift between the chambers was measured and corrected, or was found to be negligible (yes), or says that it was not corrected (no). A passage that does not mention a volume shift does not state this.',
    'ligand_stable': 'Whether the passage says that the ligand was stable over the incubation, with no degradation (for example checked by incubating it without protein and measuring the intact ligand) (yes), or says that it degraded (no). A stability said only in general of the compound, with no statement about this incubation, is not this fact.',
    'free_ligand_measured_directly': 'Whether the passage says that the free ligand concentration was measured directly in the chamber without protein (the dialysate or the filtrate) (yes), or says that it was inferred or calculated from the total and the bound (no). A passage that gives measurements of the ligand in samples without saying from which chamber does not state it.',
    'protein_retained': 'Whether the passage says that the protein did not pass through the membrane (the membrane was impermeable to the protein, the protein was retained, no protein was found in the dialysate) (yes), or says that the protein leaked through it (no). A membrane cutoff alone, with no statement about the protein, is not this fact.',
    'buffer_only_control_equal': 'Whether the passage says that a control with the ligand and no protein (buffer only) showed equal ligand concentrations in the two chambers, so that the ligand crossed the membrane freely (yes), or says that it did not equalise (no). A control that is only said to have been prepared, with no statement of its result, is not this fact.',
    'protein_at_or_above_kd': 'Whether the passage says that the protein concentration was at or above the KD, or high enough for a measurable fraction of the ligand to be bound (yes), or says that it was far below the KD (no). Two concentrations given with no statement that relates them do not state it.',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days or preparations) rather than cells of one experiment (yes), or says that they were not (no).',
    'single_estimate_method': 'Whether the passage says that the KD, or the binding of the protein and the ligand, was determined by this separation experiment only (yes), or says that the KD or the binding was also determined by another method (no). Another method that the passage mentions for a different purpose (for example a simulation, or a comparison with values from the literature) is not this fact, and a passage that reports no KD and says nothing about other methods does not state it. A sentence that only describes the method that was used does not say that no other method was used: yes needs the passage to say that this method alone was used.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices
    (separation method, device, detection, spread kind, fit model), the facts."""
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
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit
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
    """The record of ``literature_dialysis_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
