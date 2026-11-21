"""FP converter: turns the FP grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to FP, deterministic. Input: the result of grade_fp.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI and GCI converters fill), the
dependence keys the merger needs, and for every sheet component that an FP
measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  KD of a direct titration, or, when the record has no KD,
                  the Ki of a competition experiment (the grader's
                  'constant_name' says which; the measurement key names it:
                  fp_kd or fp_ki). Neither given leaves effect null.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent titrations); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the SPR, ITC, BLI
and GCI converters): analyte_preparation_ref = the titrant,
immobilized_preparation_ref = the labelled tracer partner, surface_ref = None
(FP has no surface), dataset_ref = the dataset.

Criteria mapping (FP criteria -> sheet criteria), declared in CRITERIA_MAP
--------------------------------------------------------------------------
binding_controls              free_probe_baseline + specificity_control +
                              surface_adsorption
binding_regime                tracer_concentration + concentration_series +
                              equilibrium + direct_vs_competition
binding_parameter_definition  fit_model + intensity_change
calibration_applicability     assay_window (the polarization span against the
                              plate reader's resolution: FP's counterpart of
                              the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). The researched values are kept (EXPERT_REVIEW constants below,
each with its reason) and judged gradually around them (OWNER RULE, A105_EXPERIMENT_SOP step 3: no pass/fail step at a researched value).
Continuous comparisons give a degree: supported with degree 1.0 at or better than the full-agreement limit, falling to 0 at the zero-agreement limit,
conflicting at or beyond it. Each curve is drawn on the scale on which its error acts (see the range review below):
  assay_window           linear in 1 / window between MIN_WINDOW_MP and WINDOW_ZERO_AGREEMENT_MP (each fraction-bound point carries the
                         reader's mP noise over the window);
  tracer_concentration   linear in the log of the depletion bias of the apparent KD, 1 + TRACER_BOUND_AT_MIDPOINT * tracer / KD, between
                         TRACER_MAX_OVER_KD and TRACER_ZERO_AGREEMENT_OVER_KD, unless tight binding is handled;
  concentration_series   the weakest of three: the lowest and the highest concentration each linear in the share of sites it occupies,
                         x / (1 + x) with x the concentration over the constant (LOW_FACTOR / LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR /
                         HIGH_ZERO_AGREEMENT_FACTOR), and the count linear in the residual degrees of freedom between MIN_CONCENTRATIONS and
                         FIT_PARAMETERS (the count only lowers the degree: no credit at FIT_PARAMETERS or fewer, never conflicting);
  intensity_change       linear in percent between INTENSITY_CHANGE_MAX_PERCENT and INTENSITY_ZERO_AGREEMENT_PERCENT;
  direct_vs_competition  linear in the log of the fold gap between AGREEMENT_FACTOR and AGREEMENT_ZERO_FACTOR.
Replicates: n independent titrations give supported with degree sqrt(n / MIN_REPLICATES), capped at 1 (the precision of the mean constant, relative to
the researched count); with the independence not stated yes, unknown. Equilibrium: an incubation shorter than the paper's own constant needs at the fastest plausible association (EQUILIBRATION_HALF_LIVES off-rate half-lives at koff = FAST_KON_PER_M_PER_S x the
constant, T_FAST) is conflicting; beyond it the degree is min(t / MIN_INCUBATION_MIN, log(t / T_FAST) / log(T_SLOW / T_FAST)) capped at 1, T_SLOW being the same time
at SLOW_KON_PER_M_PER_S; with no constant stated, unknown (see _judge_incubation). A sheet criterion that is
supported carries the smallest degree of its members that have one.

Range review (A105_EXPERIMENT_SOP step 3; 2026-11-21). Q1 what it protects against; Q2 general practice or lab-specific; Q3 absolute or relative
scale, and whether the grader has the fact; Q4 how badly a wrong value misleads and whether the shape fits; Q5 consistency with the other binding
assays. References: Rossi & Taylor 2011 Nat Protoc 6:365; Moerke 2009 Curr Protoc Chem Biol 1:1; Lea & Simeonov 2011 Expert Opin Drug Discov
6:17; Huang 2003 J Biomol Screen 8:34; Nikolovska-Coleska et al. 2004 Anal Biochem 332:261; Pollard 2010 Mol Biol Cell 21:4061; Jarmoskaite et
al. 2020 eLife 9:e57264; Lakowicz, Principles of Fluorescence Spectroscopy, 3rd ed., ch. 10; Schreiber, Haran & Zhou 2009 Chem Rev 109:839.
  assay_window (70 / 20 mP). Q1 a titration whose mP change is too small against the plate reader's noise to be fitted. Q2 general: about 100 mP is
    the usual target and a few mP the usual reproducibility (Lea & Simeonov 2011; Rossi & Taylor 2011); 70 allows a lower but usable window. Q3 the
    true scale is the window over the paper's own mP noise (or its Z'), which the grader does not collect (grader gap); absolute mP is the proxy,
    with the typical reader noise. Q4 each fraction-bound point has error noise / window, so losing 10 mP near 70 matters little and near 20 a great
    deal: the old linear-in-mP ramp was too steep near 70 and too gentle near 20. CHANGED: linear in 1 / window (45 mP: 0.50 -> 0.78; 25 mP:
    0.10 -> 0.28). Q5 same idea as the FRET window fold and the MST signal-to-noise (a signal over its noise).
  tracer_concentration (1 / 10 x KD). Q1 tracer depletion: the midpoint of a direct titration sits at KD + tracer / 2, so a tracer near or above KD
    inflates the apparent KD. Q2 general: tracer at or below KD, ideally well below (Rossi & Taylor 2011; Jarmoskaite et al. 2020). Q3 relative to the
    paper's KD, which the grader has. Q4 a magnitude error of (1 + r / 2)-fold, read by the sheet on a log scale; at the full end the bias is 1.5-fold,
    at the zero end 6-fold. The old linear-in-r ramp gave the first doubling of r (1 -> 2, bias 1.5 -> 2-fold) almost no penalty. CHANGED: linear in
    log(1 + r / 2) (r 2: 0.89 -> 0.79; r 4: 0.67 -> 0.50; r 5.5: 0.50 -> 0.34). Values kept. Q5 the same depletion reasoning applies to the MST and FRET
    labelled-partner ramps (flagged for them, not changed here).
  concentration_series span (0.2 / 1 x and 10 / 1 x the constant). Q1 a curve whose free baseline or bound plateau is never seen, so the fitted KD
    is extrapolated. Q2 general: about 0.1 to 10 x KD (Pollard 2010; Jarmoskaite et al. 2020). Q3 relative to the constant, which the grader has; for a
    Ki the competitor series should span the IC50, not the Ki (the IC50 and the protein concentration are a grader gap). Q4 what the ends define is the
    share of sites occupied, x / (1 + x): a top at 5.5 x KD already reaches 85 percent of the plateau, so the old linear-in-x ramp (0.50 there) was
    too harsh at the top end and slightly too lenient at the bottom end. CHANGED: linear in occupancy (top 5.5 x: 0.50 -> 0.85; top 3 x: 0.22 -> 0.61;
    bottom 0.6 x: 0.50 -> 0.38; bottom 0.5 x: 0.63 -> 0.50). Values kept. Q5 the MST, FRET and SPR span ramps use the same values and the old linear
    shape (flagged for them, not changed here).
  concentration_series count (8 / 3). Q1 too few points to test the curve's shape. Q2 FP titrations are usually 12 to 24 points (Rossi & Taylor
    2011; Moerke 2009); 8 is a usable minimum, lab-practice level. Q3 absolute: the three fitted parameters are fixed by the model. Q4 each point
    beyond three is one residual degree of freedom that tests the shape and each adds the same, so linear is right. KEPT. Q5 the same as FRET (8 / 3)
    and MST (10 / 3); a short series is partial credit, never conflicting.
  intensity_change (30 / 100 percent). Q1 a quantum-yield change Q on binding: uncorrected, the apparent KD is KD / Q (Lakowicz ch. 10). Q2 a
    correction is recommended once the total intensity changes by more than about 20 to 30 percent (lab-practice level). Q3 already relative (percent
    of the free tracer's intensity). Q4 a magnitude error of Q-fold; for an increase, log(Q) is within 0.06 of the linear ramp over 30 to 100 percent, so
    the shape is KEPT. But the record does not say whether the intensity rose or fell: a 60 percent fall is a 2.5-fold bias and scores 0.57 (grader
    gap: the sign). The zero end (conflicting) is for a magnitude error only, not a direction error; kept as committed for the owner. Q5 no
    counterpart in the other assays.
  equilibrium, DECISION A 2026-11-21 (T_FAST kept; SLOW_KON 1e5 new, owner to confirm; floor 5 min now proportional). Q1 the same as below. Q2 the slow
    kon is from memory of Schreiber, Haran & Zhou 2009 (about 1e5 to 1e7 per M per s for association without steering). Q3 relative to the constant
    (grader hands it with its refs; no grader change). Q4 the old cliff (conflicting below the needed time, unknown above) is now a curve on the log of
    the association rate: conflicting only at or below T_FAST (the paper's own numbers against even the fastest binder), full at T_SLOW = 100 x T_FAST,
    in between the share of the two decades of plausible kon covered. The floor is proportional: t / 5 min. No constant stated: unknown, also below the
    floor. Worked: KD 1000 nM, T_FAST 0.0058 min, T_SLOW 0.58 min: 5 min full, 1 min 0.20 (floor). KD 0.01 nM: T_FAST 578 min, T_SLOW 57762 min:
    1 h conflicting, 24 h 0.198, 10 days 0.70. KD 20 nM: T_FAST 0.289 min, T_SLOW 28.9 min: 4 min 0.571, 10 min 0.770, 30 min 1.0. Q5 the
    other binding assays with the same cliff are flagged, not changed here. Previously the text read as follows.
  equilibrium (MIN_INCUBATION_MIN 5 min). Q1 reading a titration before its lowest points have bound, which inflates the apparent KD. Q2 general:
    about five half-lives of the slowest approach, set by koff at the lowest concentrations (Jarmoskaite et al. 2020). Q3 the time needed is relative to
    the constant: koff = kon x KD, so a sub-nanomolar binder needs about an hour even with a fast kon; the constant is in the grader facts. CHANGED:
    the conflicting limit is now the larger of 5 min and 5 half-lives at kon = 1e7 per M per s (the fast end of typical protein-ligand association,
    Schreiber, Haran & Zhou 2009), which only matters below a constant of about 1.2 nM (KD 0.1 nM: 58 min). Q4 a step to conflicting is kept, on
    purpose: only the paper's own numbers trigger it, at a kon that makes the limit the most lenient plausible one; above it the answer is unknown,
    not credit. Q5 MST (10 min) and FRET (15 min) also use a fixed floor; the same KD-relative limit applies to them (flagged, not changed here).
  replicates (3). Q1 a constant from one dilution series and tracer preparation. Q2 three independent titrations is general practice (Jarmoskaite
    et al. 2020). Q3 absolute count. Q4 sqrt(n / 3) is the precision of the mean. KEPT. Q5 the consistency rule exactly; a stated no stays the
    grader's conflicting fact.
  direct_vs_competition (3 / 10 fold). Q1 a direct KD and a competition Ki that disagree: the label changes the binding, or the Ki conversion
    (tracer KD, protein concentration, Nikolovska-Coleska et al. 2004) is wrong. Q2 lab-practice level. Q3 kept absolute: the gap is a systematic
    difference between two methods, which the stated within-method spreads do not describe. Q4 a fold gap is multiplicative and the sheet reads
    constants on a log scale, so equal ratios should cost the same; the old linear-in-fold ramp gave 3 -> 4 fold almost nothing. CHANGED: linear in
    log(fold) (fold 6.5: 0.50 -> 0.36; fold 5.5: 0.64 -> 0.50). Values kept. Q5 MST and FRET hold the same values and the old shape (flagged).
Grader gaps of the range review, and what was done with them (form v2; needs a real-model run):
  1. mP noise of the reads (assay_window): ADDED as the quantity signal_noise (mP only; the Z' is not collected, it is derived from the same SDs). When
     stated, the window is also judged over that noise: full agreement at WINDOW_OVER_NOISE_FULL = 12 (Z' 0.5), conflicting at WINDOW_OVER_NOISE_ZERO = 3
     (limit of detection), linear in noise / window between them; the weaker of this and the absolute-mP degree counts (in addition, not instead).
     Unstated noise leaves the absolute curve alone. Unknown weight unchanged.
  2. Sign of the intensity change (intensity_change): ADDED as the choice intensity_change_direction. When stated, the degree is linear in the log of the
     bias of the apparent KD (increase p: 1 + p/100; fall p: 1/(1 - p/100); ends at the bias of the researched 30 and 100 percent as increases, 1.3 and 2),
     so a 60 percent fall (2.5-fold) is now conflicting rather than 0.57; a fall of 100 percent or more is conflicting. Direction not stated: the percent
     curve as before.
  3. Competition format (concentration_series): ADDED ic50 (quantity) and series_kind (choice titrant or competitor). A competitor series is judged
     against the IC50 (the centre of a competition curve) when the IC50 is given, with the same researched ends. NOT added: the protein and the tracer
     concentration of the competition plate. They are only needed to recompute a Ki from an IC50 (Nikolovska-Coleska 2004), which the sheet does not do;
     the paper's own Ki is the effect, and its credibility is judged by direct_vs_competition and tracer_concentration (the tracer concentration is already a
     field). Which titration the series belongs to is series_kind.
Quote support (literature_quote_support.py, SUPPORT_DEGREE direct 1.0 / implied 0.7 / about_something_else 0.3): when any stated field a member criterion reads has
support 'implied' or 'about_something_else', a supported sheet criterion gets the weakest support degree as its degree (the product with its degree where it had one);
support never changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no FP counterpart (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_criteria import NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_fp_converted_v1'
CRITERIA_MAP = {'binding_controls': ('free_probe_baseline', 'specificity_control', 'surface_adsorption'), 'binding_regime': ('tracer_concentration', 'concentration_series', 'equilibrium', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model', 'intensity_change'), 'calibration_applicability': ('assay_window',), 'sampling_basis': ('replicates',)}
MIN_WINDOW_MP = 70.0  # EXPERT_REVIEW: smallest polarization window (bound minus free, in mP) that a typical plate reader (reproducibility of a few mP) resolves into a titration curve; 100 mP or more is common practice (Lea & Simeonov 2011; Rossi & Taylor 2011), this allows for a lower but still usable window; the full-agreement limit. The degree is linear in 1 / window (the error of each fraction-bound point is the reader noise over the window).
WINDOW_ZERO_AGREEMENT_MP = 20.0  # EXPERT_REVIEW: window (mP) at or below which the sheet takes the titration as unresolved (conflicting): with a reproducibility of a few mP a window of 20 mP or less is lost in the noise of the plate reader.
WINDOW_OVER_NOISE_FULL = 12.0  # EXPERT_REVIEW: window over the paper's own noise (one SD of the polarization reads) at or above which the window is resolved with full agreement: a Z' of 0.5, the usual 'excellent assay' line, is 1 - 3 (SD_free + SD_bound) / window, which for equal SDs needs a window of 12 SD (Zhang, Chung & Oldenburg 1999 J Biomol Screen 4:67). The degree is linear in noise / window, like the absolute curve.
WINDOW_OVER_NOISE_ZERO = 3.0  # EXPERT_REVIEW: window over noise at or below which the sheet takes the titration as unresolved (conflicting): a change of three SD of the reads is the conventional limit of detection, so the curve cannot be told from noise.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable FP titration (FP titrations are usually 12 to 24 point dilution series); the full-agreement count (fewer get partial credit, see FIT_PARAMETERS).
FIT_PARAMETERS = 3  # EXPERT_REVIEW: parameters an FP binding curve is fitted with (free-tracer polarization, bound-tracer polarization and the constant; also three for a quadratic fit at a known tracer concentration and for a competition fit at a known tracer KD); a series of this many concentrations or fewer is passed through exactly by the curve and leaves no point to test it, so it is the zero-credit count (degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against).
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest titrant concentration must be at most this multiple of the reported constant (the baseline of the curve must be defined); the full-agreement limit.
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or above which the lowest concentration leaves the curve with no baseline at all (half the sites are already bound), conflicting.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest titrant concentration must be at least this multiple of the reported constant, because FP has no other way to know the bound plateau than to reach it (about 90 percent saturation); the full-agreement limit.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or below which the highest concentration reaches no more than half saturation, so the plateau is not seen at all, conflicting.
TRACER_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the tracer concentration may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by tracer depletion); the full-agreement limit.
TRACER_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW: tracer over KD at or above which the apparent KD is dominated by the tracer concentration (an apparent KD 6-fold too high), conflicting unless tight binding is handled.
TRACER_BOUND_AT_MIDPOINT = 0.5  # FIXED_BY_DEFINITION: at the midpoint of a 1:1 direct titration half the tracer is bound, so the total titrant there is KD + 0.5 x tracer; the apparent KD is (1 + 0.5 x tracer / KD)-fold too high, and the tracer degree is linear in the log of that bias.
INTENSITY_CHANGE_MAX_PERCENT = 30.0  # EXPERT_REVIEW: a change of the total fluorescence intensity larger than this on binding makes the bound and free tracers contribute unequally to the polarization, so the fraction bound is wrong unless it is corrected; the full-agreement limit.
INTENSITY_ZERO_AGREEMENT_PERCENT = 100.0  # EXPERT_REVIEW: change of the total intensity (percent) at or above which the intensity at least doubles on binding and the polarization cannot be read as a fraction bound, conflicting.
MIN_INCUBATION_MIN = 5.0  # EXPERT_REVIEW: the absolute floor (minutes): mixing, settling of the plate and reading take about this long, whatever the constant; the incubation degree from it is t / MIN_INCUBATION_MIN (proportional, never conflicting by itself). Conflicting only comes from the constant's own fastest time (see FAST_KON_PER_M_PER_S).
EQUILIBRATION_HALF_LIVES = 5.0  # EXPERT_REVIEW: half-lives of the slowest approach (koff, at the lowest titrant concentrations) after which a titration is about 97 percent equilibrated (Jarmoskaite et al. 2020 eLife 9:e57264).
FAST_KON_PER_M_PER_S = 1.0e7  # EXPERT_REVIEW: the fast end of typical protein-ligand and protein-peptide association rate constants (about 1e5 to 1e7 per M per s; Schreiber, Haran & Zhou 2009 Chem Rev 109:839). koff = kon x constant at this kon is the fastest plausible off rate, so the time it gives is the most lenient plausible equilibration time: an incubation shorter than it is too short even for a fast binder. It exceeds MIN_INCUBATION_MIN only for a constant below about 1.2 nM.
SLOW_KON_PER_M_PER_S = 1.0e5  # EXPERT_REVIEW (owner to confirm; citation from memory): the slow end of typical association rate constants for FP partners, a labelled peptide, small ligand or oligonucleotide tracer and a protein: about 1e5 per M per s without electrostatic steering (Schreiber, Haran & Zhou 2009 Chem Rev 109:839). Slower still (1e3 to 1e4) happens when a conformational change gates binding, but that is the rare case, so the plausible span is taken as 1e5 to 1e7 (two decades). It gives T_SLOW = 100 x T_FAST, the time at which even a slow binder has equilibrated; the incubation degree reaches 1 there.
NM_PER_M = 1.0e9  # FIXED_BY_DEFINITION
S_PER_MIN = 60.0  # FIXED_BY_DEFINITION
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series); the full-agreement count (fewer independent titrations get partial credit, sqrt(n / MIN_REPLICATES)).
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a direct-titration KD and a competition Ki (a Ki depends on the tracer's own KD and its uncertainty, so the standard is looser than for two direct estimates); the full-agreement limit.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap at or above which a direct KD and a competition Ki are different quantities (an order of magnitude), conflicting.
NULL_REASONS = {'recovery': 'fp_has_no_matrix_recovery_measurement', 'attributed_signal': 'fp_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'fp_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_fp_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_fp_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _log_scaled(value, full, zero, refs):
    """_scaled on the log of a positive, multiplicative quantity (a fold or a bias factor): equal ratios cost the same."""
    return _scaled(math.log(value), math.log(full), math.log(zero), refs)


def _occupancy(over_constant):
    """Share of the sites occupied at a titrant concentration of over_constant x the constant (1:1, x / (1 + x))."""
    return over_constant / (1.0 + over_constant)


def _judge_window(native):
    # Linear in 1 / window: the reader's mP noise is about the same whatever the window, so each fraction-bound point carries an error of noise / window,
    # and the KD's precision follows it (gentle near MIN_WINDOW_MP, steep near WINDOW_ZERO_AGREEMENT_MP). Guarded first: 1 / window has no meaning at or below 0.
    window, refs = native['window_mP'], native['window_refs']
    if window <= WINDOW_ZERO_AGREEMENT_MP:
        return _verdict('conflicting', refs)
    absolute = _scaled(1.0 / window, 1.0 / MIN_WINDOW_MP, 1.0 / WINDOW_ZERO_AGREEMENT_MP, refs)
    noise = native['window_noise_mP']
    if noise is None:
        return absolute
    # The paper's own noise is used in addition to the typical-reader scale, not instead of it (the weaker of the two counts): the window over the stated
    # noise, on the same 1 / window shape (the error of each fraction-bound point is noise / window).
    refs = list(dict.fromkeys([*refs, *native['window_noise_refs']]))
    if window <= noise * WINDOW_OVER_NOISE_ZERO:
        return _verdict('conflicting', refs)
    relative = _scaled(noise / window, 1.0 / WINDOW_OVER_NOISE_FULL, 1.0 / WINDOW_OVER_NOISE_ZERO, refs)
    if absolute['status'] == 'conflicting' or relative['status'] == 'conflicting':
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(absolute['degree'], relative['degree']))


def _depletion_bias(tracer_over_kd):
    return 1.0 + TRACER_BOUND_AT_MIDPOINT * tracer_over_kd


def _judge_tracer(native):
    if native['tight_binding_handled']:
        return _verdict('supported', native['tracer_refs'])      # the quadratic or tight-binding analysis does not depend on the tracer over the KD
    # Linear in the log of the apparent KD's depletion bias, the magnitude error the sheet reads on its log scale.
    return _log_scaled(_depletion_bias(native['tracer_over_kd']), _depletion_bias(TRACER_MAX_OVER_KD), _depletion_bias(TRACER_ZERO_AGREEMENT_OVER_KD), native['tracer_refs'])


def _judge_series(native):
    refs = native['series_refs']
    # The count: full credit at the researched MIN_CONCENTRATIONS, linear down to FIT_PARAMETERS. Why this shape for FP: every concentration beyond the
    # three fitted parameters of the binding curve is one residual degree of freedom that tests the curve's shape, and each adds the same, so the credit
    # is linear in the residual degrees of freedom (n - FIT_PARAMETERS); at FIT_PARAMETERS points or fewer the curve passes through every point exactly.
    # The count only lowers the degree, never makes the series conflicting (at FIT_PARAMETERS or fewer: no credit, degree 0).
    count = _agreement(native['concentration_count'], MIN_CONCENTRATIONS, FIT_PARAMETERS) or 0.0
    # The ends: linear in the share of sites occupied, x / (1 + x), because that is what an end defines (how much of the free baseline the lowest point
    # leaves, how much of the bound plateau the highest point reaches); a top at 5.5 x the constant already sees 85 percent of the plateau.
    low = _agreement(_occupancy(native['concentration_low_over_constant']), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_AGREEMENT_FACTOR))
    high = _agreement(_occupancy(native['concentration_high_over_constant']), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_AGREEMENT_FACTOR))
    if low is None or high is None:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(count, low, high))


def _equilibration_min(constant_nM, kon_per_m_per_s):
    """Minutes of EQUILIBRATION_HALF_LIVES off-rate half-lives at koff = kon x the constant."""
    koff_per_s = kon_per_m_per_s * constant_nM / NM_PER_M
    return EQUILIBRATION_HALF_LIVES * math.log(2.0) / koff_per_s / S_PER_MIN


def _judge_incubation(native):
    # A curve, not a cliff (owner rule: gradual). With the paper's own constant, the time needed to equilibrate runs from T_FAST (kon = FAST_KON_PER_M_PER_S,
    # the most lenient plausible time) to T_SLOW (kon = SLOW_KON_PER_M_PER_S); association rates span decades, so on the log scale the share of the plausible rates
    # for which the incubation covers the five half-lives is d_kon = log(t / T_FAST) / log(T_SLOW / T_FAST), clipped to 0..1. At or below T_FAST not even the fastest
    # plausible binder has equilibrated: conflicting (the zero end, as before). The absolute floor (mixing, settling, reading) is d_floor = t / MIN_INCUBATION_MIN,
    # proportional and never conflicting by itself. The degree is the weaker of the two. No constant: no scale, so unknown (a time alone is not the paper against equilibrium).
    refs, constant = native['incubation_refs'], native['constant_nM']
    if constant is None:
        return _verdict('unknown', refs)
    minutes = native['incubation_min']
    refs = list(dict.fromkeys([*refs, *native['quantities'][native['constant_name']]['source_refs']]))      # the constant sets the scale, so its quote is cited too
    t_fast = _equilibration_min(constant, FAST_KON_PER_M_PER_S)
    if minutes <= t_fast:
        return _verdict('conflicting', refs)
    t_slow = _equilibration_min(constant, SLOW_KON_PER_M_PER_S)
    d_kon = min(1.0, math.log(minutes / t_fast) / math.log(t_slow / t_fast))
    d_floor = min(1.0, minutes / MIN_INCUBATION_MIN)
    return _verdict('supported', refs, min(d_floor, d_kon))


def _intensity_bias(percent, direction):
    """The fold by which an uncorrected intensity change moves the apparent KD (Q-fold up or down, Lakowicz ch. 10): an increase of p percent is 1 + p / 100, a
    fall of p percent is 1 / (1 - p / 100). None for a fall of 100 percent or more (no signal left)."""
    if direction == 'increase':
        return 1.0 + percent / 100.0
    return None if percent >= 100.0 else 1.0 / (1.0 - percent / 100.0)


def _judge_intensity(native):
    percent, direction, refs = native['intensity_change_percent'], native['intensity_change_direction'], native['intensity_change_refs']
    if direction is None:
        return _scaled(percent, INTENSITY_CHANGE_MAX_PERCENT, INTENSITY_ZERO_AGREEMENT_PERCENT, refs)      # the sign is not stated: the size as an increase, as before
    # The sign is stated: linear in the log of the bias of the apparent KD, with the ends of the researched percentages read as increases (bias 1.3 and 2),
    # so a fall is held to the same fold error as a rise (a fall of 23 percent is a 1.3-fold bias, of 50 percent 2-fold).
    bias = _intensity_bias(percent, direction)
    if bias is None:
        return _verdict('conflicting', refs)
    return _log_scaled(bias, _intensity_bias(INTENSITY_CHANGE_MAX_PERCENT, 'increase'), _intensity_bias(INTENSITY_ZERO_AGREEMENT_PERCENT, 'increase'), refs)


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # a count alone does not say the titrations were independent dilution series
    # Full credit at the researched MIN_REPLICATES, partial below it: sqrt(n / MIN_REPLICATES), capped at 1. Why this shape for FP: the error of an FP
    # constant is dominated by the dilution series and tracer preparation, which only separate titrations sample, and the standard error of the mean
    # constant over n independent titrations falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance), so the credit is the
    # precision of n titrations relative to that of MIN_REPLICATES. One titration still gives a fitted constant, so it keeps partial credit.
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


def _judge_estimates(native):
    # Linear in log(fold): a fold gap is multiplicative and the sheet reads constants on a log scale, so equal ratios cost the same.
    return _log_scaled(native['estimate_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, native['estimate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('assay_window', 'window_recorded_for_the_sheet'): _judge_window, ('tracer_concentration', 'tracer_over_kd_recorded_for_the_sheet'): _judge_tracer,
          ('concentration_series', 'series_recorded_for_the_sheet'): _judge_series, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_incubation,
          ('intensity_change', 'intensity_change_recorded_for_the_sheet'): _judge_intensity, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates,
          ('direct_vs_competition', 'estimates_recorded_for_the_sheet'): _judge_estimates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    name = native['constant_name'] + '_spread' if native['constant_name'] else 'kd_spread'
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


def convert_fp(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    if native['constant_nM'] is None:
        null_components['effect'] = 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][native['constant_name']]
        quantities['effect'] = _operand(native['constant_nM'], 'nM', 'fp_' + native['constant_name'] + ':' + ref, constant['source_refs'], constant['origin'], native['constant_name'])
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'fp_variance:' + ref, variance_refs, 'derived', native['constant_name'] + '_spread')
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
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['tracer_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'fp', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][native['constant_name']]['support'] if native['constant_nM'] is not None else None}
