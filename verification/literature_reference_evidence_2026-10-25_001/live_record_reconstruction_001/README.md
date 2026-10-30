# Live saved-result reconstruction verification

This owned verification workload copies a consistent read-only SQLite snapshot,
copies only the immutable artifacts registered by that snapshot, then opens the
owned copy in a fresh process with the unchanged pinned actual Store/repository.
It never resumes the run, executes a selected scientific action, admits a report,
or calls `receive_cells`. It neither interprets original sources nor opens any
provider event files. Raw scientific artifacts are opaque during copy/hash checks.

From the repository root:

```bash
.venv/bin/python -B verification/literature_reference_evidence_2026-10-25_001/live_record_reconstruction_001/audit_live_reconstruction.py \
  --run verification/literature_reference_evidence_2026-10-25_001/live_yeag_004 \
  --pin verification/literature_reference_evidence_2026-10-25_001/live_pin_004 \
  --output-directory verification/literature_reference_evidence_2026-10-25_001/live_record_reconstruction_001/NEW_SNAPSHOT_DIRECTORY
```

The output directory must be new and beneath this owned directory. Each output
contains `snapshot_manifest.json`, `receipt.json`, `REPORT.md`, process stdout /
stderr, and the owned `state/` snapshot. Exit zero means the available saved-record
checks pass; `passed_with_pending_boundaries` explicitly retains missing actual
delivery/closure proof. Consult the receipt, not only the process exit code.

The SQLite backup necessarily contains database pages for all tables. The audit
does not query `runtime_model_calls` or `runtime_decision_exchanges` contents;
its SQL authorizer rejects those reads during projection. No provider directory
is copied. The real Store and repository constructors run only on the owned copy;
projection is subsequently SQL query-only. Reacquisition, population, parser,
calculator, model and delivery entrypoints are disabled; network and subprocess
launch are blocked in that audit process. Saved numerical cells and metadata
are validated structurally against their original selected operation, immutable
request/payload, typed schema, and actual receipt membership.

Inspected production paths were the complete pinned `state.py`, complete rate,
quantity, assay and ratio repositories, complete `literature_episodes.py`,
`episode_bindings.py`, `episode_receipts.py`, `episode_return_records.py`,
`episode_journal.py`, `episode_reports.py`, and `communication.py`; relevant
repository/reference methods in `episode_services.py`; and the runtime paths for
own execution, completion/observation, receipt admission, selected-child report
admission/redelivery, frozen facts and closure. Runtime method ranges inspected:
392–491, 1337–1420, 1741–1885, 2099–2194, 3129–3556. CompletionLedger staging /
slot / confirmation and source-restore paths were inspected for observation
accounting. Model implementation entrypoint names were inspected as code only.

Actual configured-model delivery branches absent in a snapshot are pending.
Diagnostic projection establishes saved-result reuse, not a new delivery. A fresh
offline process and a second real Store close/reopen establish repository reopen;
they do not establish a physical host restart or full workflow resume.
