"""Trp converter: turns the Trp grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_trp.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET and MST converters fill), the
dependence keys the merger needs, and for every sheet component that an intrinsic
fluorescence titration cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported KD in nM (point operand; the measurement key is
                  trp_kd). No KD leaves effect null. A Stern-Volmer constant Ksv
                  alone is a quenching efficiency, not a dissociation constant,
                  and is not carried into the effect; a KD whose curve was fitted
                  with the Stern-Volmer equation is not carried either (the fit
                  gives Ksv, so the number is not a KD).
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread) allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n, and only when the replicates
                  criterion is supported (n independent titrations);
                  confidence_interval -> not converted (needs its level and
                  degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the ligand (the titrant),
immobilized_preparation_ref = the protein held at a constant concentration,
surface_ref = None (a titration in solution has no surface), dataset_ref = the dataset.

Criteria mapping (Trp criteria -> sheet criteria), declared in CRITERIA_MAP
----------------------------------------------------------------------------
binding_controls              inner_filter + dilution + buffer_blank + ligand_fluorescence +
                              specificity_control + photobleaching + quenching_mechanism
binding_regime                saturation + concentration_series + protein_concentration + equilibrium
binding_parameter_definition  fit_model + excitation_selectivity
calibration_applicability     signal_amplitude (the size of the fluorescence change: this
                              method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Every researched value is the
end of a gradual curve, never a pass/fail step. Continuous comparisons give a degree: supported with degree 1.0 at or
better than the full-agreement limit, falling to 0 at the zero-agreement limit, conflicting at or beyond it. Each curve is drawn on the scale on which
its error acts (see the range review below):
  signal_amplitude       linear in percent, MIN_FLUORESCENCE_CHANGE_PERCENT / FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT;
  inner_filter           (no correction stated, an absorbance given) the weaker of: linear in the absorbance, MAX_UNCORRECTED_ABSORBANCE /
                         ABSORBANCE_ZERO_AGREEMENT; and, for a stated quenching of stated size, linear in the uncorrected inner-filter loss over the
                         paper's own fluorescence change, ARTEFACT_FULL_OVER_CHANGE / ARTEFACT_ZERO_OVER_CHANGE (conflicting when the loss alone is as
                         large as the whole change: a non-binder would show it too);
  dilution               (no correction stated, an added volume given) the same two: linear in the added volume, MAX_UNCORRECTED_DILUTION_PERCENT /
                         DILUTION_ZERO_AGREEMENT_PERCENT; and the dilution loss over the paper's own quenching, on the same artefact ends;
  protein_concentration  linear in the log of the apparent KD's depletion bias, 1 + HALF_BOUND_AT_MIDPOINT x protein / KD, between PROTEIN_MAX_OVER_KD
                         and PROTEIN_ZERO_AGREEMENT_OVER_KD, unless tight binding is handled (then supported, no degree);
  concentration_series   the weakest of three: the highest (and, when it differs, the lowest) concentration over the curve's midpoint (the KD, or
                         KD + HALF_BOUND_AT_MIDPOINT x protein with tight binding handled), each linear in the fractional occupancy x / (1 + x)
                         (HIGH_FACTOR / HIGH_ZERO_AGREEMENT_FACTOR, LOW_FACTOR / LOW_ZERO_AGREEMENT_FACTOR); and the count linear in the residual degrees of
                         freedom between MIN_CONCENTRATIONS and FIT_PARAMETERS (HILL_FIT_PARAMETERS for a Hill fit), which only lowers the degree (no
                         credit at the parameters or fewer, never conflicting: a short series is weaker evidence, not evidence against); a count
                         without a span is unknown;
  excitation_selectivity 1.0 at or above TRP_SELECTIVE_EXCITATION_MIN_NM, linear down to TRP_EXCITATION_SHARE_AT_280 (the share of the excitation
                         tryptophan takes at 280 nm in an average protein) at TYROSINE_EXCITATION_NM, and that share at or below it (the tyrosine also
                         excited lowers the attribution, it is not a conflict).
Replicates (independence yes): supported with degree min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean KD over n independent titrations;
independence not stated: unknown; stated no: the grader's conflicting. Equilibrium from an incubation time t (equilibrium fact not stated), with the paper's
own KD: T_FAST = EQUILIBRATION_HALF_LIVES off-rate half-lives at koff = FAST_KON_PER_M_PER_S x KD, T_SLOW the same at SLOW_KON_PER_M_PER_S; conflicting
when t <= T_FAST (even the fastest plausible association has not equilibrated); otherwise supported with degree min(d_floor, d_kon), d_kon =
log(t / T_FAST) / log(T_SLOW / T_FAST) clipped to 0..1 (the share, on the log scale, of the plausible association rates for which the incubation covers
the five half-lives), d_floor = min(1, t / MIN_INCUBATION_MIN) (the cuvette's mixing, proportional, never conflicting by itself); refs the incubation and the
KD. No KD as a binding constant: unknown (there is no scale; a time alone is not the paper against equilibrium), also within the mixing. A degree describes the stated value only; no unknown weight enters it (owner rule). A sheet criterion that is supported carries the smallest
degree of its members that have one.
Quote support (literature_quote_support.py, SUPPORT_DEGREE direct 1.0 / implied 0.7 / about_something_else 0.3): when any stated field a member criterion reads has
support 'implied' or 'about_something_else', a supported sheet criterion gets the weakest support degree as its degree (the product with its degree where it had one);
support never changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Range review (A105_EXPERIMENT_SOP step 3; 2026-11-21). Q1 what it protects against; Q2 general practice or lab-specific; Q3 absolute or relative
scale, and whether the grader has the fact; Q4 how badly a wrong value misleads and whether the shape fits; Q5 consistency with the other binding
assays. References (from memory, not checked on the web): Lakowicz, Principles of Fluorescence Spectroscopy, 3rd ed. 2006 (ch. 2 inner filter,
ch. 8 quenching, ch. 16 protein fluorescence); Eftink 1991 Methods Biochem Anal 35:127; van de Weert & Stella 2011 J Mol Struct 998:144; Kubista et
al. 1994 Analyst 119:417; Pace et al. 1995 Protein Sci 4:2411; Jarmoskaite et al. 2020 eLife 9:e57264; Pang & Zhou 2017 Annu Rev Biophys 46:105.
  signal_amplitude (5 / 1 percent). Q1 a KD fitted to a change no larger than the reading scatter, drift and photobleaching (a noise-made binder).
    Q2 lab/instrument level: a cuvette fluorimeter reads to about 1 percent; Trp binding changes are usually 10 to 60 percent (Lakowicz ch. 16).
    Q3 the right scale is the change over the paper's own scatter (a signal-to-noise, as MST); the grader collects no scatter (grader gap), so the
    absolute percent is the proxy. Q4 a quiet instrument (photon counting, averaged) makes a 3 percent change usable yet scored 0.5; a noisy plate
    read makes 5 percent noise yet scored 1.0: moderate. The KD's error goes as noise / change, and linear credit from 1 to 5 percent stays close to
    that. KEPT. Q5 the same ramp as the MST Fnorm change (5 / 1 per mille) and the FP / FRET windows.
  excitation_selectivity (295 / 280 nm, floor 0.58). Q1 a change read at 280 nm is partly tyrosine's, so it is not solely the tryptophan reporter the
    method relies on (the KD itself is usually still a KD). Q2 general: 295 nm for selective tryptophan excitation is textbook (Lakowicz ch. 16;
    Eftink 1991); the 0.58 floor is physics (Pace et al. 1995 absorption, average residue frequencies). Q3 absolute is right: the absorption spectra
    of Trp and Tyr belong to the residues, not the sample. Q4 mild: it only lowers one member of binding_parameter_definition, never below 0.58;
    tyrosine's share falls roughly linearly from 280 to 295 nm (Trp share about 0.72 at 285, 0.9 at 290), which the linear ramp follows. KEPT.
    Q5 no counterpart elsewhere; no unknown weight inside (fixed earlier).
  inner_filter (0.05 / 0.3 AU; NEW relative check 0.2 / 1 of the change). Q1 an absorbing ligand lowers the light with no binding at all: an
    uncorrected inner filter alone makes a saturating-looking quench from a non-binder, the main direction risk of this assay (van de Weert & Stella
    2011). Q2 general: correct above an absorbance of about 0.05 to 0.1 (Lakowicz ch. 2; Kubista et al. 1994). Q3 the harm is the artefact against
    the paper's own change: the loss 1 - 10^(-A / 2) (A at one wavelength; the correction factor is 10^((A_ex + A_em) / 2)) over the stated
    fluorescence change, which the grader has. Q4 the absolute ramp alone gave A 0.1 uncorrected beside a 10 percent quench 0.8, although the
    inner filter alone (a loss of at least 10.9 percent) accounts for the whole quench: a non-binder scored as a binder. CHANGED: in addition (SOP
    rule 6), for a stated quenching of stated size, the loss over the change, full at ARTEFACT_FULL_OVER_CHANGE, conflicting at 1 (A 0.1 with a 15
    percent quench: 0.8 -> 0.34; with 10 percent: 0.8 -> conflicting). An enhancement cannot be made by a loss, so it gets the absolute ramp only;
    an unstated direction is not assumed. Also corrected: the zero end's comment said 10^0.3 halves the light; with A at one wavelength the loss
    is 29 percent (half only when both wavelengths absorb 0.3). Value kept. Q5 FP's intensity-change ramp is the nearest (a relative artefact).
  dilution (5 / 50 percent added; NEW relative check). Q1 the added ligand dilutes the protein, lowering the fluorescence by v / (100 + v), a
    drift that imitates a quench. Q2 general: correct for dilution or keep the added volume to a few percent (Lakowicz; van de Weert & Stella 2011).
    Q3 as the inner filter: the loss over the paper's own quenching. Q4 10 percent added uncorrected beside an 8 percent quench scored 0.89 though
    the dilution (9.1 percent) is the whole quench. CHANGED: the same relative check in addition, same ends; values kept. Q5 as inner_filter.
  protein_concentration (1 / 10 x KD). Q1 ligand depletion: Trp titrations use the protein at micromolar to see its weak signal, and the fitted
    hyperbola then gives about KD + protein / 2. Q2 general: the fixed partner at or below KD (Jarmoskaite et al. 2020). Q3 already relative to the
    paper's KD. Q4 the error is a (1 + r / 2)-fold magnitude error read on a log scale (1.5-fold at the full end, 6-fold at the zero end); linear in r
    gave the first doubling almost no penalty. CHANGED: linear in log(1 + r / 2), values kept (r 2: 0.89 -> 0.79; the real TRKB case r 3.125: 0.76 ->
    0.61; r 5.5: 0.50 -> 0.34). Q5 as FP and MST (log depletion). With tight binding handled it stays supported with no degree, as FP and MST; FRET
    also grades the rounding of a quadratic curve at a very high ratio (only an upper bound of the KD is left): not modelled here, flagged.
  concentration_series span (0.2 / 1 and 10 / 1 x the midpoint). Q1 a free-protein baseline or a saturation plateau that is extrapolated, not
    measured. Q2 general: about 0.1 to 10 x KD (Jarmoskaite et al. 2020); 0.2 and 10 are lenient. Q3 relative to the curve's midpoint: the KD for a
    hyperbola fit (already the apparent midpoint), KD + protein / 2 with tight binding handled (protein and tight_binding_handled: in the grader).
    Q4 what the ends define is the occupancy x / (1 + x): linear in x gave a top at 3 x KD (75 percent bound) 0.22 and a bottom at 0.6 x 0.5.
    CHANGED: occupancy shape and midpoint scale, values kept (top 5.5 x: 0.50 -> 0.85; top 3 x: 0.22 -> 0.61; bottom 0.6 x: 0.50 -> 0.38); the lowest
    is judged only when it differs from the highest (one concentration is a short series, not a misplaced one). Q5 as SPR, MST and FRET.
  concentration_series count (8 / 2; Hill 3). Q1 too few additions to test that the change saturates. Q2 general titration practice 8 to 12
    points (Jarmoskaite et al. 2020); 2 is the 1:1 fit's free parameters on the normalised change (KD and the change at saturation; the free-protein
    reading is measured). Q3 absolute: the parameters are fixed by the model. Q4 each point beyond the parameters is one residual degree of freedom,
    so linear is right. KEPT; CHANGED only for a Hill fit, which frees the Hill coefficient too (HILL_FIT_PARAMETERS, as FRET). Q5 the shared rule.
  equilibrium CHANGED 2026-11-21 (owner to confirm; the cliff became a curve): conflicting at t <= T_FAST, then degree min(d_floor, d_kon), see above.
    NEW SLOW_KON_PER_M_PER_S = 1e5. Q1 as below. Q2 general: association rates span decades (about 1e5 to 1e7 for small ligands and proteins, Pang &
    Zhou 2017, cited from memory), so T_FAST (1e8) and T_SLOW (1e5) bracket the plausible ones and the degree is the log-scale share of them
    covered; 1e5 is the low end of the usual range, not a gated rate (a conformational change gating binding can be slower still: Schreiber, Haran
    & Zhou 2009 Chem Rev 109:839, from memory). Q3 relative to the paper's own KD, which the grader hands over (kd_nM, with its refs). Q4 steep in
    the log of the time (3 decades of rate map onto 0..1), so one doubling of a short read moves the degree by 0.10 and the zero end meets the
    old conflict without a step; the mixing floor is proportional (a read at half of MIN_INCUBATION_MIN gets 0.5). Worked: KD 20 uM (T_FAST 1.7 ms,
    T_SLOW 1.7 s): t 1 min -> d_kon 1, d_floor 0.5, degree 0.5; t 2 min or more -> 1. KD 1 nM (T_FAST 0.58 min, T_SLOW 577 min): t 5 min -> 0.31,
    60 min -> 0.67. KD 50 pM (T_FAST 11.55 min, T_SLOW 192 h): t 10 min conflicting, 60 min -> 0.24, 24 h -> 0.70. Q5 as FP and MST once they follow
    the same curve. Declared: INCUBATION_ZERO_AGREEMENT_MIN (1 min, the mixing minute) no longer decides anything (the floor is proportional and
    never conflicting by itself; the old conflict within it is gone); MIN_INCUBATION_MIN is now the floor of d_floor. Kept, not dropped.
  equilibrium before the change (mixing 1 min; MIN_INCUBATION_MIN 2 min; KD-relative limit). Q1 a titration read before the lowest points have bound, which
    raises the apparent KD. Q2 general: about five half-lives of the slowest approach, set by koff at the lowest concentrations (Jarmoskaite et al.
    2020). Q3 relative to the paper's KD (koff = kon x KD), which the grader has. Q4 the fixed one-minute floor let a 0.1 nM binder read after 2 min
    pass as unknown although even the fastest plausible association needs about 6 min. CHANGED: conflicting also below EQUILIBRATION_HALF_LIVES
    half-lives at koff = FAST_KON_PER_M_PER_S x KD (1e8 per M per s, the fast end for the small-molecule ligands typical here; it exceeds the mixing
    minute only below a KD of about 0.6 nM). A step, as FP's, on purpose: only the paper's own numbers trigger it at the most lenient kon, and a time
    never earns credit. Declared: MIN_INCUBATION_MIN has decided nothing since the earlier softening (both its sides were unknown); it is kept,
    marked as such, for the owner. Q5 as FP (which uses 1e7 for peptide and protein ligands).
  replicates (3, sqrt(n / 3)). Q1 one dilution series' pipetting and photobleaching taken as the KD. Q2 general (triplicate). Q3 absolute count.
    Q4 the precision of the mean. KEPT. Q5 the shared replicate rule.
Grader gaps (not changed here; a grader change needs steps 1-7 and a real-model run): the scatter of the fluorescence readings or a signal-to-
noise (to make signal_amplitude relative); the ligand absorbance at the excitation and at the emission wavelength separately (the record keeps the
larger only, so the loss is bounded from below by 1 - 10^(-A / 2)); (CLOSED, grader gap 3: the record now has concentration_lowest and
concentration_highest for a series stated as a range, the grader records the span over the KD from them when there is no list, and the series
judge above uses a stated end alone when the other is not stated; the real TRKB paragraph states 0-1000 nM, so only its highest end, 1000 nM,
is stated: a zero blank is not a lowest concentration); whether the free-protein fluorescence was fitted or fixed (FIT_PARAMETERS 2 or
3); a koff, kon or time course (to replace the assumed fast kon in the equilibration limit).
Decisions on those gaps (gap-closing pass): gap 3 DONE (above). Gaps 1, 2, 4 and 5 are NOT collected, by the owner's questions: (1) the scatter or
signal-to-noise of the readings is almost never stated in a quenching paper, so a field would be unavailable nearly always and the absolute
stand-in stays; (2) a ligand absorbance at each wavelength separately is rarely given and the larger value already gives the stated lower bound
of the loss, so the harm of using it is a mild under-penalty, not a misleading score; (4) whether the free-protein fluorescence was fitted is a
detail of the fit that papers seldom state and it moves the parameter count by one only; (5) kon, koff or a time course is not reported in
fluorescence-titration papers, and the stated fact equilibrium_reached already carries the paper's own claim.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_criteria import NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_trp_converted_v1'
CRITERIA_MAP = {'binding_controls': ('inner_filter', 'dilution', 'buffer_blank', 'ligand_fluorescence', 'specificity_control', 'photobleaching', 'quenching_mechanism'), 'binding_regime': ('saturation', 'concentration_series', 'protein_concentration', 'equilibrium'), 'binding_parameter_definition': ('fit_model', 'excitation_selectivity'), 'calibration_applicability': ('signal_amplitude',), 'sampling_basis': ('replicates',)}
MIN_FLUORESCENCE_CHANGE_PERCENT = 5.0  # EXPERT_REVIEW: smallest change of the protein's fluorescence (percent) between the free protein and the saturated complex; the reading noise of a steady-state fluorimeter, pipetting and photobleaching together are a few percent, so a smaller change cannot be told from them; the full-agreement limit.
FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT = 1.0  # EXPERT_REVIEW: change (percent) at or below which it is smaller than the reading noise of one measurement, conflicting.
TRP_SELECTIVE_EXCITATION_MIN_NM = 295.0  # EXPERT_REVIEW: smallest excitation wavelength (nm) that excites tryptophan almost alone; below it (280 nm) tyrosine is excited as well, so the change cannot be attributed to tryptophan; the full-agreement limit.
TYROSINE_EXCITATION_NM = 280.0  # EXPERT_REVIEW: the usual total-protein excitation wavelength, near the tyrosine absorption maximum (about 275 nm), where tyrosine takes a large share of the excitation; the low end of the excitation degree: at or below it the degree stays at TRP_EXCITATION_SHARE_AT_280 (tyrosine's share does not grow further towards its 275 nm maximum, where tryptophan still absorbs about as strongly), never a conflict.
TRP_EXCITATION_SHARE_AT_280 = 0.58  # EXPERT_REVIEW: the low end of the excitation degree, just above TYROSINE_EXCITATION_NM: the share of the 280 nm excitation that tryptophan takes in an average protein, from the molar absorption at 280 nm (Trp 5500, Tyr 1490 per M per cm; Pace et al. 1995, Protein Sci 4:2411) and the average residue frequencies of UniProtKB/Swiss-Prot (Trp about 1.1 percent, Tyr about 2.9 percent): 1.1 x 5500 / (1.1 x 5500 + 2.9 x 1490) = 0.58. Conservative: tyrosine emission in proteins is largely quenched or transferred to tryptophan, so the observed change is at least this much tryptophan's. Replaces WEIGHT_UNKNOWN as the low end (owner rule: no unknown weight inside a degree).
MAX_UNCORRECTED_ABSORBANCE = 0.05  # EXPERT_REVIEW: largest ligand absorbance (AU, at the excitation or emission wavelength, at the highest ligand concentration) for which no inner-filter correction is needed; the inner-filter correction factor 10^((A_ex + A_em) / 2) is about 6 percent at an absorbance of 0.05 and 12 percent at 0.1, which is as large as the smallest usable signal; the full-agreement limit.
ABSORBANCE_ZERO_AGREEMENT = 0.3  # EXPERT_REVIEW: ligand absorbance (AU) at or above which an uncorrected measurement loses 29 percent of its fluorescence when the ligand absorbs at one of the two wavelengths (10^(0.3 / 2) is about 1.41) and half when it absorbs 0.3 at both (10^0.3 is about 2; range review: the earlier comment gave only the second), larger than most Trp binding changes, so the fluorescence change is mostly the inner filter, conflicting.
ARTEFACT_FULL_OVER_CHANGE = FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT / MIN_FLUORESCENCE_CHANGE_PERCENT  # EXPERT_REVIEW: (range review 2026-11-21, owner to confirm; 0.2)an uncorrected artefact that lowers the fluorescence (the inner-filter loss, or the dilution loss) up to this fraction of the paper's own stated quenching leaves the binding change fully readable; it is FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT / MIN_FLUORESCENCE_CHANGE_PERCENT (1 / 5): the signal standard already accepts a reading noise of a fifth of the smallest fully usable change, and an artefact no larger is within it; the full-agreement limit of the relative check.
ARTEFACT_ZERO_OVER_CHANGE = 1.0  # EXPERT_REVIEW: (range review 2026-11-21)an uncorrected artefact at least as large as the paper's whole stated quenching explains all of it (a non-binding absorbing ligand, or the dilution alone, would show the same quench), conflicting; in between the degree is linear in the share of the change the artefact takes.
PERCENT = 100.0  # FIXED_BY_DEFINITION: percent per unit fraction.
MAX_UNCORRECTED_DILUTION_PERCENT = 5.0  # EXPERT_REVIEW: largest total volume added (percent of the starting volume) for which the dilution of the protein may be left uncorrected; the dilution lowers the fluorescence by the same percentage, which at 5 percent is as large as the smallest usable signal; the full-agreement limit.
DILUTION_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: added volume (percent) at or above which the protein is diluted by a third or more, an effect far larger than any usable signal, conflicting when not corrected.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest ligand concentrations for a usable titration (a fluorescence titration is a series of additions; with fewer than eight the two baselines and the transition of a saturation curve are not all defined); the full-agreement limit of the count.
FIT_PARAMETERS = 2  # EXPERT_REVIEW: free parameters of the 1:1 isotherm fitted to the fluorescence change (the KD and the change at saturation; the free-protein fluorescence is the measured start of the titration; whether a paper fitted it instead is a grader gap); with this many concentrations or fewer the curve passes through every point and nothing checks it, so the count gives no credit (degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against).
HILL_FIT_PARAMETERS = 3  # EXPERT_REVIEW: (range review 2026-11-21, owner to confirm)a Hill fit frees the Hill coefficient as well (FIT_PARAMETERS + 1), so it uses up three points: the zero-credit end of the count for fit_model 'hill' (as FRET's HILL_FIT_PARAMETERS).
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest ligand concentration must be at most this multiple of the curve's midpoint (the KD, or KD + protein / 2 with tight binding handled; see _midpoint) (the free-protein baseline of the curve must be defined; 0.1 x general practice with a factor 2 slack); the full-agreement limit.
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the midpoint at or above which the lowest concentration leaves the curve with no free-protein baseline at all (half the protein is already bound), conflicting; falls from LOW_FACTOR linearly in the fractional occupancy x / (1 + x) (1/6 at LOW_FACTOR, 1/2 here), the share of the curve left unsampled below the series (range review; was linear in x).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest ligand concentration must be at least this multiple of the midpoint, because the saturation plateau is only known by reaching it (about 90 percent saturation); the full-agreement limit.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the midpoint at or below which the highest concentration reaches no more than half saturation, so the plateau is not seen at all, conflicting; falls from HIGH_FACTOR linearly in the fractional occupancy (10/11 at HIGH_FACTOR, 1/2 here): steep near the midpoint, where each step up the series adds much of the curve, gentle near the plateau (range review; was linear in x).
PROTEIN_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the protein may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by depletion of the free ligand, to about KD + protein / 2: 1.5-fold here; Jarmoskaite et al. 2020 eLife 9:e57264); the full-agreement limit.
PROTEIN_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW: protein over KD at or above which the apparent KD is dominated by the protein concentration (an order of magnitude of depletion, a 6-fold error of the KD), conflicting unless tight binding is handled; falls from PROTEIN_MAX_OVER_KD linearly in the log of the depletion bias 1 + protein / (2 KD), the magnitude error the sheet reads on its log scale (range review; was linear in the ratio; as FP and MST).
HALF_BOUND_AT_MIDPOINT = 0.5  # FIXED_BY_DEFINITION: at the curve's midpoint half the protein is bound, so the titrant there is KD free plus protein / 2 bound.
MIN_INCUBATION_MIN = 2.0  # EXPERT_REVIEW: the absolute floor of the incubation (minutes): mixing and thermal equilibration of a cuvette alone take about a minute and a settled read about two; d_floor = min(1, t / MIN_INCUBATION_MIN), proportional and never conflicting by itself (2026-11-21, owner to confirm: it decided nothing before; it now sets the floor of the equilibrium degree).
INCUBATION_ZERO_AGREEMENT_MIN = 1.0  # EXPERT_REVIEW: the mixing and thermal equilibration of a cuvette alone (about a minute, the reason of MIN_INCUBATION_MIN). DECIDES NOTHING since 2026-11-21 (owner to confirm): the floor is proportional and never conflicting by itself, so a read within it is no longer conflicting; kept for the owner, not dropped for being a number.
EQUILIBRATION_HALF_LIVES = 5.0  # EXPERT_REVIEW: (range review 2026-11-21, as FP)half-lives of the slowest approach (koff, at the lowest ligand concentrations) after which a titration point is about 97 percent equilibrated (Jarmoskaite et al. 2020 eLife 9:e57264).
FAST_KON_PER_M_PER_S = 1.0e8  # EXPERT_REVIEW: (range review 2026-11-21, owner to confirm)the fast end of small-molecule-protein association rate constants (mostly 1e5 to 1e7, a few near 1e8 below the diffusion limit; Pang & Zhou 2017 Annu Rev Biophys 46:105); Trp titrations are mostly of small ligands, so this is a decade more lenient than FP's 1e7 for peptides and proteins. koff = kon x KD at this kon is the fastest plausible off rate, so the time it gives is the most lenient plausible equilibration time: a read before it is too early even for a fast binder. It exceeds INCUBATION_ZERO_AGREEMENT_MIN only for a KD below about 0.6 nM.
SLOW_KON_PER_M_PER_S = 1.0e5  # EXPERT_REVIEW: (2026-11-21, owner to confirm; citation from memory) the slow end of small-molecule-protein association rate constants for the ligands typical of Trp titrations (usual range 1e5 to 1e7, Pang & Zhou 2017 Annu Rev Biophys 46:105; slower still when a conformational change gates binding, Schreiber, Haran & Zhou 2009 Chem Rev 109:839). koff = kon x KD at this kon gives T_SLOW, the time at which the incubation covers the five half-lives for every plausible association rate; the degree rises on the log scale from T_FAST (1e8) to T_SLOW, three decades.
NM_PER_M = 1.0e9  # FIXED_BY_DEFINITION: nanomolar per molar.
S_PER_MIN = 60.0  # FIXED_BY_DEFINITION: seconds per minute.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series or preparations); the full-agreement limit of the count. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): the pipetting of the dilution series, photobleaching and the preparation vary between titrations, and the standard error of the mean KD over n independent titrations falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance); 1 titration about 0.58, 2 about 0.82; never conflicting for a stated count.
NULL_REASONS = {'recovery': 'a_fluorescence_titration_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'a_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_fluorescence_titration_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_fluorescence_titration_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _agreement(value, full, zero):
    """The degree of agreement of a measured value: 1.0 at or better than the full-agreement limit, falling linearly to 0 at the zero-agreement limit (either direction); None at or beyond it."""
    fraction = (value - zero) / (full - zero)
    return None if fraction <= 0 else min(1.0, fraction)


def _credit(value, full, zero):
    """The same curve where the far end is no credit rather than a conflict (a count, or a value whose short side only lowers the degree): 0 at or beyond ``zero``."""
    fraction = (value - zero) / (full - zero)
    return max(0.0, min(1.0, fraction))


def _scaled(value, full, zero, refs):
    degree = _agreement(value, full, zero)
    return _verdict('conflicting', refs) if degree is None else _verdict('supported', refs, degree)


def _judge_signal(native):
    return _scaled(native['fluorescence_change_percent'], MIN_FLUORESCENCE_CHANGE_PERCENT, FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT, native['change_refs'])


def _judge_excitation(native):
    # Shape: tyrosine's absorption band falls about linearly from near its maximum at 280 nm to almost nothing at 295 nm, while tryptophan
    # still absorbs up to about 305 nm; so the share of the excitation tyrosine takes, and the doubt that the change is tryptophan's, falls
    # about linearly between them. Exciting tyrosine too only loses part of the attribution and is never evidence against the binding, so the
    # degree falls only to the tryptophan share of the 280 nm excitation (TRP_EXCITATION_SHARE_AT_280, its own researched end; no unknown weight),
    # and stays there at or below 280 nm (a short excitation also excites tyrosine: a smaller attribution, not a conflict).
    selectivity = _credit(native['excitation_nm'], TRP_SELECTIVE_EXCITATION_MIN_NM, TYROSINE_EXCITATION_NM)
    return _verdict('supported', native['excitation_refs'], TRP_EXCITATION_SHARE_AT_280 + (1.0 - TRP_EXCITATION_SHARE_AT_280) * selectivity)


def _inner_filter_loss_percent(absorbance):
    """The fluorescence an uncorrected inner filter removes (percent) at a ligand absorbance A at one wavelength: 1 - 10^(-A / 2), from the correction
    factor 10^((A_ex + A_em) / 2) (Lakowicz ch. 2) with the other wavelength not absorbing; the smallest loss the recorded absorbance allows."""
    return PERCENT * (1.0 - 10.0 ** (-absorbance / 2.0))


def _dilution_loss_percent(added_percent):
    """The fluorescence an uncorrected dilution removes (percent) when added_percent of the starting volume has been added: v / (100 + v)."""
    return PERCENT * added_percent / (PERCENT + added_percent)


def _artefact_over_quench(loss_percent, native):
    """The share of the paper's own stated quenching an uncorrected artefact that lowers the fluorescence accounts for, with the refs of the change;
    None when the change is not stated or is not a quenching (a loss cannot make an enhancement; an unstated direction is not assumed)."""
    change = native['fluorescence_change_percent']
    if change is None or native['change_direction'] != 'quenching':
        return None, []
    return (loss_percent / change if change > 0 else math.inf), native['change_refs']


def _with_artefact(absolute, loss_percent, native, refs):
    """The absolute ramp's verdict, lowered (SOP rule 6: in addition, not instead) by the artefact over the paper's own quenching when it can be formed."""
    ratio, change_refs = _artefact_over_quench(loss_percent, native)
    if ratio is None:
        return _scaled(*absolute, refs)
    refs = list(dict.fromkeys([*refs, *change_refs]))
    degrees = [_agreement(*absolute), _agreement(ratio, ARTEFACT_FULL_OVER_CHANGE, ARTEFACT_ZERO_OVER_CHANGE)]
    return _verdict('conflicting', refs) if None in degrees else _verdict('supported', refs, min(degrees))


def _judge_absorbance(native):
    # Absolute: linear in the absorbance (the correction factor grows about linearly over 0 to 0.3). Relative (a stated quenching of stated size): linear in
    # the share of the change the smallest possible inner-filter loss takes; conflicting when it takes all of it (a non-binder would show the same quench).
    absorbance = native['ligand_absorbance']
    return _with_artefact((absorbance, MAX_UNCORRECTED_ABSORBANCE, ABSORBANCE_ZERO_AGREEMENT), _inner_filter_loss_percent(absorbance), native, native['absorbance_refs'])


def _judge_dilution(native):
    # As the inner filter: absolute in the added volume, and relative to the paper's own quenching with the dilution loss v / (100 + v).
    added = native['added_volume_percent']
    return _with_artefact((added, MAX_UNCORRECTED_DILUTION_PERCENT, DILUTION_ZERO_AGREEMENT_PERCENT), _dilution_loss_percent(added), native, native['added_volume_refs'])


def _depletion_bias(protein_over_kd):
    """The fold by which a 1:1 hyperbola fit overstates the KD when the protein is at r x KD: about (KD + protein / 2) / KD."""
    return 1.0 + HALF_BOUND_AT_MIDPOINT * protein_over_kd


def _judge_protein(native):
    if native['tight_binding_handled']:
        return _verdict('supported', native['protein_refs'])      # the quadratic or tight-binding analysis does not depend on the protein over the KD
    # Linear in the log of the apparent KD's depletion bias, the magnitude error the sheet reads on its log scale (range review; was linear in the ratio).
    return _scaled(math.log(_depletion_bias(native['protein_over_kd'])), math.log(_depletion_bias(PROTEIN_MAX_OVER_KD)), math.log(_depletion_bias(PROTEIN_ZERO_AGREEMENT_OVER_KD)), native['protein_refs'])


def _occupancy(ratio):
    """Fractional occupancy x / (1 + x) of a concentration given as x = c / midpoint: where on the 1:1 binding curve it sits."""
    return ratio / (1.0 + ratio)


def _midpoint(native):
    """The ligand concentration (nM) at the middle of the measured curve, the scale its span is judged on, and the refs it used besides the KD. With tight
    binding handled: KD + protein / 2 (half the protein bound needs KD free ligand plus protein / 2 bound); a KD fitted with the hyperbola is already
    the apparent midpoint."""
    kd = native['constant_nM']
    if native['tight_binding_handled'] and native['protein_nM'] is not None:
        return kd + HALF_BOUND_AT_MIDPOINT * native['protein_nM'], native['quantities']['protein_concentration']['source_refs']
    return kd, []


def _fit_parameters(native):
    """The free parameters of the fitted curve: the zero-credit end of the count."""
    return HILL_FIT_PARAMETERS if native['fit_model'] == 'hill' else FIT_PARAMETERS


def _judge_series(native):
    # Shape of the count: linear in the residual degrees of freedom of the fit (count - the fit's parameters). Each concentration beyond the two the
    # 1:1 isotherm needs is one more independent check that the fluorescence change follows a saturating curve (the free-protein baseline, the
    # transition and the plateau each need points of their own); the researched eight leave six, at two or fewer the curve is only drawn through the points.
    # The count only lowers the degree: none at the fit's parameters or fewer, never conflicting (a short series is weaker evidence, not evidence against).
    count = None if native['concentration_count'] is None else _credit(native['concentration_count'], MIN_CONCENTRATIONS, _fit_parameters(native))
    low_over, high_over = native['concentration_low_over_constant'], native['concentration_high_over_constant']
    if low_over is None and high_over is None:
        return _verdict('unknown', [])                               # the span can only be judged from the list (or the stated ends of a range) and the KD
    midpoint, midpoint_refs = _midpoint(native)
    refs = list(dict.fromkeys([*native['series_refs'], *midpoint_refs]))
    # the span over the curve's midpoint, judged on the fractional occupancy (range review; was linear in the ratio to the KD); the lowest is judged only
    # when it differs from the highest (one concentration is a short series, judged by the count, not a badly placed one). A range may state only one
    # end: that end alone is judged, the unstated one is unknown and adds nothing (never 0, never a conflict).
    low_ratio, high_ratio = (None if over is None else over * native['constant_nM'] / midpoint for over in (low_over, high_over))
    degrees = [] if count is None else [count]
    if high_ratio is not None:
        degrees.append(_agreement(_occupancy(high_ratio), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_AGREEMENT_FACTOR)))
    if low_ratio is not None and (high_ratio is None or low_ratio < high_ratio):
        degrees.append(_agreement(_occupancy(low_ratio), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_AGREEMENT_FACTOR)))
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _equilibration_min(kd_nM, kon_per_M_per_s):
    """Minutes of EQUILIBRATION_HALF_LIVES off-rate half-lives at koff = kon x KD."""
    koff_per_s = kon_per_M_per_s * kd_nM / NM_PER_M
    return EQUILIBRATION_HALF_LIVES * math.log(2.0) / koff_per_s / S_PER_MIN


def _judge_incubation(native):
    # Without the paper's own KD there is no scale: unknown (a time alone is not the paper against equilibrium), also within the mixing.
    # With it: conflicting at or below T_FAST (even the fastest plausible association has not equilibrated); then the degree is min(d_floor, d_kon), see the docstring.
    if _binding_constant(native) is None:
        return _verdict('unknown', native['incubation_refs'])
    minutes = native['incubation_min']
    refs = list(dict.fromkeys([*native['incubation_refs'], *native['quantities']['kd']['source_refs']]))
    fast = _equilibration_min(native['kd_nM'], FAST_KON_PER_M_PER_S)
    if minutes <= fast:
        return _verdict('conflicting', refs)
    slow = _equilibration_min(native['kd_nM'], SLOW_KON_PER_M_PER_S)
    d_kon = min(1.0, math.log(minutes / fast) / math.log(slow / fast))
    d_floor = min(1.0, minutes / MIN_INCUBATION_MIN)
    return _verdict('supported', refs, min(d_floor, d_kon))


def _judge_replicates(native):
    # Shape: min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean KD over n independent titrations (see MIN_REPLICATES); never conflicting for a stated count.
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_amplitude', 'fluorescence_change_recorded_for_the_sheet'): _judge_signal, ('excitation_selectivity', 'excitation_recorded_for_the_sheet'): _judge_excitation,
          ('inner_filter', 'ligand_absorbance_recorded_for_the_sheet'): _judge_absorbance, ('dilution', 'added_volume_recorded_for_the_sheet'): _judge_dilution,
          ('protein_concentration', 'protein_over_kd_recorded_for_the_sheet'): _judge_protein, ('concentration_series', 'series_recorded_for_the_sheet'): _judge_series,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_incubation, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _binding_constant(native):
    """'kd' when the record carries a KD whose curve was not fitted with the Stern-Volmer equation, else None."""
    return 'kd' if native['kd_nM'] is not None and native['fit_model'] != 'stern_volmer' else None


def _variance(graded, constant_name):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if constant_name is None:
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


def convert_trp(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        if native['kd_nM'] is not None:
            null_components['effect'] = 'the_kd_was_fitted_with_the_stern_volmer_equation_which_gives_a_quenching_constant'
        elif native['quantities']['ksv']['status'] == 'point':
            null_components['effect'] = 'only_a_stern_volmer_quenching_constant_given_not_a_dissociation_constant'
        else:
            null_components['effect'] = 'no_kd_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'trp_kd:' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'trp_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
    return {'version': VERSION, 'experiment_type': 'trp_quenching', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
