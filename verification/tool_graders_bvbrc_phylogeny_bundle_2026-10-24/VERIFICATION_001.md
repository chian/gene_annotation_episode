# Pure BV-BRC phylogeny bundle adapter verification

Recorded 2026-10-25. This report covers only the five new production modules,
three tests and this verification directory assigned by
`PURE_BUNDLE_WORKLOAD_001.md`. It does not change the immutable goal, provider
contracts, scientific formulas, original selectors, or historical reports.

## Implemented path

The GeneTree and CodonTree adapters receive the original ArtifactBundle,
original parameters/form, supplied bytes and selected scientific metadata.
They resolve exact analysis-local roles, invoke the actual ten native reader
variants, compile only the declared semantic fields, call the installed real
provider extractors/calculators, retain every original analysis in the saved
sheet/component sets, and copy requested finite fields from saved components.

The public adapter signatures and IDs match the workload. The pure contracts
module exports the closed `parameters_schema(provider=...)`, parameter and
requested-form validators, the reviewed 88-entry scalar catalog, seven array
forms, and the finite canonical reference codec. It imports no parser or
calculator. The schema supports GeneTree's `gene_tree` and
`concatenated_sequence_loci` modes and CodonTree's
`core_genome_codon_protein` mode. Cross-field identity constraints remain
deterministic validation in addition to JSON Schema.

The qualification projection contains 196 explicitly enumerated diagnostic
codes. Schema/version/reader-name literals are excluded by a regression test;
unrecognized original diagnostics remain unchanged in saved data and use the
finite `phylogeny_unregistered_diagnostic` code only in the compact projection.

Resolution validates actual byte hashes, size, complete transfer, declared
format, native application, original input parameter relationship, and all
existing C4 task-association kinds under their qualified meanings. Every
repeated alias's supplied bytes must match; canonical receipt selection occurs
only among equal representations. Conflicting parser declarations on identical
bytes invalidate every affected selection without selecting the first parse.
Forest indices retain original source order. Supplemental parsed claims are
accepted only after matching the originally declared raw ContentBinding,
validating its bytes, reparsing once and comparing the full returned object.
Malformed analysis metadata and malformed optional supplemental documents are
isolated without discarding independent valid analyses.

Projection copies Quantity values without introducing formulas. Known-unit
branch requests cannot copy native_unknown values. Exact missing causes are
scoped to requested dependencies. Conditional bootstrap frequency remains the
measured value and carries `phylogeny_bootstrap_population_incomplete` only
when that frequency depends on an incomplete selected ensemble. Actual,
expected and usable replicate counts remain distinct complete numbers. A
complete four-member selected population remains complete when another
unrelated malformed tree is retained. An actual failed bundle with no usable
requested scientific fact retains `failed` status.

Family row references use the provider's checked genome/final-row association
plus explicit FamilyBlocks. A feature-looking member label does not establish
feature identity. Distinct alignment/row pairs are not collapsed merely because
their integer row indices match.

## Actual checks

`PYTEST_003.txt`: **147 passed**, 6.32 seconds, using `.venv/bin/python` and the
three owned test files. No dependency stub or excluded failing case was used.
Tests cover all ten reader dispatches, all seven array forms, closed scalar
selectors, schema parity, finite references, both GeneTree modes, and actual
CodonTree invocation through the pure bundle path.

Specific verified values and relationships:

| Example | Result |
| --- | --- |
| Synthetic four-row matrix | 16 cells, gap fraction 0.125, ambiguity fraction 0.25, canonical fraction 0.625 |
| Synthetic tree | 4 tips, path length 0.2, native zero and negative branch lengths preserved |
| Synthetic Codon literal statistics | sum 2.875, mean 0.71875, family ranking component 1.4375, row log-frequency -0.75 |
| Explicit synthetic F1 family matrix | 3 present genomes, 1 missing genome, 1 extra copy, presence 0.75, initial family rank 2 |
| Explicit synthetic F1 memberships | 3 protein and 2 coding-nucleotide members; deleted paralog and missing CDS retained separately |
| Function composition | 2 of 4 total and 2 of 3 recorded members assigned function/A; no divided vote weights |
| Taxon composition | 1 unknown member; same-taxon pair fraction 1/3 among known pairs |
| Explicit reference-tree comparison | 4 matched tips, 1 split in each tree, 0 shared splits, RF 2, RF fraction 1 |
| Bootstrap example | 2 matches / 4 usable replicates = 0.5; expected 5 in the partial example retained separately |
| Original-member coverage | 3 of 3 original positions = 1; final-row occupancy independently 3/4; incomplete map makes only coverage null |
| Saved historical Codon observations | genome mean -1; exact native adjustment gives -0.5/-1.00001; no use of final matrix as pretrim data |
| Retained native Codon final matrix | 9 rows × 15,300 columns = 137,700 cells; 17,308 gaps; gap fraction 0.12569353667392882 |
| Retained native Codon literal sum | 10056.41975308642; mean 0.657282336803034; native family ranking component 81.30133501475134 |
| Both retained GeneTree XML files | 17 terminal tips each; raw-tree absence/converter zero-support limitations remain qualified |

