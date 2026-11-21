"""DSF converter: turns the DSF grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_dsf.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a thermal shift
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (from a series of ligand concentrations: the Tm or its shift against the concentration). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key dsf_kd, native component 'kd'; it is thermal-shift-derived, which the measurement key states). The caveats of the method (the shift shows binding only
                    indirectly; a KD needs ligand concentrations on both sides of it) are not changed in the number, they are judged by the criteria (concentration_series, concentration_range,
                    dose_dependence, shift_size, shift_over_spread) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported and n is at least SD_MIN_EXPERIMENTS (a between-experiment SD needs two experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no KD (the shift of the Tm at one or a few ligand concentrations). Then, exactly as the pull-down, EMSA, SEC, dialysis and AUC converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and the shift in degrees is not
put into the effect (it is not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'thermal_shift_c'}):
  statement           'interaction_detected' (the ligand is stated to raise the Tm), 'interaction_not_detected' (the Tm is stated not to change) or 'interaction_not_stated'
  support_refs        the spans of the fact that states it (empty when not stated)
  thermal_shift_c     the signed shift of the Tm in degrees Celsius, or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (DSF criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              protein_alone_control + ligand_alone_control (the controls that show the shift is the ligand's effect on the protein and not the vehicle, or a signal of the ligand and the dye)
binding_regime                dose_dependence + concentration_series + concentration_range (the shift follows the ligand concentration, over concentrations on both sides of the apparent KD)
binding_parameter_definition  shift_observed + shift_size + shift_over_spread (what the response is: a rise of the Tm, its size and its size over the scatter of the Tm)
calibration_applicability     curve_quality + heating_rate (the Tm is read from a clean sigmoid, near the equilibrium unfolding)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each researched value is kept as a named EXPERT_REVIEW constant and is the centre or end of a gradual curve (owner rule, A105_EXPERIMENT_SOP step 3); the
shape of each curve is chosen per criterion (see the questions below):
  shift_size          conflicting when the shift is 0 or negative (the paper's own number shows no stabilisation); a positive shift up to SHIFT_ZERO_AGREEMENT_C (inside the typical
                      reproducibility of a Tm) is supported with degree 0 (no credit, but not opposition: only the paper's own spread, shift_over_spread, can call it no larger than the scatter);
                      linear in the shift up to 1.0 at SHIFT_FULL_AGREEMENT_C.
  shift_over_spread   linear in the shift over the stated SD of the Tm, 1.0 from SHIFT_OVER_SPREAD_FULL_AGREEMENT; conflicting at or below SHIFT_OVER_SPREAD_ZERO_AGREEMENT (a shift no larger than the
                      paper's own scatter).
  concentration_series  never conflicting from the count (a short series is low partial credit): d = min(1, (n / MIN_CONCENTRATIONS) ** CONCENTRATION_CREDIT_POWER) when the record has no KD (a dose
                      dependence of the shift), d = min(1, (n / MIN_CONCENTRATIONS_FOR_KD) ** KD_CONCENTRATION_CREDIT_POWER) when it reports an apparent KD (a fit of the Tm against the concentration).
  concentration_range linear in the fractional occupancy x / (1 + x) of the lowest and of the highest concentration (x = concentration over the KD), between the occupancies at the researched ratios
                      LOW_OVER_KD_FULL_AGREEMENT / LOW_OVER_KD_ZERO_AGREEMENT and HIGH_OVER_KD_FULL_AGREEMENT / HIGH_OVER_KD_ZERO_AGREEMENT; a KD the series does not reach past on one side is conflicting;
                      the weaker side decides.
  heating_rate        1.0 up to HEATING_RATE_FULL_AGREEMENT, linear to 0 at HEATING_RATE_ZERO_AGREEMENT, conflicting from it.
  replicates          the precision of the mean over n independent experiments relative to that at MIN_REPLICATES: d = sqrt(min(n, MIN_REPLICATES) / MIN_REPLICATES), never conflicting from the count;
                      unknown when the independence is not stated as yes (a stated no is the grader's conflicting fact).
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).

The owner's questions, asked of every researched value and curve (2026-11-21). Q1 what it protects against; Q2 general practice or lab-specific (source);
Q3 absolute or relative scale, and whether the relative quantity is a grader fact; Q4 how badly a wrong value misleads and whether the shape reflects it; Q5 consistency with
the other binding assays. Sources: Pantoliano et al. 2001 J Biomol Screen 6:429; Lo et al. 2004 Anal Biochem 332:153; Matulis et al. 2005 Biochemistry 44:5258; Niesen, Berglund and
Vedadi 2007 Nat Protoc 2:2212; Vivoli et al. 2014 J Vis Exp 91:e51809; Huynh and Partch 2015 Curr Protoc Protein Sci 79:28.9; Bai et al. 2019 Sci Rep 9:2650; Gao, Oerlemans and Groves 2020
Biophys Rev 12:85; Jarmoskaite et al. 2020 eLife 9:e57264; Sanchez-Ruiz 1992 Biophys J 61:921; Zhang, Chung and Oldenburg 1999 J Biomol Screen 4:67.
  shift_size (SHIFT_FULL_AGREEMENT_C 2.0, SHIFT_ZERO_AGREEMENT_C 0.5)
    Q1 a Tm rise too small to be a stabilisation by binding (well-to-well noise, vehicle or buffer effects), or a fall (destabilisation, aggregation, a dye-binding compound).
    Q2 general screening practice: hits are commonly called at 1 to 3 degrees or at 3 SD of the controls (Niesen 2007; Gao 2020); 2.0 is the usual compound cut-off; 0.5 is the typical
       reproducibility of a DSF Tm (0.1 to 0.5 degrees between wells, Niesen 2007; Huynh and Partch 2015). Fragments often give 0.5 to 2 degrees, so 2.0 is strict for them.
    Q3 the noise end should be the paper's own spread when stated: it is (shift_over_spread, a grader fact); 0.5 stands in for it only as "no credit", never as opposition. The size end is
       truly relative to the ligand concentration over the KD and to the unfolding enthalpy (the shift grows as ln(1 + [L]/KD), Matulis 2005): the concentration at which the stated shift was read
       is not a grader fact (grader gap), the enthalpy is rarely stated; so absolute.
    Q4 a real shift of 0.3 to 0.5 degrees with a tiny stated SD was conflicting, overriding the paper's own precision and turning a weak binder into opposition (MISTAKE, fixed); linear between
       0.5 and 2.0 is kept because the shift is linear in ln(occupancy term), so equal degrees are equal fold steps in [L]/KD, the same log scale as the KD strength.
    Q5 CETSA uses the same absolute ramp (3.0 / 0.5); a stated fall stays conflicting as in CETSA.  -> CHANGED: conflicting only at a shift <= 0; 0 < shift <= 0.5 supported with degree 0.
  shift_over_spread (SHIFT_OVER_SPREAD_FULL_AGREEMENT 3.0, SHIFT_OVER_SPREAD_ZERO_AGREEMENT 1.0)
    Q1 a shift inside the paper's own scatter of the Tm.  Q2 general statistical practice (3 SD hit calling; Zhang 1999; Niesen 2007).  Q3 already relative to the paper's own SD (tm_spread,
       a grader fact); the SD of a difference of two Tm is sqrt(2) times that of one, which 3.0 absorbs; whether tm_spread is over wells or over independent experiments is not a grader fact
       (grader gap).  Q4 a shift of 1 to 3 SD is where noise and signal are told apart (one-sided tail 0.16 to 0.001), so the ramp is steep exactly there and flat beyond; the paper's own
       scatter is the paper's control, so conflicting at <= 1 SD is SOP rule 5.  Q5 same as the other assays' signal-over-own-control.  -> KEPT.
  GRADER GAPS ADDED (2026-11-21, after the range review; the owner's questions answered for each): (1) the ligand concentration at which the shift was read (new record field shift_ligand_concentration;
    grader fact shift_concentration_over_kd) lowers the clear-shift end of shift_size with ln(1 + [L]/KD) when a KD is stated (SHIFT_REFERENCE_OVER_KD); with no KD the shift stays absolute.
    (2) KD over the protein concentration (grader fact kd_over_protein from the existing protein_concentration field): a KD below the protein concentration is titration-limited, a proportional degree in
    concentration_range (KD_OVER_PROTEIN_FULL_AGREEMENT). (3) Whether tm_spread is over independent experiments or wells (new fact tm_spread_over_independent_experiments): a wells-only SD gets the
    between-experiment scatter added in quadrature in shift_over_spread (BETWEEN_EXPERIMENT_TM_SD_C). (4) A stated 'no titration' (single-concentration screen) is no longer conflicting in the grader: it is recorded
    as one concentration and gets the series' low partial credit (the commonest DSF format is a single-concentration screen: a weakness, not opposition).
  concentration_series (MIN_CONCENTRATIONS 3; new MIN_CONCENTRATIONS_FOR_KD 5, CONCENTRATION_CREDIT_POWER 1.0, KD_CONCENTRATION_CREDIT_POWER 2.0)
    Q1 a shift at one concentration that may be a single-point artefact (aggregation or dye interaction at a high dose); for a KD, a fit with too few points to fix it.
    Q2 three concentrations for a dose dependence is general practice for a qualitative DSF; an apparent KD is fitted from 8 to 16 concentrations in the method papers (Vivoli 2014; Bai 2019);
       5 is the floor used by SPR and CETSA ITDR here.  Q3 relative to what the record states: whether an apparent KD is reported (native kd_nM, available). A KD fit of the Tm against [L] has
       three parameters (Tm0, the maximal shift, KD), so 3 concentrations leave no residual degree of freedom.  Q4 was linear from 1 with one concentration conflicting: a single-dose screen (the
       commonest DSF) became opposition, and 3 points gave full credit to a KD that 3 points cannot test (both MISTAKES, fixed). For a dose dependence each concentration adds evidence in equal
       parts (proportional: 1 -> 0.33, 2 -> 0.67); for a KD the credit falls faster below the fit's need (convex: 4 -> 0.64, 3 -> 0.36, 1 -> 0.04).
    Q5 a short series is low partial credit, never conflicting (CETSA, SPR).  -> CHANGED: linear from CONCENTRATIONS_ZERO 1 (conflicting) -> proportional / convex as above; CONCENTRATIONS_ZERO removed.
  concentration_range (LOW_OVER_KD 0.2 / 1.0, HIGH_OVER_KD 5.0 / 1.0)
    Q1 an apparent KD read outside the sampled concentrations (an extrapolated KD).  Q2 general titration practice, 0.1x to 10x KD with a factor 2 slack (Jarmoskaite 2020); DSF KD papers
       follow it (Vivoli 2014).  Q3 relative to the paper's own KD (a grader fact). It should also be relative to the protein concentration: a KD below about half the protein concentration
       is titration-limited and only an upper bound (Jarmoskaite 2020); KD over protein concentration is not a grader fact (grader gap).  Q4 linear in the ratio was asymmetric: 0.5x KD gave
       0.63 but 2x KD gave 0.25, although 0.2 and 5 are symmetric fold distances (MISTAKE, fixed). Linear in occupancy x / (1 + x) is symmetric (0.5x and 2x both 0.5) and steepest near
       the KD, where each fold of range adds the most of the transition.  Q5 the same values as SPR and CETSA; those converters still use the asymmetric linear-in-ratio shape (cross-assay
       note).  -> CHANGED shape (values kept): linear in ratio -> linear in occupancy.
  heating_rate (HEATING_RATE_FULL_AGREEMENT 2.0, HEATING_RATE_ZERO_AGREEMENT 10.0)
    Q1 a Tm distorted by unfolding kinetics (irreversible unfolding and aggregation make the Tm scan-rate dependent; Sanchez-Ruiz 1992).  Q2 general: DSF is run at about 1 degree per minute
       (Niesen 2007; nanoDSF 1 degree per minute); 2.0 is the common upper rate, 10 the instruments' fast end.  Q3 absolute: the kinetic distortion depends on the protein, not on a quantity
       the paper states.  Q4 the shift is a difference of two scans at the same rate, so a fast rate biases the shift less than the Tm; the equilibrium KD models (Matulis 2005) are hurt
       more; linear between 2 and 10 is gentle, which fits a mostly cancelling bias.  Q5 a stated value beyond the method's no-longer-meaningful end is conflicting, as SPR chi^2.  -> KEPT.
  replicates (MIN_REPLICATES 3)
    Q1 a shift or KD seen once (plate, dye lot or preparation artefact).  Q2 general: biological triplicates (Niesen 2007; Huynh and Partch 2015).  Q3 absolute count.  Q4 was linear in n - 1
       with one experiment conflicting: a single experiment that shows a stabilisation became opposition (MISTAKE, fixed); what fewer experiments lose is the precision of the mean shift
       or KD, standard error ~ 1 / sqrt(n).  Q5 replicates mean precision, sqrt(n / MIN) as alpha, FP, FRET, CETSA, pull-down.
    -> CHANGED: linear in n - 1 from REPLICATES_ZERO 1 (conflicting) -> sqrt(n / MIN_REPLICATES); REPLICATES_ZERO removed; SD_MIN_EXPERIMENTS 2 added for the variance only.
  Unknown weight (row_contract WEIGHT_UNKNOWN_BY_TYPE['dsf'], not in this file and not a degree): the readout is a temperature read from a relative fluorescence curve; the shift shows
    binding only indirectly; an apparent KD is model-dependent and refers to the Tm, not 25 degrees; unstated ligand-alone controls hide the common false positives (fluorescent or dye-binding
    compounds, aggregators). Purified protein makes it cleaner than CETSA (0.6) and close to Trp quenching (0.65). Recommended 0.65; pending (outside this file).
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. variance_correspondence takes
the weakest support of the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is
not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, recovery) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the protein,
immobilized_preparation_ref = the ligand, surface_ref = None (a plate is not a surface reference), dataset_ref = the dataset.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_dsf_converted_v1'
CRITERIA_MAP = {'binding_controls': ('protein_alone_control', 'ligand_alone_control'), 'binding_regime': ('dose_dependence', 'concentration_series', 'concentration_range'), 'binding_parameter_definition': ('shift_observed', 'shift_size', 'shift_over_spread'), 'calibration_applicability': ('curve_quality', 'heating_rate'), 'sampling_basis': ('replicates',)}
SHIFT_FULL_AGREEMENT_C = 2.0  # EXPERT_REVIEW: smallest rise of the Tm (degrees Celsius) that the sheet takes as a clear stabilisation; thermal shift screens commonly call a hit a shift of 2 degrees or more.
SHIFT_ZERO_AGREEMENT_C = 0.5  # EXPERT_REVIEW: rise of the Tm (degrees Celsius) at or below which the shift cannot be told from the typical reproducibility of the Tm (a few tenths of a degree): no credit (degree 0), but not opposition, because the paper's own spread (shift_over_spread) is what can show it inside the scatter; no shift or a fall of the Tm (a destabilisation, which is not a stabilisation by binding) is conflicting; between this and SHIFT_FULL_AGREEMENT_C the degree rises linearly (the shift grows as ln(1 + [L]/KD), so equal steps are equal fold steps).
SHIFT_OVER_SPREAD_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest quotient of the signed shift over the standard deviation of the Tm taken as a shift well outside the scatter (three standard deviations).
SHIFT_OVER_SPREAD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient at or below which the shift is no larger than one standard deviation of the Tm: conflicting; the degree falls linearly in between.
MIN_CONCENTRATIONS = 3  # EXPERT_REVIEW: fewest ligand concentrations that show a concentration dependence of the shift (one gives a shift, two a single slope; three show curvature and a plateau); full agreement from it when the record reports no KD.
CONCENTRATION_CREDIT_POWER = 1.0  # EXPERT_REVIEW: shape below MIN_CONCENTRATIONS with no KD, d = n / MIN_CONCENTRATIONS (proportional: 2 -> 0.67, 1 -> 0.33). Why for DSF: the series is asked for a dose dependence of the shift, and each concentration adds that evidence in equal parts; one concentration still shows a shift, so a short series is low partial credit, never conflicting.
MIN_CONCENTRATIONS_FOR_KD = 5  # EXPERT_REVIEW: fewest ligand concentrations for an apparent KD read from the Tm (or its shift) against the concentration: the fit has three parameters (Tm0, the maximal shift, KD), so 3 concentrations leave no residual degree of freedom; 5 leaves two, the floor SPR and CETSA ITDR use here; DSF KD papers use 8 to 16 (Vivoli et al. 2014 J Vis Exp; Bai et al. 2019 Sci Rep). Full agreement from it when a KD is reported.
KD_CONCENTRATION_CREDIT_POWER = 2.0  # EXPERT_REVIEW: shape below MIN_CONCENTRATIONS_FOR_KD, d = (n / 5) ** 2 (convex: 4 -> 0.64, 3 -> 0.36, 2 -> 0.16, 1 -> 0.04). Why for a DSF KD: below the three fit parameters the KD is not determined by the data, so the credit falls faster than in proportion to the missing concentrations (as CETSA's melt-curve count).
LOW_OVER_KD_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest ratio of the lowest ligand concentration to the apparent KD at which the series defines the unliganded end of the curve (0.1x KD with a factor 2 slack; Jarmoskaite et al. 2020 eLife).
LOW_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the lowest ligand concentration to the KD from which the series does not reach below the KD: conflicting; in between the degree is linear in the occupancy x / (1 + x) (symmetric with the high side, steepest near the KD).
HIGH_OVER_KD_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest ratio of the highest ligand concentration to the apparent KD at which the series reaches the saturated end of the curve (10x KD with a factor 2 slack).
HIGH_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the highest ligand concentration to the KD up to which the series does not reach above the KD: conflicting; in between the degree is linear in the occupancy x / (1 + x).
HEATING_RATE_FULL_AGREEMENT = 2.0  # EXPERT_REVIEW: largest heating rate (degrees Celsius per minute) at which the Tm is taken as near the equilibrium unfolding (instruments are run at 1 to 2 degrees per minute, nanoDSF at 1 degree per minute).
HEATING_RATE_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: heating rate (degrees Celsius per minute) from which the unfolding is taken as kinetically distorted (the Tm depends strongly on the rate): conflicting; the degree falls linearly in between.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); wells of one plate do not count; full agreement from it. Below it d = sqrt(n / MIN_REPLICATES) (2 -> 0.82, 1 -> 0.58), never conflicting: one experiment already shows the shift; what fewer experiments lose is the precision of the mean shift or KD (the scatter between preparations, dye lots and plates averages down as 1 / sqrt(n), the same sd^2 / n this converter uses for the variance).
SHIFT_REFERENCE_OVER_KD = HIGH_OVER_KD_FULL_AGREEMENT  # EXPERT_REVIEW: ligand concentration over the apparent KD at and above which the stated shift is taken as read near saturation, so SHIFT_FULL_AGREEMENT_C applies unchanged (the series reaches the saturated end at HIGH_OVER_KD_FULL_AGREEMENT times the KD). Below it the shift that a binder gives falls as ln(1 + [L]/KD) (Matulis et al. 2005 Biochemistry 44:5258), so the shift that counts as clear falls with it: the full-agreement end becomes SHIFT_ZERO_AGREEMENT_C + (SHIFT_FULL_AGREEMENT_C - SHIFT_ZERO_AGREEMENT_C) * ln(1 + x) / ln(1 + SHIFT_REFERENCE_OVER_KD), x = the ligand concentration of the shift over the KD. The noise end stays absolute (the reproducibility of a Tm does not depend on the ligand). Used only when both the concentration of the shift and the KD are stated.
BETWEEN_EXPERIMENT_TM_SD_C = 0.5  # EXPERT_REVIEW: typical standard deviation of a Tm between independent experiments (a few tenths of a degree; Niesen et al. 2007 Nat Protoc 2:2212; Huynh and Partch 2015). A stated standard deviation over wells of one plate (the paper says so: tm_spread_over_independent_experiments = no) leaves this between-experiment scatter out, so the sheet adds it in quadrature: sd_eff = sqrt(sd^2 + BETWEEN_EXPERIMENT_TM_SD_C^2). A scatter over independent experiments, or one whose basis is not stated, is used as stated (unknown is never opposition).
KD_OVER_PROTEIN_FULL_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the apparent KD to the protein concentration from which the KD is not limited by the titration (the protein is not above the KD, so little ligand is depleted; Jarmoskaite et al. 2020 eLife 9:e57264). Below it a stoichiometric titration only bounds the KD (half-saturation lies near [P]/2 + KD, so a KD below about half the protein concentration is an upper bound): the degree falls in proportion, d = KD / [P] (0.5 -> 0.5, 0.1 -> 0.1), never conflicting (a KD with a tight-binding bound is still the paper's own number). Used only when the protein concentration is stated.
SD_MIN_EXPERIMENTS = 2  # not a quality threshold: a between-experiment standard deviation needs at least two independent experiments, so an SD with fewer is not turned into a variance of the estimate.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_thermal_shift_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_thermal_shift_is_not_an_attribution_fraction', 'total_signal': 'a_thermal_shift_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_dsf_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_dsf_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _occupancy(ratio):
    """The fractional occupancy x / (1 + x) at a ligand concentration of ``ratio`` times the KD."""
    return ratio / (1 + ratio)


def _judge_shift(native):
    # no rise or a fall: the paper's own number shows no stabilisation (conflicting). A positive shift inside the typical reproducibility gets no credit but
    # is not opposition (the paper's own spread decides that, in shift_over_spread); linear from SHIFT_ZERO_AGREEMENT_C to SHIFT_FULL_AGREEMENT_C.
    shift = native['thermal_shift_c']
    refs = list(dict.fromkeys([*native['thermal_shift_refs'], *native['shift_concentration_refs']]))
    if shift <= 0:
        return _verdict('conflicting', native['thermal_shift_refs'])
    width = SHIFT_FULL_AGREEMENT_C - SHIFT_ZERO_AGREEMENT_C
    if native['shift_concentration_over_kd'] is not None:      # the shift read below saturation is expected to be smaller: the clear-shift end falls with ln(1 + [L]/KD)
        width *= min(1.0, math.log1p(native['shift_concentration_over_kd']) / math.log1p(SHIFT_REFERENCE_OVER_KD))
    return _verdict('supported', refs, min(1.0, max(0.0, (shift - SHIFT_ZERO_AGREEMENT_C) / width)))


def _judge_shift_over_spread(native):
    ratio = native['shift_over_spread']
    if native['tm_spread_independent'] == 'no':      # a scatter over wells of one plate leaves out the scatter between experiments: add it in quadrature
        ratio = native['thermal_shift_c'] / math.hypot(native['tm_spread_c'], BETWEEN_EXPERIMENT_TM_SD_C)
    return _graded(native['shift_spread_refs'], _degree(ratio, SHIFT_OVER_SPREAD_FULL_AGREEMENT, SHIFT_OVER_SPREAD_ZERO_AGREEMENT))


def _judge_concentrations(native):
    # (a stated 'no titration' arrives here as a single concentration.) the count is never a conflict: proportional to MIN_CONCENTRATIONS for a dose dependence; convex to MIN_CONCENTRATIONS_FOR_KD when the record reports a KD fitted from the series
    if native['kd_nM'] is None:
        full, power = MIN_CONCENTRATIONS, CONCENTRATION_CREDIT_POWER
    else:
        full, power = MIN_CONCENTRATIONS_FOR_KD, KD_CONCENTRATION_CREDIT_POWER
    return _verdict('supported', native['concentration_count_refs'], min(1.0, (native['concentration_count'] / full) ** power))


def _judge_range(native):
    # linear in the occupancy at the lowest and the highest concentration, between the occupancies at the researched ratios (symmetric in fold distance from the KD)
    low = _degree(_occupancy(native['low_over_kd']), _occupancy(LOW_OVER_KD_FULL_AGREEMENT), _occupancy(LOW_OVER_KD_ZERO_AGREEMENT))
    high = _degree(_occupancy(native['high_over_kd']), _occupancy(HIGH_OVER_KD_FULL_AGREEMENT), _occupancy(HIGH_OVER_KD_ZERO_AGREEMENT))
    protein = [] if native['kd_over_protein'] is None else [min(1.0, native['kd_over_protein'] / KD_OVER_PROTEIN_FULL_AGREEMENT)]      # a KD below the protein concentration is titration-limited
    return _graded(native['range_refs'], low, high, *protein)


def _judge_heating_rate(native):
    return _graded(native['heating_rate_refs'], _degree(native['heating_rate_c_per_min'], HEATING_RATE_FULL_AGREEMENT, HEATING_RATE_ZERO_AGREEMENT))


def _judge_replicates(native):
    # the precision of the mean over n independent experiments relative to that at MIN_REPLICATES (its comment says why for a thermal shift); never a conflict from the count
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # the count is not stated to be of independent experiments
    return _verdict('supported', native['replicate_refs'], math.sqrt(min(native['replicate_count'], MIN_REPLICATES) / MIN_REPLICATES))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('shift_size', 'thermal_shift_recorded_for_the_sheet'): _judge_shift, ('shift_over_spread', 'shift_over_spread_recorded_for_the_sheet'): _judge_shift_over_spread,
          ('concentration_series', 'concentration_count_recorded_for_the_sheet'): _judge_concentrations, ('concentration_series', 'single_concentration_recorded_for_the_sheet'): _judge_concentrations, ('concentration_range', 'concentration_range_recorded_for_the_sheet'): _judge_range,
          ('heating_rate', 'heating_rate_recorded_for_the_sheet'): _judge_heating_rate, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
        if _criterion(graded, 'replicates')['status'] != 'supported' or count['value'] < SD_MIN_EXPERIMENTS:
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_dsf(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'dsf_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'dsf_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
    dependence = {'analyte_preparation_ref': preparations['protein_preparation_ref'], 'immobilized_preparation_ref': preparations['ligand_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'dsf', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities']['kd']['support']      # the support class of the KD operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'thermal_shift_c': native['thermal_shift_c']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['shift_observed'][0]      # the support class of the fact thermal_shift_observed, the one field the statement is derived from
    return converted
