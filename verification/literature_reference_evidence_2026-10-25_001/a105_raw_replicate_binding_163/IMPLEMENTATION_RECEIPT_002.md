# A105 raw-rate replicate binding: implementation receipt

This records a finite integration of existing measurement readers/calculators.
It is implementation evidence, not a replacement goal, adopted A105 reliability
formula, assay count, scientific adequacy claim or completed W04/W05 claim.
No primary paper, retained paper packet or real provider/model history was read.
All source measurements and model/provider choices exercised here are synthetic.

## Changed scope

New `literature_rate_replicate_storage.py` supplies selected execution, closed
sheet/projection definitions, persistence and custody. New
`literature_rate_replicate_prompt.py` supplies the proposed scientific TASK text
printed by the root agent before insertion, and pure scientific return rendering.
Surgical wiring is in `literature_episodes.py`, `episode_services.py`,
`literature_experimental_prompt.py` and `communication.py`. Dedicated checks are
in `tests/test_literature_rate_replicate_binding_163.py`.

The original raw input/calculator modules remain byte-identical. The reference
parent prompt remains byte-identical: its own detailed TASK is retained and the
raw child's scientific TASK is not inserted into it. Source results enter its
STEERING through the common admitted-return renderer.

`communication.py` also acquired concurrent ATAC changes outside this workload.
Those were preserved. `communication_owned_registration.diff` records only this
workload's exact-schema registration. `scoped.diff` excludes the concurrent
changes; `final_manifest_002.json` records current whole-file hashes without
claiming the correctness of unrelated code.

## Selected interface and sheet

`literature.rate.replicates.populate` is available under existing explicit
`rate_population=True`. Its closed arguments select a received source, original
or text representation, CSV/TSV delimiter, declared table kind, exact subject and
experiment, reference/test arm-condition-endpoint-normalization groups, unit
model and across-group dependence. Scientific measured numbers are read from
the actual selected source bytes, never supplied as operation arguments or
fabricated summary rows. This finite mapping is not universal publisher parsing.

The reader preserves actual physical measurement and sampling-unit identities,
native values/limits/missingness, canonical rate units, origins and literal row
custody. The existing calculator averages available repeated readings within a
unit, then weights complete unit means equally. Its raw rows, per-unit partial
summaries, group summaries and contrast are retained together in the versioned
`literature_rate_replicate_record_v1` payload.

| Requested component | Input and calculation | Evaluated quantity |
| --- | --- | --- |
| reference_rate, test_rate | Sum of selected sampling-unit means / actual unit count | Group mean for the selected subject, endpoint and normalization |
| reference_sample_sd, test_sample_sd | Sample SD of the selected unit means, denominator n-1 | Descriptive between-unit variability; not mean uncertainty |
| reference_mean_se, test_mean_se | Saved group sample SD / sqrt(actual unit count), only under selected IID-unit model | Conditional estimated uncertainty of that group mean |
| rate_difference | Reference mean minus test mean | Signed difference on the selected compatible endpoint |
| retained_fraction | Test mean / reference mean | Relative selected endpoint magnitude with actual reference denominator |
| fractional_decrease | 1 - test mean / reference mean | Dependent representation of the same relative comparison |
| paired_sample_sd | Sample SD of matched reference-unit mean minus test-unit mean | Descriptive variability of paired differences |
| difference_se | Paired difference SD / sqrt(pair count), or sqrt(reference mean SE squared + test mean SE squared) for selected independent groups | Conditional uncertainty of the difference under the selected design |

These components are copied from the existing calculator/summary. No extra
reliability/category/index/probability calculation was introduced. They do not
establish assay specificity, attribution, false-positive rates or final
annotation credit. Dependent views are not summed as independent evidence.
Missing/censored/incompatible inputs and unknown design remain explicit nulls
with reasons. Grouping does not establish independent biological preparations.

## Complete decision/information trace

1. **Ownership and information before choice.** The existing parent defines the
   scientific job, scope, allowed return and requested component list. The child
   receives its complete recurring scientific TASK and assignment on every
   iteration, lookup and restoration. No child order, new episode type, private
   loop, additional model call, gate, timer or controller rule is introduced.
2. **Selection and source custody.** A child selects the ordinary new operation.
   Existing LiteratureEpisodes schema validation, source ancestry and scope
   checks run. The adapter separately requires actual receipt of the selected
   source. Only its selected UTF-8 representation supplies measurement bytes.
3. **Actual completed work.** The unchanged reader and calculator populate the
   actual raw sheet. Selection, scope, requested projection, original input
   artifact, source ancestry, full closed sheet and original outcome are saved
   atomically under the exact run/episode/operation identity. Reusing a key for
   different work is rejected; idempotent replay returns the saved outcome.
4. **Source meanings.** Observed subject and experiment require actual rows.
   Each group separately contains its requested selector, observed status and
   observed metadata or null. Missing groups and empty tables never turn
   arbitrary selected labels into measured source facts. Projection strings are
   bound to this exact saved table/selection and never relabeled using global
   target or reference metadata.
