"""Transport_counterflow converter: turns the grader's result into what the A105 transport_response sheet takes.

Hand-built, private to transport_counterflow, deterministic. Input: the result of grade_transport_counterflow. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every
sheet component that a counterflow cannot honestly fill, the reason it stays null. Built from the spectro_direct converter, with the class core of
transport_response (G/literature_transport_response_direction.py) in place of the activity class core.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the Km of the external substrate (uM), the fold over the paper's own control
                  (dimensionless) or the exchange rate per mass (nmol/min/mg). The fold has two sources in the record, tried in this order: the fold of
                  the preloaded over the non-preloaded uptake (fold_over_control, the experiment's own baseline), then the overshoot ratio (the peak
                  over the equilibrium level reached later); both are a ratio over the experiment's own baseline and take the anchors of the class
                  quantity 'fold_over_control'. Several quantities may be stated; the one used is the best-determined, in the class order
                  TRANSPORT_EFFECT_ORDER (literature_transport_response_direction.select_transport_effect): Km, then the fold, then the rate per mass.
                  A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value
                  is the paper's, only its unit spelling changes ('fold' is read as 'dimensionless'). quantity_kind of the extraction names the kind of the
                  effect (KIND_OF_ANCHOR), which the direction function reads. The overshoot ratio is a ratio of two amounts of label and not of two rates; the
                  sheet has no kind for a ratio of amounts, so it takes the kind transport_rate_ratio (the kind substrate_response_ratio would make the
                  criterion transport_response_model required for a result that has no concentration series).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS). The preload contrast (preloaded over non-preloaded) IS the effect when the fold is stated; it is
not also used as a condition response (condition_test / condition_reference), which would count the same contrast twice.
qualitative_effect  only when NO effect is stated and the paper states whether it saw counterflow above its own baseline: statement
                  'interaction_detected' (read "transport detected") or 'interaction_not_detected' (read "transport not detected"), with the refs of the
                  fact that states it, and direction_field_support taken from the quote support of that one fact. A stated effect fixes the direction;
                  the statement is then not used. A result stated in words alone counts less than a measured one (the contract's stated_strength); that
                  is not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   non_preloaded_baseline (the same preparation without the preload: the baseline of the trans-effect)
attribution_supported     protein_free_control (the same preload and uptake without the protein)
transport_specificity     non_substrate_preload + label_identity
transport_driving_force   preload_verified + preload_over_label
membrane_system           preload_retained
transport_endpoint        uptake_endpoint
transport_response_model  substrate_range
assertion_relevance       native_substrate
sampling_basis            replicates
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, calibration_applicability, matrix_interference, condition_scope) are not selected: a
counterflow result is a ratio of two counts of the same label in the same preparation, so the specific activity of the label and the counting calibration
cancel.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the
researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step),
unknown when the paper states nothing, never conflicting for a short count. A substrate series at or beyond its zero end is conflicting (what the paper itself
shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not
selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the preparation that carries the protein is analyte_preparation_ref, the
vesicle or proteoliposome batch is immobilized_preparation_ref, surface_ref stays None (no electrode); no passage states them, so all four stay None. Qualitative
statements keep the existing vocabulary, read "transport detected / not detected". Direction and strength of a stated quantity:
literature_transport_response_direction (same paradigm as binding and activity); controls, the preload and the rest lower the WEIGHT only. The claim names a
transporter (subject) and the transported molecule (partner); in a heterologous exchange the molecule preloaded inside and the molecule labelled outside differ,
and the record does not say which one the claim's partner is (open question reported to the owner).

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW and every one is from the drafter's memory of the counterflow
literature and the Michaelis-Menten physics, NOT web-verified and NOT checked against a method paper; verify before relying on any of them. The owner's questions are asked
of each value (Q1 failure caught, Q2 general or lab-specific, Q3 absolute or relative, Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency
with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
PRELOAD_RATIO_FULL 10 -> PRELOAD_RATIO_ZERO 1, judged on the log of the preloaded substrate over the external substrate.
  Q1 a counterflow whose preloaded substrate is not large against the substrate outside cannot show an overshoot: the label inside can at most rise to the point
  where its specific activity equals that outside, so the peak over the later equilibrium level is capped near the ratio of the preloaded to the external substrate
  (Kaback's lactose counterflow; Stein, Channels, Carriers and Pumps; Maloney's reconstituted-transporter counterflow; all from memory). Q2 general physics of a
  one-to-one exchange, not lab-specific; designs load tens of mM against uM to hundreds of uM outside, a ratio of 10 to several thousand (from memory). Q3 relative
  to the paper's own two concentrations, which the grader records. Q4 the cap grows in proportion to the ratio, so the degree is linear in the log of it: at 10 the
  overshoot can reach about tenfold, far above the 10 to 20 percent scatter of tracer counting, and a bigger ratio adds little; at 1 (equal concentrations, equilibrium
  exchange) an overshoot is impossible. The ratio below 1 gets degree 0. It is supported with degree 0, NEVER conflicting: equilibrium exchange at equal concentrations
  is a legitimate design for the fold of the preloaded over the non-preloaded uptake, so a low ratio lowers the degree and is not the paper against the standard.
  Q5 the same shape as the other ratio judgements (a log-ratio ramp); no other transport type has a preload.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few external concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight concentrations spanning 0.2 to
  10 times the Km (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual; from memory), the same practice as the activity assays. Q3 absolute (a count). Q4 the
  Michaelis-Menten equation has two parameters, so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never
  conflicting); each added concentration adds one residual degree of freedom (linear in count - 2). Q5 the same residual-degree-of-freedom count as the SPR
  steady-state KD and the spectro_direct series.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest external substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). Q2 general: 0.2 to 10 times the Km. Q3
  relative to the paper's own Km (the grader records both ratios). Q4 the exchange rate is v / Vmax = S / (S + Km), so both ends are judged linearly in the
  fractional saturation S / (S + Km) (1/6 at 0.2 Km, 10/11 at 10 Km, 1/2 at the Km, the zero end of both). Q5 working rule d of the SOP: 10 where the plateau
  (Vmax) is a free amplitude known only by reaching it, as in the spectro_direct series.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a ratio from one batch of vesicles or one culture, whose batch-to-batch spread (loading, protein amount, leak) is unseen. Q2 general (triplicate practice). Q3
  absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the non-preloaded baseline, the protein-free control, the non-substrate preload, the label identity, the verified preload, the retained preload, the
equilibrium or linear interval, the native substrate): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no
researched value to soften. NOT judged, and why: the time of the peak and the time of the interval (they depend on the carrier's turnover and the leak of the
vesicles, and no general limit exists); the label's specific activity (it cancels in a ratio of two counts of the same label); the stated overshoot or fold itself (it is
the effect; its scale is the class anchor of fold_over_control, in the direction module).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method,
decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? How much faster a preloaded preparation takes up a label than the same preparation without the preload, or how far
  the label rises above its own equilibrium level: relative, a ratio of two counts of one label in one preparation. It shows that the transporter recognizes the
  preloaded and the labelled molecule on opposite sides (exchange), not how fast or how tightly.
  Is there a reference range we would trust if the paper stated less (as for KD)? No: there is no well-established range of trans-stimulation folds or overshoots; the
  anchors only say that a larger fold shows a clearer exchange.
  What does an unstated control or calibration do to what the number means? The label's calibration cancels. The non-preloaded baseline and the protein-free control
  are what make the ratio mean the protein: unstated, the common case is benign (every counterflow has the non-preloaded sample), but in cells another carrier of the
  same molecule or a metabolic trap can mimic exchange. A leak of the preloaded substrate lowers the overshoot and does not create one.
  If we assume it is fine and are wrong, how badly does the score mislead? An exchange by another carrier counted as the protein's gives the wrong protein a substrate;
  more than a KD (a magnitude only) and less than a pull-down band (a pure artefact).
  Consistent with KD? Below it (0.90) and just below spectro_direct (0.85): a relative readout with no trusted reference range.
  default 0.80. background_alternatives 0.75 (the non-preloaded sample is what the trans-effect is read against). attribution_supported 0.70 (the protein-free control
  is what ties the exchange to the protein and not to other carriers). transport_specificity 0.70 (the non-substrate preload is the defining specificity control of a
  counterflow). membrane_system 0.75 (retention of the preload is what keeps the gradient). transport_driving_force 0.85 and sampling_basis 0.90 (benign when
  unstated: the loading concentrations are in the methods of nearly every paper, and triplicates are usual for a ratio). transport_endpoint, transport_response_model,
  assertion_relevance take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_counterflow_converted'
CRITERIA_MAP = {'background_alternatives': ('non_preloaded_baseline',), 'attribution_supported': ('protein_free_control',), 'transport_specificity': ('non_substrate_preload', 'label_identity'),
                'transport_driving_force': ('preload_verified', 'preload_over_label'), 'membrane_system': ('preload_retained',), 'transport_endpoint': ('uptake_endpoint',),
                'transport_response_model': ('substrate_range',), 'assertion_relevance': ('native_substrate',), 'sampling_basis': ('replicates',)}
PRELOAD_RATIO_FULL = 10.0  # EXPERT_REVIEW, owner to confirm: preloaded substrate at least this multiple of the substrate outside: the overshoot over the equilibrium level can then reach about tenfold, far above the scatter of tracer counting (counterflow physics; Kaback, Stein, Maloney, from memory, not verified); full agreement from it.
PRELOAD_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: equal substrate inside and outside (equilibrium exchange): an overshoot is impossible (degree 0), but the design still gives the fold of preloaded over non-preloaded uptake, so it is supported with degree 0 and never conflicting; between this and PRELOAD_RATIO_FULL the degree rises linearly in the log of the ratio, because the cap of the overshoot is proportional to it. From memory, not verified.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest external substrate concentrations of a usable saturation series (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest external substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest external substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each record quantity that can be the effect (the class anchors, literature_row_contract.TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 mM is 1000 uM; 1 nM is 0.001 uM; 1 umol is 1000 nmol; 1 pmol is 0.001 nmol; a fold is a dimensionless ratio); the stated number is the paper's.
    'km': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
    'normalized_rate': ('nmol/min/mg', {'pmol/min/mg': 1.0e-3, 'nmol/min/mg': 1.0, 'umol/min/mg': 1.0e3}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
    'overshoot_ratio': ('dimensionless', {'fold': 1.0}),
}
# (anchor quantity of TRANSPORT_EFFECT_ORDER, record quantity that states it), in the order a record quantity is tried for an anchor: the fold of the preloaded over the non-preloaded uptake before the overshoot ratio.
EFFECT_SOURCES = (('transport_km', 'km'), ('normalized_rate', 'normalized_rate'), ('fold_over_control', 'fold_over_control'), ('fold_over_control', 'overshoot_ratio'))
# The quantity_kind (QUANTITY_KINDS['transport_response']) that names the kind of each effect anchor; literature_transport_response_direction.transport_quantity reads it back.
KIND_OF_ANCHOR = {'transport_km': 'transport_parameter', 'normalized_rate': 'transport_rate', 'fold_over_control': 'transport_rate_ratio'}
KIND_WITHOUT_EFFECT = 'transport_rate_ratio'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_counterflow_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_counterflow_is_not_an_attribution_fraction', 'total_signal': 'a_counterflow_is_not_an_attribution_fraction',
                'condition_test': 'the_preload_contrast_is_the_effect_itself_and_not_a_nuisance_condition_response', 'condition_reference': 'the_preload_contrast_is_the_effect_itself_and_not_a_nuisance_condition_response',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "transport detected" / "transport not detected" for this class


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


def _judge_preload_ratio(native):
    # linear in the log of the ratio from PRELOAD_RATIO_ZERO (degree 0) to PRELOAD_RATIO_FULL (degree 1); supported with degree 0 below the zero end, never conflicting (equilibrium exchange is a legitimate design)
    position = (math.log(native['preload_over_label']) - math.log(PRELOAD_RATIO_ZERO)) / (math.log(PRELOAD_RATIO_FULL) - math.log(PRELOAD_RATIO_ZERO))
    return _verdict('supported', native['preload_ratio_refs'], max(0.0, min(1.0, position)))


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
JUDGES = {('preload_over_label', 'preload_ratio_recorded_for_the_sheet'): _judge_preload_ratio, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated record quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_counterflow_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of the record quantity ``quantity``."""
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


def convert_transport_counterflow(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {}
    for anchor, quantity in EFFECT_SOURCES:
        operand = _stated_effect(native, quantity, ref)
        if operand is not None and anchor not in stated:
            stated[anchor] = operand
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if not stated:
        null_components['effect'] = 'no_transport_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen_anchor, effect = select_transport_effect(stated)
        chosen = effect['native_component']      # the record quantity that states it
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_ANCHOR[chosen_anchor], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_counterflow_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'transport_counterflow', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['transport'] is not None:      # no stated quantity: the paper's own statement of counterflow above its baseline fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['transport']], 'support_refs': list(native['transport_refs'])}
        result['direction_field_support'] = native['transport_support']
    return result
