# Composed assignment transport repair — verification 458

This packet is implementation evidence, not goal authority. The original supplied
attachment has SHA256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
It was read in full; the objective and all sixteen principles were reread
verbatim after source investigation and before implementation, and again before
this report. `GOAL.md` was not read. The agreed implementation and finite replay
boundary are in `CONTRACT.md`.

## Defect and change

The actual retained 451 Cooler `launch_local` selection is valid under its
original domain schema. The old provider conversion expanded its composed
assignment, turning optional `SoftwareBinding.native_runtime` into a required
nullable property while a different `allOf` constraint required the exact
selected software literal without that property. Neither omission nor explicit
null satisfied that generated schema. Agent 451 retained the original failure,
domain validation and null counterexample in its check002/probe001–003 packet.

The existing strict JSON-object assignment transport now also covers rooted
composition and reference schemas. The provider receives a string whose
description retains the exact original assignment schema. The original domain
and semantic validators still admit the decoded object. Values, omissions,
explicit nulls, schema-looking literals, resource allocation and selected software
are retained. No scientific schema, existing fixture, prompt, TASK/STEERING message,
resource choice, credit function, observation or controller rule was changed.

Historical replay recognizes exactly the current and immediately preceding
generation transforms. A saved selected action authenticates the whole decoded
selection. A pending exchange can authenticate its actual old provider schema
and exact response. Frozen-profile schemas compare exactly; a demonstrated
markerless serialization shape permits only unique-string `required` member
permutations at actual schema nodes. Literal data is untouched. Historical
frames, selected actions and raw responses are not rewritten.

An unmarked direct-provider response recorded before admission can lack both
proofs. On replay only, identical old/current selections proceed; differing
selections produce ordinary `original_assignment_transport_unavailable` feedback
without action or observation. Newly recorded direct-provider calls carry a
private generator marker and original-schema digest outside model context.
Fresh direct objects preserve valid explicit nulls. This narrow ambiguity
handling and the additional call/save/custody consumers were explicitly approved
by the parent task.

## Changed files and initial handoff source pins

These are the check008 pins supplied to the frozen 451/459 Workflow reruns.
The later custody correction is recorded separately below; earlier receipts
and snapshots remain unchanged.

| File | SHA256 |
| --- | --- |
| `gene_annotation_episode/runtime.py` | `5792936769bea8c91dcb4a51422f14f5d7bf10c08b22bc52d1a31038837954cf` |
| `gene_annotation_episode/bvbrc_appservice_custody.py` | `7623fc39786db657901d0178b00d9e1cb95879944a2d7eda4fa4d09e1d61bea4` |
| `tests/test_composed_episode_assignment_transport.py` | `9385caee00b6ab31149da43c26246c90bdc0ac941c18a07296cf2e3095c04f67` |

The production edits comprise assignment recognition/generation/decoding, small
pure historical comparison helpers, recorded-exchange validation, the narrow
`DecisionSource.call` and `apply_response` replay handling, and BV-BRC custody's
`_commission` use of the authoritative original selection. Existing tests were
not edited. All other new files are under this verification packet.

Pinned pre-repair sources used for comparison:

| File | SHA256 |
| --- | --- |
| `baseline/runtime.py` | `57f3fff849bc6703fe14f9a2382ea958b0f1f6697394cef9a8dfdff3a10b15ba` |
| `baseline/bvbrc_appservice_custody.py` | `b74e31706bf23b711cc1e2820e0a9951e698f272f828d76c32bc356289453a28` |

## Scope inspected

The investigation followed original call retention, pending exchange generation
and immutable history checks, `next`/`restore`/`apply_response`, action selection,
durable commission creation, execution assignment construction and exact parent
matching, child result/report accounting, and continuation consumers. It also
read the strict parser, schema-node traversal, BV-BRC original-parent custody,
and the local example. The local example exposes only `child` and `schedule`
actions and needed no change. Existing generic tool-argument transport and
scientific validation were preserved.