5. **Typed return and possession.** The exact registered closed
   `literature_rate_replicate_cells` view carries only components requested by
   `requested_rate_replicate_components` (default empty), actual source meanings,
   per-group/within-unit counts and sampling bases, measurement identities,
   missing/censor/conflict limitations, explicit unit model and pairing. Numeric
   raw operands and unrequested summaries are not expanded. Values and the exact
   available requested subset are checked against saved cells. The ordinary
   typed child/parent boundary admits the actual subset; receivers can forward
   only their admitted cells, even when they know the whole sheet reference.
6. **Presentation.** Child TASK contains the complete scientific repetition,
   missingness and conditional-uncertainty instructions. Parent TASK stays its
   own. Concise numerical/source-meaning tables enter STEERING, grouped by actual
   sheet identity so different subjects/endpoints/units/models retain their own
   qualifications. Host identities and full sheets are not rendered as steering.
7. **Reconstruction.** Factory descriptors include the new adapter/prompt and
   existing raw reader/calculator through normal implementation hashing. Current
   descriptors reconstruct; mismatched descriptors reject. Saved reads validate
   closed structures, original source/request/payload identities, source text
   digest, row/group/unit relationships, sampling bases and exact pairing. They
   do not parse saved source text, reread scientific artifacts, reinterpret
   source meaning, recalculate statistics or rewrite state. Both trusted manual
   receipt and original actual runtime-admission paths were checked with source
   acquisition, parser, summarizer and contrast calculator blocked before the
   factory and SQLite `query_only=ON`.
8. **Credit and continuation.** The adapter adds no controller observations.
   One selected population completes one ordinary own action. The controlled
   source-only child/parent check has one child population, one parent commission
   completion and one actual nonempty source-anchored parent reasoning action:
   exactly three observations. Internal parsing/statistics/reporting add none.
   Synthetic finding-progress credit remains zero. Annotation accounts,
   hypervolume, W05/final credit and configured continuation were not changed.

## Executed focused checks

The principal focused command was:

```text
.venv/bin/python -m pytest -q tests/test_literature_rate_replicate_binding_163.py tests/test_literature_rate_replicates.py tests/test_literature_rate_episode_integration.py::test_binding_validates_saved_values_and_forwarding_copies_only_admitted_subset tests/test_literature_rate_episode_integration.py::test_saved_descriptor_reconstructs_original_opt_in_and_replay_avoids_refit tests/test_literature_completion_time_integration.py::test_mixed_completion_time_and_existing_native_rate_view_keep_both_scientific_families
```

Result: **86 passed in 128.75 seconds**: 24 new synthetic binding checks, 59
unchanged raw-calculator checks and three selected legacy integration checks.
The checks cover paired/independent/unknown dependence, unbalanced technical
replication, duplicate representations, conflicting identities, missing/censored
partial work, endpoint/normalization mismatch, source ancestry, original/text
selection, source-only ordinary shared Episode execution with zero targets,
exact typed subset admission/forwarding and no-analysis read-only reconstruction.
Controlled actual provider wire checks verify full child TASK recurrence through
delta, same-decision lookup, compact operation-contract lookup and cold restore.

After a small component-selection input-type guard, the final narrow command was:

```text
.venv/bin/python -m pytest -q tests/test_literature_rate_replicate_binding_163.py::test_selected_binding_closed_arguments_and_source_custody tests/test_literature_rate_replicate_binding_163.py::test_cold_factory_and_saved_forwarding_require_no_source_or_analysis_and_no_writes tests/test_literature_rate_replicate_binding_163.py::test_controlled_shared_episode_execution_typed_parent_return_and_observation_accounting --junitxml=verification/literature_reference_evidence_2026-10-25_001/a105_raw_replicate_binding_163/final_narrow_002.xml
```

Result: **3 passed in 33.32 seconds**. This overlaps the 86 checks; it is not an
additional unique coverage count. Development fixture checks exposed a mistaken
independent-variance expected value, overly broad string checks and an invalid
empty reasoning action; those fixtures were corrected without changing the
existing statistical calculators.

`SYNTHETIC_EXAMPLE_001.json` contains an actual selected-adapter populated payload
and all 11 typed components for reference [10,20,30] and test [8,19,25], on three
paired preparations, with zero supplied targets. Its means are 20 and 52/3,
difference 8/3, retained fraction 13/15 and conditional paired-difference SE
sqrt(13)/3. This is a synthetic engineering example, not primary evidence.

## Remaining limits

No real model-backed literature investigation was run. No primary-paper example,
arbitrary publisher-table extraction, assay-specific validity/specificity reader,
experimental attribution judgment, universal sampling design inference or
annotation-credit aggregation is established by this integration. Scientific
unknowns remain distinct from those unimplemented functions. This completes the
specified missing selected/persistence/typed-return path for the existing raw
rate calculators, without an assay-count or adequacy claim.
