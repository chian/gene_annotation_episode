# Shared PSSM master metadata port 319

Implemented `extract_blast_pssm_master_metadata(sheet: dict) -> dict` in
`gene_annotation_episode/blast_pssm_master_inputs.py` with the exact
`blast_pssm_master_metadata_v1` shape accepted in 314/CONTRACT_ADDENDUM_002.md.
The input is the complete saved `blast_pssm_sheet_v1`. Every original parsed
record retains its source ordinal, PSSM key, master qualification and parser
issues; top-level issues retain the parser issues and the deduplicated union
of record issues. Unsupported, missing and malformed native masters remain
qualified records. Invalid saved-sheet structures retain the existing validator
errors. Returned mutable values are detached from the input.

The original `_master` decoder, `_plain_fields`, `_finite_json`, `_validate_sheet`,
`_node_at`, `_add`, `_bad_field` and native protein-code table now live in that
input module. The calculator imports the single decoder and validator, preserving
the existing `blast_pssm_calculators._validate_sheet` alias used by iteration
population. Native dimension and molecule checks are shared too. The input
module imports no calculator; there is no circular dependency. Matrix reshaping,
REAL decoding, statistics, component definitions and scientific formulas remain
calculator-owned and unchanged.

Only the two assigned production paths, the new assigned test file and this
verification directory were edited. Parser, iteration, metadata, worker,
status/accounting and permanent contract files were not edited by this worker.
M317 and R318 were notified when the public port became available.

The complete affected parser and calculator paths were inspected:
`blast_pssm_inputs.py`, the original and refactored `blast_pssm_calculators.py`,
`blast_iteration_inputs.py`, and `blast_iteration_calculators.py`. The entire
consuming `prepare_native_blast_database_inputs` and
`calculate_native_blast_database_sheets` functions were traced for their query
master and calculation handoffs. Existing PSSM tests and native source manifests
were read, along with the relevant native protein-code table and original query
bytes. No episode behavior or prompt was changed.

All checks used `.venv/bin/python` through the existing `local_jobs` lifecycle,
with `memory_bytes=21474836480`, `scratch_bytes=4294967296`, and
`wall_seconds=null`. Actual commands, stdout, stderr, cgroup enforcement and
return codes are retained in each named directory's `receipt.json`.

| Launcher suffix after `.venv/bin/python -B verification/tool_graders_blast_pssm_master_port_2026-10-26_319/run_checks.py` | Result | Receipt directory |
|---|---|---|
| `baseline001 baseline` | 53 original calculator results/errors retained before refactoring | `baseline001/` |
| `comparison001 compare` | All 53 complete outputs/errors equal; zero mismatches | `comparison001/` |
| `focused001 tests tests/test_blast_pssm_master_inputs.py` | 64 passed in 1.42 s | `focused001/` |
| `regression001 tests` | 234 passed in 5.36 s | `regression001/` |
| `regression002 tests` | Final 236 passed in 6.05 s, including 66 extractor cases | `regression002/` |
| `examples001 examples` | Five exact metadata examples retained; exit 0 | `examples001/` |

The final regression command was:

```text
/home/chia/repos/gene_annotation_episode/.venv/bin/python -B -m pytest -q /home/chia/repos/gene_annotation_episode/tests/test_blast_pssm_master_inputs.py /home/chia/repos/gene_annotation_episode/tests/test_blast_pssm_inputs.py /home/chia/repos/gene_annotation_episode/tests/test_blast_pssm_calculators.py /home/chia/repos/gene_annotation_episode/tests/test_blast_pssm_alphabet.py /home/chia/repos/gene_annotation_episode/tests/test_blast_iteration_inputs.py /home/chia/repos/gene_annotation_episode/tests/test_blast_iteration_calculators.py --basetemp /home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_pssm_master_port_2026-10-26_319/regression002/temporary/pytest -o cache_dir=/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_pssm_master_port_2026-10-26_319/regression002/temporary/pytest-cache
```

The final regression receipt records equal before/after hashes for every listed
production and test source during that run. Its systemd lifecycle elapsed time
was 6.561895123 seconds, exit 0, verified memory maximum 20 GiB, swap maximum
zero, and runtime maximum infinity. Scratch monitoring retains its existing
possible-overshoot qualification; the receipt records 102400 observed allocated
bytes in the run directory. The complete pre-change baseline is 29600760 bytes
and is retained outside that run directory as verification data.

