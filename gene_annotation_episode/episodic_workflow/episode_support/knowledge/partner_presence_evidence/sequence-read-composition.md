# Sequence composition and original read quality

`sequence.inspect` measures the supplied sequence. `reads.inspect` measures
exactly the selected original reads and keeps each read's association with
its source member and original quality string. The latter is one selected
operation with separate per-read measurements, not a whole-library inference.

The input's declared molecule controls interpretation. DNA and RNA GC fraction
uses G+C divided by the number of unambiguous A/C/G/T or A/C/G/U symbols,
respectively. Ambiguity fraction uses ambiguous symbols divided by total
sequence length. The sheet retains counts and denominators. Protein and
unspecified-molecule inputs do not receive a nucleotide GC interpretation.
Alphabet compatibility does not classify a molecule or imply function.

Read quality requires the complete original quality string and declared
`phred33`, `phred64` or `solexa64` encoding. Do not guess encoding from printable
characters. The deterministic calculator reports mean Phred score, expected
error count, mean error probability and counts/fractions at explicit thresholds.
Phred error probabilities use 10**(-Q/10); Solexa values use their odds
conversion. Missing encoding, invalid characters or a sequence/quality length
mismatch leaves the affected quantities unavailable, not perfect or zero.

The complete quality distribution and inputs are retained so thresholds can
be recalculated without reacquiring data. Default Q20 and Q30 reports are
measurements, not acceptance gates. Return only requested measurements;
complete raw reads, quality strings and sheets remain outside model prompts.
