# Original-rate-grid precision: independent scientific conversion review

The225 proposal supplies a justified bounded precision section for the logical A105 sheet. It still needs production readers/calculators and selected typed integration. It supplies neither an unconditional covariance of the published kinetic parameters nor a complete A105 reliability/validity/relevance assessment. The original supplied goal remains unchanged and active.

## Own primary-source reading and reset

Root read the complete1413-line original article text, complete130-line S5 visible table, complete1103-line source packet, report, both numerical outputs, both calculation scripts and proposed IO/TASK. After that combined one-paper packet, root reread the complete immutable goal and all applicable researchAGENTS authority documents, relevant current observation/replicate and common numerical contracts, and the proposed contract. Latest actual human instructions were read last. The initial truncated recovery-document read was repaired with complete sequential portions. POST_PACKET_RESET_001.json records the actual reads and hashes; no other agent's reset is substituted.

The source is Yang etal.2023, DOI10.1371/journal.pbio.3002285. Selected S1Data.xlsx data are the WT BbPK–DHA S17 block: Q193:Q205 concentrations, R193:T205 rates, panel A189, rate header B190, subject Q191 and data-column labels R192:T192. The individual study molecule remains distinct from coexisting AckA, hexokinase and glucose-6-phosphate dehydrogenase coupling enzymes. This selected block contains no wild-type/mutant coexistence comparison. Protein preparation/tag boundaries, active fraction and physical reporting-column identities remain unresolved.

The source's NADH-consumption workbook header conflicts with the applicable Methods' NADPH-production description. The two described assay formulations also differ in volume, PK concentration and helper amounts. Caption/context can support the stated concentration scale while leaving protocol mapping unresolved. The reader must preserve those qualifications; matching nominal protein mass does not establish identical assay context or molecular normalization.

## Independent original-data and calculation checks

`independent_oracles_001.py` reads the original XLSX ZIP/XML directly. It verifies original source hashes; all39 rate cells,13 concentration cells and six headers against their retained exact numeric/shared-string and XML-span witnesses; all four workbook-member hashes; and all six article-method/caption witness byte spans. It independently verifies the thirteen exact rational point means and sample variances.

The numerical oracle uses65-digit Decimal Newton fitting with analytical profiled-amplitude derivative. This is separate implementation from the research golden-section and binary64 stationarity solvers. It independently fits each source reporting column and the point means. It then calculates sensitivities with13 independent central finite-difference perturbations of observed means, rather than copying the research implicit-Hessian formula. The full cross-concentration reported-curve covariance propagates through that independently estimated sensitivity.

Results agree with225:

| Numerical component | Independently checked value |
| --- | ---: |
| Descriptive CV at10mM | .03488479237 |
| Descriptive CV at100mM | .18961065720 |
| Mean of three fitted Km values |36.495494725mM |
| Km fitted to point means |35.875991494mM |
| Conditional variance of log(Vmax/Km), mean of fitted parameter vectors |.003902974090 |
| Conditional variance of log(Vmax/Km), fit to point means |.003392732339 |

Both estimator covariances require an explicitly stipulated IID reporting-curve-vector model that the source does not establish. Descriptive variation among three labelled columns remains usable without pretending that those columns identify biological preparations. Neither matrix can be attached to the published S5 point estimates. Vmax retains its native amount-rate units and is not kcat.

For the mean-of-parameter-vectors scenario, signed propagation combines actual terms through Cvv/V²+Ckk/K²−2Cvk/(V*K). The reported approximate terms .004545335+.010295109−.010937469=.003902974 agree with the independent result. The covariance term cannot be discarded as an independence default. For the fit-to-means scenario, the separately checked matrix is approximately[[1.47461156e-7,.00123955899],[.00123955899,14.34185564]], with Vmax/Km row/column units. Distinct estimator identity is therefore a necessary field, not bookkeeping decoration.

The39-value residual sum of squares also satisfies the independently checked identity total=within-concentration spread+3*mean-curve model residual:5.806547846e-6=4.305537933e-6+1.501009913e-6. That decomposition does not establish a noise distribution, significance test or scientific acceptance threshold.

All these are original-measurement-derived research calculations, with conditional model assumptions marked separately. No synthetic measurements, extra scientific observations, new complex computational-biology software, model call or production grader was introduced.

## Additional source-report arithmetic discrepancy

Root independently reconstructed the original DOCX table cells and retained the exact XML-member hash and row byte span. The WT BbPK/DHA row reports kcat=.17s^-1,Km=35.88mM and efficiency3.80s^-1M^-1. The first two source values imply4250/897=4.73801561s^-1M^-1. Under a separately labelled nearest-last-digit rounding illustration, the reconstructed range4.5980–4.8780 does not overlap3.795–3.805. This is a same-row numerical reporting inconsistency with unknown cause, not a disagreement between independent experiments or measured uncertainty. Source values remain unchanged; reported and reconstructed quantities must remain separate. ROOT_REPORTED_PARAMETER_CONSISTENCY_001.json retains the evidence.

## Paired extraction and numerical-sheet revision

The existing original-XLSX observation reader supports contiguous row labels under group headers in a selected subject column. This transposed grid requires an explicit versioned layout: selected concentration rows, reporting columns/labels, panel/subject/header witnesses, endpoint/unit interpretation and nullable physical grouping. Silently transposing and relabelling it as the old physical-unit CSV or old observation layout would change its meaning.

The numerical section needs point descriptive means/variance/SD/CV, selected per-column parameter fits, distinct mean-of-parameter versus fit-to-means estimates, model/weighting/estimator identities, source-entry dependencies, descriptive parameter covariance, optional explicitly conditional estimator covariance, and the signed propagated precision of the selected derived quantity. Actual displayed zero, absence, censoring, formula-cached data and incomplete rosters need distinct behavior. Fitting failures preserve native/available-point partials rather than inventing values or misclassifying implementation failures as missing source facts.

The common compiled reader currently has no Vmax role or grid-derived estimate input and no matching low-efficiency contrast-uncertainty conversion. Its existing covariance type cannot simply accept this matrix while losing estimator or statistical scope. That required conversion remains unfinished. The S5 self-arithmetic discrepancy is also retained research evidence; this bounded grid workload does not silently create a general same-estimand contradiction grader.

Precision informs one part of evidence assessment. Chemical product identity, blank correction, matrix/coupling recovery and molecular attribution still require their own applicable evidence. The paper's separate HPLC/no-PK and GC-MS results address complementary weaknesses, but figure count does not establish independent preparations or calibrate the selected rate-grid covariance.

## Conversation and implementation handoff

Root printed the concrete numerical section and signed combination above in chat, explained the two estimator scopes and endpoint/source limitations, and printed the complete five-paragraph scientific TASK verbatim. The TASK is separate from the numerical sheet. No new universal probability, grade ladder, arbitrary weight or goal policy was adopted.

Fresh228 is commissioned read-only to propose exact closed pure interfaces and implementation ownership. Prospective ownership is only the existing observation input/calculation modules, a new test and its own verification artifacts; no code is released yet. It must preserve existing v1 behavior, use an explicit new grid version, preserve source/estimator/dependence meanings, and plan later selection under the existing observation operation.223 owns the concurrent common integration path. Fingerprint dependencies and frozen-cohort preservation must be coordinated before228 writes production code.

This progresses the fixed overall goal through actual source-grounded numerical components. Full common integration, broader validity/reliability/relevance/contradiction compilation, appropriate assay coverage and A105 adequacy remain required. Later literature responsibilities remain in scope after A105 is adequate.
