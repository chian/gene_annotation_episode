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
to 0 at its zero-agreement limit on the scale its judge names (and why), and conflicting (no degree) at or beyond that limit: enrichment_magnitude (fold at least FOLD_FULL_AGREEMENT, none at or below
FOLD_ZERO_AGREEMENT; linear in the log of the fold), enrichment_significance (false discovery rate at most FDR_FULL_AGREEMENT_PERCENT, none from FDR_ZERO_AGREEMENT_PERCENT; linear in the
rate) and expression_level (expression ratio at most EXPRESSION_FULL_AGREEMENT, none from EXPRESSION_ZERO_AGREEMENT; linear in the log of the ratio).
The replicate count has no cut-off (OWNER RULE, A105_EXPERIMENT_SOP.md step 3): with the independence stated yes it is supported with the degree sqrt(n / MIN_REPLICATES),
which reaches full credit at the researched MIN_REPLICATES and gives partial credit below it (see _judge_replicates for why this shape); with the independence not stated yes it
is unknown (independence stated no is the grader's own conflicting). A sheet
criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): a supported member criterion whose weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its
own degree; direct leaves it unchanged. Support never changes a status. The qualitative effect (its statement and support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the bait, immobilized_preparation_ref = the candidate, surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.

The owner's five questions, per researched value (range review 2026-11-21; Q1 what it protects against, Q2 general practice or lab-specific, Q3 absolute or relative
scale and whether the grader has the quantity, Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency with the other binding types). Method
references (from memory, not web-checked): Roux et al. 2012 J Cell Biol 196:801 (BioID); Lam et al. 2015 Nat Methods 12:51 and Hung et al. 2016 Nat Protoc 11:456 (APEX2,
ratiometric proteomics); Branon et al. 2018 Nat Biotechnol 36:880 (TurboID); Choi et al. 2011 Nat Methods 8:70 and Teo et al. 2014 J Proteomics 100:37 (SAINT, SAINTexpress);
Mellacheruvu et al. 2013 Nat Methods 10:730 (CRAPome); Lambert et al. 2015 J Proteomics 118:81 (near-endogenous Flp-In T-REx expression for BioID); Samavarchi-Tehrani et al.
2020 Mol Cell Proteomics 19:757 (proximity biotinylation review); Cumming et al. 2007 J Cell Biol 177:7 (replicates).
FOLD_FULL_AGREEMENT 4 / FOLD_ZERO_AGREEMENT 1  Q1 a candidate that is only background (endogenously biotinylated carboxylases, bead binders, abundant bystanders) called
     proximal. Q2 general practice: log2 fold change cut-offs of 1 to 2 (2 to 4 fold) are the usual ones (Hung 2016, Branon 2018; AP-MS/BioID scoring with the CRAPome);
     1 is no enrichment by definition. Q3 already relative to the paper's own control (the fold is over it); which control it is over (free enzyme vs a compartment-matched
     bait) changes what it means and is not in the grader facts (gap). Q4 MS intensities and counts have multiplicative error and the field states its cut-offs as log2
     fold, so 1 -> 2 fold matters as much as 2 -> 4; the old linear-in-ratio shape gave the usual twofold cut-off only 0.33 and made 1 -> 2 fold count a third as much as
     2 -> 4 (too harsh on modest real hits, too flat at the bottom). Q5 the pull-down's AP-MS fold (MIN_FOLD_ENRICHMENT 3 / 1) is linear in the log of the fold. CHANGED:
     values kept, shape linear in ratio -> linear in log(fold) (2 fold 0.33 -> 0.50, 1.5 fold 0.17 -> 0.29, 3 fold 0.67 -> 0.79).
FDR_FULL_AGREEMENT_PERCENT 1 / FDR_ZERO_AGREEMENT_PERCENT 10  Q1 an enrichment that the replicates do not separate from the control's spread (a chance hit). Q2 general
     practice: SAINT BFDR at most 1 percent is the strict standard of the BioID field, 5 percent common, 10 percent the most permissive used (Teo 2014; Choi 2011). Q3 a false
     discovery rate is already self-calibrated (an estimated fraction of false calls), so an absolute scale is right; whether the stated rate is the candidate's own score or
     the cut-off of the whole hit list is not in the grader facts (gap: a list cut-off of 5 percent gives 0.56 to a candidate that may lie far below it, so the error is on
     the strict side). Q4 the score misleads in proportion to the expected fraction of false calls, which is linear in the rate; a log shape was weighed and not taken
     (it would treat 1 -> 2 percent like 5 -> 10 percent although the first changes the false fraction by one point, the second by five). Q5 no other binding type
     judges an FDR; the linear-in-the-quantity-that-misleads choice matches the percent ramps of EMSA (shifted fraction) and PLA (puncta reduction). KEPT (values and shape).
