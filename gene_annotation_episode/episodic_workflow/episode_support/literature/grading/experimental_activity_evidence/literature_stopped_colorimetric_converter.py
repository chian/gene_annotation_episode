"""Stopped_colorimetric converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to stopped_colorimetric, deterministic. Input: the result of grade_stopped_colorimetric. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs,
the enzyme's molar mass the direction function needs, and for every sheet component that an activity measurement cannot honestly fill, the
reason it stays null. Built as a copy of the first type of the class (spectro_direct) and adapted to this method.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg) or the rate over the paper's own control (fold). Several may be stated; the one used is the
                  best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect; the
                  reason is in the contract). A stated value in another unit of the record's vocabulary is multiplied by its exact factor
                  (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. quantity_kind of the
                  extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None; literature_page_update passes it to
                  the direction function, which needs it for the ends of the specific-activity scale.
qualitative_effect  when NO effect is stated and the paper states whether it saw activity above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact that states it, and direction_field_support the quote support of that one fact. A stated effect fixes
                  the direction; the statement is then not used. A result stated in words alone already counts less than a measured one
                  (the contract's stated_strength); this file does not repeat that.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + reagent_background_blank + enzyme_borne_signal
attribution_supported     enzyme_dependence + product_identity
calibration_applicability  standard_curve_matrix + standard_curve_range + standard_curve_points
rate_regime               initial_rate_regime + time_course_points + enzyme_substrate_ratio
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
beyond its zero end of a ramp is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the
smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion
and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members
are dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity,
matrix_interference, partner_perturbation) are not selected. The buffer and sample effects on the colour (the sheet's matrix_interference) are carried here by standard_curve_matrix, under calibration_applicability; matrix_interference itself is not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys
stay None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated
rate: literature_activity_direction (same paradigm as binding, larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and NOT
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CONSUMED_FULL_PERCENT 10 -> CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the average over a time course that has already bent, so the rate is too low. A stopped assay is the
  more exposed one: it has no live trace, so a long fixed incubation chosen for a bigger colour is easily taken past the straight part. Q2 general:
  initial velocity means at most about 10 percent of the substrate consumed (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes;
  NCBI Assay Guidance Manual, Basics of Enzymatic Assays), from memory. Q3 relative to the paper's own substrate, which the passage states as a
  share; right. Q4 the physics gives the shape: for a first-order time course (substrate far below the Km, the worst case) the rate averaged over
  the window is f / -ln(1 - f) of the initial rate, f the fraction consumed: 0.95 at 10 percent, 0.90 at 20, 0.72 at 50, 0.39 at 90. The degree is
  linear in that bias between the two ends. The zero end is the share at which the worst-case rate is below 0.4 of the initial one (a factor of
  2.6), where a "rate" has become an end point; at or beyond it the paper shows the rate is not an initial rate (conflicting). Q5 the same value and
  curve as the continuous direct assay: the physics of the progress curve does not depend on how the product is read.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law (rate = kcat E S / (Km + S)) holds only while the enzyme is small against the substrate plus the Km. Q2 general: the
  validity parameter of the reduced (quasi-steady-state) equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446), the error of the rate
  is of the order of that parameter, from memory. Q3 relative to the paper's own S and Km; the grader records all three. Q4 an error of about the
  value of the ratio: 1 percent at 0.01 (full), unusable at 1; linear in the log of the ratio because the error is proportional to it. Q5 the same as
  the continuous direct assay (the rate law is independent of the readout).
STANDARD_EXTRAPOLATION_FULL 1.0 -> STANDARD_EXTRAPOLATION_ZERO 3.0, judged on the log of the highest product over the top standard.
  Q1 a product amount read above the top of the standard curve is an extrapolation, and colour reagents are not linear far beyond their
  working range: the malachite green-molybdate complex, the DNS and bicinchoninic reducing-sugar reagents and the DTNB, Nessler and hydroxamate
  colours all flatten or drift at high amounts, so an extrapolated amount, and the rate made from it, is too low or unsupported. Q2 general:
  kit and method instructions give each reagent a working range (for malachite green about tens of micromolar phosphate, for DNS a few mg/mL of
  sugar, Miller 1959 Anal Chem 31:426; Lanzetta 1979 Anal Biochem 100:95 for the phosphate method), from memory, and say to dilute any sample
  above the top standard. Q3 relative to the paper's own standard curve; the grader records both numbers. Q4 within the standard curve (ratio 1 or
  less) the amount is read by interpolation (full agreement). Above it the error is the curvature of the reagent response, which grows with the
  distance from the last standard in multiples of the amount, so the degree falls linearly in the log of the ratio. At three times the top standard
  the sample is far outside any working range (the zero end, conflicting: the paper itself shows it read what it did not calibrate). The 3 is a
  judgement from the working-range factor of the reagents above (a sample is normally diluted if it is more than about 1.5 to 2 times the top
  standard) and is the value the owner is asked to confirm. A product far BELOW the top standard (a small signal near the blank) is not judged:
  the paper's own spread and the control rate already carry it. Q5 a ratio ramp on the log scale like the enzyme ratio above.
MIN_STANDARD_POINTS 6, STANDARD_POINTS_ZERO 2.
  Q1 a standard curve of too few standards, so a bent response or one bad standard cannot be seen. Q2 general: calibration curves of six to eight
  concentrations including a blank are the usual practice and the kit norm (NCBI Assay Guidance Manual; ICH Q2 asks at least five concentrations
  for a linearity range), from memory. Q3 absolute (a count). Q4 a straight-line calibration has two parameters (slope, intercept), so two
  standards use up the fit and leave no residual degree of freedom (supported with degree 0, never conflicting); each added standard is one more
  check on the line: the degree rises linearly with count - 2 (four give 1/2, five give 3/4). Q5 the same residual-degree-of-freedom count as the
  substrate series below.
MIN_TIME_POINTS 5, TIME_POINTS_ZERO 2.
  Q1 a rate from one end-point read, or two, where the product could be on the bend and nothing shows it. A stopped assay reads the time course
  only at the points the experimenter chose. Q2 general: a progress curve for an initial rate needs the zero point and at least four later points
  (about five in all) so a bend shows (Copeland, Enzymes; NCBI Assay Guidance Manual), from memory; the exact 5 is a judgement. Q3 absolute (a count).
  Q4 a straight line has two parameters, so two points fix it and show nothing about linearity (degree 0, never conflicting: one end point is
  weaker evidence, not wrong evidence); each point past two is one more residual degree of freedom, and the degree rises linearly with count - 2
  (three give 1/3, four give 2/3, five give 1). Q5 the same shape as the standard points and the substrate series.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight
  concentrations spanning 0.2 to 10 times the Km (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory; the exact 6 is a judgement.
  Q3 absolute (a count). Q4 the Michaelis-Menten equation has two parameters, so two concentrations leave no residual degree of freedom (degree 0,
  supported, never conflicting); the degree rises linearly with count - 2. Q5 as for the continuous direct assay and the SPR steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off (no saturation) or the curvature is unseen (no low end). A stopped assay is
  often run at the substrate level of the colour reagent's comfortable range, which can leave the high end short. Q2 general: 0.2 to 10 times the
  Km (the references above), from memory. Q3 relative to the paper's own Km (the grader records both ratios): right. Q4 the rate is v / Vmax =
  S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km) (1/6 at 0.2 Km, 10/11 at 10 Km; 1/2 at the Km, the zero
  end of both). Q5 working rule d of the SOP: the top is 10 where the plateau (Vmax) is a free amplitude known only by reaching it.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4
  precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the no-enzyme, inactive-enzyme, zero-time and no-substrate controls, the standard curve in the reaction buffer, the enzyme
dependence, the product identity, the active-site determination, the native substrate and the purified enzyme): the paper's own statement decides;
yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the reagent class (a choice,
for recording only); the colour development time and temperature (the passage seldom states them and the standards are read the same way); the
pH and the temperature of the reaction (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The amount of a product CLASS (phosphate, reducing end, thiol, ammonia) from a colour read against a
  standard curve, turned into an absolute rate: absolute, but only if the standard curve is in the same matrix and the product class is the claimed
  product.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes for the magnitude: kcat and kcat/Km of enzymes are well known
  (Bar-Even et al. 2011, from memory), as for the continuous assay; not for the controls.
  What does an unstated control or calibration do to the number's meaning? Here it matters more than in the continuous assay: the colour reagents
  react with the substrate (free phosphate in ATP, reducing ends in a polysaccharide, thiols in a buffer additive), with the enzyme buffer and with
  contaminating enzymes (a phosphatase in a kinase prep), and the colour of a standard in water is not the colour of a sample in buffer. An
  unstated zero-time blank or buffer standard curve can make a background look like activity.
  If we assume it is fine and are wrong, how badly does the score mislead? A background counted as the enzyme's: the direction is wrong for a weak
  rate (as in the CysQ colour assay case, from the inventory) and the magnitude is wrong for a strong one; worse than a continuous trace, which
  shows the time course live.
  Consistent with KD? Below the continuous direct assay (0.85) because the readout is a product class read at chosen times, above the relative
  assays.
  default 0.80. background_alternatives 0.70 (blanks are what separates activity from reagent chemistry). attribution_supported 0.70 (a class of
  product and a possible contaminating activity). calibration_applicability 0.80 (a standard curve out of matrix or short of range changes every
  amount). rate_regime 0.80 (an unstated number of time points leaves linearity unseen). normalization_basis 0.90 and sampling_basis 0.90
  (benign when unstated, as for the continuous assay). kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_stopped_colorimetric_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'reagent_background_blank', 'enzyme_borne_signal'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('standard_curve_matrix', 'standard_curve_range', 'standard_curve_points'),
                'rate_regime': ('initial_rate_regime', 'time_course_points', 'enzyme_substrate_ratio'),
                'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the substrate consumed in the window of an initial rate (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory, not verified); full agreement up to it.
CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent consumed the rate averaged over a first-order time course (the worst case) is 0.39 of the initial rate, a factor 2.6 off: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory, not verified) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
STANDARD_EXTRAPOLATION_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: the highest product at or under the top standard is read by interpolation on the paper's own standard curve; full agreement up to it.
STANDARD_EXTRAPOLATION_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm, from memory, not verified: the colour reagents (malachite green-molybdate, DNS, DTNB, Nessler, hydroxamate) flatten or drift beyond their working range and a sample more than about 1.5 to 2 times the top standard is normally diluted; at three times it the amount is an uncalibrated extrapolation (no agreement); falls from STANDARD_EXTRAPOLATION_FULL linearly in the log of the ratio, because the curvature error grows with the distance in multiples of the amount.
MIN_STANDARD_POINTS = 6  # EXPERT_REVIEW, owner to confirm: fewest standards of a usable calibration curve (six to eight including a blank is the usual practice; ICH Q2 asks at least five for linearity, from memory, not verified); full agreement from it.
STANDARD_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a straight-line calibration has two parameters, so two standards leave no residual degree of freedom (degree 0, supported, never conflicting: a short curve is weaker evidence); between this and MIN_STANDARD_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
MIN_TIME_POINTS = 5  # EXPERT_REVIEW, owner to confirm: fewest time points of a time course that can show a bend (the zero point and about four more; Copeland; NCBI Assay Guidance Manual, from memory, not verified; the exact 5 is a judgement); full agreement from it.
TIME_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a straight line has two parameters, so two time points fix it and show nothing about linearity (degree 0, supported, never conflicting: one end point is weaker evidence, not wrong evidence); between this and MIN_TIME_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory, not verified); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
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
NULL_REASONS = {'recovery': 'stopped_colorimetric_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_colour_derived_rate_is_not_an_attribution_fraction', 'total_signal': 'a_colour_derived_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_stopped_colorimetric_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_stopped_colorimetric_record',
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
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order time course that has consumed the fraction f of the substrate."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _count_degree(count, full, zero):
    """A count's degree: 1.0 from the full count, falling linearly with the residual degrees of freedom to 0 at the zero count; never below 0, never conflicting."""
    return max(0.0, min(1.0, _share(count, full, zero)))


