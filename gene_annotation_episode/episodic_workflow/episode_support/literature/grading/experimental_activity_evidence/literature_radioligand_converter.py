"""Radioligand converter: turns the radioligand grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_radioligand.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA and AlphaScreen converters fill), the
dependence keys the merger needs, and for every sheet component that a radioligand assay cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the KD of
                  the radioligand from a saturation experiment, or, when the record has
                  no KD, the Ki of a competition (the measurement key names it:
                  radioligand_kd or radioligand_ki). Neither given leaves effect null; an
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
immobilized_preparation_ref = the receptor preparation, surface_ref = None (the filter or the
well is not a surface reference), dataset_ref = the dataset.

Criteria mapping (radioligand criteria -> sheet criteria), declared in CRITERIA_MAP
-----------------------------------------------------------------------------------
binding_controls              nonspecific_binding + nonspecific_excess + radioligand_quality + filter_binding
binding_regime                equilibrium + radioligand_range + competition_radioligand_level + wash_dissociation
binding_parameter_definition  fit_model + nonlinear_fit + hill_slope + cheng_prusoff
calibration_applicability     ligand_depletion + nonspecific_fraction (the bound fraction of the radioligand and the
                              specific binding over the non-specific binding: this method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Continuous comparisons (a percent, a ratio, a fold, a deviation) are supported with a degree of 1.0 up to the full-agreement limit, the
degree falling linearly to 0 at the zero-agreement limit, and conflicting (no degree) at or beyond it: ligand_depletion (percent bound, MAX_PERCENT_BOUND up to
PERCENT_BOUND_ZERO_AGREEMENT), nonspecific_fraction (percent, MAX_NONSPECIFIC_FRACTION up to NONSPECIFIC_FRACTION_ZERO_AGREEMENT), nonspecific_excess (fold excess,
MIN_NONSPECIFIC_EXCESS down to NONSPECIFIC_EXCESS_ZERO_AGREEMENT), competition_radioligand_level (radioligand over the KD, MAX_RADIOLIGAND_OVER_KD up to
RADIOLIGAND_OVER_KD_ZERO_AGREEMENT), hill_slope (the slope between MIN_HILL and MAX_HILL has the full degree; it falls linearly to 0 at MIN_HILL_ZERO_AGREEMENT below and at
MAX_HILL_ZERO_AGREEMENT above), cheng_prusoff (the fold gap of the reported and the calculated Ki, CHENG_PRUSOFF_FACTOR up to CHENG_PRUSOFF_ZERO_FACTOR) and radioligand_range (the
lowest and the highest concentration over the KD, the smaller of the two degrees, after the count minimum MIN_CONCENTRATIONS, which fails without a degree). Count minimums and
yes/no facts get no degree: equilibrium (an incubation below MIN_INCUBATION_MIN conflicts, otherwise unknown) and replicates (conflicting below MIN_REPLICATES, else supported when
the independence is yes, else unknown). A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the
interpretation and the merger carries it per result).
Quote support (literature_quote_support.py, SUPPORT_DEGREE: direct 1.0, implied 0.7, about_something_else 0.3, defined once there with the
reason of each): a supported sheet criterion whose members read a stated field with support 'implied' or 'about_something_else' (the grader's
native['support'], per member) has its degree multiplied by the weakest factor; where it had no degree the degree becomes that factor; 'direct' leaves it as it
is. The variance_correspondence reads the support of the spread, its kind and, for a standard deviation, the replicate count. Support never
changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_radioligand_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('nonspecific_binding', 'nonspecific_excess', 'radioligand_quality', 'filter_binding'), 'binding_regime': ('equilibrium', 'radioligand_range', 'competition_radioligand_level', 'wash_dissociation'), 'binding_parameter_definition': ('fit_model', 'nonlinear_fit', 'hill_slope', 'cheng_prusoff'), 'calibration_applicability': ('ligand_depletion', 'nonspecific_fraction'), 'sampling_basis': ('replicates',)}
MAX_PERCENT_BOUND = 10.0  # EXPERT_REVIEW: largest percent of the added radioligand that may be bound; above about 10 percent the free radioligand is no longer the added concentration (ligand depletion) and KD and IC50 are biased (the usual rule of the receptor binding literature).
PERCENT_BOUND_ZERO_AGREEMENT = 50.0  # EXPERT_REVIEW: percent bound at or above which the sheet takes the free radioligand as not the added concentration at all (conflicting); at half bound the free concentration is half the added one and the KD is biased about twofold; in between the degree falls linearly.
MAX_NONSPECIFIC_FRACTION = 50.0  # EXPERT_REVIEW: largest non-specific binding, as a percent of the total binding at the highest radioligand concentration; above half the specific signal is a small difference of two large numbers and the fit is not reliable.
NONSPECIFIC_FRACTION_ZERO_AGREEMENT = 90.0  # EXPERT_REVIEW: non-specific percent at or above which the sheet takes the specific signal as lost (conflicting); at 90 percent the specific binding is a tenth of the total and its fit is dominated by the noise of the non-specific measurement.
MIN_NONSPECIFIC_EXCESS = 100.0  # EXPERT_REVIEW: smallest excess of the unlabelled ligand over its Kd to define non-specific binding (usual 100 to 1000 times); at 100 times the Kd about 99 percent of the specific sites are occupied.
NONSPECIFIC_EXCESS_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: excess (over the Kd) at or below which the sheet takes non-specific binding as not defined at all (conflicting); at the Kd itself only half of the specific sites are occupied; in between the degree falls linearly.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest radioligand concentrations of a saturation series (usual series have eight to twelve; KD and Bmax are not both defined with fewer).
LOW_FACTOR = 0.25  # EXPERT_REVIEW: the lowest radioligand concentration must be at most this multiple of the KD (about 20 percent occupancy; the usual design starts near 0.1 times the KD).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or above which the lowest radioligand concentration leaves no low-occupancy part of the curve (conflicting); at the KD the sites are already half occupied.
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest radioligand concentration must be at least this multiple of the KD (about 83 percent occupancy, so that Bmax is defined by data; the usual design reaches 10 times the KD).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or below which the highest radioligand concentration does not reach even half occupancy (conflicting); Bmax is then an extrapolation.
MAX_RADIOLIGAND_OVER_KD = 1.0  # EXPERT_REVIEW: the single radioligand concentration of a competition must be at most this multiple of its KD (at or below the KD the IC50 is within a factor of two of the Ki and the depletion is small).
RADIOLIGAND_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: multiple of the KD at or above which the sheet takes the radioligand level as too high for the IC50 to say anything of the Ki (conflicting); at ten times the KD the IC50 is eleven times the Ki and the competition curve is read at near-saturation of the sites; in between the degree falls linearly.
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: an incubation shorter than this (minutes) is too short to call the binding at equilibrium without an association time course (usual protocols incubate 60 to 120 minutes at room temperature, longer at low temperature).
MIN_HILL = 0.8  # EXPERT_REVIEW: lowest Hill slope that still shows one site obeying mass action; a shallower curve shows several sites or negative cooperativity (usual limits 0.8 to 1.2).
MIN_HILL_ZERO_AGREEMENT = 0.5  # EXPERT_REVIEW: Hill slope at or below which the sheet takes the curve as clearly not one site (conflicting); a slope of one half is the shallowest that two sites of very different affinity give; between this and MIN_HILL the degree falls linearly.
MAX_HILL = 1.2  # EXPERT_REVIEW: highest Hill slope that still shows one site obeying mass action; a steeper curve shows cooperativity or no equilibrium.
MAX_HILL_ZERO_AGREEMENT = 1.5  # EXPERT_REVIEW: Hill slope at or above which the sheet takes the curve as clearly cooperative or not at equilibrium (conflicting); symmetric to MIN_HILL_ZERO_AGREEMENT about 1; between MAX_HILL and this the degree falls linearly.
CHENG_PRUSOFF_FACTOR = 1.5  # EXPERT_REVIEW: allowed fold gap between a reported Ki and the Ki calculated from the reported IC50, radioligand concentration and KD by the Cheng-Prusoff equation (rounding and fit differences are within a factor of 1.5; a larger gap shows another equation or another KD was used).
CHENG_PRUSOFF_ZERO_FACTOR = 5.0  # EXPERT_REVIEW: fold gap of the reported and the calculated Ki at or beyond which the sheet takes them as disagreeing (conflicting); a fivefold gap is more than the whole Cheng-Prusoff correction at the recommended radioligand level (a factor of two at most) and shows that another KD, another equation or an IC50 of another experiment was used; in between the degree falls linearly.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); wells or tubes of one experiment do not count.
NULL_REASONS = {'recovery': 'a_radioligand_assay_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_radioligand_nonspecific_binding_is_not_an_attribution_fraction', 'total_signal': 'a_radioligand_nonspecific_binding_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_radioligand_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_radioligand_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero):
    """How far the value agrees: 1.0 at the full-agreement limit (and beyond it), falling linearly to 0 at the zero-agreement limit; zero or less at or past it. Either direction (zero below or above full)."""
    return (value - zero) / (full - zero)


def _degree_verdict(value, full, zero, refs):
    degree = _degree(value, full, zero)
    if degree <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, degree))


def _judge_percent_bound(native):
    return _degree_verdict(native['percent_bound'], MAX_PERCENT_BOUND, PERCENT_BOUND_ZERO_AGREEMENT, native['percent_bound_refs'])


def _judge_nonspecific_fraction(native):
    return _degree_verdict(native['nonspecific_percent'], MAX_NONSPECIFIC_FRACTION, NONSPECIFIC_FRACTION_ZERO_AGREEMENT, native['nonspecific_fraction_refs'])


def _judge_nonspecific_excess(native):
    return _degree_verdict(native['nonspecific_excess_ratio'], MIN_NONSPECIFIC_EXCESS, NONSPECIFIC_EXCESS_ZERO_AGREEMENT, native['nonspecific_excess_refs'])


def _judge_equilibrium(native):
    if native['incubation_min'] < MIN_INCUBATION_MIN:
        return _verdict('conflicting', native['incubation_refs'])
    return _verdict('unknown', [])


def _judge_radioligand_range(native):
    count = native['concentration_count']
    if count is not None and count < MIN_CONCENTRATIONS:
        return _verdict('conflicting', native['concentration_count_refs'])
    low, high = native['concentration_low_over_kd'], native['concentration_high_over_kd']
    if low is None:
        return _verdict('unknown', [])      # the span can only be judged from the KD and a list or a lowest and a highest concentration
    degrees = (_degree(low, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR), _degree(high, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR))
    if min(degrees) <= 0:
        return _verdict('conflicting', native['concentration_span_refs'])
    return _verdict('supported', native['concentration_span_refs'], min(1.0, *degrees))


def _judge_radioligand_level(native):
    return _degree_verdict(native['radioligand_over_kd'], MAX_RADIOLIGAND_OVER_KD, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT, native['radioligand_level_refs'])


def _judge_hill_slope(native):
    slope = native['hill_slope']
    if slope < 1:
        return _degree_verdict(slope, MIN_HILL, MIN_HILL_ZERO_AGREEMENT, native['hill_slope_refs'])
    return _degree_verdict(slope, MAX_HILL, MAX_HILL_ZERO_AGREEMENT, native['hill_slope_refs'])


def _judge_cheng_prusoff(native):
    return _degree_verdict(native['cheng_prusoff_fold'], CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_FACTOR, native['cheng_prusoff_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('ligand_depletion', 'percent_bound_recorded_for_the_sheet'): _judge_percent_bound, ('nonspecific_fraction', 'nonspecific_fraction_recorded_for_the_sheet'): _judge_nonspecific_fraction,
          ('nonspecific_excess', 'excess_recorded_for_the_sheet'): _judge_nonspecific_excess, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium,
          ('radioligand_range', 'radioligand_range_recorded_for_the_sheet'): _judge_radioligand_range, ('competition_radioligand_level', 'radioligand_over_kd_recorded_for_the_sheet'): _judge_radioligand_level,
          ('hill_slope', 'hill_slope_recorded_for_the_sheet'): _judge_hill_slope, ('cheng_prusoff', 'cheng_prusoff_recorded_for_the_sheet'): _judge_cheng_prusoff,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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


def _variance_supports(native, constant_name):
    """The supports of the stated fields the variance rests on: the spread of the constant, its kind and, for a standard deviation, the replicate count."""
    quantities = native['quantities']
    names = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
    found = [quantities[name]['support'] for name in names] + [native['choice_support']['spread_kind']]
    return [support for support in found if support is not None]


def convert_radioligand(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if native['ic50_nM'] is not None else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'radioligand_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'radioligand_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
    null_components.update(NULL_REASONS)
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
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # thin quote support lowers a supported degree
    if variance is not None:
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, _variance_supports(native, constant_name))
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['radioligand_preparation_ref'], 'immobilized_preparation_ref': preparations['receptor_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'radioligand', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
