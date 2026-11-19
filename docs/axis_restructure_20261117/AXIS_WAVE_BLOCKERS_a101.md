# A101 axis wave: what blocks (19 November 2026)

## 1. The parent model run (head commissioning the result acquisition) is blocked by the launch subtree, not by a system operation

The leaf run with the real model completes (`execution_result_acquisition/tests/test_blast_grading_model_run.py`:
the model selected `blast_grade` on the fetched result; the completion controller stopped the Episode; resume
replayed the recorded answer). The run of the head `sequence_homology_evidence` commissioning it was not written,
because the head holds nothing from which the results commission can be built:

- `messages/msg_to_child.py::_results` takes the whole results assignment from the model's open `assignment` object.
  The leaf requires `handoff_ref` (a held `job_ledger` handoff row) and `target` (`execution_target_v1`: resource id
  and kind, execution id, request digest, origin episode). Only the launch child knows them.
- The launch path does not run: `execution_job_submission/api_job_execution/task.py:196` raises
  `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + member)` and `:209` raises for the job record kind;
  `execution_job_submission/task.py:124,150,178` raise for `job_access.validate_assignment`, `capabilities`,
  `received_bvbrc_context`. The built `JobAccess` (`episode_runtime/job_access.py`) offers `launch`, `check`,
  `fetch`, `cancel`, `run`; the launch episodes call members it does not have.
- Wanted, in the episodes (job-service carry-over, not this wave): `api_job_execution` launches through
  `await ctx.services['job_access'].launch(ctx, resource_id, job, inputs=...)` and returns the handoff row and the
  target in `record_refs` and controlled fields; the head's `msg_to_child._results` then builds `target` and
  `handoff_ref` from the handoff row it holds (`JOB_LEDGER` row `detail`: `resource_id`, `kind`, `native`) instead of
  taking them from the model.

## 2. Publication of a BLAST database result as per-HSP observations

`blast_grade` retains the graded sheet on an `ncbi_blast` source and writes the search into the A101 tool profile
(`native_correspondence.SEARCHES`), so the axis sheet includes the BLAST channel even without hits. The per-HSP
alignment observations that carry BLAST correspondence into the axis credit are written only by
`ToolRegistry._import_blast` (`tools/sequence_homology_evidence/tools.py`), reached through `RemoteSearches`
(`jobs/service_calls/sequence_homology_evidence/provider_jobs.py`) or by the old API episode with the original
submission snapshot. Neither path runs in the new paradigm yet (the API launch above). Until it does, a graded
BLAST return gives the head a BLAST channel of component 0.

## 3. No runner bug found

No failure of `episode_runtime/` was met. `EpisodeRun.next_decision`, `run_unit`, `run` and `resume` were used as
documented.
