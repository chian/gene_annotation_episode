"""PLA converter: turns the PLA grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_pla.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding' and quantity_kind 'relative_binding_response'), the sheet itself
(grade_assay run on it), the dependence keys the merger needs, the qualitative effect, and for every sheet component that a PLA cannot honestly fill, the reason it stays null.

The effect is QUALITATIVE (the contract limit, stated plainly)
---------------------------------------------------------------
A PLA reports puncta per cell, no binding constant; a count of puncta is never a KD and never pools with one. The converter fills NO effect and no variance: the sheet's
measured_effect, effect_variance and effect_precision cells are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is
invented. What the experiment contributes is carried beside the sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'puncta_fold_over_control'}):
  statement                'interaction_detected' (a proximity signal is stated), 'interaction_not_detected' (none is stated) or 'interaction_not_stated'
  support_refs             the spans of the fact that states it (empty when not stated)
  puncta_fold_over_control the puncta per cell of the test over those of the negative control, or None (also None when the control has 0 puncta)
and its interpretations go into the sheet's interpretations like those of every other experiment. The merger's contract is not changed.

Criteria mapping (PLA criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              single_antibody_control + no_primary_control + specificity_control + positive_control (the controls that show the puncta are the proximity of these two
                              proteins and not probes or antibodies that stick by themselves)
binding_regime                compartment (the puncta lie where both proteins are expected to meet)
binding_parameter_definition  proximity_observed + puncta_enrichment + antibody_species (what the response is: puncta of two species-specific probes, and their number over the control)
calibration_applicability     antibody_validation + blinded_quantification + statistical_test (the antibodies detect their proteins and the puncta are counted without bias and compared by a test)
sampling_basis                cells_counted + replicates
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison is supported with a degree of 1.0 up to its full-agreement limit, the degree falling linearly to 0 at its
zero-agreement limit, and conflicting (no degree) at or beyond that limit: puncta_enrichment (fold over the control at least FOLD_FULL_AGREEMENT, none at or below FOLD_ZERO_AGREEMENT;
a control with 0 puncta and a test above 0 is full agreement, a test of 0 is conflicting) and specificity_control (the fall of the puncta after the knockdown at least REDUCTION_FULL_AGREEMENT_PERCENT,
none at or below REDUCTION_ZERO_AGREEMENT_PERCENT). Count minimums get no degree: cells_counted is supported at MIN_CELLS_COUNTED cells or more, else conflicting; replicates are conflicting
below MIN_REPLICATES, else supported when the independence is yes, else unknown. A sheet criterion that is supported carries the smallest degree of its members that have one.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0, implied 0.7, about_something_else 0.3)
and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose weakest read field is implied or about_something_else gets that factor as its
degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. The qualitative effect is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is
not selected. Sheet criteria with no counterpart here are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first protein, immobilized_preparation_ref = the second protein,
surface_ref = None (a cell or a tissue section is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_pla_converted_v1'
CRITERIA_MAP = {'binding_controls': ('single_antibody_control', 'no_primary_control', 'specificity_control', 'positive_control'), 'binding_regime': ('compartment',), 'binding_parameter_definition': ('proximity_observed', 'puncta_enrichment', 'antibody_species'), 'calibration_applicability': ('antibody_validation', 'blinded_quantification', 'statistical_test'), 'sampling_basis': ('cells_counted', 'replicates')}
FOLD_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest fold of the puncta per cell of the test over the negative control taken as a clear signal; the single-antibody and no-primary reactions give a low background of puncta, and a threefold excess is the usual minimum that papers call specific.
FOLD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: fold at or below which the test cannot be told from the negative control (equal puncta per cell is no signal): conflicting; the degree falls linearly in between.
REDUCTION_FULL_AGREEMENT_PERCENT = 70.0  # EXPERT_REVIEW: smallest fall (percent) of the puncta per cell after the knockdown, the knockout or the competition of one protein taken as a specific signal; a knockdown removes most but not all of a protein, so a fall of about two thirds or more shows the puncta depend on it.
REDUCTION_ZERO_AGREEMENT_PERCENT = 20.0  # EXPERT_REVIEW: fall (percent) at or below which the puncta are not taken to depend on the protein (the cell-to-cell and the experiment-to-experiment variation of a puncta count is of this size, and an increase is a negative fall): conflicting; the degree falls linearly in between.
MIN_CELLS_COUNTED = 50  # EXPERT_REVIEW: fewest cells in which the puncta were counted; the puncta per cell are skewed and vary widely between cells, so a mean of fewer than about fifty cells is unstable.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or cultures); cells and images of one sample do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_pla_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_pla_punctum_is_not_an_attribution_fraction', 'total_signal': 'a_pla_punctum_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_pla_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_pla_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_enrichment(native):
    if native['puncta_control'] == 0:      # no division: any puncta over a control without puncta is full agreement
        return _graded(native['puncta_refs'], 1.0 if native['puncta_target'] > 0 else None)
    return _graded(native['puncta_refs'], _degree(native['puncta_fold_over_control'], FOLD_FULL_AGREEMENT, FOLD_ZERO_AGREEMENT))


def _judge_specificity(native):
    return _graded(native['reduction_refs'], _degree(native['puncta_reduction_percent'], REDUCTION_FULL_AGREEMENT_PERCENT, REDUCTION_ZERO_AGREEMENT_PERCENT))


def _judge_cells(native):
    return _verdict('supported' if native['cells_counted'] >= MIN_CELLS_COUNTED else 'conflicting', native['cells_counted_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('puncta_enrichment', 'puncta_enrichment_recorded_for_the_sheet'): _judge_enrichment, ('specificity_control', 'puncta_reduction_recorded_for_the_sheet'): _judge_specificity,
          ('cells_counted', 'cells_counted_recorded_for_the_sheet'): _judge_cells, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def convert_pla(graded):
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
    dependence = {'analyte_preparation_ref': preparations['component_a_preparation_ref'], 'immobilized_preparation_ref': preparations['component_b_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    qualitative_effect = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'puncta_fold_over_control': native['puncta_fold_over_control']}
    direction_field_support = max(native['support']['proximity_observed'], key=SUPPORTS.index, default=None)      # the statement is derived from the proximity_signal_detected fact alone; None when it is not stated (no direction)
    return {'version': VERSION, 'experiment_type': 'pla', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'qualitative_effect': qualitative_effect, 'direction_field_support': direction_field_support, 'null_components': dict(NULL_REASONS)}
