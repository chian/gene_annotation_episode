"""Fluorogenic converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to fluorogenic, deterministic. Input: the result of grade_fluorogenic. Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the enzyme's molar mass the direction function needs,
and for every sheet component that an activity measurement cannot honestly fill, the reason it stays null. Drafted 2026-11-22 as a copy of the shape of
literature_spectro_direct_converter.py (SOP steps 3 and 4); everything that differs is the method's own, and every value is EXPERT_REVIEW, owner to confirm.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1), specific activity (U/mg) or
                  the rate over the paper's own control (fold). Several may be stated; the one used is the best-determined, in the class order ACTIVITY_EFFECT_ORDER
                  (literature_activity_direction.select_activity_effect). A stated value in another unit of the record's vocabulary is multiplied by its exact factor
                  (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. A rate in fluorescence units per minute is none of the
                  four and is never an effect (it has no unit of the class); only a fold over the paper's own control, or a calibrated rate, is. quantity_kind of the
                  extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees
                  of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None; literature_page_update passes it to the direction function.
qualitative_effect  only when NO effect is stated: the paper's own statement whether it saw activity above its own control: statement 'interaction_detected' (read
                  "activity detected"), 'interaction_not_detected' (read "activity not detected") or 'interaction_not_stated', with the refs of the ONE fact that states it
                  (activity_detected_above_control); direction_field_support is that fact's quote support (None when not stated). A stated effect fixes the direction; the
                  statement is then not used. A result stated in words alone counts less than a measured one by the contract's stated_strength, not here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    spontaneous_reaction_control + substrate_independent_signal
attribution_supported      enzyme_dependence + product_identity
calibration_applicability  fluorophore_calibration + detector_linear_range
matrix_interference        inner_filter_effect
rate_regime                initial_rate_regime + enzyme_substrate_ratio
kinetic_model              substrate_range
normalization_basis        active_enzyme_amount
sampling_basis             replicates
assertion_relevance        native_reaction
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value,
falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states nothing,
never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is
supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion
and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity, partner_perturbation) are not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no
immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated rate: literature_activity_direction (larger is
stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CONSUMED_FULL_PERCENT 10 -> CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate (the same physics as every continuous assay).
  Q1 an "initial rate" that is really the average over a progress curve that has already bent, so the rate is too low. Q2 general: initial velocity means at most about
  10 percent of the substrate consumed (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes; NCBI Assay Guidance Manual, Basics of Enzymatic Assays), from
  memory. Q3 relative to the paper's own substrate, which a passage states as a share; right. For a fluorogenic assay the share is often unstated and the paper says only that
  the slope was linear (the linear-progress fact then decides). Q4 for a first-order progress curve (substrate far below the Km, the worst case) the rate averaged over
  the window is f / -ln(1 - f) of the initial rate, f the fraction consumed: 0.95 at 10 percent, 0.90 at 20, 0.72 at 50, 0.39 at 90. The degree is linear in that bias
  between the two ends. At or beyond the zero end the "rate" has become an end point (conflicting). Q5 the same idea as the replicate and series curves.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law (rate = kcat E S / (Km + S)) holds only while the enzyme is small against the substrate plus the Km; with too much enzyme the substrate is
  bound and consumed in the first moments. Q2 general: the validity parameter of the reduced equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446), from
  memory. Fluorogenic assays usually run at picomolar to nanomolar enzyme against micromolar substrate, so this is usually satisfied; it matters for tight-binding and for
  active-site-titration style assays. Q3 relative to the paper's own S and Km; the grader records all three. Q4 an error of about the ratio: 1 percent at 0.01 (full),
  unusable at 1; linear in the log of the ratio. Q5 a log-ratio ramp like the other ratio judgements.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: about six to eight concentrations (Cornish-Bowden; Copeland; NCBI Assay
  Guidance Manual), from memory; plate readers make more cheap, but six is the usual minimum of a published curve. Q3 absolute (a count). Q4 the Michaelis-Menten equation
  has two parameters, so two concentrations are used up by the fit (degree 0, supported, never conflicting); the degree rises linearly with count - 2. Q5 the same
  residual-degree-of-freedom count as spectro_direct and the SPR steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0 (the lowest substrate over the Km), HIGH_FACTOR 5 -> HIGH_ZERO_FACTOR 1.0 (the highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). Q2 general: 0.2 to about 5 to 10 times the Km
  (the references above), from memory. The top is 5 here and not the 10 of spectro_direct: the top of a fluorogenic series is capped by the inner-filter loss of the
  substrate and product, by the poor aqueous solubility of hydrophobic fluorogenic peptides (they are made up in DMSO) and by substrate inhibition, so 10 times the Km is
  often not reachable by a method whose own readout fails there; 5 times leaves the rate at 5/6 of Vmax (SOP working rule d: 5 where the plateau is constrained
  independently or its reach is limited). Q3 relative to the paper's own Km (the grader records both ratios). Q4 v / Vmax = S / (S + Km), so both ends are judged linearly in
  the fractional saturation S / (S + Km); the Km itself is the zero end of both. Q5 as spectro_direct, with the top at 5.
INNER_FILTER_FULL_ABSORBANCE 0.05 -> INNER_FILTER_ZERO_ABSORBANCE 1.0, judged on the bias of the signal, 1 - 10^(-A / 2).
  Q1 a fluorescence slope that is too low at high substrate concentrations, because the mixture absorbs the excitation or the emission light (primary and secondary inner-filter
  effect) and the saturation curve then bends over (an apparent substrate inhibition, a wrong Km). Q2 general: keep the absorbance of the mixture at the excitation and emission
  wavelengths below about 0.05 to 0.1 or correct for it (Lakowicz, Principles of Fluorescence Spectroscopy; Kubista et al. 1994 Analyst 119:417), from memory. Q3 absolute
  (absorbance units); the grader records the paper's own number and only when the paper did not state a check or a correction (a stated correction settles the criterion
  as supported, in the grader). Q4 for a right-angle cuvette with the beam at the centre the signal is lowered by 10^(-A / 2) at one wavelength (the correction factor of
  the usual formula 10^((A_ex + A_em) / 2)): 5.6 percent at A = 0.05, 11 percent at 0.1, 29 percent at 0.3, 68 percent at 1. The degree is linear in that bias between the ends;
  at A = 1 two thirds of the signal is lost and the single-formula correction is no longer trusted (conflicting). The record holds one absorbance (the larger of the two
  wavelengths), so the bias is a lower bound when both absorb. Q5 the same kind of curve as the absorbance limit of spectro_direct (a bias that grows with the departure).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)),
  the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the enzyme dependence, the product identity, the standard curve, the linear range, the inner-filter check, the active-site determination,
the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to
soften. NOT judged, and why: the excitation and emission wavelengths and the fluorophore (the identity of the readout, not its quality); the gain and the plate type (instrument
specific, covered by the standard curve fact); the pH and the temperature (the claim carries no condition, and the identity block records the temperature).
A fluorogenic substrate is nearly always a synthetic surrogate, so a paper that says so gives native_substrate 'no' and the sheet criterion assertion_relevance conflicting (weight
0 for that one criterion of the result, never a change of direction); that is the template's rule for a surrogate and is reported to the owner as a consequence.

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, decided
2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The rate of an enzyme-dependent change of fluorescence in arbitrary instrument units: relative until a standard curve of the free
  fluorophore turns it into an amount; once calibrated, absolute, with kcat, Km and kcat/Km as well-defined constants.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes for the constants (the kcat and kcat/Km range of enzymes, Bar-Even et al. 2011, from memory,
  on which the strength anchors are built) when a calibrated rate is stated; no for a bare slope, which the strength scale does not read (only a fold over the control is read).
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme blank is the main false positive of a fluorescence assay (autohydrolysis of
  the substrate, autofluorescent lysate or compound), more than for an absorbance assay; an unstated standard curve leaves a kcat unverifiable though not meaningless when the
  paper reports a kcat; an unstated inner-filter check matters most at high substrate and bends the Km.
  If we assume it is fine and are wrong, how badly does the score mislead? A background counted as the enzyme's (wrong direction for a weak rate) or a miscalibrated magnitude;
  less than a pull-down band, more than a KD.
  Consistent with KD and spectro_direct? The default 0.80 is under the spectro_direct 0.85 (a fluorescence readout has more ways to be wrong: gain and plate dependence, inner
  filter, autofluorescence); the benign unstated details equal the anchor 0.90.
  default 0.80. background_alternatives 0.70 (the blank is what separates activity from autohydrolysis and autofluorescence). attribution_supported 0.80 (a contaminating
  protease or a second reaction releasing the fluorophore). calibration_applicability 0.75 (an unstated standard curve or linear range leaves the amount of product
  instrument-dependent). matrix_interference 0.75 (an unstated inner-filter check). normalization_basis 0.90, sampling_basis 0.90 (benign when unstated, as in spectro_direct).
  rate_regime, kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_fluorogenic_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'substrate_independent_signal'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('fluorophore_calibration', 'detector_linear_range'), 'matrix_interference': ('inner_filter_effect',),
                'rate_regime': ('initial_rate_regime', 'enzyme_substrate_ratio'), 'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',),
                'sampling_basis': ('replicates',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the substrate consumed in the window of an initial rate (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement up to it.
CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent consumed the rate averaged over a first-order progress curve (the worst case) is 0.39 of the initial rate, a factor 2.6 off: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 5.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 5/6 of Vmax); lower than the 10 of spectro_direct because the top of a fluorogenic series is capped by inner-filter loss, the solubility of hydrophobic fluorogenic peptides and substrate inhibition (SOP rule d: 5 where the plateau cannot always be reached); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
INNER_FILTER_FULL_ABSORBANCE = 0.05  # EXPERT_REVIEW, owner to confirm: absorbance of the mixture at the excitation or emission wavelength at most about 0.05 (textbook range 0.05 to 0.1; Lakowicz; Kubista et al. 1994, from memory), where the signal is lowered by about 5.6 percent (bias 1 - 10^(-A / 2)); full agreement up to it.
INNER_FILTER_ZERO_ABSORBANCE = 1.0  # EXPERT_REVIEW, owner to confirm: at an absorbance of 1 about two thirds of the signal is lost (bias 0.68) and the one-formula correction is no longer trusted (no agreement); the degree falls linearly in the bias from the full end to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.ACTIVITY_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 U = 1 umol/min; mM^-1 is 1000 M^-1; uM^-1 is 1e6 M^-1; 1 nmol is 1e-3 umol; 1 pmol is 1e-6 umol; 60 s is 1 min); the stated number is the paper's.
    'catalytic_efficiency': ('M^-1s^-1', {'M^-1 s^-1': 1.0, 'mM^-1 s^-1': 1.0e3, 'uM^-1 s^-1': 1.0e6}),
    'turnover': ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}),
    'specific_activity': ('U/mg', {'U/mg': 1.0, 'umol/min/mg': 1.0, 'nmol/min/mg': 1.0e-3, 'pmol/min/mg': 1.0e-6}),
    'rate_over_control': ('fold', {'fold': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['activity_rate']) that names the kind of each effect quantity; literature_activity_direction.ACTIVITY_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'catalytic_efficiency': 'catalytic_efficiency', 'turnover': 'turnover', 'specific_activity': 'rate', 'rate_over_control': 'rate_ratio'}
KIND_WITHOUT_EFFECT = 'rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'fluorogenic_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_fluorescence_rate_is_not_an_attribution_fraction', 'total_signal': 'a_fluorescence_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_fluorogenic_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_fluorogenic_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "activity detected" / "activity not detected" / "activity not stated" for this class


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
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order progress curve that has consumed the fraction f of the substrate."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _inner_filter_bias(absorbance):
    """The relative loss of the fluorescence signal, 1 - 10^(-A / 2), of a right-angle cuvette with the beam at the centre when the mixture has the absorbance A at one wavelength."""
    return 1.0 - 10.0 ** (-absorbance / 2.0)


def _judge_regime(native):
    refs = native['consumed_refs']
    fraction, zero = native['consumed_percent'] / PERCENT_PER_FRACTION, CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_enzyme_ratio(native):
    return _graded(native['enzyme_ratio_refs'], _log(native['enzyme_over_substrate_plus_km'], ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO))


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


def _judge_inner_filter(native):
    return _graded(native['inner_filter_refs'], (_inner_filter_bias(native['inner_filter_absorbance']), _inner_filter_bias(INNER_FILTER_FULL_ABSORBANCE), _inner_filter_bias(INNER_FILTER_ZERO_ABSORBANCE)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('inner_filter_effect', 'inner_filter_absorbance_recorded_for_the_sheet'): _judge_inner_filter,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'fluorogenic_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_fluorogenic(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'fluorogenic_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'fluorogenic', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction (read like the SPR qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['activity']], 'support_refs': list(native['activity_refs'])}
        if native['activity'] is not None:
            result['direction_field_support'] = native['activity_support']      # the quote support of the fact activity_detected_above_control, the one field the statement is derived from
    return result
