"""SEC converter: turns the SEC grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_sec.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that an SEC
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an apparent KD (a titration read from the peak areas). Then the converter fills the numeric effect as the earlier quantitative
types do (quantity_kind 'binding_parameter'):
  effect            the apparent KD in nM (point operand, measurement key sec_kd). It is an APPARENT constant, with the caveats of the method (the sample
                    is diluted on the column, so a weak complex dissociates; the complex is read at the concentration of the peak, not of the injection); those
                    caveats are not changed in the number, they are judged by the criteria (complex_stable_on_column, stoichiometry, titration_depletion,
                    monodispersity) and so reach the sheet as interpretations.
  effect_variance   variance of the KD, nM_squared, only when the source's spread (kd_spread) allows it: standard_error -> se^2; standard_deviation ->
                    sd^2 / n, and only when the replicates criterion is supported (n independent experiments); confidence_interval -> not converted
                    (needs its level and degrees of freedom). Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no apparent KD (a complex peak, its shift and its mass are shown). Then, exactly as the pull-down and EMSA converters do
(quantity_kind 'relative_binding_response'), NO effect and no variance are filled: the sheet's measured_effect, effect_variance and effect_precision cells
are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no KD, and neither the shift of
the elution volume nor the molar mass is put into the effect (they are not on the nM scale). What the experiment does contribute is carried beside the sheet,
in 'qualitative_effect' ({'statement', 'support_refs', 'elution_shift_ml'}):
  statement          'interaction_detected' (a complex peak is stated), 'interaction_not_detected' (no complex peak is stated) or 'interaction_not_stated'
  support_refs       the spans of the fact that states it (empty when not stated)
  elution_shift_ml   the shift of the elution volume in mL (stated, or the difference of the two stated volumes), or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (SEC criteria -> sheet criteria), declared in CRITERIA_MAP
---------------------------------------------------------------------------
binding_controls              components_alone + complex_composition + single_component_control + resin_interaction + monodispersity (the controls that
                              show the early peak is a complex of these two proteins and not a component alone, an aggregate or a resin effect)
binding_regime                complex_stable_on_column + titration_depletion (the complex survives the dilution on the column; the free peak is used up as the
                              complex grows)
binding_parameter_definition  complex_peak_observed + elution_shift + mals_mass + stoichiometry (what the response is: a complex peak, its shift, its mass and its
                              composition)
calibration_applicability     column_calibration (the column is calibrated with standards)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The researched values are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). Each researched value is the full-credit end of a GRADUAL curve (owner rule, A105_EXPERIMENT_SOP.md step 3): no pass/fail
step at it, partial credit (a degree in [0, 1]) on the worse side, its scale and shape chosen for SEC (the owner's questions below give the reason for each):
  elution_shift      full from the researched shift scaled to the paper's own column: MIN_ELUTION_SHIFT_ML times the stated elution volume of the earlier-eluting
                     component over REFERENCE_ELUTION_VOLUME_ML (the absolute MIN_ELUTION_SHIFT_ML when that volume is not stated); a smoothstep rise from
                     ELUTION_SHIFT_ZERO_ML; at or below it (the mixture elutes no earlier than the component alone, by the paper's own volumes) conflicting.
  stoichiometry      full within the fold 1 + STOICHIOMETRY_TOLERANCE of 1:1 (the fold max(r, 1/r), the same on both sides), falling linearly in the share of 1:1
                     complexes to STOICHIOMETRY_ZERO_FOLD (2:1 or 1:2), conflicting there.
  resin_interaction  full from MIN_SALT_MM, rising linearly in the square root of the salt (Debye screening) from SALT_ZERO_MM; at or below it conflicting (the paper's
                     own running buffer is below the salt at which the resin interacts with charged proteins).
  complex_stable_on_column  full from MIN_LOAD_OVER_KD, below it the fraction of complex that survives in the peak (after COLUMN_DILUTION_FOLD) relative to its value at
                     MIN_LOAD_OVER_KD; never conflicting (the numbers alone do not state that the complex fell apart).
  monodispersity     full up to MAX_POLYDISPERSITY, falling linearly in the share of the peak that is one species to POLYDISPERSITY_ZERO (a peak of equal masses of a
                     species and its dimer), conflicting there.
  replicates         sqrt(min(count, MIN_REPLICATES) / MIN_REPLICATES) when the independence is stated yes (1 -> 0.58, 2 -> 0.82, 3 -> 1), else unknown; never
                     conflicting for a stated count (a stated 'no' independence is the grader's conflict).
  mals_mass          supported with 1.0 at an absolute deviation of at most MASS_FULL_AGREEMENT_PERCENT, falling linearly to 0 at the zero end, conflicting (no degree)
                     from it. The zero end is MASS_ZERO_AGREEMENT_PERCENT, or, when the smaller component's own MALS mass is stated, that mass in percent of the
                     complex (the measured mass is then that of the larger component alone, or of the complex with one more smaller partner), never below
                     MASS_RESOLVABLE_PERCENT.
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and
the merger carries it per result). No degree holds an unknown weight: a degree describes a stated value; how much an unstated criterion counts is decided outside
this file.

The owner's questions, asked of every researched value (2026-11-21; Q1 what it protects against, Q2 general practice or lab/instrument-specific, Q3 absolute or
relative scale and whether the grader holds the quantity, Q4 how badly a wrong value misleads and whether the shape follows that, Q5 consistent with the other
binding assays). Method sources: Cytiva (GE) handbook 'Size Exclusion Chromatography: Principles and Methods' (18-1022-18; buffer, sample volume, resolution);
Wen, Arakawa & Philo 1996 Anal Biochem 240:155 (SEC-LS/UV/RI for proteins and their complexes); Folta-Stogniew 2006 Methods Mol Biol 328:97 (oligomeric state by
SEC-MALS); Some 2013 Biophys Rev 5:147 (light-scattering analysis of interactions); Hong, Koza & Bouvier 2012 J Liq Chromatogr Relat Technol 35:2923 (secondary
interactions with the resin); Pollard 2010 Mol Biol Cell 21:4061 (dilution on gel filtration; binding-assay design).
  elution_shift (MIN_ELUTION_SHIFT_ML, REFERENCE_ELUTION_VOLUME_ML, ELUTION_SHIFT_ZERO_ML): Q1 a 'complex peak' that is the earlier component's own peak (a shoulder,
    run-to-run drift of the elution volume). Q2 the rule (the complex peak must be resolved from the component peak) is general; 0.3 mL is specific to a ~24 mL
    analytical column (Superdex/Superose 10/300), where peaks are about 1 mL wide. Q3 MISTAKE: the absolute mL misjudges every other column (0.1 mL on a 2.4 mL
    3.2/300 column is a large shift but got 0.26; 0.3 mL on a 120 mL 16/600 column, peaks eluting at about 65 mL, is a fifth of its resolvable shift but got full credit). Plate theory: the peak's sigma is
    Ve / sqrt(N), so resolution is a shift relative to the elution volume. The grader holds the earlier component's elution volume (it is the control the shift is
    read against). CHANGED: full credit at MIN_ELUTION_SHIFT_ML * Ve / REFERENCE_ELUTION_VOLUME_ML (about 2.3 percent of Ve, 2 to 3 peak sigmas at about
    48,000 plates per metre, where two equal peaks show two maxima); without that volume but with the stated column volume (new record field column_volume, a former
    grader gap) the full-credit shift is MIN_ELUTION_SHIFT_ML * column volume / REFERENCE_COLUMN_VOLUME_ML; with neither, the absolute value is kept. Q4 a shift within the
    reproducibility of Ve barely moves the maximum of overlapping peaks, so the smoothstep (flat at the start, flat into full credit) is kept. Q5 the AUC shift is
    likewise relative to the paper's own component control.
  stoichiometry (STOICHIOMETRY_TOLERANCE, STOICHIOMETRY_ZERO_FOLD): Q1 a peak-area KD read as a one-site constant for a 2:1 / 1:2 complex. Q2 general (a molar ratio
    from MALS mass or densitometry is not read closer than about 10 percent; Wen 1996, Folta-Stogniew 2006). Q3 dimensionless; but which partner is named first is
    arbitrary, so the scale must be the fold max(r, 1/r). MISTAKE (small): the full end was 1.1 above 1:1 but 1/0.9 = 1.11 below it, so A:B = 1.11 got 0.99 and the
    same complex named B:A (0.90) got 1.0. CHANGED: full within the fold 1 + STOICHIOMETRY_TOLERANCE on both sides; values kept. Q4 the stated ratio is the mean of
    a 1:1 / 2:1 population, so the share of 1:1 complexes (linear) is what biases the KD: kept. Q5 AUC uses the same fold but takes 1.5 as conflicting; SEC keeps
    its researched 2:1 zero end (population reading); the difference is for the owner to settle.
  resin_interaction (MIN_SALT_MM, SALT_ZERO_MM): Q1 an elution delayed or a peak shifted by ionic adsorption to the matrix (and nonspecific electrostatic
    co-elution at low ionic strength). Q2 general: the handbook asks for an ionic strength of about 0.15 M (Hong 2012: secondary interactions grow below about
    50 mM); usual SEC buffers hold 100 to 150 mM NaCl. Q3 the right scale is the ionic strength of the whole buffer (the buffer ions screen too) and the protein's
    charge (pH vs pI); the record holds only the monovalent salt. Collecting the rest was considered (range-review grader gap) and judged NOT worth it: the pI is not stated in a
    passage (the proteins' own property, not something a quote gives), the buffer's own ions (20 to 50 mM Tris or HEPES, mostly weakly charged) add little to a 100 to 150 mM
    salt, and the pH of the buffer alone, without the pI, would move no verdict; so the researched absolute values are kept. Q4 MISTAKE: at or below SALT_ZERO_MM the
    verdict was unknown, which the row weighs with the type's unknown weight (0.9), while 51 mM was supported with a degree of about 0.02: a better buffer weighed
    about forty times less. CHANGED: conflicting at or below SALT_ZERO_MM (the stated buffer is below the salt at which the resin interacts), so the weight runs
    continuously to 0; the square-root shape (Debye screening) is kept. Q5 the pull-down wash salt is likewise conflicting at or below 50 mM.
  complex_stable_on_column (MIN_LOAD_OVER_KD, COLUMN_DILUTION_FOLD): Q1 a complex that dissociates on the column, so the peak areas give a KD too weak (or miss the
    complex). Q2 general: an analytical injection is diluted about ten- to twentyfold (handbook; Pollard 2010: gel filtration detects only complexes with a KD well
    below the concentration in the peak). Q3 already relative to the paper's own KD. The dilution itself is the peak volume over the injected volume: CHANGED (former grader gap, now collected): with the injected
    volume stated the dilution is sqrt(peak^2 + sample^2) / sample, the peak being PEAK_VOLUME_FRACTION_OF_COLUMN of the stated column volume (REFERENCE_COLUMN_VOLUME_ML
    when not stated); without the injected volume COLUMN_DILUTION_FOLD as before. The full-credit end stays at MIN_LOAD_OVER_KD at COLUMN_DILUTION_FOLD, so a small sample
    on a big column (more dilution) lowers the credit and a larger sample raises it, up to 1. The off-rate and the run time are not collected (a slowly dissociating
    complex survives regardless; a rate is rarely stated for an SEC) and the resin-interaction scale stays absolute (see below). Q4 the credit is the 1:1 binding curve at the peak's concentration, steep where the
    complex in the peak falls and flat above the researched multiple: kept. Q5 never conflicting, as a load in the other binding assays.
  monodispersity (MAX_POLYDISPERSITY, POLYDISPERSITY_ZERO, SECOND_SPECIES_MASS_MULTIPLE): Q1 an aggregate, or a mixture of complex and free component, taken for the
    complex. Q2 general SEC-MALS practice: a monodisperse protein peak reads Mw/Mn below about 1.05 (Some 2013; Folta-Stogniew 2006). Q3 dimensionless (a ratio of
    the peak's own averages). The two-species formula is symmetric under k -> 1/k, so the dimer case also covers a complex with free component of half its mass.
    Q4 Mw/Mn saturates at the monomer-dimer maximum, so the credit is linear in the second species' share, steep near POLYDISPERSITY_ZERO: kept. Q5 yes.
  replicates (MIN_REPLICATES, REPLICATES_ZERO): Q1 a result from one preparation or one run. Q2 three independent experiments is the common reporting minimum;
    injections of one sample are not replicates. Q3 a count, absolute. Q4/Q5 MISTAKE: one experiment was conflicting and the curve was linear in the degrees of
    freedom of a spread, (n - 1) / (MIN - 1). The binding assays treat replicates as the precision of the mean (SPR, pull-down, AUC): CHANGED to
    sqrt(min(n, MIN) / MIN), supported when the independence is yes; a single experiment is less evidence, not evidence against. A standard deviation still
    becomes a variance only from two or more experiments (MIN_COUNT_FOR_A_SPREAD). REPLICATES_ZERO removed.
  mals_mass (MASS_FULL_AGREEMENT_PERCENT, MASS_ZERO_AGREEMENT_PERCENT): Q1 a peak that is a component alone, a homodimer or another stoichiometry, not the A:B complex.
    Q2 general: SEC-MALS masses are good to about 5 percent with a known dn/dc, about 10 percent for modified or glycosylated proteins (Wen 1996; Folta-Stogniew 2006).
    Q3 MISTAKE: the zero end (50 percent) is right only for equal-mass partners; with a partner of 20 percent of the complex a mass 15 percent low is three quarters
    of the way to the larger component alone and got 0.875. The grader holds the smaller component's own MALS mass (component_mass_measured_smaller). CHANGED: the
    zero end is that mass in percent of the complex (at most the researched 50 percent), never below MASS_RESOLVABLE_PERCENT (twice the MALS accuracy: below it the
    mass cannot tell the complex from the larger partner alone, and the shift and SDS-PAGE carry that question). Q4 linear kept: the method's error band (5-10
    percent) and the distance to the next species (10-50 percent) overlap, so no part of the ramp is flatter. Q5 the AUC mass named the same relative zero end as
    its grader gap.
  Unstated criteria (SOP step 3 item 4; not applied in this file): the elution volume is a relative readout (hydrodynamic radius and shape, meaningful only
    against each component alone on the same column); the MALS mass is absolute with a trusted reference (the sequence mass). Unstated salt, calibration or
    replicates are benign typical practice (SEC running buffers almost always hold 100 to 150 mM salt) and could count near the KD weight. Unstated
    components_alone, complex_composition (SDS-PAGE of the peak) or single_component_control are not benign: without them an earlier peak cannot be assigned to the
    A:B complex, so they deserve a much lower weight. Proposal for the owner; the weight (WEIGHT_UNKNOWN_BY_TYPE['sec']) lives outside this converter.
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0,
implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads (the criteria declare every field a judge reads,
the smaller component's mass for mals_mass and the injected and column volumes for the load among them). A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree (the
mass criterion's degree from the deviation, for example); direct leaves it unchanged. Support never changes a status. variance_correspondence takes
the weakest support of the spread (and of the replicate count for a standard deviation). The qualitative effect (its statement and support_refs) is
not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the first component,
immobilized_preparation_ref = the second component, surface_ref = None (a column is not a surface reference), dataset_ref = the dataset.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_criteria import NM_PER_UNIT, PERCENT_PER_FRACTION
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_sec_converted_v1'
CRITERIA_MAP = {'binding_controls': ('components_alone', 'complex_composition', 'single_component_control', 'resin_interaction', 'monodispersity'), 'binding_regime': ('complex_stable_on_column', 'titration_depletion'), 'binding_parameter_definition': ('complex_peak_observed', 'elution_shift', 'mals_mass', 'stoichiometry'), 'calibration_applicability': ('column_calibration',), 'sampling_basis': ('replicates',)}
MIN_ELUTION_SHIFT_ML = 0.3  # EXPERT_REVIEW: smallest shift (mL) of the complex peak below the earlier-eluting component alone that counts as a resolved complex peak ON AN ANALYTICAL COLUMN OF ABOUT 24 mL (Superdex/Superose 10/300); peaks there are about 1 mL wide at the base, so a smaller shift overlaps the component peak. Full credit from it, scaled to the paper's own column by the stated elution volume (see REFERENCE_ELUTION_VOLUME_ML); used as is only when that volume is not stated.
REFERENCE_ELUTION_VOLUME_ML = 13.0  # EXPERT_REVIEW: the elution volume (mL) at which MIN_ELUTION_SHIFT_ML was reasoned: the middle of the fractionation range of a 24 mL analytical column (void about 8 mL, total about 24 mL; proteins of about 30 to 200 kDa elute at about 11 to 16 mL on Superdex 200 Increase 10/300 GL). The peak's sigma is Ve / sqrt(N) (plate theory), so the resolvable shift is a share of the elution volume: 0.3 / 13, about 2.3 percent, 2 to 3 sigmas at about 48,000 plates per metre, where two equal peaks show two maxima.
REFERENCE_COLUMN_VOLUME_ML = 24.0  # EXPERT_REVIEW: the bed volume (mL) of the analytical column the researched values were reasoned for (Superdex / Superose 10/300, about 24 mL; Cytiva column data). Peak widths and the resolvable shift scale with the column volume, so when the earlier component's elution volume is not stated but the column volume is, the full-credit shift is MIN_ELUTION_SHIFT_ML times the column volume over this (the same 13 mL elution volume at 24 mL, a mid-range protein).
PEAK_VOLUME_FRACTION_OF_COLUMN = 0.10  # EXPERT_REVIEW: the volume of a peak at the column outlet as a share of the column volume (about 2.4 mL base width for a protein on a 24 mL analytical column: the peak's sigma is Ve / sqrt(N), and its base, 4 sigma plus the tailing, is about 1 to 3 mL at an elution volume of about 13 mL). The dilution of the sample on the column is then sqrt(peak^2 + sample^2) / sample, the sample volume adding its own width in quadrature; at 0.24 mL on a 24 mL column it is about 10, the lower end of the 'ten- to twenty-fold' of COLUMN_DILUTION_FOLD, so the two agree where the sample volume is a usual analytical one. Used only when the injected volume is stated (see _dilution).
ELUTION_SHIFT_ZERO_ML = 0.0  # EXPERT_REVIEW: a mixture that elutes no earlier than the earlier-eluting component alone (shift 0 or less) shows no complex at all: the paper's own volumes are against the standard (conflicting). Between this and MIN_ELUTION_SHIFT_ML the credit rises on a smoothstep (see _judge_shift).
MAX_POLYDISPERSITY = 1.05  # EXPERT_REVIEW: largest Mw/Mn of a monodisperse peak (the usual MALS reading of a monodisperse protein is below 1.05; above it the peak holds a mixture of species such as aggregates). Full credit up to it.
POLYDISPERSITY_ZERO = 1.125  # EXPERT_REVIEW: Mw/Mn of a peak that holds equal masses of one species and of its dimer (the commonest second species in an SEC peak), (1 + 1/2)(1 - 1/4) = 1.125; such a peak does not define one species (no agreement, conflicting). It is also the largest Mw/Mn any monomer-dimer mixture can reach, so a higher value means larger aggregates. Must be re-derived if SECOND_SPECIES_MASS_MULTIPLE changes.
SECOND_SPECIES_MASS_MULTIPLE = 2.0  # EXPERT_REVIEW: the second species assumed in the peak when the polydispersity is turned into a share of the mass (see _second_species_share): a dimer, twice the mass, the usual first aggregate of a protein or complex in SEC-MALS.
MIN_LOAD_OVER_KD = 10.0  # EXPERT_REVIEW: the injected concentration must be at least this multiple of the KD; the sample is diluted about ten- to twenty-fold on the column, so below it the complex dissociates in the peak and a KD is not read at the concentration of the injection. Full credit from it.
COLUMN_DILUTION_FOLD = 10.0  # EXPERT_REVIEW: the dilution of the sample on an analytical SEC column (about ten- to twenty-fold, as above); the lower end is used, so at MIN_LOAD_OVER_KD the peak runs at about the KD. It sets where on the binding curve the peak sits (see _judge_load).
MIN_SALT_MM = 100.0  # EXPERT_REVIEW: smallest concentration (mM) of monovalent salt in the running buffer that is taken to rule out ionic interaction with the resin when the passage does not say so (the usual SEC buffer holds 100 to 150 mM NaCl; the Cytiva SEC handbook asks for an ionic strength of about 0.15 M; below about 50 mM the resin interacts with charged proteins). Full credit from it.
SALT_ZERO_MM = 50.0  # EXPERT_REVIEW: the 'below about 50 mM the resin interacts with charged proteins' of MIN_SALT_MM: at or below it the paper's own running buffer is against the standard (conflicting, as the pull-down's low-salt wash), so the row weight falls continuously to 0 (it was unknown here, weighed 0.9, above the ~0.02 of 51 mM: a mistake, corrected 2026-11-21).
STOICHIOMETRY_TOLERANCE = 0.1  # EXPERT_REVIEW: largest fold max(r, 1/r) - 1 of the stated stoichiometry away from 1:1 at which a KD from peak areas is the one-site constant (a molar ratio is not read closer than about 10 percent); the fold, because which partner is named first is arbitrary. Another ratio (2:1, 1:2) needs more than one binding step and its apparent KD is not a single constant. Full credit within it.
STOICHIOMETRY_ZERO_FOLD = 2.0  # EXPERT_REVIEW: the next integer stoichiometry, 2:1 (or 1:2, the same fold the other way): a complex stated at it is a two-step complex whose apparent KD is not a one-site constant (no agreement, conflicting).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); injections of one sample do not count. Full credit from it; below it (owner rule: replicates mean precision in every binding assay) the degree is sqrt(n / MIN_REPLICATES), the standard error of a mean over n independent experiments falling as 1 / sqrt(n): 1 about 0.58, 2 about 0.82; never conflicting for a stated count.
MIN_COUNT_FOR_A_SPREAD = 2  # FIXED_BY_DEFINITION: a standard deviation between experiments needs at least two of them; with fewer a stated SD is not the spread of independent experiments and is not turned into a variance.
MASS_FULL_AGREEMENT_PERCENT = 10.0  # EXPERT_REVIEW: largest absolute deviation (percent) of the MALS molar mass of the complex peak from the mass the complex should have that the sheet takes as full agreement; SEC-MALS is accurate to about 5 percent with a known dn/dc, about 10 percent for modified proteins (Wen 1996; Folta-Stogniew 2006).
MASS_ZERO_AGREEMENT_PERCENT = 50.0  # EXPERT_REVIEW: absolute deviation (percent) from which the mass is a different species (conflicting) when the smaller component's own mass is not stated: half the mass is the larger component alone for equal-mass partners (the largest a smaller partner can be), 1.5 times the complex with one more such partner. With the smaller component's mass stated, the zero end is that mass in percent of the complex (at most this value; see _judge_mass); linear in between.
MASS_RESOLVABLE_PERCENT = 2 * MASS_FULL_AGREEMENT_PERCENT  # EXPERT_REVIEW: the lowest zero end: two species are told apart by MALS only when their masses differ by more than twice its accuracy (each reading within its accuracy of its own mass); a smaller partner below it cannot be seen in the mass, and the zero end stays here.
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'an_sec_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_sec_complex_peak_is_not_an_attribution_fraction', 'total_signal': 'an_sec_complex_peak_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_sec_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_sec_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _stated(native, name):
    """The record operand of a quantity the judge reads beside the grader's recorded facts, or None when it is not stated."""
    operand = native['quantities'][name]
    return operand if operand['status'] == 'point' else None


