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
criterion and reason to its judgement). Every value is a researched EXPERT_REVIEW constant with its reason. OWNER RULE (A105_EXPERIMENT_SOP step 3): no hard pass/fail
cut-off at a researched value; the researched value is the full-credit end of a gradual curve whose shape is chosen for FCS (the reason is beside each judge).
Continuous comparisons are supported with a degree of 1.0 at or better than the full-agreement limit, the degree falling to 0 at the zero-agreement limit,
and conflicting (no degree) at or beyond it: diffusion_change (ratio, linear, MIN_DIFFUSION_RATIO down to DIFFUSION_RATIO_ZERO_AGREEMENT), mass_consistency (the fold
between the diffusion ratio and the cube-root expectation, linear in its logarithm, MASS_CONSISTENCY_FACTOR up to MASS_CONSISTENCY_ZERO_FACTOR), saturation (percent,
linear, MIN_FRACTION_BOUND_MAXIMUM_PERCENT down to FRACTION_BOUND_ZERO_AGREEMENT_PERCENT), labelled_over_kd (ratio, linear, LABELLED_MAX_OVER_KD up to
LABELLED_OVER_KD_ZERO_AGREEMENT; with a tight-binding analysis full up to TIGHT_BINDING_FULL_OVER_KD and falling as the curve's rounding 1 / sqrt(ratio) to
TIGHT_BINDING_ZERO_OVER_KD), and the span of concentration_series (the lowest concentration over the KD, linear, LOW_FACTOR up to LOW_ZERO_AGREEMENT_FACTOR; the
highest judged by the fraction bound it gives a 1:1 binding, on the saturation scale). Former lone limits, full credit (no degree) at the researched value:
labelled_range (inside MIN_PARTICLE_NUMBER..MAX_PARTICLE_NUMBER, else MIN_LABELLED_NM..MAX_LABELLED_NM; outside, linear in the logarithm to the zero ends a decade
beyond, conflicting there), the count of concentration_series (sqrt(count / MIN_CONCENTRATIONS), never conflicting; the smallest of the count and the two span degrees
counts; with no list the span is not known, so unknown), acquisition ((total / MIN_TOTAL_ACQUISITION_S) ** ACQUISITION_NOISE_EXPONENT, never conflicting; a short total
with the repeat count not given stays unknown) and replicates (sqrt(count / MIN_REPLICATES), never conflicting; supported only when the independence is yes, else
unknown). equilibrium (the paper's own equilibrium fact unknown, 2026-11-21): with the KD stated, an incubation t at or below T_FAST (the time the paper's KD needs at the
fastest plausible association) conflicts, and above it the degree is min(t / MIN_INCUBATION_MIN, log(t / T_FAST) / log(T_SLOW / T_FAST)) with T_SLOW the same time at the slow
association KON_SLOW_PER_M_S (full at T_SLOW); no KD stated: unknown. The labelled_over_kd line above and the span's low end are restated below (2026-11-21).
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the
merger carries it per result). No degree holds any weight for an unknown (unknown is a status, never a degree).

Owner's questions, answered per researched value (review of 2026-11-21; Q1 failure caught, Q2 general or lab-specific, Q3 absolute or relative,
Q4 cost of being wrong and the curve shape, Q5 consistency with the other binding assays). Gaps the grader would have to fill are marked GRADER GAP.
- diffusion_change 1.3 / 1.0: Q1 a fraction bound read from a diffusion change too small to split into two components. Q2 general: two species are resolved by a
  two-component fit only from about a 1.6-fold diffusion-time difference when nothing is fixed (Meseth et al. 1999, Biophys J 76:1619), less when the free time is
  fixed (judged by diffusion_model), so 1.3 with a fixed free time; the 10 percent scatter of repeated diffusion times is typical practice. Q3 relative to the
  paper's own scatter of the diffusion times would be better: FILLED 2026-11-21 (grader gap 4: the record holds free_diffusion_time_spread, the grader records diffusion_time_scatter = spread / free time; the full-credit ratio is then 1 + (1.3 - 1) * max(scatter, 0.10) / 0.10, so the stated scatter can only raise it above 1.3). Q4 the error of a fraction bound is about
  scatter / (ratio - 1), so its precision is linear in ratio - 1: the linear ramp is that precision. Kept. Q5 like the window or Rmax checks of FP and SPR.
- mass_consistency 1.5 / 3.0: Q1 a diffusion change from aggregation, oligomerisation or another species instead of the 1:1 complex. Q2 general physics: the cube-root
  (Stokes-Einstein) law, moved by shape (Perrin friction factors of proteins about 1.1-1.3), the dye and hydration; not instrument-specific. Q3 already relative to the
  paper's own mass ratio. Q4 the mismatch is a fold and the implied mass is off by its cube (1.5 is 3.4-fold, 3 is 27-fold in mass), so equal folds must cost equal
  credit: CHANGED from linear in the fold to linear in its logarithm (a twofold mismatch, eightfold in mass, now 0.58, was 0.67). Values kept. A slower-than-expected
  complex (aggregation, the classic FCS artefact) is worse than a faster one (partial binding, an elongated partner); the curve is symmetric, owner to decide.
