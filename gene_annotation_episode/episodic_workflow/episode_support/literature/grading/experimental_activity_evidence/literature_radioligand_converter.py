"""Radioligand converter: turns the radioligand grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_radioligand.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA and AlphaScreen converters fill), the
dependence keys the merger needs, and for every sheet component that a radioligand assay cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the KD of
                  the radioligand from a saturation experiment, or, when the record has
                  no KD, the Ki of a competition (the measurement key names it:
                  radioligand_kd or radioligand_ki). Neither given leaves effect null; an
                  IC50 alone is a half-maximal concentration, not a dissociation constant (it
                  depends on the concentration and the KD of the radioligand it competes with) and is not
                  carried into the effect.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent experiments); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the radioligand,
immobilized_preparation_ref = the receptor preparation, surface_ref = None (the filter or the
well is not a surface reference), dataset_ref = the dataset.

Criteria mapping (radioligand criteria -> sheet criteria), declared in CRITERIA_MAP
-----------------------------------------------------------------------------------
binding_controls              nonspecific_binding + nonspecific_excess + radioligand_quality + filter_binding
binding_regime                equilibrium + radioligand_range + competition_radioligand_level + wash_dissociation
binding_parameter_definition  fit_model + nonlinear_fit + hill_slope + cheng_prusoff
calibration_applicability     ligand_depletion + nonspecific_fraction (the bound fraction of the radioligand and the
                              specific binding over the non-specific binding: this method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed; when the variance rests on a standard deviation it carries
                              the replicates degree (a spread from fewer independent experiments than MIN_REPLICATES is a poorer variance); a
                              standard deviation from SINGLE_EXPERIMENT experiment gives no variance
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Every researched value is kept as a named EXPERT_REVIEW constant and is the end of a gradual curve, never a pass/fail step.
A continuous comparison is supported with a degree of 1.0 at or beyond its full-agreement limit, falling to 0 at its zero-agreement limit, and conflicting (no degree)
at or beyond that limit. The fall is linear on the scale the error of THIS criterion grows on (_graded, with the scale named per judge; the reasons are in the owner's
questions below): ligand_depletion on the log of the KD bias that the bound fraction causes (MAX_PERCENT_BOUND to PERCENT_BOUND_ZERO_AGREEMENT); nonspecific_fraction on
the log of the non-specific over the specific binding (MAX_NONSPECIFIC_FRACTION to NONSPECIFIC_FRACTION_ZERO_AGREEMENT); nonspecific_excess on the log of the excess
(MIN_NONSPECIFIC_EXCESS to NONSPECIFIC_EXCESS_ZERO_AGREEMENT); radioligand_range's lowest and highest concentration and competition_radioligand_level on the fractional
occupancy x / (1 + x) that a concentration of x times the KD gives (LOW_FACTOR to LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR to HIGH_ZERO_AGREEMENT_FACTOR,
MAX_RADIOLIGAND_OVER_KD to RADIOLIGAND_OVER_KD_ZERO_AGREEMENT); cheng_prusoff on the log of the fold gap (CHENG_PRUSOFF_FACTOR to CHENG_PRUSOFF_ZERO_FACTOR); hill_slope
linearly in the slope (MIN_HILL..MAX_HILL full, to MIN_HILL_ZERO_AGREEMENT below and MAX_HILL_ZERO_AGREEMENT above). The three lone minimums are curves that never
conflict for a stated value: radioligand_range's count has the full degree at MIN_CONCENTRATIONS and falls linearly in the residual degrees of freedom of the
saturation fit to 0 at SATURATION_FIT_PARAMETERS (supported with degree 0 at or below it: a short series is weak evidence, not evidence against, as in SPR);
replicates (independence yes) is supported with degree min(1, sqrt(n / MIN_REPLICATES)), the precision of the mean constant over n independent experiments, as in
every binding assay (independence not stated: unknown; a stated no is the grader's conflicting); equilibrium from an incubation is supported with the degree of the
first-order approach to equilibrium that the incubation reaches, relative to HALF_LIVES_AT_MIN_INCUBATION half-lives at MIN_INCUBATION_MIN (full from
MIN_INCUBATION_MIN, falling smoothly below it, never conflicting: only a stated 'no' equilibrium is). No unknown weight is used inside any degree.

Owner's questions, per researched value (A105_EXPERIMENT_SOP.md step 3; citations from memory, not web-checked: H&T = Hulme & Trevethick 2010 Br J Pharmacol
161:1219; B&T = Bylund & Toews 1993 Am J Physiol 265:L421; M&N = Motulsky & Neubig, Curr Protoc Neurosci unit 7.5; AGM = NCBI Assay Guidance Manual, Receptor
Binding Assays; C&P = Cheng & Prusoff 1973 Biochem Pharmacol 22:3099; Swillens 1995 Mol Pharmacol 47:1197). Q1 protects against / Q2 general or lab-specific /
Q3 absolute or relative scale / Q4 how badly a wrong value misleads and the shape / Q5 consistency with the other binding assays.
- ligand_depletion (MAX_PERCENT_BOUND 10, PERCENT_BOUND_ZERO_AGREEMENT 50). Q1 the added concentration taken as free when receptor binds much of it: the fit
  of B against added L gives an apparent KD = KD (1 + f / (2 (1 - f))) with f the bound fraction at low L (Swillens), and a competition IC50 gains a floor of
  half the receptor concentration. Q2 general (<10 percent bound: H&T, B&T, AGM). Q3 already relative (bound over added, stated by the paper). Q4 the KD bias is
  1.06-fold at 10 percent, 1.21 at 30, 1.5 at 50 where the receptor equals the KD and the competition floor reaches KD / 2: small near 10, growing fast towards
  50. CHANGED shape: linear in the log of that bias (was linear in the percent, which charged 20 percent bound as much as 40 to 50). Q5 a deviation of the paper's
  own number; conflicting only beyond the researched end. GAP CLOSED (fact): the grader now also records whether the paper says the depletion was corrected
  (free radioligand measured, or a fit that takes it into account); a stated yes gives degree 1.0 (the bias the curve measures is removed), unstated or no
  leaves the percent bound to judge. Not collected (not worth it): the concentration at which the percent holds (the depletion is worst at the lowest
  radioligand concentration and papers state one overall figure) and the receptor over the KD (no volume basis for receptor_amount).
- nonspecific_fraction (MAX_NONSPECIFIC_FRACTION 50, NONSPECIFIC_FRACTION_ZERO_AGREEMENT 90). Q1 a specific signal that is a small difference of two large
  numbers. Q2 general (NSB under half of total at the top concentration: B&T, H&T, AGM). Q3 already relative (percent of the paper's own total). Q4 an error of the
  NSB measurement reaches the specific binding multiplied by NSB / specific = p / (1 - p): 1 at 50, 2.3 at 70, 9 at 90; small changes near 90 matter most.
  CHANGED shape: linear in the log of p / (1 - p) (was linear in p). Q5 consistent (a stated value; conflicting only at the researched end). DECIDED NOT TO COLLECT the concentration at which the
  percent is stated: non-specific binding is linear in the radioligand while specific binding saturates, so the top concentration is the worst case and a
  figure stated at another concentration is milder than the top one (a lenient error, not a false failure); the field's description says 'usually at the
  highest', most papers state one figure, and a mismatch moves the gradual degree, never a status. Revisit if the real runs show papers stating several.
- nonspecific_excess (MIN_NONSPECIFIC_EXCESS 100, NONSPECIFIC_EXCESS_ZERO_AGREEMENT 1). Q1 an NSB tube in which the displacer leaves specific sites to the
  radioligand, so specific binding (Bmax, and the top of the curve) is lost into the 'non-specific'. Q2 general (100 to 1000 times its Kd: B&T, H&T, M&N). Q3
  relative to a Kd (correct). GAP CLOSED: the grader divides the displacer concentration by the displacer's OWN Kd (nonspecific_ligand_kd), or by the
  radioligand's KD only when the paper says the displacer is the unlabelled radioligand (fact); otherwise the excess is not given. Q4 the specific
  binding left in the NSB tubes is about (1 + L / KD) / x: each tenfold of excess cuts it tenfold, so 10x is half-way, not almost nothing (the linear ramp gave
  10x 0.09). CHANGED shape: linear in log(x). Q5 consistent.
- equilibrium, KD SCALE of the no-koff route (REFERENCE_KD_NM 1; owner to confirm; citations from memory). Q1 a picomolar radioligand read after a time that is
  enough for a nanomolar one: the lowest concentrations are far from equilibrium and the KD comes out too high; the old score could not see it. Q2 the five
  half-lives rule is general (H&T, M&N); that 30 min stands for about 1 nM is a judgement (typical protocols), flagged. Q3 relative to the paper's own KD
  (the grader already hands kd_nM; its refs join the verdict only when the KD lengthens the time); the association rate is not collected, so the 1 / KD
  law at a fixed kon is the scale (a faster kon would need less; not collected, not worth it). Q4 the needed time grows as 1 / KD: 0.1 nM asks 300 min, so
  a 60 min incubation gives (1 - 0.5^1) / (31/32) = 0.516, against 1.0 before (it was blind); the curve stays the concave approach, gentle near the needed
  time and steep far from it. Never less than 30 min for KD above 1 nM: a weaker constant dissociates faster, and with no koff the 30 min is the researched
  floor (the usual practice); no Q1-Q5 answer asks for less. Q5 as in the koff route and in SPR/BLI: a short incubation is partial credit, never conflicting.
  No new weight inside a degree. Old behaviour (absolute 30 min for every KD) kept for KD at or above 1 nM and for records with no KD.
- equilibrium, koff route (kept, no change; Q1-Q5 answered). Q1 same failure, judged on the paper's own kinetics. Q2 five half-lives of the slowest step
  (H&T, M&N). Q3 relative: ln 2 / koff is the slowest the approach can be (k_obs = kon [L] + koff >= koff), at the stated conditions, so the KD and
  temperature are not needed separately; koff is already collected. Q4 the same concave approach curve; the worst case (vanishing radioligand) makes it
  a conservative judge, a lenient radioligand level would shorten the true time, so the score errs low, not high. Q5 consistent with the no-koff route
  and with the other binding assays (partial credit, never conflicting).
- equilibrium (MIN_INCUBATION_MIN 30, HALF_LIVES_AT_MIN_INCUBATION 5). Q1 a binding read before equilibrium (low concentrations under-bound: KD too high; a slow
  competitor at hemi-equilibrium). Q2 the five-half-lives rule is general (H&T, M&N); 30 minutes is typical practice for a nM radioligand at room temperature, not
  for a pM one or at 4 C. Q3 should be relative: the needed time is about 5 ln2 / k_obs with k_obs = kon [L] + koff >= koff. GAP CLOSED for the off-rate: when the paper
  states koff (dissociation_rate) the incubation is judged in half-lives of ln2 / koff, the slowest the approach can be (the researched five half-lives
  stand for full agreement); the KD and the temperature are then not needed separately (koff holds at the stated conditions). Not collected: an association
  time course (the equilibrium fact already carries what it shows) and a competitor's own kinetics (hemi-equilibrium of a slow competitor stays unseen). Q4 a pM radioligand incubated 60 min can be far from equilibrium
  (now seen through the KD scale above, when the paper gives a KD); the approach curve is concave (a little short loses little). CHANGED: at or above MIN_INCUBATION_MIN supported with degree 1 (was
  unknown) and below it the approach ratio itself (was the approach times WEIGHT_UNKNOWN: an unknown weight inside a degree, against the owner rule, and
  0.9 there against the per-type 0.80 of binding_regime, a step). Q5 a short incubation is low partial credit, never conflicting.
- radioligand_range count (MIN_CONCENTRATIONS 8, SATURATION_FIT_PARAMETERS 2). Q1 a saturation curve too sparse to define KD and Bmax and to show one site.
  Q2 general (8 to 12 concentrations: H&T, M&N; SPR uses 5, a sensorgram set). Q3 absolute (a count). Q4 each point beyond the two fitted parameters is one
  check; linear in residual degrees of freedom kept. CHANGED: 2 or fewer concentrations are supported with degree 0 (were conflicting): a short series is low
  partial credit, never conflicting, as in SPR.
- radioligand_range span (LOW_FACTOR 0.25 / LOW_ZERO_AGREEMENT_FACTOR 1, HIGH_FACTOR 5 / HIGH_ZERO_AGREEMENT_FACTOR 1). Q1 a curve whose foot or plateau has
  no data (KD or Bmax extrapolated). Q2 general (about 0.1 to 10 times the KD: H&T, B&T, M&N). Q3 relative to the paper's own KD (in the grader facts). Q4 what
  the end concentrations buy is the share of the binding curve covered, the occupancy x / (1 + x): 5 -> 4 times the KD moves it only 0.83 -> 0.80, 2 -> 1 moves it
  0.67 -> 0.50. CHANGED shape: linear in the occupancy (was linear in x, steep where the occupancy hardly changes). Ends kept.
- competition_radioligand_level (MAX_RADIOLIGAND_OVER_KD 1, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT 10). Q1 a competition read at high radioligand occupancy, where
  the IC50 is mostly the C&P correction (1 + L / KD) and depletion grows. Q2 general (L at or below the KD: C&P, H&T, AGM). Q3 relative to the paper's own KD (in
  the grader facts). Q4 the share of an error of the KD that reaches the Ki is d ln Ki / d ln KD = (L / KD) / (1 + L / KD), the radioligand occupancy: 0.5 at 1,
  0.67 at 2, 0.91 at 10; it rises fastest just above the KD and saturates (the Ki error never exceeds the KD error, so the zero end at 10 rests on the
  near-saturation and depletion reason; flagged for expert review). CHANGED shape: linear in that occupancy (was linear in L / KD), the same scale as the span.
- hill_slope (MIN_HILL 0.8, MAX_HILL 1.2, MIN_HILL_ZERO_AGREEMENT 0.5, MAX_HILL_ZERO_AGREEMENT 1.5). Q1 several sites or negative cooperativity (shallow);
  depletion, titration or non-equilibrium (steep). Q2 general (0.8 to 1.2, or not different from 1: Motulsky & Christopoulos 2004, H&T). Q3 the honest scale would be
  the slope relative to its own standard error. DECIDED NOT TO COLLECT it: this criterion protects against several sites, and a slope outside the
  0.8 to 1.2 window with a wide standard error is not evidence of one site, so the spread would only rescue slopes the window rightly lowers (a gradual
  credit already softens the window). Q4 a slope of 0.7 already shows a two-site mixture as often as
  noise; the linear ramps (arithmetic, as the 0.8 to 1.2 convention is) are kept. KEPT values and shape.
- cheng_prusoff (CHENG_PRUSOFF_FACTOR 1.5, CHENG_PRUSOFF_ZERO_FACTOR 5). Q1 a reported Ki that its own IC50, radioligand level and KD do not give (another KD,
  equation or experiment). Q2 the equation is general (C&P); the 1.5-fold tolerance is a judgement for rounding and fit differences. Q3 already a relative fold.
  Q4 Ki errors are multiplicative: a 2-fold gap is as far from 1 as a 1/2-fold. CHANGED shape: linear in the log of the fold (was linear in the fold). Q5 the
  paper's own numbers disagreeing: conflicting at the researched end.
- replicates (MIN_REPLICATES 3, SINGLE_EXPERIMENT 1). Q1 errors that only separate preparations, radioligand batches and days show. Q2 general (n of at least 3
  independent experiments is usual; the BJP guidance, Curtis et al. 2018 Br J Pharmacol 175:987, asks 5 for statistics). Q3 absolute (a count). Q4 the standard
  error of the mean constant falls as 1 / sqrt(n). CHANGED shape: min(1, sqrt(n / MIN_REPLICATES)) and never conflicting for a stated count (was linear in
  n - 1 with one experiment conflicting), as in SPR, ITC, FP, AlphaScreen. SINGLE_EXPERIMENT kept, now where it applies by definition: a standard deviation from
  a single experiment is not a spread between experiments and is not turned into the effect variance.
Unknown weight (per assay, held in literature_row_contract WEIGHT_UNKNOWN_BY_TYPE / _BY_CRITERION, not here): the readout is absolute (bound fmol from the specific
activity; KD and Bmax absolute; a Ki is relative to the radioligand KD by C&P); NSB definition and subtraction are universal practice (binding_controls 0.90);
depletion and equilibrium are the usual unstated failures (binding_regime 0.80, calibration_applicability 0.80); a failed unstated detail mostly biases the
constant's size, and a displaceable specific signal rarely fakes 'binds' (default 0.85, near the label-free KD methods). This converter uses no unknown weight.
A sheet criterion that is supported carries the smallest degree of its members that have one (the sheet reads no degree; it travels with the
interpretation and the merger carries it per result).
Quote support (literature_quote_support.py, SUPPORT_DEGREE: direct 1.0, implied 0.7, about_something_else 0.3, defined once there with the
reason of each): a supported sheet criterion whose members read a stated field with support 'implied' or 'about_something_else' (the grader's
native['support'], per member) has its degree multiplied by the weakest factor; where it had no degree the degree becomes that factor; 'direct' leaves it as it
is. The variance_correspondence reads the support of the spread, its kind and, for a standard deviation, the replicate count. Support never
changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_radioligand_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('nonspecific_binding', 'nonspecific_excess', 'radioligand_quality', 'filter_binding'), 'binding_regime': ('equilibrium', 'radioligand_range', 'competition_radioligand_level', 'wash_dissociation'), 'binding_parameter_definition': ('fit_model', 'nonlinear_fit', 'hill_slope', 'cheng_prusoff'), 'calibration_applicability': ('ligand_depletion', 'nonspecific_fraction'), 'sampling_basis': ('replicates',)}
MAX_PERCENT_BOUND = 10.0  # EXPERT_REVIEW: largest percent of the added radioligand that may be bound; above about 10 percent the free radioligand is no longer the added concentration (ligand depletion) and KD and IC50 are biased (the usual rule of the receptor binding literature: H&T, B&T, AGM). Full agreement up to it.
PERCENT_BOUND_ZERO_AGREEMENT = 50.0  # EXPERT_REVIEW: percent bound at or above which the sheet takes the free radioligand as not the added concentration at all (conflicting): the receptor then equals the KD, the KD read against the added concentration is biased 1.5-fold and the competition IC50 has a floor of KD / 2 (Swillens 1995). In between the degree is linear in the log of that KD bias, 1 + f / (2 (1 - f)) (_depletion_bias).
MAX_NONSPECIFIC_FRACTION = 50.0  # EXPERT_REVIEW: largest non-specific binding, as a percent of the total binding at the highest radioligand concentration; above half the specific signal is a small difference of two large numbers and the fit is not reliable (B&T, H&T, AGM). Full agreement up to it.
NONSPECIFIC_FRACTION_ZERO_AGREEMENT = 90.0  # EXPERT_REVIEW: non-specific percent at or above which the sheet takes the specific signal as lost (conflicting); at 90 percent the specific binding is a tenth of the total and an error of the non-specific measurement reaches it nine times over. In between the degree is linear in the log of non-specific over specific, p / (100 - p) (_nonspecific_odds).
MIN_NONSPECIFIC_EXCESS = 100.0  # EXPERT_REVIEW: smallest excess of the unlabelled ligand over its Kd to define non-specific binding (usual 100 to 1000 times: B&T, H&T, M&N); at 100 times the Kd about 99 percent of the specific sites are occupied. Full agreement from it.
NONSPECIFIC_EXCESS_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: excess (over the Kd) at or below which the sheet takes non-specific binding as not defined at all (conflicting); at the Kd itself only half of the specific sites are occupied. In between the degree is linear in log(excess): the specific binding left in the non-specific tubes, about (1 + L / KD) / excess, falls tenfold per tenfold of excess.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest radioligand concentrations of a saturation series (usual series have eight to twelve: H&T, M&N; KD and Bmax are not both defined with fewer). The full-agreement end of the count; below it the degree falls linearly towards SATURATION_FIT_PARAMETERS.
SATURATION_FIT_PARAMETERS = 2  # EXPERT_REVIEW: the free parameters of the one-site saturation fit, KD and Bmax (the reason of MIN_CONCENTRATIONS); with this many concentrations or fewer the hyperbola passes through every point and no point checks it: degree 0, supported, never conflicting (a short series is weak evidence, not evidence against; as SPR's CONCENTRATIONS_ZERO). A global fit of total and non-specific binding (KD, Bmax, a non-specific slope and a background on 2n points) has 2n - 4 = 2(n - 2) residual degrees of freedom, so it ends at the same count.
LOW_FACTOR = 0.25  # EXPERT_REVIEW: the lowest radioligand concentration must be at most this multiple of the KD (about 20 percent occupancy; the usual design starts near 0.1 times the KD: H&T, B&T). Full agreement up to it; the degree is linear in the occupancy x / (1 + x).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or above which the lowest radioligand concentration leaves no low-occupancy part of the curve (conflicting); at the KD the sites are already half occupied.
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest radioligand concentration must be at least this multiple of the KD (about 83 percent occupancy, so that Bmax is defined by data; the usual design reaches 10 times the KD). Full agreement from it; the degree is linear in the occupancy x / (1 + x).
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the KD at or below which the highest radioligand concentration does not reach even half occupancy (conflicting); Bmax is then an extrapolation.
MAX_RADIOLIGAND_OVER_KD = 1.0  # EXPERT_REVIEW: the single radioligand concentration of a competition must be at most this multiple of its KD (at or below the KD the IC50 is within a factor of two of the Ki and the depletion is small: C&P, H&T, AGM). Full agreement up to it.
RADIOLIGAND_OVER_KD_ZERO_AGREEMENT = 10.0  # EXPERT_REVIEW: multiple of the KD at or above which the sheet takes the radioligand level as too high for the IC50 to say anything of the Ki (conflicting); at ten times the KD the IC50 is eleven times the Ki and the competition curve is read at near-saturation of the sites. In between the degree is linear in the radioligand occupancy x / (1 + x), which is also the share of an error of the KD that reaches the Ki (d ln Ki / d ln KD).
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: the incubation (minutes) that stands for equilibrium of a typical nanomolar radioligand at room temperature (usual protocols incubate 60 to 120 minutes, longer at low temperature or for a picomolar radioligand). Full agreement from it; below it the degree falls with the approach to equilibrium (HALF_LIVES_AT_MIN_INCUBATION); never conflicting.
HALF_LIVES_AT_MIN_INCUBATION = 5.0  # EXPERT_REVIEW: half-lives of the approach to equilibrium that MIN_INCUBATION_MIN stands for (the usual rule of the receptor binding literature: incubate for about five half-lives of the slowest step, when the binding is within about 3 percent of equilibrium, 1 - 0.5^5: H&T, M&N); it fixes how fast the degree of a shorter incubation falls.
REFERENCE_KD_NM = 1.0  # EXPERT_REVIEW (owner to confirm; new): the KD (nM) of the radioligand for which MIN_INCUBATION_MIN stands ("a typical nanomolar radioligand"). With no koff stated, the incubation needed is MIN_INCUBATION_MIN x max(1, REFERENCE_KD_NM / KD of the paper): five half-lives take a time that grows as 1 / KD for a fixed association rate (koff = kon KD; near the KD k_obs = kon [L] + koff ~ 2 kon KD), so a 0.1 nM radioligand is asked 10 times as long, a 10 nM one no less than MIN_INCUBATION_MIN (never less for a weaker constant). Continuous (no step at the reference); not capped (a picomolar radioligand really needs hours: H&T, M&N, from memory). Without a KD in the record the 30 min stands as it was.
MIN_HILL = 0.8  # EXPERT_REVIEW: lowest Hill slope that still shows one site obeying mass action; a shallower curve shows several sites or negative cooperativity (usual limits 0.8 to 1.2: Motulsky & Christopoulos 2004, H&T).
MIN_HILL_ZERO_AGREEMENT = 0.5  # EXPERT_REVIEW: Hill slope at or below which the sheet takes the curve as clearly not one site (conflicting); a slope of one half is the shallowest that two sites of very different affinity give; between this and MIN_HILL the degree falls linearly.
MAX_HILL = 1.2  # EXPERT_REVIEW: highest Hill slope that still shows one site obeying mass action; a steeper curve shows cooperativity, receptor depletion (titration) or no equilibrium.
MAX_HILL_ZERO_AGREEMENT = 1.5  # EXPERT_REVIEW: Hill slope at or above which the sheet takes the curve as clearly cooperative or not at equilibrium (conflicting); symmetric to MIN_HILL_ZERO_AGREEMENT about 1 (the 0.8 to 1.2 convention is arithmetic); between MAX_HILL and this the degree falls linearly.
CHENG_PRUSOFF_FACTOR = 1.5  # EXPERT_REVIEW: allowed fold gap between a reported Ki and the Ki calculated from the reported IC50, radioligand concentration and KD by the Cheng-Prusoff equation (rounding and fit differences are within a factor of 1.5; a larger gap shows another equation or another KD was used). Full agreement up to it.
CHENG_PRUSOFF_ZERO_FACTOR = 5.0  # EXPERT_REVIEW: fold gap of the reported and the calculated Ki at or beyond which the sheet takes them as disagreeing (conflicting); a fivefold gap is more than the whole Cheng-Prusoff correction at the recommended radioligand level (a factor of two at most) and shows that another KD, another equation or an IC50 of another experiment was used. In between the degree is linear in the log of the fold (Ki errors are multiplicative).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate experiments on separate days or preparations); wells or tubes of one experiment do not count (usual n of 3; Curtis et al. 2018 ask 5 for statistics). Full agreement from it; below it the degree is sqrt(n / MIN_REPLICATES), the precision of the mean constant (standard error ~ 1 / sqrt(n)), as in every binding assay; never conflicting for a stated count.
SINGLE_EXPERIMENT = 1  # EXPERT_REVIEW: one experiment shows no spread between experiments at all (n - 1 = 0 degrees of freedom): a standard deviation stated with this many independent experiments is a spread of wells or tubes, not of experiments, and is not turned into the effect variance (sd^2 / n would understate it).
NULL_REASONS = {'recovery': 'a_radioligand_assay_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_radioligand_nonspecific_binding_is_not_an_attribution_fraction', 'total_signal': 'a_radioligand_nonspecific_binding_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_a_radioligand_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_radioligand_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero):
    """How far the value agrees: 1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (value - zero) / (full - zero)


