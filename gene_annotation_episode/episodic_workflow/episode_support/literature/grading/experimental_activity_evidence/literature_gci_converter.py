"""GCI converter: turns the GCI grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to GCI, deterministic. Input: the result of grade_gci.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC and BLI converters fill), the
dependence keys the merger needs, and for every sheet component that a KD
measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the GCI KD in nM (point operand), only when the source
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
                  replicates on separate channels or chips); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the SPR, ITC and
BLI converters): analyte_preparation_ref = the analyte in the flow,
immobilized_preparation_ref = the partner on the chip, surface_ref = the
record's chip_ref (the chip or chip lot: channels of one chip share it),
dataset_ref = the dataset.

Criteria mapping (GCI criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              reference_subtraction + bulk_solvent_correction +
                              nonspecific_binding_control +
                              baseline_and_regeneration
binding_regime                concentration_series + dissociation_window +
                              mass_transport + steady_state_vs_kinetic
binding_parameter_definition  fit_model + kinetic_consistency
binding_species               immobilized_activity
calibration_applicability     surface_level_and_response (the immobilized
                              amount and the response against the
                              instrument's usable range) + rmax_consistency
                              (the observed maximum response against the
                              theoretical one from the masses, the level and
                              the stoichiometry: the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and
hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement): surface_level_and_response
judged on the immobilization level (full agreement at most
IMMOBILIZATION_MAX_PG_MM2, falling linearly to degree 0 at
IMMOBILIZATION_ZERO_PG_MM2 and staying 0 beyond it, never conflicting: see the
range review) and the maximum response (full agreement at least
RESPONSE_MIN_PG_MM2, linear to RESPONSE_ZERO_PG_MM2, conflicting at or below
it), unknown when one of them is not given (unless the response alone is
conflicting); concentration_series judged on the number of concentrations (full
agreement from MIN_CONCENTRATIONS, falling on a concave curve of power
SERIES_COUNT_CURVE_POWER to no credit at CONCENTRATIONS_ZERO_COUNT, one
concentration; a short series is weaker evidence, supported with that low
degree, never conflicting), the lowest over the KD (full agreement at most
LOW_FACTOR) and the highest over the KD (full agreement at least HIGH_FACTOR),
both ramps linear in the 1:1 occupancy r / (1 + r) at that concentration; with
waveRAPID stated as used only the highest over the KD is judged and the count
is not asked; replicates supported with degree min(1, sqrt(n / MIN_REPLICATES))
when the independence is yes (never conflicting for a stated count), unknown
when it is not stated (a stated no is the grader's conflicting);
kinetic_consistency judged on the symmetric fold between koff/kon and the KD
(full agreement at most KINETIC_FOLD, linear in log fold to KINETIC_ZERO_FOLD);
steady_state_vs_kinetic judged on the fold between the two KDs (full agreement
at most AGREEMENT_FACTOR, linear in log fold to AGREEMENT_ZERO_FACTOR);
rmax_consistency judged on observed over theoretical maximum response (full
agreement from RMAX_RATIO_MIN to RMAX_RATIO_MAX, linear to the zero ends
RMAX_RATIO_ZERO_MIN and RMAX_RATIO_ZERO_MAX); dissociation_window judged on the
decayed fraction 1 - exp(-koff x time) (full agreement from
DISSOCIATION_DECAY_MIN, linear to DISSOCIATION_DECAY_ZERO) and, when the
maximum response is given, on the decayed signal against the response ramp. A
continuous comparison is supported with a degree of 1.0 at its full-agreement
limit, falling to 0 at its zero-agreement limit (the *_ZERO_* constants) on the
scale named above, and, for a value (not a count, not the immobilization
level), conflicting (no degree) at or beyond that limit. A sheet criterion that
is supported carries the smallest degree of its members that have one (the
sheet reads no degree; it travels with the interpretation and the merger
carries it per result).

Range review (2026-11-21; the owner's five questions per researched value; Q1 what it protects
against, Q2 general practice or lab-specific, Q3 absolute or relative scale, Q4 how badly a wrong
value misleads and whether the shape fits, Q5 consistency with the other binding assays)
------------------------------------------------------------------------------------------------
MIN_CONCENTRATIONS 5, CONCENTRATIONS_ZERO_COUNT 1, SERIES_COUNT_CURVE_POWER 2 (count of a titration)
  Q1 a KD from too few concentrations: the concentration dependence (kobs = kon C + koff) and the
  1:1 model are not tested. Q2 general biosensor practice (Myszka 1999, J Mol Recognit 12:279: at
  least five concentrations spanning about 0.1 to 10 x KD; Rich & Myszka annual surveys). Q3 a
  count is dimensionless: absolute is right. Q4 three or four concentrations in a global kinetic fit
  usually give a KD close to the five-point one (a small magnitude error), so the curve must be
  gentle near 5 and steep near 1; the old linear rise (0.5 at three) was too harsh there. Q5 GCI
  multi-cycle data are fitted like BLI (global kinetic fit), so GCI takes BLI's concave shape,
  d = 1 - ((5 - n) / 4)^2 (2: 0.44, 3: 0.75, 4: 0.94). SPR's zero at two follows its isotherm
  argument; never conflicting, as everywhere. CHANGED: linear -> concave power 2.
LOW_FACTOR 0.2 / LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 5 / HIGH_ZERO_FACTOR 1.0 (span over the KD)
  Q1 a series that does not bracket the KD: the lower half or the plateau of the binding curve is
  extrapolated, so KD and Rmax trade off. Q2 general (Myszka 1999; Deranleau 1969, JACS 91:4044:
  data should cover about 20 to 80 % saturation, which is 0.25 to 4 x KD; 0.2 and 5 x KD are that
  with slack). Q3 already relative to the paper's own KD. Q4 what a missing end costs is the share
  of the isotherm left unsampled, so the ramp is now linear in the 1:1 occupancy r / (1 + r)
  (0.17 -> 0.5 at the low end, 0.83 -> 0.5 at the high end): a top concentration of 3 x KD
  samples 75 % saturation and gets 0.75 (linear in r gave 0.5, too harsh); a lowest of 0.6 x KD
  gets 0.375 (was 0.5). The values are kept. Open for the owner: a pure kinetic fit needs the low
  end less than a steady-state fit; GCI, SPR and BLI all treat both alike. Q5 SPR and BLI keep the
  linear-in-r ramps; the same occupancy argument applies to them (flagged, not changed here).
  CHANGED: shape linear in r -> linear in occupancy; values kept. waveRAPID uses the high ramp
  only (Kartal et al. 2021, SLAS Discov 26:995, single concentration with pulses of rising
  length); the 5 x KD target for its one concentration is the titration's value, not checked
  against Kartal (EXPERT_REVIEW).
IMMOBILIZATION_MAX_PG_MM2 2000 / IMMOBILIZATION_ZERO_PG_MM2 4000 (ligand density)
  Q1 a crowded surface: mass transport and rebinding slow the apparent kon and koff. Q2 a
  protein-protein default (vendor guidance; 1 pg/mm2 ~ 1 RU, Biacore-style density advice); the
  right level depends on the pair: small-molecule and fragment work (a main GCI use) routinely
  immobilizes far more, because the analyte's response scales with its mass. Q3 the physics is
  relative: mass transport goes with kon x the molar site density (level / ligand mass), and a
  theoretical Rmax needs the analyte and ligand masses; the grader collects neither (GRADER GAP).
  Q4 for a small analyte the old zero end made a normal surface conflicting, which misleads badly;
  until the masses are collected the level is a proxy and cannot show the paper against the
  standard. Linear in level is right where it applies (the mass-transport number is linear in
  the site density). Q5 BLI's loading ramp has the same problem (flagged). CHANGED: values and
  ramp kept; at and beyond the zero end the level gives degree 0, never conflicting.
RESPONSE_MIN_PG_MM2 1.0 / RESPONSE_ZERO_PG_MM2 0.1 (maximum response)
  Q1 a binding signal at the noise: no kinetics can be fitted. Q2 instrument-specific: 0.1 pg/mm2
  is a conservative noise (WAVE specifications claim lower, about 0.01 pg/mm2; not verified from a
  primary paper); full credit at 10 x that noise is the analytical limit-of-quantitation
  convention (10 sigma; IUPAC, ICH Q2). Q3 relative to the paper's stated baseline noise would be
  right; the grader does not collect it (GRADER GAP). Q4 if the true noise is lower the score is
  conservative between 0.1 and 1 pg/mm2, and a response at or below 0.1 pg/mm2 is suspicious for
  any analyte (a 150 Da fragment on a 30 kDa protein at 3000 pg/mm2 gives about 15 pg/mm2), so
  conflicting there is fair. Q5 BLI uses the same noise-based ramp in nm. KEPT.
MIN_REPLICATES 3 (independent channels or chips)
  Q1 a KD from one surface: chip-to-chip activity and density variation unseen. Q2 general
  (triplicate is the common standard; Katsamba et al. 2006, Anal Biochem 352:208 shows the
  between-run spread). Q3 a count: absolute. Q4 replicates change precision, not direction:
  sqrt(n / 3) is gentle (1: 0.58, 2: 0.82). Q5 identical to every assay (consistency rule 1). KEPT.
KINETIC_FOLD 1.2 / KINETIC_ZERO_FOLD 1.8 (KD against koff/kon; were KINETIC_TOLERANCE 0.20 /
KINETIC_ZERO_TOLERANCE 0.8 on the relative gap)
  Q1 a reported KD that is not the fit's koff/kon: a mislabelled steady-state KD, a different fit,
  or a transcription error. Q2 an arithmetic identity of a 1:1 fit; 1.2 covers two-significant-
  figure rounding and mean-of-ratios against ratio-of-means over replicates. Q3 relative to the
  paper's KD: right. Q4 the old relative gap was asymmetric: koff/kon at 1.8 x KD was conflicting
  while 5 x below the KD still got credit. An internal inconsistency is the same whichever side it
  falls, so the comparison is now the symmetric fold, linear in log fold, with the old high-side
  ends (1.2, 1.8) kept on both sides; the low side is now as strict as the high side. Q5 SPR and
  BLI keep the asymmetric gap (flagged). CHANGED: relative gap -> symmetric fold.
AGREEMENT_FACTOR 2 / AGREEMENT_ZERO_FACTOR 10 (steady-state KD against kinetic KD)
  Q1 heterogeneity, mass transport, a non-1:1 mechanism or a missed equilibrium show as two KDs
  that disagree. Q2 general (agreement within about twofold is the usual check, Myszka 1999;
  tenfold is a different event). Q3 relative to the paper's own two KDs: right. Q4 a fold is a
  multiplicative error, so equal ratios should cost equal steps: linear in log fold (3: 0.75,
  6: 0.32), where linear in fold gave a sixfold gap 0.5. Q5 the KD strength anchors also work on
  the log scale; SPR and BLI keep linear in fold (flagged). CHANGED: linear in fold -> log fold.
RMAX_RATIO_MIN 0.3 / RMAX_RATIO_ZERO_MIN 0.1, RMAX_RATIO_MAX 1.2 / RMAX_RATIO_ZERO_MAX 2.0 (GRADER GAP
  1 closed 2026-11-21: analyte_mass, ligand_mass, stoichiometry collected; new criterion rmax_consistency)
  Q1 an immobilized partner that is mostly inactive or has another stoichiometry (ratio low), or
  non-specific binding or aggregation adding signal (ratio high): the fitted KD then describes
  something other than the 1:1 interaction. Q2 general SPR/biosensor practice (Myszka 1999; the
  GCI response is a surface mass in pg/mm2 and 1 RU ~ 1 pg/mm2, so the theoretical maximum
  response = analyte mass / ligand mass x level x stoichiometry holds as in SPR); the values are the
  SPR converter's, none is GCI-specific. Q3 relative to the paper's own masses, level and response:
  right, all collected by the grader now. Q4 a ratio below 0.3 loses signal but not direction, a ratio
  above 1.2 adds foreign signal; linear ramps to a tenth and to twice, conflicting at the far ends as
  in SPR (the paper's own response then shows the standard is not met: this one is not a proxy like
  the level, because it compares the paper's own numbers). Q5 identical to SPR. It also answers the
  relative-immobilization-scale gap: the level is still judged on the absolute proxy above (kept; the
  masses now give the activity check instead of a second scale, and the surface-level ramp stays a
  protein-protein default).
DISSOCIATION_DECAY_MIN 0.05 / DISSOCIATION_DECAY_ZERO 0.01 (GRADER GAP 4 closed 2026-11-21:
  dissociation_time collected; new criterion dissociation_window)
  Q1 a koff that is extrapolated from a phase in which the complex barely dissociated (tight binders;
  for waveRAPID, pulses too short for a slow koff). Q2 general biosensor practice (at least a few
  percent decay; Myszka 1999), the same as BLI. Q3 relative to the paper's koff and time: right; the
  grader also passes the maximum response so that the decayed signal in pg/mm2 is judged on the
  response ramp as in BLI (no new number). Q4 linear 1 to 5 percent (koff's error is inversely
  proportional to the decay); conflicting at or below 1 percent, where the paper's own numbers show koff
  is not measured. Q5 same as BLI. Because it needs koff and a stated time, it is unknown for a paper that
  gives a KD only.
No unknown weight is used inside any degree (consistency rule 3). The new criteria map into the existing
sheet criteria binding_regime and calibration_applicability, so no unknown weight entry changes; a
paper that states no masses now leaves calibration_applicability unknown even with a level and a
response (the same as SPR).
Grader gaps not closed (judged not worth collecting): (2) the stated baseline noise: papers almost never
state it, so a relative response scale would almost always be unknown and the conservative absolute noise
(RESPONSE_ZERO_PG_MM2) stays the better scale; (3) a fit-quality number (chi-squared over Rmax or residuals): the Creoptix
software reports no such figure in the text of a paper (the grader's criteria file states it), so the field would be
unavailable nearly always, and the global-fit shape of the count curve and the kinetic and steady-state
agreement already guard the fit.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no GCI counterpart (measurement_identity, matrix_interference,
background_alternatives, attribution_supported, assertion_relevance,
condition_scope, binding_comparison) are not selected, and the sheet reports
them as not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_gci_converted'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
CRITERIA_MAP = {'binding_controls': ('reference_subtraction', 'bulk_solvent_correction', 'nonspecific_binding_control', 'baseline_and_regeneration'), 'binding_regime': ('concentration_series', 'dissociation_window', 'mass_transport', 'steady_state_vs_kinetic'), 'binding_parameter_definition': ('fit_model', 'kinetic_consistency'), 'binding_species': ('immobilized_activity',), 'calibration_applicability': ('surface_level_and_response', 'rmax_consistency'), 'sampling_basis': ('replicates',)}
MIN_CONCENTRATIONS = 5  # EXPERT_REVIEW: fewest analyte concentrations for a usable titration series (GCI series are usually 5 to 8 steps); full agreement from it.
CONCENTRATIONS_ZERO_COUNT = 1  # EXPERT_REVIEW: one concentration in a titration (not waveRAPID) shows no concentration dependence at all, so it defines no binding curve (no credit: degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against); the credit rises from it to MIN_CONCENTRATIONS on the curve of SERIES_COUNT_CURVE_POWER.
SERIES_COUNT_CURVE_POWER = 2  # EXPERT_REVIEW: shape of the rise from CONCENTRATIONS_ZERO_COUNT to MIN_CONCENTRATIONS, d = 1 - ((MIN - n) / (MIN - ZERO))^power: concave, because a GCI multi-cycle series is fitted globally like BLI's (kobs = kon x C + koff): the second concentration gives the concentration dependence and the third the first check of the 1:1 model, while the fourth and fifth mostly add redundancy; the same value as BLI (same fit), flattening into full credit at MIN_CONCENTRATIONS with no kink (range review).
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest concentration should be at most this multiple of KD (0.1x with a factor of 2 slack; Deranleau 1969: about 20 % saturation); full agreement up to it. The ramp is linear in the 1:1 occupancy r / (1 + r) (range review).
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: lowest concentration at the KD itself leaves the lower half of the binding curve undefined, so no agreement; falls linearly in occupancy from LOW_FACTOR (0.17 -> 0.5).
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest concentration (or the one waveRAPID concentration) should be at least this multiple of KD (10x with a factor of 2 slack; Deranleau 1969: about 80 % saturation); full agreement from it. The ramp is linear in the 1:1 occupancy r / (1 + r) (range review).
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: highest concentration at the KD itself never reaches saturation, so no agreement; falls linearly in occupancy from HIGH_FACTOR (0.83 -> 0.5).
IMMOBILIZATION_MAX_PG_MM2 = 2000.0  # EXPERT_REVIEW: above about 2 ng/mm2 of immobilized partner a protein-protein surface is crowded and mass transport and rebinding distort the kinetics; full agreement up to it. A protein-protein default: the right level depends on the ligand and analyte masses, which the grader does not collect (range review: grader gap).
IMMOBILIZATION_ZERO_PG_MM2 = 4000.0  # EXPERT_REVIEW: twice the crowding limit, a protein-protein surface is saturated and the kinetics are dominated by mass transport and rebinding (degree 0); falls linearly from IMMOBILIZATION_MAX_PG_MM2. Never conflicting: a small-molecule or fragment surface is routinely denser, so without the masses the level cannot show the paper against the standard (range review).
RESPONSE_MIN_PG_MM2 = 1.0  # EXPERT_REVIEW: full agreement from ten times the instrument's baseline noise (taken conservatively as about 0.1 pg/mm2): the 10-sigma limit-of-quantitation convention (IUPAC; ICH Q2).
RESPONSE_ZERO_PG_MM2 = 0.1  # EXPERT_REVIEW: the instrument's baseline noise (conservatively about 0.1 pg/mm2; WAVE specifications claim lower): a response this small is not a signal (no agreement); falls linearly from RESPONSE_MIN_PG_MM2.
RMAX_RATIO_MIN = 0.3  # EXPERT_REVIEW: observed / theoretical maximum response below this means a mostly inactive surface or a wrong stoichiometry; full agreement from it (the same value as SPR: the GCI response is a surface mass like SPR's, so the ratio means the same).
RMAX_RATIO_ZERO_MIN = 0.1  # EXPERT_REVIEW: a tenth of the theoretical maximum response or less is an essentially inactive surface (no agreement; conflicting, as in SPR); falls linearly from RMAX_RATIO_MIN.
RMAX_RATIO_MAX = 1.2  # EXPERT_REVIEW: observed / theoretical above this means non-specific binding or aggregation on the surface; full agreement up to it (as SPR).
RMAX_RATIO_ZERO_MAX = 2.0  # EXPERT_REVIEW: twice the theoretical maximum response or more is mostly non-specific signal (no agreement; conflicting, as in SPR); falls linearly from RMAX_RATIO_MAX.
DISSOCIATION_DECAY_MIN = 0.05  # EXPERT_REVIEW: the signal must decay at least this fraction in the dissociation phase for koff to be measured, not extrapolated; full agreement from it (the same value as BLI).
DISSOCIATION_DECAY_ZERO = 0.01  # EXPERT_REVIEW: a decay of one percent is within the baseline noise, so koff is not measured at all (no agreement); falls linearly from DISSOCIATION_DECAY_MIN. In addition, when the maximum response is given, the decayed signal (decay x response, in pg/mm2) is judged on the RESPONSE_ZERO_PG_MM2 -> RESPONSE_MIN_PG_MM2 ramp (koff's precision is about noise / decayed signal); no new number.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent replicate experiments (on separate channels or chips); full agreement from it. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): the immobilized amount and activity vary from chip to chip, and the standard error of the mean KD over n independent chips falls as 1 / sqrt(n); 1 run about 0.58, 2 about 0.82; never conflicting for a stated count.
KINETIC_FOLD = 1.2  # EXPERT_REVIEW: allowed fold between the KD and koff/kon, either side (the old 20 % relative gap): two-significant-figure rounding of kon and koff, and mean-of-ratios against ratio-of-means over replicates; full agreement up to it.
KINETIC_ZERO_FOLD = 1.8  # EXPERT_REVIEW: koff/kon 1.8 times above or below the KD (the old high-side zero end, now on both sides) means the rates and the KD are not from one fit (no agreement); falls linearly in log fold from KINETIC_FOLD (range review: an internal inconsistency is the same whichever side it falls).
AGREEMENT_FACTOR = 2.0  # EXPERT_REVIEW: allowed fold gap between steady-state KD and kinetic KD (Myszka 1999); full agreement up to it.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: a tenfold gap between the two KD estimates is a different binding event (no agreement); falls linearly in log fold from AGREEMENT_FACTOR (a fold is a multiplicative error: equal ratios cost equal steps).
NULL_REASONS = {'recovery': 'gci_has_no_matrix_recovery_measurement', 'attributed_signal': 'gci_reference_subtraction_is_not_an_attribution_fraction', 'total_signal': 'gci_reference_subtraction_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_gci_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_gci_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _share(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (zero - value) / (zero - full)


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit) on the scale the criterion is judged on. Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly to 0 at the zero limit."""
    degrees = [_share(value, full, zero) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _occupancy(ratio):
    """The 1:1 fraction bound at a concentration of ratio x KD, ratio / (1 + ratio) (the 1:1 isotherm itself, FIXED_BY_DEFINITION): the scale of the span ramps."""
    return ratio / (1 + ratio)


def _log_fold(fold, full, zero):
    """A fold comparison on the log scale (a fold is a multiplicative error)."""
    return math.log(fold), math.log(full), math.log(zero)


def _judge_surface(native):
    level, response = native['immobilization_level_pg_mm2'], native['response_max_pg_mm2']
    refs = native['surface_refs']
    if response is not None and _share(response, RESPONSE_MIN_PG_MM2, RESPONSE_ZERO_PG_MM2) <= 0:
        return _verdict('conflicting', refs)      # no binding signal above the noise: the paper shows it
    if level is None or response is None:
        return _verdict('unknown', [])      # both are needed for the surface to be judged supported
    # the level is a protein-protein proxy until the masses are collected: degree 0 at and beyond its zero end, never conflicting (range review)
    level_degree = max(0.0, _share(level, IMMOBILIZATION_MAX_PG_MM2, IMMOBILIZATION_ZERO_PG_MM2))
    return _verdict('supported', refs, min(1.0, level_degree, _share(response, RESPONSE_MIN_PG_MM2, RESPONSE_ZERO_PG_MM2)))


def _judge_series(native):
    refs = native['concentration_refs']
    high = (_occupancy(native['concentration_high_over_kd']), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_FACTOR))      # the share of the isotherm sampled (range review)
    if native['pulse_kinetics']:
        return _graded(refs, high)      # waveRAPID: one concentration is the design, the count is not asked
    verdict = _graded(refs, (_occupancy(native['concentration_low_over_kd']), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_FACTOR)), high)
    if verdict['status'] == 'conflicting':
        return verdict
    # the count: full credit from MIN_CONCENTRATIONS, partial below it on a concave curve (most of what a global kinetic fit gains comes with the
    # second and third concentration), no credit at CONCENTRATIONS_ZERO_COUNT, never conflicting (a short series is weaker evidence, not evidence against)
    shortfall = min(1.0, max(0, MIN_CONCENTRATIONS - native['concentration_count']) / (MIN_CONCENTRATIONS - CONCENTRATIONS_ZERO_COUNT))
    return _verdict('supported', refs, min(verdict['degree'], 1 - shortfall ** SERIES_COUNT_CURVE_POWER))


