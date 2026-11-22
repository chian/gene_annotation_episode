"""Co-localization converter: turns the co-localization grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_colocalization.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding' and quantity_kind 'relative_binding_response'), the sheet itself
(grade_assay run on it), the dependence keys the merger needs, the qualitative effect, and for every sheet component that a co-localization cannot honestly fill, the reason it stays null.

The effect is QUALITATIVE (the contract limit, stated plainly)
---------------------------------------------------------------
A co-localization reports where fluorescence lies (a fraction of the scored objects, a Pearson coefficient, an enrichment), no binding constant; none of them is a KD and none pools with one. The converter fills NO effect and no variance: the sheet's
measured_effect, effect_variance and effect_precision cells are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is
invented. What the experiment contributes is carried beside the sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'enrichment_ratio'}):
  statement                'interaction_detected' (a co-localization or a recruitment is stated), 'interaction_not_detected' (none is stated) or 'interaction_not_stated'
  support_refs             the spans of the fact that states it (empty when not stated)
  enrichment_ratio         the stated enrichment of the signal at the site of the partner over the signal elsewhere, or None
and its interpretations go into the sheet's interpretations like those of every other experiment. The merger's contract is not changed.

Criteria mapping (co-localization criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------------------
binding_controls              specificity_control (an unrelated protein or the tag alone is not recruited, and the localization is lost without the partner)
binding_regime                directness (a heterologous host or purified proteins leave no native bridge; a binding-region mutant that does not co-localize; the protein follows the partner when it is moved)
binding_parameter_definition  colocalization_observed + colocalization_readout (what the response is: the protein found where the partner is, and its fraction, Pearson coefficient or enrichment)
calibration_applicability     expression_validity (the proteins are near the native level, not for purified proteins, and the tag does not change the localization or the function)
sampling_basis                objects_counted + replicates
The researched values are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). OWNER RULE (step 3 of A105_EXPERIMENT_SOP.md): each value is the centre of a gradual curve, never a pass/fail cut.
A continuous comparison is supported with a degree of 1.0 up to its full-agreement limit, the degree falling to 0 at its zero-agreement limit on the scale the judge names, and
conflicting (no degree) at or beyond that limit, where the paper's own numbers show the standard is not met. colocalization_readout judges each stated number on its own
ramp (fraction FRACTION_FULL_AGREEMENT_PERCENT / FRACTION_ZERO_AGREEMENT_PERCENT, linear; Pearson PEARSON_FULL_AGREEMENT / PEARSON_ZERO_AGREEMENT, linear; enrichment
ENRICHMENT_FULL_AGREEMENT / ENRICHMENT_ZERO_AGREEMENT, linear in the LOG of the ratio) and takes the BEST degree of the stated numbers: the three are different views of one result and a
coefficient is known to read low for a small focus in a large cell, so a weak coefficient beside a strong fraction does not lower it; it is conflicting only when EVERY stated number is
at or beyond its zero end (the paper's own numbers all show no co-localization). The two counts are gradual around their values:
  objects_counted  n cells, foci or droplets: degree = min(1, sqrt(n / OBJECTS_COUNTED_FULL_CREDIT)), the precision of the mean over n objects relative to that over the researched number.
  replicates       n independent experiments: degree = min(1, sqrt(n / REPLICATES_FULL_CREDIT)) when their independence is stated yes (owner rule: replicates mean precision in every assay);
                   unknown when the independence is not stated (a stated no is the grader's conflicting).
A small count is weaker evidence, not evidence against: it is supported with a partial degree, never conflicting. A sheet criterion that is supported carries the smallest degree
of its members that have one.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0, implied 0.7, about_something_else 0.3)
and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose weakest read field is implied or about_something_else gets that factor as its
degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. The qualitative effect is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is
not selected. Sheet criteria with no counterpart here are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first protein, immobilized_preparation_ref = the second protein,
surface_ref = None (a cell, a droplet or a membrane is not a surface reference), dataset_ref = the dataset.

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, confirmed by the owner 2026-11-22, and every one is from the drafter's memory of imaging practice and the
literature, NOT web-verified and NOT checked against a method paper; verify before relying on any of them. The owner's questions are asked of each value (Q1 failure caught, Q2 general or
lab-specific, Q3 absolute or relative, Q4 how badly a wrong value misleads, Q5 consistency with the other binding assays).
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ENRICHMENT_FULL_AGREEMENT 3 / ENRICHMENT_ZERO_AGREEMENT 1 (colocalization_readout, enrichment)
  Q1 a signal at the partner's site that is no larger than elsewhere: no recruitment. Q2 the zero end is physics (a ratio of 1 is no enrichment); the 3 is a practice estimate that a visible
  focus or a droplet stands out about threefold over the surroundings; recruited proteins in condensates are often reported at tens to hundreds (partition coefficients), so 3 is a low full
  agreement and generous to a modest recruitment; lab- and imaging-specific. Q3 relative to the paper's own surroundings. Q4 a wrong 3 moves the degree of a real recruitment, never its direction
  (the statement comes from colocalization_observed). Q5 the same log-ratio ramp (3 / 1) as the PLA fold, the pull-down enrichment and the split-reporter fold.
PEARSON_FULL_AGREEMENT 0.7 / PEARSON_ZERO_AGREEMENT 0.2 (colocalization_readout, Pearson)
  Q1 two channels that do not follow each other pixel by pixel. Q2 the usual reading of the Pearson coefficient is that about 0.5 is moderate and above about 0.7 strong correlation, and that values
  near 0 are no correlation; 0.2 is a practice estimate of the level that bleed-through, autofluorescence and overlap by crowding give by themselves (no method paper fixes it: Dunn, Kamocka and McDonald 2011
  Am J Physiol Cell Physiol 300:C723 and Costes et al. 2004 Biophys J 86:3993 argue for a per-image significance test, which is not collected; from memory, to verify); lab- and image-specific. Q3 absolute, and
  it should be relative to the coefficient of an unrelated protein under the same conditions: not collected. Q4 a coefficient reads low for a small focus in a large cell, so a too-strict 0.7 would
  punish a true recruitment; that is why the readout takes the best of the stated numbers. Linear: a coefficient is an additive correlation scale. Q5 no other binding assay has a coefficient.
FRACTION_FULL_AGREEMENT_PERCENT 80 / FRACTION_ZERO_AGREEMENT_PERCENT 10 (colocalization_readout, fraction)
  Q1 a recruitment that happens in a minority of the scored objects (a focus in a few cells, a rare droplet). Q2 practice estimate: a recruitment that the paper builds on is usually reported in most
  of the objects; 10 is the level that stray overlap of a focus with a spot gives in an unrelated protein (no paper fixes it; from memory, to verify); lab-specific, and it depends on what the object is.
  Q3 absolute, and it should be relative to the fraction of an unrelated protein or of the deletion strain: not collected (the facts unrelated_protein_not_recruited and lost_without_partner carry them
  as yes or no). Q4 a wrong value moves only the degree of the readout. Linear: the fraction is an additive proportion. Q5 no other binding assay has a fraction of objects.
OBJECTS_COUNTED_FULL_CREDIT 100 (objects_counted)
  Q1 a fraction or a mean from a handful of cells, foci or droplets. Q2 practice: a proportion needs about a hundred objects for a standard error near 5 points (sqrt(0.25 / 100));
  published imaging papers score from tens to hundreds. Lab-specific. Q3 absolute; kept. Q4 the count limits only the within-run precision, so a wrong 100 misleads little; sqrt(n / 100) is steep at a few
  objects (10 objects 0.32) and gentle near 100 (50 objects 0.71). Q5 the same precision shape as the PLA cells counted (there 50, as a mean puncta count needs fewer cells than a proportion).
REPLICATES_FULL_CREDIT 3 (replicates)
  Q1 a co-localization seen in one run (expression, fixation, imaging and droplet preparation vary between runs; more cells of one run do not average them). Q2 general: three independent
  experiments (Cumming, Fidler and Vaux 2007 J Cell Biol 177:7; journal reporting standards). Q3 absolute. Q4 sqrt(n / 3): one experiment 0.58, two 0.82, full from three. Q5 the owner's replicate rule, as in
  PLA, pull-down, Y2H, proximity, FP, FRET, AlphaScreen and CETSA.
Facts (colocalization_observed, specificity_control, directness, expression_validity, and the quantification fact of objects_counted) hold no value: yes supported, no conflicting, silence unknown. The imaging mode is recorded and
not judged (diffraction-limited imaging shows nearness within about 250 nm, which the weight of the type carries).
Unknown weight: this converter holds none and no degree contains one (the weight for an unstated criterion is per type and criterion in
literature_row_contract.WEIGHT_UNKNOWN_BY_TYPE / WEIGHT_UNKNOWN_BY_CRITERION: colocalization 0.60; BC 0.50, CA 0.60, BR 0.70, SB 0.80).
"""
from math import log, sqrt

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_colocalization_converted_v1'
CRITERIA_MAP = {'binding_controls': ('specificity_control',), 'binding_regime': ('directness',), 'binding_parameter_definition': ('colocalization_observed', 'colocalization_readout'), 'calibration_applicability': ('expression_validity',), 'sampling_basis': ('objects_counted', 'replicates')}
ENRICHMENT_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW, confirmed by the owner 2026-11-22: smallest enrichment (signal at the partner's site over the signal elsewhere) taken as a clear recruitment; a focus or a droplet that stands out about threefold is visible by eye. From memory, not verified.
ENRICHMENT_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW, confirmed by the owner 2026-11-22: enrichment at or below which the site is no brighter than its surroundings (a ratio of 1 is no enrichment): no recruitment; in between the degree rises linearly in the LOG of the ratio (a quotient of two intensities, whose error is multiplicative; the same scale as the PLA fold).
PEARSON_FULL_AGREEMENT = 0.7  # EXPERT_REVIEW, confirmed by the owner 2026-11-22: Pearson coefficient of the two channels taken as a strong correlation (the usual reading puts 0.7 and above as strong). From memory, not verified.
PEARSON_ZERO_AGREEMENT = 0.2  # EXPERT_REVIEW, confirmed by the owner 2026-11-22: Pearson coefficient at or below which the two channels are taken as uncorrelated (bleed-through and crowding give about this much by themselves); the degree falls linearly in between (a coefficient is an additive scale). From memory, not verified.
FRACTION_FULL_AGREEMENT_PERCENT = 80.0  # EXPERT_REVIEW, confirmed by the owner 2026-11-22: percent of the scored cells, foci or droplets that show the co-localization taken as the usual full reading of a recruitment that a paper builds on. From memory, not verified.
FRACTION_ZERO_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW, confirmed by the owner 2026-11-22: percent at or below which the co-localization is as rare as stray overlap of an unrelated protein; the degree rises linearly in between (a proportion is an additive scale). From memory, not verified.
# EXPERT_REVIEW, confirmed by the owner 2026-11-22: number of cells, foci or droplets scored that gets full credit; a proportion needs about a hundred objects for a standard error near 5 points. Gradual (not a pass/fail minimum):
# below it the degree is sqrt(n / 100), the precision of the mean over n objects relative to that over a hundred (50 objects ~0.71, 10 objects ~0.32), smooth, rising with n and reaching 1 at a hundred.
# Fewer objects are weaker evidence, not evidence against. From memory, not verified.
OBJECTS_COUNTED_FULL_CREDIT = 100
# EXPERT_REVIEW, confirmed by the owner 2026-11-22: number of independent experiments (separate experiments on separate days or cultures; cells, foci and droplets of one sample do not count) that gets full credit.
# Gradual: below it the degree is sqrt(n / 3) (owner rule: replicates mean precision in every assay); 1 -> about 0.58, 2 -> about 0.82, full from three.
REPLICATES_FULL_CREDIT = 3
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_colocalization_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_colocalization_is_not_an_attribution_fraction', 'total_signal': 'a_colocalization_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_colocalization_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_colocalization_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _linear(value):
    """The scale of a quantity whose error is additive (a proportion, a correlation coefficient)."""
    return value


def _degree(value, full, zero, scale=_linear):
    """1.0 at ``full`` (or beyond it), falling linearly in ``scale`` to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``.
    ``scale`` is monotone, so the side test is made on the value itself (before a log could see a value at or below 0)."""
    if (value - zero) * (full - zero) <= 0:
        return None
    return min(1.0, (scale(value) - scale(zero)) / (scale(full) - scale(zero)))


def _judge_readout(native):
    """Each stated number on its own ramp; the best degree of them counts (three views of one result; a Pearson coefficient reads low for a small focus), and the readout is
    conflicting only when every stated number is at or beyond its zero end."""
    degrees = []
    if native['colocalization_fraction'] is not None:
        degrees.append(_degree(native['colocalization_fraction'], FRACTION_FULL_AGREEMENT_PERCENT, FRACTION_ZERO_AGREEMENT_PERCENT))
    if native['colocalization_pearson'] is not None:
        degrees.append(_degree(native['colocalization_pearson'], PEARSON_FULL_AGREEMENT, PEARSON_ZERO_AGREEMENT))
    if native['colocalization_enrichment'] is not None:
        degrees.append(_degree(native['colocalization_enrichment'], ENRICHMENT_FULL_AGREEMENT, ENRICHMENT_ZERO_AGREEMENT, log))
    stated = [degree for degree in degrees if degree is not None]
    if not stated:
        return _verdict('conflicting', native['readout_refs'])
    return _verdict('supported', native['readout_refs'], max(stated))


def _judge_objects(native):
    # the precision of the mean over n objects relative to that over the researched number (standard error ~ 1 / sqrt(n)); full credit at OBJECTS_COUNTED_FULL_CREDIT
    return _verdict('supported', native['objects_counted_refs'], min(1.0, sqrt(native['objects_counted'] / OBJECTS_COUNTED_FULL_CREDIT)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated: the count alone does not say independent experiments
    # the precision of the mean over n independent experiments relative to that of the researched number; full credit at REPLICATES_FULL_CREDIT
    return _verdict('supported', native['replicate_refs'], min(1.0, sqrt(native['replicate_count'] / REPLICATES_FULL_CREDIT)))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('colocalization_readout', 'colocalization_readout_recorded_for_the_sheet'): _judge_readout, ('objects_counted', 'objects_counted_recorded_for_the_sheet'): _judge_objects,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def convert_colocalization(graded):
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
    qualitative_effect = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'enrichment_ratio': native['colocalization_enrichment']}
    direction_field_support = max(native['support']['colocalization_observed'], key=SUPPORTS.index, default=None)      # the statement is derived from the colocalization_observed fact alone; None when it is not stated (no direction)
    return {'version': VERSION, 'experiment_type': 'colocalization', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'qualitative_effect': qualitative_effect, 'direction_field_support': direction_field_support, 'null_components': dict(NULL_REASONS)}
