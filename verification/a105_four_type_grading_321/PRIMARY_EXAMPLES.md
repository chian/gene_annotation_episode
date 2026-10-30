# Original-source demonstrations of the four A105 assay types

These demonstrations reuse four retained sources and existing readers. They add no papers, assay types or paper-specific graders. The pipeline is **retained source → existing reader/calculator → one of four reusable assay-type graders → numerical A105 assessment fields**. Source identities locate measurements; `assay_type` and `quantity_kind` select the scientific assessment.

The examples preserve measured numerical results and do **not** fabricate variance, competing predictions or a known-variance normal model to obtain an overall number. Consequently, all four retain an unavailable `source_log_evidence_ratio` with explicit reasons. This is not a zero grade or a claim that the measured effect is absent. Complete numerical-model behavior is tested separately with explicitly synthetic examples in the core grader tests.

## Actual numerical results

| Reusable type and selected quantity | Retained source example | Native reader/calculator result passed to `measured_effect` | Scientific qualifications retained |
|---|---|---|---|
| Enzyme activity/rate comparisons: `activity_rate`, `rate_ratio` | *C. kluyveri* Bcd/Etf complex, TTC reduction with versus without crotonyl-CoA, Table 2 of [PMC2223550](https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/). | Substrate-omitted/full activity = **0.6/12 = 0.05**. Both source rates are µmol TTC reduced/min/mg purified complex. The existing reader also returns fractional decrease **0.95**. | Both selected TTC arms are at 25 °C. The substrate omission is the intended change; it is not a no-enzyme control and does not establish isolated enzyme attribution. Selected source rows report no spread or sampling count. A rate ratio does not require inventing a fitted kinetic model. |
| Reaction progress/endpoint conversion: `endpoint_conversion`, `conversion_difference` | Purified P205 capecitabine parent-removal screen, 24 h, author workbook `summary` row 5, linked to [PMC11741061](https://pmc.ncbi.nlm.nih.gov/articles/PMC11741061/). | Active-minus-inactive removal = **0.5892910079533679** fraction. The separate active-minus-abiotic contrast is **0.7267493538355493**. | The two contrasts share the active measurement. Original SD labels do not supply covariance or the SE of either difference. The selected path lacks the underlying normalization denominator and equality of mutant protein amount. These are parent-disappearance contrasts, not product yields or initial rates. |
| Product distribution/equilibrium: `product_distribution`, `equilibrium_fraction` | R5P/Ru5P composition in the HFP preparation, [PMC12051542](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/), Results p0060 and Figure 5. | R5P fraction = **0.603**; companion Ru5P fraction **0.397**. Selected closure deviation is **0**. | The source describes equilibrium and reverse approach from either starting compound. It also confirms contaminating *E. coli* RpiA. Composition therefore does not establish HFP-specific isomerase attribution. Closure is a dependent arithmetic description, not independent mass balance. The existing partition calculator explicitly has unimplemented uncertainty calculation. |
| Reaction coupling/stoichiometric balance: `reaction_coupling`, `stoichiometric_ratio` | T252N P450cam product formation and NADH consumption, Table 3 of [PMC2577879](https://pmc.ncbi.nlm.nih.gov/articles/PMC2577879/). | Descriptive product/cofactor ratio = **92/216 = 23/54 ≈ 0.4259259259**. | Product identity has authentic-standard chromatographic/mass-spectral support. Product formation used 10–30 min incubations; NADH consumption used a separately described steady-state experiment. The selected extraction does not establish common preparation, normalization or compatible windows. Physical productive fraction remains conditional, and ratio variance is unavailable without the joint covariance. |

The controlled experiments and identified species are evidence for their particular questions; they are not blanket proofs of validity, reliability, relevance or attribution. For each example, the test supplies only scientifically justified `supported` interpretations, explicitly `unknown` limitations, and source references. Omitted considerations remain unselected; this is distinct from proving that a paper omitted them.

## Source review and custody

The actual retained passages were reread for this task. The tests check source hashes and selected original bytes rather than trusting case summaries alone.

**Activity.** Read the original Table 2 and its footnotes, the TTC assay-method paragraph and the Results interpretation. The table specifies TTC measurements at 25 °C, their mixture, and the source-specific definition of a unit. The broader table also contains NADH and hydrogen endpoints under different temperatures and protocols; those were not merged into a coupling estimate. The test revalidates the selected table witnesses and reparses the retained mapped table with `read_rate_table`, then calls `populate_rate_table_bounds`. Source hash: `318ac6fe96b509815001892dcaa996688c703175c7dedf88b663d99fe9c90bcf`. Mapped-table hash: `9bfc3ef31cf01bc4770890644c0f45c03e69a86aa0a2307833769f81aa73441e`.

**Endpoint conversion.** Read the article's purified-protein screening method, inactive-mutant description, screening results, and product-validation paragraph. The screening used 183 micropollutants in submixtures, nominal 200 µM substrates, approximately 190 nM purified P205, S146A control and timepoints including 24 h. The later capecitabine product-verification experiment in the paper used **P131**. That product identity was not transferred to the P205 measurement. The test rereads the original workbook with `read_parent_depletion_inputs` and `populate_parent_depletion_components`. Workbook hash: `24d5734e8a8643ab20306a1725843686460761362cb85a9ef0c1e6c25304a2ae`; article hash: `1919a2a62baa2983b2bf9e9ccbde7c9631bdc2322c2951be68ecc1c798da4e1e`.

**Distribution.** Read Results p0055/p0060/p0065, Figure 5, the contamination discussion p0115 and purification/heating description p0185. The reverse-approach observation supports equilibrium interpretation. The tag/cleanup/heating changes and mass-spectrometric RpiA identification prevent the reported mixture composition from serving as isolated HFP attribution. The test uses the existing primary-source selection helper, `read_product_partition_inputs` and `populate_product_partition_components`; it adds the actual contaminant and composition witnesses already used in the retained test. Source hash: `da929d9013cedb766ca861164e5c67f35bdbca891b6e1f5826df24c3eda873db`.

**Coupling.** Read original-source packet paragraphs P4, P9, P10, P11, P12, P17 and P19, and all Table 3 rows. P10 and P12 establish distinct product/cofactor protocols; P11/P17 support product identity; P19 supports the author's endpoint comparison. The test uses the existing primary-source helper and `read_product_coupling_inputs`/`populate_product_coupling`. It selects the descriptive ratio and preserves the physical fraction's existing conditional status. Source hash: `fe5ba79bc3152f6d94f730cc7e02b43c041fbcb5092afa434386ba3c60c2e7de`.

## Mapping to the common grader

`tests/test_literature_assay_grading_primary.py` converts each selected native cell to the core's operand structure without changing its number or unit. The endpoint reader's `origin="calculated"` is normalized to the core synonym `derived`; the other native origins are preserved. Measurement ownership comes from the existing reader or from a stable identity of its retained rate row. The demonstration's support references denote checked retained source locations; this direct core test does not claim to create live Store reference records.

Only `quantities.effect` is populated. The other eight operand roles and `prediction_model` remain null. No reader-provided recovery, attribution fraction or nuisance-condition correction is silently reapplied. Every example verifies:

- The correct measured numerical effect survives into the common A105 assessment.
- `effect_variance`, `effect_precision` and `source_log_evidence_ratio` remain unavailable.
- Overall reasons include `effect_variance_not_selected`, `assertion_prediction_not_selected`, `alternative_prediction_not_selected` and `prediction_model_not_selected`.
- Relevant scientific limitations remain explicit—for example HFP attribution and P450 matched windows.
- Renaming an assertion identifier does not change the numerical cells or scientific interpretations. Case names do not dispatch the grader.

These tests exercise the actual readers, calculations and `grade_assay` core. They do not test an autonomous model's ability to discover the interpretations, and they are not a substitute for separate selected-operation storage, typed-return, replay or full numerical-model tests.

## Selected grader instructions

`literature_assay_grading_prompt.py` supplies the complete selected scientific TASK. It uses the core's `CRITERION_QUESTIONS` for common and type-specific considerations, explains all nine numerical roles, prevents repeated application of native corrections, and requires the explicit model before an overall conditional likelihood comparison. It contains no paper-specific routing instructions.

`literature_task_selection.py` registers `literature_assay_grading_cells`, its repository, requested-component field, `literature.assay_grading.populate`, the `assay_grading_population` flag and its returned evaluation scope. The full TASK is inserted for actual requests/owned work/attempts/results; seeing the operation in a catalog alone does not activate it. The existing experimental TASK now displays `requested_assay_grading_components` with the other actual assignment requests.

Validation with `/tmp/gene-annotation-literature-py314-20261029/bin/python`:

`python -m pytest -q tests/test_literature_assay_grading_primary.py tests/test_literature_assay_selection_guidance_320.py`

**26 passed.** These comprise five original-source numerical/limitation checks and 21 recurring/selected TASK checks, including both parent and child, all five selection routes, source-format limitations, identity-independent scientific selection and TASK/STEERING separation.