def _judge_mass(native):
    """Supported with a degree from 1.0 (deviation at most MASS_FULL_AGREEMENT_PERCENT) falling linearly to 0 at the zero end; conflicting from there on. The zero end is
    MASS_ZERO_AGREEMENT_PERCENT, or, when the smaller component's own MALS mass is stated, that mass in percent of the complex (at most MASS_ZERO_AGREEMENT_PERCENT, at
    least MASS_RESOLVABLE_PERCENT): a deviation of one smaller partner is the mass of the larger component alone (or of the complex with one more smaller partner)."""
    deviation = abs(native['mass_deviation_percent'])
    zero, refs = MASS_ZERO_AGREEMENT_PERCENT, native['mass_support_refs']
    smaller = _stated(native, 'component_mass_measured_smaller')
    if smaller is not None:
        zero = min(MASS_ZERO_AGREEMENT_PERCENT, max(MASS_RESOLVABLE_PERCENT, smaller['value'] / native['mass_theoretical'] * PERCENT_PER_FRACTION))
        refs = list(dict.fromkeys([*refs, *smaller['source_refs']]))
    if deviation >= zero:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, (zero - deviation) / (zero - MASS_FULL_AGREEMENT_PERCENT)))


def _judge_shift(native):
    """Conflicting at or below ELUTION_SHIFT_ZERO_ML; else supported with the smoothstep x^2 (3 - 2x) of x = the shift's share of the way to the full-credit shift (1.0
    from it). The full-credit shift is MIN_ELUTION_SHIFT_ML * Ve / REFERENCE_ELUTION_VOLUME_ML with Ve the stated elution volume of the earlier-eluting component (the
    peak width scales with Ve, so the resolvable shift does too), or MIN_ELUTION_SHIFT_ML when Ve is not stated.
    Why a smoothstep for SEC: the shift is read between two overlapping peaks; a very small shift is within the run-to-run reproducibility of the elution volume and the
    peak maximum of a mixture barely moves, so credit starts flat; near the resolvable shift the two peaks are already apart and more shift adds little, so it
    flattens into full credit with no kink."""
    shift, refs = native['shift_ml'], native['shift_refs']
    full = MIN_ELUTION_SHIFT_ML
    volume = _stated(native, 'component_elution_volume_earlier')
    if volume is not None:
        full = MIN_ELUTION_SHIFT_ML * volume['value'] / REFERENCE_ELUTION_VOLUME_ML
        refs = list(dict.fromkeys([*refs, *volume['source_refs']]))
    elif native['column_mL'] is not None:
        full = MIN_ELUTION_SHIFT_ML * native['column_mL'] / REFERENCE_COLUMN_VOLUME_ML
        refs = list(dict.fromkeys([*refs, *native['column_refs']]))
    if shift <= ELUTION_SHIFT_ZERO_ML:
        return _verdict('conflicting', refs)
    x = min(1.0, (shift - ELUTION_SHIFT_ZERO_ML) / (full - ELUTION_SHIFT_ZERO_ML))
    return _verdict('supported', refs, x * x * (3 - 2 * x))


