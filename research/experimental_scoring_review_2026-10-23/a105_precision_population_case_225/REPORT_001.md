# A105 precision case225: actual reported curves and estimator-specific uncertainty

This is a one-paper research conversion and numerical proposal. It adds no production grader, installed operation, episode type, scoring policy or annotation-credit calculation. The fixed goal remains authoritative; no goal or amendment file was changed. The common assessment remains unfinished. Effect isolation, endpoint relevance, comparability and statistical precision remain separate questions.

## Source and selected experiment

Yang et al.2023, *Construction of an artificial phosphoketolase pathway that efficiently catabolizes multiple carbon sources to acetyl-CoA*, DOI10.1371/journal.pbio.3002285. Original article and supplementary workbook are retained in `originals/`, with primary URLs, exact hashes and byte/cell witnesses in SOURCE_PACKET_001.json. No new experiment, complex biology suite or actual model-backed episode was run.

The selected data are **WT BbPK with DHA**, S1Data.xlsx, Sheet1, FigS17 block: panel A189, rate/endpoint B190, subject Q191, reported column labels R192:S192:T192 and concentrations Q193:Q205 with rates R193:T205. All39 selected rate cells and13 concentration cells are numeric nonformula cells. Exact decimal lexemes, worksheet/member identities, complete cell XML and uncompressed member byte spans are retained. `data-1`, `data-2`, `data-3` are source reporting labels, not inferred physical-preparation IDs.

The source molecule is BbPK, described as from “Actinobacteria Bifidobacterium,” expressed from pET-28a in E.coli BL21(DE3), nickel-affinity purified; BCA uses BSA as standard. This selected curve is wild type; mutants and other substrates occur elsewhere but are not substituted into its39 readings. Exact retained tag/construct boundaries, preparation identities and the mapping from synthesized sequence labels to this data block remain unknown. No target-to-reference correspondence is evaluated.

DHA concentration changes across thirteen values1,2.5,5,10,20,30,40,50,60,70,80,90,100. The S17 caption gives mM and0.25mg/mL enzyme and says error bars are SD,n=3. The workbook concentration column itself has no explicit unit header. The methods describe a coupled nicotinamide readout with PK plus AckA, hexokinase and glucose-6-phosphate dehydrogenase. These helpers coexist; the reported curve is not a measurement of purified PK alone without coupling contributions.

There are important source limitations:

- **Endpoint conflict:** workbook B190 says “NADH consumption rate µmol min-1”; the short-chain methods describe NADPH production at340nm. Preserve both. This report does not silently choose a cofactor or direction, call it a chemically identified product rate, or derive a cofactor/product stoichiometry.
- **Protocol ambiguity:** the PK/mutant method describes100µL with approximately0.5mg/mL PK; the multi-species short-chain method describes200µL with0.25mg/mL PK and different helper amounts. S17 caption states0.25mg/mL. The nominal PK mass happens to be0.05mg in either described formulation, but equal nominal mass does not establish the actual preparation, volume, helper conditions or active fraction of these cells.
- **Repetition scope:** the article describes triplicate experiments and the workbook has three labelled data columns. It does not establish independent enzyme preparations or physical pairing across concentrations. The column structure is usable reporting-level grouping. Its physical/sampling interpretation remains unknown.
- **No quantitative matched blank or recovery is linked to these39 rates.** Statistical dispersion therefore cannot become molecular attribution, an assay false-positive rate, quantitative product recovery or an overall reliability probability.

## What the existing164 case supplies, and what changes here

The earlier Fig2B case164 has three Parallel-labelled activity entries per substrate. Those support descriptive mean/SD/CV and substrate contrasts, while preparation grouping, pairing and the meaning of its printed± remain unknown. They do not supply a joint covariance for a selected mean merely because there are three entries.

The same paper's S17 **rate grid** supplies a new, explicit comparison of uncertainty bases: per-concentration observed spread, dispersion of three fitted reporting-column parameter vectors, and uncertainty of a fit to the point means under a separately stipulated sampling model. These are different estimators and must not share covariance by convenience. They are numerical sections of the same logical A105 assessment, not new axes or three independent assay graders.

## Populated numerical components from original-source cells

For each concentration let yij be the actual rate in source column j. The descriptive point mean is sum(yij)/3; sample variance is sum((yij-mean_i)^2)/2. These describe the three reported values. There is no unconditional SE or independent-preparation count.

