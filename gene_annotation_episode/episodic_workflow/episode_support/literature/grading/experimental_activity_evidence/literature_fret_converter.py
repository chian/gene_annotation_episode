"""FRET converter: turns the FRET grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to FRET, deterministic. Input: the result of grade_fret.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI and FP converters fill), the
dependence keys the merger needs, and for every sheet component that a FRET
measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  KD of a direct titration, or, when the record has no KD,
                  the Ki of a competition experiment (the measurement key
                  names it: fret_kd or fret_ki). Neither given leaves effect
                  null; an EC50 or an IC50 alone is not a binding constant (it
                  depends on the labelled concentrations) and is not carried
                  into the effect.
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
immobilized_preparation_ref = the labelled partner held fixed, surface_ref = None
(FRET in solution has no surface), dataset_ref = the dataset.

Criteria mapping (FRET criteria -> sheet criteria), declared in CRITERIA_MAP
----------------------------------------------------------------------------
binding_controls              spectral_crosstalk + specificity_control +
                              compound_interference
binding_regime                labelled_concentration + concentration_series +
                              equilibrium + direct_vs_competition
binding_parameter_definition  fit_model + labelling_scheme + ratiometric_readout
calibration_applicability     assay_window + time_gating (the ratio span against
                              the plate reader's resolution, and the gating of the
                              read: FRET's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Every value is a researched EXPERT_REVIEW constant with its reason.
OWNER RULE (A105_EXPERIMENT_SOP step 3, soften, do not cut): the researched value is the full-credit end of a gradual curve whose shape is chosen for FRET (the
owner's questions below give the reason of each shape). Supported with a degree (1.0 at or better than the full-agreement limit, falling to 0 at the zero end),
conflicting at or beyond a zero end only where the stated value itself is against the standard:
- assay_window: the ratio fold, linear, MIN_WINDOW_FOLD down to WINDOW_ZERO_AGREEMENT_FOLD (conflicting there: no window); when the paper states a Z' factor, also Z'
  linear, Z_PRIME_MIN down to Z_PRIME_ZERO (conflicting there: no separation of the plateaus); the weaker of the two.
- time_gating: the delay, linear, MIN_DELAY_US down to DELAY_ZERO_AGREEMENT_US (conflicting there: not gated in effect); the integration window, when given,
  (window / MIN_INTEGRATION_US) ** INTEGRATION_NOISE_EXPONENT, never conflicting (fewer photons only), where the window is first scaled to the donor's own lifetime
  when the paper names the lanthanide (window x REFERENCE_LIFETIME_US / DONOR_LIFETIME_US[lanthanide]); the weaker of the two.
- labelled_concentration: labelled over KD, linear in the log of the depletion bias 1 + ratio / 2, from LABELLED_MAX_OVER_KD up to LABELLED_ZERO_AGREEMENT_OVER_KD; with a tight-binding analysis (quadratic fit or tight
  binding stated as considered) full up to TIGHT_BINDING_FULL_OVER_KD and falling as the curve's rounding at equivalence, 1 / sqrt(ratio), to TIGHT_BINDING_ZERO_OVER_KD.
- concentration_series: the count linear in the residual degrees of freedom of the fit, SERIES_FIT_PARAMETERS (HILL_FIT_PARAMETERS for a Hill fit) up to
  MIN_CONCENTRATIONS, never conflicting (a short series is weaker evidence, not evidence against); the lowest and highest concentration linear in the one-site
  occupancy x / (1 + x) between LOW_FACTOR / LOW_ZERO_AGREEMENT_FACTOR and HIGH_FACTOR / HIGH_ZERO_AGREEMENT_FACTOR, where x is the concentration over the curve's own
  midpoint (the titration the paper says the series belongs to, series_format: the KD, else EC50, of a direct titration, the IC50, else Ki, of a competition; when it
  is not stated, a competition format or a Ki as the constant gives the IC50 else Ki, otherwise the reported constant); the weakest of the three.
- direct_vs_competition: the fold of KD and Ki, linear in its logarithm, AGREEMENT_FACTOR up to AGREEMENT_ZERO_FACTOR.
- replicates: sqrt(n / MIN_REPLICATES) below MIN_REPLICATES when the independence is yes, full at it; unknown when the independence is not stated.
- equilibrium: with a stated incubation and a stated koff, the fraction of the approach to equilibrium reached, 1 - 2 ** (-incubation x koff / ln 2), linear from
  APPROACH_ZERO_HALF_LIVES half-lives (conflicting) to APPROACH_FULL_HALF_LIVES (full); with no koff, the share of the plausible association rates covered:
  log(t / T_FAST) / log(KON_FAST / KON_SLOW) clipped to 0..1, T_FAST = MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM (conflicting at or below it);
  with no constant, unknown.
A sheet criterion that is supported carries the smallest degree of its members that have one. No unknown weight is used inside any degree here (FRET's unknown
weights, default 0.75 with binding_controls 0.70, binding_parameter_definition 0.70, calibration_applicability 0.85, live in literature_row_contract).

Owner's questions, answered per researched value (review of 2026-11-21; Q1 failure caught, Q2 general practice or lab-specific, Q3 absolute or relative and is the
relative quantity in the grader facts, Q4 how badly a wrong value misleads and whether the shape follows, Q5 consistency with the other binding assays). Facts the
grader would have to collect are marked GRADER GAP (not changed here: a grader change needs a real-model run).
- MIN_WINDOW_FOLD 2 / WINDOW_ZERO_AGREEMENT_FOLD 1: Q1 a titration whose ratio change is too small to separate the free and bound plateaus, so the constant is set by
  noise. Q2 general: Z' >= 0.5 is the robust-assay limit (Zhang, Chung and Oldenburg 1999, J Biomol Screen 4:67), and with 5 percent scatter at both ends a fold of
  2 gives Z' about 0.55; TR-FRET windows of 2 to 20 are usual (Degorce et al. 2009, Curr Chem Genomics 3:22). Q3 already relative to the paper's own free-state
  ratio; the better scale, the window over the scatter of the ratio (Z' or S/N), needs that scatter: GRADER GAP (no SD of the ratio or Z' is recorded). Q4 the
  error of a fraction bound is the ratio's scatter over (fold - 1), so its precision is linear in fold - 1: the linear ramp is that precision; above 2 the cap
  carries the concavity the AlphaScreen log ramp gives over 1 to 10 (log and linear differ by at most 0.09 between 1 and 2). KEPT. Q5 the window check of FP and
  AlphaScreen; a fold of 1 is the paper's own data showing no change, so conflicting at the zero end is allowed.
- MIN_DELAY_US 50 / DELAY_ZERO_AGREEMENT_US 5: Q1 prompt background (compound and plate fluorescence, direct acceptor excitation, flash afterglow) read with the
  lanthanide emission, which can turn an autofluorescent titrant into an apparent binding curve. Q2 general TR-FRET practice, 50 to 150 us (Degorce et al. 2009;
  vendor HTRF and LANCE defaults). Q3 absolute is right: the prompt background decays in nanoseconds to a few microseconds whatever the concentrations, and
  every lanthanide donor lives far longer (hundreds of us to ms), so the delay costs it nothing. Q4 the background decays exponentially, so the decades of
  background rejected grow linearly with the delay: the linear ramp is linear in the rejection. KEPT. Q5 a delay at the zero end leaves the read ungated and
  uncorrected, the same as a plain FRET read whose crosstalk correction is stated 'no' (spectral_crosstalk conflicting): conflicting there is consistent.
- MIN_INTEGRATION_US 100 (INTEGRATION_ZERO_AGREEMENT_US 10 removed, INTEGRATION_NOISE_EXPONENT 0.5 added): Q1 a ratio counted from too few donor and acceptor
  photons. Q2 general: integration windows of 200 to 400 us are kit defaults (Degorce et al. 2009); 100 us is the lenient full-credit end. Q3 relative to the
  donor's lifetime would be exact (the fraction collected is about window / lifetime; Tb and Eu differ two- to threefold): GRADER GAP (the lanthanide and its
  lifetime are not recorded, only 'lanthanide_with_organic_acceptor'). Q4 MISTAKE: a short window was conflicting at 10 us, but it only collects fewer photons,
  and the paper's ratio is still a ratio: it costs precision, not meaning. The ratio's counting noise falls as sqrt(photons), i.e. sqrt(window). CHANGED: linear
  10 -> 100 with a conflict -> sqrt(window / 100), never conflicting (10 us now 0.32 supported, 55 us 0.74, was 0.5). Q5 as the FCS acquisition time (sqrt,
  never conflicting) and the short-series rule.
- MIN_CONCENTRATIONS 8 / SERIES_FIT_PARAMETERS 3 (HILL_FIT_PARAMETERS 4 added): Q1 a series too short to pin the KD and test the hyperbola. Q2 general titration
  practice, 8 to 12 points (Jarmoskaite et al. 2020, eLife 9:e57264; NCBI Assay Guidance Manual); FRET plate series are usually 10 to 16 points. Q3 absolute (a
  count), but the parameters the fit consumes follow the paper's stated model (fit_model is in the grader facts): a Hill fit frees the Hill coefficient too.
  CHANGED: zero-credit count 3 -> 4 for a Hill fit (3 for 1:1, quadratic at a known labelled concentration and competition at a known tracer KD). Q4 the width of
  the KD's confidence interval, t(n - p) / sqrt(n), relative to that at 8 points is 0.87, 0.70, 0.47, 0.14, 0 for 7 to 3 points against the linear 0.8, 0.6, 0.4,
  0.2, 0: linear in the residual degrees of freedom follows it. Shape KEPT. Q5 as SPR and AlphaScreen (linear in residual degrees of freedom, never conflicting);
  FCS uses sqrt(count) because its ends are fixed, which a FRET fit's ends are not.
- LOW_FACTOR 0.2 / LOW_ZERO_AGREEMENT_FACTOR 1 and HIGH_FACTOR 10 / HIGH_ZERO_AGREEMENT_FACTOR 1: Q1 a series that misses the free baseline or the bound plateau,
  so the fit extrapolates them and the constant drifts. Q2 general (0.1x to 10x the constant; Hulme and Trevethick 2010, Br J Pharmacol 161:1219; Jarmoskaite et al.
  2020). Q3 relative to the curve's own midpoint, in the grader facts. MISTAKE: for a competition the grader's constant is the Ki (or the tracer's KD), but the
  competitor's curve turns at its IC50 = Ki (1 + labelled / KD), so the span was judged against the wrong point. CHANGED: a competition (format 'competition', or a
  Ki as the constant) is judged against its IC50 when stated, else its Ki. Which titration the series belongs to is not recorded: GRADER GAP (a series tied to the
  direct or the competitor titration). Q4 what each end shows is the one-site occupancy reached there: 2x already shows 67 percent of the plateau, 5x 83, 10x 91,
  so the linear ramp in x was steep where little changes (5x got 0.44). CHANGED: linear in x -> linear in occupancy (5x now 0.81, 2x 0.41; lowest end 0.6x 0.375,
  was 0.5). Values KEPT. Q5 as AlphaScreen (same values, same shape) and FCS (high end on the occupancy scale).
- LABELLED_MAX_OVER_KD 1 / LABELLED_ZERO_AGREEMENT_OVER_KD 10 (TIGHT_BINDING_FULL_OVER_KD 10 and TIGHT_BINDING_ZERO_OVER_KD 100 added): Q1 depletion of the titrant
  (titration regime), raising the apparent KD by about labelled / 2. Q2 general (Pollard 2010, Mol Biol Cell 21:4061; Jarmoskaite et al. 2020; Hieb et al. 2012,
  NAR 40:e33 for FRET). Q3 relative to the paper's own KD, in the grader facts. Q4 (changed 2026-11-21, owner to confirm) without a tight-binding analysis the bias is
  b = 1 + ratio / 2 (apparent KD about KD + labelled / 2) and a KD error is a fold, so the degree is linear in log b between the kept ends b(1) = 1.5 (full) and
  b(10) = 6 (conflicting): ratio 5.5 gives (ln 6 - ln 3.75) / ln 4 = 0.34, was linear 0.5; no assay-specific reason for a linear scale (the bias is linear in the
  ratio, but the error it causes is the fold). Q5 as TRP, FP, MST and split reporter. MISTAKE (tight-binding branch, unchanged): with a tight-binding analysis any ratio got full credit, but the analysis removes the bias, not the loss of information: the curve's rounding at
  equivalence is 1 / sqrt(ratio) of the full signal, and at 100x KD that rounding (0.1) is the noise of a fraction bound read from a ratio of fold 2 with 5 percent
  scatter, so only an upper bound of the KD is left. CHANGED: full credit to 10x, falling with the rounding to 100x (20x now 0.57), conflicting there. Q5 the same
  as FCS (FP's tracer check has the same gap, flagged there).
- MIN_INCUBATION_MIN 15 (EQUILIBRATION_REFERENCE_NM 2 added): Q1 a pre-equilibrium read, whose apparent KD is too weak (worst for tight binders). Q2 the 15 minutes
  rested on a typical off rate (0.003 to 0.005 per s), i.e. on one affinity: the general rule is five half-lives of the approach, 5 ln2 / (kon (C + KD))
  (Jarmoskaite et al. 2020), so it scales with 1 / KD. Q3 relative to the paper's own constant (constant_nM, in the grader facts); a koff or a time course would be
  exact: GRADER GAP (not recorded; the equilibrium criterion's reads also do not list the constant, so its quote support is not counted). Q4 MISTAKE: the absolute
  15 minutes made binding_regime conflicting for a 10-minute incubation of a micromolar binder (at equilibrium in seconds) and passed a 20-minute incubation of a
  10 pM binder (hours needed). CHANGED: conflicting below 15 min x 2 nM / constant (15 minutes is five half-lives at 2 nM with kon 10^6 per M per s, the fast
  end of typical protein association, Schreiber, Haran and Zhou 2009, Chem Rev 109:839); no constant: unknown. CHANGED 2026-11-21 (owner to confirm): the cliff
  (conflicting below, unknown above) became a curve. T_FAST is that time (kon 1e6, kept); T_SLOW is the same formula at KON_SLOW 1e5 (slow protein association and
  gated binding; citation from memory), ten times T_FAST; degree = log(t / T_FAST) / log(T_SLOW / T_FAST) clipped to 0..1, the share of the plausible rates (a log
  scale, rates span decades) for which the incubation covers five half-lives; t <= T_FAST stays conflicting (the zero end), t >= T_SLOW full. Worked numbers: a 20 nM
  KD (T_FAST 1.5 min, T_SLOW 15 min): 10 min 0.82, 4.7 min 0.5, 1.5 min conflicting, 15 min and longer full; a weak 5 uM binder (T_FAST 0.006 min = 0.36 s): 1 min full;
  a tight 10 pM binder (T_FAST 3000 min, T_SLOW 30000 min): 20 min or 24 h conflicting, 100 h (6000 min) 0.30, 500 h full. FRET has no separate floor (mixing and plate
  settling are not a constant of this converter; MIN_INCUBATION_MIN is the scale's reference, not a floor), so no d_floor is added (a new number without a researched
  value); the degree is d_kon alone, conflicting only at d_kon <= 0. A koff route is unchanged. Q5 the same scale as AlphaScreen
  (30 min x 1 nM / constant, identical); FCS uses the fastest plausible kon with a 5-minute floor (owner to unify).
- MIN_REPLICATES 3: Q1 a KD from one dilution series whose between-titration scatter (pipetting, plate position, day) is unknown. Q2 general (Vaux, Fidler and
  Cumming 2012, EMBO Rep 13:291: independent repeats, not wells). Q3 absolute (a count). Q4 sqrt(n / 3) is the standard error of the mean, the same sd^2 / n used
  for the variance; two titrations keep 0.82. KEPT. Q5 the cross-assay replicate rule.
- AGREEMENT_FACTOR 3 / AGREEMENT_ZERO_FACTOR 10: Q1 a titration KD and a competition Ki that describe different events (the label altering the binding, a wrong
  tracer KD in the Cheng-Prusoff correction). Q2 general (Cheng and Prusoff 1973, Biochem Pharmacol 22:3099: a Ki carries the tracer KD's error, so two- to
  threefold is the usual agreement of orthogonal estimates). Q3 already relative (one of the paper's constants over the other). Q4 binding constants are
  log-normal and the strength anchors are on the log scale, so equal folds must cost equal credit; linear in the fold was too lenient between the ends (6.5-fold
  got 0.5, now 0.36). CHANGED: linear -> log of the fold. Q5 as AlphaScreen.
GRADER GAPS of that review, decided 2026-11-21 (grader, record form, extraction and passages changed for 1 to 4; each new fact is optional, and an unstated one leaves
the earlier judgement unchanged):
1. Scatter of the ratio: ADDED the Z' factor (z_prime; Zhang, Chung and Oldenburg 1999: Z' >= 0.5 an excellent assay, 0 to 0.5 marginal, <= 0 no separation band). Z'
   is the number HTS TR-FRET papers state for the window and it holds the ratio's scatter at both ends. Gradual, in addition to the fold, never instead.
2. Donor lifetime: ADDED the lanthanide (donor_lanthanide: terbium, europium, other), which papers state far more often than a lifetime. The researched lifetimes
   (DONOR_LIFETIME_US) are converter constants, so the experts can correct them. The photons collected go as window / lifetime, so the window is judged at
   window x REFERENCE_LIFETIME_US / lifetime.
3. Which titration a series belongs to: ADDED series_format (direct_titration or competition), used first for the curve's midpoint.
4. Equilibrium time course: ADDED the stated dissociation rate constant (koff). The quote support of the equilibrium criterion now counts koff and the four constants
   (its reads list them). A stable-signal time course is already the equilibrium_reached fact.
5. Ratio SD for the tight-binding branch: NOT added. The branch assumes a fold of MIN_WINDOW_FOLD with 5 percent scatter (Z' = 1 - 3 (sd_high + sd_low) / window gives
   Z' about 0.55 for that); a stated Z' already enters through assay_window, and feeding it into this curve too would count the same scatter twice. The raw SD of
   the ratio is rarely stated.
Quote support (literature_quote_support.py, SUPPORT_DEGREE direct 1.0 / implied 0.7 / about_something_else 0.3): when any stated field a member criterion reads has
support 'implied' or 'about_something_else', a supported sheet criterion gets the weakest support degree as its degree (the product with its degree where it had one);
support never changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no FRET counterpart (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_criteria import NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_fret_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('spectral_crosstalk', 'specificity_control', 'compound_interference'), 'binding_regime': ('labelled_concentration', 'concentration_series', 'equilibrium', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model', 'labelling_scheme', 'ratiometric_readout'), 'calibration_applicability': ('assay_window', 'time_gating'), 'sampling_basis': ('replicates',)}
MIN_WINDOW_FOLD = 2.0  # EXPERT_REVIEW: smallest signal-over-background of the emission ratio (highest over lowest) that gives a usable curve: with 5 percent variation on both ends a fold of 2 still gives a Z' factor of about 0.5, the usual limit for a robust plate assay; the full-agreement limit.
Z_PRIME_MIN = 0.5  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): Z' factor at or above which an assay window is excellent (Zhang, Chung and Oldenburg 1999, J Biomol Screen 4:67); the full-agreement limit of a stated Z'. Z' holds the ratio's scatter at both ends, which the fold alone does not.
Z_PRIME_ZERO = 0.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): Z' at or below which the separation bands of the free and bound plateaus touch or overlap (Zhang et al. 1999: no usable window), conflicting. Between, the degree is linear in Z', the scale on which assay windows are reported and compared.
WINDOW_ZERO_AGREEMENT_FOLD = 1.0  # EXPERT_REVIEW: fold at or below which the sheet takes the titration as unresolved (conflicting): a highest ratio no larger than the lowest is no window at all.
MIN_DELAY_US = 50.0  # EXPERT_REVIEW: shortest delay (microseconds) between flash and read that lets prompt background (plate, compound and acceptor direct fluorescence, nanoseconds to a few microseconds) decay; instrument defaults for lanthanide assays are 50 to 150 microseconds; the full-agreement limit.
DELAY_ZERO_AGREEMENT_US = 5.0  # EXPERT_REVIEW: delay (microseconds) at or below which the read is not gated in effect (the prompt background lasts up to a few microseconds), conflicting.
MIN_INTEGRATION_US = 100.0  # EXPERT_REVIEW: shortest integration window (microseconds): the lanthanide emission lasts hundreds of microseconds to milliseconds, and a window much shorter than the common 200 to 400 microseconds collects too little signal; the full-credit end of the integration curve.
DONOR_LIFETIME_US = {'terbium': 2000.0, 'europium': 600.0}  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): luminescence lifetime (microseconds) of the lanthanide donor of a TR-FRET pair: terbium chelates and cryptates 1.5 to 2.8 ms, europium cryptates and chelates 0.3 to 0.7 ms (Selvin 2002, Annu Rev Biophys Biomol Struct 31:275; Degorce et al. 2009, Curr Chem Genomics 3:22). A lanthanide named 'other' or not named has no entry: the window is then judged on the reference lifetime, as before.
REFERENCE_LIFETIME_US = 1000.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): the lifetime for which MIN_INTEGRATION_US was chosen (hundreds of microseconds to milliseconds, between europium and terbium). The photons collected in a window short against the lifetime go as window / lifetime, so a window w with a donor of lifetime tau is judged as w x REFERENCE_LIFETIME_US / tau (terbium needs about twice the window, europium about 0.6 of it).
INTEGRATION_NOISE_EXPONENT = 0.5  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): for a window much shorter than the donor's lifetime the photons collected grow with the window, and the counting noise of the ratio falls as their square root, so a window w below MIN_INTEGRATION_US gives a ratio (w / MIN_INTEGRATION_US) ** 0.5 as precise as the full-credit one. A short window costs precision, never meaning: never conflicting (replaces INTEGRATION_ZERO_AGREEMENT_US 10, a conflict end).
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable FRET titration (general titration practice 8 to 12 points, Jarmoskaite et al. 2020, eLife 9:e57264; plate titrations are usually 10 to 16 point dilution series); the full-credit end of the count curve (softened from a pass/fail count, OWNER RULE).
SERIES_FIT_PARAMETERS = 3  # EXPERT_REVIEW: free parameters of the ratiometric 1:1 FRET titration fit (emission ratio of the free labelled partner, ratio of the complex, and the constant; also three for a quadratic fit at a known labelled concentration and for a competition fit at a known tracer KD); a series of this many points or fewer is fitted exactly, with no residual left to test the curve: the zero-credit end of the count curve (degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against).
HILL_FIT_PARAMETERS = 4  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): a Hill fit frees the Hill coefficient as well, so it consumes four points: the zero-credit end of the count curve for fit_model 'hill'.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest titrant concentration must be at most this multiple of the curve's midpoint (the baseline of the curve must be defined; one-site occupancy there 17 percent; 0.1x general practice with a factor 2 slack, Hulme and Trevethick 2010, Br J Pharmacol 161:1219); the full-agreement limit.
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the midpoint at or above which the lowest concentration leaves the curve with no baseline at all (half the sites are already bound), conflicting. In between the degree is linear in the one-site occupancy x / (1 + x) at the lowest concentration.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest titrant concentration must be at least this multiple of the curve's midpoint, because the bound plateau is only known by reaching it (about 90 percent saturation); the full-agreement limit.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the midpoint at or below which the highest concentration reaches no more than half saturation, so the plateau is not seen at all, conflicting. In between the degree is linear in the one-site occupancy x / (1 + x) at the highest concentration (most of the plateau is seen by 2x to 5x).
LABELLED_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the limiting labelled partner may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by depletion of the titrant, by about labelled / 2; Jarmoskaite et al. 2020); the full-agreement limit.
LABELLED_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW: labelled partner over KD at or above which the apparent KD is dominated by the labelled concentration (an order of magnitude of depletion), conflicting unless tight binding is handled.
TIGHT_BINDING_FULL_OVER_KD = 10.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): with a tight-binding analysis the depletion bias is removed, and the curve keeps a rounding at equivalence of 1 / sqrt(labelled / KD) of the full signal; up to ten times the KD that rounding (0.32) is three or more times the noise of a fraction bound read from an emission ratio, so the KD is well defined: full credit.
TIGHT_BINDING_ZERO_OVER_KD = 100.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): at a hundred times the KD the rounding 1 / sqrt(100) = 0.1 is the noise of a fraction bound read from a ratio of fold MIN_WINDOW_FOLD with 5 percent scatter (0.075 / 1), so even a quadratic fit gives only an upper bound of the KD (titration regime, Jarmoskaite et al. 2020): conflicting. Between, the degree is the rounding above this noise, relative to its value at TIGHT_BINDING_FULL_OVER_KD.
MIN_INCUBATION_MIN = 15.0  # EXPERT_REVIEW: five half-lives of a typical off rate of 0.003 to 0.005 per second are 12 to 15 minutes; this is the time five half-lives of the approach to equilibrium take at EQUILIBRATION_REFERENCE_NM, so it is the reference point of a scale that follows the paper's own constant: the time needed is MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM. Conflicting at or below it (the zero end, T_FAST), then a degree that is the log share of rates up to KON_SLOW; no constant: unknown.
APPROACH_FULL_HALF_LIVES = 5.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): with the paper's own koff, the incubation in half-lives of the dissociation (t1/2 = ln 2 / koff) that gives a full-credit equilibrium: five half-lives reach 97 percent of the approach (Jarmoskaite et al. 2020, eLife 9:e57264). The observed approach rate is koff + kon x C, never slower than koff, so this is a conservative end.
APPROACH_ZERO_HALF_LIVES = 1.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): one half-life reaches only half of the approach, so the apparent KD is still far from its equilibrium value (50 percent of the complex has not formed): conflicting at or below it. Between, the degree is linear in the fraction of the approach reached.
EQUILIBRATION_REFERENCE_NM = 2.0  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): the constant at which MIN_INCUBATION_MIN is five half-lives of the approach with the titrant at the constant, 5 ln2 / (2 kon KD) = 866 s, about 15 minutes, with kon = 10^6 per M per s, the fast end of typical protein association (Schreiber, Haran and Zhou 2009, Chem Rev 109:839); the same scale as AlphaScreen (30 min at 1 nM). A faster-associating pair needs less; this is a conflict limit, so it should not be set slower.
KON_FAST_PER_M_S = 1.0e6  # EXPERT_REVIEW (names the rate already behind EQUILIBRATION_REFERENCE_NM, unchanged): the fastest plausible association rate constant of a FRET pair (Schreiber, Haran and Zhou 2009, Chem Rev 109:839, from memory); T_FAST = MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM is five half-lives at this rate, the zero end of the incubation curve.
KON_SLOW_PER_M_S = 1.0e5  # EXPERT_REVIEW (added 2026-11-21, owner to confirm): slow association rate constant for FRET partners (proteins, peptides, nucleic acids, small ligands on a labelled protein): protein association without electrostatic steering is about 1e5 to 1e6 per M per s, and a conformational change that gates binding lowers it (Schreiber, Haran and Zhou 2009, Chem Rev 109:839, from memory; small molecules are usually faster, so 1e5 is the slow end for the class). The time at this rate is T_SLOW = T_FAST x KON_FAST / KON_SLOW (ten times T_FAST), the full-credit end.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series; Vaux, Fidler and Cumming 2012, EMBO Rep 13:291); the full-credit end of the replicate curve (softened from a pass/fail count, OWNER RULE).
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a direct-titration KD and a competition Ki (a Ki depends on the labelled partner's own KD and its uncertainty through the Cheng-Prusoff correction, so the standard is looser than for two direct estimates); the full-agreement limit.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap at or above which a direct KD and a competition Ki are different quantities (an order of magnitude), conflicting. In between the degree falls with the log of the fold (binding constants are log-normal).
NULL_REASONS = {'recovery': 'fret_has_no_matrix_recovery_measurement', 'attributed_signal': 'fret_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'fret_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_fret_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_fret_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _occupancy(over_midpoint):
    """The one-site occupancy at a concentration given as a multiple of the curve's midpoint: x / (1 + x) (the fraction of the binding curve reached there)."""
    return over_midpoint / (1.0 + over_midpoint)