The retained Codon example saves all seven supplied reads, nine full final
matrix rows, four partitions (3,825 columns each), four fitted model records,
100 bootstrap trees, ten selected families and 160 membership entries. It does
not invent a complete preselection family matrix or final family block
coordinates from those outputs. Full native metadata is retained independently
of the requested numerical projection.

Failure/state checks include malformed independent alignments, a missing matrix
with a valid tree, a broken forest member with original surviving indices,
ambiguous roles, wrong task/hash, noncanonical repeated-byte tampering,
incompatible parser declarations, missing/forged supplemental content, invalid
second analysis metadata, unknown alphabets/branch units/bootstrap methods,
all-gap matrices, explicitly complete empty subsets, zero denominators, and
request-limited requirements. Original forms, parameters and input artifacts
are unchanged by consumption.

## Complete saved examples and implementation identity

`EXAMPLES_001/manifest.json` records ten complete examples, their input/result
SHA256 values, native source locations, actual byte sizes, dependency hashes,
and replay results. Each `.result.json` contains the full PureAdapterResult,
including complete PhylogenySheetSet and PhylogenyComponentSet. Each
`.inputs.json` contains the original bundle, supplied values, parameters,
requested form, byte manifest, and source-derived/synthetic byte payloads when
no retained native file supplies them. Native originals are referenced by their
exact digest and existing source path, not copied as new acquisitions.

The saved native Codon result is 59,458,150 bytes. All ten saved JSON examples
were reloaded and recalculated using the actual provider calculator, with
native parsing, file reads, sockets and subprocess execution forbidden. Each
recalculated component object exactly equals its saved component object. The
scientific consume calls also pass with I/O blocked in both provider cases.
`export_examples_001.py` reproduces these exports into a new directory; it
refuses to overwrite an existing example directory.

Dependency-framed implementation SHA256:

`d2cad59d6b38933bdb7e9d2a3412612b87d70c16567c128d68632fff821e4093`

It covers 21 actual repository adapter/contract/parser/provider/calculator and
schema files. Filename and byte length frame each input unambiguously. Hashing
is a configuration operation; scientific calls perform no source-file reads.
All per-file hashes were rechecked against the export manifest after export.

Installed Codon dependencies were the final root-provided modules:

- inputs: `00f915ded5a9d8c259d338c59c7829761a397a781e72b5be72de7f631cab6aa5`
- grader: `5393d24a52e255fb1d1027082218dadc9165e1f4a0a7f279bc14cb2db82f83be`
- calculator: `e8eeab6a379af3cf80b0c92089df13a8c06630abf8baabe04593d94aaab87d54`

## Preserved failed checks and corrections

- Earlier malformed-empty alignment checks exposed unavailable selected pair
  indices causing the provider calculation to discard an independent tree.
  Incomplete populations now omit only unavailable pair operands internally,
  retain the original plan and record their precise dependency. Complete
  populations with invalid pair selections are not silently repaired.
- `CODON_ADAPTER_CHECK_001.txt` records two failed assertions: the fixture
  supplied the entire retained genome/family table (4,184 families rather than
  the ten intended selected families), and the test expected a reason name
  different from the actual calculator's `family_membership_required`. The
  fixture now explicitly supplies the intended membership features; the
  provider formula and reason were not changed. `_002.txt` passes.
- `BOOTSTRAP_ADAPTER_CHECK_001.txt` records the initially unqualified
  conditional frequency. Root confirmed the exact projection meaning; the
  value remains 0.5 and only that dependent frequency receives an incomplete
  population requirement. `_002.txt` passes the complete, partial, unknown
  method and unrelated-tree cases.
- `FINAL_SCOPE_CHECK_001.txt` records two deliberately stronger fixture
  assumptions that did not hold: all four population rows lacked original
  member associations when only row zero was supplied, and auxiliary family
  alignments did not become primary final genome rows. Coverage now explicitly
  selects the one known member population, and family projection uses checked
  provider genome rows. `_002.txt` passes. Same-label feature inference was
  removed from both this adapter and the separately owned saved-return reader.
- `PYTEST_001.txt` and `PYTEST_002.txt` preserve the earlier 143- and 146-test
  passing states. The final 147-test result adds both GeneTree mode selections.

## Ownership and remaining verification boundaries

The original immutable goal and all sixteen design principles were read in
full and reread during source/tool review and before handoff, followed by the
exact accepted workload/contracts. The reviewed scalar catalog and reference
codec were sent to root before projection coding. `SCALAR_CATALOG_001.json`
remains historical; `_002.json` plus `CATALOG_AMENDMENT_001.md` records the two
approved literal-metric spelling corrections.

All acquisition/task receipts in these pure adapter tests are explicitly
synthetic. Retained official native bytes and source-derived current table/log
fixtures are labeled separately. No BV-BRC task, scientific inference program,
remote API, model, local/HPC job or Aurora operation was executed by this
workload. Current service deployment/version, sidecar formats not represented
here, original producer-byte certainty and live PhyML/FastTree output remain
unverified here.

This workload does not prove AppService custody/publication, static registry,
library selection, tool-info delivery, immediate-parent admission, typed return
across results→scientific→root, execution-resource choice, or full episode
integration. Root and the separately assigned consumers own and test those
paths. No host/registry/library/prompt/W05/controller/provider/shared-module
edits were made in this workload. Passing pure tests are not a claim of complete
integrated tool capability.
