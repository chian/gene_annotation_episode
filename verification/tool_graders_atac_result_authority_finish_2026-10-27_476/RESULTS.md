# Workload C verification results, packet 476

These are implementation observations, not a replacement for the original
user-supplied goal or a declaration that the complete ATAC workflow is verified.

The latest observed result for each of 166 distinct tests is passing: 22 operand
tests, 55 result-receipt tests, and 89 return-authority tests. This is an
incremental aggregate across immutable snapshots, **not** a single all-green run
of all 166 tests against the final checkout. The later checks target changes
made after the earlier complete-file checks. Every failed attempt remains
recorded below and in its original directory.

| Attempt | Observed result | Interpretation |
|---|---|---|
| check001 | 21 passed, 85 failed | Snapshot preceded root's ATAC shared schema registration. The return cases exposed that missing binding; one operand assertion incorrectly assumed Store started with no source records. |
| check002 | 108 passed, 3 failed, 23 errors | New authored receipt fixture supplied an invalid empty requested form. The other failures were the operand source-count assumption, an expected-error text mismatch, and a real exception-boundary defect for a corrupted frozen compact-contract frame. |
| check003 | 1 error | Focused reproduction of the authored receipt fixture's empty requested form. |
| check004 | 1 passed | Corrected nonterminal collection fixture, including exact replay after removing original BAMs and the current resource factory. |
| check005 | 49 passed | Receipt-authority cases and corrected operand assertion. |
| check006 | 54 passed | Receipt-authority cases after authenticating both original commissions and permitted launch resource/request/constraints. |
| check007 | 2 passed | Corrected return-schema error assertion and explicit inherited instruction additions. |
| check008 | 5 passed | Original compact declaration, corrupted frozen frame, changed declaration, missing frame, and compact redelivery after the exception-boundary repair. |

All eight attempts were collected using their original lifecycle handles and
were terminal and quiescent. The original return codes were 1 for check001–003
and 0 for check004–008. Source, installed dependency closure and interpreter
digests were unchanged in every attempt. From check003 onward, the copied
standard-library digests were also unchanged; check001 and check002 did not
copy or separately pin the standard library. Each attempt retains its selected
request, original goal identity, before/after pins, handle, native receipt,
stdout/stderr and JUnit record.

Every attempt used the existing bounded `local_jobs` / `native_lifecycle` path:
20 GiB RAM, 4 GiB scratch, zero swap, and no wall-time budget. Scratch enforcement
is the existing monitored allocated-byte mechanism with possible overshoot,
with a hard per-file limit. No application test ran directly in the host shell.
`run_checks.py` separates launch, status and collect and never turns collection
into a new launch.

The original 471/check001 was inspected, not relaunched. It ended with code 1;
its old runner did not retain dependency pins. The accidentally launched
471/collect attempt ended with code 4 because pytest received an invalid
`check001` path. Neither is counted as successful verification here.

The test evidence covers exact received input custody, selected actions and
original handoffs, both original launch commissions, saved and historical
authority independent of current factory bindings, origin meanings,
nonterminal and zero/missing/failure distinctions, compound saved-bundle
receipt authority, frozen received prefixes, forwarding, compact forms,
redelivery, and repeated-population credit. It uses authored opaque input and
software identities, real Store/Journal/receipt records, and explicitly
synthetic native observations. The return suite uses a strict synthetic result
host. These controls establish no native ATAC measurement.

This packet does not execute MACS2 or establish a completed native result-worker
publication through the full workflow. Root's separate 478 run owns that path
and the requested tampering checks against its actual completed worker receipt.
Sibling 474 owns producer execution; sibling 475 owns finite worker and saved
partial-stream execution evidence. Their results are not counted in this
packet. Source-level worker authority inspection is recorded in TRACE.md;
source inspection alone does not establish the unexecuted path.

`OWNED_FILE_IDENTITIES.json` identifies the final owned code and test files.
`LATEST_TEST_OBSERVATIONS.json` records the per-test incremental aggregate and
its originating attempt. No inventory row or permanent direction record was
changed. No controller, estimator, numerical calculator, literature grader or
W05 annotation-credit implementation was changed.