- saturation 80 / 20 percent: Q1 a KD extrapolated from the foot of the curve. Q2 general: a binding curve carries its information between about 20 and 80 percent
  saturation (Deranleau 1969, J Am Chem Soc 91:4044). Q3 relative by nature (a fraction). Q4 in FCS the fraction bound is an amplitude fraction of a fit whose free
  time is fixed, so the ends are anchored and a lower reach costs gradually: linear kept. Kept. Q5 the same idea as the span's high end, now judged on this scale.
- labelled_range N 0.1-10 (zero 0.01 / 100), nM 0.3-30 (zero 0.03 / 300): Q1 too few passages averaged (dilute; impurities weigh as much as the sample) or an
  amplitude 1/N lost in background, afterpulsing and laser noise (crowded). Q2 general FCS practice (Krichevsky and Bonnet 2002, Rep Prog Phys 65:251; Haustein and
  Schwille 2007, Annu Rev Biophys 36:151); the nM window is instrument-specific (it assumes a confocal volume of about half a femtolitre). Q3 the high end is really
  the count rate (N times the molecular brightness) against the detector's linear range, since without background the noise of the curve barely depends on N
  (Koppel 1974): FILLED 2026-11-21 (grader gaps 1 and 2: the record holds detection_volume in fL, so a labelled concentration is turned into a particle number, N = nM * fL * 0.6022; labelled_range reads the brightness and judges the count rate N * brightness against the detector's linear range, 1 MHz full to 10 MHz zero, log-linear, weaker of the two counts; a stated particle number, or a nM with no volume, is judged as before). Q4 both failure modes
  scale by factors of concentration: log-linear kept. Kept.
- labelled_over_kd 1 / 10: Q1 depletion of the titrant (titration regime) raising the apparent KD by about labelled / 2. Q2 general (Pollard 2010, Mol Biol Cell
  21:4061; Jarmoskaite et al. 2020, eLife 9:e57264). Q3 relative to the paper's own KD, available. Q4 the bias grows linearly with the ratio: linear kept, as in FP.
  A tight-binding (quadratic) analysis removes the bias but not the loss of information: the curve's rounding at equivalence is 1 / sqrt(ratio) of the full signal,
  so a quadratic fit at 100 times the KD (rounding 0.1, the size of the noise of an FCS amplitude fraction) gives only an upper bound of the KD. CHANGED: was full
  credit at any ratio with a tight-binding analysis; now full to TIGHT_BINDING_FULL_OVER_KD 10, falling as the rounding to TIGHT_BINDING_ZERO_OVER_KD 100, conflicting
  there. Q5 FP's tracer check has the same gap (not changed here).
- concentration_series count 8: Q1 a series too short to pin the KD and test the curve's shape. Q2 general titration practice (8-12 points; Jarmoskaite 2020).
  Q3 absolute (a count). Q4 with the free time fixed each FCS point is its own estimate of the fraction bound, so the KD's precision grows as sqrt(count): CHANGED
  from linear in residual degrees of freedom with a conflict at 3 to sqrt(count / MIN_CONCENTRATIONS), never conflicting (a short series is low partial credit;
  CONCENTRATIONS_ZERO_AGREEMENT 3 removed, it existed only as the conflict end). Whether the bound end is fixed too is not recorded: GRADER GAP NOT FILLED, on purpose (a fact that the
  bound diffusion time or the plateau was fixed): it would only move the plateau end, for which there is no researched shape, and the saturation criterion and the
  span's high end already judge the plateau reach. Q5 as the other binding assays: short is partial credit, never conflicting.
- concentration_series span low 0.2 / 1.0 KD: Q1 no free-partner baseline. Q2 general 0.1x-10x KD guidance with a factor 2 slack. Q3 relative to the KD, available.
  Q4 linear kept (in FCS the free baseline is the fixed free time, so it is the lesser end). Kept, as SPR and FP.
- concentration_series span high 10 / 1.0 KD: Q4 a mistake inside this converter: it judged the plateau reach on a second scale stricter than saturation (a top at
  the KD, 50 percent bound, conflicted here and got 0.5 there). CHANGED: the highest concentration is judged by its 1:1 fraction bound, top / (top + KD), on the
  saturation scale (80 percent, i.e. 4x KD, full; 20 percent, 0.25x KD, zero); HIGH_FACTOR 10 and HIGH_ZERO_AGREEMENT_FACTOR 1 removed.
- CHANGED 2026-11-21 (owner's decisions A, B, C; every new number EXPERT_REVIEW, owner to confirm):
  A equilibrium, cliff to curve. Q1 a pre-equilibrium titration whose apparent KD is too weak. Q2 general: five half-lives of the approach (Jarmoskaite 2020);
  KON_SLOW_PER_M_S 1e5 is new (Schreiber, Haran and Zhou 2009, Chem Rev 109:839, from memory: protein association without steering about 1e5 to 1e6, lower when a
  conformational change gates it); T_FAST (kon 1e8) is the former conflict time, kept with its formula; the 5 min floor is mixing and settling and is now proportional.
  Q3 relative to the paper's own KD (the grader already hands it with its refs); unknown without a KD. Q4 association rates span decades, so the share of plausible
  rates is judged on the log scale; t <= T_FAST stays conflicting, t >= T_SLOW is full; the floor alone never conflicts. Q5 same idea as FP, MST, Trp.
  Worked: KD 1 uM: T_FAST 0.00029 min, T_SLOW 0.289 min, so d_kon = 1 from 0.29 min and the floor decides (1 min: 0.2, 5 min: 1.0). KD 10 pM: T_FAST 28.9 min,
  T_SLOW 28 881 min (20 days): 60 min 0.106, 300 min 0.339, 28.9 min or less conflicting. Physics reason not to apply: none; the grader's equilibrium fact decides when stated.
  B labelled_over_kd without a tight-binding analysis: was linear in r between 1 and 10, now linear in log b(r), b = 1 + r / 2 (b(1) = 1.5 full, b(10) = 6 zero):
  r 2 0.79 (was 0.89), 3 0.63 (was 0.78), 5 0.39 (was 0.56). The former 'bias grows linearly, as FP' reason holds for every assay, not for FCS alone, and KD errors are folds.
  The tight-binding branch (rounding 1 / sqrt(r)) is a different physics and is unchanged.
  C span low end: was linear in low / KD between LOW_FACTOR 0.2 and LOW_ZERO_AGREEMENT_FACTOR 1.0, now linear in the occupancy x / (1 + x) between the same ends (0.167
  full, 0.5 zero): 0.25 KD 0.90 (was 0.94), 0.5 KD 0.50 (was 0.625), 0.6 KD 0.375 (was 0.5). The high end was already on the fraction bound. Ends unchanged.
- equilibrium 5 min (former notes, superseded by A above): Q1 a pre-equilibrium titration, whose apparent KD is too weak. Q2 the 5 minutes is lab practice (mixing and settling); the general rule is five
  half-lives of the approach (Jarmoskaite 2020). Q3 relative to the paper's own KD: CHANGED, the incubation must also reach EQUILIBRATION_HALF_LIVES half-lives at
  the titrant at the KD with the fastest plausible association KON_MAX_PER_M_S (k_obs = 2 kon KD); 5 minutes binds above a KD of about 60 pM, a tighter binder needs
  longer. A stated koff or time course would be exact: GRADER GAP NOT FILLED (equilibrium titrations by FCS rarely report one and the kon-at-the-diffusion-limit time is the conservative bound already used); quantities.kd is now in the criterion's reads (2026-11-21). Q4 shorter is
  conflicting, longer stays unknown (no credit side). Q5 as FP and MST, with the KD scale added.
- acquisition 60 s, exponent 0.5: Q1 a noisy correlation curve, so a noisy amplitude split. Q2 general (Koppel 1974, Phys Rev A 10:1938: noise falls as sqrt(time));
  60 s is typical practice for a millisecond diffusion time. Q3 the noise depends on the brightness and the diffusion time too (signal-to-noise about
  brightness * sqrt(time * diffusion time) for a dim molecule, and independent of the brightness for a bright one): FILLED 2026-11-21 (grader gap 3: acquisition reads the brightness and the free diffusion time; the needed total is 60 s * (diffusion time / 1 ms) * (signal factor at 10 kHz and 1 ms / signal factor of the paper) ** 2 with the signal factor m / (1 + m), m = brightness * diffusion time in photons per passage; a value not given is taken at its reference). Q4 sqrt is
  the physics. Kept.
- replicates 3: Q1 a KD from one labelling batch and dilution series, whose between-titration scatter is unknown. Q2 general (Vaux et al. 2012, EMBO Rep 13:291).
  Q3 absolute (a count). Q4/Q5 a mistake against the cross-assay rule: it was linear in degrees of freedom with a conflict at one titration. CHANGED to the precision
  of the mean, sqrt(count / MIN_REPLICATES), as FP and ITC; one titration still gives a fitted KD (0.58); REPLICATES_ZERO_AGREEMENT 1 removed.
- Unknown weight (per assay, not set here: no hook in this converter): FCS reads an absolute fraction bound only when the free time is fixed, the volume is calibrated
  and triplet, background and brightness change are handled; an unstated control can make the fraction meaningless, so an unstated FCS criterion deserves less than
  KD's 0.9. Owner to set where the row weight is decided.
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
from math import log, sqrt

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_fcs_converted_v1'
CRITERIA_MAP = {'binding_controls': ('volume_calibration', 'triplet_state', 'brightness', 'crosstalk', 'background', 'aggregates', 'photobleaching', 'surface_adsorption', 'labelling', 'specificity_control'), 'binding_regime': ('saturation', 'labelled_range', 'labelled_over_kd', 'concentration_series', 'equilibrium'), 'binding_parameter_definition': ('diffusion_model', 'fit_model'), 'calibration_applicability': ('diffusion_change', 'mass_consistency', 'acquisition'), 'sampling_basis': ('replicates',)}
MIN_DIFFUSION_RATIO = 1.3  # EXPERT_REVIEW: smallest slow-over-fast diffusion ratio of the complex and the free labelled partner that can be read as a fraction bound; diffusion times of repeated measurements scatter by about ten percent, so a change below about thirty percent cannot be told from the scatter (with nothing fixed a two-component fit needs about 1.6, Meseth et al. 1999, Biophys J 76:1619; the free time fixed, judged by diffusion_model, lowers it).
TYPICAL_TIME_SCATTER = 0.10  # EXPERT_REVIEW: the relative scatter of repeated diffusion times (about ten percent) that MIN_DIFFUSION_RATIO was reasoned with. Named here (2026-11-21, grader gap) so that the paper's own stated scatter of the free diffusion time can scale the ratio the same way: the error of a fraction bound is about scatter / (ratio - 1), so the ratio that keeps the committed error is 1 + (MIN_DIFFUSION_RATIO - 1) * scatter / TYPICAL_TIME_SCATTER. The stated scatter can only raise the requirement, never lower it below the typical one: a few repeats on one sample understate the scatter between preparations.
DIFFUSION_RATIO_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: diffusion ratio at or below which the sheet takes the diffusion change as absent (conflicting): a ratio of 1 is no change of the diffusion at all; in between the degree falls linearly.
MASS_CONSISTENCY_FACTOR = 1.5  # EXPERT_REVIEW: the reported diffusion ratio may differ from the ratio the cube-root law gives for the reported mass ratio by at most this factor either way; shape, the dye and the hydration shell move the ratio by tens of percent.
MASS_CONSISTENCY_ZERO_FACTOR = 3.0  # EXPERT_REVIEW: factor between the reported and the expected diffusion ratio at or beyond which the sheet takes them as disagreeing (conflicting); a threefold mismatch is beyond any shape or hydration effect and points to aggregation, oligomerisation or no binding. Between the two the degree is linear in the logarithm of the fold (see _judge_mass_consistency).
MIN_FRACTION_BOUND_MAXIMUM_PERCENT = 80.0  # EXPERT_REVIEW: the largest fraction bound reached (percent) must be at least this for the plateau of the binding curve to be known; at 80 percent the titration reaches about four times the KD of a one-site binding (the 20-80 percent saturation window, Deranleau 1969, J Am Chem Soc 91:4044). Also the full-credit end of the span's high end (judged by the fraction bound it gives).
FRACTION_BOUND_ZERO_AGREEMENT_PERCENT = 20.0  # EXPERT_REVIEW: largest fraction bound (percent) at or below which the sheet takes the plateau as not reached at all (conflicting); at 20 percent bound the highest titrant concentration is about a quarter of the KD, only the foot of the curve is seen.
MIN_PARTICLE_NUMBER = 0.1  # EXPERT_REVIEW: fewest fluorescent molecules on average in the confocal volume; below it the molecules are in the volume so seldom that the correlation curve needs impractically long measurements. Softened: the low full-credit end of the particle-number window.
MAX_PARTICLE_NUMBER = 10.0  # EXPERT_REVIEW: most fluorescent molecules on average in the confocal volume; the correlation amplitude is the inverse of this number, and above it the fluctuations are lost in the shot noise. Softened: the high full-credit end of the particle-number window.
PARTICLE_NUMBER_LOW_ZERO_AGREEMENT = 0.01  # EXPERT_REVIEW (added by the 2026-11-21 softening, owner to confirm): particle number at or below which the labelled partner is taken as too dilute for FCS (conflicting), one decade below MIN_PARTICLE_NUMBER; at 0.01 molecules the volume is empty about 99 percent of the time, so ten times fewer passages are averaged than at 0.1 in the same time, and a rare bright impurity or aggregate weighs as much as the sample.
PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT = 100.0  # EXPERT_REVIEW (added by the 2026-11-21 softening, owner to confirm): particle number at or above which the labelled partner is taken as too concentrated for FCS (conflicting), one decade above MAX_PARTICLE_NUMBER; at 100 molecules the correlation amplitude 1/N is 0.01, a fluctuation of one percent of the mean signal, of the order of the distortions from uncorrelated background, detector afterpulsing and laser intensity noise.
MAX_COUNT_RATE_KHZ = 1000.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm; grader gap, the high end of the labelled range is the count rate): total count rate (kHz, the particle number times the molecular brightness) up to which a single-photon avalanche detector counts linearly; with a dead time of about 50 ns (typical of the silicon detectors of FCS set-ups) 1 MHz loses about 5 percent of the counts, which is within the noise of the amplitude. Full-credit end of the count-rate curve.
COUNT_RATE_ZERO_KHZ = 10000.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): total count rate (kHz) at or above which the detector no longer counts what arrives (conflicting): at 10 MHz with a dead time of 50 ns a third of the counts are lost and the correlation curve is distorted beyond use (and the detector can be damaged). Between the two the degree falls linearly in the logarithm of the rate, as both ends are factors.
MIN_LABELLED_NM = 0.3  # EXPERT_REVIEW: lowest labelled concentration (nM) used when no particle number is given; in a typical confocal volume of about half a femtolitre 0.3 nM is about 0.1 molecules.
MAX_LABELLED_NM = 30.0  # EXPERT_REVIEW: highest labelled concentration (nM) used when no particle number is given; in a typical confocal volume of about half a femtolitre 30 nM is about 10 molecules.
LABELLED_LOW_ZERO_AGREEMENT_NM = 0.03  # EXPERT_REVIEW (added by the 2026-11-21 softening, owner to confirm): labelled concentration (nM) at or below which the labelled partner is taken as too dilute (conflicting) when no particle number is given; in a volume of about half a femtolitre 0.03 nM is about 0.01 molecules (PARTICLE_NUMBER_LOW_ZERO_AGREEMENT).
LABELLED_HIGH_ZERO_AGREEMENT_NM = 300.0  # EXPERT_REVIEW (added by the 2026-11-21 softening, owner to confirm): labelled concentration (nM) at or above which the labelled partner is taken as too concentrated (conflicting) when no particle number is given; in a volume of about half a femtolitre 300 nM is about 100 molecules (PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT).
LABELLED_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the labelled partner may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by depletion of the free titrant).
LABELLED_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: multiple of the KD at or above which the sheet takes the labelled partner as too high for any KD to be read without a tight-binding analysis (conflicting); at ten times the KD the titration is stoichiometric and the transition sits at the labelled concentration, not at the KD.
TIGHT_BINDING_FULL_OVER_KD = 10.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): with a tight-binding (quadratic) analysis the depletion bias is removed, and the curve keeps a rounding at equivalence of 1 / sqrt(labelled / KD) of the full signal; up to ten times the KD that rounding (0.32) is about three times the noise of an FCS amplitude fraction, so the KD is well defined: full credit.
TIGHT_BINDING_ZERO_OVER_KD = 100.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): at a hundred times the KD the rounding 1 / sqrt(100) = 0.1 is the size of the noise of a two-component amplitude fraction (about ten percentage points, Meseth et al. 1999, Biophys J 76:1619), so even a quadratic fit gives only an upper bound of the KD (Jarmoskaite et al. 2020, eLife 9:e57264, titration regime): conflicting. Between, the degree is the rounding above this noise, relative to its value at TIGHT_BINDING_FULL_OVER_KD.
DEPLETION_BIAS_SLOPE = 0.5  # EXPERT_REVIEW (named 2026-11-21, owner to confirm; the physics is the standard titration-regime estimate, Jarmoskaite et al. 2020, eLife 9:e57264, from memory): with the labelled partner at r times the KD the apparent KD is about KD + labelled / 2, so the bias fold is b(r) = 1 + DEPLETION_BIAS_SLOPE * r; b(1) = 1.5 (full) and b(10) = 6 (conflicting) at this assay's own ends.
ROUNDING_EXPONENT = -0.5 # FIXED_BY_DEFINITION: the quadratic (tight-binding) curve with the labelled partner at r times the KD is bound to 1 - 1 / sqrt(r) at equivalence (r >> 1), so its rounding is r ** -0.5 of the full signal.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable titration (general titration practice is 8 to 12 points; with fewer the transition and the curve's shape are thinly sampled). The full-credit end of the count curve.
SERIES_PRECISION_EXPONENT = 0.5  # EXPERT_REVIEW (2026-11-21, owner to confirm): with the free diffusion time fixed, each FCS titration point is its own amplitude-fraction estimate of the fraction bound, so the precision of the KD grows as the square root of the count: the count's degree is (count / MIN_CONCENTRATIONS) ** 0.5. A short series is low partial credit, never conflicting (cross-assay rule); one point gives 0.35, three 0.61.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest titrant concentration must be at most this multiple of the KD (the free-partner baseline of the curve must be defined; 0.1x KD general practice with a factor of 2 slack, as SPR and FP).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or above which the lowest titrant concentration leaves no free-partner baseline (conflicting); at the KD the partner is already half bound.
MIN_INCUBATION_MIN = 5.0  # EXPERT_REVIEW: the incubation (minutes) that covers mixing and settling of a small sample in a chamber (a few minutes; lab practice); the floor under the KD-derived times below. An incubation shorter than this gets the proportional degree t / MIN_INCUBATION_MIN (never conflicting by itself).
KON_MAX_PER_M_S = 1.0e8  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): fastest plausible association rate constant of a protein binding (per molar per second; the diffusion limit, Jarmoskaite et al. 2020, eLife 9:e57264; most protein pairs are 1e5 to 1e7 without electrostatic steering), so the equilibration time it gives is the shortest any real binding with the paper's KD can have.
KON_SLOW_PER_M_S = 1.0e5  # EXPERT_REVIEW (added 2026-11-21, owner to confirm; citation from memory): slow association rate constant of this assay's partners (per molar per second), the other end of the log scale of association rates from KON_MAX_PER_M_S. FCS partners are mostly proteins binding proteins, nucleic acids or small ligands; the basal association of proteins without electrostatic steering is about 1e5 to 1e6 (Schreiber, Haran and Zhou 2009, Chem Rev 109:839), and a conformational change gating the binding goes lower, so 1e5 is the slow end of the plausible rates; T_SLOW is then the incubation that equilibrates a binding with the paper's KD at that rate.
EQUILIBRATION_HALF_LIVES = 5.0 # EXPERT_REVIEW (added 2026-11-21, owner to confirm): half-lives of the approach to equilibrium an incubation must cover (five give 97 percent of the equilibrium signal; Jarmoskaite et al. 2020). The approach is judged with the titrant at the KD, where the KD is read: k_obs = kon * KD + koff = 2 * kon * KD.
M_PER_NM = 1.0e-9  # FIXED_BY_DEFINITION: one nanomolar in molar.
S_PER_MIN = 60.0  # FIXED_BY_DEFINITION: seconds in a minute.
MIN_TOTAL_ACQUISITION_S = 60.0  # EXPERT_REVIEW: least total acquisition time per sample (seconds, one measurement times its repeats); at nanomolar concentrations a correlation curve of a molecule that crosses the volume in a millisecond needs about a minute of photons for a stable fit. Softened: the full-credit end of the acquisition curve.
ACQUISITION_NOISE_EXPONENT = 0.5  # EXPERT_REVIEW (added by the 2026-11-21 softening, owner to confirm): the noise of a measured correlation curve at a given lag falls with the square root of the total acquisition time (Koppel 1974, Phys Rev A 10:1938), so a total T below MIN_TOTAL_ACQUISITION_S gives a curve (T / MIN_TOTAL_ACQUISITION_S) ** 0.5 as precise as the full-credit one.
REFERENCE_DIFFUSION_TIME_US = 1000.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): the diffusion time (microseconds) for which MIN_TOTAL_ACQUISITION_S is the researched total ('a molecule that crosses the volume in a millisecond'). The independent samples of a curve number total / diffusion time, so the total needed grows in proportion to the diffusion time (Koppel 1974).
REFERENCE_BRIGHTNESS_KHZ = 10.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): the molecular brightness (kilohertz, counts per second per molecule) with which MIN_TOTAL_ACQUISITION_S is reasoned; 10 kHz per molecule is the lower end of what well-behaved organic dyes (Alexa 488, Atto dyes, rhodamines) give at tens of microwatts at the sample.
PHOTONS_PER_KHZ_US = 1.0e-3  # FIXED_BY_DEFINITION: photons per molecule per diffusion time for a brightness of 1 kHz and a diffusion time of 1 microsecond (1000 counts per second times 1e-6 seconds).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series or preparations; Vaux et al. 2012, EMBO Rep 13:291). The full-credit end of the replicate curve.
REPLICATE_PRECISION_EXPONENT = 0.5  # EXPERT_REVIEW (2026-11-21, the cross-assay rule, as FP and ITC): the standard error of a KD averaged over n independent titrations falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance), so the degree is the precision relative to MIN_REPLICATES, (n / MIN_REPLICATES) ** 0.5; one titration still gives a fitted KD (0.58), never conflicting.
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