def _graded(value, full, zero, refs, scale):
    """Conflicting at or beyond the zero-agreement limit (checked on the value itself); else supported with a degree linear in scale(value), 1.0 at
    scale(full) (capped there) and 0 at scale(zero). ``scale`` is increasing and names the quantity the error of the criterion grows with."""
    if (value <= zero) if full > zero else (value >= zero):
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, _degree(scale(value), scale(full), scale(zero))))


def _linear(value):
    return value


def _occupancy(over_kd):
    """The fractional occupancy of one site at a concentration of this many times its KD (mass action, by definition)."""
    return over_kd / (1.0 + over_kd)


def _depletion_bias(percent_bound):
    """The log of the KD bias when the added radioligand is taken as free while this percent of it is bound (at low concentration f = R / (KD + R),
    and the half-maximal added concentration is KD + R / 2, so the apparent KD is KD (1 + f / (2 (1 - f))))."""
    f = percent_bound / 100.0
    return math.log(1.0 + f / (2.0 * (1.0 - f)))


def _nonspecific_odds(percent):
    """The log of the non-specific over the specific binding, p / (100 - p): the factor by which an error of the non-specific measurement reaches the specific binding."""
    return math.log(percent / (100.0 - percent))


def _judge_percent_bound(native):
    # A paper that says it corrected for the depletion (measured the free radioligand, or fitted a model that takes the bound radioligand into
    # account: Swillens 1995) has removed the bias that the bound fraction causes, so the fraction no longer lowers the degree. That is a stated
    # fact of the paper, not an assumption: unstated or 'no' leaves the judgement on the percent bound.
    if native['depletion_corrected'] == 'yes':
        return _verdict('supported', native['percent_bound_refs'] + native['depletion_corrected_refs'], 1.0)
    return _graded(native['percent_bound'], MAX_PERCENT_BOUND, PERCENT_BOUND_ZERO_AGREEMENT, native['percent_bound_refs'], _depletion_bias)


