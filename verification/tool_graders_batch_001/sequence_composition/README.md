# B001-COMP verification

This directory verifies the pure sequence-composition sheet, extractor and
calculator. It does not establish the production selected-tool, resource-child,
publication, credit or parent-return path. Root owns those integration changes.
No pending NCBI job is part of this work.

## Inputs and responsibilities

The public signatures are the frozen B001-COMP signatures in
`docs/TOOL_GRADER_BATCH_001_2026-10-24.md`. The builder accepts the actual supplied
sequence, declared molecule, optional full quality string and declared encoding.
It retains both original strings and numerical symbol/quality distributions.
The calculator consumes the saved sheet and an explicit tuple of integer Phred
thresholds. It validates saved measurements against retained input without
altering the sheet, acquiring data or rerunning a native scientific operation.
The facade returns `{"sheet": ..., "scores": ...}`.

The existing material/domain contract declares `phred33`, `phred64`,
`solexa64` and `unspecified`. The grader accepts these names without inventing
aliases or detecting encoding from characters. Unknown string encodings remain
retained and unavailable for quality calculations. Wrong argument types and
unsupported molecule declarations raise specific `ValueError` codes.

Only ASCII letter case is normalized for counts. No symbol is removed. DNA uses
ACGT and RNA ACGU as unambiguous nucleotides. Nucleotide ambiguity uses
RYSWKMBDHVN. Protein ambiguity uses BXZJ; U and O remain specific residues and *
remains a stop. An unspecified molecule retains all literal symbol counts and
leaves molecule-dependent quantities unknown. Invalid declared-molecule symbols
remain counted with an issue; valid composition measurements survive.

## Numerical meanings

All counts refer to this one supplied sequence or its supplied quality string.
No count asserts that reads are independent. Uncertainty intervals and quality
calibration metadata are not available through the frozen input contract.

| Field | Calculation and population | Units and missing behavior |
| --- | --- | --- |
| `length` | Exact supplied string length, including invalid symbols | Symbols; empty input is 0 |
| `symbol_counts` | Count each symbol after ASCII uppercase only | Symbols; original sequence remains retained |
| `unambiguous_nucleotide_count` | Sum ACGT for DNA, ACGU for RNA | nt; protein/unspecified is null |
| `ambiguous_symbol_count` | Sum the declared molecule's ambiguity symbols | Symbols; unspecified is null |
| `ambiguity_fraction` | Ambiguous count / all supplied symbols | Fraction; length 0 or unspecified is null |
| `gc_count` | C + G for DNA/RNA | nt; protein/unspecified is null |
| `gc_denominator` | Declared unambiguous nucleotide count | nt; ambiguous and invalid symbols excluded |
| `gc_fraction` | GC count / GC denominator | Fraction; denominator 0 or nonnucleotide molecule is null |
| `composition.invalid_symbol_count` | Sum counts outside the declared molecule's canonical, ambiguity and allowed stop symbols | Symbols; unspecified molecule is null |
| `quality_measurements.character_count` | Exact supplied quality-string length, even when different from sequence length | Characters; absent quality is null |
| `quality_measurements.native_score_distribution` | Per-character ASCII code minus declared offset, grouped with integer occurrence counts | Native Phred or Solexa score and characters; unknown encoding is null |
| `quality_measurements.decoded_character_count` / `invalid_character_count` | Counts inside / outside the declared encoding's allowed range | Characters; absent quality or unknown encoding is null |
| `quality_measurements.invalid_characters` | Exact zero-based quality-string position and Unicode code point for every out-of-range character | Character offsets and code points, retained even when whole-read summaries are unavailable |
| `quality_observation_count` | Sum native quality-distribution counts only when the full quality string is valid under its declaration and matches sequence length | Base-quality observations; absent/invalid/unknown encoding is null |
| `mean_phred` | Sum count × unrounded Phred / quality count | Phred; no valid nonempty population is null |
| `mean_error_probability` | Sum count × encoding-implied error probability / quality count | Probability; no valid nonempty population is null |
| `expected_error_count` | Sum count × encoding-implied error probability | Expected base-call errors; not observed errors, and additive expectation needs no independence assumption |
| `quality_thresholds` | For every requested integer cutoff, count unrounded Phred values greater than or equal to cutoff, then divide by quality count | Phred cutoff, observations and fraction; no acceptance decision |

