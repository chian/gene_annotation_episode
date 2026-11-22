"""BLI converter: turns the BLI grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to BLI, deterministic. Input: the result of grade_bli.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR and ITC converters fill), the dependence
keys the merger needs, and for every sheet component that a KD measurement
cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the BLI KD in nM (point operand), only when the source
                  gave a KD as a point value. A KD the source did not give
                  leaves effect null.
                  With no KD the result is the experiment's stated yes/no
                  result (fact binding_detected): 'qualitative_effect'
                  carries its statement (interaction_detected,
                  interaction_not_detected, or interaction_not_stated when
                  the passage states neither) and the spans that state it.
effect_variance   variance of that KD estimate, nM_squared, only when the
                  source's spread allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n, and only when the
                  replicates criterion is supported (n independent
                  replicates on separate sensors); confidence_interval -> not
                  converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the SPR and ITC
converters): analyte_preparation_ref = the analyte in the well,
immobilized_preparation_ref = the partner loaded on the sensor, surface_ref =
the record's sensor_ref (the sensor or sensor lot), dataset_ref = the dataset.

Criteria mapping (BLI criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              reference_subtraction +
                              nonspecific_binding_control +
                              baseline_and_regeneration
binding_regime                concentration_series + dissociation_window +
                              avidity_and_mass_transport +
                              steady_state_vs_kinetic
binding_parameter_definition  fit_model + kinetic_consistency
binding_species               immobilized_activity
calibration_applicability     loading_and_response (the sensor loading and
                              the response against the instrument's usable
                              range: BLI's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and
hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement): loading_and_response judged on
the loading level (full agreement at most LOADING_MAX_NM) and the maximum
response (full agreement at least RESPONSE_MIN_NM), unknown when one of them or
the documentation of the loading is not given; concentration_series judged on
the number of concentrations (full agreement from MIN_CONCENTRATIONS, partial
credit below it on a concave curve that reaches no credit at
SERIES_ZERO_CONCENTRATIONS for an isotherm (steady-state or unstated) fit and at
SERIES_ZERO_CONCENTRATIONS_KINETIC for a kinetic fit (KINETIC_FIT_MODELS); a
short series is weaker evidence, supported with that low degree, never
conflicting), the lowest over the KD (full agreement at most LOW_FACTOR; for an
isotherm fit falling linearly to LOW_ZERO_FACTOR, for a kinetic fit the free
fraction (1 + LOW_FACTOR) / (1 + low), never conflicting) and the highest over
the KD (full agreement at least HIGH_FACTOR); fit_model judged on the fit
R-squared (full agreement at least FIT_R_SQUARED_MIN), unknown for a 1:1 model
whose bivalence is not answered no; dissociation_window judged on the decayed
fraction (full agreement at least DISSOCIATION_DECAY_MIN) and, when the source
gives the maximum response, on the decayed signal (fraction x response, on the
RESPONSE_MIN_NM / RESPONSE_ZERO_NM noise ramp); replicates supported with
degree min(1, sqrt(n / MIN_REPLICATES)) when the independence is yes (never
conflicting for a stated count), unknown when it is not stated (a stated no is
the grader's conflicting); kinetic_consistency judged on the fold between
koff/kon and the KD, either way (full agreement at most KINETIC_FOLD_MAX, linear
in the log of the fold to KINETIC_ZERO_FOLD); steady_state_vs_kinetic judged on
the fold between the two KDs (full agreement at most AGREEMENT_FACTOR, linear
in the log of the fold to AGREEMENT_ZERO_FACTOR). A continuous comparison is
supported with a degree of 1.0 at its full-agreement limit, falling to 0 at its
zero-agreement limit (the *_ZERO_* constants), and, for a value (not a count,
not the kinetic low end), conflicting (no degree) at or beyond that limit:
what the paper itself states is at or past the point of no agreement. A sheet criterion that is supported
carries the smallest degree of its members that have one (the sheet reads no
degree; it travels with the interpretation and the merger carries it per
result).
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no BLI counterpart (measurement_identity, matrix_interference,
background_alternatives, attribution_supported, assertion_relevance,
condition_scope, binding_comparison) are not selected, and the sheet reports
them as not selected.

Range review: the owner's five questions, per researched value (2026-11-21; Q1 what it protects against, Q2 general
practice or lab/instrument-specific, Q3 absolute or relative scale and whether the grader has the quantity, Q4 how
badly a wrong value misleads and whether the shape fits, Q5 consistency with the other binding assays). Method
sources: Myszka 1999 J Mol Recognit 12:279 (improving biosensor analysis); Abdiche et al. 2008 Anal Biochem 377:209
(Octet kinetics and affinities); Concepcion et al. 2009 Comb Chem HTS 12:791 (BLI kinetic characterisation); Kamat &
Rafique 2017 Anal Biochem 536:16 (designing BLI kinetic assays: loading density, avidity); Wartchow et al. 2011
J Comput Aided Mol Des 25:669 (small-molecule BLI on densely loaded sensors); Pollard 2010 Mol Biol Cell 21:4061 and
Jarmoskaite et al. 2020 eLife 9:e57264 (binding-series design); Cumming et al. 2007 J Cell Biol 177:7 (replicates).
Physics used below: in a kinetic fit kobs = kon C + koff, so kobs / koff = 1 + C / KD; koff comes from the
dissociation step on its own.
  MIN_CONCENTRATIONS 5 / SERIES_COUNT_CURVE_POWER 2 / SERIES_ZERO_CONCENTRATIONS 1: Q1 a KD whose concentration
    dependence (and the 1:1 model) was never tested. Q2 general (5 to 8 two- or three-fold steps; Abdiche 2008, Myszka
    1999). Q3 a count, absolute; its placement is the span below. Q4 MISTAKE for a kinetic fit: zero credit at one
    concentration came from isotherm reasoning, but one association/dissociation pair already gives kon and koff, so the
    KD is measured (untested), not absent; a steady-state isotherm has two unknowns (KD, Rmax) and one point gives no KD.
    CHANGED: the zero end is the count the fit needs to give a KD, minus one (EMSA's rule: the KD itself is one unit of
    credit): isotherm or model not stated 1 (kept: 2 -> 0.44, 3 -> 0.75, 4 -> 0.94), kinetic 0 (new
    SERIES_ZERO_CONCENTRATIONS_KINETIC: 1 -> 0.36 (was 0), 2 -> 0.64, 3 -> 0.84, 4 -> 0.96). Concave kept (the 2nd and
    3rd concentrations add the concentration dependence and the first 1:1 check, the 4th and 5th mostly redundancy).
    Q5 never conflicting, as rule 2 asks.
  LOW_FACTOR 0.2 / LOW_ZERO_FACTOR 1.0: Q1 a KD read from one arm of the curve (no concentration samples the free
    branch). Q2 general (0.1x to 10x KD, 0.2x with slack; Pollard 2010, Jarmoskaite 2020). Q3 relative to the paper's
    own KD: already so. Q4 MISTAKE for a kinetic fit: a series lying wholly above the KD is the usual design for tight
    (antibody, sub-nM) binders and still measures kon from kobs and koff from the dissociation, yet it was made
    conflicting and sank binding_regime. For an isotherm (steady-state, model 'other' or not stated) the lower arm is
    half the curve: the linear 0.2 -> 1.0 ramp, conflicting at 1x, kept. CHANGED for KINETIC_FIT_MODELS: degree =
    (1 + LOW_FACTOR) / (1 + low), the free fraction at the lowest concentration relative to that at 0.2x (1x 0.6, 3x
    0.3, 10x 0.11): gentle, reaches 0 only at full saturation, so never conflicting. Q5 SPR and GCI use the same linear
    ramp for their kinetic KDs; the same reasoning applies there (flagged, not changed here).
  HIGH_FACTOR 5 / HIGH_ZERO_FACTOR 1: Q1 kon not separable from koff and the plateau not reached. Q2 general (10x KD,
    5x with slack). Q3 relative to the KD: already so. Q4 linear in C/KD is linear in kobs/koff, the kinetic
    information itself: at a top concentration at the KD the kobs of the whole series spans at most 2-fold and kon is a
    difference of two near-equal rates, so conflicting there is right. KEPT. Q5 SPR, GCI, EMSA 5 / 1: the same.
  FIT_R_SQUARED_MIN 0.95 / FIT_R_SQUARED_ZERO 0.80: Q1 a KD from a model that does not describe the sensorgrams. Q2
    instrument-software guidance (Octet: R-squared above 0.95 with a small Chi-squared), widely quoted, not a method
    paper. Q3 R-squared is already relative (unexplained fraction of the variance) but rises with the signal span, so a
    large response hides a systematic misfit; Chi-squared or residuals relative to the response would be better and are
    not collected (grader gap). Q4 linear in R-squared is linear in the unexplained variance (5 -> 20 percent): adequate.
    KEPT. Q5 BRET 0.95 / 0.80: the same.
  LOADING_MAX_NM 2.0 / LOADING_ZERO_NM 4.0: Q1 a crowded tip: rebinding and avidity slow the apparent koff and tighten
    the KD. Q2 vendor and method guidance for protein analytes (about 1 to 2 nm; Abdiche 2008, Kamat & Rafique 2017);
    sensor- and size-specific: the shift per molecule grows with the loaded partner's mass, and small-molecule BLI loads
    densely on purpose (Wartchow 2011), where 4 nm is normal and the rule misleads (conflicting). Q3 should be relative
    to the analyte/partner masses (expected response from the loading, BLI's Rmax ratio); the masses are not collected
    (grader gap). Q4 for protein analytes rebinding grows with density; linear between 2 and 4 nm adequate. KEPT, with
    the gap. Q5 GCI's immobilization ramp (2 -> 4 ng/mm2) is the same idea.
  RESPONSE_MIN_NM 0.05 / RESPONSE_ZERO_NM 0.01: Q1 a "binding" response that is baseline noise or drift. Q2
    instrument-specific: 0.01 nm is the noise of the smaller instruments; RED96e/RED384-class instruments are quieter
    (a few pm), where 0.02 nm is a real signal. Q3 should be relative to the paper's reference-sensor signal or stated
    noise; not collected (grader gap). Q4 linear in nm is linear in signal-to-noise (1x to 5x noise): adequate. KEPT.
    Q5 GCI's response ramp: the same.
  DISSOCIATION_DECAY_MIN 0.05 / DISSOCIATION_DECAY_ZERO 0.01: Q1 a koff extrapolated from a window in which the
    complex barely dissociated (tight binders; BLI's open-well dissociation is limited by drift). Q2 general
    biosensor practice (at least 5 percent decay; Myszka 1999; Octet guidance). Q3 relative to the signal already, but a
    fraction alone ignores how much signal there was: 5 percent of a 0.1 nm response is 0.005 nm, below the noise, so
    koff is not measured. The grader has the maximum response: CHANGED (in addition, not instead): the decayed signal
    (fraction x maximum response) is also judged on the RESPONSE_ZERO_NM -> RESPONSE_MIN_NM ramp (koff's precision is
    about noise / decayed signal: 5x noise is about 20 percent, the KINETIC_FOLD_MAX tolerance; 1x noise is no
    measurement), the smaller degree counts; no new number. The maximum response is the most favourable curve. Q4
    linear 1 -> 5 percent kept (the koff error is inversely proportional to the decay). Q5 SPR has no response-based
    decay check (flagged).
  MIN_REPLICATES 3: Q1 a KD from one sensor/run (sensor-to-sensor loading and lot variation). Q2 general (three
    independent experiments; Cumming 2007). Q3 a count, absolute. Q4 sqrt(n / 3), the precision of a mean (1 -> 0.58,
    2 -> 0.82). KEPT. Q5 rule 1: the same in every binding assay.
  KINETIC_TOLERANCE 0.20 / KINETIC_ZERO_TOLERANCE 0.8 -> KINETIC_FOLD_MAX 1.2 / KINETIC_ZERO_FOLD 1.8: Q1 a reported KD
    that is not the koff/kon of the same fit (another analysis, a unit or transcription error). Q2 general: for one
    fit KD = koff/kon by definition; 1.2-fold covers two-figure rounding and replicate averaging, 1.8-fold one-figure
    rounding of a rate. Q3 relative to the paper's own KD: already so. Q4 MISTAKE: the relative gap |r - 1| was
    asymmetric (koff/kon at half the KD got 0.5, at 1.8 times the KD conflicting; the old comment's 0.8 only patched
    it), though a factor off either way is the same inconsistency. CHANGED to the fold max(r, 1/r) with the same ends
    (1.2 full, 1.8 zero), linear in the log of the fold like steady_state_vs_kinetic: half the KD is now conflicting
    (was 0.5), 0.8x 0.90 (was 1.0). Q5 SPR and GCI carry the same asymmetry (flagged).
  AGREEMENT_FACTOR 2 / AGREEMENT_ZERO_FACTOR 10: Q1 a KD that depends on the analysis (heterogeneity, rebinding,
    avidity, a non-1:1 process). Q2 general (kinetic and steady-state KDs agree within about 2-fold for a clean 1:1
    interaction; Myszka 1999). Q3 already a symmetric fold of the paper's own two KDs. Q4 the fold is multiplicative and
    the KD is used on a log scale (the strength anchors), so each doubling of disagreement should cost the same; linear
    in the fold under-penalised 3- to 5-fold gaps (3-fold 0.875). CHANGED to linear in the log of the fold, values
    kept: 3-fold 0.75, 4-fold 0.57, 6-fold 0.32. Q5 FCS's mass-consistency fold is linear in its log; SPR and GCI
    are linear in the fold (flagged).
  Grader gaps closed (2026-11-21), each with the owner's questions:
    partner mass (LOADING_REFERENCE_MASS_KDA 50): Q1 a dense loading read as a crowded tip when the partner is large.
    Q2 the 2 / 4 nm ends are protein-partner practice; Q3 the physics is relative (molar density = nm / mass), the
    grader now records the stated partner mass; Q4 unstated mass: the old absolute ends (unchanged); a large partner
    now gets proportionally higher ends (continuous); a small partner keeps the absolute ends because the coating
    limits density; Q5 GCI has the same gap (flagged). NOT added: the analyte mass and a theoretical response from the
    loading: it needs the stoichiometry and the active fraction of the loaded partner, neither of which a passage
    states reliably, so a response far below the theoretical value would be read as bad quality when it is often
    inactivity or sub-stoichiometric binding (already asked by immobilized_activity).
    stated baseline noise (SIGNAL_TO_NOISE_FULL 5, derived): Q1 a response or decayed signal that is noise. Q3 relative
    to the paper's own noise, now collected (baseline_noise); the reference-sensor signal was not added (it is
    subtracted before the noise level is read, so the stated noise is the same fact and is stated more often).
    Q4 unstated noise: the fixed ends (unchanged); stated noise: zero at the noise, full at 5x, still linear in
    signal-to-noise.
    Not added: Chi-squared (the Octet X2 is software- and normalisation-specific and the owner-approved ends of the
    other binding assays are not transferable; R-squared stays); a koff-above-resolution check (new criterion).
  Unknown weight: this converter holds none and no degree contains one (rule 3); the BLI weights (0.85, BC 0.80) live
    in literature_row_contract.py.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_bli_converted_v1'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
CRITERIA_MAP = {'binding_controls': ('reference_subtraction', 'nonspecific_binding_control', 'baseline_and_regeneration'), 'binding_regime': ('concentration_series', 'dissociation_window', 'avidity_and_mass_transport', 'steady_state_vs_kinetic'), 'binding_parameter_definition': ('fit_model', 'kinetic_consistency'), 'binding_species': ('immobilized_activity',), 'calibration_applicability': ('loading_and_response',), 'sampling_basis': ('replicates',)}
MIN_CONCENTRATIONS = 5  # EXPERT_REVIEW: fewest analyte concentrations for a usable titration series (BLI series are usually 6 to 8 steps); full agreement from it.
KINETIC_FIT_MODELS = ('1:1', '2:1_bivalent_analyte', 'heterogeneous_ligand')  # EXPERT_REVIEW: the fit models whose KD is koff/kon from the sensorgrams (kobs = kon x C + koff, koff from the dissociation step); 'steady_state', 'other' and a model not stated are judged as an isotherm (the stricter rules) because the KD may then be read from the plateau responses.
SERIES_ZERO_CONCENTRATIONS = 1  # EXPERT_REVIEW: isotherm fit (steady-state, 'other' or model not stated): the isotherm has two unknowns (KD and Rmax), so one concentration gives no KD at all and two give a KD with no check; zero credit at one (degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against); the credit rises from it to MIN_CONCENTRATIONS on the curve below.
SERIES_ZERO_CONCENTRATIONS_KINETIC = 0  # EXPERT_REVIEW: kinetic fit (KINETIC_FIT_MODELS): one association/dissociation pair already gives kon (from kobs) and koff, so a single concentration measures the KD (untested); the zero end is the count that gives no KD, none, so one concentration gets low partial credit (0.36) instead of none.
SERIES_COUNT_CURVE_POWER = 2  # EXPERT_REVIEW: shape of the rise from the zero end to MIN_CONCENTRATIONS, d = 1 - ((MIN - n) / (MIN - ZERO))^power: concave, because in a BLI global fit (kobs = kon x C + koff) the second concentration gives the concentration dependence and the third the first check of the 1:1 model, while the fourth and fifth mostly add redundancy against one bad sensor tip; a power of 2 flattens into full credit at MIN_CONCENTRATIONS with no kink.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest concentration should be at most this multiple of KD (0.1x with a factor of 2 slack); full agreement up to it. Kinetic fit: above it the degree is the free fraction at the lowest concentration relative to that at LOW_FACTOR, (1 + LOW_FACTOR) / (1 + low), never conflicting (a series wholly above the KD still measures kon from kobs and koff from the dissociation; it only leaves the free branch untested).
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: isotherm fit: lowest concentration at the KD itself leaves the lower half of the binding curve undefined, so no agreement; falls linearly from LOW_FACTOR. Not used for a kinetic fit (see LOW_FACTOR).
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest concentration should be at least this multiple of KD (10x with a factor of 2 slack); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: highest concentration at the KD itself never reaches saturation, so no agreement; falls linearly from HIGH_FACTOR.
FIT_R_SQUARED_MIN = 0.95  # EXPERT_REVIEW: a fit R-squared below this is a poor fit by the usual Octet analysis guidance; full agreement from it.
FIT_R_SQUARED_ZERO = 0.80  # EXPERT_REVIEW: an R-squared of 0.80 means a fifth of the signal variance is not described by the model, so the fit does not describe the data (no agreement); falls linearly from FIT_R_SQUARED_MIN.
LOADING_MAX_NM = 2.0  # EXPERT_REVIEW: above about 2 nm of loaded partner the sensor is crowded and rebinding and avidity distort the kinetics; full agreement up to it.
LOADING_ZERO_NM = 4.0  # EXPERT_REVIEW: twice the crowding limit, the sensor is saturated and the kinetics are dominated by rebinding (no agreement); falls linearly from LOADING_MAX_NM.
RESPONSE_MIN_NM = 0.05  # EXPERT_REVIEW: a maximum response below this is within a few multiples of the instrument's noise (about 0.01 nm); full agreement from it.
RESPONSE_ZERO_NM = 0.01  # EXPERT_REVIEW: the instrument's noise level (about 0.01 nm): a response this small is not a signal (no agreement); falls linearly from RESPONSE_MIN_NM.
SIGNAL_TO_NOISE_FULL = RESPONSE_MIN_NM / RESPONSE_ZERO_NM  # EXPERT_REVIEW (derived, no new number): when the paper states its own baseline noise N, the response ramp is zero at N (a response no larger than the noise is no signal) and full at N x this (5, the same ratio as the fixed ends: koff/kon precision about noise / signal, 5x noise about 20 percent). Replaces the fixed 0.01 nm noise, which is instrument-class specific.
LOADING_REFERENCE_MASS_KDA = 50.0  # EXPERT_REVIEW: the partner mass (a typical recombinant protein, 30 to 70 kDa) for which LOADING_MAX_NM / LOADING_ZERO_NM are the crowding limits. When the paper states the partner mass above it, both ends scale with mass / this (the shift per molecule is proportional to the mass, so the same molar sensor density reads n times the nm); below it they stay (the coating limits the density). Continuous in the mass, no step.
DISSOCIATION_DECAY_MIN = 0.05  # EXPERT_REVIEW: the signal must decay at least this fraction in the dissociation window for koff to be measured, not extrapolated; full agreement from it.
DISSOCIATION_DECAY_ZERO = 0.01  # EXPERT_REVIEW: a decay of one percent is within the baseline noise, so koff is not measured at all (no agreement); falls linearly from DISSOCIATION_DECAY_MIN. In addition, when the source gives the maximum response, the decayed signal (decay x response) is judged on the RESPONSE_ZERO_NM -> RESPONSE_MIN_NM noise ramp (koff's precision is about noise / decayed signal).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent replicate experiments (on separate sensors); full agreement from it. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of the mean KD over n independent sensors (loading, sensor lot) falls as 1 / sqrt(n), the same sd^2 / n this converter uses for the effect variance; 1 run about 0.58, 2 about 0.82; never conflicting for a stated count.
KINETIC_FOLD_MAX = 1.2  # EXPERT_REVIEW: allowed fold between the KD and koff/kon, either way (was KINETIC_TOLERANCE 0.20 as a one-sided relative gap); for one fit they are equal by definition, 1.2-fold covers two-figure rounding of the rates and replicate averaging; full agreement up to it.
KINETIC_ZERO_FOLD = 1.8  # EXPERT_REVIEW: a 1.8-fold gap either way (beyond one-figure rounding of one rate) means the rates do not describe the reported KD (no agreement); was KINETIC_ZERO_TOLERANCE 0.8 on the asymmetric relative gap, which allowed koff/kon down to a fifth of the KD; falls linearly in the log of the fold from KINETIC_FOLD_MAX.
AGREEMENT_FACTOR = 2.0  # EXPERT_REVIEW: allowed fold gap between steady-state KD and kinetic KD; full agreement up to it.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: a tenfold gap between the two KD estimates is a different binding event (no agreement); falls linearly in the log of the fold from AGREEMENT_FACTOR (the KD is used on a log scale, so each doubling of the gap costs the same).
NULL_REASONS = {'recovery': 'bli_has_no_matrix_recovery_measurement', 'attributed_signal': 'bli_reference_subtraction_is_not_an_attribution_fraction', 'total_signal': 'bli_reference_subtraction_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_bli_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_bli_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _ramp(value, full, zero):
    """1.0 at the full-agreement limit, falling linearly to 0 at the zero-agreement limit (unclipped: above 1 past the full limit, at or below 0 at or past the zero limit)."""
    return (zero - value) / (zero - full)


def _log_ramp(fold, full, zero):
    """The same ramp for a fold (at least 1), linear in its logarithm: each doubling costs the same."""
    return math.log(zero / fold) / math.log(zero / full)


def _graded(refs, *degrees):
    """Conflicting when any degree is at or below 0 (a value at or past its zero limit); else supported with the smallest degree, capped at 1.0."""
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _noise_ends(native):
    """(full, zero) of the response ramp in nm: the paper's own stated baseline noise N when given (zero at N, full at N x SIGNAL_TO_NOISE_FULL), else the fixed instrument-class ends. Plus the refs of the noise when used."""
    noise = native['baseline_noise_nm']
    if noise is None:
        return RESPONSE_MIN_NM, RESPONSE_ZERO_NM, []
    return noise * SIGNAL_TO_NOISE_FULL, noise, native['noise_refs']


