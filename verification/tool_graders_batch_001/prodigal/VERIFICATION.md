# Prodigal/Pyrodigal B001-GENE verification

This isolated workload implements the frozen `build_prodigal_sheet`,
`calculate_prodigal_scores`, and `grade_prodigal` signatures in
`gene_annotation_episode/prodigal_grader.py`. It changes no execution, prompt,
schema, library, runtime, or credit code. Production publication and episode
return integration are owned by the root workload and are not established by
the tests recorded here.

The module uses supplied unshifted `sequence_ops.predict_genes` dictionaries,
the submitted region length, and its optional parent offset. The numerical
sheet and calculations retain every candidate and native field. Valid finite
components survive malformed neighboring fields. Nonfinite/non-JSON payloads
raise `finite_json_prodigal_native_required`, consistent with the worker's
`allow_nan=False` boundary; no tagged replacement numeric type is introduced.

## Inspected implementation and native definitions

Read the complete authoritative attachment, root AGENTS.md, batch 001 contract,
tool-grader goal/principles document, current/prodigal status row, BLAST grader
design, `blast_graders.py`, and `blast_pairwise_grader.py`. Read the complete
`sequence_ops.py`, `sequence_worker.py`, relevant complete ToolRegistry methods
`_sequence_worker_async`, `_prepare_sequence_work_async`, and `_derive`, and
`test_exact_mapping_integration.py` and `test_native_batch_runtime.py`.

Inspected installed Pyrodigal 3.7.1 documentation and native source defining
`Gene` coordinates, `partial_begin`/`partial_end`, `Gene.confidence`,
`Gene.translate`, and `GeneFinder.train` length constraints. Its native
coordinates are one-based inclusive; `sequence_ops.predict_genes` already
converts them to zero-based half-open. Its partial flags refer to lower/upper
input sequence boundaries even on the reverse strand. Confidence is a native
gene-prediction percentage. The default translated string includes terminal
stop markers. The worker does not report reading frame or codon correspondence.

The authoritative objective and entire DESIGN PRINCIPLES block were reread
verbatim after substantial native/docs examination and before final reporting.

## Numerical meanings and limitations

- `interval_length_nt` is validated relative end minus start.
- `translated_symbol_count` is the complete native string length, including
  literal `*`; `protein_length_aa` excludes `*` while retaining ambiguous amino
  acid symbols. These are counts of the supplied prediction, not a new
  translation of DNA.
- Internal stops are literal `*` positions before the last translated symbol;
  terminal-stop count is 1 when the string ends in `*`, otherwise 0. Missing or
  invalid strings yield null measurements.
- `span_symbol_length_delta_nt` subtracts three times the native symbol count
  from the reported span. A zero difference establishes length consistency,
  not codon identity or biological correctness. Mismatches remain explicit.
- Confidence and score remain separate per-candidate native quantities; no
  average, overall score, annotation confidence, or annotation credit exists.
- `union_coding_bases` counts the interval union, including either strand, once
  per base. Duplicates remain separate candidates but cannot increase union
  coverage. Invalid intervals cannot manufacture covered bases.
- Coverage uses the explicit submitted-region length. Partial coverage is a
  union of valid reported intervals with completeness false. If candidates
  exist but all intervals are unusable, the numerator remains unknown; an
  explicit empty candidate list instead yields zero covered bases. Empty input
  has a zero denominator and null fractional coverage.
- Partial count is the number with at least one native true partial flag. The
  known/unknown partial-status population is supplied separately. Missing
  partial flags are not inferred from terminal markers or labels.
- Parent intervals add `input_start` once. They refer to the supplied parent's
  coordinates. Mapping through older extracted/reversed ancestors remains the
  existing caller-owned mapping operation and is outside this pure contract.
- Saved extracted fields are checked against their retained native source
  before calculation. A corrupted interval or validity flag cannot silently
  authorize another numerical answer. This performs no native analysis rerun.

## Filled examples

