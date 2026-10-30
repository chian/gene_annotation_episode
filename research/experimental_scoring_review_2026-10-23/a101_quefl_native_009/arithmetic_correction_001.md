# Additive record of the coordinate check

The first one-off arithmetic diagnostic attempted to apply the main paper's B. subtilis coordinates 55, 62, 70 and 97 directly as one-based positions in the full NP_389258.1 sequence printed in Supplemental Data 1. Its assertion failed. It produced no `arithmetic_checks.json` output; it had already created the source-sequence transcription file `derived_sequence_records.json`, whose sequence bytes were not changed.

Counting the published full sequence including its initial methionine gives the figure's corresponding residues at 56 C, 63 D, 71 Y and 98 E. Pcal_0221's corresponding supplied-sequence positions are 21 C, 28 D, 36 Y and 63 E. The corrected result is stored separately in `arithmetic_checks_001.json` and retains the main paper's original coordinates as distinct fields.

This corrects the diagnostic assumption about coordinate convention, not the source paper. The cause of the one-residue difference is unknown in this review. No claim about initiator-methionine cleavage, mature protein numbering or a source error is made. The available supplied sequence lengths are 165 aa for NP_389258.1 and 109 aa for YP_001055124.1.

The successful diagnostic checked the four mapped amino-acid identities, the sum 4/4, the conversion 16/100 and 22/100, the 21 transcribed QueF/QueF-like sequence records, and absence of the complete signature in the eight QueF-like records using the documented relaxed `h` position. The exact B. subtilis signature ESKSLKLY occurs at supplied-sequence positions 79–86. No new alignment, BLAST search, model inference, scorer or scientific episode ran.