def _softened_verdict(degree, refs):
    """A former lone limit made gradual: at or past the researched value supported with no degree (the committed full-credit answer, unchanged); between it
    and the zero end supported with the degree; at or past the zero end conflicting (the stated value itself is against the standard)."""
    if degree <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, degree if degree < 1.0 else None)


def _log_window_degree(value, low_full, low_zero, high_full, high_zero):
    """Full credit inside [low_full, high_full]; outside it the degree falls linearly in the logarithm of the value to 0 at low_zero or high_zero."""
    if value <= 0:
        return 0.0
    position = log(value)
    return min(1.0, _degree(position, log(low_full), log(low_zero)), _degree(position, log(high_full), log(high_zero)))


# Relative to the paper's own scatter (grader gap 4): the ratio for full credit is 1 + (MIN_DIFFUSION_RATIO - 1) * scatter / TYPICAL_TIME_SCATTER, the stated scatter
# of the free diffusion time (relative to that time) replacing the typical one only where it is larger. Without a stated scatter it is MIN_DIFFUSION_RATIO, unchanged.
def _judge_diffusion_change(native):
    scatter = native['diffusion_time_scatter']
    full = MIN_DIFFUSION_RATIO if scatter is None else 1.0 + (MIN_DIFFUSION_RATIO - 1.0) * max(scatter, TYPICAL_TIME_SCATTER) / TYPICAL_TIME_SCATTER
    return _degree_verdict(native['diffusion_ratio'], full, DIFFUSION_RATIO_ZERO_AGREEMENT, native['diffusion_refs'])


