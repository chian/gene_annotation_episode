"""The extraction of ONE analytical ultracentrifugation (AUC: sedimentation velocity and sedimentation equilibrium) experiment (a protein, or a mixture of two proteins, is spun in an analytical ultracentrifuge; in velocity runs a complex sediments faster than either component alone and the fit gives its molar mass; in equilibrium runs a global fit of several concentrations and speeds gives the mass, the stoichiometry and, for a reversible association, the KD; mostly qualitative or semi-quantitative, occasionally a KD from a concentration series) from one
chunk of text, derived from the grader's input form (``literature_auc_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC and dialysis extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: an AUC is mostly qualitative or semi-quantitative, so the KD and its spread are fields that are mostly
unavailable, and the complex itself is a fact. The reported numbers are the sedimentation coefficients (of the complex and of the larger and the smaller component alone, in S), the frictional
ratio, the molar mass of the complex from the fit and the mass it should have, the stoichiometry, the lowest and the highest loading concentration and their number, the rmsd of the fit, the rotor
speed, the temperature and the number of independent experiments; the run mode, the analysis model, the detection and the spread kind are choices; and the facts are the controls and the results of this method (a complex,
each component alone, each component homogeneous, a series of loading concentrations, a reversible association, a mass that matches the complex, random residuals, a corrected buffer density and viscosity, equilibrium reached, several speeds, a
non-binding control, independent experiments, one estimate method). Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the two components and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_auc_record import (
    ANALYSIS_MODELS, DETECTIONS, EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, QUANTITIES, RUN_MODES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
RUN_MODE = 'run_mode'
ANALYSIS_MODEL = 'analysis_model'
DETECTION = 'detection'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('concentration_count', 'replicate_count')
CHOICES = {RUN_MODE: RUN_MODES, ANALYSIS_MODEL: ANALYSIS_MODELS, DETECTION: DETECTIONS, SPREAD_KIND: SPREAD_KINDS}

MEANING = {
    'kd': 'The equilibrium dissociation constant of the two proteins, as the passage reports it under the name KD or Kd (dissociation constant) from the analytical ultracentrifugation experiment described in the passage (a series of loading concentrations in a velocity run, or a global fit of a sedimentation equilibrium run). A KD that the passage cites as a known or previously reported property of the proteins, or one that comes from another method (for example fluorescence polarization, ITC or SPR, which a passage on ultracentrifugation may also mention, or a KD the passage says was determined elsewhere or earlier), rather than from the ultracentrifugation experiment described, is not stated: leave it unavailable. A concentration at which a complex was seen, or that the passage says was above the KD, is not this field. When the passage gives KD values for several pairs or conditions without saying which one is the result, leave it unavailable.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value (for example the plus-minus of a sedimentation coefficient or of a mass) is not this field.',
    'complex_sedimentation_coefficient': 'The sedimentation coefficient, in Svedberg units (S), of the peak or species that the passage says is the complex of the two proteins (the peak of the mixture at the larger s, as the passage gives it as one number; a value given with a plus-minus is the number before it). The sedimentation coefficient of a component alone, of an unbound component in the mixture, and of a species that the passage does not call the complex are not this field. A sedimentation coefficient in another unit is not offered: leave it unavailable with the reason unit_not_in_vocabulary.',
    'component_sedimentation_coefficient_larger': 'The sedimentation coefficient, in Svedberg units (S), of the component that is the larger of the two proteins (larger by its mass, as the passage states it or makes plain) when it is run alone, as the passage gives it as one number. The sedimentation coefficient of the mixture, and several values for the same component (for example a monomer and a dimer, or several conditions) without saying which one is the result, are not this field.',
    'component_sedimentation_coefficient_smaller': 'The sedimentation coefficient, in Svedberg units (S), of the component that is the smaller of the two proteins (smaller by its mass, as the passage states it or makes plain) when it is run alone, as the passage gives it as one number. The sedimentation coefficient of the mixture, and several values for the same component without saying which one is the result, are not this field.',
    'frictional_ratio': 'The frictional ratio f/f0 that the passage reports for the species or the complex (fitted or assumed in the analysis), as one number. A ratio of masses, a stoichiometry and a ratio of concentrations are not this field.',
    'complex_mass_measured': 'The molar mass of the complex species measured by the ultracentrifugation experiment (the mass of the peak of the mixture from the c(s) fit, from a Lamm equation fit, or from the equilibrium fit), in kilodaltons, as the passage gives it for the complex of the two proteins (a value given with a plus-minus is the number before it). A mass of a component alone, the mass of an unbound species in the mixture, a mass read from the sequence, and a mass the complex is expected to have are not this field. When the passage gives several masses of the mixture under different conditions without saying which one is the result, leave it unavailable.',
    'complex_mass_theoretical': 'The molar mass, in kilodaltons, that the complex should have (the theoretical or calculated mass of the complex, the sum of the masses of its components for the stated composition, or the mass the passage says a 1:1 complex would have), as the passage gives it as one number for the complex. The theoretical mass of one component, and the masses of the components of a complex that you would have to add up yourself, are not this field.',
    'component_mass_larger': 'The molar mass, in kilodaltons, of the component that is the larger of the two proteins, when it is run alone as a single (monomeric) species, as the passage gives it as one number (calculated from the sequence, or measured alone in the experiment; a value given with a plus-minus is the number before it). The mass of the complex, the mass of a dimer or aggregate of a component, and several masses of the same component without a statement of which one is the monomer, are not this field.',
    'component_mass_smaller': 'The molar mass, in kilodaltons, of the component that is the smaller of the two proteins, when it is run alone as a single (monomeric) species, as the passage gives it as one number (calculated from the sequence, or measured alone in the experiment; a value given with a plus-minus is the number before it). The mass of the complex, the mass of a dimer or aggregate of a component, and several masses of the same component without a statement of which one is the monomer, are not this field.',
    'stoichiometry_ratio': 'The molar ratio of the two components in the complex, as the passage states it for the complex (first named component over second named: a 1:1 complex or a heterodimer made of one of each is 1, a 2:1 complex is 2, a 1:2 complex is 0.5), as a number. The ratio in which the proteins were mixed is not the stoichiometry of the complex, and neither is an oligomeric state of one protein alone (a homodimer). A passage that gives no ratio and names no composition does not state it.',
    'loaded_concentration_lowest': 'The lowest loading concentration of the series, as the passage gives it as a molar concentration (the concentration of the protein or of each protein in the loaded sample; the smallest one when several are given). A concentration in mass per volume (for example mg/mL) or as an absorbance is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one loading concentration does not state a lowest one.',
    'loaded_concentration_highest': 'The highest loading concentration of the series, as the passage gives it as a molar concentration (the concentration of the protein or of each protein in the loaded sample; the largest one when several are given). A concentration in mass per volume (for example mg/mL) or as an absorbance is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one loading concentration does not state a highest one.',
    'concentration_count': 'The number of different loading concentrations at which the experiment was run, as the passage gives it as a whole number (for example a dilution series of five concentrations). The number of speeds, of scans, of samples and of replicates is not this field.',
    'fit_rmsd': 'The root mean square deviation (rmsd) of the fit of the experiment, as the passage gives it as one number in absorbance units (AU, OD) or in fringes. A reduced chi-square, a percent and a p-value are not this field.',
    'rotor_speed': 'The rotor speed at which the experiment was run, as the passage gives it in revolutions per minute (rpm); a speed in g or in another unit is not offered: leave it unavailable with the reason unit_not_in_vocabulary. When several speeds were used, give none of them unless the passage names one as the speed of the result.',
    'run_temperature': 'The temperature at which the ultracentrifuge was run, as a number. A passage that says only room temperature or the cold room does not state it, and the temperature of a pre-incubation or of a storage is not this field.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days or preparations, or independent runs reported as replicates), as a whole number. Scans of one cell and loading concentrations of one series are not this field.',
    RUN_MODE: 'The kind of ultracentrifugation run the passage describes: sedimentation velocity (a high speed, a sedimentation coefficient distribution c(s), a Lamm equation fit; SV-AUC), sedimentation equilibrium (a lower speed until sedimentation and diffusion balance; SE-AUC), or both when the passage reports both for the same experiment. A passage that does not name the run does not state it.',
    ANALYSIS_MODEL: 'How the passage says the data were analysed: a continuous sedimentation coefficient distribution c(s), a Lamm equation fit of the species, a global fit of the equilibrium gradients, or another model. A program name alone (for example SEDFIT or SEDPHAT) does not state it unless the passage also names the model. A passage that says the data were analysed with a continuous distribution c(s) (or fitted to a c(s) distribution model) names the model: state c_of_s.',
    DETECTION: 'The optical detection that the passage says was used: absorbance (a wavelength), interference (Rayleigh interference, fringes), fluorescence, or another detection. A passage that does not name a detection does not state it.',
    SPREAD_KIND: 'What the uncertainty given in the kd_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    'complex_detected': 'Whether the passage says that a complex of the two proteins was seen: a peak or species of the mixture at a larger sedimentation coefficient (or mass) than either component alone, or a complex species that the fit assigns to the two proteins together (yes), or says that no such species was seen and the mixture sedimented as the separate components (no). A faster species that the passage ascribes to aggregation, and an interaction that the passage shows only with another method, are not this fact.',
    'components_run_alone': 'Whether the passage says that each of the two components was also run alone under the same conditions, so that the sedimentation of the mixture is compared with that of each component (yes), or says that they were not (no).',
    'components_monodisperse': 'Whether the passage says that each component alone sedimented as a single species (monomeric, homogeneous, no aggregate and no self-association) (yes), or says that a component alone was a mixture of species, such as a monomer and a dimer, or aggregated (no). A component alone with a measured s and no statement of its homogeneity does not state it.',
    'concentration_series_measured': 'Whether the passage says that the experiment was run at several loading concentrations, as a concentration series or titration (yes), or says that only one concentration was used (no).',
    'reversible_association_shown': 'Whether the passage says that the sedimentation (the weight-average s, the peak areas or the mass) changed with the loading concentration as it does for a reversible association, or that a global fit of the concentrations held for a reversible model (yes), or says that it did not (no). A complex seen at one concentration does not state it.',
    'mass_matches_complex': 'Whether the passage says that the molar mass of the complex species from the experiment agrees with the mass expected for the complex (a heterodimer, a 1:1 complex), as consistent, in agreement or matching the combined masses (yes), or says that it does not agree (no). A mass given with no statement of what it is compared with does not state it.',
    'fit_residuals_random': 'Whether the passage says that the residuals of the fit were random, small or showed no systematic deviation (yes), or says that they showed systematic deviations (no). The mention of a residual plot or of a good fit with no statement about the residuals does not state it.',
    'buffer_density_viscosity_corrected': 'Whether the passage says that the buffer density and viscosity (and the partial specific volume of the proteins) were calculated or measured and used in the analysis, for example with SEDNTERP (yes), or says that they were not (no).',
    'equilibrium_reached_shown': 'Whether the passage says that a sedimentation equilibrium run reached equilibrium (successive scans were the same, they overlaid) (yes), or says that equilibrium was not reached (no). A velocity run has no equilibrium: leave this unavailable.',
    'multiple_speeds_used': 'Whether the passage says that a sedimentation equilibrium run was done at several rotor speeds that were fitted together (yes), or says that only one speed was used (no). A velocity run: leave this unavailable.',
    'non_binding_control_done': 'Whether the passage says that a control in which one partner was replaced by a non-binding mutant or by an unrelated protein did not form the complex (yes), or says that it did (no). Running each component alone is not this fact.',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days or preparations) rather than scans of one sample (yes), or says that they were not (no).',
    'single_estimate_method': 'Whether the passage says that the KD, or the binding of the two proteins, was determined by analytical ultracentrifugation only (yes), or says that the KD or the binding of these two proteins was also determined by another method (no). Another method that the passage mentions for a different purpose (for example to locate the interface) is not this fact, and a passage that reports no KD and says nothing about other methods for the binding does not state it. A sentence that only describes the method that was used does not say that no other method was used: yes needs the passage to say that this method alone was used.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (run mode, analysis model, detection, spread kind), the facts."""
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
        if name in QUANTITIES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_auc_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
