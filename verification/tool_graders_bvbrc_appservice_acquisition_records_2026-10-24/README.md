# Acquisition receipt persistence verification

This directory records a supporting storage component, not a scientific grader
or completion of the immutable tool-library goal.

## Actual verification

| Scope | Result | Captured evidence |
| --- | --- | --- |
| New acquisition receipt persistence suite | 56 passed in 1017.51 seconds | `acquisition.command.json`, `acquisition.log`, `acquisition.result.json` |
| Existing records and production host support/handoff regressions | 20 passed in 143.32 seconds | `regression.command.json`, `regression.log`, `regression.result.json` |
| Retained synthetic Store/action/call/receipt example | Exact nine bytes retained; same value reopened; no additional runtime observations | `EXAMPLE.json`, `EXAMPLE.receipt.json`, `retained_example/` |

The new tests retain real Store records, original selected actions, frozen
preparation/call records and exact synthetic native bytes. They check replay,
interrupted publication, missing completed outcomes, changed arguments, wrong
task/selector/source/digests, tampered frozen inputs, forged envelopes with
matching hashes/outcomes, and preservation of partial/error/range/empty bodies.
They also retain the existing CommonReceipt fallback and TaskHandoff encoding.

The example's bytes are `61626364656600ff0a` (nine bytes), SHA-256
`85da2d9b7620ac8c9ec4292b2ce1399f49ff4199f14d2eda6345cfc9c75ca06c`.
The acquisition's decoded self-reference equals its actual source
`source_91e98fe4394a1ed6abd3bf74`; the hashed envelope omits that field, and
`publication_ref` remains null. Its observed transfer body is complete and its
declared total is nine bytes. These are byte-retention measurements, with no
annotation-confidence score.

`INSPECTION.json` records the authority, reviewed paths and owned-file hashes.
`preflight-note.json` records an earlier interrupted diagnostic run; it supplies
no claimed pass count. The complete captured runs above are the test results.

## Limits and handoff

No live API/HPC call, model inference, scientific calculation, new scoring rule,
new episode loop or full shared-method-loop acquisition-return verification was
performed. Synthetic native replies are not scientific measurements. The host
owner integrates these unchanged public publish/read signatures, freezes the
publication inputs, authenticates prior dependency custody, and publishes the
separate BundlePublication. The host also owns receiver-facing results and
ordinary observation/credit/continuation behavior.

The full-path read identified the generic support-receipt accessor's assumption
that all non-common values have a nested receipt. This was reported to the
integration owner, who separately added explicit rejection of acquisitions at
that support-only consumer while preserving the dedicated manifest acquisition
reader. No files belonging to that owner were edited here.
