"""Stopped_flow converter: turns the grader's result into what the A105 activity_rate sheet takes.

DRAFT of 2026-11-22 for the owner to correct. Hand-built, private to stopped_flow, deterministic, copied in structure from the spectro_direct
converter. Input: the result of grade_stopped_flow. Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'activity_rate'),
the sheet itself (grade_assay run on it), the dependence keys the merger needs, the enzyme's molar mass the direction function needs (None here: no
specific activity is an effect of this type), and for every sheet component that a stopped-flow experiment cannot honestly fill, the reason it stays
null.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1) or turnover (s^-1). Of the four
                  rate quantities of the record, three are rates per enzyme in s^-1 and are read on the turnover scale, the first stated of
                  steady_state_turnover, single_turnover_rate, observed_rate_constant (EFFECT_SOURCES). The order is the LOWEST first, on purpose: the
                  steady-state turnover kcat is the true turnover and is at most the rate of the chemical step; the single-turnover rate is at least
                  kcat; the observed rate constant of one condition is at most the limiting one. Reading the lower of two stated numbers never
                  gives the result more strength than the paper's own numbers allow. Catalytic efficiency, when stated, comes first, as in the class
                  order (ACTIVITY_EFFECT_ORDER, literature_activity_direction.select_activity_effect). A stated value in another unit of the record's
                  vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling
                  changes. quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT source quantity allows it:
                  standard_error (the standard error of a fit is one) -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is
                  supported; confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   None: the record holds no enzyme mass because no specific activity is read by this type (the key is kept because
                  literature_page_update reads it for every activity_rate result).
qualitative_effect  only when NO effect is stated and the paper states whether it saw the reaction above its own control: statement
                  'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the refs of
                  the fact that states it, and direction_field_support taken from the quote support of that one fact. A stated effect fixes the
                  direction; the statement is then not used. A result stated in words alone already counts less than a measured one
                  (literature_row_contract.stated_strength): nothing is re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   spontaneous_reaction_control + enzyme_only_signal
attribution_supported     phase_assignment + product_identity
rate_regime               dead_time_coverage + enzyme_excess
kinetic_model             substrate_range
normalization_basis       active_enzyme_amount + burst_amplitude
sampling_basis            shots_averaged + replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, calibration_applicability, matrix_interference, partner_perturbation) are not selected:
a first-order rate constant does not depend on how the signal is calibrated, and no matrix or partner is part of this type.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made
gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the
physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero
end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members
that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined
status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members
are all not_applicable is not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay
None (no immobilized enzyme, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated rate:
literature_activity_direction (same paradigm as binding, larger is stronger); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value
misleads and whether the shape fits, Q5 consistency with the other assays). THE VALUES BELOW ARE A FIRST DRAFT: every number is EXPERT_REVIEW, owner to
confirm, and every literature citation is from the drafter's memory and NOT verified.
-----------------------------------------------------------------------------------------------------------------------------------
DEAD_TIME_OBSERVED_FULL 0.90 -> DEAD_TIME_OBSERVED_ZERO 0.05, judged linearly in the share of the phase that was seen, exp(-k t_dead).
  Q1 a rate constant so fast that most of the phase happened inside the dead time, so the reported k_obs is extrapolated from the tail, or from an
  amplitude that is mostly missing. Q2 general physics: for a first-order phase the share of its amplitude that is over before the first observation is
  1 - exp(-k t_dead); the instrument literature (Gutfreund, Enzymes: Physical Principles; Johnson 2003 and 2009, Methods in Enzymology, from memory) asks
  that the half-time be several dead times. 0.90 seen is k t_dead = 0.105, a half-time of about 6.6 dead times; the dead time itself (about 1 ms) is the
  instrument's own, stated by the paper. Q3 relative to the paper's own dead time and rate constant (the grader records both); right. Q4 at 0.05 seen
  (k t_dead = 3.0) 95 percent of the amplitude is gone and the rate is no longer measured (conflicting); in between the loss is graded linearly in the
  share seen, which is the quantity the instrument actually loses. Q5 no other type has a dead time; the linear ramp on a physical quantity follows the
  other converters (apparent absorbance, bias of the average rate).
ENZYME_EXCESS_FULL 5 -> ENZYME_EXCESS_ZERO 1, judged on the log of E / S (only when the passage itself says single turnover).
  Q1 a reaction called single turnover whose enzyme is not in excess, so a share of the enzyme turns over more than once, or the substrate is not all
  bound, and the observed rate constant is not that of one turn. Q2 general: single-turnover experiments use the enzyme in excess, about two- to
  ten-fold over the substrate, so that all the substrate is bound and each enzyme reacts at most once (Fersht, Structure and Mechanism in Protein
  Science; Johnson 2003, from memory); 5 is the middle of that practice. Q3 relative to the paper's own two concentrations (the grader records the ratio);
  right. Q4 at E / S of 1 the enzyme is not in excess at all (the paper's own numbers contradict its statement, conflicting); the loss of agreement between
  1 and 5 is on the log of the ratio because the fraction of substrate bound rises with the log of the excess when the binding is not very tight. A larger
  excess is not judged better. Q5 a log-ratio ramp, like the enzyme-over-substrate-plus-Km ramp of spectro_direct.
BURST_FULL_PER_SITE 0.5 -> BURST_ZERO_PER_SITE 0.02, judged on the log of the burst amplitude per active site.
  Q1 a rate constant that belongs to a small part of the enzyme (a contaminating activity, a damaged minority) and not to the enzyme preparation the
  paper is about. Q2 practice, from memory: a burst of the order of one equivalent per active site shows the main population reacts; a substoichiometric
  burst (one half and less) is common and legitimate when the equilibrium of the chemical step is not far to the product, so full agreement starts at
  one half; two percent is the contamination level of a good preparation (purity of 98 percent), under which the phase cannot be told from a
  contaminant. Q3 relative to the paper's own active sites (per site, or the burst over the enzyme concentration); right. Q4 a burst above one per site is
  not judged (it would show the active-site concentration is understated, which the active-site fact guards). The log scale is because a contaminant
  share is multiplicative. Q5 no other type has a burst.
MIN_SUBSTRATE_CONCENTRATIONS 5, SUBSTRATE_CONCENTRATIONS_ZERO 2 (the concentrations at which k_obs was measured).
  Q1 a limiting rate constant and a half-saturation concentration fitted to too few k_obs to show the hyperbola holds. Q2 general: k_obs against the
  substrate is a hyperbola of two parameters (the limiting rate constant and the half-saturation concentration, plus sometimes an intercept) and is
  usually measured at five to eight concentrations (Johnson 2003; Fersht), from memory; 5 is the low end, and not 6 as for a steady-state curve,
  because every k_obs is itself a fit of an averaged trace and is better determined than one steady-state rate. Q3 absolute (a count). Q4 two
  parameters use up two concentrations: the degree rises linearly with the residual degrees of freedom, (count - 2) / (5 - 2): 2 concentrations give 0, 3 give 1/3, 4 give
  2/3, 5 give 1; never conflicting. Q5 the same residual-degree-of-freedom count as spectro_direct and the SPR steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the half-saturation concentration).
  Q1 a series that does not bracket the half-saturation concentration, so the limiting rate constant and the half-saturation concentration trade off
  (no saturation) or the low end (which gives the second-order rate constant) is unseen. Q2 general: 0.2 to 10 times the half-saturation concentration
  (Johnson 2003; Cornish-Bowden), from memory. Q3 relative to the paper's own half-saturation concentration (the grader records both ratios); right.
  Q4 k_obs / k_max = S / (S + K), so both ends are judged linearly in the fractional saturation S / (S + K) (1/6 at 0.2 K, 10/11 at 10 K, 1/2 at K, the
  zero end of both). Q5 the SOP working rule d: the top is 10 where the plateau is a free amplitude known only by reaching it; the limiting rate constant
  is that. (A stopped-flow paper is often limited by solubility, the signal or the syringe concentration: those papers earn a partial degree, not a
  conflict, until the highest concentration is no more than the half-saturation concentration.)
SHOTS_FULL_CREDIT 5, degree min(1, sqrt(n / 5)).
  Q1 a trace that is one shot, whose noise sets the error of k_obs. Q2 practice: three to ten shots are averaged into one trace (instrument manuals and
  Johnson 2003), from memory; 5 is the middle. Q3 absolute count. Q4 the noise of an average falls as 1 / sqrt(n): one shot 0.45, three 0.77, full from
  five; never conflicting. Shots are technical repeats of one mixture and are NOT replicates (the independent experiments are judged apart). Q5 the
  owner's precision-of-a-mean shape, as the replicate rule.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate constant from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4
  precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the phase assignment, the product identity, the active-site determination, the native substrate and the purified
enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged,
and why: the temperature and the pH (the claim carries no condition and the identity block records the temperature); the size of the rate constant (it is
the effect, read by the direction function); the fit error of k_obs (it is the spread and enters the effect variance); the amplitude of the signal in
absorbance or fluorescence units (a first-order rate constant does not depend on it).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this
type, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The first-order rate constant of one phase of an optical signal read from about a millisecond: absolute and
  independent of the signal's calibration (the reason this type needs no extinction coefficient), but a rate of a PHASE, which is the chemistry only when
  the phase is assigned to it.
  Is there a reference range we would trust if the paper stated less? Yes for the size: rate constants of the chemical step of enzymes sit in the range of
  kcat (about 0.01 to 1000 s^-1, Bar-Even et al. 2011, from memory), which the strength anchors use. No for the assignment: a fast optical change is as
  likely a binding or a conformational step.
  What does an unstated control do to the number's meaning? An unstated enzyme-free or buffer trace is usually benign for a large signal change (mixing
  and dilution artefacts are small and routine to subtract). An unstated assignment of the phase to the chemical step is the dominant risk: the number is
  then a real rate constant of something else, and the direction of the claim is at stake.
  If we assume it is fine and are wrong, how badly does the score mislead? For the assignment, the claim could be supported by a binding or conformational
  rate: more severe than a KD's magnitude error. For the other criteria, a few percent to a factor in the rate.
  Consistent with KD and with spectro_direct? The default 0.80 is under spectro_direct (0.85) because the phase must be assigned, which a steady-state
  absorbance slope of a product does not need; the benign criteria equal the anchor 0.90.
  default 0.80. attribution_supported 0.65 (the assignment of the phase to the chemical step, and the identity of the product, are the central gap).
  rate_regime 0.85 (the dead time is usually about a millisecond and most chemical-step rate constants are far under it; the enzyme excess of a
  single-turnover design is usually apparent from the text). normalization_basis 0.90 and sampling_basis 0.90 (benign when unstated: a first-order rate
  constant does not scale with the enzyme amount at saturating substrate, and replicates are usual). background_alternatives, kinetic_model,
  assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_stopped_flow_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'enzyme_only_signal'), 'attribution_supported': ('phase_assignment', 'product_identity'),
                'rate_regime': ('dead_time_coverage', 'enzyme_excess'), 'kinetic_model': ('substrate_range',), 'normalization_basis': ('active_enzyme_amount', 'burst_amplitude'),
                'sampling_basis': ('shots_averaged', 'replicates'), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
DEAD_TIME_OBSERVED_FULL = 0.90  # EXPERT_REVIEW, owner to confirm: at least 90 percent of the phase seen after the dead time (k t_dead of 0.105, a half-time of about 6.6 dead times; Gutfreund; Johnson 2003, from memory); full agreement from it.
DEAD_TIME_OBSERVED_ZERO = 0.05  # EXPERT_REVIEW, owner to confirm: 5 percent of the phase seen (k t_dead of 3.0): 95 percent of the amplitude is over before the first observation and the rate is extrapolated, not measured (no agreement); the degree falls linearly in the share seen, exp(-k t_dead), from the full end to here.
ENZYME_EXCESS_FULL = 5.0  # EXPERT_REVIEW, owner to confirm: enzyme in about fivefold excess over the substrate, the middle of the two- to ten-fold practice of single-turnover experiments (Fersht; Johnson 2003, from memory); full agreement from it.
ENZYME_EXCESS_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: enzyme no larger than the substrate is not in excess, so the paper's numbers contradict the single-turnover statement (no agreement); falls from ENZYME_EXCESS_FULL linearly in the log of E / S.
BURST_FULL_PER_SITE = 0.5  # EXPERT_REVIEW, owner to confirm: a burst of half an equivalent per active site or more shows the main population of the enzyme reacts (substoichiometric bursts are common and legitimate, from memory); full agreement from it.
BURST_ZERO_PER_SITE = 0.02  # EXPERT_REVIEW, owner to confirm: two percent of the sites is the contamination level of a good preparation (98 percent pure): the phase cannot be told from a contaminant (no agreement); falls from BURST_FULL_PER_SITE linearly in the log of the burst per site, because a contaminant share is multiplicative.
MIN_SUBSTRATE_CONCENTRATIONS = 5  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable k_obs against substrate curve (five to eight, Johnson 2003; Fersht, from memory; one fewer than a steady-state curve because each k_obs is a fit of an averaged trace); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the hyperbola has two parameters (limiting rate constant, half-saturation concentration), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the half-saturation concentration (k_obs is 1/6 of its limit there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the half-saturation concentration itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + K).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the half-saturation concentration (k_obs is 10/11 of its limit); the limiting rate constant is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the half-saturation concentration itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + K).
SHOTS_FULL_CREDIT = 5  # EXPERT_REVIEW, owner to confirm: shots averaged into one trace, full credit from it (three to ten is the usual practice, instrument manuals and Johnson 2003, from memory); below it degree min(1, sqrt(n / SHOTS_FULL_CREDIT)): the noise of an average falls as 1 / sqrt(n); never conflicting.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect source quantity (literature_row_contract.ACTIVITY_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
_RATE_CONSTANT_FACTORS = ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE})   # FIXED_BY_DEFINITION: 60 s is 1 min; the stated number is the paper's.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (mM^-1 is 1000 M^-1; uM^-1 is 1e6 M^-1; 60 s is 1 min); the stated number is the paper's.
    'catalytic_efficiency': ('M^-1s^-1', {'M^-1 s^-1': 1.0, 'mM^-1 s^-1': 1.0e3, 'uM^-1 s^-1': 1.0e6}),
    'steady_state_turnover': _RATE_CONSTANT_FACTORS,
    'single_turnover_rate': _RATE_CONSTANT_FACTORS,
    'observed_rate_constant': _RATE_CONSTANT_FACTORS,
}
# The effect quantity of the class (ACTIVITY_EFFECT_ORDER) -> the record quantities that can state it, the first stated one used (the lowest first, see the docstring).
EFFECT_SOURCES = {'catalytic_efficiency': ('catalytic_efficiency',), 'turnover': ('steady_state_turnover', 'single_turnover_rate', 'observed_rate_constant')}
# The quantity_kind (QUANTITY_KINDS['activity_rate']) that names the kind of each effect quantity; literature_activity_direction.ACTIVITY_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'catalytic_efficiency': 'catalytic_efficiency', 'turnover': 'turnover'}
KIND_WITHOUT_EFFECT = 'rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'stopped_flow_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_rate_constant_is_not_an_attribution_fraction', 'total_signal': 'a_rate_constant_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_stopped_flow_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_stopped_flow_record',
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
    """Fractional saturation S / (S + K) of a substrate S given as S / K: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _share_seen(rate_per_s, dead_time_s):
    """The share of a first-order phase of rate constant k that is still left of its amplitude at the first observation, after the dead time: exp(-k t_dead)."""
    return math.exp(-rate_per_s * dead_time_s)


