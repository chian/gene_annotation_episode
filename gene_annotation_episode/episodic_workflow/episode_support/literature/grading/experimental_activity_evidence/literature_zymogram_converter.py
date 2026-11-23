"""Zymogram converter: turns the grader's result into what the A105 activity_rate sheet takes.

Hand-built, private to zymogram, deterministic. Input: the result of grade_zymogram. Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'activity_rate'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, the enzyme's molar mass key the activity direction
function reads (None here), the qualitative effect, and for every sheet component that an in-gel activity stain cannot honestly fill, the reason it stays null.
Drafted 2026-11-22 (owner to correct) on the shape of spectro_direct and of the qualitative types (colocalization, the no-constant branch of spr).

The effect is QUALITATIVE (the contract limit, stated plainly)
---------------------------------------------------------------
A zymogram reports that an activity band is seen (or not seen) at the position of the enzyme, no rate, no kcat, no Km and no specific activity; a band's
darkness or the size of a cleared zone is not a rate and never enters the record. The converter fills NO effect and no variance: the sheet's effect cells are
unavailable, with the reason 'qualitative_assay_reports_no_rate_or_constant' in null_components, and the extraction's quantity_kind is the class kind without an
effect ('rate'). What the experiment contributes is carried beside the sheet, in 'qualitative_effect' ({'statement', 'support_refs'}):
  statement      'interaction_detected' (read "activity detected": an activity band is stated), 'interaction_not_detected' (read "activity not detected": the paper
                 states that no activity band was detected) or 'interaction_not_stated'
  support_refs   the spans of the fact activity_band_detected, which states it (empty when not stated)
direction_field_support is the support class of that one fact (the statement is derived from it alone); None when it is not stated (no direction).
The vocabulary interaction_detected / interaction_not_detected / interaction_not_stated is kept and read for this class (decision 3 of 2026-11-21).
A measured result supports by its graded strength and never opposes; opposition comes here only from the paper itself stating that no activity band was detected.
A result stated in words alone already counts less than a measured one (the contract's stated_strength); it is not re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives   substrate_dependence_control + inactive_sample_control
calibration_applicability  stain_positive_control (a known active enzyme shows its band: the gel and the stain can show an activity)
measurement_identity      band_position (the apparent mass of the band against the mass expected from the sequence: does the band identify the construct)
attribution_supported     band_assignment + inhibitor_sensitivity
sampling_basis            replicates
assertion_relevance       native_substrate
condition_scope           purified_enzyme
Sheet criteria with no counterpart here (matrix_interference, variance_correspondence, rate_regime, normalization_basis, kinetic_model, partner_perturbation) are
not selected: a zymogram has no rate, no variance and no fitted model, and the sheet reports them as not selected. The thresholds are judged here, not in the
grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement).
Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value, falling smoothly to zero at a researched
no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states nothing, never conflicting for a short count. A
value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of
its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined
status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all
not_applicable is not selected.

How the class decisions apply here (2026-11-21, owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None. The
converter returns enzyme_mass_g_per_mol None (the activity direction function needs a molar mass only for a specific activity, which a zymogram does not state; the
expected mass of the record is a criterion's operand, not a conversion constant).

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads
and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner to
confirm.
-----------------------------------------------------------------------------------------------------------------------------------
MASS_FULL_FACTOR 1.2 -> MASS_ZERO_FACTOR 3.0, judged on the absolute natural log of the band mass over the expected mass.
  Q1 an activity band at a mass that is not the enzyme's: another enzyme of the sample (a co-migrating or contaminating protease or dehydrogenase) has been read as the
  enzyme. Q2 general for the gel, specific to the enzyme: the apparent mass of a protein on an SDS gel, read against marker proteins, is good to about ten percent for
  most soluble proteins, and glycosylated, lipidated, strongly acidic or membrane proteins and proteins that run as stable oligomers can depart by thirty percent or more
  (Weber and Osborn 1969 J Biol Chem 244:4406 for the accuracy, from memory; the departures are common knowledge of gel practice). A zymogen and its processed form differ by
  ten to twenty percent (the matrix metalloproteinases of gelatin zymography, for example 72 and 62 kDa, from memory), so a band at either is the enzyme. A zymogram of a
  native gel gives no mass; then no mass is stated and the criterion is unknown. Q3 relative to the paper's own expected mass (the grader records both); right. Q4 the
  error of the apparent mass is multiplicative, so the scale is the log of the ratio, and the same distance above and below the expected mass counts the same (a band
  half the expected mass is as far as a band twice it). Full agreement up to a factor 1.2 (the usual accuracy of the gel). The zero end is a factor 3: a band three times
  or a third of the expected mass cannot be put down to anomalous migration (rarely more than a factor of 1.5), and only a trimer or a fragment could explain it, so the
  band is another species (conflicting); between 1.2 and 3 the degree falls linearly in the log of the ratio, because a dimer (a factor of 2) or a processed form is a
  real possibility that the assignment criterion, not this one, decides. A wrong value moves only the degree of a criterion that carries the weight of a weak support;
  the direction comes from the statement alone. Q5 a log-ratio ramp like the other ratio judgements of the class (the enzyme over substrate plus Km, the fold gaps of the
  binding assays).
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a band seen on one gel, whose preparation-to-preparation and gel-to-gel spread is unseen (the renaturation and the development time vary from gel to gel). Q2 general
  (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the owner's replicate rule. Q5 exactly the shared replicate rule (spectro_direct,
  colocalization): independence stated yes gives the degree; independence not stated is unknown; a stated no is the grader's conflicting fact; a stated count is never
  conflicting.
Facts with no number (the controls, the band assignment, the inhibitor, the native substrate, the purified enzyme): the paper's own statement decides; yes is supported,
no is conflicting (for the inhibitor: unknown, see the criteria file), silence is unknown. They have no researched value to soften. NOT judged, and why: the
amount of protein loaded and the development time (they bound the sensitivity of the stain, which only a negative result needs, and papers state them with units and
purposes too varied for one researched value; recorded as a gap in the registration note); the gel concentration and the substrate concentration of the gel (method
settings, not evidence quality); the pH and the temperature of the development (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay,
drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? Whether something in the sample, at one position of the gel, acts on the substrate under the conditions of the gel: a
  relative, qualitative readout with no calibration and no rate. The assay says an activity exists; it does not say how large or whose it is.
  Is there a reference range we would trust if the paper stated less (as for KD)? No. There is no quantity whose usual range could stand in for an unstated detail; what
  stands in is common practice (a no-substrate lane and a boiled lane are usual in a figure), which a paper often leaves unsaid.
  What does an unstated control or calibration do to what the result means? An unstated no-substrate or inactive-sample lane leaves open that the band is a stain
  artefact (the tetrazolium stains colour a band for reasons other than the enzyme) or a non-enzymatic reaction: a real gap. An unstated band assignment, in an extract, is
  the central gap: the band may be another enzyme of the sample. An unstated positive control matters only for a negative result (an absent band says nothing if the
  stain did not work); it is benign for a band that is seen.
  If we assume it is fine and are wrong, how badly does the score mislead? A band of another enzyme is counted as the target's activity: the existence of the activity
  is wrong, not only its size; this is a worse error than for a rate (spectro_direct), and about as bad as a pull-down band that is a bead artefact.
  Consistent with KD and with the other types? The default 0.65 sits under pulldown and emsa (gel-based, relative; a stated band) and above colocalization and y2h (where
  the readout is further from the molecule); the criteria that guard against a false band are lower, the benign ones higher.
  default 0.65. background_alternatives 0.60 (the no-substrate and the inactive lanes are what tell an enzyme band from a stain artefact; usual in a figure, often not
  worded). attribution_supported 0.55 (the assignment of a band in an extract is the central gap). calibration_applicability 0.75 (benign for a band that is seen).
  measurement_identity 0.70 (a band mass is usually in the text when a mass is known; an unstated mass leaves the position unchecked, a small gap). sampling_basis 0.80
  (a gel shown is usually a representative of repeats; the count is benign when unstated). assertion_relevance and condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_zymogram_converted'
CRITERIA_MAP = {'background_alternatives': ('substrate_dependence_control', 'inactive_sample_control'), 'calibration_applicability': ('stain_positive_control',),
                'measurement_identity': ('band_position',), 'attribution_supported': ('band_assignment', 'inhibitor_sensitivity'), 'sampling_basis': ('replicates',),
                'assertion_relevance': ('native_substrate',), 'condition_scope': ('purified_enzyme',)}
MASS_FULL_FACTOR = 1.2  # EXPERT_REVIEW, owner to confirm, from memory not verified: the band mass within this factor of the expected mass (either side) gets full agreement: about the accuracy of an apparent mass read against marker proteins on an SDS gel (ten percent for most soluble proteins, a little more for processed forms; Weber and Osborn 1969), a zymogen and its processed form differ by about ten to twenty percent.
MASS_ZERO_FACTOR = 3.0  # EXPERT_REVIEW, owner to confirm, from memory not verified: a band three times or a third of the expected mass is another species (anomalous migration rarely exceeds a factor of 1.5; a dimer, factor 2, stays possible and is for the assignment criterion to decide): no agreement (conflicting); the degree falls linearly in the absolute log of the ratio from MASS_FULL_FACTOR to here, because the error of an apparent mass is multiplicative.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
KIND_WITHOUT_EFFECT = 'rate'   # the kind of an extraction that fills no effect (QUANTITY_KINDS['activity_rate']); a zymogram always fills none
NULL_REASONS = {'effect': 'qualitative_assay_reports_no_rate_or_constant', 'effect_variance': 'qualitative_assay_reports_no_rate_or_constant', 'recovery': 'a_zymogram_has_no_matrix_recovery_measurement',
                'attributed_signal': 'a_band_of_activity_is_not_an_attribution_fraction', 'total_signal': 'a_band_of_activity_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_zymogram_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_zymogram_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "activity detected" / "activity not detected" / "activity not stated" for this class


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


def _judge_band_position(native):
    # the distance of the band from the expected mass on the log scale, the same above and below; full up to MASS_FULL_FACTOR, zero at MASS_ZERO_FACTOR
    return _graded(native['band_position_refs'], (abs(math.log(native['band_over_expected'])), math.log(MASS_FULL_FACTOR), math.log(MASS_ZERO_FACTOR)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('band_position', 'band_position_recorded_for_the_sheet'): _judge_band_position, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def convert_zymogram(graded):
    native = graded['native']
    ref = graded['experiment_ref']
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'activity_rate', 'assertion_ref': native['assertion_ref'], 'quantity_kind': KIND_WITHOUT_EFFECT, 'quantities': dict.fromkeys(ROLES), 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'zymogram', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': dict(NULL_REASONS), 'direction_field_support': None, 'enzyme_mass_g_per_mol': None,
              'qualitative_effect': {'statement': STATEMENTS[native['activity']], 'support_refs': list(native['activity_refs'])}}
    if native['activity'] is not None:      # the paper's own statement of an activity band fixes the direction; its support is the support of the one fact it is derived from
        result['direction_field_support'] = native['activity_support']
    return result
