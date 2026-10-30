# Direct-protocol receipt-context regression: authorized test repair

This is additive implementation evidence under the original user-supplied goal.
It does not redefine the goal, scoring, prompts, or runtime behavior. Root owns
the runtime repair in packet601 `RECEIVED_CONTEXT_REPAIR_008.md`.

## Evidence and ownership before editing

The saved check061 report has 38 passes and 12 failures. All four actual UniProt
Workflow grant cases passed. The direct regression fails at construction of
`ScientificEvidenceCredit(CreditPolicy())`, before a Workflow exists. The current
`CreditPolicy` explicitly raises `categorical_annotation_scoring_retired_use_original_snapshot_for_historical_replay`.
That file is byte-identical to the check060 snapshot. No retired score will be
restored to make this test run.

The complete changed runtime path was read: direct/exchange decision dispatch,
working-state selection, receipt binding/inheritance/admission, projection
arguments, child commissioning/return admission, completed-action observation,
and run binding. The complete affected test functions and their fixture helpers
were read. The check060/current runtime delta contains exactly the three
scientific-context guard replacements and the new helper. Root tool restrictions
already occur in both versions' catalog, action schema, dispatch and action
validation. Empty reasoning commits are rejected by `apply_response`; they are
therefore not an appropriate zero-gain action for this verification.

Owned edit: only
`test_different_parent_scalar_does_not_grant_unreceived_information_to_child`
in `tests/test_episode_receipts.py`, and its two now-unused retired-scorer imports.
All other test functions, production code, prompts, scoring and progress rows
remain outside this worker's editing boundary.

## Exact test change

Replace the retired parent scorer with an explicitly synthetic zero-credit
function taking exactly `(store, scope)`. Assert that it has no
`requires_episode_receipts` attribute and actually receives those existing two
arguments. Keep `ScientificFindingProgress(FindingProgressPolicy(4))` for the
child; bind `episode_record_receipts=True`, `initial_known_record_refs=[]` and
the direct protocol explicitly.

The root's only selected action remains commissioning its scientific child. The
child's only selected action remains its currently legal `episode.credit`
inspection. No tool executes at the restricted annotation root, no finding is
injected as caller knowledge, and no new scientific measurement is fabricated.

Before commissioning and at the child's first decision, require zero credit,
the received-immutable-record view, no assessment, and absence of the stored
finding from visible references. After closure require: both initial credits
are zero; each episode has exactly one own observation and zero gain; the parent
receives exactly `local_progress: 0`; no assessment receipt or `decision_input`
receipt was manufactured; neither current nor baseline known assessment
selection contains the stored finding; the original finding remains unchanged;
and the saved settings still contain an empty caller-known record list.

## Twelve failures: source-grounded initial classification

The following causes are tied to saved failure reports and full test source.
The bounded read-only collector will retain the corresponding saved DB rows
before these are reported as fully confirmed. This table is not a claim that
the old tests were executed against check060.

| check061 case | Observed failure and smallest legitimate repair to propose |
| --- | --- |
| requested child information, False | Script exhausted after parent selects root `episode.credit`; preserve child receipt/replay checks and use a legal parent action or inspect projection directly after the child. |
| requested child information, True | Same selected root tool in the standard-binding variant; preserve distinct binding coverage. |
| native workbook pages | Child native extraction/interpretation completes; parent then selects root `episode.credit`. Preserve the saved workbook work; inspect the existing projector directly or through a permitted child, without rerunning the original native analysis just to classify this failure. |
| selected state read, False | Root `state.query` is rejected; next callback incorrectly expects received credit 5. Define whether this should verify root rejection or a permitted child's actual acquisition. Do not restore a root/global discovery tool. |
| selected state read, True | Same root restriction for exact-reference mode; retain this separate selector case in any approved repair. |
| different parent scalar | Retired `CreditPolicy()` constructor blocks runtime. Repair only as specified above. |
| form repair/interruption, False | Child work and redelivery survive; resumed parent selects root `episode.credit`, exhausting the script. Preserve zero-observation redelivery and original gain assertions; use a legal completed parent action. |
| form repair/interruption, True | Same selected root tool after the alternative interruption boundary; preserve both recovery boundaries. |
| multiple context exchanges | Root selects `sequence.inspect`, absent from its allowed actions. Keep lookup/one-action accounting by using legal reasoning or a genuinely non-root tool-owning episode. |
| own input detail requests | First root `fixture.measure` selection is rejected. Preserve exact selected-input lookup using legal reasoning input, or move tool-specific coverage to a tool-owning child. |
| lookup-visible publications | First root `fixture.measure` selection is rejected, so the expected published reference cannot exist. Exercise publication lookup through a permitted child/own-action path; keep original raw-context immutability assertions. |
| injected legacy/markerless resume | The test expects `episode.history` in the new annotation root's empty tool catalog and initially selects a root fixture tool. Protocol-marker absence is separate from the root-action boundary marker. Use legal work and test actual protocol preservation; do not re-enable historical root tools. |

## Bounded verification

Use the existing packet529 runner and check005 dependency closure, with the
unique attempt `check062_received_context_direct`. Run this one repaired test
and a packet611-owned collector that opens frozen copies of all twelve failed
check061 databases read-only and exports the relevant saved rows. The collector
does not import the application or rerun any historical analysis. All DB reads,
application imports and tests occur inside the existing 20 GiB memory / 4 GiB
scratch / zero swap / no wall-cap runner. Host work is stdlib source/AST/JSON,
hashing and staging only. Preserve original check061 files and verify hashes.

Completion of this assignment means this direct regression is actually verified
and the other eleven failures are precisely classified with proposed repairs.
It does not establish broad regression repair, live-model science, or completion
of the original tool-grader goal.