EXPRESSION_FULL_AGREEMENT 2 / EXPRESSION_ZERO_AGREEMENT 10  Q1 an overexpressed fusion that saturates its natural partners, mislocalises and labels non-natural neighbours.
     Q2 general practice: near-endogenous expression (inducible Flp-In T-REx lines titrated to the endogenous level, or knock-in at the endogenous locus; Roux 2012, Lambert
     2015); up to about twofold is what papers accept as near-endogenous; tenfold is the expert zero end (no standard value; EXPERT_REVIEW). Q3 already relative to the
     endogenous bait (the paper's own measurement): right. Q4 once the natural partners are occupied, the excess fusion only adds bystander labelling, so the specific
     over bystander contrast falls by about the same factor for each doubling of expression: a multiplicative effect; the old linear-in-ratio shape lost only a quarter of
     the credit at fourfold (0.75) and most of it only near tenfold. Q5 the multiplicative quantities of the other types (the pull-down fold, the radioligand excess) are
     ramped in the log. CHANGED: values kept, shape linear in ratio -> linear in log(ratio) (4x 0.75 -> 0.57, 6x 0.50 -> 0.32, 8x 0.25 -> 0.14). Low expression is not
     penalised: it costs sensitivity (a missed neighbour), not a false proximity, and no researched lower value exists.
MIN_REPLICATES 3 (sqrt(n / 3))  Q1 an enrichment from one labelling culture, which carries its culture-to-culture variation (labelling efficiency, bead background,
     stochastic MS sampling). Q2 three independent experiments is general practice (Cumming 2007; label-free and TMT tests need three for a variance), though SAINT-based
     BioID often uses two biological replicates (Teo 2014): two then gets 0.82, a mild loss that matches its lower precision; the significance itself is judged by the FDR.
     Q3 absolute (a count). Q4 one experiment still shows the enrichment, so partial credit (0.58), never conflicting; the precision of a mean grows as sqrt(n). Q5 owner
     rule: replicates mean precision, sqrt(n / MIN) as in pull-down, EMSA, PLA, split reporter, BRET, Y2H. KEPT.
The fact-only members (proximity_observed, the three controls, biotinylation_dependence, streptavidin_capture, localization, orthogonal_validation) hold no researched value.
Unknown weight: this converter holds none and no degree contains one (the weight for an unstated criterion is per type and per sheet criterion in literature_row_contract).
GAP RESOLUTION 2026-11-21 (the range-review gaps below, decided): (1) DONE: fact fold_over_matched_control; stated 'no' (free enzyme or unlabelled cells) moves the full-credit fold from 4 to FOLD_FULL_AGREEMENT_UNMATCHED 8
(expert judgment, gradual, same zero end); yes or unknown: unchanged. (2) NOT DONE: a list cut-off or the candidate's own rate both bound the false calls from above, so the stated rate errs on the strict side;
correcting it needs a number with no standard value, and a SAINT probability is a different scale. (3) NOT DONE: isobaric compression understates the true fold, so a stated TMT fold that clears the ramp is conservative; no honest
correction without an unreasoned factor. (4) NOT DONE: the harm of a long labelling (more bystanders) is what the controls and the fold over the control already measure, and the right time depends on the enzyme (BioID is designed for 18 to 24 h),
a choice that may not decide a criterion. (5) DONE as a grader rule: a candidate stated NOT enriched is a stated result (proximity_observed supported, direction carried by the qualitative statement), and the magnitude and the significance are not applicable for it.
ORIGINAL GAP LIST (as written by the range review): (1) enrichment_magnitude: which control the fold is over (free enzyme, no
labelling, or a compartment-matched/unrelated bait); a fold over a free enzyme overstates proximity for a protein that lives in the bait's compartment. (2)
enrichment_significance: whether the stated rate is the candidate's own (SAINT BFDR or q-value of that protein) or the cut-off of the hit list, and the SAINT probability
(AvgP) when a paper states that instead of a rate. (3) enrichment_magnitude: isobaric (TMT) quantification compresses ratios, so a stated TMT fold understates the true
one; the quantification is only a record choice without a span, and a choice may not decide a criterion. (4) Not a value gap but a criterion gap: the labelling time
is recorded and not judged (a BioID run of 16 to 24 h, or TurboID run for hours, labels more bystanders than a 10 min TurboID or 1 min APEX2 pulse; Branon 2018).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_proximity_converted'
CRITERIA_MAP = {'binding_controls': ('ligase_only_control', 'unlabeled_control', 'unrelated_bait_control'), 'binding_regime': ('expression_level', 'localization'), 'binding_parameter_definition': ('proximity_observed', 'enrichment_magnitude', 'enrichment_significance', 'orthogonal_validation'), 'calibration_applicability': ('biotinylation_dependence', 'streptavidin_capture'), 'sampling_basis': ('replicates',)}
FOLD_FULL_AGREEMENT = 4.0  # EXPERT_REVIEW: smallest fold enrichment of the candidate over the control that the sheet takes as a clear proximity; a fourfold enrichment (log2 fold change of 2) is a common cut-off of proximity proteomics for a confident hit, the usual lower cut-off being twofold.
FOLD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: fold at or below which the candidate is not enriched over the control (an equal or lower abundance): conflicting; in between the degree rises linearly in the log of the fold (MS intensities and counts have multiplicative error and the cut-offs are stated as log2 fold: twofold, the usual lower cut-off, is half credit).
FDR_FULL_AGREEMENT_PERCENT = 1.0  # EXPERT_REVIEW: largest false discovery rate (percent) taken as a statistically confident enrichment (a rate of 1 percent is the usual strict cut-off of SAINT and of moderated tests).
FDR_ZERO_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: false discovery rate (percent) from which the enrichment is not taken as statistically supported (the most permissive rate used for proximity hits): conflicting; in between the degree falls linearly.
EXPRESSION_FULL_AGREEMENT = 2.0  # EXPERT_REVIEW: largest expression of the fusion relative to the endogenous bait (ratio) taken as near the physiological level (up to about twofold).
EXPRESSION_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: expression ratio from which the fusion is so strongly overexpressed that mislocalisation and labelling of non-natural neighbours is expected (tenfold): conflicting; in between the degree falls linearly in the log of the ratio (beyond the natural partners the excess fusion only adds bystander labelling, so the specific over bystander contrast falls by about the same factor per doubling).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate cultures, days or preparations) for an enrichment statistic; lanes or injections of one sample do not count. Since the owner rule (step 3) it is where the replicate degree reaches full credit, no longer a pass/fail cut-off: fewer independent experiments get partial credit (_judge_replicates).
FOLD_FULL_AGREEMENT_UNMATCHED = 8.0  # EXPERT_REVIEW (expert judgment, no standard value): where the fold is stated over a control that does NOT match the bait (the free enzyme or unlabelled cells), a candidate that merely shares the bait's compartment is enriched over it without being near the bait, so full credit needs one more doubling than over a matched control (log2 fold change of 3 instead of 2); the zero end (no enrichment, fold 1) is the same. Not applied when the paper does not say which control it is over (unknown) or states a matched control (yes).
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_proximity_labeling_run_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_proximity_enrichment_is_not_an_attribution_fraction', 'total_signal': 'a_proximity_enrichment_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_proximity_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_proximity_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _linear(value):
    return value


