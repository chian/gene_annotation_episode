# BV-BRC original report-contract custody repair

This packet records a narrow result-path repair under the original user goal,
SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The original objective and all 16 design principles were reread verbatim,
followed by this workload's exact input/output contract. Repository designs,
tests and this packet are implementation evidence, not replacement authority.
`GOAL.md` was not read. This packet does not claim completion of the broader
tool-library or scientific-grader goal.

## Production change

Only `gene_annotation_episode/bvbrc_appservice_custody.py` was changed by this
workload. Its final SHA256 is
`bc173c2aa427d053dcb74d64817cec2e8415978f7f696091b114ca4b99b1a818`.
`PRODUCTION_IDENTITY.json` and `PRODUCTION_DIFF.patch` retain the exact change
against the pre-repair source in the actual 458/check012 verification snapshot.

- Original parent actions and model-call selections must agree. A saved call
  retains its decision purpose and original allowed response schema; a compact
  selection additionally uses its original frozen role/fact catalog.
- Selected compact fact references are expanded against that frozen catalog.
  The exact child declaration, expanded schema, purpose/information metadata,
  assignment, scope, goal, durable commission and receipt inheritance must agree
  with their original records. An internally coherent replacement declaration
  and expanded schema cannot replace the original catalog.
- `_commission` preserves its `(parent_context, original_index)` return.
  `_attempt` preserves `(child_context, form, expanded_schema)`, authenticates
  original full/compact forms and validates delivered values against frozen
  child facts. Explicit redelivery uses its own original decision frame and the
  same child's original frozen values.
- Corrupt frozen contract information becomes `AppServiceCustodyError` with the
  existing `bvbrc_appservice_custody_` prefix, including failures raised by the
  runtime's saved-frame validator. No source, receipt, observation, credit or
  service call is created by this reader.

Literal closed schemas without declarations remain supported for historical
no-profile decisions. If a saved model-call row exists, its original schema is
required. Profile-backed full forms still require their exact declaration, even
when their fact-reference list is empty. Generic scientific-child forwarding
uses the original selected form. `process.revise` preserves its separate
construction-owner exception and the original frozen-form/value checks.

No numerical sheet, parser, calculator, episode type, model prompt, resource
choice, estimator, W05 formula or literature implementation was changed here.
The seven downstream BV-BRC return readers are separately owned and verified in
workload 480; they rely on this custody interface to obtain the authenticated
expanded schema.

## Verification and retained attempts

All application/test execution used the existing local_jobs/native_lifecycle
path with 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time budget. Each
launched attempt retained its original handle. Source, all installed Python
site packages, the complete standard library excluding site packages/cache,
and the Python binary were copied, made immutable and hashed. All collected
attempts had unchanged source/dependency/stdlib/binary pins.

| Attempt | Result | Meaning |
| --- | --- | --- |
| check001 | 1 failed | Initial test construction omitted the required explicit practical YieldController. |
| check002 | 1 failed | Reused scripted provider asserted an unrelated scientific prompt phrase on a launch prompt. |
| check003 | 1 passed | Actual Workflow full-form launch/API commissions, preparation return and compact redelivery. |
| check004 | No native execution | Preflight rejected a nonexistent requested monitor-test filename. No native handle exists. |
| check005 | 209 passed, 4 failed; 2419.33 s pytest duration | Full custody, host, input, native-monitor and shared Workflow monitor/recovery coverage. Four durable-fixture setup failures are retained exactly. |
| check006 | 4 passed; 31.01 s pytest duration | Corrected durable fixtures use a real Workflow-published original intent before dispatch. |
| check007 | 2 passed; 281.67 s pytest duration | Focused current-snapshot full/compact first-return and compact-redelivery checks; original handle collected. |

The four check005 failures all occurred before custody validation at
`CommissionCoordinator.select`, raising `CommissionError: identity_conflict`.
That test setup tried to publish a durable commission over a copied completed
blocking action. The corrected fixture lets actual Workflow publish the
original durable intent and interrupts only at dispatch, before any completed
action. It then checks the valid commission, a changed declaration inside a
rehashed durable spec, a changed selected purpose, and changed receipt
inheritance. The production custody hash is identical in checks 005 and 006.
The failed snapshot has not been rewritten. The broader suite was not rerun.

