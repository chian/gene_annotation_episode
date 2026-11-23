"""Pull-down / co-IP converter: turns the pull-down grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_pulldown.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding' and quantity_kind
'relative_binding_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
qualitative effect, and for every sheet component that a pull-down cannot honestly fill, the reason it stays null.

The effect is QUALITATIVE (the contract limit, stated plainly)
---------------------------------------------------------------
A pull-down or co-IP reports no binding constant. The sheet's effect operand is a number (a point or a bounded value with a unit), and the
binding merger pools effects on the nM scale of the binding parameter, so there is nowhere in the sheet to put "the prey was detected in the
eluate". The converter therefore fills NO effect and no variance: the sheet's measured_effect, effect_variance and effect_precision cells are
unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: not a KD, and not the fold
enrichment or the percent of the input put into the effect (they are not on the nM scale and cannot be pooled with a constant).
What the experiment does contribute is carried beside the sheet, in 'qualitative_effect':
  statement          'interaction_detected' (the prey is stated in the eluate of the specific capture), 'interaction_not_detected' (it is stated not to be)
                     or 'interaction_not_stated'
  support_refs       the spans of the fact that states it (empty when not stated)
  fold_enrichment    the stated fold enrichment over the control (a number), or None
and its interpretations (controls, regime, species, response definition, calibration, sampling) go into the sheet's interpretations like those of every other
experiment. The scoring reads 'qualitative_effect', without an effect to pool: its statement fixes the direction
(literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (pull-down criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------------
binding_controls              negative_control + positive_control + bait_minus_control + input_lane + reciprocal + competition + nuclease + specificity (the controls that
                              rule out a prey that sticks to beads, a tag artefact, a bridge of nucleic acid or an antibody that detects the wrong protein)
binding_regime                wash_stringency + wash_count + incubation (the strength of the wash a prey survives, and the time it had to bind)
binding_species               expression_level + direct_interaction (endogenous or overexpressed proteins, and purified proteins against a mixture)
binding_parameter_definition  prey_in_eluate + enrichment (what the response is: a prey in the eluate, and its signal over the control)
calibration_applicability     quantification (band intensities quantified and normalized)
sampling_basis                replicates
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). Every researched value below is KEPT as a named EXPERT_REVIEW constant; none is a pass/fail cut-off (owner rule,
A105_EXPERIMENT_SOP.md step 3). Each judge is 1.0 at or beyond its full-agreement value and falls to 0 at its zero-agreement value, on the scale its own physics
gives (_degree; the scale is named per judge, not shared by default):
  wash salt        linear in the square root of the salt (Debye screening; the same scale as the SEC resin salt); at or below the zero value degree 0, NOT conflicting
  wash detergent   linear in the percent (no detergent identity in the record, so no CMC-relative scale); none at all is degree 0, NOT conflicting.
                   The wash degree is the weaker of the two stated components (they remove different non-specific binders: charged and hydrophobic).
  wash_count       linear in the count (each wash removes about the same fraction of unbound prey: the count is the log-reduction); a stated count of none
                   is conflicting (the paper says the separation step was not done, like a fact answered no)
  incubation       linear in the log of the time (association times of unknown complexes span decades); at or below the zero value degree 0, NOT
                   conflicting; when the prey is stated DETECTED the incubation is full agreement (a too-short capture can only lose a prey, never invent one)
  enrichment       linear in the log of the fold (a ratio of two band or spectral intensities whose error is multiplicative); at or below 1 (no larger than the
                   control) conflicting: the paper's own numbers show no enrichment. When a spread (SEM, or SD) of the fold is stated the degree is also at most the
                   fold's distance above 1 in standard errors over SPREAD_Z_FULL (rule 6: the paper's own uncertainty in addition, not instead)
  positive_control a stated yes/no. Prey detected: full agreement. Not detected / not stated: yes full agreement, no conflicting (the negative is uninterpretable)
  replicates       sqrt(count / MIN_REPLICATES) (the precision of the mean band ratio), supported only when independence is stated yes, else unknown.
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and
the merger carries it per result). The qualitative effect is unchanged.

The owner's questions, asked of every researched value (2026-11-21; Q1 failure caught, Q2 general or lab-specific, Q3 absolute or relative and is the
relative quantity in the grader facts, Q4 how badly a wrong value misleads and does the shape reflect it, Q5 consistency with the other binding assays)
------------------------------------------------------------------------------------------------------------------------------------------------------
MIN_WASH_NACL_MM 150 / WASH_NACL_ZERO_AGREEMENT_MM 50
  Q1 a prey held to the beads or bait by charge alone surviving the wash (a false positive). Q2 general: physiological 150 mM is the standard co-IP / GST
  pull-down wash, 300-500 mM the stringent one (Harlow & Lane, Using Antibodies, 1999; Bonifacino et al., Curr Protoc Cell Biol 2001, unit 7.2). Q3 absolute
  is right (ionic screening is physics, not the paper's scale); but only NaCl is recorded, KCl or the buffer's own ionic strength is not (grader gap). Q4
  mild: the clean negative control, washed the same way, is what proves a prey is not sticky, so a gentle wash is a weaker design, not evidence against;
  conflicting at <= 50 mM was WRONG (a deliberate low-salt wash for a weak complex was made to oppose). Shape was linear in mM; screening goes as sqrt(I),
  so the first salt above 50 mM screens most: CHANGED to linear in sqrt. Q5 matches the SEC salt scale; low-salt is low credit, never conflicting.
MIN_WASH_DETERGENT_PERCENT 0.05 / WASH_DETERGENT_ZERO_AGREEMENT_PERCENT 0
  Q1 hydrophobic non-specific binders (abundant lysate proteins on beads and tube walls). Q2 general: 0.05-1 percent Triton X-100 / NP-40 / Tween-20 (same
  sources); 0.05 percent is about three times the CMC of Triton X-100 or NP-40 (about 0.015-0.02 percent). Q3 should be RELATIVE to the detergent's CMC
  (0.05 percent CHAPS is far below its CMC of about 0.5 percent; RIPA's SDS is far harsher): the detergent identity is not in the grader (gap); absolute kept.
  Q4 conflicting at 0 was WRONG: detergent-free washes are deliberate (AP-MS final washes, purified-protein pull-downs, detergent-sensitive complexes) and
  show nothing against the interaction; now degree 0. Linear kept (no identity, so no CMC knee can be placed). Q5 as the salt. (Owner question, not
  changed, for both wash values: for a NOT detected prey a very stringent wash, e.g. RIPA or 500 mM salt, can strip a real weak complex, yet the curve still
  rewards stringency there; no researched upper limit exists to soften around.)
MIN_WASHES 3 / WASH_COUNT_ZERO_AGREEMENT 0
  Q1 unbound prey left in the bead bed carried into the eluate. Q2 general: three to five washes (Harlow & Lane; Einarson, Cold Spring Harb Protoc 2007 for
  GST pull-down). Q3 the true scale is the bead-bed hold-up over the wash volume (about a tenth per wash); the volumes are not in the grader (gap, minor).
  Q4 linear in the count = linear in log residual background, so each wash counts the same: right. Zero washes stated is the separation not done: kept
  conflicting. KEPT.
MIN_INCUBATION_MIN 30 / INCUBATION_ZERO_AGREEMENT_MIN 5
  Q1 a capture too short for a slow or weak complex to form on the beads: a FALSE NEGATIVE, never a false positive. Q2 general: one hour to overnight at 4 C is
  usual; 30 min is the short end (Harlow & Lane; Bonifacino et al.). Q3 relative to the complex's association rate, unknown for a pull-down; the
  temperature is in the record (native quantities) but the 30 min reference is already the 4 C case, so a room-temperature incubation is judged
  conservatively; absolute kept. Q4 the old curve rewarded long incubation also for a DETECTED prey and made a detected prey after 5 min CONFLICTING: wrong
  (a short capture cannot invent a band). CHANGED: detected -> full agreement; not detected or not stated -> linear in log time (5 -> 10 min doubles the
  time and matters; 25 -> 30 min does not), degree 0 at 5 min, never conflicting. (Owner question, not changed: overnight incubation of a lysate raises
  post-lysis reassociation, Mili & Steitz, RNA 2004; no researched upper limit.)
MIN_FOLD_ENRICHMENT 3 / ENRICHMENT_ZERO_AGREEMENT_FOLD 1
  Q1 a prey present in the eluate at the control's level (background, not capture). Q2 general for AP-MS (fold-change scoring with cut-offs of about 2-10:
  Choi et al., SAINT, Nat Methods 2011; Mellacheruvu et al., CRAPome, Nat Methods 2013); for western densitometry 3x is common practice, no guideline.
  Q3 already relative to the paper's own control signal; and now also relative to the fold's own stated spread (rule 6; the grader records the SD and the SEM
  of the fold since the 2026-11-21 gap pass, SPREAD_Z_FULL 2 standard errors, the weaker degree counts). Q4 linear in fold gave 1 -> 1.5 a quarter of the credit of 1.5 -> 3 although both are ratio steps on a multiplicative error: CHANGED to linear
  in log fold (2 fold: 0.50 -> 0.63). <= 1 stays conflicting (a signal no larger than the paper's own control, SOP rule 5). Q5 the PLA, proximity and Y2H
  fold ramps are still linear in the fold (not in this file's scope; same question applies).
POSITIVE CONTROL (a fact; added for the range-review gap 'was a positive control detected under the same wash')
  Q1 a negative result (prey not detected) from a failed wash, blot, antibody or bead lot: without a positive control a missing prey may be a failed assay.
  Q2 general practice for pull-down and co-IP (Harlow & Lane 1999; a known interacting pair taken through the same wash and detection). Q3 a yes/no fact: no scale.
  Q4 an unstated control is unknown (not opposed); a stated failure of it is the paper itself showing the negative uninterpretable: conflicting (rule 5); for a DETECTED
  prey the control is not needed. Q5 the same idea as the empty-bait control (negative_control): a stated no conflicts, silence is unknown.
MIN_REPLICATES 3
  Q1 a band seen once (blot-to-blot variation, a one-off sticky lot of beads). Q2 general: three independent experiments (Cumming, Fidler & Vaux, J Cell
  Biol 2007; journal reporting standards). Q3 absolute count is right. Q4 sqrt(n/3): one experiment 0.58, two 0.82; a single experiment with its controls
  already shows the band, so steep loss below one is not warranted. Q5 same as FP, FRET, AlphaScreen, CETSA, proximity: KEPT.
Unknown weight (per assay, SOP step 3 rule 4; held in literature_row_contract.WEIGHT_UNKNOWN_BY_TYPE, NOT in any degree here)
  A pull-down readout is qualitative (a band) and only relative to its own controls; there is no reference range to trust without the paper; an unstated
  negative control leaves a sticky prey (the dominant false positive, CRAPome) indistinguishable from a binder; assuming it fine when it is not counts a
  bead binder as an interaction. Consistent with Y2H 0.5, PLA 0.5, proximity 0.55: about 0.5 for pull-down. The contract still holds the pending 0.9 (gap:
  not editable here).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree
(the continuous comparisons above); direct leaves it unchanged. Support never changes a status. The qualitative effect (its statement and
support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity, matrix_interference,
background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, variance_correspondence) are not selected, and
the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the prey,
immobilized_preparation_ref = the bait (held on the beads), surface_ref = None (a bead is not a surface reference), dataset_ref = the dataset.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_pulldown_converted'
CRITERIA_MAP = {'binding_controls': ('negative_control', 'positive_control', 'bait_minus_control', 'input_lane', 'reciprocal', 'competition', 'nuclease', 'specificity'), 'binding_regime': ('wash_stringency', 'wash_count', 'incubation'), 'binding_species': ('expression_level', 'direct_interaction'), 'binding_parameter_definition': ('prey_in_eluate', 'enrichment'), 'calibration_applicability': ('quantification',), 'sampling_basis': ('replicates',)}
MIN_WASH_NACL_MM = 150.0  # EXPERT_REVIEW: lowest sodium chloride (mM) of the wash buffer that still removes weakly and electrostatically stuck proteins, for full agreement (physiological salt; washes with less keep sticky preys, and usual pull-down washes use 150 to 500 mM).
WASH_NACL_ZERO_AGREEMENT_MM = 50.0  # EXPERT_REVIEW: sodium chloride (mM) at or below which the sheet gives the wash no credit for removing electrostatic binders (degree 0, not conflicting: a low-salt wash is a weaker design, and the negative control washed the same way shows stickiness); a third of physiological salt or less keeps them; in between the degree rises linearly in the square root of the salt (Debye screening grows as sqrt of the ionic strength).
MIN_WASH_DETERGENT_PERCENT = 0.05  # EXPERT_REVIEW: lowest detergent (percent) of the wash buffer for full agreement; below this the beads and the tube walls keep hydrophobic non-specific binders (usual washes use 0.05 to 1 percent of Triton X-100, NP-40 or Tween-20; about three times their CMC).
WASH_DETERGENT_ZERO_AGREEMENT_PERCENT = 0.0  # EXPERT_REVIEW: detergent (percent) at or below which the sheet gives the wash no credit for removing hydrophobic binders (degree 0, not conflicting: detergent-free washes are a deliberate choice, e.g. AP-MS final washes or detergent-sensitive complexes); in between the degree rises linearly in the percent.
MIN_WASHES = 3  # EXPERT_REVIEW: fewest washes of the beads after the capture for full agreement; fewer leave unbound prey on the beads (usual protocols wash three to five times). Below it the degree falls linearly to WASH_COUNT_ZERO_AGREEMENT, no step.
WASH_COUNT_ZERO_AGREEMENT = 0  # EXPERT_REVIEW: washes at or below which the sheet takes the unbound prey as not removed at all (conflicting): a stated count of none is the paper saying it did not wash. Linear between: each wash leaves roughly the same fraction (the liquid held by the bead bed over the wash volume, about a tenth) of the unbound prey, so the log of the residual background falls in proportion to the number of washes, and credit is the share of the researched three-wash reduction reached.
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: an incubation of bait with prey of at least this many minutes is full agreement; a shorter one is too short for a slow or weak interaction to be captured (usual protocols incubate one hour to overnight, at 4 C). It guards a NOT detected (or not stated) prey only: a detected prey is full agreement at any time.
INCUBATION_ZERO_AGREEMENT_MIN = 5.0  # EXPERT_REVIEW: incubation (minutes) at or below which the sheet gives a negative no credit (only an immediate strong interaction could have been captured): degree 0, not conflicting; in between the degree rises linearly in the log of the time (association times of unknown complexes span decades, so doubling a short time matters and adding minutes to a long one does not).
MIN_FOLD_ENRICHMENT = 3.0  # EXPERT_REVIEW: smallest signal of the prey in the specific capture over the control capture for full agreement; below about threefold the prey is hard to tell from the control background (the usual cut-off of affinity-purification mass spectrometry scoring is two to ten fold).
ENRICHMENT_ZERO_AGREEMENT_FOLD = 1.0  # EXPERT_REVIEW: fold enrichment at or below which the sheet takes the prey as not enriched over the control (conflicting: the paper's own signal is no larger than its control); in between the degree rises linearly in the log of the fold (a ratio of intensities with multiplicative error).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days, preparations or cultures) for full agreement; lanes or wells of one experiment do not count. Below it the degree is sqrt(count / MIN_REPLICATES), no step: one experiment with its controls already shows the band (about 0.58), and each independent repeat adds less, as the uncertainty of a band ratio falls as 1/sqrt(count).
SPREAD_Z_FULL = 2.0  # EXPERT_REVIEW: the fold's distance above 1 (no enrichment), in standard errors of its mean, for full agreement; two standard errors is about the 95 percent interval of a mean (Cumming, Fidler & Vaux, J Cell Biol 2007, on reading error bars). The degree is linear in that distance from 0 (a fold indistinguishable from 1) to this value; it is used in addition to the researched fold values above, never instead of them. A stated SEM is used as it is; a stated SD is divided by sqrt(count) when the count of independent experiments is stated, and used as it is when it is not (an SD is never smaller than the SEM, so this is the conservative reading).
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_pulldown_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_pulldown_band_is_not_an_attribution_fraction', 'total_signal': 'a_pulldown_band_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_pulldown_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_pulldown_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _enrichment(native):
    operand = native['quantities']['fold_enrichment']
    return operand['value'] if operand['status'] == 'point' else None


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _linear(value):
    """The scale of a quantity whose effect is proportional to it (the detergent percent; the wash count, itself a log-reduction)."""
    return value


def _degree(value, full, zero, scale):
    """0 at or below the zero-agreement value, 1.0 at or above the full-agreement value, linear in ``scale`` in between (the judge names the scale and why)."""
    if value <= zero:
        return 0.0
    return min(1.0, (scale(value) - scale(zero)) / (scale(full) - scale(zero)))


def _judge_wash(native):
    """Each stated component judged on its own scale (salt: sqrt, Debye screening; detergent: linear); the weaker degree, the refs of both. Never conflicting:
    a gentle wash is a weaker design, and the negative control washed the same way is what shows a sticky prey."""
    parts = []
    if native['nacl_wash_mM'] is not None:
        parts.append((_degree(native['nacl_wash_mM'], MIN_WASH_NACL_MM, WASH_NACL_ZERO_AGREEMENT_MM, math.sqrt), native['nacl_wash_refs']))
    if native['detergent_percent'] is not None:
        parts.append((_degree(native['detergent_percent'], MIN_WASH_DETERGENT_PERCENT, WASH_DETERGENT_ZERO_AGREEMENT_PERCENT, _linear), native['detergent_wash_refs']))
    return _verdict('supported', list(dict.fromkeys(r for _, refs in parts for r in refs)), min(degree for degree, _ in parts))


def _judge_wash_count(native):
    """Linear in the count up to MIN_WASHES: each wash removes about the same fraction of the unbound prey, so the count is the log-reduction of the background.
    A stated count of none is conflicting: the paper says the separation step was not done."""
    if native['wash_count'] <= WASH_COUNT_ZERO_AGREEMENT:
        return _verdict('conflicting', native['wash_count_refs'])
    return _verdict('supported', native['wash_count_refs'], _degree(native['wash_count'], MIN_WASHES, WASH_COUNT_ZERO_AGREEMENT, _linear))


def _judge_incubation(native):
    """A detected prey: full agreement (a short capture can only lose a prey, never invent a band). Otherwise linear in log time up to MIN_INCUBATION_MIN,
    degree 0 at or below INCUBATION_ZERO_AGREEMENT_MIN, never conflicting (a short capture weakens a negative; it shows nothing against an interaction)."""
    if native['interaction'] == 'detected':
        return _verdict('supported', native['incubation_refs'], 1.0)
    return _verdict('supported', native['incubation_refs'], _degree(native['incubation_min'], MIN_INCUBATION_MIN, INCUBATION_ZERO_AGREEMENT_MIN, math.log))


def _standard_error(native):
    """The stated spread of the fold as a standard error of its mean with its refs, or (None, []) when none is stated: the SEM as it is, else the SD over sqrt(count) when the count is stated, else the SD."""
    if native['fold_enrichment_sem'] is not None:
        return native['fold_enrichment_sem'], native['fold_enrichment_sem_refs']
    if native['fold_enrichment_sd'] is not None:
        count = native['replicate_count']
        return native['fold_enrichment_sd'] / (1 if count is None else math.sqrt(count)), native['fold_enrichment_sd_refs'] + ([] if count is None else native['replicate_refs'])
    return None, []


def _judge_enrichment(native):
    """Linear in log fold up to MIN_FOLD_ENRICHMENT; conflicting at or below ENRICHMENT_ZERO_AGREEMENT_FOLD (the signal is no larger than the paper's own control).
    When a spread of the fold is stated, the degree is also limited by the fold's distance above 1 in standard errors (linear up to SPREAD_Z_FULL): the weaker of the two."""
    fold = native['fold_enrichment']
    if fold <= ENRICHMENT_ZERO_AGREEMENT_FOLD:
        return _verdict('conflicting', native['fold_enrichment_refs'])
    degree = _degree(fold, MIN_FOLD_ENRICHMENT, ENRICHMENT_ZERO_AGREEMENT_FOLD, math.log)
    error, refs = _standard_error(native)
    if error is not None:
        degree = min(degree, min(1.0, (fold - ENRICHMENT_ZERO_AGREEMENT_FOLD) / error / SPREAD_Z_FULL))
    return _verdict('supported', list(dict.fromkeys(native['fold_enrichment_refs'] + refs)), degree)


def _judge_positive_control(native):
    """A positive control matters only for a prey that is not detected (a missing prey is a real absence only if the same wash and detection could show a known pair).
    Prey detected: full agreement (no degree) whatever the control (a failed positive control cannot invent a band; the same reasoning as the incubation). Not detected or not stated:
    the control gave its expected band (yes) is full agreement; it did not (no) is conflicting: the paper itself shows the negative is uninterpretable."""
    if native['interaction'] == 'detected' or native['positive_control'] == 'yes':
        return _verdict('supported', native['positive_control_refs'])      # a fact: full agreement carries no degree
    return _verdict('conflicting', native['positive_control_refs'])


def _judge_replicates(native):
    """Independent experiments stated yes: sqrt(count / MIN_REPLICATES), full at MIN_REPLICATES; independence not stated: unknown (a stated no is the grader's conflict)."""
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])
    return _verdict('supported', native['replicate_refs'], math.sqrt(min(native['replicate_count'], MIN_REPLICATES) / MIN_REPLICATES))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('positive_control', 'positive_control_recorded_for_the_sheet'): _judge_positive_control, ('wash_stringency', 'wash_recorded_for_the_sheet'): _judge_wash, ('wash_count', 'wash_count_recorded_for_the_sheet'): _judge_wash_count, ('incubation', 'incubation_recorded_for_the_sheet'): _judge_incubation,
          ('enrichment', 'fold_enrichment_recorded_for_the_sheet'): _judge_enrichment, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def convert_pulldown(graded):
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
    qualitative_effect = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'fold_enrichment': _enrichment(native)}
    return {'version': VERSION, 'experiment_type': 'pulldown', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'qualitative_effect': qualitative_effect, 'null_components': dict(NULL_REASONS), 'direction_field_support': (native['support']['prey_in_eluate'] or [None])[0] if native['interaction'] is not None else None}
