"""EMSA converter: turns the EMSA grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_emsa.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that an EMSA
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (a titration). Then the converter fills the numeric effect as the earlier quantitative types do
(quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key emsa_kd). It is an APPARENT constant, with the caveats of the
                    method (the gel is not at equilibrium during the run, the cage effect of the gel, the probe concentration must be at or below
                    the KD); those caveats are not changed in the number, they are judged by the criteria (equilibrium, complex_stability,
                    probe_concentration, protein_range, saturation, fit_model) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments) and n is at least
                    MIN_EXPERIMENTS_FOR_A_SPREAD (one gel has no gel-to-gel spread); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no apparent KD (a shift is shown). Then, exactly as the pull-down converter does (quantity_kind
'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells are
unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and the fraction shifted at
the highest protein concentration is not put into the effect (it is not on the nM scale). What the experiment does contribute is carried beside the
sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'fraction_shifted'}):
  statement          'interaction_detected' (a shifted band is stated), 'interaction_not_detected' (no shift is stated) or 'interaction_not_stated'
  support_refs       the spans of the fact that states it (empty when not stated)
  fraction_shifted   the stated percent of the probe shifted at the highest protein concentration, or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (EMSA criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              specific_competition + nonspecific_competition + mutant_probe + probe_alone_lane + nonspecific_protein_control +
                              protein_identity (the controls that show the shift is specific to this protein and this sequence)
binding_regime                equilibrium + complex_stability + probe_concentration + protein_range + titration_points
binding_parameter_definition  shift_observed + single_complex + fit_model (what the response is: a shifted band, one species, and the model of the KD)
calibration_applicability     free_probe_quantified + saturation (the shifted fraction is read from the free and shifted probe, and reaches a plateau)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Every researched value is kept as a named EXPERT_REVIEW constant with its reason; none is a pass/fail cut-off of a
supported criterion (owner rule, SOP step 3). Continuous comparisons are supported with a degree of 1.0 up to the full-agreement limit, the degree falling linearly to 0 at the
zero-agreement limit, and conflicting at or beyond that limit: probe_concentration (probe over the KD, on the LOG of the depletion bias b(r) = 1 + r / 2 between b(MAX_PROBE_OVER_KD) and b(PROBE_OVER_KD_ZERO_AGREEMENT); supported with no degree when the KD comes from a quadratic fit, which
solves for the probe depletion), protein_range (the lowest and the highest protein over the KD, each on the one-site occupancy x / (1 + x) between its own ends, the weaker degree taken), saturation (percent shifted at the highest protein)
and, for a one-site model with a stated probe, fit_model (the same probe over the KD, the same log-bias degree). The two counts are never conflicting (a short series or a single gel is weaker
evidence, not evidence against): titration_points is supported with (n - p + 1) / (MIN_TITRATION_POINTS - p + 1), p = TITRATION_FIT_PARAMETERS and n counted as p when
below it (2 lanes or fewer 0.2, 3 0.4, 4 0.6, 5 0.8, 6 or more 1.0); replicates, with the experiments stated independent, is supported with sqrt(n / MIN_REPLICATES)
capped at 1 (1 gel 0.58, 2 gels 0.82), otherwise unknown. Facts get no degree: single_complex (more than one species needs a multi-site model; this judgement holds the
classification of the fit models as one-site or not), specific_competition (a 'no' with a competitor excess below MIN_COMPETITOR_EXCESS is unknown, not a test of specificity, else
conflicting). equilibrium (with a stated KD and no stated time course) is a curve: T_FAST = the time of EQUILIBRATION_HALF_LIVES half-lives of the lane at the KD with the fast
association rate, T_SLOW the same with the slow one; an incubation t at or below T_FAST is conflicting, otherwise supported with degree min(1, ln(t / T_FAST) / ln(T_SLOW / T_FAST)); with no KD
there is no scale and it is unknown. A competitor excess has no curve (unknown / conflicting, neither carries a degree). The judgement of
single_complex can be not_applicable (several species and no apparent KD), and such a member is dropped like any other. A sheet criterion that is supported carries the smallest
degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result). The qualitative effect is unchanged.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree
(the continuous comparisons above); direct leaves it unchanged. Support never changes a status. variance_correspondence takes the weakest support of
the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the protein,
immobilized_preparation_ref = the labelled probe, surface_ref = None (a gel is not a surface reference), dataset_ref = the dataset.

The owner's five questions, per researched value (2026-11-21 review; Q1 what it protects against, Q2 general practice or lab-specific, Q3 absolute or
relative scale and whether the grader has the quantity, Q4 how badly a wrong value misleads and whether the shape fits, Q5 consistency with the other
binding types). Method references: Hellman & Fried 2007 Nat Protoc 2:1849 (EMSA protocol), Fried 1989 Electrophoresis 10:366 (EMSA binding parameters),
Jarmoskaite et al. 2020 eLife 9:e57264 (how to measure binding affinities), Pollard 2010 Mol Biol Cell 21:4061 (binding assays).
MIN_COMPETITOR_EXCESS 50x  Q1 a 'not abolished by the cold probe' read as non-specific binding when too little competitor was added. Q2 general practice
     (Hellman & Fried 2007; competition with 50 to 200 fold excess). Q3 physically relative: the competitor must outnumber the protein's sites, so the needed
     excess is (protein + KD) / probe; the protein concentration of the competition lane is not in the grader facts (gap). Q4 a 'no' between 49x and 50x jumps
     from unknown to conflicting; a conflicting carries no degree, so no gentler shape exists on this side; misleads when the protein is in large excess over
     the competitor. Q5 the same fact-gate shape as the pull-down's wash stringency. KEPT.
INCUBATION (MIN_INCUBATION_MIN 15 min removed; FAST 1e8 / SLOW_ASSOCIATION_RATE_PER_M_PER_S 1e6 / EQUILIBRATION_HALF_LIVES 5)  Q1 an apparent KD measured before binding equilibrated (too weak a KD for tight
     binders). Q2 general practice for the 15 to 30 min (Hellman & Fried 2007) but it is a habit, not physics: mixing and settling in an EMSA take seconds, and the
     time to equilibrate is set by the KD (koff = kon KD; Jarmoskaite 2020: several half-lives). Q3 relative: the KD is in the grader facts and so are the incubation and its
     refs; kon is not stated by an EMSA paper, so it is a range, fast 1e8 to slow 1e6 (SLOW is new, owner to confirm, from memory: von Hippel & Berg 1989; Schreiber, Haran
     & Zhou 2009). Q4 the cliff (conflicting below T_FAST, unknown above) is now a curve: d = ln(t / T_FAST) / ln(T_SLOW / T_FAST), the share of the plausible association rates (log
     scale) for which the incubation covers 5 half-lives; t <= T_FAST stays conflicting (the zero end, today's conflict). t >= T_SLOW is full. FLOOR: no absolute floor in the KD
     case (the 15 min was lab practice, and Q4 of the earlier review showed it mislabelled a 20 nM binder at 10 min); with no KD there is no scale: unknown (was conflicting
     below 15 min), so MIN_INCUBATION_MIN is deleted. Q5 the same curve as the other assays that judge an incubation (decision A). CHANGED. 20 nM: T_FAST 0.87 s, T_SLOW 87 s;
     5 pM: T_FAST 57.8 min, T_SLOW 96 h; 10 uM: T_FAST 0.0017 s, T_SLOW 0.17 s.
MAX_PROBE_OVER_KD 1 / PROBE_OVER_KD_ZERO_AGREEMENT 10  Q1 a stoichiometric titration whose apparent KD reports the probe (half-saturation at KD + probe / 2).
     Q2 general practice (probe at or below the KD; Hellman & Fried 2007, Jarmoskaite 2020 'titration regime'). Q3 relative to the paper's own KD: already so.
     Q4 at 1x the apparent KD is about 1.5-fold too weak, at 10x about 6-fold; KD errors are folds, so the degree is on the log of the bias b = 1 + r / 2
     between the kept ends: (ln b(10) - ln b(r)) / (ln b(10) - ln b(1)), r = 3 gives 0.63, r = 5.5 gives 0.34 (was linear 0.78 and 0.5). The old reason for linear ('to stay with the other
     types') holds for every assay, so it is not an assay-specific reason. Q5 FP, MST and Trp use the same log-bias degree and support a tight-binding (quadratic) analysis without
     the ratio. CHANGED: a quadratic fit (DEPLETION_MODELS) is supported with no degree; the ends are kept, the shape between them is log-bias (also for fit_model).
LOW_FACTOR 0.25 / LOW_ZERO_AGREEMENT_FACTOR 1  Q1 an unsampled lower arm (the KD read from one side of the curve). Q2 general practice (0.1x to 10x the KD;
     Pollard 2010, Jarmoskaite 2020); 0.25x is about 20 percent shifted. Q3 relative to the KD: already so. Q4 at 1x half the probe is shifted in the first
     lane. Q5 sixteen assays judge both ends on the one-site occupancy x / (1 + x) between ends kept, the share of the binding curve covered. CHANGED: degree linear in the occupancy
     between 0.25 (0.2) and 1 (0.5): x = 0.5 gives 0.56 (was 0.67).
HIGH_FACTOR 5 / HIGH_ZERO_AGREEMENT_FACTOR 1  Q1 an unreached plateau (KD extrapolated). Q2 general practice (titration to 10x the KD, 5x with slack). Q3
     relative to the KD: already so. Q4 at 1x only half is shifted, the KD is an extrapolation. Q5 the same occupancy scale as the low end and the other assays. CHANGED: degree linear in the
     occupancy between 5 (0.833) and 1 (0.5): x = 2 gives 0.50 (was 0.25), x = 3 gives 0.75 (was 0.5).
MIN_FRACTION_SHIFTED_HIGHEST 80 / FRACTION_SHIFTED_ZERO_AGREEMENT 50 percent  Q1 the same unreached plateau, read from the gel directly. Q2 general practice
     (80 percent is the fraction at about 4x the KD, 50 at the KD; Fried 1989). Q3 should be relative to the fitted plateau (the active fraction of the probe:
     an inactive probe population caps the shift below 100 percent); the plateau is not in the grader facts (gap). Q4 an inactive probe makes a saturated
     titration look unsaturated (conflicting at a 50 percent cap); linear between is adequate otherwise. Q5 no other type reads a fraction at the top. KEPT.
MAX_SHIFTED_SPECIES 1 / ONE_SITE_MODELS  Q1 several complexes (multiple sites, oligomers) fitted with a one-site model: the KD is not one constant. Q2 general
     practice (Fried 1989; a ladder of bands needs a multi-site or cooperative model). Q3 absolute by definition (a count of species against a model). Q4 a
     faint second band makes it conflicting; it is a categorical mismatch, no curve. Q5 SPR's bivalent-analyte check is the same idea. KEPT.
MIN_TITRATION_POINTS 6 / TITRATION_FIT_PARAMETERS 2 (was TITRATION_POINTS_ZERO_AGREEMENT)  Q1 too few lanes to show the shifted fractions follow one
     isotherm. Q2 general practice (8 to 12 protein lanes per gel; six as the full end). Q3 absolute (a count of lanes; the spacing is judged by
     protein_range). Q4 two lanes still give a measured apparent KD (each lane's fraction is normalised by its own free probe), only untested, so
     conflicting misled; a short series is weak, not against. Q5 owner rule: a short series is low partial credit, never conflicting. CHANGED: (n - p + 1) /
     (MIN - p + 1), n at least p: 2 lanes or fewer 0.2 (was conflicting), 3 0.4 (was 0.25), 4 0.6, 5 0.8, 6 1.0; the KD itself counts as one unit of credit.
MIN_REPLICATES 3 / MIN_EXPERIMENTS_FOR_A_SPREAD 2 (was REPLICATES_ZERO_AGREEMENT 1)  Q1 a KD from one gel, which carries the gel-to-gel variation (probe
     batch, gel temperature, dissociation in the run). Q2 general practice (three independent experiments; Cumming et al. 2007 J Cell Biol 177:7). Q3
     absolute (a count). Q4 one gel still gives the KD, so conflicting at one misled; precision of a mean KD over n gels grows as sqrt(n). Q5 owner rule:
     replicates mean precision, sqrt(n / MIN) as in the pull-down, FP, FRET, AlphaScreen, proximity. CHANGED: sqrt(n / 3), 1 gel 0.58 (was conflicting),
     2 gels 0.82 (was 0.5); the 'one gel has no spread' fact moved to the variance: a standard deviation becomes a variance only over at least two experiments.
RANGE REVIEW GAPS ADDED (2026-11-21, the grader now collects them): (1) specific_competition: the protein concentration of the competition reactions
     (competition_protein_concentration). With it and the probe concentration the competitor is judged as a molar excess over the protein
     (MIN_COMPETITOR_OVER_PROTEIN 5); the fixed MIN_COMPETITOR_EXCESS applies only when it is not stated. The unknown / conflicting step stays a step
     (neither carries a degree). (3) saturation: the fitted plateau (plateau_shifted_fraction). The shifted fraction at the top is read as a percent of
     the plateau , on the unchanged 80 / 50 curve. NOT ADDED: the association rate or a time course of the equilibration
     (an EMSA paper almost never reports a rate constant; the time course is already the fact equilibrium_reached, and the assumed kon range 1e6 to 1e8 makes the
     equilibrium degree a share of plausible rates, and conflicting only at the fast end) and the incubation temperature (it shifts kon and koff by a small
     factor for the 4 to 37 C used, much smaller than the assumed range of kon).
Unknown weight: this converter holds none and no degree contains one (the weight for an unstated criterion is literature_resolution's, per type).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_emsa_converted'
CRITERIA_MAP = {'binding_controls': ('specific_competition', 'nonspecific_competition', 'mutant_probe', 'probe_alone_lane', 'nonspecific_protein_control', 'protein_identity'), 'binding_regime': ('equilibrium', 'complex_stability', 'probe_concentration', 'protein_range', 'titration_points'), 'binding_parameter_definition': ('shift_observed', 'single_complex', 'fit_model'), 'calibration_applicability': ('free_probe_quantified', 'saturation'), 'sampling_basis': ('replicates',)}
MIN_COMPETITOR_EXCESS = 50.0  # EXPERT_REVIEW: smallest fold excess of the unlabelled specific probe over the labelled probe at which a shift that is NOT abolished counts against specificity; below it the competitor is too little to compete (the usual EMSA competition uses 50 to 200 fold).
MIN_COMPETITOR_OVER_PROTEIN = 5.0  # EXPERT_REVIEW: used when the protein concentration of the competition reactions and the probe concentration are both stated (the fold excess is then turned into a molar competitor over protein, excess x probe / protein). An unlabelled competitor of the same affinity shares the protein with the labelled probe in proportion to their amounts, so with the competitor at this multiple of the protein, and the protein saturating the probe, about 1 / (1 + 5) = 17 percent of the shift is left: a shift that survives is then evidence against specificity; below it a surviving shift is what a competitor too small to compete leaves. 5 is the conventional 'several fold' (Hellman & Fried 2007 use 50 to 200 fold of the probe, which over a probe at or below the KD and a protein near the KD is the same order). The fixed MIN_COMPETITOR_EXCESS stays for a record that does not state the protein concentration of the competition.
FAST_ASSOCIATION_RATE_PER_M_PER_S = 1e8  # EXPERT_REVIEW: a fast association rate constant for a protein binding its site on a nucleic acid in vitro (measured values mostly 1e6 to 1e8 per M per s, faster only with facilitated diffusion; von Hippel & Berg 1989 J Biol Chem 264:675). The fast end is taken so the time it gives (T_FAST) is the SHORTEST a binder of that KD needs: an incubation at or below it is too short for any usual binder (conflicting, the zero end of the curve), one above it is on the curve towards T_SLOW.
SLOW_ASSOCIATION_RATE_PER_M_PER_S = 1e6  # EXPERT_REVIEW: owner to confirm; citation from memory. A slow association rate constant for a protein binding its DNA site in vitro, the lower end of the usual range 1e6 to 1e8 per M per s (von Hippel & Berg 1989; Schreiber, Haran & Zhou 2009 Chem Rev 109:839 give 1e5 to 1e6 for association without electrostatic steering, slower still when a conformational change gates binding; a protein that must first find its site among nonspecific DNA or that rearranges on binding sits at the slow end). Two decades below the fast end. The time it gives (T_SLOW) is where the incubation covers the half-lives for every plausible rate: full degree.
EQUILIBRATION_HALF_LIVES = 5.0  # EXPERT_REVIEW: half-lives of the approach to equilibrium an incubation must last (5 half-lives reach 97 percent; Jarmoskaite et al. 2020 recommend several, typically 3 to 5, half-lives of the slowest step). Applied to the lane at the KD, which fixes the apparent KD: there k_obs = kon [P] + koff = 2 kon KD.
M_PER_NM = 1e-9  # FIXED_BY_DEFINITION: molar per nanomolar.
S_PER_MIN = 60.0  # FIXED_BY_DEFINITION: seconds per minute.
MAX_PROBE_OVER_KD = 1.0  # EXPERT_REVIEW: the probe concentration must be at most this multiple of the KD for full agreement; above the KD the titration is stoichiometric, the shifted fraction reports the probe concentration and the apparent KD is about half of it (usual rule: probe at or below the KD).
PROBE_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: probe over KD from which the sheet takes the titration as stoichiometric (conflicting); at ten times the KD the shifted fraction only reports the probe concentration; in between the degree falls linearly (the same 1x / 10x ramp as the limiting partner of FP, MST, FRET and Trp).
DEPLETION_MODELS = ('quadratic',)  # EXPERT_REVIEW: the fit models that solve for the depletion of the probe (the quadratic, Morrison-type binding equation), so the probe over the KD does not bias their KD; such a KD is supported on this criterion with no degree, as FP, MST, FRET and Trp treat a handled tight-binding analysis.
PERCENT = 100.0  # FIXED_BY_DEFINITION: percent of the whole. When the fitted plateau (Fried 1989; Jarmoskaite et al. 2020 fit it as a free parameter because part of a probe can be inactive) is stated, the shifted fraction at the highest protein is read as a percent OF THAT PLATEAU, capped at 100, on the unchanged saturation curve (MIN_FRACTION_SHIFTED_HIGHEST / FRACTION_SHIFTED_ZERO_AGREEMENT); with none stated the reference is 100 percent of the probe.
LOW_FACTOR = 0.25  # EXPERT_REVIEW: the lowest protein concentration must be at most this multiple of the KD for full agreement (about 20 percent of the probe shifted; the usual titration starts near 0.1 times the KD).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: lowest protein concentration (multiple of the KD) from which the sheet takes the low end of the curve as not sampled (conflicting); at the KD half of the probe is already shifted.
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest protein concentration must be at least this multiple of the KD for full agreement (about 83 percent of the probe shifted, so that the plateau is defined by data; the usual titration reaches 10 times the KD).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: highest protein concentration (multiple of the KD) at or below which the sheet takes the plateau as not reached (conflicting); at the KD only half of the probe is shifted.
MIN_TITRATION_POINTS = 6  # EXPERT_REVIEW: fewest protein concentrations of a titration for FULL agreement (usual gels have 8 to 12 lanes with protein; a KD and a plateau are poorly defined with fewer than six). Not a cut-off: fewer points get low partial credit (see TITRATION_FIT_PARAMETERS), never conflicting.
TITRATION_FIT_PARAMETERS = 2  # EXPERT_REVIEW: the free parameters of the one-site fit of the shifted fraction, the apparent KD and the plateau; with this many lanes or fewer the curve passes through every lane, so the series checks nothing about the isotherm but still gives a measured apparent KD (each lane's shifted fraction is normalised by that lane's own free probe). Shape: (n - p + 1) / (MIN_TITRATION_POINTS - p + 1), n counted as p when below it: the KD itself is one unit of credit and each lane beyond the p the fit uses up is one more independent check (in an EMSA every lane is a separate binding mixture quantified once), so 2 lanes or fewer 0.2, 3 0.4, 4 0.6, 5 0.8, 6 1.0. A short series is weak evidence, not evidence against: never conflicting (was: conflicting at 2 or fewer, until 2026-11-21).
MIN_FRACTION_SHIFTED_HIGHEST = 80.0  # EXPERT_REVIEW: smallest percent of the probe shifted at the highest protein concentration for a plateau to be reached, for full agreement; below it the KD is extrapolated beyond the data (about the shifted fraction at five times the KD).
FRACTION_SHIFTED_ZERO_AGREEMENT = 50.0  # EXPERT_REVIEW: percent shifted at the highest protein concentration at or below which the sheet takes the plateau as not reached (conflicting); half of the probe shifted means the highest concentration is only the KD; in between the degree rises linearly.
MAX_SHIFTED_SPECIES = 1  # EXPERT_REVIEW: most shifted bands (distinct complexes) that one-site binding describes; more than one shifted species needs a model with more than one site (or Hill) for an apparent KD.
ONE_SITE_MODELS = ('one_site', 'quadratic')  # EXPERT_REVIEW: the fit models that describe one shifted species; several species fitted with one of them have a KD that is not a single constant.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations) for FULL agreement; lanes of one gel do not count. Not a cut-off: below it the degree is sqrt(n / MIN_REPLICATES) (1 gel 0.58, 2 gels 0.82), never conflicting. Why this shape for an EMSA: an EMSA KD varies mainly between gels (probe labelling batch, gel temperature, dissociation during the run), and the mean KD over n independent gels has a standard error falling as 1 / sqrt(n), the same sd^2 / n this converter uses for the variance; one gel still gives the KD.
MIN_EXPERIMENTS_FOR_A_SPREAD = 2  # EXPERT_REVIEW: fewest independent experiments over which a stated standard deviation is a gel-to-gel spread and so becomes a variance of the KD (sd^2 / n); one gel gives no between-gel spread (its SD would be of lanes or of the fit). Was REPLICATES_ZERO_AGREEMENT = 1, the conflicting end of the replicates curve, until 2026-11-21.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'an_emsa_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_emsa_shifted_fraction_is_not_an_attribution_fraction', 'total_signal': 'an_emsa_shifted_fraction_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_emsa_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_emsa_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_specific_competition(native):
    protein, probe = native['competition_protein_nM'], native['probe_nM']
    if protein is not None and probe is not None:
        # the competitor must outnumber the protein it competes for: a molar competitor over protein, not a fold of the probe
        if native['specific_competitor_excess'] * probe / protein < MIN_COMPETITOR_OVER_PROTEIN:
            return _verdict('unknown', [])
        return _verdict('conflicting', list(dict.fromkeys([*native['specific_competition_refs'], *native['competition_protein_refs']])))
    if native['specific_competitor_excess'] < MIN_COMPETITOR_EXCESS:
        return _verdict('unknown', [])      # a competitor in so small an excess is not a test of specificity
    return _verdict('conflicting', native['specific_competition_refs'])


def _equilibration_min(kd_nM, rate=FAST_ASSOCIATION_RATE_PER_M_PER_S):
    """The incubation (minutes) a binder of this KD needs: EQUILIBRATION_HALF_LIVES half-lives of the lane at the KD, k_obs = 2 kon KD, with the fast kon (T_FAST) or, given, the slow one (T_SLOW)."""
    return EQUILIBRATION_HALF_LIVES * math.log(2) / (2 * rate * kd_nM * M_PER_NM) / S_PER_MIN


def _judge_equilibrium(native):
    # no KD: no scale for the time (a time alone is not the paper against equilibrium): unknown
    if native['kd_nM'] is None:
        return _verdict('unknown', [])
    refs = list(dict.fromkeys([*native['incubation_refs'], *native['quantities']['kd']['source_refs']]))
    fast, slow = _equilibration_min(native['kd_nM']), _equilibration_min(native['kd_nM'], SLOW_ASSOCIATION_RATE_PER_M_PER_S)
    if native['incubation_min'] <= fast:
        return _verdict('conflicting', refs)      # even the fastest plausible association has not equilibrated: the zero end of the curve
    # the share of the plausible association rates (on the log scale, between the fast and the slow end) for which the incubation covers the half-lives
    return _verdict('supported', refs, min(1.0, math.log(native['incubation_min'] / fast) / math.log(slow / fast)))


def _depletion_bias(ratio):
    """Apparent KD over true KD when the labelled probe is this multiple of the KD: the half-saturation is at KD + probe / 2."""
    return 1.0 + ratio / 2.0


def _probe_over_kd_degree(value, refs):
    """Conflicting from the zero end; otherwise the degree is the share of the log of the bias between the zero end and the full end: (log b(zero) - log b(r)) / (log b(zero) - log b(full)), 1 at or below the full end (KD errors are folds, judged on the log scale)."""
    if value >= PROBE_OVER_KD_ZERO_AGREEMENT:
        return _verdict('conflicting', refs)
    zero, full = math.log(_depletion_bias(PROBE_OVER_KD_ZERO_AGREEMENT)), math.log(_depletion_bias(MAX_PROBE_OVER_KD))
    return _verdict('supported', refs, min(1.0, (zero - math.log(_depletion_bias(value))) / (zero - full)))


def _occupancy(factor):
    """One-site occupancy of a protein concentration that is this multiple of the KD: x / (1 + x), the share of the binding curve covered."""
    return factor / (1.0 + factor)


def _occupancy_at_most(value, full, zero, refs):
    """_at_most on the occupancy scale."""
    return _at_most(_occupancy(value), _occupancy(full), _occupancy(zero), refs)


def _occupancy_at_least(value, full, zero, refs):
    """_at_least on the occupancy scale."""
    return _at_least(_occupancy(value), _occupancy(full), _occupancy(zero), refs)


def _judge_probe(native):
    if native['fit_model'] in DEPLETION_MODELS:
        return _verdict('supported', native['probe_over_kd_refs'])      # the quadratic fit solves for the probe depletion: the probe over the KD does not bias its KD
    return _probe_over_kd_degree(native['probe_over_kd'], native['probe_over_kd_refs'])


def _judge_protein_range(native):
    refs = native['protein_range_refs']
    low, high = _occupancy_at_most(native['protein_low_over_kd'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, refs), _occupancy_at_least(native['protein_high_over_kd'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, refs)
    if 'conflicting' in (low['status'], high['status']):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(low['degree'], high['degree']))


def _judge_titration_points(native):
    # (n - p + 1) / (MIN_TITRATION_POINTS - p + 1), n counted as p below it: the KD is one unit, each lane beyond the fit's parameters one more check; never conflicting
    lanes = max(native['titration_point_count'], TITRATION_FIT_PARAMETERS)
    degree = (lanes - TITRATION_FIT_PARAMETERS + 1) / (MIN_TITRATION_POINTS - TITRATION_FIT_PARAMETERS + 1)
    return _verdict('supported', native['titration_point_refs'], min(1.0, degree))


def _judge_saturation(native):
    percent, refs = native['fraction_shifted_percent'], native['fraction_shifted_refs']
    if native['plateau_percent'] is not None:      # read against the fitted plateau, not against 100 percent of the probe
        percent, refs = min(PERCENT, percent / native['plateau_percent'] * PERCENT), list(dict.fromkeys([*refs, *native['plateau_refs']]))
    return _at_least(percent, MIN_FRACTION_SHIFTED_HIGHEST, FRACTION_SHIFTED_ZERO_AGREEMENT, refs)


def _judge_single_complex(native):
    if native['shifted_species_count'] <= MAX_SHIFTED_SPECIES:
        return _verdict('supported', native['shifted_species_refs'])
    if native['kd_nM'] is None:
        return _verdict('not_applicable', [])      # several species and no apparent KD: no constant for the criterion to bias
    if native['fit_model'] is None:
        return _verdict('unknown', [])
    return _verdict('conflicting' if native['fit_model'] in ONE_SITE_MODELS else 'supported', native['shifted_species_kd_refs'])


def _judge_fit_model_probe(native):
    return _probe_over_kd_degree(native['probe_over_kd'], native['fit_model_probe_refs'])


def _judge_replicates(native):
    # the precision of the mean KD over n independent gels relative to that over MIN_REPLICATES: sqrt(n / MIN_REPLICATES), capped at 1; never conflicting on the count
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])      # independence not stated: the count may be lanes of one gel (a stated 'no' is the grader's own conflict)
    return _verdict('supported', native['replicate_refs'], math.sqrt(min(max(native['replicate_count'], 0), MIN_REPLICATES) / MIN_REPLICATES))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('specific_competition', 'competition_excess_recorded_for_the_sheet'): _judge_specific_competition, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium,
          ('probe_concentration', 'probe_over_kd_recorded_for_the_sheet'): _judge_probe, ('protein_range', 'protein_range_recorded_for_the_sheet'): _judge_protein_range,
          ('titration_points', 'titration_points_recorded_for_the_sheet'): _judge_titration_points, ('saturation', 'fraction_shifted_recorded_for_the_sheet'): _judge_saturation,
          ('single_complex', 'shifted_species_recorded_for_the_sheet'): _judge_single_complex, ('fit_model', 'one_site_probe_over_kd_recorded_for_the_sheet'): _judge_fit_model_probe,
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
        if _criterion(graded, 'replicates')['status'] != 'supported' or count['value'] < MIN_EXPERIMENTS_FOR_A_SPREAD:      # one gel has no gel-to-gel spread
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_emsa(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'emsa_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'emsa_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    if not quantitative:
        null_components['effect'] = 'qualitative_assay_reports_no_binding_constant'
        null_components['effect_variance'] = 'qualitative_assay_reports_no_binding_constant'
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [member for member in (apply_support(_criterion(graded, m), native['support'][m]) for m in members) if member['status'] != 'not_applicable']
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
    dependence = {'analyte_preparation_ref': preparations['protein_preparation_ref'], 'immobilized_preparation_ref': preparations['probe_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'emsa', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components,
                 'direction_field_support': native['quantities']['kd']['support'] if quantitative else (native['support']['shift_observed'] or [None])[0] if native['interaction'] is not None else None}
    if not quantitative:
        fraction = native['quantities']['fraction_shifted_highest']
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'fraction_shifted': fraction['value'] if fraction['status'] == 'point' else None}
    return converted
