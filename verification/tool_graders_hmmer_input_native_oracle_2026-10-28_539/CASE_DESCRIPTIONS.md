# Finite first-wave conformance cases

CASES.json and SOURCE_PINS.json freeze all exact operands and fixture identities.
There are 201 planned native comparisons: 36 classifier, 116 guess, 49 open/read.
These counts are authored tests, not passing results. C supplies the expected
classification, scanner histograms, digital rows, annotations and checksum at
runtime. `source_expected_rule`, `source_expected_status` and call-count fields
are separately labeled source-derived assertions; they are not captured outputs.

Classifier cases cover n=10/11, all-N 2000/2001, every E/F/I/J/L/O/P/Q/Z giveaway,
aa-only precedence over canonical fractions, DNA/RNA exact and above 2 percent,
all-four canonical requirements, DNA-before-RNA precedence, rich amino input and
the unresolved fourteen-letter non-giveaway diversity set. The >=15 diversity
branch cannot be reached for nonnegative counts without prior aa-only selection;
no fictitious native branch coverage is claimed. Defined large int64 N and a
narrowed count exactly INT_MAX are exercised; overflow and narrowing outside the
source-defined domain are excluded.

The ten declared formats (Stockholm, Pfam, AFA, A2M, PSI-BLAST, SELEX, Clustal,
Clustal-like, PHYLIP, PHYLIPS) each have strict 500/501, 5000/5001 and 50000/50001
whole-line cases, a huge single line, later EOF resolution, early first success,
blank input and format-specific raw regions. PHYLIP guess-only inputs skip ten
bytes on every line, including continuations. Guess-only malformed grammar is
explicitly harmless scanner input and is never treated as a successfully parsed
alignment. Stockholm/Pfam test later records and malformed suffixes; two extra
cases show a nonblank `//` token can trigger another checkpoint with no new letters.
Names, comments, headers, ignored map O, NUL token delimiters, literal CR and
trailing Clustal tokens remain format-specific byte regions. All guess inputs
are ASCII; signed-char/locale high-byte behavior is not probed.

Four retained inputs are used unchanged for both guessing and A2M reading:

| Input | Original SHA256 |
|---|---|
| cmemit aligned_a2m/emitted.out | 7e85ea14332e2dff9ff62f274e81c07fa59699c96f48236a46a8d41dd2b24197 |
| cmemit a2m_insertions/emitted.out | 4a47f0cd7fad3b309d62e69985932c31b12358e0befa0e78d0d4cb92b7ed22e3 |
| Easel a2m.good.1 | 6f144c7e8d59836304b1096fb01246297ebc1ae36548feb4bae7a9e0997f1b70 |
| Easel a2m.good.2 | ebbe37f07e8e508cc0a2b3309c46f92a958a1e5d190630b61f7ea381db419367 |

Their existing emission/source provenance stays in packet534's evidence index;
no producer is rerun. The retained insertion artifact has twelve consensus
columns and internal insertion slots; it does not supply leading/trailing
insert examples. Those are separately authored A2M inputs, including a dotful
equivalent, unequal insertion lengths, multiline whitespace and uppercase O.

Safe AFA reads exercise multiline source, duplicate row names, DNA/RNA/amino
aliases, all native gap/nonresidue/missing symbols, LF/CRLF/final unterminated
lines, reversible header bytes, leading ASCII whitespace and NUL unknown aliases.
Read errors cover missing names/headers, empty AFA rows, unequal lengths or
consensus counts, ordinary invalid symbols and malformed whole-file suffixes.
An internal high byte in AFA follows a safe ASCII prefix and reaches dsqcat;
no leading high byte or A2M high byte is passed into native ctype routines.
Empty/blank files test actual EOF with no MSA. Auto reads compare native-open
histograms and selected alphabet; short undetermined inputs test native status26,
while explicit short inputs prove native guess bypass.

Successful decoded lexical rows are canonicalized with existing `_normalize`
and the gap aliases already used by existing stockholm_digital_checksum. Exact
native row order, name hex, description hex, width and RF must match. The existing
checksum is compared directly with native esl_msa_Checksum, with no new checksum,
MAP, weighting or scoring implementation. Lexical source case/gaps remain in
production decoder output and pinned source; canonical comparison does not
rewrite them. Failed native readers destroy their MSA, so comparison checks
actual status and absence of native rows, never fabricated native partial rows.

Excluded from all native read cases: A2M lowercase-o/NUL structural mismatches;
any A2M first-zero-consensus multirow case; high-byte ctype source corners;
nonpositive/overflow PHYLIP dimensions and malformed native row-array cases;
empty MAP and after-last-match accesses. No MAP/weight program is called at all.
First-wave row conformance is AFA/A2M only. Other formats have scanner coverage,
not reader conformance or integration completion. GF/GS free-text propagation,
resource branches, scientific returns and replay remain outside this packet.
