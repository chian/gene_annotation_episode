"""SPR converter: turns the SPR grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to SPR, deterministic. Input: the result of grade_spr.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components), the dependence keys the merger needs, and for every sheet
component that a KD measurement cannot honestly fill, the reason it stays
null.

Quantities filled
-----------------
effect            the SPR KD in nM (point operand), only when the source
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
                  replicates); confidence_interval -> not converted (needs
                  its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery,
attributed signal/total signal, condition test/reference, the assertion and
alternative predictions. They belong to calibration of a different detector,
to a nuisance-condition control SPR does not supply, or to the target's
assertion, not to the experiment. The sheet therefore leaves the cells
recovery_deviation, attributed_fraction, condition_response, both prediction
errors and source_log_evidence_ratio unavailable.

Criteria mapping (SPR criteria -> sheet criteria)
-------------------------------------------------
binding_controls              reference_subtraction + baseline_regeneration
binding_regime                concentration_series + mass_transport +
                              steady_state_vs_kinetic
binding_parameter_definition  fit_model + kinetic_consistency
binding_species               immobilized_activity
calibration_applicability     rmax_consistency
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and
hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement): concentration_series judged
on the number of concentrations (full agreement from MIN_CONCENTRATIONS, rising
linearly from no credit at the zero count of the KD's analysis:
KINETIC_CONCENTRATIONS_ZERO when the paper says the KD is a kinetic fit (or says nothing and kon and koff are
stated), CONCENTRATIONS_ZERO when it says steady-state or there is no sign of a kinetic fit; a short series is weaker evidence, supported with that low degree,
never conflicting), the lowest over the KD (full agreement at most LOW_FACTOR;
judged only when the series has a lower end distinct from its upper end) and
the highest over the KD (full agreement at least HIGH_FACTOR), both ramps
linear in the fractional occupancy c / (c + KD); fit_model judged on
chi-squared over Rmax (full agreement at most CHI2_OVER_RMAX_MAX) and, when the noise is stated, also chi-squared over
noise squared (at most CHI2_OVER_NOISE2_MAX; the weakest counts), unknown for
a 1:1 model whose bivalence is not answered no; rmax_consistency judged on the
observed over theoretical Rmax (full agreement from RMAX_RATIO_MIN to
RMAX_RATIO_MAX); replicates (independence yes) supported with degree
min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean KD over n
independent runs relative to that at MIN_REPLICATES (never conflicting for a
stated count; independence not stated: unknown; stated no: the grader's
conflicting); kinetic_consistency judged on the fold gap between koff/kon and
the KD, either way (full agreement at most KINETIC_FOLD_MAX);
steady_state_vs_kinetic judged on the fold gap (full agreement at most
AGREEMENT_FACTOR); both folds linear in log fold. A continuous comparison of a
value is supported with a degree of 1.0 at its full-agreement limit, falling
linearly on its scale to 0 at its zero-agreement limit (the *_ZERO*
constants), and conflicting (no degree) at or beyond that limit. No researched
value is a pass/fail step: a value just short of its full-agreement limit gets
partial credit. A sheet criterion that is supported carries the smallest degree of its
members that have one (the sheet reads no degree; it travels with the
interpretation and the merger carries it per result).
Quote support: the extraction records for each stated field how well its quote supports it ('direct', 'implied',
'about_something_else'); the grader only keeps it (native 'support', per criterion, from the fields the criterion
reads) and the judgement is made here with literature_quote_support.apply_support. A supported sheet criterion
whose fields include an 'implied' one has its degree multiplied by 0.7, an 'about_something_else' one by 0.3 (the
weakest field counts once; the degree is that factor where there was none; 'direct' changes nothing). Support never
changes a status, and unknown or conflicting criteria carry no degree. The constants (SUPPORT_DEGREE) and their
reasons are in literature_quote_support.py.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no SPR counterpart (measurement_identity, matrix_interference,
background_alternatives, attribution_supported, assertion_relevance,
condition_scope, binding_comparison) are not selected, and the sheet reports
them as not selected.

Range review (2026-11-21, SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative,
Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency with the other binding assays)
-------------------------------------------------------------------------------------------------------------
MIN_CONCENTRATIONS 5, CONCENTRATIONS_ZERO 2, KINETIC_CONCENTRATIONS_ZERO 1 (new).
  Q1 a KD fitted to too few concentrations to show the 1:1 model holds. Q2 general: a series spanning 0.1x to 10x
  KD (Myszka 1999 J Mol Recognit 12:279); five or more is the usual count, the exact 5 is a judgement. Q3 absolute (a count). Q4 a 3- or 4-point kinetic series usually gives a
  KD within about twofold when the fit is clean, so the shape must not punish it like a 2-point isotherm. The old
  zero end (2, the isotherm's two parameters) is right for a steady-state KD and wrong for a kinetic one: one
  sensorgram already fixes kon and koff, so further points are checks (count - 1), not residuals (count - 2).
  CHANGED: zero end 1 when kon and koff are stated, 2 otherwise; linear in both. Q5 no conflict for a short series
  (kept); the kinetic shape is GCI's (same global-fit physics); BLI uses a concave power-2 shape for the same
  physics, which the coordinator may want to align.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 5 -> HIGH_ZERO_FACTOR 1.0.
  Q1 a series that does not bracket the KD, so the KD is extrapolated (no saturation: KD and Rmax trade off; no low
  end: the curvature is unseen). Q2 general: 0.1x to 10x KD (Myszka 1999; Rich & Myszka biosensor surveys), with a
  factor of 2 slack. Q3 relative to the paper's own KD (the grader records both ratios): right. Q4 the old ramps
  were linear in c/KD, which made the low side lenient (0.6x KD scored 0.5) and the high side strict (3x KD scored
  0.5) although 0.2 and 5 are mirror images on the binding curve (occupancy 1/6 and 5/6). CHANGED: both ramps are
  linear in the occupancy c / (c + KD), the share of the curve covered (0.6x -> 0.375, 3x -> 0.75); values kept.
  A single concentration is no longer conflicting through the low ramp (it has no lower end): it is a short series.
  Q5 conflicting only at the zero end of a researched ramp: kept.
CHI2_OVER_RMAX_MAX 0.10 -> CHI2_OVER_RMAX_ZERO 0.30.
  Q1 a fit that does not describe the sensorgrams (heterogeneity, wrong model, drift). Q2 instrument-specific: the
  Biacore evaluation rule of thumb (chi^2 in RU^2 below about a tenth of Rmax in RU); it is not dimensionless, so
  it is lenient for a large Rmax and strict for a small one. Q3 the right scale is chi^2 against the instrument
  noise^2 (a good fit has residuals at the noise); the grader has no noise (GAP below). Q4 at 0.30 the RMS residual
  is only sqrt(3) times that at 0.10, so the ramp is steep in residual terms, but the KD of a poor fit can be off
  by much more than that, so steep is acceptable. KEPT (values and shape) until the noise is recorded.
RMAX_RATIO_MIN 0.3 -> RMAX_RATIO_ZERO_MIN 0.1, RMAX_RATIO_MAX 1.2 -> RMAX_RATIO_ZERO_MAX 2.0.
  Q1 low: a mostly inactive surface (a heterogeneous ligand population can bias the KD); high: non-specific
  binding, aggregation or a wrong stoichiometry, which puts signal into the fit that is not the 1:1 binding. Q2
  general practice (Myszka 1997 Curr Opin Biotechnol 8:50; amine-coupled proteins are often 30 to 100 percent
  active; 1.2 leaves room for refractive-index increment differences between partners). Q3 relative to the
  theoretical Rmax from the paper's own masses, level and stoichiometry: right. Q4 a low ratio mostly loses signal
  (mild), a high ratio corrupts the KD (severe): the high ramp is already the steeper one (1.2 to 2, against 0.3 to
  0.1), linear in the active fraction and in the excess. KEPT.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a KD from one surface, whose chip-to-chip spread is unseen. Q2 general (triplicate practice; inter-lab spread
  in Katsamba et al. 2006 Anal Biochem 352:208). Q3 absolute count. Q4 precision of the mean (1 / sqrt(n)), the same
  sd^2 / n used for the effect variance. Q5 exactly the shared replicate rule. KEPT.
KINETIC_TOLERANCE 0.20 -> KINETIC_ZERO_TOLERANCE 0.8 (relative gap), now KINETIC_FOLD_MAX 1.2 -> KINETIC_FOLD_ZERO 1.8.
  Q1 a reported KD that is not the one the reported rates give (another analysis, another model, a typo). Q2 not
  a guideline value: arithmetic of one fit, separated only by rounding and replicate averaging (about 10 percent).
  Q3 relative to the paper's own KD: right, but a relative gap |r - 1| is asymmetric: the old curve forgave 5-fold
  below the KD and only 1.8-fold above. Q4 an error by a factor matters on the log KD scale. CHANGED: fold either
  way, full at 1.2, zero at 1.8, linear in log fold (koff/kon at half the KD was 0.5, now conflicting). Q5 now the
  same fold scale as steady_state_vs_kinetic, and stricter than it, as it should be (one fit, not two analyses).
AGREEMENT_FACTOR 2 -> AGREEMENT_ZERO_FACTOR 10.
  Q1 steady-state and kinetic KDs that disagree (mass transport, rebinding, heterogeneity, a wrong model). Q2
  general practice to check that the two analyses agree (Myszka 1999; Karlsson & Falt 1997 J Immunol Methods
  200:121); the twofold and tenfold ends are a judgement, not a published number. Q3 relative (fold of the paper's two estimates): right. Q4 the old ramp was linear in
  fold, gentle at small gaps (3-fold 0.875) and steep near tenfold, the reverse of how a factor misleads on the log
  KD scale. CHANGED: linear in log fold (3-fold 0.75, 6-fold 0.32); values kept. Q5 BLI and GCI carry the same
  comparison linear in fold; the coordinator may want them on the log scale too.
Unknown weight: SPR keeps the owner's 0.9 (literature_row_contract.py); no weight is used in any degree here.
Grader gaps of the range review, and what was done (needs a real-model run for the two added fields):
  - the instrument or baseline noise in RU: ADDED as the quantity baseline_noise. chi^2 is a residual variance, so
    chi^2 / noise^2 near 1 is a fit at the noise (CHI2_OVER_NOISE2_MAX 2, CHI2_OVER_NOISE2_ZERO 10, linear in log ratio,
    both EXPERT_REVIEW). Q1 a fit with a systematic misfit; Q2 general (residuals at the noise level, Myszka 1999),
    the ends a judgement; Q3 relative to the paper's own noise, which the grader now records; Q4 a poor fit moves the
    KD a lot, a ratio is the natural scale of a variance; Q5 a fold-style log ramp like the other folds. It applies
    in addition to the Rmax scale (the weakest counts) and only when the noise is stated; unstated noise leaves the
    Rmax scale alone, as before (unknown is not opposition).
  - how the KD was obtained: ADDED as the fact kd_analysis (kinetic_fit, steady_state_fit; silence unknown). A stated
    kinetic_fit or steady_state_fit decides the zero end of the count curve (KINETIC_CONCENTRATIONS_ZERO or
    CONCENTRATIONS_ZERO); only when the paper says nothing do stated kon and koff stand for a kinetic fit, as before.
  - NOT ADDED: whether the stoichiometry in the theoretical Rmax is stated or assumed, and the analyte class for the
    refractive-index increment. Q1/Q4 the effect is limited: protein and nucleic acid analytes have similar response
    per mass, which the 1.2 slack of RMAX_RATIO_MAX already covers, and an assumed stoichiometry that is wrong
    shows as the same ratio the criterion already lowers. Q3 a stated-or-assumed label would need a new curve with
    no researched ends, which the rules forbid; the quotes for it ("assuming 1:1") are rare and a model cannot
    tell assumed from measured without judging, which the extraction must not do.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_spr_converted'
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
CRITERIA_MAP = {'binding_controls': ('reference_subtraction', 'baseline_regeneration'), 'binding_regime': ('concentration_series', 'mass_transport', 'steady_state_vs_kinetic'), 'binding_parameter_definition': ('fit_model', 'kinetic_consistency'), 'binding_species': ('immobilized_activity',), 'calibration_applicability': ('rmax_consistency',), 'sampling_basis': ('replicates',)}
MIN_CONCENTRATIONS = 5  # EXPERT_REVIEW: fewest analyte concentrations for a usable titration series (spanning 0.1x to 10x KD, Myszka 1999, J Mol Recognit 12:279; five or more is the usual count); full agreement from it.
CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW: for a KD with no stated rates (a steady-state fit, or a KD whose analysis is not stated): the 1:1 binding isotherm has two free parameters (KD and Rmax), so two concentrations are used up by the fit and leave no residual degree of freedom to show the curve describes the data (no credit: degree 0, supported, never conflicting: a short series is weaker evidence, not evidence against). Between this and MIN_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2), because each added concentration is one more independent point on the binding curve that the fitted KD must pass through; 4 concentrations give 2/3, 3 give 1/3.
KINETIC_CONCENTRATIONS_ZERO = 1  # EXPERT_REVIEW: for a KD with kon and koff stated (a kinetic fit): one sensorgram already fixes kon and koff (the association phase gives kobs = kon x C + koff, the dissociation phase koff), so one concentration determines the KD but shows no concentration dependence (no credit: degree 0, supported, never conflicting); each added concentration is one independent check that the same kon and koff describe another concentration, so the degree rises linearly with count - 1 (2 give 1/4, 3 give 1/2, 4 give 3/4), as in the GCI converter for the same global-fit physics.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest concentration should be at most this multiple of KD (0.1x with a factor of 2 slack); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: lowest concentration at the KD itself leaves the lower half of the binding curve undefined, so no agreement; falls from LOW_FACTOR linearly in the fractional occupancy c / (c + KD) (1/6 at LOW_FACTOR, 1/2 here), the share of the binding curve the series leaves uncovered.
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest concentration should be at least this multiple of KD (10x with a factor of 2 slack); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: highest concentration at the KD itself never reaches saturation, so no agreement; falls from HIGH_FACTOR linearly in the fractional occupancy c / (c + KD) (5/6 at HIGH_FACTOR, 1/2 here). LOW_FACTOR and HIGH_FACTOR are mirror images on this scale (1/6 and 5/6), so both ends are judged alike.
CHI2_OVER_RMAX_MAX = 0.10  # EXPERT_REVIEW: fit chi-squared above this fraction of Rmax marks a poor fit (instrument-software rule of thumb); full agreement up to it.
CHI2_OVER_RMAX_ZERO = 0.30  # EXPERT_REVIEW: chi-squared at three times the rule of thumb is a fit that does not describe the data (no agreement); falls linearly from CHI2_OVER_RMAX_MAX.
CHI2_OVER_NOISE2_MAX = 2.0  # EXPERT_REVIEW: chi-squared is the residual variance of the fit in RU^2, so a fit that describes the sensorgrams leaves residuals at the instrument noise and chi-squared near noise^2 (Myszka 1999 J Mol Recognit 12:279: residuals should scatter randomly at about the noise level; the Biacore evaluation notes read chi-squared against the noise, not against Rmax); twice noise^2 (a residual RMS of 1.4 times the noise) leaves room for the small systematic errors of a real surface; full agreement up to it. Used in addition to the Rmax scale, only when the paper states the noise.
CHI2_OVER_NOISE2_ZERO = 10.0  # EXPERT_REVIEW: chi-squared at ten times noise^2 is a residual RMS of 3.2 times the noise, a fit with a clear systematic misfit (wrong model, heterogeneity, drift) that no noise explains (no agreement); falls from CHI2_OVER_NOISE2_MAX linearly in log ratio, because chi-squared is a variance and a factor of it is the natural scale of a misfit. The ends are a judgement, not a published number.
RMAX_RATIO_MIN = 0.3  # EXPERT_REVIEW: observed/theoretical Rmax below this means a mostly inactive surface or wrong stoichiometry; full agreement from it.
RMAX_RATIO_ZERO_MIN = 0.1  # EXPERT_REVIEW: a tenth of the theoretical Rmax or less is an essentially inactive surface (no agreement); falls linearly from RMAX_RATIO_MIN.
RMAX_RATIO_MAX = 1.2  # EXPERT_REVIEW: observed/theoretical Rmax above this means non-specific binding or aggregation; full agreement up to it.
RMAX_RATIO_ZERO_MAX = 2.0  # EXPERT_REVIEW: twice the theoretical Rmax or more is mostly non-specific signal (no agreement); falls linearly from RMAX_RATIO_MAX.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent replicate experiments; full agreement from it. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of the mean KD over n independent surfaces falls as 1 / sqrt(n) (the same sd^2 / n this converter uses for the effect variance); 1 run about 0.58, 2 about 0.82; never conflicting for a stated count.
KINETIC_FOLD_MAX = 1.2  # EXPERT_REVIEW: allowed fold gap between the KD and koff/kon, either way (the earlier 20 percent relative gap, now on both sides): the two come from the same fit, so only rounding of the reported numbers (a few percent at two significant figures) and averaging over replicates (the mean of KDs against the ratio of mean rates, about CV^2, ~10 percent at a 30 percent CV) separate them; full agreement up to it.
KINETIC_FOLD_ZERO = 1.8  # EXPERT_REVIEW: a 1.8-fold gap either way (the earlier 80 percent relative gap above the KD) is beyond what rounding and averaging produce and below the twofold at which two different analyses (AGREEMENT_FACTOR) start to lose credit: the KD is not the one the reported rates describe (no agreement); falls from KINETIC_FOLD_MAX linearly in log fold, because an error by a factor matters on the log KD scale the strength is read on.
AGREEMENT_FACTOR = 2.0  # EXPERT_REVIEW: allowed fold gap between steady-state KD and kinetic KD; full agreement up to it.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: a tenfold gap between the two KD estimates is a different binding event (no agreement); falls from AGREEMENT_FACTOR linearly in log fold (threefold about 0.75, fivefold about 0.43), because the KD is read on a log scale: doubling the gap from 2 to 4 costs as much as from 5 to 10.
NULL_REASONS = {'recovery': 'spr_has_no_matrix_recovery_measurement', 'attributed_signal': 'spr_double_referencing_is_not_an_attribution_fraction', 'total_signal': 'spr_double_referencing_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_spr_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_spr_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _share(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (zero - value) / (zero - full)


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit), all on the criterion's own scale (as given, fractional occupancy, or log fold). Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly on that scale to 0 at the zero limit."""
    degrees = [_share(value, full, zero) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _occupancy(ratio):
    """Fractional occupancy c / (c + KD) of a concentration c given as c / KD: where on the 1:1 binding curve it sits."""
    return ratio / (1 + ratio)


def _fold(value, full, zero):
    """A fold limit on the log scale, for _graded: 1.0 at the full fold, 0 at the zero fold, linear in log fold."""
    return math.log(value), math.log(full), math.log(zero)


def _judge_series(native):
    # the two ratios keep their ramps (conflicting at their zero end), judged on the fractional occupancy; the lower end is judged only when the series
    # has one distinct from its upper end (one concentration is a short series, not a badly placed one). The count of concentrations only lowers the
    # degree: partial credit below MIN_CONCENTRATIONS, none at or below the zero count of the KD's analysis, never conflicting (a short series is weaker evidence)
    refs = native['concentration_refs']
    low, high = native['concentration_low_over_kd'], native['concentration_high_over_kd']
    limits = [(_occupancy(high), _occupancy(HIGH_FACTOR), _occupancy(HIGH_ZERO_FACTOR))]
    if low < high:
        limits.append((_occupancy(low), _occupancy(LOW_FACTOR), _occupancy(LOW_ZERO_FACTOR)))
    verdict = _graded(refs, *limits)
    if verdict['status'] == 'conflicting':
        return verdict
    # the paper's own statement of how the KD was obtained decides; only when it says nothing do stated rates stand for a kinetic fit (see the two constants)
    kinetic = native['kd_analysis'] == 'kinetic_fit' or (native['kd_analysis'] != 'steady_state_fit' and native['kd_from_rates_nM'] is not None)
    zero = KINETIC_CONCENTRATIONS_ZERO if kinetic else CONCENTRATIONS_ZERO
    count_degree = max(0.0, min(1.0, _share(native['concentration_count'], MIN_CONCENTRATIONS, zero)))
    return _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_fit(native):
    # each scale the paper allows is applied and the weakest counts (the noise scale in addition to the Rmax scale, never instead of it)
    limits = []
    if native['chi2_over_rmax'] is not None:
        limits.append((native['chi2_over_rmax'], CHI2_OVER_RMAX_MAX, CHI2_OVER_RMAX_ZERO))
    if native['chi2_over_noise_squared'] is not None:
        limits.append(_fold(native['chi2_over_noise_squared'], CHI2_OVER_NOISE2_MAX, CHI2_OVER_NOISE2_ZERO))
    verdict = _graded(native['fit_refs'], *limits)
    if verdict['status'] == 'supported' and native['fit_model'] == '1:1_langmuir' and native['fit_bivalent_answer'] != 'no':
        return _verdict('unknown', [])
    return verdict


def _judge_rmax(native):
    return _graded(native['rmax_refs'], (native['rmax_ratio'], RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MIN), (native['rmax_ratio'], RMAX_RATIO_MAX, RMAX_RATIO_ZERO_MAX))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


def _judge_kinetic(native):
    rates, kd = native['kd_from_rates_nM'], native['kd_nM']
    return _graded(native['kinetic_refs'], _fold(max(rates, kd) / min(rates, kd), KINETIC_FOLD_MAX, KINETIC_FOLD_ZERO))      # the same fold either way scores the same


def _judge_steady_kinetic(native):
    return _graded(native['steady_kinetic_refs'], _fold(native['steady_kinetic_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_series, ('fit_model', 'chi_squared_recorded_for_the_sheet'): _judge_fit,
          ('rmax_consistency', 'rmax_ratio_recorded_for_the_sheet'): _judge_rmax, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates,
          ('kinetic_consistency', 'kd_from_rates_recorded_for_the_sheet'): _judge_kinetic, ('steady_state_vs_kinetic', 'estimate_fold_recorded_for_the_sheet'): _judge_steady_kinetic}


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
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_spr(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    kd = native['quantities']['kd']
    if native['kd_nM'] is None:
        null_components['effect'] = 'kd_not_given_as_a_point_value'
    else:
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'spr_kd:' + ref, kd['source_refs'], kd['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'spr_kd_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
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
    converted = {'version': VERSION, 'experiment_type': 'spr', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if native['kd_nM'] is not None:
        converted['direction_field_support'] = kd['support']      # the support class of the KD operand, the field that fixes the effect
    else:      # no KD: the experiment's stated yes/no result stands (owner, 2026-11-22), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs'])}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['interaction_support']      # the support class of the fact binding_detected, the one field the statement is derived from
    return converted
