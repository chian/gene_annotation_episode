# CodonTree native numeric and artifact corrections

Fresh workload `codon_native_numeric_correction_125`, 2026-10-24. Both assigned
review corrections are implemented in the existing staged reader and its test:

- `../staging/gene_annotation_episode/bvbrc_codon_tree_native.py`
- `../staging/tests/test_bvbrc_codon_tree_native.py`

All new evidence is confined to this additive directory. The 19 files under
`../codon-native-verification/` were checked against their baseline identities
and remain unchanged. No production file, shared module, provider wrapper,
calculator, formula, prompt, episode path, resource binding or status row was
edited. No subagent, upstream program, scientific service or model was invoked.

The complete immutable goal, local AGENTS.md, tool-grader principles, current
native contract and previous handoff were read. The objective and all sixteen
design principles were reread verbatim after inspecting the relevant complete
producer paths, and again after verification before writing this handoff; each
reset was followed by the exact current native-table contract. The unchanged
goal SHA256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`;
contract SHA256 is
`c6021e7c0d5870efd2a0da0af11c9e83f7869ae2b4ae20d8e5bf7f6da36b4ee4`.

## Corrections and receiving contract

Native floating observations now call the existing pure
`phylogeny_format_contracts._native_number` after their existing strict token
syntax check. A nonzero decimal that underflows to floating zero, such as
`1e-999`, becomes `value=null,state=failed` with its unchanged `raw_token`, byte
location and `codon_native_number_invalid` diagnostic. Explicit signed zero,
finite negative values and representable nonzero subnormals stay available.
Count parsing and numerical meanings are unchanged.

The restricted Python scalar-map reader validates a float constant's original
source segment through the same helper before applying its permitted unary
sign. It does not trust the AST's already rounded zero. Underflowed maps retain
the complete raw qualifier and receive `codon_bad_sequence_map_invalid`; they
produce no fabricated scalar values. Independent family observations and later
valid maps survive. Existing AST restrictions, duplicate-key detection and exact
integer handling remain; calls, nested objects and numeric expressions are not
executed. Explicit integer and floating `+0`/`-0` remain valid.

All four readers now reuse the shared pure `_artifact` validator and compare the
digest exactly. The supplied three-field ArtifactRef therefore uses canonical
lowercase hexadecimal, matching the downstream stored-format contract. Uppercase
and malformed hashes return `invalid`, `value=null`,
`codon_artifact_invalid` in phase `association`. Caller metadata is never
normalized or mutated. Valid-shaped wrong digests still produce
`codon_hash_mismatch` before decoding.

This adds a dependency on the existing pure `phylogeny_format_contracts` module;
the prior handoff's statement that the reader has no shared-module import is a
historical statement about its previous code. The shared module was read fully
and was not edited.

Public signatures, ReadResult/value shapes, source identities, native units,
population IDs, table IDs and failure vocabulary are unchanged. The receiving
provider remains `extract_codon_tree_sheet` with the precise input envelope in
`NATIVE_METADATA_CONTRACT.md`. No provider implementation was present among this
reader's current call sites: its existing consumers were tests and the prior
evidence exporter, which were inspected completely. This work does not claim
provider or episode integration.

## Verification and numerical examples

All test runs used the absolute repository interpreter, staging cwd and staging
PYTHONPATH, with assertions on actual reader/shared-module import paths:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging /home/chia/repos/gene_annotation_episode/.venv/bin/python ../codon-native-numeric-correction-125/run_verification.py corrected-159 --tb=short
```

| Run | Passed | Failed | Result |
| --- | ---: | ---: | --- |
| Original unchanged baseline | 101 | 0 | Previous suite reproduced before edits. |
| Expanded checks before reader correction | 138 | 21 | Six observation-underflow, nine scalar-map-underflow and six hash-contract failures exposed. |
| Corrected reader | 159 | 0 | All 101 prior test nodes retained, plus 58 new cases. |

The final run took 0.351 seconds according to JUnit. Four of the 21 exposed
failures are original test cases whose uppercase-hash acceptance expectation
was corrected; 17 belong to new cases. The prior workload's historical initial
97-test run with three failed truncation/digest assertions remains separately
recorded, along with its later passing reports. It is not counted as a failure
of this correction run.

One ancillary exporter attempt failed because a reused test helper assumed the
fixture artifact ID `raw/codon-native`, while the new export intentionally used
its own ID. The exporter was corrected to validate the actual supplied identity
and byte spans directly. No reader or test change was needed, and no exported
artifact had been written before that assertion. The failure is retained in
`exporter-initial-failure.json`; the corrected exporter completed successfully.

The new retained example uses synthetic numeric boundary tokens within the
source-derived family-table syntax; it is not a live CodonTree measurement:

| Native token/context | Retained value | State/result |
| --- | ---: | --- |
| Floating observation `1e-999` | null | failed; original token retained |
| Floating observation `-0e-999` | -0.0 | available |
| Floating observation `na` | null | missing |
| Floating observation `5e-324` | 5e-324 | available |
| Floating observation `-2.5` | -2.5 | available |
| Scalar map containing `-1e-999` | no typed map values | raw qualifier retained with diagnostic |
| Scalar map `-0.000e-999`, `5e-324`, `+9.5` | -0.0, 5e-324, 9.5 | valid values retained in source order |

Tests also preserve exact integers above floating precision/range, check original
Unicode byte locations, malformed numeric syntax, injection/duplicate-key
rejection, immutable inputs, closed shapes and JSON output. The supplied-byte
purity test includes the new boundary cases and all four invalid-hash paths with
file, socket/network, subprocess, shell and builtin eval operations disabled.

All five previous populated examples were reparsed and matched their saved
outputs exactly. The actual historical membership remains 20 typed rows and
30 physical rows; the four current-writer fixtures remain source-derived.

`VALIDATION.json` contains actual run counts, failure identities, preserved prior
receipts and numerical examples. `SOURCE_AND_CODE_HASHES.json` records the full
source/contract/code identities. Final reader SHA256:
`3f83d5c0268b8efa43c593a873cebe212f6acaf0f4626f064c14272f70d86340`.
Final test SHA256:
`ff708a1c2a7587d12d4ad4d03a5a69c7bf39b6339c8a72ef43f32541db43311e`.

Current live CodonTree output, provider sheet assembly/calculation, C4 dispatch,
selected child execution, task/artifact custody and typed episode return paths
remain outside this correction and unverified here. These parser corrections
do not establish completion of fixed row C-L193-CodonTree.
