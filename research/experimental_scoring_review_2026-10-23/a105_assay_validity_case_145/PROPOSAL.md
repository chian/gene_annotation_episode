# A105 case 145: coupled product validity and contaminating isomerase

Bounded scientific proposal, 2026-10-27. This is one contrasting retained case,
not a case quota, a completed A105 template, or a production grader. The original
supplied goal remains authoritative. No A106 work or final-credit change occurs.

Selected before reading a paper packet: retained group
`spec_aquifex_hfp_coupling_contamination`; **Identification of the phosphatase
essential for riboflavin biosynthesis in Aquifex aeolicus**,
[primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/).
The original XML was downloaded from Europe PMC. The failed PMC browser request
returned a challenge page; it supplied no experimental evidence. No other paper
was opened. Existing lane grades were not used. Original sources and retained
historical files were not changed.

## Scientific questions before numerical formulas

1. Does this readout establish a chemical conversion, merely detect the product
   of a coupled pathway, or identify the protein responsible? The 470-nm
   riboflavin readout addresses pathway output. A 410-nm signal alone also
   contains lumazine, phosphorylated lumazine, and intermediate breakdown
   products. Neither wavelength choice nor a preparation name measures the
   fraction of signal due to HFP.
2. Are HFP and IMP coexisting contributors or separate alternatives? In the
   one-pot comparison they are added to separate vessels; each coexists with
   RibBA, RibD, RibH and RibE, and possible expression-host contaminants. This
   is replacement between arms, with multiple contributors inside each arm.
3. What differs outside the intended HFP-versus-IMP change? Most reaction
   conditions and the common master mix match, but nominal phosphatase amounts
   differ, 8.4 versus 8.8 micromolar. Differences in purification, contamination,
   active amount and production temperature are not controlled merely by the
   shared buffer. These affect comparability independently of effect isolation.
4. Does a measured product partition validate molecular identity, quantify
   product recovery, or assign the activity to HFP? NMR and authentic standards
   support sugar-phosphate identities; the observed 39.7:60.3 partition belongs
   to the preparation. Detection of E. coli RpiA and activity in four of five
   other selected preparations argue against assigning that isomerization to
   HFP. They do not quantify the contaminant's activity share.
5. Does cleanup isolate a variable? Adding a His tag, affinity purification,
   gel filtration, and 90-degree heating changes several things. Slower
   equilibration is a measured preparation difference; its molecular cause
   needs HFP recovery and contaminant measurements. Completion time is not an
   initial velocity.
6. Which observations supply uncertainty or independent replication? Reported
   one-pot triplicates and phosphorus-NMR triplicates have no recovered numerical
   replicate measurements, SD, SEM, CI, or distinct preparation owners. Carbon
   NMR was performed once. No distribution or covariance follows from those
   repetition statements.

## Experimental facts and scope

The source molecule is A. aeolicus PP17/HFP, heterologously produced in E. coli
BL21(DE3), initially in native untagged form. A separate C-terminal His-tagged
construct was prepared for the contaminant investigation. PP11/IMP is the
comparison phosphatase. Source-organism genotype beyond the published genome
selection is not established. Construct sequence boundaries are not supplied
in the main text read here; no native in-cell equivalence is inferred.

The screening cocktail pre-generates ARAPDP and DHBP anaerobically overnight at
37 degrees C, adds phosphatases for 1 h at 55 degrees C (YigB at 37 degrees C),
then adds RibH/RibE for 2 h at 55 degrees C. Positive cocktails were assayed
individually. YigB is a positive functional control with a temperature difference,
not a matched no-enzyme blank or a numerical calibration.

The one-pot assay combines RibBA 7.6, RibD 10.8, RibH 30.9 and RibE 33.3
micromolar; GTP 1, Ru5P .72 and NADPH 1 millimolar, anaerobically, at 55 degrees C
for 4.5 h. HFP or IMP is added to separate aliquots. The main text reports
riboflavin formation with HFP and not IMP; it supplies no numerical 470-nm
sample/blank readings or product calibration. This endpoint supports the narrow
assertion **the HFP-containing preparation permits riboflavin production in this
reconstituted mixture**. It supports the proposed HFP ARAPDP phosphatase role,
with unresolved quantitative protein attribution; it does not measure an HFP
kcat, establish exclusive physiological substrate specificity, or establish
HFP-catalyzed sugar-phosphate isomerization.