def _degree(value, full, zero, scale):
    """1.0 at ``full`` (or beyond it), falling to 0 at ``zero`` linearly in ``scale`` (the judge names the scale and why; the limits may lie on either side of each other);
    None at or beyond ``zero``. The scale is applied only strictly between the limits, so a zero or negative value never reaches a logarithm."""
    if (value - zero) * (full - zero) <= 0:
        return None
    if (value - full) * (full - zero) >= 0:
        return 1.0
    return (scale(value) - scale(zero)) / (scale(full) - scale(zero))


def _graded(refs, *degrees):
    """The verdict of a continuous comparison: conflicting where any degree is None, else supported with the smallest degree."""
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _judge_fold(native):
    """Linear in the log of the fold: MS intensities and counts have multiplicative error and the field states its cut-offs as log2 fold (range review, FOLD_*)."""
    full = FOLD_FULL_AGREEMENT_UNMATCHED if native['fold_matched_control'] == 'no' else FOLD_FULL_AGREEMENT
    return _graded(native['fold_refs'], _degree(native['fold_enrichment'], full, FOLD_ZERO_AGREEMENT, math.log))


def _judge_fdr(native):
    """Linear in the rate: what misleads is the expected fraction of false calls, which is the rate itself (range review, FDR_*)."""
    return _graded(native['fdr_refs'], _degree(native['fdr_percent'], FDR_FULL_AGREEMENT_PERCENT, FDR_ZERO_AGREEMENT_PERCENT, _linear))


def _judge_expression(native):
    """Linear in the log of the ratio: past the natural partners each doubling of the fusion cuts the specific over bystander contrast by about the same factor (range review, EXPRESSION_*)."""
    return _graded(native['expression_refs'], _degree(native['expression_ratio'], EXPRESSION_FULL_AGREEMENT, EXPRESSION_ZERO_AGREEMENT, math.log))


def _judge_replicates(native):
    """Independence stated yes: supported with the degree sqrt(n / MIN_REPLICATES), capped at 1; otherwise unknown (the count alone does not say independent experiments).

    Why this shape for proximity labelling: the labelling and the streptavidin capture vary from culture to culture (labelling efficiency, the background of endogenously
    biotinylated carboxylases and of proteins that stick to the beads, the stochastic sampling of the mass spectrometer), so a proximal hit is called on the enrichment
    averaged over the independent labelling experiments. The uncertainty of that average falls as 1 / sqrt(n), so the degree is its precision relative to the precision
    at the researched MIN_REPLICATES: full credit at MIN_REPLICATES and above, partial below it (one experiment about 0.58, two about 0.82), never a step and never 0 for
    a stated experiment (one experiment still shows the enrichment; it only gives no spread). Each further experiment adds less than the one before, as an average does.
    """
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


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
