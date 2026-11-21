"""Split-reporter converter: turns the split-reporter grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_split_reporter.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a split reporter
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (from a titration or the kinetics of a reversible split reporter such as NanoBiT). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key split_reporter_kd, so that it is labelled as derived from the split reporter and is not a KD of the
                    purified proteins). The caveats of the method (a KD needs titration concentrations on both sides of it; an irreversible reporter has no equilibrium) are not
                    changed in the number, they are judged by the criteria (titration_series, titration_range, saturable_titration, reversible_reporter) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no KD (a signal above the controls is shown). Then, exactly as the pull-down, EMSA, SEC, dialysis and AUC converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the signal over the
background nor the signal over the negative control is put into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'signal_over_negative_control'}):
  statement                    'interaction_detected' (a signal above the controls is stated), 'interaction_not_detected' (no such signal is stated) or 'interaction_not_stated'
  support_refs                 the spans of the fact that states it (empty when not stated)
  signal_over_negative_control the stated fold of the signal over the negative control, or None
The scoring reads only 'statement' and 'support_refs' of 'qualitative_effect': the statement fixes the direction
(literature_direction.py) and the support refs join the row (literature_row.py).

Criteria mapping (split-reporter criteria -> sheet criteria), declared in CRITERIA_MAP
--------------------------------------------------------------------------------------
binding_controls              fragment_alone_control + unrelated_pair_control + binding_mutant_control + positive_control (the controls that show the signal is the two partners
                              bringing the fragments together and not the fragments alone, a nonspecific pair, or a dead assay)
binding_regime                fusion_orientations + saturable_titration + titration_series + titration_range + reversible_reporter (the signal is seen in several orientations, is
                              saturable, is followed over concentrations on both sides of the KD, and a reversible reporter reports an equilibrium)
binding_parameter_definition  interaction_observed + signal_to_background + negative_control_ratio (what the response is: a reconstituted signal, over the background and over the negative control)
calibration_applicability     expression_verified + background_correction (the signal is read against the expression of the fusions and a subtracted background)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison is supported with a degree of 1.0 up to its full-agreement limit, the degree falling
to 0 at its zero-agreement limit linearly on the criterion's own scale (see the range review below), and conflicting (no degree) at or beyond that limit:
signal_to_background (ratio at least SIGNAL_TO_BACKGROUND_FULL_AGREEMENT, none up to SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT; linear in log fold),
negative_control_ratio (at least NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT, none up to NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT; linear in log fold) and titration_range (the lowest
concentration over the KD at most LOW_OVER_KD_FULL_AGREEMENT, none from LOW_OVER_KD_ZERO_AGREEMENT; the highest over the KD at least HIGH_OVER_KD_FULL_AGREEMENT, none up to
HIGH_OVER_KD_ZERO_AGREEMENT; both linear in the 1:1 occupancy r / (1 + r); the weaker of the two decides; the low end is judged only when the series has a lowest
concentration below its highest, as in SPR: one concentration is a short series, judged by titration_series, not a badly placed one).
OWNER RULES (2026-11-21, researched values made gradual; a short count is weaker evidence, never conflicting): the count minimums are no longer pass/fail. Each researched
minimum is kept as the full-credit count, and below it the degree falls by the count's own reasoned shape, supported, never conflicting: fusion_orientations min(1, n /
MIN_ORIENTATIONS) (each geometry tested is one check that the signal does not depend on one fusion geometry); titration_series linear from no credit at
CONCENTRATIONS_ZERO_AGREEMENT (the two parameters of the background-corrected one-site isotherm, no residual) to full at MIN_CONCENTRATIONS; replicates (independence yes)
min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean over n independent experiments (independence not stated: unknown; stated no: the grader's conflicting). A sheet
criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it
per result). No unknown weight enters any degree: the assay's unknown weights (0.65; binding_controls 0.55, binding_regime 0.60) are the contract's, for unstated criteria only.

Range review (A105_EXPERIMENT_SOP step 3; 2026-11-21). Q1 what it protects against; Q2 general practice or lab/instrument-specific; Q3 absolute or relative scale, and
whether the grader has the fact; Q4 how badly a wrong value misleads and whether the shape fits; Q5 consistency with the other binding assays. References: Hu, Chinenov &
Kerppola 2002 Mol Cell 9:789; Kerppola 2006 Nat Protoc 1:1278; Kerppola 2008 Annu Rev Biophys 37:465; Kodama & Hu 2012 BioTechniques 53:285; Horstman et al. 2014 Plant
Physiol 164:1735 (BiFC cautions); Dixon et al. 2016 ACS Chem Biol 11:400 (NanoBiT); Pollard 2010 Mol Biol Cell 21:4061; Jarmoskaite et al. 2020 eLife 9:e57264;
Myszka 1999 J Mol Recognit 12:279.
  SIGNAL_TO_BACKGROUND 10 / 2. Q1 a reconstituted signal that cannot be told from the background (empty vectors, untransfected cells, substrate alone): no reconstitution was
    actually seen. Q2 general but reporter-dependent: a split NanoLuc gives tens to thousands of fold (Dixon et al. 2016), a split fluorescent protein a few fold to ten because of
    fragment self-assembly and autofluorescence (Kerppola 2008; Kodama & Hu 2012); 10 is the boundary between the two, 2 about the scatter of a transfected-cell readout. Q3 already
    relative to the paper's own background; the better scale is the signal over the background's spread (its SD or a Z'), which the grader does not record. GRADER GAP CONSIDERED AND DECLINED (2026-11-21): a paper paragraph almost never states the SD of the background or a Z' for a split-reporter result (it is a screening statistic), so the fact would be unavailable nearly always while adding a new researched cut (Z' 0.5, Zhang et al. 1999) and a second ratio to judge; the replicate count and independence already carry the run-to-run noise. The
    reporter_system IS in the grader facts, so a per-reporter full value (lower for a split fluorescent protein) is possible, but no researched per-reporter value is in hand: kept
    single, an owner/expert question. Q4 a fold is multiplicative (transfection and expression variation scale the signal), so equal ratios should cost the same; the committed
    linear-in-fold ramp gave 2 -> 4 fold (a doubling, clearly visible) only 0.25 and 9 -> 10 fold as much as 2 -> 3. CHANGED: linear -> linear in log fold, values kept (S/B 3:
    0.125 -> 0.25; 4: 0.25 -> 0.43; 6: 0.50 -> 0.68). Q5 AlphaScreen's signal window made the same change (log, 10 / 1); the Y2H reporter fold (10 / 2), the PLA puncta fold
    (3 / 1) and the FRET window fold (2 / 1) hold the old linear shape (flagged for them, not changed here).
  NEGATIVE_CONTROL_RATIO 5 / 1.5. Q1 the main false positive of the method: fragment self-assembly or crowding at high expression gives a signal for any pair, so only the ratio
    to a non-interacting (or binding-mutant) pair at matched expression shows specificity (Kerppola 2006, 2008; Horstman et al. 2014). Q2 the comparison is general practice;
    the exact 5 / 1.5 is a judgement (expression differences between constructs alone give about 1.5 fold). Q3 already relative to the paper's own control pair; it should be at
    matched expression, and the grader records only whether expression was verified, not the expression ratio of the test and control fusions, nor which control (fragment alone,
    unrelated pair, binding mutant) the ratio is over. GRADER GAP, PART ADDED (2026-11-21): the fact expression_matched_to_control (a paper says whether the fusions were at comparable levels, a number it rarely gives); stated no is the paper showing the ratio can come from expression alone: conflicting (owner rule 5, member of negative_control_ratio); stated yes or not stated changes no degree (unknown is never opposition). The expression RATIO is not collected (rarely stated, and a graded scale for it would be a new unreasoned number), and neither is which control the ratio is over (the three controls have their own facts, and a different credit per control kind has no researched value). Q4 multiplicative like the signal-to-background, and the low end matters most (1.5 -> 3 fold is the difference
    between no specificity and a clear one): the linear ramp gave 3 fold 0.43. CHANGED: linear -> linear in log fold, values kept (2 fold: 0.14 -> 0.24; 3 fold: 0.43 -> 0.58;
    half credit at 2.7 fold instead of 3.25). The conflicting zero end stays: a signal within expression noise of the paper's own negative pair is the paper showing no
    specificity (owner rule 5). Q5 the same as PLA's fold over its control and the pull-down's enrichment over its empty-bait control (a signal against the paper's own control).
  MIN_ORIENTATIONS 2, min(1, n / 2). Q1 a result that depends on one fusion geometry (a steric block giving a false negative, a fusion position forcing proximity giving a false
    positive). Q2 testing several, ideally all eight, N/C combinations is general practice (Kerppola 2006; Dixon et al. 2016; the NanoBiT protocol); the eight are a search for
    a working geometry, the evidence is a signal in more than one, so 2 is the evidential minimum. Q3 absolute count. Q4 if the full value should be higher, a two-orientation result
    is over-credited mildly: the dominant false positive (self-assembly) is judged by the controls, not here; each geometry one equal share is the reason for linear. KEPT. GRADER GAP ADDED
    (2026-11-21): the count of orientations that gave a signal (orientation_pairs_positive) is now collected and is the evidence, judged by the same min(1, n / MIN_ORIENTATIONS); with
    no such count, a stated 'only one orientation' (signal_in_several_orientations no) is one positive orientation, half credit; with neither, the number tested as before. GRADER RULE
    CHANGED: a stated no for signal_in_several_orientations was conflicting although a real pair often signals in only some geometries (Kerppola 2006; Dixon et al. 2016); it is now
    the same partial credit as one geometry (a short count, never conflicting, rule 2). Q5 a count: partial credit, never conflicting, as in every assay.
  MIN_CONCENTRATIONS 3 -> 5, CONCENTRATIONS_ZERO_AGREEMENT 1 -> 2. Q1 an apparent KD fitted to too few concentrations to show that the signal follows a saturable one-site
    curve. Q2 general practice is a series spanning the KD with enough points to test the hyperbola's shape (Pollard 2010; Jarmoskaite et al. 2020); five is the usual count for an
    isotherm (Myszka 1999, used by SPR); the committed 3 was a lab-level judgement that confused defining a curve with testing it. Q3 absolute (a count). Q4 with the background
    subtracted (background_correction) the isotherm has two free parameters (KD and the plateau): three points leave one residual and cannot tell a hyperbola from a straight
    line plus noise, or a cooperative curve, so the old full credit at three misled about a KD that can be several fold off. Each point beyond the two parameters adds one equal
    residual that tests the shape, so linear in (n - 2) is right. MISTAKE DECLARED: the committed values gave three points full credit. CHANGED: 3 -> 5 full, 1 -> 2 zero (3 points:
    1.0 -> 0.33; 4: 1.0 -> 0.67; 2: 0.5 -> 0, still supported, never conflicting). Q5 the same as the SPR steady-state isotherm (5 / 2); FP (8 / 3) fits a free baseline.
  LOW_OVER_KD 0.2 / 1.0, HIGH_OVER_KD 5 / 1.0. Q1 a series that does not bracket the KD, so the apparent KD is extrapolated (no plateau: KD and the maximal signal trade off; no low
    end: the curvature is unseen). Q2 general: about 0.1 to 10 x KD with a factor of 2 slack (Pollard 2010; Jarmoskaite et al. 2020). Q3 relative to the paper's own apparent KD,
    which the grader has: right. A second scale the grader lacks is the concentration of the constant (non-titrated) fusion partner: well above the KD the titration is
    stoichiometric and the apparent KD only an upper bound (as FP's tracer concentration) GRADER GAP ADDED (2026-11-21): fixed_partner_concentration is now collected and judged on the depletion bias 1 + 0.5 x fixed / KD, linear in its log between
    FIXED_PARTNER_MAX_OVER_KD 1 (full) and FIXED_PARTNER_ZERO_AGREEMENT_OVER_KD 10 (conflicting: the apparent KD is only an upper bound), the same researched ends and shape as the FP tracer
    (Rossi & Taylor 2011; Jarmoskaite et al. 2020); not stated: not judged (unknown is never opposition); the weakest of the range ends and the constant partner decides. Q4 what the ends define is the share of the curve covered, r / (1 + r):
    0.2 and 5 are mirror images (1/6 and 5/6), but the linear-in-r ramps made the low side lenient (0.6 x: 0.50) and the high side strict (3 x: 0.50). CHANGED: both linear in
    occupancy, values kept (low 0.6 x: 0.50 -> 0.375; low 0.5 x: 0.625 -> 0.50; high 3 x: 0.50 -> 0.75; high 2 x: 0.25 -> 0.50); a single concentration (lowest = highest) is no
    longer judged by the low ramp. Q5 the same values and shape as SPR, GCI and FP.
  MIN_REPLICATES 3, min(1, sqrt(n / 3)). Q1 an apparent KD or a ratio from one transfection or preparation, whose dominant variation (expression level of the two fusions, cell
    state) is unseen. Q2 three independent experiments is general practice (Kodama & Hu 2012 for quantitative BiFC; the same triplicate practice as every binding assay).
    Q3 absolute count. Q4 the precision of the mean, 1 / sqrt(n), the same sd^2 / n this converter uses for the variance. KEPT. Q5 exactly the shared replicate rule; a stated no
    stays the grader's conflicting fact.
Grader gaps (2026-11-21 pass; the first range review listed four): (1) the spread of the background or a Z' (signal_to_background): DECLINED, rarely stated, see above. (2) the expression
ratio of the test and negative-control fusions and which control the ratio is over (negative_control_ratio): the fact expression_matched_to_control ADDED, the ratio and the control kind
declined, see above. (3) the number of orientations that gave a signal, and the conflicting 'no' for signal_in_several_orientations (fusion_orientations): orientation_pairs_positive ADDED, the
'no' rule CHANGED to partial credit. (4) the concentration of the constant fusion partner (titration_range, the KD regime): fixed_partner_concentration ADDED. Not a grader gap, still an owner
question: a per-reporter full-credit value for signal_to_background (lower for a split fluorescent protein).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. variance_correspondence takes
the weakest support of the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is
not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, recovery) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first component,
immobilized_preparation_ref = the second component, surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_split_reporter_converted_v1'
CRITERIA_MAP = {'binding_controls': ('fragment_alone_control', 'unrelated_pair_control', 'binding_mutant_control', 'positive_control'), 'binding_regime': ('fusion_orientations', 'saturable_titration', 'titration_series', 'titration_range', 'reversible_reporter'), 'binding_parameter_definition': ('interaction_observed', 'signal_to_background', 'negative_control_ratio'), 'calibration_applicability': ('expression_verified', 'background_correction'), 'sampling_basis': ('replicates',)}
SIGNAL_TO_BACKGROUND_FULL_AGREEMENT = 10.0  # EXPERT_REVIEW: smallest signal over background taken as a clear signal; a split luciferase (NanoBiT) typically gives tens to thousands of fold over the background, a split fluorescent protein a few fold to ten.
SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT = 2.0  # EXPERT_REVIEW: signal over background at or below which the signal cannot be told from the variation of the background (a twofold change is about the noise of a transfected-cell assay): conflicting; the degree falls linearly in log fold in between (a fold is multiplicative; range review).
NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest signal over the negative control pair taken as specific; five fold clearly exceeds the spread between non-interacting pairs.
NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT = 1.5  # EXPERT_REVIEW: signal over the negative control at or below which the pair cannot be told from a non-interacting pair (expression differences alone give about this much); conflicting; the degree falls linearly in log fold in between (range review).
MIN_ORIENTATIONS = 2  # EXPERT_REVIEW: fewest fusion orientation combinations tested; one orientation can fail by steric block or give a signal by position alone, two or more show that the result does not depend on one geometry. Full agreement from it. Below it (owner rule: a short count is weaker evidence, never conflicting) the degree is min(1, n / MIN_ORIENTATIONS), each geometry tested one equal share of the check: ONE orientation gets half credit, because its signal is a real reconstitution, but whether it depends on that one fusion geometry (steric block of the other termini, proximity forced by the fusion position) is not shown, and that check is exactly what the second geometry adds.
MIN_CONCENTRATIONS = 5  # EXPERT_REVIEW (range review 2026-11-21: was 3): fewest titration concentrations that both define an apparent KD and test that the signal follows a saturable one-site curve (a series spanning the KD, Pollard 2010, Jarmoskaite et al. 2020; five as for an isotherm in SPR, Myszka 1999). Three points fix the two parameters of the background-corrected isotherm with one residual only, which cannot tell a hyperbola from a line plus noise. Full agreement from it.
CONCENTRATIONS_ZERO_AGREEMENT = 2  # EXPERT_REVIEW (range review 2026-11-21: was 1): the two free parameters of the background-corrected one-site isotherm (KD and the plateau; the background is judged by background_correction): two concentrations or fewer leave no residual, so nothing tests the apparent KD (no credit: degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against). Linear in the count up to MIN_CONCENTRATIONS: each point beyond the two parameters is one equal residual that tests the shape (3: one third, 4: two thirds). The same ends as the SPR steady-state isotherm.
LOW_OVER_KD_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest ratio of the lowest titration concentration to the apparent KD at which the series defines the free end of the isotherm (0.1 x KD with a factor of 2 slack; occupancy 1/6).
LOW_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the lowest titration concentration to the KD from which the series does not reach below the KD (occupancy 1/2): conflicting; the degree falls linearly in the 1:1 occupancy r / (1 + r) in between, the share of the curve left unsampled (range review).
HIGH_OVER_KD_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest ratio of the highest titration concentration to the KD at which the series reaches the saturated end of the isotherm (10 x KD with a factor of 2 slack; occupancy 5/6, the mirror image of LOW_OVER_KD_FULL_AGREEMENT).
HIGH_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the highest titration concentration to the KD up to which the series does not reach above the KD (occupancy 1/2): conflicting; the degree falls linearly in the 1:1 occupancy r / (1 + r) in between (range review).
SINGLE_POSITIVE_ORIENTATIONS = 1  # FIXED_BY_DEFINITION (EXPERT_REVIEW: reading): a passage that says the signal was seen in only one orientation (signal_in_several_orientations no) states exactly one orientation with a signal.
FIXED_PARTNER_MAX_OVER_KD = 1.0  # EXPERT_REVIEW (grader gap, 2026-11-21): the constant (non-titrated) partner may be at most this multiple of the apparent KD for the 1:1 hyperbola to give the KD; above it the titration is partly stoichiometric (the titrated partner is depleted by binding) and the apparent KD is raised; the full-agreement limit. The same physics and value as the FP tracer (Rossi & Taylor 2011; Jarmoskaite et al. 2020).
FIXED_PARTNER_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW (grader gap, 2026-11-21): constant partner over KD at or above which the apparent KD is dominated by the constant partner concentration (about 6-fold too high at the midpoint; only an upper bound), conflicting; the degree falls linearly in the log of the depletion bias in between. The same ends as the FP tracer (1 / 10).
FIXED_PARTNER_BOUND_AT_MIDPOINT = 0.5  # FIXED_BY_DEFINITION (EXPERT_REVIEW: derivation): at the midpoint of a 1:1 direct titration half the constant partner is bound, so the titrated partner there is KD + 0.5 x constant partner and the apparent KD is (1 + 0.5 x constant / KD)-fold too high.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days, transfections or preparations); wells of one plate do not count. Full agreement from it. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): the dominant variation of a split-reporter assay is between transfections or preparations (expression level of the two fusions, cell state), and the standard error of the mean over n independent experiments falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the variance); 1 experiment about 0.58, 2 about 0.82; never conflicting for a stated count.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_split_reporter_signal_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_split_reporter_signal_is_not_an_attribution_fraction', 'total_signal': 'a_split_reporter_signal_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_split_reporter_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_split_reporter_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _log_degree(fold, full, zero):
    """_degree on the log scale: a fold is multiplicative, so equal ratios cost the same (range review)."""
    return _degree(math.log(fold), math.log(full), math.log(zero))


def _occupancy(ratio):
    """The 1:1 occupancy r / (1 + r) of a concentration given as r = c / KD: where on the binding curve it sits."""
    return ratio / (1 + ratio)


def _occupancy_degree(ratio, full, zero):
    """_degree on the 1:1 occupancy: the share of the binding curve a titration end covers (range review)."""
    return _degree(_occupancy(ratio), _occupancy(full), _occupancy(zero))


def _graded(refs, *degrees):
    """The verdict of a continuous comparison: conflicting where any degree is None, else supported with the smallest degree."""
    if None in degrees:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(degrees))


def _judge_signal_to_background(native):
    return _graded(native['signal_to_background_refs'], _log_degree(native['signal_to_background'], SIGNAL_TO_BACKGROUND_FULL_AGREEMENT, SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT))


def _judge_negative_control_ratio(native):
    return _graded(native['signal_over_negative_control_refs'], _log_degree(native['signal_over_negative_control'], NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT, NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT))


def _counted(refs, degree):
    """A count's verdict: supported with its degree, never conflicting (a short count is weaker evidence, not evidence against)."""
    return _verdict('supported', refs, min(1.0, max(0.0, degree)))