# Shape of the mass consistency (was linear in the fold): linear in the logarithm of the fold, because the fold is a ratio whose cube is the factor by which the
# implied mass is off (1.5 is 3.4-fold, 2 is 8-fold, 3 is 27-fold in mass), so equal folds must cost equal credit.
def _judge_mass_consistency(native):
    ratio, expected = native['diffusion_ratio'], native['expected_diffusion_ratio']
    fold = max(ratio / expected, expected / ratio)
    return _degree_verdict(log(fold), log(MASS_CONSISTENCY_FACTOR), log(MASS_CONSISTENCY_ZERO_FACTOR), native['mass_consistency_refs'])


def _judge_saturation(native):
    return _degree_verdict(native['fraction_bound_maximum'], MIN_FRACTION_BOUND_MAXIMUM_PERCENT, FRACTION_BOUND_ZERO_AGREEMENT_PERCENT, native['fraction_bound_maximum_refs'])


def _one_site_percent_bound(over_kd):
    """The percent of the labelled partner bound by a one-site binding with the titrant at over_kd times the KD (titrant in excess)."""
    return 100.0 * over_kd / (1.0 + over_kd)


# Shape of the labelled-range window (was: conflicting just outside MIN..MAX): log-linear outside the window, because in FCS the correlation amplitude is 1/N
# and both failure modes scale by factors of concentration (too few passages averaged when dilute, an amplitude shrinking as 1/N when concentrated); a
# threefold excess is as bad as a threefold shortfall whatever the absolute numbers, so equal factors take equal steps of credit.
# The particle number is the stated one or, with the stated detection volume, the labelled concentration turned into molecules in that volume (grader gap 2); with the
# molecular brightness given, the total count rate (particle number times brightness) is judged too, against the detector's linear range (grader gap 1), and the
# weaker of the two counts. With no brightness the count rate is not known and only the particle number is judged.
def _judge_particle_number(native):
    degree = _log_window_degree(native['particle_number_used'], MIN_PARTICLE_NUMBER, PARTICLE_NUMBER_LOW_ZERO_AGREEMENT, MAX_PARTICLE_NUMBER, PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT)
    if native['count_rate_kHz'] is not None:
        degree = min(degree, _degree(log(native['count_rate_kHz']), log(MAX_COUNT_RATE_KHZ), log(COUNT_RATE_ZERO_KHZ)))
    return _softened_verdict(degree, native['labelled_range_refs'])


