# CodonTree native-table reader handoff

Fresh workload `codon_tree_native_tables_122`, 2026-10-24. The four assigned
pure readers and their tests are implemented in the two owned staging files:

- `../staging/gene_annotation_episode/bvbrc_codon_tree_native.py`
- `../staging/tests/test_bvbrc_codon_tree_native.py`

No production, shared-format/calculator, provider sheet/grader, runtime, prompt,
resource, registry, fixed status row, original goal or design file was edited.
No subagents were spawned. No upstream program was imported or executed.

The complete immutable goal was read. Its objective and all sixteen design
principles were reread verbatim after substantial source/native examination,
before implementation, and again after verification before this handoff. The
exact native-table contract and provider envelope were reread. Verified original
goal SHA256 is `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`;
the unchanged contract SHA256 is
`c6021e7c0d5870efd2a0da0af11c9e83f7869ae2b4ae20d8e5bf7f6da36b4ee4`.

## Delivered functions and exact handoff

```python
parse_codon_membership(data: bytes, *, artifact: dict,
    dialect: Literal["pgfams_legacy", "homologs_current"]) -> dict
parse_codon_family_statistics(data: bytes, *, artifact: dict,
    dialect: Literal["current_missing_header_tab"]) -> dict
parse_codon_genome_counts(data: bytes, *, artifact: dict) -> dict
parse_codon_analysis_statistics(data: bytes, *, artifact: dict,
    dialect: Literal["retained_current_source"]) -> dict
```

Each returns the frozen `{status,value,diagnostics}`. The fixed, no-dialect-arg
genome reader labels its exact known table syntax `genes_per_genome_current`.
The module is standard-library-only and has no shared parser/calculator import.
The test imports the existing C4 validator to validate actual diagnostics.

The receiving function remains the separately owned
`extract_codon_tree_sheet(documents=..., inputs=..., observed_run=..., joins=...,
parameters=...)`. Its `documents` input is the envelope defined in
NATIVE_METADATA_CONTRACT.md: `parsed`, `raxml_runs`, `membership`,
`family_statistics`, `genome_counts`, `analysis_statistics`, all required.
Place each successful/partial ReadResult **value** in its named input array;
retain the ReadResult diagnostics as qualifications. Each value's table must
equal its same-ID `parsed.store.native_tables` entry. Tables have the exact
artifact-ref-plus-suffix IDs in the frozen contract. `source_row_index` and
`source_row_indices` refer to stored physical-row indices, not physical line
numbers; headers are excluded from row arrays. Measurements use
`<table_id>/row/<row_index>/<NativeField>`. Identifier segments in family/genome
population IDs are percent-encoded, including slash, percent and UTF-8 bytes.

The provider must bind the relevant CodonAnalysis document fields and
`native_engine_observation_ids` using supplied same-analysis evidence, flatten
observations into the sheet, and construct native populations without inventing
members from count facts. These actions have not been implemented or tested by
this workload. `UNSELECTED_PROVIDER_INPUT_EXAMPLE.json` demonstrates the exact
input envelope and same-ID table equality with `analyses=[]`. The historical
artifact and independent source-derived fixtures are deliberately unselected;
they are not fabricated into a common scientific run.

## Additive contract clarification

The root explicitly approved this during the workload:

> Approved: incompatible family-statistics header returns status=invalid,value=null with the exact header diagnostic; original supplied bytes remain retained. Do not assert header_defect=missing_tab_before_used_in_tree for a different header. For the recognized header, independent valid numeric cells survive alongside failed/null cells; structurally invalid rows remain raw-only. Record this specific clarification additively in your handoff; no new output keys.

The parser follows this without modifying the original frozen contract. Other
incompatible table headers also return invalid/null. Empty membership retains
an unknown-completeness table and invalid status; a header-only numerical table
has no successful zero observations. All current writers terminate their lines;
an unterminated final physical row remains raw-only with truncated completeness,
while preceding complete records survive.

## Source and numerical evidence

Read the relevant complete producing paths in pinned
`scripts/p3x-build-codon-tree.py`: family count construction, family evaluation,
native statistics/inclusion, end-trim boundary, membership/table writers and
analysisStats writer. Read the complete native `calcAlignmentStats` routine in
`lib/phylocode.py`. Source identities match the 118 receipts. Both source files,
the goal/contracts and delivered files are hashed in SOURCE_AND_CODE_HASHES.json.

