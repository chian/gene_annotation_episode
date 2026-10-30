# Native pairwise parser fixtures

`native_pair_result.json` and `native_pair_result.tsv` are exact copies of
the actual BLAST+ 2.17.0 `-subject` outputs produced on 2026-10-24 in
`verification/w04_blast_graders_2026-10-24_001/native_pair/`.
That directory's `execution.json` records the native commands and input
construction. The query is the public 253-aa YbhP example; the reference is
synthetic, made by removing ten residues and substituting five residues.
There was no local database search, API request or HPC job for these fixtures.

These exercise native formatter compatibility, not biological annotation
accuracy. Numerical correctness of the graders is tested separately.

The tabular native formatter prints `# Database: User specified sequence set
(Input: ...)` even for pairwise `-subject` execution. This is retained verbatim
and must not be classified as a database-search result.