Read-only retained production inputs were the actual 451 probe001 selected
Cooler action, check002 original model request/schema/context, and check001
completed saved responses/actions, plus agent 457's retained nonnull HIC software
binding. SQLite inputs were opened with `mode=ro`; before/after pins and original
observation counts were checked. No scientific output was fabricated or acquired
by this task.

## Focused result

`check008` passed **56 tests in 52.81 seconds** on the final production pins.
The original unit was
`gene-local-job-4662f848fe6f404ca2abd812385cf27c.service`. Its collected receipt
reports return code 0, terminal and quiescent state, and unchanged source/input
pins.

Coverage includes:

* `anyOf`, `allOf`, `oneOf`, JSON references and anchors; exact omitted, null and
  nonnull values; literal schema-looking data; original domain rejection.
* Malformed, duplicate-key, non-object and nonfinite assignment strings rejected
  by the existing strict parser and ordinary feedback with no action/observation.
* Production `ExecutionEpisodes` launch-to-local action generation/admission,
  original semantic parent constraints, and exact requested typed assignment.
* The actual retained Cooler selection, with absent `native_runtime`, now valid
  for generated transport and exactly restored for original domain validation;
  actual HIC software with a nonnull runtime through the same transport.
* Exact pre-repair generator/decoder comparison; completed real 451 selections;
  pending old exchanges reopened after serialization for both profile modes;
  unchanged frames and response bytes; whole-selection conflict rejection.
* Rejection of missing, extra, duplicate or nonstring required names, modified
  constraints, reordered alternatives, and changed schema-looking literal data.
* Unmarked direct-provider replay ambiguity, new private marker replay, bad or
  unknown marker rejection, and original whole-selection BV-BRC custody.

The pending-exchange fixture records through production exchange storage and
then reopens before admission. Its labelled synthetic completed result is an
engineering operand, not a native measurement. Actual completed 451 histories
are tested separately read-only.

## Resource and receipt discipline

All tests and project-level probes ran through existing `local_jobs` /
`native_lifecycle` under 20 GiB RAM, 4 GiB scratch, zero swap and no wall budget.
Each attempt retained an immutable source snapshot, input/source pins, selected
request, original handle, output and collected receipt. Handles were followed
to completion, without timeout/restart substitution. Administrative runners
import only the existing launch/collection mechanics outside those jobs.

The check008 receipt verifies cgroup memory 21,474,836,480 bytes, swap zero and
runtime `infinity`; observed scratch was 70,393,856 bytes. Scratch is the existing
visible allocated-byte monitor with possible overshoot and a per-file hard limit,
not a filesystem quota. Python/site paths and test-cache locations are explicit
in each `selected_request.json`.

## Retained attempts and consumer regressions

| Attempt | Outcome and interpretation |
| --- | --- |
| check001 | 29 passed, 10 setup errors: new fixture lacked explicit role-credit binding. |
| check002 | 37 passed, 2 failed: new requested-form fixture was empty and correctly rejected. Source pins unchanged; input pins differ because the administrative runner was edited while this attempt was active. |
| check003 | 38 passed, 2 failed: corrected the new fixture's false expectation that valid explicit null must be rejected; pending old required-order issue exposed. |
| check004 | One isolated pending-history diagnostic failed. |
| check005 | 40 passed; source/input pins unchanged. |
| check006 | Two reopened pending-history checks failed, demonstrating exact profile constructor ordering and markerless required-member serialization ordering. Original frames preserved. |
| check007 | 51 passed; source/input pins unchanged. |
| check008 | Final focused suite: 56 passed; source/input pins unchanged. |
| check009 | Collection error before any tests: regression snapshot lacked legacy fixture target sequence files. No production result inferred. |
| baseline001 | Three sampled consumer cases also failed with both pinned pre-repair production files and check010's exact frozen dependencies; source/input pins unchanged. |
| check010 | 169 passed, 38 failed in 1477.61 seconds; terminal/quiescent, source/input pins unchanged. Exact failed-case baseline comparison is separate. |
| baseline002 | All 38 exact check010 failures reproduced on the pinned pre-repair modules in 299.52 seconds; source/input pins unchanged. |
| check011 | 62 passed, one new profile fixture failed because it omitted the actual tool catalog; no production defect inferred. |
| check012 | 62 passed, one new API profile case reached an existing custody message-whitelist incompatibility; retained as a separate integration limit below. |
| check013 | Final expanded focused suite: 63 passed in 171.22 seconds; source/input pins unchanged. |
| check014 | All 83 unchanged BV-BRC custody consumers passed in 416.66 seconds on final production sources; source/input pins unchanged. |

