# MinHash workload A implementation handoff

Implemented the bounded supplied-metadata contract and common fraction authority.
This is static-only coding evidence, not completion of MinHash integration or
live-resource verification. No application/scientific imports, test collection,
test execution, scientific native commands, network calls or independent jobs
were run in this workload. One attempted host `python` read failed because that
executable was unavailable; subsequent host file/AST work used `python3`.

## Owned files and ports

- `gene_annotation_episode/bvbrc_minhash_contracts.py`: new pure
  `minhash_result_selector_schema()`, `validate_minhash_result_selector(value)`,
  `validate_minhash_pair_metadata(value, *, request)`, and
  `validate_minhash_publication_inputs(value, *, request, selector)`.
- `gene_annotation_episode/bvbrc_minhash_grader.py`: the existing calculator now
  calls `calculate_minhash_shared_hash_fraction(shared_hashes,
  compared_union_hashes, *, row_identity_available: bool) -> float | None`;
  `MINHASH_DIAGNOSTIC_CODES` contains the 52 existing parser/calculator codes.
- `tests/test_bvbrc_minhash_contracts.py`: 25 authored test functions, many
  parametrized. `tests/test_bvbrc_minhash_grader.py`: six authored additions,
  31 total functions, plus an exact 2/3 assertion in the existing example.

No service, host, views, execution, prompts, instruction library, TASK/STEERING,
literature, W05 or inventory files were edited by this workload.

## Boundary behavior

Legacy selector `{}` remains valid. V2 selectors and publication envelopes use
exact closed fields and preserve list order and duplicate pair candidates.
Metadata values are explicit positive non-boolean integers or null. Each nonnull
field has one evidence entry; null has none. JSON pointers remain unresolved.
Only `native_parameter_equivalence=unestablished` is accepted. Query mode and
operand must equal the supplied complete service request, not an RPC envelope.
The existing service remains authoritative for native invocation validation.

Each publication binding identifies the original metadata-list occurrence by
`pair_metadata_index`, matches its field/value/source/artifact/pointer exactly,
and preserves the content-addressed reference/digest relationship. Saved mode
retains the original source/artifact references, common sheet/components names,
and checks original request mode/all eight operands and outer row associations.
The host still must authenticate actual received sources, bytes, pointers and
complete saved contents. A structurally accepted envelope is no proof of custody.

Stable errors are `minhash_result_selector_invalid`,
`minhash_pair_metadata_invalid`, `minhash_metadata_query_conflict`, and
`minhash_publication_inputs_conflict`. All validators return detached copies.
They import only standard-library copy/math/re and invoke no parser/calculator.

The shared fraction helper returns the original Python division only for exact
True identity, integer counts with 0 <= shared <= union, and a positive union.
The full calculator retains the original diagnostic branches and calls its
existing internal `parse_minhash_result` saved-data validation. AST comparison
confirmed that all other existing grader functions, including parsing, distance
and binomial-tail calculations, are unchanged. The common
`bvbrc_minhash_sheet_v1` and `bvbrc_minhash_components_v1` remain unchanged.

## Verification prepared, not executed

Root test selectors: `tests/test_bvbrc_minhash_contracts.py` and
`tests/test_bvbrc_minhash_grader.py`, in the root-owned frozen
native_lifecycle/local_jobs environment under 20 GiB RAM, 4 GiB scratch,
zero-swap and no invented wall-time cap.

Authored assertions cover full/null/k-only metadata; exact query association;
closed fields; no coercion; duplicate candidates; per-field evidence and exact
list-index bindings; malformed envelopes; saved-mode copied associations;
exact 2/3; zero/invalid counts and absent identity; retained fraction rounding
and underflow diagnostics; and the existing scientific values. Expected example
values are fraction 2/3, distance 0.22314355131420976 and p-value
0.2592592592592592; the existing saved k=2 test retains distance
0.11157177565710488 and p-value 0.10400000000000001. These are assertions and
historical expectations, not newly executed measurements.

Host-standard-library AST parsing passed for all four owned source/test files.
Static comparison found only the intended common-helper call among pre-existing
grader function ASTs. AST inspection also confirmed the finite diagnostic
collection exactly matches the 52 actual issue-code literals. No runtime pass
count is claimed.

## Inspection and retained evidence

Read the full supplied original attachment, actual AGENTS.md, finalized boundary
CONTRACT.md and ROOT_INTERFACE_CLARIFICATION_001.md; read the complete grader,
grader tests, service, host and projector; inspected the relevant inventory row
and the complete domain schema validation/construction functions. The original
objective and all ten operating principles were reread from the attachment after
tool/source work. No GOAL.md or repository goal/scope-amendment file was used.

`before/` and `BEFORE_MANIFEST.json` retain the two original edited files and
record that the two new files were absent. `CHANGES.diff`,
`SOURCE_MANIFEST.json` and `STATIC_REVIEW.json` retain exact changes, source
hashes, port locations and the limited verification status.

No unresolved pure-port mismatch was identified by static inspection. Still
pending outside A: root runtime verification; service/host custody and publication
binding; projector consumption of the shared helper and requested V2 returns;
full selected episode/saved/replay verification; feedback-dependent instruction
presentation; and live service/index parameter-equivalence evidence. This
handoff does not mark the wider MinHash boundary or goal complete.
