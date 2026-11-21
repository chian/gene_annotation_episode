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
The researched values are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). OWNER RULE (step 3 of A105_EXPERIMENT_SOP.md): each researched value is kept and is the centre of a gradual curve, never a pass/fail cut.
A continuous comparison is supported with a degree of 1.0 up to its full-agreement limit, the degree falling to 0 at its zero-agreement limit on the scale the judge names, and
conflicting (no degree) at or beyond that limit, where the paper's own numbers show the standard is not met: puncta_enrichment (fold over the control at least FOLD_FULL_AGREEMENT,
none at or below FOLD_ZERO_AGREEMENT, a test no larger than the paper's own control; linear in the LOG of the fold in between; a control with 0 puncta and a test above 0 is full
agreement, a test of 0 is conflicting) and specificity_control (the fall of the SPECIFIC puncta, test minus negative control, after the knockdown at least
REDUCTION_FULL_AGREEMENT_PERCENT, none at or below REDUCTION_ZERO_AGREEMENT_PERCENT, no fall beyond the count's own variation; linear in the percent in between; the fall of the
total puncta is used when the control is not stated or the test is not above it).
The two counts are gradual around their researched values (they were pass/fail cuts before):
  cells_counted  n cells: degree = min(1, sqrt(n / CELLS_COUNTED_FULL_CREDIT)), the precision of the mean puncta per cell relative to that of the researched number of cells.
  replicates     n independent experiments: degree = min(1, sqrt(n / REPLICATES_FULL_CREDIT)) when their independence is stated yes, the precision of the mean puncta difference over
                 n independent experiments (owner rule: replicates mean precision in every assay); unknown when the independence is not stated (a stated no is the grader's conflicting).
A small count is weaker evidence, not evidence against: it is supported with a partial degree, never conflicting. A sheet criterion that is supported carries the smallest degree
of its members that have one.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0, implied 0.7, about_something_else 0.3)
and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose weakest read field is implied or about_something_else gets that factor as its
degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. The qualitative effect is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is
not selected. Sheet criteria with no counterpart here are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first protein, immobilized_preparation_ref = the second protein,
surface_ref = None (a cell or a tissue section is not a surface reference), dataset_ref = the dataset.

The owner's questions, asked of every researched value (range review 2026-11-21; Q1 failure caught, Q2 general or lab-specific, Q3 absolute or relative and is the relative
quantity in the grader facts, Q4 how badly a wrong value misleads and does the shape reflect it, Q5 consistency with the other binding assays). Citations are from memory, not
web-verified.
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
FOLD_FULL_AGREEMENT 3 / FOLD_ZERO_AGREEMENT 1 (puncta_enrichment)
  Q1 puncta at the level of the technical background (one probe or antibody sticking alone, non-templated ligation): a "proximity" that is background. It does NOT catch a
  cross-reactive antibody (that gives real puncta above background); specificity_control does. Q2 the zero end is physics (equal puncta = no signal). The 3x is common practice,
  not a guideline: no method paper fixes a fold (Soderberg et al. 2006 Nat Methods 3:995; Weibrecht et al. 2010 Expert Rev Proteomics 7:401; Alam 2018 Curr Protoc Immunol
  123:e58 compare to the single-antibody controls by eye or by a test); the background depends on the antibodies, the cells and the image threshold (lab-specific). KEPT.
  Q3 already relative to the paper's own control. It should ALSO be relative to the spread of the puncta per cell (the fold in standard errors, as the pull-down does) and know
  WHICH negative control is the denominator (a no-primary control has less background than a single-antibody control, so a fold over it overstates): neither is collected
  (grader gaps 1, 2). Q4 a wrong 3x moves a real signal by a fraction of the BPD degree, never its direction (the statement comes from proximity_signal_detected); the score
  misleads mildly. The shape was linear in the fold, so 1 -> 1.5 (a x1.5 step) got a third of the credit of 1.5 -> 3 (a x2 step), although the error of a quotient of two
  counts is multiplicative and ratio steps should count by their size: CHANGED to linear in log fold (fold 1.5: 0.25 -> 0.37; 2: 0.50 -> 0.63; 3: 1.0). <= 1 stays conflicting (SOP rule 5, a signal no larger than the paper's
  own control). A control of 0 puncta with a test above 0 stays full agreement (no ratio exists; a paper states 0 only for a clean control). Q5 now the same log-fold ramp as the
  pull-down enrichment (MIN_FOLD_ENRICHMENT 3 / 1).
