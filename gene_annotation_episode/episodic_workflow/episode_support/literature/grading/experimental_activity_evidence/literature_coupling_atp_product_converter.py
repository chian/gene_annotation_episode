"""Coupling_atp_product converter: turns the grader's result into what the A105 reaction_coupling sheet takes.

Hand-built, private to coupling_atp_product, deterministic. Input: the result of grade_coupling_atp_product. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'reaction_coupling'), the sheet itself (grade_assay run on it), the dependence keys the merger needs and, for every
sheet component that a coupling measurement cannot honestly fill, the reason it stays null. DRAFT 2026-11-22 (owner to correct): the structure is copied
from the spectro_direct converter; the class core (effect, order, anchors) is the reaction_coupling class's (G/literature_reaction_coupling_direction.py).

Quantities filled
-----------------
effect            ONE link in the anchor unit 'fraction', in the class order COUPLING_EFFECT_ORDER (literature_reaction_coupling_direction.select_coupling_effect):
                  1. the PRODUCTIVE FRACTION (the share of the hydrolysed nucleotide that ends in product, the reaction's own coefficient applied), which is
                     the stated productive fraction (a percent is divided by 100), else the stated coefficient over the stated nucleotides per product, else the
                     stated coefficient times the stated product per nucleotide (exact arithmetic on stated numbers, marked origin 'derived');
                  2. the STOICHIOMETRIC RATIO (product per nucleotide, no coefficient applied), which is the stated product per nucleotide, else one over the
                     stated nucleotides per product (derived).
                  The nucleotide cost per product is NOT a fraction (a cost above 1 is the normal result of this method); it is read as a fraction only through
                  the coefficient, or as its reciprocal, the product per nucleotide. The link is never worked out from the amounts or the rates of the two sides.
                  quantity_kind of the extraction names the kind of the effect (productive_fraction or stoichiometric_ratio), which the direction function reads.
effect_variance   variance of that effect in 'fraction_squared', only when the passage's spread of THE QUANTITY THE EFFECT COMES FROM allows it (the spread of a
                  stated cost is carried to the derived fraction or ratio by first-order propagation, sd times the derivative; the coefficient is exact):
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted
                  (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO link is stated: statement 'interaction_detected' (read "coupled product formation detected"), 'interaction_not_detected' (read
                  "no product formed above the paper's own control or detection limit") or 'interaction_not_stated', with the refs of the fact coupled_product_detected
                  that states it; direction_field_support is that fact's quote support (None when not stated). A stated link fixes the direction; the statement is
                  then not used. A result stated in words alone counts less than a measured one (the contract's stated_strength); this file does not re-implement that.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    no_enzyme_control + reagent_blank
attribution_supported      hydrolysis_dependence
calibration_applicability  product_calibration + nucleotide_calibration
product_identity           product_identity
stoichiometry              coefficient_stated + coupling_within_bound
matched_windows            same_mixture + same_window
reporter_specificity       basal_rate_accounted + basal_share + reporter_capacity + nucleotide_supply
sampling_basis             replicates
assertion_relevance        native_reaction
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference) are not selected.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good
value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the paper states
nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion
that is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported
criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped;
a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation, from which both sides of the coupling come, is
analyte_preparation_ref; the other keys stay None (nothing immobilized, no surface). Direction and strength of a stated link:
literature_reaction_coupling_direction (larger is stronger, per-quantity anchors); controls, blanks, windows, the coefficient and the rest lower the WEIGHT only.

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, owner to confirm, and every literature figure is from the drafter's memory,
NOT web-verified and NOT checked against a method paper; verify before relying on any of them.
Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
BASAL_SHARE_FULL 0.10 -> BASAL_SHARE_ZERO 1.0, judged linearly in the basal rate over the total rate (the net share of the total rate).
  Q1 a link between the product and the hydrolysis that is mostly basal (uncoupled) hydrolysis: after the basal rate is taken off the net hydrolysis is a small
  difference of two large numbers and the cost per product is badly determined. Q2 general practice for substrate- or partner-stimulated ATPases (AAA+ ATPases,
  helicases, transporters, nitrogenase) is to report the stimulated rate over the basal rate; a stimulation of tenfold or more (basal share 0.1 or less) is a clean
  subtraction, and twofold to fivefold stimulation (share 0.2 to 0.5) is common and workable (from memory, not verified; lab- and enzyme-specific). Q3 relative to the
  paper's own total rate, which the grader records with the basal rate: right. Q4 the net rate is the total times (1 - share), so a fixed error in the basal rate costs
  the net rate an error that grows as 1 / (1 - share): the degree is the net share (1 - share) relative to its value at the full end, linear in the share, 1 at 0.1,
  0.56 at 0.5, 0.11 at 0.9; at or beyond 1 the basal hydrolysis is the whole hydrolysis and no net coupling is shown (conflicting). Q5 the same idea as the other
  background-share judgements of the class table (full at 10 percent, zero at the whole signal).
NUCLEOTIDE_CONSUMED_FULL_PERCENT 10 -> NUCLEOTIDE_CONSUMED_ZERO_PERCENT 90, judged linearly in the log of the ADP-to-ATP ratio f / (1 - f). It is read only when no
  regenerating system is stated.
  Q1 a measurement over a window in which so much nucleotide was hydrolysed that the ATP has fallen and the ADP (or GDP) has risen: ADP is a competitive product inhibitor
  of most ATPases and the phosphate or NADH signal leaves its linear range, so the rate and the link drift during the window. Q2 general: an initial rate means about 10
  percent consumed at most (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); with no regeneration the ADP-to-ATP ratio is f / (1 - f) and the inhibition
  by ADP goes with it (a Ki of ADP near the Km of ATP is common; from memory, not verified). Q3 relative to the paper's own starting nucleotide, which the passage states as a
  share: right. Q4 the ratio spans two orders between the ends, 0.11 at 10 percent and 9 at 90 percent; a log scale gives half the degree at 50 percent consumed (ADP equal to
  ATP) and falls gently at first and faster later; at or beyond 90 percent the nucleotide is largely gone (conflicting). A regenerating system removes the question (the grader
  returns supported and records no number). Q5 the same kind of ramp as the initial-rate judgement of spectro_direct (10 to 90 percent), on the scale this method's physics gives.
PRODUCTIVE_BOUND_FULL 1.2 -> PRODUCTIVE_BOUND_ZERO 2.0, judged linearly in the log of the productive fraction (read only above the full end).
  Q1 a link that claims more product than the hydrolysed nucleotide can make by the paper's own reaction account (a productive fraction above 1): one side is miscalibrated,
  the coefficient is wrong, or the two sides are not the same reaction. Q2 the combined error of two independent calibrated assays (a phosphate dye and a product assay) is
  commonly 10 to 20 percent (from memory, not verified), so 1.2 allows it; twice the bound (2.0) is beyond any such error. Not a stoichiometry the literature fixes; it is the
  method's own bound. Q3 relative to the paper's own coefficient: right (the grader records which numbers it rests on). Q4 an error of two sides is multiplicative, so the scale
  is the log; a productive fraction below 1 is not judged here (a low fraction is weaker evidence of coupling, and the strength scale reads it). CsiD-style values beyond the bound
  are diagnostics and are not clipped (the effect keeps the stated value); at or beyond 2.0 the stoichiometry criterion is conflicting and the direction is not touched. Q5 a
  ratio judged on the log of the ratio, as the other multiplicative judgements.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a link from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean
  (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the blank, the basal subtraction, the reporter capacity, the regeneration, the hydrolysis dependence, the product identity and
calibrations, the same mixture and window, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is
unknown. They have no researched value to soften. NOT judged, and why: the nucleotide, the readout and the pH and temperature (the claim carries no condition, and the identity
block records the temperature); the cost per product itself (a cost of 4 or of 40 is the paper's measurement, read by the strength scale after the coefficient turns it to a share).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method, decided
2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The ratio of two absolute amounts (nucleotide hydrolysed and product formed), each from its own calibration: dimensionless and
  absolute, but only as good as the worse calibration and the match of the two sides.
  Is there a reference range we would trust if the paper stated less (as for KD)? Only for a few well-studied systems (nitrogenase near 4 to 5 ATP per electron pair, motor and
  helicase step sizes; from memory); no general range for an arbitrary ATP-driven enzyme. Weaker than for KD.
  What does an unstated control or calibration do to the number's meaning? An unstated basal rate is the dominant failure (uncoupled hydrolysis counted as cost makes the cost too
  high by a factor); unstated windows or mixtures make the ratio of two numbers that may not belong together, which can be uninterpretable; a phosphate standard curve or the NADH
  extinction coefficient is routine and benign when unstated; triplicate practice is usual.
  If we assume it is fine and are wrong, how badly does the score mislead? The size of the link is off by a factor, and the existence of coupling can be wrong when the windows
  differ; worse than a KD (a magnitude only), less than a pull-down band (a pure artefact).
  Consistent with KD? The default 0.80 is under the KD anchor 0.90 and under spectro_direct 0.85: a link has two sides to go wrong.
  default 0.80. matched_windows 0.65 and product_identity 0.70 (a ratio of sides that may not be matched, or of a product that may not be the claimed one, is the least
  interpretable), reporter_specificity 0.70 (the unstated basal rate), background_alternatives 0.75, attribution_supported 0.75 (hydrolysis dependence is often shown with a
  dead mutant or analogue but papers leave it unsaid), stoichiometry 0.75 (an unstated coefficient leaves a bare ratio, not a wrong one), calibration_applicability 0.85 and
  sampling_basis 0.90 (benign when unstated). assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reaction_coupling_direction import select_coupling_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_coupling_atp_product_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('no_enzyme_control', 'reagent_blank'), 'attribution_supported': ('hydrolysis_dependence',),
                'calibration_applicability': ('product_calibration', 'nucleotide_calibration'), 'product_identity': ('product_identity',),
                'stoichiometry': ('coefficient_stated', 'coupling_within_bound'), 'matched_windows': ('same_mixture', 'same_window'),
                'reporter_specificity': ('basal_rate_accounted', 'basal_share', 'reporter_capacity', 'nucleotide_supply'), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
BASAL_SHARE_FULL = 0.10  # EXPERT_REVIEW, owner to confirm: basal hydrolysis at most a tenth of the hydrolysis of the reaction that makes the product (a tenfold stimulation; from memory, not verified); full agreement up to it.
BASAL_SHARE_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: basal hydrolysis as large as the whole hydrolysis leaves no net hydrolysis to pair with the product (no agreement); the degree is the net share of the total rate relative to its value at the full end, linear in the share, because a fixed error of the basal rate costs the net rate an error that grows as 1 / (1 - share).
NUCLEOTIDE_CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the starting nucleotide hydrolysed in the window with no regenerating system (the usual initial-rate ceiling; Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement up to it.
NUCLEOTIDE_CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent hydrolysed the nucleotide is largely gone and the ADP-to-ATP ratio is 9 (no agreement); the degree falls linearly in the log of the ADP-to-ATP ratio f / (1 - f) from the full end to here, because ADP inhibits by that ratio (ADP Ki near the ATP Km, from memory, not verified).
PRODUCTIVE_BOUND_FULL = 1.2  # EXPERT_REVIEW, owner to confirm: a productive fraction up to 1.2 is within the combined error of two independent calibrated assays (10 to 20 percent, from memory, not verified); full agreement up to it. A fraction below it is not judged here.
PRODUCTIVE_BOUND_ZERO = 2.0  # EXPERT_REVIEW, owner to confirm: twice what the reaction's own coefficient allows is beyond any such error: a side is miscalibrated, the coefficient is wrong or the sides are not one reaction (no agreement); the degree falls from PRODUCTIVE_BOUND_FULL linearly in the log of the productive fraction, because the errors of the two sides multiply.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The exact factor from each unit of the record's vocabulary to the anchor unit 'fraction' (literature_row_contract.COUPLING_STRENGTH_ANCHORS). A spread has the units of its quantity.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: a percent is a hundredth; a mole per mole is dimensionless; the stated number is the paper's.
    'productive_fraction': {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION},
    'stoichiometric_ratio': {'mol_per_mol': 1.0, 'fraction': 1.0},
    'nucleotides_per_product': {'mol_per_mol': 1.0},
    'stoichiometric_coefficient': {'mol_per_mol': 1.0},
}
ANCHOR_UNIT = 'fraction'
KIND_WITHOUT_EFFECT = 'stoichiometric_ratio'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_coupling_has_no_matrix_recovery_measurement', 'attributed_signal': 'the_link_is_the_effect_not_an_attribution_fraction', 'total_signal': 'the_link_is_the_effect_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_coupling_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_coupling_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "coupled product formation detected" / "no product formed above the control" / "not stated" for this class


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


def _log(value, full, zero):
    """A ratio limit on the log scale, for _graded."""
    return math.log(value), math.log(full), math.log(zero)


def _logit(fraction):
    """The log of the ADP-to-ATP ratio f / (1 - f) of a nucleotide of which the fraction f has been hydrolysed."""
    return math.log(fraction / (1.0 - fraction))


def _number(native, name):
    """The stated quantity (or the spread of a quantity: name ends in '_spread') in the anchor unit, or None when not stated."""
    operand = native['quantities'][name]
    if operand['status'] != 'point':
        return None
    return operand['value'] * UNIT_FACTORS[name.replace('_spread', '')][operand['unit']]


def _item(native, names, value, sd, origin, spread):
    """One link: its value in the anchor unit, the standard deviation of that value carried from the spread of the quantity named ``spread`` (or None), where it comes from."""
    operands = [native['quantities'][name] for name in names]
    return {'value': value, 'sd': sd, 'spread': spread, 'names': names, 'origin': origin,
            'refs': list(dict.fromkeys(ref for operand in operands for ref in operand['source_refs'])),
            'support': max((operand['support'] for operand in operands), key=SUPPORTS.index)}      # the weakest support of the quotes it rests on


def _links(native):
    """The links a record states or allows, by effect quantity: 'productive_fraction' and 'stoichiometric_ratio' (each only when it can be read from stated numbers)."""
    coefficient, fraction = _number(native, 'stoichiometric_coefficient'), _number(native, 'productive_fraction')
    ratio, cost = _number(native, 'stoichiometric_ratio'), _number(native, 'nucleotides_per_product')
    links = {}
    if fraction is not None:
        links['productive_fraction'] = _item(native, ('productive_fraction',), fraction, _number(native, 'productive_fraction_spread'), 'reported', 'productive_fraction')
    elif coefficient is not None and cost is not None:
        spread = _number(native, 'nucleotides_per_product_spread')
        links['productive_fraction'] = _item(native, ('nucleotides_per_product', 'stoichiometric_coefficient'), coefficient / cost, None if spread is None else coefficient * spread / cost ** 2, 'derived', 'nucleotides_per_product')
    elif coefficient is not None and ratio is not None:
        spread = _number(native, 'stoichiometric_ratio_spread')
        links['productive_fraction'] = _item(native, ('stoichiometric_ratio', 'stoichiometric_coefficient'), coefficient * ratio, None if spread is None else coefficient * spread, 'derived', 'stoichiometric_ratio')
    if ratio is not None:
        links['stoichiometric_ratio'] = _item(native, ('stoichiometric_ratio',), ratio, _number(native, 'stoichiometric_ratio_spread'), 'reported', 'stoichiometric_ratio')
    elif cost is not None:
        spread = _number(native, 'nucleotides_per_product_spread')
        links['stoichiometric_ratio'] = _item(native, ('nucleotides_per_product',), 1.0 / cost, None if spread is None else spread / cost ** 2, 'derived', 'nucleotides_per_product')
    return links


def _judge_basal_share(native):
    return _graded(native['basal_refs'], (native['basal_share'], BASAL_SHARE_FULL, BASAL_SHARE_ZERO))


def _judge_consumed(native):
    fraction, zero = native['consumed_percent'] / PERCENT_PER_FRACTION, NUCLEOTIDE_CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', native['consumed_refs'])
    return _graded(native['consumed_refs'], (_logit(fraction), _logit(NUCLEOTIDE_CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION), _logit(zero)))


def _judge_bound(native):
    return _graded(native['link_refs'], _log(_links(native)['productive_fraction']['value'], PRODUCTIVE_BOUND_FULL, PRODUCTIVE_BOUND_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('basal_share', 'basal_share_recorded_for_the_sheet'): _judge_basal_share, ('nucleotide_supply', 'consumed_recorded_for_the_sheet'): _judge_consumed,
          ('coupling_within_bound', 'link_recorded_for_the_sheet'): _judge_bound, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(link, kind, ref):
    """The link as an effect operand in the anchor unit (its 'support' is the weakest of the quotes it rests on)."""
    return _operand(link['value'], ANCHOR_UNIT, 'coupling_atp_product_' + kind + ':' + ref, link['refs'], link['origin'], link['names'][0], link['support'])


def _variance(graded, link):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread the chosen link comes from."""
    native = graded['native']
    spread = native['quantities'][link['spread'] + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, link['spread'] + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = link['sd']
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_coupling_atp_product(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    links = _links(native)
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if not links:
        null_components['effect'] = 'no_coupling_link_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_coupling_effect({kind: _stated_effect(link, kind, ref) for kind, link in links.items()})
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, links[chosen])
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT + '_squared', 'coupling_atp_product_' + chosen + '_variance:' + ref, variance_refs, 'derived', links[chosen]['spread'] + '_spread')
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
    preparations = native['preparations']
    result = {'version': VERSION, 'experiment_type': 'coupling_atp_product', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(preparations), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated link: the paper's own statement of product formation above its control stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENT[native['coupling']], 'support_refs': list(native['coupling_refs'])}
        result['direction_field_support'] = native['coupling_support']      # the support class of the fact coupled_product_detected, the one field the statement is derived from; None when not stated
    return result