def _loading_ends(native):
    """(full, zero) of the loading ramp in nm: scaled up with the partner's mass above LOADING_REFERENCE_MASS_KDA (a partner of n times the mass carries n times the shift per molecule, so the same molar density is n times the nm); never scaled down (a small partner cannot crowd the sensor by a smaller nm: the coating, not the shift, limits the density). Plus the refs of the mass when used."""
    mass = native['partner_mass_kda']
    if mass is None:
        return LOADING_MAX_NM, LOADING_ZERO_NM, []
    scale = max(1.0, mass / LOADING_REFERENCE_MASS_KDA)
    return LOADING_MAX_NM * scale, LOADING_ZERO_NM * scale, native['partner_mass_refs']


def _judge_loading(native):
    loading, response = native['loading_level_nm'], native['response_max_nm']
    loading_full, loading_zero, mass_refs = _loading_ends(native)
    response_full, response_zero, noise_refs = _noise_ends(native)
    degrees = [_ramp(value, full, zero) for value, full, zero in ((loading, loading_full, loading_zero), (response, response_full, response_zero)) if value is not None]      # only what the source gave is judged
    verdict = _graded(list(dict.fromkeys([*native['loading_refs'], *(mass_refs if loading is not None else []), *(noise_refs if response is not None else [])])), *degrees)
    return _verdict('unknown', []) if verdict['status'] == 'supported' and (loading is None or response is None or native['loading_documented'] != 'yes') else verdict