REDUCTION_FULL_AGREEMENT_PERCENT 70 / REDUCTION_ZERO_AGREEMENT_PERCENT 20 (specificity_control)
  Q1 the dominant PLA false "binds": a cross-reactive primary antibody whose puncta do not come from the named protein (Uhlen et al. 2016 Nat Methods 13:823, the genetic
  strategy of antibody validation: the signal must fall when the protein is depleted). Q2 70: an siRNA knockdown typically removes 70 to 90 percent of a protein, so puncta
  that depend on it fall by about that much (general practice for knockdowns; a knockout should give about 100, a competing peptide varies: lab- and reagent-specific);
  20: the run-to-run variation of a mean puncta count (practice estimate; no method paper gives a value, lab-specific). KEPT. Q3 the fall was taken of the TOTAL puncta, which include the technical background that no
  knockdown can remove: test 6, control 3, knockdown 3 (all specific puncta gone) scored 50 percent (degree 0.6), so a modest fold was punished twice. CHANGED: the fall is taken
  of the SPECIFIC puncta, (test - knockdown) / (test - control), when the grader's native values give the control and the test is above it (they do: puncta_control and the
  knockdown in native quantities); else the total fall as before (it is never larger, so the fallback is the conservative reading). The fall should ALSO be relative to the
  measured depletion of the protein (a 50 percent knockdown cannot give a 70 percent fall) and to which manipulation it was (knockdown, knockout, competition): not collected
  (grader gaps 3, 4). Q4 too strict a value turns an honest partial knockdown into low credit or, at <= 20, conflicting; without the depletion a small fall could be a failed
  knockdown rather than a cross-reactive antibody, so the conflicting end is the most consequential number here (owner question, kept: the paper's own numbers show the puncta
  do not follow the protein, SOP rule 5). Linear in the percent kept: the fall is an additive fraction of a count, not a ratio. Q5 the same paper-own-control ramp as the
  pull-down competition and the EMSA competition (a stated failure conflicts, silence is unknown).
CELLS_COUNTED_FULL_CREDIT 50 (cells_counted)
  Q1 an unstable or cherry-picked mean puncta per cell from a few representative cells (the puncta per cell are skewed and vary widely between cells). Q2 general practice,
  no guideline: papers count about 30 to 200 cells per condition, 50 being a usual minimum (practice seen across PLA papers; Alam 2018 for the counting method; no guideline fixes it); lab-specific in its exact value.
  KEPT. Q3 the cells a mean needs scale with the cell-to-cell spread over the effect (a tenfold signal needs few cells, a 1.5-fold one many): the per-cell SD of the puncta
  is not collected, nor whether the count is per condition or in total (grader gaps 1, 5); absolute kept. Q4 the cell count limits only the within-run precision; the
  run-to-run variation is the replicates', so a wrong 50 misleads little. sqrt(n / 50) is steep at a handful of cells (an anecdote: 1 cell 0.14, 10 cells 0.45) and gentle
  near 50 (25 cells 0.71): the standard error of a mean, right. KEPT. Q5 the same precision shape as replicates in every assay.
