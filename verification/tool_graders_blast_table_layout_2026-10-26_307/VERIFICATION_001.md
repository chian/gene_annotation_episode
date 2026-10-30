# Defined fields and implemented population function

`blast_report_collection._tabular_search` now retains the supplied format,
original declared fields and effective delimiter in the exact `table_layout`
descriptor frozen by CONTRACT_001.md. It preserves the existing native text,
row locations, normalized measurements and non-table output shapes. Workloads
303 and 305 separately consume this descriptor to avoid reconstructing input
facts that were already supplied.

Eight new checks and 330 existing checks passed: **338 passed**, one expected
duplicate-ZIP-name warning, in 180.23 seconds. Actual receipt, JUnit and logs
are in check_001. The existing local_jobs boundary enforced 20 GiB RAM and
zero swap, used the 4 GiB scratch policy, and left wall time unset. The service
exited successfully; observed allocated scratch was 33,173,504 bytes.

The tests include the full collection/context/legacy-reader regressions,
pairwise sheets and result projections, native coordinate conventions, and
54 existing retained-result HSP-site tests. Those tests reuse previously
retained native reports and the result publication/read path. This run did not
launch BLAST, acquire new biological results, or verify a new HPC deployment.

Concrete synthetic example: a tabular6 report with `@` as its supplied delimiter
and `s#1` as a subject ID retains format `tabular6`, delimiter `@`, the original
field list, three separate repeated-query sections and HSP query endpoint 4.
The `#` inside the value does not select a different parser. A header-only
tabular7 field declaration retains `declared_fields=null` while preserving the
actual header fields separately. Empty output and an explicit zero-hit report
keep distinct unknown/zero counts. JSON results receive no table descriptor.

The receipt contains before/after hashes of all top-level production and test
Python files. The changed collector and all files used by this packet's focused
collector/pairwise checks were unchanged during the run. Seven other files
changed in parallel workloads: profile/PSSM code and tests, and a separate
literature workload. The receipt lists them exactly; this is not a claim of a
stable whole-checkout snapshot.

Collector SHA-256 after verification:
`c8d19a057ff51e029323d5f92468007f5011a618f1223ecf2bcb4fe95f7378aa`.

Root reread the immutable objective, all sixteen design principles and this
packet's exact contract after verification. Historical receipts and saved sheets
were not rewritten. This correction adds no completed scientific mode to the
fixed tally; it implements fields and their population for downstream graders.
