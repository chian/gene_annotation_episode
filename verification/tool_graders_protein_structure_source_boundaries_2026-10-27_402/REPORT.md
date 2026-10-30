# Protein source receipt and generic resolver exclusions

The assigned three guards are implemented and verified. This is a source-family
classification/denial increment, not production protein-host integration.
Completion accounting remains **112/308**; no inventory row was edited.

The controlling objective is the immutable attachment
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
SHA-256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
AGENTS.md, EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION, TOOL_KNOWLEDGE, both
practical-execution direction records, the grader principles, and the existing
compare_protein_structures inventory row were read. The complete immutable goal,
including all sixteen principles, was reread before handoff, followed by the
applicable source contract and approved guard rows in
[394/PROPOSED_BOUNDARY_001.md](../tool_graders_protein_structure_operand_boundary_2026-10-27_394/PROPOSED_BOUNDARY_001.md)
and [394/ROOT_APPROVAL_AND_TYPED_ANCESTRY_002.md](../tool_graders_protein_structure_operand_boundary_2026-10-27_394/ROOT_APPROVAL_AND_TYPED_ANCESTRY_002.md).
No GOAL.md was created.

Exactly three production lines add `native_protein_structure_bundle_v1`:

| File and line in the executed snapshot | Behavior |
| --- | --- |
| gene_annotation_episode/episode_receipts.py:199 | A source receipt alone stops before traversing its bundle and auxiliaries. Explicit artifact references remain in the normal pending receipt list. |
| gene_annotation_episode/execution_episodes.py:1178 | `_received` excludes this specialized native family before generic `_read_result`. |
| gene_annotation_episode/execution_episodes.py:1901 | `resolve` denies this family at its final generic execution-result fallback before generic `_read_result`. |

The exact before/after production diff is [source_changes.diff](source_changes.diff).
Original files are retained under `baseline/gene_annotation_episode/`.

Read-path inspection included complete EpisodeReceipts bind/manifest/selection/
receive behavior; ExecutionEpisodes initialization, `_selection`, `_received`,
`resolve`, `_read_result` and its publication/validation/selected-action/selector
path; received-form reference admission; result facts, credit and completion
consumers; runtime receipt admission and resolver consumers; and
WorkflowServices.reference_in_context. Their production code outside the three
listed lines was not edited. In particular, generic Workflow fallback and the
earlier specialized received-authority hook remain separate root integration
responsibilities. A False from this final ExecutionEpisodes fallback is not a
claim that every enclosing Workflow resolver now denies protein material.

One bounded attempt ran: [check001/stdout.txt](check001/stdout.txt),
[check001/stderr.txt](check001/stderr.txt), [check001/junit.xml](check001/junit.xml),
[check001/selected_request.json](check001/selected_request.json), and
[check001/receipt.json](check001/receipt.json). **26 passed in 54.20 seconds**,
zero failures/errors/skips; stderr is empty. All executed project and test
files came from the read-only `check001/source_snapshot/`, with **2,115 exact
file pins** unchanged after execution and zero checkout drift. No failed
attempt occurred in this packet; its harness preserves every attempt directory
and refuses to overwrite one.

| Actually executed cases | Count | Evidence and limits |
| --- | ---: | --- |
| New source-only protein receipts across initial, decision_input, own_action, child_form and report_redelivery | 5 | Real Store and Journal; no bundle/auxiliary receipt expansion; frozen child/grandchild inheritance; later child receives the explicit later artifact; replay and reopen retain exact receipt rows. No runtime action or observation is manufactured. |
| New explicit artifact in either same-delivery order | 2 | The selected artifact is received; bundle and other auxiliary remain absent. No descriptor authentication is claimed. |
| New unrelated provider/version receipt controls | 2 | Existing recursive receipt behavior remains unchanged. |
| New preexisting native receipt-family controls | 4 | Infernal preparation, HMMER preparation, BLAST database and RNA structure keep their prior exclusions. |
| New actual ExecutionEpisodes `_received` and `resolve` cases | 9 | Eight prior native families plus protein structure; `_read_result` and artifact-byte reads fail the test if entered. All four namespaces None/source/execution_result/artifact are denied by the final fallback. |
| New identical version with unrelated provider | 1 | Remains an ordinary source, using the actual resolver. |
| Existing test_episode_receipts inheritance/reopen case | 1 | `test_inheritance_freezes_prefix_without_copying_receipts_and_survives_reopen`. |
| Existing test_execution_episodes_family generic-result cases | 2 | `test_results_actual_bounded_windows_exact_replay_completion_and_unchanged_launch` and `test_result_selector_rejects_escape_and_altered_window_before_read`. These execute tiny real local file-writing jobs and the actual generic result acquisition/read/replay/resolver path. They do not execute a protein tool. |

The enclosing local_jobs policy was exactly 20 GiB RAM, 4 GiB scratch, zero
swap and no wall-time limit. The native receipt verifies memory_max=21474836480,
memory_swap_max=0 and runtime_max=infinity. Observed scratch was 56,274,944 bytes;
service-wall duration was 54.81105423 seconds. Scratch uses the existing monitored
allocated-byte enforcement, with possible overshoot and a hard per-file limit;
this is not a filesystem sandbox. The existing two local-job regression fixtures
retain their smaller original inner limits (128 MiB RAM, 8 MiB scratch, no wall
limit); the outer verification policy remains the requested 20 GiB/4 GiB.

The eight historical test_episode_receipts failures were **not rerun**. The
retained [360/check014/stdout.txt](../tool_graders_rna_structure_integration_2026-10-26_360/check014/stdout.txt)
was inspected: it reports 8 failed, 7 deselected, with scripted-provider
StopIteration/RuntimeError failures in the two runtime-credit cases, workbook
case, two selected-state-read cases, different-parent-scalar case and two
failed-form-repair cases. This packet neither repairs nor recategorizes them as
new regressions. No tests/test_execution_episodes.py exists; the actual generic
consumer file used here is tests/test_execution_episodes_family.py.

| Executed source | SHA-256 |
| --- | --- |
| gene_annotation_episode/episode_receipts.py | `523e29fc44d9ecbe074e57d650425dd8ac90311d96de280a3411e205427caeba` |
| gene_annotation_episode/execution_episodes.py | `616199a64000c10813cd9a482161ad3eda1119659baae67999d8a70462bff6cb` |
| tests/test_protein_structure_source_boundaries.py | `638e66ed5aa0965512b36fc01da0fcbd89f33cc13191c3cc8fac4100268dd6df` |
| This packet's run_bounded.py | `f74ec1477934460f45b716d37b0a53afded6ac92885a4e12fe7bb12edf34f796` |

Full before/after executed pins and post-run checkout pins are retained in
check001. The source helper supplies intentionally synthetic non-native bundle
bytes. No protein parser, scoring sheet, calculator, descriptor authorization,
protein host publication, protein native execution, live service, HPC execution,
model prompt, controller change or complete protein episode communication was
implemented or claimed by these tests.
