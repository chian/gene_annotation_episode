# Current review artifacts

This directory proposes one own-outcome-to-next-own-decision boundary for the
existing UniProt results episode. It contains no application implementation.

| Artifact | Current purpose |
| --- | --- |
| [DECISION_INFORMATION_TRACE_001.md](DECISION_INFORMATION_TRACE_001.md) | Exact source path, ownership, available/missing facts, secondary exposure paths and later integration checks |
| [INTERMEDIATE_SHAPE_002.md](INTERMEDIATE_SHAPE_002.md) | Precise internal view selected from the current exact acquisition and original report contract |
| [TASK_TEMPLATE_001.md](TASK_TEMPLATE_001.md) | Full existing recurring instruction bodies, filled-section placeholders and substantive UniProt result meanings |
| [STEERING_FIXTURES_002.md](STEERING_FIXTURES_002.md) | Clearly illustrative complete/partial text tables, with existing-input yield placeholders |
| [ARTIFACT_CHECKS_001.json](ARTIFACT_CHECKS_001.json) | Fourteen passing stdlib source/document consistency checks; no runtime or integration test claim |

The 001 intermediate and fixture drafts are retained. Correction002 makes
`requested_record_ordinal` nonnullable to match R002; unmatched accession
clauses use the existing selection failure without inventing a record. It also
requires missing original context to yield a diagnostic instead of raw fallback,
and includes both legacy label and legacy term failures in the long-name fixture.

The schema/projector contract in
`../tool_graders_uniprot_requested_returns_2026-10-28_601/CONTRACT_002.md`
remains a separate proposal. Current R002 explicitly filters the original
acquisition by `operation_key`; the own view must compare the full saved outcome.

Source inspection establishes the defect and missing consumers; it does not
establish an implemented fix. The current preview caller is `DecisionSource.next`.
UniProt results currently reaches the provider's JSON fallback, so a selected
dictionary alone would not implement the required text message. The proposed
template must be shown to the user for running feedback before code adoption,
as required by `docs/TASK_AND_STEERING.md`. This is a design-review requirement;
it adds no approval gate or reviewer to episode runtime.

No application imports/tests, native scientific calculations, API requests,
configured-model calls, HPC jobs or host database reads were run. Only this
directory was written by this task. Validated completed acquisition must still
close through the existing exact-zero controller path without an extra prompt.
