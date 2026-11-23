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
The scoring reads 'statement' (the direction, literature_direction.py) and 'support_refs' (the row, literature_row.py) of 'qualitative_effect'.

Criteria mapping (Y2H criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              bait_autoactivation + prey_autoactivation + non_interacting_control + positive_control + nonselective_growth + reciprocal_orientation (the controls that show the reporter was activated by the interaction
                              of these two proteins and not by the bait or the prey alone, by a sticky or unrelated partner, or by a failure of the system or of the plasmids)
binding_species               expression_verified (the fusions that are tested are expressed in yeast)
binding_parameter_definition  interaction_observed + reporter_concordance + reporter_fold (what the response is: reporter activation, by more than one reporter, and how far above the control)
sampling_basis                replicates
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). The researched values
are kept as EXPERT_REVIEW constants; no judgement cuts pass/fail at them (owner rule, A105_EXPERIMENT_SOP.md step 3):
  reporter_fold  (kept ramp ends; shape changed in the range review) supported with a degree of 1.0 from its full-agreement limit (REPORTER_FOLD_FULL_AGREEMENT), the degree falling linearly IN THE LOG OF THE FOLD
                 to 0 at its zero-agreement limit (REPORTER_FOLD_ZERO_AGREEMENT), and conflicting (no degree) at or below that limit (the paper's own pair activity cannot be told from its own negative control).
  replicates     (softened from a lone minimum) when the independence is stated yes: degree min(1, sqrt(n / MIN_REPLICATES)), the owner's one shape for replicates in every assay (the reason is at
                 _judge_replicates), no step and no conflicting for a low count; unknown when the independence is not stated (a stated no is the grader's conflicting).
A degree is attached when it is below full credit (the reporter_fold ramp attaches it always, as before). A sheet criterion that is supported carries the smallest degree of its members that
have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0, implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it
reads. A supported member criterion whose weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. The
qualitative effect (its statement and support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no
counterpart here are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the prey, immobilized_preparation_ref = the bait, surface_ref = None (a yeast cell is not a surface reference), dataset_ref = the dataset.

Gap pass (2026-11-21, the range review's grader gaps; the five gaps and what was done are in the report of that pass; numbers below are named EXPERT_REVIEW constants)
  1 spread: reporter_fold is also limited by the fold's distance above REPORTER_FOLD_ZERO_AGREEMENT in standard errors of the fold (SPREAD_Z_FULL, as in the pull-down; the weaker degree counts; propagation of the relative errors of the two activities).
  2 growth titre: a growth-only paper has the titre ratio (dilution factor of the most dilute growing spot, pair over negative control), the same log ramp (GROWTH_TITRE_FULL_AGREEMENT 100 to GROWTH_TITRE_ZERO_AGREEMENT 1, conflicting at or below 1).
    The fold and the titre are each not applicable when the other is the paper's read-out. A stated negative interaction drops both (the direction carries it).
  3 3-AT: a bait-alone test at a higher 3-AT than the scoring's gets the degree scoring / test (3-AT is a competitive inhibitor, stringency proportional to concentration); at or below it, full agreement.
  4 'no' as 'not done': the form now asks no only for a test that was done and went the other way. A stated no: reciprocal orientation and second reporter are partial credit ONE_OF_TWO_SHARE (never conflicting); a failed positive control is conflicting only for a
    result that is not an observed interaction (as the pull-down); a fusion not expressed stays conflicting (the paper itself shows against the standard).
  5 stated negative: interaction_observed is not applicable when the answer is no (it was counted twice: as the direction and as a failed quality criterion).

Range review (SOP step 3, 2026-11-21; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative scale, Q4 how badly a
wrong value misleads and whether the shape follows, Q5 consistency; citations from memory, not checked on the web)
--------------------------------------------------------------------------------------------------------------------------------
REPORTER_FOLD_FULL_AGREEMENT 10 / REPORTER_FOLD_ZERO_AGREEMENT 2
  Q1 a 'positive' whose lacZ activity is within the leak of the reporter: a weakly autoactivating or sticky fusion, a leaky reporter, a mixed colony; the
  reporter activation the paper calls an interaction cannot be told from the empty-vector background. Q2 NOT a guideline: no method paper fixes a fold. The
  reporters differ by orders of magnitude in sensitivity (number of operators, GAL1 / GAL2 / MEL1 promoters, plasmid copy number; Estojak, Brent & Golemis 1995,
  Mol Cell Biol 15:5820, also show lacZ activity tracks affinity, so a weak real pair gives a low fold), so 10 is reporter- and lab-specific practice (known
  positive pairs give tens to hundreds of fold); 2 is a noise statement (the empty-vector background varies about twofold between transformants and days),
  likewise not from a guideline. Q3 already relative to the paper's own negative control, which is the right base. Considered and REJECTED: rescaling the
  full end by the paper's positive-control window (beta_galactosidase_positive_control is in the grader's native quantities): the window measures the reporter's
  sensitivity, while this criterion asks whether the pair stands out of the background NOISE, which a weaker reporter does not shrink. The right relative scale
  is the paper's own spread of the activities (SD / SEM and n of the pair and of the control), as the pull-down fold uses since its gap pass: NOT collected by
  the grader (grader gap). Q4 a too-high full end only lowers the credit of a weak but real pair inside binding_parameter_definition (the direction comes from
  the statement, not from this degree); a too-low zero end would let a leak count as activation. The fold is a ratio of two Miller-unit activities whose
  error is multiplicative (the twofold noise is itself a fold), so equal RATIO steps should count equally; linear in the fold gave 2 -> 3 (out of the noise)
  an eighth of the credit and 9 -> 10 the same eighth: WRONG shape. CHANGED to linear in log fold (6-fold 0.50 -> 0.68; 4-fold 0.25 -> 0.43; geometric middle
  4.47-fold is 0.5): steep in fold just above the noise, gentle near ten. Values kept. Conflicting at <= 2 KEPT: the far zero end of a researched ramp (SOP
  consistency rule 2), the paper's own numbers within its background's known variation; owner question: with the spread collected, the zero end would be the
  paper's own noise and conflicting could move to fold <= 1 (no larger than the control, as pull-down, PLA and proximity). Q5 now the same log-fold shape as the
  pull-down enrichment (the PLA and proximity fold ramps are still linear in the fold; outside this file).
MIN_REPLICATES 3
  Q1 a reading of one transformation: a clone with a spontaneous reporter-activating mutation, a rearranged plasmid, a mixed colony, plating density. Q2 general:
  three independent experiments (Vaux, Fidler & Cumming 2012, EMBO Rep 13:291); for Y2H a retest by fresh co-transformation is standard pipeline practice (Braun
  et al. 2009, Nat Methods 6:91; Dreze et al. 2010, Methods Enzymol 470:281). Q3 an absolute count is right (the precision of a mean scales with nothing the paper
  states). Q4 sqrt(n / 3): 1 -> 0.58, 2 -> 0.82; a single directed co-transformation with its controls already shows the growth, so a steeper loss is not
  warranted; a count of 3 vs 4 changes little, as the curve says. Q5 the owner's one replicate shape (min(1, sqrt(n / MIN_REPLICATES))), unknown without stated
  independence, never conflicting for a count. KEPT.
No unknown weight is used inside any degree here (the per-type weight lives in literature_row_contract.WEIGHT_UNKNOWN_BY_TYPE['y2h'] = 0.60 with overrides).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_y2h_converted'
CRITERIA_MAP = {'binding_controls': ('bait_autoactivation', 'prey_autoactivation', 'non_interacting_control', 'positive_control', 'nonselective_growth', 'reciprocal_orientation'), 'binding_species': ('expression_verified',), 'binding_parameter_definition': ('interaction_observed', 'reporter_concordance', 'reporter_fold', 'growth_titre'), 'sampling_basis': ('replicates',)}
REPORTER_FOLD_FULL_AGREEMENT = 10.0  # EXPERT_REVIEW: smallest fold of the beta-galactosidase activity of the pair over the negative control (empty vectors) that the sheet takes as a clear reporter activation; positive pairs usually give ten-fold or more over the empty-vector background, and the background itself varies by about two-fold between experiments.
REPORTER_FOLD_ZERO_AGREEMENT = 2.0  # EXPERT_REVIEW: fold at or below which the activity of the pair cannot be told from the negative control (the between-experiment variation of the background); conflicting; the degree rises linearly in the log of the fold in between (a ratio of two activities with multiplicative error; range review).
SPREAD_Z_FULL = 2.0  # EXPERT_REVIEW: the fold's distance above the zero-agreement fold (REPORTER_FOLD_ZERO_AGREEMENT), in standard errors of the fold, for full agreement; two standard errors is about the 95 percent interval of a mean (Cumming, Fidler & Vaux, J Cell Biol 2007, on reading error bars); the same value and use as the pull-down converter (consistency). A stated SEM is used as it is; a stated SD is divided by sqrt(count) when the count of independent experiments is stated, else used as it is (an SD is never smaller than the SEM: the conservative reading). Used in addition to the researched fold ends, never instead of them (SOP step 3, rule 6).
GROWTH_TITRE_FULL_AGREEMENT = 100.0  # EXPERT_REVIEW: smallest ratio of the dilution factor of the most dilute growing spot of the pair over that of the negative control that the sheet takes as a clear growth difference; dilution series are made in ten-fold steps, one step is within the spot-to-spot variation of a drop test, and two steps (a hundred-fold) are a difference no spot variation explains. Lab practice, not from a guideline.
GROWTH_TITRE_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio at or below which the pair grows no further along the dilution series than the negative control (no difference); conflicting; the degree rises linearly in the log of the ratio in between (dilution is geometric, like the fold).
ONE_OF_TWO_SHARE = 0.5  # EXPERT_REVIEW: the share of the tests that confirm when a stated no means one of two tests agreed: the pair seen in one of the two orientations, or one of the two reporters active. No literature value is claimed: it is the observed fraction, kept as the one partial credit for 'one of two'; owner question whether to use a researched fraction instead (single-orientation detection of true pairs is common in large Y2H screens; Braun et al. 2009, Nat Methods 6:91, cited from memory).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate transformations or experiments on separate days); spots or colonies of one plate do not count. Full credit from it; below it partial credit, min(1, sqrt(n / MIN_REPLICATES)) (see _judge_replicates), not a fail.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_y2h_test_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_y2h_reporter_is_not_an_attribution_fraction', 'total_signal': 'a_y2h_reporter_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_y2h_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_y2h_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _log_degree(value, full, zero):
    """1.0 at ``full`` (or beyond it), falling linearly in the log of the value to 0 at ``zero`` (full above zero; all positive); None at or below ``zero``.
    Log because the value judged is a fold of two activities whose error is multiplicative: equal ratio steps count equally (range review)."""
    if value <= zero:
        return None
    return min(1.0, math.log(value / zero) / math.log(full / zero))


def _graded(refs, *degrees):
    """The verdict of a continuous comparison: conflicting where any degree is None, else supported with the smallest degree."""
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _standard_error(native, prefix):
    """The stated spread of one activity ('interaction' or 'negative_control') as a standard error of its mean: the SEM as it is, else the SD over sqrt(count) when the count is stated, else the SD; None when no spread is stated."""
    spread = native['activity_spread']
    if 'beta_galactosidase_' + prefix + '_sem' in spread:
        return spread['beta_galactosidase_' + prefix + '_sem']
    if 'beta_galactosidase_' + prefix + '_sd' in spread:
        count = native['replicate_count']
        return spread['beta_galactosidase_' + prefix + '_sd'] / (1 if count is None else math.sqrt(count))
    return None


def _fold_standard_error(native):
    """The standard error of the fold by propagation of the relative errors of the two activities (a quotient; independent errors), using each one's stated spread; an unstated spread counts as 0 (the stated one alone is the information); None when none is stated."""
    errors = {prefix: _standard_error(native, prefix) for prefix in ('interaction', 'negative_control')}
    if all(error is None for error in errors.values()):
        return None
    relative = math.hypot(*(error / native['quantities']['beta_galactosidase_' + prefix]['value'] for prefix, error in errors.items() if error is not None))      # sqrt of the sum of the squared relative errors
    return native['reporter_fold'] * relative


def _judge_fold(native):
    # absolute fold over the paper's own negative control; the positive-control window is deliberately not a scale here (range review, Q3).
    # When the paper states a spread of the activities, the degree is also limited by the fold's distance above the zero-agreement fold in standard errors (linear up to SPREAD_Z_FULL): the weaker of the two.
    if native['interaction'] == 'not_detected':
        return _verdict('not_applicable', [])      # a stated negative: the fold is part of the result, which the direction carries, not a quality of it
    degree = _log_degree(native['reporter_fold'], REPORTER_FOLD_FULL_AGREEMENT, REPORTER_FOLD_ZERO_AGREEMENT)
    error = _fold_standard_error(native)
    if degree is not None and error is not None:
        degree = min(degree, min(1.0, (native['reporter_fold'] - REPORTER_FOLD_ZERO_AGREEMENT) / error / SPREAD_Z_FULL))
    return _graded(list(dict.fromkeys(native['reporter_fold_refs'] + (native['activity_spread_refs'] if error is not None else []))), degree)


def _judge_growth_titre(native):
    # a growth read-out on a dilution series: the same log ramp as the fold, on the titre ratio (dilution is geometric); a stated negative is not judged here (as the fold)
    if native['interaction'] == 'not_detected':
        return _verdict('not_applicable', [])
    return _graded(native['growth_titre_refs'], _log_degree(native['growth_titre'], GROWTH_TITRE_FULL_AGREEMENT, GROWTH_TITRE_ZERO_AGREEMENT))


def _judge_bait_alone_three_at(native):
    """The bait-alone test (no growth) at a 3-AT concentration no higher than the scoring's is at least as permissive, so its silence covers the scoring: full agreement. At a HIGHER concentration, no growth there says less about the scoring
    medium; 3-AT is a competitive inhibitor of the HIS3 product, so the stringency is proportional to its concentration: the degree is the scoring's concentration over the test's (a test at twice the scoring concentration shows half as much).
    Never conflicting (the paper shows the bait inactive)."""
    bait, scoring = native['bait_alone_three_at_mM'], native['scoring_three_at_mM']
    return _verdict('supported', native['bait_alone_three_at_refs'], min(1.0, scoring / bait) if bait > scoring else None)


def _judge_positive_control(native):
    """A known pair that did not activate (stated no): when the pair itself is stated to interact, its own growth stands (a failed positive control cannot invent a growth; the same reasoning as the pull-down); otherwise the negative
    result is uninterpretable (the system did not work): conflicting."""
    if native['interaction'] == 'detected':
        return _verdict('supported', native['positive_control_refs'])
    return _verdict('conflicting', native['positive_control_refs'])


def _judge_one_of_two(refs_key):
    def judge(native):
        return _verdict('supported', native[refs_key], ONE_OF_TWO_SHARE)      # seen in one of two: partial credit, never conflicting
    return judge


def _judge_replicates(native):
    # Shape (owner rule, the same in every assay): min(1, sqrt(n / MIN_REPLICATES)): 1 about 0.58, 2 about 0.82, then full. Replicates mean
    # precision: a Y2H reading (growth on the selective medium, reporter on or off, the reporter fold) varies from transformation to transformation
    # (a clone with a spontaneous reporter-activating mutation, a rearranged plasmid, a mixed colony, plating density), and the standard error of
    # what n independent transformations show together falls as 1 / sqrt(n). (This replaces the earlier linear n / MIN_REPLICATES, which treated
    # each reproduction as an equal share.) A single experiment, a real observation, keeps partial credit; a low count is never conflicting.
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated: the count alone does not say independent experiments
    share = min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES))
    return _verdict('supported', native['replicate_refs'], share if share < 1.0 else None)      # full credit carries no degree, as before


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('reporter_fold', 'reporter_fold_recorded_for_the_sheet'): _judge_fold, ('growth_titre', 'growth_titre_recorded_for_the_sheet'): _judge_growth_titre, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates,
          ('bait_autoactivation', 'bait_alone_three_at_recorded_for_the_sheet'): _judge_bait_alone_three_at, ('positive_control', 'positive_control_failed_recorded_for_the_sheet'): _judge_positive_control,
          ('reciprocal_orientation', 'one_orientation_only_recorded_for_the_sheet'): _judge_one_of_two('reciprocal_orientation_refs'), ('reporter_concordance', 'one_reporter_only_recorded_for_the_sheet'): _judge_one_of_two('more_than_one_reporter_refs')}


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
        judged = [(m, _criterion(graded, m)) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        graded_members = [apply_support(verdict, native['support'][m]) for m, verdict in judged if verdict['status'] != 'not_applicable']      # a judge may drop a member (a stated negative is not judged by the fold)
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
