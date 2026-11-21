"""DSF converter: turns the DSF grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_dsf.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a thermal shift
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (from a series of ligand concentrations: the Tm or its shift against the concentration). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key dsf_kd, native component 'kd'; it is thermal-shift-derived, which the measurement key states). The caveats of the method (the shift shows binding only
                    indirectly; a KD needs ligand concentrations on both sides of it) are not changed in the number, they are judged by the criteria (concentration_series, concentration_range,
                    dose_dependence, shift_size, shift_over_spread) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no KD (the shift of the Tm at one or a few ligand concentrations). Then, exactly as the pull-down, EMSA, SEC, dialysis and AUC converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and the shift in degrees is not
put into the effect (it is not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'thermal_shift_c'}):
  statement           'interaction_detected' (the ligand is stated to raise the Tm), 'interaction_not_detected' (the Tm is stated not to change) or 'interaction_not_stated'
  support_refs        the spans of the fact that states it (empty when not stated)
  thermal_shift_c     the signed shift of the Tm in degrees Celsius, or None
The merger (literature_binding_merger.py) reads 'qualitative_effect' to take such a result into the row's interpretations and its own qualitative block; the
merger's contract is not changed.

Criteria mapping (DSF criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              protein_alone_control + ligand_alone_control (the controls that show the shift is the ligand's effect on the protein and not the vehicle, or a signal of the ligand and the dye)
binding_regime                dose_dependence + concentration_series + concentration_range (the shift follows the ligand concentration, over concentrations on both sides of the apparent KD)
binding_parameter_definition  shift_observed + shift_size + shift_over_spread (what the response is: a rise of the Tm, its size and its size over the scatter of the Tm)
calibration_applicability     curve_quality + heating_rate (the Tm is read from a clean sigmoid, near the equilibrium unfolding)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison (a degree, a quotient, a rate) is supported with a degree of 1.0 up to its full-agreement limit, the degree falling
linearly to 0 at its zero-agreement limit, and conflicting (no degree) at or beyond that limit: shift_size (signed shift at least SHIFT_FULL_AGREEMENT_C, none up to SHIFT_ZERO_AGREEMENT_C; a fall of the Tm is a destabilisation and
is conflicting), shift_over_spread (signed shift over the standard deviation at least SHIFT_OVER_SPREAD_FULL_AGREEMENT, none up to SHIFT_OVER_SPREAD_ZERO_AGREEMENT), concentration_range (the lowest ligand concentration over the KD at most
LOW_OVER_KD_FULL_AGREEMENT, none from LOW_OVER_KD_ZERO_AGREEMENT; the highest over the KD at least HIGH_OVER_KD_FULL_AGREEMENT, none up to HIGH_OVER_KD_ZERO_AGREEMENT; the weaker of the two decides) and heating_rate (at most
HEATING_RATE_FULL_AGREEMENT, none from HEATING_RATE_ZERO_AGREEMENT). Count minimums get no degree: concentration_series is supported at MIN_CONCENTRATIONS ligand concentrations or more, else conflicting; replicates are conflicting below
MIN_REPLICATES, else supported when the independence is yes, else unknown. A sheet criterion that is supported carries the smallest degree of its members that have one (the
sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. variance_correspondence takes
the weakest support of the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is
not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, recovery) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the protein,
immobilized_preparation_ref = the ligand, surface_ref = None (a plate is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_dsf_converted_v1'
CRITERIA_MAP = {'binding_controls': ('protein_alone_control', 'ligand_alone_control'), 'binding_regime': ('dose_dependence', 'concentration_series', 'concentration_range'), 'binding_parameter_definition': ('shift_observed', 'shift_size', 'shift_over_spread'), 'calibration_applicability': ('curve_quality', 'heating_rate'), 'sampling_basis': ('replicates',)}
SHIFT_FULL_AGREEMENT_C = 2.0  # EXPERT_REVIEW: smallest rise of the Tm (degrees Celsius) that the sheet takes as a clear stabilisation; thermal shift screens commonly call a hit a shift of 2 degrees or more.
SHIFT_ZERO_AGREEMENT_C = 0.5  # EXPERT_REVIEW: rise of the Tm (degrees Celsius) at or below which the shift cannot be told from the reproducibility of the Tm (a few tenths of a degree); no shift or a fall of the Tm (a destabilisation, which is not a stabilisation by binding) is conflicting, in between the degree falls linearly.
SHIFT_OVER_SPREAD_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest quotient of the signed shift over the standard deviation of the Tm taken as a shift well outside the scatter (three standard deviations).
SHIFT_OVER_SPREAD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient at or below which the shift is no larger than one standard deviation of the Tm: conflicting; the degree falls linearly in between.
MIN_CONCENTRATIONS = 3  # EXPERT_REVIEW: fewest ligand concentrations that show a concentration dependence of the shift (one gives a shift, two a single slope; three show curvature and a plateau).
LOW_OVER_KD_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest ratio of the lowest ligand concentration to the apparent KD at which the series defines the unliganded end of the curve.
LOW_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the lowest ligand concentration to the KD from which the series does not reach below the KD: conflicting; the degree falls linearly in between.
HIGH_OVER_KD_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest ratio of the highest ligand concentration to the apparent KD at which the series reaches the saturated end of the curve.
HIGH_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the highest ligand concentration to the KD up to which the series does not reach above the KD: conflicting; the degree falls linearly in between.
HEATING_RATE_FULL_AGREEMENT = 2.0  # EXPERT_REVIEW: largest heating rate (degrees Celsius per minute) at which the Tm is taken as near the equilibrium unfolding (instruments are run at 1 to 2 degrees per minute, nanoDSF at 1 degree per minute).
HEATING_RATE_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: heating rate (degrees Celsius per minute) from which the unfolding is taken as kinetically distorted (the Tm depends strongly on the rate): conflicting; the degree falls linearly in between.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); wells of one plate do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_thermal_shift_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_thermal_shift_is_not_an_attribution_fraction', 'total_signal': 'a_thermal_shift_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_dsf_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_dsf_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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
    return _graded(native['thermal_shift_refs'], _degree(native['thermal_shift_c'], SHIFT_FULL_AGREEMENT_C, SHIFT_ZERO_AGREEMENT_C))


def _judge_shift_over_spread(native):
    return _graded(native['shift_spread_refs'], _degree(native['shift_over_spread'], SHIFT_OVER_SPREAD_FULL_AGREEMENT, SHIFT_OVER_SPREAD_ZERO_AGREEMENT))


def _judge_concentrations(native):
    return _verdict('supported' if native['concentration_count'] >= MIN_CONCENTRATIONS else 'conflicting', native['concentration_count_refs'])


def _judge_range(native):
    return _graded(native['range_refs'], _degree(native['low_over_kd'], LOW_OVER_KD_FULL_AGREEMENT, LOW_OVER_KD_ZERO_AGREEMENT), _degree(native['high_over_kd'], HIGH_OVER_KD_FULL_AGREEMENT, HIGH_OVER_KD_ZERO_AGREEMENT))


def _judge_heating_rate(native):
    return _graded(native['heating_rate_refs'], _degree(native['heating_rate_c_per_min'], HEATING_RATE_FULL_AGREEMENT, HEATING_RATE_ZERO_AGREEMENT))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('shift_size', 'thermal_shift_recorded_for_the_sheet'): _judge_shift, ('shift_over_spread', 'shift_over_spread_recorded_for_the_sheet'): _judge_shift_over_spread,
          ('concentration_series', 'concentration_count_recorded_for_the_sheet'): _judge_concentrations, ('concentration_range', 'concentration_range_recorded_for_the_sheet'): _judge_range,
          ('heating_rate', 'heating_rate_recorded_for_the_sheet'): _judge_heating_rate, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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


def convert_dsf(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'dsf_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'dsf_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
    dependence = {'analyte_preparation_ref': preparations['protein_preparation_ref'], 'immobilized_preparation_ref': preparations['ligand_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'dsf', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities']['kd']['support']      # the support class of the KD operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'thermal_shift_c': native['thermal_shift_c']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['shift_observed'][0]      # the support class of the fact thermal_shift_observed, the one field the statement is derived from
    return converted
