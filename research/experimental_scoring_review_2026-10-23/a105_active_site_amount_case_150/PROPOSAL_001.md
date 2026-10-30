# A105 functional-site amount: one original-source case

2026-10-27. Research proposal, not an implemented reader, settled overall A105
sheet, annotation-credit policy, or completed goal. No production file changed.
The original supplied goal remains authoritative at its attachment path; this
document supplies case evidence and implementation proposals only.

Source: Voget et al., *Development of an active-site titrant for SARS-CoV-2 main
protease as an indispensable tool for evaluating enzyme kinetics*, DOI
10.1016/j.apsb.2024.03.001, PMCID PMC11121168, PMID 38799620.
[Original article](https://doi.org/10.1016/j.apsb.2024.03.001).
[Publisher supplement](https://ars.els-cdn.com/content/image/1-s2.0-S2211383524000820-mmc1.pdf).
Source bytes, exact read scope and reset provenance are in READ_PROVENANCE_001.json.

## Experimental definitions and what the measurements establish

The biochemical subject is recombinant SARS-CoV-2 main protease (Mpro), either
C-terminally His10-tagged or with that tag removed by HRV 3C protease. The
N-terminal autocleavage sequence and C-terminal HRV 3C cleavage linkage are
specified in Methods 2.1 (XML p0035). Exact viral strain, amino-acid boundaries,
the biochemical preparation's expression host and method of protein mass
quantification are not established in the read biochemical methods. The
supplement's crystallographic preparation specifically uses E. coli BL21(DE3);
do not silently assign that host or preparation to every biochemical batch.
No catalytic mutant comparison is used in the amount experiment. The cited
C145A structure is a structural comparator, not a coexisting biochemical arm.

The titration uses synthetic aza-tetrapeptidic nitrile 1 to inactivate Mpro
before addition of a fluorogenic peptide. Methods 2.3 (p0045) specifies at least
eight final titrant concentrations, generally 2–27.5 nM, 5 min pre-incubation
at 37 degrees C, followed by substrate 2 at 50 micromolar, total volume
50 microliters, and 4% DMSO. The no-titrant DMSO control defines 100% residual
rate; it is not a no-enzyme blank or a measured zero contaminating contribution.
Assay buffer: 50 mM MOPS pH 7.2, 10 mM NaCl, 1 mM EDTA, .01% Triton X-100.
The fluorescence readout is followed for 10 min. Residual rate divided by the
no-titrant rate is regressed against final titrant concentration; the x-intercept
is interpreted by the source as active-site concentration.

The 25-microliter pre-incubation mixture is diluted to 50 microliters on substrate
addition. Reported final concentrations already account for that dilution.
Do not multiply the reported intercept by two while leaving protein amount on
the final-volume basis. A generic implementation would record volumes and the
concentration stage explicitly; this case needs no extra dilution correction.

Main text p0085 reports covalent attachment to catalytic Cys145 in a 1.77-Angstrom
complex structure, and fast irreversible inhibition. The authors consequently
propose 1:1 titrant-to-active-site stoichiometry. This is supported experimental
interpretation, not a measured universal calibration constant. Each protomer
contains one described catalytic site (p0015). Mpro is a dimer; report site/monomer
equivalents, not the fraction of dimers having at least one active site. A general
reader must distinguish site count from protein-particle count.

This establishes an amount relevant to catalytic peptide cleavage under the
declared conditions. It is not a measurement of native viral replication,
natural polyprotein processing rate, all substrate specificity, or target
correspondence. Fluorogenic cleavage, covalent-site structure, pre-incubation
checks and reporter-substrate checks address different weaknesses. They do not
become independent preparations of the activity assay.

## Numerical sheet proposal paired with extraction fields

All real reported source values below have their actual units and qualifications.
Computed digits expose arithmetic and do not increase source precision.
`null` means unknown with a reason, never an imputed zero or one.

| Extraction fields and source | Proposed numerical cell and calculation | Populated value | Meaning |
|---|---|---:|---|
| Fig 2: final His-tagged protein mass concentration rho=2.0 ng/uL; p0090: assumed monomer molecular mass M=34.21 kDa | `total_monomer_concentration = rho/M`, with units converted to g/L and g/mol | 58.46244 nM | Protein-based monomer-equivalent denominator under the paper's assumed mass; its mass-assay calibration is unreported |
| Fig 2: active-site x-intercept Ea=32.6 nM | `active_site_concentration`, copy source value | 32.6 nM | Functional-site amount for these aliquots and conditions; not nominal amount |
| Fig 2 Ea and rho; p0015, p0085–p0090 site/stoichiometry meaning | `functional_sites_per_total_monomer = Ea/(n_sites*rho/M)`; n_sites=1 per monomer | .557623 | Functional-site fraction on this preparation's monomer basis; source reports rounded 56% separately |
| Same operands and same-preparation linkage in Fig 2 | `conditional_nominal_denominator_factor = 1/f` | 1.7933263 | Converts an actual same-stock rate per total monomer to rate per active-site equivalent; no rate application performed here |
| Fig 2 regression spread=3.8 nM, specifically SD associated with the linear regression | `relative_regression_spread = 3.8/32.6` | .1165644 | Relative spread of the fitted amount, not preparation CV, SEM or confidence probability |
| Fig S5: native rho=7.5 ng/uL, Ea=43.0 nM, spread=.9 nM; same paper-assumed M | same native amount/fraction/factor cells | total=219.23414 nM; f=.19613733; F=5.0984684; relative spread=.02093023 | Separate native preparation; source reports rounded 20% |
| Fig S2: same-preparation aliquots at 5 and 20 min: 24.5 and 25.0 nM | `preincubation_amount_difference = Ea20-Ea5`; `preincubation_amount_ratio = Ea20/Ea5` | +.5 nM; 1.0204082 | Sensitivity of inferred site amount to this incubation change; does not establish a universal incubation correction |
| Fig S3: reporter 2–5 estimates 28.4,29.2,28.9,28.7 nM | `reporter_amount_range = max-min`; `reporter_max_min_ratio = max/min` | .8 nM; 1.0281690 | Empirical reporter dependence within this tested set; not independent replication or a probability |
| Fig S6: native/tag mass=5.65/2.0 ng/uL; active fractions=.20/.56 | `mass_amount_ratio_native_tag`; `active_amount_ratio_native_tag = (rhoN*fN)/(rhoT*fT)` on the same stipulated monomer basis | 2.825; 1.0089286 | The arms use different total mass to approach equal active concentration; approximately 33 nM each is stated in Methods 2.4 |
| Fig S6: active-normalized kcat=.221(native),.173(tag) s^-1 | `active_normalized_turnover_ratio_native_tag` | 1.2774566 | Measured functional comparison after active-site amount normalization; no uncertainty of this ratio established |
| Fig S6 kcat/Km=2170(native),2030(tag) L/mol/s | `active_normalized_efficiency_ratio_native_tag` | 1.0689655 | Comparison on substrate 2 under these conditions, not equivalence proof or universal tag effect |

Fig 2 uses five experiments from aliquots of one preparation; Fig S5 uses three
from one native preparation. This directly supports one named preparation per
figure, not five or three independent protein preparations. Fig S2 and S3 also
use aliquots from the same preparation within each figure. The shared 1.64 ng/uL
recipe does not establish that S2 and S3 are identical experiments or stocks;
their numerical results must not be pooled on that basis. Figure 3/S6 triplicate
measurements do not establish three independent preparations.

These are numerical components usable in an experimental-evidence sheet. The
ratios quantify denominator/comparability effects and assay sensitivity. None
is an overall experimental-reliability score. No bounded probability is inferred
from their closeness to one. The full amount precision and quantitative effect
isolation remain unknown. The existing sheet must permit those unknowns while
retaining the measured amount and sensitivity components.

## Explicit physical combination and uncertainty behavior

For a rate v and actual total monomer concentration C from the assayed stock,
`a_total = v/C`, `Ea = n_sites*f*C`, and
`a_site = a_total/(n_sites*f)`. For this monomer/site convention n_sites=1.
This is a physical denominator conversion. It is applied once only if the
source rate's denominator is actually total monomer amount for this stock.

Using the source-rounded fractions for the explicit Fig S6 linkage:

* Counterfactual total-monomer-normalized turnover from the reported active-site
  result is `.173*.56=.09688 s^-1` (tag), `.221*.20=.0442 s^-1` (native).
  These are derived denominator illustrations, not separately measured rates.
* Their ratio `.0442/.09688=.4562345` becomes the active-normalized comparison
  by multiplication with `.56/.20=2.8`: `.4562345*2.8=1.2774566`.
* The reported `.173` and `.221 s^-1` already use active-site concentration.
  Applying `1/f` to either reported kcat would repeat the correction incorrectly.
* An equal-total-protein comparison would conflate catalytic rate per active
  site with preparation active fraction. Conversely, this normalization does
  not isolate a causal tag effect from all other preparation differences.

For an actually source-supported titrant intercept Ieq that has not already
been expressed as site amount, `Ea=Ieq/nu`, with nu the number of titrant
molecules consumed per site. Require its experimental meaning and endpoint
stage. Here source 32.6 nM is already described as active-enzyme/site amount;
do not apply the stoichiometric conversion twice.

For `f=Ea*M/(n_sites*rho)`, variance, if supported, is `J Sigma J^T`, with
the ordered gradient for `(Ea,M,rho)` equal to `(f/Ea,f/M,-f/rho)`, plus any
actually supported uncertainty in site/stoichiometric assumptions. For
`F=1/f`, first-order variance is `Var(f)/f^4`. For `a=v/Ea`, the ordered
gradient is `(1/Ea,-v/Ea^2)` and
`Var(a)=Var(v)/Ea^2+v^2*Var(Ea)/Ea^4-2*v*Cov(v,Ea)/Ea^3`.
Missing covariance is not zero. A derived f shares Ea and rho; do not treat
f and Ea or f and total amount as independent repeated measurements.

This paper gives regression SD for Ea but no full joint uncertainty for protein
mass, assumed molecular mass, titrant concentration calibration, or kinetic
rate/amount dependence. Full f/F/activity uncertainty therefore remains null.
Supplement S17 reports 95% LC-MS/DAD purity for titrant 1. That chromatographic
purity is not a calibrated molar fraction or a measured active titrant fraction;
it cannot automatically supply a .95 concentration multiplier. No gravimetric
stock calibration uncertainty or correction for that purity is supplied by the
read titration methods. Preserve this limitation alongside the source's 1:1
stoichiometric interpretation.
An explicitly labeled *regression-only conditional spread*, holding rho/M fixed,
would be `3.8/58.46244=.064999` for the tagged fraction and
`.9/219.23414=.0041052` for native. These are not total SDs or confidence
intervals; they must not replace missing full uncertainty. The reported SDs are
not promoted to known normal variance. Likewise S2/S3 ratio uncertainty remains
unknown without covariance. No normal-score/profile-index calculation is justified.

Signal subtraction, instrument calibration, functional amount normalization,
condition-response correction and contamination correction have different
meanings. A valid extended activity expression could use the existing physical
sum/multiplier structure `((q-g)/k)*(v_condition/u_condition)/Ea` when all
operands are actually supported. This case does not supply measured g=0, k=1,
or unit condition response. Thus it cannot populate the full existing
`corrected_activity` by inserting defaults. The source's reported kinetic
result can remain a reported result without fabricating those operands.

## Separate recurring investigation TASK proposal

Determine what the functional experiments establish about the molecule connected
to the supplied sequence, selected file material or snippets. An initial function
or searchable public name is not required. Identify the assayed molecule,
construct, preparation, actual endpoint and functional assertion before assigning
amounts to the comparison. Read how protein quantity was measured and distinguish
total protein, nominal molecule recipe, target mass and experimentally counted
functional sites. When an active-site titration is available, inspect the titrant,
stoichiometric meaning, irreversibility or turnover assumptions, residual-activity
reference, incubation time, limiting reagent and dilution stage. A reaction
amplitude alone is not a site count when turnover, binding kinetics or substrate
limitation can determine the amplitude.

Determine whether the active-site measurement and activity rate concern the same
stock and assay state. Establish whether the rate is already normalized by active
amount. Compare relevant preparations separately; replacement across wells does
not establish coexistence or purity. Distinguish a preparation's inactive fraction
from enzyme specificity or a background contaminating activity. Examine controls
that change incubation or reporter and retain both the measured sensitivity and
its limitations. Preserve uncertainty kind, shared aliquots and missing joint
uncertainty. Identify which complementary experiment addresses each weakness.
Return the parent's typed information with source-backed operands and constrained
meaning selections. Keep target correspondence and final annotation credit separate.

The detailed recurring TASK above stays separate from the sheet and calculator.
Decision-specific STEERING may concisely state, for example: "Active-site amount
reported; total-protein method unreported; rate already active-normalized."
Host identities, hashes and record tracking do not belong in that steering text.

## Targeted reader/calculator proposal and actual implementation gap

Propose a narrow `read_reported_active_site_amount` operation, not a relabeling
of the existing nominal/mass reader. It would receive source span selectors for
the reported active-site amount and spread; subject/construct/preparation/stock;
method and endpoint (here irreversible titrant residual-rate x-intercept);
amount basis (sites, monomers or oligomer particles); concentration stage;
stoichiometric/source-model witnesses; optional mass concentration and molecular
mass with their methods; same-stock and rate-denominator relationship witnesses;
and physical observation/dependency identity. Supported meanings must include
unknown and conflicting values. Numbers and units are parsed deterministically.
Selecting a source-supported interpretation does not prove the model universally.

`populate_active_site_amount_components` would consume those typed operands and
populate the exact amount, fraction, factor, spread and missing-reason cells above.
It needs explicit site/particle conversion and compatible amount-stage checking.
It must retain a source-reported active fraction independently of the recomputed
fraction, and preserve discrepancies without clamping. Optional titration raw-data
fitting is a separate unimplemented route: the published figures do not provide
an actual numerical point table here, so no fit was performed or invented.
An active fraction outside [0,1] is retained as an inconsistent estimate with
its reason, not silently made a physical fraction or normalized activity factor.

Literature selection and an actual dataset carrying titration measurements could
populate the same scientific cells. A separately typed dataset interface and
source-owned covariance would still need implementation and verification.

Existing complete paths read: literature_amount_inputs.py, calculations.py,
prompt.py and storage.py; literature_assay_inputs.py, activity_calculations.py,
and assay_prompt.py. Amount input enums support same-stock target/total mass
estimates and between-arm nominal molar amounts only. Their validator/calculator
cannot accept an active-site measurand; units ng/uL, nmol/L and kDa also require
an appropriate explicit unit path. Storage projection retains no active-site
method, site stoichiometry, molecular mass, amount-stage or rate-denominator binding.
The assay point reader can parse an explicitly reported E concentration only
with its own strict unit spans, but has no site-basis and same-stock validation
for this proposed amount graph. Its calculator requires q,g,k,E,u,v and cannot
substitute this fraction for k. None of these gaps is completed by this case note.
No generic fluorescence/IFE calculator was implemented or borrowed from the
NADH-specific optical path. Its operation was not inspected or used here.

The important complementary experiments in this same paper are fast irreversible
inactivation (reported bound >70,000 L/mol/s; do not convert into an exact rate),
covalent-site crystallography, the S2 incubation comparison, S3 reporter
comparison, free-fluorophore calibration and IFE correction. They address titrant
meaning, completion and detector response; they do not supply a measured zero
off-target contribution, protein mass uncertainty, independent preparation
replication, or a universal reliability number. Synthetic substrate activity
does not by itself establish native biological substrate performance.