def _judge_stoichiometry(native):
    """Full credit within the fold 1 + STOICHIOMETRY_TOLERANCE of 1:1 (fold = max(r, 1/r): which partner is named first is arbitrary); beyond it the degree falls
    linearly to 0 at STOICHIOMETRY_ZERO_FOLD (conflicting there).
    Why this shape for SEC: a stated ratio between 1:1 and 2:1 is the mean of a population of 1:1 and 2:1 complexes, ratio = 1 + (share of 2:1), so 2 - ratio is the
    share of complexes from which a one-site KD is read; below 1:1 the same holds for 1:2 complexes in the inverse ratio. The degree is linear in that share, scaled so the
    researched tolerance (the measurement accuracy of the ratio) is full credit."""
    ratio = native['stoichiometry_ratio']
    fold = max(ratio, 1 / ratio)
    share = (STOICHIOMETRY_ZERO_FOLD - fold) / (STOICHIOMETRY_ZERO_FOLD - (1 + STOICHIOMETRY_TOLERANCE))
    if share <= 0:
        return _verdict('conflicting', native['stoichiometry_refs'])
    return _verdict('supported', native['stoichiometry_refs'], min(1.0, share))


def _judge_salt(native):
    """Conflicting at or below SALT_ZERO_MM (the stated running buffer is below the salt at which the resin interacts with charged proteins); above it supported with a
    degree linear in the square root of the salt, 1.0 from MIN_SALT_MM, so the weight runs continuously to 0 at SALT_ZERO_MM.
    Why the square root for SEC: the resin's interaction with a charged protein is electrostatic, and its screening grows with the inverse Debye length, which goes as the
    square root of the ionic strength; so the first salt added above SALT_ZERO_MM screens the most, and the curve is concave in the salt."""
    salt = native['salt_mM']
    if salt <= SALT_ZERO_MM:
        return _verdict('conflicting', native['salt_refs'])
    return _verdict('supported', native['salt_refs'], min(1.0, (math.sqrt(salt) - math.sqrt(SALT_ZERO_MM)) / (math.sqrt(MIN_SALT_MM) - math.sqrt(SALT_ZERO_MM))))