def _judge_window(native):
    # Linear in the fold: the error of a fraction bound is the ratio's scatter over (fold - 1), so the precision of the curve is linear in fold - 1.
    # A Z' stated by the paper holds the ratio's own scatter and is judged in addition to the fold: linear in Z' between Z_PRIME_ZERO and Z_PRIME_MIN.
    refs = native['window_refs']
    verdicts = []
    if native['ratio_fold'] is not None:
        verdicts.append(_scaled(native['ratio_fold'], MIN_WINDOW_FOLD, WINDOW_ZERO_AGREEMENT_FOLD, refs))
    if native['z_prime'] is not None:
        verdicts.append(_scaled(native['z_prime'], Z_PRIME_MIN, Z_PRIME_ZERO, refs))
    if any(v['status'] == 'conflicting' for v in verdicts):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(v['degree'] for v in verdicts))


def _judge_gating(native):
    # The delay: linear (the prompt background decays exponentially, so the decades rejected grow linearly with the delay); conflicting at the zero end, where
    # the read is ungated in effect. The integration window: the counting precision of the ratio, sqrt(window / MIN_INTEGRATION_US), never conflicting.
    refs = native['gating_refs']
    delay = _agreement(native['delay_us'], MIN_DELAY_US, DELAY_ZERO_AGREEMENT_US)
    if delay is None:
        return _verdict('conflicting', refs)
    degrees = [delay]
    if native['integration_us'] is not None:
        window = native['integration_us'] * REFERENCE_LIFETIME_US / DONOR_LIFETIME_US.get(native['donor_lanthanide'], REFERENCE_LIFETIME_US)      # the window in units of the reference donor lifetime
        degrees.append(min(1.0, max(window, 0.0) / MIN_INTEGRATION_US) ** INTEGRATION_NOISE_EXPONENT)
    return _verdict('supported', refs, min(degrees))


