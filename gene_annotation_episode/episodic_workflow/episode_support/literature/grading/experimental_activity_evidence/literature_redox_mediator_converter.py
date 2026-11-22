"""Redox_mediator converter: turns the grader's result into what the A105 activity_rate sheet takes.

DRAFT (2026-11-22), hand-built, private to redox_mediator, deterministic; copied from the shape of literature_spectro_direct_converter.py.
Input: the result of grade_redox_mediator. Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'activity_rate'), the
sheet itself (grade_assay run on it), the dependence keys the merger needs, the enzyme's molar mass the direction function needs, and for every
sheet component that a dye-rate measurement cannot honestly fill, the reason it stays null.

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
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None.
qualitative_effect  only when NO effect is stated and the paper states whether it saw the dye change above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact that states it; direction_field_support is the quote support of that one fact. A stated effect fixes the
                  direction; the statement is then not used. (The contract's stated_strength makes a result in words count less than a
                  measured one; it is not re-implemented here.)

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    dye_background_control + substrate_independent_signal
attribution_supported      enzyme_dependence + product_identity
calibration_applicability  extinction_coefficient_stated + absorbance_range + electron_stoichiometry + oxygen_reoxidation
rate_regime                initial_rate_regime + mediator_saturation
kinetic_model              substrate_range
normalization_basis        active_enzyme_amount
sampling_basis             replicates
assertion_relevance        native_reaction + native_electron_partner
condition_scope            purified_enzyme
variance_correspondence    supported only when a variance was computed
Why the dye-specific members sit where they do. The electrons per dye molecule and the re-oxidation of the reduced dye by oxygen decide whether
the slope of the dye equals the electron flux of the enzyme: they belong to the calibration of the readout (calibration_applicability), not to
the controls. The dye's own concentration against its Km decides whether the rate is near the maximal rate with the dye (rate_regime, the
concentration regime of the rate). The native electron partner is the bypass question (can the dye take electrons where the natural partner
cannot): whether the activity is the claimed reaction, so assertion_relevance, beside the native substrate. The kind and the role of the
mediator are recorded only.

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
rate: literature_activity_direction (larger is stronger); controls, blanks and the rest lower the WEIGHT only. A dye rate that bypasses the
native partner lowers the weight through assertion_relevance, not the rate.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CONSUMED_FULL_PERCENT 10 -> CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate (the share of the DYE consumed).
  Q1 an "initial rate" that is really the average over a progress curve that has already bent. In a dye assay the dye is usually the reagent
  that is used up first: it is added at a concentration set by the absorbance range (DCPIP about 50 to 100 uM, ferricyanide about 0.5 to 1 mM,
  a viologen about 1 to 2 mM, from memory), well below the substrate, so its own consumption is what bends the curve, and a dye held below
  its Km makes the rate fall in proportion to the dye left. Q2 general: initial velocity means at most about 10 percent of the limiting reagent
  consumed (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes; NCBI Assay Guidance Manual, Basics of Enzymatic Assays), from
  memory. Q3 relative to the paper's own dye, stated as a share; right. Q4 the first-order worst case (a dye far below its Km): the rate averaged
  over the window is f / -ln(1 - f) of the initial rate, f the fraction consumed: 0.95 at 10 percent, 0.90 at 20, 0.72 at 50, 0.39 at 90. The
  degree is linear in that bias between the two ends. At or beyond 90 percent the "rate" has become an end point (conflicting: the paper shows
  the rate is not an initial rate). Q5 the same shape as the other direct optical assay of the class, because the physics of a first-order
  progress curve is the same; only the reagent the share refers to differs (the dye here).
MEDIATOR_FULL_FACTOR 10 -> MEDIATOR_ZERO_FACTOR 0.1 (the dye concentration over the enzyme's Km for the dye), judged linearly in the fractional
  saturation c / (c + Km).
  Q1 a rate measured with the dye far below its Km is a rate of the dye, not of the enzyme: it is proportional to the dye concentration and
  tells nothing about the maximal rate, so a specific activity or kcat taken there underestimates the enzyme and cannot be compared with another
  paper's. Artificial acceptors are often used at a convenient concentration set by the absorbance, not by the enzyme's Km. Q2 general: a
  saturating second substrate is the usual rule of a steady-state assay (Cornish-Bowden; Copeland), from memory; the Km of dehydrogenases for
  DCPIP or ferricyanide spans micromolar to millimolar (from memory), so no single dye concentration is saturating for every enzyme and the
  paper's own Km is the right scale. Q3 relative to the paper's own Km for the dye (the grader records both); right. Q4 v / Vmax = c / (c + Km):
  0.91 at 10 Km (full, the free plateau of SOP rule d is reached only by going well past the Km), 0.5 at the Km (degree 0.5), 0.09 at 0.1 Km (zero:
  the rate is a tenth of the maximum and proportional to the dye, conflicting); linear in the fractional saturation because the rate itself is.
  Q5 the same fractional-saturation ramp as the substrate series and the binding-assay ends (SOP cross-assay rule c), with the same top of 10.
  Only a weight: a rate with a sub-saturating dye is still evidence that the enzyme acts on the dye, and the strength scale reads its size.
ABSORBANCE_FULL 1.0 -> ABSORBANCE_ZERO 3.0, STRAY_LIGHT 0.01, judged on the bias of the apparent absorbance.
  Q1 Beer-Lambert fails at high absorbance: stray light puts a floor under the transmitted intensity and the slope of the dye in absorbance
  units underestimates the rate. A dye that is bleached by the reaction (oxidised DCPIP at 600 nm) starts at its highest absorbance, so the
  starting value is the one that matters; a dye that develops colour (a reduced viologen at 578 or 600 nm, a formazan) ends at it, and the
  extraction asks for the highest absorbance reached, whichever end that is.
  Q2 general: keep the absorbance below about 1 (instrument manuals and photometry texts), from memory; a stray light of 1 percent is the
  conservative end of the instruments in use. Q3 absolute (absorbance units); the grader records the paper's own highest absorbance. Q4 the
  apparent absorbance is -log10((10^-A + s) / (1 + s)), so the slope is underestimated by about 4 percent at A = 1, 15 percent at 2, 35
  percent at 3; the degree is linear in that bias between the two ends; at A = 3 a third of the signal is lost (conflicting). Q5 the same
  physics as the direct optical assay; only the dye in place of the product is read.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight
  concentrations spanning 0.2 to 10 times the Km (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory; the exact 6 is a judgement.
  Q3 absolute (a count). Q4 the Michaelis-Menten equation has two parameters, so two concentrations are used up by the fit and leave no residual
  degree of freedom (degree 0, supported, never conflicting); each added concentration adds one: the degree rises linearly with count - 2.
  Q5 the same residual-degree-of-freedom count as the other assays of the class and the SPR steady-state KD. With a mediator the curve is made
  at one fixed dye concentration, so the Km is an apparent one unless the dye is saturating (judged separately above).
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and Vmax trade off or the curvature is unseen. Q2 general: 0.2 to 10 times the Km (the references
  above), from memory. Q3 relative to the paper's own Km (the grader records both ratios); right. Q4 v / Vmax = S / (S + Km): both ends are judged
  linearly in the fractional saturation (1/6 at 0.2 Km, 10/11 at 10 Km, 1/2 at the Km, the zero end of both). Q5 working rule d of the SOP: 10 at the
  top where the plateau (Vmax) is a free amplitude known only by reaching it.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4
  precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the enzyme dependence, the electron stoichiometry, the product identity, the oxygen exclusion, the
active-site determination, the native substrate and electron partner and the purified enzyme): the paper's own statement decides; yes is
supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the extinction coefficient's
value (the paper's own constant, stated with its wavelength; the coefficient of a dye depends on pH and buffer, for DCPIP about 21 mM^-1 cm^-1 at
600 nm near pH 7 and falling toward acid, from memory, which the identity block's pH records; a wrong constant shows as an implausible rate, which
the strength scale already reads); the kind of the dye (recorded only: the physics that differs between dyes, oxygen sensitivity and electron
count, is asked as facts the paper states, so no criterion rests on a choice); the pH and the temperature (the claim carries no condition).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The rate at which an artificial electron acceptor or donor changes colour, turned into an absolute
  rate with the dye's extinction coefficient and its electron count. Absolute in form, indirect in meaning: it is the rate of electron transfer
  to a surrogate, not necessarily the rate of the claimed reaction.
  Is there a reference range we would trust if the paper stated less? Only partly. The range of kcat and kcat/Km of enzymes is well known, but a
  rate with an artificial dye has no such reference: the same enzyme can be 100-fold faster or slower with a dye than with its native partner
  (the old Bcd/Etf case: methyl viologen drops the hydrogen rate from about 5 to 0.02 and the NADH rate from about 7 to 5 umol/min/mg), so the
  anchors are a looser guide here than for a direct assay.
  What does an unstated control or calibration do to the number's meaning? An unstated dye blank matters more than in a direct assay: DCPIP,
  ferricyanide and tetrazolium dyes are reduced by thiols and ascorbate of the buffer, tetrazolium dyes and phenazines by light, and crude
  preparations carry diaphorase-like activities, all from memory; an unstated extinction coefficient is read from the literature value of the
  common dyes and is off by a factor, not meaningless; an unstated oxygen state matters only for oxygen-sensitive dyes (reduced viologens react
  with oxygen at a near diffusion-controlled rate, from memory).
  If we assume it is fine and are wrong, how badly does the score mislead? Worst for the native-partner question: a dye can take electrons
  from a site the natural partner never reaches, so the activity may not be the claimed reaction at all. Next worst for the controls and the
  second activity. The magnitude error of a calibration is the mildest.
  Consistent with KD? Below it and a little below spectro_direct (0.85): default 0.80.
  default 0.80. background_alternatives 0.70 (the dye blank is what separates enzyme from spontaneous reduction and the dyes are reactive).
  attribution_supported 0.75 (a contaminating dye-reducing activity or a second reaction on the dye is common in the preparations these assays
  are used on). assertion_relevance 0.65 (the native partner is the bypass question and the main risk). calibration_applicability 0.85
  (the extinction coefficients and electron counts of the common dyes are well known, so unstated they are benign; an unstated oxygen state is a
  smaller gap). normalization_basis 0.90, sampling_basis 0.90 (benign when unstated: the mass basis is the usual convention and triplicates are
  usual). rate_regime, kinetic_model, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_redox_mediator_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('dye_background_control', 'substrate_independent_signal'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('extinction_coefficient_stated', 'absorbance_range', 'electron_stoichiometry', 'oxygen_reoxidation'),
                'rate_regime': ('initial_rate_regime', 'mediator_saturation'), 'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',),
                'sampling_basis': ('replicates',), 'assertion_relevance': ('native_reaction', 'native_electron_partner'), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the limiting reagent (here the dye) consumed in the window of an initial rate (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement up to it.
CONSUMED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent of the dye consumed the rate averaged over a first-order progress curve (the worst case, a dye far below its Km) is 0.39 of the initial rate, a factor 2.6 off: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
MEDIATOR_FULL_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the dye concentration should be at least this multiple of the enzyme's Km for the dye (the rate is 10/11 of its maximum there); a free plateau is reached only by going well past the Km (SOP rule d: 10); full agreement from it. From memory, not verified: the Km of dehydrogenases for DCPIP or ferricyanide spans micromolar to millimolar, so the paper's own Km is the scale.
MEDIATOR_ZERO_FACTOR = 0.1  # EXPERT_REVIEW, owner to confirm: at a tenth of the Km the rate is about a ninth of the maximum and proportional to the dye concentration, a rate of the dye and not of the enzyme (no agreement); falls from MEDIATOR_FULL_FACTOR linearly in the fractional saturation c / (c + Km) because the rate itself is linear in it (0.5 degree at the Km).
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
ABSORBANCE_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: keep the absorbance of the dye at most about 1 (photometry practice, from memory); full agreement up to it (the apparent-absorbance bias there is about 4 percent at 1 percent stray light).
ABSORBANCE_ZERO = 3.0  # EXPERT_REVIEW, owner to confirm: at an absorbance of 3 a stray light of 1 percent loses about a third of the signal (no agreement); the degree falls linearly in the bias of the apparent absorbance from the full end to here.
STRAY_LIGHT = 0.01  # EXPERT_REVIEW, owner to confirm: the fraction of stray light in the transmitted intensity; 1 percent is the conservative end of the spectrophotometers and plate readers in use (a good UV-visible instrument has 0.1 percent or less).
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
NULL_REASONS = {'recovery': 'redox_mediator_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_dye_rate_is_not_an_attribution_fraction', 'total_signal': 'a_dye_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_redox_mediator_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_redox_mediator_record',
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


def _saturation(ratio):
    """Fractional saturation c / (c + Km) of a concentration c given as c / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order progress curve that has consumed the fraction f of the reagent."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _apparent_absorbance_bias(absorbance):
    """The relative shortfall of the apparent absorbance, -log10((10^-A + s) / (1 + s)), against the true A, for the stray light STRAY_LIGHT."""
    return 1.0 - -math.log10((10.0 ** -absorbance + STRAY_LIGHT) / (1.0 + STRAY_LIGHT)) / absorbance


def _judge_regime(native):
    refs = native['consumed_refs']
    fraction, zero = native['consumed_percent'] / PERCENT_PER_FRACTION, CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_mediator(native):
    return _graded(native['mediator_refs'], (_saturation(native['mediator_over_km']), _saturation(MEDIATOR_FULL_FACTOR), _saturation(MEDIATOR_ZERO_FACTOR)))


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


def _judge_absorbance(native):
    return _graded(native['absorbance_refs'], (_apparent_absorbance_bias(native['absorbance_max']), _apparent_absorbance_bias(ABSORBANCE_FULL), _apparent_absorbance_bias(ABSORBANCE_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('mediator_saturation', 'mediator_recorded_for_the_sheet'): _judge_mediator,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('absorbance_range', 'absorbance_recorded_for_the_sheet'): _judge_absorbance,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'redox_mediator_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_redox_mediator(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'redox_mediator_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'redox_mediator', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of dye change above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