def _judge_orientations(native):
    # the orientations that gave a signal are the evidence (grader gap): a stated number of them, else a stated 'only one orientation' (one), else the number tested;
    # partial credit below MIN_ORIENTATIONS (one geometry: half, see MIN_ORIENTATIONS), no step, never conflicting (a real pair often signals in only some geometries)
    if native['orientation_pairs_positive'] is not None:
        return _counted(native['orientation_pairs_positive_refs'], native['orientation_pairs_positive'] / MIN_ORIENTATIONS)
    if native['orientation_single']:
        return _counted(native['orientation_single_refs'], SINGLE_POSITIVE_ORIENTATIONS / MIN_ORIENTATIONS)
    return _counted(native['orientation_pairs_refs'], native['orientation_pairs_tested'] / MIN_ORIENTATIONS)


def _judge_concentrations(native):
    # partial credit below MIN_CONCENTRATIONS (one residual per point beyond the isotherm's two parameters; two or fewer: none, see CONCENTRATIONS_ZERO_AGREEMENT), no step, never conflicting
    return _counted(native['concentration_count_refs'], (native['concentration_count'] - CONCENTRATIONS_ZERO_AGREEMENT) / (MIN_CONCENTRATIONS - CONCENTRATIONS_ZERO_AGREEMENT))


