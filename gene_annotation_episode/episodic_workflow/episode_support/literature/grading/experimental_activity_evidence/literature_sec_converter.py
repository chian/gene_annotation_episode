"""SEC converter: turns the SEC grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_sec.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that an SEC
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (a titration read from the peak areas). Then the converter fills the numeric effect as the earlier quantitative
types do (quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key sec_kd). It is an APPARENT constant, with the caveats of the method (the sample
                    is diluted on the column, so a weak complex dissociates; the complex is read at the concentration of the peak, not of the injection); those
                    caveats are not changed in the number, they are judged by the criteria (complex_stable_on_column, stoichiometry, titration_depletion,
                    monodispersity) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no apparent KD (a complex peak, its shift and its mass are shown). Then, exactly as the pull-down and EMSA converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the shift of
the elution volume nor the molar mass is put into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet,
in 'qualitative_effect' ({'statement', 'support_refs', 'elution_shift_ml'}):
  statement          'interaction_detected' (a complex peak is stated), 'interaction_not_detected' (no complex peak is stated) or 'interaction_not_stated'
  support_refs       the spans of the fact that states it (empty when not stated)
  elution_shift_ml   the shift of the elution volume in mL (stated, or the difference of the two stated volumes), or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (SEC criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              components_alone + complex_composition + single_component_control + resin_interaction + monodispersity (the controls that
                              show the early peak is a complex of these two proteins and not a component alone, an aggregate or a resin effect)
binding_regime                complex_stable_on_column + titration_depletion (the complex survives the dilution on the column; the free peak is used up as the
                              complex grows)
binding_parameter_definition  complex_peak_observed + elution_shift + mals_mass + stoichiometry (what the response is: a complex peak, its shift, its mass and its
                              composition)
calibration_applicability     column_calibration (the column is calibrated with standards)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement): elution_shift supported at a shift of at least MIN_ELUTION_SHIFT_ML else conflicting; stoichiometry supported within STOICHIOMETRY_TOLERANCE
of 1 else conflicting; resin_interaction supported at a salt of at least MIN_SALT_MM else unknown; complex_stable_on_column supported at a load of at least MIN_LOAD_OVER_KD times
the KD else conflicting; monodispersity supported at a polydispersity of at most MAX_POLYDISPERSITY else conflicting; replicates conflicting below MIN_REPLICATES, else supported
when the independence is yes, else unknown; mals_mass is supported with a degree of 1.0 at an absolute deviation of at most MASS_FULL_AGREEMENT_PERCENT, the degree falling linearly to 0 at
MASS_ZERO_AGREEMENT_PERCENT, and conflicting (no degree) at or above it. A sheet criterion that is supported carries the smallest degree of its members that have one (the
sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree (the
mass criterion's degree from the deviation, for example); direct leaves it unchanged. Support never changes a status. variance_correspondence takes
the weakest support of the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is
not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first component,
immobilized_preparation_ref = the second component, surface_ref = None (a column is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_sec_converted_v1'
CRITERIA_MAP = {'binding_controls': ('components_alone', 'complex_composition', 'single_component_control', 'resin_interaction', 'monodispersity'), 'binding_regime': ('complex_stable_on_column', 'titration_depletion'), 'binding_parameter_definition': ('complex_peak_observed', 'elution_shift', 'mals_mass', 'stoichiometry'), 'calibration_applicability': ('column_calibration',), 'sampling_basis': ('replicates',)}
MIN_ELUTION_SHIFT_ML = 0.3  # EXPERT_REVIEW: smallest shift (mL) of the complex peak below the earlier-eluting component alone that counts as a resolved complex peak; peaks on an analytical column of about 24 mL are about 1 mL wide at the base, so a smaller shift overlaps the component peak.
MAX_POLYDISPERSITY = 1.05  # EXPERT_REVIEW: largest Mw/Mn of a monodisperse peak (the usual MALS reading of a monodisperse protein is below 1.05; above it the peak holds a mixture of species such as aggregates).
MIN_LOAD_OVER_KD = 10.0  # EXPERT_REVIEW: the injected concentration must be at least this multiple of the KD; the sample is diluted about ten- to twenty-fold on the column, so below it the complex dissociates in the peak and a KD is not read at the concentration of the injection.
MIN_SALT_MM = 100.0  # EXPERT_REVIEW: smallest concentration (mM) of monovalent salt in the running buffer that is taken to rule out ionic interaction with the resin when the passage does not say so (the usual SEC buffer holds 100 to 150 mM NaCl; below about 50 mM the resin interacts with charged proteins).
STOICHIOMETRY_TOLERANCE = 0.1  # EXPERT_REVIEW: largest distance of the stated stoichiometry from 1 (1:1) at which a KD from peak areas is the one-site constant; another ratio (2:1, 1:2) needs more than one binding step and its apparent KD is not a single constant.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); injections of one sample do not count.
MASS_FULL_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: largest absolute deviation (percent) of the MALS molar mass of the complex peak from the mass the complex should have that the sheet takes as agreement (supported); MALS is accurate to about 5 to 10 percent.
MASS_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: absolute deviation (percent) from which the sheet takes the mass as disagreeing (conflicting); half the mass or less, or 1.5 times or more, is a different species; in between the sheet's statuses cannot say how much agreement there is, so it is unknown.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'an_sec_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_sec_complex_peak_is_not_an_attribution_fraction', 'total_signal': 'an_sec_complex_peak_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_sec_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_sec_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _judge_mass(native):
    """Supported with a degree from 1.0 (deviation at most MASS_FULL_AGREEMENT_PERCENT) falling linearly to 0 at MASS_ZERO_AGREEMENT_PERCENT; conflicting from there on."""
    deviation = abs(native['mass_deviation_percent'])
    if deviation >= MASS_ZERO_AGREEMENT_PERCENT:
        return _verdict('conflicting', native['mass_support_refs'])
    return _verdict('supported', native['mass_support_refs'], min(1.0, (MASS_ZERO_AGREEMENT_PERCENT - deviation) / (MASS_ZERO_AGREEMENT_PERCENT - MASS_FULL_AGREEMENT_PERCENT)))


def _judge_shift(native):
    return _verdict('supported' if native['shift_ml'] >= MIN_ELUTION_SHIFT_ML else 'conflicting', native['shift_refs'])


def _judge_stoichiometry(native):
    return _verdict('supported' if abs(native['stoichiometry_ratio'] - 1) <= STOICHIOMETRY_TOLERANCE else 'conflicting', native['stoichiometry_refs'])


def _judge_salt(native):
    return _verdict('supported' if native['salt_mM'] >= MIN_SALT_MM else 'unknown', native['salt_refs'])      # a low salt does not show an interaction


def _judge_load(native):
    return _verdict('supported' if native['load_over_kd'] >= MIN_LOAD_OVER_KD else 'conflicting', native['load_refs'])


def _judge_polydispersity(native):
    return _verdict('supported' if native['polydispersity'] <= MAX_POLYDISPERSITY else 'conflicting', native['polydispersity_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('mals_mass', 'mass_deviation_recorded_for_the_sheet'): _judge_mass, ('elution_shift', 'elution_shift_recorded_for_the_sheet'): _judge_shift,
          ('stoichiometry', 'stoichiometry_recorded_for_the_sheet'): _judge_stoichiometry, ('resin_interaction', 'salt_recorded_for_the_sheet'): _judge_salt,
          ('complex_stable_on_column', 'load_over_kd_recorded_for_the_sheet'): _judge_load, ('monodispersity', 'polydispersity_recorded_for_the_sheet'): _judge_polydispersity,
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


def convert_sec(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'sec_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'sec_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
        variance_fields = ['kd_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['component_a_preparation_ref'], 'immobilized_preparation_ref': preparations['component_b_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'sec', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities']['kd']['support']      # the support class of the KD operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'elution_shift_ml': native['shift_ml']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['complex_peak_observed'][0]      # the support class of the fact complex_peak_detected, the one field the statement is derived from
    return converted