def _judge_nonspecific_fraction(native):
    return _graded(native['nonspecific_percent'], MAX_NONSPECIFIC_FRACTION, NONSPECIFIC_FRACTION_ZERO_AGREEMENT, native['nonspecific_fraction_refs'], _nonspecific_odds)


def _judge_nonspecific_excess(native):
    # log: the specific binding left in the non-specific tubes is about (1 + L / KD) / excess, so each tenfold of excess cuts it tenfold
    return _graded(native['nonspecific_excess_ratio'], MIN_NONSPECIFIC_EXCESS, NONSPECIFIC_EXCESS_ZERO_AGREEMENT, native['nonspecific_excess_refs'], math.log)


def _approach(half_lives):
    """The fraction of the way to equilibrium after this many half-lives of a first-order approach (by the definition of a half-life)."""
    return 1.0 - 0.5 ** half_lives


def _judge_equilibrium(native):
    # Shape: a radioligand associates with its receptor as a first-order approach to equilibrium (bound = equilibrium bound x (1 - exp(-k_obs t))),
    # so the share of the equilibrium binding an incubation of t minutes reaches is 1 - 0.5^(t / half-life). The researched MIN_INCUBATION_MIN stands
    # for HALF_LIVES_AT_MIN_INCUBATION half-lives; the degree is that approach relative to the one at MIN_INCUBATION_MIN, full from there. It is concave
    # (most of the binding happens in the first half-lives), so an incubation a little short loses little and a very short one loses most. A short
    # incubation is not the paper stating that equilibrium was not reached, so it never conflicts (a stated 'no' is the grader's conflicting).
    # The scale is absolute (minutes) unless the paper states the off-rate koff of the radioligand. Then it is relative to the paper's own kinetics: the
    # approach to equilibrium has k_obs = k_on [L] + k_off >= k_off, so the half-life of the dissociation, ln 2 / k_off, is the slowest the approach can be
    # (it is the approach at a vanishing radioligand concentration, the worst case of the lowest concentrations of a saturation series), and the
    # researched HALF_LIVES_AT_MIN_INCUBATION of that half-life stands for equilibrium (H&T, M&N). The degree is again the approach reached relative to that
    # at the researched half-lives. A picomolar or cold incubation with a slow off-rate is then seen; a fast one is no longer asked for 30 minutes. The
    # temperature and the KD are not needed separately: koff is already the rate at the stated conditions.
    if native['dissociation_rate_per_min'] is None:
        # No koff: the absolute MIN_INCUBATION_MIN stands for a radioligand of REFERENCE_KD_NM. The paper's own KD scales it: for a fixed association rate the
        # time five half-lives take grows as 1 / KD (a tighter radioligand dissociates more slowly, koff = kon KD, and k_obs = kon [L] + koff is small at the
        # concentrations near its KD). A weaker constant never asks for less than MIN_INCUBATION_MIN. Continuous in the KD; the KD is a fact the grader hands over.
        kd = native['kd_nM']
        scale = 1.0 if kd is None else max(1.0, REFERENCE_KD_NM / kd)
        needed = MIN_INCUBATION_MIN * scale
        refs = native['incubation_refs'] + (native['quantities']['kd']['source_refs'] if scale > 1.0 else [])      # the degree rests on the KD only when it lengthens the time
        reached = _approach(HALF_LIVES_AT_MIN_INCUBATION * native['incubation_min'] / needed) / _approach(HALF_LIVES_AT_MIN_INCUBATION)
        return _verdict('supported', list(dict.fromkeys(refs)), min(1.0, reached))
    half_lives = native['incubation_min'] * native['dissociation_rate_per_min'] / math.log(2.0)      # incubation over the dissociation half-life ln 2 / koff
    reached = _approach(half_lives) / _approach(HALF_LIVES_AT_MIN_INCUBATION)
    return _verdict('supported', native['incubation_refs'] + native['dissociation_rate_refs'], min(1.0, reached))


