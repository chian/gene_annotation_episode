"""Dialysis converter: turns the dialysis grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_dialysis.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a dialysis
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has a KD (else a Ki). Then the converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the KD in nM (point operand, measurement key dialysis_kd), else the Ki in nM (dialysis_ki), as the radioligand converter takes its constant. A Bmax is not a
                    binding constant and is never the effect.
  effect_variance   variance of that constant, nM_squared, only when the source's spread (kd_spread for a KD, ki_spread for a Ki) allows it: standard_error -> se^2;
                    standard_deviation -> sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has neither a KD nor a Ki (a percent bound, a percent unbound or a fraction bound at one or more concentrations, or a Bmax alone). Then, exactly as the pull-down,
EMSA and SEC converters do (quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the percent bound nor the fraction unbound is put
into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'percent_bound'}):
  statement          'interaction_detected' (binding is observed), 'interaction_not_detected' (binding is stated not to be observed, or the stated percent bound is below the minimum)
                     or 'interaction_not_stated'
  support_refs       the spans of the fact or of the stated fraction that decides it (empty when not stated)
  percent_bound      the percent of the total ligand that was bound (stated, or from the percent unbound, the fraction bound or the fraction unbound), or None
The merger (literature_binding_merger.py) reads 'qualitative_effect' to take such a result into the row's interpretations and its own qualitative block; the
merger's contract is not changed.

Criteria mapping (dialysis criteria -> sheet criteria), declared in CRITERIA_MAP
-------------------------------------------------------------------------------
binding_controls              buffer_only_control + protein_retained + device_adsorption + ligand_stability (the controls that show the ligand crosses the membrane, the protein does
                              not, nothing is lost to the device and nothing is degraded)
binding_regime                equilibrium + ligand_depletion + protein_level + concentration_series + volume_shift (equilibrium, the sites not used up, a protein concentration at which a
                              fraction is measurable, a series that brackets the KD, no volume shift)
binding_parameter_definition  binding_observed + fit_model (what the response is: a bound fraction, and the model of the fit)
calibration_applicability     recovery + free_measured_directly + free_fraction_measurable (the measurement of the free ligand: a mass balance, a direct measurement, a free fraction that is measurable)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). Continuous comparisons are supported with a degree of 1.0 up to (or from) the full-agreement limit, the degree falling linearly
to 0 at the zero-agreement limit, and conflicting at or beyond that limit: equilibrium (time), recovery, device_adsorption, volume_shift (a stated shift), ligand_depletion
(bound over protein), protein_level (protein over KD), free_fraction_measurable (percent unbound) and concentration_series (the lowest and the highest concentration over the KD,
the weaker degree taken). No degree: binding_observed (a detection decision: the percent bound shows binding or it does not, and the qualitative statement follows it, so a
partial credit would contradict it), the salt of volume_shift (supported at the minimum, otherwise unknown), the concentration count of concentration_series and the replicates
(count minimums: conflicting below them; replicates supported when independent is yes, else unknown). A sheet criterion that is supported carries the smallest degree of its members
that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
The qualitative statement, when the fact binding_detected is not stated and a fraction is, is the sheet's reading of the judgement of binding_observed: supported is
'interaction_detected', conflicting (the percent bound below MIN_PERCENT_BOUND) is 'interaction_not_detected', with the refs of the fraction, exactly as before.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree (the
continuous comparisons above); direct leaves it unchanged. Support never changes a status. variance_correspondence takes the weakest support of the
spread (and of the replicate count for a standard deviation).
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the ligand, immobilized_preparation_ref = the protein,
surface_ref = None (a membrane or a device is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import BOUND_FROM

VERSION = 'a105_dialysis_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('buffer_only_control', 'protein_retained', 'device_adsorption', 'ligand_stability'), 'binding_regime': ('equilibrium', 'ligand_depletion', 'protein_level', 'concentration_series', 'volume_shift'), 'binding_parameter_definition': ('binding_observed', 'fit_model'), 'calibration_applicability': ('recovery', 'free_measured_directly', 'free_fraction_measurable'), 'sampling_basis': ('replicates',)}
MIN_PERCENT_BOUND = 5.0  # EXPERT_REVIEW: smallest percent of the total ligand bound that shows binding; below about 5 percent the free and the total concentration differ by no more than the error of the two measurements (a few percent each), so no binding is shown.
MIN_PERCENT_UNBOUND = 1.0  # EXPERT_REVIEW: smallest percent unbound that is a measurable free fraction, for full agreement; below 1 percent the free concentration is near the limit of quantification of the detector and the percent unbound (and so the KD) is not reliable by dialysis.
FREE_FRACTION_ZERO_AGREEMENT_PERCENT = 0.0  # EXPERT_REVIEW: percent unbound at or below which the sheet takes the free fraction as not measurable (conflicting); no free ligand at all; in between the degree rises linearly.
MIN_EQUILIBRATION_H = 4.0  # EXPERT_REVIEW: shortest time (hours) that is taken as reaching equilibrium without a time course, for full agreement; 4 to 6 hours is the usual protocol of rapid equilibrium dialysis for plasma protein binding, and a shorter time is too short for most proteins (large proteins and tight binders need longer).
EQUILIBRATION_ZERO_AGREEMENT_H = 1.0  # EXPERT_REVIEW: time to equilibrium (hours) at or below which the sheet takes the binding as not at equilibrium (conflicting); within an hour a dialysis of a protein and a small ligand is far from equilibrium; in between the degree rises linearly.
MIN_RECOVERY_PERCENT = 80.0  # EXPERT_REVIEW: smallest recovery (percent of the total ligand found in both chambers) of an acceptable mass balance, for full agreement (the usual acceptance is 80 to 120 percent); below it the lost ligand biases the free concentration.
RECOVERY_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: recovery (percent) at or below which the sheet takes the mass balance as failed (conflicting); when half of the ligand is lost the free concentration cannot be trusted; in between the degree rises linearly.
MAX_ADSORPTION_PERCENT = 15.0  # EXPERT_REVIEW: largest nonspecific binding of the ligand to the membrane and the device (percent of the ligand) that does not bias the result, for full agreement; 10 to 15 percent is the usual limit, above it the apparent binding is inflated.
ADSORPTION_ZERO_AGREEMENT_PERCENT = 40.0  # EXPERT_REVIEW: adsorption (percent of the ligand) from which the sheet takes the binding as dominated by the device (conflicting); in between the degree falls linearly.
MAX_VOLUME_SHIFT_PERCENT = 10.0  # EXPERT_REVIEW: largest volume shift of the protein chamber (percent) that can be left uncorrected, for full agreement; above 10 percent the concentrations on the two sides differ by the shift (osmotic flow, Donnan effect) and the free fraction is biased.
VOLUME_SHIFT_ZERO_AGREEMENT_PERCENT = 30.0  # EXPERT_REVIEW: volume shift (percent) from which the sheet takes the concentrations of the two sides as no longer comparable (conflicting); in between the degree falls linearly.
MIN_SALT_MM = 100.0  # EXPERT_REVIEW: smallest concentration (mM) of monovalent salt that is taken to keep the Donnan effect small when the passage does not say the volume shift was corrected or measured (physiological buffers hold about 150 mM; at low ionic strength a charged protein shifts salt and water across the membrane).
MAX_BOUND_OVER_PROTEIN = 1.0  # EXPERT_REVIEW: largest ratio of the bound ligand concentration to the protein concentration, for full agreement (the owner's rule: the bound ligand must not exceed the protein; for a one-site protein a larger ratio means the sites are used up and the ligand is depleted).
BOUND_OVER_PROTEIN_ZERO_AGREEMENT = 3.0  # EXPERT_REVIEW: ratio of the bound ligand to the protein from which the sheet takes the sites as exceeded beyond what several sites per protein could explain (conflicting); in between the degree falls linearly.
MIN_PROTEIN_OVER_KD = 0.2  # EXPERT_REVIEW: smallest ratio of the protein concentration to the KD at which a fraction bound can be measured, for full agreement; at 0.2 times the KD about 17 percent of a trace of ligand is bound (protein / (protein + KD)), above the 5 percent that shows binding.
PROTEIN_OVER_KD_ZERO_AGREEMENT = 0.05  # EXPERT_REVIEW: protein over KD at or below which the sheet takes the fraction bound as not measurable (conflicting); at 0.05 times the KD about 5 percent of a trace of ligand is bound, the minimum that shows binding; in between the degree rises linearly.
MIN_CONCENTRATIONS = 6  # EXPERT_REVIEW: fewest ligand concentrations of a saturation series for a KD (the usual series have six to ten; KD and Bmax are not both defined with fewer).
LOW_FACTOR = 0.5  # EXPERT_REVIEW: the lowest total ligand concentration must be at most this multiple of the KD for full agreement (about a third of the sites occupied, the usual design starts below the KD).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: lowest total ligand concentration (multiple of the KD) from which the sheet takes the low end of the curve as not sampled (conflicting); at the KD half of the sites are already occupied.
HIGH_FACTOR = 4.0  # EXPERT_REVIEW: the highest total ligand concentration must be at least this multiple of the KD for full agreement (about 80 percent of the sites occupied, so that the plateau is defined by data).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: highest total ligand concentration (multiple of the KD) at or below which the sheet takes the plateau as not reached (conflicting); at the KD only half of the sites are occupied.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); cells or wells of one experiment do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_dialysis_recovery_is_a_mass_balance_not_a_matrix_recovery', 'attributed_signal': 'a_dialysis_bound_fraction_is_not_an_attribution_fraction', 'total_signal': 'a_dialysis_bound_fraction_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_dialysis_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_dialysis_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _at_most(value, full, zero, refs):
    """Supported with degree 1.0 up to the full-agreement limit, falling linearly to 0 at the zero-agreement limit; conflicting from there on (a larger value is worse)."""
    if value >= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (zero - value) / (zero - full)))


def _at_least(value, full, zero, refs):
    """The same for a value that must not fall below its limit (a smaller value is worse)."""
    if value <= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (value - zero) / (full - zero)))


def _judge_binding_observed(native):
    return _verdict('supported' if native['percent_bound'] >= MIN_PERCENT_BOUND else 'conflicting', native['percent_bound_refs'])      # a detection decision: no degree


def _judge_equilibrium(native):
    return _at_least(native['equilibration_h'], MIN_EQUILIBRATION_H, EQUILIBRATION_ZERO_AGREEMENT_H, native['equilibration_refs'])


def _judge_recovery(native):
    return _at_least(native['recovery_percent'], MIN_RECOVERY_PERCENT, RECOVERY_ZERO_AGREEMENT_PERCENT, native['recovery_refs'])


def _judge_adsorption(native):
    return _at_most(native['adsorption_percent'], MAX_ADSORPTION_PERCENT, ADSORPTION_ZERO_AGREEMENT_PERCENT, native['adsorption_refs'])


def _judge_volume_shift(native):
    return _at_most(native['volume_shift_percent'], MAX_VOLUME_SHIFT_PERCENT, VOLUME_SHIFT_ZERO_AGREEMENT_PERCENT, native['volume_shift_refs'])


def _judge_salt(native):
    return _verdict('supported' if native['salt_mM'] >= MIN_SALT_MM else 'unknown', native['salt_refs'])      # a low salt does not show a shift


def _judge_depletion(native):
    return _at_most(native['bound_over_protein'], MAX_BOUND_OVER_PROTEIN, BOUND_OVER_PROTEIN_ZERO_AGREEMENT, native['bound_over_protein_refs'])


def _judge_protein_level(native):
    return _at_least(native['protein_over_kd'], MIN_PROTEIN_OVER_KD, PROTEIN_OVER_KD_ZERO_AGREEMENT, native['protein_over_kd_refs'])


def _judge_free_fraction(native):
    return _at_least(native['percent_unbound'], MIN_PERCENT_UNBOUND, FREE_FRACTION_ZERO_AGREEMENT_PERCENT, native['percent_unbound_refs'])


def _judge_concentration_series(native):
    count = native['concentration_count']
    if count is not None and count < MIN_CONCENTRATIONS:
        return _verdict('conflicting', native['concentration_count_refs'])
    if native['concentration_low_over_kd'] is None:
        return _verdict('unknown', [])      # the count is enough but the span cannot be read
    refs = native['concentration_span_refs']
    low, high = _at_most(native['concentration_low_over_kd'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, refs), _at_least(native['concentration_high_over_kd'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, refs)
    if 'conflicting' in (low['status'], high['status']):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(low['degree'], high['degree']))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('binding_observed', 'percent_bound_recorded_for_the_sheet'): _judge_binding_observed, ('equilibrium', 'equilibration_time_recorded_for_the_sheet'): _judge_equilibrium,
          ('recovery', 'recovery_recorded_for_the_sheet'): _judge_recovery, ('device_adsorption', 'adsorption_recorded_for_the_sheet'): _judge_adsorption,
          ('volume_shift', 'volume_shift_recorded_for_the_sheet'): _judge_volume_shift, ('volume_shift', 'salt_recorded_for_the_sheet'): _judge_salt,
          ('ligand_depletion', 'bound_over_protein_recorded_for_the_sheet'): _judge_depletion, ('protein_level', 'protein_over_kd_recorded_for_the_sheet'): _judge_protein_level,
          ('free_fraction_measurable', 'percent_unbound_recorded_for_the_sheet'): _judge_free_fraction, ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_concentration_series,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _interaction(graded):
    """(the qualitative statement of the record, its refs): the grader's own when the fact binding_detected states it; else, when a stated fraction decides, the sheet's reading of the judgement of binding_observed."""
    native = graded['native']
    if graded['reasons']['binding_observed'] == 'percent_bound_recorded_for_the_sheet':
        return ('detected' if _criterion(graded, 'binding_observed')['status'] == 'supported' else 'not_detected'), list(native['percent_bound_refs'])
    return native['interaction'], list(native['interaction_refs'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _binding_constant(native):
    """The name of the binding constant the effect carries (kd, else ki), or None."""
    return next((name for name in BINDING_CONSTANTS if native[name + '_nM'] is not None), None)


def _variance(graded, constant_name):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if constant_name is None:
        return None, 'no_effect_to_carry_a_variance', []
    name = constant_name + '_spread'
    spread = native['quantities'][name]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, name + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_dialysis(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    quantitative = constant_name is not None
    if quantitative:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'dialysis_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'dialysis_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
    if not quantitative:
        null_components['effect'] = 'qualitative_assay_reports_no_binding_constant'
        null_components['effect_variance'] = 'qualitative_assay_reports_no_binding_constant'
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [apply_support(_criterion(graded, m), native['support'][m]) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
    if variance is not None:
        variance_fields = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['ligand_preparation_ref'], 'immobilized_preparation_ref': preparations['protein_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'dialysis', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities'][constant_name]['support']      # the support class of the binding-constant operand, the field that fixes the effect
    else:
        interaction, interaction_refs = _interaction(graded)
        converted['qualitative_effect'] = {'statement': STATEMENTS[interaction], 'support_refs': interaction_refs, 'percent_bound': native['percent_bound']}
        if interaction is not None:
            if graded['reasons']['binding_observed'] == 'percent_bound_recorded_for_the_sheet':
                # the statement is the sheet's reading of the stated fraction: the support class of the first stated field the percent bound is taken from
                converted['direction_field_support'] = next(native['quantities'][name]['support'] for name, _ in BOUND_FROM if native['quantities'][name]['status'] == 'point')
            else:
                converted['direction_field_support'] = native['support']['binding_observed'][0]      # the fact binding_detected states it (first of the criterion's reads; its support is set whenever it is answered yes or no)
    return converted
