# Translation numerical workload280 — implemented and verified

Owned implementation is `sequence_translation_grader.py`, its focused test
module, `knowledge/sequence-translation.md`, and this verification directory.
No producer, mapping, shared runtime, progress ledger or permanent goal record
was edited by this workload. Root owns the producer snapshot and publication/
Workflow bindings; its changes were inspected separately.

## Delivered ports and numerical meanings

`build_translation_sheet(native, *, input_sequence, subject_ref,
parent_mapping, request, genetic_code=None)` retains exact operands and extracts
numeric geometry, native product counts, native-setting comparisons and ordered
codon rows. `calculate_translation_scores(sheet)` validates saved cells against
those operands and calculates the counts/fraction. `grade_translation` returns
exactly `{sheet, scores}`. As clarified in workload279's additive shape record,
the numerical fields live only in `scores.summary`; source-bound rows,
`component_status`, `issues` and explicit definitions are separate siblings.

Counts distinguish consumed complete codons, returned amino-acid/ambiguous/stop
symbols, a CDS stop deliberately omitted from the product, frame-skipped bases
and trailing bases. Compatibility counts include the omitted stop's context
check; mapped-output counts exclude the omitted stop. Mapping is supplied
ancestry, never inferred from lengths or names. Split, repeated and reversed
paths retain their original subject identities and order. A missing map yields
null mapped-output count. An output-length disagreement does not establish a
mapped prefix.

Frozen table validation retains native null aliases, alternative CDS starts,
dual-coding stops, and missing reference fields. Finite IUPAC codon expansion
uses only the saved table. No installed Bio table, translation call, Store,
filesystem, network, resource selection, model call or biological confidence
calculation is present in the reader/calculator. Native product counts remain
available independently of missing table entries. A missing product differs
from a retained empty/corrupt output and from measured zero stops.

## Actual filled examples

The complete native inputs, requests, genetic codes, results, sheets and scores
for 15 actual tiny translations are retained under `native002/`; artifact SHA256
values and all numerical summaries are in `native002/examples.json`.

| Input/mode | Native product | Consumed codons | Output / amino-acid symbols | Internal / returned terminal / omitted stops | Compatible / unknown codons |
| --- | --- | ---: | ---: | ---: | ---: |
| `ATGTAGAAATAACC`, code1 | `M*K*` | 4 | 4 / 2 | 1 / 1 / 0 | 4 / 0 |
| `ATATGAAGA`, code1 | `I*R` | 3 | 3 / 2 | 1 / 0 / 0 | 3 / 0 |
| `ATATGAAGA`, code2 | `MW*` | 3 | 3 / 2 | 0 / 1 / 0 | 3 / 0 |
| `GTGAAATAA`, code11 CDS | `MK` | 3 | 2 / 2 | 0 / 0 / 1 | 3 / 0 |
| `GCNRAYWTAATNTARTANNNN`, code1 | `ABJX*XX` | 7 | 7 / 6 | 1 / 0 / 0 | 7 / 0 |
| `HTGAAATAR`, code11 CDS | `MK` | 3 | 2 / 2 | 0 / 0 / 1 | 3 / 0 |
| `ATGTGATGA`, code27 CDS | `MW` | 3 | 2 / 2 | 0 / 0 / 1 | 3 / 0 |
| `ATGTAATGA`, code28 CDS | `MQ` | 3 | 2 / 2 | 0 / 0 / 1 | 3 / 0 |
| `ATGTAATAG`, code31 CDS | `ME` | 3 | 2 / 2 | 0 / 0 / 1 | 3 / 0 |

The first example has 14 input nt, 12 translated nt and 2 trailing nt. The
ambiguity example has 7 ambiguous codons but 5 ambiguous output symbols: GCN
resolves to A, while TAR is a stop. For a selected 12-nt interval in a 16-nt
input, every one of the six strand/frame cases has selection fraction 12/16 =
0.75. Products at frames 0/1/2 are `MK*P`, `*NN`, `EIT` on `+`, and `GLFH`,
`GYF`, `VIS` on `-`; used lengths are 12/9/9 nt and trailing counts 0/2/1.

## Verification and provenance

- `native001`: nine real tiny translator executions inspected before the grader
  was coded. Native output was retained without claiming a numerical grader.
- `check001`: 59 tests passed in 0.35 s, with numerical assertions independent
  of the grader's calculated answers.
- `check002`: 67 tests passed in 0.37 s after adding missing-table-field,
  repeated-source and impossible-CDS corruption cases. This is the final code
  revision tested here, with unchanged before/after source hashes.
- `native002`: 15 actual tiny translator executions completed successfully with
  full grading output retained, including all six strand/frame combinations.
- The canonical and recursively reversed-key JSON sheet files from the saved
  recalculation test remain in `check002/temporary/`. The test prohibited
  builtins/io/path file reads, socket creation, subprocess creation, native
  translation and installed codon-table lookup. Both returned exactly the
  original saved scores without mutating the sheet.
- Deliberate input/result/table/mapping corruptions are explicitly labelled in
  test names/comments. Native translations were real Biopython1.88 operations
  on supplied tiny fixtures. Synthetic source paths are distinguished from the
  native translation outputs they accompany.

All recorded native/test jobs used existing `local_jobs` with 21474836480 memory
bytes, 4294967296 scratch bytes and no wall-time cap. Receipts show systemd
cgroup memory enforcement, zero swap, infinite runtime allowance and scratch
monitoring. No installation, API scientific request, HPC work or local database
BLAST was performed.

Complete source paths inspected: `sequence_ops.py`, `sequence_mapping.py`,
`sequence_views.py`, `sequence_composition_grader.py`, `local_jobs.py`, source
retention functions in `tool_grading_artifacts.py`, complete affected
`ToolRegistry` execution/derivation/source/publication paths, and Store sequence
mapping/coverage/footprint paths. Installed `Bio.Seq._translate_str` and
`Bio.Data.CodonTable` ambiguity implementations were read completely at their
relevant function boundaries. The [official Bio.Seq documentation](https://biopython.org/docs/latest/api/Bio.Seq.html)
was also consulted; frozen installed native operands determine these results.

Final tested source hashes:

| Source | SHA256 |
| --- | --- |
| `sequence_translation_grader.py` | `59c9376f8c077543cc8c15b5779777648120b4a2e75ee2859baf1edb24af2b50` |
| `test_sequence_translation_grader.py` | `fee788b7aab871970223f9765b62e63ad8103a63ae61d14e8d8431a47d4f0611` |
| `knowledge/sequence-translation.md` | `600febaeec321a25a55d7bbe553266d6073d5448f47ce850a5753898b3feb61a` |
| Root's `sequence_ops.py` | `3f39fd2927697a4bdeae563271aa4244e9fab2ddd28360e80f644723921370ed` |
| Unchanged `sequence_mapping.py` | `241195f974b6a8dab6a06434daa47d04bd277c6a584c77a534f30a274fb3c1c3` |

The immutable pasted goal SHA256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`;
workload279's original contract SHA256 is
`93531c90861e56b80d849be513dc22d68d2434fe903e5ca73bb75909dc579dbf`.
The goal, all 16 original design principles, contract and additive summary shape
are reread before the completion handoff. The full 308-tool scope is unchanged.

No unresolved numerical-contract gap is known for the assigned translation
workload. Actual selected-tool/child/parent Workflow verification remains root's
separate responsibility; these unit/native results do not establish that path.
The broader tool inventory and other scientific modes are not declared complete.
