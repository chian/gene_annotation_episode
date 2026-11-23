"""Coupling_electron_balance converter: turns the grader's result into what the A105 reaction_coupling sheet takes.

Hand-built, private to coupling_electron_balance, deterministic. Input: the result of grade_coupling_electron_balance. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'reaction_coupling'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and
for every sheet component that an electron balance cannot honestly fill, the reason it stays null. A DRAFT of the reaction_coupling class (2026-11-22);
every number is EXPERT_REVIEW, owner to confirm, and every literature figure is from memory, not verified.

Quantities filled
-----------------
effect            ONE quantity in the unit 'fraction', quantity_kind 'productive_fraction' (the class's first effect quantity): the share of the delivered
                  electrons recovered in the product. It is the stated productive fraction (a percent divided by 100, exact), or, when the passage states no
                  share but states the electrons delivered, the product formed and the electrons per product, the electrons per product times the product
                  over the electrons delivered (exact arithmetic of the paper's own numbers, origin 'derived'; inventory section 6 and open question 3,
                  owner to confirm). literature_reaction_coupling_direction.coupling_direction_and_ratio reads it.
effect_variance   variance of a STATED share, in fraction_squared, only when the passage's spread allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees of
                  freedom). A worked-out share has no stated spread, so no variance.
recovery          the stated recovery of a product standard, as a fraction, when stated.
attributed_signal and total_signal   the electrons recovered in the product and the electrons delivered, both in umol, when the three amounts are stated;
                  the sheet then forms their ratio itself (its attributed_fraction cell).
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO share can be stated or worked out: the statement is 'interaction_detected' (read "coupled product formation detected"),
                  'interaction_not_detected' (read "no product formed above the paper's own control or detection limit") or 'interaction_not_stated', taken
                  from the fact product_detected_from_electrons, with its refs; direction_field_support is the support of that one fact. A result stated in
                  words alone counts less than a measured one (stated_strength of the contract); that is not redone here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity       both_sides_stated
calibration_applicability  delivery_calibration + product_calibration + standard_recovery
matrix_interference        headspace_accounting
background_alternatives    no_enzyme_control + background_electrons
attribution_supported      inactive_enzyme_control
product_identity           product_identity
stoichiometry              electrons_per_product_stated + electron_closure
matched_windows            matched_windows
reporter_specificity       oxygen_excluded + mediator_bypass    (the "reporter" of this type is the electron carrier: what else takes the electrons)
assertion_relevance        native_electron_carrier
condition_scope            purified_enzyme
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES
maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at
the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics gives (never a step), unknown
when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against
the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref; the keys stay as the record gives
them (all None, no passage states a preparation reference). Direction and strength of a stated share: literature_reaction_coupling_direction (larger is
stronger, productive_fraction anchors 1 percent and 90 percent); controls, blanks and the rest lower the WEIGHT only. A share above 1 is read at the strong end
by the direction and is judged here (electron_closure).

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong
value misleads and whether the shape fits, Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
BACKGROUND_FULL_SHARE 0.10 -> BACKGROUND_ZERO_SHARE 0.90, judged on the log of the net share 1 - b (b the background over the electrons delivered).
  Q1 the electrons that reach the product or the donor without the enzyme (an electrode making H2 on its own, a reductant reducing the mediator, the
  donor oxidised by chemistry) counted as the enzyme's. Q2 general: a blank under about a tenth of the signal is subtracted without loss (inventory
  section 4, from the activity-assay practice, from memory). Q3 relative to the paper's own delivered electrons, which the grader records: right.
  Q4 the net electrons are (1 - b) of the delivered ones, and the error of the net from an error in the blank grows as b / (1 - b): about 0.11 at b = 0.1,
  1 at 0.5, 9 at 0.9. A logarithmic scale in the net share makes each loss of net signal by the same factor cost the same; at 0.9 the net is a tenth of the
  signal and the balance is mostly the blank (conflicting). Q5 the same idea as the no-substrate share of the class core: full at about a tenth, zero when
  the blank is the signal; the zero end 0.9 and not 1 because the log of the net share has no value at 1.
CLOSURE_FULL 1.10 -> CLOSURE_ZERO 1.50, judged on the electron recovery above 1 (linear). A recovery at or below 1 is not judged here (a low share is a
  weak result, which the strength scale already reads, not an invalid one).
  Q1 more electrons found in the product than were delivered cannot be: it shows an electron source that was not counted (carry-over reductant, a
  mediator pool, the electrode, an uncorrected gas standard). Q2 general: the product (gas chromatography of H2) and the electron count (a titration or a
  coulometer) each carry an error of about 5 percent, from memory, so about 10 percent over 1 is the measurement's own error; the Bcd/EtfAB case (H2 depends on
  the viologen, PMC2223550) is the mediator-bypass kind of error the criterion catches. Q3 relative to what is physically possible, 1; right. Q4 additive error
  of two counts: linear; 1.5 means a third of the product electrons have no counted source (conflicting). Q5 the class direction reads a share above 1 at the
  strong end and leaves the diagnosis to the criteria (inventory open question 4): this is that criterion.
RECOVERY_FULL_FACTOR 1/0.9 -> RECOVERY_ZERO_FACTOR 2.0, judged on the log of the factor f = max(r, 1/r) of the recovery r of a product standard.
  Q1 a product measurement that does not give back a known amount (gas lost from the headspace, a detector off the standard). Q2 general: a standard
  recovered between 0.9 and 1.1 is the usual acceptance of a quantitative gas or chromatographic method (inventory section 4, from memory). Q3 relative to
  the amount put in, which the paper states as a recovery: right. Q4 the error multiplies the efficiency by r, so the scale is the log of the factor and a
  recovery of 0.5 or 2 doubles or halves every share (conflicting); 0.9 and 1.1 both give full agreement (1.1 is 1/0.909). Q5 a log-ratio ramp like the
  fold gaps of the binding assays.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a share from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a
  mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the calibrations, the headspace, the oxygen and mediator exclusions, the product identity, the matched windows, the
carrier and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to
soften. NOT judged, and why: the electrons per product (the paper's own stoichiometric account; a wrong one would show as a share far from 1, which
electron_closure reads); the pH and the temperature (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this
type, first DRAFT 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The share of the delivered electrons found in the product: a dimensionless number with a physical bound
  (1), absolute, but each side needs its own calibration (the electron count and the product amount).
  Is there a reference range we would trust if the paper stated less? Partly: the electrons per product of common products are textbook (2 per H2), and
  well-closed balances run near 100 percent, so a stated share is readable; but a reference range says nothing about WHERE the electrons went.
  What does an unstated control or calibration do to what the number means? An unstated gas standard or titrant standardisation is usually benign
  (routine and the share lands near the truth, off by a factor); an unstated no-enzyme blank, mediator-bypass check or oxygen exclusion is the dominant
  false positive of the method: the electrons can reach the product by the mediator or the electrode with no help from the enzyme (Bcd/EtfAB: the H2
  rate fell from 5 to 0.02 umol/min/mg without the viologen), and then the share is real but not the enzyme's.
  If we assume it is fine and are wrong, how badly does the score mislead? A bypass or a background counted as the enzyme's coupling: the direction is wrong,
  not only the size; worse than a KD (a size) and about as bad as a pull-down band.
  Consistent with KD (0.90) and spectro_direct (0.85)? The default is below both (0.75): two calibrations, and the controls that separate the enzyme from a
  bypass are often unstated; the criteria that guard against a false coupling are lower, the benign ones are near the anchor.
  default 0.75. background_alternatives 0.65, reporter_specificity 0.60 (the bypass and side-consumption gaps above). matched_windows 0.65 (a share from a
  product taken over one interval and electrons over another is uninterpretable). attribution_supported 0.70. product_identity 0.85 (H2 by gas
  chromatography identifies itself). stoichiometry 0.85, calibration_applicability 0.80, matrix_interference 0.80, measurement_identity 0.80 (routine when
  unstated). sampling_basis 0.90. assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_electron_balance_criteria import PERCENT_PER_FRACTION
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_coupling_electron_balance_converted'
CRITERIA_MAP = {'measurement_identity': ('both_sides_stated',), 'calibration_applicability': ('delivery_calibration', 'product_calibration', 'standard_recovery'),
                'matrix_interference': ('headspace_accounting',), 'background_alternatives': ('no_enzyme_control', 'background_electrons'),
                'attribution_supported': ('inactive_enzyme_control',), 'product_identity': ('product_identity',),
                'stoichiometry': ('electrons_per_product_stated', 'electron_closure'), 'matched_windows': ('matched_windows',),
                'reporter_specificity': ('oxygen_excluded', 'mediator_bypass'), 'assertion_relevance': ('native_electron_carrier',),
                'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
BACKGROUND_FULL_SHARE = 0.10  # EXPERT_REVIEW, owner to confirm: the no-enzyme background up to this share of the electrons delivered is subtracted without loss (blank under about a tenth of the signal, from memory); full agreement up to it.
BACKGROUND_ZERO_SHARE = 0.90  # EXPERT_REVIEW, owner to confirm: at this share the net electrons are a tenth of the signal and the balance is mostly the blank (no agreement); the degree falls linearly in the log of the net share 1 - b, because the error of the net grows as b / (1 - b); not 1 because the log has no value there.
CLOSURE_FULL = 1.10  # EXPERT_REVIEW, owner to confirm: an electron recovery up to this is within the error of the two counts (gas chromatography of the product and the electron count, about 5 percent each, from memory); full agreement up to it.
CLOSURE_ZERO = 1.50  # EXPERT_REVIEW, owner to confirm: a recovery of 1.5 means a third of the product electrons have no counted source (carry-over reductant, mediator pool, electrode) (no agreement); the degree falls linearly (additive error of two counts) from CLOSURE_FULL.
RECOVERY_FULL_FACTOR = 1.0 / 0.9  # EXPERT_REVIEW, owner to confirm: a product standard recovered within 0.9 to 1.1 is the usual acceptance of a quantitative gas or chromatographic method (from memory); full agreement for a recovery r with max(r, 1/r) up to this (0.9 and 1.1 both).
RECOVERY_ZERO_FACTOR = 2.0  # EXPERT_REVIEW, owner to confirm: a standard recovered at half or at double doubles or halves every share (no agreement); the degree falls linearly in the log of max(r, 1/r) from RECOVERY_FULL_FACTOR, because the error multiplies the share.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
KIND = 'productive_fraction'   # the quantity_kind (QUANTITY_KINDS['reaction_coupling']) of the effect, and of an extraction that fills no effect
UNIT = 'fraction'              # the anchor unit of that kind (literature_row_contract.COUPLING_STRENGTH_ANCHORS)
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "coupled product formation detected" / "no product formed above the control" / "not stated" for this class
NULL_REASONS = {'condition_test': 'no_matched_nuisance_condition_response_in_an_electron_balance_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_electron_balance_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment',
                'effect_degrees_of_freedom': 'no_student_t_model_selected'}
MISSING_REASONS = {'effect': 'no_share_stated_and_not_all_of_electrons_delivered_product_formed_and_electrons_per_product_stated', 'effect_variance': 'no_effect',
                   'recovery': 'no_standard_recovery_stated', 'attributed_signal': 'electrons_delivered_product_formed_and_electrons_per_product_not_all_stated',
                   'total_signal': 'electrons_delivered_product_formed_and_electrons_per_product_not_all_stated'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _judge_background(native):
    share, refs = native['background_share'], native['background_refs']
    if share >= BACKGROUND_ZERO_SHARE:
        return _verdict('conflicting', refs)
    full, zero = math.log(1.0 - BACKGROUND_FULL_SHARE), math.log(1.0 - BACKGROUND_ZERO_SHARE)
    return _verdict('supported', refs, min(1.0, (math.log(1.0 - share) - zero) / (full - zero)))


def _judge_closure(native):
    recovery, refs = native['recovery_fraction'], native['recovery_refs']
    if recovery >= CLOSURE_ZERO:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (CLOSURE_ZERO - recovery) / (CLOSURE_ZERO - CLOSURE_FULL)))      # a recovery at or below 1 is not judged here, it only reaches the full end


def _judge_standard_recovery(native):
    factor, refs = max(native['standard_recovery_fraction'], 1.0 / native['standard_recovery_fraction']), native['standard_recovery_refs']
    if factor >= RECOVERY_ZERO_FACTOR:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (math.log(RECOVERY_ZERO_FACTOR) - math.log(factor)) / (math.log(RECOVERY_ZERO_FACTOR) - math.log(RECOVERY_FULL_FACTOR))))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('background_electrons', 'background_recorded_for_the_sheet'): _judge_background, ('electron_closure', 'closure_recorded_for_the_sheet'): _judge_closure,
          ('standard_recovery', 'standard_recovery_recorded_for_the_sheet'): _judge_standard_recovery, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance in fraction_squared or None, reason or None, refs) of the spread of a STATED share."""
    native = graded['native']
    spread = native['quantities']['productive_fraction_spread']
    kind = native['spread_kind']
    if native['recovery_origin'] != 'reported':
        return None, 'effect_is_worked_out_from_amounts_and_has_no_stated_spread', []
    if spread['status'] != 'point':
        return None, 'productive_fraction_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] / PERCENT_PER_FRACTION if spread['unit'] == 'percent' else spread['value']
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_coupling_electron_balance(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = dict(NULL_REASONS)
    if native['recovery_fraction'] is None:
        null_components['effect'] = MISSING_REASONS['effect']
        null_components['effect_variance'] = MISSING_REASONS['effect_variance']
    else:
        origin = native['recovery_origin']
        quantities['effect'] = _operand(native['recovery_fraction'], UNIT, 'coupling_electron_balance_productive_fraction:' + ref, native['recovery_refs'], origin, 'productive_fraction')
        variance, variance_reason, variance_refs = _variance(graded)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT + '_squared', 'coupling_electron_balance_productive_fraction_variance:' + ref, variance_refs, 'derived', 'productive_fraction_spread')
    if native['standard_recovery_fraction'] is None:
        null_components['recovery'] = MISSING_REASONS['recovery']
    else:
        quantities['recovery'] = _operand(native['standard_recovery_fraction'], UNIT, 'coupling_electron_balance_standard_recovery:' + ref, native['standard_recovery_refs'], 'reported', 'standard_recovery')
    if native['electrons_delivered_umol'] is None:
        null_components['attributed_signal'] = MISSING_REASONS['attributed_signal']
        null_components['total_signal'] = MISSING_REASONS['total_signal']
    else:
        quantities['attributed_signal'] = _operand(native['electrons_in_product_umol'], 'umol', 'coupling_electron_balance_electrons_in_product:' + ref, native['balance_refs'], 'derived', 'electrons_per_product_times_product_formed')
        quantities['total_signal'] = _operand(native['electrons_delivered_umol'], 'umol', 'coupling_electron_balance_electrons_delivered:' + ref, native['balance_refs'], 'reported', 'electrons_delivered')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'reaction_coupling', 'assertion_ref': native['assertion_ref'], 'quantity_kind': KIND, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    converted = {'version': VERSION, 'experiment_type': 'coupling_electron_balance', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']),
                 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantities['effect'] is not None:
        converted['direction_field_support'] = native['recovery_support']      # the support class of the stated share, or the weakest of the three amounts it is worked out from
    else:      # no share: the experiment's stated yes/no result stands, scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['product_detected']], 'support_refs': list(native['product_detected_refs'])}
        if native['product_detected'] is not None:
            converted['direction_field_support'] = native['product_detected_support']      # the support class of the fact product_detected_from_electrons, the one field the statement is derived from
    return converted
