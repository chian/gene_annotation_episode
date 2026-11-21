"""FCS converter: turns the FCS grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_fcs.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST and Trp converters fill), the
dependence keys the merger needs, and for every sheet component that a fluorescence
correlation titration cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported KD in nM (point operand; the measurement key is
                  fcs_kd). No KD leaves effect null.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread) allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n, and only when the replicates
                  criterion is supported (n independent titrations);
                  confidence_interval -> not converted (needs its level and
                  degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the titrant,
immobilized_preparation_ref = the labelled partner held at a low constant concentration,
surface_ref = None (a titration in solution has no surface), dataset_ref = the dataset.

Criteria mapping (FCS criteria -> sheet criteria), declared in CRITERIA_MAP
----------------------------------------------------------------------------
binding_controls              volume_calibration + triplet_state + brightness + crosstalk +
                              background + aggregates + photobleaching + surface_adsorption +
                              labelling + specificity_control
binding_regime                saturation + labelled_range + labelled_over_kd + concentration_series + equilibrium
binding_parameter_definition  diffusion_model + fit_model
calibration_applicability     diffusion_change + mass_consistency + acquisition (the size of the
                              diffusion change and its agreement with the mass, and the photons
                              collected: this method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Continuous comparisons (a ratio, a fold, a percent) are supported with a degree of 1.0 up to the full-agreement limit, the degree falling
linearly to 0 at the zero-agreement limit, and conflicting (no degree) at or beyond it: diffusion_change (ratio, MIN_DIFFUSION_RATIO down to DIFFUSION_RATIO_ZERO_AGREEMENT),
mass_consistency (the factor between the diffusion ratio and the cube-root expectation, MASS_CONSISTENCY_FACTOR up to MASS_CONSISTENCY_ZERO_FACTOR), saturation (percent,
MIN_FRACTION_BOUND_MAXIMUM_PERCENT down to FRACTION_BOUND_ZERO_AGREEMENT_PERCENT), labelled_over_kd (ratio, LABELLED_MAX_OVER_KD up to LABELLED_OVER_KD_ZERO_AGREEMENT; a
tight-binding analysis above the limit is supported without a degree), and concentration_series (the lowest and the highest concentration over the KD, the smaller of the two
degrees, after the count minimum MIN_CONCENTRATIONS, which fails without a degree). Count minimums, absolute quantities and yes/no facts get no degree: labelled_range (the
particle number between MIN_PARTICLE_NUMBER and MAX_PARTICLE_NUMBER, else the concentration between MIN_LABELLED_NM and MAX_LABELLED_NM), equilibrium (an incubation below
MIN_INCUBATION_MIN conflicts, otherwise unknown), acquisition (a total of at least MIN_TOTAL_ACQUISITION_S is supported; below it conflicting when the repeat count is given,
else unknown) and replicates (conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown). A sheet criterion that is supported carries the
smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
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
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_fcs_converted_v1'
CRITERIA_MAP = {'binding_controls': ('volume_calibration', 'triplet_state', 'brightness', 'crosstalk', 'background', 'aggregates', 'photobleaching', 'surface_adsorption', 'labelling', 'specificity_control'), 'binding_regime': ('saturation', 'labelled_range', 'labelled_over_kd', 'concentration_series', 'equilibrium'), 'binding_parameter_definition': ('diffusion_model', 'fit_model'), 'calibration_applicability': ('diffusion_change', 'mass_consistency', 'acquisition'), 'sampling_basis': ('replicates',)}
MIN_DIFFUSION_RATIO = 1.3  # EXPERT_REVIEW: smallest slow-over-fast diffusion ratio of the complex and the free labelled partner that can be read as a fraction bound; diffusion times of repeated measurements scatter by about ten percent, so a change below about thirty percent cannot be told from the scatter.
DIFFUSION_RATIO_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: diffusion ratio at or below which the sheet takes the diffusion change as absent (conflicting): a ratio of 1 is no change of the diffusion at all; in between the degree falls linearly.
MASS_CONSISTENCY_FACTOR = 1.5  # EXPERT_REVIEW: the reported diffusion ratio may differ from the ratio the cube-root law gives for the reported mass ratio by at most this factor either way; shape, the dye and the hydration shell move the ratio by tens of percent.
MASS_CONSISTENCY_ZERO_FACTOR = 3.0  # EXPERT_REVIEW: factor between the reported and the expected diffusion ratio at or beyond which the sheet takes them as disagreeing (conflicting); a threefold mismatch is beyond any shape or hydration effect and points to aggregation, oligomerisation or no binding.
MIN_FRACTION_BOUND_MAXIMUM_PERCENT = 80.0  # EXPERT_REVIEW: the largest fraction bound reached (percent) must be at least this for the plateau of the binding curve to be known; at 80 percent the titration reaches about four times the KD of a one-site binding.
FRACTION_BOUND_ZERO_AGREEMENT_PERCENT = 20.0  # EXPERT_REVIEW: largest fraction bound (percent) at or below which the sheet takes the plateau as not reached at all (conflicting); at 20 percent bound the highest titrant concentration is about a quarter of the KD, only the foot of the curve is seen.
MIN_PARTICLE_NUMBER = 0.1  # EXPERT_REVIEW: fewest fluorescent molecules on average in the confocal volume; below it the molecules are in the volume so seldom that the correlation curve needs impractically long measurements.
MAX_PARTICLE_NUMBER = 10.0  # EXPERT_REVIEW: most fluorescent molecules on average in the confocal volume; the correlation amplitude is the inverse of this number, and above it the fluctuations are lost in the shot noise.
MIN_LABELLED_NM = 0.3  # EXPERT_REVIEW: lowest labelled concentration (nM) used when no particle number is given; in a typical confocal volume of about half a femtolitre 0.3 nM is about 0.1 molecules.
MAX_LABELLED_NM = 30.0  # EXPERT_REVIEW: highest labelled concentration (nM) used when no particle number is given; in a typical confocal volume of about half a femtolitre 30 nM is about 10 molecules.
LABELLED_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the labelled partner may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by depletion of the free titrant).
LABELLED_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: multiple of the KD at or above which the sheet takes the labelled partner as too high for any KD to be read without a tight-binding analysis (conflicting); at ten times the KD the titration is stoichiometric and the transition sits at the labelled concentration, not at the KD.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable titration (the two baselines and the transition of a binding curve are not all defined with fewer than eight).
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest titrant concentration must be at most this multiple of the KD (the free-partner baseline of the curve must be defined).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or above which the lowest titrant concentration leaves no free-partner baseline (conflicting); at the KD the partner is already half bound.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest titrant concentration must be at least this multiple of the KD, because the saturation plateau is only known by reaching it (about 90 percent saturation).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or below which the highest titrant concentration does not reach even half saturation (conflicting).
MIN_INCUBATION_MIN = 5.0  # EXPERT_REVIEW: an incubation shorter than this (minutes) is too short to call a complex at equilibrium without a time course (mixing and settling of a small sample in a chamber alone take a few minutes, and slow binders need longer).
MIN_TOTAL_ACQUISITION_S = 60.0  # EXPERT_REVIEW: least total acquisition time per sample (seconds, one measurement times its repeats); at nanomolar concentrations a correlation curve of a molecule that crosses the volume in a millisecond needs about a minute of photons for a stable fit.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series or preparations).
NULL_REASONS = {'recovery': 'a_fluorescence_correlation_titration_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'a_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_fluorescence_correlation_titration_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_fluorescence_correlation_titration_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_diffusion_change(native):
    return _degree_verdict(native['diffusion_ratio'], MIN_DIFFUSION_RATIO, DIFFUSION_RATIO_ZERO_AGREEMENT, native['diffusion_refs'])


def _judge_mass_consistency(native):
    ratio, expected = native['diffusion_ratio'], native['expected_diffusion_ratio']
    return _degree_verdict(max(ratio / expected, expected / ratio), MASS_CONSISTENCY_FACTOR, MASS_CONSISTENCY_ZERO_FACTOR, native['mass_consistency_refs'])


def _judge_saturation(native):
    return _degree_verdict(native['fraction_bound_maximum'], MIN_FRACTION_BOUND_MAXIMUM_PERCENT, FRACTION_BOUND_ZERO_AGREEMENT_PERCENT, native['fraction_bound_maximum_refs'])


def _judge_particle_number(native):
    return _verdict('supported' if MIN_PARTICLE_NUMBER <= native['particle_number'] <= MAX_PARTICLE_NUMBER else 'conflicting', native['labelled_range_refs'])


def _judge_labelled_concentration(native):
    return _verdict('supported' if MIN_LABELLED_NM <= native['labelled_nM'] <= MAX_LABELLED_NM else 'conflicting', native['labelled_range_refs'])


def _judge_labelled_over_kd(native):
    ratio, refs = native['labelled_over_kd'], native['labelled_over_kd_refs']
    if ratio > LABELLED_MAX_OVER_KD and native['tight_binding_analysis']:
        return _verdict('supported', refs)      # the depletion is handled by the analysis: no degree
    return _degree_verdict(ratio, LABELLED_MAX_OVER_KD, LABELLED_OVER_KD_ZERO_AGREEMENT, refs)


def _judge_concentration_series(native):
    if native['concentration_count'] < MIN_CONCENTRATIONS:
        return _verdict('conflicting', native['concentration_count_refs'])
    low, high = native['concentration_low_over_constant'], native['concentration_high_over_constant']
    if low is None:
        return _verdict('unknown', [])      # the span can only be judged from the list and the KD
    degrees = (_degree(low, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR), _degree(high, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR))
    if min(degrees) <= 0:
        return _verdict('conflicting', native['concentration_span_refs'])
    return _verdict('supported', native['concentration_span_refs'], min(1.0, *degrees))


def _judge_equilibrium(native):
    if native['incubation_min'] < MIN_INCUBATION_MIN:
        return _verdict('conflicting', native['incubation_refs'])
    return _verdict('unknown', [])


def _judge_acquisition(native):
    if native['acquisition_total_s'] >= MIN_TOTAL_ACQUISITION_S:
        return _verdict('supported', native['acquisition_refs'])
    if native['measurement_repeats_given']:
        return _verdict('conflicting', native['acquisition_refs'])
    return _verdict('unknown', [])      # a short single measurement: the repeats may be unreported


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('diffusion_change', 'diffusion_ratio_recorded_for_the_sheet'): _judge_diffusion_change, ('mass_consistency', 'mass_consistency_recorded_for_the_sheet'): _judge_mass_consistency,
          ('saturation', 'fraction_bound_maximum_recorded_for_the_sheet'): _judge_saturation, ('labelled_range', 'particle_number_recorded_for_the_sheet'): _judge_particle_number,
          ('labelled_range', 'labelled_concentration_recorded_for_the_sheet'): _judge_labelled_concentration, ('labelled_over_kd', 'labelled_over_kd_recorded_for_the_sheet'): _judge_labelled_over_kd,
          ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_concentration_series, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium,
          ('acquisition', 'acquisition_recorded_for_the_sheet'): _judge_acquisition, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded, has_effect):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if not has_effect:
        return None, 'no_effect_to_carry_a_variance', []
    spread = native['quantities']['kd_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'kd_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_titrations_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def _variance_supports(native):
    """The supports of the stated fields the variance rests on: the spread, its kind and, for a standard deviation, the replicate count."""
    quantities = native['quantities']
    names = ['kd_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
    found = [quantities[name]['support'] for name in names] + [native['choice_support']['spread_kind']]
    return [support for support in found if support is not None]


def convert_fcs(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    has_effect = native['kd_nM'] is not None
    if has_effect:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'fcs_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    else:
        null_components['effect'] = 'no_kd_given_as_a_point_value'
    variance, variance_reason, variance_refs = _variance(graded, has_effect)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'fcs_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, _variance_supports(native))
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['fixed_partner_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'fcs', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities']['kd']['support'] if has_effect else None}
