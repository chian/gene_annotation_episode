# MinHash receipt and return boundary verification

This is a narrow C4d verification of the original results owner's acquisition,
saved numerical publication, typed child return and subsequent forwarding.
It is not a BV-BRC availability, metadata-acquisition or annotation-correctness
claim. Tests use fresh Stores and worker095's `MinhashRun` fixture: real shared
Workflow construction, API service preparation, publication and communication,
scripted episode selections, and explicitly synthetic native-shaped response
bytes at the urllib boundary. No live service, credentials or model is used.

## Reproduced and repaired defect

The scientific episode can explicitly select two different results children for
the same retained handoff and selector. Their separate acquisitions legitimately
produce the same content-addressed source. Originally, `read_result` chose the
first indexed results owner, so the second owner's `read_own` failed with
`bvbrc_minhash_host_acquisition_owner_conflict` despite its completed selected
action and valid acquisition receipt. The concrete reproducer made one RPC and
two selected result acquisitions; it did not manufacture a host context.

The root implementation now accepts an optional results `episode_id` when
qualifying `read_result`; MinHash `read_own` supplies its authenticated owner.
`test_two_selected_result_owners_can_read_same_retained_source` checks both real
owners, unchanged saved grades, one HTTP request, two distinct acquisitions,
deduplicated received facts, and zero additional operational credit for the
second acquisition of already inherited information. No production files were
edited by this verification worker.

## What the tests exercise

- Actual results ownership, exact saved context, wrong run/episode/assignment,
  and fabricated but correctly content-addressed source rejection.
- Count-only root forwarding: returned count 2; no match rows or genome-ID
  resolution obtained by possessing that source reference. The launch episode
  cannot read its later sibling results' numerical data.
- Exact `record_admission` form, schema, receiver and operation key; a changed
  count, boolean substituted for a number, different schema, another receiver,
  missing original attempt and noncanonical decision index are rejected.
- Selected operation identity, completed original action, acquisition receipt,
  prepared scientific request, original eight-argument RPC request and retained
  snapshot metadata. Temporary corruption is restored after each assertion.
- SHA-256 checking of retained raw response, request metadata, sent RPC request
  and grading artifact bytes.
- Actual admission order: the receiver sees no MinHash facts before typed
  admission or immediately afterward before the form is saved. The successful
  saved `runtime_report_attempts.form` supplies the admitted facts before receipt
  and credit projection. It is the existing admission record. Shared
  method_loop's later contract revalidation changes no durable history.
- Reopen, own/received reads and replay of the original selected API/result
  actions with service invocation, parsers, calculators and model decisions
  disabled. Saved grades, returns, actions, observations and credits stay equal.
- One observation per actual own action, no additional grading turn, and
  unchanged run-owned runtime tables after read-only validation and replay.

The synthetic numerical example contains two original rows for genome
`83333.1`. Native distance/p-value pairs remain `0.02 / 0.001` and
`0.03 / 0.002`. Sampled hash fractions are `41/1000 = 0.041` and
`20/1000 = 0.02`; distinct row indices remain `0` and `1`. Returned count is 2.
Search-population size, truncation and actual k/length/alphabet metadata remain
unknown, so native distance and p-value are not recomputed.

## Source inspection and limits

Read the complete `bvbrc_minhash_host.py`, `episode_return_records.py`,
`api_service_execution.py`, `api_bvbrc_minhash.py`, `bvbrc_minhash_views.py`,
`api_services.py`, `episode_admission.py`, `episode_receipts.py`, relevant complete
shared forwarding functions, and blocking/durable typed-admission consumers in
`runtime.py` and `method_loop/episode.py`. Read the supplied immutable objective
and all sixteen design principles, then repeated the required reset after
substantial source study and before handoff. Contracts 003–005 retain authority
within the user's immutable goal.

The dynamic tests here use the existing blocking child path. The independent
durable return transaction (`episode_admission.admit_return` and
`Workflow.next_return`) was inspected for the same admission-before-receipt
order; this worker did not run an independent-execution MinHash commission.
Source-only forwarding, both genome/FASTA selection, partial native rows and
other original-child corruption cases also have separate worker095 tests;
those are not counted as this worker's dynamic assertions. Live BV-BRC calls,
source metadata acquisition and scientific interpretation remain unfinished
outside this boundary.

## Verification commands

The final results and exact commands are recorded in `test_results.txt`.
Earlier test-development failures were harness corrections: temporary receipt
JSON initially omitted the original required trailing newline, and the timing
probe initially did not account for shared method_loop's later revalidation.
Both failed assertions were corrected without changing production behavior.