def _judge_series(native):
    refs = native['concentration_refs']
    count = native['concentration_count']
    kinetic = native['fit_model'] in KINETIC_FIT_MODELS
    # the count: full credit from MIN_CONCENTRATIONS, partial below it on a concave curve (most of what a BLI series adds comes with its second and third concentration),
    # no credit at the zero end (the count that gives no KD: none for a kinetic fit, one for an isotherm), never conflicting (a short series is weaker evidence, not evidence against), no step
    zero_count = SERIES_ZERO_CONCENTRATIONS_KINETIC if kinetic else SERIES_ZERO_CONCENTRATIONS
    shortfall = min(1.0, max(0, MIN_CONCENTRATIONS - count) / (MIN_CONCENTRATIONS - zero_count))
    count_degree = 1 - shortfall ** SERIES_COUNT_CURVE_POWER
    low = native['concentration_low_over_kd']
    # the low end: an isotherm needs its lower arm (linear ramp, conflicting at the KD); a kinetic fit only loses the free-branch test (the free fraction, never conflicting)
    low_degree = (1 + LOW_FACTOR) / (1 + low) if kinetic else _ramp(low, LOW_FACTOR, LOW_ZERO_FACTOR)
    verdict = _graded(refs, low_degree, _ramp(native['concentration_high_over_kd'], HIGH_FACTOR, HIGH_ZERO_FACTOR))
    return verdict if verdict['status'] == 'conflicting' else _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_fit(native):
    verdict = _graded(native['fit_refs'], _ramp(native['fit_r_squared'], FIT_R_SQUARED_MIN, FIT_R_SQUARED_ZERO))
    if verdict['status'] == 'supported' and native['fit_model'] == '1:1' and native['fit_bivalent_answer'] != 'no':
        return _verdict('unknown', [])
    return verdict