def _depletion_bias(fixed_over_kd):
    """The factor by which the constant partner raises the apparent KD at the midpoint of a 1:1 direct titration."""
    return 1.0 + FIXED_PARTNER_BOUND_AT_MIDPOINT * fixed_over_kd


def _judge_range(native):
    # both ends on the 1:1 occupancy; the low end only when the series has one below its highest concentration (one concentration is a short series, judged by titration_series);
    # the constant partner (grader gap) on the log of its depletion bias; the weakest stated part decides
    degrees, refs = [], []
    if native['high_over_kd'] is not None:
        low, high = native['low_over_kd'], native['high_over_kd']
        degrees.append(_occupancy_degree(high, HIGH_OVER_KD_FULL_AGREEMENT, HIGH_OVER_KD_ZERO_AGREEMENT))
        if low < high:
            degrees.append(_occupancy_degree(low, LOW_OVER_KD_FULL_AGREEMENT, LOW_OVER_KD_ZERO_AGREEMENT))
        refs += native['range_refs']
    if native['fixed_over_kd'] is not None:
        degrees.append(_degree(math.log(_depletion_bias(native['fixed_over_kd'])), math.log(_depletion_bias(FIXED_PARTNER_MAX_OVER_KD)), math.log(_depletion_bias(FIXED_PARTNER_ZERO_AGREEMENT_OVER_KD))))
        refs += native['fixed_refs']
    return _graded(list(dict.fromkeys(refs)), *degrees)