def _judge_labelled_concentration(native):
    return _softened_verdict(_log_window_degree(native['labelled_nM'], MIN_LABELLED_NM, LABELLED_LOW_ZERO_AGREEMENT_NM, MAX_LABELLED_NM, LABELLED_HIGH_ZERO_AGREEMENT_NM), native['labelled_range_refs'])


# Shape with a tight-binding analysis (was: full credit at any ratio): the depletion bias is removed, but the KD's information is the rounding of the curve at
# equivalence, 1 / sqrt(ratio) of the full signal; the degree is that rounding above the noise of an amplitude fraction (its value at TIGHT_BINDING_ZERO_OVER_KD),
# relative to its value at TIGHT_BINDING_FULL_OVER_KD. Without the analysis the bias grows linearly with the ratio: linear, as committed (and as FP).
def _judge_labelled_over_kd(native):
    ratio, refs = native['labelled_over_kd'], native['labelled_over_kd_refs']
    if ratio > LABELLED_MAX_OVER_KD and native['tight_binding_analysis']:
        if ratio <= TIGHT_BINDING_FULL_OVER_KD:
            return _verdict('supported', refs)      # the depletion is handled by the analysis and the rounding is well above the noise: no degree
        rounding = (ratio ** ROUNDING_EXPONENT, TIGHT_BINDING_FULL_OVER_KD ** ROUNDING_EXPONENT, TIGHT_BINDING_ZERO_OVER_KD ** ROUNDING_EXPONENT)
        return _softened_verdict(_degree(*rounding), refs)
    # Without the analysis: the depletion bias of the apparent KD, b(r) = 1 + r / 2, judged on its logarithm between the assay's own ends (KD errors are folds; as FP, MST, Trp).
    bias = lambda r: log(1.0 + DEPLETION_BIAS_SLOPE * r)
    return _degree_verdict(bias(ratio), bias(LABELLED_MAX_OVER_KD), bias(LABELLED_OVER_KD_ZERO_AGREEMENT), refs)


