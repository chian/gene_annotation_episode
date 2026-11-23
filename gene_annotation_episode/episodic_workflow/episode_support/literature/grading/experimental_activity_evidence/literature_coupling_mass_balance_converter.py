"""Coupling_mass_balance converter: turns the grader's result into what the A105 reaction_coupling sheet takes.

DRAFT of 2026-11-22 for the owner to correct. Hand-built, private to coupling_mass_balance, deterministic. Input: the result of grade_coupling_mass_balance. Output: the
sheet's input (the 'extraction' grade_assay takes, with assay_type 'reaction_coupling'), the sheet itself (grade_assay run on it), the dependence keys the merger needs,
and for every sheet component that a mass balance cannot honestly fill, the reason it stays null. Built from the spectro_direct converter; the class core is the
reaction_coupling class (A105_REACTION_COUPLING_INVENTORY.md) and its direction function (literature_reaction_coupling_direction.py).

Quantities filled
-----------------
effect            the closure as a productive fraction, in the anchor unit 'fraction' (quantity_kind 'productive_fraction'): the share of the substrate consumed that the
                  identified products account for. It is the stated closure (a percent turned into a fraction by an exact factor, origin 'reported'), or, when none is
                  stated, the number the grader fixed by unit arithmetic from the stated amounts (origin 'derived': the stated sum of the products over the substrate
                  consumed, or one minus the stated residual over the substrate consumed). The direction function reads it on the productive-fraction scale
                  (COUPLING_STRENGTH_ANCHORS). A closure above 1 is read at the strong end there and is not clipped: that it is beyond the stoichiometric bound is the business
                  of the stoichiometry criterion (closure_bound), which lowers the weight.
effect_variance   variance of that effect, in fraction_squared, only for a STATED closure and only when its spread allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees of freedom). A closure
                  worked out from amounts has no stated spread. Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
recovery          the closure of the sample with no reaction (zero_time_closure, as a fraction), when stated: the method's own recovery, the sheet's recovery_deviation cell.
attributed_signal / total_signal   the stated sum of the identified products and the stated substrate consumed, only when both are stated in the same unit: the sheet's
                  attributed_fraction cell (products over consumed, not clamped, as the class core defines).
Every other role stays null, with a reason (NULL_REASONS): condition test/reference, the assertion and alternative predictions.
qualitative_effect  only when NO closure is available: the paper's own statement of product formation (fact product_formation_detected), statement 'interaction_detected'
                  (read "coupled product formation detected"), 'interaction_not_detected' (read "no product formed above the paper's control or detection limit") or
                  'interaction_not_stated', with the refs of the fact that states it. direction_field_support is then the support of that one fact. A stated closure fixes the
                  direction; the statement is then not used. A result stated in words alone already counts less than a measured one (stated_strength in the contract); that
                  is not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
product_identity          product_identity
calibration_applicability species_calibration + method_recovery + minor_species_detectability
matrix_interference       volatile_loss
background_alternatives   blank_controls
attribution_supported     product_coverage + inactive_enzyme
stoichiometry             reaction_equation + closure_bound
matched_windows           matched_windows
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
Not selected (the sheet reports them as not selected): reporter_specificity (a mass balance has no reporter; the sheet refuses not_applicable for a required criterion,
so none is declared) and measurement_identity (no member of this type reads it).
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value, falling
smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states nothing, never
conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported
carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never
changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose
members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None. Qualitative
statements keep the existing vocabulary. Direction and strength of a stated closure: literature_reaction_coupling_direction (a larger link is stronger); controls, blanks and
the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CLOSURE_FULL_AGREEMENT 1.10 -> CLOSURE_ZERO_AGREEMENT 1.50 (closure_bound, on the closure itself, linear).
  Q1 more product counted than the substrate consumed can give: a calibration error, a product that does not come from the substrate (a contaminant, the enzyme
  preparation, the buffer), a coefficient not applied (two products per substrate counted as one balance), or a substrate loss that was under-measured. Q2 general: the
  routine accuracy of a calibrated chromatographic or NMR quantification is a few percent per species (ICH Q2 style accuracy limits, about 98 to 102 percent for an assay and
  wider for minor species) and the sum of several species adds their errors; pharmaceutical mass-balance practice accepts about 95 to 105 percent, sometimes 90 to 110 (ICH
  Q1A and forced-degradation practice), from memory. So a closure up to 1.10 is within the error of the method (full agreement). Q3 relative to the substrate the paper itself
  consumed: right, and it is the stoichiometric bound that the paper's own numbers must respect. Q4 the errors of the species add, so the ramp is linear in the closure; at 1.50
  a third of the counted product cannot come from the consumed substrate, whatever the calibration (no agreement, conflicting). A closure BELOW 1 is not judged: it is the
  result (graded by its strength) and the unmeasured remainder is caught by product_coverage and volatile_loss. Q5 the cross-assay rule is the same ramp shape as the
  other judgements of a measured number against a researched good value; no other type has a bound above 1.
ZERO_TIME_DEVIATION_FULL 0.05 -> ZERO_TIME_DEVIATION_ZERO 0.30 (method_recovery, on |zero-time closure - 1|, linear).
  Q1 a method that does not give back what is put in (loss on work-up or injection, ion suppression, evaporation, adsorption), so every closure measured with it carries the same
  loss. Q2 general: spike-recovery acceptance of 95 to 105 percent for routine chromatographic assays and 85 to 115 percent for bioanalytical methods (FDA bioanalytical method
  validation guidance), from memory; the full end 0.05 is the stricter one because a closure is a sum and a statement to within 10 percent needs a method better than that.
  Q3 relative to the amount the paper itself added: right. Q4 two-sided: too low means loss, too high means interference or a calibration bias, and both mislead the closure by
  the same amount; at a deviation of 0.30 (a recovery of 70 or 130 percent) a closure cannot be read to within the usual 10 percent (conflicting). Linear: the recovery error
  shifts the closure additively. Q5 the same two-sided linear shape as the calibration-recovery curve of the class note (0.9 to 1.1 full, 0.5 or 2 zero), here stricter at the
  full end.
DETECTION_LIMIT_SHARE_FULL 0.05 -> DETECTION_LIMIT_SHARE_ZERO 0.50 (minor_species_detectability, on detection limit / substrate consumed, linear).
  Q1 a product that was formed but sits below the detection limit hides in the residual: with a detection limit that is a large share of the substrate consumed, the balance
  can be closed or open by up to that share without the method seeing it. Q2 general: the limit of detection is where the signal is about three times the noise and the limit
  of quantification ten times (ICH Q2), from memory; a species at the detection limit is not quantified, so it is part of what the closure cannot see. The full end 0.05 equals
  the usual few percent accuracy of the quantification (a hidden share below it is inside the error); the zero end 0.5 is a detection limit as large as half of the consumed
  substrate, where any closure statement is empty. Q3 relative to the substrate the paper itself consumed: right, and the grader records both. Q4 the hidden share adds to the
  closure, so linear; at or beyond the zero end the paper's own numbers show it cannot test closure (conflicting). Q5 no other type has a detection limit over a consumed amount.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a closure from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean
  (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (product identity, calibration of each species, the blank controls, the inactive-enzyme control, the coverage of the products, the volatile loss, the
reaction equation, the matched mixture and window, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting,
silence is unknown. They have no researched value to soften. NOT judged, and why: the balance basis and the analysis method (choices: a choice holds no span after the merge, and
the basis changes what the closure counts, not whether it is a closure); the pH and the temperature (the claim carries no condition, and the identity block records the
temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, decided
2026-11-22, owner to confirm:
  What does it measure; absolute or relative? A ratio of two amounts of the same reaction, each quantified against standards (an absolute, dimensionless closure); but the
  ratio is only as good as the calibration of EVERY species, so it is absolute with respect to the standards and not a constant of the enzyme.
  Is there a reference range we would trust if the paper stated less? Only the physical bound: a closure cannot exceed 1 by more than the error of the method. There is no
  trusted range of closures as there is for kcat or KD (a low closure is a real result), so nothing stands in for a missing detail.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme or time-zero sample lets spontaneous loss of the substrate (hydrolysis,
  oxidation, evaporation) count as enzymatic consumption and a closure be built on it; an unstated identification lets any peak count as a product; an unstated match of
  mixture and window sets two different reactions against each other (the class note's example: product at 30 min against substrate at 2 min).
  If we assume it is fine and are wrong, how badly does the score mislead? A closure built from unidentified peaks or unmatched windows is uninterpretable (the existence of
  the coupling is wrong); a missing calibration or replicate only changes the size.
  Consistent with the others? Under the activity and end-point types (0.85) because the closure needs more details to be right (every species), above the nearness types.
  default 0.80. product_identity 0.70 and matched_windows 0.70 (a sum over peaks that were not identified, or over unmatched windows, is uninterpretable). background_alternatives
  0.75 (the no-enzyme or time-zero sample separates enzymatic consumption from spontaneous loss). attribution_supported 0.75 (an unquantified expected product or a missing
  inactive-enzyme control leaves the balance open). sampling_basis 0.90 (benign when unstated: triplicates are usual and only the precision is affected).
  calibration_applicability, matrix_interference, stoichiometry, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_coupling_mass_balance_converted'
CRITERIA_MAP = {'product_identity': ('product_identity',), 'calibration_applicability': ('species_calibration', 'method_recovery', 'minor_species_detectability'),
                'matrix_interference': ('volatile_loss',), 'background_alternatives': ('blank_controls',), 'attribution_supported': ('product_coverage', 'inactive_enzyme'),
                'stoichiometry': ('reaction_equation', 'closure_bound'), 'matched_windows': ('matched_windows',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
FRACTION_OF_UNIT = {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION}  # FIXED_BY_DEFINITION: exact unit spelling of a share.
UNITY = 1.0  # FIXED_BY_DEFINITION: a recovery of exactly 1 gives back all that was put in.
CLOSURE_FULL_AGREEMENT = 1.10  # EXPERT_REVIEW, owner to confirm: a closure up to about 110 percent is within the summed error of a calibrated quantification of several species (pharmaceutical mass-balance practice 95 to 105, sometimes 90 to 110 percent, ICH Q1A and forced-degradation practice, from memory, not verified); full agreement up to it. A closure below 1 is not judged here.
CLOSURE_ZERO_AGREEMENT = 1.50  # EXPERT_REVIEW, owner to confirm: at a closure of 150 percent a third of the counted product cannot come from the substrate consumed (no agreement, conflicting); the degree falls linearly in the closure from the full end to here (the errors of the species add).
ZERO_TIME_DEVIATION_FULL = 0.05  # EXPERT_REVIEW, owner to confirm: the recovery of a sample with no reaction within 5 percent of 1 (routine chromatographic spike recovery 95 to 105 percent, bioanalytical 85 to 115 percent, from memory, not verified); full agreement up to it.
ZERO_TIME_DEVIATION_ZERO = 0.30  # EXPERT_REVIEW, owner to confirm: a recovery of 70 or 130 percent: the method loses or adds so much that a closure cannot be read to within the usual 10 percent (no agreement, conflicting); the degree falls linearly in the deviation from the full end to here.
DETECTION_LIMIT_SHARE_FULL = 0.05  # EXPERT_REVIEW, owner to confirm: a detection limit up to 5 percent of the substrate consumed hides at most the usual few percent accuracy of the quantification (limit of detection about three times the noise, ICH Q2, from memory, not verified); full agreement up to it.
DETECTION_LIMIT_SHARE_ZERO = 0.50  # EXPERT_REVIEW, owner to confirm: a detection limit of half of the substrate consumed: a product at the limit could account for half of the balance and no closure statement is possible (no agreement, conflicting); the degree falls linearly in the share from the full end to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
QUANTITY_KIND = 'productive_fraction'  # the kind (QUANTITY_KINDS['reaction_coupling']) of the closure, whether or not an effect is filled; literature_reaction_coupling_direction.COUPLING_QUANTITY_OF_KIND reads it back.
NULL_REASONS = {'condition_test': 'no_matched_nuisance_condition_response_in_a_mass_balance_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_mass_balance_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "coupled product formation detected" / "no product formed above the control" / "not stated" for this class


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _ramp(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (zero - value) / (zero - full)


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit), all on the criterion's own scale. Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly on that scale to 0 at the zero limit."""
    degrees = [_ramp(value, full, zero) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _judge_closure(native):
    return _graded(native['closure_refs'], (native['closure'], CLOSURE_FULL_AGREEMENT, CLOSURE_ZERO_AGREEMENT))


def _judge_recovery(native):
    return _graded(native['zero_time_refs'], (abs(native['zero_time_closure'] - UNITY), ZERO_TIME_DEVIATION_FULL, ZERO_TIME_DEVIATION_ZERO))


def _judge_detectability(native):
    return _graded(native['detection_limit_refs'], (native['detection_limit_share'], DETECTION_LIMIT_SHARE_FULL, DETECTION_LIMIT_SHARE_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('closure_bound', 'closure_recorded_for_the_sheet'): _judge_closure, ('method_recovery', 'zero_time_closure_recorded_for_the_sheet'): _judge_recovery,
          ('minor_species_detectability', 'detection_limit_recorded_for_the_sheet'): _judge_detectability, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': origin, 'native_component': component}


def _variance(graded, ref):
    """Return (variance in fraction_squared or None, reason or None, refs) of the spread of the stated closure."""
    native = graded['native']
    if native['closure_origin'] != 'reported':
        return None, 'closure_worked_out_from_amounts_has_no_stated_spread', []
    spread = native['quantities']['closure_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'closure_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * FRACTION_OF_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_coupling_mass_balance(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    effect_support = None
    if native['closure'] is None:
        null_components['effect'] = 'no_closure_stated_and_none_can_be_worked_out_from_the_stated_amounts'
        null_components['effect_variance'] = 'no_effect'
    else:
        quantities['effect'] = _operand(native['closure'], 'fraction', 'coupling_mass_balance_closure:' + ref, native['closure_refs'], native['closure_origin'], native['closure_component'])
        effect_support = native['closure_support']
        variance, variance_reason, variance_refs = _variance(graded, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, 'fraction_squared', 'coupling_mass_balance_closure_variance:' + ref, variance_refs, 'derived', 'closure_spread')
    if native['zero_time_closure'] is None:
        null_components['recovery'] = 'no_closure_of_a_sample_with_no_reaction_stated'
    else:
        quantities['recovery'] = _operand(native['zero_time_closure'], 'fraction', 'coupling_mass_balance_zero_time_closure:' + ref, native['zero_time_refs'], 'reported', 'zero_time_closure')
    products, consumed = native['quantities']['products_total'], native['quantities']['substrate_consumed']
    if products['status'] == 'point' and consumed['status'] == 'point' and products['unit'] == consumed['unit']:
        quantities['attributed_signal'] = _operand(products['value'], products['unit'], 'coupling_mass_balance_products_total:' + ref, products['source_refs'], 'reported', 'products_total')
        quantities['total_signal'] = _operand(consumed['value'], consumed['unit'], 'coupling_mass_balance_substrate_consumed:' + ref, consumed['source_refs'], 'reported', 'substrate_consumed')
    else:
        null_components['attributed_signal'] = 'products_total_and_substrate_consumed_not_both_stated_in_one_unit'
        null_components['total_signal'] = 'products_total_and_substrate_consumed_not_both_stated_in_one_unit'
    null_components.update(NULL_REASONS)
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'reaction_coupling', 'assertion_ref': native['assertion_ref'], 'quantity_kind': QUANTITY_KIND, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'coupling_mass_balance', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no closure: the paper's own statement of product formation fixes the direction (stated in words, like any stated result)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['detection']], 'support_refs': list(native['detection_refs'])}
        if native['detection'] is not None:
            result['direction_field_support'] = native['detection_support']      # the support class of the fact product_formation_detected, the one field the statement is derived from
    return result