def _judge_replicates(native):
    # the precision of the mean over n independent experiments, sqrt(n / MIN_REPLICATES) (see MIN_REPLICATES), no step, never conflicting for a stated count
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _counted(native['replicate_refs'], math.sqrt(native['replicate_count'] / MIN_REPLICATES))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_to_background', 'signal_to_background_recorded_for_the_sheet'): _judge_signal_to_background,
          ('negative_control_ratio', 'negative_control_ratio_recorded_for_the_sheet'): _judge_negative_control_ratio,
          ('fusion_orientations', 'orientation_pairs_recorded_for_the_sheet'): _judge_orientations,
          ('fusion_orientations', 'orientation_positive_recorded_for_the_sheet'): _judge_orientations,
          ('fusion_orientations', 'orientation_single_recorded_for_the_sheet'): _judge_orientations,
          ('titration_series', 'concentration_count_recorded_for_the_sheet'): _judge_concentrations,
          ('titration_range', 'titration_range_recorded_for_the_sheet'): _judge_range,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if native['kd_nM'] is None:
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
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_split_reporter(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'split_reporter_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'split_reporter_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
        variance_fields = ['kd_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['component_a_preparation_ref'], 'immobilized_preparation_ref': preparations['component_b_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'split_reporter', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components}
    # quantitative: the support of the KD operand that is the effect; qualitative: the support of the interaction_detected fact the statement is derived from (None when not stated: no direction)
    converted['direction_field_support'] = max([native['quantities']['kd'].get('support')] if quantitative else native['support']['interaction_observed'], key=SUPPORTS.index, default=None)
    if not quantitative:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'signal_over_negative_control': native['signal_over_negative_control']}
    return converted
