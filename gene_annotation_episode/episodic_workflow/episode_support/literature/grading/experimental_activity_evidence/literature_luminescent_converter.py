"""Luminescent converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to luminescent, deterministic. Input: the result of grade_luminescent. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
enzyme's molar mass the direction function needs, and for every sheet component that a luminescent measurement cannot honestly fill, the
reason it stays null. A private copy of the spectro_direct converter (copies between types are intended) with the judgements of this method.

The method. A kinase or ATPase (or another enzyme that makes or uses ATP, ADP, NAD(P)H or pyrophosphate) runs in a plate well; a detection
reagent turns the ADP made (ADP-Glo), the ATP left (Kinase-Glo) or the NAD(P)H made into light with a luciferase; the light (RLU) is read once
or at a few times. The light is a relative signal: it becomes an amount of product only through a standard series of known ATP or ADP amounts
read in the same plate, and a rate only through the reaction time. The reagent sees the ADP or ATP, not which reaction made it, so a
contaminating ATPase, the enzyme's own autophosphorylation, ATP carried over into the reagent and a luciferase-inhibiting component of the
mixture are the usual false signals.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg) or the rate over the paper's own control (fold). Several may be stated; the one used is the
                  best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated
                  value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the
                  value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect
                  (KIND_OF_QUANTITY), which the direction function reads. The fold is the signal-derived product or rate of the enzyme over the
                  paper's own control (a signal-to-background ratio of raw light includes the reagent's own baseline, so it understates the
                  fold of the net product: it is a safe, low reading).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None.
qualitative_effect  only when NO effect is stated and the paper states whether it saw activity above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact that states it; direction_field_support is the quote support of that one fact. A stated effect fixes the
                  direction; the statement is then not used. (The contract's stated_strength makes this words-only result count less than a
                  measured one; it is not repeated here.)

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + substrate_independent_signal + assay_window
matrix_interference       detection_interference_control
attribution_supported     enzyme_dependence + product_identity
calibration_applicability standard_curve_used + standard_range
rate_regime               initial_rate_regime + enzyme_substrate_ratio
kinetic_model             substrate_range
normalization_basis       active_enzyme_amount
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The Z' factor (assay_window) goes to background_alternatives because Z' is the separation of the enzyme signal from the control band in
standard deviations: it measures how well the control (the background) is told apart from the signal. A paper that does not report Z' leaves
that member unknown, as the SOP says (silence is unknown); this lowers the weight of background_alternatives by the unknown weight of the
type and nothing else. Sheet criteria with no counterpart here (measurement_identity, partner_perturbation) are not selected.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made
gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the
scale the physics of the assay gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or
beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest
degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never
changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are
dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other
keys stay None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated
rate: literature_activity_direction (same paradigm as binding, larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CONSUMED_FULL_PERCENT 20 -> CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the average over a time course that has already bent, so the rate is too low. Q2 general for the
  principle: initial velocity means a small share of the substrate converted, about 10 percent in the textbooks (Cornish-Bowden; Copeland; NCBI
  Assay Guidance Manual, from memory). Specific to this method: the light has to rise clearly over the reagent's baseline (ATP carried over
  into an ADP-Glo or Kinase-Glo read-out), so these assays are run at a few to about 30 percent conversion (the kit manuals recommend roughly
  10 to 30 percent ATP-to-ADP conversion, from memory); the full end is therefore 20, not the 10 of an absorbance assay. Q3 relative to the
  paper's own substrate, which the passage states as a share; right. Q4 the physics gives the shape: for a first-order time course (substrate far
  below the Km, the worst case) the rate averaged over the window is f / -ln(1 - f) of the initial rate, f the fraction converted: 0.90 at 20
  percent, 0.72 at 50, 0.39 at 90. The degree is linear in that bias between the two ends, so it falls gently at first and faster later. The
  zero end is the share at which the worst-case rate is below 0.4 of the initial one (a factor of 2.6), where a "rate" has become an end point;
  at or beyond it the paper shows the rate is not an initial rate (conflicting). Q5 the same shape and zero end as spectro_direct; only the full
  end differs, for the reason above.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law holds only while the enzyme is small against the substrate plus the Km. Q2 general: the validity parameter of the
  reduced equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446, from memory). Q3 relative to the paper's own S and Km. Q4 an
  error of about the value of the ratio: 1 percent at 0.01 (full), unusable at 1; linear in the log of the ratio because the error is
  proportional to it. Q5 the same as spectro_direct (the physics does not depend on the detection).
STANDARD_RANGE_FULL 1.0 -> STANDARD_RANGE_ZERO 10.0, judged on the log of the highest product over the highest standard.
  Q1 a product amount read from light above the top of the standard series is an extrapolation of the calibration: the light per ATP bends at
  high signal (detector and reagent limits) and nothing in the paper shows where. Q2 general practice for any calibrated read-out (read inside
  the calibrated range); the size of the allowed extrapolation is a judgement: the reagent and plate readers are linear over several decades of
  ATP (manufacturer data, from memory, not verified), so a small overshoot is mild and a decade beyond the top is uncontrolled. Q3 relative to the
  paper's own standard series, which the grader records. Q4 inside the range (ratio at most 1) the calibration applies fully; the loss is
  taken as proportional to the number of octaves beyond the top, so the ramp is linear in the log of the ratio (a ratio of 2 gives 0.70, 4 gives
  0.40); at 10 and beyond the calibration says nothing (conflicting). Q5 a log-ratio ramp like the enzyme ratio and the fold judgements of the
  binding assays. No literature source is known for the exact ends: both are judgements, marked as such.
ZPRIME_FULL 0.5 -> ZPRIME_ZERO 0.0, judged linearly in Z'.
  Q1 a signal band that is not clearly apart from its control band, so a rate may be noise. Q2 general for plate assays: Z' = 1 - 3 (sd of signal
  + sd of control) / |difference of the means| (Zhang, Chung and Oldenburg 1999, J Biomol Screen 4:67-73, from memory); Z' of 0.5 or more is an
  excellent assay, 0 to 0.5 marginal, 0 or less no separation. Q3 relative to the paper's own controls (a statistic of its own two bands).
  Q4 Z' is already the number of standard deviations of separation on a linear scale (1 - Z' is three times the sum of the relative spreads over
  the separation); full agreement from 0.5, falling linearly to 0 where the bands touch. A Z' of 0 or less cannot be extracted (a number must
  be above 0), so the zero end of this ramp is never reached and this judgement never returns conflicting (a Z' near 0 gives a degree near 0). Q5 a linear ramp between a researched good
  value and the value of no separation, as for the other quality statistics.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight
  concentrations (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); the exact 6 is a judgement. Q3 absolute (a count). Q4 the
  Michaelis-Menten equation has two parameters (Km and Vmax), so two concentrations are used up by the fit and leave no residual degree of
  freedom (supported with degree 0, never conflicting); the degree rises linearly with count - 2. Q5 the same count as spectro_direct and the SPR
  steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 5 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off. Q2 general: about 0.2 times the Km at the bottom (the references above).
  The top differs from the 10 of an absorbance assay on purpose: the substrate of these assays is usually ATP, and the detection reagents
  tolerate ATP only up to about 1 mM (kit manuals, from memory), so a top of 10 times the Km cannot be reached for an enzyme with an ATP Km
  above 100 uM; 5 times the Km (83 percent of Vmax, the usual 10 with a factor of 2 slack) is the end the SOP rule d gives where the top is
  limited by something other than the paper's care. Q3 relative to the paper's own Km (the grader records both ratios). Q4 the rate is
  v / Vmax = S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km) (1/6 at 0.2 Km, 5/6 at 5 Km, 1/2 at the
  Km, the zero end of both). Q5 the same as spectro_direct except the top, for the reason above.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose preparation-to-preparation spread is unseen (wells of one plate share the mixture). Q2 general
  (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the
  shared replicate rule.
Facts with no number (the no-enzyme, inactive-enzyme and no-substrate controls, the detection-interference control, the enzyme dependence, the
product identity, the standard curve, the active-site determination, the native substrate and the purified enzyme): the paper's own statement
decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the exact
standard series (its lowest point and shape: the paper's own spread already carries a poor low end); the reagent brand; the pH and the
temperature (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? Light from a luciferase reaction: relative (RLU), made absolute (umol/min, per mg, per enzyme) only
  through a standard series and the reaction time. It reads ADP, ATP or NAD(P)H, not the reaction itself.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes for the enzyme constants (kcat and kcat/Km of natural
  enzymes, Bar-Even et al. 2011, from memory, the same as the strength anchors), but the readout is indirect, so less than a direct absorbance.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme blank is common practice and mostly benign for a
  strong signal, but the ATP carried over and a contaminating ATPase are the dominant false positives of this readout; an unstated standard
  curve is ordinary (the paper's absolute number implies one) but cannot be checked; an unstated luciferase-interference check matters for
  Kinase-Glo, where a luciferase inhibitor in the mixture looks like extra enzyme activity (false positive), and for ADP-Glo it looks like
  inhibition.
  If we assume it is fine and are wrong, how badly does the score mislead? A background, a contaminating ATPase or an interfering component is
  counted as the enzyme's activity: the direction is wrong for a weak signal and the magnitude for a strong one; more often than for a direct
  absorbance assay, because the readout cannot tell which reaction made the ADP.
  Consistent with KD and spectro_direct? The default 0.80 is under the spectro_direct 0.85 (an indirect, relative readout) and under the KD
  anchor 0.90.
  default 0.80. background_alternatives 0.75 (the blank and the no-substrate control are what separate the enzyme from carried-over ATP and
  autophosphorylation). matrix_interference 0.75 (an unchecked luciferase disturbance can produce a false activity in an ATP-depletion format).
  attribution_supported 0.70 (the reagent cannot tell which reaction made the ADP: a contaminating ATPase is the central risk and papers often
  leave the product unidentified). normalization_basis 0.90 and sampling_basis 0.90 (benign when unstated: the mass basis is the usual
  convention and changes the magnitude not the existence, triplicate wells are usual). calibration_applicability, rate_regime, kinetic_model,
  assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_luminescent_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'substrate_independent_signal', 'assay_window'), 'matrix_interference': ('detection_interference_control',),
                'attribution_supported': ('enzyme_dependence', 'product_identity'), 'calibration_applicability': ('standard_curve_used', 'standard_range'),
                'rate_regime': ('initial_rate_regime', 'enzyme_substrate_ratio'), 'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',),
                'sampling_basis': ('replicates',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
CONSUMED_FULL_PERCENT = 20.0  # EXPERT_REVIEW, owner to confirm, from memory not verified: the initial-rate window of a luminescent assay is run at a few to about 30 percent conversion so that the light rises over the reagent baseline (kit manuals recommend about 10 to 30 percent ATP-to-ADP conversion); at 20 percent the worst-case average rate is 0.90 of the initial one; full agreement up to it.
CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent converted the rate averaged over a first-order time course (the worst case) is 0.39 of the initial rate, a factor 2.6 off: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
STANDARD_RANGE_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: a product read at or below the top of the standard series is inside the calibration; full agreement up to it.
STANDARD_RANGE_ZERO = 10.0  # EXPERT_REVIEW, owner to confirm, a judgement (no source known, reagent linearity from memory): a product a decade above the top standard is an extrapolation the paper does not control (no agreement); the degree falls linearly in the log of the ratio, because the loss grows with the octaves beyond the calibration.
ZPRIME_FULL = 0.5  # EXPERT_REVIEW, owner to confirm: Z' of 0.5 or more is an excellent plate assay (Zhang, Chung and Oldenburg 1999, from memory); full agreement from it.
ZPRIME_ZERO = 0.0  # EXPERT_REVIEW, owner to confirm: Z' of 0 means the signal and control bands touch at three standard deviations (no usable separation); the degree falls linearly in Z' from ZPRIME_FULL to here.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 5.0  # EXPERT_REVIEW, owner to confirm, from memory not verified: the highest substrate should be at least this multiple of the Km (v is 5/6 of Vmax); 5 and not 10 because the substrate is usually ATP and the detection reagents tolerate ATP only up to about 1 mM (kit manuals), so 10 times the Km is out of reach for an ATP Km above 100 uM (SOP rule d: 5 where the top is limited by the assay); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.ACTIVITY_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 U = 1 umol/min; mM^-1 is 1000 M^-1; uM^-1 is 1e6 M^-1; 1 nmol is 1e-3 umol; 1 pmol/ug is 1 nmol/mg; 60 s is 1 min); the stated number is the paper's.
    'catalytic_efficiency': ('M^-1s^-1', {'M^-1 s^-1': 1.0, 'mM^-1 s^-1': 1.0e3, 'uM^-1 s^-1': 1.0e6}),
    'turnover': ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}),
    'specific_activity': ('U/mg', {'U/mg': 1.0, 'umol/min/mg': 1.0, 'nmol/min/mg': 1.0e-3, 'pmol/min/ug': 1.0e-3}),
    'rate_over_control': ('fold', {'fold': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['activity_rate']) that names the kind of each effect quantity; literature_activity_direction.ACTIVITY_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'catalytic_efficiency': 'catalytic_efficiency', 'turnover': 'turnover', 'specific_activity': 'rate', 'rate_over_control': 'rate_ratio'}
KIND_WITHOUT_EFFECT = 'rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'luminescent_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_luminescent_rate_is_not_an_attribution_fraction', 'total_signal': 'a_luminescent_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_luminescent_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_luminescent_record',
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


def _judge_enzyme_ratio(native):
    return _graded(native['enzyme_ratio_refs'], _log(native['enzyme_over_substrate_plus_km'], ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO))


def _judge_standard_range(native):
    return _graded(native['standard_range_refs'], _log(native['product_over_standard_top'], STANDARD_RANGE_FULL, STANDARD_RANGE_ZERO))


def _judge_z_prime(native):
    return _graded(native['z_prime_refs'], (native['z_prime'], ZPRIME_FULL, ZPRIME_ZERO))


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
JUDGES = {('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('standard_range', 'product_over_standard_recorded_for_the_sheet'): _judge_standard_range,
          ('assay_window', 'z_prime_recorded_for_the_sheet'): _judge_z_prime, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'luminescent_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_luminescent(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'luminescent_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'luminescent', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