def _judge_radioligand_range(native):
    # Shape of the count: linear in the residual degrees of freedom of the saturation fit (count - SATURATION_FIT_PARAMETERS). Each radioligand
    # concentration beyond the two the one-site hyperbola needs (KD and Bmax) is one more independent check that the specific binding saturates as one
    # site (the low-occupancy part, the KD region and the plateau each need points of their own); the researched eight leave six, two leave none (degree
    # 0, never conflicting). The span: linear in the occupancy each end concentration gives, the share of the binding curve the data cover.
    count = native['concentration_count']
    count_degree = 1.0 if count is None else max(0.0, _degree(count, MIN_CONCENTRATIONS, SATURATION_FIT_PARAMETERS))
    low, high = native['concentration_low_over_kd'], native['concentration_high_over_kd']
    if low is None:
        return _verdict('unknown', [])      # the span can only be judged from the KD and a list or a lowest and a highest concentration
    span_refs = native['concentration_span_refs']
    ends = (_graded(low, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, span_refs, _occupancy), _graded(high, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, span_refs, _occupancy))
    if any(end['status'] == 'conflicting' for end in ends):
        return _verdict('conflicting', span_refs)
    refs = span_refs + (native['concentration_count_refs'] if count_degree < 1.0 else [])      # a short count lowers the degree: it rests on the count too
    return _verdict('supported', list(dict.fromkeys(refs)), min(count_degree, *(end['degree'] for end in ends)))


