# Genomic-overlap execution information

Fresh workload438, additive2026-10-27. Own only
`gene_annotation_episode/genomic_overlap_execution_information.py`,
`tests/test_genomic_overlap_execution_information.py` and packet438. Root owns
the callers in execution_progress.py and execution_episodes.py. No prompt or
TASK/STEERING renderer edits, scientific math, artifact reads or native work.

Implement this pure port:

```python
describe_genomic_overlap_result(target, *, called_operation=None, selector=None) -> dict
```

Validate the existing execution_target_v1 shape and actual configured local
native_genomic_overlap requested-job shape. Read complete current
describe_execution_target/ExecutionTargetReader.describe_target and the protein
information module to match their consumed information contract. A supplied
called_operation is the actual handoff receipt operation, one of
practical.job.start/status/collect. Null means it has not been supplied; never
invent an operation or infer it from an arbitrary filename. For saved inputs,
the caller can pass an already authenticated historical target without opening
current native files.

Return library information with these exact keys:
resource_kind, service_or_program, operation, mode, output_format,
called_operation, selected_outputs, result_selector_schema, result_selection,
status_operations, acquisition_operations, status_meanings, extractors,
return_fact_sources. Values come from the actual job, accepted428/G1 selector,
426/G2 fixed outputs and013 public sources. Keep the selector schema self-contained
when embedded; no unresolved root-local definitions. Validate selector shape,
ordered requested comparisons and occurrence scope with the existing pure
worker selector validation. Do not create a different selector language.

Original native results have exactly execution.results.status and
execution.results.collect as available results operations; monitoring progress
is the existing resource observation. Do not advertise generic byte-window
acquisition as the genomic-overlap grader. State original native format,
actual finite capture, bounded worker, parser, sheet/calculator and projection
implementations by their existing functions. Identify the actual called
scientific operation as analyze_genomic_region_overlap and actual bedtools
native execution; do not call the local calculation worker the original native
algorithm.

Saved-sheet calculation has the same two results operations but no fresh native
status probe or acquisition. Identify retained sheet plus explicit parameters
as its operands, original receipt authority as distinct from byte availability,
and bounded calculation as distinct from a new bedtools analysis. Complete
data is retained; only selected comparisons/fields/page and requested public
sources return. Missing/partial/unavailable remain distinct from measured zero.
Do not add support scores, annotation judgments, an LLM extraction step,
unrequested statistics or another episode type.

Descriptions here are deterministic operation/library information, not a new
tool-specific monitoring TASK. Existing generic resource monitoring instructions
remain unchanged. No human prompt approval is inferred from the existence of
this module.

Verify both original and saved descriptions, exact available operations and
function names, configured local identity, wrong selectors/resources, source
lists, detached outputs and self-contained embedded selector schema. No native
files, Store, process or network calls may occur. Tests use existing bounded
local_jobs20GiB/4GiB/zero swap/no wall with pinned readonly source snapshots.
Read the original user-supplied goal/AGENTS and accepted contracts; do not read
GOAL.md. Reread original objective/all16 principles after substantial source
examination and before handoff. Root owns integration and completion accounting.
