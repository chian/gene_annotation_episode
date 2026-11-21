"""CETSA converter: turns the CETSA grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_cetsa.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'ligand_binding'), the sheet itself (grade_assay run on it), the
dependence keys the merger needs, the qualitative effect when the experiment reports no constant, and for every sheet component that a CETSA
cannot honestly fill, the reason it stays null.

Two cases (the contract of the earlier types is unchanged)
---------------------------------------------------------
QUANTITATIVE: the record has an EC50 of the isothermal dose-response (or an apparent affinity the passage derives from it). Then the converter fills the numeric effect as the earlier quantitative types do
(quantity_kind 'binding_parameter'): effect = the EC50 in nM, an APPARENT engagement constant derived from the cellular thermal shift (not an equilibrium dissociation constant; it depends on the heating temperature and time), labelled as such by
its measurement key 'cetsa_apparent_kd' and its native component 'engagement_ec50'. The caveats of the method are judged by the criteria (dose_response, concentration_range, isothermal_window, thermal_shift and the controls) and so reach the sheet as interpretations.
  effect_variance   variance of the EC50, nM_squared, only when the source's spread (engagement_ec50_spread) allows it: standard_error -> se^2; standard_deviation -> sd^2 / n, and only when the replicates criterion is supported (n independent
                    experiments) and n is at least SD_MIN_EXPERIMENTS (a between-experiment SD needs two experiments); confidence_interval -> not converted. Otherwise null.
  effect_precision  the sheet computes 1 / variance from the above.
  There is no qualitative_effect: the result enters the merger's pool and is not counted a second time as a qualitative result.
QUALITATIVE: the record has no EC50 (a target engagement, perhaps with a shift of the melting temperature). Then, exactly as the pull-down, EMSA, SEC, dialysis and AUC converters do (quantity_kind 'relative_binding_response'), NO effect and no variance
are filled: the sheet's measured_effect, effect_variance and effect_precision cells are unavailable, with the reason 'qualitative_assay_reports_no_binding_constant' in null_components. Nothing is invented: no constant, and the shift in degrees is not put into
the effect (it is not on the nM scale). What the experiment does contribute is carried beside the sheet, in 'qualitative_effect' ({'statement', 'support_refs', 'thermal_shift_celsius'}):
  statement             'interaction_detected' (a target engagement is stated), 'interaction_not_detected' (it is stated that there was none) or 'interaction_not_stated'
  support_refs          the spans of the fact that states it (empty when not stated)
  thermal_shift_celsius the shift of the melting temperature in degrees Celsius, or None
The scoring reads 'qualitative_effect': its statement fixes the direction (literature_direction.py) and its support refs join the row (literature_row.py).

Criteria mapping (CETSA criteria -> sheet criteria), declared in CRITERIA_MAP
-----------------------------------------------------------------------------
binding_controls              vehicle_control + loading_control + negative_control + specificity_control + total_level_control (the controls that show the stabilisation is the compound's direct binding to the target and not the solvent, the load, a change of the expression or another effect)
binding_regime                temperature_series + isothermal_window + dose_response + concentration_range (the engagement is followed over a melt curve of enough temperatures, or at a temperature in the transition over enough concentrations on both sides of the EC50)
binding_parameter_definition  engagement_observed + thermal_shift (what the response is: a thermal stabilisation and its size)
calibration_applicability     cell_integrity (the cells were alive and took up the compound, so the measurement is an in-cell engagement)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Each researched value is kept as a
named EXPERT_REVIEW constant and is the centre or end of a gradual curve (OWNER RULE, A105_EXPERIMENT_SOP.md step 3); the shape is chosen per criterion (see the range review below):
  thermal_shift       conflicting when the shift is 0 or negative (the paper's own Tm values show no stabilisation; the criterion asks for a rise); a positive shift up to TM_SHIFT_ZERO_AGREEMENT_C is supported with degree 0
                      (no credit, not opposition: no paper spread of the Tm is collected that could show it inside the scatter); linear in the shift up to 1.0 at TM_SHIFT_FULL_AGREEMENT_C.
                      With a stated SD of the Tm the shift over the SD is a second degree (full from SHIFT_OVER_SPREAD_FULL_AGREEMENT, conflicting at or below SHIFT_OVER_SPREAD_ZERO_AGREEMENT); the weaker of the two counts.
  temperature_series  d = min(1, (n / MIN_TEMPERATURES) ** TEMPERATURE_CREDIT_POWER), never conflicting from the count; with the range ends and a Tm stated, also the distances of the Tm values from the ends of the range
                      (full from TEMPERATURE_MARGIN_FULL_C, linear below, conflicting at or beyond an end); the weaker degree decides.
  isothermal_window   when the isothermal temperature and the unbound Tm are stated: linear in |T - Tm| from full credit at ISOTHERMAL_WINDOW_FULL_C to conflicting at ISOTHERMAL_WINDOW_ZERO_C; otherwise the grader's fact.
  dose_response       never conflicting from the count: d = min(1, (n / MIN_CONCENTRATIONS) ** CONCENTRATION_CREDIT_POWER) when the record reports no EC50 (a dose dependence), d = min(1, (n / MIN_CONCENTRATIONS_FOR_EC50) **
                      EC50_CONCENTRATION_CREDIT_POWER) when it reports an EC50 fitted from the series.
  concentration_range linear in the fractional occupancy x / (1 + x) of the lowest and of the highest concentration (x = concentration over the EC50), between the occupancies at LOW_OVER_EC50_FULL_AGREEMENT / LOW_OVER_EC50_ZERO_AGREEMENT
                      and HIGH_OVER_EC50_FULL_AGREEMENT / HIGH_OVER_EC50_ZERO_AGREEMENT; an EC50 the series does not reach past on one side is conflicting; the weaker side decides.
  replicates          d = min(1, (n / MIN_REPLICATES) ** REPLICATE_CREDIT_POWER) (= sqrt(n / MIN), the precision of a mean) when the independence is yes, else unknown (independence stated as no is the grader's conflicting fact).
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).

Range review: the owner's five questions, per researched value and curve (2026-11-21). Q1 what it protects against; Q2 general practice or lab-specific (source); Q3 absolute or relative scale, and whether the relative
quantity is a grader fact; Q4 how badly a wrong value misleads and whether the shape reflects it; Q5 consistency with the other binding assays. Sources (from memory, not web-verified): Martinez Molina et al. 2013 Science 341:84;
Jafari et al. 2014 Nat Protoc 9:2100; Savitski et al. 2014 Science 346:1255784; Franken et al. 2015 Nat Protoc 10:1567; Matulis et al. 2005 Biochemistry 44:5258; Hulme and Trevethick 2010 Br J Pharmacol 161:1219; Jarmoskaite et al. 2020 eLife 9:e57264.
  thermal_shift (TM_SHIFT_FULL_AGREEMENT_C 3.0, TM_SHIFT_ZERO_AGREEMENT_C 0.5)
    Q1 a "stabilisation" that is blot-to-blot scatter of the Tm, or a fall of the Tm read as engagement.  Q2 general for the method: CETSA shifts of true binders are mostly a few degrees and up to about 10 (Martinez Molina 2013; Jafari 2014);
       a western-blot or TPP Tm is reproducible to about 0.5 to 1 degree (Jafari 2014; Savitski 2014; Franken 2015), so 0.5 is the generous noise end. 3.0 is above DSF's 2.0 because an in-cell blot Tm scatters more than a plate Tm.
    Q3 the noise end should be the paper's own scatter of the Tm, and the size end is relative to the compound concentration of the melt curve over the binding constant (the shift grows as ln(1 + [L]/K), Matulis 2005; in cells
       also with uptake); neither the Tm spread nor the concentration of the melt curve is a grader fact (grader gaps), so both ends stay absolute. The CETSA shift is also known not to rank affinity (Jafari 2014), another reason
       the size end should give only partial, not zero, credit to small shifts.
    Q4 a stated positive shift of 0 to 0.5 degrees was conflicting, overriding a paper that states engagement on the strength of a convention value with no paper spread to back it (MISTAKE, fixed; SOP rule 5 keeps conflicting
       for what the paper itself shows). Linear in the shift between 0.5 and 3.0 is kept: the shift is linear in ln(occupancy term), so equal steps are equal fold steps in [L]/K, the scale of the KD strength. A stated fall
       is still conflicting by the criterion's question (a rise), although a ligand can destabilise its target (Savitski 2014 report destabilised binders): criteria gap below.
    Q5 the same treatment as DSF after its review (conflicting only at <= 0, degree 0 inside the reproducibility).  -> CHANGED: conflicting at <= 0.5 -> conflicting at <= 0, 0 < shift <= 0.5 supported with degree 0; values kept.
  temperature_series (MIN_TEMPERATURES 5, TEMPERATURE_CREDIT_POWER 2.0)
    Q1 a Tm read from too few temperatures to define the transition (two plateaux, the midpoint, the slope).  Q2 general: melt curves use 8 to 12 temperatures (Jafari 2014) and TPP 10 (Savitski 2014; Franken 2015); 5 is the
       floor that leaves one residual degree of freedom for a four-parameter sigmoid.  Q3 an absolute count is the right scale for the fit; what it misses is whether the temperatures bracket both Tm values (temperature_lowest,
       temperature_highest, tm_vehicle and tm_ligand are record quantities, but the criterion neither reads them nor keeps their quote support: grader gap).  Q4 below the fit's parameter count the Tm is not determined, so
       the credit falls faster than in proportion (convex: 4 -> 0.64, 3 -> 0.36); a paper with 6 to 7 temperatures gets full credit, a mild over-credit.  Q5 a short series is partial credit, never conflicting; the same convex
       shape as DSF's KD series.  -> KEPT.
  dose_response (MIN_CONCENTRATIONS 5 -> 3 for a dose dependence; MIN_CONCENTRATIONS_FOR_EC50 5 new for an EC50, EC50_CONCENTRATION_CREDIT_POWER 2.0 new; CONCENTRATION_CREDIT_POWER 1.0 kept)
    Q1 a stabilisation at one dose that may be a single-point artefact (cytotoxicity, aggregation at a high dose); for an EC50, a fit with too few points to fix it.  Q2 general: three concentrations show a monotone rise and
       curvature (as DSF); ITDR EC50s are fitted from 8 to 12 concentrations (Jafari 2014); 5 leaves one residual degree of freedom for a four-parameter logistic.  Q3 relative to what the record states: whether an EC50 is
       reported (native ec50_nM, available).  Q4 one curve for both was wrong both ways: a dose dependence shown with 3 or 4 concentrations got only 0.6 to 0.8, and an EC50 fitted from 3 points got 0.6 for a constant 3 points
       cannot test (MISTAKE, fixed). A dose dependence gains evidence in equal parts per concentration (proportional: 2 -> 0.67, 1 -> 0.33); an EC50 loses faster below the fit's need (convex: 4 -> 0.64, 3 -> 0.36, 1 -> 0.04).
    Q5 the same split and values as DSF (3 proportional; 5 convex for a constant); never conflicting from the count.  -> CHANGED as above.
  concentration_range (LOW_OVER_EC50 0.2 / 1.0, HIGH_OVER_EC50 5.0 / 1.0)
    Q1 an apparent EC50 read outside the sampled concentrations (an extrapolated EC50, one plateau missing).  Q2 general titration practice, 0.1x to 10x of the constant with a factor 2 slack (Hulme and Trevethick 2010; Jarmoskaite
       2020); ITDR series span several logs (Jafari 2014).  Q3 relative to the paper's own EC50 (a grader fact). A titration limit by the target concentration would also matter in a lysate, but the cellular target concentration is
       almost never stated, so no gap is listed.  Q4 linear in the ratio was asymmetric: 0.5x EC50 gave 0.63 but 2x EC50 gave 0.25, although 0.2 and 5 are symmetric fold distances (MISTAKE, the cross-assay note of the DSF review,
       fixed). An ITDR is fitted as a logistic in log concentration (Hill 1: x / (1 + x)), so linear in occupancy is symmetric (0.5x and 2x both 0.5) and steepest near the EC50, where each fold of range adds the most of the curve.
       An EC50 not bracketed on one side stays conflicting: the paper's own numbers show the plateau was not sampled.  Q5 the same values and shape as DSF.  -> CHANGED shape (values kept): linear in ratio -> linear in occupancy.
  replicates (MIN_REPLICATES 3, REPLICATE_CREDIT_POWER 0.5)
    Q1 a shift or EC50 seen once (a blot, lysis or preparation artefact).  Q2 general: biological triplicates for western-blot CETSA (Jafari 2014); TPP commonly runs two biological replicates (Savitski 2014; Franken 2015), which
       gets 0.82 here, a mild under-credit.  Q3 absolute count (the readout could set the minimum, but one value for all readouts is kept until the owner asks).  Q4 fewer experiments lose the precision of the mean shift or EC50
       (standard error ~ 1 / sqrt(n)), so the concave sqrt is the right shape: one experiment still shows the stabilisation (0.58).  Q5 sqrt(n / MIN) as DSF, FP, FRET, alpha, pull-down; unknown without stated independence.
       -> KEPT.  The variance from a standard deviation now needs at least SD_MIN_EXPERIMENTS (2) experiments: since the softening a single experiment is supported, and sd^2 / 1 was being made a variance from a between-experiment
       SD that one experiment cannot have (MISTAKE, fixed; the same guard as DSF).
  Facts with no constant (engagement_observed, vehicle_control, loading_control, isothermal_window, negative_control, specificity_control, cell_integrity, total_level_control): the grader's yes/no rule; nothing to soften here.
  No unknown weight is used inside any degree here; the unknown weight is WEIGHT_UNKNOWN_BY_TYPE['cetsa'] in literature_row_contract.py (A105_ASSAY_CALIBRATION_DETAILS.md), not touched.
  GRADER GAPS ADDRESSED (2026-11-21, after the range review; the owner's questions answered for each):
    (1) Tm spread: DONE. New record quantity tm_spread (C) and fact tm_spread_over_independent_experiments; thermal_shift now also takes the shift over the paper's own SD of the Tm (SHIFT_OVER_SPREAD_FULL_AGREEMENT 3.0,
        ZERO 1.0 as DSF: a shift within one SD is conflicting, three SD full credit); an SD over technical replicates only gets BETWEEN_EXPERIMENT_TM_SD_C 1.0 added in quadrature. Folded into thermal_shift, not a new sheet criterion.
    (2) Melt-curve compound concentration: NOT DONE, not worth it. DSF scales the clear-shift end by ln(1 + [L]/KD) because DSF often reports a KD; a CETSA melt curve is run at one usually saturating dose (10 to 100 uM) and
        reports no EC50 (the EC50 comes from a different, isothermal run), so the quotient [L]/EC50 is almost never both stated; and CETSA shifts are known not to rank affinity (Jafari 2014). A field that is almost always unavailable
        would only add a quote for the model to get wrong.
    (3) Temperature range check: DONE. temperature_series now also reads temperature_lowest, temperature_highest, tm_vehicle and tm_ligand: the distances of the stated Tm values from the ends of the sampled range are a grader fact;
        TEMPERATURE_MARGIN_FULL_C 5.0 gives full credit, linear below, and a Tm at or beyond an end of the range (distance <= 0, extrapolated) is conflicting; the degree is the weaker of the count and the margins.
    (4) Isothermal window from numbers: DONE. isothermal_window now also reads isothermal_temperature and tm_vehicle: |T - Tm| within ISOTHERMAL_WINDOW_FULL_C 5.0 full credit, linear to ISOTHERMAL_WINDOW_ZERO_C 12.0 (conflicting). A fact answered no
        stays conflicting; when both numbers are stated they decide (a stated yes is not trusted over the paper's own numbers); otherwise the fact decides as before.
    (5) Destabilisation: NOT CHANGED (decision, flagged for the owner). The criterion asks for a rise and so does the extraction: a lower Tm is routed to target_engagement_shown = no (tm_shift is above 0 only), and a fall computed from
        two stated Tm values stays conflicting. TPP counts a destabilised target as a hit (Savitski 2014), but in a one-target CETSA paragraph a fall cannot be told from an indirect effect (a complex falling apart, a change of the cell) without
        a further control, and the record has no signed shift field. Counting a fall would need a signed field, a direction fact and an owner ruling on the claim "binds".
Quote support (SUPPORT_DEGREE in literature_quote_support.py): the record carries, per stated field, how well its quote supports it (direct 1.0, implied 0.7, about_something_else 0.3) and the grader keeps, per criterion, the supports of the fields it reads. A supported member criterion whose
weakest read field is implied or about_something_else gets that factor as its degree where it had none, or the product with its own degree; direct leaves it unchanged. Support never changes a status. variance_correspondence takes the weakest support of the spread (and of the replicate count for a standard
deviation). The qualitative effect (its statement and support_refs) is not touched by support.
Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, binding_comparison, recovery) are not selected, and the sheet reports them as not selected.

Dependence keys handed to the merger (the same four keys as the other converters): analyte_preparation_ref = the ligand (the compound), immobilized_preparation_ref = the target, surface_ref = None (a cell is not a surface reference), dataset_ref = the dataset.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_cetsa_converted_v1'
CRITERIA_MAP = {'binding_controls': ('vehicle_control', 'loading_control', 'negative_control', 'specificity_control', 'total_level_control'), 'binding_regime': ('temperature_series', 'isothermal_window', 'dose_response', 'concentration_range'), 'binding_parameter_definition': ('engagement_observed', 'thermal_shift'), 'calibration_applicability': ('cell_integrity',), 'sampling_basis': ('replicates',)}
TM_SHIFT_FULL_AGREEMENT_C = 3.0  # EXPERT_REVIEW: smallest thermal shift (degrees Celsius) of the melting temperature by the compound that the sheet takes as a clear stabilisation; published CETSA shifts of true binders are mostly 2 to 10 degrees, and the Tm of one sample is reproducible to about 0.5 to 1 degree.
TM_SHIFT_ZERO_AGREEMENT_C = 0.5  # EXPERT_REVIEW: positive shift (degrees Celsius) at or below which the melt curve with the compound cannot be told from the vehicle curve by the typical reproducibility of the Tm (0.5 to 1 degree for a western-blot or TPP Tm; Jafari et al. 2014 Nat Protoc; Franken et al. 2015 Nat Protoc): degree 0, supported (no credit, not opposition: the record holds no paper spread of the Tm that could show the shift inside the scatter); no shift or a fall is conflicting (the paper's own numbers show no rise); between this and TM_SHIFT_FULL_AGREEMENT_C the degree rises linearly (the shift grows as ln(1 + [L]/K), so equal steps are equal fold steps).
MIN_TEMPERATURES = 5  # EXPERT_REVIEW: fewest heating temperatures that define a melt curve (a folded baseline, the transition and a denatured end; usual CETSA curves use 8 to 12). Full credit from this count; below it partial credit (TEMPERATURE_CREDIT_POWER), not a cut-off.
TEMPERATURE_CREDIT_POWER = 2.0  # EXPERT_REVIEW: shape of the credit below MIN_TEMPERATURES, d = (n / MIN_TEMPERATURES) ** 2 (convex: 4 -> 0.64, 3 -> 0.36, 2 -> 0.16, 1 -> 0.04). Why for CETSA: the Tm, and so the shift, comes from a fit of a four-parameter sigmoid (folded and denatured plateaux, Tm, slope); with fewer temperatures than that the transition is not defined and the Tm is read from a few points by eye, so the credit falls faster than in proportion to the missing temperatures.
MIN_CONCENTRATIONS = 3  # EXPERT_REVIEW: fewest compound concentrations that show a dose dependence of the stabilisation when the record reports no EC50 (one gives a stabilisation, two a single slope, three a monotone rise with curvature; as DSF). Full credit from this count; below it partial credit (CONCENTRATION_CREDIT_POWER), not a cut-off. (Was 5 for every record: range review, a dose dependence does not need the full sigmoid.)
CONCENTRATION_CREDIT_POWER = 1.0  # EXPERT_REVIEW: shape of the credit below MIN_CONCENTRATIONS, d = n / MIN_CONCENTRATIONS (proportional: 2 -> 0.67, 1 -> 0.33). Why for CETSA: the criterion asks for a dose dependence, and each concentration adds that evidence in equal parts (ITDR-CETSA is mostly used to show dose dependence and rank compounds); one concentration still shows a stabilisation, so a short series is low partial credit, never conflicting.
MIN_CONCENTRATIONS_FOR_EC50 = 5  # EXPERT_REVIEW: fewest compound concentrations for an ITDR EC50: the four-parameter logistic (two plateaux, the slope, the EC50) leaves one residual degree of freedom at 5; usual ITDR series use 8 to 12 (Jafari et al. 2014 Nat Protoc 9:2100). Full credit from this count when an EC50 is reported; below it partial credit (EC50_CONCENTRATION_CREDIT_POWER).
EC50_CONCENTRATION_CREDIT_POWER = 2.0  # EXPERT_REVIEW: shape below MIN_CONCENTRATIONS_FOR_EC50, d = (n / 5) ** 2 (convex: 4 -> 0.64, 3 -> 0.36, 2 -> 0.16, 1 -> 0.04). Why for a CETSA EC50: below the fit's parameter count the EC50 is not determined by the data, so the credit falls faster than in proportion to the missing concentrations (as the melt-curve count here and DSF's KD series).
LOW_OVER_EC50_FULL_AGREEMENT = 0.2  # EXPERT_REVIEW: largest ratio of the lowest compound concentration to the EC50 at which the series defines the unstabilised end of the dose-response (0.1x with a factor 2 slack; Hulme and Trevethick 2010 Br J Pharmacol; Jarmoskaite et al. 2020 eLife: about 17 % occupancy).
LOW_OVER_EC50_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the lowest concentration to the EC50 from which the series does not reach below the EC50 (the lower plateau is missing): conflicting; in between the degree is linear in the occupancy x / (1 + x) (an ITDR is a logistic in log concentration; symmetric with the high side, steepest near the EC50).
HIGH_OVER_EC50_FULL_AGREEMENT = 5.0  # EXPERT_REVIEW: smallest ratio of the highest compound concentration to the EC50 at which the series reaches the saturated end of the dose-response (10x with a factor 2 slack: about 83 % occupancy).
HIGH_OVER_EC50_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: ratio of the highest concentration to the EC50 up to which the series does not reach above the EC50 (the upper plateau is missing): conflicting; in between the degree is linear in the occupancy x / (1 + x).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); wells or tubes of one sample do not count. Full credit from this count; below it partial credit (REPLICATE_CREDIT_POWER), not a cut-off.
REPLICATE_CREDIT_POWER = 0.5  # EXPERT_REVIEW: shape of the credit below MIN_REPLICATES, d = (n / MIN_REPLICATES) ** 0.5 (concave: 2 -> 0.82, 1 -> 0.58). Why for CETSA: one experiment already shows the stabilisation; what fewer independent experiments lose is the precision of the stated shift or EC50 (a mean whose standard error falls as 1 / sqrt(n); western-blot CETSA varies from blot to blot), so the credit follows that relative precision.
SHIFT_OVER_SPREAD_FULL_AGREEMENT = 3.0  # EXPERT_REVIEW: smallest quotient of the shift over the stated standard deviation of the Tm taken as a shift well outside the scatter (three standard deviations, the usual hit-calling distance; the SD of a difference of two Tm is sqrt(2) times that of one, which the 3 absorbs; same value as DSF).
SHIFT_OVER_SPREAD_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: quotient at or below which the shift is no larger than one standard deviation of the Tm, so the paper's own numbers do not separate it from the scatter: conflicting; the degree falls linearly in between (same as DSF).
BETWEEN_EXPERIMENT_TM_SD_C = 1.0  # EXPERT_REVIEW: typical standard deviation (degrees Celsius) of a western-blot or TPP Tm between independent experiments (0.5 to 1 degree, Jafari et al. 2014 Nat Protoc; Franken et al. 2015 Nat Protoc; from memory, not web-checked; the upper end because an in-cell blot scatters more than a plate Tm). A stated SD that the paper says is over technical replicates only (tm_spread_over_independent_experiments = no) leaves this scatter out, so it is added in quadrature: sd_eff = sqrt(sd^2 + this^2). A scatter over independent experiments, or one whose basis is not stated, is used as stated (unknown is never opposition).
TEMPERATURE_MARGIN_FULL_C = 5.0  # EXPERT_REVIEW: smallest distance (degrees Celsius) of a stated Tm from each end of the sampled temperature range at which the curve has a plateau on that side: a melt transition goes from 10 % to 90 % soluble over about 10 degrees, so a Tm about 5 degrees from the end of the range leaves the plateau reached (TPP samples 37 to 67 degrees for Tm values of about 45 to 60, Savitski et al. 2014). Full credit from this distance; linear below it.
TEMPERATURE_MARGIN_ZERO_C = 0.0  # FIXED_BY_DEFINITION, not a quality threshold: a stated Tm at or beyond an end of the sampled range was not inside the temperatures measured (it is extrapolated, the plateau on that side is missing): conflicting; the paper's own numbers show it.
ISOTHERMAL_WINDOW_FULL_C = 5.0  # EXPERT_REVIEW: largest distance (degrees Celsius) of the isothermal heating temperature from the stated Tm of the unbound target at which the temperature lies in the transition (a melt transition runs from about 10 % to 90 % soluble over about 10 degrees, so within 5 degrees of the Tm is the window ITDR-CETSA is meant to use; Jafari et al. 2014 Nat Protoc, from memory, not web-checked). Full credit within it; linear beyond it.
ISOTHERMAL_WINDOW_ZERO_C = 12.0  # EXPERT_REVIEW: distance (degrees Celsius) of the isothermal temperature from the unbound Tm at which the unbound target is within about 1 % of its plateau (logistic transition of about 10 degrees from 10 % to 90 %: 0.5 % at 12 degrees): no window between the unbound and the bound target, so conflicting (the paper's own numbers show it); the degree falls linearly from ISOTHERMAL_WINDOW_FULL_C to this.
SD_MIN_EXPERIMENTS = 2  # FIXED_BY_DEFINITION, not a quality threshold: a between-experiment standard deviation needs at least two independent experiments, so an SD with fewer is not turned into a variance of the estimate (sd^2 / n).
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}
NULL_REASONS = {'recovery': 'a_cetsa_run_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_cetsa_stabilisation_is_not_an_attribution_fraction', 'total_signal': 'a_cetsa_stabilisation_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_cetsa_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_cetsa_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _count_degree(count, full, power):
    """1.0 at the researched count ``full`` (or more); below it (count / full) ** power: rising with the count, above 0 for any stated count, no step."""
    return min(1.0, (count / full) ** power)


def _occupancy(ratio):
    """The fractional occupancy x / (1 + x) at a compound concentration of ``ratio`` times the EC50 (an ITDR with a Hill slope of 1)."""
    return ratio / (1 + ratio)


def _judge_shift(native):
    # no rise or a fall: the paper's own numbers show no stabilisation (conflicting). A positive shift inside the typical reproducibility of the Tm gets no credit but is not
    # opposition (no paper spread of the Tm is collected to show it inside the scatter); linear from TM_SHIFT_ZERO_AGREEMENT_C to TM_SHIFT_FULL_AGREEMENT_C.
    # When the paper states a standard deviation of the Tm, the shift over that scatter is a second, relative degree (the weaker of the two counts) and a shift no larger than one SD is conflicting.
    shift = native['shift_celsius']
    if shift <= 0:
        return _verdict('conflicting', native['shift_refs'])
    degree = min(1.0, max(0.0, (shift - TM_SHIFT_ZERO_AGREEMENT_C) / (TM_SHIFT_FULL_AGREEMENT_C - TM_SHIFT_ZERO_AGREEMENT_C)))
    if native['tm_spread_c'] is None:
        return _verdict('supported', native['shift_refs'], degree)
    sd = native['tm_spread_c']
    if native['tm_spread_independent'] == 'no':      # a scatter over technical replicates leaves out the scatter between experiments: add it in quadrature
        sd = math.hypot(sd, BETWEEN_EXPERIMENT_TM_SD_C)
    return _graded(native['shift_spread_refs'], degree, _degree(shift / sd, SHIFT_OVER_SPREAD_FULL_AGREEMENT, SHIFT_OVER_SPREAD_ZERO_AGREEMENT))


def _judge_temperatures(native):
    # the count credit, and, when the sampled range and a Tm are stated, how far each end of the range lies beyond the stated Tm values (a Tm outside the range is conflicting)
    degree = _count_degree(native['temperature_count'], MIN_TEMPERATURES, TEMPERATURE_CREDIT_POWER)
    if native['temperature_margin_low_c'] is None:
        return _verdict('supported', native['temperature_count_refs'], degree)
    margins = [_degree(native[key], TEMPERATURE_MARGIN_FULL_C, TEMPERATURE_MARGIN_ZERO_C) for key in ('temperature_margin_low_c', 'temperature_margin_high_c')]
    return _graded(list(dict.fromkeys([*native['temperature_count_refs'], *native['temperature_bracket_refs']])), degree, *margins)


def _judge_window(native):
    # linear from full credit within ISOTHERMAL_WINDOW_FULL_C of the unbound Tm to none at ISOTHERMAL_WINDOW_ZERO_C (symmetric: below the Tm the target is mostly folded, above it mostly denatured)
    return _graded(native['isothermal_window_refs'], _degree(abs(native['isothermal_over_tm_c']), ISOTHERMAL_WINDOW_FULL_C, ISOTHERMAL_WINDOW_ZERO_C))


def _judge_concentrations(native):
    # proportional to MIN_CONCENTRATIONS for a dose dependence; convex to MIN_CONCENTRATIONS_FOR_EC50 when the record reports an EC50 fitted from the series; never a conflict from the count
    if native['ec50_nM'] is None:
        return _verdict('supported', native['concentration_count_refs'], _count_degree(native['concentration_count'], MIN_CONCENTRATIONS, CONCENTRATION_CREDIT_POWER))
    return _verdict('supported', native['concentration_count_refs'], _count_degree(native['concentration_count'], MIN_CONCENTRATIONS_FOR_EC50, EC50_CONCENTRATION_CREDIT_POWER))


def _judge_range(native):
    # linear in the occupancy at the lowest and the highest concentration, between the occupancies at the researched ratios (symmetric in fold distance from the EC50)
    low = _degree(_occupancy(native['low_over_ec50']), _occupancy(LOW_OVER_EC50_FULL_AGREEMENT), _occupancy(LOW_OVER_EC50_ZERO_AGREEMENT))
    high = _degree(_occupancy(native['high_over_ec50']), _occupancy(HIGH_OVER_EC50_FULL_AGREEMENT), _occupancy(HIGH_OVER_EC50_ZERO_AGREEMENT))
    return _graded(native['range_refs'], low, high)


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # the count is not stated to be of independent experiments
    return _verdict('supported', native['replicate_refs'], _count_degree(native['replicate_count'], MIN_REPLICATES, REPLICATE_CREDIT_POWER))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('thermal_shift', 'thermal_shift_recorded_for_the_sheet'): _judge_shift, ('temperature_series', 'temperature_count_recorded_for_the_sheet'): _judge_temperatures, ('isothermal_window', 'isothermal_window_recorded_for_the_sheet'): _judge_window,
          ('dose_response', 'concentration_count_recorded_for_the_sheet'): _judge_concentrations, ('concentration_range', 'concentration_range_recorded_for_the_sheet'): _judge_range,
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
    if native['ec50_nM'] is None:
        return None, 'no_effect_to_carry_a_variance', []
    spread = native['quantities']['engagement_ec50_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'ec50_spread_not_given', []
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


def convert_cetsa(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    quantitative = native['ec50_nM'] is not None
    if quantitative:
        constant = native['quantities']['engagement_ec50']
        quantities['effect'] = _operand(native['ec50_nM'], 'nM', 'cetsa_apparent_kd:' + ref, constant['source_refs'], constant['origin'], 'engagement_ec50')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'cetsa_variance:' + ref, variance_refs, 'derived', 'engagement_ec50_spread')
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
        variance_fields = ['engagement_ec50_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, [native['quantities'][n].get('support') for n in variance_fields if native['quantities'][n].get('support')])
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter' if quantitative else 'relative_binding_response', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['ligand_preparation_ref'], 'immobilized_preparation_ref': preparations['target_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    converted = {'version': VERSION, 'experiment_type': 'cetsa', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': None}
    if quantitative:
        converted['direction_field_support'] = native['quantities']['engagement_ec50']['support']      # the support class of the engagement EC50 operand, the field that fixes the effect
    else:
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['interaction']], 'support_refs': list(native['interaction_refs']), 'thermal_shift_celsius': native['shift_celsius']}
        if native['interaction'] is not None:
            converted['direction_field_support'] = native['support']['engagement_observed'][0]      # the support class of the fact target_engagement_shown, the one field the statement is derived from
    return converted