def _judge_radioligand_level(native):
    return _graded(native['radioligand_over_kd'], MAX_RADIOLIGAND_OVER_KD, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT, native['radioligand_level_refs'], _occupancy)


def _judge_hill_slope(native):
    slope = native['hill_slope']
    if slope < 1:
        return _graded(slope, MIN_HILL, MIN_HILL_ZERO_AGREEMENT, native['hill_slope_refs'], _linear)
    return _graded(slope, MAX_HILL, MAX_HILL_ZERO_AGREEMENT, native['hill_slope_refs'], _linear)


def _judge_cheng_prusoff(native):
    return _graded(native['cheng_prusoff_fold'], CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_FACTOR, native['cheng_prusoff_refs'], math.log)


def _judge_replicates(native):
    # Shape: min(1, sqrt(n / MIN_REPLICATES)), as in every binding assay. The main errors of a radioligand assay that one experiment cannot show (the
    # membrane or cell preparation, the radioligand batch and its decay, the day) average down over independent experiments as 1 / sqrt(n), the same
    # sd^2 / n this converter uses for the effect variance; the degree is the precision at n relative to that at the researched three. A stated count
    # is never a conflict (one experiment still gives a constant); independence not stated: unknown (a stated no is the grader's conflicting).
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', [])
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('ligand_depletion', 'percent_bound_recorded_for_the_sheet'): _judge_percent_bound, ('nonspecific_fraction', 'nonspecific_fraction_recorded_for_the_sheet'): _judge_nonspecific_fraction,
          ('nonspecific_excess', 'excess_recorded_for_the_sheet'): _judge_nonspecific_excess, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium,
          ('radioligand_range', 'radioligand_range_recorded_for_the_sheet'): _judge_radioligand_range, ('competition_radioligand_level', 'radioligand_over_kd_recorded_for_the_sheet'): _judge_radioligand_level,
          ('hill_slope', 'hill_slope_recorded_for_the_sheet'): _judge_hill_slope, ('cheng_prusoff', 'cheng_prusoff_recorded_for_the_sheet'): _judge_cheng_prusoff,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


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
    """Return (variance_nM_squared or None, reason or None, refs, degree or None); the degree is that of the replicates when the variance rests on a standard deviation."""
    native = graded['native']
    if constant_name is None:
        return None, 'no_effect_to_carry_a_variance', [], None
    name = constant_name + '_spread'
    spread = native['quantities'][name]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, name + '_not_given', [], None
    if kind is None:
        return None, 'spread_kind_not_stated', [], None
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs'], None
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        replicates = _criterion(graded, 'replicates')
        if replicates['status'] != 'supported' or count['value'] <= SINGLE_EXPERIMENT:      # a spread of one experiment is not a spread between experiments
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', [], None
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']])), replicates['degree']
    return None, 'confidence_interval_not_converted', [], None


def _variance_supports(native, constant_name):
    """The supports of the stated fields the variance rests on: the spread of the constant, its kind and, for a standard deviation, the replicate count."""
    quantities = native['quantities']
    names = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
    found = [quantities[name]['support'] for name in names] + [native['choice_support']['spread_kind']]
    return [support for support in found if support is not None]


def convert_radioligand(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if native['ic50_nM'] is not None else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'radioligand_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs, variance_degree = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'radioligand_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
    null_components.update(NULL_REASONS)
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
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # thin quote support lowers a supported degree
    if variance is not None:
        correspondence = _verdict('supported', variance_refs, variance_degree)      # a standard deviation from fewer experiments than MIN_REPLICATES is a poorer variance
        interpretations['variance_correspondence'] = apply_support(correspondence, _variance_supports(native, constant_name))
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['radioligand_preparation_ref'], 'immobilized_preparation_ref': preparations['receptor_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'radioligand', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