def _judge_labelled(native):
    # Without a tight-binding analysis the depletion bias grows linearly with the ratio: linear. With one the bias is removed, but the KD's information is the
    # curve's rounding at equivalence, 1 / sqrt(ratio) of the full signal: full credit to TIGHT_BINDING_FULL_OVER_KD, then that rounding above its value at
    # TIGHT_BINDING_ZERO_OVER_KD (the noise of a fraction bound), conflicting there (only an upper bound of the KD is left).
    ratio, refs = native['labelled_over_kd'], native['labelled_refs']
    if native['tight_binding_handled']:
        if ratio <= TIGHT_BINDING_FULL_OVER_KD:
            return _verdict('supported', refs)
        return _scaled(ratio ** -0.5, TIGHT_BINDING_FULL_OVER_KD ** -0.5, TIGHT_BINDING_ZERO_OVER_KD ** -0.5, refs)
    # Without a tight-binding analysis: linear in the LOG of the depletion bias of the KD, b(r) = 1 + r / 2 (the apparent KD is about KD + labelled / 2), between the
    # bias at LABELLED_MAX_OVER_KD (full) and at LABELLED_ZERO_AGREEMENT_OVER_KD (conflicting): KD errors are folds, judged on the log scale (as TRP, FP, MST, split reporter).
    return _scaled(math.log(_depletion_bias(ratio)), math.log(_depletion_bias(LABELLED_MAX_OVER_KD)), math.log(_depletion_bias(LABELLED_ZERO_AGREEMENT_OVER_KD)), refs)


