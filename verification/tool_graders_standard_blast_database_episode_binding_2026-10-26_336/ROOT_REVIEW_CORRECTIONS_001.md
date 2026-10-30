# E closeout corrections from direct contract and root review

The original test receipts and source snapshots remain unchanged. The initial
complete acquisition/episode run recorded 37 passing cases and one fixture
failure; its receiver selection omitted run_id/episode_id. The focused E11
correction then passed once. The initial complete results/returns run recorded
46 passing cases and one fixture failure: the null-PSSM consumer test had no
native query id/title and correctly stopped at query_operand_unresolved. Its
new explicit PSSM fixture supplies the actual matching id/title `one`.

Read-only contract review identified the exact public attempt method spelling.
The new acquisition, target reader, PBS adapter and test stub now use
`authenticate_standard_blast_database_attempt`. No existing caller needed an
alias. Original-attempt ledger/request authentication is unchanged.

Root then identified a real failure-classification and exception-handling defect:
a negative exit was incorrectly called a resource limit, while the actual
`AcquisitionError` emitted by local_jobs was not caught. The new E boundary now
catches that explicit type. Only its exact `local_job_resource_limit` code yields
the closed worker_resource_limit failure. Negative exits without that finding
and other typed lifecycle failures yield worker_failed.

The original code, phase and complete operational facts are copied into retained
diagnostics and a local-job failure receipt. The worker path retains its atomic
siblings and partial logs without promoting them to numerical rows. The
implementation-inventory path records its failure receipt and returns the same
original exception details through the outer results boundary. A caller failure
remains retained even if a worker manifest is available. No resource retry,
second selected action, native database command or broad BaseException catch is
introduced.

The new four-case regression calls the real native_lifecycle.collect function
with explicitly synthetic returned status facts for resource/nonresource errors
at the worker and inventory boundaries. It asserts exact preserved exception
fields, closed failure meaning, incomplete outcome, retained atomic siblings
where available, typed return and no repeated local job on replay. The negative
SIGKILL fixture remains expressly non-resource exhaustion and now expects
worker_failed. No physical memory/scratch exhaustion is claimed.

The existing 12-file BLAST/shared regression run ended before these edits:
251 passed in 1322.93 seconds, check_20261026T214940585294Z. Its source snapshot
is historical coverage of the additive shared integration before the exact
method rename and E failure correction. Focused final-source checks are recorded
separately; the earlier mixed runs are not reclassified as passes.