# Shape of the count (was linear in the residual degrees of freedom, conflicting at three): the square root of the count over MIN_CONCENTRATIONS, because with the
# free diffusion time fixed each FCS point is its own amplitude-fraction estimate of the fraction bound and the KD's precision grows as sqrt(count). A short series
# is low partial credit, never conflicting. The high end of the span is judged by the one-site fraction bound it gives, on the saturation scale (was a second,
# stricter scale, 10x / 1x KD, that judged the same reach of the plateau differently from the saturation criterion).
def _judge_concentration_series(native):
    count_degree = (native['concentration_count'] / MIN_CONCENTRATIONS) ** SERIES_PRECISION_EXPONENT
    low, high = native['concentration_low_over_constant'], native['concentration_high_over_constant']
    if low is None:
        return _verdict('unknown', [])      # the span can only be judged from the list and the KD
    # The low end on the one-site occupancy low / (1 + low), the share of the binding curve covered, between this assay's own ends (LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR); the high end already is.
    degrees = (_degree(_one_site_percent_bound(low), _one_site_percent_bound(LOW_FACTOR), _one_site_percent_bound(LOW_ZERO_AGREEMENT_FACTOR)), _degree(_one_site_percent_bound(high), MIN_FRACTION_BOUND_MAXIMUM_PERCENT, FRACTION_BOUND_ZERO_AGREEMENT_PERCENT))
    if min(degrees) <= 0:
        return _verdict('conflicting', native['concentration_span_refs'])
    return _verdict('supported', native['concentration_span_refs'], min(1.0, count_degree, *degrees))      # the weakest of the count and the two ends


