# Packet 410: complete protein Workflow verification

Status: check011 passed all four tests in 5007.26 seconds. This verifies the
selected scripted Workflow on its pinned sources. It does not mark the broad
tool-grader goal complete or change the fixed 112/308 accounting.

This packet owns only `tests/test_protein_structure_workflow_integration.py` and
its fixture, runner and evidence. It changes no production code. The immutable
goal is the attached text with SHA256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The objective and all sixteen design principles were reread after substantive
native/output work and again before final claims. Packet 380/021 with additive
022, 024 and 025, and packet 403/001–004, define the relevant boundaries. Full D1
typed forms use the standard production configuration;
there is no injected compact-profile declaration or literature configuration.

## Selected connected case

Engineering inputs are two synthetic PDB files encoding AGST. Fixed residue
identifiers are `10, 10A, 11, 15`; moving identifiers are `101, 102, 103, 104`. The files are
actual caller-supplied artifacts, not fabricated scientific source records.
The first three CA sites are `(0,0,0)`, `(1,0,0)`, `(0,1,0)` in both structures.
The fourth is `(0,0,1)` fixed and `(2,0,1)` moving. Native extraction returned
both exact StructureSequenceDescriptors through commissioned results children.
A newly commissioned scientific child aligns the received references using the
actual protein `sequence.align` tool. A delegating spy records that 401's real
authorization method authenticates both operands before native preparation.
The resulting actual retained AlignmentDescriptor and residue maps supply the
comparison's correspondence; author numbering is not used as correspondence.

The selected mode is `fit_then_evaluate_ca`. Explicit alignment columns 0–2
form the fit; column 3 alone forms the initial evaluation. Independently, the
identity transform fits the three noncollinear sites. The held-out displacement
is 2 Å, its squared distance is 4 Å², and RMSD is
`sqrt(4 / 1) = 2 Å`. AGST versus AGST has four paired positions and native
BLOSUM62 score `4 + 6 + 4 + 5 = 19`. These expectations are assertions, not
manufactured native results. The parent requests only alignment score, mapped
pair count, fit/evaluation used counts, evaluation SSE and RMSD, with their
original typed units/populations.

A later results child receives the actual saved-sheet descriptor and explicit
new parameters: evaluation over all four mapped pairs and distance threshold
1.5 Å. The fit remains the same, so SSE remains 4 and RMSD becomes
`sqrt(4 / 4) = 1 Å`. The tests verified that the original sheet, original
component baseline and closed observations remained byte/value identical. A delegating dispatch
spy accepts only the existing results worker in saved-sheet mode, with its
unchanged argv and explicit retained sheet/baseline inputs. Original acquisition,
progress observation and parent network entry points are denied during that
phase. This is not a system-wide syscall/network audit of subprocesses.

The real Workflow, shared method_loop, ExecutionServiceFactory, ExecutionEpisodes,
native launch/capture/preparation/publication and real 406/407/397/398 ports are
used. No root scientific execution tool, positive injected authority, extra
parser/model turn, replacement resource or production monitoring itinerary is
introduced. The test driver explicitly waits for already selected native work;
it is not an autonomous monitor. Scripted scientific choices and finite test
continuation horizons are fixture inputs. Practical roles retain the actual
estimator/controller path: one own action/observation and exact-zero expectation
at validated completion, retaining the final gain. Original operational units
are 7 for local usable handoff, 3 for launch receipt, 2 for original acquisition;
saved recalculation supplies no repeated acquisition credit. An earlier actual
scientific sibling supplies the relevant frozen-receipt negative boundary.

## Reproduction and retained attempts

From repository root, use:

```text
.venv/bin/python -B verification/tool_graders_protein_structure_workflow_2026-10-27_410/run_bounded.py CHECK_NAME
```

The successful original command was the same prefix with `check011`. The
runner creates a new directory and rejects an existing check name, preserving
earlier attempts. Its exact expanded argv and environment are in
[check011/selected_request.json](check011/selected_request.json).

The runner executes only this packet's pytest module through existing
`local_jobs`, with caller-owned 20 GiB RAM, 4 GiB scratch, zero swap and no wall
allocation. Executed sources are pinned and chmod read-only. Each run retains
the exact argv/environment/policy, stdout, stderr, junit where applicable,
before/after executed pins, checkout drift, and the enforcement receipt. Native
work and its outputs remain under that run's pytest directory. Checkout drift
is reported separately from immutable executed-source equality.