| Concentration | Original cells | Mean, source µmol/min convention | Descriptive SD | SD/mean |
| --- | --- | ---: | ---: | ---: |
|10mM|R196:T196|0.0008054300|0.00002809726|0.03488479|
|100mM|R205:T205|0.0036631193|0.0006945665|0.18961066|

The unequal spreads are visible facts about these entries, not proof of a particular noise model. Source error bars labelled SD do not become parameter SEs. All thirteen point summaries and exact source-fraction means/variances are in NUMERICAL_COMPONENTS_001.json.

### Fitted reporting-column dispersion

The **proposed research fit**, not a quoted source measurement, minimizes unweighted squared residuals to v(S)=Vmax*S/(Km+S) separately for each labelled reporting column. Positive Km is profiled with an analytical least-squares Vmax. A golden-section solution and an independent derivative-root solution agree. Vmax retains the native reported amount-rate convention; it is **not kcat**.

| Source reporting column | Derived Vmax, µmol/min | Derived Km, mM |
| --- | ---: | ---: |
|data-1, R193:R205|0.004760076|29.23415|
|data-2, S193:S205|0.005475490|41.38770|
|data-3, T193:T205|0.006021939|38.86463|

For these three derived vectors θj=(Vj,Kj), their mean is (0.005419168,36.49549). Their **descriptive** joint sample covariance is:

| | Vmax | Km |
| --- | ---: | ---: |
|Vmax|4.0045379e-7 (µmol/min)^2|0.0032447408 (µmol/min)*mM|
|Km|0.0032447408 (µmol/min)*mM|41.136819 mM^2|

The correlation is0.7994447. This is measured-data-derived parameter dispersion across reporting columns. It is not covariance of a population mean or of the paper's published parameters.

**Explicit conditional illustration using these actual data:** if the three reporting-column vectors were IID exchangeable units, C(meanθ)=sampleCov(θ)/3. That assumption is not source-established. First-order log-efficiency variance then is:

Var[ln(V/K)] = Cvv/V² + Ckk/K² - 2*Cvk/(V*K)

=0.004545335+0.010295109-0.010937469=**0.003902974**, with standard uncertainty0.06247379. Omitting the covariance term gives0.014840443. These are alternative representations of one dependent calculation, not independent evidence or extra score credit. No normality, p-value, confidence level or probability of function is inferred.

### A different estimator needs different covariance

The unweighted fit to the thirteen point means is (Vmax,Km)≈(0.005379052,35.87599), distinct from the mean of three fitted parameter vectors. S5Table reports BbPK/DHA Km35.88mM, which is consistent after rounding with the point-mean fit. That numerical agreement does **not** establish the source's fit basis, weighting, raw-to-fit linkage or uncertainty method. In particular, sampleCov(column fits)/3 cannot be attached to the published35.88 just because it is nearby.

For the explicitly stipulated IID reported-curve-vector scenario, one can instead calculate the covariance of this actual **fit-to-means estimator**. Let S_y be the full13×13 sample covariance of the three reported curve vectors, preserving their cross-concentration reporting-column association. Let A be the derivative of the selected fitted parameter vector with respect to the thirteen means. Then:

C_fit ≈ A*(S_y/3)*Aᵀ.

At the least-squares solution, A=(JᵀJ−sum_i residual_i*Hessian(f_i))⁻¹Jᵀ. The residual Hessian term is retained; it is not silently replaced by a zero-residual approximation. The resulting conditional matrix is:

| | Vmax | Km |
| --- | ---: | ---: |
|Vmax|1.4746116e-7|0.0012395590|
|Km|0.0012395590|14.341856|

Its first-order log(Vmax/Km) variance is **0.00339273234**, standard uncertainty0.05824717. Three independent directional re-fits verify the sensitivity and propagated variance (0.00339273235). The matrix has the same row/column units as above. It targets the fit to mean rates, not the mean of separately fitted parameters. Full13×13 reporting-column covariance is preserved; no independence across concentrations is fabricated.

This remains conditional statistical analysis of actual values. Column labels do not prove physical pairing or IID biological units. The unconditional covariance of the published S5 parameters remains **unknown**. POOLED_ESTIMATOR_COVARIANCE_002.json preserves the exact estimator, derivative, covariance and assumptions.

### Explicit sum assessing the curve model

For the fit-to-means curve, the39-value residual sum of squares decomposes as:

5.80654785e-6 = 4.30553793e-6 + 1.50100991e-6.

