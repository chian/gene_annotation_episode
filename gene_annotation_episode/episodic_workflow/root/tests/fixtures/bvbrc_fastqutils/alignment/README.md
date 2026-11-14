These SAM/BAM fixtures are handcrafted synthetic bytes generated from the
retained SAM 1.6 specification by `198/evidence_a/build_examples.py`. No native
aligner, samtools executable, or BV-BRC service was run. The manifest in
`evidence_a/FIXTURE_MANIFEST.json` binds exact bytes and parser contexts.

They exercise explicit SAM headers and qualities, mapped/unmapped/secondary
records, all scalar BAM auxiliary types and a nonfinite float array, absent
numeric qualities, and a bounded malformed record with an intact later sibling.
The full long-CIGAR, BGZF integrity and array-subtype matrix is generated in the
alignment format tests rather than claiming a retained native execution.
