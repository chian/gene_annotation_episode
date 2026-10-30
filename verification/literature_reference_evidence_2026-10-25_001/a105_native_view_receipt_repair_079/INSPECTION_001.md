# 079 bounded native own-view repair: inspected scope

Read the full active attachment first:
`/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt`,
then the full `native_ratio_source_parent_review_071/OWN_VIEW_REPAIR_RELEASE_079_054.md`.
Read complete repository AGENTS.md, GOAL.md, docs/EPISODE_STRUCTURE.md,
docs/TIME_AWARE_ESTIMATION.md, research/experimental_scoring_review_2026-10-23/AGENTS.md
and docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md.
No paper or retained paper-specific scientific evidence was opened; no scientific
interpretation or post-paper reset is claimed.

Read the complete original native module and original native/readonly test files,
including `native_case`, `multi_source_view_case`, repository/context construction,
native forgeries, saved replay, parent delivery and fresh readonly projection.
Read the full image_evidence.py. Read complete ToolRegistry execute/execute_async,
_execute_operation_async and _save functions and the image.view dispatch branch.
Read complete DecisionSource.execute, including original selected-action save,
pending snapshot addition, recorded-outcome projection and completion staging.

Traced every receipt consumer: native populate authenticates before reading image
bytes; the pure input reader's complete schema builder, custody dependency helper,
_view_bytes and read_relative_signal_source_inputs preserve receipt identity;
validation's complete _view_binding, _validate_extraction and
validate_relative_signal_saved validate retained association/arithmetic;
native read re-authenticates the original receipt from runtime/tool records;
native project_cells reads saved sheets; inherited _sheet_owner, fact_cells,
validate_fact_values, validate_returned_values, receive_cells, received_cells,
_runtime_delivery_cells and delivery binding/digest helpers preserve owner and
admitted-subset checks. The original native and readonly regression tests exercise
these consumers. No code in those downstream consumers was changed.

The bounded frozen077 read used only declared action0's action/result, its exact
ToolRegistry operation and the metadata/request artifact needed by _own_view_receipt.
No runtime model-call, private provider, live-run, unrelated DB or paper data was
queried. The separate077 NATIVE_CUSTODY_FAILURE_001.json was read in full. The
readonly pre-fix probe reproduced the primary mismatch directly; the earlier
pytest log's later None-result fixture exception is not used as mismatch proof.

Ownership remains unchanged: the selected episode owns image.view; ToolRegistry
saves its original exact tool result; runtime adds its declared pending snapshot;
native custody compares the tool portion and hashes the full runtime result;
saved reads compare that same original full digest. The repair performs no
decisions, source acquisition, model calls, credit/observation writes or controller
changes. Constructed receipt tests explicitly assert no observations; selected
Workflow/C1/C4 proof remains077's independent responsibility.

Process-visibility qualification: a broad `ps -C python` diagnostic used to check
the engineering pytest processes also displayed unrelated live-run process
command lines. No files, databases, model/provider content or scientific facts
from those live runs were read. Those incidental command lines were not retained
or used as verification evidence. The earlier no-live-run statement above means
no deliberate live-run data access; it must not be read as zero incidental
process visibility. Root was notified of this qualification.
