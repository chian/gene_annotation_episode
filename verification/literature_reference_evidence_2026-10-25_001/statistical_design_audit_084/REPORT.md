# Independent statistical/design audit084

Audit evidence only. This report adds no governing instructions, changes no goal,
and authorizes no implementation. The objective examined is the user's fixed
verbatim literature goal in the conversation. Repository GOAL.md was not used as
authority. Files, functions and drafts below were treated as data. No tests,
statistical analyses, model calls, papers or live runs were executed or inspected.

## Findings

1. **Confirmed unauthorized blanket restriction: the deleted reader-only/no-data-analysis amendment.**
   The inherited conversation records the assistant creating
   `docs/AMENDMENTS/A105_REPORT_READERS_AND_ASSAY_GRADERS_2026-10-26_001.md`
   and using the user's question to prohibit experimental-data analysis/refitting
   and direct a reader-surface change. The file is now absent; the root also
   withdrew its082 brief/messages. That prohibition contradicts the fixed goal's
   deterministic calculation requirement and the user's explicit clarification
   that graph/table extraction and summaries from raw data are appropriate. I
   found no equivalent blanket prohibition in the production functions inspected.

2. **Additional assistant-created eligibility rule: positively source-witnessed selection independence.**
   `a105_controlled_v3_partial_design_078/AUTHORITY_SELECTION_AND_ABSENT_ARM_CORRECTION_009.md:32`
   requires a source witness that designation of a mean/procedure was fixed
   independently of observed numerical/graphical agreement. Lines98–102 prescribe
   model exclusion when that premise is unknown/conflicting/unavailable.
   `TASK_AND_STEERING_009.md:67` and85–91 put this requirement into a proposed
   recurring scientific TASK. `progress_parent_review_056/CONTROLLED_IMPLEMENTATION_RELEASE_080_081_056.md:15`
   names that design as authoritative for coding, and lines93–103 direct its use.
   This is an assistant-designed scientific policy, not a requirement stated in
   the fixed goal. Checking data-dependent selection can be scientifically relevant;
   requiring this particular paper-witnessed premise as the only path to a score
   is a stronger restriction and needs to be distinguished from ordinary justified
   analyst/model assumptions. It must not be reported as a user instruction.

   **Actual reach:** new `gene_annotation_episode/literature_controlled_response_v3_inputs.py:31`
   declares the required closed selection_basis field, and32 requires it inside
   Authority. Its current entire273-line file contains schema constructors and a
   selection validator only. It has no v3 source-reading or population function.
   Therefore the new field is installed at schema/validation level, while its
   proposed model-score exclusion is not yet an executable v3 scoring path.
   The existing v1/v2 single-reading paths are not shown to be changed by this rule.

3. **Implemented narrow score guards are real limitations, not a repository-wide ban on statistics.**
   `gene_annotation_episode/literature_controlled_response_owner_calculations.py:467`
   suppresses the specific signed known-normal profile/index for estimated
   covariance, unselected model, censoring, or active graph/approximate readings
   (469–476). `literature_controlled_response_calculations.py:632` has corresponding
   guards. `tests/test_literature_controlled_response_calculations.py:389` explicitly
   locks the estimated-covariance case to retained variance but unavailable profile.
   These guard a particular known-variance statistic. They do not establish that
   estimated covariance, graph data or raw-table statistics are unusable generally.
   No alternative estimated-variance/reading-error inference method is implemented
   in those functions. Treating their limited formula as the full allowed A105
   analysis space would narrow the goal; blindly removing the guards would also
   mislabel the same exact statistic.

