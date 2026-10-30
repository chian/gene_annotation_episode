# Direct MinHash requested-fact projection verification

C4c implements `minhash_fact_sources()` and
`project_minhash_facts(qualified_results, *, requested_sources)` in
`gene_annotation_episode/bvbrc_minhash_views.py`, following contract
`docs/TOOL_GRADER_BVBRC_ANALYSIS_BATCH_2026-10-24_003.md`.

This is a supplied-data validator and projection. The host authenticates actual
selected-action, original acquisition, source and frozen grading receipts before
calling it. A syntactically valid `source_ref`, valid numerical relationships or
an input called `qualified_results` cannot establish that authentication. No
store, network, filesystem, parser, calculator, model, runtime, credit or prompt
operation occurs in the projector. The native cells and saved fraction operands
are checked for consistency; saved sheets and components are never regenerated,
modified, recalculated or replaced.

The functions declare and return only the requested families:

| Family | Values and meanings |
| --- | --- |
| `bvbrc_minhash_matches` | Source reference, original zero-based row index, native genome identifier when valid, native reported distance/p-value, shared and compared-union integer hash counts, saved sampled shared-hash fraction, row projection parse status. Duplicates and native order remain intact. |
| `bvbrc_minhash_counts` | One source row with the actual native-array length and saved acquisition parse status. Population size and truncation remain null, including empty arrays and results exceeding requested max hits. |

Distances and p-values retain their native numerical meanings. The shared hash
fraction is a sampled Jaccard quantity, with the compared sampled hash union as
denominator, not genes, bases or search population. No confidence or annotation
probability is created. Missing/invalid parsed cells stay null; measured zero
stays zero. Native count operands with numerator exceeding denominator remain
retained numbers with a partial parse qualification; their fraction stays null.
A zero denominator also leaves the fraction null. C4b supplies no pair metadata,
so this envelope requires null k/length/alphabet/null-model inputs and null
recomputed distance/p-value. Separately metadata-fed C2 calculation is outside
this v1 publication contract.

`source_ref` uses existing `format=reference` and namespace `execution_result`;
the supplied string must have the existing durable `source_` plus 24–64 lowercase
hexadecimal-character shape. This only checks syntax. `genome_id` uses existing
`format=identifier` and namespace `bvbrc_minhash_genome`. Both array schemas pass
the existing controlled communication schema validator when placed in its
required closed parent form. Actual form admission also requires the host's
namespace-specific resolver; other identifier namespaces do not substitute.

## Additive identifier clarification

The controlled communication validator does not impose a global identifier
regular expression; its resolver owns admission. C2 accepts any nonblank native
genome string, whereas the concrete MinHash ID shape already used by C1 is
`[0-9]+\.[0-9]+`. The integration owner explicitly directed reuse of that native
rule with the existing identifier format; no shared communication format changed.

An invalid or missing native genome identifier projects to null, preserving its
original native/sheet value in storage. A malformed identifier with retained
numerical cells gives row `parse_status=partial`; with no numerical cells it
gives `invalid`. Otherwise row status follows source-cell completeness. Count
status remains the original acquisition parse status, so a C2-`ok` native prose
identifier can yield a partial projected row and an `ok` count row. No prose ID
is placed in the typed match output or its genome-identifier resolver registry.
This correction adds qualification without changing C2 or historical artifacts.

## Checked relationships and failures

Validation covers the exact closed C4b envelope, original nine-field assignment,
eight native RPC operands in order, deterministic original-request correlation
ID, method/mode/Workspace-path identity, sheet/component schemas and row counts,
original row indices, raw-row associations and native numerical values. Every
component must agree with its sheet row's ID, index, reported values and count
operands. Its saved fraction must equal the valid operands' ratio, or stay null
when unavailable. No independently sorted lists or genome-ID-only joins occur.
Parser diagnostics, component diagnostics and acquisition parse status must
remain associated with their frozen rows.

All supplied JSON numbers must be finite, including unprojected raw values and
provenance. Booleans in raw malformed cells are preserved as raw data, and their
numeric cells remain null; booleans cannot occupy numeric cells, integer flags
or row indices. Invalid requested families, forged fields, request identities,
source references, row associations, operands, metadata or fractions raise
`ValueError` with a specific code and path. There is no coercion to zero or
repair of a forged saved result.

## Source inspection and evidence limits

Read before implementation: the immutable original objective and all sixteen
principles, AGENTS.md, the permanent tool-grader direction, relevant inventory
row, contracts 001/002/003, complete C2 grader and its tests, the retained native
`Minhash.spec`, C2's numerical/source evidence, the complete controlled
communication validator, C1's actual preparation path, and current C4b service.
The original objective/principles and contract 003 were reread after source
study and again before handoff. The projection changes only its assigned module,
test file and this new verification directory.

`FILLED_EXAMPLES.json` contains eight explicitly synthetic C4b-shaped envelopes
constructed with the actual C1 preparer and C2 parser/calculator, followed by
their requested projections. The first two reuse the retained upstream Mash row
`genome1.fna reads 0.12101 4.48626e-214 41/1000` with an explicitly synthetic
BV-BRC genome-ID association. They are not retained successful BV-BRC responses.

Checkable values include:

- Both input modes: reported distance `0.12101`, p-value `4.48626e-214`, counts
  `41` and `1000`, shared fraction `0.041`.
- Duplicate genome rows with fractions `2/3` and `0`, then a `0/0` row with
  fraction null; all three rows survive and returned count is `3`.
- Missing distance/p-value with valid `2/3` counts retains fraction
  `0.6666666666666666`. Invalid `3/2` operands remain `3` and `2`, fraction null.
- An empty array has returned count `0`, status `ok`, and unknown population and
  truncation. Two malformed rows have returned count `2`, status `invalid`.
- A native prose identifier remains only in storage; projected ID is null and
  row status partial. A count-only request returns no match identifiers or values.

The tests also check exact integers above `2**53`, underflow-qualified native
numeric strings, partial arrays, wrong namespaces, duplicate-row swaps, boolean
numbers, nonfinite values anywhere, forged saved values and missing denominators.
Parser/calculator functions and file/socket/subprocess access are disabled in
the relevant pure-projection tests. Reprojection is deterministic and leaves
the supplied data unchanged.

Run from the repository root:

```sh
.venv/bin/python -m pytest -q tests/test_bvbrc_minhash_views.py
.venv/bin/python verification/tool_graders_bvbrc_minhash_views_2026-10-24/verify_offline.py
```

`TEST_RESULTS.txt` records the actual pytest run; `OFFLINE_VERIFICATION.json`
records example checks and input/source hashes. These establish the pure C4c
interface with synthetic envelopes and retained upstream numerical values.
They do not establish live BV-BRC execution, authenticated source custody,
resource-child selection, replay of a real acquisition or full episode-path
integration. Those are separate C4d responsibilities. No access credentials,
live services, Aurora resources, mutable goal/accounting or prompts were used.
