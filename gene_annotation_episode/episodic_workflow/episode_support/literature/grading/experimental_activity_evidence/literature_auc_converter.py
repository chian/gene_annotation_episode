"""AUC converter: turns the AUC grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_auc.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that an AUC
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has a KD (from a concentration series: the weight-average s against the concentration in a velocity run, or a global equilibrium fit). Then the
converter fills the numeric effect as the earlier quantitative types do (quantity_kind 'binding_parameter'):
  effect            the KD in nM (point operand, measurement key auc_kd). The caveats of the method (a KD needs loading concentrations on both sides of it; a fast
                    reversible association gives one reaction boundary) are not changed in the number, they are judged by the criteria (concentration_series,
                    concentration_range, reversibility, stoichiometry, fit_quality) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no KD (a complex species, its s, its mass and its stoichiometry are shown). Then, exactly as the pull-down, EMSA, SEC and dialysis converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the s nor the molar mass is
put into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect'
({'statement', 'support_refs', 'sedimentation_shift_percent'}):
  statement                    'interaction_detected' (a complex is stated), 'interaction_not_detected' (no complex is stated) or 'interaction_not_stated'
  support_refs                 the spans of the fact that states it (empty when not stated)
  sedimentation_shift_percent  how many percent larger the s of the complex is than the s of the larger component alone, or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (AUC criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              components_alone + component_homogeneity + non_binding_control (the controls that show the faster species is a complex of these two
                              proteins and not a component alone, an aggregate or a self-association)
binding_regime                concentration_series + concentration_range + reversibility + equilibrium_reached + multiple_speeds (the association is followed over
                              concentrations on both sides of the KD, it is reversible, and an equilibrium run reached equilibrium and was fitted at several speeds)
binding_parameter_definition  complex_observed + sedimentation_shift + mass + stoichiometry (what the response is: a complex, its s, its mass and its composition)
calibration_applicability     fit_quality + buffer_correction (the fit describes the data; the buffer density and viscosity turn the measurement into a standard s and a mass)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). A continuous comparison is supported with a degree of 1.0 at or beyond its full-agreement limit, falling to 0 at its zero-agreement
limit, and conflicting (no degree) at or beyond that limit, because there the paper's OWN numbers show the standard is not met. Each criterion has its own scale and shape
(the owner's questions below give the reason for each): sedimentation_shift (percent of the larger component's own s, concave), mass (percent deviation, linear),
stoichiometry (the fold away from 1:1, symmetric in A:B and B:A, linear), concentration_range (the fractional saturation the two ends of the series reach, the weaker end
decides) and fit_quality (rmsd per optical unit, linear). The two counts are never conflicting (a short series or a single experiment is less evidence, not evidence
against): concentration_series has the degree count / MIN_CONCENTRATIONS, replicates sqrt(count / MIN_REPLICATES) when the independence is yes, else unknown. A sheet
criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries
it per result). No degree holds an unknown weight: a degree describes a stated value; how much an unstated criterion counts is decided outside this file.

The owner's questions, asked of every researched value (2026-11-21; Q1 what it protects against, Q2 general practice or lab-specific, Q3 absolute or relative scale,
Q4 how badly a wrong value misleads and whether the shape follows that, Q5 consistent with the other binding assays). Method sources: Lebowitz, Lewis & Schuck 2002
Protein Sci 11:2067 (AUC tutorial review); Schuck 2000 Biophys J 78:1606 (c(s)); Schuck 2003 Anal Biochem 320:104 (s_w isotherms); Dam & Schuck 2005 Biophys J 89:651
(reaction boundaries); Cole, Lary, Moody & Laue 2008 Methods Cell Biol 84:143 (SV and SE practice); Zhao, Brautigam, Ghirlando & Schuck 2013 Curr Protoc Protein Sci
20.12 (current SV/SE methods); Zhao et al. 2015 PLoS ONE 10:e0126420 (multi-laboratory s accuracy); Pollard 2010 Mol Biol Cell 21:4061 and Jarmoskaite et al. 2020
eLife 9:e57264 (binding-series design).
  sedimentation_shift (SHIFT_*): Q1 a "complex peak" that is the larger component itself (s within its reproducibility). Q2 general: s of one species is reproducible
    to about 1-2 percent within a run/instrument (Zhao 2015: 0.7 percent CV across 67 instruments after calibration corrections, about 2.5 percent before); 10 percent
    is a clearly separate species. Q3 already relative to the paper's own control (the s of the larger component alone). The full end is now also relative to the
    shift expected for the partner's size (s ~ M^(2/3): a partner a tenth of the mass raises s by about 6.6 percent) when the paper states both component masses
    (grader gap CLOSED: fields component_mass_larger and component_mass_smaller; SHIFT_FULL_FRACTION_OF_EXPECTED, SHIFT_FULL_MIN_OVER_ZERO); without them the absolute 10 percent
    stays. Q4 small partners get partial, not full, credit; the shape was linear, but a change near the noise floor (2 -> 4 percent: from inside to well
    outside the reproducibility) matters far more than one near 10 percent (already resolved): CHANGED to concave (SHIFT_EASE_POWER), values kept. Q5 yes.
  mass (MASS_*): Q1 a faster species that is a homodimer, an aggregate or another stoichiometry, not the A:B complex. Q2 general: c(s) masses rest on a weight-average
    f/f0 and are good to about 10-15 percent; SE masses to about 5 percent (Schuck 2000; Cole 2008). Q3 the zero end should be relative to the smaller component's mass
    (one partner more or less); 50 percent is right only for equal-mass partners. CHANGED when the smaller component's mass is stated (grader gap CLOSED: field
    component_mass_smaller; MASS_FULL_FRACTION_OF_ZERO): zero = smaller mass / theoretical complex mass, full = 0.2 of it; the absolute values stay without the mass. Q4 linear kept: the method's error band
    (10-15 percent) and the distance to the next species (20-50 percent) overlap, so no part of the ramp is flatter. Kept.
  stoichiometry (STOICHIOMETRY_*): Q1 a KD read as a one-site constant when the complex is 2:1. Q2 general (a molar ratio is not read closer than about 10 percent;
    1.5 molecules per one is halfway in counts between 1:1 and 2:1). Q3 the ratio is A over B, but which partner is first is arbitrary, so the scale must be the fold
    max(r, 1/r). MISTAKE: the old distance |r - 1| made 1.5 conflicting but its mirror 0.67 (the same complex named the other way round) got degree 0.42. CHANGED
    to the fold, with the same researched numbers (full 1.1, zero 1.5 molecules per one); linear in the fold, i.e. in the count of the excess partner. Q5 yes.
  concentration_series (MIN_CONCENTRATIONS): Q1 a KD or a reversible association read from too few points of the isotherm. Q2 general: three loading concentrations
    (with several speeds) is the classical SE design (Cole 2008, Zhao 2013); an s_w isotherm needs points across the KD (Schuck 2003). Q3 a count, absolute; its
    placement relative to the KD is concentration_range. A stated 'no series' (fact concentration_series_measured) with no count is now a series of one
    (grader rule CHANGED: recorded as count 1, not conflicting). Q4/Q5 MISTAKE: one concentration was conflicting, which made binding_regime conflicting for the most common
    qualitative AUC experiment (one c(s) run of the mixture). A short series is less evidence, never evidence against: CHANGED to count / MIN_CONCENTRATIONS (each
    loading concentration is one more equal point on the isotherm): 1 -> 1/3, 2 -> 2/3, 3 -> 1. MIN_CONCENTRATIONS = 3 kept; CONCENTRATIONS_ZERO_AGREEMENT removed.
  concentration_range (LOW_/HIGH_OVER_KD_*): Q1 a KD extrapolated from a series all on one side of it (all free or all bound). Q2 general for any binding series:
    about 0.1x to 10x KD, i.e. about 20 to 80 percent saturation (Pollard 2010; Jarmoskaite 2020), 0.2x/5x keeps a factor of 2 slack. Q3 already relative to the
    paper's own KD. Q4 the ramp was linear in c/KD, so the two ends were judged unequally (low end at 0.5x KD got 0.63, high end at 2x KD only 0.25), though the
    isotherm is symmetric (theta at KD/x and at x*KD are mirror images). CHANGED: linear in the fractional saturation theta = r/(1 + r) each end reaches (values
    kept: full at theta 1/6 and 5/6, zero at 1/2). This is steep near the KD (moving the low end from KD to KD/2 opens half the free branch) and gentle near the
    full end. theta assumes the titrated partner is in excess over the other. NOT ADDED (equimolar dilution series): with both partners at the same total c the complex
    fraction at c = KD is about 38 percent instead of 50, a shift of the scale smaller than the factor of 2 of slack already kept in 0.2x and 5x, and the series design
    would be unreliable to extract.
  fit_quality (FIT_RMSD_*): Q1 a mass or KD from a model that does not describe the data. Q2 the rule (rmsd comparable to the optical noise) is general practice
    (Schuck 2000; Zhao 2013); the noise values (0.005 AU, 0.003 fringes) are instrument-generation specific (XL-A/XL-I; the Optima is quieter). Q3 an rmsd relative
    to the loading signal (plateau absorbance or fringes) or to the noise stated in the paper would be better; neither is recorded. NOT ADDED: the rmsd is judged against the
    noise of the optics, a property of the instrument and not of the loading, so the absolute scale is the physically right one; the paper rarely states either quantity, so a field
    would almost always be unavailable. Q4 linear between
    1x and 4x noise kept (rmsd/noise is about sqrt(reduced chi^2); 1.5-2x is common practice, 4x is a misfit). Kept.
  replicates (MIN_REPLICATES): Q1 a result from one preparation or one run (one aggregated prep, one mis-calibrated cell). Q2 three independent experiments is the
    common reporting minimum; scans of one cell are not replicates. Q3 a count, absolute. Q4/Q5 MISTAKE: one experiment was conflicting and the curve was the
    precision of a spread, sqrt((n - 1)/(MIN - 1)). The binding assays treat replicates as the precision of the mean: CHANGED to sqrt(min(n, MIN) / MIN)
    (1 -> 0.58, 2 -> 0.82, 3 -> 1), supported when the independence is yes. A standard deviation still becomes a variance only from two or more experiments
    (MIN_COUNT_FOR_A_SPREAD). REPLICATES_ZERO_AGREEMENT removed.
  Unstated criteria (SOP step 3 item 4; not applied in this file): AUC reads absolute quantities (s and mass from hydrodynamics, no calibration curve), with trusted
    reference values (s and mass from sequence), so unstated technical details (buffer correction, rmsd, equilibrium, speeds) are benign typical practice of the
    SEDFIT/SEDPHAT era and could count near the KD weight. Unstated components_alone, component_homogeneity or non_binding_control are not benign: without them a
    peak at a larger s cannot be assigned to the A:B complex, so they deserve a much lower weight. Proposal for the owner; the weight lives outside this converter.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree (the
mass criterion's degree from the deviation, for example); direct leaves it unchanged. Support never changes a status. variance_correspondence takes
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

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_auc_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_auc_converted_v1'
CRITERIA_MAP = {'binding_controls': ('components_alone', 'component_homogeneity', 'non_binding_control'), 'binding_regime': ('concentration_series', 'concentration_range', 'reversibility', 'equilibrium_reached', 'multiple_speeds'), 'binding_parameter_definition': ('complex_observed', 'sedimentation_shift', 'mass', 'stoichiometry'), 'calibration_applicability': ('fit_quality', 'buffer_correction'), 'sampling_basis': ('replicates',)}
SHIFT_FULL_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: smallest increase (percent) of the s of the complex over the s of the larger component alone that the sheet takes as a clear complex peak; binding of a partner a fifth of the mass of the larger component raises s by about 10 percent, and the s of one species is reproducible to 1 to 2 percent.
SHIFT_ZERO_AGREEMENT_PERCENT = 2.0  # EXPERT_REVIEW: increase (percent) at or below which the s of the complex cannot be told from the larger component alone (the reproducibility of s); a smaller or negative shift is conflicting.
SHIFT_FULL_FRACTION_OF_EXPECTED = 0.5  # EXPERT_REVIEW: when the masses of both components are stated, the shift that gets full credit is this fraction of the shift a compact 1:1 complex would show, s ~ M^(2/3) (Svedberg; a partner a tenth of the mass raises s by about 6.6 percent), capped at SHIFT_FULL_AGREEMENT_PERCENT. One half because a complex is usually less compact than the sphere of the same mass (a frictional ratio above that of its components), which lowers the s it reaches by tens of percent of the expected rise (Lebowitz 2002; Zhao 2013).
SHIFT_FULL_MIN_OVER_ZERO = 2  # EXPERT_REVIEW: the full-credit shift is never set below this multiple of SHIFT_ZERO_AGREEMENT_PERCENT: a shift of two reproducibility widths (s reproducible to 1 to 2 percent, Zhao 2015) is the smallest that can be told apart from the component alone, however small the partner.
SHIFT_EASE_POWER = 2  # EXPERT_REVIEW: the shape between the two shift limits, degree = 1 - (1 - share) ** SHIFT_EASE_POWER: steep at the noise floor (each percent there moves the shift from inside to well outside the reproducibility of s), flat as it joins full credit (a peak already resolved gains nothing from another percent). 2 is the gentlest power whose slope is zero at the full end (no kink).
MASS_FULL_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: largest absolute deviation (percent) of the molar mass of the complex from the AUC fit from the mass the complex should have that the sheet takes as agreement; the mass from c(s) or from a global equilibrium fit is accurate to about 5 to 10 percent.
MASS_FULL_FRACTION_OF_ZERO = 0.2  # EXPERT_REVIEW: when the mass of the smaller component is stated, the zero-agreement deviation is the deviation of one partner more or less, smaller component / theoretical complex mass, capped at MASS_ZERO_AGREEMENT_PERCENT (equal partners: 50 percent), and the full-agreement deviation is this fraction of it, capped at MASS_FULL_AGREEMENT_PERCENT: the ratio 10 to 50 of the researched values for equal partners, kept for every partner size (a partner a tenth of the mass: zero at 9 percent, full at 1.8 percent, which c(s) masses cannot reach, so the credit is partial throughout, as the method deserves).
MASS_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: absolute deviation (percent) from which the sheet takes the mass as disagreeing (conflicting); half the mass or less, or 1.5 times or more, is a different species; the degree falls linearly in between.
STOICHIOMETRY_FULL_AGREEMENT_FOLD = 1.1  # EXPERT_REVIEW: largest fold max(r, 1/r) of the stated molar ratio r away from 1:1 at which a KD is the one-site constant (a ratio is not read more closely than 10 percent). The fold, not |r - 1|, because which partner is named first is arbitrary: A:B = 1.5 and B:A = 0.67 are the same complex.
STOICHIOMETRY_ZERO_AGREEMENT_FOLD = 1.5  # EXPERT_REVIEW: fold from which the complex is taken as not 1:1 (conflicting): 1.5 molecules of one partner per one of the other is halfway, in counts, between 1:1 and 2:1 (or 1:2); the degree falls linearly in the fold (the count of the excess partner) in between.
MIN_CONCENTRATIONS = 3  # EXPERT_REVIEW: loading concentrations at which concentration_series reaches FULL credit, the fewest that show the concentration dependence of a reversible association (one gives a mass or an s, two a single slope; three show curvature and a plateau; three concentrations is the classical sedimentation equilibrium design). Below it the degree is count / MIN_CONCENTRATIONS (each loading concentration is one more equal point on the isotherm): one concentration is low partial credit (1/3), never conflicting.
LOW_OVER_KD_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest ratio of the lowest loading concentration to the KD at which the series defines the free-component end of the isotherm (0.1x KD with a factor of 2 slack; fractional saturation 1/6).
LOW_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the lowest loading concentration to the KD from which the series does not reach below the KD (half saturated or more in the whole series): conflicting; in between the degree is linear in the fractional saturation r / (1 + r).
HIGH_OVER_KD_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest ratio of the highest loading concentration to the KD at which the series reaches the saturated end of the isotherm (10x KD with a factor of 2 slack; fractional saturation 5/6, the mirror of the low end).
HIGH_OVER_KD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the highest loading concentration to the KD up to which the series does not reach above the KD (never more than half saturated): conflicting; in between the degree is linear in the fractional saturation r / (1 + r).
FIT_RMSD_FULL_AGREEMENT = {'AU': 0.005, 'fringes': 0.003}  # EXPERT_REVIEW: largest rmsd of the fit taken as noise-limited, per unit (the noise of the absorbance optics is about 0.005 absorbance units, that of the interference optics about 0.003 fringes).
FIT_RMSD_ZERO_AGREEMENT = {'AU': 0.02, 'fringes': 0.012}  # EXPERT_REVIEW: rmsd of the fit, per unit, from which the sheet takes the fit as not describing the data (four times the noise): conflicting; the degree falls linearly in between.
MIN_REPLICATES = 3  # EXPERT_REVIEW: independent experiments (separate experiments on separate days or preparations; scans of one cell do not count) at which replicates reach FULL credit. Below it the degree is the precision of the mean relative to that at MIN_REPLICATES, sqrt(count / MIN_REPLICATES) (the standard error of a mean falls as 1 / sqrt(n)): one experiment 0.58, two 0.82; never conflicting.
MIN_COUNT_FOR_A_SPREAD = 2  # FIXED_BY_DEFINITION: a standard deviation between experiments needs at least two of them; with fewer a stated SD is not the spread of independent experiments and is not turned into a variance.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'an_auc_run_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_auc_complex_species_is_not_an_attribution_fraction', 'total_signal': 'an_auc_complex_species_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_auc_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_auc_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _shift_full(native):
    """The shift that gets full credit: SHIFT_FULL_AGREEMENT_PERCENT, or lower when the partner is small (stated masses of the two components)."""
    larger, smaller = native['component_mass_larger'], native['component_mass_smaller']
    if larger is None or smaller is None:
        return SHIFT_FULL_AGREEMENT_PERCENT
    expected = (((larger + smaller) / larger) ** (2 / 3) - 1) * 100      # s ~ M^(2/3) at a constant shape and density
    return max(SHIFT_FULL_MIN_OVER_ZERO * SHIFT_ZERO_AGREEMENT_PERCENT, min(SHIFT_FULL_AGREEMENT_PERCENT, SHIFT_FULL_FRACTION_OF_EXPECTED * expected))


def _judge_shift(native):
    share = _degree(native['shift_percent'], _shift_full(native), SHIFT_ZERO_AGREEMENT_PERCENT)
    return _graded(native['shift_refs'], None if share is None else 1 - (1 - share) ** SHIFT_EASE_POWER)      # concave: steep at the noise floor, flat at full credit


def _judge_mass(native):
    zero, full = MASS_ZERO_AGREEMENT_PERCENT, MASS_FULL_AGREEMENT_PERCENT
    if native['mass_smaller_component'] is not None:      # one partner more or less is the next species
        zero = min(zero, native['mass_smaller_component'] / native['mass_theoretical'] * 100)
        full = min(full, MASS_FULL_FRACTION_OF_ZERO * zero)
    return _graded(native['mass_support_refs'], _degree(abs(native['mass_deviation_percent']), full, zero))


def _judge_stoichiometry(native):
    ratio = native['stoichiometry_ratio']
    fold = max(ratio, 1 / ratio)      # A:B and B:A are the same complex
    return _graded(native['stoichiometry_refs'], _degree(fold, STOICHIOMETRY_FULL_AGREEMENT_FOLD, STOICHIOMETRY_ZERO_AGREEMENT_FOLD))


def _judge_concentrations(native):
    count = native['concentration_count']
    if count < 1:
        return _verdict('unknown', [])      # not a count of loading concentrations (the extraction refuses numbers at or below 0)
    # each loading concentration is one more equal point on the isotherm; a short series is low partial credit, never conflicting
    return _verdict('supported', native['concentration_count_refs'], min(1.0, count / MIN_CONCENTRATIONS))


def _saturation(over_kd):
    """The fractional saturation c / (c + KD) at a loading concentration c = over_kd * KD (the partner titrated in excess)."""
    return over_kd / (1 + over_kd)


def _judge_range(native):
    # linear in the saturation each end reaches: the two ends are mirror images on the isotherm (theta 1/6 and 5/6 full, 1/2 zero)
    low = _degree(_saturation(native['low_over_kd']), _saturation(LOW_OVER_KD_FULL_AGREEMENT), _saturation(LOW_OVER_KD_ZERO_AGREEMENT))
    high = _degree(_saturation(native['high_over_kd']), _saturation(HIGH_OVER_KD_FULL_AGREEMENT), _saturation(HIGH_OVER_KD_ZERO_AGREEMENT))
    return _graded(native['range_refs'], low, high)


def _judge_fit(native):
    unit = native['fit_rmsd_unit']
    return _graded(native['fit_refs'], _degree(native['fit_rmsd'], FIT_RMSD_FULL_AGREEMENT[unit], FIT_RMSD_ZERO_AGREEMENT[unit]))


def _judge_replicates(native):
    count = native['replicate_count']
    if count < 1 or native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])      # independence not stated (the count alone does not say independent experiments), or not a count of experiments
    # the precision of the mean relative to that at MIN_REPLICATES; one experiment is low partial credit, never conflicting
    return _verdict('supported', native['replicate_refs'], math.sqrt(min(count, MIN_REPLICATES) / MIN_REPLICATES))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('sedimentation_shift', 'sedimentation_shift_recorded_for_the_sheet'): _judge_shift, ('mass', 'mass_deviation_recorded_for_the_sheet'): _judge_mass,
          ('stoichiometry', 'stoichiometry_recorded_for_the_sheet'): _judge_stoichiometry, ('concentration_series', 'concentration_count_recorded_for_the_sheet'): _judge_concentrations,
          ('concentration_range', 'concentration_range_recorded_for_the_sheet'): _judge_range, ('fit_quality', 'fit_rmsd_recorded_for_the_sheet'): _judge_fit,
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
        if _criterion(graded, 'replicates')['status'] != 'supported' or count['value'] < MIN_COUNT_FOR_A_SPREAD:
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_auc(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'auc_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'auc_variance:' + ref, variance_refs, 'derived', 'kd_spread')
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
    converted = {'version': VERSION, 'experiment_type': 'auc', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities']['kd']['support']      # the support class of the KD operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'sedimentation_shift_percent': native['shift_percent']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['complex_observed'][0]      # the support class of the fact complex_detected, the one field the statement is derived from
    return converted
