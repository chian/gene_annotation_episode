# B001-PAIR standalone verification

The implementation is `gene_annotation_episode/biopython_pairwise_grader.py`.
Its three frozen entry points are `build_biopython_pairwise_sheet`,
`calculate_biopython_pairwise_scores`, and `grade_biopython_pairwise`.
The facade returns `{"sheet": ..., "scores": ...}`. The module imports only
Python standard-library modules and performs no analysis execution, acquisition,
resource selection, model request, publication, or annotation-credit change.

`native_examples.json` retains the exact result dictionaries from eight actual
local Biopython 1.88 executions on explicitly supplied tiny synthetic sequences.
It also records each invocation's complete arguments. `filled_examples.json`
contains their complete sheets and separately calculated scores. Neither file
is a biological validation benchmark. `provenance.json` distinguishes these
direct native executions from resource-child and episode integration.

| Native case | Columns | Paired | Identical | Paired identity | Query paired coverage | Query aligned coverage | Native score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DNA global, `ACGTT` / `ACTT`, gap open −2 | 5 | 4 | 4 | 1 | 4/5 | 5/5 | 6 |
| DNA local, `GGACGTCC` / `TTACGTAA` | 4 | 4 | 4 | 1 | 4/8 | 4/8 | 8 |
| RNA global, `AUGC` / `AUAC` | 4 | 4 | 3 | 3/4 | 4/4 | 4/4 | 5 |
| RNA local, `GGAUGCCC` / `AAAUGCUU` | 4 | 4 | 4 | 1 | 4/8 | 4/8 | 8 |
| Protein global, `ACDE` / `ACE`, gap open −2 | 4 | 3 | 3 | 1 | 3/4 | 4/4 | 16 |
| Protein local, `WWACDEWW` / `GGACDEGG` | 4 | 4 | 4 | 1 | 4/8 | 4/8 | 24 |
| DNA local no alignment, `AAA` / `CCC` | 0 | 0 | 0 | null | 0/3 | 0/3 | null |
| DNA global, `A` / `C`, gaps −0.1 | 2 | 0 | 0 | null | 0/1 | 1/1 | −0.2 |

The first row has four matched pairs and one reference gap. Its alignment
identity is 4/5, reference paired coverage is 4/4, and reference aligned coverage
is 4/4. All positions use the native zero-based convention; intervals are
half-open. Local flanks are outside the aligned intervals. RNA native tracebacks
contain T because the existing operation converts U to T before alignment;
the grader records this fact and does not reconstruct original U symbols.

The tests additionally use an explicitly synthetic local traceback
`ACD-EFG` / `ACTVE-G`, query interval [1, 7), reference interval [3, 9), operand
lengths 10 and 12. It yields 7 columns, 5 pairs, 4 identities, 1 substitution,
1 gap on each operand, paired identity 4/5, alignment identity 4/7, paired
coverages 5/10 and 5/12, and aligned coverages 6/10 and 6/12. Its score 17.5 is a
synthetic reported native-score fixture, not a score recalculated by Biopython.

Verification executed:

```text
.venv/bin/python -m verification.tool_graders_batch_001.biopython_pairwise.generate_examples
  Eight actual native outputs retained (Biopython 1.88).

.venv/bin/python -m pytest -q tests/test_biopython_pairwise_grader.py tests/test_sequence_ops.py tests/test_blast_pairwise_grader.py
  102 passed in 0.31s (58 new pairwise cases).
```

The pairwise tests check all six molecule/mode combinations, gap placement and
unaligned flanks, no alignment, a valid zero-pair alignment, literal ambiguity
identity, contradictory reported counts/fractions, missing and malformed
traceback/geometry/lengths, negative and zero native scores, very large integer
score preservation, finite malformed individual values, nonfinite/native-contract
rejection, calculator validation, and caller immutability. The saved-sheet test
reopens a JSON file, forbids native alignment calls, and reproduces the scores.
The retained examples are independently replayed through parser and calculator.
An additional check varied 16 native fields across 12 finite values (192 cases),
preserving partial output without unexpected exceptions. A separate Python
`-S` process recalculated all eight saved sheets with site-packages disabled;
Biopython, Store, and ToolRegistry were not imported.

Nonfinite or non-JSON native input raises a specific `ValueError`, following the
existing BLAST boundary and batch clarification. It is never rewritten into a
tagged numeric value. Finite malformed fields remain verbatim in `native_result`;
affected extracted fields become null with specific issues. Valid traceback
counts survive bad coordinates, but no positional coverage is calculated from
that invalid geometry. Missing traceback never becomes a zero-result alignment.

This workload verified the standalone parser/calculator and direct native
execution. Root owns production publication, the selected resource-child path,
typed episode returns, and their integration verification; these tests do not
establish those completion columns. This native operation returns one alignment,
not all alternative optima. Its result lacks original unaligned sequence symbols
and reference identifiers, so the grader cannot independently authenticate those
operands or reconstruct unaligned sequence; root preserves their actual custody.

The original authoritative objective and entire DESIGN PRINCIPLES block were
reread after native-output examination and before final review, together with
the B001-PAIR frozen contract. The pending NCBI BLAST job was not accessed.
