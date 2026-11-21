"""BRET converter: turns the BRET grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_bret.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a BRET
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (a tracer titration, NanoBRET target engagement) or else a Ki (a displacement of a tracer by an unlabelled competitor). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the KD in nM, else the Ki in nM (point operand, measurement key bret_kd or bret_ki). It is an APPARENT constant measured in live cells by BRET, not a constant of the purified proteins; the label is the
                    measurement key, and the caveats of the method are not changed in the number, they are judged by the criteria (saturation, the controls, the titration, the fit) and so reach the sheet as interpretations.
  effect_variance   variance of that constant, nM_squared, only when the source's spread (kd_spread for a KD, ki_spread for a Ki) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has neither a KD nor a Ki (a BRET ratio, a saturation curve and its BRET50). Then, exactly as the pull-down, EMSA, SEC, dialysis and AUC converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: a BRET50 is an acceptor-to-donor ratio, not a concentration, and a BRET ratio is not on the nM scale, so neither is put into the effect. What the
experiment does contribute is carried beside the sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'signal_over_control'}):
  statement           'interaction_detected' (the interaction fact is yes), 'interaction_not_detected' (it is no) or 'interaction_not_stated'
  support_refs        the spans of the fact that states it (empty when not stated)
  signal_over_control the BRET ratio of the pair over that of the negative control, or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (BRET criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              donor_only_control + acceptor_only_control + negative_control + orientation (the controls that show the signal is a specific pair and not the donor's own emission, the acceptor's, random collision or a fusion artefact)
binding_regime                saturation_shown + titration_points + ratio_range + expression_matching + competition + tracer_regime (the signal is followed over acceptor-to-donor ratios on both sides of BRET50 with the expression measured, a tracer is displaced, and for a Ki the tracer is used near or below its own KD)
background_alternatives       bystander_test (the direct test of the alternative explanation, random collision of over-expressed proteins: a hyperbola preferred over a straight line, or BRET constant when the total expression changes; either test is enough)
binding_parameter_definition  interaction_observed + bret50_specificity + signal_over_control (what the response is: a signal above the control and a BRET50 far below that of the control)
calibration_applicability     fit_quality + background_correction (the fit describes the data; the donor-only background is subtracted)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison (a quotient, a coefficient) is supported with a degree of 1.0 up to its full-agreement limit, the degree falling
linearly to 0 at its zero-agreement limit, and conflicting (no degree) at or beyond that limit: bret50_specificity (BRET50 of the negative control over that of the pair at least BRET50_CONTROL_FULL_AGREEMENT, none up to BRET50_CONTROL_ZERO_AGREEMENT),
signal_over_control (at least SIGNAL_FULL_AGREEMENT, none up to SIGNAL_ZERO_AGREEMENT), ratio_range (the lowest ratio over BRET50 at most LOW_OVER_BRET50_FULL_AGREEMENT, none from LOW_OVER_BRET50_ZERO_AGREEMENT; the highest over BRET50 at least
HIGH_OVER_BRET50_FULL_AGREEMENT, none up to HIGH_OVER_BRET50_ZERO_AGREEMENT; both ends linear in the share of the plateau reached, x / (1 + x), not in x; the weaker of the two decides) and fit_quality (R squared at least FIT_R_SQUARED_FULL_AGREEMENT, none up to FIT_R_SQUARED_ZERO_AGREEMENT).
The count minimums are gradual as well (owner rule 2026-11-21: the researched value is kept as the point of full credit, partial credit below it, no step):
titration_points is supported with 1.0 at MIN_TITRATION_POINTS points or more, the degree falling linearly with the residual degrees of freedom of the two-parameter curve to
no credit at TITRATION_POINTS_ZERO_AGREEMENT points or fewer (supported with degree 0, never conflicting: a short series is weaker evidence, not evidence against); replicates
(independence yes) are supported with degree min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean over n independent transfections, never conflicting for a stated count;
independence not stated: unknown; stated no: the grader's conflicting. A sheet criterion that is supported carries the smallest degree of its members that have one (the
sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. variance_correspondence takes
the weakest support of the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is
not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, recovery) are not selected,
and the sheet reports them as not selected.

Range review (A105_EXPERIMENT_SOP step 3; 2026-11-21). Q1 what it protects against; Q2 general practice or lab-specific; Q3 absolute or relative
scale, and whether the grader has the fact; Q4 how badly a wrong value misleads and whether the shape fits; Q5 consistency with the other binding
assays. The failure that matters most in BRET is bystander BRET: over-expressed proteins in one membrane give a signal by random collision that is a
full false "binds" (A105_ASSAY_CALIBRATION_DETAILS, BRET Q4). References: Pfleger & Eidne 2006 Nat Methods 3:165; Pfleger, Seeber & Eidne 2006 Nat
Protoc 1:337; Marullo & Bouvier 2007 Trends Pharmacol Sci 28:362; James et al. 2006 Nat Methods 3:1001; Lan et al. 2015 Sci Rep 5:10166; Felce et al.
2017 Cell Rep 20:2654; Mercier et al. 2002 J Biol Chem 277:44925; Robers et al. 2015 Nat Commun 6:10091; Motulsky & Christopoulos 2004, Fitting
Models to Biological Data (OUP); Vaux, Fidler & Cumming 2012 EMBO Rep 13:291.
  bret50_specificity (control over pair 3 / 1). Q1 a pair whose BRET50 is no lower than that of a non-interacting pair: bystander saturation, not a
    specific complex. Q2 the comparison with a negative pair is general practice (Marullo & Bouvier 2007; Mercier et al. 2002); the 3-fold full end
    is a lab-practice judgement, no guideline gives a number, and bystander pairs can themselves saturate (Lan et al. 2015; Felce et al. 2017). Q3
    already relative to the paper's own control BRET50, which the grader has; the better scale, the separation over the BRET50's run-to-run spread,
    is a grader gap. Q4 BRET50s in arbitrary expression-ratio units scatter about twofold between experiments, so a 1.5-fold separation is within
    the noise; the linear-in-quotient ramp gives it little (0.25) and is convex on the log scale, which is right for a noisy fold. KEPT (values and
    shape). Q5 the same fold-over-own-control idea as the pull-down, PLA and split-reporter negative-pair ramps; conflicting only at a quotient of 1
    (the paper's own control saturates as readily), the zero end of the ramp.
  signal_over_control (3 / 1). Q1 a BRET ratio no larger than the negative control's (no specific energy transfer). Q2 the control comparison is
    general practice (Pfleger, Seeber & Eidne 2006); 3-fold is a lab-practice judgement that fits NET ratios (donor-only background subtracted).
    Q3 relative to the paper's own control, which the grader has; but the record does not say whether the stated ratios are raw or net, nor give
    the donor-only ratio or the ratios' spread (grader gaps). Q4 with raw ratios (donor bleed-through in both) a clear pair can sit at 1.3 to 2-fold
    and scores 0.15 to 0.5: an under-credit, never a false "binds"; the zero end (pair no larger than its control) holds for raw and net alike.
    KEPT until the raw/net fact is collected; linear in the excess over the control, (q - 1) / 2, the net signal relative to the control. Q5 as
    the pull-down (3 / 1) and PLA (3 / 1) folds; conflicting only when the paper's own signal is no larger than its control.
  titration_points (5 -> 8 / 2). Q1 too few acceptor-to-donor ratios to tell a saturating hyperbola from the straight line of bystander BRET. Q2
    published saturation curves usually show 8 to 15 or more ratios pooled over transfections (Mercier et al. 2002; Pfleger, Seeber & Eidne 2006);
    tracer titrations are 8 to 12 points (Robers et al. 2015); 5 was the SPR count, where each concentration is set exactly. Q3 absolute (the curve's
    two parameters are fixed by the model). Q4 each BRET point carries the error of its measured x as well as of its y, and the count guards the
    dominant false positive (bystander), so 5 points were full credit too early. CHANGED: full credit at 8 (5 points 1.0 -> 0.5, 4 points 0.67 ->
    0.33); zero end 2 (the hyperbola's two parameters) and the linear-in-residual-degrees-of-freedom shape kept. Q5 the radioligand and SPA
    hyperbolas use 8 / 2 and EMSA 6 / 2; a short series is partial credit, never conflicting (kept).
  ratio_range (low 0.2 / 1 x BRET50, high 5 / 1 x BRET50). Q1 a series that never shows the rising part or never reaches the plateau, so BRET50 and
    BRETmax are extrapolated and a straight line cannot be excluded. Q2 the plateau must be reached (Marullo & Bouvier 2007; James et al. 2006); 0.2
    and 5 mirror the 0.1x to 10x binding-titration span with a factor of 2 slack (as SPR, FP). Q3 relative to the paper's own BRET50, which the grader
    has. Q4 the old ramps were linear in x, which made a top at 3x BRET50 (75 percent of BRETmax, clearly bent) score 0.5 and a bottom at 0.6x
    (already 37.5 percent) score 0.5 too, although 0.2 and 5 are mirror images on the hyperbola (1/6 and 5/6 of BRETmax). CHANGED: both ends linear
    in the share of the plateau, x / (1 + x) (top 3x 0.50 -> 0.75; top 2x 0.25 -> 0.50; bottom 0.6x 0.50 -> 0.375; bottom 0.5x 0.625 -> 0.50);
    values kept. Q5 the same shape and values as SPR and FP; conflicting only at the zero end (the series never leaves or never passes half of the
    plateau).
  fit_quality (R squared 0.95 / 0.80 -> 0.50). Q1 a curve that does not describe its points, so BRET50 or the KD is poorly determined. Q2 R squared
    limits are a general nonlinear-fit convention, not a BRET guideline, and R squared is a weak test of a nonlinear fit (Motulsky & Christopoulos
    2004); it cannot catch bystander BRET, because a hyperbola with a large BRET50 fits a straight line with a high R squared (the hyperbola-versus-
    line test is a grader gap). Q3 already relative (the share of the points' variance explained). Q4 a poor R squared widens BRET50, it does not
    invent binding, so the ramp should be gentle and conflicting rare; cell BRET points scatter in x and are pooled over transfections, and a scatter
    of about a tenth of BRETmax, usual for such data, gives an R squared near 0.8, which the old zero end made conflicting. CHANGED: zero end 0.50
    (explained variance equal to the residual variance), full end 0.95 kept, linear in R squared (0.875: 0.50 -> 0.83; 0.80: conflicting -> 0.67;
    0.60: conflicting -> 0.22). Owner to confirm. Q5 BLI keeps 0.95 / 0.80 for a purified-protein sensorgram fit with no error in x; BRET differs
    for the reason in Q4.
  replicates (MIN_REPLICATES 3). Q1 a result from one transfection, whose expression levels (and so the acceptor-to-donor ratios) are the largest
    source of variation. Q2 general: three independent experiments is the usual norm (Vaux, Fidler & Cumming 2012; Pfleger, Seeber & Eidne 2006).
    Q3 absolute (a count of independent experiments). Q4 the standard error of a mean falls as 1 / sqrt(n), so 1 experiment 0.58 and 2 experiments
    0.82 are right for precision; a wrong n misleads modestly. KEPT. Q5 consistency rule 1 exactly: sqrt(n / MIN_REPLICATES) with independence yes,
    unknown when not stated, a stated no the grader's conflicting, never conflicting for a stated count.
  GRADER GAPS COLLECTED (second pass, 2026-11-21; the range review listed six; five are now facts or quantities of the record, one is declined).
  (1) raw vs net ratios: signal_over_control now reads the fact background_subtracted and the donor-only ratio (bret_ratio_donor_only). With the stated ratios raw (answer no)
    and the donor-only ratio stated, the quotient is judged NET of that background, (pair - donor) / (control - donor): the donor's bleed-through is in both raw ratios and
    compresses the quotient toward 1 (Pfleger, Seeber & Eidne 2006); a pair no larger than the donor alone is the zero end (conflicting), a control no larger than the donor alone
    leaves the quotient at full credit (its net signal is nil). Raw with no donor-only ratio, or background_subtracted not stated: the quotient as stated (the old under-credit, never a false
    "binds"). Q3 relative to the paper's own donor-only signal, which the grader now collects. Q4 raw 1.3 to 2-fold quotients of a clear pair were scored 0.15 to 0.5; net they are
    judged as the 3-fold net-ratio value was meant. Q5 as the donor-only background of FRET and FP.
  (2, 3) spread of the BRET ratios and of the BRET50s: collected (bret_ratio_pair_spread, bret_ratio_negative_control_spread, bret50_spread, bret50_negative_control_spread; the kind is
    spread_kind). A standard error is used as stated, a standard deviation over n independent experiments (replicates yes) as sd / sqrt(n), a confidence interval is not converted, a
    spread of one only is not used. The difference pair - control (ratios) or ln(control / pair) over its own standard error (BRET50, on the log scale, where the noise is a fold)
    is a z, judged with SIGNIFICANCE_FULL_AGREEMENT / SIGNIFICANCE_ZERO_AGREEMENT in addition to the quotient (the weaker degree decides, owner rule 6: the paper's own noise in addition,
    not instead; the same signal-over-noise idea as MST and FRET). Q1 a quotient that is within the run-to-run scatter of the paper's own numbers. Q2 a gap of about 3 standard errors
    is a clear separation, 1 or less is none (Cumming, Fidler & Vaux 2007 J Cell Biol 177:7). Q3 relative to the paper's own noise. Q4 linear between the ends, conflicting only where
    the difference is no larger than one standard error (the paper's own numbers show no separation). Q5 the unit is the same as MST's signal-to-noise ramp.
  (4) the direct tests against bystander BRET: collected as two facts, hyperbola_preferred_over_linear and bret_constant_across_expression, graded by the new criterion bystander_test
    (supported when either is yes and none is no; conflicting when one is no, which the paper itself states; unknown when neither is stated) and mapped to the sheet criterion
    background_alternatives (it protects exactly against the alternative explanation; it is newly selected for bret, so an unstated test counts the type's unknown weight, 0.70, since
    WEIGHT_UNKNOWN_BY_CRITERION has no entry for it: central, owner to decide). R squared stays as it is (it cannot tell the two apart; the tests can).
  (5) tracer concentration against the tracer's own KD for a Ki: collected (tracer_kd; the existing tracer_concentration), criterion tracer_regime (not applicable without a Ki), mapped to
    binding_regime. Cheng-Prusoff: Ki = IC50 / (1 + [tracer] / KD) (Cheng & Prusoff 1973 Biochem Pharmacol 22:3099); NanoBRET target engagement uses the tracer at or below its apparent KD
    (Robers et al. 2015 Nat Commun 6:10091), so the correction is at most a factor of 2. Judged on the log scale of the quotient, full credit at TRACER_OVER_KD_FULL_AGREEMENT (1), falling
    linearly in log10 to degree 0 at TRACER_OVER_KD_ZERO_AGREEMENT (10, where the IC50 is 11 times the Ki, the competition curve is shifted far to the right and the Ki rests on the
    correction and on the stated tracer KD); supported with degree 0, never conflicting (a high tracer weakens the Ki, it does not contradict the paper). Q3 relative to the tracer's
    own KD, which is the point. Q4 the error of a Ki grows with the correction. Q5 a short or off-range design is partial credit, never conflicting (consistency rule 2).
  (6) expression level as a number: DECLINED. Donor luminescence counts and fluorescence units are instrument- and gain-specific, so no value is comparable between papers; the same
    protection (bystander BRET at high expression) is what the saturation curve, the negative pair and now the two direct tests of (4) address, and expression_matching (measured in the
    same cells) stays a fact. Collecting an uninterpretable number would add a field no judgement can use.
  The unknown weight (WEIGHT_UNKNOWN_BY_TYPE bret 0.70, BC 0.60, BR 0.60 in A105_ASSAY_CALIBRATION_DETAILS) is not used in any curve here: every
  degree describes a stated value; an unstated value is unknown (consistency rule 3).

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the donor-fused protein (component a),
immobilized_preparation_ref = the acceptor-fused protein (component b), surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_bret_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('donor_only_control', 'acceptor_only_control', 'negative_control', 'orientation'), 'binding_regime': ('saturation_shown', 'titration_points', 'ratio_range', 'expression_matching', 'competition', 'tracer_regime'), 'binding_parameter_definition': ('interaction_observed', 'bret50_specificity', 'signal_over_control'), 'calibration_applicability': ('fit_quality', 'background_correction'), 'sampling_basis': ('replicates',), 'background_alternatives': ('bystander_test',)}
BRET50_CONTROL_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest quotient of the BRET50 of the negative control pair over that of the pair under test that the sheet takes as a clear separation of a specific interaction from random collision (the control needs three times the acceptor to reach half of its plateau).
BRET50_CONTROL_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient at or below which the negative control saturates as readily as the pair (no separation): conflicting; in between the degree falls linearly.
SIGNAL_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest quotient of the BRET ratio of the pair over that of the negative control (or of the donor alone) that the sheet takes as a clear signal above the control; a ratio near 1 is background.
SIGNAL_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient at or below which the pair gives no more signal than the control: conflicting; in between the degree falls linearly.
MIN_TITRATION_POINTS = 8  # EXPERT_REVIEW: fewest acceptor-to-donor ratios (or tracer concentrations) for FULL credit for a hyperbola of two parameters (BRET50 and BRETmax) whose curvature and plateau must be told from the straight line of bystander BRET. Was 5 (the SPR count); raised 2026-11-21 (range review): every BRET point carries the error of its MEASURED acceptor-to-donor ratio (fluorescence over luminescence of separately transfected wells) as well as of its BRET ratio, published saturation curves usually show 8 to 15 or more ratios pooled over transfections (e.g. Mercier et al. 2002 JBC 277:44925), NanoBRET tracer titrations are 8 to 12 point dilutions (Robers et al. 2015 Nat Commun 6:10091), and the radioligand and SPA saturation hyperbolas (same two parameters) use 8. Not a cut-off: partial credit below it.
TITRATION_POINTS_ZERO_AGREEMENT = 2  # EXPERT_REVIEW: the number of parameters of that curve (BRET50 and BRETmax; KD and the plateau for a tracer titration). With this many points (or fewer) both a hyperbola and a straight line pass through every point, so the series cannot tell a specific (saturating) interaction from bystander BRET (linear): no credit (degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against); between it and MIN_TITRATION_POINTS the degree rises linearly, one step per residual degree of freedom.
LOW_OVER_BRET50_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest quotient of the lowest ratio over BRET50 at which the series defines the rising part of the curve (1/6 of BRETmax on the hyperbola; the 0.1x to 10x span of a binding titration with a factor of 2 slack, as SPR and FP).
LOW_OVER_BRET50_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient of the lowest ratio over BRET50 from which the series starts above half of the plateau (no rising part): conflicting; in between the degree falls linearly in the share of the plateau reached, x / (1 + x) (1/6 here at full, 1/2 at zero), as SPR and FP.
HIGH_OVER_BRET50_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest quotient of the highest ratio over BRET50 at which the series reaches the plateau (5/6 of BRETmax for a one-site hyperbola, the mirror image of LOW_OVER_BRET50_FULL_AGREEMENT).
HIGH_OVER_BRET50_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient of the highest ratio over BRET50 up to which the series does not pass half of the plateau (BRETmax is not defined by the data): conflicting; in between the degree falls linearly in the share of the plateau reached, x / (1 + x) (5/6 at full, 1/2 at zero).
FIT_R_SQUARED_FULL_AGREEMENT = 0.95  # EXPERT_REVIEW: smallest R squared taken as a fit that describes the data of a saturation or displacement curve (the usual nonlinear-fit convention, as BLI; residual scatter about a fifth of the spread of the points).
FIT_R_SQUARED_ZERO_AGREEMENT = 0.50  # EXPERT_REVIEW: R squared at or below which the sheet takes the fit as not describing the data: the curve explains no more of the variance than it leaves (explained over residual variance 1): conflicting; the degree falls linearly in between. Was 0.80 (the BLI value for a purified-protein sensorgram fit); lowered 2026-11-21 (range review, owner to confirm): a cell BRET saturation curve has scatter in x (the measured acceptor-to-donor ratio) and is pooled over transfections, so a residual scatter of about a tenth of BRETmax, usual for such data, already gives an R squared near 0.8; at 0.80 a valid curve was conflicting.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate transfections, days or passages); wells of one plate do not count. Now the point of FULL credit (no longer a pass/fail cut-off). Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): in cells the largest variation is between transfections (expression levels, acceptor-to-donor ratio), and the standard error of the mean over n independent experiments falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance); 1 experiment about 0.58, 2 about 0.82; never conflicting for a stated count.
SIGNIFICANCE_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: difference of the pair and its negative control over the standard error of that difference (for the BRET50 the same on the log scale) from which the separation is a clear one (a gap of about three standard errors: Cumming, Fidler & Vaux 2007 J Cell Biol 177:7); only used when the paper states both spreads.
SIGNIFICANCE_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: difference over its standard error at or below which the paper's own numbers show no separation (within one standard error, the scatter of a single estimate): conflicting; the degree falls linearly in between.
TRACER_OVER_KD_FULL_AGREEMENT = 1.0  # EXPERT_REVIEW: largest quotient of the tracer concentration over the tracer's own KD for full credit of a Ki: at the KD the Cheng-Prusoff correction 1 + [tracer] / KD is 2 (Cheng & Prusoff 1973 Biochem Pharmacol 22:3099), and NanoBRET target engagement is run with the tracer at or below its apparent KD (Robers et al. 2015 Nat Commun 6:10091).
TRACER_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: quotient at and above which the Ki gets no credit (degree 0, supported, never conflicting): the IC50 is then 11 times the Ki (correction 1 + 10), the displacement curve is shifted far to the right and the Ki rests on the correction and on the stated tracer KD; in between the degree falls linearly in log10 of the quotient (the correction is a power of the concentration ratio).
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_bret_run_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_bret_ratio_is_not_an_attribution_fraction', 'total_signal': 'a_bret_ratio_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_bret_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_bret_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero):
    """1.0 at ``full`` (or beyond it), falling linearly to 0 at ``zero`` (the limits may lie on either side of each other); None at or beyond ``zero``."""
    if (value - zero) * (full - zero) <= 0:
        return None
    return min(1.0, (value - zero) / (full - zero))


def _graded(refs, *degrees):
    """The verdict of a continuous comparison: conflicting where any degree is None, else supported with the smallest degree."""
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _standard_error(spread, native):
    """The standard error of an estimate from its stated spread: a standard error as stated; a standard deviation over n independent experiments (replicates stated independent) as sd / sqrt(n); None for a confidence interval, an unstated kind or count, or no spread."""
    kind = native['spread_kind']
    if spread is None or kind is None:
        return None
    if kind == 'standard_error':
        return spread
    if kind == 'standard_deviation' and native['replicate_independent'] == 'yes':
        return spread / math.sqrt(native['replicate_count'])
    return None


def _judge_bret50(native):
    # the quotient control over pair on its own scale, and (when both spreads are stated) the log quotient over the standard error of the log quotient (a BRET50 scatters as a fold):
    # the weaker degree decides, so the paper's own noise adds to the researched fold and never replaces it
    degrees = [_degree(native['bret50_control_over_pair'], BRET50_CONTROL_FULL_AGREEMENT, BRET50_CONTROL_ZERO_AGREEMENT)]
    pair = native['quantities']['bret50']['value']
    control = native['bret50_control_over_pair'] * pair
    se_pair, se_control = _standard_error(native['bret50_pair_spread'], native), _standard_error(native['bret50_control_spread'], native)
    if se_pair is not None and se_control is not None:
        noise = math.hypot(se_pair / pair, se_control / control)
        degrees.append(_degree(math.log(control / pair) / noise, SIGNIFICANCE_FULL_AGREEMENT, SIGNIFICANCE_ZERO_AGREEMENT))
    return _graded(native['bret50_refs'], *degrees)


def _judge_signal(native):
    # the quotient pair over control; with RAW ratios (background_subtracted answered no) and the donor-only ratio stated, the quotient of the NET signals (the donor's bleed-through is in
    # both raw ratios and compresses the quotient toward 1): a pair no larger than the donor alone has no net signal (the zero end), a control no larger than the donor alone has none
    # to compare with (full credit); then, when both spreads are stated, the difference over its standard error, the weaker degree deciding
    pair, control, donor = native['signal_pair'], native['signal_control'], native['signal_donor_only']
    quotient = native['signal_over_control']
    if native['signal_background_subtracted'] == 'no' and donor is not None:
        quotient = None if pair <= donor else float('inf') if control <= donor else (pair - donor) / (control - donor)
    degrees = [None if quotient is None else _degree(quotient, SIGNAL_FULL_AGREEMENT, SIGNAL_ZERO_AGREEMENT)]
    se_pair, se_control = _standard_error(native['signal_pair_spread'], native), _standard_error(native['signal_control_spread'], native)
    if se_pair is not None and se_control is not None:
        degrees.append(_degree((pair - control) / math.hypot(se_pair, se_control), SIGNIFICANCE_FULL_AGREEMENT, SIGNIFICANCE_ZERO_AGREEMENT))
    return _graded(native['signal_refs'], *degrees)


def _judge_tracer(native):
    # Cheng-Prusoff: the correction 1 + [tracer] / KD grows with the quotient; linear in its logarithm from full credit at TRACER_OVER_KD_FULL_AGREEMENT to degree 0 at
    # TRACER_OVER_KD_ZERO_AGREEMENT; beyond it degree 0, supported, never conflicting (a high tracer weakens the Ki, it does not contradict the paper)
    degree = _degree(math.log10(native['tracer_over_kd']), math.log10(TRACER_OVER_KD_FULL_AGREEMENT), math.log10(TRACER_OVER_KD_ZERO_AGREEMENT))
    return _verdict('supported', native['tracer_refs'], 0.0 if degree is None else degree)


def _judge_points(native):
    # Shape (BRET): the question a BRET titration answers is hyperbola (a specific pair saturates) or straight line (bystander BRET of over-expressed proteins rises linearly).
    # Both have two parameters, so each ratio beyond TITRATION_POINTS_ZERO_AGREEMENT adds one residual degree of freedom that can show the curvature and the plateau; the
    # degree is that number of residual degrees of freedom over the number at MIN_TITRATION_POINTS (linear in the count, full credit at the researched value, no step);
    # at or below TITRATION_POINTS_ZERO_AGREEMENT no credit, never conflicting (a short series is weaker evidence, not evidence against).
    return _verdict('supported', native['titration_refs'], _degree(native['titration_point_count'], MIN_TITRATION_POINTS, TITRATION_POINTS_ZERO_AGREEMENT) or 0.0)


def _plateau_share(ratio):
    """The share of BRETmax reached on the one-site hyperbola at an acceptor-to-donor ratio given as ratio / BRET50: x / (1 + x)."""
    return ratio / (1 + ratio)


def _judge_range(native):
    # Shape: linear in the share of the plateau reached, x / (1 + x), not in x: the two ends are mirror images on the hyperbola (1/6 and 5/6 of BRETmax), so the
    # low and the high end are judged alike (as SPR and FP); conflicting at the zero end (the series never leaves, or never passes, half of the plateau).
    low = _degree(_plateau_share(native['low_over_bret50']), _plateau_share(LOW_OVER_BRET50_FULL_AGREEMENT), _plateau_share(LOW_OVER_BRET50_ZERO_AGREEMENT))
    high = _degree(_plateau_share(native['high_over_bret50']), _plateau_share(HIGH_OVER_BRET50_FULL_AGREEMENT), _plateau_share(HIGH_OVER_BRET50_ZERO_AGREEMENT))
    return _graded(native['range_refs'], low, high)


def _judge_fit(native):
    return _graded(native['fit_refs'], _degree(native['fit_r_squared'], FIT_R_SQUARED_FULL_AGREEMENT, FIT_R_SQUARED_ZERO_AGREEMENT))


def _judge_replicates(native):
    # Shape: min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean over n independent transfections (see MIN_REPLICATES): concave, 1.0 at the researched
    # MIN_REPLICATES, partial credit below it, no step, never conflicting for a stated count.
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # the independence is not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('bret50_specificity', 'bret50_comparison_recorded_for_the_sheet'): _judge_bret50, ('signal_over_control', 'signal_over_control_recorded_for_the_sheet'): _judge_signal,
          ('tracer_regime', 'tracer_regime_recorded_for_the_sheet'): _judge_tracer,
          ('titration_points', 'titration_point_count_recorded_for_the_sheet'): _judge_points, ('ratio_range', 'ratio_range_recorded_for_the_sheet'): _judge_range,
          ('fit_quality', 'fit_r_squared_recorded_for_the_sheet'): _judge_fit, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    constant_name = native['constant_name']
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
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_bret(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = native['constant_name']
    quantitative = constant_name is not None
    if quantitative:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native['constant_nM'], 'nM', 'bret_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'bret_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
    if not quantitative:
        null_components['effect'] = 'qualitative_assay_reports_no_binding_constant'
        null_components['effect_variance'] = 'qualitative_assay_reports_no_binding_constant'
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['component_a_preparation_ref'], 'immobilized_preparation_ref': preparations['component_b_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'bret', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities'][constant_name]['support']      # the support class of the binding-constant operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'signal_over_control': native['signal_over_control']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['interaction_observed'][0]      # the support class of the fact interaction_detected, the one field the statement is derived from
    return converted
