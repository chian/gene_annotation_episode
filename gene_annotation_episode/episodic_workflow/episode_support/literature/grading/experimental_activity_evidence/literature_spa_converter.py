"""SPA converter: turns the SPA grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_spa.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen and radioligand converters fill), the
dependence keys the merger needs, and for every sheet component that an SPA cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the KD of
                  the radioligand from a saturation experiment, or, when the record has
                  no KD, the Ki of a competition (the measurement key names it:
                  spa_kd or spa_ki). Neither given leaves effect null; an
                  IC50 alone is a half-maximal concentration, not a dissociation constant (it
                  depends on the concentration and the KD of the radioligand it competes with) and is not
                  carried into the effect.
                  With no effect operand the result is the experiment's stated yes/no
                  result (fact binding_detected): 'qualitative_effect' carries its
                  statement (interaction_detected, interaction_not_detected, or
                  interaction_not_stated when the passage states neither) and the
                  spans that state it.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent experiments) and n is at least
                  SD_MIN_EXPERIMENTS; confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the radioligand,
immobilized_preparation_ref = the captured target, surface_ref = None (the bead and the well are not a surface reference),
dataset_ref = the dataset.

Criteria mapping (SPA criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              nonspecific_binding + nonspecific_excess + nonproximity_signal + bead_only_control + radioligand_quality
binding_regime                equilibrium + radioligand_range + competition_radioligand_level + homogeneous_format
binding_parameter_definition  fit_model + nonlinear_fit + hill_slope + cheng_prusoff
calibration_applicability     ligand_depletion + nonspecific_fraction + quench_interference + bead_settling (the bound fraction of the
                              radioligand, the specific signal over the non-specific signal, and the two ways the counted light can
                              be mis-scaled in a bead assay, colour quench and bead settling: this method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet';
JUDGES maps each such criterion and reason to its judgement). Every researched value is a named EXPERT_REVIEW constant and an end of a gradual curve
(owner rule, A105_EXPERIMENT_SOP step 3): degree 1.0 at or past its full-agreement end, falling to 0 at its zero-agreement end, conflicting at or beyond
that end for a stated value. Two shapes, each chosen per criterion in the block below: linear in the stated value (ligand_depletion, nonspecific_fraction,
bead_only_control, hill_slope on both sides, cheng_prusoff) and linear in the fractional occupancy theta = x / (1 + x) of a concentration over its constant
(nonspecific_excess, the low and the high end of radioligand_range, competition_radioligand_level). Two counts never conflict: the concentration count of a
saturation series is max(0, (n - SATURATION_FIT_PARAMETERS) / (MIN_CONCENTRATIONS - SATURATION_FIT_PARAMETERS)), capped at 1 (radioligand_range takes the
weakest of it and the span; a count with no readable span is unknown); the replicates are min(1, sqrt(n / MIN_REPLICATES)) when the independence is yes,
else unknown. equilibrium without a half-time is gradual against the paper's KD (see _judge_equilibrium): conflicting only at or below T_FAST, no KD unknown. A sheet
criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and
the merger carries it per result).

Owner's questions per researched value (SOP step 3, 2026-11-21). Q1 the failure it catches; Q2 general practice or lab-specific; Q3 absolute or relative
scale, and is the fact in the grader; Q4 how badly a wrong value misleads, does the shape fit; Q5 consistency with the other binding assays. Sources:
Bylund and Toews 1993 Am J Physiol 265:L421; Hulme and Trevethick 2010 Br J Pharmacol 161:1219; Auld et al., Receptor Binding Assays for HTS and Drug
Discovery, Assay Guidance Manual (AGM, filtration and SPA); Motulsky and Christopoulos 2004, Fitting Models to Biological Data; Cheng and Prusoff 1973
Biochem Pharmacol 22:3099; Udenfriend, Gerber and Nelson 1987 Anal Biochem 161:494; Glickman, Schmid and Ferrand 2008 Assay Drug Dev Technol 6:433.
  ligand_depletion (MAX_PERCENT_BOUND 10, PERCENT_BOUND_ZERO_AGREEMENT 30)
    Q1 free radioligand taken as the added one: KD and Ki biased up.  Q2 general, under 10 percent bound (Bylund 1993; Hulme 2010; AGM); 30 is ours.  Q3 relative
    already (bound over added); the direct measure is receptor over KD (= f / (1 - f) at trace radioligand): bmax and receptor_amount are grader facts, the well
    volume is not (grader gap).  Q4 the midpoint KD bias 1 + Rt / (2 KD) is 1.06 at 10 and 1.21 at 30 percent; linear in percent is within 0.07 of linear in that
    bias. Stricter than filtration (50) because an SPA never counts the free radioligand and its bound counts are not in concentration units (unknown SPA
    efficiency), so depletion cannot be corrected in the analysis.  Q5 radioligand ends at 50 (that reason).  -> KEPT.
  nonspecific_fraction (MAX_NONSPECIFIC_FRACTION 50, NONSPECIFIC_FRACTION_ZERO_AGREEMENT 80)
    Q1 specific binding as a small difference of two large counts.  Q2 general, NSB under half the total at the highest concentration (Bylund 1993; AGM); 80 is
    ours.  Q3 relative to the paper's own total (a stated percent); the concentration at which the percent was read is not a grader fact (grader gap).  Q4 the
    relative error of T - N grows as sqrt(1 + f^2) / (1 - f); that precision rescaled between 50 and 80 is within 0.03 of linear. 80 not 90 because SPA counts
    per well are low (only radioligand within micrometres of a bead scintillates), so the same error ceiling comes earlier.  Q5 radioligand 90.  -> KEPT.
  bead_only_control (MAX_BEAD_ONLY_FRACTION 20, BEAD_ONLY_ZERO_AGREEMENT 50)
    Q1 SPA-specific: radioligand held by the bead itself (WGA, PVT, streptavidin); a displaceable part is counted as specific.  Q2 the control is general SPA
    practice (Udenfriend 1987; Glickman 2008; AGM); 20 and 50 are our judgement, not a guideline.  Q3 relative to the total (stated); a sharper scale is
    bead-only over NSB (bead signal above the NSB is displaceable), both grader percents but at unstated concentrations (same gap as nonspecific_fraction).
    Q4 non-displaceable bead binding sits in the NSB and costs only precision (judged by nonspecific_fraction); no stated number isolates the displaceable part,
    so the plain linear shape stays.  Q5 filtration has only a filter_binding fact.  -> KEPT.
  nonspecific_excess (MIN_NONSPECIFIC_EXCESS 100, NONSPECIFIC_EXCESS_ZERO_AGREEMENT 10)
    Q1 NSB wells still holding specific binding: specific binding and Bmax underestimated.  Q2 general, 100 to 1000 times the Ki or KD (Bylund 1993; Hulme
    2010).  Q3 relative to the constant of the unlabelled ligand; the grader divides by the cold ligand's own KD or Ki,
    else by the radioligand KD only when the cold ligand is the unlabelled radioligand; the cold ligand's own affinity and its identity are now grader facts (nonspecific_ligand_affinity, nonspecific_ligand_is_radioligand): the grader divides by the right constant or records nothing.  Q4 the specific binding left is 1 - theta = 1 / (1 + x): 1 percent at
    100, 9 at 10. Linear in x spent half the credit between 100 and 55 (residual 1.0 to 1.8 percent) and was flat near 10 where it matters (MISTAKE, fixed);
    linear in theta: 55 -> 0.90, 20 -> 0.53.  Q5 radioligand ends at 1 (half occupancy); SPA's 10 is a residual of the order of its depletion end.
    -> CHANGED shape (values kept): linear in x -> linear in occupancy.
  radioligand_range count (MIN_CONCENTRATIONS 8, SATURATION_FIT_PARAMETERS 3 -> 2)
    Q1 KD and Bmax from too few concentrations to fix both and show one-site saturation.  Q2 general, 8 to 12 concentrations (Hulme 2010; Motulsky 2004; AGM).
    Q3 absolute count.  Q4 the zero end 3 assumed the fit spends a parameter on the non-proximity slope; with NSB wells that slope is read from its own wells (a
    global fit has 2n points and 4 parameters, 2 (n - 2) residual df), as in filtration: 2 (MISTAKE of the earlier SPA pass, fixed). Three or fewer was
    conflicting, a short series made opposition (MISTAKE, fixed). Linear in residual df: each concentration is one more independent check of the hyperbola.
    Q5 SPR: zero end 2, never conflicting; radioligand: 2, still conflicting.  -> CHANGED: 3 -> 2; conflicting -> supported with degree max(0, (n - 2) / 6).
  radioligand_range span (LOW_FACTOR 0.25 / LOW_ZERO_AGREEMENT_FACTOR 1.0, HIGH_FACTOR 5.0 / HIGH_ZERO_AGREEMENT_FACTOR 1.0)
    Q1 KD or Bmax extrapolated outside the sampled curve.  Q2 general, 0.1 to 10 times the KD (Bylund 1993; Hulme 2010).  Q3 relative to the paper's own KD
    (grader fact).  Q4 linear in the ratio was asymmetric (0.5x KD 0.67 but 2x KD 0.25, each one fold from the KD) and on the high side spent most credit from
    5x to 3x (occupancy 83 to 75 percent) and little from 2x to 1x (67 to 50), where Bmax becomes an extrapolation (MISTAKE, fixed); linear in occupancy:
    0.5x -> 0.56, 2x -> 0.50, 2.5x -> 0.64.  Q5 DSF uses occupancy; SPR, radioligand, alpha keep linear in the ratio.  -> CHANGED shape (values kept).
  competition_radioligand_level (MAX_RADIOLIGAND_OVER_KD 1, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT 10)
    Q1 a Ki that is mostly the Cheng-Prusoff correction: Ki = IC50 / (1 + r), and the share of an error in the KD or the radioligand concentration passed into
    the Ki is r / (1 + r), the radioligand occupancy.  Q2 general, radioligand at or below its KD (Hulme 2010; AGM).  Q3 relative to the paper's own KD (grader
    fact).  Q4 linear in r spent little credit from 1x to 3x (error share 50 to 75 percent) and most from 3x to 10x (75 to 91): the wrong way round (MISTAKE,
    fixed); linear in occupancy: 2x -> 0.59, 3x -> 0.39, 5x -> 0.19.  Q5 radioligand has the same values, linear in r.  -> CHANGED shape (values kept).
  equilibrium (MIN_INCUBATION_MIN 30)
    Q1 binding not at equilibrium (affinity underestimated for slow radioligands; in an SPA also incomplete capture on the beads).  Q2 general, five half-lives of
    the slowest step (Hulme 2010); SPA protocols 1 to 4 h or overnight (Glickman 2008); 30 min is ours.  Q3 relative to the paper's own association half-time when
    it states one (association_half_time, now a grader fact: EQUILIBRIUM_HALF_TIMES 5, a gradual fraction of the plateau reached, supported and never conflicting);
    with no half-time the incubation is judged against the paper's KD (2026-11-21, owner's gradual rule): T_FAST = 5 ln2 / (KON_FAST * KD), T_SLOW likewise
    with KON_SLOW (1e8 and 1e5 per M per s, EXPERT_REVIEW, owner to confirm, from memory); d_kon = log(t / T_FAST) / log(T_SLOW / T_FAST) clipped to 0..1, the
    share of the plausible association rates (log scale) for which the incubation covers five half-lives; t <= T_FAST is conflicting (the zero end: even the
    fastest plausible association has not equilibrated); d_floor = min(1, t / MIN_INCUBATION_MIN) for mixing, settling and bead capture, proportional; supported
    with degree min(d_floor, d_kon); no KD stated: unknown (no scale, also below the floor).  Q4 the log scale because association rates span decades: one
    decade of rate costs a third of the curve; the KD sets the scale because koff = kon * KD limits the approach (kobs = kon * ([L] + KD), slowest at the lowest
    radioligand concentration).  Numbers: KD 1 uM, 120 min: T_FAST 0.0006 min, T_SLOW 0.58 min, d_kon 1, degree 1; KD 2 nM, 120 min: T_FAST 0.289 min, d_kon 0.873;
    KD 1 pM, 960 min: T_FAST 578 min, d_kon 0.074; KD 1 pM, 120 min: conflicting (the tight binder needs hours even at the fastest rate).  Q5 as the other
    binding assays: gradual, conflicting only at the zero end.  -> CHANGED (the 30 min step is now the proportional floor, the KD scale is new).
  hill_slope (MIN_HILL 0.8, MAX_HILL 1.2, HILL_LOW_ZERO_AGREEMENT 0.5, HILL_HIGH_ZERO_AGREEMENT 2.0)
    Q1 not one site obeying mass action (heterogeneity, cooperativity, depletion or non-equilibrium steepening).  Q2 general, 0.8 to 1.2 (Hulme 2010; Motulsky
    2004).  Q3 should be relative to the slope's own SE; that spread is not a grader fact (grader gap).  Q4 the 10-90 percent span of the curve is
    81^(1 / nH)-fold, so 0.5 and 2.0 are equally far from mass action; linear in nH on each side is within 0.13 of linear in 1 / nH or log nH.  Q5 radioligand
    ends at 1.5 above (not symmetric with its 0.5).  -> KEPT.
  cheng_prusoff (CHENG_PRUSOFF_FACTOR 1.5, CHENG_PRUSOFF_ZERO_AGREEMENT_FACTOR 5.0)
    Q1 a reported Ki not computed from this experiment's IC50, radioligand and KD (another KD or equation, IC50 given as Ki, a unit slip).  Q2 the equation is
    general (Cheng and Prusoff 1973); 1.5 (rounding, fit) and 5 are ours.  Q3 relative already (the paper's Ki over the Ki recomputed from its own numbers).
    Q4 linear in log fold would differ by at most 0.15 (3x: 0.42 against 0.57); a 2 to 3 fold Ki error moves the strength by a fraction of a log unit, so the
    linear shape of the other fold gaps stays.  Q5 radioligand, SPR and alpha fold gaps are linear.  -> KEPT.
  replicates (MIN_REPLICATES 3; REPLICATES_ZERO 1 removed)
    Q1 a constant from one bead suspension, capture and day.  Q2 general, three independent experiments (Hulme 2010; AGM).  Q3 absolute count.  Q4 was linear in
    n - 1 with one experiment conflicting: one well-run SPA became opposition (MISTAKE of the earlier SPA pass, fixed); fewer experiments lose precision of the
    mean constant, standard error ~ 1 / sqrt(n).  Q5 replicates mean precision, sqrt(n / MIN) as SPR, alpha, FP, FRET, pull-down, DSF.
    -> CHANGED: linear in n - 1 from REPLICATES_ZERO (conflicting) -> min(1, sqrt(n / 3)); SD_MIN_EXPERIMENTS 2 added for the variance only.
  Grader gaps considered and NOT added (2026-11-21): the assay well volume (percent_bound is the direct depletion measure and is collected; the volume route needs
    bmax, receptor_amount and volume all stated in compatible units, rarely all given); the concentration at which the NSB or bead-only percent was read (the form's
    meaning already fixes the NSB percent at the highest concentration; the sharper bead-over-NSB scale would still rest on the same unstated concentration); the
    Hill slope's own SE (rarely reported beside a Hill slope; the 0.8 to 1.2 practice range stays); a settling-time curve (settling is bead- and plate-specific, no
    general researched scale; the fact bead_settling_controlled and the recorded settling_min stay).
  Unknown weight (row_contract WEIGHT_UNKNOWN_BY_TYPE['spa'], not in this file and never inside a degree): the counted light is relative (unknown SPA
    efficiency) but the KD is read on the radioligand concentration axis, absolute as in filtration, with the same reference range; NSB wells are standard
    practice; the SPA checks often unstated (bead-only, non-proximity, quench, settling) mostly blur or shift a constant rather than invent one. Consistent
    with radioligand and the KD reasoning: 0.9 kept, no change needed.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree
(the continuous comparisons above); direct leaves it unchanged. Support never changes a status. variance_correspondence takes the weakest support of
the spread (and of the replicate count for a standard deviation).
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_spa_converted_v1'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('nonspecific_binding', 'nonspecific_excess', 'nonproximity_signal', 'bead_only_control', 'radioligand_quality'), 'binding_regime': ('equilibrium', 'radioligand_range', 'competition_radioligand_level', 'homogeneous_format'), 'binding_parameter_definition': ('fit_model', 'nonlinear_fit', 'hill_slope', 'cheng_prusoff'), 'calibration_applicability': ('ligand_depletion', 'nonspecific_fraction', 'quench_interference', 'bead_settling'), 'sampling_basis': ('replicates',)}
MAX_PERCENT_BOUND = 10.0  # EXPERT_REVIEW: largest percent of the added radioligand that may be bound for full agreement; above about 10 percent the free radioligand is no longer the added concentration (ligand depletion) and KD and IC50 are biased (the usual rule of the receptor binding literature; in an SPA the free radioligand cannot be measured because nothing is separated).
PERCENT_BOUND_ZERO_AGREEMENT = 30.0  # EXPERT_REVIEW: percent bound from which the sheet takes depletion as disagreeing (conflicting); with 30 percent bound the free radioligand is only 70 percent of the added one and the constants are off by more than the fit can correct; in between the degree falls linearly.
MAX_NONSPECIFIC_FRACTION = 50.0  # EXPERT_REVIEW: largest non-specific binding, as a percent of the total binding at the highest radioligand concentration, for full agreement; above half the specific signal is a small difference of two large numbers and the fit is not reliable.
NONSPECIFIC_FRACTION_ZERO_AGREEMENT = 80.0  # EXPERT_REVIEW: non-specific percent from which the sheet takes the specific signal as lost (conflicting); at 80 percent the specific binding is a fifth of the total and cannot be told from the noise of the two large numbers.
MAX_BEAD_ONLY_FRACTION = 20.0  # EXPERT_REVIEW: largest signal of the control without the captured target (beads and radioligand only), as a percent of the total signal, for full agreement; the radioligand can bind the bead itself, and above about a fifth the bead background is a large part of the counted light and is not removed by the non-specific binding correction alone.
BEAD_ONLY_ZERO_AGREEMENT = 50.0  # EXPERT_REVIEW: bead-only percent from which the sheet takes the signal as mostly bead background (conflicting); at half of the total the counted light is mainly not the captured target.
MIN_NONSPECIFIC_EXCESS = 100.0  # EXPERT_REVIEW: smallest excess of the unlabelled ligand over its Kd to define non-specific binding for full agreement (usual 100 to 1000 times); at 100 times the Kd about 99 percent of the specific sites are occupied.
NONSPECIFIC_EXCESS_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: excess (fold over the Kd) at or below which the sheet takes non-specific binding as not defined (conflicting); at 10 times the Kd about 91 percent of the sites are occupied, below it the remaining specific binding is counted as non-specific. In between the degree is linear in the occupancy x / (1 + x), i.e. in the specific binding left in the NSB wells, 1 / (1 + x).
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest radioligand concentrations of a saturation series (usual series have eight to twelve; KD and Bmax are not both defined with fewer). The full-credit count: below it the credit falls linearly in the residual degrees of freedom towards SATURATION_FIT_PARAMETERS, never conflicting.
SATURATION_FIT_PARAMETERS = 2  # EXPERT_REVIEW: the free parameters of the one-site saturation hyperbola, KD and Bmax. The non-proximity signal of an SPA is non-specific binding like the filter background of a filtration assay: it is read from the paired wells with excess unlabelled ligand (a global fit of total and non-specific wells has 2n points and four parameters, 2 (n - 2) residual degrees of freedom), so it does not raise the end. With this many concentrations or fewer no point checks the hyperbola: degree 0, supported, never conflicting (a short series is weaker evidence, not evidence against).
LOW_FACTOR = 0.25  # EXPERT_REVIEW: the lowest radioligand concentration must be at most this multiple of the KD for full agreement (about 20 percent occupancy; the usual design starts near 0.1 times the KD).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: lowest concentration (multiple of the KD) from which the sheet takes the low end of the curve as not sampled (conflicting); at the KD the occupancy is already half. In between the degree is linear in the occupancy at the lowest concentration (20 to 50 percent).
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest radioligand concentration must be at least this multiple of the KD for full agreement (about 83 percent occupancy, so that Bmax is defined by data; the usual design reaches 10 times the KD).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: highest concentration (multiple of the KD) at or below which the sheet takes the plateau as not reached (conflicting); at the KD the occupancy is only half and Bmax is not defined by data. In between the degree is linear in the occupancy at the highest concentration (50 to 83 percent).
MAX_RADIOLIGAND_OVER_KD = 1.0  # EXPERT_REVIEW: the single radioligand concentration of a competition must be at most this multiple of its KD for full agreement (at or below the KD the IC50 is within a factor of two of the Ki and the depletion is small).
RADIOLIGAND_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: radioligand over KD from which the sheet takes the IC50 as no longer near the Ki (conflicting); at ten times the KD the IC50 is eleven times the Ki. In between the degree is linear in the radioligand occupancy r / (1 + r), the share of an error in the KD or the radioligand concentration that passes into the Ki (50 percent at 1x, 91 percent at 10x).
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: the absolute floor (minutes) of the incubation: the beads need time to settle and capture the target and the plate to be mixed (usual SPA protocols incubate 1 to 4 hours at room temperature, longer at low temperature). Now only the proportional d_floor = min(1, t / 30), never conflicting by itself (was a conflicting step below 30 min).
KON_FAST_PER_M_S = 1.0e8  # EXPERT_REVIEW, owner to confirm (from memory: Schreiber, Haran and Zhou 2009 Chem Rev 109:839; Hulme and Trevethick 2010 Br J Pharmacol 161:1219, who give radioligand association rate constants from about 1e5 to 1e8 per M per s): the fastest plausible association rate constant of a small-molecule radioligand with its captured target. With it T_FAST is the incubation that covers five half-lives even for the fastest plausible association; at or below it the incubation is conflicting (the zero end of the curve). New in this assay: the old rule had a time only, no KD scale.
KON_SLOW_PER_M_S = 1.0e5  # EXPERT_REVIEW, owner to confirm (from memory: same sources; Schreiber 2009 gives about 1e5 to 1e6 per M per s for association without electrostatic steering, slower when a conformational change gates binding): a slow association rate constant of a radioligand with a purified or membrane target on a bead. With it T_SLOW = T_FAST * KON_FAST / KON_SLOW (1000 times T_FAST, three decades) is the incubation that covers five half-lives for nearly all plausible rates; from it the incubation counts fully.
# T_FAST and T_SLOW use t_eq = EQUILIBRIUM_HALF_TIMES * ln 2 / (kon * KD) (EXPERT_REVIEW, owner to confirm): kobs = kon * ([L] + KD) is slowest at the lowest radioligand concentration of a series, where it is about koff = kon * KD.
EQUILIBRIUM_HALF_TIMES = 5.0  # EXPERT_REVIEW: incubation, in half-times of the paper's own association time course, for full agreement; five half-lives is the usual rule for equilibrium (Hulme and Trevethick 2010), at which 1 - 2^-5 = 97 percent of the plateau binding is reached. Below it the degree is the fraction of the plateau reached, (1 - 2^-r) / (1 - 2^-5): half the plateau at one half-time gives 0.52. Relative to the paper's own kinetics, never conflicting (a stated short incubation is partial credit, not opposition); it has no zero end of its own because the fraction reached falls to 0 as the incubation does.
MIN_HILL = 0.8  # EXPERT_REVIEW: lowest Hill slope that still shows one site obeying mass action for full agreement; a shallower curve shows several sites or negative cooperativity (usual limits 0.8 to 1.2).
MAX_HILL = 1.2  # EXPERT_REVIEW: highest Hill slope that still shows one site obeying mass action for full agreement; a steeper curve shows cooperativity or no equilibrium.
HILL_LOW_ZERO_AGREEMENT = 0.5  # EXPERT_REVIEW: Hill slope at or below which the sheet takes the curve as not one site (conflicting); half the steepness of mass action is a clear mixture of sites or strong negative cooperativity.
HILL_HIGH_ZERO_AGREEMENT = 2.0  # EXPERT_REVIEW: Hill slope at or above which the sheet takes the curve as not one site (conflicting); twice the steepness of mass action is clear cooperativity or no equilibrium.
CHENG_PRUSOFF_FACTOR = 1.5  # EXPERT_REVIEW: allowed fold gap between a reported Ki and the Ki calculated from the reported IC50, radioligand concentration and KD by the Cheng-Prusoff equation for full agreement (rounding and fit differences are within a factor of 1.5; a larger gap shows another equation or another KD was used).
CHENG_PRUSOFF_ZERO_AGREEMENT_FACTOR = 5.0  # EXPERT_REVIEW: fold gap from which the sheet takes the reported Ki as not the Cheng-Prusoff one (conflicting); a fivefold gap is not rounding or fit difference but another equation or another KD.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); wells of one experiment do not count. Full credit from it; below it (owner rule: replicates mean precision in every assay) the degree is sqrt(n / MIN_REPLICATES), the standard error of the mean constant over n independent experiments (fresh bead suspension, capture, bead lot, counter) relative to that at the researched count: one 0.58, two 0.82; never conflicting for a stated count.
SD_MIN_EXPERIMENTS = 2  # not a quality threshold: a between-experiment standard deviation needs at least two independent experiments, so an SD stated with fewer (a spread of wells) is not turned into a variance of the estimate.
NULL_REASONS = {'recovery': 'an_spa_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_spa_nonspecific_binding_is_not_an_attribution_fraction', 'total_signal': 'an_spa_nonspecific_binding_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_spa_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_spa_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _at_most(value, full, zero, refs):
    """Supported with degree 1.0 up to the full-agreement limit, falling linearly to 0 at the zero-agreement limit; conflicting from there on (a larger value is worse)."""
    if value >= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (zero - value) / (zero - full)))


def _at_least(value, full, zero, refs):
    """The same for a value that must not fall below its limit (a smaller value is worse)."""
    if value <= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (value - zero) / (full - zero)))


def _occupancy(ratio):
    """The fraction of sites a ligand at this multiple of its dissociation constant occupies at equilibrium (mass action)."""
    return ratio / (1.0 + ratio)


def _by_occupancy(ratio, full, zero, refs):
    """A concentration over its constant judged in its occupancy: 1.0 at or past the full-agreement end, falling linearly in ratio / (1 + ratio) to 0 at the
    zero-agreement end, conflicting at or beyond it (either orientation). Equal degree steps are equal steps of the binding curve, steepest near the constant."""
    share = (_occupancy(ratio) - _occupancy(zero)) / (_occupancy(full) - _occupancy(zero))
    if share <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, share))


def _weakest(first, second, refs):
    """Two continuous comparisons that both must hold: conflicting if either is, else the smaller degree."""
    if 'conflicting' in (first['status'], second['status']):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(first['degree'], second['degree']))


def _judge_ligand_depletion(native):
    return _at_most(native['percent_bound'], MAX_PERCENT_BOUND, PERCENT_BOUND_ZERO_AGREEMENT, native['percent_bound_refs'])


def _judge_nonspecific_fraction(native):
    return _at_most(native['nonspecific_fraction_percent'], MAX_NONSPECIFIC_FRACTION, NONSPECIFIC_FRACTION_ZERO_AGREEMENT, native['nonspecific_fraction_refs'])


def _judge_nonspecific_excess(native):
    # linear in the occupancy of the specific sites by the unlabelled ligand: the specific binding left in the NSB wells is 1 / (1 + x), so each fold of excess
    # matters most near the zero end (see the docstring block); the excess is the grader's, over the radioligand KD
    return _by_occupancy(native['nonspecific_excess_ratio'], MIN_NONSPECIFIC_EXCESS, NONSPECIFIC_EXCESS_ZERO_AGREEMENT, native['nonspecific_excess_refs'])


def _judge_bead_only(native):
    return _at_most(native['bead_only_percent'], MAX_BEAD_ONLY_FRACTION, BEAD_ONLY_ZERO_AGREEMENT, native['bead_only_refs'])


def _judge_equilibrium(native):
    # No association half-time stated, the paper's own equilibrium fact unknown: the incubation against the KD scale (owner's standing rule: gradual).
    # t_eq(kon) = five half-lives of the slowest relaxation, EQUILIBRIUM_HALF_TIMES * ln 2 / (kon * KD), in minutes; T_FAST for the fastest plausible kon, T_SLOW
    # for a slow one. d_kon = log(t / T_FAST) / log(T_SLOW / T_FAST) clipped to 0..1: the share, on the log scale, of the plausible association rates for which the
    # incubation covers five half-lives. t <= T_FAST: not even the fastest plausible association has equilibrated (conflicting, the zero end). d_floor = min(1, t /
    # MIN_INCUBATION_MIN): mixing, settling and capture on the beads, proportional and never conflicting by itself. No KD: no scale, unknown (also below the floor).
    kd_nM = native['kd_nM']
    if kd_nM is None:
        return _verdict('unknown', [])
    minutes = native['incubation_min']
    t_fast = EQUILIBRIUM_HALF_TIMES * math.log(2.0) / (KON_FAST_PER_M_S * kd_nM * 1e-9) / 60.0
    d_kon = max(0.0, min(1.0, math.log(minutes / t_fast) / math.log(KON_FAST_PER_M_S / KON_SLOW_PER_M_S)))
    refs = list(dict.fromkeys([*native['incubation_refs'], *native['kd_refs']]))
    if d_kon <= 0.0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(min(1.0, minutes / MIN_INCUBATION_MIN), d_kon))


def _judge_equilibrium_half_times(native):
    # the incubation relative to the paper's own association half-time: the fraction of the plateau a first-order approach has reached after r half-times is
    # 1 - 2^-r, over the fraction at the researched five (see the docstring block); the stated kinetics are the paper's own evidence, so this is supported with a degree
    ratio = native['incubation_over_half_time']
    return _verdict('supported', native['half_time_refs'], min(1.0, (1.0 - 2.0 ** -ratio) / (1.0 - 2.0 ** -EQUILIBRIUM_HALF_TIMES)))


def _judge_radioligand_range(native):
    # The count: max(0, (n - 2) / (8 - 2)), the residual degrees of freedom of the saturation fit over those of the researched eight-point series; each
    # concentration beyond KD and Bmax is one more independent well (its own counting error and bead scatter) that the hyperbola must pass through. A short
    # series lowers the degree and never conflicts. The span: the occupancy at the lowest and at the highest concentration (see _by_occupancy). No listed or
    # stated count: the span alone is judged; a count with no readable span is unknown.
    count = native['concentration_count']
    if native['concentration_low_over_kd'] is None:
        return _verdict('unknown', [])      # the span cannot be read; a count alone never supports the range
    count_degree = 1.0 if count is None else max(0.0, min(1.0, (count - SATURATION_FIT_PARAMETERS) / (MIN_CONCENTRATIONS - SATURATION_FIT_PARAMETERS)))
    refs = native['concentration_span_refs']
    if count_degree < 1.0:
        refs = list(dict.fromkeys([*refs, *native['concentration_count_refs']]))      # a count below full credit is part of the judgement
    span = _weakest(_by_occupancy(native['concentration_low_over_kd'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, refs), _by_occupancy(native['concentration_high_over_kd'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, refs), refs)
    if span['status'] == 'conflicting':
        return _verdict('conflicting', native['concentration_span_refs'])
    return _verdict('supported', refs, min(span['degree'], count_degree))


def _judge_radioligand_level(native):
    # linear in the radioligand occupancy r / (1 + r): the share of an error in the KD or the radioligand concentration that the Cheng-Prusoff correction
    # passes into the Ki, which rises fastest just above the KD (see the docstring block)
    return _by_occupancy(native['radioligand_over_kd'], MAX_RADIOLIGAND_OVER_KD, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT, native['radioligand_over_kd_refs'])


def _judge_hill_slope(native):
    slope, refs = native['hill_slope'], native['hill_slope_refs']
    if slope < MIN_HILL:
        return _at_least(slope, MIN_HILL, HILL_LOW_ZERO_AGREEMENT, refs)
    if slope > MAX_HILL:
        return _at_most(slope, MAX_HILL, HILL_HIGH_ZERO_AGREEMENT, refs)
    return _verdict('supported', refs, 1.0)


def _judge_cheng_prusoff(native):
    ki, calculated = native['ki_nM'], native['calculated_ki_nM']
    return _at_most(max(ki, calculated) / min(ki, calculated), CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_AGREEMENT_FACTOR, native['cheng_prusoff_refs'])


def _judge_replicates(native):
    # min(1, sqrt(n / MIN_REPLICATES)): an independent SPA experiment is a fresh bead suspension with a fresh capture of the target, and the capture efficiency,
    # bead lot and counter efficiency change between experiments; the mean constant over n of them has a standard error ~ 1 / sqrt(n), so the degree is its
    # precision relative to the researched count. A stated count never conflicts (a stated 'no' independence is the grader's conflicting).
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])      # independence not stated: the count may be wells of one experiment
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('ligand_depletion', 'percent_bound_recorded_for_the_sheet'): _judge_ligand_depletion, ('nonspecific_fraction', 'nonspecific_fraction_recorded_for_the_sheet'): _judge_nonspecific_fraction,
          ('nonspecific_excess', 'excess_recorded_for_the_sheet'): _judge_nonspecific_excess, ('bead_only_control', 'bead_only_percent_recorded_for_the_sheet'): _judge_bead_only,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium, ('equilibrium', 'incubation_over_half_time_recorded_for_the_sheet'): _judge_equilibrium_half_times, ('radioligand_range', 'concentration_series_recorded_for_the_sheet'): _judge_radioligand_range,
          ('competition_radioligand_level', 'radioligand_over_kd_recorded_for_the_sheet'): _judge_radioligand_level, ('hill_slope', 'hill_slope_recorded_for_the_sheet'): _judge_hill_slope,
          ('cheng_prusoff', 'cheng_prusoff_gap_recorded_for_the_sheet'): _judge_cheng_prusoff, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
        if _criterion(graded, 'replicates')['status'] != 'supported' or count['value'] < SD_MIN_EXPERIMENTS:
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_spa(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if native['ic50_nM'] is not None else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'spa_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'spa_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
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
        variance_fields = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['radioligand_preparation_ref'], 'immobilized_preparation_ref': preparations['receptor_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'spa', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
    if quantities['effect'] is None:      # no effect operand: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact binding_detected
    return converted
