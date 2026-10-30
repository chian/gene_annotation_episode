# Alignment preflight implementation, workload 401

Authority is the immutable attachment
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
SHA-256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The full attachment was read first. The objective and all sixteen principles
were reread verbatim after implementation-path examination, followed by the
exact 380/015 contract and the relevant approved 394/001–002 port requirements.
AGENTS.md and the episode, time-estimation, practical-execution, tool-knowledge
and tool-grader directions were read. No prompt or scoring-sheet change is made.

Owned production changes are only `episode_services.py`, the `EpisodeServices`
protocol declaration in `episode_bindings.py`, and
`scientific_process_episodes.py`. The new test file is
`tests/test_protein_structure_alignment_preflight.py`; this packet owns all
verification output. No inventory or completion row is changed. The original
112/308 accounting remains root-owned; the protein capability is not accepted
by this seam alone.

## Complete relevant path inspected

- `ScientificProcessEpisodes` construction, original-context/selection
  validation, exact selected catalog/schema, complete `execute`, return/credit
  consumers and implementation binding identity.
- `WorkflowServices` real tool catalog/dispatch and contextual reference ports;
  `BindingContext`, `EpisodeServices`, and actual registry role lookup.
- The 398 immutable ancestry classifier and complete original sequence
  authentication path, including binding validation, received descriptors,
  exact use, source/reference identity, native/map/sequence/file validation.
- The 397 received sequence public ports and current context authentication;
  no replacement authority algorithm is added here.
- `ToolRegistry.execute_async`, `_execute_operation_async`, `_save`,
  `_prepare_sequence_work_async`, `_alignment_arguments`, `_estimate_native`,
  `_prepare_alignment_async`, `_sequence`, `_record_native_execution`, and
  `_align_one` publication.
- Runtime `Workflow.execute` dispatch/forecast projection and
  `DecisionSource.execute` recorded result, received outcome, credit and
  `ActionFailure` handling. An invalid outcome preserves its audit result and
  does not become a completed own action.
- Existing mother/service, ordinary alignment/timing, native structure operands
  and child-return tests; existing `local_jobs` and immutable-run launcher.

## Ownership and effects

The scientific child selects the original `sequence.align` arguments or the
same nested arguments in `execution.estimate`. Its exact schema validation
precedes the new service call inside the existing invalid-feedback block.
The service requires the current workflow run, independently classifies query
and reference using 398, and returns null for a truly ordinary operand. For a
protected operand it resolves exactly role `results` from the current binding
registry and passes that owner's `native_protein_structure_returns` to 398.
Missing owner/returns gives the existing `sequence_not_received` issue.
Foreign workflow context gives `original_commission_mismatch` at
authority/receipt. Existing structured operand failures propagate unchanged.

The service adds no source/known-reference permission, persistent cache, receipt,
artifact read, dispatch, projection or observation. The operand adapter alone
performs its already specified retained-byte validation after authority. Its
detached unchanged descriptor must authorize `sequence_align`.

Successful arguments, scope and operation key reach the unchanged dispatch.
Rejected selections reach none of `execute_tool`, native preparation/sequence
read, statistics recovery, native measurement or forecast projection. Runtime's
existing invalid-action handling records the failure without completion credit
or a controller observation. No controller, algorithm, schema, root capability,
resource factory or numerical policy changes.

## Verification qualifications

The new checks use real `WorkflowServices`, constructed scientific children,
real immutable Store ancestry, and real retained native extraction output.
`ReceivedAuthorityFixture` is an explicitly injected authority port, registered
on `ResultsOwnerFixture`; it asserts no real extraction-result receipt or frozen
typed report delivery. Selected stale/absent-receipt failures are supplied by
that port to test precise propagation. The full authority path remains root's
extraction -> original result -> actual typed receipt -> new child -> alignment
verification responsibility.

All pytest and native/scientific work run through existing `local_jobs`, at
20 GiB RAM, 4 GiB scratch, zero swap and no wall-time limit. Every attempt keeps
its exact selected request, immutable executed snapshot, before/after hashes,
loaded-module paths, stdout/stderr, lifecycle receipt and live-source drift.
Executed results and any fixture corrections will be recorded additively in
the final verification/handoff records.
