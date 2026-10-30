# Native-six lifecycle failure correction: verification

The contract-scoped correction is implemented and verified. Root owns acceptance.
There was no incompatible interface and no expansion of production ownership.

## Executed checks

| Run | Actual pytest result | Actual service wall seconds | Observed scratch bytes |
| --- | --- | ---: | ---: |
| inventory_check_20261026T223404800795Z | 2 passed, 25 deselected in 26.67 s | 27.258962124 | 4513792 |
| contract_check_20261026T223543602934Z | 9 passed, 18 deselected in 149.53 s | 150.180090316 | 20897792 |
| success_return_check_20261026T223714614770Z | 1 passed, 26 deselected in 23.45 s | 24.012829622 | 4251648 |

These are **10 distinct test cases**: the first two inventory cases are repeated
in the nine-case contract group and are not additional coverage. All invocations
returned exit 0. The focused group and successful-return group used identical
before/after source pins. The metadata owner held exactly the two shared metadata
modules stable during that approximately 2.5-minute window, then was released.

Each test invocation ran through the existing run_local_job using the existing
.venv/bin/python -B, 21474836480-byte memory and 4294967296-byte scratch policies,
wall_seconds null. The actual receipts retain verified cgroup memory_max
21474836480, memory_swap_max 0, runtime_max infinity, kill_mode control-group and
oom_policy kill. Service-wall time is reported as measured; it is not relabeled
native-only execution time.

Actual test receipts:

- [Focused contract receipt](contract_check_20261026T223543602934Z/receipt.json)
- [Focused stdout](contract_check_20261026T223543602934Z/pytest.stdout)
- [Successful typed-return receipt](success_return_check_20261026T223714614770Z/receipt.json)
- [Successful typed-return stdout](success_return_check_20261026T223714614770Z/pytest.stdout)
- [Earlier inventory receipt](inventory_check_20261026T223404800795Z/receipt.json)

[EVIDENCE_INDEX_001.json](EVIDENCE_INDEX_001.json) records the exact paths, byte
sizes and SHA-256 hashes for these records, the seven distinct failure examples,
and the original durable native-six action receipts. The test run directories
also retain the Store, original bundle bytes, worker outputs, calculations,
implementation receipts and original typed forms in the action/report journal.

## Concrete verified behavior

| Case | Existing closed failure | Retained evidence and result |
| --- | --- | --- |
| Unqualified synthetic SIGKILL | native_blast_database_worker_failed / implementation_failure | Original native_returncode -9 and injection marker; complete collection.json sibling and stderr retained; no manifest and no numerical rows |
| Actual collect, injected oom-kill, worker boundary | native_blast_database_worker_resource_limit / resource_limit | Original AcquisitionError code local_job_resource_limit, phase local_execution, resource memory_bytes, limit 21474836480 and evidence systemd_service_result oom-kill retained exactly |
| Actual collect, injected oom-kill, inventory boundary | Same resource failure | Same original typed facts plus implementation-receipt.json retained; no numerical generation |
| Actual collect, injected missing native receipt, worker boundary | native_blast_database_worker_failed / implementation_failure | Original AcquisitionError code local_job_execution_error, phase local_execution, reason native_receipt_missing and execution_failure null retained exactly |
| Actual collect, injected missing native receipt, inventory boundary | Same non-resource failure | Same original typed facts plus implementation-receipt.json retained; no numerical generation |
| Exception after a valid sealed manifest, both typed error classes | Correct resource or non-resource failure as above | Caller diagnostics and worker diagnostics remain separate retained artifacts. One sealed, published HSP returns native_score_bits 20 and native_evalue 0.0; prepared status partial; projection_complete and complete false |

All seven failure examples exercised the actual selected result owner and the
existing immediate-child parent form validation/admission/received-facts path.
Each preserved exactly one selected action in runtime_actions. Replaying the
same saved action was explicitly forbidden from invoking a local job, observing
the remote target or reading remote files, and returned the original outcome.
The number of local-job calls remained two for worker-boundary cases (inventory
plus worker), or one for inventory-boundary cases. No completion proof was
produced. Already known result references had zero additional operational credit.

The sealed-partial cases retained one original scientific observation before and
after replay, rather than creating additional observations from exception
recording or delivery. The unsealed sibling was never used as row authority.

The separate successful PSIBLAST case retained complete=true and the original
requested typed parent HSP return: native_score_bits 20, native_evalue 0 and the
underlying published native_raw_score 40. Its expected original subject/source
relationships were checked by the existing test. The successful frozen replay
case still validated without remote work or numerical recalculation and detected
deliberate retained-row corruption. That latter negative check intentionally
leaves the altered test artifact in its own temporary case directory; the
separate successful typed-return case retains the valid positive example.

The invalid calculator-model case still reports calculation /
native_blast_database_calculation_failed / calculator_contract_invalid, preserves
the original invalid request and ValueError, produces no generation manifest,
and returns through the existing typed boundary.

## Exact changed files

| File | Final bytes | SHA-256 |
| --- | ---: | --- |
| gene_annotation_episode/native_blast_database_result_publication.py | 66847 | 24343190ba76a4926a689fe236a7d8e4fe551d89dd3fe630b17f2c60932449a5 |
| gene_annotation_episode/native_blast_database_results.py | 21709 | 51480aea3a9cf063ab519675bc39706e46fc0917cfee52971331586f69f6f068 |
| tests/test_native_blast_database_results.py | 35795 | 908fad09c0b8d0b67cd854b2baef38695bd60b5532c01fbe2a721f7e9b314cce |

The original bytes/hashes are in [BEFORE_SHA256_001.json](BEFORE_SHA256_001.json)
and `before/`; final source bytes are identified by
[AFTER_SHA256_001.json](AFTER_SHA256_001.json). Production/test bytes match those
used by both final checks. The tested shared metadata pins were:

- native_blast_database_metadata.py:
  4292386638f1a624358d52109914d54d34562741c4d5eeada753465d4b29a19b
- native_blast_standard_database_metadata.py:
  f378270daadb53b6925664934b951a6a09295b3ba77e65aa169eb5abdbfaccc3

The numerical worker, local_jobs and native_lifecycle hashes were unchanged
through the two final checks. Their exact hashes are in the actual receipts.
No scientific formulas, receipt history, permanent decisions or accounting rows
were rewritten. Other owners may subsequently change their own dependency bytes;
these receipts remain evidence about the precise tested versions above.

## Limits

These statuses are explicitly injected test inputs to the real lifecycle
classifier, not physical resource exhaustion. The synthetic report and local PBS
fixture do not establish live HPC deployment or actual native database BLAST.
There was no scientific API/HPC job, local database BLAST, installation or
download. This correction was verified on the shared native-six result owner
using PSIBLAST fixtures; the full 27-case owned test file and the other five
programs were not rerun in this packet. No configured-model episode or estimator
run, new numerical formula or broader tool completion is claimed.

The immutable purpose/all sixteen principles and the exact 341 contract were
reread before closing this packet. Root acceptance remains separate from these
implementation/test observations.
