# Axis wave A104: what stops or limits the grading route (19 November 2026)

Scope: the A104 grading of `LOST_CONTENT_a104.md` (head sheets, literature assay grading) and item 6 of
`IMPORT_FIX_NOTES.md` for A104. What was built is listed in the wave's report.

## 1. A native phylogeny cannot enter an Episode's custody outside the HPC chain (blocks head tool units on real data)

The four A104 measurement tools (`phylogeny_measure_placement`, `phylogeny_compare_histories`,
`phylogeny_clade_functions`, `phylogeny_compare_placements`) and `phylogeny_inspect` read a native phylogeny through
`hpc.native_body(store, ref)`: a `native.a104.phylogeny` source with its `a104_native_results` work-table row, the
`a104_native_requests` row of its request and the `episode.hpc_result` receipt it was imported from. The only writer
of those rows is `hpc.import_result(store, request_ref=..., hpc_result_ref=..., known_record_refs=..., scope=...,
ledger=...)`, which needs the owner HPC ledger's `owner` and `plan` rows (`HpcLedger.existing(store, ledger)`) and
an `episode.hpc_result` receipt. Those are written by the HPC chain (`hpc_work_planning` and its sister), whose
units stop at the job services that do not exist yet:

- `hpc_work_planning/task.py`: `ctx.services['estimate_table'].policy()` and
  `ctx.services['estimate_table'].record(**measurement, key=ctx.operation_key)` (raise
  `NotImplementedError('BLOCKED-ON-JOB-SERVICE: estimate_table ...')`), the job ledger handoff record
  (`handoff_target`), and in `messages/msg_to_child.py` the ledger records the prediction sister reads
  (`ledger_refs`).
- `hpc_allocation_execution/task.py`: `ctx.services['hpc_ledger'].open(owner_episode_id, scope, commission)` (no
  service implements it; the parent now passes `ledger` and `ledger_refs`, so the call wanted is
  `HpcLedger.existing(ctx.store, episode['ledger'])` once the sister is carried onto the custody ledger, which uses
  methods the new ledger does not have: `save_action`, `once`, `cached`).

So no test can hold a real native phylogeny, the measurement units run only their refusal paths
(`root/a104/evolutionary_history_evidence/tests/test_a104_grading.py`), and the sheet builders are exercised on the
retained native fixture of PBS job 9040517 only where they need no Store. The real-model run of the head was not
made: with nothing to measure, its only productive routes are the HPC child (blocked as above) and reasoning.

The retained fixture (`grading/evolutionary_history_evidence/tests/fixtures/a104/real/mj0044/native-pbs-9040517.json`)
is the native body itself, without its request, receipt or ledger, and its README says it "cannot establish
native-execution custody by itself". Wanted: either the HPC job services (stage 1b) so that a test can run the chain
against a recorded receipt, or a system operation that admits a recorded native result into a test Store under
custody.

## 2. The head does not commission the literature subtree (characterized clade stays uncharacterized)

The clade characterization (`grading/evolutionary_history_evidence/characterization.py`) reads held A105
assay-grading sheets. The head's old `allowed_child_roles` offered only its own kind and `hpc`, so the `literature`
slot is declared and not offered; held A105 sheets reach the head only when its parent passes them. The literature
leaves now return `sheet_record_refs` (every record a receiver needs to read the sheet again), so the route works when
offered. Not changed: offering the slot is an owner decision (`INVESTIGATION_FINDING_FEATURES_a104.md` 0.7, 9.2).

## 3. The parent's real-model run graded the source itself

`source_evidence_examination/tests/test_model_run.py` ran the parent with its three children registered. In the two
runs the model read the page and committed the graded reasoning itself (credit 1.0, the completion target, then the
yield controller stopped it); it did not select the passage child. The commission path from parent to leaf is the
system's and the leaf's own real-model run grades and returns its controlled finding; the parent's choice is the
model's. Nothing in the system is missing for it.

## 4. Library leftovers on other routes (not changed)

- `jobs/hpc/evolutionary_history_evidence/hpc.py` `sequence()` imports the deleted
  `records.documents.evolutionary_history_evidence.materials_packing` for a `read_subject` operand (the request
  preparation route, not grading).
- `hpc_allocation_execution/task.py` still names `ledger.path` in one provenance list (`str(ledger.path)`,
  discovery); the sister's ledger is the undeclared service of item 1.