The administrative runner then copied the named legacy target files, native
program fixture and both referenced publications. The native program is a
prerequisite operand; the relevant assignment tests explicitly forbid launching
it. Consumer regression results and baseline comparisons are appended below once
their original handles are collected.

`baseline001` finished with three failures in 40.43 seconds. The unchanged
all-five-assignments roundtrip fixture rejects its `scientific_process` value
under the original host domain at test line 216. Both reference/anchor scientific
tool cases stop before transport construction with
`scientific_tool_resource_kind_required:fixture.inspect`. Thus those sampled
failures exist with the pinned pre-repair runtime/custody too; no passing
regression claim is made for them. `run_baseline.py` substitutes only those two
baseline modules into check010's frozen dependencies before pinning the new
read-only snapshot.

The unchanged check010 consumer files produced these results:

| Consumer | Passed | Failed |
| --- | ---: | ---: |
| `test_episode_assignment_transport.py` | 19 | 3 |
| `test_scientific_process_schema_transport.py` | 0 | 21 |
| `test_runtime.py` | 27 | 8 |
| `test_runtime_decision_exchanges.py` | 24 | 4 |
| `test_contract_information_runtime_059.py` | 16 | 2 |
| `test_bvbrc_appservice_custody.py` | 83 | 0 |

The exact per-case failures and messages are retained in `check010/CASES.json`
and JUnit output. They include resource-kind omissions before schema
construction, 19-versus-21 catalog assumptions, retired categorical scoring,
and runtime-script/domain failures. The initial baseline001 sample established
only its three cases. The subsequent `baseline002` ran precisely all 38 failed
case IDs on pinned pre-repair modules and otherwise identical check010
dependencies: all 38 failed, and all 38 first-line failure categories matched.
`baseline002/COMPARISON.json` retains each comparison. The original unit was
`gene-local-job-9befea56602144faa1540d8a82ca3033.service`; its terminal/quiescent
receipt has unchanged source/input pins. Thus the broader run is not green,
but none of its observed failures is newly introduced by the initial transport
repair. This comparison is not a claim that every repository regression passes.

## Final custody correction

`custody005` concretely reproduced an additional read-only consumer ambiguity
with **3 diagnostic cases passing in 31.11 seconds**, unchanged source/input pins
and original unit `gene-local-job-192859a7a34d4b928f576a4127a7ab8b.service`.
The test executed the exact pinned old `DecisionSource.call`, producing a
provider-valid saved unmarked direct response. Ordinary current runtime replay
refused its changed whole selection. Separately, actual
`Workflow.selected/build` construction reached unsaved BV-BRC custody, which
authenticated the current-null interpretation despite the absent transport
proof. Current marked direct dispatch and recorded old exchange were controls.
All original call bytes remained unchanged; the pending call had zero actions
and observations. No API/native operation ran. The API request uses explicit
empty preparation parameters and explicit start-parameter values, not a claim
of native submission readiness.