| Attempt | Selected work | Observed result |
| --- | --- | --- |
| check001 | Full module | Four setup errors before native work: fixture put bare artifacts in generic scientific evidence_refs. Fixed by retaining caller receipt and putting the explicit structure requests in the original assignment context; generic evidence refs identify the supplied sequence. |
| check002 | Full module | Four setup errors before native work: earlier sibling used an empty requested form. It now requests its actual credit snapshot. |
| check003 | Full module | Four setup errors after actual first native extraction and valid launch_local/launch receipts. Selected results collection returned invalid_schema. Duration 272.59 seconds. Executed sources unchanged; one checkout test-file drift while the immutable snapshot ran. |
| check004 | Bounded retained-state diagnostic | Diagnostic constructor omitted required log_roles; retained failure, corrected. No native work dispatched. |
| check005 | Bounded retained-state diagnostic | Catalog, target, selector, 397 context, 406 assignment and selected-action intent all accepted the actual copied check003 state. No native work dispatched. |
| check006 | Bounded retained-state diagnostic | Exact rejection reproduced in 406 `_decode`: existing shared assignment.json is canonical JSON plus one LF, while the new receipt reader required canonical bytes without LF. All preceding checks passed. No native work dispatched. |
| check007 | Full module with corrected 406 shared envelope | Actual first extraction, capture and existing result worker succeeded; results collection completed with credit 2. Required full D1 descriptor then failed the real parent report audit filter with audit_identity. Duration 306.83 seconds. Executed sources unchanged. |
| check008 | Bounded actual-report diagnostic | Diagnostic's copied Store path conflicted with 406's original worker-input path identity. This was a diagnostic relocation error, not a new production defect. No native work dispatched. |
| check009 | Bounded actual-report diagnostic | Actual full D1 runtime form passed schema/reference validation and actual host semantic validation, then failed runtime.TypedReportContract's generic admission call. method_loop.ParentReport.exclude_audit_identifiers rejected required custody.result_episode_id and the operation key containing the same current child ID. Original descriptor was unchanged. No native work dispatched. |
| check010 | Same actual-report diagnostic after root 414 repair | All checks including typed report admission accepted the actual retained native descriptor. Returncode 0, executed pins unchanged and no checkout drift. No native work dispatched; this is not a complete Workflow pass. |
| check011 | Full module after the shared repairs | Four tests passed in 5007.26 seconds; returncode 0. All 888 executed source pins unchanged. One checkout file drift is identified below. Actual complete selected native and typed communication path, saved recalculation, practical histories and earlier-sibling denial passed. |

For diagnostics the exact command suffix was `check004 --diagnose check003`,
then `check005 --diagnose check003`, then `check006 --diagnose check003` with
the same runner prefix. The original check003 Store/run was not modified.
Each diagnostic used a separate Store copy under its own bounded run directory.
Root assigned the narrowly scoped shared assignment-envelope correction to 406;
this packet does not alter a production parser or shared serialization.

406 subsequently supplied receipt source
`941ffebd2fbf91db8b92e8c14b742c3456b7d31e1059313dff0df876ce0114fc`;
its separate actual-shared-writer regression passed 9 checks. Check007 uses that
source and establishes that the collection failure is repaired in the actual
Workflow. At that point, parent receipt, alignment and comparison were still
unverified. The later admission failure was a distinct root-owned shared boundary. The exact
minimal reproduction is retained in check009/diagnostic.json and stderr.txt;
it uses the original D1 schema, original saved form, actual reference resolver
and actual `ExecutionEpisodes.validate_report` semantic validator. Its copied
database is query-only; artifact reads keep the original retained root so native
input-location proof is not changed. Run with the usual runner prefix and
`check009 --diagnose-report check007` (or a fresh check name). Check008 and
check010 used the same `--diagnose-report check007` suffix with their respective
check names. Earlier failed diagnostics remain preserved.

The narrow root 414 correction is recorded in 380/025. Check010 pins runtime
`57f3fff849bc6703fe14f9a2382ea958b0f1f6697394cef9a8dfdff3a10b15ba`
and the new domain report boundary
`27e5fe4783dbb4bde43f9f8fc946e4b5618031270e4a0ac9f03b7e67c3f5a7ea`.
Its exception covers authenticated internal custody only; the ordinary audit
filter over declared model inputs remains strict. Check011 is the new complete
Workflow run after root's focused correction checks. It retains its original
immutable source snapshot while later owner work continues in the checkout.

