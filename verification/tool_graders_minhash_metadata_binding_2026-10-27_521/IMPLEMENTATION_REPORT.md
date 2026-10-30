# MinHash metadata binding implementation handoff

Implementation evidence only. The original user attachment remains authoritative;
this report changes no goal, requirement or inventory obligation.

## Written code

- `api_bvbrc_minhash.py`: additive V2 result selector and grading envelope; exact
  selected metadata retained through preparation; unchanged legacy `{}` prepared
  intents and native request bytes/arity; existing shared sheet/calculator used
  for native and explicitly selected saved input modes. Saved mode copies the
  original parse status/diagnostics and sheet from the retained grading artifact;
  the existing calculator retains its pure saved-native validation.
- `bvbrc_minhash_host.py`: exact scalar source/artifact/pointer/value bindings,
  original metadata-list occurrence preservation, own completed tool action or
  admitted immediate-child return proof, exact selected parent assignment with
  custody before its commission, same-request/response saved-result association,
  frozen input checks without pointer extraction or current calculation, and the
  two optional requested fact families. Calculation-only genome identifiers
  resolve from their received family without materializing unrequested matches.
- `api_service_execution.py`: fresh MinHash input validation, original immutable
  publication-input snapshot and receipt digest, recovery preferring those saved
  records, input error detail propagation, and the legacy empty-selector basis
  for original native acquisition identity. New calculated publications remain
  distinct sources while unchanged response bytes have the original credit identity.
- `execution_episodes.py`: MinHash-only parent input validation and explicitly
  selected initial reference custody. No new episode, observation or controller.
- `execution_progress.py`: actual selected calculation operands and saved-input
  basis plus available typed return families; no prompt/template change.
- `communication.py`: exact complete top-level registration of the declared
  MinHash calculation-diagnostics fact schema. Generic grammar is unchanged.

## Static checks and authored runtime checks

All eight changed source/test files parse with Python stdlib `ast.parse`.
The scoped diff was reviewed against retained before snapshots. No application
or scientific module was imported; no pytest, native program, HTTP request,
model service or new scientific analysis ran in this workload.

Five new service test functions contain 11 parameterized cases. Twelve new
custody test functions contain 26 parameterized cases. These 37 authored cases
have not been executed or claimed passing. They cover both RPC modes, native
bytes and legacy intents, full/null/k-only metadata, duplicate row candidates,
request/response associations, own and admitted source custody, precommission
ownership, unavailable source/artifact/pointer/value failures, exact integer
inputs, auxiliary grading artifacts, RFC 6901 pointers, immutable publication
inputs, interrupted publication recovery, saved recalculation, acquisition
identity, calculation-only references, and exact diagnostic schema registration.
Existing service tests remain in place. Root owns complete Workflow checks and
runs all scientific verification in its frozen lifecycle.

The numerical assertions reuse the existing synthetic 2/3 example: k=1 and
lengths 2/2, alphabet 2 expect distance 0.22314355131420976 and p-value
0.2592592592592592; k=2 expects 0.11157177565710488 and 0.10400000000000001.
These are expected test values, not new measured BV-BRC results.

## Explicit unfinished work

- Execute the authored service/custody tests and combined root-owned Workflow,
  replay, requested-return and credit checks; repair any demonstrated failure.
- Instruction presentation remains unfinished. In particular the historical
  `result_capabilities` description still says recalculation is unavailable.
  The handoff excludes prompt/library edits pending the required feedback path.
- Actual intended-service live output and deployed sketch parameter equivalence
  remain unverified; supplied numerical inputs retain `unestablished` equivalence.
- No whole MinHash, R2 or R1-R7 completion is claimed. Existing inventory history
  and the fixed unfinished rows were not changed by workload B.

## Review artifacts and dependencies

`before/`, `BEFORE_MANIFEST.json`, `SCOPED_DIFF.patch` and
`FINAL_SOURCE_MANIFEST.json` identify the exact changed files. The new custody
checks import fixtures/helpers from `test_api_bvbrc_minhash.py`; that existing
module imports `test_bvbrc_analysis_transport` and `test_execution_episodes_family`.
The pure A519 contracts/calculator and C520 saved projector remain separately
owned; B changed none of their files. No conflict within the owned files was identified by the static review.
Runtime behavior remains pending root checks.

A later D522 consumer trace identified an unresolved receiver defect outside B
ownership: `runtime.py` action commissioning catches `ContractError` as
`ValueError` and saves only `str(error)`, dropping the structured `.detail`
provided by the MinHash host. The selected invalid-input Workflow tests retain
the required source/field assertions. Root has been notified to own the narrow
receiver repair; B did not edit runtime.py or weaken those assertions.