Earlier probe receipts remain: custody001 exposed an accidental shared-scope
mutation in the probe; custody002 exposed invalid old expanded-provider operands
and a probe constructor typo; custody003 retained missing provider-required
start fields; custody004 isolated those missing fields. They are diagnostic
attempts, not successful capability evidence. The corrected probe retained all
production validators and actual call/exchange writers.

The parent reviewed the concrete result and required the same transport proof
in custody. The correction factors the existing marker/digest check into one
pure helper shared by runtime and custody. Custody enables the existing
unproven-replay comparison; the same decoder explicitly recognizes a matching
current exchange schema as current proof. Exactly two transforms remain. Whole
saved selections, frames, values, current direct behavior, domain validation,
scientific execution, prompts, credit and continuation are unchanged.

The expanded focused suite adds actual-writer old-direct rejection, current
marked dispatch, old/current exchanges, and bad-marker custody rejection. A
separate actual local-boundary test verifies current full-profile transport
proof and admission.

An additional full-profile BV-BRC control in check012 reached an existing
integration limit after transport proof succeeded: the child message contains
`report_contract_declaration`, but `_commission`'s original allowed-message
fields omit it, yielding `bvbrc_appservice_custody_commission_message_conflict`.
That whitelist is unchanged from the pinned pre-repair source. The failure
receipt is preserved; no message authorization was broadened within this
transport repair. The final regression tests do not assert that this rejection
is desirable. Full-profile BV-BRC message integration remains unverified/limited
by that separate incompatibility, while the actual direct/markerless-exchange
BV-BRC custody controls cover this repair's changed paths.

`check013` passed **63 tests in 171.22 seconds** on the final sources below.
The original unit was
`gene-local-job-cf9023de40604e9a9e0d13f64aac3069.service`. Its collected receipt
reports return code 0, terminal/quiescent state and unchanged input/source pins.
The cgroup retained 20 GiB RAM, zero swap and no wall limit; observed scratch
was 87,298,048 bytes under the same 4 GiB policy described above.

| Final changed source | SHA256 |
| --- | --- |
| `gene_annotation_episode/runtime.py` | `07b9aafe11440a57a3d681abe694f57b8ff2e91191a3850b3bb3781d32fa85bc` |
| `gene_annotation_episode/bvbrc_appservice_custody.py` | `52916a7179d13715664e2dc6e16c8b669fab9e930fd0da0aed5cc1177505e21c` |
| `tests/test_composed_episode_assignment_transport.py` | `a50faa69ddf84d0177dd476852f1baad70b77293a5809164baf4095e4afefc73` |

`FINAL_RUNTIME.diff` and `FINAL_CUSTODY.diff` contain the complete production
diffs against the preserved pre-repair source. No existing regression test was
edited. The final unchanged BV-BRC custody rerun, `check014`, passed **83 tests in
416.66 seconds**, including its shared Workflow/typed-return case. Original unit
`gene-local-job-7eb1c1ad5f7e49ff8fdc383f723eec90.service` is collected and
terminal/quiescent with return code 0 and unchanged source/input pins. It used
the same 20 GiB RAM / 4 GiB scratch / zero-swap / no-wall-limit policy. All 458
handles have been collected; no 458 test or native job remains active.

## Handoff and limits

The initial handoff hashes and 56-case result were sent directly to agents 451
and 459 and the parent. Agent 451 froze those sources for its seven unchanged
complete Cooler Workflow cases in its separate check003. Agent 459 owns the
separate HIC Workflow verification. Their frozen evidence retains its original
source pins; it is not relabelled as the later custody-corrected source. The
final hashes and 63-case result were sent to all three owners too. This packet
does not claim either native Workflow outcome in advance.

No literature grading, annotation-score changes, new episode type, root
scientific tool, autonomous loop, scheduler, gate or policy change was made.
Pre-admission direct responses without transport proof remain a finite replay
limit when old and current selections differ; they receive explicit feedback
rather than an inferred commission. No broad repository-wide test result is
claimed.
