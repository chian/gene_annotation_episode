"""Transport_vesicle_probe_flux converter: turns the grader's result into what the A105 transport_response sheet takes.

Hand-built, private to transport_vesicle_probe_flux, deterministic. Input: the result of grade_transport_vesicle_probe_flux. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for
every sheet component that a vesicle flux cannot honestly fill, the reason it stays null. The class has no enzyme mass: unlike the activity types the result
carries no extra field for the direction function.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (literature_row_contract.TRANSPORT_STRENGTH_ANCHORS): the turnover per transporter (s^-1),
                  the fold over the paper's own protein-free vesicles (dimensionless) or the rate per mg of protein (nmol/min/mg). Several may be stated; the one
                  used is the best-determined, in the class order TRANSPORT_EFFECT_ORDER (literature_transport_response_direction.select_transport_effect; the
                  reason is in the contract). A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS,
                  FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes. quantity_kind of the extraction names the kind of the effect
                  (TRANSPORT_KIND_OF_QUANTITY of the contract), which the direction function reads.
                  NOT an effect, and why: the fraction released (percent of the pool), the rate constant and the half-time of the release. The class reads any
                  's^-1' transport rate as a turnover per transporter, and a rate constant of the vesicle population depends on how many transporters each vesicle
                  holds; the fraction released has no kind of the class. They are recorded and used by the criteria release_over_control and time_resolution.
                  A turnover stated by the paper as a limit ("more than 30,000 per second", the flux faster than the apparatus) is used at its stated number: the
                  strength read from it can only be too low, never too high.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). A rate the paper itself calls a limit has no variance.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative
predictions. The share of the signal that belongs to the protein, (release - control) / release, is judged here as a degree of the criterion release_over_control
and not given to the sheet as an attributed/total pair.
qualitative_effect  only when NO effect is stated: statement 'interaction_detected' (read "transport detected"), 'interaction_not_detected' (read "transport not
                  detected") or 'interaction_not_stated', with the refs of the fact transport_detected_above_control that states it; direction_field_support is
                  the quote support of that one fact (None when it is not stated). A stated effect fixes the direction and the statement is then not used. A result
                  stated in words alone counts less than a measured one (the contract's stated_strength); that is not done here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    protein_free_vesicle_control
membrane_system            protein_free_vesicle_control + vesicle_integrity
attribution_supported      release_over_control + protein_amount_in_vesicles
calibration_applicability  probe_calibration
transport_endpoint         detergent_reference + time_resolution
transport_driving_force    ionophore_control + gradient_defined
transport_specificity      second_ion_control + probe_selectivity
sampling_basis             replicates
assertion_relevance        native_substrate
condition_scope            purified_protein
variance_correspondence    supported only when a variance was computed
Not selected: measurement_identity, matrix_interference, transport_response_model (optional for a rate or a fold: a vesicle flux of this type states no
concentration series).
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value,
falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states
nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet
criterion that is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of
a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable
members are dropped; a sheet criterion whose members are all not_applicable is not selected.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the purified protein stock (or the culture the native vesicles come from) is
analyte_preparation_ref and the reconstituted vesicle batch is immobilized_preparation_ref; surface_ref stays None (no electrode holds the membrane: the bath
electrode is not a sample). All four stay None until a passage can state them. Qualitative statements keep the existing vocabulary. Direction and strength of a
stated rate: literature_transport_response_direction (larger is stronger, TRANSPORT_STRENGTH_ANCHORS); controls, blanks and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value
misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is
EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
NET_SHARE_FULL 0.9 -> NET_SHARE_ZERO 0, judged linearly on the net share (release - control) / release.
  Q1 a release that the protein-free vesicles show nearly as well: the leak of the vesicles, a dye or an electrode drift and not the transporter. Q2 general
  practice: a protein-free control is run beside every reconstituted flux, and its leak is expected to be small against the signal (leak of well-made
  liposomes is slow, a few percent over the assay; from memory, not verified); lab- and lipid-specific. Q3 relative to the paper's own control at the same time, which the grader records beside the release. Q4 a control at a
  tenth of the signal changes the net flux by a tenth; at the signal itself the net flux is nothing: the net share is the share of the signal that belongs to
  the protein, so it is judged linearly in itself (an additive proportion), full from 0.9 (the control at most a tenth of the signal) to 0 at a control as large
  as the signal (no better than the leak: conflicting, the paper's own control shows no transport). The degree only lowers the weight; the direction comes from
  the effect or the statement. Q5 the same idea as the empty-vector and protein-free background of the other transport types, and as the signal-over-own-control
  limit of the binding assays.
LAG_FULL 0.1 -> LAG_ZERO 1.0, judged linearly on the product k * t of the stated rate constant and the response time.
  Q1 a rate constant that is the lag of the electrode (or dye, or mixing) and not the release. Q2 physics: the response of the probe is a first-order lag with
  time constant t, so the release seen through it has an apparent rate constant k_app = 1 / (1 / k + t) and the true k is k_app / (1 - k_app t); the stated
  value is too low by the fraction k_app * t, which is the quantity judged; in the fluoride channel work (Fluc) the release was faster than the electrode's response of about one second and
  was therefore reported as a limit (inventory section 3.5, from memory, not verified). A pure delay (dead time) does not bias k, so reading a dead time as a lag is the
  conservative side. Q3 relative to the paper's own rate constant and its own response time, both recorded by the grader. Q4 a stated rate constant
  that is 10 percent low (k t = 0.1) is full agreement: it is within ordinary rate-constant scatter; at k t = 1 the stated rate is entirely the lag, the true
  rate is unbounded and the stated number says nothing (no agreement, conflicting); between them the degree falls linearly in the bias, which is the error
  itself. A paper that says the flux is only a limit is supported without a degree (fact flux_faster_than_apparatus_response yes). Q5 the same idea as the
  bias judgements of the other assays (a degree linear in the error that the departure gives).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a flux from one batch of vesicles, whose preparation-to-preparation spread (reconstitution efficiency, lipid, orientation) is unseen. Q2 general
  (triplicate practice, independent reconstitutions). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5
  exactly the shared replicate rule.
Facts with no number (the protein-free control, the second ion, the probe selectivity, the ionophore, the gradient, the detergent reference, the calibration,
the vesicle integrity, the protein amount, the native substrate and the purified protein): the paper's own statement decides; yes is supported, no is
conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the amount of the protein per vesicle (the Poisson share of empty
vesicles, 30 to 50 percent in a typical reconstitution, makes a release below 100 percent normal; it is not leak and no field asks it); the temperature and the
pH (the claim carries no condition, and the identity block records the temperature); the release time (it is read beside both shares, and the grader keeps it
with their refs).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this
assay, decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? How much of a trapped (or added) ion or substrate crosses the membrane of vesicles, in real time, as a fraction of
  the pool that a detergent releases (relative to its own total) and, with a calibrated probe, as an amount per time: an absolute rate constant of a clean
  defined system, but a per-transporter or per-mg rate also needs the protein amount in the vesicles.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: the ranges of transporter and channel turnover are known (the anchors
  are built on them), and a reconstituted flux above protein-free vesicles is the standard evidence that a purified protein moves an ion or substrate. The size
  of a rate is not trusted without the control and the calibration.
  What does an unstated control or calibration do to what the number means? An unstated protein-free control is the main gap: leak and nonspecific release
  would then be counted as transport (a possible false positive); an unstated second ion or probe selectivity leaves open that the electrode answers to
  something else (chloride on a fluoride electrode, a pH change for an ion); an unstated calibration is benign in typical practice (standard additions are
  usual) and changes the size, not the existence; an unstated response time can make a fast rate a lag, but the release fraction remains evidence.
  If we assume it is fine and are wrong, how badly does the score mislead? A background counted as transport (wrong direction for a weak result) or a species
  misidentified; less severe than a pull-down band (a pure artefact), more than a KD (a magnitude only).
  Consistent with KD? The default 0.80 is under the activity anchor spectro_direct 0.85 (a vesicle flux has more ways to be wrong: reconstitution, orientation,
  probe response, counter-ion limits); the sheet criteria that guard against a false transport or the wrong species are lower, the benign ones are higher.
  default 0.80. background_alternatives 0.70 (the protein-free vesicle is what separates transport from leak). transport_specificity 0.70 (the species and the
  selectivity of the probe). transport_endpoint 0.75 (the response time and the detergent total decide whether a rate is a rate). calibration_applicability
  0.85 and sampling_basis 0.90 (benign when unstated: standard additions and triplicates are usual). membrane_system, attribution_supported,
  transport_driving_force, assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE, TRANSPORT_KIND_OF_QUANTITY
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_vesicle_probe_flux_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('protein_free_vesicle_control',), 'membrane_system': ('protein_free_vesicle_control', 'vesicle_integrity'),
                'attribution_supported': ('release_over_control', 'protein_amount_in_vesicles'), 'calibration_applicability': ('probe_calibration',),
                'transport_endpoint': ('detergent_reference', 'time_resolution'), 'transport_driving_force': ('ionophore_control', 'gradient_defined'),
                'transport_specificity': ('second_ion_control', 'probe_selectivity'), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_substrate',), 'condition_scope': ('purified_protein',)}
NET_SHARE_FULL = 0.9  # EXPERT_REVIEW, owner to confirm: the share of the release that belongs to the protein, (release - control) / release; at 0.9 the protein-free control is at most a tenth of the signal (leak of well-made liposomes is slow; from memory, not verified); full agreement from it.
NET_SHARE_ZERO = 0.0  # EXPERT_REVIEW, owner to confirm: a control as large as the release of the protein vesicles leaves no net transport (no agreement, conflicting: the paper's own control shows nothing above the leak); falls from NET_SHARE_FULL linearly in the net share, an additive proportion.
LAG_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: the stated rate constant times the response time of the apparatus is the fraction by which the stated rate is too low (a first-order lag of the probe: k_app = 1 / (1 / k + t)); 0.1 is a tenth, within ordinary rate-constant scatter; full agreement up to it. From memory of the physics, not verified.
LAG_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: at k t = 1 the stated rate is entirely the lag of the probe and the true rate is unbounded (no agreement, conflicting); falls from LAG_FULL linearly in the bias k t, which is the error itself. A dead time that is a pure delay does not bias k, so this reads it on the conservative side.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments (independent vesicle preparations or reconstitutions, or days); full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (60 s is 1 min; 1 umol is 1000 nmol; 1 pmol is 1e-3 nmol; a fold is the dimensionless ratio itself); the stated number is the paper's.
    'turnover': ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
    'normalized_rate': ('nmol/min/mg', {'pmol/min/mg': 1.0e-3, 'nmol/min/mg': 1.0, 'umol/min/mg': 1.0e3}),
}
KIND_WITHOUT_EFFECT = 'transport_rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_vesicle_flux_has_no_matrix_recovery_measurement', 'attributed_signal': 'the_net_share_over_the_protein_free_control_is_judged_as_a_degree_not_given_as_a_sheet_signal',
                'total_signal': 'the_net_share_over_the_protein_free_control_is_judged_as_a_degree_not_given_as_a_sheet_signal',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_vesicle_flux_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_vesicle_flux_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "transport detected" / "transport not detected" / "transport not stated" for this class
RATE_QUANTITIES = ('turnover', 'normalized_rate')   # the effects that a flux stated as a limit makes a limit (the fold is a ratio of two fluxes and is not)


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


def _judge_release_over_control(native):
    net_share = (native['release_percent'] - native['control_release_percent']) / native['release_percent']
    return _graded(native['release_over_control_refs'], (net_share, NET_SHARE_FULL, NET_SHARE_ZERO))


def _judge_time_resolution(native):
    lag_bias = native['rate_constant_per_s'] * native['dead_time_s']      # the fraction by which the stated rate constant is too low, see LAG_FULL
    return _graded(native['time_resolution_refs'], (lag_bias, LAG_FULL, LAG_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('release_over_control', 'release_over_control_recorded_for_the_sheet'): _judge_release_over_control,
          ('time_resolution', 'time_resolution_recorded_for_the_sheet'): _judge_time_resolution,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_vesicle_probe_flux_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][quantity + '_spread']
    kind = native['spread_kind']
    if quantity in RATE_QUANTITIES and native['flux_bound']:
        return None, 'rate_is_stated_as_a_limit_and_has_no_spread', []
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


def convert_transport_vesicle_probe_flux(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_transport_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_transport_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = TRANSPORT_KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_vesicle_probe_flux_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'transport_response', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'transport_vesicle_probe_flux', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of transport above its protein-free vesicles fixes the direction (None when it states none)
        result['qualitative_effect'] = {'statement': STATEMENT[native['transport']], 'support_refs': list(native['transport_refs'])}
        result['direction_field_support'] = native['transport_support']
    return result
