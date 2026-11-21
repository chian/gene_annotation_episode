"""The extracted record of ONE analytical ultracentrifugation (AUC) experiment: a protein, or a mixture of two proteins, is spun in an analytical ultracentrifuge (an optical cell, read by absorbance, interference or fluorescence) and the movement of the sample in the centrifugal field is followed. Two kinds of run belong to it. SEDIMENTATION VELOCITY (SV): a high speed moves the protein as a boundary; the sedimentation coefficient s (in Svedberg, S) of each species is read from a distribution c(s) (SEDFIT) or a fit of the Lamm equation, and a complex of two proteins sediments faster than either component alone (a peak, or a reaction boundary, at a larger s, with a molar mass from the fit). SEDIMENTATION EQUILIBRIUM (SE): a lower speed lets sedimentation and diffusion balance; the concentration gradient at equilibrium, at several loading concentrations and several speeds, is fitted globally to give the molar mass and, for a reversible association, the dissociation constant KD and the stoichiometry. The result is mostly QUALITATIVE or semi-quantitative (a complex peak, its s, its mass, its stoichiometry); a KD comes from a series of loading concentrations (the weight-average s against the concentration in SV, or the global fit in SE).

What a leaf extraction holds for one AUC experiment: the proteins (alone and mixed), each at one or more loading concentrations in a buffer (its density and viscosity, needed to turn the measured s into a standard one), spun at a speed (rpm) and a temperature, read by absorbance, interference or fluorescence, and analysed with a model (c(s), a Lamm-equation fit, a global equilibrium fit); the fit has residuals and a root mean square deviation (rmsd, in absorbance units or in fringes). The control of the experiment is each component alone under the same conditions (its s and its homogeneity), a non-binding mutant in place of one partner, and a concentration series.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC and dialysis records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What AUC shows and what can go wrong is what the form keeps. The s of a complex must be read against each component alone under the same conditions (a shift of the peak, or a new peak); a reaction boundary of a fast, reversible association is one peak at a weight-average s that moves with the loading concentration, not a resolved complex, so the proof of a reversible association is a series of concentrations, and a KD needs concentrations on both sides of it (below the KD the complex is not formed, above it the protein is saturated). The molar mass from c(s) is as good as the frictional ratio that the model assumes. An aggregate or a self-association of a component (a monomer-dimer mixture) is taken for a complex, so each component must be shown homogeneous alone. A sedimentation equilibrium is reached only after a time that depends on the speed and the column height (successive scans must overlay), and one speed does not separate mass from non-ideality: several speeds and concentrations are fitted globally. The buffer density and viscosity, and the partial specific volume of the protein, are needed for the standard s and for the mass. The residuals of the fit must be random and small.

Record fields
-------------
version, experiment_type ('auc'), experiment_ref, source_ref, assertion_ref
preparations   component_a_preparation_ref, component_b_preparation_ref (the two proteins that are mixed, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (component a as the analyte key, component b as the other partner; there is no surface).
quantities     kd, kd_spread, complex_sedimentation_coefficient, component_sedimentation_coefficient_larger, component_sedimentation_coefficient_smaller, frictional_ratio,
               complex_mass_measured, complex_mass_theoretical, stoichiometry_ratio, loaded_concentration_lowest, loaded_concentration_highest, concentration_count, fit_rmsd,
               rotor_speed, run_temperature, replicate_count: one operand each.
               Units: kd and kd_spread pM, nM, uM or mM (the dissociation constant from the concentration series and its spread); complex_sedimentation_coefficient,
               component_sedimentation_coefficient_larger and component_sedimentation_coefficient_smaller 'S' (Svedberg: the sedimentation coefficient of the complex peak and of the
               larger and the smaller component run alone); frictional_ratio 'ratio' (f/f0); complex_mass_measured and complex_mass_theoretical 'kDa' (the molar mass of the complex
               from the AUC fit, and the mass the complex should have); stoichiometry_ratio 'ratio' (the molar ratio of the components in the complex, first named over second named);
               loaded_concentration_lowest and loaded_concentration_highest pM, nM, uM or mM (the lowest and the highest loading concentration of the series); concentration_count 'count'
               (the number of loading concentrations); fit_rmsd 'AU' (absorbance units) or 'fringes' (the root mean square deviation of the fit); rotor_speed 'rpm';
               run_temperature 'C' or 'K'; replicate_count 'count'.
run_mode       'sedimentation_velocity', 'sedimentation_equilibrium', 'velocity_and_equilibrium' or None: the kind of run the result is from.
analysis_model 'c_of_s', 'lamm_equation_fit', 'global_equilibrium_fit', 'other' or None: how the data were analysed. Kept in the record for the reviewer.
detection      'absorbance', 'interference', 'fluorescence', 'other' or None. Kept in the record for the reviewer.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (run_mode, analysis_model, detection, spread_kind), None when the choice is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's
fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (the quote states it only by
implication), 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand and
an 'unknown' fact carry support None. The grader keeps it and does not judge it; the converter does. Rule for the constructors: they take
``support`` and default it to 'direct' only so that forms built by tests, which do not go through the extraction, are direct; the extraction always
passes the model's own value.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record

SUPPORTS = ('direct', 'implied', 'about_something_else')


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': support}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    return {**literature_spr_record.fact(answer, refs), 'support': None if answer == 'unknown' else support}


VERSION = 'a105_auc_record_v1'
EXPERIMENT_TYPE = 'auc'
QUANTITIES = ('kd', 'kd_spread', 'complex_sedimentation_coefficient', 'component_sedimentation_coefficient_larger', 'component_sedimentation_coefficient_smaller', 'frictional_ratio', 'complex_mass_measured', 'complex_mass_theoretical', 'stoichiometry_ratio', 'loaded_concentration_lowest', 'loaded_concentration_highest', 'concentration_count', 'fit_rmsd', 'rotor_speed', 'run_temperature', 'replicate_count')
PREPARATION_KEYS = ('component_a_preparation_ref', 'component_b_preparation_ref', 'dataset_ref')
RUN_MODES = ('sedimentation_velocity', 'sedimentation_equilibrium', 'velocity_and_equilibrium')
ANALYSIS_MODELS = ('c_of_s', 'lamm_equation_fit', 'global_equilibrium_fit', 'other')
DETECTIONS = ('absorbance', 'interference', 'fluorescence', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'complex_detected': YES_NO, 'components_run_alone': YES_NO, 'components_monodisperse': YES_NO, 'concentration_series_measured': YES_NO, 'reversible_association_shown': YES_NO, 'mass_matches_complex': YES_NO, 'fit_residuals_random': YES_NO, 'buffer_density_viscosity_corrected': YES_NO, 'equilibrium_reached_shown': YES_NO, 'multiple_speeds_used': YES_NO, 'non_binding_control_done': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'complex_sedimentation_coefficient': ('S',), 'component_sedimentation_coefficient_larger': ('S',), 'component_sedimentation_coefficient_smaller': ('S',), 'frictional_ratio': ('ratio',), 'complex_mass_measured': ('kDa',), 'complex_mass_theoretical': ('kDa',), 'stoichiometry_ratio': ('ratio',), 'loaded_concentration_lowest': CONCENTRATION_UNITS, 'loaded_concentration_highest': CONCENTRATION_UNITS, 'concentration_count': ('count',), 'fit_rmsd': ('AU', 'fringes'), 'rotor_speed': ('rpm',), 'run_temperature': ('C', 'K'), 'replicate_count': ('count',)}
