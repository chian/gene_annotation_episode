"""Y2H converter: turns the Y2H grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_y2h.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect, and for every sheet component that a Y2H cannot honestly fill, the reason it stays null.

One case: QUALITATIVE
---------------------
A yeast two-hybrid reports growth on selective medium or a reporter activity, never a binding constant: an interaction-strength number such as Miller units is not a KD and is not on the nM scale, so it is never pooled.
Exactly as the pull-down, EMSA, SEC and dialysis converters do for a result with no constant (quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect,
effect_variance and effect_precision cells are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'reporter_fold'}):
  statement       'interaction_detected' (an interaction is stated), 'interaction_not_detected' (no interaction is stated) or 'interaction_not_stated'
  support_refs    the spans of the fact that states it (empty when not stated)
  reporter_fold   the beta-galactosidase activity of the pair over that of the negative control, or None
The merger (literature_binding_merger.py) reads 'statement' and 'support_refs' of 'qualitative_effect'; the merger's contract is not changed.

Criteria mapping (Y2H criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              bait_autoactivation + prey_autoactivation + non_interacting_control + positive_control + nonselective_growth + reciprocal_orientation (the controls that show the reporter was activated by the interaction
                              of these two proteins and not by the bait or the prey alone, by a sticky or unrelated partner, or by a failure of the system or of the plasmids)
binding_species               expression_verified (the fusions that are tested are expressed in yeast)
binding_parameter_definition  interaction_observed + reporter_concordance + reporter_fold (what the response is: reporter activation, by more than one reporter, and how far above the control)
sampling_basis                replicates
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). The one continuous
comparison, reporter_fold, is supported with a degree of 1.0 from its full-agreement limit (REPORTER_FOLD_FULL_AGREEMENT), the degree falling linearly to 0 at its zero-agreement limit (REPORTER_FOLD_ZERO_AGREEMENT), and conflicting (no degree)
at or below that limit. The replicate count is a count minimum and gets no degree: conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown. A sheet criterion that is supported carries the smallest degree of its members that
have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0, implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it
reads. A supported member criterion whose weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. The
qualitative effect (its statement and support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no
counterpart here are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the prey, immobilized_preparation_ref = the bait, surface_ref = None (a yeast cell is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_y2h_converted_v1'
CRITERIA_MAP = {'binding_controls': ('bait_autoactivation', 'prey_autoactivation', 'non_interacting_control', 'positive_control', 'nonselective_growth', 'reciprocal_orientation'), 'binding_species': ('expression_verified',), 'binding_parameter_definition': ('interaction_observed', 'reporter_concordance', 'reporter_fold'), 'sampling_basis': ('replicates',)}
REPORTER_FOLD_FULL_AGREEMENT = 10.0  # EXPERT_REVIEW: smallest fold of the beta-galactosidase activity of the pair over the negative control (empty vectors) that the sheet takes as a clear reporter activation; positive pairs usually give ten-fold or more over the empty-vector background, and the background itself varies by about two-fold between experiments.
REPORTER_FOLD_ZERO_AGREEMENT = 2.0  # EXPERT_REVIEW: fold at or below which the activity of the pair cannot be told from the negative control (the between-experiment variation of the background); conflicting; the degree rises linearly in between.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate transformations or experiments on separate days); spots or colonies of one plate do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_y2h_test_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_y2h_reporter_is_not_an_attribution_fraction', 'total_signal': 'a_y2h_reporter_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_y2h_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_y2h_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_fold(native):
    return _graded(native['reporter_fold_refs'], _degree(native['reporter_fold'], REPORTER_FOLD_FULL_AGREEMENT, REPORTER_FOLD_ZERO_AGREEMENT))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('reporter_fold', 'reporter_fold_recorded_for_the_sheet'): _judge_fold, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def convert_y2h(graded):
    native = graded['native']
    ref = graded['experiment_ref']
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'relative_binding_response', 'quantities': dict.fromkeys(ROLES), 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['prey_preparation_ref'], 'immobilized_preparation_ref': preparations['bait_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    qualitative_effect = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'reporter_fold': native['reporter_fold']}
    direction_field_support = max(native['support']['interaction_observed'], key=SUPPORTS.index, default=None)      # the statement is derived from the interaction_detected fact alone; None when it is not stated (no direction)
    return {'version': VERSION, 'experiment_type': 'y2h', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'qualitative_effect': qualitative_effect, 'direction_field_support': direction_field_support, 'null_components': dict(NULL_REASONS)}
