"""Distribution_gc converter: turns the grader's result into what the A105 product_distribution sheet takes.

Hand-built, private to distribution_gc, deterministic. Input: the result of grade_distribution_gc. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'product_distribution'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for
every sheet component that a gas-chromatography share cannot honestly fill, the reason it stays null. DRAFT of 2026-11-22: the owner has not reviewed
it; every number below is EXPERT_REVIEW and every literature figure is from the drafter's memory, not verified.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the share of the claimed product among the products (fraction) or the ratio
                  of that product to another product (dimensionless, the claimed product in the numerator). Both may be stated; the one used is the
                  best-determined, in the class order PRODUCT_DISTRIBUTION_EFFECT_ORDER (literature_product_distribution_direction.select_product_distribution_effect).
                  A share stated in percent is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION); the value is the paper's, only its
                  unit spelling changes. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
                  The equilibrium quantities of the class (equilibrium_fraction, equilibrium_ratio) are not used: a gas chromatograph reads a product
                  spectrum, not where an equilibrium lies.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): the recovery role is the closure of all the products, which a gas-chromatography
extraction recovery is not (it is judged as a matrix criterion below, once, and not a second time as a recovery), the attributed and total signal
(the quantity kind already is the share), the condition test and reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated and the paper states whether the product was found among the products: statement
                  'interaction_detected' (read "product detected") or 'interaction_not_detected' (read "product not detected"), with the refs of the
                  fact claimed_product_detected that states it, and direction_field_support the quote support of that one fact. A stated effect
                  fixes the direction; the statement is then not used. A result stated in words alone already counts less than a measured one
                  (literature_row_contract.stated_strength); nothing of that is done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
species_identity          species_identification
response_factors          response_factors_applied
common_denominator        denominator_coverage
calibration_applicability detection_limit_ratio
matrix_interference       injector_stability + extraction_recovery
background_alternatives   no_enzyme_control + product_stability
attribution_supported     inactive_enzyme_control
assertion_relevance       native_reaction
condition_scope           purified_enzyme
sampling_basis            replicates
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity; equilibrium_state, which the sheet asks only of an equilibrium kind) are not selected.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES
maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement
at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a
step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper
itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is
not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay
None (no immobilized enzyme, no surface). Qualitative statements keep the existing vocabulary, read for this class. Direction and strength of a stated
share or ratio: literature_product_distribution_direction (same paradigm as binding, larger is stronger); controls, response factors, the shared
denominator and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong
value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every
number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
RI_FULL_DIFFERENCE 5 -> RI_ZERO_DIFFERENCE 30 (retention-index units), and LIBRARY_MATCH_DEGREE 0.7, judged linearly in the difference.
  Q1 a product named only by a library match of its mass spectrum: isomeric terpenes and other regio-isomers have almost the same electron-impact
  spectrum, so the match alone does not tell them apart; the retention index does. Q2 general: libraries and papers on essential oils and terpene
  synthase products accept a retention index within about 10 units of the published one on the same stationary phase (Adams, Identification of Essential
  Oil Components by Gas Chromatography/Mass Spectrometry, 4th ed.; van Den Dool and Kratz 1963; from memory). Neighbouring monoterpenes on a
  5 percent phenyl column lie 14 to 30 units apart (alpha-pinene 932, camphene 946, beta-pinene 974 in the Adams table; from memory), so a difference
  of 30 is where a neighbour is as near as the named compound. Q3 relative to the paper's own published value, which the grader records beside the
  measured one; column phase and temperature program are not collected (a gap, listed in the registration note). Q4 an index is an additive scale
  (a linear interpolation between n-alkanes), so the ramp is linear in the difference: 1.0 at 5, 0.5 at 17.5, 0 at 30 (conflicting there, the paper's
  own numbers say it is another compound). LIBRARY_MATCH_DEGREE caps a library identification below an identification by an authentic standard (the
  Metabolomics Standards Initiative puts a library match at level 2 and a standard at level 1, Sumner et al. 2007, from memory); 0.7 is a judgement and
  is not the quote-support factor of the same value. Q5 the ramp is the same idea as the replicate and series curves: a number that departs from its
  researched value lowers the degree gradually.
FID_UNCORRECTED_DEGREE 0.8 and MS_UNCORRECTED_DEGREE 0.5 (raw area percent read from the detector the paper names).
  Q1 a share given as raw peak area percent is a share of detector signal; it is the share of the amount of product only if every product responds
  alike. Q2 general: the flame-ionization response is nearly proportional to the number of oxidizable carbon atoms (the effective carbon number,
  Ackman 1964; Scanlon and Willis 1985, from memory), so for hydrocarbon products, and for products of the same formula such as terpene isomers, an
  FID area percent is close to the mass percent (within about 10 to 20 percent) and differs from the mole percent by the ratio of the molar masses (up
  to 1.5 between C10 and C15 terpenes). A mass-spectrometer area (total ion current) has no such rule: the response of electron-impact ionization varies
  by a factor of two or more between compounds of different structure, less among isomers. Q3 absolute for the detector, and the paper states which
  detector gave the areas (two facts). Q4 an uncorrected share is wrong by a bounded factor, not meaningless; the direction is unaffected, so only the
  degree is lowered: 0.8 (an error of about 20 percent) for FID, 0.5 (a factor of two) for MS. This is a degree of a STATED fact (the paper says the
  areas are raw); it is not an unknown weight. Q5 the same two-state shape as no other method; stated here so that the owner can set the pair.
IDENTIFIED_FULL_FRACTION 0.95 -> IDENTIFIED_ZERO_FRACTION 0.5, judged linearly in the log of the identified fraction.
  Q1 product peaks left unidentified: if the share of the claimed product is taken over the identified compounds only, it is too large by the factor
  1 / c, c the identified fraction; if it is taken over all peaks, the unidentified peaks may be the claimed product's own isomers. Q2 general: reports of
  terpene and essential-oil profiles assign about 90 to 99 percent of the area (from memory); 95 is the full end. Q3 relative to the paper's own total
  area, which the passage states as a share. Q4 the bias is the factor 1 / c, so the degree is linear in ln c: 1.0 at 0.95, 0.5 at about 0.69 (the
  factor 1.36), 0 at 0.5 (a factor of two, conflicting). Q5 a multiplicative bias on a log scale, as the fold gaps of the binding assays.
LIMIT_RATIO_FULL 10 -> LIMIT_RATIO_ZERO 1, judged linearly in the inverse of the share over the limit.
  Q1 a share that sits at the smallest share the method integrates or detects: its area is mostly noise and baseline placement. Q2 general: a limit of
  detection is about 3.3 times the noise of the blank over the sensitivity and a limit of quantification about 10 times (ICH Q2(R1), from memory); a
  stated smallest integrated share is a detection or integration limit, and a share ten times above it is quantified. Q3 relative to the paper's own
  limit, which it states as a share (a limit given in an amount is not in the unit vocabulary and is left unavailable). Q4 the relative error of an area
  near the limit goes as the limit over the share, so the degree is linear in 1 / ratio: 1.0 at 10, 0.89 at 5, 0.56 at 2, 0 at 1 (conflicting: the
  stated share is no larger than the stated limit). Q5 the precision of a signal over its noise, as for the signal-over-control judgements of the
  binding assays.
RECOVERY_FULL 0.8 -> RECOVERY_ZERO 0.3, judged linearly in |ln recovery| (so a recovery of 1.25 counts like 0.8).
  Q1 a product lost, or gained, in the extraction or the sampling step more than another product: volatile products evaporate faster the lighter they are,
  headspace and fibre sampling bind each compound differently, and the share then describes the sampling and not the reaction. Q2 general: a mean
  recovery of 80 to 110 percent is the usual acceptance range for an analyte at the mg per kg to percent level (AOAC guidelines for single-laboratory
  validation, from memory); lab- and method-specific. Q3 relative to the paper's own spiked or measured recovery, which is stated as a share. Q4 a recovery
  is multiplicative, so the scale is the log: 1.0 at 0.8 (and 1.25), 0 at 0.3 (and 3.3), where most of the product is lost and the loss between products can
  no longer be assumed equal. Q5 a multiplicative bias on a log scale, as above. A recovery of one product does not show the others equal; only the
  one number is judged.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a share from one reaction, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice for terpene synthase product profiles).
  Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the injector check, the no-enzyme control, the product stability, the inactive-enzyme control, the native substrate, the
purified enzyme, an authentic standard, calibrated response factors, all peaks in the total): the paper's own statement decides; yes is supported, no is
conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the column and its temperature program (not collected;
the retention index is judged against the paper's own reference, not against a column); the pH and the temperature of the reaction (the claim carries no
condition, and the identity block records the temperature); the conversion at the sampling time (not collected).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for
this method, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The share of each product of one reaction in the total of the product peaks: a relative readout within one
  chromatogram, absolute in that it is a composition (a fraction of the products), and well defined when the species are identified.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: a terpene synthase or a fatty-acid-modifying enzyme gives a
  reproducible product spectrum, and a GC share by FID of isomers is close to the true share even when little is stated.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme extract is the real gap here: solvent, plastic, column
  bleed and the spontaneous rearrangement of the substrate or of a labile product all give peaks, and a minor product can be one of them. An unstated
  identification leaves a neighbouring isomer a possible reading of the peak. An unstated injector check hides thermal rearrangement (a germacrene
  becoming an elemene in the hot inlet is the textbook case, from memory). An unstated response correction is benign for isomers read by FID and
  worse for MS.
  If we assume it is fine and are wrong, how badly does the score mislead? A background or a rearrangement artefact counted as the enzyme's product
  gives a false product, which is worse than a wrong magnitude; a wrong response factor only moves a share.
  Consistent with KD? Below the KD anchor 0.90 and level with the activity types: 0.80 by default.
  default 0.80. species_identity 0.75 (a peak read as the wrong isomer), background_alternatives 0.70 (the false-product risk above),
  matrix_interference 0.75 (the injector and the extraction decide whether the peak is the product made), response_factors 0.85 and
  calibration_applicability 0.85 (benign for FID isomers), sampling_basis 0.90 (triplicates are usual and an unstated count changes the precision, not
  the existence). attribution_supported, common_denominator, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_distribution_direction import select_product_distribution_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_distribution_gc_converted_v1'
CRITERIA_MAP = {'species_identity': ('species_identification',), 'response_factors': ('response_factors_applied',), 'common_denominator': ('denominator_coverage',),
                'calibration_applicability': ('detection_limit_ratio',), 'matrix_interference': ('injector_stability', 'extraction_recovery'),
                'background_alternatives': ('no_enzyme_control', 'product_stability'), 'attribution_supported': ('inactive_enzyme_control',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
RI_FULL_DIFFERENCE = 5.0  # EXPERT_REVIEW, owner to confirm: retention-index difference (units, from the published value on the same phase) up to which a library identification is fully in agreement (published tolerance about 10, Adams; from memory, not verified); full agreement up to it.
RI_ZERO_DIFFERENCE = 30.0  # EXPERT_REVIEW, owner to confirm: difference at which the measured index is as near a neighbouring isomer as the named compound (neighbouring monoterpenes lie 14 to 30 units apart on a 5 percent phenyl column, from memory, not verified): no agreement, conflicting; the degree falls linearly in the difference (an index is an additive scale).
LIBRARY_MATCH_DEGREE = 0.7  # EXPERT_REVIEW, owner to confirm: the best degree of an identification by library match and retention index, below an identification by an authentic standard (Metabolomics Standards Initiative level 2 against level 1, Sumner et al. 2007, from memory, not verified); a judgement.
FID_UNCORRECTED_DEGREE = 0.8  # EXPERT_REVIEW, owner to confirm: degree of a share from raw FID area percent: FID response is nearly proportional to the oxidizable carbon (effective carbon number, Ackman 1964; Scanlon and Willis 1985, from memory, not verified), so the area percent is the mass percent within about 10 to 20 percent for hydrocarbons and isomers.
MS_UNCORRECTED_DEGREE = 0.5  # EXPERT_REVIEW, owner to confirm: degree of a share from raw mass-spectrometer area percent: electron-impact response differs by a factor of two or more between compounds of different structure (from memory, not verified), so the share is right only within about a factor of two.
IDENTIFIED_FULL_FRACTION = 0.95  # EXPERT_REVIEW, owner to confirm: part of the total area assigned to identified compounds at which the denominator is fully covered (profiles of terpene and essential-oil products assign about 90 to 99 percent, from memory, not verified); full agreement from it.
IDENTIFIED_ZERO_FRACTION = 0.5  # EXPERT_REVIEW, owner to confirm: half of the area unidentified: a share over the identified compounds is too large by a factor of two (no agreement, conflicting); the degree falls linearly in the log of the identified fraction, because the bias is the factor 1 / c.
LIMIT_RATIO_FULL = 10.0  # EXPERT_REVIEW, owner to confirm: share over the smallest integrated or detected share at which the share is quantified (a limit of quantification is about 10 times the noise, a limit of detection about 3.3, ICH Q2(R1), from memory, not verified); full agreement from it.
LIMIT_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a share no larger than the paper's own smallest integrated share is not quantified (no agreement, conflicting); the degree falls linearly in the inverse of the ratio, because the relative error of an area near the limit goes as limit over share.
RECOVERY_FULL = 0.8  # EXPERT_REVIEW, owner to confirm: extraction or sampling recovery at (or above, as 1 / 0.8) which no product is taken to be lost more than another (80 to 110 percent is the usual acceptance range, AOAC single-laboratory validation guidelines, from memory, not verified); full agreement within it.
RECOVERY_ZERO = 0.3  # EXPERT_REVIEW, owner to confirm: a recovery of 30 percent (or 1 / 0.3 above): most of the product is lost or gained and a loss that differs between volatile products cannot be assumed equal (no agreement, conflicting); the degree falls linearly in |ln recovery|, because a recovery is multiplicative.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate reactions; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent reactions falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: a percent is a hundredth of a fraction; the stated number is the paper's.
    'product_fraction': ('fraction', {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION}),
    'product_fraction_ratio': ('dimensionless', {'dimensionless': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['product_distribution']) that names the kind of each effect quantity; literature_product_distribution_direction reads it back.
KIND_OF_QUANTITY = {'product_fraction': 'product_fraction', 'product_fraction_ratio': 'product_fraction_ratio'}
KIND_WITHOUT_EFFECT = 'product_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_gc_extraction_recovery_is_not_the_closure_of_the_products', 'attributed_signal': 'a_product_share_is_the_effect_not_an_attribution_fraction', 'total_signal': 'a_product_share_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_distribution_gc_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_distribution_gc_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "product detected" / "product not detected" for this class
UNCORRECTED_DEGREE = {'flame_ionization': FID_UNCORRECTED_DEGREE, 'mass_spectrometer': MS_UNCORRECTED_DEGREE}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _linear(value):
    """The scale of a quantity whose error is additive (a retention index)."""
    return value


def _inverse(value):
    """The scale of a share over a limit: the relative error of an area near its limit goes as the limit over the share."""
    return 1.0 / value


def _deviation(recovery):
    """How far a recovery is from 1 on the multiplicative scale: |ln recovery| (0.8 and 1.25 are equally far)."""
    return abs(math.log(recovery))


def _degree(value, full, zero, scale=_linear):
    """1.0 at ``full`` (or beyond it), falling linearly in ``scale`` to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``.
    ``scale`` is monotone, so the side test is made on the value itself (before a log could see a value at or below 0)."""
    if (value - zero) * (full - zero) <= 0:
        return None
    return min(1.0, (scale(value) - scale(zero)) / (scale(full) - scale(zero)))


def _graded(refs, degree, ceiling=1.0):
    """Conflicting when the degree is None (at or beyond the zero end); else supported with the degree, at most the ceiling."""
    if degree is None:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, degree * ceiling)


def _judge_identification(native):
    return _graded(native['identification_refs'], _degree(native['retention_index_difference'], RI_FULL_DIFFERENCE, RI_ZERO_DIFFERENCE), LIBRARY_MATCH_DEGREE)


def _judge_response(native):
    return _verdict('supported', native['uncorrected_refs'], UNCORRECTED_DEGREE[native['uncorrected_detector']])


def _judge_coverage(native):
    return _graded(native['identified_refs'], _degree(native['identified_fraction'], IDENTIFIED_FULL_FRACTION, IDENTIFIED_ZERO_FRACTION, math.log))


def _judge_limit(native):
    return _graded(native['limit_refs'], _degree(native['share_over_limit'], LIMIT_RATIO_FULL, LIMIT_RATIO_ZERO, _inverse))


def _judge_recovery(native):
    return _graded(native['recovery_refs'], _degree(_deviation(native['recovery']), _deviation(RECOVERY_FULL), _deviation(RECOVERY_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('species_identification', 'library_identification_recorded_for_the_sheet'): _judge_identification, ('response_factors_applied', 'uncorrected_areas_recorded_for_the_sheet'): _judge_response,
          ('denominator_coverage', 'coverage_recorded_for_the_sheet'): _judge_coverage, ('detection_limit_ratio', 'share_over_limit_recorded_for_the_sheet'): _judge_limit,
          ('extraction_recovery', 'recovery_recorded_for_the_sheet'): _judge_recovery, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'distribution_gc_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][quantity + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, quantity + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    unit, factors = UNIT_FACTORS[quantity]
    sd = spread['value'] * factors[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_distribution_gc(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_product_share_or_ratio_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_product_distribution_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'distribution_gc_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'product_distribution', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'distribution_gc', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['product'] is not None:      # no stated share or ratio: the paper's own statement that the product was found (or not) fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['product']], 'support_refs': list(native['product_refs'])}
        result['direction_field_support'] = native['product_support']      # the support class of the fact claimed_product_detected, the one field the statement is derived from
    return result
