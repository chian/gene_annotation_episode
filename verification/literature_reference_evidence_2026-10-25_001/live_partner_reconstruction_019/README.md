# Read-only saved partner reconstruction

`audit_live_partner.py` takes a WAL-consistent SQLite backup from the explicitly
selected run using a read-only/query-only transaction, hashes/copies only named
artifacts as opaque bytes, then opens only its owned backup in a fresh pinned
subprocess. Each invocation requires a new output directory below this directory.

```sh
.venv/bin/python verification/literature_reference_evidence_2026-10-25_001/live_partner_reconstruction_019/audit_live_partner.py \
  --run /absolute/selected/run \
  --pin /absolute/selected/SOURCE_MANIFEST_pin \
  --output-directory /home/chia/repos/gene_annotation_episode/verification/literature_reference_evidence_2026-10-25_001/live_partner_reconstruction_019/NEW_OUTPUT
```

The process verifies every SOURCE_MANIFEST file and exact actual pinned imports.
It blocks source/native/scalar/defined-unit/calculation functions and loaded
aliases, population, receipt writes, model transport, host reacquisition, SQL
mutation and private model-table reads. Only saved sheet/request artifact bytes
may be read during reconstruction. All existing public table hashes are retained
and checked before/after, including the second real Store reopen. Standard Store
and repository constructors run against the owned copy before the SQL authorizer;
the original table inventory and public hashes must remain identical. No live
Store is opened. The snapshot phase is the only phase that opens the selected
run database, always through SQLite mode=ro/query_only.

Selected operations, immutable request/signature/outcome/payload identities,
source receipts, saved typed projections, original typed forms/facts/admissions,
and unique action/observation/credit identities are checked mechanically. A saved
`episode_execution` binding requires original completion slots and exact original
controller inputs; missing slots fail. Legacy direct-observation runs retain an
explicit absent/unverified slot boundary. No controller is reconstructed/refit.

For generic019 PROCESS inputs, the original pinned caller/process manifest,
SOURCE_INPUTS record bytes and JOB digest are checked. PROCESS does not contain
an original loaded-module receipt: that boundary remains explicitly unverified.
Current auditor imports are independently verified against the selected pin.
Pinned caller bytes do not prove original model scientific behavior.

Final controlled018 checks are in `controlled_nadh_004/` and `controlled_h2_002/`;
see `CONTROLLED_VALIDATION_RECEIPT.json`. Each verified one selected v3 sheet,
eight cells, one actual typed attempt/admitted subset and three original
zero-credit observations with 59 unchanged public tables. Both report absent
legacy completion slots. The first two failed nadh outputs remain as facts;
intermediate passing outputs also remain. No earlier snapshot or pin changed.

These are controlled engineering checks, not actual model science, a host restart,
a resumed run, annotation completion or a whole-run/multi-axis audit. v1/v2 use
the same pinned saved-record repository validation but were not exercised in this
workload. Other literature namespaces remain outside the verified scope. No
actual019 run has been launched, polled or audited by this workload.
