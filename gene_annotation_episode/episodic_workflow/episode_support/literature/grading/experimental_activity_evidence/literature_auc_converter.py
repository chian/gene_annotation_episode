"""AUC converter: turns the AUC grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_auc.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that an AUC
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has a KD (from a concentration series: the weight-average s against the concentration in a velocity run, or a global equilibrium fit). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the KD in nM (point operand, measurement key auc_kd). The caveats of the method (a KD needs loading concentrations on both sides of it; a fast
                    reversible association gives one reaction boundary) are not changed in the number, they are judged by the criteria (concentration_series,
                    concentration_range, reversibility, stoichiometry, fit_quality) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no KD (a complex species, its s, its mass and its stoichiometry are shown). Then, exactly as the pull-down, EMSA, SEC and dialysis converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the s nor the molar mass is
put into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'sedimentation_shift_percent'}):
  statement                    'interaction_detected' (a complex is stated), 'interaction_not_detected' (no complex is stated) or 'interaction_not_stated'
  support_refs                 the spans of the fact that states it (empty when not stated)
  sedimentation_shift_percent  how many percent larger the s of the complex is than the s of the larger component alone, or None
The merger (literature_binding_merger.py) reads 'qualitative_effect' to take such a result into the row's interpretations and its own qualitative block; the
merger's contract is not changed.

Criteria mapping (AUC criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              components_alone + component_homogeneity + non_binding_control (the controls that show the faster species is a complex of these two
                              proteins and not a component alone, an aggregate or a self-association)
binding_regime                concentration_series + concentration_range + reversibility + equilibrium_reached + multiple_speeds (the association is followed over
                              concentrations on both sides of the KD, it is reversible, and an equilibrium run reached equilibrium and was fitted at several speeds)
binding_parameter_definition  complex_observed + sedimentation_shift + mass + stoichiometry (what the response is: a complex, its s, its mass and its composition)
calibration_applicability     fit_quality + buffer_correction (the fit describes the data; the buffer density and viscosity turn the measurement into a standard s and a mass)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison (a percent, a ratio, a deviation) is supported with a degree of 1.0 up to its full-agreement limit, the degree falling
linearly to 0 at its zero-agreement limit, and conflicting (no degree) at or beyond that limit: sedimentation_shift (shift at least SHIFT_FULL_AGREEMENT_PERCENT, none below SHIFT_ZERO_AGREEMENT_PERCENT),
mass (absolute deviation at most MASS_FULL_AGREEMENT_PERCENT, none from MASS_ZERO_AGREEMENT_PERCENT), stoichiometry (distance from 1 at most STOICHIOMETRY_FULL_AGREEMENT, none from
STOICHIOMETRY_ZERO_AGREEMENT), concentration_range (the lowest loading concentration over the KD at most LOW_OVER_KD_FULL_AGREEMENT, none from LOW_OVER_KD_ZERO_AGREEMENT; the highest over the KD at least
HIGH_OVER_KD_FULL_AGREEMENT, none up to HIGH_OVER_KD_ZERO_AGREEMENT; the weaker of the two decides) and fit_quality (rmsd at most FIT_RMSD_FULL_AGREEMENT, none from FIT_RMSD_ZERO_AGREEMENT, per unit).
Count minimums get no degree: concentration_series is supported at MIN_CONCENTRATIONS loading concentrations or more, else conflicting; replicates are conflicting below MIN_REPLICATES, else supported
when the independence is yes, else unknown. A sheet criterion that is supported carries the smallest degree of its members that have one (the
sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree (the
mass criterion's degree from the deviation, for example); direct leaves it unchanged. Support never changes a status. variance_correspondence takes
the weakest support of the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is
not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, recovery) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first component,
immobilized_preparation_ref = the second component, surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_auc_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_auc_converted_v1'
CRITERIA_MAP = {'binding_controls': ('components_alone', 'component_homogeneity', 'non_binding_control'), 'binding_regime': ('concentration_series', 'concentration_range', 'reversibility', 'equilibrium_reached', 'multiple_speeds'), 'binding_parameter_definition': ('complex_observed', 'sedimentation_shift', 'mass', 'stoichiometry'), 'calibration_applicability': ('fit_quality', 'buffer_correction'), 'sampling_basis': ('replicates',)}
SHIFT_FULL_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: smallest increase (percent) of the s of the complex over the s of the larger component alone that the sheet takes as a clear complex peak; binding of a partner a fifth of the mass of the larger component raises s by about 10 percent, and the s of one species is reproducible to 1 to 2 percent.
SHIFT_ZERO_AGREEMENT_PERCENT = 2.0  # EXPERT_REVIEW: increase (percent) at or below which the s of the complex cannot be told from the larger component alone (the reproducibility of s); a smaller or negative shift is conflicting, in between the degree falls linearly.
MASS_FULL_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: largest absolute deviation (percent) of the molar mass of the complex from the AUC fit from the mass the complex should have that the sheet takes as agreement; the mass from c(s) or from a global equilibrium fit is accurate to about 5 to 10 percent.
MASS_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: absolute deviation (percent) from which the sheet takes the mass as disagreeing (conflicting); half the mass or less, or 1.5 times or more, is a different species; the degree falls linearly in between.
STOICHIOMETRY_FULL_AGREEMENT = 0.1  # EXPERT_REVIEW: largest distance of the stated stoichiometry from 1 (1:1) at which a KD is the one-site constant (a ratio is not read more closely than 10 percent).
STOICHIOMETRY_ZERO_AGREEMENT = 0.5  # EXPERT_REVIEW: distance of the stated stoichiometry from 1 from which the sheet takes the complex as not 1:1 (a ratio of 2:1 or 1:2 is 1 or 0.5 away, halfway to it is 1.5 or 0.5); the degree falls linearly in between.
MIN_CONCENTRATIONS = 3  # EXPERT_REVIEW: fewest loading concentrations that show the concentration dependence of a reversible association (one gives a mass or an s, two a single slope; three show curvature and a plateau).
LOW_OVER_KD_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest ratio of the lowest loading concentration to the KD at which the series defines the free-component end of the isotherm.
LOW_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the lowest loading concentration to the KD from which the series does not reach below the KD (the complex is already formed in the whole series): conflicting; the degree falls linearly in between.
HIGH_OVER_KD_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest ratio of the highest loading concentration to the KD at which the series reaches the saturated end of the isotherm.
HIGH_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the highest loading concentration to the KD up to which the series does not reach above the KD (the complex is not saturated anywhere): conflicting; the degree falls linearly in between.
FIT_RMSD_FULL_AGREEMENT = {'AU': 0.005, 'fringes': 0.003}  # EXPERT_REVIEW: largest rmsd of the fit taken as noise-limited, per unit (the noise of the absorbance optics is about 0.005 absorbance units, that of the interference optics about 0.003 fringes).
FIT_RMSD_ZERO_AGREEMENT = {'AU': 0.02, 'fringes': 0.012}  # EXPERT_REVIEW: rmsd of the fit, per unit, from which the sheet takes the fit as not describing the data (four times the noise): conflicting; the degree falls linearly in between.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); scans of one cell do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'an_auc_run_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_auc_complex_species_is_not_an_attribution_fraction', 'total_signal': 'an_auc_complex_species_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_auc_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_auc_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero):
    """1.0 at ``full`` (or beyond it), falling linearly to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``."""
    if (value - zero) * (full - zero) <= 0:
        return None
    return min(1.0, (value - zero) / (full - zero))


def _graded(refs, *degrees):
    """The verdict of a continuous comparison: conflicting where any degree is None, else supported with the smallest degree."""
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _judge_shift(native):
    return _graded(native['shift_refs'], _degree(native['shift_percent'], SHIFT_FULL_AGREEMENT_PERCENT, SHIFT_ZERO_AGREEMENT_PERCENT))


def _judge_mass(native):
    return _graded(native['mass_support_refs'], _degree(abs(native['mass_deviation_percent']), MASS_FULL_AGREEMENT_PERCENT, MASS_ZERO_AGREEMENT_PERCENT))


def _judge_stoichiometry(native):
    return _graded(native['stoichiometry_refs'], _degree(abs(native['stoichiometry_ratio'] - 1), STOICHIOMETRY_FULL_AGREEMENT, STOICHIOMETRY_ZERO_AGREEMENT))


def _judge_concentrations(native):
    return _verdict('supported' if native['concentration_count'] >= MIN_CONCENTRATIONS else 'conflicting', native['concentration_count_refs'])


def _judge_range(native):
    return _graded(native['range_refs'], _degree(native['low_over_kd'], LOW_OVER_KD_FULL_AGREEMENT, LOW_OVER_KD_ZERO_AGREEMENT), _degree(native['high_over_kd'], HIGH_OVER_KD_FULL_AGREEMENT, HIGH_OVER_KD_ZERO_AGREEMENT))


def _judge_fit(native):
    unit = native['fit_rmsd_unit']
    return _graded(native['fit_refs'], _degree(native['fit_rmsd'], FIT_RMSD_FULL_AGREEMENT[unit], FIT_RMSD_ZERO_AGREEMENT[unit]))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('sedimentation_shift', 'sedimentation_shift_recorded_for_the_sheet'): _judge_shift, ('mass', 'mass_deviation_recorded_for_the_sheet'): _judge_mass,
          ('stoichiometry', 'stoichiometry_recorded_for_the_sheet'): _judge_stoichiometry, ('concentration_series', 'concentration_count_recorded_for_the_sheet'): _judge_concentrations,
          ('concentration_range', 'concentration_range_recorded_for_the_sheet'): _judge_range, ('fit_quality', 'fit_rmsd_recorded_for_the_sheet'): _judge_fit,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if native['kd_nM'] is None:
        return None, 'no_effect_to_carry_a_variance', []
    spread = native['quantities']['kd_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'kd_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_auc(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'auc_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'auc_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    if not quantitative:
        null_components['effect'] = 'qualitative_assay_reports_no_binding_constant'
        null_components['effect_variance'] = 'qualitative_assay_reports_no_binding_constant'
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [apply_support(_criterion(graded, m), native['support'][m]) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
    if variance is not None:
        variance_fields = ['kd_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['component_a_preparation_ref'], 'immobilized_preparation_ref': preparations['component_b_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'auc', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities']['kd']['support']      # the support class of the KD operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'sedimentation_shift_percent': native['shift_percent']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['complex_observed'][0]      # the support class of the fact complex_detected, the one field the statement is derived from
    return converted