def _depletion_bias(labelled_over_kd):
    """The fold by which depletion of the titrant raises the apparent KD: 1 + labelled / (2 KD)."""
    return 1.0 + labelled_over_kd / 2.0


def _series_midpoint(native):
    """The name of the constant the series' ends are judged against: the curve's own midpoint. A competitor's curve turns at its IC50, not at its Ki (nor at the
    tracer's KD), so a competitor series takes the IC50 when stated, else the Ki; a direct series takes the KD, else the EC50. Which titration the series belongs to is
    the stated series_format; when it is not stated, a competition format or a Ki as the grader's constant means a competitor series; otherwise the grader's constant."""
    titration = native['series_format'] or ('competition' if native['assay_format'] == 'competition' or native['constant_name'] == 'ki' else None)
    for name in {'competition': ('ic50', 'ki'), 'direct_titration': ('kd', 'ec50')}.get(titration, ()):
        if native[name + '_nM'] is not None:
            return name
    return native['constant_name']


def _judge_series(native):
    # The count: linear in the residual degrees of freedom of the fit, count - the parameters it consumes (HILL_FIT_PARAMETERS for a Hill fit, else
    # SERIES_FIT_PARAMETERS), full at MIN_CONCENTRATIONS: the width of the KD's confidence interval, t(n - p) / sqrt(n), falls nearly linearly in n - p over
    # this range. A series fitted exactly gets zero credit, never a conflict. The two ends: linear in the one-site occupancy reached there (what the lowest
    # point shows of the baseline, the highest of the plateau), against the curve's own midpoint; conflicting at or past their zero ends.
    midpoint = _series_midpoint(native)
    rescale = native['constant_nM'] / native[midpoint + '_nM']
    if midpoint == native['constant_name']:
        refs = native['series_refs']
    else:
        refs = list(dict.fromkeys([*native['concentration_series']['source_refs'], *native['quantities'][midpoint]['source_refs']]))
    parameters = HILL_FIT_PARAMETERS if native['fit_model'] == 'hill' else SERIES_FIT_PARAMETERS
    count = _agreement(native['concentration_count'], MIN_CONCENTRATIONS, parameters) or 0.0
    low = _agreement(_occupancy(native['concentration_low_over_constant'] * rescale), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_AGREEMENT_FACTOR))
    high = _agreement(_occupancy(native['concentration_high_over_constant'] * rescale), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_AGREEMENT_FACTOR))
    if low is None or high is None:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(count, low, high))


