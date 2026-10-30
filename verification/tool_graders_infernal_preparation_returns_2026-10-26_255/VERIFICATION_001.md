# Infernal preparation returns — workload 255

Implemented only `gene_annotation_episode/native_infernal_preparation_returns.py`,
its matching test module, and this verification directory. Root owns production
results/runtime integration. The governing contracts are 247/T1, R1–R5 and P2.
R5 supersedes T1/R3's per-action population wording: exact same-source facts may
deduplicate; distinct original source associations remain distinct.

The immutable user goal was read completely and its objective and all sixteen
design principles reread verbatim after source/native study and before this
handoff, followed by current T1/R1–R5/P2. Its verified SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
AGENTS, GOAL, episode structure, estimation, task/steering, practical execution,
the original practical contract, the tool-grader principles and the relevant
fixed inventory rows were read. Existing return, reference-frame, communication,
Store, receipt/journal, runtime and execution consumers were inspected.

## Behavior

The reader authenticates actual runtime identities, the immediate-parent
commission and requested form, scope containment, original results assignment,
saved facts, original admitted form and redelivery request. Preparation rows,
artifacts, populations and reference forms retain their separate meanings.
Generic execution-result forms are handled only for the actual preparation
results owner; unrelated providers retain their own handling.

Only facts explicitly returned across each immediate-child form are forwarded.
Source/artifact possession, inherited receipts or a sibling's result cannot
expose numerical rows, native names, accessions, missing-key diagnostics or
artifact digests. Sources resolve only as source records and artifacts only as
artifact records. Numerical-row check occurrences preserve every returned file
association. Missing keys authenticate a returned absence diagnostic and do not
become present rows. Digests authenticate only from returned artifact rows.

Repeated forms add no repeated facts. Equal counts or bytes from distinct
original sources preserve those associations. Frozen scientific returns remain
their original authenticated subsets when later descendants deliver additional
facts. Only the existing synchronous form-validation frame caches a snapshot;
source mutations are checked on the next form validation.

There is no new journal, observation, scientific record, credit, scheduler,
controller, episode type, network request, native execution or recalculation.
The receiver does not call the result port's `read_result`, `result_identity` or
own-result resolver to expand received knowledge.

## Executed verification

`boundary_003`: **54 passed in 178.49 seconds**, exit 0. The runner used the
existing `local_jobs` lifecycle, `.venv/bin/python`,
`PYTHONDONTWRITEBYTECODE=1`, 20 GiB RAM, 4 GiB scratch and no wall-time cap.
The recorded systemd service-wall measurement is 179.191621789 seconds;
observed scratch was 20,144,128 bytes. Original logs, JUnit output, source hashes,
native artifact hashes and resource evidence are retained with `receipt.json`.

The tests use real Store, Journal, EpisodeReceipts, BindingContext,
TypedReportContract and saved runtime tables, plus an explicitly supplied
completed-results port. Its retained native artifact bytes are digest/size
checked, rebound to real Store artifact IDs and selected by the real 253 pure
projector. The test port is distinct from production acquisition/publication.
Production Workflow execution and native launch-to-return integration remain
root's verification responsibility.

| Retained example | Verified returned facts |
| --- | --- |
| 250 prior consensus emission / 246 native bytes | 12 generated residues; GC count 8; canonical denominator 12; GC fraction 2/3. Missing/inapplicable model-row components remain null. |
| 248 pressed-model sheet / 219 native quartet | Repeated original validation checks keep i1m, i1i, i1f and i1p occurrence associations, including aggregate rows without a single artifact attribution. |
| 248 binary-conversion sheet / 246 native bytes | Binary artifact 7,166 bytes; empty stdout and stderr remain separate role associations sharing the same actual artifact; unavailable decoded-model count stays null. |

Additional cases cover every forwarded source, reference-only forms, parent and
child scope containment, missing diagnostic keys, scientific/grandchild
forwarding, frozen subsets, same/distinct-source populations, duplicate
redelivery without an action, wrong result owner, changed original commissions,
missing completed actions, changed source records, forged quantities/checks/
associations/digests, altered forms/schemas and cache expiration. All tests assert
zero scientific observations and zero runtime observations; receiving calls
leave the database unchanged. Native programs, acquisition, parsers, calculators
and networking are forbidden during the suite; reprojecting is separately
forbidden during the native-derived return checks.

Earlier attempts remain preserved: `boundary_001` found a fixture-only immutable
scope copying error (53 failed, 1 passed); `boundary_002` found a test assertion
selecting the model row's unavailable quantity instead of the generated sequence
row (1 failed). Both fixtures were corrected before `boundary_003`; the final
54-test run passed in full. These earlier runs are not additional passing coverage.

## Exact handoff identities

| File | SHA-256 |
| --- | --- |
| `gene_annotation_episode/native_infernal_preparation_returns.py` | `6aef0c9ed3646fbcf88e41246e1f434f44dd453594aaa2a93769cf4200373387` |
| `tests/test_native_infernal_preparation_returns.py` | `8341aee7e62778b2967dcc29a5bf636bdd0e2dbaf40861687fc1856f13ee21d6` |
| `run_tests.py` | `621811947e335102be79c9de197fdd02fb57e558778159300388fc0d7b2661e0` |
| `boundary_003/receipt.json` | `7ee01d40d8918d00146b39b8f1d76ae10be0949c1469ca8d5c6348d9f0c28531` |
| `boundary_003/tests.xml` | `1e3dcd9f55902ebd33f2329f6ec8ee337f1baf9c14536677f0a5898b488debdf` |

No network, installation or HPC operation was performed. This verification does
not establish new native execution, live-resource deployment or configured-model
scientific investigation.
