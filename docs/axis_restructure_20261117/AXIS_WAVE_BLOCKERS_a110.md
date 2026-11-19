# Axis wave A110: what stops or limits the grading route (19 November 2026)

Scope: the rows of `LOST_CONTENT_a110.md` and the leftovers of `IMPORT_FIX_NOTES.md` for A110. No system
operation was found missing on the literature grading route: the leaf and its parent ran to the end with the real
model (`yield_stop`), and resume replayed the recorded answers.

## 1. R14, R15: the per-use qualification sheets are not restored

`a110_qualification.py` (sheet `a110_received_qualification_v1`) and `a110_experimental_qualification.py` (sheet
`a110_experimental_component_use_v1`) at `97308b94c` qualify a *received native accounting result*. Their inputs do
not exist in the new paradigm yet:

- `component_axis_native_hpc.read(store, ref)` / `require(...)` and `RESULT_PROVIDER`: the reader of the native
  component result. The library's `jobs/sequence_and_context_sources/component_axis_native_hpc` is A107-only.
- `component_sequence_attribution.protein_correspondence` and `component_source_identity.catalog` (A110 copies at
  `97308b94c`, not in the library).
- the head tool that produces the result: `chemistry.request_accounting_hpc`. The head `task.py` still has
  `_not_placed('component_axis_reports.current_scoring_sheets')` and the other `_not_placed` stubs; the submission
  goes through the job services (`job_access`), which the A110 job episodes do not call yet (section 2).

The calculator (R11, R12), its input panel (R13) and the A110 index (R16) are restored and tested
(`calculations/biochemical_feasibility_evidence/chemical_accounting.py`,
`forms/biochemical_feasibility_evidence/{a110_chemical_contracts,component_axis_native_contracts}.py`,
`grading/biochemical_feasibility_evidence/contribution.py`, test
`grading/tests/test_biochemical_feasibility_chemical_accounting.py`); nothing calls them from an episode yet.
Wanted next: a head tool `chemistry_request_accounting` whose unit runs `chemical_accounting.calculate(document,
selection)` on a held panel source (or submits it through `ctx.services['job_access']` when the owner wants it on
HPC), saves the result as a work-table sheet, and then the two qualification modules carried onto that sheet.

## 2. R17, R18: the job route of A110 is still on `BLOCKED-ON-JOB-SERVICE` stubs

`execution_result_acquisition/messages/read_from_parent.py` raises for `flux_balance_result_selector_v1` (R17), and
`hpc_work_planning/task.py` `resolve_tool_request` raises `scientific_tool_library_required_for_hpc_tool_request`
(R18). Both sit among 30+ stubs of the same kind in `execution_*`, `hpc_work_planning` and
`hpc_allocation_execution` (`job_access`, `estimate_table`, the HPC monitor controller, the HPC commission sources).
`episode_runtime/job_access.py` and `estimate_table.py` exist now; rewiring these episodes onto them is the job
wave (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`), not this grading wave. R17 also needs the FBA result reader
(`root/a110/native_flux_balance_results.py` at `97308b94c`), which is not in `ES/jobs/`.

## 3. IMPORT_FIX_NOTES leftovers for A110 (done, with one choice to confirm)

- `ledger.path` is gone from both HPC tasks: the frozen plan for the launch child is an artifact the ledger names
  (`launch_input` evidence, `supplied_input_artifact_ref`, passed in the launch commission's `record_refs`), and
  `closed_measurement(..., ledger=ledger.ledger)` names the ledger by its id (A110 `hpc_history.py` as the A107 copy).
- The ledger id is passed by argument: `ledger_view` carries `ledger` and `row_refs`; `hpc_work_planning.action`
  adds `ledger` to every tool call, `msg_to_child` passes `ledger` and `ledger_row_refs` to `hpc_allocation_execution`
  (new form fields) and `ledger_refs` to `hpc_resource_prediction` (the old `NotImplementedError` there is gone).
  Choice made: the id is added by code, not declared in the model-visible tool schemas, so the model never copies an
  id it cannot get wrong otherwise.
- Mismatch left: `hpc_resource_prediction` reads its own work table `hpc_evidence`, not the `HpcLedger` rows it is
  now passed (`jobs/hpc_ledger.py` table). That belongs to the job wave.

## 4. Not exercised by a real run

- The model runs made no typed reasoning commit, so the assessment features of the finding (P1 to P13) were zero and
  the custody closure `finding_record_refs` (each retained assessment and the held records it names) was never
  passed with content. The code path is real; a run with a commit, or a test with a hand-built commit payload, is
  still to be done.
- `investigation_progress.project_finding_progress` no longer opens a Store `read_snapshot` (the reader has none);
  a unit's reads see one state.