def _judge_incubation(native):
    # A gradual degree against the paper's own kinetics. With a stated koff: the fraction of the approach to equilibrium reached. Without it: the time the binding
    # needs at the paper's own constant, MIN_INCUBATION_MIN x EQUILIBRATION_REFERENCE_NM / constant_nM at the fastest plausible association (the approach rate
    # kon (C + KD) is proportional to the constant at C = KD), is the zero end, and the same time at the slow association is the full end (see below).
    # With no constant there is no scale, and the time alone is not the paper showing against equilibrium: unknown.
    koff = native['koff_per_s']
    if koff is not None:      # the paper's own dissociation rate: the fraction of the approach to equilibrium that the incubation reaches, with a degree
        reached = 1 - 2 ** (-native['incubation_min'] * 60 * koff / math.log(2))
        return _scaled(reached, 1 - 2 ** -APPROACH_FULL_HALF_LIVES, 1 - 2 ** -APPROACH_ZERO_HALF_LIVES, native['incubation_refs'])
    constant = native['constant_nM']
    if constant is None or constant <= 0:
        return _verdict('unknown', [])      # no scale: a time alone is not the paper against equilibrium
    refs = list(dict.fromkeys([*native['incubation_refs'], *native['quantities'][native['constant_name']]['source_refs']]))
    fastest = MIN_INCUBATION_MIN * EQUILIBRATION_REFERENCE_NM / constant      # five half-lives at the fastest plausible kon
    # Association rates span decades: the degree is the share of them (on the log scale, from KON_FAST to KON_SLOW) for which the incubation covers the five half-lives.
    # At or below the fastest-kon time the degree is 0: conflicting (even the fastest association has not equilibrated). No floor here: MIN_INCUBATION_MIN is the scale's reference, not a mixing time.
    return _scaled(math.log(native['incubation_min'] / fastest), math.log(KON_FAST_PER_M_S / KON_SLOW_PER_M_S), 0.0, refs)