def _judge_dead_time(native):
    return _graded(native['dead_time_refs'], (_share_seen(native['fastest_rate_per_s'], native['dead_time_s']), DEAD_TIME_OBSERVED_FULL, DEAD_TIME_OBSERVED_ZERO))


def _judge_enzyme_excess(native):
    return _graded(native['enzyme_excess_refs'], _log(native['enzyme_over_substrate'], ENZYME_EXCESS_FULL, ENZYME_EXCESS_ZERO))


def _judge_burst(native):
    return _graded(native['burst_refs'], _log(native['burst_per_site'], BURST_FULL_PER_SITE, BURST_ZERO_PER_SITE))


def _judge_series(native):
    # the two ratios keep their ramps (conflicting at their zero end), judged on the fractional saturation; the lower end is judged only when the series
    # has one distinct from its upper end (one concentration is a short series, not a badly placed one). The count only lowers the degree, never conflicts.
    refs = native['concentration_refs']
    low, high = native['concentration_low_over_half'], native['concentration_high_over_half']
    limits = [(_saturation(high), _saturation(HIGH_FACTOR), _saturation(HIGH_ZERO_FACTOR))]
    if low < high:
        limits.append((_saturation(low), _saturation(LOW_FACTOR), _saturation(LOW_ZERO_FACTOR)))
    verdict = _graded(refs, *limits)
    if verdict['status'] == 'conflicting':
        return verdict
    count_degree = max(0.0, min(1.0, _share(native['concentration_count'], MIN_SUBSTRATE_CONCENTRATIONS, SUBSTRATE_CONCENTRATIONS_ZERO)))
    return _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_shots(native):
    return _verdict('supported', native['shots_refs'], min(1.0, math.sqrt(native['shots_averaged'] / SHOTS_FULL_CREDIT)))      # precision of the averaged trace, see SHOTS_FULL_CREDIT


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('dead_time_coverage', 'dead_time_recorded_for_the_sheet'): _judge_dead_time, ('enzyme_excess', 'enzyme_excess_recorded_for_the_sheet'): _judge_enzyme_excess,
          ('burst_amplitude', 'burst_amplitude_recorded_for_the_sheet'): _judge_burst, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
          ('shots_averaged', 'shots_recorded_for_the_sheet'): _judge_shots, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, source, ref):
    """The stated source quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][source]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[source]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'stopped_flow_' + source + ':' + ref, operand['source_refs'], operand['origin'], source, operand['support'])


def _first_stated(native, quantity, ref):
    """(source, effect operand) of the first stated source quantity of the effect ``quantity``, or (None, None)."""
    for source in EFFECT_SOURCES[quantity]:
        operand = _stated_effect(native, source, ref)
        if operand is not None:
            return source, operand
    return None, None


def _variance(graded, source, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of the source quantity ``source``."""
    native = graded['native']
    spread = native['quantities'][source + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, source + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    unit, factors = UNIT_FACTORS[source]
    sd = spread['value'] * factors[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_stopped_flow(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    found = {quantity: _first_stated(native, quantity, ref) for quantity in EFFECT_SOURCES}
    stated = {quantity: operand for quantity, (source, operand) in found.items()}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_activity_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_activity_effect(stated)
        source = found[chosen][0]
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, source, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[source][0] + '_squared', 'stopped_flow_' + source + '_variance:' + ref, variance_refs, 'derived', source + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'stopped_flow', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support, 'enzyme_mass_g_per_mol': None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of the reaction above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']      # the support class of the fact activity_detected_above_control, the one field the statement is derived from
    return result