In separate NMR assays, 1.4 micromolar enzymes, 50 mM Hepes pH 8, 10 mM MgSO4,
and substrate/buffer negative controls were used. HFP/IMP/buffer incubations are
55 degrees C; YigB uses 37 degrees C. Standards at matching concentrations and
buffer establish chemical shifts. IMP dephosphorylates NADPH and Ru5P; HFP does
not show those dephosphorylations under the tested conditions. Neither
dephosphorylates GTP in the 1-h assay, but both do at higher enzyme amount and
24 h. Nondetection has no reported detection threshold; it is not zero activity.
HFP also shows FMN phosphatase activity. A claim of absolute ARAPDP specificity
would therefore exceed these results.

Source locations are complete Results sections Detection of ARAPDP phosphatase
activity, Determination of phosphatase specificity, Determination of competing
activities, FMN phosphatase activity; the complete Discussion; complete Methods
for relevant expression, purification, phosphatase screens, one-pot assays,
31P-NMR and 13C-NMR. See `primary_read.txt` lines 25–90 and 102–109. Main-text
descriptions of Figs S4–S8 were read; the supplementary spectra and raw traces
were not inspected. The XML body and generated text are retained for custody;
retention of a section is not a claim of reading every XML element.

## Populated numerical cells and their combination meanings

All operands below are reported; arithmetic is derived. No synthetic scientific
values or categorical numerical grades are introduced. The exact byte-selected
operands and checked arithmetic are in `CALCULATED_CELLS.json`.

| Numerical cell | Actual operands and calculation | Value | What it evaluates; combination role |
|---|---|---:|---|
| Same-stock target/total mass-estimate ratio | Approximate visual HFP 5 / Bradford total protein 7 mg/mL | approximately .714286 | Amount denominator interpretation; not active fraction or isolation |
| Conditional mass-denominator multiplier | 7/5 | approximately 1.4 | If an identified same-stock rate is per mg total protein, multiply it once by 1.4 to express per estimated mg HFP. No such rate is reported here, so not applied |
| Between-arm amount difference | HFP 8.4 − IMP 8.8 micromolar | −.4 micromolar | Comparability outside the changed phosphatase identity |
| Between-arm nominal amount ratio | 8.4/8.8 | .954545 | Nominal amount relationship. It is not an activity-response multiplier without a supported dose-response relation |
| Preparation R5P partition | 60.3/(39.7+60.3) | .603 | Sugar-phosphate composition at observed equilibrium; distinct from total product recovery and HFP attribution |
| Preparation Ru5P partition | 39.7/(39.7+60.3) | .397 | Same composition denominator; the two fractions sum to 1 and are not two independent measurements |
| Cleanup equilibration-time ratio | t_after/t_before, with t_after >18 h and t_before <10 min | >108 | Quantifies preparation sensitivity to cleanup; elapsed completion time, not rate |
| Reciprocal completion metric | (1/t_after)/(1/t_before) | <.00925926 | Same time observations, reciprocal representation. Never an additional independent component or HFP activity-retention fraction |

The 5/7 values concern the earlier HFP chromatography stock. The article says
NMR/ICPMS samples were purified further using ammonium sulfate; the tagged/heat
sample is another preparation. **Do not attach 5/7 to either NMR preparation.**
Even for the original stock, 7−5 is not a calibrated contaminant concentration:
the methods and analytes differ, and no common calibration uncertainty is given.

The R5P fraction uses the sum of the two reported sugar-phosphate fractions.
It is not a phosphate mass balance: a normalized partition can sum to 100%
while total recovery is unknown. No relaxation/response correction, quantitative
NMR standard recovery, original integral values, or per-replicate uncertainty is
reported in the inspected main text. Do not assign quantitative NMR accuracy 1.

The manuscript reports .67 mM for the initial NMR substrate solutions but .67 M
in the reversibility protocol. This is a 1000-fold unit discrepancy in the
source, preserved as conflicting experiment linkage. It prevents silently using
either concentration to convert the equilibrium fractions into molar yields
for that reversibility comparison. The fractions/time bound themselves remain.

The observed four-of-five panel is retained as four selected preparations with
the activity among five selected preparations. It is neither a random-sample
trial probability nor .8 reliability, and adds no automatic score.

## Actual numerical sheet equation: correction operands remain missing