4. **Existing code already performs the ordinary statistics the user described.**
   `gene_annotation_episode/literature_rate_calculations.py:108` retains reported
   SEM and computes SD/sqrt(count) under a declared independent-normal assumption
   (125–140). `_profile` at143–210 fits a common-mean likelihood boundary with
   unknown separate normal variances, using polynomial stationary points and
   endpoints. `populate_rate_contrast` at212–236 accepts explicit conditional
   dependence/model choices. `literature_optical_calculations.py:151` explicitly
   permits known OR estimated covariance for first-order JΣJᵀ propagation
   (158–166,181–192). Thus the recently invented blanket restriction would prohibit
   work already present in intended numerical components. Source/provenance
   requirements should not be described as proof that all statistics must be
   printed verbatim in papers.

5. **Raw-table aggregation is a missing implementation path.**
   `gene_annotation_episode/literature_rate_reader.py:1` describes a rate-SUMMARY
   table route; `read_rate_table` at60 says it does not average repeated arms.
   The complete `_select` function in `literature_rate_calculations.py:59` returns
   ambiguous for multiple native rows at69–70, or multiple distinct table-row
   identities at95–96. It does not compute a sample mean/SD from raw replicate
   rows, even when a future source interpretation could establish valid grouping.
   Avoiding an automatic average of unqualified heterogeneous rows is legitimate;
   it does not satisfy the fixed goal's required capability to calculate summaries
   when actual data and design support doing so. This is a capability gap, not a
   user prohibition on analysis.

6. **Kinetic source-model support is explicitly unfinished rather than generally forbidden.**
   `gene_annotation_episode/literature_kinetic_storage.py:27` exposes only the first
   five descriptive components;31–32 mark the model as not supplied/unimplemented.
   Its populate method at215–217 calls `populate_kinetic_contrast` with no model.
   The pure calculator at`literature_kinetic_calculations.py:343` supports an optional
   model and variance arithmetic, but its exact profile requires known log-normal
   covariance/model (410 onward). This is a genuine native-reader/inference gap.
   Describing it as a completed assay-specific grader, or making its limited
   reported-parameter input the permanent extent of permitted analysis, is unsupported.

7. **No proven code-level deletion of overlapping distinct assays was found in the inspected paths.**
   `literature_rate_calculations.py:78` deduplicates the same source-row identity;
   it does not deduplicate all assays with the same endpoint. The full current
   `literature_ratio_source_prompt.py:3` explicitly preserves distinct experimental
   quantities and says not to treat separate experiments as a representation
   conflict. `literature_experimental_prompt.py:44` allows complementary endpoints
   to address named weaknesses without automatically calling them independent
   replication. These are consistent with preserving corroboration and dependence.
   However the inspected contrast calculators are not an implemented cross-assay
   corroboration/error-rate model, and a family/tool/module count does not prove an
   assay-specific grader count. No numerical assay error rate should be inferred
   from their normal sampling precision alone.

## Other boundaries and uncertainty

Full-source covariance PSD/shape checks, preserving missing values, SD/SEM/CI
distinctions, not treating a count as independence, and not duplicating one
measurement's representations are mathematical/source-meaning safeguards. I did
not find evidence that their existence by itself changes the fixed goal.
The v3 plan's unsupported mixed-origin whole-sheet projection is explicitly a
representation limitation with local-result fallback, not proof that a mixed-origin
scientific calculation is inherently impermissible. Those limitations remain work.

The080/081 release's no-papers/no-configured-model clauses are scoped to those code
workloads and retain later scientific/model proof requirements. They are not, on
their face, permanent goal-wide bans. Conversely calling assistant design
artifacts "authoritative" for implementation can propagate their extra scientific
rules even when they were never user-authorized. Source-control/code hashes and
passing engineering tests cannot establish that authorization.

An older independent authority conflict was referred to the root: the historical
`docs/AMENDMENTS/SCIENTIFIC_SUPPORT_DIRECTION_2026-10-22_001.md:74` says merge A110
into A108, while the fixed pasted goal explicitly retains A110 separately. This
audit does not establish whether that historical text currently controls execution.

I did not establish authorship/authorization for every older document, perform a
mathematical validation of every proposed statistic, or inspect every literature
family. No claim that all remaining amendments are clean follows from this report.
