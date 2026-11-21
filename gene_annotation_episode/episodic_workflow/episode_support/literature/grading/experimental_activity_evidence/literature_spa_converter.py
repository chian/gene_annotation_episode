"""SPA converter: turns the SPA grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_spa.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen and radioligand converters fill), the
dependence keys the merger needs, and for every sheet component that an SPA cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the KD of
                  the radioligand from a saturation experiment, or, when the record has
                  no KD, the Ki of a competition (the measurement key names it:
                  spa_kd or spa_ki). Neither given leaves effect null; an
                  IC50 alone is a half-maximal concentration, not a dissociation constant (it
                  depends on the concentration and the KD of the radioligand it competes with) and is not
                  carried into the effect.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent experiments); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the radioligand,
immobilized_preparation_ref = the captured target, surface_ref = None (the bead and the well are not a surface reference),
dataset_ref = the dataset.

Criteria mapping (SPA criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              nonspecific_binding + nonspecific_excess + nonproximity_signal + bead_only_control + radioligand_quality
binding_regime                equilibrium + radioligand_range + competition_radioligand_level + homogeneous_format
binding_parameter_definition  fit_model + nonlinear_fit + hill_slope + cheng_prusoff
calibration_applicability     ligand_depletion + nonspecific_fraction + quench_interference + bead_settling (the bound fraction of the
                              radioligand, the specific signal over the non-specific signal, and the two ways the counted light can
                              be mis-scaled in a bead assay, colour quench and bead settling: this method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet';
JUDGES maps each such criterion and reason to its judgement). A continuous comparison (a percent, a fold, a quotient, a slope against a limit)
is supported with a degree of 1.0 up to its full-agreement limit, the degree falling linearly to 0 at its zero-agreement limit, and conflicting at or beyond
that limit: ligand_depletion (percent bound), nonspecific_fraction, nonspecific_excess, bead_only_control, radioligand_range (the lowest and the highest
concentration over the KD, the weaker of the two), competition_radioligand_level, hill_slope (both sides) and cheng_prusoff (the fold gap). Count minimums and
facts get no degree: the concentration count and the replicates (conflicting below the minimum; replicates supported when independent is yes, else unknown), and
equilibrium (an incubation below MIN_INCUBATION_MIN is conflicting, otherwise unknown: an incubation time alone never supports equilibrium). A sheet criterion that
is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree
(the continuous comparisons above); direct leaves it unchanged. Support never changes a status. variance_correspondence takes the weakest support of
the spread (and of the replicate count for a standard deviation).
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_spa_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('nonspecific_binding', 'nonspecific_excess', 'nonproximity_signal', 'bead_only_control', 'radioligand_quality'), 'binding_regime': ('equilibrium', 'radioligand_range', 'competition_radioligand_level', 'homogeneous_format'), 'binding_parameter_definition': ('fit_model', 'nonlinear_fit', 'hill_slope', 'cheng_prusoff'), 'calibration_applicability': ('ligand_depletion', 'nonspecific_fraction', 'quench_interference', 'bead_settling'), 'sampling_basis': ('replicates',)}
MAX_PERCENT_BOUND = 10.0  # EXPERT_REVIEW: largest percent of the added radioligand that may be bound for full agreement; above about 10 percent the free radioligand is no longer the added concentration (ligand depletion) and KD and IC50 are biased (the usual rule of the receptor binding literature; in an SPA the free radioligand cannot be measured because nothing is separated).
PERCENT_BOUND_ZERO_AGREEMENT = 30.0  # EXPERT_REVIEW: percent bound from which the sheet takes depletion as disagreeing (conflicting); with 30 percent bound the free radioligand is only 70 percent of the added one and the constants are off by more than the fit can correct; in between the degree falls linearly.
MAX_NONSPECIFIC_FRACTION = 50.0  # EXPERT_REVIEW: largest non-specific binding, as a percent of the total binding at the highest radioligand concentration, for full agreement; above half the specific signal is a small difference of two large numbers and the fit is not reliable.
NONSPECIFIC_FRACTION_ZERO_AGREEMENT = 80.0  # EXPERT_REVIEW: non-specific percent from which the sheet takes the specific signal as lost (conflicting); at 80 percent the specific binding is a fifth of the total and cannot be told from the noise of the two large numbers.
MAX_BEAD_ONLY_FRACTION = 20.0  # EXPERT_REVIEW: largest signal of the control without the captured target (beads and radioligand only), as a percent of the total signal, for full agreement; the radioligand can bind the bead itself, and above about a fifth the bead background is a large part of the counted light and is not removed by the non-specific binding correction alone.
BEAD_ONLY_ZERO_AGREEMENT = 50.0  # EXPERT_REVIEW: bead-only percent from which the sheet takes the signal as mostly bead background (conflicting); at half of the total the counted light is mainly not the captured target.
MIN_NONSPECIFIC_EXCESS = 100.0  # EXPERT_REVIEW: smallest excess of the unlabelled ligand over its Kd to define non-specific binding for full agreement (usual 100 to 1000 times); at 100 times the Kd about 99 percent of the specific sites are occupied.
NONSPECIFIC_EXCESS_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: excess (fold over the Kd) at or below which the sheet takes non-specific binding as not defined (conflicting); at 10 times the Kd about 91 percent of the sites are occupied, below it the remaining specific binding is counted as non-specific.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest radioligand concentrations of a saturation series (usual series have eight to twelve; KD and Bmax are not both defined with fewer).
LOW_FACTOR = 0.25  # EXPERT_REVIEW: the lowest radioligand concentration must be at most this multiple of the KD for full agreement (about 20 percent occupancy; the usual design starts near 0.1 times the KD).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: lowest concentration (multiple of the KD) from which the sheet takes the low end of the curve as not sampled (conflicting); at the KD the occupancy is already half.
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest radioligand concentration must be at least this multiple of the KD for full agreement (about 83 percent occupancy, so that Bmax is defined by data; the usual design reaches 10 times the KD).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: highest concentration (multiple of the KD) at or below which the sheet takes the plateau as not reached (conflicting); at the KD the occupancy is only half and Bmax is not defined by data.
MAX_RADIOLIGAND_OVER_KD = 1.0  # EXPERT_REVIEW: the single radioligand concentration of a competition must be at most this multiple of its KD for full agreement (at or below the KD the IC50 is within a factor of two of the Ki and the depletion is small).
RADIOLIGAND_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: radioligand over KD from which the sheet takes the IC50 as no longer near the Ki (conflicting); at ten times the KD the IC50 is eleven times the Ki.
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: an incubation shorter than this (minutes) is too short to call the binding at equilibrium without an association time course (usual SPA protocols incubate 1 to 4 hours at room temperature, longer at low temperature, and the beads need time to capture the target).
MIN_HILL = 0.8  # EXPERT_REVIEW: lowest Hill slope that still shows one site obeying mass action for full agreement; a shallower curve shows several sites or negative cooperativity (usual limits 0.8 to 1.2).
MAX_HILL = 1.2  # EXPERT_REVIEW: highest Hill slope that still shows one site obeying mass action for full agreement; a steeper curve shows cooperativity or no equilibrium.
HILL_LOW_ZERO_AGREEMENT = 0.5  # EXPERT_REVIEW: Hill slope at or below which the sheet takes the curve as not one site (conflicting); half the steepness of mass action is a clear mixture of sites or strong negative cooperativity.
HILL_HIGH_ZERO_AGREEMENT = 2.0  # EXPERT_REVIEW: Hill slope at or above which the sheet takes the curve as not one site (conflicting); twice the steepness of mass action is clear cooperativity or no equilibrium.
CHENG_PRUSOFF_FACTOR = 1.5  # EXPERT_REVIEW: allowed fold gap between a reported Ki and the Ki calculated from the reported IC50, radioligand concentration and KD by the Cheng-Prusoff equation for full agreement (rounding and fit differences are within a factor of 1.5; a larger gap shows another equation or another KD was used).
CHENG_PRUSOFF_ZERO_AGREEMENT_FACTOR = 5.0  # EXPERT_REVIEW: fold gap from which the sheet takes the reported Ki as not the Cheng-Prusoff one (conflicting); a fivefold gap is not rounding or fit difference but another equation or another KD.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); wells of one experiment do not count.
NULL_REASONS = {'recovery': 'an_spa_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_spa_nonspecific_binding_is_not_an_attribution_fraction', 'total_signal': 'an_spa_nonspecific_binding_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_spa_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_spa_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _weakest(first, second, refs):
    """Two continuous comparisons that both must hold: conflicting if either is, else the smaller degree."""
    if 'conflicting' in (first['status'], second['status']):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(first['degree'], second['degree']))


def _judge_ligand_depletion(native):
    return _at_most(native['percent_bound'], MAX_PERCENT_BOUND, PERCENT_BOUND_ZERO_AGREEMENT, native['percent_bound_refs'])


def _judge_nonspecific_fraction(native):
    return _at_most(native['nonspecific_fraction_percent'], MAX_NONSPECIFIC_FRACTION, NONSPECIFIC_FRACTION_ZERO_AGREEMENT, native['nonspecific_fraction_refs'])


def _judge_nonspecific_excess(native):
    return _at_least(native['nonspecific_excess_ratio'], MIN_NONSPECIFIC_EXCESS, NONSPECIFIC_EXCESS_ZERO_AGREEMENT, native['nonspecific_excess_refs'])


def _judge_bead_only(native):
    return _at_most(native['bead_only_percent'], MAX_BEAD_ONLY_FRACTION, BEAD_ONLY_ZERO_AGREEMENT, native['bead_only_refs'])


def _judge_equilibrium(native):
    if native['incubation_min'] < MIN_INCUBATION_MIN:
        return _verdict('conflicting', native['incubation_refs'])
    return _verdict('unknown', [])      # a long incubation alone does not show equilibrium


def _judge_radioligand_range(native):
    count = native['concentration_count']
    if count is not None and count < MIN_CONCENTRATIONS:
        return _verdict('conflicting', native['concentration_count_refs'])
    if native['concentration_low_over_kd'] is None:
        return _verdict('unknown', [])      # the count is enough but the span cannot be read
    refs = native['concentration_span_refs']
    return _weakest(_at_most(native['concentration_low_over_kd'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, refs), _at_least(native['concentration_high_over_kd'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, refs), refs)


def _judge_radioligand_level(native):
    return _at_most(native['radioligand_over_kd'], MAX_RADIOLIGAND_OVER_KD, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT, native['radioligand_over_kd_refs'])


def _judge_hill_slope(native):
    slope, refs = native['hill_slope'], native['hill_slope_refs']
    if slope < MIN_HILL:
        return _at_least(slope, MIN_HILL, HILL_LOW_ZERO_AGREEMENT, refs)
    if slope > MAX_HILL:
        return _at_most(slope, MAX_HILL, HILL_HIGH_ZERO_AGREEMENT, refs)
    return _verdict('supported', refs, 1.0)


def _judge_cheng_prusoff(native):
    ki, calculated = native['ki_nM'], native['calculated_ki_nM']
    return _at_most(max(ki, calculated) / min(ki, calculated), CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_AGREEMENT_FACTOR, native['cheng_prusoff_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('ligand_depletion', 'percent_bound_recorded_for_the_sheet'): _judge_ligand_depletion, ('nonspecific_fraction', 'nonspecific_fraction_recorded_for_the_sheet'): _judge_nonspecific_fraction,
          ('nonspecific_excess', 'excess_recorded_for_the_sheet'): _judge_nonspecific_excess, ('bead_only_control', 'bead_only_percent_recorded_for_the_sheet'): _judge_bead_only,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium, ('radioligand_range', 'concentration_series_recorded_for_the_sheet'): _judge_radioligand_range,
          ('competition_radioligand_level', 'radioligand_over_kd_recorded_for_the_sheet'): _judge_radioligand_level, ('hill_slope', 'hill_slope_recorded_for_the_sheet'): _judge_hill_slope,
          ('cheng_prusoff', 'cheng_prusoff_gap_recorded_for_the_sheet'): _judge_cheng_prusoff, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


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


def convert_spa(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if native['ic50_nM'] is not None else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'spa_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'spa_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['radioligand_preparation_ref'], 'immobilized_preparation_ref': preparations['receptor_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'spa', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
