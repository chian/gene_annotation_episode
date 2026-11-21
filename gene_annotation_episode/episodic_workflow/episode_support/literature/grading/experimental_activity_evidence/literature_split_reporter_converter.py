"""Split-reporter converter: turns the split-reporter grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_split_reporter.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a split reporter
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (from a titration or the kinetics of a reversible split reporter such as NanoBiT). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key split_reporter_kd, so that it is labelled as derived from the split reporter and is not a KD of the
                    purified proteins). The caveats of the method (a KD needs titration concentrations on both sides of it; an irreversible reporter has no equilibrium) are not
                    changed in the number, they are judged by the criteria (titration_series, titration_range, saturable_titration, reversible_reporter) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no KD (a signal above the controls is shown). Then, exactly as the pull-down, EMSA, SEC, dialysis and AUC converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the signal over the
background nor the signal over the negative control is put into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'signal_over_negative_control'}):
  statement                    'interaction_detected' (a signal above the controls is stated), 'interaction_not_detected' (no such signal is stated) or 'interaction_not_stated'
  support_refs                 the spans of the fact that states it (empty when not stated)
  signal_over_negative_control the stated fold of the signal over the negative control, or None
The scoring reads only 'statement' and 'support_refs' of 'qualitative_effect': the statement fixes the direction
(literature_direction.py) and the support refs join the row (literature_row.py).

Criteria mapping (split-reporter criteria -> sheet criteria), declared in CRITERIA_MAP
--------------------------------------------------------------------------------------
binding_controls              fragment_alone_control + unrelated_pair_control + binding_mutant_control + positive_control (the controls that show the signal is the two partners
                              bringing the fragments together and not the fragments alone, a nonspecific pair, or a dead assay)
binding_regime                fusion_orientations + saturable_titration + titration_series + titration_range + reversible_reporter (the signal is seen in several orientations, is
                              saturable, is followed over concentrations on both sides of the KD, and a reversible reporter reports an equilibrium)
binding_parameter_definition  interaction_observed + signal_to_background + negative_control_ratio (what the response is: a reconstituted signal, over the background and over the negative control)
calibration_applicability     expression_verified + background_correction (the signal is read against the expression of the fusions and a subtracted background)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison (a ratio) is supported with a degree of 1.0 up to its full-agreement limit, the degree falling
linearly to 0 at its zero-agreement limit, and conflicting (no degree) at or beyond that limit: signal_to_background (ratio at least SIGNAL_TO_BACKGROUND_FULL_AGREEMENT, none up to SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT),
negative_control_ratio (at least NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT, none up to NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT) and titration_range (the lowest concentration over the KD at most LOW_OVER_KD_FULL_AGREEMENT, none from LOW_OVER_KD_ZERO_AGREEMENT; the highest
over the KD at least HIGH_OVER_KD_FULL_AGREEMENT, none up to HIGH_OVER_KD_ZERO_AGREEMENT; the weaker of the two decides).
Count minimums get no degree: fusion_orientations is supported at MIN_ORIENTATIONS combinations or more, else conflicting; titration_series is supported at MIN_CONCENTRATIONS concentrations or more, else conflicting;
replicates are conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown. A sheet criterion that is supported carries the smallest degree of its members that have one (the
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

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first component,
immobilized_preparation_ref = the second component, surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_split_reporter_converted_v1'
CRITERIA_MAP = {'binding_controls': ('fragment_alone_control', 'unrelated_pair_control', 'binding_mutant_control', 'positive_control'), 'binding_regime': ('fusion_orientations', 'saturable_titration', 'titration_series', 'titration_range', 'reversible_reporter'), 'binding_parameter_definition': ('interaction_observed', 'signal_to_background', 'negative_control_ratio'), 'calibration_applicability': ('expression_verified', 'background_correction'), 'sampling_basis': ('replicates',)}
SIGNAL_TO_BACKGROUND_FULL_AGREEMENT = 10.0  # EXPERT_REVIEW: smallest signal over background taken as a clear signal; a split luciferase (NanoBiT) typically gives tens to thousands of fold over the background, a split fluorescent protein a few fold to ten.
SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT = 2.0  # EXPERT_REVIEW: signal over background at or below which the signal cannot be told from the variation of the background (a twofold change is about the noise of a transfected-cell assay): conflicting; the degree falls linearly in between.
NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest signal over the negative control pair taken as specific; five fold clearly exceeds the spread between non-interacting pairs.
NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT = 1.5  # EXPERT_REVIEW: signal over the negative control at or below which the pair cannot be told from a non-interacting pair (expression differences alone give about this much); conflicting; the degree falls linearly in between.
MIN_ORIENTATIONS = 2  # EXPERT_REVIEW: fewest fusion orientation combinations tested; one orientation can fail by steric block or give a signal by position alone, two or more show that the result does not depend on one geometry.
MIN_CONCENTRATIONS = 3  # EXPERT_REVIEW: fewest titration concentrations that define an apparent KD (one gives a signal, two a single slope; three show curvature and a plateau).
LOW_OVER_KD_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest ratio of the lowest titration concentration to the apparent KD at which the series defines the free end of the isotherm.
LOW_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the lowest titration concentration to the KD from which the series does not reach below the KD: conflicting; the degree falls linearly in between.
HIGH_OVER_KD_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest ratio of the highest titration concentration to the KD at which the series reaches the saturated end of the isotherm.
HIGH_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the highest titration concentration to the KD up to which the series does not reach above the KD: conflicting; the degree falls linearly in between.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days, transfections or preparations); wells of one plate do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_split_reporter_signal_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_split_reporter_signal_is_not_an_attribution_fraction', 'total_signal': 'a_split_reporter_signal_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_split_reporter_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_split_reporter_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_signal_to_background(native):
    return _graded(native['signal_to_background_refs'], _degree(native['signal_to_background'], SIGNAL_TO_BACKGROUND_FULL_AGREEMENT, SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT))


def _judge_negative_control_ratio(native):
    return _graded(native['signal_over_negative_control_refs'], _degree(native['signal_over_negative_control'], NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT, NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT))


def _judge_orientations(native):
    return _verdict('supported' if native['orientation_pairs_tested'] >= MIN_ORIENTATIONS else 'conflicting', native['orientation_pairs_refs'])


def _judge_concentrations(native):
    return _verdict('supported' if native['concentration_count'] >= MIN_CONCENTRATIONS else 'conflicting', native['concentration_count_refs'])


def _judge_range(native):
    return _graded(native['range_refs'], _degree(native['low_over_kd'], LOW_OVER_KD_FULL_AGREEMENT, LOW_OVER_KD_ZERO_AGREEMENT), _degree(native['high_over_kd'], HIGH_OVER_KD_FULL_AGREEMENT, HIGH_OVER_KD_ZERO_AGREEMENT))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_to_background', 'signal_to_background_recorded_for_the_sheet'): _judge_signal_to_background,
          ('negative_control_ratio', 'negative_control_ratio_recorded_for_the_sheet'): _judge_negative_control_ratio,
          ('fusion_orientations', 'orientation_pairs_recorded_for_the_sheet'): _judge_orientations,
          ('titration_series', 'concentration_count_recorded_for_the_sheet'): _judge_concentrations,
          ('titration_range', 'titration_range_recorded_for_the_sheet'): _judge_range,
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


def convert_split_reporter(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'split_reporter_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'split_reporter_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
    converted = {'version': VERSION, 'experiment_type': 'split_reporter', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components}
    # quantitative: the support of the KD operand that is the effect; qualitative: the support of the interaction_detected fact the statement is derived from (None when not stated: no direction)
    converted['direction_field_support'] = max([native['quantities']['kd'].get('support')] if quantitative else native['support']['interaction_observed'], key=SUPPORTS.index, default=None)
    if not quantitative:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'signal_over_negative_control': native['signal_over_negative_control']}
    return converted