`calculator_baseline.json` was written once before changing the calculator.
It contains the complete original input sheets and complete results or exact
exception types/arguments, including both native fixtures. The comparison reads
it without rewriting it. `calculator_comparison.json` records zero mismatches.
The original calculator SHA-256 is
`6e31453767a3616677c9c1c4513335c55ff8a46352b9874c40df51d814ec0ac8`;
the immutable baseline SHA-256 is
`858fb7ff24d7788a1c6d97624ba62d6c36c5bfd676ec51db3dd28c38bbfbb3ae`.

| Source | Exact final SHA-256 |
|---|---|
| `gene_annotation_episode/blast_pssm_master_inputs.py` | `021cb9c32f0dab90ae42986b125a467d5094e73faef7a7186c604ddc9ee8eba0` |
| `gene_annotation_episode/blast_pssm_calculators.py` | `59cddfe4ebe15f0b0c5368113a3a3669ca95e187d175eeaf1976c883f398bf3f` |
| `tests/test_blast_pssm_master_inputs.py` | `f3be2a50d49a4f28f62a62a1b07505c68ac49f7ae2112f334a28582d9240b5cb` |
| Unchanged `gene_annotation_episode/blast_pssm_inputs.py` | `0aa2962d617a3217eda2c8c16f5c9c0378201294944f8da0f27c4032c45e2ec1` |
| Retained `pssm_freq_ratios.asn` | `56bc1fdf3e1591254e5e031e4b3d84067525954093ab74e3b868a586b7aa613b` |
| Retained `pssm_zero_fratios.asn` | `385d3086fa8e91e2b8dbffec07ff5acd63e9f4450624450cf3e66aec10f26882` |
| Retained `seqport_util.cpp` | `4515624da7832a66b34c04240380236d08f0eea475ec9a6899079ad7b636beb9` |

`source_hashes_before.json` additionally records the authoritative goal,
accepted additive contract, parser, original calculator, original iteration
sources and native sources/manifests. `source_hashes_after.json` records all
final port sources, observed consumer versions and generated evidence. Consumer
hashes record observation times; M317, R318 and root own independent ongoing
changes in their respective files.

The retained native `pssm_freq_ratios.asn` gives a complete ncbistdaa master:
232 reported residues, 232 decoded symbols and 232 original-column mappings,
beginning `QIKDLLVSSS` and ending `P`. Every symbol is checked against an
independent oracle derived directly from the retained native literal bytes and
the pinned primary-source symbol table. The retained native zero-ratio fixture
has no query master and correctly produces `master_missing`, null lengths,
null sequence and null map. These are unchanged upstream native input fixtures,
not newly executed BLAST searches.

Synthetic examples verify all supported encodings, exact known gap positions,
extended amino-acid symbols, invalid codes, odd/malformed hex, unsupported
encoding and representation, incompatible molecule, missing/wrong/duplicate
lengths and columns, malformed/compound query structure, missing masters,
original ordinals after unsupported records, truncated tails, issue locations,
and exact saved-sheet validation errors. The concatenation of three unchanged
native fixtures is explicitly a synthetic multi-record container. It retains
the complete/unavailable/complete master sequence in source order. A gap master
`A-D` keeps positions `[0,null,2]`; a reported length 4 with decoded `ACD`
retains the sequence and decoded length 3 while leaving the map null.

The purity test forbids calculator, matrix, numeric, filesystem, process,
socket and HTTP entry points while extracting saved sheets. It checks unchanged
inputs and independent mutable output structures. Matrix/statistic failures do
not become extra master-decoding issues. Existing PSSM and iteration regressions
continue to test retained matrices, native zero values, REAL precision/failures,
coordinate behavior and composition through their existing calculation ports.

All retained local-job checks passed. An earlier read-only exploratory symbol
table probe failed with `IndexError` because of an overescaped regex; the final
independent native-sequence oracle uses the corrected expression and passed.
The checkout has no Git metadata, so source hashes and exact output comparison
are the retained change evidence.

No live native database search, acquisition, HPC deployment, authentication or
complete episode return was performed or established by this input-port work.
The M317/R318 production integration is separately owned. No annotation finding,
confidence, scientific formula, W05 connection or historical scoring result was
introduced or revised.

Before handoff, the objective and all 16 DESIGN PRINCIPLES were reread verbatim
from the immutable attachment, followed by the entire 314/002 additive contract
and the full 306 contract and its 002/003 addenda. This record reports the
implemented field/function port and its verification; it does not redefine the
broader goal's scope or completion.