def _complex_fraction(concentration_over_kd):
    """The fraction of an equimolar 1:1 pair that is in the complex at a total concentration of each partner of concentration_over_kd times the KD: the root of
    (1 - f)^2 c = f, written in its stable form 1 / (h + sqrt(h^2 - 1)) with h = 1 + 1 / (2 c)."""
    h = 1 + 1 / (2 * concentration_over_kd)
    return 1 / (h + math.sqrt(h * h - 1))


def _dilution(native):
    """(the dilution of the sample on the column, the refs it rests on). With the injected volume stated: sqrt(peak^2 + sample^2) / sample, the peak volume being
    PEAK_VOLUME_FRACTION_OF_COLUMN of the stated column volume (REFERENCE_COLUMN_VOLUME_ML when it is not stated), so a larger sample or a smaller column dilutes less;
    never below 1 (a sample is not concentrated). Without the injected volume: COLUMN_DILUTION_FOLD, as before."""
    if native['loaded_mL'] is None:
        return COLUMN_DILUTION_FOLD, []
    column, refs = (native['column_mL'], native['column_refs']) if native['column_mL'] is not None else (REFERENCE_COLUMN_VOLUME_ML, [])
    peak = PEAK_VOLUME_FRACTION_OF_COLUMN * column
    return math.sqrt(peak * peak + native['loaded_mL'] ** 2) / native['loaded_mL'], [*native['loaded_refs'], *refs]


