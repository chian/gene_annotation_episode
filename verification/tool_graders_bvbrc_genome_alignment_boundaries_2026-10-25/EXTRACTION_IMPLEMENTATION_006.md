# Accepted GenomeAlignment extraction workloads

Root accepts the input-only extension in
../tool_graders_bvbrc_genome_alignment_extraction_boundaries_2026-10-25/EXTRACTION_CONTRACT_001.md
(SHA256 cd937c37c2012bca6729b13583677c903b73edff5adcf16305cb1209979a07e1)
with its additive RETENTION_FAILURES_002.md
(SHA256 7a9c03577abf4e93856c6801d0e3b868a45a9be8025b20398b7b9c1c80959f0f).
The latter controls per-record error recovery and original input-binding
pointer semantics. This is implementation authorization for fixed row
C-L202-GenomeAlignment, not a change to the immutable goal or a completion claim.

C1 owns new gene_annotation_episode/bvbrc_genome_alignment_inputs.py and
bvbrc_genome_alignment_retained_records.py, corresponding tests with those
basenames, and verification/tool_graders_bvbrc_genome_alignment_extraction_2026-10-25/.
It implements extract_genome_alignment_inputs and the detached retained-record
validator. The validator's public export remains available from inputs.py for
C2; a separate module may hold its byte/envelope/receipt implementation.
The exact inputs and outputs are the accepted001/002 contracts. Original
occurrences, received request/log evidence, actual supplied FASTA records and
missing dependent relationships must remain distinct. No positive same-run
source, contig, feature or interval-map decoder is invented.

C2 owns new gene_annotation_episode/bvbrc_genome_alignment_associations.py,
tests/test_bvbrc_genome_alignment_associations.py, and
verification/tool_graders_bvbrc_genome_alignment_associations_2026-10-25/.
It implements bind_genome_alignment_artifacts with the added supplied_bytes
and retained_records keywords. It imports C1's retained-record validator and
root's unchanged C value validators. C1 completion is needed to execute their
combined path, not to implement independent native artifact association logic.
Actual output object association is separate from producer-byte identity;
native quantities survive missing source/member/interval relationships.

Both workers may read all necessary implementation but edit only their listed
new files. No registry, execution, controller, shared contract, permanent design,
inventory or prior verification changes. No network operation, scientific job,
installation, model call or live-service claim. Root owns the authenticated
host collection of records, provider forwarding, registration, pins and complete
selected episode-path verification. A/B output shapes stay unchanged.

Each worker must read the immutable goal in full and reread its PURPOSE and all
16 DESIGN PRINCIPLES verbatim after substantial source/native-output study and
before handoff. Relevant original principles include:

> Native-output parsers, metadata extractors and calculators operate on supplied data. They make no network requests, submit no jobs, invoke no LLM and choose no resource.

> Additional information needed for a calculation becomes an explicit acquisition requirement for the responsible episode.

> Measured zero, missing, not measured, failed, truncated and incompatible are different states.

> Preserve valid partial work and return specific structured failures that permit meaningful repair. Termination is not scientific completion.

Required tests include real current receipt shapes with explicitly synthetic
custody, actual envelope/snapshot bytes, original occurrence and parameter joins,
wrong task/request/receipt/byte identity, conflicting duplicate receipts, one bad
neighbor among valid records, missing and truncated logs/FASTA, repeated genome
occurrences, wrong formats, unknown same-run source and interval identity,
unchanged input values, and forbidden I/O/native/model calls. C2 additionally
exercises retained real Mauve/XMFA/sidecar bytes while clearly labelling synthetic
task relationships. Saved-source content and input relationship checks must use
the real C validators, not test substitutes. Report source hashes, filled values,
commands, results and unverified boundaries separately.
