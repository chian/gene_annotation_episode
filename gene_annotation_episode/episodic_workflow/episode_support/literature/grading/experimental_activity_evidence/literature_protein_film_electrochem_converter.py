"""Protein_film_electrochem converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to protein_film_electrochem, deterministic. Input: the result of grade_protein_film_electrochem. Output: the sheet's input
(the 'extraction' grade_assay takes, with assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger
needs, the enzyme's molar mass the direction function needs (always None here: no effect of this type is a specific activity), and for every
sheet component that an electrode experiment cannot honestly fill, the reason it stays null. Draft built 2026-11-22 from the first built type
(spectro_direct); all numbers EXPERT_REVIEW, owner to confirm; every literature citation is from memory and not verified.

Quantities filled
-----------------
effect            ONE quantity in the anchor unit of its quantity: catalytic efficiency kcat/Km (M^-1s^-1), turnover kcat (s^-1) or the catalytic
                  current over the paper's own control (fold). Several may be given; the one used is the best-determined, in the class order
                  ACTIVITY_EFFECT_ORDER (literature_activity_direction.select_activity_effect). A stated value in another unit of the record's
                  vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION). The catalytic current itself (nA, uA) is no
                  effect of the class: the class has no scale for a current, and a current is a rate per area of an electrode, not a rate per enzyme.
                  TURNOVER FROM THE CURRENT. When the paper states no turnover frequency, but states the catalytic current density, the electroactive
                  coverage, the electrons per turnover AND that the coverage was measured on the film (the fact electroactive_coverage_determined is yes),
                  the turnover frequency is the exact consequence of the definition of the current of an enzyme film:
                  kcat = j / (n F Gamma), j the current density (A/cm^2), n the electrons per turnover, F the Faraday constant, Gamma the
                  electroactive coverage (mol/cm^2). It is an operand with origin 'derived', its support is the weakest support of the three
                  values, its refs are theirs, and it carries no variance (no spread is derived from three numbers). A coverage that is only the
                  amount of protein applied is not electroactive and gives no turnover frequency (the fact is then not yes).
effect_variance   variance of the STATED effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null. A derived turnover has none.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
enzyme_mass_g_per_mol   None (the record has no enzyme mass: no effect of this type is a specific activity).
qualitative_effect  only when NO effect is stated or derived and the paper states whether it saw catalytic current above its own control:
                  statement 'interaction_detected' (read "activity detected") or 'interaction_not_detected' (read "activity not detected"), with the
                  refs of the fact that states it and its support as direction_field_support. A stated effect fixes the direction; the statement is
                  then not used.
dependence        the record's preparation keys as given. Mapping decided 2026-11-21 for this type (owner to confirm): the enzyme film's enzyme
                  preparation is immobilized_preparation_ref, the electrode is surface_ref, analyte_preparation_ref stays None (the substrate solution
                  is no preparation).

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   bare_electrode_control + substrate_free_baseline
attribution_supported     substrate_dependence + product_identity
calibration_applicability potential_reference + electrode_area
rate_regime               mass_transport_excluded + steady_state_wave
normalization_basis       electroactive_amount + film_stability
kinetic_model             substrate_range
sampling_basis            replicates
assertion_relevance       native_reaction
condition_scope           purified_enzyme
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS method made
gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the
scale the physics of the method gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or
beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest
degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never
changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are
dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity,
matrix_interference, partner_perturbation) are not selected.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a
wrong value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not
verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
FILM_LOSS_FULL_PERCENT 10 -> FILM_LOSS_ZERO_PERCENT 90, linear in the share of the signal lost.
  Q1 an enzyme film loses enzyme from the electrode (desorption) or activity (inactivation, for example by the potential or the product) while
  the current is recorded, so the current read at the end is lower than the current of the film that was measured at the start, and a rate
  taken from a decaying current is too low and depends on when it was read. Q2 general to protein-film electrochemistry: film loss is the
  well-known first complication of the method, and papers correct for it (a decay of the non-turnover signal, a repeat of the first
  potential, a normalisation to the current at a reference time) or keep the experiment short (Leger and Bertrand 2008 Chem Rev 108:2379;
  Armstrong and co-workers, from memory). The sizes (a few percent to tens of percent over a scan or an experiment) are from memory and are
  lab- and film-specific. Q3 relative to the paper's own current, which the passage states as a share: right. Q4 for a loss that grows
  linearly in time the window-mean current is low by half the final loss f and the current at the end by f, so the bias of the rate is
  proportional to f: the degree is linear in f between the two ends. Full agreement up to 10 percent (a rate low by at most about 5 percent
  on the mean, smaller than the film-to-film spread of coverage that the replicates already carry); no agreement from 90 percent (the film is
  nearly gone, the number is a decaying remainder, a factor of two or more off on the mean: conflicting, what the paper itself shows). A
  loss stated as corrected for is supported (a fact, no number to soften). Q5 the same idea as the other curves: a bias that grows with the
  departure from the researched value; the zero end is nearer to the spectro_direct consumed-substrate zero end (90 percent) than to a cut.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 an apparent Km fitted to too few substrate concentrations to show the hyperbola holds. Q2 general: a saturation curve of about six to
  eight concentrations spanning 0.2 to 10 times the Km (Cornish-Bowden; Copeland; NCBI Assay Guidance Manual), from memory; the exact 6 is a
  judgement. In electrode experiments the current is read at each concentration from one film (a substrate titration) or from several, and
  the apparent Km is the one the current-substrate curve gives (an apparent value that depends on mass transport, which is the
  rate_regime criterion, not this one). Q3 absolute (a count). Q4 the Michaelis-Menten equation has two parameters (Km and the plateau current),
  so two concentrations are used up by the fit and leave no residual degree of freedom (no credit, supported with degree 0, never conflicting);
  each added concentration is one more point the fitted curve must pass through: the degree rises linearly with count - 2. Q5 the same residual
  degree-of-freedom count as spectro_direct and the SPR steady-state KD.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and the plateau current trade off (no saturation) or the curvature is unseen (no low end).
  Q2 general: 0.2 to 10 times the Km (the references above), from memory. Q3 relative to the paper's own Km (the grader records both
  ratios): right. Q4 the current is i / i_max = S / (S + Km), so both ends are judged linearly in the fractional saturation S / (S + Km)
  (1/6 at 0.2 Km, 10/11 at 10 Km; 1/2 at the Km, the zero end of both). A film with a substrate that inhibits at high concentration is not
  seen by this curve and is a limit of it. Q5 working rule d of the SOP: 10 where the plateau is a free amplitude known only by reaching it,
  which is the case for a plateau current whose size depends on the film.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a current from one film, whose film-to-film spread is unseen. Q2 general (triplicate practice); in protein-film electrochemistry the
  electroactive coverage of separately prepared films often varies by tens of percent, so independent films, not repeated scans of one film,
  are the replicates (the criterion's independence fact), from memory. Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same
  sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the bare-electrode and no-substrate controls, the substrate dependence, the product identity, the potential reference,
the electrode area, the exclusion of mass transport, the steady-state wave, the electroactive coverage, the native substrate and the purified
enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften.
NOT judged, and why: the size of the coverage (a thick film slows electron transfer and substrate diffusion, but papers do not state a limit
that is general across enzymes and electrodes; the strength scale reads the turnover it gives); the scan rate and the rotation rate (the facts
steady_state_wave and mass_transport_excluded carry what they are for); the temperature and the pH (the claim carries no condition, and the
identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered
for this method, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The current of an enzyme film at a controlled potential: an electron flow per electrode area. It
  is a rate per enzyme (kcat) only when the electroactive coverage is measured; without it the number is relative to the film.
  Is there a reference range we would trust if the paper stated less (as for KD)? Partly: the range of kcat and kcat/Km of enzymes is known
  (Bar-Even et al. 2011, from memory) and the strength anchors are built on it, but a bare current density has no such range and cannot be
  turned into a rate per enzyme from the passage alone.
  What does an unstated control or calibration do to the number's meaning? An unstated bare-electrode or no-substrate control matters more here
  than in a solution assay: the substrate (or the solvent, protons, oxygen) can be turned over at the electrode or at a contaminant without the
  enzyme, a false catalytic current; an unstated coverage leaves the number relative; an unstated reference electrode shifts the potential by a
  known offset (hundreds of mV between references) and does not make the current meaningless; an unstated rotation leaves a mass-transport
  limited current that reads low but still exists.
  If we assume it is fine and are wrong, how badly does the score mislead? A background current counted as the enzyme's gives a wrong direction
  for a weak current and a wrong magnitude for a strong one; an unmeasured coverage gives a wrong size, not a wrong existence.
  Consistent with KD and with spectro_direct? The default 0.75 is under spectro_direct's 0.85 because the readout is relative unless the
  coverage is given. Criteria that guard against a false activity or a relative number are lower; benign ones are higher.
  default 0.75. background_alternatives 0.65 (the blank separates catalysis from direct electrolysis; a real gap). attribution_supported 0.75
  (the current of a contaminant or of the film's mediator reaction, stated by a substrate dependence in most papers but often left unsaid).
  normalization_basis 0.60 (without the electroactive coverage and the film loss a current is only relative). calibration_applicability 0.85 (a
  reference electrode and an area are benign when unstated: typical practice, a known offset). rate_regime 0.75, sampling_basis 0.85,
  kinetic_model, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import select_activity_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE, SUPPORT_WEAKEST_ORDER
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_protein_film_electrochem_converted_v1'
CRITERIA_MAP = {'background_alternatives': ('bare_electrode_control', 'substrate_free_baseline'), 'attribution_supported': ('substrate_dependence', 'product_identity'),
                'calibration_applicability': ('potential_reference', 'electrode_area'), 'rate_regime': ('mass_transport_excluded', 'steady_state_wave'),
                'normalization_basis': ('electroactive_amount', 'film_stability'), 'kinetic_model': ('substrate_range',), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',)}
FARADAY_C_PER_MOL = 96485.33212  # FIXED_BY_DEFINITION: the Faraday constant, the elementary charge times the Avogadro constant (both exact since 2019), in C/mol.
CURRENT_DENSITY_A_PER_CM2 = {'nA/cm^2': 1.0e-9, 'uA/cm^2': 1.0e-6, 'mA/cm^2': 1.0e-3}  # FIXED_BY_DEFINITION: exact unit conversions to A/cm^2.
COVERAGE_MOL_PER_CM2 = {'pmol/cm^2': 1.0e-12, 'nmol/cm^2': 1.0e-9}  # FIXED_BY_DEFINITION: exact unit conversions to mol/cm^2.
FILM_LOSS_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: up to about 10 percent of the signal lost over the measurement leaves the rate low by about 5 percent on the window mean for a linear decay, less than the film-to-film spread of coverage (Leger and Bertrand 2008, from memory); full agreement up to it.
FILM_LOSS_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent lost the film is nearly gone and the mean rate is low by about 45 percent (a factor of nearly 2) and the end value by a factor of 10: a decaying remainder, not a rate (no agreement); the degree falls linearly in the loss from the full end to here, because the bias of the rate is proportional to the loss.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable current-substrate curve (about six to eight, Cornish-Bowden; Copeland; NCBI Assay Guidance Manual, from memory); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: the Michaelis-Menten equation has two parameters (Km, plateau current), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (the current is 1/6 of the plateau there); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (the current is 10/11 of the plateau); the plateau current is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent films or electrodes; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent films falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.ACTIVITY_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (mM^-1 is 1000 M^-1; uM^-1 is 1e6 M^-1; 60 s is 1 min); the stated number is the paper's.
    'catalytic_efficiency': ('M^-1s^-1', {'M^-1 s^-1': 1.0, 'mM^-1 s^-1': 1.0e3, 'uM^-1 s^-1': 1.0e6}),
    'turnover': ('s^-1', {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}),
    'rate_over_control': ('fold', {'fold': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['activity_rate']) that names the kind of each effect quantity; literature_activity_direction.ACTIVITY_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'catalytic_efficiency': 'catalytic_efficiency', 'turnover': 'turnover', 'rate_over_control': 'rate_ratio'}
KIND_WITHOUT_EFFECT = 'rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'protein_film_electrochem_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_catalytic_current_is_not_an_attribution_fraction', 'total_signal': 'a_catalytic_current_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_protein_film_electrochem_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_protein_film_electrochem_record',
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
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _judge_film_loss(native):
    return _graded(native['film_loss_refs'], (native['film_loss_percent'], FILM_LOSS_FULL_PERCENT, FILM_LOSS_ZERO_PERCENT))


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
JUDGES = {('film_stability', 'film_loss_recorded_for_the_sheet'): _judge_film_loss, ('substrate_range', 'substrate_series_recorded_for_the_sheet'): _judge_series,
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
    return _operand(operand['value'] * factors[operand['unit']], unit, 'protein_film_electrochem_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _turnover_from_current(native, ref):
    """kcat = j / (n F Gamma) from the stated current density, electroactive coverage and electrons per turnover, only when the coverage was measured on the film; else None."""
    names = ('catalytic_current_density', 'electroactive_coverage', 'electrons_per_turnover')
    density, coverage, electrons = (native['quantities'][name] for name in names)
    if native['coverage_determined'] != 'yes' or any(operand['status'] != 'point' for operand in (density, coverage, electrons)):
        return None
    current = density['value'] * CURRENT_DENSITY_A_PER_CM2[density['unit']]
    charge = electrons['value'] * FARADAY_C_PER_MOL * coverage['value'] * COVERAGE_MOL_PER_CM2[coverage['unit']]
    refs = list(dict.fromkeys(r for operand in (density, coverage, electrons) for r in operand['source_refs']))
    support = min((operand['support'] for operand in (density, coverage, electrons)), key=SUPPORT_WEAKEST_ORDER.index)      # the weakest of the three
    return _operand(current / charge, UNIT_FACTORS['turnover'][0], 'protein_film_electrochem_turnover_from_current:' + ref, refs, 'derived', 'catalytic_current_density', support)


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


def convert_protein_film_electrochem(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    if stated['turnover'] is None:
        stated['turnover'] = _turnover_from_current(native, ref)
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_activity_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_activity_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        if effect['origin'] == 'derived':
            variance, variance_reason, variance_refs = None, 'turnover_derived_from_current_has_no_spread', []
        else:
            variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'protein_film_electrochem_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'protein_film_electrochem', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support,
              'enzyme_mass_g_per_mol': None}
    if quantities['effect'] is None and native['activity'] is not None:      # no stated quantity: the paper's own statement of activity above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['activity']], 'support_refs': list(native['activity_refs'])}
        result['direction_field_support'] = native['activity_support']
    return result
