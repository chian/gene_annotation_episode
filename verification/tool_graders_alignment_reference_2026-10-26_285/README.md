# Workload 285: reference-position sheets and original-coordinate mapping

Implemented the three frozen extractors in `alignment_site_inputs.py`, the
separate `calculate_reference_site_components` calculator, and the shared
`map_operand_interval` leaf. Ownership remained within the five assigned source,
test and knowledge files and this verification directory. Existing Biopython,
minimap2 and sequence-mapping modules were read and reused without modification.

The readers validate complete native geometry and supplied operand joins before
producing selected rows. They preserve the original selector, request order and
duplicates, one event per contiguous insertion run, original quality indices,
ordered derivation segments, missing ancestry and native whole-alignment
measurements. The calculator uses unique reference positions, explicit ratio
denominators and separately named observed subset counts. It revalidates saved
rows against retained pure inputs with type-sensitive JSON comparison; bool is
not an integer coordinate. Neither stage performs I/O, native execution or model
calls. The full frozen contract was reread at handoff.

All verification jobs use `.venv/bin/python` through the existing `local_jobs`
runner, with 20 GiB RAM, 4 GiB scratch and no wall-time cap. Commands, receipts,
complete stdout and stderr are retained in each run directory:

| Run | Result | Meaning |
| --- | --- | --- |
| run_001 | 60 passed, 3.60 s | Initial numerical and retained-native tests |
| run_002 | 4 failed, 60 passed, 3.37 s | Added tests exposed bool/int/float equality and malformed phmmer inherited fields |
| run_003 | 64 passed, 3.69 s | Corrected both validation defects |
| run_004 | 71 passed, 3.91 s | Final tests include explicit metadata names, member identities, source locators, versions and unknown lengths |
| examples_001 | exit 0 | 25 complete filled examples saved and recalculated from disk with I/O disabled during calculation |

Concrete checked values:

| Example | Paired | Identical | Substituted | Query gaps | Inserted query positions | Paired identity | Selected alignment identity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Synthetic Biopython gapped | 5 | 4 | 1 | 1 | 1 | 4/5 | 4/7 |
| Synthetic phmmer compatibility | 5 | 4 | 1 | 1 | 1 | 4/5 | 4/7 |
| Synthetic PAF hand geometry | 4 | 3 | 1 | 2 | 1 | 3/4 | 3/7 |
| Retained forward/reverse PAF, each preset | 2397 | 2392 | 5 | 3 | 1 | 2392/2397 | 2392/2401 |
| Retained exact PAF, each preset | 2000 | 2000 | 0 | 0 | 0 | 1 | 1 |

The Biopython request contains 8 rows, 7 unique positions and 1 duplicate;
paired whole-operand coverage is 5/10 query and 5/12 reference. The reverse
four-base PAF selection maps reference [0,3] to original query [3,0], preserving
quality characters `5`/`!` and Phred scores 20/0. Unspecified encoding keeps
those characters with null numerical scores. A `2M3N2M` fixture has 4 paired
positions and 3 reference skips, zero deletions and 4 represented columns.
Split translated residue [1,2) maps to ordered original nt segments [3,4) and
[8,10), and the reverse path retains reversed segment order and strand.

The 18 retained minimap2 PAF rows come from six separate earlier executions on
explicit synthetic input sequences: map-ont, map-pb, map-hifi, lr:hq, map-iclr
and sr, native version 2.31-r1302. This workload reads their actual PAF bytes and
FASTA contents and preserves actual byte-row locators. It does not run minimap2
again. Their whole aligned-reference selections have 2397/2398 query paired
coverage and 2397/3200 reference paired coverage for the forward/reverse cases.
The original R/Y difference is a substitution even though native normalized cs
has N=N. Full rows remain saved, not truncated to the 12-row preview size.

`examples_001/filled/` retains each full sheet and calculated component result.
`manifest.json` labels synthetic supplied-native fixtures separately from actual
retained native minimap2 outputs. `retained_input_hashes.json` records the exact
PAF, FASTA and historical receipts read. `recalculation_report.json` records 25
successful saved-sheet calculations with file access, sockets, subprocesses and
the aligner blocked. The saved sheets remain unchanged. `before_hashes.json`
and `after_hashes.json` cover owned source files and the three reused upstream
modules; `source_check.json` records AST/whitespace checks and unchanged upstream
hashes. The checkout has no Git repository; hashes provide the source evidence.

These checks establish pure supplied-data parsing, numerical calculations and
saved-sheet validation. Biopython mode and phmmer compatibility fixtures here
are explicitly synthetic retained-input representations; no fresh Biopython,
phmmer, minimap2, network or HPC execution occurred. Complete selected-child
execution, Store custody, exact PAF-byte admission, original read-member/quality
authentication, same-length swapped Biopython/phmmer subject rejection, scoped
insertion ownership, typed receiver delivery, replay, observation and credit
counts belong to root's integration workload and are not established here.

The pure source descriptor is a host custody input; changing a valid arbitrary
subject reference cannot be authenticated from same-length native symbols
alone. Likewise, a plausible shifted byte locator requires its full retained
artifact and host custody validation. The reader rejects impossible locator
shapes and mismatching supplied native names/lengths. Native long cs and original
sequences detect the tested same-length wrong-sequence join; cg-only aggregate
counts do not uniquely authenticate every possible same-length sequence.
Biopython's native U-to-T normalization cannot restore an original RNA U;
query_original_symbol remains null where original symbols are unavailable.
Missing original maps never become invented identity maps or invalidate valid
local counts. Production availability of API/HPC operations is not asserted.
