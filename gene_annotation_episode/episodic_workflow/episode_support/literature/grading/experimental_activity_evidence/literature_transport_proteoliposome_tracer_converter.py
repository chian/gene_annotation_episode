"""Transport_proteoliposome_tracer converter: turns the grader's result into what the A105 transport_response sheet takes.

Hand-built, private to transport_proteoliposome_tracer, deterministic. DRAFT built 2026-11-22 on the shape of literature_spectro_direct_converter.py with the class core of
transport_response (A105_TRANSPORT_RESPONSE_INVENTORY.md and literature_transport_response_direction.py), owner to correct. Input: the result of
grade_transport_proteoliposome_tracer. Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run
on it), the dependence keys the merger needs, and for every sheet component that a proteoliposome tracer measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the Km of the substrate (uM), the turnover per transporter molecule (s^-1), the fold over the
                  paper's own protein-free liposomes (dimensionless) or the rate per mg of protein (nmol/min/mg). Several may be stated; the one used is the best-determined,
                  in the class order TRANSPORT_EFFECT_ORDER (literature_transport_response_direction.select_transport_effect; the reason is in the contract). A stated value in
                  another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling
                  changes. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads. An accumulated amount at a
                  time is not an effect (class decision).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "transport detected"), 'interaction_not_detected' (read "transport not detected") or
                  'interaction_not_stated', with the refs of the fact transport_detected_above_control that states it; direction_field_support is then the quote support of that
                  one fact (None when it is not stated). A stated effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a
                  measured one by the contract (stated_strength); that is not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   empty_liposome_control
membrane_system           empty_liposome_control + leak_check
attribution_supported     inactive_protein_control + protein_amount_basis
calibration_applicability  active_fraction
transport_driving_force   no_gradient_control + gradient_verified
transport_specificity     competitor_control + substrate_identity
transport_endpoint        initial_rate_regime
transport_response_model  substrate_range
sampling_basis            replicates
assertion_relevance       native_substrate
condition_scope           purified_protein
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference) are not selected: the passage-level facts of this method do not answer them.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value, falling
smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states nothing, never
conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported
carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes
a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are
all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the purified protein preparation is analyte_preparation_ref and the reconstituted
proteoliposome batch is immobilized_preparation_ref; surface_ref stays None (no electrode); the keys are taken from the record as the merger gives them. Qualitative
statements keep the existing vocabulary. Direction and strength of a stated effect: literature_transport_response_direction (larger is stronger, except the Km where smaller
is stronger); controls, the gradient and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
EQUILIBRIUM_FULL_PERCENT 10 -> EQUILIBRIUM_ZERO_PERCENT 80, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the average over an uptake time course that has already bent towards its plateau, so the rate is too low. Q2 general: an initial rate is
  taken while uptake is still a small part of the plateau (the usual statement is about 10 to 20 percent of equilibrium; Cornish-Bowden and the transport-assay practice of
  taking the first, linear points; from memory, not verified). Q3 relative to the paper's own plateau, which the passage can state as a share; right. Q4 the physics gives the
  shape: uptake into a closed vesicle approaches its plateau as 1 - exp(-k t), so the rate averaged over the window is f / -ln(1 - f) of the initial rate, f the fraction of the
  plateau reached: 0.95 at 10 percent, 0.90 at 20, 0.72 at 50, 0.50 at 80. The degree is linear in that bias between the two ends, so it falls gently at first and faster
  later. The zero end is the share at which the averaged rate is only half the initial one (80 percent, a factor of 2); at or beyond it the paper shows the rate is not an
  initial rate (conflicting). The zero end is 80 and not nearer 90 (the activity assays' share of the substrate consumed) because the driving force does not hold: a proton or
  ion gradient is used up by the flux in the small internal volume and an electrogenic flux builds an opposing potential, so the real time course bends earlier than the
  first-order shape says (from memory, not verified). Q5 the same bias shape as the activity assays' share of the substrate consumed,
  with its own zero end because the vesicle gradient runs down.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation series of about six to eight concentrations (Cornish-Bowden;
  transport-kinetics practice in proteoliposomes, from memory); the exact 6 is a judgement. Q3 absolute (a count). Q4 the Michaelis-Menten equation has two parameters (Km and
  Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (supported with degree 0, never conflicting); each added concentration is one
  more point the fitted curve must pass through: the degree rises linearly with count - 2 (4 give 1/2, 5 give 3/4). Q5 the same residual-degree-of-freedom count as the other
  Km series.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0 and HIGH_FACTOR 5 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). Q2 general: about 0.2 to 5 times the Km for a
  radiotracer uptake into proteoliposomes (from memory, not verified); the top is 5 and not 10 because the labelled substrate is costly and is diluted with unlabelled
  substrate at high concentration, and because a high substrate concentration changes the osmolarity of the outside medium and the gradient of the vesicles. Q3 relative to the
  paper's own Km (the grader records both ratios): right. Q4 the rate is v / Vmax = S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km)
  (1/6 at 0.2 Km, 5/6 at 5 Km; 1/2 at the Km, the zero end of both). Q5 SOP working rule d: 5 where the plateau is constrained independently, 10 where it is a free amplitude
  known only by reaching it; this type takes 5 although Vmax is a free amplitude, for the practical reasons above (owner to decide; the cell tracer type of the class takes 10).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one reconstitution, whose protein-preparation-to-preparation spread (orientation, incorporation, lipid) is unseen. Q2 general: three independent experiments;
  for proteoliposomes the independent unit is a reconstitution or a protein preparation, not a sample of one batch (the grader's replicates fact says it). Q3 absolute count.
  Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the empty-liposome control, the inactive-protein control, the no-gradient control, the gradient check, the leak check, the competitor, the label
identity, the protein amount after reconstitution, the active fraction, the native substrate and the purified protein): the paper's own statement decides; yes is supported,
no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the lipid-to-protein ratio, the vesicle size, the temperature and the pH
(the claim carries no condition and the identity block records the temperature; the ratio and size change the magnitude of a rate per mg, not the existence of transport);
the driving force and the flux direction are plain choices, recorded only.

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, decided
2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The movement of a labelled substrate into or out of vesicles that hold only one purified protein, lipid and an imposed
  gradient: an absolute rate when the specific activity of the label and the protein amount are known, a relative one (a fold over empty liposomes) otherwise; the Km is
  absolute and intensive.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes for the Km and the turnover of carriers (Km from 1 uM to 1 mM, turnover 1 to 100 per
  second, from memory); the strength anchors are built on it. The cleanest system for "this protein moves this substrate".
  What does an unstated control or calibration do to the number's meaning? An unstated empty-liposome control is the dominant false positive (leak, label sticking to the lipid
  or the filter, a co-purified contaminating transporter), though practically every paper runs it; an unstated driving-force control or gradient check leaves the energization
  ambiguous but not the existence of transport; an unstated protein amount after reconstitution changes the magnitude of a rate per mg and not its existence; an unstated label
  identity is benign in a purified system (no cellular metabolism).
  If we assume it is fine and are wrong, how badly does the score mislead? A leak or non-specific uptake counted as transport: the direction is wrong for a weak signal and the
  magnitude for a strong one; less severe than a pull-down band (a pure artefact), more than a KD (a magnitude only).
  Consistent with KD? The default 0.85 is just under the KD anchor 0.90, as for the direct spectrophotometric assay: a rate has a few more ways to be wrong than a KD by a
  label-free method; the criteria that guard against a false transport are lower, the benign ones are at 0.90.
  default 0.85. background_alternatives 0.75 (a real gap: the empty liposomes separate carrier-mediated transport from leak and sticking). membrane_system 0.80 (the tightness
  of the vesicles is often unstated, and the empty-liposome control is part of it). transport_driving_force 0.80 (the gradient and its control define the flux; an unstated
  control leaves a real doubt although a uniporter needs none). transport_specificity 0.90 (a competitor is evidence of specificity but its absence does not invalidate a
  purified system; label identity is benign here). calibration_applicability 0.90 and sampling_basis 0.90 (benign when unstated: the active fraction changes the size of a
  turnover, not its existence, and triplicates are usual). attribution_supported, transport_endpoint, transport_response_model, assertion_relevance and condition_scope take the
  default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_proteoliposome_tracer_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('empty_liposome_control',), 'membrane_system': ('empty_liposome_control', 'leak_check'),
                'attribution_supported': ('inactive_protein_control', 'protein_amount_basis'), 'calibration_applicability': ('active_fraction',),
                'transport_driving_force': ('no_gradient_control', 'gradient_verified'), 'transport_specificity': ('competitor_control', 'substrate_identity'),
                'transport_endpoint': ('initial_rate_regime',), 'transport_response_model': ('substrate_range',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_substrate',), 'condition_scope': ('purified_protein',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
EQUILIBRIUM_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: an initial rate is taken while at most about 10 percent of the plateau uptake is reached (usual practice is 10 to 20 percent; from memory, not verified); full agreement up to it (the averaged rate is then 0.95 of the initial one).
EQUILIBRIUM_ZERO_PERCENT = 80.0  # EXPERT_REVIEW, owner to confirm: at 80 percent of the plateau the rate averaged over a first-order approach is 0.50 of the initial one, a factor 2 off, and the vesicle gradient has run down besides: an approach to equilibrium, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation series (about six to eight, Cornish-Bowden; transport practice, from memory, not verified); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 5.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 5/6 of Vmax); a labelled substrate in proteoliposomes is costly, is diluted with unlabelled substrate at high concentration and changes the osmolarity (from memory, not verified); the SOP rule d would give 10 for a free amplitude: owner to decide; full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments (independent reconstitutions or protein preparations); full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (the contract's TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 nM is 1e-3 uM; 1 mM is 1e3 uM; 60 s is 1 min; 1 pmol is 1e-3 nmol; 1 umol is 1e3 nmol; a stated "n-fold" is the ratio n); the stated number is the paper's.
    'km': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
    'turnover': ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
    'normalized_rate': ('nmol/min/mg', {'pmol/min/mg': 1.0e-3, 'nmol/min/mg': 1.0, 'umol/min/mg': 1.0e3}),
}
# The name of each effect quantity in the class order TRANSPORT_EFFECT_ORDER (select_transport_effect reads these keys).
ANCHOR_QUANTITY = {'km': 'transport_km', 'turnover': 'turnover', 'fold_over_control': 'fold_over_control', 'normalized_rate': 'normalized_rate'}
# The quantity_kind (QUANTITY_KINDS['transport_response']) that names the kind of each effect quantity; the direction function reads it back (the kind 'transport_rate' is told apart by the effect's unit).
KIND_OF_QUANTITY = {'km': 'transport_parameter', 'turnover': 'transport_rate', 'fold_over_control': 'transport_rate_ratio', 'normalized_rate': 'transport_rate'}
KIND_WITHOUT_EFFECT = 'transport_rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_proteoliposome_tracer_experiment_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_proteoliposome_transport_value_is_not_an_attribution_fraction', 'total_signal': 'a_proteoliposome_transport_value_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_proteoliposome_tracer_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_proteoliposome_tracer_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "transport detected" / "transport not detected" / "transport not stated" for this class


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


def _saturation(ratio):
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order approach to the plateau that has reached the fraction f of it."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _judge_regime(native):
    refs = native['equilibrium_refs']
    fraction, zero = native['equilibrium_percent'] / PERCENT_PER_FRACTION, EQUILIBRIUM_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(EQUILIBRIUM_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_series(native):
    # the two ratios keep their ramps (conflicting at their zero end), judged on the fractional saturation; the lower end is judged only when the series
    # has one distinct from its upper end (one concentration is a short series, not a badly placed one). The count only lowers the degree, never conflicts.
    refs = native['concentration_refs']
    low, high = native['concentration_low_over_km'], native['concentration_high_over_km']
    limits = [(_saturation(high), _saturation(HIGH_FACTOR), _saturation(HIGH_ZERO_FACTOR))]
    if low < high:
        limits.append((_saturation(low), _saturation(LOW_FACTOR), _saturation(LOW_ZERO_FACTOR)))
    verdict = _graded(refs, *limits)
    if verdict['status'] == 'conflicting':
        return verdict
    count_degree = max(0.0, min(1.0, _share(native['concentration_count'], MIN_SUBSTRATE_CONCENTRATIONS, SUBSTRATE_CONCENTRATIONS_ZERO)))
    return _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'equilibrium_recorded_for_the_sheet'): _judge_regime, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_proteoliposome_tracer_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_transport_proteoliposome_tracer(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {ANCHOR_QUANTITY[quantity]: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_transport_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        anchor, effect = select_transport_effect(stated)
        chosen = next(quantity for quantity, name in ANCHOR_QUANTITY.items() if name == anchor)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_proteoliposome_tracer_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'transport_response', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'transport_proteoliposome_tracer', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of transport above its control fixes the direction (the quote support of the one fact it is derived from)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['transport']], 'support_refs': list(native['transport_refs'])}
        if native['transport'] is not None:
            result['direction_field_support'] = native['transport_support']
    return result