def _judge_replicates(native):
    refs = native['replicate_refs']
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', refs)      # the independence is not stated: the count alone gives nothing to judge
    count = native['replicate_count']
    if count >= MIN_REPLICATES:
        return _verdict('supported', refs)
    # Softened (OWNER RULE): below MIN_REPLICATES the credit is the precision of the mean KD over n independent dilution series relative to the researched n,
    # sqrt(n / MIN_REPLICATES). Why this shape for FRET: the replicate titrations are separate dilution series read on the plate reader, and their scatter
    # (pipetting of the series, plate position) averages down as 1 / sqrt(n), the same sd^2 / n this converter uses for the variance. Never conflicting for a stated count.
    return _verdict('supported', refs, math.sqrt(max(count, 0) / MIN_REPLICATES))


def _judge_estimates(native):
    # On the log of the fold: binding constants are log-normal (the strength anchors are on the log scale too), so equal folds cost equal credit.
    return _scaled(math.log(native['estimate_fold']), math.log(AGREEMENT_FACTOR), math.log(AGREEMENT_ZERO_FACTOR), native['estimate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('assay_window', 'window_recorded_for_the_sheet'): _judge_window, ('time_gating', 'gating_recorded_for_the_sheet'): _judge_gating,
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


def convert_fret(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        half_maximal = [name for name in ('ec50', 'ic50') if native[name + '_nM'] is not None]
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if half_maximal else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'fret_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'fret_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
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
    return {'version': VERSION, 'experiment_type': 'fret', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
