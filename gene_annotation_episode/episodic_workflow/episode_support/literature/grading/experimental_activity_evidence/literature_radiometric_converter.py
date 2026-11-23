"""Radiometric converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to radiometric, deterministic. Input: the result of grade_radiometric. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
enzyme's molar mass the direction function needs, and for every sheet component that an activity measurement cannot honestly fill, the
reason it stays null. Draft built 2026-11-22 by copying the shape of spectro_direct; every number is EXPERT_REVIEW, owner to confirm, and
every literature citation is from memory and not verified.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1),
                  specific activity (U/mg) or the rate over the paper's own control (fold). Several may be stated; the one used is the
                  best-determined, in the class order ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated
                  value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the
                  value is the paper's, only its unit spelling changes (a radiometric specific activity is often in pmol/min/mg or nmol/min/mg).
                  quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None.
qualitative_effect  only when NO effect is stated and the paper states whether it saw activity above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact that states it, and direction_field_support the support of that one fact. A stated effect fixes the
                  direction; the statement is then not used. A result in words alone counts less than a measured one by the contract's
                  stated_strength; that is not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + carryover_control + counts_over_background
attribution_supported     enzyme_dependence + product_identity
calibration_applicability specific_radioactivity_stated + counting_calibration
matrix_interference       separation_recovery
rate_regime               initial_rate_regime + enzyme_substrate_ratio
kinetic_model             substrate_range
normalization_basis       active_enzyme_amount
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected; the degree is the smallest degree of the members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Sheet criteria with no
counterpart here (measurement_identity, partner_perturbation) are not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other
keys stay None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated
rate: literature_activity_direction (larger is stronger); controls, blanks and the rest lower the WEIGHT only, never the direction.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Each value is a researched value of THIS assay made
gradual: full agreement at the good value, falling smoothly (never a step) to zero at a no-longer-meaningful value; a value at or beyond its zero
end is conflicting (the paper itself shows it against the standard); unknown when the paper states nothing.
-----------------------------------------------------------------------------------------------------------------------------------
BACKGROUND_FOLD_FULL 10 -> BACKGROUND_FOLD_ZERO 1, judged linearly in the log of the counts over the blank. (New for this assay.)
  Q1 a radiometric signal is the label of the substrate carried into the product fraction. The blank (no enzyme, time zero, substrate alone
  through the separation) is made of unconverted substrate that leaks through the separation and of label impurities of the substrate (a
  labelled substrate decomposes by radiolysis, a few percent per month, from memory); at a weak activity, which is where radiometry is used
  because it is so sensitive, the blank can be most of the counts. Q2 general practice, not lab-specific: a blank of at most about a tenth of
  the counts of the reaction is the usual aim (from memory; no single guideline). Q3 relative to the paper's own blank, which the passage
  states as two counts or a ratio; right. Q4 the net signal is the reaction counts minus the blank, and the blank is itself uncertain
  (counting statistics and variable carry-over, say 20 percent of itself, an assumption): the relative error of the net rate is about 0.2 / (r - 1)
  for r counts over the blank, so 2 percent at r = 10, 7 percent at 4, 20 percent at 2, and no net signal at r = 1. The degree is linear in log r
  between 10 (full) and 1 (zero): 0.30 at r = 2, 0.60 at 4, 0.85 at 7. The log scale makes a doubling of the signal over the blank count the same
  step everywhere, as the class's own fold anchors do (rate_over_control runs from 1 to 1e3 on the log scale). At or under 1 the counts are no larger
  than the paper's own blank: conflicting (the paper itself shows no activity above its control). A fold at or under 1 given for the RATE
  is not judged here (it is strength 0 of the effect). Q5 same family as the other ratio ramps (enzyme ratio, fold gaps of the binding assays).
CONVERTED_FULL_PERCENT 10 -> CONVERTED_ZERO_PERCENT 90, judged on the bias of the average rate (as spectro_direct, same physics).
  Q1 an "initial rate" that is really the average over a time course that has already bent, so the rate is too low; in a discontinuous assay with
  one or two time points this is the main way the rate goes wrong. Q2 general: initial velocity means at most about 10 percent of the substrate
  converted (Cornish-Bowden, Fundamentals of Enzyme Kinetics; Copeland, Enzymes; NCBI Assay Guidance Manual, Basics of Enzymatic Assays), from
  memory; radiometric papers often say less than 5 or 10 percent, which is inside full agreement. Q3 relative to the paper's own substrate, stated as a
  share; right. Q4 for a first-order time course (substrate far below the Km, the worst case) the rate averaged over the window is f / -ln(1 - f)
  of the initial rate (0.95 at 10 percent, 0.72 at 50, 0.39 at 90); the degree is linear in that bias between the two ends; at or beyond 90
  percent a "rate" is an end point (conflicting). Q5 as the other curves: a bias that grows with the departure.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km) (as spectro_direct, same physics).
  Q1 the steady-state rate law holds only while the enzyme is small against the substrate plus the Km. Q2 general: the validity parameter
  of the reduced equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446), from memory. Q3 relative to the paper's own S and Km;
  the grader records all three (S is the total, labelled plus unlabelled, substrate). Q4 an error about equal to the ratio: 1 percent at 0.01,
  unusable at 1; linear in the log of the ratio. Q5 a log-ratio ramp like the other ratio judgements.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2, LOW_FACTOR 0.2, LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10, HIGH_ZERO_FACTOR 1.0 (as spectro_direct).
  Q1 a Km fitted to too few or badly placed substrate concentrations, so Km and Vmax trade off. Q2 general: about six to eight concentrations from 0.2
  to 10 times the Km (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory. In a radiometric assay the top is reached by diluting
  the label with unlabelled substrate, so the cost of the label does not cap it, and 10 stays (Vmax is a free amplitude known only by reaching
  it). Q3 count absolute; the two ratios relative to the paper's own Km. Q4 two parameters (Km, Vmax) use two concentrations, so the degree
  is linear in the residual degrees of freedom (count - 2) and 0 at 2 (supported, never conflicting); the two ends are judged linearly in
  the fractional saturation S / (S + Km), full at 0.2 Km and at 10 Km, zero (conflicting) at 1 Km. Q5 as spectro_direct and the SPR steady-state KD.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (duplicate to triplicate is the usual radiometric
  practice; triplicate is the aim). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the
  shared replicate rule.
Facts with no number (the controls, the enzyme dependence, the product identity, the counting calibration, the recovery, the active-site
determination, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence
is unknown. NOT judged, and why: the value of the specific radioactivity (it is the paper's own constant, stated with the amount of label; a wrong
one would show as an implausible rate, which the strength scale already reads); the counting efficiency (it is a property of the isotope and the
cocktail, not good or bad; only whether the counts were converted is a fact); the half-life correction of 32P and 35S (not stated by papers as
a fact that can be quoted); the temperature and pH (the identity block records them).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The amount of label carried from the substrate into the separated product per time, turned into an
  absolute rate by the specific radioactivity and the counting efficiency: absolute.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes: the same kcat and kcat/Km range as for any enzyme (Bar-Even et
  al. 2011, from memory), on which the strength anchors are built. A purified enzyme, a stated rate and a labelled native substrate are the standard evidence.
  What does an unstated control or calibration do to the number's meaning? The method is so sensitive that it is used for weak and slow
  activities, exactly where a blank (carry-over, label impurity) is most of the signal; an unstated blank is therefore not benign here. The
  product is known only through the separation, so an unstated identity leaves a second labelled product open. An unstated specific
  radioactivity or counting efficiency changes the size of the rate by a factor, not its existence.
  If we assume it is fine and are wrong, how badly does the score mislead? A carry-over or a labelled impurity counted as the enzyme's product:
  the direction is wrong for a weak rate; more severe than for an optical blank of a strong rate, less than a pull-down band.
  Consistent with KD and with spectro_direct? The default 0.85 equals spectro_direct (absolute rate with a trusted reference range); the two criteria
  that guard against a false activity are lower than there (background_alternatives 0.70 against 0.75, attribution_supported 0.75 against 0.80) because
  the signal is the label alone; the normalization basis and the replicates are benign when unstated, as for any enzyme assay (0.90).
  default 0.85. background_alternatives 0.70. attribution_supported 0.75. normalization_basis 0.90. sampling_basis 0.90.
  calibration_applicability, matrix_interference, rate_regime, kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_radiometric_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'carryover_control', 'counts_over_background'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('specific_radioactivity_stated', 'counting_calibration'), 'matrix_interference': ('separation_recovery',),
                'rate_regime': ('initial_rate_regime', 'enzyme_substrate_ratio'), 'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',),
                'sampling_basis': ('replicates',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
BACKGROUND_FOLD_FULL = 10.0  # EXPERT_REVIEW, owner to confirm: counts of the reaction at least ten times the counts of its own blank (the net rate is then off by about 2 percent if the blank is uncertain by 20 percent, an assumption; from memory, no single guideline); full agreement from it.
BACKGROUND_FOLD_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: counts equal to the blank leave no net signal (no agreement; at or under it the paper itself shows no activity above its control: conflicting); the degree falls from BACKGROUND_FOLD_FULL linearly in the log of the fold, because the relative error of the net rate goes as 1 / (fold - 1) and a doubling of the signal over the blank is the same step everywhere.
CONVERTED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the substrate converted in the window of an initial rate (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement up to it.
CONVERTED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent converted the rate averaged over a first-order time course (the worst case) is 0.39 of the initial rate, a factor 2.6 off: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, Vmax), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (v is 1/6 of Vmax there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (v is 10/11 of Vmax); Vmax is a free amplitude known only by reaching it, and the top is reached by diluting the label with unlabelled substrate (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments (duplicate to triplicate is usual in radiometric work); full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
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
NULL_REASONS = {'recovery': 'a_radiometric_assay_has_no_matrix_recovery_measurement_of_this_role', 'attributed_signal': 'a_counted_rate_is_not_an_attribution_fraction', 'total_signal': 'a_counted_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_radiometric_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_radiometric_record',
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
    refs = native['converted_refs']
    fraction, zero = native['converted_percent'] / PERCENT_PER_FRACTION, CONVERTED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(CONVERTED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_background(native):
    return _graded(native['background_refs'], _log(native['counts_over_background'], BACKGROUND_FOLD_FULL, BACKGROUND_FOLD_ZERO))


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


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'converted_recorded_for_the_sheet'): _judge_regime, ('counts_over_background', 'background_ratio_recorded_for_the_sheet'): _judge_background,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'radiometric_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_radiometric(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'radiometric_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'radiometric', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