The first term is spread within concentrations; the second is three times the mean-curve residual sum of squares. This identity keeps repetition scatter and model discrepancy distinct. It supplies no lack-of-fit p-value or universal acceptance threshold, especially given unequal source spreads and unresolved sampling design.

## Bearing on the functional assertion

The measured-rate spread and parameter covariance inform **precision of the selected reporter-kinetic inference**. They do not establish accuracy, the fraction attributable to PK, or chemically identified AcP production. Vmax is an amount-rate amplitude; kcat would additionally require the applicable enzyme amount in molecular units and its active-fraction/normalization meaning. Nominal protein mass alone is insufficient.

The article's S3 test includes a no-PK control and acetate detection after AcP decomposition. S5 uses GC-MS to identify formaldehyde for DHA and glycolaldehyde for erythrulose. These are complementary assays addressing product/background and coproduct identity. They are not new independent preparations inferred from figure count, and their qualitative identities do not calibrate the rate-grid covariance or resolve its NADH/NADPH conflict. Quantitative matched blanks, matrix/coupling recovery and an explicit rate-grid-to-product assay linkage would address weaknesses left by the kinetic precision calculation.

Statistical and experimental comparisons combine only through their declared models: subtraction of applicable background, multiplicative recovery/amount/response corrections when measured, and signed J*C*Jᵀ propagation for the **same selected estimator**. Unknown correction factors and cross-assay covariance remain unknown. No universal reliability/validity/relevance grade or arbitrary multiplier is added.

## Current implementation and precise missing conversion

Complete inspected implementation paths are recorded in READ_PROVENANCE_001.json:

- `literature_rate_replicate_inputs.py`/`calculations.py` parse an explicitly mapped CSV/TSV with actual sampling-unit and observation meanings. They compute descriptive unit summaries and explicitly conditional IID-unit/pair SEs. That does not authorize inventing physical IDs for these reporting columns.
- `literature_rate_observation_inputs.py`/`calculations.py` read selected original XLSX entries, retain exact cell custody and calculate descriptive mean/SD/CV. Their accepted layout is contiguous row-labelled observations under group headers in a selected subject column. **S17 is transposed:** concentration rows and data1–3 columns. Its grid cannot simply be passed as that layout or silently transposed while pretending it was the original source.
- `literature_kinetic_calculations.py` and `literature_kinetic_model_inputs.py` consume supplied kinetic parameter/log-covariance records. They do not fit raw rate curves or produce covariance. Their two comparison operands must have the same parameter kind. C(Vmax,Km) is not the existing numerator/denominator log-covariance type.
- The current common reader/calculator consumes selected native kcat/Km rows and a supplied covariance of actual selected estimates. It has no Vmax role or raw-grid-to-derived-fit-estimate conversion, and no uncertainty propagation for its low-substrate-efficiency contrast. The covariance producer must retain sampling/model/estimator scope; the matrix alone is insufficient. This research output cannot be relabelled as its existing covariance source.

Missing source facts: physical preparation/column pairing identities, source fit basis and weighting, linkage resolving the cofactor/direction conflict, applicable active amount, numerical blank and recovery. Missing implementation: a source-bound transposed-grid reader and an estimator-specific dispersion/conditional-covariance calculator/typed handoff. These are distinct. No physical preparation count, current common-model export or unconditional covariance is populated here.

The one proposed narrow implementation interface is in FUNCTION_IO_PROPOSAL_001.md. It reuses the existing literature assay/reader path with a typed reported-curve section after review; it does not add a new episode or impose an assay itinerary. TASK_PROPOSAL_001.txt supplies the scientific investigation distinctions separately from the numerical sheet. No production implementation is released by this research.

## Verification and preservation

Both research calculations ran successfully using only Python standard-library source reading, basic statistics and elementary numerical minimization. No new package was installed. An initial optional openpyxl import was unavailable; the source workbook was instead read directly with ZIP/XML and exact cell lexemes. Original source hashes, all39 rate-cell witnesses, selected headers and methods are retained. Text witnesses were checked against normalized original HTML, with exact offsets in the separately identified retained-text representation.

Three per-column fits agree across two algorithms; the39-value sum-of-squares identity holds; positive-semidefinite covariance is checked; three directional re-fits independently verify the fit-to-mean sensitivity and propagated variance. These checks verify this research arithmetic and custody, not scientific sampling truth, an installed grader or A105 adequacy. Own full post-paper authority/contract reset and latest-human-last read are recorded separately. Parent must perform its own reset and print the proposed numerical conversion before adoption or broad replication.
