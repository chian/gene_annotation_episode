# A103 axis wave: what stops or limits the grading route (19 November 2026)

No missing system operation blocks the A103 grading route: the head links with the public API, is stepped with
`EpisodeRun.next_decision` / `run_unit`, grades held measurements (`context.grade`), returns the controlled finding,
and runs with the real model to a `yield_stop`. What remains open:

## 1. Rows of LOST_CONTENT_a103.md restored but not wired to an A103 tool

Rows 1-4 (BV-BRC ComparativeSystems sheet and calculator; GenomeAlignment sheet with the Mauve and XMFA
calculators) are restored from `97308b94c` into the library. No A103 tool publishes a ComparativeSystems or
GenomeAlignment result, and none did at `97308b94c` (only the unimported bundle adapters called them), so no A103
episode writes these sheets. Rows 2-4 have no running test: `97308b94c` retained no saved GenomeAlignment document or
components (only `retained_sources/mauve/testdata/small.mauve`, a native file without the parsed document the
calculators take). Row 5 (genomic overlap) likewise has no caller (`native_genomic_overlap_driver` has no result path
in A103).

## 2. HPC subtree (IMPORT_FIX_NOTES item, A103)

Done: the ledger id travels by argument (`ledger_view['ledger']`, injected by `hpc_work_planning.action` into every
tool call after `hpc_initialize`, passed to both sisters by `msg_to_child` and declared in their assignment forms);
`launch_input_path(ctx, ledger, plan_id)` and `closed_measurement(..., ledger=<id>)` no longer use `ledger.path`;
`hpc_allocation_execution` opens `HpcLedger.existing(ctx.store, arguments['ledger'])` (it imported the deleted
`HPCLedger` and could not be imported, which made the whole A103 head unlinkable).

Not done (outside the grading route; each is still a `NotImplementedError` of the job-service stage):
`hpc_resource_prediction.open_ledger` (needs `once`/`model_credit` on `HpcLedger`), the ledger rows a sister reads are
not named in a `record_refs` field of its commission (`HpcLedger.existing` selects only held rows, so a sister reads
an empty ledger until the planner passes the row references), the launch-input file write in `hpc_plan`, and the
`job_access` / `estimate_table` calls.

## 3. Real-model behaviour observed

Leaf (runs/ma103_4): after the stepped lookups and measurements the head graded them without a model decision, then
the model committed the assessment linking the recurrence sheet's context observation to the proposed annotation
(after the commit form was written into the grading instructions; before that, 35 consecutive commits were rejected
for missing assessment fields and the rejection feedback named the wrong field), then chose context.grade and
context.bind_locus; the bounded-quality controller stopped it at credit 0.5 after 14 units; resume replayed it with no
model call. Parent: the model commissioned one recursive head (selection "own"); the child stopped at credit 0 without
measuring; the parent received its credit and controlled finding only and stopped after 3 units; resume replayed it.

Library limit seen: `model_exchange.rejection_feedback` reports `relation` enum as the first issue for an assessment
that lacks `alias`, `applicability`, `extent_basis` and the ref lists (misleading feedback; not changed here).
