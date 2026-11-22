"""Separation_band converter: turns the grader's result into what the A105 activity_rate sheet takes.

DRAFT (2026-11-22). Hand-built, private to separation_band, deterministic. Input: the result of grade_separation_band. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
enzyme's molar mass the direction function needs, and for every sheet component that a gel or plate measurement cannot honestly fill, the reason it
stays null. Built on the shape of the first type of the class (spectro_direct); the researched values are this method's own.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg) or the rate over the paper's own control (fold). Several may be stated; the one used is the
                  best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated
                  value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the
                  value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect
                  (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion
and alternative predictions.
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None; literature_page_update passes it to
                  the direction function, which needs it for the ends of the specific-activity scale.
qualitative_effect  only when NO effect is stated and the paper states whether it saw product above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact activity_detected_above_control that states it, and direction_field_support the quote support of that one
                  fact. A stated effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a
                  measured one by the contract's stated_strength; nothing is re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   no_enzyme_lane + catalytic_mutant_lane      (spontaneous breakage or hydrolysis; a copurified contaminating activity)
attribution_supported     enzyme_dependence + product_identity
calibration_applicability  signal_linearity + lane_total_denominator
rate_regime               initial_rate_regime + time_course_points + reaction_stopped + enzyme_substrate_ratio
kinetic_model             substrate_range
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
stay None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated
rate: literature_activity_direction (same paradigm as binding, larger is stronger); controls, lanes and the rest lower the WEIGHT only.

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, owner to confirm, and every literature reference is from
the drafter's memory, NOT web-verified and NOT checked against a method paper; verify before relying on any of them.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
CONSUMED_FULL_PERCENT 20 -> CONSUMED_ZERO_PERCENT 80, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the average over a time course that has already bent, so the rate is too low. Q2 general practice for gel and
  plate assays: the rate is taken from the early, linear part of the time course, with at most about 10 to 20 percent of the substrate converted
  (the general rule of enzyme kinetics, Cornish-Bowden, Fundamentals of Enzyme Kinetics; for gel kinetics of nucleases, polymerases and kinases the
  usual statement is "less than 20 percent of the substrate converted"), from memory. The full end is 20 and not the 10 of a continuous assay because the
  first points of a stopped gel assay carry the densitometry noise (a few percent of the lane signal), so a slope taken only under 10 percent conversion
  is itself uncertain; the paper's own spread already carries that noise. Q3 relative to the paper's own substrate, which the passage states as a
  share; right. Q4 the physics gives the shape: for a first-order time course (substrate far below the Km, the worst case) the rate averaged over the
  window is f / -ln(1 - f) of the initial rate, f the fraction converted: 0.90 at 20 percent, 0.72 at 50, 0.50 at 80. The degree is linear in that bias
  between the two ends. The zero end is the share at which the worst-case average rate is half the initial rate (a factor of 2): the points are
  then largely an end point; at or beyond it the paper shows the rate is not an initial rate (conflicting). Q5 the same bias curve as the continuous
  assays (the physics of a progress curve is the same), with its own ends.
ENZYME_OVER_SUBSTRATE_FULL 0.1 -> ENZYME_OVER_SUBSTRATE_ZERO 1.0, judged on the log of E / S.
  Q1 gel assays are often run with the enzyme in excess over a labelled substrate (single-turnover kinetics, standard for ribozymes, helicases and
  many nucleases, Fersht, Structure and Mechanism in Protein Science; Johnson's analysis of pre-steady-state kinetics, from memory). With E at or above S the
  product can be at most one per enzyme: the experiment cannot tell a catalyst from a stoichiometric reagent, and a rate per enzyme (turnover) is not
  the steady-state one. Q2 general: a catalyst is shown by more product than enzyme; E / S at 0.1 allows ten turnovers, the usual practical start of
  multiple-turnover assays; from memory. Q3 relative to the paper's own enzyme and substrate; right, and the grader records both. Q4 the number of
  possible turnovers is S / E, so a log scale is right: ten turnovers (0.1) full, one turnover (1.0) none; more enzyme than substrate is conflicting
  for a claim of catalytic turnover. Not judged on the Km: gel assays rarely state it (the SOP's spectro ratio E / (S + Km) is not asked). Q5 the same
  log ramp family as the other ratio judgements, with its own ends (0.1 / 1.0), because a single turnover is the question here and not the steady-state
  validity of the rate law.
MIN_TIME_POINTS 5, TIME_POINTS_ZERO 2.
  Q1 a rate from too few stopped time points; a continuous trace has thousands, a gel has a handful, so the count is the quality of the line. Q2
  general: a gel time course has about 5 to 10 times including zero; a straight line has two parameters (slope, intercept), so two points leave no
  residual degree of freedom, from memory. Q3 absolute (a count). Q4 the degree rises linearly with the residual degrees of freedom, count - 2 (3 points
  1/3, 4 points 2/3, 5 or more full); two or one points give no credit but are supported with degree 0, never conflicting. Q5 the same residual-degree-of-freedom
  count as the substrate series below and the SPR steady-state KD.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight
  concentrations spanning 0.2 to 10 times the Km (Cornish-Bowden; Copeland, Enzymes; NCBI Assay Guidance Manual), from memory; the exact 6 is a judgement.
  Q3 absolute (a count). Q4 the Michaelis-Menten equation has two parameters, so two concentrations are used up by the fit and leave no residual
  degree of freedom (degree 0, supported, never conflicting); the degree rises linearly with count - 2. Q5 as the time points, and as spectro_direct.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). Q2 general: 0.2 to
  10 times the Km, from memory. Q3 relative to the paper's own Km (the grader records both ratios): right. Q4 v / Vmax = S / (S + Km), so both ends are
  judged linearly in the fractional saturation (1/6 at 0.2 Km, 10/11 at 10 Km; 1/2 at the Km, the zero end of both). A gel assay finds the high end
  harder (a labelled substrate must be diluted with unlabelled substrate and the bands then leave the linear range, which the signal_linearity fact
  catches separately), but the plateau is still a free amplitude known only by reaching it, so the SOP's working rule d (10 for a free plateau) is kept.
  Q5 working rule d of the SOP.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one gel, whose gel-to-gel and preparation-to-preparation spread is unseen (gel loading, exposure and quantification vary between
  gels). Q2 general (triplicate practice; Cumming, Fidler and Vaux 2007 J Cell Biol 177:7, from memory). Q3 absolute count. Q4 precision of a mean
  (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the no-enzyme lane, the catalytic-mutant lane, the product marker, the stop at each time point, the enzyme dependence, the linear
range of the densitometry, the lane total as denominator, the active-site determination, the native substrate and the purified enzyme): the paper's own
statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the detector
(a phosphorimager, film and a stain differ in linear range, which the signal_linearity fact asks); the gel type and the pH and temperature (the claim
carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The fraction of the substrate converted at stopped times, as the product band over the lane total: a
  ratio of two signals in one lane, absolute for an end-labelled substrate (one label per molecule, equal response of substrate and product) and only
  approximately so for a stain (response grows with size). A rate, turnover or fold derived from it is absolute where the amounts are stated.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes, the same kcat and kcat/Km range as spectro_direct (Bar-Even
  et al. 2011, from memory), but a gel conversion is a coarser number than a continuous slope, so the trust is a little lower.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme lane is usually benign (a stable substrate is the
  norm) but an unstated catalytic-mutant lane leaves open the classic false positive of the field: a copurified contaminating nuclease or protease
  giving a product band; an unmarked band can be a degradation product that is not the claimed product; an unstated linear range matters for film and
  stain (saturation lowers the apparent conversion) and little for a phosphorimager.
  If we assume it is fine and are wrong, how badly does the score mislead? A contaminant or an unassigned band is counted as the enzyme's activity:
  the direction is wrong, as for spectro_direct but with more ways to be wrong (an absorbance change names no product, a band names its size).
  Consistent with KD? The default 0.80 is under spectro_direct (0.85): the assay is discontinuous and semi-quantitative.
  default 0.80. background_alternatives 0.70 (the contaminant and the spontaneous breakage are the dominant false positives of a gel assay),
  attribution_supported 0.75 (an unmarked band and an enzyme-independent product), calibration_applicability 0.75 (stain and film response, saturation),
  rate_regime 0.75 (a discontinuous rate needs its stopped times and its early points; unstated they are a real gap), normalization_basis 0.90 (benign when
  unstated: the mass basis changes the magnitude, not the existence), sampling_basis 0.85 (triplicate gels are usual, a single representative gel is
  common). kinetic_model, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_separation_band_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('no_enzyme_lane', 'catalytic_mutant_lane'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('signal_linearity', 'lane_total_denominator'),
                'rate_regime': ('initial_rate_regime', 'time_course_points', 'reaction_stopped', 'enzyme_substrate_ratio'),
                'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
CONSUMED_FULL_PERCENT = 20.0  # EXPERT_REVIEW, owner to confirm: at most about 20 percent of the substrate converted in the window of an initial rate of a gel time course (the usual "less than 20 percent converted" of gel kinetics; the general 10 percent rule of Cornish-Bowden is relaxed because the first stopped points carry the densitometry noise); from memory, not verified; full agreement up to it.
CONSUMED_ZERO_PERCENT = 80.0  # EXPERT_REVIEW, owner to confirm: at 80 percent converted the rate averaged over a first-order time course (the worst case) is half the initial rate, a factor 2 off: the points are largely an end point (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
ENZYME_OVER_SUBSTRATE_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: enzyme at most a tenth of the substrate allows about ten turnovers, the practical start of a multiple-turnover assay (the enzyme is then shown to be a catalyst, not a reagent); from memory, not verified; full agreement up to it.
ENZYME_OVER_SUBSTRATE_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as the substrate allows at most one turnover (a single-turnover reaction cannot show catalysis or a steady-state rate; no agreement); falls from ENZYME_OVER_SUBSTRATE_FULL linearly in the log of the ratio, because the number of possible turnovers is substrate over enzyme.
MIN_TIME_POINTS = 5  # EXPERT_REVIEW, owner to confirm: fewest stopped time points of a usable time course (a gel time course has about 5 to 10 times including zero; from memory); full agreement from it (three residual degrees of freedom for a line).
TIME_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a line has two parameters (slope and intercept), so two time points leave no residual degree of freedom (degree 0, supported, never conflicting: a short time course is weaker evidence); between this and MIN_TIME_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); from memory, not verified; full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments (separate gels and reactions); full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
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
NULL_REASONS = {'recovery': 'separation_band_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_band_conversion_is_not_an_attribution_fraction', 'total_signal': 'a_band_conversion_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_separation_band_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_separation_band_record',
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
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order time course that has converted the fraction f of the substrate."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _judge_regime(native):
    refs = native['consumed_refs']
    fraction, zero = native['consumed_percent'] / PERCENT_PER_FRACTION, CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_time_points(native):
    # the count only lowers the degree, never conflicts: linear in the residual degrees of freedom of a line, count - 2
    degree = max(0.0, min(1.0, _share(native['time_point_count'], MIN_TIME_POINTS, TIME_POINTS_ZERO)))
    return _verdict('supported', native['time_point_refs'], degree)


def _judge_enzyme_ratio(native):
    return _graded(native['enzyme_ratio_refs'], _log(native['enzyme_over_substrate'], ENZYME_OVER_SUBSTRATE_FULL, ENZYME_OVER_SUBSTRATE_ZERO))


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
JUDGES = {('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('time_course_points', 'time_points_recorded_for_the_sheet'): _judge_time_points,
          ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'separation_band_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_separation_band(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'separation_band_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'separation_band', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of product above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
