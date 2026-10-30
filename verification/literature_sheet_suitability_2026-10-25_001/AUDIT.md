# Suitability audit of the ten current numerical research sheets

User steering: “check that the 10 sheets are appropriate to the task”.
The complete controlling implementation goal is preserved byte-for-byte in
`GOAL_VERBATIM.txt`. Current sheet selection follows research delivery016.
This is an additive audit; original research records and proposed policies
remain unchanged. No reader implementation or W05 completion is claimed.

## Overall finding

All ten sheets contain actual numerical components and explicit calculations.
They are suitable foundations for literature population, with two consequential
design concerns and a concrete uncertainty-interface omission to resolve before
literal implementation. A defined proposed calculation is not an adopted policy
or a calibrated probability. Unknown empirical inputs are not an implementation
defect when correctly retained as unknown.

## Findings requiring attention

1. A101's current sheet section 4 merges distinct required regions by transitive
   coordinate overlap. That prevents duplicate-coordinate counting but can also
   erase distinct biological requirements. Regions 1–100 and 100–101, with support
   on 1–100, produce 100/101 after union versus sqrt(1*.5) when treated as separate
   requirements. The latter is a comparison of meanings, not an adopted fix.
   Deduplication needs biological identity as well as coordinates. See
   `a101_complete_sheet_015/CURRENT_PROPOSED_SHEET.md:182` under the review directory.
2. A106's Q=sum(H*a)/max(1,sum(H)) can remove shared source-to-target attenuation
   through additional distinct assay designs on the same source. H=.1,a=.8 gives
   .08 for one group and .8 for ten. This is disclosed in the sheet, not an
   arithmetic error; nevertheless extra source assays do not establish a closer
   source-to-target relationship. Preserve row cells; reconsider this proposed
   aggregate before treating it as the intended transfer behavior. See
   `a106_complete_deliverable_028/A106_NUMERICAL_SHEET_028.md:218`.
3. A101's exact common Cell has no full statistical uncertainty record (kind,
   magnitude, level where applicable, sampling basis), although R4 accepts an
   uncertainty type. A103 ReportedNumber similarly cannot directly retain a
   general reported SD/SEM record. Add lossless uncertainty fields to the
   implementation contract rather than misusing identification bounds. See
   `a101_complete_sheet_015/READER_IO_UNIMPLEMENTED.md:11` and
   `a103_complete_deliverable_023/EXACT_FIELDS.md:25`.

## Per-axis assessment and limits

| Axis | Fit to the literature-population task | Essential qualification |
|---|---|---|
| A101 | Reported sequence comparisons, characterized functions and functional sites | Repair region identity/uncertainty contracts; supported native-score compilation is protein BLAST/HMMER. Identity-only evidence remains usable partial data. |
| A102 | Reported structural comparisons and relevant molecular features | RMSD/TM alone can fill bases; missing local geometry leaves dependent components unknown. New geometry calculations belong to the tool work. |
| A103 | Gene arrangements, measured cohorts and reported neighborhood scores | Verbal proximity supplies no score; positive-only examples supply no complete cohort denominator. |
| A104 | Organismal-tree agreement, fixed conserved-function clade placement and outliers | Preserve characterized coverage, mixed-function limits, shared tree samples and HGT applicability. Strict heterogeneity treatment reflects later user direction. |
| A105 | Direct activity, specificity, attribution, comparability and target correspondence | Assay-specific models/uncertainty are required for their corresponding likelihood calculations; measured partial cells survive. No perturbation substitution. |
| A106 | Perturbation/restoration arms, amount, comparability, isolation and transfer | Retain replacement/coexistence distinctions; pooling concern above. |
| A107 | Required partner sets, genomic presence and expression statistics | Worked expression branch is transcript log2(TPM+1), equal-condition, growth-adjusted Pearson. Genomic baseline .5 is not evidence that coexpression was established. Other expression measurements remain native/unsupported. |
| A108 | Specific organism/sample compatibility requirements | Capability=1 means a compatible state is witnessed; sample coverage is a different quantity. Neither is overall confidence in a function. |
| A110 | Reaction/pathway predictions, resources and conservation | Relative fit can favor the less bad of two poor models; retain absolute residuals. Presence of a gene is not measured pathway capacity. |
| A111 | Experimental structural features connected to the actual target | Finite X-ray/EM/NOE routes. Fit is not chemical identity/activity, and max pooling does not accumulate weaker corroboration. |

The native-score transformations, kernel scales, fixed weights and aggregation
conventions remain labeled proposals. They are not categorical confidence grades,
but their explicit arithmetic alone does not establish biological calibration.
Requested component subsets should remain returnable without a complete candidate
coordinate or initial candidate name.

## Inspection and verification scope

Three fresh read-only agents inspected disjoint complete current sheet/reader
contracts: A101/A102/A103; A104/A106/A107; A108/A110/A111. The coordinator inspected
delivery016, complete A105 sheet, LiteratureEpisodes and evidence-axis contracts,
and independently checked the cited A101/A103 contracts and A106/A107 equations.
A102 incorporated draft002/additive005 and the A104 correction were included in
the assigned reviews. A108 included both inherited reader contracts and the
uncertainty addendum. No primary papers or retained paper-specific packets were
reopened for this audit; published measurements were not revalidated.

`a101_region_check.json` and `a106_pooling_check.json` are executed synthetic
arithmetic checks, not biological findings, production tests, source extraction,
or model-backed literature execution. No runtime files, tool graders, annotation
formula, existing progress records or historical research deliverables changed.

## Fixed implementation checklist

All items retain their original meanings. None is completed by this audit.

- [ ] L00 — Inspect existing sheets and implementation; define coverage, interfaces and ownership. Sheet suitability audit recorded; complete runtime consumer trace and implementation handoffs remain.
- [ ] L01 — Implement shared literature extraction, validation and calculation mechanics.
- [ ] A105 — Implement and verify experimental molecular activity population.
- [ ] A101 — Implement and verify sequence-homology literature population.
- [ ] A102 — Implement and verify structural-homology literature population.
- [ ] A103 — Implement and verify genomic-neighborhood literature population.
- [ ] A104 — Implement and verify evolutionary-history literature population.
- [ ] A106 — Implement and verify perturbation/restoration population.
- [ ] A107 — Implement and verify required-partner/coexpression literature population.
- [ ] A108 — Implement and verify organism/sample-plausibility population.
- [ ] A110 — Implement and verify biochemical/pathway-consistency population.
- [ ] A111 — Implement and verify experimental-structure/correspondence population.
- [ ] L02 — Complete existing LiteratureEpisodes integration and typed returns.
- [ ] L03 — Complete cross-component verification and the explicit W05 handoff.