def _judge_load(native):
    """Supported with the fraction of complex that survives in the peak (the injected load over the KD diluted by _dilution: COLUMN_DILUTION_FOLD, or the dilution from the stated injected and column volumes) relative to that fraction at
    MIN_LOAD_OVER_KD, 1.0 from it. Why this shape for SEC: what the researched minimum protects is the complex surviving the dilution on the column, and that is the
    1:1 binding curve at the peak's concentration; below the minimum the credit falls as the complex in the peak falls, towards 0 only as the load goes to 0. Never
    conflicting: the two numbers alone do not state that the complex fell apart (the paper may still show the peak)."""
    dilution, refs = _dilution(native)
    survived = _complex_fraction(native['load_over_kd'] / dilution) / _complex_fraction(MIN_LOAD_OVER_KD / COLUMN_DILUTION_FOLD)
    return _verdict('supported', list(dict.fromkeys([*native['load_refs'], *refs])), min(1.0, survived))


def _second_species_share(polydispersity):
    """The weight fraction w of a second species of SECOND_SPECIES_MASS_MULTIPLE (k) times the mass in a peak whose Mw/Mn is polydispersity:
    Mw/Mn = (1 + a w)(1 + b w) with a = k - 1 and b = 1/k - 1, the smaller root of a b w^2 + (a + b) w - (Mw/Mn - 1) = 0."""
    k = SECOND_SPECIES_MASS_MULTIPLE
    a, b = k - 1, 1 / k - 1
    return (-(a + b) + math.sqrt((a + b) ** 2 + 4 * a * b * (polydispersity - 1))) / (2 * a * b)