def _equilibration_min(kd_nM, kon_per_M_s):
    """The shortest incubation (minutes) a binding with this KD needs: EQUILIBRATION_HALF_LIVES half-lives of the approach with the titrant at the KD and the
    given association rate constant, k_obs = 2 * kon * KD."""
    return EQUILIBRATION_HALF_LIVES * log(2.0) / (2.0 * kon_per_M_s * kd_nM * M_PER_NM) / S_PER_MIN


# Shape of the equilibrium (was a cliff: conflicting below the larger of MIN_INCUBATION_MIN and the time the fastest association needs, unknown above, no credit side).
# The paper's own equilibrium fact is unknown here, so the incubation is judged against the unknown association rate on the log scale (association rates span decades):
# d_kon = log(t / T_FAST) / log(T_SLOW / T_FAST), clipped to 0..1, the share of the plausible rates for which the incubation covers EQUILIBRATION_HALF_LIVES half-lives.
# t <= T_FAST stays conflicting (even the fastest plausible association has not equilibrated; today's conflict, the zero end). t >= T_SLOW is full. The lab floor
# MIN_INCUBATION_MIN (mixing and settling) is proportional, d_floor = min(1, t / MIN_INCUBATION_MIN), never conflicting by itself. Degree = min(d_floor, d_kon).
# No KD stated: there is no scale, a time alone is not the paper against equilibrium: unknown, also below the floor. (Owner to confirm: the floor no longer conflicts.)
def _judge_equilibrium(native):
    incubation, kd = native['incubation_min'], native['kd_nM']
    if kd is None:
        return _verdict('unknown', [])
    t_fast, t_slow = _equilibration_min(kd, KON_MAX_PER_M_S), _equilibration_min(kd, KON_SLOW_PER_M_S)
    refs = list(dict.fromkeys(native['incubation_refs'] + native['quantities']['kd']['source_refs']))
    if incubation <= t_fast:
        return _verdict('conflicting', refs)
    d_kon = min(1.0, log(incubation / t_fast) / log(t_slow / t_fast))
    d_floor = min(1.0, incubation / MIN_INCUBATION_MIN)
    return _softened_verdict(min(d_floor, d_kon), refs)


