# V3 job validation reuse within one synchronous result check

This implementation contract addresses the measured repeated validation in
675's PROFILE_REPORT_001.md. It does not redefine the user-entered goal.

## Ownership and unchanged interfaces

Fresh676 owns only these production edits:

- `gene_annotation_episode/native_blast_utility_contracts.py`:
  `validate_native_blast_utility_job(value: dict) -> dict` and a private
  uncached implementation of its existing body.
- `gene_annotation_episode/native_blast_utility_results.py`:
  `NativeBLASTUtilityResults._validate_body(self, value, scope) -> dict`
  and a private implementation containing its unchanged checks.

Also own `tests/test_vdb_validation_reuse_676.py` and this verification
directory. Read, but do not change, the existing frame helper, acquisition,
publication, worker, result-return, practical-execution and Workflow consumers.
Root has completed674 and transfers these two touchpoints to676. Agent673
owns its existing Workflow test and original live handle; do not alter either.

## Exact behavior

1. Every public job-validator call still runs `finite_json_copy(value)`.
   Preserve the exact existing union-schema and semantic validation in the
   uncached implementation. Reuse successful V3 validation only, including the
   schema check; keep V1/V2 on the unchanged uncached path. Invalid top-level
   shapes retain their original schema/error behavior.
2. Use existing `form_validation_value` and a key consisting of a private
   function/version namespace plus the entire sorted finite JSON job text.
   Preserve list order and JSON value types, including true versus1 versus1.0.
   No ID-only key, partial-key hash, persistent cache, LRU or new cache owner.
   The cached result is only the detached validated job dictionary.
3. `_validate_body` enters one fresh existing `form_reference_validation()`
   frame, then calls its private original implementation. Nested frames restore
   the outer frame on exit. No frame spans async execution, report history or
   workflow operations. The helper implementation itself is unchanged.
4. Store bytes, scope, original selected actions/assignments, target ancestry,
   receipt/intent/observation, provenance proof, prepared/publication values,
   frozen forms, commissions and explicit reference grants remain live checks.
   Do not cache their truth under a job key. The674 failure-publication branch
   stays intact. No scientific parser, numerical calculation, credit,
   continuation, selected work, schema or prompt behavior changes.
5. Preserve failure non-caching, detached return values, frame-exit clearing
   and inactive copied-context behavior supplied by the existing helper. Read
   all V3 validator callees and verify that the reusable job validation is pure.
   Use a lazy import if needed to preserve module import order.

## Verification and handoff

Read675's full profile report and its eight-case verification matrix. Cover:
same-value reuse versus uncached equivalence; no reuse outside frames; changed
job content and nested lists; caller/returned-object mutation isolation;
bool/int/float distinctions; repeated invalid inputs; separate and nested frame
lifetimes; copied contexts after exit; V1/V2 unchanged behavior. Verify the
actual saved result body and return consumers, including current artifact-byte,
scope/action/intent/observation, metadata/proof and frozen-value/grant tampering.
Use original676 code paths, not test doubles that replace the validator under
test. Existing controlled target/native ports must remain explicitly qualified.

Measure retained-body/return behavior with the complete validator enabled and
disabled only at the pure memo boundary, using the same saved controlled case.
Report exact invocation counts and measured timings; do not infer total673
speedup from675's controlled fixture. Prefer retained675 artifacts; a new tiny
controlled engineering fixture is acceptable when necessary, but no native
helper, service or historical acquisition may be rerun for profiling. Preserve
all original675 and673 evidence. No new whole-utility or operation-count claim.

All imports, tests, Store/SQLite and data processing use bounded529 with explicit
check005 dependencies,20GiB RAM/4GiB scratch/zero swap/no wall cap. Source and
evidence metadata inspection may use the host. Observe the same launched handle;
do not resubmit because a wait returns. Fix test-only failures and rerun only
affected cases. Report terminal/quiescent receipts and source-pin limits.

Before coding, read the user-entered goal attachment in full, applicable
AGENTS.md, the required episode/time/practical design documents,675's full
report and the complete affected implementation/consumer paths. Do not read
GOAL.md or create a goal/scope-amendment file. After each bioinformatics tool or
substantial external/native-output review, reread the attachment's objective
and entire OPERATING PRINCIPLES block verbatim, then this contract before a
completion claim. Keep the two formatter exclusions; do not change inventory.

Handoff includes exact changed files, equivalence/custody checks, same-case
profile results, preserved limitations and current source hashes. If evidence
requires broadening this boundary, report the specific dependency to root
before editing additional production files.