## Check011 result and measured example

All four tests passed. Both extraction descriptors crossed the actual D1
report-admission boundary.
The subsequently commissioned scientific child ran the real protein alignment:
native score 19 and four paired positions. Its comparison request retained that
alignment and the actual two residue maps. The comparison results child
delivered the requested numerical projection and saved-sheet descriptor back
to that scientific child before the saved recalculation was commissioned.

The original retained comparison components have evaluation SSE
`3.9999999999999964 Å²` and RMSD `1.9999999999999991 Å` over one held-out pair.
The actual saved results action subsequently published SSE
`3.9999999999999964 Å²` and RMSD `0.9999999999999996 Å` over all four pairs.
Both retain native alignment score 19, mapped count 4 and fit count 3. The exact
six requested numerical fields reached the original receiving scientific
episode, its coordinator, and the root. No additional field was substituted
for the selected comparison projection.

| Requested numerical field | Original held-out evaluation | Saved evaluation over all pairs |
| --- | ---: | ---: |
| Native alignment score | 19 | 19 |
| Mapped pair count | 4 | 4 |
| Fit used count | 3 | 3 |
| Evaluation used count | 1 | 4 |
| Evaluation SSE, Å² | 3.9999999999999964 | 3.9999999999999964 |
| Evaluation RMSD, Å | 1.9999999999999991 | 0.9999999999999996 |
| RMSD population denominator | 1 | 4 |

The denominator is preserved typed population metadata, not an extra requested
numerical field. The original native alignment has four paired positions.
Both protected operands were authenticated by the real method before native
alignment preparation. The retained native alignment, residue maps, sheet and
original component baseline were inspected by the passing test.

There are 14 episodes, 22 scripted decision records, 22 completed own actions
and 22 durable observations. All 10 operational episodes have exactly one
action/observation and the real `verified_practical_endpoint_yield_v1`
provenance, with future expected gain equal to exact zero. Final local histories
are `[7]` three times, launch histories `[3]` three times, and results histories
`[2], [2], [2], [0]`. The root retains `[0, 0]` under the explicitly labeled
scientific test horizon. Its runtime state is `yielded`; this is not a claim
that a scientific annotation goal is complete. No annotation was created.

The saved calculation dispatched exactly one existing results worker. Three
original producer plans and their three attempt copies remained unchanged;
the one native sequence alignment was not repeated. The original sheet,
baseline, original authority and already closed observations remained unchanged.
The earlier actual sibling could not use either later sequence descriptor or
its protected reference. Only the scientific receiver could use the saved-sheet
descriptor; the earlier sibling, coordinator and root were denied.

The passing tests, with pytest-reported times including applicable fixture work:

| Test | Seconds |
| --- | ---: |
| Full native alignment/comparison and exact requested return | 4470.227 |
| Received saved-sheet recalculation | 4.874 |
| Practical completion and durable observations | 135.953 |
| Later receipt cannot authorize an earlier sibling | 395.153 |

The [junit result](check011/junit.xml) records 4 tests, 0 errors, 0 failures and
0 skips. [stdout](check011/stdout.txt) records the four passes;
[stderr](check011/stderr.txt) is empty. The enclosing bounded service measured
5008.325386836 seconds, separately from pytest's 5007.257 seconds.

The original comparison producer's completed observation measured
`4.070881438 s` of service wall time with native returncode 0. Its earlier
usable-handoff snapshot's `1.163405508 s` remains an earlier running observation,
not a completed duration. The original comparison results worker measured
`1.780104081 s`; the saved worker measured `1.374301786 s`. The enclosing
original collect action measured `26.620042969 s`. These have different
boundaries; service wall time is not pure numerical computation time.
Overall Workflow time also contains typed communication, authority checks,
fixture preparation and final assertions. A later profiling plan must measure
those paths separately rather than assign the elapsed time to an assumed cause.

## Source integrity, enforcement and handoff

[The enforcement receipt](check011/receipt.json) records returncode 0,
`memory_max=21474836480`, `memory_swap_max=0`, `runtime_max=infinity`, and
observed scratch of 182140928 bytes. Scratch enforcement is the existing
monitored visible-allocation mechanism with a hard per-file limit; no stronger
filesystem isolation is claimed.

The executed snapshot is
`check011/source_snapshot`. All 888 entries in
[source_pins_before.json](check011/source_pins_before.json) match
[source_pins_after.json](check011/source_pins_after.json). Key executed pins:

| File | SHA256 |
| --- | --- |
| execution_episodes.py | `e87d13a0f697d2ca33cebf7b9bbb2851a776936b72554311f0fd1a215d768016` |
| runtime.py | `57f3fff849bc6703fe14f9a2382ea958b0f1f6697394cef9a8dfdff3a10b15ba` |
| protein_structure_report_boundary.py | `27e5fe4783dbb4bde43f9f8fc946e4b5618031270e4a0ac9f03b7e67c3f5a7ea` |
| protein_structure_result_receipts.py | `941ffebd2fbf91db8b92e8c14b742c3456b7d31e1059313dff0df876ce0114fc` |
| native_protein_structure_results.py | `04dda1eadd6d9a3cffa2691dc8bfc1ebc0f85d62fda4e1cacc2079718ffa7338` |
| native_protein_structure_contracts.py | `13e1f7c4e9e60fed6283ab66aea03dd3b54de4767941d6509f496c2188cdaea0` |
| test_protein_structure_workflow_integration.py | `33487d7fe8a0760f9dc26defa1801d413ad96b5b339ecaa21ce26226ecbb1943` |
| fixture_helpers.py | `6405670c166657c0ae2bceb628fc2d4f430eef824a3e7c9526a55c3266207863` |
| run_bounded.py | `ccf4fce8fa2f4a117d7fc89f739199d231926f31da7983e39d7e50cf211a6723` |

One tracked checkout file changed while this immutable snapshot ran:
`gene_annotation_episode/native_protein_structure_contracts.py`, to SHA256
`44e7308e77e0e6fdcc25cdf4bfa1448037150875c40284ae13ecfe668fc81774`.
Check011 verifies the executed `13e1...` source, not that later checkout source.
The full before/after checkout comparison remains in the receipt and
[checkout_source_pins_after.json](check011/checkout_source_pins_after.json).

Exact retained locations relative to this packet:

- [CASE.json](check011/temporary/pytest/protein-workflow4100/CASE.json): actual native plans, alignment descriptor/outcome, typed returned/forwarded forms and controller states.
- [SAVED_CHECK.json](check011/temporary/pytest/protein-workflow4100/SAVED_CHECK.json): actual authentication/dispatch evidence, original received descriptor and producer plan paths.
- [ROOT_RECEIVED_CONTEXT_FIXTURE.json](ROOT_RECEIVED_CONTEXT_FIXTURE.json): read-only index into the completed root's actual database/run records, with its exact direct-child summary and the passing real-port assertion. It is not an authority provider, and no new runtime diagnostic was executed to construct it.
- [MEASURED_EXAMPLE.json](MEASURED_EXAMPLE.json): numerical values, timing scopes, source-integrity result, resource receipt and durable-history summary extracted from those retained files.
- `check011/temporary/pytest/protein-workflow4100/state/state.sqlite3`: actual completed Store; preserve original artifact-root paths when copying the database for query-only diagnostics.
- `check011/temporary/pytest/protein-workflow4100/run`: actual commissions, returns, results receipts and archived histories.

The exact root identity is
`episode_9f8c84a8e91a97238b0633be20fd2fd6a7631cb3911e1d90ba6295d8aff8fdbe`.
The real `received_context` assertion is at test line 147; the complete Workflow
constructor is at fixture helper line 164. The index preserves the actual root
row and points to `native_protein_structure_returns.context(root_episode_id)`
for reconstruction through the real port. The full `received_context` output
was not separately serialized; the passing test checked its exact summary list
against the actual direct-child return retained in CASE.json.

[PROFILING_PLAN.md](PROFILING_PLAN.md) proposes four bounded, read-only diagnostic
invocations against this completed evidence. Root will assign any follow-up
with fresh context and current 417 sources. Packet 410 did not execute profiling
or rerun standalone native science.

## Limits

These are synthetic structures with actual local native execution and scripted
episode choices. No configured LLM investigation, autonomous monitoring, external
data acquisition, clinical/biological validation, Aurora deployment, literature
grading or W05/final annotation scoring is established. This packet does not
duplicate the separate 397/398 permission matrix or broaden historical suites.
The helper's optional same-file and reverse-orientation inputs were not exercised
by this four-test case. The fixed 112/308 accounting is unchanged. No production
file, permanent direction record, inventory or accounting file was edited by
this packet. Later source optimization and model-facing TASK/STEERING work
remain separate from this verified snapshot.
