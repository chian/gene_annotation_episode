"""BRET converter: turns the BRET grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_bret.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a BRET
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (a tracer titration, NanoBRET target engagement) or else a Ki (a displacement of a tracer by an unlabelled competitor). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the KD in nM, else the Ki in nM (point operand, measurement key bret_kd or bret_ki). It is an APPARENT constant measured in live cells by BRET, not a constant of the purified proteins; the label is the
                    measurement key, and the caveats of the method are not changed in the number, they are judged by the criteria (saturation, the controls, the titration, the fit) and so reach the sheet as interpretations.
  effect_variance   variance of that constant, nM_squared, only when the source's spread (kd_spread for a KD, ki_spread for a Ki) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has neither a KD nor a Ki (a BRET ratio, a saturation curve and its BRET50). Then, exactly as the pull-down, EMSA, SEC, dialysis and AUC converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: a BRET50 is an acceptor-to-donor ratio, not a concentration, and a BRET ratio is not on the nM scale, so neither is put into the effect. What the
experiment does contribute is carried beside the sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'signal_over_control'}):
  statement           'interaction_detected' (the interaction fact is yes), 'interaction_not_detected' (it is no) or 'interaction_not_stated'
  support_refs        the spans of the fact that states it (empty when not stated)
  signal_over_control the BRET ratio of the pair over that of the negative control, or None
The merger (literature_binding_merger.py) reads 'qualitative_effect' to take such a result into the row's interpretations and its own qualitative block; the merger's contract is not changed.

Criteria mapping (BRET criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              donor_only_control + acceptor_only_control + negative_control + orientation (the controls that show the signal is a specific pair and not the donor's own emission, the acceptor's, random collision or a fusion artefact)
binding_regime                saturation_shown + titration_points + ratio_range + expression_matching + competition (the signal is followed over acceptor-to-donor ratios on both sides of BRET50 with the expression measured, and a tracer is displaced)
binding_parameter_definition  interaction_observed + bret50_specificity + signal_over_control (what the response is: a signal above the control and a BRET50 far below that of the control)
calibration_applicability     fit_quality + background_correction (the fit describes the data; the donor-only background is subtracted)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison (a quotient, a coefficient) is supported with a degree of 1.0 up to its full-agreement limit, the degree falling
linearly to 0 at its zero-agreement limit, and conflicting (no degree) at or beyond that limit: bret50_specificity (BRET50 of the negative control over that of the pair at least BRET50_CONTROL_FULL_AGREEMENT, none up to BRET50_CONTROL_ZERO_AGREEMENT),
signal_over_control (at least SIGNAL_FULL_AGREEMENT, none up to SIGNAL_ZERO_AGREEMENT), ratio_range (the lowest ratio over BRET50 at most LOW_OVER_BRET50_FULL_AGREEMENT, none from LOW_OVER_BRET50_ZERO_AGREEMENT; the highest over BRET50 at least
HIGH_OVER_BRET50_FULL_AGREEMENT, none up to HIGH_OVER_BRET50_ZERO_AGREEMENT; the weaker of the two decides) and fit_quality (R squared at least FIT_R_SQUARED_FULL_AGREEMENT, none up to FIT_R_SQUARED_ZERO_AGREEMENT).
Count minimums get no degree: titration_points is supported at MIN_TITRATION_POINTS points or more, else conflicting; replicates are conflicting below MIN_REPLICATES, else supported
when the independence is yes, else unknown. A sheet criterion that is supported carries the smallest degree of its members that have one (the
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

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the donor-fused protein (component a),
immobilized_preparation_ref = the acceptor-fused protein (component b), surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_bret_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('donor_only_control', 'acceptor_only_control', 'negative_control', 'orientation'), 'binding_regime': ('saturation_shown', 'titration_points', 'ratio_range', 'expression_matching', 'competition'), 'binding_parameter_definition': ('interaction_observed', 'bret50_specificity', 'signal_over_control'), 'calibration_applicability': ('fit_quality', 'background_correction'), 'sampling_basis': ('replicates',)}
BRET50_CONTROL_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest quotient of the BRET50 of the negative control pair over that of the pair under test that the sheet takes as a clear separation of a specific interaction from random collision (the control needs three times the acceptor to reach half of its plateau).
BRET50_CONTROL_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient at or below which the negative control saturates as readily as the pair (no separation): conflicting; in between the degree falls linearly.
SIGNAL_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest quotient of the BRET ratio of the pair over that of the negative control (or of the donor alone) that the sheet takes as a clear signal above the control; a ratio near 1 is background.
SIGNAL_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient at or below which the pair gives no more signal than the control: conflicting; in between the degree falls linearly.
MIN_TITRATION_POINTS = 5  # EXPERT_REVIEW: fewest acceptor-to-donor ratios (or tracer concentrations) that define a hyperbola of two parameters (BRET50 and BRETmax) and show its curvature and plateau.
LOW_OVER_BRET50_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest quotient of the lowest ratio over BRET50 at which the series defines the rising part of the curve.
LOW_OVER_BRET50_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient of the lowest ratio over BRET50 from which the series starts above half of the plateau (no rising part): conflicting; the degree falls linearly in between.
HIGH_OVER_BRET50_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest quotient of the highest ratio over BRET50 at which the series reaches the plateau (about 83 percent of BRETmax for a one-site hyperbola).
HIGH_OVER_BRET50_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient of the highest ratio over BRET50 up to which the series does not pass half of the plateau (BRETmax is not defined by the data): conflicting; the degree falls linearly in between.
FIT_R_SQUARED_FULL_AGREEMENT = 0.95  # EXPERT_REVIEW: smallest R squared taken as a fit that describes the data of a saturation or displacement curve.
FIT_R_SQUARED_ZERO_AGREEMENT = 0.80  # EXPERT_REVIEW: R squared at or below which the sheet takes the fit as not describing the data (a fifth of the variance unexplained): conflicting; the degree falls linearly in between.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate transfections, days or passages); wells of one plate do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_bret_run_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_bret_ratio_is_not_an_attribution_fraction', 'total_signal': 'a_bret_ratio_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_bret_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_bret_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_bret50(native):
    return _graded(native['bret50_refs'], _degree(native['bret50_control_over_pair'], BRET50_CONTROL_FULL_AGREEMENT, BRET50_CONTROL_ZERO_AGREEMENT))


def _judge_signal(native):
    return _graded(native['signal_refs'], _degree(native['signal_over_control'], SIGNAL_FULL_AGREEMENT, SIGNAL_ZERO_AGREEMENT))


def _judge_points(native):
    return _verdict('supported' if native['titration_point_count'] >= MIN_TITRATION_POINTS else 'conflicting', native['titration_refs'])


def _judge_range(native):
    return _graded(native['range_refs'], _degree(native['low_over_bret50'], LOW_OVER_BRET50_FULL_AGREEMENT, LOW_OVER_BRET50_ZERO_AGREEMENT), _degree(native['high_over_bret50'], HIGH_OVER_BRET50_FULL_AGREEMENT, HIGH_OVER_BRET50_ZERO_AGREEMENT))


def _judge_fit(native):
    return _graded(native['fit_refs'], _degree(native['fit_r_squared'], FIT_R_SQUARED_FULL_AGREEMENT, FIT_R_SQUARED_ZERO_AGREEMENT))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('bret50_specificity', 'bret50_comparison_recorded_for_the_sheet'): _judge_bret50, ('signal_over_control', 'signal_over_control_recorded_for_the_sheet'): _judge_signal,
          ('titration_points', 'titration_point_count_recorded_for_the_sheet'): _judge_points, ('ratio_range', 'ratio_range_recorded_for_the_sheet'): _judge_range,
          ('fit_quality', 'fit_r_squared_recorded_for_the_sheet'): _judge_fit, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    constant_name = native['constant_name']
    if constant_name is None:
        return None, 'no_effect_to_carry_a_variance', []
    name = constant_name + '_spread'
    spread = native['quantities'][name]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, name + '_not_given', []
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


def convert_bret(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = native['constant_name']
    quantitative = constant_name is not None
    if quantitative:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native['constant_nM'], 'nM', 'bret_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'bret_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
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
        variance_fields = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['component_a_preparation_ref'], 'immobilized_preparation_ref': preparations['component_b_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'bret', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities'][constant_name]['support']      # the support class of the binding-constant operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'signal_over_control': native['signal_over_control']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['interaction_observed'][0]      # the support class of the fact interaction_detected, the one field the statement is derived from
    return converted
