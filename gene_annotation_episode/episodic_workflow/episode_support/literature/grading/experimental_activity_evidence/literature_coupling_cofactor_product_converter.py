"""Coupling_cofactor_product converter: turns the grader's result into what the A105 reaction_coupling sheet takes.

Hand-built, private to coupling_cofactor_product, deterministic. Input: the result of grade_coupling_cofactor_product. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'reaction_coupling'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet component
that a cofactor-and-product measurement cannot honestly fill, the reason it stays null. DRAFT 2026-11-22 for the owner to correct (SOP steps 3 and 5); the class core is
A105_REACTION_COUPLING_INVENTORY.md sections 2, 4 and 6 and G/literature_reaction_coupling_direction.py.

Quantities filled
-----------------
effect            ONE coupling value in the anchor unit 'fraction' (literature_reaction_coupling_direction, COUPLING_STRENGTH_ANCHORS): the stated productive fraction, else the
                  coefficient times the product per cofactor, else the bare product per cofactor. The grader chose and, where it had to, derived it by exact arithmetic
                  ('reported' or 'derived' in the operand's origin); a percent is divided by its hundred and a mol-per-mol is already a fraction. quantity_kind of the
                  extraction names the kind of the effect ('productive_fraction' or 'stoichiometric_ratio'), which the direction function reads.
effect_variance   variance of that effect, in 'fraction_squared', only when the passage states the spread of THAT reported quantity: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees of
                  freedom). A derived effect has no stated spread (its spread would be propagated from both sides, which the passage does not give): null with the reason.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO coupling value is found and the paper states whether it saw product above its own control or detection limit in the reaction that
                  consumed the cofactor: statement 'interaction_detected' (read "coupled product formation detected") or 'interaction_not_detected' (read "no product formed
                  above the paper's own control or detection limit"), with the refs of the fact that states it. direction_field_support is then the support of that one fact
                  (coupled_product_detected). A stated coupling value fixes the direction; the statement is then not used, and direction_field_support is the weakest support
                  of the stated fields the value rests on.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity       same_enzyme_preparation
calibration_applicability  product_calibrated + extinction_coefficient_stated + absorbance_range + calibration_recovery
background_alternatives    spontaneous_oxidation_control + background_subtracted
attribution_supported      inactive_enzyme_control
assertion_relevance        native_reaction
condition_scope            purified_enzyme
sampling_basis             replicates
product_identity           product_identified
stoichiometry              coefficient_stated + stoichiometric_bound
matched_windows            same_reaction_mixture + same_window
reporter_specificity       no_substrate_oxidation + byproduct_accounted (the reporter here is the cofactor's own absorbance: the cofactor used by something other than the claimed
                           reaction, the uncoupled oxidation, is the side consumption)
variance_correspondence    supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value,
falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the paper states nothing,
never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is
supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion
and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (matrix_interference) are not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (nothing is
immobilized, nothing is on a surface; the two sides come from one preparation, so they are one dependence unit). Qualitative statements keep the existing vocabulary.
Direction and strength of a stated coupling value: literature_reaction_coupling_direction (same paradigm as binding and activity, LARGER is stronger, anchors per quantity);
controls, blanks, matched windows, the coefficient and the reporter lower the WEIGHT only, never the direction. A coupling value above 1 is read at the strong end by the
direction; that it passes the stoichiometric bound is judged here (stoichiometric_bound), where it lowers the weight and, far enough above, is conflicting.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other types). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
BACKGROUND_SHARE_FULL 0.10 -> BACKGROUND_SHARE_ZERO 0.90 (no_substrate_oxidation), judged on the log of the amplification 1 / (1 - share).
  Q1 the cofactor the enzyme oxidises with no substrate (the uncoupled turnover, the oxidase and peroxide-forming side of a monooxygenase) is a large part of the test rate:
  what is left for the coupled reaction after the background is taken off is a small difference of two large rates, so the cofactor side of the ratio is imprecise; and where
  the background is not taken off the cofactor use is overstated and the coupling understated. Q2 general: a small blank is taken off accurately and a blank that nears the
  signal is not (the limit-of-quantitation argument of any blank-corrected assay; NCBI Assay Guidance Manual, from memory); the 10 percent end is the usual 'blank under a tenth
  of the signal' practice; lab- and enzyme-specific in detail (a P450 with a non-native substrate is often mostly uncoupled). Q3 relative to the paper's own test rate, which the
  grader records beside it: right. Q4 a relative error e of the gross rates becomes e / (1 - share) of the net, so the loss of precision grows as 1 / (1 - share); the degree is linear
  in the log of that amplification between 1.11 (share 0.10) and 10 (share 0.90, where a 10 percent error of the gross rates is a 100 percent error of the net). At or beyond
  0.90 the background is the test rate (conflicting): the paper's own numbers show the net cofactor use cannot be told from the background. Q5 the same idea as the other
  blank-against-signal judgements, a bias that grows with the departure from the researched value; not the uncoupled turnover itself as an effect (it is the opposite of
  the coupling and is the subject of the by-product type).
RECOVERY_FULL_FACTOR 1.15 -> RECOVERY_ZERO_FACTOR 2.0 (calibration_recovery), judged on the log of the recovery over 100 percent, two-sided.
  Q1 a product assay that does not return the known amount put in (extraction loss from the reaction mixture, ion suppression in mass spectrometry, an unresolved peak in
  HPLC) gives a wrong amount of product and so a wrong coupling. Q2 general: bioanalytical method validation accepts an accuracy within 15 percent (ICH M10 and the FDA
  bioanalytical guidance, from memory), so a recovery within 1.15-fold either way is the researched good value. Q3 relative to 100 percent (the known amount), stated by the paper
  itself. Q4 the coupling is the product over the cofactor, so it is wrong by the same factor as the recovery: under- and over-recovery both mislead, so the scale is the
  log of the recovery (a half and a double are the same size of error) and falls linearly to zero at a factor of 2, where the product amount is wrong by as much as the
  coupling could be (conflicting). Q5 consistent with the calibration judgements of the other types, which take their ends from the paper's own constant.
BOUND_FULL 1.15 -> BOUND_ZERO 2.0 (stoichiometric_bound), judged linearly on the coupling value.
  Q1 more product than the cofactor consumed can make (a coupling value above 1): the two sides do not refer to the same reaction, the product comes from another source
  (a second reaction, an endogenous pool, a carry-over), or the cofactor was regenerated; the stoichiometry of the claimed reaction does not hold for these numbers. Q2 general
  (the stoichiometric ceiling is physics: a productive fraction cannot exceed 1); the 1.15 allows the error of two independent measurements (the product to about 15 percent
  by chromatography against a standard, the cofactor to a few percent by its absorbance) to push a true 1 above 1, from memory. Q3 absolute (the ceiling is 1 for a
  productive fraction with the reaction's own coefficient applied; for a bare ratio with no coefficient stated it is the same number, because every cofactor-coupled
  reaction of this kind takes at least one cofactor per product); the grader records the value. Q4 an error of the quotient is proportional to the value, so the degree is
  linear in it; at 2 the product is twice what the cofactor could have made, which no measurement error explains (conflicting). A low value is NOT judged here: a low coupling
  is the strength of the effect (the direction's scale), not a failure of the experiment. Q5 the same linear-ramp shape as the other recorded numbers; the open owner question
  (a value above 1 as a diagnostic, not clipped: the value itself is kept in the effect and read at the strong end) stays open in the inventory (question 4).
ABSORBANCE_FULL 1.0 -> ABSORBANCE_ZERO 3.0, STRAY_LIGHT 0.01 (absorbance_range), judged on the bias of the apparent absorbance.
  Q1 Beer-Lambert fails at high absorbance: stray light puts a floor under the transmitted intensity, the apparent absorbance bends over and the absorbance loss of the cofactor
  underestimates its consumption (so the coupling is overstated). Q2 general: keep the absorbance below about 1 (instrument manuals and photometry texts), from memory; a stray
  light of 1 percent is the conservative end of the instruments in use. 0.2 mM NAD(P)H at 340 nm in a 1 cm path (6.22 mM^-1 cm^-1, Dawson et al. 1986, from memory) reads 1.24,
  so a typical assay starts a little above the full end and loses only a few percent (a degree near 0.97). Q3 absolute (absorbance units), and the grader records the highest
  absorbance of the paper itself. Q4 the apparent absorbance is -log10((10^-A + s) / (1 + s)), so the underestimate is about 4 percent at A = 1, 15 percent at 2, 35 percent
  at 3; the degree is linear in that bias between the two ends; conflicting at or beyond A = 3. A low absorbance is not judged: the paper's own spread carries it.
  Q5 the same bias shape and constants as spectro_direct (a private copy, intended).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a coupling from one experiment, whose preparation-to-preparation spread is unseen (and a ratio of two measurements carries both their spreads). Q2 general (triplicate
  practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the product identification and calibration, the matched mixture, window and preparation, the controls, the by-product, the inactive enzyme, the native
substrate and the purified enzyme) and the stated coefficient: the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no
researched value to soften. NOT judged, and why: the extinction coefficient's value (it is the paper's own constant, stated with its wavelength; for NAD(P)H at 340 nm it is
6.22 mM^-1 cm^-1, but QueF-type work reads 334 or 365 nm and a paper may use another chromophore, so no single value is the right one); the overlap of the two windows as a
number (papers state it as a fact, not as two intervals; the fact same_window carries it); the pH and the temperature (the claim carries no condition, and the identity
block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, decided
2026-11-22, owner to confirm:
  What does it measure; absolute or relative? A dimensionless, absolute link between two quantities measured in the same reaction (product per cofactor): absolute, but each side
  needs its own calibration (the cofactor by its extinction coefficient, the product by a standard series), and the link means something only when the two sides are matched.
  Is there a reference range we would trust if the paper stated less? Partly: P450 couplings run from a few percent (non-native substrates) to near 100 percent (camphor with
  P450cam); the range helps with the size of the effect, not with whether the sides were matched or the product identified.
  What does an unstated control or calibration do to the number's meaning? An unstated extinction coefficient is benign (the NAD(P)H value is well known); an unstated product
  calibration is a usual practice but mislabels the amount; an unstated no-substrate control leaves the uncoupled share open, which is the quantity the method exists to separate;
  an unidentified product makes the ratio a ratio of a peak, not of the claimed product; unmatched sides (different windows or preparations, as in the T252N case of the primary
  grading test) make the ratio uninterpretable.
  If we assume it is fine and are wrong, how badly does the score mislead? For the matched sides and the product identity, badly (the number is about something else); for the
  background, the size of the coupling (and so the strength), not its existence; for the calibration and the replicates, the size by a factor.
  Consistent with KD? Under it (a ratio of two measurements has more ways to be wrong than one fitted constant) and level with spectro_direct for the benign criteria.
  default 0.80. product_identity 0.65 and matched_windows 0.65 (the ratio is uninterpretable without them). reporter_specificity 0.70 (the uncoupled cofactor use unstated).
  background_alternatives 0.75. stoichiometry 0.75 (an unstated coefficient leaves a factor of 2 open for the reactions that take two cofactors). calibration_applicability 0.85
  and sampling_basis 0.90 (benign when unstated). measurement_identity, attribution_supported, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_coupling_cofactor_product_converted'
CRITERIA_MAP = {'measurement_identity': ('same_enzyme_preparation',),
                'calibration_applicability': ('product_calibrated', 'extinction_coefficient_stated', 'absorbance_range', 'calibration_recovery'),
                'background_alternatives': ('spontaneous_oxidation_control', 'background_subtracted'), 'attribution_supported': ('inactive_enzyme_control',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',),
                'product_identity': ('product_identified',), 'stoichiometry': ('coefficient_stated', 'stoichiometric_bound'),
                'matched_windows': ('same_reaction_mixture', 'same_window'), 'reporter_specificity': ('no_substrate_oxidation', 'byproduct_accounted')}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
BACKGROUND_SHARE_FULL = 0.10  # EXPERT_REVIEW, owner to confirm: the cofactor oxidation with no substrate at most a tenth of the test cofactor rate (the usual 'blank under a tenth of the signal' practice, from memory); full agreement up to it.
BACKGROUND_SHARE_ZERO = 0.90  # EXPERT_REVIEW, owner to confirm: at nine tenths the net cofactor use is a tenth of the gross, so a 10 percent error of the gross rates is a 100 percent error of the net (no agreement); the degree falls linearly in the log of the amplification 1 / (1 - share) from the full end to here.
RECOVERY_FULL_FACTOR = 1.15  # EXPERT_REVIEW, owner to confirm: a recovery of the product standard within 1.15-fold of 100 percent either way (bioanalytical validation accuracy of 15 percent, ICH M10 and FDA guidance, from memory); full agreement within it.
RECOVERY_ZERO_FACTOR = 2.0  # EXPERT_REVIEW, owner to confirm: a recovery of half or double the known amount makes the product amount wrong by a factor 2, as large as the coupling itself could be wrong (no agreement); the degree falls linearly in the log of the recovery from the full end to here, two-sided.
BOUND_FULL = 1.15  # EXPERT_REVIEW, owner to confirm: the largest coupling value that still counts as within the stoichiometric ceiling of 1 once the error of two measurements (about 15 percent for a product by chromatography, a few percent for the cofactor absorbance) is allowed, from memory; full agreement up to it.
BOUND_ZERO = 2.0  # EXPERT_REVIEW, owner to confirm: twice the product the cofactor consumed could have made, which no measurement error explains: the two sides are not one reaction (no agreement); the degree falls linearly in the value from the full end to here.
ABSORBANCE_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: keep the absorbance at most about 1 (photometry practice, from memory); full agreement up to it (the apparent-absorbance bias there is about 4 percent at 1 percent stray light).
ABSORBANCE_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm: at an absorbance of 3 a stray light of 1 percent loses about a third of the signal (no agreement); the degree falls linearly in the bias of the apparent absorbance from the full end to here.
STRAY_LIGHT = 0.01  # EXPERT_REVIEW, owner to confirm: the fraction of stray light in the transmitted intensity; 1 percent is the conservative end of the spectrophotometers and plate readers in use (a good UV-visible instrument has 0.1 percent or less).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
ANCHOR_UNIT = 'fraction'   # the unit of the effect (literature_reaction_coupling_direction, COUPLING_STRENGTH_ANCHORS); a percent was divided by its hundred and a mol per mol is already a fraction by the grader.
KIND_WITHOUT_EFFECT = 'productive_fraction'   # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'calibration_recovery_is_judged_in_calibration_applicability_and_is_not_a_second_cell', 'attributed_signal': 'the_coupling_is_the_effect_and_its_two_sides_are_not_a_second_attribution',
                'total_signal': 'the_coupling_is_the_effect_and_its_two_sides_are_not_a_second_attribution', 'condition_test': 'no_matched_nuisance_condition_response_in_a_coupling_cofactor_product_record',
                'condition_reference': 'no_matched_nuisance_condition_response_in_a_coupling_cofactor_product_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "coupled product formation detected" / "no product formed above the paper's own control or detection limit" for this class


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _share(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (zero - value) / (zero - full)


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit), all on the criterion's own scale. Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly on that scale to 0 at the zero limit."""
    degrees = [_share(value, full, zero) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _amplification(share):
    """The log of 1 / (1 - share): how much the relative error of the gross cofactor rates is multiplied in the net (the rate after the background is taken off)."""
    return -math.log1p(-share)


def _apparent_absorbance_bias(absorbance):
    """The relative shortfall of the apparent absorbance, -log10((10^-A + s) / (1 + s)), against the true A, for the stray light STRAY_LIGHT."""
    return 1.0 - -math.log10((10.0 ** -absorbance + STRAY_LIGHT) / (1.0 + STRAY_LIGHT)) / absorbance


def _judge_background(native):
    refs, share = native['background_refs'], native['background_over_test']
    if share >= BACKGROUND_SHARE_ZERO:
        return _verdict('conflicting', refs)
    return _graded(refs, (_amplification(share), _amplification(BACKGROUND_SHARE_FULL), _amplification(BACKGROUND_SHARE_ZERO)))


def _judge_recovery(native):
    deviation = abs(math.log(native['recovery_percent'] / PERCENT_PER_FRACTION))
    return _graded(native['recovery_refs'], (deviation, math.log(RECOVERY_FULL_FACTOR), math.log(RECOVERY_ZERO_FACTOR)))


def _judge_bound(native):
    return _graded(native['link_refs'], (native['link_value'], BOUND_FULL, BOUND_ZERO))


def _judge_absorbance(native):
    return _graded(native['absorbance_refs'], (_apparent_absorbance_bias(native['absorbance_max']), _apparent_absorbance_bias(ABSORBANCE_FULL), _apparent_absorbance_bias(ABSORBANCE_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('no_substrate_oxidation', 'background_recorded_for_the_sheet'): _judge_background, ('calibration_recovery', 'recovery_recorded_for_the_sheet'): _judge_recovery,
          ('stoichiometric_bound', 'link_recorded_for_the_sheet'): _judge_bound, ('absorbance_range', 'absorbance_recorded_for_the_sheet'): _judge_absorbance,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded, link, ref):
    """Return (variance in fraction_squared or None, reason or None, refs) of the stated spread of the reported coupling quantity."""
    native = graded['native']
    if link['spread'] is None:
        return None, ('effect_is_derived_and_has_no_stated_spread' if link['origin'] == 'derived' else 'effect_spread_not_given'), []
    kind = native['spread_kind']
    if kind is None:
        return None, 'spread_kind_not_stated', []
    if kind == 'standard_error':
        return link['spread'] * link['spread'], None, link['spread_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return link['spread'] * link['spread'] / count['value'], None, list(dict.fromkeys([*link['spread_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_coupling_cofactor_product(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    link = native['link']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if link is None:
        null_components['effect'] = 'no_coupling_value_stated_or_derivable_from_stated_amounts_or_rates'
        null_components['effect_variance'] = 'no_effect'
    else:
        quantities['effect'] = _operand(link['value'], ANCHOR_UNIT, 'coupling_cofactor_product_' + link['quantity'] + ':' + ref, link['refs'], link['origin'], link['quantity'])
        quantity_kind, effect_support = link['quantity'], link['support']
        variance, variance_reason, variance_refs = _variance(graded, link, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT + '_squared', 'coupling_cofactor_product_' + link['quantity'] + '_variance:' + ref, variance_refs, 'derived', link['quantity'] + '_spread')
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        graded_members = [_criterion(graded, m) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
        supports = [s for m in members if graded['criteria'][m]['status'] != 'not_applicable' for s in native['support'][m]]
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'reaction_coupling', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'coupling_cofactor_product', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['coupling'] is not None:      # no coupling value: the paper's own statement of product above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['coupling']], 'support_refs': list(native['coupling_refs'])}
        result['direction_field_support'] = native['coupling_support']
    return result