| Case | Input nt | Candidates | Union nt | Coverage | Known partial candidates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Actual native meta, synthetic DNA | 306 | 1 | 303 | 0.9901960784313726 | 1 |
| Actual native single, supplied native test DNA | 100000 | 103 | 85743 | 0.85743 | 2 |
| Synthetic overlapping/duplicate candidates | 20 | 3 | 15 | 0.75 | 1 |
| Synthetic malformed partial output | 20 | 3 | 9 | 0.45, incomplete | 0 of 1 known; 2 unknown |

Meta's native candidate is `[2,305)` on `+`, with 101 translated amino acid
symbols, both partial flags true, score `51.84391561353229`, and native confidence
`99.99933317172413` percent. That percentage is not annotation correctness.

The synthetic overlapping example has intervals `[0,9)`, `[6,15)`, and repeated
`[0,9)`; the overlapping candidate is on `-`. At parent offset 100 they become
`[100,109)`, `[106,115)`, and `[100,109)`. Coverage is 15/20, not 27/20. Strings
`MK*` and `M**` have respectively 2 and 1 non-stop amino acid symbols, 0 and 1
internal stop markers, and one terminal marker each. Native scores 10 and -2,
and confidence percentages 90 and 0, remain unchanged and uncombined.

The malformed fixture retains all three native rows: one usable, one with
invalid interval/partial flag/confidence and missing `partial_end`, and a null
candidate. Eleven components are invalid and one is missing. Its valid
negative score and supplied protein string survive independently.

## Actual native execution and provenance

Both native modes ran directly through `sequence_ops.predict_genes` with code
11 and installed Pyrodigal 3.7.1. No network, service, HPC operation, BLAST job,
or model call was used.

`meta.input.fna` is deliberately synthetic `ATG + AAA*100 + TAA` (306 nt),
SHA-256 `2e66229eb55c77a1513f0fff152a59ad0907054da68129d9894d0088a0f4e22e`.
Its first invocation took 0.001989469 seconds.

`single.input.fna` is the supplied 100,000-base native test fragment from
installed Pyrodigal's
`tests/data/GCF_001457455.1_NCTC11397_genomic_100kb.fna.gz`, header accession
`NZ_LN831026.1`. This uses meaningful native training input, not a tiny or
repetitive training sequence. SHA-256
`8dd87e70a6e09ecb0c54ca659c18d2246558ca548d30744d923d89c1aee3986e`.
Its first invocation took 0.041796956 seconds.

First-run process maximum resident set was 96,012 KiB, well below the 20 GiB
limit. Inputs and complete native outputs are retained locally in this
directory, far below 4 GiB scratch. The times are execution receipts, not
forecast statistics or scientific scores. They do not establish full episode
integration or biological validation of any candidate.

## Commands and results

Run from repository root:

```text
.venv/bin/python -m pytest -q tests/test_prodigal_grader.py
46 passed in 0.29s

PYTHONPATH=. .venv/bin/python verification/tool_graders_batch_001/prodigal/write_examples.py
4 cases saved and recalculated exactly; inputs and saved sheets unchanged;
no acquisition or native rerun.
```

The 46 tests include hand-checkable overlaps, duplicates, offsets, reverse
strand, unknown and malformed candidate components, invalid bounds and flags,
explicit empty results, nonfinite rejection, saved-sheet corruption, input
immutability, retained real native outputs, and actual meta and single runs.
The offline test prevents native rerun and socket acquisition while
recalculating. The example writer reopens actual saved JSON files and confirms
exact recalculation in all four cases.

For an explicitly requested reproduction into a new output directory:

```text
PYTHONPATH=. .venv/bin/python verification/tool_graders_batch_001/prodigal/run_native.py --output NEW_DIRECTORY
```

`run_native.py` refuses to overwrite an existing output directory, preserving
earlier receipts. Verification I/O and native invocation remain separate from
the production extraction/calculation module.

Remaining integration work for the root: retain this grading envelope beside
the actual unshifted native artifact before `_derive` shifts coordinates;
publish requested typed scalar measurements; verify selected child ownership,
parent return, partial publication behavior, and unchanged credit/continuation
through the real production path. No fixed progress rows were changed by this
isolated workload.
