# Local handles, results and failures

The original requested job has a durable disk handle and systemd execution
identity. Recovery observes that handle; it does not repeat submission because
the episode or caller restarted. Prepared, starting, running, terminal and
unknown states have different meanings. Process liveness does not establish
productive computation. A missing terminal receipt is not a successful exit.

`practical.job.status` and `practical.job.collect` expose the native outcome,
available stdout/stderr tails, original offsets and file sizes. Use
`practical.file.read` when a further log/output window is needed. Elapsed
`systemd_service_wall_seconds` includes the native service lifecycle; it is
not a separately measured queue wait or program-only execution interval.

A scoped `receipt_ref` lets a later practical episode observe an original
execution from another episode. The binding verifies the saved receipt's scope,
requested job digest and resource kind. The receiver validates its own output
requirements against that original execution; it does not rewrite the closed
launch's actions or credit.

The caller's endpoint is either a usable job handoff or successful requested
job outputs with the declared predicates. A handoff can be complete while the
native job continues. For an output endpoint, successful return and file
presence alone may not establish exact result identity: use declared file-hash
predicates where needed. Preparation commands cannot self-declare completion.
Validated endpoint completion makes future expected credit exactly zero while
preserving the final actual gain; the configured controller owns continuation.

Native execution, resource and filesystem failures retain their specific
outcomes. Unknown or active work is never replaced. A later explicit
`practical.job.start` can name `retry_failed_execution_id` only for the exact
confirmed failed current execution; repairing preparation does not itself
authorize a replacement. No retry, timer, polling cadence or forced cancellation
is chosen by this library. Source rows L3–L5.