def _judge_dissociation(native):
    decay = native['dissociation_decay']
    degrees = [_ramp(decay, DISSOCIATION_DECAY_MIN, DISSOCIATION_DECAY_ZERO)]
    refs = native['dissociation_refs']
    response = native['quantities']['response_max']
    if response['status'] == 'point':
        # in addition: the decayed signal against the instrument noise (a few percent of a small response is no measured koff)
        full, zero, noise_refs = _noise_ends(native)
        degrees.append(_ramp(decay * response['value'], full, zero))
        refs = list(dict.fromkeys([*refs, *response['source_refs'], *noise_refs]))
    return _graded(refs, *degrees)


def _judge_replicates(native):
    # the precision of the mean over n independent sensors relative to that at MIN_REPLICATES (see MIN_REPLICATES), no step, never conflicting for a stated count
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


def _judge_kinetic(native):
    rates, kd = native['kd_from_rates_nM'], native['kd_nM']
    fold = max(rates, kd) / min(rates, kd)      # either way: a factor off is the same inconsistency whichever side it lies
    return _graded(native['kinetic_refs'], _log_ramp(fold, KINETIC_FOLD_MAX, KINETIC_ZERO_FOLD))


def _judge_steady_kinetic(native):
    return _graded(native['steady_kinetic_refs'], _log_ramp(native['steady_kinetic_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('loading_and_response', 'loading_and_response_recorded_for_the_sheet'): _judge_loading, ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_series,
          ('fit_model', 'r_squared_recorded_for_the_sheet'): _judge_fit, ('dissociation_window', 'dissociation_decay_recorded_for_the_sheet'): _judge_dissociation,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates, ('kinetic_consistency', 'kd_from_rates_recorded_for_the_sheet'): _judge_kinetic,
          ('steady_state_vs_kinetic', 'estimate_fold_recorded_for_the_sheet'): _judge_steady_kinetic}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    spread = native['quantities']['kd_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'kd_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * _SCALES[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_sensors_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_bli(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    kd = native['quantities']['kd']
    if native['kd_nM'] is None:
        null_components['effect'] = 'kd_not_given_as_a_point_value'
    else:
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'bli_kd:' + ref, kd['source_refs'], kd['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'bli_kd_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if variance is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': variance_refs}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['analyte_preparation_ref'], 'immobilized_preparation_ref': preparations['immobilized_preparation_ref'], 'surface_ref': preparations['sensor_ref'], 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'bli', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if native['kd_nM'] is not None:
        converted['direction_field_support'] = kd['support']      # the support class of the operand that fixes the effect
    else:      # no binding constant: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact binding_detected, the one field the statement is derived from
    return converted
