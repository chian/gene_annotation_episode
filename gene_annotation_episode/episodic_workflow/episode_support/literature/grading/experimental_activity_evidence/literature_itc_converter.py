"""ITC converter: turns the ITC grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to ITC, deterministic. Input: the result of grade_itc.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the sheet
itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR converter fills), the dependence keys the
merger needs, and for every sheet component an ITC KD cannot honestly fill,
the reason it stays null.

Quantities filled
-----------------
effect            the ITC KD in nM (point operand), only when the source
                  gave a KD as a point value. Otherwise null.
effect_variance   variance of that KD estimate, nM_squared, only when the
                  source's spread allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n, and only when the
                  replicate_titrations_independent criterion is supported;
                  confidence_interval -> not converted (needs its level and
                  degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (same four keys as the SPR converter):
analyte_preparation_ref = the syringe preparation, immobilized_preparation_ref
= the cell preparation (the partner held in the vessel), surface_ref = None
(ITC has no surface), dataset_ref = the dataset.

Criteria mapping (ITC criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              heat_of_dilution_control + buffer_matching
binding_regime                c_value_window + injections_sufficient +
                              temperature_stated_and_controlled
binding_parameter_definition  fit_model_appropriate + thermodynamic_consistency
binding_species               concentration_accuracy_and_active_fraction
calibration_applicability     stoichiometry_consistency
sampling_basis                replicate_titrations_independent
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and
hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement). Every researched value is a
named EXPERT_REVIEW constant below, with its reason; none is a pass/fail cut:
concentration_accuracy_and_active_fraction judged on n / expected n (full
agreement from N_OVER_EXPECTED_MIN to N_OVER_EXPECTED_MAX), unknown when a
fact is unknown; c_value_window judged on c (full agreement from C_VALUE_MIN to
C_VALUE_MAX, falling linearly in log10(c) to none one decade outside each end);
injections_sufficient judged on the injection count (full
agreement from MIN_INJECTIONS, partial credit below it, falling as the square
root of the points beyond the fitted parameters to no credit at
INJECTIONS_ZERO; a short run is weaker evidence, supported with that low
degree, never conflicting);
temperature_stated_and_controlled judged on the temperature (full agreement
from TEMPERATURE_MIN_K to TEMPERATURE_MAX_K, falling linearly to none at the
instrument limits TEMPERATURE_ZERO_MIN_K and TEMPERATURE_ZERO_MAX_K), then by
the control answer (yes supported, unknown unknown, not_applicable not
applicable); replicate_titrations_independent judged on the replicate count
(supported with degree min(1, sqrt(n / MIN_REPLICATE_TITRATIONS)) when the
independence is yes, never conflicting for a stated count; independence not
stated: unknown; stated no: the grader's conflicting); stoichiometry_consistency: when
the paper states the expected n, the fitted n against it is judged once, by
concentration_accuracy_and_active_fraction, and this criterion only asks that n was
fitted freely (supported, no degree); when no expected n is stated, judged on the
fitted n (full agreement from STOICHIOMETRY_MIN, conflicting at STOICHIOMETRY_ZERO_MIN)
and on its distance from a multiple of STOICHIOMETRY_STEP (full agreement up to
STOICHIOMETRY_STEP_TOLERANCE, no credit but never conflicting at
STOICHIOMETRY_STEP_ZERO); unknown when the free fit is not stated yes;
thermodynamic_consistency judged on the gap of the two free
energies (full agreement up to DG_TOLERANCE_KJ_PER_MOL). A judged comparison
is supported with a degree of 1.0 at its full-agreement limit, falling
gradually (linearly for the windows and the gap, linearly in log10(c) for the
c value, as a square root for the counts) to 0 at its zero-agreement limit (the
*_ZERO* constants), and, for a value (not a count, not the distance from a simple
ratio), conflicting (no degree) at or beyond that limit.

The owner's questions, asked of every researched value (2026-11-21; Q1 what it
protects against, Q2 general practice or lab/instrument-specific, Q3 absolute or
relative scale, Q4 how badly a wrong value misleads and whether the shape follows
that, Q5 consistent with the other binding assays). Method sources, cited from
memory and not checked on the web: Wiseman, Williston, Brandts & Lin 1989 Anal
Biochem 179:131 (the c window); Turnbull & Daranas 2003 JACS 125:14859 (low c);
Velazquez-Campoy & Freire 2006 Nat Protoc 1:186 (high affinity, displacement);
Pierce, Raman & Nall 1999 Methods 19:213 (ITC practice); Myszka et al. 2003 J Biomol
Tech 14:247 (ABRF-MIRG inter-laboratory ITC study); Mizoue & Tellinghuisen 2004
Anal Biochem 326:125 (first-injection artefact); Tellinghuisen 2005 J Phys Chem B
109:20027 (injection number and size); Markova & Hallen 2004 Anal Biochem 331:77
(single-injection ITC); Fukada & Takahashi 1998 Proteins 33:159 (buffer ionization
enthalpies).
  n_over_expected (N_OVER_EXPECTED_*): Q1 an inactive fraction or a concentration
    error. With n fitted freely an error in the CELL concentration (or an inactive
    cell fraction) is absorbed by n and leaves KD and dH per mole of titrant
    unbiased; an error in the SYRINGE concentration (overstated or impure titrant)
    biases KD and dH as well, and it shows as a HIGH n. Q2 general: n within about
    20-30 percent of the expected value is routine for good preparations (Pierce
    1999; Myszka 2003). Q3 already relative to the paper's own expected n. Q4 the
    asymmetry follows the physics: the low side (cell, KD unbiased) is lenient, zero
    at a 3.3-fold deficit; the high side (syringe, KD biased, or a second site) is
    stricter, zero at 2-fold, the next simple stoichiometry. Linear kept: no point
    of either side matters more than another. Q5 yes (relative to the paper's own
    value, conflicting only at the far zero end). Kept.
  c_value_window (C_VALUE_*): Q1 a KD not determined by the isotherm: at low c the
    curve is flat and KD is correlated with n and dH; at high c the curve is a step
    and gives only a limit on KD. Q2 general: 1 < c < 1000 (Wiseman 1989); c = 0.1
    and 10^4 are one decade beyond each end, where direct titration fails without
    extra conditions (Turnbull & Daranas 2003 below; displacement titration above,
    Velazquez-Campoy & Freire 2006). Q3 already relative to the paper's own KD and
    cell concentration. Q4 MISTAKE: the ramp was linear in c, so 0.1 -> 0.3 (a
    tripling of c) earned only 0.22 and 1000 -> 2000 lost as much as 9000 -> 10000,
    although the shape of the isotherm, and the KD precision, change per factor of
    c, not per unit. CHANGED to linear in log10(c), values kept: each factor of 10
    beyond the window costs the whole credit, c = 0.32 and c = 3200 both get 0.5.
    Turnbull & Daranas show a low-c KD is still good when the titration reaches
    near saturation. GAP CLOSED (final_molar_ratio collected): the grader records
    the final total ligand over KD (r c / n); the low zero end moves from
    C_VALUE_ZERO_MIN down to C_VALUE_ZERO_MIN_SATURATED (one decade) smoothly with
    log10 of it between SATURATION_ZERO_OVER_KD and SATURATION_FULL_OVER_KD; with
    no ratio stated the window is as before. Not done: n fixed from outside, which
    the stoichiometry criterion judges as a fixed n. Q5 yes (as the SPR/AUC series bracketing, scaled by
    the paper's own KD).
  injections_sufficient (MIN_INJECTIONS, INJECTIONS_ZERO): Q1 an isotherm sampled
    by too few points to define its transition. Q2 15-30 injections is general
    practice on large-cell instruments (Pierce 1999); low-volume cells commonly run
    13-19, and Tellinghuisen 2005 finds the precision insensitive to the number
    beyond about 10, so 15 is the conservative general value and the sqrt shape
    keeps 12-14 near 0.9. INJECTIONS_ZERO = 3 is the three fitted parameters (n, KD,
    dH); if the count includes the small first injection that is routinely
    discarded (Mizoue & Tellinghuisen 2004) the true no-dof point is 4: the score
    then misleads by at most 0.29 at four injections and under 0.05 above eight,
    a range no real incremental run uses. Q3 absolute; the points that inform KD
    are those in the transition, which depends on c and the injection volumes
    (grader gap). A single-injection or continuous titration (Markova & Hallen 2004)
    has one injection but hundreds of points: GAP CLOSED (titration_mode collected),
    a stated single_injection or continuous mode makes the criterion not applicable
    (dropped from binding_regime); an unstated mode is judged on the count as before. Q4 sqrt: steep at 4-6, gentle at 12-14. Q5 yes (a short count is
    low partial credit, never conflicting). Kept.
  temperature_stated_and_controlled (TEMPERATURE_*): Q1 a mis-transcribed or
    implausible temperature (a C/K or unit error) and a measurement where the protein
    is not native. Q2 the 5-50 C window is general practice; 2-80 C are the limits of
    the common instruments (MicroCal VP/ITC200/PEAQ, TA Nano ITC): instrument-specific
    but shared by all current ones. Q3 the upper end would better be relative to the
    protein's melting temperature (grader gap); absolute kept. Q4 inside the window
    nothing changes, a KD is valid at the temperature it was measured; outside, a
    wrong value misleads little, so a linear ramp to the instrument limits (steep
    below, 3 K; gentle above, 30 K) fits; at or beyond a limit the stated value is not
    a possible ITC run (conflicting). Q5 yes. Kept. (Note, not changed: a stated
    temperature with the control answer unknown stays unknown, although ITC is
    isothermal by construction; that rule is outside the researched values.)
  replicate_titrations_independent (MIN_REPLICATE_TITRATIONS): Q1 a KD from one
    preparation or one titration (one bad loading, one mis-determined
    concentration). Q2 three independent titrations is the common reporting minimum
    (Myszka 2003 shows inter-run spread well above the fit error). Q3 a count,
    absolute. Q4/Q5 min(1, sqrt(n / 3)), the precision of a mean, the shared binding
    rule; never conflicting for a stated count. Kept.
  stoichiometry_consistency (STOICHIOMETRY_*): Q1 a fitted n that is not a physical
    stoichiometry: a gross concentration or activity error, a fit at too low c, or
    the wrong model. Q2 the size floor is general (n far below any expected ratio
    means the heat is not stoichiometric binding); the lattice of halves is NOT a
    method standard: practice compares n with the stoichiometry expected from the
    biology, n = 0.75 is a routine 75 percent active protein, and 1/3 or 1/4 (one
    ligand per trimer or tetramer) are real. Q3 the scale should be relative to the
    paper's stated expected n, which the grader holds (expected_stoichiometry,
    n_over_expected). MISTAKES: (a) with the expected n stated the same deviation
    was judged twice, once relative (binding_species) and once on the absolute
    lattice (calibration_applicability); (b) n = 0.75 or 1.25, exactly between two
    halves, was conflicting, though a cell-side deviation leaves KD unbiased (see
    n_over_expected) and ambiguity is not evidence against. CHANGED: with the
    expected n stated, only the free fit is asked here (supported, no degree; the
    deviation counts once, in binding_species); with no expected n, the lattice is a
    fallback with the same values and linear ramp, but its zero end is no credit
    (degree 0), never conflicting; the size floor (n <= 0.2 conflicting) is kept.
    Q4 linear kept for both. Q5 yes (one fact counted once; conflicting only at the
    far end of a ramp whose zero end means the paper's numbers are wrong).
  thermodynamic_consistency (DG_*): Q1 an internally inconsistent set of reported
    thermodynamics (a kcal/kJ mix-up, a sign error, -T dS reported as dS, values
    from different fits): dG = RT ln KD and dH - T dS come from one fit and agree
    by definition. Q2 general (an identity); 2 kJ/mol covers rounding of each term
    and averaging over replicates (mean of ln KD vs ln of mean KD). Q3 absolute in
    kJ/mol is the right scale: the gap is a fold error in KD, exp(gap / RT): 2 kJ/mol
    about 2-fold, 10 kJ/mol about 60-fold; RT varies only 10 percent over 5-50 C.
    Q4 linear between them; a paper reporting a buffer-ionization-corrected
    (intrinsic) dH beside an observed KD has a legitimate gap of several kJ/mol
    (Fukada & Takahashi 1998), which the gentle 10 kJ/mol zero end tolerates
    GAP CLOSED (enthalpy_buffer_ionization_corrected collected): a dH stated as
    corrected for buffer ionization is not the observed dH of the fit, so the
    identity does not apply (not applicable); stated no or not stated is compared as
    before, the 10 kJ/mol end kept (no tighter researched value is available for a
    stated observed dH). Q5 yes.
  Grader gaps NOT closed (decided not worth collecting): (3) the protein's melting
    temperature for the upper temperature end: an ITC paragraph almost never states
    it (it comes from a separate DSF/CD measurement), and inside 5-50 C, where nearly
    all ITC is run, a mesophilic protein is native; the absolute window stays.
    (4) the oligomeric state of the cell component, to recognise ratios such as 1/3
    without a stated expected n: the expected n, when the paper gives it, is
    already collected (expected_stoichiometry) and judged relative; an oligomeric
    state alone does not fix the ligand : partner ratio, so working an expected n out
    of it would be an inference the quote-only extraction may not make. (5) separate
    concentration-determined facts for the cell and the syringe: the cell and syringe
    concentrations are collected, and the passage that says how each was determined
    nearly always says both in one sentence; the joint fact stays, the n deviation
    is judged relative to the expected n with its physical asymmetry already in the
    N_OVER_EXPECTED ends.
  Unstated criteria (SOP step 3 item 4; not applied in this file): ITC is absolute
    and self-calibrated; an unstated c (no cell concentration) is the real gap,
    see A105_ASSAY_CALIBRATION_DETAILS.md. No degree here holds an unknown weight.
A sheet criterion that is supported carries the smallest degree of its members
that have one (the sheet reads no degree; it travels with the interpretation and
the merger carries it per result).
Combined status: any conflicting -> conflicting; else any unknown -> unknown;
else supported. not_applicable members are dropped; a sheet criterion whose
members are all not_applicable is not selected. Sheet criteria with no ITC
counterpart are not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_itc_converted_v1'
CRITERIA_MAP = {'binding_controls': ('heat_of_dilution_control', 'buffer_matching'), 'binding_regime': ('c_value_window', 'injections_sufficient', 'temperature_stated_and_controlled'), 'binding_parameter_definition': ('fit_model_appropriate', 'thermodynamic_consistency'), 'binding_species': ('concentration_accuracy_and_active_fraction',), 'calibration_applicability': ('stoichiometry_consistency',), 'sampling_basis': ('replicate_titrations_independent',)}
N_OVER_EXPECTED_MIN = 0.7  # EXPERT_REVIEW: fitted n / expected n below this suggests an inactive fraction or a concentration error; full agreement from it. The low side is the more lenient (zero at a 3.3-fold deficit vs 2-fold excess): a low n is mostly a cell-side error, absorbed by a freely fitted n (KD unbiased), a high n a syringe-side error that biases KD and dH.
N_OVER_EXPECTED_ZERO_MIN = 0.3  # EXPERT_REVIEW: fitted n under a third of the expected n is mostly inactive protein or a gross concentration error (no agreement); falls linearly from N_OVER_EXPECTED_MIN.
N_OVER_EXPECTED_MAX = 1.3  # EXPERT_REVIEW: fitted n / expected n above this suggests a concentration error or non-specific heat; full agreement up to it.
N_OVER_EXPECTED_ZERO_MAX = 2.0  # EXPERT_REVIEW: fitted n at twice the expected n or more is another stoichiometry or a gross concentration error (no agreement); falls linearly from N_OVER_EXPECTED_MAX.
C_VALUE_MIN = 1.0  # EXPERT_REVIEW: below c = 1 the curve is too flat and KD is poorly determined; full agreement from it.
C_VALUE_ZERO_MIN = 0.1  # EXPERT_REVIEW: at c = 0.1 (a decade below the Wiseman window) the isotherm is a nearly straight line and KD is not determined by direct titration (no agreement); falls linearly in log10(c) from C_VALUE_MIN (the isotherm's shape and the KD precision change per factor of c, not per unit).
C_VALUE_ZERO_MIN_SATURATED = 0.01  # EXPERT_REVIEW: the low-c zero end when the titration reached its plateau (the final total ligand is SATURATION_FULL_OVER_KD times KD or more): one decade lower, c = 0.01. A low-c isotherm still fixes KD when it is titrated to a large ligand excess so that the plateau, hence n and dH, is defined (Turnbull & Daranas 2003, from memory, not checked); it stays much weaker evidence than c >= 1, so the zero end moves by one decade only, and it moves smoothly with the saturation share (no step).
SATURATION_ZERO_OVER_KD = 1.0  # EXPERT_REVIEW: final total ligand equal to KD or less: at most half the sites are bound at the end, the plateau is not reached and the low-c zero end does not move. In the ITC units, final total ligand / KD = r x [cell] / KD = r c / n for the final molar ratio r.
SATURATION_FULL_OVER_KD = 10.0  # EXPERT_REVIEW: final total ligand ten times KD or more: about 90 percent of the sites bound at the end (bound fraction L / (L + KD)), the plateau is defined; the share of the zero-end shift rises in log10 of the final ligand over KD between SATURATION_ZERO_OVER_KD and this (a binding saturation falls per factor of concentration, as c itself).
C_VALUE_MAX = 1000.0  # EXPERT_REVIEW: above c = 1000 the curve is a step and only a limit on KD is determined; full agreement up to it.
C_VALUE_ZERO_MAX = 10000.0  # EXPERT_REVIEW: at c = 10000 (a decade above the window, where displacement titration is needed) the curve is a step with no usable shape (no agreement); falls linearly in log10(c) from C_VALUE_MAX.
MIN_INJECTIONS = 15  # EXPERT_REVIEW: fewest injections for a defined binding isotherm; full agreement from it (no longer a pass/fail cut: fewer injections get partial credit).
INJECTIONS_ZERO = 3  # EXPERT_REVIEW: the one-set-of-sites isotherm fits three parameters (n, KD, dH); with that many injections or fewer the fit has no residual degree of freedom and KD is not determined (no credit: degree 0, supported, never conflicting: a short run is weaker evidence, not evidence against).
TEMPERATURE_MIN_K = 278.15  # EXPERT_REVIEW: lowest temperature (5 C) of the usual calorimeter experiment; full agreement from it.
TEMPERATURE_ZERO_MIN_K = 275.15  # EXPERT_REVIEW: 2 C, the lowest operating temperature of the common commercial ITC instruments (MicroCal VP-ITC / PEAQ-ITC, TA Nano ITC: 2-80 C); a stated temperature at or below it is not a plausible ITC measurement (no agreement); falls linearly from TEMPERATURE_MIN_K.
TEMPERATURE_MAX_K = 323.15  # EXPERT_REVIEW: highest temperature (50 C) of the usual calorimeter experiment on mesophilic proteins; full agreement up to it.
TEMPERATURE_ZERO_MAX_K = 353.15  # EXPERT_REVIEW: 80 C, the highest operating temperature of the same instruments; between 50 and 80 C only thermostable proteins are titrated, so plausibility falls linearly from TEMPERATURE_MAX_K to none here.
MIN_REPLICATE_TITRATIONS = 3  # EXPERT_REVIEW: fewest independent replicate titrations; full agreement from it. Below it (owner rule: replicates mean precision in every assay) the degree is min(1, sqrt(n / MIN_REPLICATE_TITRATIONS)): the standard error of a KD averaged over n independent titrations falls as 1 / sqrt(n); one titration still gives a fitted KD (about 0.58), two about 0.82; never conflicting for a stated count.
STOICHIOMETRY_MIN = 0.4  # EXPERT_REVIEW: used only when the paper states no expected n: a fitted n below this is not a meaningful stoichiometry; full agreement from it.
STOICHIOMETRY_ZERO_MIN = 0.2  # EXPERT_REVIEW: half of STOICHIOMETRY_MIN, a fitted n this small is noise (no agreement, conflicting); falls linearly from STOICHIOMETRY_MIN.
STOICHIOMETRY_STEP = 0.5  # EXPERT_REVIEW: used only when the paper states no expected n (the fallback for the paper's own ratio): the step of a simple stoichiometry (n is expected near a multiple of one half).
STOICHIOMETRY_STEP_TOLERANCE = 0.15  # EXPERT_REVIEW: fitted n must lie this close (absolute) to a multiple of STOICHIOMETRY_STEP; full agreement up to it.
STOICHIOMETRY_STEP_ZERO = 0.25  # EXPERT_REVIEW: half the step, the farthest a number can be from a multiple of it (exactly between two simple ratios: no credit, degree 0, never conflicting: an n such as 0.75 is routinely a 75 percent active cell protein, which leaves KD unbiased, so it is ambiguity, not evidence against); falls linearly from STOICHIOMETRY_STEP_TOLERANCE.
DG_TOLERANCE_KJ_PER_MOL = 2.0  # EXPERT_REVIEW: allowed gap between dG from KD and dG from dH - T dS; full agreement up to it.
DG_ZERO_KJ_PER_MOL = 10.0  # EXPERT_REVIEW: a gap of 10 kJ/mol is about a 60-fold error in KD at room temperature, so the KD and the enthalpy-entropy pair describe different binding (no agreement); falls linearly from DG_TOLERANCE_KJ_PER_MOL.
NULL_REASONS = {'recovery': 'itc_has_no_matrix_recovery_measurement', 'attributed_signal': 'itc_heat_of_dilution_control_is_not_an_attribution_fraction', 'total_signal': 'itc_heat_of_dilution_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_itc_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_itc_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit). Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly to 0 at the zero limit."""
    degrees = [(zero - value) / (zero - full) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _counted(refs, count, full, zero):
    """A count judged against its researched minimum: 1.0 from ``full``, below it the square root of the share of the
    way from ``zero`` to ``full`` (the precision of a fitted or averaged ITC value grows as the square root of the
    independent information, points beyond the fitted parameters or titrations, so each missing one costs a little,
    not all); no credit (degree 0) at or below ``zero``, never conflicting: a short count is weaker evidence, not evidence against."""
    share = (count - zero) / (full - zero)
    return _verdict('supported', refs, math.sqrt(min(1.0, max(0.0, share))))


def _judge_n_over_expected(native):
    ratio = native['n_over_expected']
    verdict = _graded(native['n_over_expected_refs'], (ratio, N_OVER_EXPECTED_MIN, N_OVER_EXPECTED_ZERO_MIN), (ratio, N_OVER_EXPECTED_MAX, N_OVER_EXPECTED_ZERO_MAX))
    return _verdict('unknown', []) if verdict['status'] == 'supported' and native['concentration_facts_unknown'] else verdict


def _judge_c_value(native):
    # Linear in log10(c), not in c: the isotherm's shape, and how well it fixes KD, change per factor of c (Wiseman 1989),
    # so each decade beyond the window costs the same; a c of zero or less is beyond any limit.
    c = native['c_value']
    log_c = math.log10(c) if c > 0 else -math.inf
    # A low-c titration taken to a large ligand excess still defines its plateau: the low zero end moves down by up to one decade,
    # smoothly with how far past KD the final total ligand went; nothing is lowered by a final ratio that is not stated.
    over_kd = native['final_ligand_over_kd']
    share = 0.0 if over_kd is None else min(1.0, max(0.0, (math.log10(over_kd) - math.log10(SATURATION_ZERO_OVER_KD)) / (math.log10(SATURATION_FULL_OVER_KD) - math.log10(SATURATION_ZERO_OVER_KD))))
    zero_min = math.log10(C_VALUE_ZERO_MIN) + share * (math.log10(C_VALUE_ZERO_MIN_SATURATED) - math.log10(C_VALUE_ZERO_MIN))
    refs = list(dict.fromkeys([*native['c_value_refs'], *(native['final_ratio_refs'] if share > 0 else [])]))
    return _graded(refs, (log_c, math.log10(C_VALUE_MIN), zero_min), (log_c, math.log10(C_VALUE_MAX), math.log10(C_VALUE_ZERO_MAX)))


def _judge_injections(native):
    # Square root, not linear: an ITC isotherm is a least-squares fit of n, KD and dH, whose parameter errors shrink as
    # the square root of the points beyond those three; a run of 12-14 injections (common on low-volume cells) loses
    # little precision, while 4-5 injections barely define the curve.
    return _counted(native['injection_refs'], native['injection_count'], MIN_INJECTIONS, INJECTIONS_ZERO)


def _judge_titration_mode(native):
    # A single-injection or continuous titration has one injection (or none) but hundreds of points (Markova & Hallen 2004):
    # the injection count says nothing about how well the isotherm is sampled, so the criterion does not apply to it.
    return _verdict('not_applicable', [])


def _judge_temperature(native):
    # Linear, as the other windows here: outside the usual 5-50 C an ITC run is less and less plausible towards the
    # instrument limits; no physical law sets a sharper shape, and inside the window the temperature costs nothing.
    kelvin = native['temperature_K']
    verdict = _graded(native['temperature_refs'], (kelvin, TEMPERATURE_MIN_K, TEMPERATURE_ZERO_MIN_K), (kelvin, TEMPERATURE_MAX_K, TEMPERATURE_ZERO_MAX_K))
    if verdict['status'] == 'conflicting':
        return verdict
    control = native['temperature_control']
    if control == 'yes':
        return verdict
    return _verdict('not_applicable' if control == 'not_applicable' else 'unknown', [])


def _judge_replicates(native):
    # min(1, sqrt(n / MIN_REPLICATE_TITRATIONS)): the precision of a KD averaged over independent titrations (its standard
    # error) scales as 1/sqrt(n). A single titration still gives a fitted KD, so it keeps partial credit (about 0.58).
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATE_TITRATIONS)))