The implemented source-activity sheet uses

    q = sample rate − matched blank rate
    attributed_rate = q − g
    h = u/v
    a = (q − g) * v / (k * E * u)

`g` must be the contaminating contribution to that same measured endpoint; `k`
the measured recovery; `E` the applicable molecule concentration; `u,v` the
same-endpoint condition-response controls outside the intended change. This is
an explicit sum/subtraction and multiplier combination with defined physical
meanings. Its uncertainty uses the actual joint covariance once. The observed
stock factor cannot replace g or k, the nominal arm ratio cannot replace h,
and the cleanup time ratio cannot replace q.

For the coupled readout, `a` would first describe riboflavin throughput per
nominal added phosphatase in the defined mixture. A kinetic/pathway model or
direct ARAPDP/ARAPD assay is additionally needed to interpret it as HFP's own
dephosphorylation rate. It cannot simply be renamed HFP catalytic turnover.

Here q, g, k, u/v and their covariance are unquantified in the main text.
Nominal 8.4 micromolar belongs only to the one-pot arm. It cannot fill E for a
separate isomerase preparation. The standalone output intentionally leaves the
joint activity row unpopulated. The known-normal presence transformation is
inapplicable without the corresponding measurement and uncertainty model;
`source_presence_index` remains null. Unknown does not mean no activity.

An additive mixture model makes the isolation gap precise:

    observed same-endpoint rate = HFP contribution + contaminant contribution

The endpoint composition and completion times do not identify those two terms.
Even a small contaminant mass can account for all of a high-turnover activity.
Persistence across several purification methods does not create independent
attribution evidence. No fraction of HFP-attributable activity is calculated.

## Targeted TASK and extraction judgments (proposal, not installed prompt)

TASK — Determine what the HFP-containing preparation establishes about molecular
conversion in the supplied experiment. Establish the assayed construct, source
organism and expression host, purification history, substrate/product identities,
coupling enzymes and actual measured endpoint. Keep the one-pot, untagged NMR,
and tagged/heat preparations separate. Decide whether compared molecules replace
one another between vessels or coexist within a vessel. For each observed
conversion, identify alternative contributors, chemical instability and readout
interference. Determine which measurements assign the activity to HFP and which
only identify product or preparation activity. Check authentic standards,
quantitative recovery, background controls, substrate loss/product appearance,
and whether controls share the same sample, calibration or denominator. Read the
neighboring descriptions of contaminating RpiA before interpreting isomerization
as HFP activity. Preserve limits, completion-time endpoints, conflicting mM/M
conditions, untyped repetition and unknown preparation identities. Select exact
source spans for the requested numerical facts; calculators perform arithmetic.
Return partial supported facts and specific unresolved relationships. Do not
fill missing attribution or calibration with purity, wavelength choice, counts,
or an overall quality label. Do not calculate transfer to another protein.

STEERING — Example of a concise next-decision table, using only admitted facts:

| Fact affecting the next decision | Qualification |
|---|---|
| Preparation interconverts Ru5P/R5P | HFP attribution unresolved; RpiA detected |
| Cleanup changes completion time from <10 min to >18 h | Multiple variables change; recovered HFP amount unknown |
| Same-stock HFP/total estimates 5/7 | Different stock from NMR/cleanup comparisons |
| .67 mM versus .67 M | Source protocol conflict; no concentration conversion |

This is a proposed case-specific TASK insert and steering illustration. The
parent's actual return form still controls requested output. There is no
production prompt change, second report-composition call, new episode type,
continuation gate, or synthetic controller observation.

## Exact field → reader → component mapping and implementation boundary

