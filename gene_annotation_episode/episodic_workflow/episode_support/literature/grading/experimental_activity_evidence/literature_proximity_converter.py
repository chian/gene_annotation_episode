"""Proximity-labeling converter: turns the proximity grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_proximity.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect, and for every sheet component that a proximity-labeling experiment
cannot honestly fill, the reason it stays null.

The path is QUALITATIVE only (as the pull-down, EMSA, SEC, dialysis and AUC converters do without a constant; quantity_kind 'relative_binding_response'): an enrichment is never a KD and never pools. NO effect and no
variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in
null_components. What the experiment does contribute is carried beside the sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'fold_enrichment'}):
  statement         'interaction_detected' (the candidate is stated enriched, that is, proximal), 'interaction_not_detected' (stated not enriched) or 'interaction_not_stated'.
                    Contract note: the merger's vocabulary has these three statements only; for this method 'interaction_detected' means PROXIMITY (within about 10 to 20 nm in living cells), which is not direct binding.
                    No statement is added and the merger is not changed; the experiment type 'proximity' that travels with the result tells the reader which kind of statement it is.
  support_refs      the spans of the fact that states it (empty when not stated)
  fold_enrichment   the fold enrichment of the candidate over the control as a ratio, or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (proximity criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------------
binding_controls              ligase_only_control + unlabeled_control + unrelated_bait_control (the controls that show the enrichment comes from the bait and the labelling and not from the enzyme, the capture or the compartment)
binding_regime                expression_level + localization (the fusion is expressed near the endogenous level and is where the endogenous bait is, so the labelled neighbourhood is the natural one)
binding_parameter_definition  proximity_observed + enrichment_magnitude + enrichment_significance + orthogonal_validation (what the response is: an enrichment, its size, its statistic, and whether an independent method confirms it)
calibration_applicability     biotinylation_dependence + streptavidin_capture (the labelling depends on the fusion and the capture takes the biotinylated proteins)
sampling_basis                replicates
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison is supported with a degree of 1.0 up to its full-agreement limit, the degree falling
linearly to 0 at its zero-agreement limit, and conflicting (no degree) at or beyond that limit: enrichment_magnitude (fold at least FOLD_FULL_AGREEMENT, none at or below FOLD_ZERO_AGREEMENT),
enrichment_significance (false discovery rate at most FDR_FULL_AGREEMENT_PERCENT, none from FDR_ZERO_AGREEMENT_PERCENT) and expression_level (expression ratio at most EXPRESSION_FULL_AGREEMENT, none from EXPRESSION_ZERO_AGREEMENT).
Count minimums get no degree: replicates are conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown. A sheet
criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): a supported member criterion whose weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its
own degree; direct leaves it unchanged. Support never changes a status. The qualitative effect (its statement and support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the bait, immobilized_preparation_ref = the candidate, surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_proximity_converted_v1'
CRITERIA_MAP = {'binding_controls': ('ligase_only_control', 'unlabeled_control', 'unrelated_bait_control'), 'binding_regime': ('expression_level', 'localization'), 'binding_parameter_definition': ('proximity_observed', 'enrichment_magnitude', 'enrichment_significance', 'orthogonal_validation'), 'calibration_applicability': ('biotinylation_dependence', 'streptavidin_capture'), 'sampling_basis': ('replicates',)}
FOLD_FULL_AGREEMENT = 4.0  # EXPERT_REVIEW: smallest fold enrichment of the candidate over the control that the sheet takes as a clear proximity; a fourfold enrichment (log2 fold change of 2) is a common cut-off of proximity proteomics for a confident hit, the usual lower cut-off being twofold.
FOLD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: fold at or below which the candidate is not enriched over the control (an equal or lower abundance): conflicting; in between the degree rises linearly.
FDR_FULL_AGREEMENT_PERCENT = 1.0  # EXPERT_REVIEW: largest false discovery rate (percent) taken as a statistically confident enrichment (a rate of 1 percent is the usual strict cut-off of SAINT and of moderated tests).
FDR_ZERO_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: false discovery rate (percent) from which the enrichment is not taken as statistically supported (the most permissive rate used for proximity hits): conflicting; in between the degree falls linearly.
EXPRESSION_FULL_AGREEMENT = 2.0  # EXPERT_REVIEW: largest expression of the fusion relative to the endogenous bait (ratio) taken as near the physiological level (up to about twofold).
EXPRESSION_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: expression ratio from which the fusion is so strongly overexpressed that mislocalisation and labelling of non-natural neighbours is expected (tenfold): conflicting; in between the degree falls linearly.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate cultures, days or preparations) for an enrichment statistic; lanes or injections of one sample do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_proximity_labeling_run_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_proximity_enrichment_is_not_an_attribution_fraction', 'total_signal': 'a_proximity_enrichment_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_proximity_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_proximity_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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
    return _graded(native['fold_refs'], _degree(native['fold_enrichment'], FOLD_FULL_AGREEMENT, FOLD_ZERO_AGREEMENT))


def _judge_fdr(native):
    return _graded(native['fdr_refs'], _degree(native['fdr_percent'], FDR_FULL_AGREEMENT_PERCENT, FDR_ZERO_AGREEMENT_PERCENT))


def _judge_expression(native):
    return _graded(native['expression_refs'], _degree(native['expression_ratio'], EXPRESSION_FULL_AGREEMENT, EXPRESSION_ZERO_AGREEMENT))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('enrichment_magnitude', 'enrichment_fold_recorded_for_the_sheet'): _judge_fold, ('enrichment_significance', 'enrichment_fdr_recorded_for_the_sheet'): _judge_fdr,
          ('expression_level', 'expression_ratio_recorded_for_the_sheet'): _judge_expression, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def convert_proximity(graded):
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
    dependence = {'analyte_preparation_ref': preparations['bait_preparation_ref'], 'immobilized_preparation_ref': preparations['candidate_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    qualitative_effect = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'fold_enrichment': native['fold_enrichment']}
    direction_field_support = max(native['support']['proximity_observed'], key=SUPPORTS.index, default=None)      # the statement is derived from the candidate_enriched fact alone; None when it is not stated (no direction)
    return {'version': VERSION, 'experiment_type': 'proximity', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'qualitative_effect': qualitative_effect, 'direction_field_support': direction_field_support, 'null_components': dict(NULL_REASONS)}
