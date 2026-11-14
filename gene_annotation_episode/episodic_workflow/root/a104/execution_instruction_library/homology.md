A101 homology workloads

For BLAST/phmmer/hmmsearch/hmmscan, record query count/residues, target database
count/residues and version, algorithm/search options, threads/nodes, indexing
state, and software/hardware fingerprints. Include database acquisition/build,
profile preparation, sharding and merge costs where required. Predict setup
separately from search; reuse a verified database or environment instead of
charging its construction on every run. hmmscan and hmmsearch have different
operand directions and cannot share an unqualified timing class.

Preserve query/target identities and complete native artifacts, including
no-hit and failure outcomes. A101's existing native result readers and graders
own the numerical evidence. A compact HPC result.json is an operational receipt,
not a replacement for BLAST/HMMER output, a retained grading sheet, or a newly
invented scientific score. Confirm the configured result adapter before launch.
