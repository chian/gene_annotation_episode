"""The extracted record of ONE isothermal titration calorimetry (ITC) experiment.

What a leaf extraction holds for one ITC titration (or one set of replicate
titrations reported as one result), in the same operand shape as the SPR
record and the existing A105 assay grading inputs (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component). A value the
source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted. The plain constructors point,
unavailable and fact are the SPR record module's; they are shared because
they only build operands.

Record fields
-------------
version, experiment_type ('itc'), experiment_ref, source_ref, assertion_ref
preparations   syringe_preparation_ref (the titrant, the ligand in the
               syringe), cell_preparation_ref (the partner in the cell),
               dataset_ref: each a string or None (unknown). The converter
               hands them to the merger as its dependence keys.
quantities     kd, kd_spread, stoichiometry (the fitted n), expected_stoichiometry
               (the n the complex is expected to have, from the source),
               enthalpy, entropy, temperature, cell_concentration,
               syringe_concentration, injection_count, replicate_count,
               final_molar_ratio (the ligand : partner molar ratio reached at
               the end of the titration).
               Units: kd/kd_spread/cell_concentration/syringe_concentration
               nM, uM or mM; stoichiometry and expected_stoichiometry
               dimensionless; enthalpy kJ/mol or kcal/mol; entropy
               J/mol/K, cal/mol/K or kJ/mol/K (the entropy dS itself, not
               T dS); temperature K or C; injection_count and
               replicate_count count; final_molar_ratio dimensionless.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval'
               or None. What kd_spread is.
fit_model      'one_set_of_sites', 'two_sets_of_sites', 'sequential_sites',
               'competitive', 'other' or None.
titration_mode 'incremental' (a series of discrete injections),
               'single_injection' (one long injection) or 'continuous'
               (continuous injection or slow ramp), or None. With a
               single-injection or continuous titration the injection count
               does not measure how well the curve is sampled.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in
               FACTS below. No fact holds text: a controlled answer only.
               binding_detected is the experiment's stated yes/no result (the passage
               says the two partners bound, or says they did not); no criterion reads
               it. It lets a result stated without a constant count (owner, 2026-11-22).
choice_support name -> support of each plain choice field (spread_kind, fit_model, titration_mode), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span
               behind each reference the record cites. The buffer, the
               baseline treatment and the active-fraction method are kept as
               these spans; the facts hold only the controlled answers.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import SUPPORTS, fact, point, unavailable   # support: see literature_spr_record (every stated value carries 'support'; the constructors default it to 'direct' for forms built outside the extraction)

VERSION = 'a105_itc_record'
EXPERIMENT_TYPE = 'itc'
QUANTITIES = ('kd', 'kd_spread', 'stoichiometry', 'expected_stoichiometry', 'enthalpy', 'entropy', 'temperature', 'cell_concentration', 'syringe_concentration', 'injection_count', 'replicate_count', 'final_molar_ratio')
PREPARATION_KEYS = ('syringe_preparation_ref', 'cell_preparation_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
TITRATION_MODES = ('incremental', 'single_injection', 'continuous')
FIT_MODELS = ('one_set_of_sites', 'two_sets_of_sites', 'sequential_sites', 'competitive', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
BUFFER_MATCHING = ('dialysed_together', 'matched_by_stated_procedure', 'not_matched', 'unknown')
FACTS = {'dilution_control_performed': YES_NO, 'dilution_control_subtracted': YES_NO, 'baseline_corrected': YES_NO, 'concentrations_determined': YES_NO, 'active_fraction_determined': YES_NO, 'binding_sites_heterogeneous': YES_NO, 'residuals_reported': YES_NO, 'n_fitted_freely': YES_NO, 'buffer_matching': BUFFER_MATCHING, 'temperature_controlled': YES_NO, 'independent_titrations': YES_NO, 'enthalpy_buffer_ionization_corrected': YES_NO, 'binding_detected': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry (the docstring above lists them in words).
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'stoichiometry': ('dimensionless',), 'expected_stoichiometry': ('dimensionless',), 'enthalpy': ('kJ/mol', 'kcal/mol'), 'entropy': ('J/mol/K', 'cal/mol/K', 'kJ/mol/K'), 'temperature': ('K', 'C'), 'cell_concentration': CONCENTRATION_UNITS, 'syringe_concentration': CONCENTRATION_UNITS, 'injection_count': ('count',), 'replicate_count': ('count',), 'final_molar_ratio': ('dimensionless',)}