REPLICATES_FULL_CREDIT 3 (replicates)
  Q1 a puncta difference seen in one run (ligation and amplification efficiency, antibody lot and imaging vary between runs; more cells of one run do not average them).
  Q2 general: three independent experiments (Cumming, Fidler & Vaux 2007 J Cell Biol 177:7; journal reporting standards). KEPT. Q3 an absolute count is right. Q4 sqrt(n / 3):
  one experiment 0.58, two 0.82, full from three; one experiment with its controls already shows the puncta, so a steep loss below one is not warranted. Independence not
  stated is unknown; a stated no is the grader's conflicting fact. Q5 the owner's replicate rule, as in pull-down, Y2H, proximity, FP, FRET, AlphaScreen and CETSA. KEPT.
Facts (single_antibody_control, no_primary_control, positive_control, antibody_species, antibody_validation, compartment, blinded_quantification, statistical_test,
proximity_observed) hold no researched value: yes supported, no conflicting, silence unknown. The amplification time is recorded and not judged (it changes the punctum size,
not the count).
Grader gap pass 2026-11-21 (the six gaps of the range review; the owner's questions applied to each):
  ADDED (1) the spread (SD or SE, and its kind) of the puncta per cell of the test and the control: the fold is also read in standard errors of the difference
  (SPREAD_Z_FULL 2, rule 6, the weaker degree counts; same as the pull-down); the cell count stays absolute. ADDED (3) the measured depletion of the protein in the specificity
  control: the researched ends of the fall (70 / 20 percent, valid for a full depletion) are scaled by depletion / 100, because the puncta of a proximity pair scale with the
  amount of the depleted partner; no new constant. NOT ADDED (2) which negative control the count is: both the single-antibody and the no-primary reactions already have their own
  fact (single_antibody_control, no_primary_control), and a correction of the fold for the kind of control would need a number that no method paper gives (an unreasoned constant,
  consistency rule 4). NOT ADDED (4) the kind of manipulation: where it matters its effect is the measured depletion (a knockout is about 100 percent, gap 3); a competing peptide has
  no depletion to measure and its expected fall is reagent-specific, so the kind alone would need an unreasoned expected fall. NOT ADDED (5) per condition or in total: using it
  needs the number of conditions, which is not collected, and the count's effect is already small (Q4 above). NOT ADDED (6) the p-value: a test over cells is pseudoreplicated (many
  cells give a small p for a small effect), so the p-value adds nothing the fold in standard errors and the replicate count do not already say, and it has no researched scale.
