"""Coupling_isotope_label converter: turns the grader's result into what the A105 reaction_coupling sheet takes.

Hand-built, private to coupling_isotope_label, deterministic. Input: the result of grade_coupling_isotope_label. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'reaction_coupling'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet
component that an isotope-label experiment cannot honestly fill, the reason it stays null. DRAFT 2026-11-22, owner to correct. It is a type of the
reaction_coupling class (class core: A105_REACTION_COUPLING_INVENTORY.md sections 2, 4 to 6; direction: literature_reaction_coupling_direction.py).

Quantities filled
-----------------
effect            ONE stated share, as a productive fraction in the anchor unit 'fraction': the label incorporation (the share of the product that carries the
                  label of the claimed source) or, when only a double label is stated, the label retention (the share of the second label that is transferred).
                  The label incorporation is first (EFFECT_ORDER): it counts the product molecules themselves; the retention is a ratio of two counts. A percent is
                  divided by 100 (exact, FIXED_BY_DEFINITION); the value is the paper's, only its unit spelling changes. quantity_kind of the extraction is
                  'productive_fraction', which the class direction function reads against COUPLING_STRENGTH_ANCHORS (noise end 0.01, strong end 0.9). The label share is
                  read as the productive fraction of the label: the share of the product whose atom came from the claimed source. No coefficient is applied: the
                  atoms the reaction puts in are judged by the label_stoichiometry criterion, not multiplied in.
effect_variance   variance of that effect, in 'fraction_squared', only when the passage's spread of THAT quantity allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n and only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees
                  of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated: the paper's own statement of whether it found the label of the claimed source in the product above its control,
                  as 'interaction_detected' (read "label flow from the claimed source into the product detected"), 'interaction_not_detected' (read "no label found in
                  the product above the control or detection limit") or 'interaction_not_stated', with the refs of the one fact it comes from (label_detected_in_product).
                  direction_field_support is the quote support of that same fact (None when it is not stated: no direction). A stated effect fixes the direction and
                  its own support; the statement is then not used. A result in words alone counts less than a measured one (literature_row_contract.stated_strength).

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
attribution_supported       unlabelled_control + back_exchange_control + label_position
background_alternatives     spontaneous_labelling_control + control_label_level
product_identity            product_identity
calibration_applicability   label_purity + natural_abundance_correction
stoichiometry               label_stoichiometry
matched_windows             matched_runs
assertion_relevance         native_reaction
condition_scope             purified_enzyme
sampling_basis              replicates
variance_correspondence     supported only when a variance was computed
Not selected, and why: reporter_specificity (no reporter chemistry stands between the label and the readout; the mass spectrometer or the counter reads the product
itself: the class note's 'not_applicable' for a type with no reporter; no grader criterion invented for it), measurement_identity and matrix_interference (no grader
criterion for them in this draft: ion suppression and an isobaric co-eluting ion are real but are not statements papers make in a form a quote can carry).
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good value,
falling linearly on the scale the physics gives to zero at a researched no-longer-meaningful value (never a step), unknown when the paper states nothing, never
conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper's own numbers show against the standard). A sheet criterion that is
supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion
and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped.

How the class decisions apply here (2026-11-22, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (nothing
immobilized, no surface); the labelled and the unlabelled run come from one preparation, so they are one dependence unit. Direction and strength of a stated share:
literature_reaction_coupling_direction (a larger share is stronger; the productive fraction anchors). Controls, blanks, the atom count and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and
whether the shape fits, Q5 consistency with the other types). EVERY literature citation below is from memory and NOT verified; every number is EXPERT_REVIEW, owner to
confirm. This is the least certain type of the class: nothing like it was found in the places searched, and every value is the drafter's reasoning from the physics of
isotope labelling and mass spectrometry.
-----------------------------------------------------------------------------------------------------------------------------------
LABEL_PURITY_FULL_PERCENT 95 -> LABEL_PURITY_ZERO_PERCENT 10, judged on the amplification 1 / purity.
  Q1 a labelled source so dilute that the labelled product cannot be told from the natural heavy isotope, or whose unlabelled share is large enough that an
  unlabelled product looks like "no flow". Q2 general: commercial 18O2 gas and H2 18O are sold at about 95 to 99 atom percent, 13C and 15N substrates at 98 to 99
  (supplier catalogues, from memory); cheap 18O water of 10 to 50 percent is used when the label is cheap to dilute (from memory). The natural abundance of the heavy
  isotopes is 0.2 percent for 18O, 1.1 percent for 13C and 0.4 percent for 15N, so a molecule of 20 carbons has a natural M+1 peak of about 22 percent of M
  (isotope tables; from memory; Fernandez et al. 1996, J Mass Spectrom 31:255, on the correction, from memory). Q3 absolute (an atom percent), and the grader records the
  paper's own. Q4 a share of the product read from the mass spectrum is the true share times the purity, so the correction divides by the purity and the error of the
  corrected share goes as 1 / purity: 1.05 at 95 percent, 2 at 50, 10 at 10 percent. The degree is linear in that amplification between the two ends (1 at 95 percent,
  0.89 at 50, 0.56 at 20); at or beyond 10 percent (an error amplification of ten, a label within reach of the natural abundance of a large molecule) the label no longer
  separates (conflicting). Q5 the same kind of scale as the other assays' bias-linear ramps (the share consumed and the absorbance in spectro_direct).
ATOM_DEVIATION_FULL 0.10 -> ATOM_DEVIATION_ZERO 0.50, judged on |atoms found / atoms expected - 1|.
  Q1 a label count that does not fit the reaction the paper claims: two 18O atoms in a product of a monooxygenase, one in a product of a dioxygenase, or one 18O from
  water where the claimed reaction takes its oxygen from O2. Q2 general: the label atoms put in by a reaction are whole numbers fixed by its mechanism (monooxygenase one
  atom of O2, dioxygenase two, hydrolase one from water; Hayaishi et al. 1955, J Am Chem Soc 77:5450 and Mason et al. 1955, from memory); a mean over labelled molecules
  can be a little off a whole number (mixed labelled sources, partial exchange). Q3 relative to the paper's own account (the grader records both numbers). Q4 a deviation
  of 0.10 or less is inside what label purity and natural-abundance correction leave in a mean count (5 to 10 percent), full agreement; half an atom off a one-atom
  account (or one atom off a two-atom account) is a different reaction (no agreement, conflicting); linear in the relative deviation between. Q5 a count against its own
  expectation is not met elsewhere in the draft; the relative deviation is the plain scale of it.
CONTROL_OVER_TEST_FULL 0.05 -> CONTROL_OVER_TEST_ZERO 1.0, judged linearly on the control label over the test label.
  Q1 label that reaches the product without the enzyme (spontaneous exchange of a carbonyl oxygen with the labelled water, a non-enzymatic route): the "flow" is the
  background. Q2 general: with no subtraction the test share is too large by the control share, so the relative bias of the test share is the control over the test;
  isotopic ratio measurement by mass spectrometry reaches a few percent (from memory), so 5 percent is the level a control cannot be told from measurement noise. Carbonyl
  oxygens exchange with water on the scale of minutes to hours at neutral pH and faster in acid (from memory), so this is a common failure of 18O-water experiments.
  Q3 relative to the paper's own test, which the grader records. Q4 at a control as large as the test (ratio 1) there is no enzyme-dependent label (no agreement,
  conflicting: the paper's own numbers); linear because the bias is the ratio itself. Q5 the same signal-over-control idea as the rate over its control in spectro_direct,
  put as the control's share of the signal.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a label share from one experiment, whose preparation-to-preparation and gas-handling spread is unseen (18O2 and 18O-water work is also costly, and one run is common).
  Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the unlabelled control, the back-exchange control, the label position, the no-enzyme and inactive-enzyme controls, the identification by the mass
shift, the natural-abundance correction, the matched runs, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is
conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the label share itself beyond the effect scale (it IS the effect, graded by
the direction function); the mass resolution of the instrument (the form keeps no number a passage states for it); the readout and the label source (recorded for the
reviewer, a choice carries no span after the merge).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method,
decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The share of the product molecules that carry the label of the claimed source: an absolute fraction read from a ratio of ion
  intensities (or counts) in one measurement, so it needs no external calibration; but it shows the ORIGIN of an atom, not how much of the consumed partner ended in the
  product (the most indirect type of the class).
  Is there a reference range we would trust if the paper stated less? Partly: the atoms a reaction puts in are fixed by its mechanism and commercial labels are of
  known purity (95 to 99 atom percent), so an unstated purity or count is benign; but whether the label came through the claimed reaction depends on controls a paper
  may not state.
  What does an unstated control do to what the number means? An unstated unlabelled run or purity is benign (the mass shift itself shows the label). An unstated
  back-exchange control or no-enzyme control is the dominant false positive of an 18O-water experiment (a carbonyl exchanging with the solvent looks like flow), so these
  are a real gap. An unstated product identification by the mass shift leaves open that the shifted ion is another molecule.
  If we assume it is fine and are wrong, how badly does the score mislead? An exchange artefact counted as flow gives a wrong direction for the origin of the atom; less
  severe than a pull-down band (a pure artefact) and more than a KD (a magnitude only).
  Consistent with KD? The default 0.75 is below the KD anchor 0.90 and below the class draft near 0.8: the readout is absolute but the claim it supports is indirect.
  default 0.75. attribution_supported 0.65 (the exchange, unlabelled and position controls are what turn a mass shift into a flow through the claimed reaction).
  product_identity 0.70 (a shifted ion without a standard can be another molecule). calibration_applicability 0.85 and sampling_basis 0.85 (benign when unstated:
  commercial labels are of known purity and correction is usual in modern isotopologue analysis; triplicates are usual). matched_windows 0.80: unlike the two-sided
  types of the class, no ratio of two measurements depends on it; the labelled and unlabelled run are paired by design and the isotopic ratio is read within one
  spectrum, so an unstated match is benign. background_alternatives 0.75 and the others take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_coupling_isotope_label_converted_v1'
CRITERIA_MAP = {'attribution_supported': ('unlabelled_control', 'back_exchange_control', 'label_position'),
                'background_alternatives': ('spontaneous_labelling_control', 'control_label_level'), 'product_identity': ('product_identity',),
                'calibration_applicability': ('label_purity', 'natural_abundance_correction'), 'stoichiometry': ('label_stoichiometry',),
                'matched_windows': ('matched_runs',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
LABEL_PURITY_FULL_PERCENT = 95.0  # EXPERT_REVIEW, owner to confirm: commercial 18O2 gas, H2 18O and 13C or 15N substrates are sold at about 95 to 99 atom percent (supplier catalogues, from memory, not verified); full agreement from it.
LABEL_PURITY_ZERO_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at 10 atom percent the corrected label share is amplified tenfold (1 / purity) and a label sits within reach of the natural M+1 peak of a large molecule (about 22 percent for 20 carbons, from memory): no agreement; the degree is linear in the amplification 1 / purity from the full end to here.
ATOM_DEVIATION_FULL = 0.10  # EXPERT_REVIEW, owner to confirm: the mean label atoms of a labelled product molecule may differ from the paper's account by this relative amount (label purity and natural-abundance correction leave 5 to 10 percent); full agreement up to it.
ATOM_DEVIATION_ZERO = 0.50  # EXPERT_REVIEW, owner to confirm: half an atom off a one-atom account, or one off a two-atom account, is a different reaction (no agreement, conflicting); the degree is linear in the relative deviation between this and ATOM_DEVIATION_FULL.
CONTROL_OVER_TEST_FULL = 0.05  # EXPERT_REVIEW, owner to confirm: a control label of at most this share of the test label is within the few-percent measurement error of an isotope ratio by mass spectrometry (from memory, not verified); full agreement up to it.
CONTROL_OVER_TEST_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a control as large as the test leaves no enzyme-dependent label (no agreement, conflicting); the degree is linear in the ratio, which is the relative bias of an unsubtracted test share.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
EFFECT_ORDER = ('label_incorporation', 'label_retention')   # EXPERT_REVIEW, owner to confirm: the effect is the first stated of these: the share of the product molecules that carry the label counts the product itself; the retention of a second label is a ratio of two counts and is read only when the first is not stated.
SPREAD_OF = {'label_incorporation': 'label_incorporation_spread', 'label_retention': 'label_retention_spread'}
UNIT_FACTORS = {'fraction': 1.0, 'percent': 1.0 / PERCENT_PER_FRACTION}   # FIXED_BY_DEFINITION: exact conversion of a share to the anchor unit 'fraction'; the stated number is the paper's.
ANCHOR_UNIT = 'fraction'
KIND_OF_EFFECT = 'productive_fraction'   # the quantity_kind (QUANTITY_KINDS['reaction_coupling']) of the effect; literature_reaction_coupling_direction.COUPLING_QUANTITY_OF_KIND reads it back
KIND_WITHOUT_EFFECT = 'productive_fraction'   # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'an_isotope_label_flow_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_label_share_is_not_stated_as_two_signals', 'total_signal': 'a_label_share_is_not_stated_as_two_signals',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_isotope_label_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_isotope_label_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "label flow detected" / "not detected" / "not stated" for this class


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


def _judge_purity(native):
    # the error of the corrected label share goes as 1 / purity: judged linearly in the amplification
    amplification = lambda percent: PERCENT_PER_FRACTION / percent
    return _graded(native['label_purity_refs'], (1.0 / native['label_purity_fraction'], amplification(LABEL_PURITY_FULL_PERCENT), amplification(LABEL_PURITY_ZERO_PERCENT)))


def _judge_atoms(native):
    return _graded(native['atoms_refs'], (abs(native['atoms_found_over_expected'] - 1.0), ATOM_DEVIATION_FULL, ATOM_DEVIATION_ZERO))


def _judge_control(native):
    return _graded(native['control_refs'], (native['control_over_test'], CONTROL_OVER_TEST_FULL, CONTROL_OVER_TEST_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('label_purity', 'label_purity_recorded_for_the_sheet'): _judge_purity, ('label_stoichiometry', 'label_atoms_recorded_for_the_sheet'): _judge_atoms,
          ('control_label_level', 'control_label_recorded_for_the_sheet'): _judge_control, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated share as an effect operand in the anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point':
        return None
    return _operand(operand['value'] * UNIT_FACTORS[operand['unit']], ANCHOR_UNIT, 'coupling_isotope_label_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][SPREAD_OF[quantity]]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, SPREAD_OF[quantity] + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * UNIT_FACTORS[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_coupling_isotope_label(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in EFFECT_ORDER}
    chosen = next((quantity for quantity in EFFECT_ORDER if stated[quantity] is not None), None)
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if chosen is None:
        null_components['effect'] = 'no_label_share_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        effect = stated[chosen]
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_EFFECT, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT + '_squared', 'coupling_isotope_label_' + chosen + '_variance:' + ref, variance_refs, 'derived', SPREAD_OF[chosen])
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'reaction_coupling', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'coupling_isotope_label', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated share: the experiment's stated yes/no result stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['label_flow']], 'support_refs': list(native['label_flow_refs'])}
        if native['label_flow'] is not None:
            result['direction_field_support'] = native['label_flow_support']      # the support class of the fact label_detected_in_product, the one field the statement is derived from
    return result