The authoritative check005 JUnit counts are: existing custody 83 passed;
new compact custody 26 passed and 4 setup failures; host 8 passed; inputs 27
passed; native monitor 64 passed; shared Workflow monitoring and interrupted
recovery 1 passed. `check005/TEST_SUMMARY.json` retains the exact failure sites.

The new actual Workflow cases use scripted provider choices and the real
packaged Homology preparation operation. They do not invoke a model or submit
BV-BRC work. First-return and redelivery checks forbid current catalog/factory
reconstruction and network access; the saved replay also runs with SQLite
`query_only=ON`. Redelivery leaves record/action/observation counts unchanged.
`EXAMPLE_CHECK003.json` records three actual actions and three observations
across root, launch and API episodes, with zero submission actions. Both
practical child completion flags remain false: successful preparation is
partial execution work, not a completed scientific job or usable handoff.

Negative checks cover conflicting model/action role, assignment, scope, goal,
purpose and submitted form; missing/altered declarations; missing or corrupt
frozen frames, roles and fact sources; a self-consistent forged expansion;
redelivery frame, purpose, delivery identity, requested schema, frozen facts
and returned-value corruption. Existing service-response/monitor fixtures are
explicitly synthetic. No live AppService submission, authenticated service
access or native scientific result is claimed.

## Current workspace comparison

The immutable check005 input closure is unchanged. Comparing those tested pins
with the later workspace found 16 changed source files, including the corrected
new test and other owners' ATAC, literature and return-consumer work. Comparing
check006 found three changed source files: the other session's
`literature_partner_source_fields.py` and workload 480's two corrected legacy
redelivery fixtures. In both comparisons all 5,313 dependency files, 643
standard-library files and the interpreter match. Exact paths and before/current
hashes are retained in each attempt's `workspace_drift.json`; these comparisons
cover pinned files and do not claim that no new workspace files exist.

The root owner inspected the two shared production differences in check005:
`communication.py` adds a literature-rate-observation schema branch, and
`episode_services.py` adds a literature-rate-observation repository accessor.
They do not change this BV-BRC path. Check007 had already launched before that
scope comparison arrived; its original handle was retained and collected.
Path-level drift alone is not evidence of a BV-BRC behavior change.

Both check007 cases passed. Its immutable source, dependency, standard-library
and binary pins were unchanged at collection. A final comparison against the
current workspace found zero changes among all its pinned source, dependency,
standard-library and binary files. All launched handles are terminal and
collected; no further test run is pending.

## Separate downstream findings

Workload 480's broad existing-return comparisons retained the new custody in
both arms, so they cannot establish whether a failure was preexisting custody
behavior. Two constructed legacy redelivery tests omitted the original saved
request/schema and were rejected by the new reader. The real current writer
and retained pre-repair writer both save context and schema. The exact trace
and required fixture shape are in `REDELIVERY_WRITER_TRACE.md`.

Workload 480 corrected those two fixtures without weakening custody. Its
check010 passed three cases: both original full-form redeliveries and a
conflicting original-purpose schema rejected without database mutation. The
other 148 missing-artifact failures in its broad comparison remain unverified
cases. They are neither passing cases nor established production failures.

## Original handles

- check001: `gene-local-job-b60ccedbacec4e56a0c09654fe091652.service`
- check002: `gene-local-job-ed8b5e71dc8e4831a76a355dc6b9936a.service`
- check003: `gene-local-job-3061c9819629403c821a94bc1a7f5012.service`
- check005: `gene-local-job-9f22c72bc609468aa7634c492ec20897.service`
- check006: `gene-local-job-b511e87160f941bbab7c51f75e46ab94.service`
- check007: `gene-local-job-b7ec2060205542d8aacfed2af965c3b3.service`

Each handle is retained at `checkNNN/handle.json`; terminal collection receipts
are at `checkNNN/receipt.json`. Check004 has only preflight evidence.
