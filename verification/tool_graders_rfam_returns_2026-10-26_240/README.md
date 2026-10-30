# Rfam source custody and typed returns

The owned workload implements `RfamBatchReturns` in
`gene_annotation_episode/rfam_batch_returns.py` and verifies it with
`tests/test_rfam_batch_returns.py`. Root owns shared execution hooks and the full
Workflow proof. Publication239 owns the retained source writer. The exact scope
is [RETURNS_WORKLOAD_004.md](../tool_graders_rfam_implementation_2026-10-26_234/RETURNS_WORKLOAD_004.md).

The reader starts with the actual generic API `read_result` receipt. It checks
the original submission and response, original publication operation, all three
source identities, grading manifest, original input and selector, parse, numerical
sheet and saved calculator artifacts. It copies only the original selected
projection. The two fact families are `rfam_result_rows` and
`rfam_result_populations`; the latter preserves a complete empty population
without inventing a hit. Foreign table rows retain null query attribution and
explicit unavailable cells. Optional metadata failures preserve unaffected
native quantities and their specific qualification.

The existing `EpisodeReturnRecords` path authenticates the original commission,
child scope, frozen form, admitted report and forwarding. Numerical ownership is
limited to results and receiving annotation/scientific-process episodes. A source
reference, population-only form or completion-only form does not grant numerical
row access. Recursive scientific forwarding preserves exactly what the original
child form admitted. Replayed reads and reports make no database mutations,
acquisitions, parsers, calculator calls or additional observations.

The shared form validator already supports `alignment_strand`; Rfam uses that
format and separately restricts its values to `+`, `-` or null. Its legacy
`unknown` value is rejected. This avoids changing the shared string-enum grammar.

## Verification

All runs used the established bounded runner with 20 GiB RAM, 4 GiB scratch and
no wall-time cap. The receipts record enforcement, elapsed time, scratch usage,
commands and source hashes. The final two runs record before/after hashes of
18 relevant source and test files; neither changed during those runs.

| Run | Result | Purpose |
| --- | --- | --- |
| [tests_001](tests_001/verification-receipt.json) | Interrupted; 2 passed, 38 failed | Exposed the shared literal `+`/`-` enum restriction; history retained. |
| [tests_002](tests_002/verification-receipt.json) | 7 passed, 1 failed | Exposed incompatible retained multipart wire bytes in a synthetic batch fixture; fixture corrected. |
| [tests_003](tests_003/verification-receipt.json) | 9 passed in 60.52 s | Corrected table, empty and partial fixture cases. |
| [tests_004](tests_004/verification-receipt.json) | 55 passed in 462.38 s | Full suite before the last receiving-parent role guard. |
| [tests_005](tests_005/verification-receipt.json) | 6 passed in 27.02 s | New forged monitor-parent regression, exact forwarding and optional metadata after the guard. |
| [tests_006](tests_006/verification-receipt.json) | 4 passed in 14.95 s | Optional metadata checks against the final shared scope helper. |

There are 56 distinct passing cases across these runs; targeted runs overlap.
They use real Store records, ToolRegistry publication, generic API execution
receipts and handoffs. Runtime commissions, frozen forms and report attempts
are controlled fixtures. These tests do not establish actual Workflow/model
decisions or configured yield-controller behavior. Root verifies that separately.

Checks cover selected-only rows and identifiers, exact forwarding, complete zero
versus partial unknown populations, JSON and generated-name table results,
unavailable cells, selected metadata failures, wrong child/owner/scope, forged
values and associations, changed original commissions/selectors, corrupted
sources and artifacts, restricted original forms, exact replay and no work during
return. Return reads are tested with acquisition, Rfam/Infernal parsers and
calculators disabled. Network and subprocess creation are forbidden in tests.

## Evidence attribution

The unchanged single-query JSON and submission bytes come from the previously
retained transport workload. They report 104.6 bits, E-value 1.4e-24 and query-span
fraction 1.0. Full model coverage is explicitly unavailable because full model
length is unknown. These are different retained measurements from the older
contract's illustrative 104.9-bit result; the older receipt is not rewritten.

Batch fixtures explicitly mark synthetic evidence: they adapt observed native
table formatting and query names to the generated original input contract.
Missing, malformed, duplicate, foreign, empty and partial variants are synthetic.
No new live Rfam request, model call or HPC job was run by this workload.

[FILLED_RETURN_EXAMPLE.json](FILLED_RETURN_EXAMPLE.json) is copied from the actual
saved publication and two equal frozen forms in the final forwarding regression.
It includes source paths and the retained native digest; it is not a newly
calculated scientific result. [CLOSURE.json](CLOSURE.json) records final source
hashes, contract hashes, all run results, corrections and limits. The authoritative
objective and all sixteen principles were reread verbatim after study and at
closure, followed by the exact return/publication and original numerical/return
contracts. No shared tracker completion, W05 credit aggregation or broad Rfam
capability completion is asserted by this record.