For phred33, ASCII 33–126 represents Q=0–93. For phred64, ASCII 64–126
represents Q=0–62. For solexa64, ASCII 59–126 represents S=-5–62, with
`p = 1/(1+10**(S/10))` and `Q = 10*log10(1+10**(S/10))`. These are the
encoding meanings in the [Biopython QualityIO documentation](https://biopython.org/docs/latest/api/Bio.SeqIO.QualityIO.html),
checked against all supported characters using the installed Biopython native
FASTQ readers. Phred error probability is `10**(-Q/10)`.

The sheet stores native-score bins, not rounded Phred bins. Calculator output
retains every bin's native score, count, converted Phred and error probability
before aggregation. Thresholds preserve caller order and duplicate requests.
They produce reports, never a quality gate or annotation-confidence score.

An explicitly supplied empty quality string paired with an empty sequence and a
supported encoding is a valid empty population: observation count 0, expected
error sum 0, null means and null threshold fractions. Missing quality is
different: those quantities are null. A mismatched or partly invalid quality
string keeps the raw string, native valid bins and precise issues; whole-sequence
quality summaries remain null. A missing optional quality string does not make
otherwise complete composition extraction fail.

## Filled examples

`filled_examples.json` retains full facade outputs, and
`recalculated_thresholds.json` contains recalculation of the first example from
its JSON-reopened sheet. These are deliberately synthetic numerical examples.

| Example | Expected answer |
| --- | --- |
| DNA `acgN`, phred33 `!+5?` | Length 4; A/C/G/N each 1; ambiguity 1/4; GC 2/3; Q = 0,10,20,30; mean Q 15; expected errors 1.111; mean error 0.27775; Q20 2/4, Q30 1/4 |
| RNA `ggcuuN`, no quality | Length 6; ambiguity 1/6; GC 3/5; quality measurements null |
| Protein `ABXZWJOu*`, no quality | Length 9; ambiguous count 4; ambiguity 4/9; nucleotide/GC measurements null |
| Unspecified `ACGT` | Symbol counts retained; ambiguity/GC interpretation null |
| DNA `ACG`, solexa64 `;@J` | Native S = -5,0,10; probabilities = 1/(1+10^-0.5), 1/2, 1/11; native negative score retained |
| DNA `ACGT`, phred33 `II?` | Quality length 3 versus sequence length 4; native scores retained, whole-read quality quantities null |
| Empty DNA and supplied empty phred33 quality | Counts and expected error sum 0; ratios/means null |

## Actual verification performed

The focused command was `.venv/bin/python -m pytest -q tests/test_sequence_composition_grader.py`.
Its result is recorded in `verification.json`. Cases cover finite values, DNA,
RNA, protein and unspecified molecules, invalid symbols, the actual declared
encodings and all their supported native ASCII characters, empty populations,
missing/unknown/invalid/mismatched quality, malformed contracts, nonfinite saved
sheets, incorrect saved numerical cells and threshold recalculation without
calling the builder. Inputs and saved sheets remain unchanged.

One test executes the existing `material_parsing.records` FASTQ parser on the
exact first wrapped synthetic record from
`tests/test_packed_materials.py::WRAPPED_FASTQ`. It verifies the full sequence
`ACGTTGCA` and quality `!@+~@@##` reach the pure grader, with mean Q=25 only when
phred33 is explicitly declared. The fixture's original unspecified encoding
keeps quality scores unknown. This is a parser-contract exercise using synthetic
native-format bytes, not a biological sequencing experiment or full Store and
episode communication test.

No original biological FASTQ dataset, remote resource, production publication,
typed parent return or credit path was executed here. The module imports no
Store, ToolRegistry, network client, subprocess or LLM interface. Root separately
supplies complete actual sequence/quality through original member custody.