# Shape of the acquisition (was: conflicting below MIN_TOTAL_ACQUISITION_S when the repeat count is given): the square root of the total over the researched
# minimum, because the noise of an FCS correlation curve falls with the square root of the photon-collection time (Koppel 1974); the degree is the
# precision of the curve relative to the full-credit one. It reaches 0 only at no acquisition, so a stated short total gets partial credit, never a conflict.
# The total needed scales with the diffusion time and the brightness (grader gap 3; Koppel 1974): the curve has total / diffusion time independent samples, and each
# sample's signal-to-noise rises with the photons a molecule gives in one diffusion time, m = brightness * diffusion time, as m / (1 + m) (it saturates once a molecule
# gives about a photon or more per passage: a brighter dye then does not help; below one it is proportional to m). The needed total is MIN_TOTAL_ACQUISITION_S at the
# reference diffusion time and brightness and scales as (diffusion time / reference) * (reference signal factor / its signal factor) ** 2. A value not given is taken at
# its reference (the committed 60 s then applies unchanged).
def _acquisition_needed_s(free_time_us, brightness_kHz):
    time = REFERENCE_DIFFUSION_TIME_US if free_time_us is None else free_time_us
    bright = REFERENCE_BRIGHTNESS_KHZ if brightness_kHz is None else brightness_kHz
    m, m_reference = bright * time * PHOTONS_PER_KHZ_US, REFERENCE_BRIGHTNESS_KHZ * REFERENCE_DIFFUSION_TIME_US * PHOTONS_PER_KHZ_US
    return MIN_TOTAL_ACQUISITION_S * (time / REFERENCE_DIFFUSION_TIME_US) * ((m_reference / (1.0 + m_reference)) / (m / (1.0 + m))) ** 2


def _judge_acquisition(native):
    total = native['acquisition_total_s']
    needed = _acquisition_needed_s(native['free_diffusion_time_us'], native['brightness_kHz'])
    if total < needed and not native['measurement_repeats_given']:
        return _verdict('unknown', [])      # a short single measurement: the repeats may be unreported
    return _softened_verdict(min(1.0, total / needed) ** ACQUISITION_NOISE_EXPONENT, native['acquisition_refs'])


# Shape of the replicates (was linear in the degrees of freedom of the spread, conflicting at one titration; a mistake against the cross-assay rule): the
# precision of the mean KD over n independent titrations relative to MIN_REPLICATES, (n / MIN_REPLICATES) ** 0.5, as FP and ITC; one titration still gives a
# fitted KD, so it keeps partial credit and never conflicts. A count without independence stated yes is unknown (a stated no conflicts in the grader).
def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])
    return _softened_verdict(min(1.0, (native['replicate_count'] / MIN_REPLICATES) ** REPLICATE_PRECISION_EXPONENT), native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('diffusion_change', 'diffusion_ratio_recorded_for_the_sheet'): _judge_diffusion_change, ('mass_consistency', 'mass_consistency_recorded_for_the_sheet'): _judge_mass_consistency,
          ('saturation', 'fraction_bound_maximum_recorded_for_the_sheet'): _judge_saturation, ('labelled_range', 'particle_number_recorded_for_the_sheet'): _judge_particle_number,
          ('labelled_range', 'particle_number_derived_from_volume_recorded_for_the_sheet'): _judge_particle_number, ('labelled_range', 'labelled_concentration_recorded_for_the_sheet'): _judge_labelled_concentration, ('labelled_over_kd', 'labelled_over_kd_recorded_for_the_sheet'): _judge_labelled_over_kd,
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
