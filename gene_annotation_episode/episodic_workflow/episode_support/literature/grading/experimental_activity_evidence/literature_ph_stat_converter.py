"""Ph_stat converter: turns the grader's result into what the A105 activity_rate sheet takes.

DRAFT of 2026-11-22 (owner to confirm; every number is EXPERT_REVIEW and every literature figure is from the drafter's memory, NOT verified).
Hand-built, private to ph_stat, deterministic. Input: the result of grade_ph_stat. Output: the sheet's input (the 'extraction' grade_assay takes,
with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the enzyme's molar mass the direction
function needs, and for every sheet component that a titration cannot honestly fill, the reason it stays null. Copied in shape from the first type of
the class, spectro_direct (SOP steps 1 to 8).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg) or the rate over the paper's own control (fold). Several may be stated; the one used is the
                  best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated value
                  in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is
                  the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY).
                  A plain titrant addition rate (umol/min, uM/min) with no enzyme amount is none of the four and fills no effect (reported to the owner).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None.
qualitative_effect  the RESULT STATED IN WORDS: only when NO effect is stated and the paper states whether it saw activity above its own control:
                  statement 'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected", opposes),
                  with the refs of the fact activity_detected_above_control that states it, and direction_field_support taken from the quote support of
                  that one fact. A stated effect fixes the direction; the statement is then not used. A result in words alone counts the contract's
                  stated_strength of QUALITATIVE_LOG_RATIO (literature_row_contract); nothing is re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + substrate_independent_signal + carbon_dioxide_excluded
attribution_supported     enzyme_dependence + product_identity
calibration_applicability  titrant_standardized + proton_yield + buffer_capacity
rate_regime               initial_rate_regime + enzyme_substrate_ratio
kinetic_model             substrate_range
normalization_basis       active_enzyme_amount
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES
maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at
the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a
step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper
itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is
not selected. Sheet criteria with no counterpart here (measurement_identity, matrix_interference, partner_perturbation) are not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay
None. Qualitative statements keep the existing vocabulary. Direction and strength of a stated rate: literature_activity_direction (larger is stronger);
controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong
value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number
is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
TITRATED_FULL 0.95 -> TITRATED_ZERO 0.10, judged on the log of the titrated share f = 1 / (1 + 10^(pKa - pH)).
  Q1 the base added counts only the protons that are neutralized at the set pH: a product acid with a pKa near or above the pH is only partly
  ionized, so the titrant rate understates the reaction rate by the factor f. This is the central correction of the method (free fatty acids from a
  lipase, whose apparent pKa at an interface is raised, are the classic case). Q2 general: the pH-stat is run well above the pKa of the product
  acid, or the base added is divided by f or calibrated against a known amount of the acid (textbook pH-stat practice, from memory); the figure 0.95 is a
  judgement (pH one and a quarter units above the pKa). Q3 relative to the paper's own pH and pKa, which the grader records; right. Q4 the error of the
  rate is the factor f itself, a multiplicative error, so the degree is linear in ln f from 0.95 (about 5 percent low, full) to 0.10 (a tenfold
  understatement that depends entirely on the exact pKa, which shifts with ionic strength, temperature and the interface; no agreement; at or under it
  the paper's own numbers show the titrant does not count the reaction: conflicting). A stated correction (fact ionization_corrected yes) takes
  the grader's supported and never reaches this curve. Q5 a log-ratio ramp like the other multiplicative-error judgements of the class (enzyme ratio).
  Limit: the curve covers a proton-releasing reaction titrated with a base, the extraction's question says so.
BUFFER_FULL_MM 2 -> BUFFER_ZERO_MM 100, judged on the log of the buffer concentration.
  Q1 the controller adds base only after the pH has drifted past its dead band; a buffer holds the pH, so more protons are released before the
  electrode sees the drift: the added base lags the reaction and a short window misses part of it. A strongly buffered mixture also lowers the pH signal
  per proton, the sensitivity of the whole method. Q2 general: a pH-stat is run in unbuffered or very lightly buffered medium (the pH-stat lipase and
  esterase assays use 1 to 5 mM or no buffer; from memory). Q3 absolute concentration, which the grader records; the other determinant, the vessel
  volume and dead band, is not collected. Q4 the lag in moles is the buffer capacity times the volume times the dead band, and the buffer capacity is
  proportional to the buffer concentration (beta at most 0.58 x concentration per pH unit); for a 10 mL vessel and a 0.02 pH dead band that is about
  0.2 umol at 2 mM and about 12 umol at 100 mM, against a measurement window of the order of 10 umol of base: a few percent at the full end, the whole window at the zero
  end. Linear in the log of the concentration because the error is proportional to it. Q5 the same log-ratio ramp as the enzyme ratio; the reaction
  stated as unbuffered is supported without a degree, as for a fact. The titrant concentration is not judged (it is standardized or not: a fact).
CONSUMED_FULL_PERCENT 10 -> CONSUMED_ZERO_PERCENT 90, judged on the bias of the average rate.
  Q1 an "initial rate" that is really the average over a titration curve that has already bent, so the rate is too low. Q2 general: initial velocity
  means at most about 10 percent of the substrate consumed (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes; NCBI Assay Guidance Manual,
  Basics of Enzymatic Assays), from memory; a pH-stat reads the slope of the titrant volume against time, which is linear while the substrate is
  saturating, so a paper that states a larger share consumed but a linear curve is judged here conservatively (the worst case, a first-order curve). Q3 relative
  to the paper's own substrate, which the passage states as a share; right. Q4 the physics gives the shape: for a first-order progress curve the rate
  averaged over the window is f / -ln(1 - f) of the initial rate, f the fraction consumed: 0.95 at 10 percent, 0.90 at 20, 0.72 at 50, 0.39 at 90.
  The degree is linear in that bias between the two ends. The zero end is the share at which the worst-case rate is below 0.4 of the initial one, where
  a "rate" has become an end point; at or beyond it conflicting. Q5 the same as spectro_direct: a bias that grows with the departure.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law (rate = kcat E S / (Km + S)) holds only while the enzyme is small against the substrate plus the Km. Q2 general: the
  validity parameter of the reduced (quasi-steady-state) equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446), from memory. Q3
  relative to the paper's own S and Km: right, and the grader records all three (an interfacial Km of a lipase is not a bulk Km: the ratio is then
  recorded only when the paper states a Km). Q4 an error about the value of the ratio: 1 percent at 0.01 (full), unusable at 1; linear in the log of
  the ratio. Q5 as in spectro_direct.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to eight concentrations
  spanning 0.2 to 10 times the Km (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory. Q3 absolute (a count). Q4 the Michaelis-Menten
  equation has two parameters, so two concentrations are used up by the fit (no credit, supported with degree 0, never conflicting); each added
  concentration adds a degree of freedom: the degree rises linearly with count - 2. Q5 as in spectro_direct and SPR.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km. Q2 general: 0.2 to 10 times the Km (the references above), from memory; a pH-stat limits the low end by
  its sensitivity (the rate at 0.2 Km must still be titratable), which the paper's own lowest concentration already shows. Q3 relative to the paper's own
  Km: right. Q4 the rate is v / Vmax = S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km). Q5 working rule d of
  the SOP: 10 at the top where the plateau (Vmax) is a free amplitude known only by reaching it.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one titration, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of
  a mean (1 / sqrt(n)). Q5 exactly the shared replicate rule.
Facts with no number (the three controls, the carbon dioxide exclusion, the titrant standardization, the enzyme dependence, the product identity, the
active-site determination, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting,
silence is unknown. They have no researched value to soften. NOT judged, and why: the set pH against the enzyme's optimum and the temperature (the
claim carries no condition, and the identity block records pH and temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this
assay, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The base added to hold a pH: an absolute amount of protons, turned into a rate with the titrant concentration
  and the proton yield, with no extinction coefficient; absolute, but NOT selective: every proton source counts.
  Is there a reference range we would trust if the paper stated less? Yes for the rate (the range of kcat and kcat/Km of enzymes, as for spectro_direct), no
  for the attribution: the paper has to show the signal is the claimed reaction.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme blank or carbon dioxide exclusion is the dominant false
  positive of the method (spontaneous ester hydrolysis rises with the pH; carbon dioxide dissolving at pH above 7 consumes base for hours): for a weak
  activity it can be the whole signal. An unstated titrant standardization or proton yield is benign for a carboxylic acid titrated above its pKa and
  changes the magnitude, not the existence.
  If we assume it is fine and are wrong, how badly does the score mislead? Background counted as activity: wrong direction for a weak rate, wrong
  magnitude for a strong one; more than a KD (a magnitude only), about as much as a spectrophotometric rate with a missing blank.
  Consistent with KD and with spectro_direct? The default 0.80 is under spectro_direct's 0.85 (a chromophore at one wavelength is more selective than a
  count of all protons); the sheet criteria that guard against a false activity are lower than there.
  default 0.80. background_alternatives 0.70, attribution_supported 0.75, calibration_applicability 0.85, normalization_basis 0.90, sampling_basis 0.90
  (benign when unstated: the mass basis is the usual convention and triplicates are usual). rate_regime, kinetic_model, assertion_relevance,
  condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_ph_stat_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'substrate_independent_signal', 'carbon_dioxide_excluded'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('titrant_standardized', 'proton_yield', 'buffer_capacity'), 'rate_regime': ('initial_rate_regime', 'enzyme_substrate_ratio'),
                'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
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
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
TITRATED_FULL = 0.95  # EXPERT_REVIEW, owner to confirm (from memory, not verified): the titrated share f = 1 / (1 + 10^(pKa - pH)) of the released protons at which the base added is taken to count the reaction (about 5 percent low, the pH about one and a quarter units above the product pKa); full agreement from it.
TITRATED_ZERO = 0.10  # EXPERT_REVIEW, owner to confirm (from memory, not verified): a tenfold understatement of the rate by the base added, which depends entirely on the exact pKa (shifted by ionic strength, temperature and an interface): the paper's own numbers show the titrant does not count the reaction (no agreement, conflicting); the degree falls linearly in ln f from TITRATED_FULL to here (the error of the rate is the factor f).
BUFFER_FULL_MM = 2.0  # EXPERT_REVIEW, owner to confirm (from memory, not verified): buffer concentration up to which the lag of the added base behind the reaction is a few percent of a typical window (the lag in moles is the buffer capacity x vessel volume x pH dead band, about 0.2 umol for 2 mM, 10 mL and 0.02 pH, against about 10 umol of base in the window); pH-stat esterase and lipase assays are run in 1 to 5 mM buffer or none; full agreement up to it.
BUFFER_ZERO_MM = 100.0  # EXPERT_REVIEW, owner to confirm (from memory, not verified): at 100 mM the same lag is about 12 umol, the whole window (no agreement, conflicting); the degree falls linearly in the log of the concentration from BUFFER_FULL_MM, because the buffer capacity, and so the lag, is proportional to the concentration.
NM_PER_MM = 1.0e6  # FIXED_BY_DEFINITION: 1 mM is 1e6 nM (the grader hands the buffer over in nM).
IONIZATION_BASE = 10.0  # FIXED_BY_DEFINITION: the Henderson-Hasselbalch relation, the ionized over the unionized acid is 10^(pH - pKa).
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
NULL_REASONS = {'recovery': 'ph_stat_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_titrant_rate_is_not_an_attribution_fraction', 'total_signal': 'a_titrant_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_ph_stat_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_ph_stat_record',
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
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order progress curve that has consumed the fraction f of the substrate."""
    return 1.0 - fraction / -math.log1p(-fraction)


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


def _titrated_share(gap):
    """The share f = 1 / (1 + 10^gap) of the released protons that are titrated at the set pH, for gap = pKa of the product acid minus the pH."""
    return 1.0 / (1.0 + IONIZATION_BASE ** gap)


def _judge_proton_yield(native):
    return _graded(native['proton_yield_refs'], _log(_titrated_share(native['product_pka_minus_ph']), TITRATED_FULL, TITRATED_ZERO))


def _judge_buffer(native):
    return _graded(native['buffer_refs'], _log(native['buffer_nM'] / NM_PER_MM, BUFFER_FULL_MM, BUFFER_ZERO_MM))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('proton_yield', 'proton_yield_recorded_for_the_sheet'): _judge_proton_yield, ('buffer_capacity', 'buffer_recorded_for_the_sheet'): _judge_buffer,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'ph_stat_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_ph_stat(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'ph_stat_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'ph_stat', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
