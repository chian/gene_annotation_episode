# Root review: actual local-job failure interface

This is an additive review finding, not acceptance of E336 or a change to the
immutable tool-grader goal. Root read all four new E modules, the E boundary
in327, its additive003/004 contracts, and the actual local-job failure interface.
Shared-consumer and complete test review remain in progress.

## Confirmed defect

`prepare_standard_blast_database_grading` in
`native_blast_standard_database_result_publication.py` labels every negative
`LocalJobResult.returncode` as `native_blast_standard_database_worker_resource_limit`.
Its abrupt-worker test injects `returncode=-9` and explicitly records no actual
resource exhaustion, yet requires that resource-limit label. A signal alone
does not establish this cause.

The real `native_lifecycle.collect` implementation instead raises
`AcquisitionError('local_job_resource_limit', phase=..., operational=...)` when
its original lifecycle facts establish a resource limit. Other execution
failures have their own `AcquisitionError` code. `AcquisitionError` inherits
`RuntimeError`. Neither the new preparation boundary nor the outer
`StandardBLASTDatabaseResults.execute` error branch catches it. Thus the
synthetic negative-return test does not exercise the actual resource-failure
interface.

## Correction assigned to the existing E336 owner

- Consume the actual typed acquisition exception. Preserve its original code,
  phase and operational evidence in retained diagnostics/receipts.
- Use the closed worker-resource-limit result only for the lifecycle's explicit
  resource-limit finding. A negative return without that finding is a worker
  failure; retain the actual return code without inventing its cause.
- Preserve already written atomic siblings and logs, while withholding numeric
  row authority when no valid manifest exists. Keep completion false.
- Handle the same typed interface if the fresh implementation-inventory job
  fails before a grading generation is created.
- Verify an explicit resource-limit exception, a non-resource execution
  exception, the signal-only return, and the inventory failure boundary. Keep
  original failed receipts and distinguish injected failures from physically
  exhausting resources.

This uses the accepted closed failure codes and existing diagnostics storage.
It adds no retry, alternate resource, extra episode action, observation,
scientific score or controller rule. The prior regression run remains active;
edits must respect the coordinated source window.

No tests were run by this review. Root separately confirmed that the active
regression's systemd unit was active/running with a live MainPID before
requesting the correction. No grader-count change is warranted by this finding.