def _judge_stoichiometry(native):
    n, refs = native['stoichiometry_n'], native['stoichiometry_refs']
    if native['n_over_expected'] is not None:
        # The paper states its own expected n: the fitted n against it is judged once, relative, by
        # concentration_accuracy_and_active_fraction; judging the same deviation again on the absolute lattice would count it twice.
        verdict = _verdict('supported', refs)
    else:
        size = _graded(refs, (n, STOICHIOMETRY_MIN, STOICHIOMETRY_ZERO_MIN))
        if size['status'] == 'conflicting':
            return size
        steps = n / STOICHIOMETRY_STEP
        distance = abs(steps - round(steps)) * STOICHIOMETRY_STEP
        lattice = min(1.0, max(0, (STOICHIOMETRY_STEP_ZERO - distance) / (STOICHIOMETRY_STEP_ZERO - STOICHIOMETRY_STEP_TOLERANCE)))      # never conflicting: between two simple ratios is ambiguity
        verdict = _verdict('supported', refs, min(size['degree'], lattice))
    return _verdict('unknown', []) if native['stoichiometry_free'] != 'yes' else verdict


def _judge_free_energies(native):
    # dG = dH - T dS holds for the observed (fitted) dH, the one that goes with the KD of the same fit. A dH the paper says it
    # corrected for buffer ionization is an intrinsic enthalpy, which differs from it by a legitimate several kJ/mol
    # (Fukada & Takahashi 1998): the comparison does not apply. Stated no, or not stated: the identity is compared as before.
    if native['enthalpy_ionization_corrected'] == 'yes':
        return _verdict('not_applicable', [])
    return _graded(native['dg_refs'], (native['dg_gap_kJ_per_mol'], DG_TOLERANCE_KJ_PER_MOL, DG_ZERO_KJ_PER_MOL))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('concentration_accuracy_and_active_fraction', 'n_over_expected_recorded_for_the_sheet'): _judge_n_over_expected, ('c_value_window', 'c_value_recorded_for_the_sheet'): _judge_c_value,
          ('injections_sufficient', 'injection_count_recorded_for_the_sheet'): _judge_injections, ('injections_sufficient', 'titration_mode_recorded_for_the_sheet'): _judge_titration_mode, ('temperature_stated_and_controlled', 'temperature_recorded_for_the_sheet'): _judge_temperature,
          ('replicate_titrations_independent', 'replicate_count_recorded_for_the_sheet'): _judge_replicates, ('stoichiometry_consistency', 'stoichiometry_recorded_for_the_sheet'): _judge_stoichiometry,
          ('thermodynamic_consistency', 'free_energy_gap_recorded_for_the_sheet'): _judge_free_energies}


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
        if _criterion(graded, 'replicate_titrations_independent')['status'] != 'supported':
            return None, 'sd_needs_independent_titrations_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_itc(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    kd = native['quantities']['kd']
    if native['kd_nM'] is None:
        null_components['effect'] = 'kd_not_given_as_a_point_value'
    else:
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'itc_kd:' + ref, kd['source_refs'], kd['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'itc_kd_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        graded_members = [m for m in (_criterion(graded, name) for name in members) if m['status'] != 'not_applicable']      # the sheet's own judgement can also be not_applicable (the temperature control)
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
        supports = [s for name in members if _criterion(graded, name)['status'] != 'not_applicable' for s in native['support'][name]]
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if variance is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': variance_refs}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['syringe_preparation_ref'], 'immobilized_preparation_ref': preparations['cell_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'itc', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': kd['support'] if native['kd_nM'] is not None else None}
