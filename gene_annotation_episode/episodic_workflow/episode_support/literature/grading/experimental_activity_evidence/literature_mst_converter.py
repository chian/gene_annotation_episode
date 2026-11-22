"""MST converter: turns the MST grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to MST, deterministic. Input: the result of grade_mst.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP and FRET converters fill), the
dependence keys the merger needs, and for every sheet component that an MST
measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  KD of a direct titration, or, when the record has no KD,
                  the Ki of a competition experiment (the measurement key
                  names it: mst_kd or mst_ki). Neither given leaves effect
                  null; an EC50 alone is not a binding constant (it depends on
                  the detected partner's concentration) and is not carried
                  into the effect.
                  With no binding constant the result is the experiment's
                  stated yes/no result (fact binding_detected):
                  'qualitative_effect' carries its statement
                  (interaction_detected, interaction_not_detected, or
                  interaction_not_stated when the passage states neither) and
                  the spans that state it.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent titrations); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the titrant,
immobilized_preparation_ref = the detected partner held fixed, surface_ref = None
(MST in solution has no surface), dataset_ref = the dataset.

Criteria mapping (MST criteria -> sheet criteria), declared in CRITERIA_MAP
----------------------------------------------------------------------------
binding_controls              initial_fluorescence + aggregation_adsorption +
                              specificity_control + fluorescence_level
binding_regime                labelled_concentration + concentration_series +
                              equilibrium + direct_vs_competition
binding_parameter_definition  fit_model + labelling_scheme + readout_window
calibration_applicability     signal_amplitude (the size of the Fnorm change against
                              the noise: MST's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Continuous comparisons give a degree: supported with degree 1.0 up to
the full-agreement limit, falling to 0 at the zero-agreement limit on the scale named below, conflicting at or beyond it (signal_amplitude: the signal-to-noise against
MIN_SIGNAL_TO_NOISE / SIGNAL_TO_NOISE_ZERO_AGREEMENT, linear; only when the paper states no signal-to-noise, the Fnorm change against MIN_FNORM_AMPLITUDE_PERMILLE /
FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE, linear; readout_window's F-hot time of a thermophoresis readout against MIN_FHOT_S / FHOT_ZERO_AGREEMENT_S, linear;
labelled_concentration against LABELLED_MAX_OVER_KD / LABELLED_ZERO_AGREEMENT_OVER_KD unless tight binding is handled, linear in the log of the depletion error 1 + r / 2;
concentration_series' lowest and highest concentration over the curve's midpoint (see _midpoint) against LOW_FACTOR / LOW_ZERO_AGREEMENT_FACTOR and HIGH_FACTOR /
HIGH_ZERO_AGREEMENT_FACTOR, linear in the fractional occupancy c / (c + midpoint), the lowest judged only when it differs from the highest, and its count against
MIN_CONCENTRATIONS / CONCENTRATIONS_ZERO_AGREEMENT, the weakest of the three (the count only lowers the degree: no credit at or below the zero count, never
conflicting; a count without a span is unknown); direct_vs_competition against AGREEMENT_FACTOR / AGREEMENT_ZERO_FACTOR, linear in log fold). The two counts are gradual too (owner rules, 2026-11-21:
soften, do not cut; a short count is weaker evidence, never conflicting): the concentration count gives full credit at MIN_CONCENTRATIONS, falling linearly in the residual degrees
of freedom of the fit to no credit at CONCENTRATIONS_ZERO_AGREEMENT; replicates (independence yes) are supported with degree min(1, sqrt(n / MIN_REPLICATES)), the precision of
the mean KD over n independent titrations; independence not stated: unknown; stated no: the grader's conflicting. equilibrium, when the paper states no equilibrium fact, is a curve on the paper's own constant (the reported KD, else Ki; an EC50 is no binding constant): T_FAST = MIN_INCUBATION_MIN x
EQUILIBRATION_REFERENCE_NM / constant_nM (five half-lives at the fast association rate KON_FAST_PER_M_S), T_SLOW = T_FAST x KON_FAST_PER_M_S / KON_SLOW_PER_M_S, and the degree is
log(t / T_FAST) / log(T_SLOW / T_FAST) clipped to 1, the share of the plausible association rates (a log scale) for which the incubation covers five half-lives; t <= T_FAST is conflicting
(even the fastest association has not equilibrated: the zero end of the curve, the old conflict), t >= T_SLOW is full; no constant: unknown (no scale; a time alone is not the paper against
equilibrium). MST has no separate floor (see the range review), so the degree is d_kon alone. A sheet criterion that is supported carries the smallest degree of its members that have one.
Quote support (literature_quote_support.py, SUPPORT_DEGREE direct 1.0 / implied 0.7 / about_something_else 0.3): when any stated field a member criterion reads has
support 'implied' or 'about_something_else', a supported sheet criterion gets the weakest support degree as its degree (the product with its degree where it had one);
support never changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no MST counterpart (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Range review (SOP step 3, 2026-11-21; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative scale, Q4 how badly a
wrong value misleads and whether the shape follows, Q5 consistency; citations from memory, not checked on the web)
--------------------------------------------------------------------------------------------------------------------------------
signal-to-noise 5 / 1     Q1 a KD fitted to a curve no larger than its scatter (a noise-made binder). Q2 general: vendor guidance S/N >= 5
                          (Jerabek-Willemsen et al. 2014 J Mol Struct 1077:101; benchmark Lopez-Mendez et al. 2021 Eur Biophys J 50:653).
                          Q3 already relative (amplitude over the paper's own scatter). Q4 the fit's KD error goes as 1 / (S/N); linear credit
                          from S/N 1 (no curve) to 5 stays within about 0.1 of that ratio. Q5 like the FP and FRET window ramps. KEPT.
Fnorm change 5 / 1 per mille  Q1 the same failure. Q2 instrument-specific: it assumes about 1 per mille capillary noise (label-free and older
                          instruments are noisier, newer ones quieter). Q3 the right scale is the paper's own noise, i.e. the S/N, which the
                          grader collects. Q4 the old min(S/N, change) gave a 3 per mille change at S/N 18 a degree of 0.5 (a quiet instrument
                          read as a weak curve): misleading. CHANGED: the S/N governs when stated; the absolute change is the fallback only.
F-hot time 1 s / 0 s      Q1 a 'thermophoresis' Fnorm read inside the heating transient. Q2 instrument timing (Monolith IR heating); vendor
                          defaults read at about 1 to 1.5 s (current) or 20 to 30 s (older), both at full credit. Q3 absolute is right: the
                          jump time belongs to the instrument, not the sample. Q4 mild: an early window still holds a binding-dependent signal
                          (the T-jump is itself an MST readout), so the KD is rarely wrong; the gentle linear ramp fits; conflicting only at
                          0 s or less (no heated reading at all). Q5 MST only. KEPT.
count 10 / 3              Q1 baselines and transition not all sampled. Q2 general: the vendor's standard series is 16 two-fold dilutions
                          (Wienken et al. 2010 Nat Commun 1:100; Jerabek-Willemsen 2014); 10 is a lenient floor; 3 is the fit's parameters
                          (physics). Q3 absolute: the fit's residual degrees of freedom scale with nothing the paper states. Q4 linear in the
                          residual degrees of freedom; nine points keep 0.86. Q5 same shape as FP / FRET (3 parameters) and ITC; never
                          conflicting. KEPT (a Hill fit has 4 parameters; not modelled, as in FP / FRET).
span 0.2 / 1 and 10 / 1   Q1 an unbound baseline or a bound plateau that is extrapolated, not measured. Q2 general: about 0.1x to 10x the
                          midpoint (Myszka 1999 J Mol Recognit 12:279; MST guidance asks for the highest at 20x or more); 0.2 and 10 are
                          lenient. Q3 RELATIVE TO THE CURVE'S MIDPOINT, which is the reported constant only for a hyperbola KD: with tight
                          binding handled the midpoint is KD + [detected] / 2 (labelled_nM, tight_binding_handled: collected); for a
                          competition Ki it is the IC50 / EC50 (ec50_nM, used when stated). Q4 linear in the ratio was harsh near 1x (a top
                          at 2x KD, already 67 percent bound, got 0.11) and gentle near 10x; occupancy c / (c + midpoint) is steep where the
                          coverage changes fast. Q5 as SPR (occupancy; the lowest judged only when it differs from the highest, so one
                          concentration is a short series, not a conflict). CHANGED: midpoint scale and occupancy shape; values kept.
detected/KD 1 / 10        Q1 titrant depletion: a hyperbola fit gives about KD + [detected] / 2. Q2 general ([detected] <= KD; Jarmoskaite et
                          al. 2020 eLife 9:e57264). Q3 already relative to the KD. Q4 the harm is the fold error 1 + r / 2 (1.5x at r = 1, 6x at
                          r = 10) read on the log KD scale; linear in r gave r = 5.5 (3.75x) 0.5, now 0.34, and r = 2 (2x) 0.89, now 0.79.
                          Q5 log scale as the SPR fold ramps. CHANGED: shape linear in log(1 + r / 2); values kept.
incubation 10 min (step)  Q1 a curve read before the complex has equilibrated (low points under-bound, KD too high). Q2 reasoned (5 half-lives
                          of koff 0.01 / s about 6 min, plus margin); protocols vary (5 to 30 min). Q3 should be relative to koff (t_eq about
                          5 ln2 / koff), but MST gives no koff; the paper's own KD is in the record, and koff = kon x KD, so the scale is the
                          KD with an assumed kon (the grader now hands over the KD, else Ki, in nM with its refs: incubation_constant_nM;
                          GRADER CHANGE 2026-11-21). Q4 MISTAKE of the absolute 10 min: it made binding_regime conflicting for a 5-minute
                          incubation of a micromolar binder (equilibrated in seconds) and passed 30 minutes for a 10 pM binder (days needed),
                          and it was a cliff with no full-credit end. CHANGED 2026-11-21 (owner to confirm): the 10 minutes is kept as the
                          researched value, now stated at the KD it stands for: koff 0.01 / s at kon 1e6 per M per s is KD 10 nM
                          (EQUILIBRATION_REFERENCE_NM), so T_FAST = 10 min x 10 nM / KD (kon 1e6, the fast end of association, Schreiber,
                          Haran and Zhou 2009 Chem Rev 109:839, from memory), T_SLOW the same formula at KON_SLOW 1e5 (ten times T_FAST;
                          slow protein association and gated binding; from memory), degree = log(t / T_FAST) / log(T_SLOW / T_FAST) clipped
                          to 0..1; t <= T_FAST stays conflicting (the zero end), t >= T_SLOW full; no KD or Ki: unknown. Worked numbers: KD
                          10 nM (the reference): T_FAST 10 min, T_SLOW 100 min, 30 min 0.48, 10 min conflicting, 100 min full; weak 1 uM
                          binder: T_FAST 0.1 min = 6 s, T_SLOW 1 min, 5 min full; tight 10 pM binder: T_FAST 10000 min, T_SLOW 100000 min,
                          30 min conflicting, 100 h (6000 min) conflicting, 20000 min 0.30, 100000 min full. MST has NO d_floor: MIN_INCUBATION_MIN
                          here is the scale's reference, not a mixing time, and capillary filling is not a constant of this converter (a
                          floor would be a new number without a researched value). The pM end is conservative on purpose: the approach rate is
                          kon x [titrant] + koff, so a titration point far above the KD equilibrates much faster, but the points near the
                          midpoint, which fix the KD, relax at about 2 x koff and MST at picomolar KD is known to need very long incubations.
                          Q5 the same scale and curve as FRET (10 min at 10 nM here, 15 min at 2 nM there; kon fast 1e6 and slow 1e5 the
                          same); FP and FCS add a floor, which MST does not.
replicates 3, sqrt(n/3)   Q1 one dilution series' pipetting error taken as the KD. Q2 general (triplicate). Q3 absolute count. Q4 precision of
                          the mean. Q5 the shared replicate rule. KEPT.
KD vs Ki fold 3 / 10      Q1 a KD and a Ki that describe different binding (wrong competition model or probe KD). Q2 general within 2 to 3
                          fold, 3 for a Ki that carries the probe KD's error (Nikolovska-Coleska et al. 2004 Anal Biochem 332:261). Q3
                          already relative (the paper's two numbers). Q4 the KD is read on a log scale; linear in fold gave 6.5-fold 0.5, now
                          0.36 (5-fold 0.58). Q5 as SPR's log-fold AGREEMENT ramp. CHANGED: shape linear in log fold; values kept.
Grader gaps, decided afterwards. (3) the capillary noise in per mille: COLLECTED as the record quantity fnorm_noise; when no S/N is
stated but the amplitude and the noise are, the amplitude over the noise is judged on the S/N scale (same values), so a quiet or a
noisy (label-free) instrument is read against its own stated noise; the 1 per mille proxy stays the last fallback. (1) the competition
midpoint without an EC50: NOT collected. The EC50 / IC50 is already a record field and is used; a competition paper that reports a Ki
nearly always reports the IC50 it came from, and the alternative (the probe's KD) is a second number a paper rarely states beside the
probe concentration; the cost is a wider-than-true span test only for a Ki-alone paper, where it is unknown-or-mild, not conflicting.
(2) koff for an incubation scale: NOT collected. MST does not measure koff, a time course is shown as a figure (not read), and the
equilibrium_reached fact already carries the paper's own statement.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_criteria import NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_mst_converted_v1'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('initial_fluorescence', 'aggregation_adsorption', 'specificity_control', 'fluorescence_level'), 'binding_regime': ('labelled_concentration', 'concentration_series', 'equilibrium', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model', 'labelling_scheme', 'readout_window'), 'calibration_applicability': ('signal_amplitude',), 'sampling_basis': ('replicates',)}
MIN_SIGNAL_TO_NOISE = 5.0  # EXPERT_REVIEW: smallest signal-to-noise of the titration curve from which a KD is fitted; the instrument vendor's guidance treats a curve below 5 as not clearly distinguishable from noise; the full-agreement limit.
SIGNAL_TO_NOISE_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: signal-to-noise at or below which the signal is the size of the noise (nothing to fit), conflicting.
MIN_FNORM_AMPLITUDE_PERMILLE = 5.0  # EXPERT_REVIEW: smallest change of Fnorm (per mille) between the unbound and the bound state; the noise of one capillary is of the order of 1 per mille, so a change below 5 per mille leaves a signal-to-noise below 5; the full-agreement limit. An absolute proxy for the signal-to-noise (the noise is instrument-specific), so it is judged only when the paper states no signal-to-noise (range review).
FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE = 1.0  # EXPERT_REVIEW: Fnorm change (per mille) at or below which it is the noise of one capillary, conflicting.
MIN_FHOT_S = 1.0  # EXPERT_REVIEW: earliest F-hot time (seconds after the infrared laser is switched on) for a thermophoresis readout; the temperature jump of the dye is over within about a second, and a window starting earlier mixes it into the signal; the full-agreement limit.
FHOT_ZERO_AGREEMENT_S = 0.0  # EXPERT_REVIEW: F-hot time (seconds) at or below which the window starts as the laser is switched on and holds the whole temperature jump, conflicting.
MIN_CONCENTRATIONS = 10  # EXPERT_REVIEW: fewest titrant concentrations for a usable MST titration (the usual series is 16 two-fold dilutions; with fewer than ten the two baselines and the transition are not all defined); the full-credit count, with partial credit below it (no longer a pass/fail cut).
CONCENTRATIONS_ZERO_AGREEMENT = 3  # EXPERT_REVIEW: the number of free parameters of the MST KD fit (the unbound Fnorm, the bound Fnorm and the KD; the detected partner's concentration is fixed): with this many concentrations or fewer the fitted curve passes through every point and nothing is left to show the sigmoid (no credit: degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against).
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest titrant concentration must be at most this multiple of the curve's midpoint (the reported constant, or KD + [detected] / 2 with tight binding handled, or the EC50 of a competition; see _midpoint) (the unbound baseline of the curve must be defined); the full-agreement limit.
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the midpoint at or above which the lowest concentration leaves the curve with no unbound baseline at all (half the sites are already bound), conflicting; falls from LOW_FACTOR linearly in the fractional occupancy c / (c + midpoint) (1/6 at LOW_FACTOR, 1/2 here), the share of the binding curve left unsampled below the series.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest titrant concentration must be at least this multiple of the curve's midpoint, because the bound plateau is only known by reaching it (about 90 percent saturation); the full-agreement limit.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the midpoint at or below which the highest concentration reaches no more than half saturation, so the plateau is not seen at all, conflicting; falls from HIGH_FACTOR linearly in the fractional occupancy (10/11 at HIGH_FACTOR, 1/2 here): steep near the midpoint, where each step up the series adds much of the curve, gentle near the plateau (as SPR).
LABELLED_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the detected partner may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by depletion of the titrant, to about KD + [detected] / 2: 1.5-fold here); the full-agreement limit.
LABELLED_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW: detected partner over KD at or above which the apparent KD is dominated by the detected concentration (an order of magnitude of depletion, a 6-fold error of the KD), conflicting unless tight binding is handled; falls from LABELLED_MAX_OVER_KD linearly in the log of the depletion error 1 + r / 2, because the harm is a fold error of the KD, read on a log scale.
MIN_INCUBATION_MIN = 10.0  # EXPERT_REVIEW (researched value, kept): an incubation shorter than this (minutes) is too short to call a complex at equilibrium without a time course (five half-lives of an off rate of 0.01 per second are about 6 minutes, and a margin is kept for slower complexes). Since 2026-11-21 (owner to confirm) it is the reference point of a scale that follows the paper's own constant: the time needed is MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM (T_FAST, the zero end: conflicting at or below it), then a degree that is the log share of rates up to KON_SLOW_PER_M_S; no constant: unknown.
EQUILIBRATION_REFERENCE_NM = 10.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): the KD at which MIN_INCUBATION_MIN is the researched time: koff = kon x KD = 1e6 per M per s x 1e-8 M = 0.01 per s, the off rate whose five half-lives (about 6 minutes, with a margin 10) the old rule stated. koff scales with the KD at a given kon, so the time needed scales as 1 / KD. Continuous in the KD, not capped.
KON_FAST_PER_M_S = 1.0e6  # EXPERT_REVIEW (names the rate already behind the 0.01 per s and EQUILIBRATION_REFERENCE_NM, added 2026-11-21, owner to confirm): the fast end of typical protein association (Schreiber, Haran and Zhou 2009, Chem Rev 109:839, from memory); T_FAST is five half-lives at this rate, the zero end of the incubation curve.
KON_SLOW_PER_M_S = 1.0e5  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): slow association rate constant for MST partners (proteins and peptides, nucleic acids, and small ligands on a labelled protein): protein association without electrostatic steering is about 1e5 to 1e6 per M per s, and a conformational change that gates binding lowers it (Schreiber, Haran and Zhou 2009, Chem Rev 109:839, from memory; small molecules are usually faster, so 1e5 is the slow end for the class). T_SLOW = T_FAST x KON_FAST_PER_M_S / KON_SLOW_PER_M_S (ten times T_FAST) is the full-credit end.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series); the full-credit count. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): the pipetting of the serial dilution is the main run-to-run error of an MST KD, and the standard error of the mean KD over n independent series falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance); 1 titration about 0.58, 2 about 0.82; never conflicting for a stated count.
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a direct-titration KD and a competition Ki (a Ki depends on the detected partner's own KD and its uncertainty, so the standard is looser than for two direct estimates); the full-agreement limit.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap at or above which a direct KD and a competition Ki are different quantities (an order of magnitude), conflicting; falls from AGREEMENT_FACTOR linearly in log fold (5-fold about 0.58, 6.5-fold about 0.36), because the KD is read on a log scale (as SPR).
NULL_REASONS = {'recovery': 'mst_has_no_matrix_recovery_measurement', 'attributed_signal': 'mst_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'mst_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_mst_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_mst_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _agreement(value, full, zero):
    """The degree of agreement of a measured value: 1.0 at or better than the full-agreement limit, falling linearly to 0 at the zero-agreement limit (either direction); None at or beyond it."""
    fraction = (value - zero) / (full - zero)
    return None if fraction <= 0 else min(1.0, fraction)


def _scaled(value, full, zero, refs):
    degree = _agreement(value, full, zero)
    return _verdict('conflicting', refs) if degree is None else _verdict('supported', refs, degree)


def _occupancy(ratio):
    """Fractional occupancy c / (c + midpoint) of a concentration given as c / midpoint: where on the 1:1 binding curve it sits."""
    return ratio / (1 + ratio)


def _depletion_error(labelled_over_kd):
    """The fold by which a 1:1 hyperbola fit overstates the KD when the detected partner is at r x KD: about (KD + [detected] / 2) / KD."""
    return 1 + labelled_over_kd / 2


def _judge_signal(native):
    # the signal-to-noise is the paper's own relative scale and governs when stated; the Fnorm change in per mille is an absolute proxy (it assumes an
    # instrument noise of about 1 per mille) and is judged only when no signal-to-noise is stated (range review; was: the weaker of the two)
    if native['signal_to_noise'] is not None:
        return _scaled(native['signal_to_noise'], MIN_SIGNAL_TO_NOISE, SIGNAL_TO_NOISE_ZERO_AGREEMENT, native['signal_refs'])
    if native['fnorm_amplitude'] is not None and native['fnorm_noise'] is not None:
        # the paper's own noise of Fnorm turns the amplitude into a signal-to-noise (amplitude over noise), judged on the signal-to-noise scale
        return _scaled(native['fnorm_amplitude'] / native['fnorm_noise'], MIN_SIGNAL_TO_NOISE, SIGNAL_TO_NOISE_ZERO_AGREEMENT, native['signal_refs'])
    return _scaled(native['fnorm_amplitude'], MIN_FNORM_AMPLITUDE_PERMILLE, FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE, native['signal_refs'])


def _judge_fhot(native):
    return _scaled(native['fhot_s'], MIN_FHOT_S, FHOT_ZERO_AGREEMENT_S, native['fhot_refs'])


def _judge_labelled(native):
    if native['tight_binding_handled']:
        return _verdict('supported', native['labelled_refs'])      # the quadratic or tight-binding analysis does not depend on the detected partner over the KD
    error = _depletion_error(native['labelled_over_kd'])
    return _scaled(math.log(error), math.log(_depletion_error(LABELLED_MAX_OVER_KD)), math.log(_depletion_error(LABELLED_ZERO_AGREEMENT_OVER_KD)), native['labelled_refs'])


def _midpoint(native):
    """The titrant concentration (nM) at the middle of the measured curve, the scale its span is judged on, and the refs of what it used besides the constant.
    A KD with tight binding handled: KD + [detected] / 2 (half the detected partner bound needs free titrant KD plus bound titrant [detected] / 2); a KD
    fitted with the hyperbola is already the apparent midpoint. A Ki: the EC50 of the competition curve when stated (the Ki sits below the curve's middle;
    without the EC50 the Ki is used, a grader gap). An EC50 is the midpoint."""
    constant = native['constant_nM']
    if native['constant_name'] == 'kd' and native['tight_binding_handled'] and native['labelled_nM'] is not None:
        return constant + native['labelled_nM'] / 2, native['quantities']['labelled_concentration']['source_refs']
    if native['constant_name'] == 'ki' and native['ec50_nM'] is not None:
        return native['ec50_nM'], native['quantities']['ec50']['source_refs']
    return constant, []


def _judge_series(native):
    # Gradual count (was: conflicting below MIN_CONCENTRATIONS). d = (n - 3) / (10 - 3), the residual degrees of freedom of the MST KD fit over those of the
    # researched 10-point series. Why this shape for MST: every concentration is its own capillary, an independent Fnorm reading with its own noise (the
    # capillary-to-capillary scatter dominates), and the fit spends three of them on the unbound baseline, the bound plateau and the KD; what is left to show
    # the sigmoid shape grows by one capillary at a time, so the credit grows linearly with the points beyond the three fitted parameters.
    # The count only lowers the degree; at or below CONCENTRATIONS_ZERO_AGREEMENT it gives no credit, never a conflict (a short series is weaker evidence).
    count = _agreement(native['concentration_count'], MIN_CONCENTRATIONS, CONCENTRATIONS_ZERO_AGREEMENT) or 0.0
    if native['concentration_low_over_constant'] is None:
        return _verdict('unknown', [])                               # the span can only be judged from the list and the reported constant
    midpoint, midpoint_refs = _midpoint(native)
    refs = native['series_refs'] if native['concentration_count'] >= MIN_CONCENTRATIONS else list(dict.fromkeys([*native['series_refs'], *native['count_refs']]))      # a count below full credit is part of the judgement
    refs = list(dict.fromkeys([*refs, *midpoint_refs]))
    # the span over the curve's midpoint, judged on the fractional occupancy (range review; was: linear in the ratio to the reported constant); the lowest
    # is judged only when it differs from the highest (one concentration is a short series, judged by the count, not a badly placed one)
    low_ratio, high_ratio = (native[name] * native['constant_nM'] / midpoint for name in ('concentration_low_over_constant', 'concentration_high_over_constant'))
    degrees = [count, _agreement(_occupancy(high_ratio), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_AGREEMENT_FACTOR))]
    if low_ratio < high_ratio:
        degrees.append(_agreement(_occupancy(low_ratio), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_AGREEMENT_FACTOR)))
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _judge_incubation(native):
    # Was a cliff (conflicting below MIN_INCUBATION_MIN, unknown above). Now a curve on the paper's own constant: with no KD or Ki there is no scale and a time alone is
    # not the paper against equilibrium: unknown. Otherwise T_FAST = MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant is five half-lives at the fastest
    # plausible kon (the zero end: conflicting at or below it) and the degree is the share of the plausible rates, on the log scale from KON_FAST to KON_SLOW, for which
    # the incubation covers the five half-lives. No floor: MIN_INCUBATION_MIN is the scale's reference, not a mixing time.
    constant = native['incubation_constant_nM']
    if constant is None or constant <= 0:
        return _verdict('unknown', [])
    fastest = MIN_INCUBATION_MIN * EQUILIBRATION_REFERENCE_NM / constant
    if native['incubation_min'] <= fastest:
        return _verdict('conflicting', native['incubation_refs'])
    return _verdict('supported', native['incubation_refs'], min(1.0, math.log(native['incubation_min'] / fastest) / math.log(KON_FAST_PER_M_S / KON_SLOW_PER_M_S)))


def _judge_replicates(native):
    # Gradual count (was: conflicting below MIN_REPLICATES). d = min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean KD over n independent serial
    # dilutions relative to that of the researched three (see MIN_REPLICATES); never conflicting for a stated count.
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


def _judge_estimates(native):
    return _scaled(math.log(native['estimate_fold']), math.log(AGREEMENT_FACTOR), math.log(AGREEMENT_ZERO_FACTOR), native['estimate_refs'])      # linear in log fold


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_amplitude', 'signal_recorded_for_the_sheet'): _judge_signal, ('readout_window', 'fhot_time_recorded_for_the_sheet'): _judge_fhot,
          ('labelled_concentration', 'labelled_over_kd_recorded_for_the_sheet'): _judge_labelled, ('concentration_series', 'series_recorded_for_the_sheet'): _judge_series,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_incubation, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates,
          ('direct_vs_competition', 'estimates_recorded_for_the_sheet'): _judge_estimates}


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
            return None, 'sd_needs_independent_titrations_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_mst(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if native['ec50_nM'] is not None else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'mst_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'mst_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
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
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['fixed_partner_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'mst', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if constant_name is not None:
        converted['direction_field_support'] = native['quantities'][constant_name]['support']      # the support class of the operand that fixes the effect
    else:      # no binding constant: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact binding_detected, the one field the statement is derived from
    return converted