Unknown weight: this converter holds none and no degree contains one (the weight for an unstated criterion is per type and criterion in
literature_row_contract.WEIGHT_UNKNOWN_BY_TYPE / WEIGHT_UNKNOWN_BY_CRITERION, A105_ASSAY_CALIBRATION_DETAILS.md: PLA 0.55; BC 0.50, CA 0.50, BR 0.70, SB 0.80).
"""
from math import log, sqrt

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pla_criteria import PERCENT_PER_FRACTION
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_pla_converted_v1'
CRITERIA_MAP = {'binding_controls': ('single_antibody_control', 'no_primary_control', 'specificity_control', 'positive_control'), 'binding_regime': ('compartment',), 'binding_parameter_definition': ('proximity_observed', 'puncta_enrichment', 'antibody_species'), 'calibration_applicability': ('antibody_validation', 'blinded_quantification', 'statistical_test'), 'sampling_basis': ('cells_counted', 'replicates')}
FOLD_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest fold of the puncta per cell of the test over the negative control taken as a clear signal; the single-antibody and no-primary reactions give a low background of puncta, and a threefold excess is the usual minimum that papers call specific.
FOLD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: fold at or below which the test cannot be told from the negative control (equal puncta per cell is no signal): conflicting; in between the degree rises linearly in the LOG of the fold (a quotient of two mean counts, whose error is multiplicative, so equal ratio steps count equally; the same scale as the pull-down enrichment).
REDUCTION_FULL_AGREEMENT_PERCENT = 70.0  # EXPERT_REVIEW: smallest fall (percent) of the SPECIFIC puncta per cell (test minus negative control) after the knockdown, the knockout or the competition of one protein taken as a specific signal; a knockdown removes most but not all of a protein (siRNA typically 70 to 90 percent), so a fall of about two thirds or more shows the puncta depend on it. Read of the total puncta when the control is not stated or the test is not above it.
REDUCTION_ZERO_AGREEMENT_PERCENT = 20.0  # EXPERT_REVIEW: fall (percent) at or below which the puncta are not taken to depend on the protein (the cell-to-cell and the experiment-to-experiment variation of a puncta count is of this size, and an increase is a negative fall): conflicting; the degree falls linearly in the percent in between (the fall is an additive fraction of a count).
# EXPERT_REVIEW: number of cells in which the puncta were counted that gets full credit; the puncta per cell are skewed and vary widely between cells, so a mean of fewer than about
# fifty cells is unstable. Gradual (was a pass/fail minimum): below it the degree is sqrt(n / 50). Why this shape for a PLA: what the cell count buys is the precision of ONE number,
# the mean puncta per cell, and with a wide cell-to-cell spread the standard error of that mean falls as 1 / sqrt(n); sqrt(n / 50) is the precision of the mean of n cells relative to
# that of fifty (25 cells ~0.71, 10 cells ~0.45, 1 cell ~0.14), smooth, rising with n and reaching 1 at fifty. Fewer cells are weaker evidence, not evidence against.
CELLS_COUNTED_FULL_CREDIT = 50
SPREAD_Z_FULL = 2.0  # EXPERT_REVIEW: the difference test minus control, in standard errors of that difference, for full agreement; two standard errors is about the 95 percent interval of a mean (Cumming, Fidler & Vaux 2007 J Cell Biol 177:7, on reading error bars), the same value as the pull-down. The degree is linear in that distance from 0 (indistinguishable from the control) to this value and is used in addition to the researched fold values, never instead of them. A stated SD is divided by sqrt(replicate count) when the count is stated, else used as it is (never smaller than the SE: the conservative reading).
# EXPERT_REVIEW: number of independent experiments (separate experiments on separate days or cultures; cells and images of one sample do not count) that gets full credit.
# Gradual (was a pass/fail minimum): below it the degree is sqrt(n / 3) (owner rule: replicates mean precision in every assay). Why: the run-to-run variation of a PLA (ligation and
# rolling-circle amplification efficiency, antibody lot, imaging) is not reduced by counting more cells of one run, so only independent experiments average it down, and the standard
# error of the mean puncta difference over n of them falls as 1 / sqrt(n); 1 -> about 0.58, 2 -> about 0.82, full from three. (Replaces the earlier linear n / 3.)
REPLICATES_FULL_CREDIT = 3
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_pla_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_pla_punctum_is_not_an_attribution_fraction', 'total_signal': 'a_pla_punctum_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_pla_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_pla_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _linear(value):
    """The scale of a quantity whose error is additive (the fall of a count in percent)."""
    return value


def _degree(value, full, zero, scale=_linear):
    """1.0 at ``full`` (or beyond it), falling linearly in ``scale`` to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``.
    ``scale`` is monotone, so the side test is made on the value itself (before a log could see a value at or below 0)."""
    if (value - zero) * (full - zero) <= 0:
        return None
    return min(1.0, (scale(value) - scale(zero)) / (scale(full) - scale(zero)))


def _graded(refs, *degrees):
    """The verdict of a continuous comparison: conflicting where any degree is None, else supported with the smallest degree."""
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _standard_error(native, spread):
    """A stated spread as the standard error of its mean: a standard error as it is, a standard deviation over sqrt(replicate count) when the count is stated, else as it is (an SD is
    never smaller than the SE, so the conservative reading)."""
    if native['puncta_spread_kind'] == 'standard_error':
        return spread
    count = native['quantities']['replicate_count']
    return spread / sqrt(count['value']) if count['status'] == 'point' else spread


def _judge_enrichment(native):
    """The fold on the log scale between FOLD_ZERO_AGREEMENT and FOLD_FULL_AGREEMENT; when the spread of both counts is stated the degree is also at most the difference of the
    two means in standard errors of that difference over SPREAD_Z_FULL (rule 6: the paper's own uncertainty in addition, not instead); the weaker degree counts."""
    if native['puncta_control'] == 0:      # no division: any puncta over a control without puncta is full agreement
        degree = 1.0 if native['puncta_target'] > 0 else None
    else:
        # linear in the log of the fold: a quotient of two mean counts has a multiplicative error, so 1 -> 1.5 and 2 -> 3 are equal steps
        degree = _degree(native['puncta_fold_over_control'], FOLD_FULL_AGREEMENT, FOLD_ZERO_AGREEMENT, log)
    refs = native['puncta_refs']
    if degree is not None and native['puncta_spread_kind'] is not None:
        error_target, error_control = _standard_error(native, native['puncta_spread_target']), _standard_error(native, native['puncta_spread_control'])
        error = sqrt(error_target * error_target + error_control * error_control)      # the standard error of the difference of two independent means
        if error > 0:
            degree = min(degree, min(1.0, (native['puncta_target'] - native['puncta_control']) / error / SPREAD_Z_FULL))
        refs = list(dict.fromkeys(refs + native['spread_refs']))
    return _graded(refs, degree)


def _reduction_ends(native):
    """The full and zero ends of the fall in percent, scaled by the measured depletion of the protein when it is stated (capped at the full depletion): puncta of a proximity pair
    scale with the amount of the depleted partner, so a 50 percent depletion can give at most about a 50 percent fall and the researched ends (which hold for a full depletion) are
    taken in the same proportion. Not stated: the researched ends as they are."""
    depletion = native['protein_depletion_percent']
    scale = 1.0 if depletion is None else min(depletion, PERCENT_PER_FRACTION) / PERCENT_PER_FRACTION
    return REDUCTION_FULL_AGREEMENT_PERCENT * scale, REDUCTION_ZERO_AGREEMENT_PERCENT * scale


def _judge_specificity(native):
    """The fall of the SPECIFIC puncta, (test - knockdown) / (test - control) in percent, when the negative control is stated and the test is above it: the technical background
    of the control is in every well and no knockdown can remove it, so the total fall would punish a modest fold a second time. Otherwise the grader's fall of the total puncta
    (never larger than the specific fall, so the conservative reading)."""
    target, control = native['puncta_target'], native['puncta_control']
    if target is None or control is None or target <= control:
        return _graded(native['reduction_refs'] + native['depletion_refs'], _degree(native['puncta_reduction_percent'], *_reduction_ends(native)))
    knockdown = native['quantities']['puncta_per_cell_knockdown']['value']      # stated: the grader computed its fall from it
    specific_fall = (target - knockdown) / (target - control) * PERCENT_PER_FRACTION
    refs = list(dict.fromkeys(native['reduction_refs'] + native['puncta_refs'] + native['depletion_refs']))
    return _graded(refs, _degree(specific_fall, *_reduction_ends(native)))


def _judge_cells(native):
    # the precision of the mean puncta per cell relative to that of the researched number of cells (standard error ~ 1 / sqrt(n)); full credit at CELLS_COUNTED_FULL_CREDIT
    return _verdict('supported', native['cells_counted_refs'], min(1.0, sqrt(native['cells_counted'] / CELLS_COUNTED_FULL_CREDIT)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated: the count alone does not say independent experiments
    # the precision of the mean over n independent experiments relative to that of the researched number; full credit at REPLICATES_FULL_CREDIT
    return _verdict('supported', native['replicate_refs'], min(1.0, sqrt(native['replicate_count'] / REPLICATES_FULL_CREDIT)))


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