def _judge_regime(native):
    refs = native['consumed_refs']
    fraction, zero = native['consumed_percent'] / PERCENT_PER_FRACTION, CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_enzyme_ratio(native):
    return _graded(native['enzyme_ratio_refs'], _log(native['enzyme_over_substrate_plus_km'], ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO))


def _judge_standard_range(native):
    return _graded(native['standard_range_refs'], _log(native['product_over_standard_high'], STANDARD_EXTRAPOLATION_FULL, STANDARD_EXTRAPOLATION_ZERO))


def _judge_standard_points(native):
    return _verdict('supported', native['standard_points_refs'], _count_degree(native['standard_points'], MIN_STANDARD_POINTS, STANDARD_POINTS_ZERO))


def _judge_time_points(native):
    return _verdict('supported', native['time_points_refs'], _count_degree(native['time_points'], MIN_TIME_POINTS, TIME_POINTS_ZERO))


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
    return _verdict('supported', refs, min(verdict['degree'], _count_degree(native['concentration_count'], MIN_SUBSTRATE_CONCENTRATIONS, SUBSTRATE_CONCENTRATIONS_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('standard_curve_range', 'standard_range_recorded_for_the_sheet'): _judge_standard_range,
          ('standard_curve_points', 'standard_points_recorded_for_the_sheet'): _judge_standard_points, ('time_course_points', 'time_points_recorded_for_the_sheet'): _judge_time_points,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'stopped_colorimetric_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_stopped_colorimetric(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'stopped_colorimetric_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'stopped_colorimetric', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