| Fields and required scientific meaning | Reader/calculator | Status and resulting cells |
|---|---|---|
| `quantities.numerator` HFP visual 5 mg/mL; `denominator` Bradford total 7 mg/mL; subject/construct/preparation/stock/method/basis; same-stock relationship; approximation; reported uncertainty | `read_amount_inputs` → `populate_amount_components` → `LiteratureAmountRepository.project_cells` | Existing complete files inspected. Can represent amount ratio and conditional denominator factor. This case was not run through repository or LiteratureEpisodes |
| `quantities.numerator` nominal HFP8.4 μM; `denominator` nominal IMP8.8 μM; separate-arm relationship and intended change | Same existing amount path | Difference −.4 μM, ratio .954545; no response correction. This case not integrated |
| `assay` subject/construct/preparation/endpoint/arrangement and source witnesses; `primitives.q,g,k,E,u,v`; actual covariance and observation model | `read_assay_inputs` → `populate_corrected_activity` → `LiteratureAssayRepository.project_cells`, `assay_cells_schema` | Existing complete files inspected. Point-input rate route cannot populate censored completion times or composition; missing same-endpoint rate/correction inputs remain null |
| `product_partition.experiment/preparation/endpoint`; `species[].identity`, `reported_fraction`, denominator species, authentic-standard identity, numeric qualification, calibration/relaxation meaning, original measurement owner, uncertainty kind and repeats | Proposed **unimplemented** `read_nmr_product_partition`; deterministic `populate_product_partition` | New targeted producer/representation needed for reported .603/.397 with correct denominator. Neither a generic rate nor a per-protein amount field suffices |
| `completion_comparison.before/after` construct/purification/heat/history; `endpoint_definition`, elapsed time value/unit/comparator; starting state and substrate; equilibrium criterion; HFP recovery, same-condition relationship, physical owner, sampling uncertainty | Proposed **unimplemented** `read_equilibration_time_comparison`; deterministic bound unit conversion/division | Produces >108 time ratio and <1/108 reciprocal metric with open bounds and unresolved same-endpoint criterion; not an initial-rate operation |
| `attribution_controls` RpiA identification, activity of selected other preparations, actual matched contaminant depletion/addback or absolute activity calibration if present | Aspect-specific interpretation plus proposed **unimplemented** attribution-control producer for such measurements | Current article has qualitative identification, not g. Need quantitative same-endpoint contaminant measurement to populate g; RpiA MS identity alone cannot do so |

New product/time readers must be defined against the numerical rows above,
including open bounds, denominator membership, experiment owners and missing
conditions, before any production coding. No shared operation, schema, consumer,
or test was changed. The standalone calculation is not an installed reader.
Other raw-rate/domain/delivery paths were not claimed as inspected or executed.

## Named weaknesses, complementary experiments and dependence

| Weakness | Experiment that addresses it | Correct numerical use and dependence |
|---|---|---|
| RpiA may own observed isomerization | Remove/quantify RpiA in the same preparation, measure HFP recovery and time-resolved substrate/product, with matched RpiA add-back | Supplies contaminant contribution or constrained mixture terms; cleanup plus add-back reuses baseline and must retain shared error |
| Coupled product is not direct HFP dephosphorylation rate | Quantify ARAPDP loss, ARAPD appearance and phosphate with authentic standards and matched blanks | Productive coupling/product recovery measured separately; correction operands enter once, not extra independent proof bonuses |
| 410-nm signal has multiple contributors | Product-resolving chromatography/MS/NMR plus calibrated spectrum/background | Establishes which species contribute; product identity alone does not supply quantitative fraction at 470 nm |
| Amount differs between comparison arms | Matched active enzyme amounts or measured dose-response in those preparations | Amount-response calibration can correct outside-variable differences; nominal ratios alone cannot |
| Partition has unknown quantitative response and total recovery | Quantitative NMR with standards, response/relaxation checks and phosphate mass balance | Correct integrals once before fractions; .603/.397 complement each other and share denominator |
| Triplicate labels have unknown independent units/spread | Retain replicate values and preparation/aliquot ownership, shared standards and controls | Supplies appropriate SD/SEM/covariance; a repetition count alone gives no uncertainty model |

31P-NMR and 13C-NMR are complementary product-identity evidence with different
spectral information, potentially using the same preparation. They are not two
independent preparations or two repeated estimates of HFP catalytic activity.
Figures, captions and Results restating the equilibrium are one reported result.
The two time metrics and the mass ratio/reciprocal are arithmetic aliases. The
4/5 panel addresses a contamination alternative and does not establish its
population frequency. FMN activity narrows specificity; it is not automatically
a contradiction of the more limited ARAPDP-activity assertion.

## What this case changes in the A105 template proposal

Preserve numerical correction components and separate comparability/isolation.
Add explicit reader-supported endpoints for reported product composition and
censored completion-time comparisons when useful, with their scientific limits.
Do not retrofit them as activity rates or reliability multipliers. This paper
does not supply a calibrated source-reliability number; a case with incomplete
attribution remains an informative partial example. Missing source facts and
missing product/time reader implementations are separate unfinished matters.
This one workload does not establish A105 adequacy or close the larger goal.
