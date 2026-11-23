"""Transport_cell_tracer_uptake converter: turns the grader's result into what the A105 transport_response sheet takes.

Hand-built, private to transport_cell_tracer_uptake, deterministic. Input: the result of grade_transport_cell_tracer_uptake. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
qualitative effect when no quantity is stated, and for every sheet component that a whole-cell tracer uptake cannot honestly fill, the reason it stays null.
It is a draft built 2026-11-22 on the shape of spectro_direct_converter.py, with the class core of transport_response (A105_TRANSPORT_RESPONSE_INVENTORY.md,
sections 2 and 4; literature_transport_response_direction.py).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the Km (uM, kind transport_parameter), the fold over the paper's own control
                  (dimensionless, kind transport_rate_ratio) or the uptake rate per mass of cells (nmol/min/mg, kind transport_rate). Several may be stated; the
                  one used is the best-determined, in the class order TRANSPORT_EFFECT_ORDER (literature_transport_response_direction.select_transport_effect:
                  Km, then fold over the control, then rate per mass). A stated value in another unit of the record's vocabulary is multiplied by its exact
                  factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. The paper's "n-fold" is the
                  dimensionless ratio n. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
                  An accumulated amount, a rate per cell and a current are not effects and are not in the record.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level
                  and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative
predictions.
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "transport detected"), 'interaction_not_detected' (read "transport not
                  detected") or 'interaction_not_stated', with the refs of the fact uptake_detected_above_control that states it; direction_field_support is the quote
                  support of that one fact. A stated effect fixes the direction; the statement is then not used. A result stated in words alone already counts less than a
                  measured one (the contract's stated_strength); this file does not repeat it.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    background_controls (empty-vector or zero-time sample)
attribution_supported      expression_confirmed
calibration_applicability  specific_activity_stated
assertion_relevance        native_substrate
membrane_system            cell_integrity
transport_endpoint         initial_rate_regime
transport_driving_force    energy_dependence
transport_specificity      competitor_control + label_identity
transport_response_model   substrate_range
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, matrix_interference, condition_scope) are not selected: the identity block records the
temperature and the pH, and no tracer-uptake fact is asked for the other two.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched
good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper
states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet
criterion that is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a
supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members
are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the cell culture (or transfection) is analyte_preparation_ref; the other keys stay
None (whole cells have no vesicle batch and no electrode). Qualitative statements keep the existing vocabulary, read "transport detected / not detected / not
stated". Direction and strength of a stated quantity: literature_transport_response_direction (same paradigm as binding and activity; for the Km smaller is
stronger, for the fold and the rate larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value
misleads and whether the shape fits, Q5 consistency with the other assays). EVERY number below is EXPERT_REVIEW, owner to confirm, and every literature
statement is "from memory, not verified": none was checked against a paper in this draft.
-----------------------------------------------------------------------------------------------------------------------------------
TIME_FULL_SECONDS 60 -> TIME_ZERO_SECONDS 3600 with TIME_CONSTANT_SECONDS 300, judged on the bias of the average rate (initial_rate_regime).
  Q1 an "initial rate" that is really the average over an uptake that has already bent towards its steady state (the label leaves again, is metabolized,
  or the cells fill up), so the rate is too low; or an accumulation over hours called a rate (a 3.5 h accumulation is not an initial rate). Q2 general:
  whole-cell uptake rates are taken from the linear part of the time course, usually 10 s to 2 min (the FucP case used 120 s, the BtsT case the first 30 s);
  the time constant is a rough figure for how fast a good carrier in a bacterial cell approaches its steady state (about 5 minutes; from memory, not
  verified); cells and carriers differ. Q3 absolute (a time), but the right scale is the time against the approach to the steady state of the paper's own
  system, which the grader cannot know; the paper's own statement that the interval is linear (the fact linear_interval_shown) decides first and is
  not judged here. Q4 the physics gives the shape: for a first-order approach to a steady state with time constant tau the rate averaged over an
  interval t is (1 - exp(-t / tau)) / (t / tau) of the initial rate, so the shortfall is 1 - (1 - exp(-t / tau)) / (t / tau): 0.09 at 60 s, 0.18 at 120 s,
  0.83 at 30 min, 0.92 at 60 min (tau 300 s). The degree is linear in that shortfall between the two ends, so 120 s gets about 0.90, 10 min about 0.4 and 30 min
  about 0.10; one hour or longer is an accumulation, not a rate (conflicting). Q5 the same idea as the consumed-substrate curve of spectro_direct: a
  bias that grows with the departure from the researched value; the zero end is where the shortfall passes about 0.92.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation series of about six to eight concentrations
  spanning 0.2 to 10 times the Km (Cornish-Bowden; the transport literature uses the same practice, from memory); the exact 6 is a judgement. Q3 absolute
  (a count). Q4 the Michaelis-Menten equation has two parameters (Km and Vmax), so two concentrations are used up by the fit and leave no residual degree
  of freedom (supported with degree 0, never conflicting); each added concentration is one more point the curve must pass through: the degree rises
  linearly with count - 2 (4 give 1/2, 5 give 3/4). A fitted non-saturable (diffusion) term, which cells often have, would use a third parameter; it is
  not assumed. Q5 the same residual-degree-of-freedom count as spectro_direct and the SPR steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). Q2 general: 0.2 to 10 times
  the Km, from memory; in transport work the top is often held lower by the cost of the labelled substrate and by a non-saturable component that grows with
  concentration, so a series that stops at 5 times the Km is common and gets about 0.8 of the top ramp. Q3 relative to the paper's own Km (the grader records both
  ratios): right. Q4 the rate is v / Vmax = S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km) (1/6 at 0.2 Km, 10/11 at
  10 Km; 1/2 at the Km, the zero end of both). Q5 SOP rule d: the top is 10 where the plateau (Vmax) is a free amplitude known only by reaching it, as it
  is in cells (the maximal rate depends on how much protein each cell holds); 5 only where it is constrained independently.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose culture-to-culture spread is unseen (repeated filters of one sample share one culture and one induction). Q2 general
  (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the expression, the cell integrity, the competitor, the label identity, the energy dependence, the native substrate): the
paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the
specific activity's value (it is the paper's own constant; a wrong one shows as an implausible rate, which the strength scale already reads); the temperature and
the pH (the claim carries no condition, and the identity block records them); the size of the fold over the control (it is the effect, graded on its own scale by
the direction function, not a quality of the experiment).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay,
decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The label kept by living cells, turned into an amount per mg by the specific activity: absolute in form (pmol/min/mg,
  Km), but its meaning rests on the matched control cells (the host takes up and metabolizes the substrate too): absolute number, relative meaning.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: the Km of nutrient carriers (about 1 to 1000 uM) and the rates of well
  expressed carriers (about 0.1 to 10 nmol/min/mg) are known ranges (from memory), but the rate depends on expression, which a paper may not state.
  What does an unstated control or calibration do to what the number means? An unstated empty-vector control is the dominant false positive of the assay: other
  host transporters or metabolism of the label can be the whole signal. An unstated label identity matters too (a metabolite or trapped label is not transport).
  An unstated specific activity is benign (suppliers' values are known and a rate per mg was derived with it).
  If we assume it is fine and are wrong, how badly does the score mislead? A host background counted as the protein's transport gives the wrong direction for a weak
  uptake and a wrong size for a strong one: worse than a KD (a size only), less than a pull-down band (a pure artefact).
  Consistent with KD? The default 0.75 is below spectro_direct (0.85, a purified enzyme with one dominant false positive, the blank) because whole cells have
  more ways to be wrong; the two guards (background, specificity) are lower, the benign details are near the KD anchor.
  default 0.75. background_alternatives 0.65, transport_specificity 0.65 (the host background and the label identity), attribution_supported 0.80 (the protein is
  presumed present), membrane_system 0.85 and transport_driving_force 0.85 (routine filtration assays use intact cells; an energy test is an extra),
  assertion_relevance 0.85, sampling_basis 0.85, calibration_applicability 0.90, transport_response_model 0.90 (the series is usually in a figure and the Km is
  stated); transport_endpoint takes the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_cell_tracer_uptake_converted'
CRITERIA_MAP = {'background_alternatives': ('background_controls',), 'attribution_supported': ('expression_confirmed',), 'calibration_applicability': ('specific_activity_stated',),
                'assertion_relevance': ('native_substrate',), 'membrane_system': ('cell_integrity',), 'transport_endpoint': ('initial_rate_regime',),
                'transport_driving_force': ('energy_dependence',), 'transport_specificity': ('competitor_control', 'label_identity'), 'transport_response_model': ('substrate_range',),
                'sampling_basis': ('replicates',)}
TIME_FULL_SECONDS = 60.0  # EXPERT_REVIEW, owner to confirm: a whole-cell uptake interval of up to about a minute is an initial rate for a carrier of ordinary speed (usual intervals are 10 s to 2 min; from memory, not verified); full agreement up to it.
TIME_ZERO_SECONDS = 3600.0  # EXPERT_REVIEW, owner to confirm: an hour or more is an accumulation and not a rate (the average rate is then below about a tenth of the initial one with the time constant below; a 3.5 h accumulation is not an initial rate); no agreement at or beyond it (conflicting); the degree falls from TIME_FULL_SECONDS linearly in the shortfall of the average rate.
TIME_CONSTANT_SECONDS = 300.0  # EXPERT_REVIEW, owner to confirm: the time constant of the approach of the uptake to its steady state for a good carrier in a bacterial cell, about five minutes (from memory, not verified); it sets the shape of the shortfall of the average rate, 1 - (1 - exp(-t / tau)) / (t / tau).
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation series (about six to eight, Cornish-Bowden; transport practice, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (the anchors of the class direction module) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 nM is 1e-3 uM; 1 mM is 1e3 uM; 1 pmol is 1e-3 nmol; 1 umol is 1e3 nmol; a stated "n-fold" is the ratio n); the stated number is the paper's.
    'km': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
    'normalized_rate': ('nmol/min/mg', {'pmol/min/mg': 1.0e-3, 'nmol/min/mg': 1.0, 'umol/min/mg': 1.0e3}),
}
# The name of each effect quantity in the class order TRANSPORT_EFFECT_ORDER (select_transport_effect reads these keys).
ANCHOR_QUANTITY = {'km': 'transport_km', 'fold_over_control': 'fold_over_control', 'normalized_rate': 'normalized_rate'}
# The quantity_kind (QUANTITY_KINDS['transport_response']) that names the kind of each effect quantity; the direction function reads it back.
KIND_OF_QUANTITY = {'km': 'transport_parameter', 'fold_over_control': 'transport_rate_ratio', 'normalized_rate': 'transport_rate'}
KIND_WITHOUT_EFFECT = 'transport_rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_cell_tracer_uptake_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_tracer_uptake_value_is_not_an_attribution_fraction', 'total_signal': 'a_tracer_uptake_value_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_cell_tracer_uptake_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_cell_tracer_uptake_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "transport detected" / "transport not detected" / "transport not stated" for this class


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
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


def _average_rate_bias(seconds):
    """The shortfall 1 - (1 - exp(-t / tau)) / (t / tau) of the rate averaged over an uptake interval t that approaches its steady state with the time constant TIME_CONSTANT_SECONDS."""
    scaled = seconds / TIME_CONSTANT_SECONDS
    return 1.0 - (1.0 - math.exp(-scaled)) / scaled


def _judge_window(native):
    refs = native['time_window_refs']
    seconds = native['time_window_s']
    if seconds >= TIME_ZERO_SECONDS:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(seconds), _average_rate_bias(TIME_FULL_SECONDS), _average_rate_bias(TIME_ZERO_SECONDS)))


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
JUDGES = {('initial_rate_regime', 'time_window_recorded_for_the_sheet'): _judge_window, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_cell_tracer_uptake_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_transport_cell_tracer_uptake(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_cell_tracer_uptake_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'transport_cell_tracer_uptake', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of transport above its control fixes the direction (the support of the one fact it is derived from)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['transport']], 'support_refs': list(native['transport_refs'])}
        if native['transport'] is not None:
            result['direction_field_support'] = native['transport_support']
    return result
