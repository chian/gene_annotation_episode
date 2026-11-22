"""The extracted record of ONE surface plasmon resonance (SPR) experiment.

This is what a leaf extraction holds for one SPR experiment, in the operand
shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component). A value the
source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('spr'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref,
               surface_ref, dataset_ref: each a string or None (unknown).
               The merger reads these to decide which experiments are not
               independent of each other.
quantities     kd, kd_steady_state, kon, koff, rmax, kd_spread, chi_squared,
               baseline_noise, immobilization_level, analyte_mass, ligand_mass,
               stoichiometry, replicate_count: one operand each.
               Units: kd/kd_steady_state/kd_spread nM, uM or mM; kon
               M^-1 s^-1; koff s^-1; rmax, immobilization_level RU;
               chi_squared RU^2; analyte_mass, ligand_mass kDa;
               stoichiometry dimensionless (analyte per immobilized
               partner); replicate_count count; baseline_noise RU (the
               stated baseline or instrument noise level, in the unit of the
               response, so that chi_squared can be read against its square).
               Fact kd_analysis (kinetic_fit, steady_state_fit, unknown): how
               the reported KD was obtained.
concentration_series
               operand whose 'value' is a list of analyte concentrations
               (unit nM, uM or mM), or None when not given.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval'
               or None. What kd_spread is.
fit_model      '1:1_langmuir', 'heterogeneous_ligand', 'bivalent_analyte',
               'two_state', 'steady_state_affinity', 'other' or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in
               FACTS below. binding_detected is the experiment's stated
               yes/no result (the passage says the two partners bound, or says
               they did not); no criterion reads it. It lets a result that
               is stated without a constant count (owner, 2026-11-22).
choice_support name -> support of each plain choice field (spread_kind, fit_model), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span
               behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries
'support', the extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or
fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the topic but is really
about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated
choice carry None. The grader does not judge it; the converter does. Rule for the constructors: they take ``support``
and default it to 'direct', and the default is only for forms built by tests that do not go through the extraction
(the extraction always passes the model's answer).
"""

VERSION = 'a105_spr_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'spr'
QUANTITIES = ('kd', 'kd_steady_state', 'kon', 'koff', 'rmax', 'kd_spread', 'chi_squared', 'baseline_noise', 'immobilization_level', 'analyte_mass', 'ligand_mass', 'stoichiometry', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1_langmuir', 'heterogeneous_ligand', 'bivalent_analyte', 'two_state', 'steady_state_affinity', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'reference_surface': YES_NO, 'double_referencing': YES_NO, 'mass_transport': ('checked_not_limited', 'checked_limited', 'not_checked', 'unknown'), 'baseline_drift': YES_NO, 'regeneration': YES_NO, 'independent_surfaces': YES_NO, 'immobilized_activity': YES_NO, 'analyte_bivalent_or_oligomeric': YES_NO, 'residuals_reported': YES_NO, 'single_estimate_method': YES_NO, 'kd_analysis': ('kinetic_fit', 'steady_state_fit', 'unknown'), 'binding_detected': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_steady_state': CONCENTRATION_UNITS, 'kon': ('M^-1 s^-1',), 'koff': ('s^-1',), 'rmax': ('RU',), 'kd_spread': CONCENTRATION_UNITS, 'chi_squared': ('RU^2',), 'baseline_noise': ('RU',), 'immobilization_level': ('RU',), 'analyte_mass': ('kDa',), 'ligand_mass': ('kDa',), 'stoichiometry': ('dimensionless',), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
