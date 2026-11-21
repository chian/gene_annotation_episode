"""EMSA converter: turns the EMSA grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_emsa.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that an EMSA
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (a titration). Then the converter fills the numeric effect as the earlier quantitative types do
(quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key emsa_kd). It is an APPARENT constant, with the caveats of the
                    method (the gel is not at equilibrium during the run, the cage effect of the gel, the probe concentration must be at or below
                    the KD); those caveats are not changed in the number, they are judged by the criteria (equilibrium, complex_stability,
                    probe_concentration, protein_range, saturation, fit_model) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no apparent KD (a shift is shown). Then, exactly as the pull-down converter does (quantity_kind
'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells are
unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and the fraction shifted at
the highest protein concentration is not put into the effect (it is not on the nM scale). What the experiment does contribute is carried beside the
sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'fraction_shifted'}):
  statement          'interaction_detected' (a shifted band is stated), 'interaction_not_detected' (no shift is stated) or 'interaction_not_stated'
  support_refs       the spans of the fact that states it (empty when not stated)
  fraction_shifted   the stated percent of the probe shifted at the highest protein concentration, or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (EMSA criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              specific_competition + nonspecific_competition + mutant_probe + probe_alone_lane + nonspecific_protein_control +
                              protein_identity (the controls that show the shift is specific to this protein and this sequence)
binding_regime                equilibrium + complex_stability + probe_concentration + protein_range + titration_points
binding_parameter_definition  shift_observed + single_complex + fit_model (what the response is: a shifted band, one species, and the model of the KD)
calibration_applicability     free_probe_quantified + saturation (the shifted fraction is read from the free and shifted probe, and reaches a plateau)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Continuous comparisons are supported with a degree of 1.0 up to the full-agreement limit, the degree falling linearly to 0 at the
zero-agreement limit, and conflicting at or beyond that limit: probe_concentration (probe over the KD), protein_range (the lowest and the highest protein over the KD, the weaker
degree taken), saturation (percent shifted at the highest protein) and, for a one-site model with a stated probe, fit_model (the same probe over the KD). Count minimums and
facts get no degree: titration_points and replicates (conflicting below the minimum), single_complex (more than one species needs a multi-site model; this judgement holds the
classification of the fit models as one-site or not), specific_competition (a 'no' with a competitor excess below MIN_COMPETITOR_EXCESS is unknown, not a test of specificity, else
conflicting) and equilibrium (an incubation below MIN_INCUBATION_MIN is conflicting, otherwise unknown: an incubation time alone never supports equilibrium). The judgement of
single_complex can be not_applicable (several species and no apparent KD), and such a member is dropped like any other. A sheet criterion that is supported carries the smallest
degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result). The qualitative effect is unchanged.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree
(the continuous comparisons above); direct leaves it unchanged. Support never changes a status. variance_correspondence takes the weakest support of
the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the protein,
immobilized_preparation_ref = the labelled probe, surface_ref = None (a gel is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_emsa_converted_v1'
CRITERIA_MAP = {'binding_controls': ('specific_competition', 'nonspecific_competition', 'mutant_probe', 'probe_alone_lane', 'nonspecific_protein_control', 'protein_identity'), 'binding_regime': ('equilibrium', 'complex_stability', 'probe_concentration', 'protein_range', 'titration_points'), 'binding_parameter_definition': ('shift_observed', 'single_complex', 'fit_model'), 'calibration_applicability': ('free_probe_quantified', 'saturation'), 'sampling_basis': ('replicates',)}
MIN_COMPETITOR_EXCESS = 50.0  # EXPERT_REVIEW: smallest fold excess of the unlabelled specific probe over the labelled probe at which a shift that is NOT abolished counts against specificity; below it the competitor is too little to compete (the usual EMSA competition uses 50 to 200 fold).
MIN_INCUBATION_MIN = 15.0  # EXPERT_REVIEW: an incubation shorter than this (minutes) is too short to call the binding at equilibrium without a time course (usual EMSA incubations are 15 to 30 minutes, longer for slow or low-temperature binding).
MAX_PROBE_OVER_KD = 1.0  # EXPERT_REVIEW: the probe concentration must be at most this multiple of the KD for full agreement; above the KD the titration is stoichiometric, the shifted fraction reports the probe concentration and the apparent KD is about half of it (usual rule: probe at or below the KD).
PROBE_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: probe over KD from which the sheet takes the titration as stoichiometric (conflicting); at ten times the KD the shifted fraction only reports the probe concentration; in between the degree falls linearly.
LOW_FACTOR = 0.25  # EXPERT_REVIEW: the lowest protein concentration must be at most this multiple of the KD for full agreement (about 20 percent of the probe shifted; the usual titration starts near 0.1 times the KD).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: lowest protein concentration (multiple of the KD) from which the sheet takes the low end of the curve as not sampled (conflicting); at the KD half of the probe is already shifted.
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest protein concentration must be at least this multiple of the KD for full agreement (about 83 percent of the probe shifted, so that the plateau is defined by data; the usual titration reaches 10 times the KD).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: highest protein concentration (multiple of the KD) at or below which the sheet takes the plateau as not reached (conflicting); at the KD only half of the probe is shifted.
MIN_TITRATION_POINTS = 6  # EXPERT_REVIEW: fewest protein concentrations of a titration (usual gels have 8 to 12 lanes with protein; a KD and a plateau are poorly defined with fewer than six).
MIN_FRACTION_SHIFTED_HIGHEST = 80.0  # EXPERT_REVIEW: smallest percent of the probe shifted at the highest protein concentration for a plateau to be reached, for full agreement; below it the KD is extrapolated beyond the data (about the shifted fraction at five times the KD).
FRACTION_SHIFTED_ZERO_AGREEMENT = 50.0  # EXPERT_REVIEW: percent shifted at the highest protein concentration at or below which the sheet takes the plateau as not reached (conflicting); half of the probe shifted means the highest concentration is only the KD; in between the degree rises linearly.
MAX_SHIFTED_SPECIES = 1  # EXPERT_REVIEW: most shifted bands (distinct complexes) that one-site binding describes; more than one shifted species needs a model with more than one site (or Hill) for an apparent KD.
ONE_SITE_MODELS = ('one_site', 'quadratic')  # EXPERT_REVIEW: the fit models that describe one shifted species; several species fitted with one of them have a KD that is not a single constant.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); lanes of one gel do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'an_emsa_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_emsa_shifted_fraction_is_not_an_attribution_fraction', 'total_signal': 'an_emsa_shifted_fraction_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_emsa_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_emsa_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_specific_competition(native):
    if native['specific_competitor_excess'] < MIN_COMPETITOR_EXCESS:
        return _verdict('unknown', [])      # a competitor in so small an excess is not a test of specificity
    return _verdict('conflicting', native['specific_competition_refs'])


def _judge_equilibrium(native):
    if native['incubation_min'] < MIN_INCUBATION_MIN:
        return _verdict('conflicting', native['incubation_refs'])
    return _verdict('unknown', [])      # a long incubation alone does not show equilibrium


def _judge_probe(native):
    return _at_most(native['probe_over_kd'], MAX_PROBE_OVER_KD, PROBE_OVER_KD_ZERO_AGREEMENT, native['probe_over_kd_refs'])


def _judge_protein_range(native):
    refs = native['protein_range_refs']
    low, high = _at_most(native['protein_low_over_kd'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, refs), _at_least(native['protein_high_over_kd'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, refs)
    if 'conflicting' in (low['status'], high['status']):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(low['degree'], high['degree']))


def _judge_titration_points(native):
    return _verdict('supported' if native['titration_point_count'] >= MIN_TITRATION_POINTS else 'conflicting', native['titration_point_refs'])


def _judge_saturation(native):
    return _at_least(native['fraction_shifted_percent'], MIN_FRACTION_SHIFTED_HIGHEST, FRACTION_SHIFTED_ZERO_AGREEMENT, native['fraction_shifted_refs'])


def _judge_single_complex(native):
    if native['shifted_species_count'] <= MAX_SHIFTED_SPECIES:
        return _verdict('supported', native['shifted_species_refs'])
    if native['kd_nM'] is None:
        return _verdict('not_applicable', [])      # several species and no apparent KD: no constant for the criterion to bias
    if native['fit_model'] is None:
        return _verdict('unknown', [])
    return _verdict('conflicting' if native['fit_model'] in ONE_SITE_MODELS else 'supported', native['shifted_species_kd_refs'])


def _judge_fit_model_probe(native):
    return _at_most(native['probe_over_kd'], MAX_PROBE_OVER_KD, PROBE_OVER_KD_ZERO_AGREEMENT, native['fit_model_probe_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('specific_competition', 'competition_excess_recorded_for_the_sheet'): _judge_specific_competition, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium,
          ('probe_concentration', 'probe_over_kd_recorded_for_the_sheet'): _judge_probe, ('protein_range', 'protein_range_recorded_for_the_sheet'): _judge_protein_range,
          ('titration_points', 'titration_points_recorded_for_the_sheet'): _judge_titration_points, ('saturation', 'fraction_shifted_recorded_for_the_sheet'): _judge_saturation,
          ('single_complex', 'shifted_species_recorded_for_the_sheet'): _judge_single_complex, ('fit_model', 'one_site_probe_over_kd_recorded_for_the_sheet'): _judge_fit_model_probe,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if native['kd_nM'] is None:
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
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_emsa(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'emsa_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'emsa_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    if not quantitative:
        null_components['effect'] = 'qualitative_assay_reports_no_binding_constant'
        null_components['effect_variance'] = 'qualitative_assay_reports_no_binding_constant'
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [member for member in (apply_support(_criterion(graded, m), native['support'][m]) for m in members) if member['status'] != 'not_applicable']
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
        variance_fields = ['kd_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['protein_preparation_ref'], 'immobilized_preparation_ref': preparations['probe_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'emsa', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components,
                 'direction_field_support': native['quantities']['kd']['support'] if quantitative else (native['support']['shift_observed'] or [None])[0] if native['interaction'] is not None else None}
    if not quantitative:
        fraction = native['quantities']['fraction_shifted_highest']
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'fraction_shifted': fraction['value'] if fraction['status'] == 'point' else None}
    return converted