The complete official historical membership artifact is 4,060 bytes, SHA256
`0cbccad42d58222b053dbbb3ac484fd7362d2b3f7a34b828067d6e3fe47590e5`.
It produces **20 typed membership rows**, ten protein plus ten coding-nucleotide,
**eight included feature IDs per row**, and **30 stored physical rows**, including
ten blank separators. This is retained native evidence, not a newly executed run.

The four current examples are source-derived syntax fixtures. Their bytes and
populated results are exported separately, with individual artifact IDs/hashes:

| Example | Actual parser values |
| --- | --- |
| Current membership | Three typed rows; explicit deleted paralog and lacking-codon lists; missing-codon family PGF_2; six physical rows retained. |
| PGF_1 pre-trim row | gaps=2 characters; sum_squared_freq=3.25 column-summed squared fraction; mean_squared_freq=0.8125; length=4 columns; sequences=2; worst ratio=2.0; used_in_tree=true. |
| PGF_2 pre-trim row | Five native measured zeros; worst ratio is null/missing with raw token `na`; used_in_tree=false and native low-alignment-score reason. |
| PGF_3 pre-trim row | gaps=3, sum=1.5, mean=0.5, length=3, sequences=2, worst ratio=9.0; native bad-sequence scalar map `g/1`=9.0 and reason `bad seqs`. |
| Genome g1 | All-family=12, single-copy-family=8, filtered-single-copy-family=3, all in families. A separate g0 row has three measured zeros. |
| Analysis report | Num_genomes=2; Num_protein_alignments=2; Num_aligned_amino_acids=4; Num_CDS_alignments=2; Num_aligned_nucleotides=12, all retained as reported counts. |

The analysis CDS count carries the source-defect qualification; it is not
asserted to be an observed CDS population. Its retained `raxmlHPC -f I ...`
command has observed origin and **unknown role**, as required. PGFams and the
17-second duration row are retained uninterpreted by this scientific schema.
Pre-trim counts are never filled from final report counts; ranking is not
manufactured from the TSV, and inclusion categories are not numerical scores.

## Verification performed

Final command, with exact staging import assertions:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging /home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_bvbrc_codon_tree_native.py --junitxml=../codon-native-verification/pytest-final-101.xml
```

Run from the staging directory: **101 passed in 0.22 seconds**. The exporter was
then run with the same absolute interpreter, cwd and PYTHONPATH, and exported
five populated examples successfully. No scientific executable was invoked.

Tests verify the full historical artifact; complete current writer syntax;
closed result/table/row/observation/command shapes; exact caller signatures;
numeric answers, zero/missing/failed distinctions, signed finite statistics;
duplicate family/feature/genome records; orphan/conflicting continuations;
the exact fused header versus malformed variants; bad-sequence calls, nested
values, booleans, nonfinite numbers and duplicate keys; all source identities,
byte/line positions and percent-escaped population IDs; CRLF/Unicode/control
boundaries; empty/truncated inputs; wrong digest/encoding/dialect; wrong input
types; JSON serialization; input immutability; and operation with file, socket,
subprocess, shell and builtin eval calls disabled.

The initial run had **94 passed, 3 failed**. All three failures were in the test's
truncation-preservation comparison: appending bytes changes the supplied
artifact digest, but the assertion expected the old digest in surviving
observation locations. The corrected assertion checks the new digest and
unchanged prior numerical values/positions. That correction produced 97 passes;
the four added shape/reference/type/control checks produced 101 passes. Raw JUnit
reports and complete failure identities/messages are retained in TEST_RUNS.json.
An ancillary `git status` attempt returned exit 128 because this workspace is not
a Git checkout; no VCS action or production edit followed.

## Remaining work and limitations

No current live CodonTree output has been acquired or executed. The current
tables have source-derived fixtures; the historical membership is actual retained
native output. Current native bad-sequence maps and table defects still need a
live/deployment specimen for live-format verification.

Provider sheet assembly, calculator execution/recalculation, native-population
construction, C4 registration/dispatch, selected resource-child execution,
actual task-to-artifact custody, authentication and typed episode returns remain
outside this delivered workload and unverified here. No completion claim is made
for fixed row C-L193-CodonTree. This parser work does not establish source
deployment, scientific validity of upstream selection, original residue maps,
preselection membership, or actual biological support.

Full code SHA256:
`71be6edbff8868d3689f7d0d4dd7f8facea990ac69fabb47b645c785b21e462d`.
Test SHA256:
`b68026951d2097bdd0ff58c79d811225a78ece0c8ae6f7a7a97ec3164b472e37`.
