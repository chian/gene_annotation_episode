"""Pull-down / co-IP converter: turns the pull-down grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_pulldown.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding' and quantity_kind
'relative_binding_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the
qualitative effect, and for every sheet component that a pull-down cannot honestly fill, the reason it stays null.

The effect is QUALITATIVE (the contract limit, stated plainly)
---------------------------------------------------------------
A pull-down or co-IP reports no binding constant. The sheet's effect operand is a number (a point or a bounded value with a unit), and the
binding merger pools effects on the nM scale of the binding parameter, so there is nowhere in the sheet to put "the prey was detected in the
eluate". The converter therefore fills NO effect and no variance: the sheet's measured_effect, effect_variance and effect_precision cells are
unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: not a KD, and not the fold
enrichment or the percent of the input put into the effect (they are not on the nM scale and cannot be pooled with a constant).
What the experiment does contribute is carried beside the sheet, in 'qualitative_effect':
  statement          'interaction_detected' (the prey is stated in the eluate of the specific capture), 'interaction_not_detected' (it is stated not to be)
                     or 'interaction_not_stated'
  support_refs       the spans of the fact that states it (empty when not stated)
  fold_enrichment    the stated fold enrichment over the control (a number), or None
and its interpretations (controls, regime, species, response definition, calibration, sampling) go into the sheet's interpretations like those of every other
experiment. The scoring reads 'qualitative_effect', without an effect to pool: its statement fixes the direction
(literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (pull-down criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------------
binding_controls              negative_control + bait_minus_control + input_lane + reciprocal + competition + nuclease + specificity (the controls that
                              rule out a prey that sticks to beads, a tag artefact, a bridge of nucleic acid or an antibody that detects the wrong protein)
binding_regime                wash_stringency + wash_count + incubation (the strength of the wash a prey survives, and the time it had to bind)
binding_species               expression_level + direct_interaction (endogenous or overexpressed proteins, and purified proteins against a mixture)
binding_parameter_definition  prey_in_eluate + enrichment (what the response is: a prey in the eluate, and its signal over the control)
calibration_applicability     quantification (band intensities quantified and normalized)
sampling_basis                replicates
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). Continuous comparisons are supported with a degree of 1.0 at or beyond the full-agreement limit, the degree falling linearly
to 0 at the zero-agreement limit, and conflicting at or beyond that limit: wash_stringency (the salt and the detergent, each stated one judged, the weaker degree taken;
a conflicting one decides), incubation (time) and enrichment (fold). A count minimum gets no degree: wash_count (conflicting below MIN_WASHES, else supported) and
replicates (conflicting below MIN_REPLICATES, else supported when independent is yes, else unknown). A sheet criterion that is supported carries the smallest degree of its
members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result). The qualitative effect is unchanged.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree
(the continuous comparisons above); direct leaves it unchanged. Support never changes a status. The qualitative effect (its statement and
support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (measurement_identity, matrix_interference,
background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, variance_correspondence) are not selected, and
the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the prey,
immobilized_preparation_ref = the bait (held on the beads), surface_ref = None (a bead is not a surface reference), dataset_ref = the dataset.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_pulldown_converted_v1'
CRITERIA_MAP = {'binding_controls': ('negative_control', 'bait_minus_control', 'input_lane', 'reciprocal', 'competition', 'nuclease', 'specificity'), 'binding_regime': ('wash_stringency', 'wash_count', 'incubation'), 'binding_species': ('expression_level', 'direct_interaction'), 'binding_parameter_definition': ('prey_in_eluate', 'enrichment'), 'calibration_applicability': ('quantification',), 'sampling_basis': ('replicates',)}
MIN_WASH_NACL_MM = 150.0  # EXPERT_REVIEW: lowest sodium chloride (mM) of the wash buffer that still removes weakly and electrostatically stuck proteins, for full agreement (physiological salt; washes with less keep sticky preys, and usual pull-down washes use 150 to 500 mM).
WASH_NACL_ZERO_AGREEMENT_MM = 50.0  # EXPERT_REVIEW: sodium chloride (mM) at or below which the sheet takes the wash as removing no electrostatic binders (conflicting); a wash of a third of physiological salt or less is a low-salt wash that keeps them; in between the degree rises linearly.
MIN_WASH_DETERGENT_PERCENT = 0.05  # EXPERT_REVIEW: lowest detergent (percent) of the wash buffer for full agreement; below this the beads and the tube walls keep hydrophobic non-specific binders (usual washes use 0.05 to 1 percent of Triton X-100, NP-40 or Tween-20).
WASH_DETERGENT_ZERO_AGREEMENT_PERCENT = 0.0  # EXPERT_REVIEW: detergent (percent) at or below which the sheet takes the wash as removing no hydrophobic binders (conflicting); no detergent at all; in between the degree rises linearly.
MIN_WASHES = 3  # EXPERT_REVIEW: fewest washes of the beads after the capture; fewer leave unbound prey on the beads (usual protocols wash three to five times).
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: an incubation of bait with prey of at least this many minutes is full agreement; a shorter one is too short for a slow or weak interaction to be captured (usual protocols incubate one hour to overnight, at 4 C).
INCUBATION_ZERO_AGREEMENT_MIN = 5.0  # EXPERT_REVIEW: incubation (minutes) at or below which the sheet takes the incubation as capturing only an immediate strong interaction (conflicting); in between the degree rises linearly.
MIN_FOLD_ENRICHMENT = 3.0  # EXPERT_REVIEW: smallest signal of the prey in the specific capture over the control capture for full agreement; below about threefold the prey is hard to tell from the control background (the usual cut-off of affinity-purification mass spectrometry scoring is two to ten fold).
ENRICHMENT_ZERO_AGREEMENT_FOLD = 1.0  # EXPERT_REVIEW: fold enrichment at or below which the sheet takes the prey as not enriched over the control (conflicting); a signal equal to the control's is no enrichment; in between the degree rises linearly.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days, preparations or cultures); lanes or wells of one experiment do not count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_binding_constant', 'effect_variance': 'qualitative_assay_reports_no_binding_constant', 'recovery': 'a_pulldown_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_pulldown_band_is_not_an_attribution_fraction', 'total_signal': 'a_pulldown_band_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_pulldown_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_pulldown_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _enrichment(native):
    operand = native['quantities']['fold_enrichment']
    return operand['value'] if operand['status'] == 'point' else None


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _at_least(value, full, zero, refs):
    """Supported with degree 1.0 at or above the full-agreement limit, falling linearly to 0 at the zero-agreement limit; conflicting at or below it."""
    if value <= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (value - zero) / (full - zero)))


def _judge_wash(native):
    """Each stated component (salt, detergent) is judged; one that is conflicting decides (the salt first), else supported with the weaker degree and the refs of both."""
    parts = []
    if native['nacl_wash_mM'] is not None:
        parts.append(_at_least(native['nacl_wash_mM'], MIN_WASH_NACL_MM, WASH_NACL_ZERO_AGREEMENT_MM, native['nacl_wash_refs']))
    if native['detergent_percent'] is not None:
        parts.append(_at_least(native['detergent_percent'], MIN_WASH_DETERGENT_PERCENT, WASH_DETERGENT_ZERO_AGREEMENT_PERCENT, native['detergent_wash_refs']))
    for part in parts:
        if part['status'] == 'conflicting':
            return part
    return _verdict('supported', list(dict.fromkeys(r for part in parts for r in part['support_refs'])), min(part['degree'] for part in parts))


def _judge_wash_count(native):
    return _verdict('supported' if native['wash_count'] >= MIN_WASHES else 'conflicting', native['wash_count_refs'])


def _judge_incubation(native):
    return _at_least(native['incubation_min'], MIN_INCUBATION_MIN, INCUBATION_ZERO_AGREEMENT_MIN, native['incubation_refs'])


def _judge_enrichment(native):
    return _at_least(native['fold_enrichment'], MIN_FOLD_ENRICHMENT, ENRICHMENT_ZERO_AGREEMENT_FOLD, native['fold_enrichment_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('wash_stringency', 'wash_recorded_for_the_sheet'): _judge_wash, ('wash_count', 'wash_count_recorded_for_the_sheet'): _judge_wash_count, ('incubation', 'incubation_recorded_for_the_sheet'): _judge_incubation,
          ('enrichment', 'fold_enrichment_recorded_for_the_sheet'): _judge_enrichment, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def convert_pulldown(graded):
    native = graded['native']
    ref = graded['experiment_ref']
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'relative_binding_response', 'quantities': dict.fromkeys(ROLES), 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['prey_preparation_ref'], 'immobilized_preparation_ref': preparations['bait_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    qualitative_effect = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'fold_enrichment': _enrichment(native)}
    return {'version': VERSION, 'experiment_type': 'pulldown', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'qualitative_effect': qualitative_effect, 'null_components': dict(NULL_REASONS), 'direction_field_support': (native['support']['prey_in_eluate'] or [None])[0] if native['interaction'] is not None else None}