def _judge_rmax(native):
    ratio = native['rmax_ratio']
    return _graded(native['rmax_refs'], (ratio, RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MIN), (ratio, RMAX_RATIO_MAX, RMAX_RATIO_ZERO_MAX))


def _judge_dissociation(native):
    decay = native['dissociation_decay']
    limits = [(decay, DISSOCIATION_DECAY_MIN, DISSOCIATION_DECAY_ZERO)]
    if native['dissociation_response_pg_mm2'] is not None:
        limits.append((decay * native['dissociation_response_pg_mm2'], RESPONSE_MIN_PG_MM2, RESPONSE_ZERO_PG_MM2))      # in addition: a few percent of a small response is no measured koff
    return _graded(native['dissociation_refs'], *limits)


def _judge_replicates(native):
    # The count is a curve, not a cut-off: the precision of the mean KD over n independent chips relative to that at
    # MIN_REPLICATES, min(1, sqrt(n / MIN_REPLICATES)) (see MIN_REPLICATES); never conflicting for a stated count.
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])      # independence not stated: nothing says the runs were on separate channels or chips (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


def _judge_kinetic(native):
    ratio = native['kd_from_rates_nM'] / native['kd_nM']
    fold = max(ratio, 1 / ratio)      # symmetric: koff/kon above or below the KD is the same inconsistency (range review)
    return _graded(native['kinetic_refs'], _log_fold(fold, KINETIC_FOLD, KINETIC_ZERO_FOLD))


def _judge_steady_kinetic(native):
    return _graded(native['steady_kinetic_refs'], _log_fold(native['steady_kinetic_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('surface_level_and_response', 'surface_level_and_response_recorded_for_the_sheet'): _judge_surface, ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_series,
          ('rmax_consistency', 'rmax_ratio_recorded_for_the_sheet'): _judge_rmax, ('dissociation_window', 'dissociation_decay_recorded_for_the_sheet'): _judge_dissociation,
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
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_channels_or_chips_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_gci(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    kd = native['quantities']['kd']
    if native['kd_nM'] is None:
        null_components['effect'] = 'kd_not_given_as_a_point_value'
    else:
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'gci_kd:' + ref, kd['source_refs'], kd['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'gci_kd_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
    dependence = {'analyte_preparation_ref': preparations['analyte_preparation_ref'], 'immobilized_preparation_ref': preparations['immobilized_preparation_ref'], 'surface_ref': preparations['chip_ref'], 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'gci', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if native['kd_nM'] is not None:
        converted['direction_field_support'] = kd['support']      # the support class of the operand that fixes the effect
    else:      # no binding constant: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact binding_detected, the one field the statement is derived from
    return converted
