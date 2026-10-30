# Genomic-overlap execution/results information

Workload438, 2026-10-27. Implemented only the assigned information module, its
tests and this packet. No prompt, TASK/STEERING renderer, scientific formula,
result host, caller or completion-accounting file was edited by this workload.

The original supplied goal attachment is the authority, with SHA-256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
Its objective and all sixteen design principles were read initially, reread
after source examination before implementation, and reread before handoff.
AGENTS.md, EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION, the permanent tool-grader
direction and relevant fixed inventory row were read. GOAL.md was not read.

## Ready ports

```python
describe_genomic_overlap_result(target, *, called_operation=None, selector=None) -> dict
genomic_overlap_result_selector_schema() -> dict
```

The second pure port was explicitly requested by root after019, for reuse in
ExecutionEpisodes.assignment_schema. It keeps only unchanged G1 definitions
reachable from Selector, handles repeated/recursive references, and supplies
its own local `$id` so references resolve when embedded under another schema.
No new selector language or schema fields were introduced.

The descriptor validates execution_target_v1, the local assignment/resource
identity, the exact native_genomic_overlap requested-job contract and its digest.
The caller still owns actual configured-resource and original receipt authority.
Supplied called operations are limited to practical.job.start/status/collect;
absence stays null. Ordered comparisons and occurrence scope use the existing
pure worker `_selector`. Native/saved mode and saved-sheet identity use the
existing accepted source rules. Neither byte availability nor execution success
is inferred from paths, declared hashes or operation names.

All fourteen top-level keys are exactly019's keys. The scientific operation stays
analyze_genomic_region_overlap; the original program is bedtools_intersect_all_pairs,
with the selected bedtools executable and declared version described separately
from the bounded retained-data calculation worker. No generic results.read is
advertised. Original/saved results both expose execution.results.status and
execution.results.collect; only original work exposes progress.observe.

The original descriptor names the actual finite capture, worker preparation,
worker output capture, input/native parser, metadata extractor, sheet builder,
calculator and projector. Saved mode identifies only the received sheet and
explicit parameters as calculation operands; it advertises no native input
acquisition, parser or fresh native status observation. Both modes retain
complete data while projecting selected comparisons, fields, occurrences and
page, and selecting only receiving-form requested public sources:

- genomic_overlap_pair_metrics
- genomic_overlap_saved_sheets
- genomic_overlap_failures

Native success, current capture completeness, scientific extent and requested
delivery remain separate; partial/unavailable/missing values are not measured
zero. Original receipt authority and current retained-byte availability remain
separate. These are library descriptions, not measured status or annotation scores.

## Source trace

Read the complete describe_execution_target and ExecutionTargetReader.describe_target,
the protein information module and tests, and the relevant complete result
selection/catalog/execute/decision-context consumer methods in ExecutionEpisodes.
Read the complete overlap worker, native capture, result projection and public
return-source modules; examined the native requested-job validators/fixed-output
compiler, G1 selector/record validators, driver entrypoint, preparation/capture
entrypoints and saved-sheet authority entrypoint. Read the newly supplied436
NativeGenomicOverlapResults class and actual original/saved/publication paths.

The final source-selection descriptor names
genomic_overlap_return_views.requested_genomic_overlap_sources, which is consumed
by GenomicOverlapResultReceipts.publication. An earlier check001 descriptor named
the existing but unused select_genomic_overlap_return_facts helper; this was
corrected before check002 without changing host behavior.

## Verification

All attempts are retained. Both ran through existing local_jobs with readonly
source snapshots, exact source/interpreter pins, logs, JUnit and lifecycle receipts.

| Attempt | Result | Meaning |
| --- | --- | --- |
| check001 | 53 passed, 2.64 s | Initial pure information checks; preceding source-selection description. |
| check002 | 53 passed, 2.53 s | Final code, including the actual consumed source-selection helper. |

These are the same 53 checks repeated after a correction, not 106 independent checks.
For both attempts, executed source, checkout source, interpreter and original-goal
pins remained unchanged. The final receipt records memory_max=21474836480,
memory_swap_max=0 and runtime_max=infinity; scratch allocation is 4294967296 bytes,
monitored with possible overshoot plus a hard per-file limit. It is not a hard
aggregate filesystem quota. Final observed scratch was 22007808 bytes.

Coverage includes original/saved descriptions for pair/set/occurrence projections;
all operation identities and exact catalog; configured local identity; malformed
targets and wrong resources; request/digest/output mismatches; selector comparison
order, occurrence scope, parameters, saved format and source identity; detached
outputs; embedded schema equivalence and absence of unreachable definitions; and
actual callable implementation names. Guarded checks prohibit file access, Store
operations, native observations, processes, network, parsers and calculations while
the information ports run.

Concrete synthetic information example: configured-local-438, original scientific
mode unstranded_outer_span, fixed 26 native output declarations, selected comparisons
comparison_0/comparison_2, minimum_overlap_bp=4, minimum_a_fraction=0/1,
minimum_b_fraction=1/3, requested unfiltered.jaccard_bp with offset 1/limit 2.
The saved description preserves that selection and identifies an explicit
genomic_region_overlap_sheet_v1 operand; it offers only status/collect and no
fresh bedtools work. No numerical Jaccard measurement is claimed by this example.

## Remaining verification boundary

This packet verifies pure descriptions and callable identities using synthetic
supplied records. It runs no native bedtools analysis, result calculation,
scientific-byte acquisition or complete Workflow. Root owns both caller bindings,
the complete native/saved results communication tests, and any fixed-row completion
decision. A passing information test does not establish those integrated capabilities.
