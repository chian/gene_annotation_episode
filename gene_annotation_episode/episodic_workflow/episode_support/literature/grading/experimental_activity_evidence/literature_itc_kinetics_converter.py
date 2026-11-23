"""Itc_kinetics converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to itc_kinetics, deterministic. Input: the result of grade_itc_kinetics. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
enzyme's molar mass the direction function needs, and for every sheet component that an activity measurement cannot honestly fill, the
reason it stays null. Built 2026-11-22 as a copy of the spectro_direct converter (the model of the class); the constants below are this
method's own. DRAFT: every number is EXPERT_REVIEW, owner to confirm; every literature citation is from memory and not verified.

The method in one paragraph. The reaction runs in a calorimeter cell and its heat is read as thermal power. The power is the rate times the cell
volume times the apparent reaction enthalpy, so the rate is only as good as (1) the enthalpy, which has to be measured on its own (complete
conversion of a known amount of substrate in the same buffer, because the apparent enthalpy contains the heat of buffer protonation: Todd and
Gomez 2001 Anal Biochem 296:179, from memory), (2) the separation of the reaction heat from the heats of diluting and mixing the substrate
and the enzyme and from the baseline noise, and (3) the response time of the instrument, which lags the power by tens of seconds, so a fast
change of the rate is smeared. The heat is non-specific: any process in the cell (a contaminating activity, binding, aggregation, buffer
ionisation) adds to it, so the assay does not say what the product is.

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
enzyme_mass_g_per_mol   the enzyme's molar mass in g/mol (the stated mass in kDa times 1000), or None; literature_page_update passes it to
                  the direction function, which needs it for the ends of the specific-activity scale.
qualitative_effect  only when NO effect is stated and the paper states whether it saw activity above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact that states it, and direction_field_support the support of that one fact. A stated effect fixes the direction;
                  the statement is then not used. A result stated in words alone counts less than a measured one by the contract (stated_strength);
                  that is not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   substrate_dilution_control + enzyme_dilution_control + signal_over_blank
attribution_supported     enzyme_dependence + product_identity
calibration_applicability  enthalpy_stated + enthalpy_determined + signal_over_noise
rate_regime               initial_rate_regime + response_time_accounted + enzyme_substrate_ratio
kinetic_model             substrate_range
normalization_basis       active_enzyme_amount
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made
gradual (SOP step 3): full agreement at the researched good value, falling linearly on the scale the physics gives to zero at a researched
no-longer-meaningful value (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its
zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its
members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a
status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity,
matrix_interference, partner_perturbation) are not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys
stay None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated
rate: literature_activity_direction (same paradigm as binding, larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
BLANK_SHARE_FULL 0.1 -> BLANK_SHARE_ZERO 1.0, judged linearly in the share q = control power / reaction power.
  Q1 the heat of diluting and mixing the substrate and the enzyme is the commonest false heat in a calorimeter: a reaction power that is mostly
  control heat is mostly not the enzyme. Q2 general: the control titration is subtracted in every enzyme-kinetics ITC protocol (Todd and Gomez
  2001; the MicroCal and TA Instruments application notes, from memory); the share is lab-specific but the principle is not. Q3 relative to the
  paper's own reaction power, which the passage states, and the grader records both. Q4 a subtracted blank leaves an error of the order of the
  blank's own uncertainty, which grows with its share; 10 percent of the signal is the full end (the net signal is at least 90 percent of the
  gross), and a control as large as the reaction power (q = 1) leaves no net enzyme heat at all (no agreement, conflicting: the paper's own
  control shows nothing above it). The degree is linear in q because the net signal 1 - q is linear in it. Q5 the same relative-to-the-paper's-
  own-control idea as the signal over the control of the other assays.
NOISE_SHARE_FULL 0.1 -> NOISE_SHARE_ZERO 0.3, judged linearly in the share e = baseline noise / reaction power.
  Q1 a reaction power that is hardly above the baseline noise has a large relative error, and below the detection limit it cannot be told from the
  baseline. Q2 general: the limit of quantification is 10 times the noise (signal to noise 10) and the limit of detection about 3.3 times (ICH Q2 and
  IUPAC practice, from memory); the noise itself (peak-to-peak or standard deviation) is instrument-specific, which is why the paper's own noise is
  read. Q3 relative to the paper's own power and noise, both recorded by the grader. Q4 the relative error of the power is the noise over the
  power, so the degree is linear in e between the quantification limit (full) and the detection limit (no agreement: the heat is not distinguished
  from the baseline, conflicting). The paper's noise may be a peak-to-peak value, which is about five times a standard deviation; this makes the
  judgement stricter than a standard deviation would, and the choice is left to the owner. Q5 the same relative-error scale as the blank share.
CONSUMED_FULL_PERCENT 10 -> CONSUMED_ZERO_PERCENT 60, judged linearly in the fraction f consumed.
  Q1 a rate read from the power when much of the substrate is gone is the rate at a lower substrate concentration than the one the paper names.
  Q2 general: initial velocity means at most about 10 percent of the substrate consumed (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from
  memory. Q3 relative to the paper's own substrate, which the passage states as a share. Q4 in ITC the rate is the instantaneous power, not an
  average over a window, so in the worst case (substrate far below the Km, first-order) the rate read at the consumed fraction f is 1 - f of the
  rate at the start; the degree is linear in that shortfall f between the two ends. The zero end 0.6 is where the worst-case rate is 0.4 of the
  initial one (a factor 2.5 off), the same factor as the zero end of the average-rate bias in the spectrophotometric type (the instantaneous
  shortfall is steeper than the average one, so the same factor sits at a smaller consumed share). Q5 same idea as the other rate-regime curves.
ENZYME_RATIO_FULL 0.01 -> ENZYME_RATIO_ZERO 1.0, judged on the log of E / (S + Km).
  Q1 the steady-state rate law (rate = kcat E S / (Km + S)) holds only while the enzyme is small against the substrate plus the Km; a calorimeter needs
  enough heat, so ITC kinetics often runs at higher enzyme than an optical assay, which makes this check matter more here. Q2 general: the validity
  parameter of the reduced (quasi-steady-state) equation is E0 / (S0 + Km) (Segel and Slemrod 1989, SIAM Rev 31:446), from memory. Q3 relative to the
  paper's own S and Km: right, and the grader records all three. Q4 an error of about the value of the ratio: 1 percent at 0.01 (full), unusable
  at 1; linear in the log of the ratio because the error is proportional to it. Q5 the same as the spectrophotometric type.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2; LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0.
  Q1 a Km fitted to too few or badly placed substrate concentrations (separate experiments, or the points of one multiple-injection or progress-curve
  analysis). Q2 general: about six to eight concentrations spanning 0.2 to 10 times the Km (Cornish-Bowden; Copeland), from memory; a single
  injection sweeps the substrate down by itself, which a paper may state as a series. Q3 relative to the paper's own Km. Q4 the rate is
  v / Vmax = S / (S + Km); the count is linear in the residual degrees of freedom (two parameters, Km and Vmax) and the ends are linear in the
  fractional saturation S / (S + Km). Q5 working rule d of the SOP: 10 where Vmax is a free amplitude known only by reaching it. Same values as the
  spectrophotometric type: the hyperbola is the same.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one titration, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice in calorimetry). Q3 absolute count.
  Q4 precision of a mean (1 / sqrt(n)). Q5 exactly the shared replicate rule.
Facts with no number (the dilution controls, the enthalpy determination, the enzyme dependence, the product identity, the response time, the
active-site determination, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting,
silence is unknown. They have no researched value to soften. NOT judged, and why: the size of the enthalpy (a larger heat only makes the signal
larger, which the signal-over-noise share already reads); the temperature and the buffer (the identity block records the temperature; a buffer
effect on the enthalpy is carried by the fact that the enthalpy was measured in the assay buffer); the sign of the enthalpy.

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The heat rate of any reaction in the cell, turned into an absolute rate (per mg, per enzyme) by a
  separately measured enthalpy: absolute, with kcat, Km and kcat/Km as well-defined constants, but only as good as that enthalpy and the controls.
  Is there a reference range we would trust if the paper stated less (as for KD)? Yes for the constants (the range of kcat and kcat/Km of
  enzymes, Bar-Even et al. 2011, from memory, as for the spectrophotometric type); no for the heat itself, which any process in the cell adds to.
  What does an unstated control or calibration do to the number's meaning? An unstated dilution control is a real gap (dilution heat is the usual
  false heat, although the ITC practice nearly always includes the control); an unstated enthalpy determination leaves the rate off by a factor
  that is small against the decades of the strength scale; an unidentified product means a contaminating activity or a second heat source is
  counted as the enzyme's.
  If we assume it is fine and are wrong, how badly does the score mislead? A background heat or a contaminant counted as the enzyme's: the direction is
  wrong for a weak rate and the magnitude for a strong one: a little worse than for a chromophore assay, whose signal names the substance.
  Consistent with KD? Just under the spectrophotometric type (0.85), which has a specific signal.
  default 0.80. background_alternatives 0.70 (the dilution heat, the commonest false heat). attribution_supported 0.75 (heat is non-specific and the
  product is rarely identified). normalization_basis 0.90 and sampling_basis 0.90 (benign when unstated, as for the spectrophotometric type).
  calibration_applicability, rate_regime, kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_itc_kinetics_converted'
CRITERIA_MAP = {'background_alternatives': ('substrate_dilution_control', 'enzyme_dilution_control', 'signal_over_blank'), 'attribution_supported': ('enzyme_dependence', 'product_identity'),
                'calibration_applicability': ('enthalpy_stated', 'enthalpy_determined', 'signal_over_noise'), 'rate_regime': ('initial_rate_regime', 'response_time_accounted', 'enzyme_substrate_ratio'),
                'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
GRAMS_PER_MOL_PER_KDA = 1000.0  # FIXED_BY_DEFINITION: 1 kDa is 1000 g/mol.
BLANK_SHARE_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: control (dilution) power at most a tenth of the reaction power, so the net enzyme heat is at least 90 percent of the gross; full agreement up to it.
BLANK_SHARE_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a control as large as the reaction power leaves no net enzyme heat (no agreement, conflicting: the paper's own control shows nothing above it); the degree falls linearly in the share, because the net signal 1 - share is linear in it.
NOISE_SHARE_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: baseline noise at most a tenth of the reaction power, signal to noise 10, the limit of quantification (ICH Q2, IUPAC practice, from memory); full agreement up to it.
NOISE_SHARE_ZERO = 0.3  # EXPERT_REVIEW, owner to confirm: noise a third of the power, signal to noise about 3.3, the limit of detection (ICH Q2, from memory): the heat is not told from the baseline (no agreement, conflicting); the degree falls linearly in the relative error noise / power.
CONSUMED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the substrate consumed when the rate is read (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement up to it.
CONSUMED_ZERO_PERCENT = 60.0  # EXPERT_REVIEW, owner to confirm: at 60 percent consumed the instantaneous rate of a first-order reaction (the worst case) is 0.4 of the initial one, a factor 2.5 off, the same factor as the zero end of the spectro_direct average-rate bias (no agreement); the degree falls linearly in the shortfall, which in the worst case equals the consumed fraction.
ENZYME_RATIO_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: the validity parameter E / (S + Km) of the steady-state rate law (Segel and Slemrod 1989, from memory) at 0.01, about 1 percent error; full agreement up to it.
ENZYME_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme as large as substrate plus Km: the steady-state law does not describe the reaction (no agreement); falls from ENZYME_RATIO_FULL linearly in the log of the ratio, because the error of the rate is proportional to it.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable saturation curve (about six to eight, Cornish-Bowden; Copeland, from memory); full agreement from it.
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
NULL_REASONS = {'recovery': 'itc_kinetics_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_heat_rate_is_not_an_attribution_fraction', 'total_signal': 'a_heat_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_itc_kinetics_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_itc_kinetics_record',
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


def _judge_blank(native):
    return _graded(native['blank_refs'], (native['dilution_over_signal'], BLANK_SHARE_FULL, BLANK_SHARE_ZERO))


def _judge_noise(native):
    return _graded(native['noise_refs'], (native['noise_over_signal'], NOISE_SHARE_FULL, NOISE_SHARE_ZERO))


def _judge_regime(native):
    return _graded(native['consumed_refs'], (native['consumed_percent'] / PERCENT_PER_FRACTION, CONSUMED_FULL_PERCENT / PERCENT_PER_FRACTION, CONSUMED_ZERO_PERCENT / PERCENT_PER_FRACTION))


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
JUDGES = {('signal_over_blank', 'blank_share_recorded_for_the_sheet'): _judge_blank, ('signal_over_noise', 'noise_share_recorded_for_the_sheet'): _judge_noise,
          ('initial_rate_regime', 'consumed_recorded_for_the_sheet'): _judge_regime, ('enzyme_substrate_ratio', 'enzyme_ratio_recorded_for_the_sheet'): _judge_enzyme_ratio,
          ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'itc_kinetics_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


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


def convert_itc_kinetics(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'itc_kinetics_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'itc_kinetics', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': mass['value'] * GRAMS_PER_MOL_PER_KDA if mass['status'] == 'point' else None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
