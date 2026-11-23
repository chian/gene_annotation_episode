"""Oxygen_electrode converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to oxygen_electrode, deterministic (DRAFT 2026-11-22 for the owner to correct; copied from spectro_direct and adapted to this method). Input: the
result of grade_oxygen_electrode. Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'activity_rate'), the sheet itself
(grade_assay run on it), the dependence keys the merger needs, the enzyme's molar mass the direction function needs, and for every sheet component that an
oxygen-rate measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg, umol O2 per minute per mg) or the rate over the paper's own control (fold). Several may be stated; the one used
                  is the best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated value
                  in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's,
                  only its unit spelling changes. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None; literature_page_update passes it to the direction function.
qualitative_effect  only when NO effect is stated and the paper states whether it saw oxygen uptake or evolution above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the refs of the one
                  fact that states it (oxygen_change_detected_above_control), and direction_field_support is the quote support of that same fact. A stated effect
                  fixes the direction; the statement is then not used. A result stated in words alone counts less than a measured one: that is the contract's
                  stated_strength, not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + substrate_independent_signal
attribution_supported     enzyme_dependence + oxygen_use_coupled + product_identity
calibration_applicability  electrode_calibration
rate_regime               initial_rate_regime + enzyme_substrate_ratio
kinetic_model             oxygen_supply + substrate_range
normalization_basis       active_enzyme_amount
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made
gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the
scale the physics of the assay gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or
beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest
degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never
changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are
dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity,
matrix_interference, partner_perturbation) are not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys
stay None (no immobilized enzyme, no electrode of the claim). Qualitative statements keep the existing vocabulary. Direction and strength of a stated
rate: literature_activity_direction (same paradigm as binding, larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
OXYGEN_CONSUMED_FULL_PERCENT 10 -> OXYGEN_CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the slope over a trace that has already bent because the chamber is running out of oxygen, so the rate is too low. A
  closed chamber is a depleting system: the oxygen is the one reagent that cannot be topped up. Q2 general: the initial rate is taken while only a small
  part of the reagents is used (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes; NCBI Assay Guidance Manual, from memory); oxygraph practice is to
  read the rate over the first minute or two from air saturation, often a few percent to 20 percent of the oxygen. Q3 relative to the paper's own starting
  oxygen, which the passage states as a share; right. Q4 the worst case is an enzyme not saturated with oxygen (Km for O2 above the oxygen left), for which the
  rate falls in proportion to the oxygen: the rate averaged over the window is f / -ln(1 - f) of the initial rate, f the fraction consumed: 0.95 at 10
  percent, 0.90 at 20, 0.72 at 50, 0.39 at 90. The degree is linear in that bias between the two ends, so it falls gently at first and faster later. The zero end is
  the share at which the worst-case rate is below 0.4 of the initial one, where a "rate" has become an end point; at or beyond it the paper shows the
  rate is not an initial rate (conflicting). Q5 the same physics and the same ends as the share of substrate consumed in spectro_direct, because the
  progress-curve bias is the same; the reagent here is the oxygen.
OXYGEN_SUPPLY_FULL_RATIO 5 -> OXYGEN_SUPPLY_ZERO_RATIO 0.1, judged on the fractional saturation O2 / (O2 + Km(O2)).
  Q1 oxygen is a second substrate: a rate measured at an oxygen far under the enzyme's Km for oxygen is the oxygen supply's rate, not the enzyme's capacity, and a
  kcat read from it is too low. Q2 general: the Km for oxygen of oxidases and oxygenases ranges from a few uM (the terminal oxidases) to several hundred uM or more
  (many flavin oxidases and some dioxygenases are not saturated by air), while air-saturated water holds about 250 uM at 25 degrees C and about 210 uM at 37
  degrees C (Benson and Krause 1984 tables; instrument manuals; all from memory); many papers therefore run at air saturation and state the Km for oxygen. Q3 relative
  to the paper's own oxygen Km, and the grader records both. Q4 the rate is v / Vmax = O2 / (O2 + Km), so the degree is linear in that fractional saturation: full at
  5 times the Km (83 percent of Vmax; the working rule d of the SOP, about 5 where the plateau is constrained independently, here by the physical oxygen supply), zero at a tenth
  of the Km (9 percent of Vmax, where the rate says almost nothing about the enzyme). An oxygen under the Km is common and the activity is real, so the ramp ends only at
  a tenth and the criterion only lowers the weight of the kinetic model. Q5 the same occupancy scale as the substrate range of spectro_direct.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law (rate = kcat E S / (Km + S)) holds only while the enzyme is small against the substrate plus the Km; with too much
  enzyme the substrate is bound and consumed in the first moments and the measured rate is not the Michaelis-Menten rate. Q2 general: the
  validity parameter of the reduced (quasi-steady-state) equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446), the error of the rate
  is of the order of that parameter. Q3 relative to the paper's own S and Km: right, and the grader records all three. Q4 an error of about the
  value of the ratio: 1 percent at 0.01 (full), unusable at 1 (enzyme as large as substrate plus Km); linear in the log of the ratio because the
  error is proportional to it. Q5 as spectro_direct: this law does not depend on the readout.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight
  concentrations spanning 0.2 to 10 times the Km (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory; the exact 6 is a judgement. An oxygen
  chamber takes one filling per concentration, which is why series are often short; the count is judged the same way. Q3 absolute (a count). Q4 the
  Michaelis-Menten equation has two parameters (Km and Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (no
  credit, supported with degree 0, never conflicting); each added concentration is one more point the fitted curve must pass through: the degree rises
  linearly with count - 2. Q5 the same residual-degree-of-freedom count as spectro_direct and the SPR steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). Q2 general: 0.2 to
  10 times the Km (the references above), from memory. Q3 relative to the paper's own Km (the grader records both ratios): right. Q4 the rate
  is v / Vmax = S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km) (1/6 at 0.2 Km, 10/11 at 10 Km; 1/2 at
  the Km, the zero end of both). Q5 working rule d of the SOP: the top is 10 where the plateau (Vmax) is a free amplitude known only by reaching it. A high substrate that
  autoxidizes would add its own oxygen use; that is a control question (the no-enzyme blank), not a range question.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one chamber filling, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4
  precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the three controls, the electrode calibration, the enzyme dependence, the coupling of the oxygen to the reaction, the product identity, the
active-site determination, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They
have no researched value to soften. NOT judged, and why: the response time of the sensor and the stirring (papers rarely state them and the rate of an enzyme at
an oxygen rate of tens of uM per minute is far slower than the response of a Clark-type electrode, a few seconds to tens of seconds, from memory); the sensor kind (a
choice, kept in the record: a choice carries no span after the merge); the temperature and the pH (the claim carries no condition, and the identity block records the
temperature). The specific activity is per mole of oxygen, which is the paper's own unit; the stoichiometry of oxygen to product (1 for most oxidases, 2 or more for
some oxygenases, one half when catalase returns oxygen from peroxide) is a factor within the same order of magnitude and the strength scale is logarithmic, so it is not converted.

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The rate of oxygen uptake or evolution in an amount of oxygen per time, absolute after the two-point calibration (air-saturated
  and zero oxygen), with the physical oxygen content of air-saturated buffer as the reference. The readout is absolute but NOT specific: it names no reaction.
  Is there a reference range we would trust if the paper stated less (as for KD)? For the sensor yes (the oxygen solubility is physics, and an electrode gives no number
  without a calibration). For the reaction no: kcat and specific activity of the enzyme are known from the literature of the same classes (Bar-Even et al. 2011, from memory), but the
  oxygen use itself could belong to anything in the chamber.
  What does an unstated control or calibration do to the number's meaning? An unstated calibration is benign (the instrument cannot report without it). An unstated blank is not:
  autoxidation of reduced cofactors, thiols, catechols and metal ions, and the electrode's own drift, take up oxygen without any enzyme, and a lysate or membrane
  holds other oxidases. An unstated coupling or product identification leaves open that the oxygen is used in a side reaction (a hydrogen-peroxide or superoxide
  producing futile cycle: the CsiD case in the inventory, where oxygen uptake alone may be uncoupled oxygenase chemistry).
  If we assume it is fine and are wrong, how badly does the score mislead? A background or an uncoupled oxygen use counted as the enzyme's reaction: the direction is
  wrong for a weak rate and the claimed reaction is wrong for a strong one; worse than spectro_direct, whose chromophore at least names the substrate or product.
  Consistent with KD? The default 0.80 is under spectro_direct (0.85) because oxygen use is the less specific readout; the sheet criteria that guard against a false
  reaction are lower, the benign ones are as for spectro_direct.
  default 0.80. background_alternatives 0.65 (autoxidation and drift are the dominant false positive of the method). attribution_supported 0.70 (uncoupled oxygen use, a contaminating
  oxidase and a second reaction on the oxygen; typical papers do not say). calibration_applicability 0.90, normalization_basis 0.90, sampling_basis 0.90 (benign when
  unstated: the electrode must be calibrated to give a number, the mass basis is the usual convention and changes the magnitude not the existence, triplicates are usual).
  rate_regime, kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_oxygen_electrode_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'substrate_independent_signal'), 'attribution_supported': ('enzyme_dependence', 'oxygen_use_coupled', 'product_identity'),
                'calibration_applicability': ('electrode_calibration',), 'rate_regime': ('initial_rate_regime', 'enzyme_substrate_ratio'),
                'kinetic_model': ('oxygen_supply', 'substrate_range'), 'normalization_basis': ('active_enzyme_amount',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
OXYGEN_CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the dissolved oxygen used in the window of an initial rate (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory; oxygraph practice reads the first minute or two from air saturation); full agreement up to it.
OXYGEN_CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent used the rate averaged over a trace for an enzyme not saturated with oxygen (the worst case, first order in oxygen) is 0.39 of the initial rate, a factor 2.6 off: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
OXYGEN_SUPPLY_FULL_RATIO = 5.0  # EXPERT_REVIEW, owner to confirm: the starting oxygen at 5 times the enzyme's Km for oxygen gives 83 percent of Vmax (SOP working rule d, about 5 where the plateau is constrained independently; here by the physical oxygen supply); full agreement from it.
OXYGEN_SUPPLY_ZERO_RATIO = 0.1  # EXPERT_REVIEW, owner to confirm: the starting oxygen at a tenth of the oxygen Km gives 9 percent of Vmax: the rate is set by the oxygen supply and says almost nothing about the enzyme (no agreement); air-saturated buffer (about 250 uM at 25 degrees C, from memory) is under the Km of many flavin oxidases, so the ramp ends at a tenth, not at the Km; falls from the full end linearly in the fractional saturation O2 / (O2 + Km).
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments (chamber fillings from independent preparations); full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.ACTIVITY_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 U = 1 umol/min; mM^-1 is 1000 M^-1; uM^-1 is 1e6 M^-1; 1 nmol is 1e-3 umol; 60 s is 1 min); the stated number is the paper's.
    'catalytic_efficiency': ('M^-1s^-1', {'M^-1 s^-1': 1.0, 'mM^-1 s^-1': 1.0e3, 'uM^-1 s^-1': 1.0e6}),
    'turnover': ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}),
    'specific_activity': ('U/mg', {'U/mg': 1.0, 'umol/min/mg': 1.0, 'nmol/min/mg': 1.0e-3}),
    'rate_over_control': ('fold', {'fold': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['activity_rate']) that names the kind of each effect quantity; literature_activity_direction.ACTIVITY_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'catalytic_efficiency': 'catalytic_efficiency', 'turnover': 'turnover', 'specific_activity': 'rate', 'rate_over_control': 'rate_ratio'}
KIND_WITHOUT_EFFECT = 'rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'oxygen_electrode_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_oxygen_rate_is_not_an_attribution_fraction', 'total_signal': 'an_oxygen_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_oxygen_electrode_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_oxygen_electrode_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "activity detected" / "activity not detected" for this class


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


def _saturation(ratio):
    """Fractional saturation x / (x + Km) of a reagent x given as x / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order trace that has consumed the fraction f of the reagent."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _judge_regime(native):
    refs = native['oxygen_consumed_refs']
    fraction, zero = native['oxygen_consumed_percent'] / PERCENT_PER_FRACTION, OXYGEN_CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(OXYGEN_CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_enzyme_ratio(native):
    return _graded(native['enzyme_ratio_refs'], _log(native['enzyme_over_substrate_plus_km'], ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO))


def _judge_oxygen_supply(native):
    return _graded(native['oxygen_supply_refs'], (_saturation(native['oxygen_over_oxygen_km']), _saturation(OXYGEN_SUPPLY_FULL_RATIO), _saturation(OXYGEN_SUPPLY_ZERO_RATIO)))


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
JUDGES = {('initial_rate_regime', 'oxygen_consumed_recorded_for_the_sheet'): _judge_regime, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('oxygen_supply', 'oxygen_supply_recorded_for_the_sheet'): _judge_oxygen_supply, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'oxygen_electrode_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_oxygen_electrode(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_activity_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_activity_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'oxygen_electrode_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'activity_rate', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    mass = native['quantities']['enzyme_mass']
    result = {'version': VERSION, 'experiment_type': 'oxygen_electrode', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of oxygen change above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']      # the support class of the fact oxygen_change_detected_above_control, the one field the statement is derived from
    return result