def _judge_polydispersity(native):
    """Conflicting from POLYDISPERSITY_ZERO; else supported with a degree linear in the share of the peak's mass that is one species, 1.0 up to MAX_POLYDISPERSITY.
    Why this shape for SEC-MALS: Mw/Mn is not linear in how much of the peak is aggregate (it rises fast at first and saturates at the monomer-dimer maximum), so the
    number is first turned back into the dimer's share of the mass, and the credit falls with that share; near POLYDISPERSITY_ZERO it falls steeply, as Mw/Mn barely
    moves while the share of the second species grows."""
    polydispersity = native['polydispersity']
    if polydispersity >= POLYDISPERSITY_ZERO:
        return _verdict('conflicting', native['polydispersity_refs'])
    zero, full = _second_species_share(POLYDISPERSITY_ZERO), _second_species_share(MAX_POLYDISPERSITY)
    return _verdict('supported', native['polydispersity_refs'], min(1.0, (zero - _second_species_share(polydispersity)) / (zero - full)))


def _judge_replicates(native):
    """Independent experiments stated yes: supported with sqrt(min(count, MIN_REPLICATES) / MIN_REPLICATES), the precision of the mean over independent experiments
    (owner rule, the same in every binding assay); independence not stated: unknown (the count may be injections of one sample; a stated no is the grader's conflict).
    A stated count is never conflicting: one experiment is less evidence, not evidence against."""
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])
    return _verdict('supported', native['replicate_refs'], math.sqrt(min(native['replicate_count'], MIN_REPLICATES) / MIN_REPLICATES))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('mals_mass', 'mass_deviation_recorded_for_the_sheet'): _judge_mass, ('elution_shift', 'elution_shift_recorded_for_the_sheet'): _judge_shift,
          ('stoichiometry', 'stoichiometry_recorded_for_the_sheet'): _judge_stoichiometry, ('resin_interaction', 'salt_recorded_for_the_sheet'): _judge_salt,
          ('complex_stable_on_column', 'load_over_kd_recorded_for_the_sheet'): _judge_load, ('monodispersity', 'polydispersity_recorded_for_the_sheet'): _judge_polydispersity,
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


def convert_sec(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['kd_nM'] is not None
    if quantitative:
        constant = native['quantities']['kd']
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'sec_kd:' + ref, constant['source_refs'], constant['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'sec_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    if not quantitative:
        null_components['effect'] = 'qualitative_assay_reports_no_binding_constant'
        null_components['effect_variance'] = 'qualitative_assay_reports_no_binding_constant'
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        # the support of the quotes (kept by the grader) gives or lowers the degree of a supported member; it never changes a status
        graded_members = [apply_support(_criterion(graded, m), graded['native']['support'][m]) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
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
    converted = {'version': VERSION, 'experiment_type': 'sec', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities']['kd']['support']      # the support class of the KD operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'elution_shift_ml': native['shift_ml']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['complex_peak_observed'][0]      # the support class of the fact complex_peak_detected, the one field the statement is derived from
    return converted
