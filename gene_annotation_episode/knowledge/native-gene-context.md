# Native gene-context investigation (A103)

Start with actual sequence or genomic files. No candidate function is required.
`context.bind_locus` reads one explicit GenBank CDS or GFF3+FASTA coding locus.
Supply the record accession and one current locus tag, protein ID or coordinate.
GenBank nucleotide intervals remain in the returned record's native frame;
retained EFetch parameters map them to the original accession. GFF3 input needs
an explicit genetic code and actual FASTA, either separate or inline. A plain
protein string does not establish which genome or organism supplied it.

The host distinguishes caller-associated target genomic files from reference
leads. A model cannot change that association using an argument. Exact input
placements retain offsets, alternative loci and acquired-record limits. A
homolog locus remains a homolog locus even after its sequence map is received.

`reference.neighborhood` accepts an A103 binding with `left_bp` and `right_bp`.
It retains actual CDS indices, strands, regulatory footprints, signed gaps and
overlaps, circular origin handling and missing flanks. Gene and CDS rows are
not independent neighboring components. Source product names are annotations;
they do not become experiments or independently established activities.

`context.compare_neighborhoods` compares an explicit panel and fixed definition
of distance, intervening genes, orientation and order. The left CDS must be the
bound focal locus. Identify the particular right component with a received
protein reference. Supply sampling groups; closely related genomes can repeat
one pattern. Native counts, known exceptions, unknown rows and group-balanced
fractions remain separate. Required definition Sources establish the question
and provenance; they are not numerical measurements.

If the right component was not detected, use `right_feature_index:null` and an
actual scoped `right_detection_ref`. An empty coordinate window, absent source
label, truncated assembly or unexamined search cannot establish absence.

`context.detection_inventory` consumes a parent-delivered complete native phmmer
search. It requires its registered parsed snapshot, actual native output Source,
the exact searched FASTA Source, query component and genomic bindings. The
existing job-results `job_result_progress` fact can explicitly deliver native
source identities. An optional `neighborhood_ref` narrows the CDS inventory to
that measured window. Every relevant evaluable CDS must be in the searched
database for a negative result. Native inclusion criteria and excluded hits are
retained. Non-detection applies only to the recorded sequences and method; it
does not establish absence from unexamined replicons or an entire genome.
This operation collects an existing search; it launches no homology search.

`context.cooccurrence` uses actual detection receipts for both components in
each declared genome/record set. It preserves unknown rows, contingency counts,
effect direction, one-sided Fisher significance, the fixed-margin null and
unadjusted comparison status. Related samples sharing a group do not produce
an independent-row significance contribution. The declared bounded profile is
`L/(1+L)` for positive enrichment, where `L=-log10(p)`; raw values stay visible.
There is no inferred p-value from words such as "many" or "conserved".

`context.fusion` measures actual nonoverlapping regions in one coding product.
Each region needs its own component sequence and correspondence. Received
maps qualify the relevant region and create features/observations at mapped
original target positions. A conserved region or observed fusion does not by
itself establish the activities of every domain or a whole-protein function.

`context.association_channels` reads actual complete STRING provider captures.
It keeps `nscore`, `fscore` and `pscore` separate, with the actual endpoints,
taxon and pinned request. Endpoint names alone are insufficient: received
UniProt sequence/cross-reference records can establish their canonical protein
identity. Combined scores and expression, experimental and text-mining
channels do not substitute for A103 context channels.

`context.contrast` records a source-grounded comparison of alternative roles,
paralogs and optional modules. It references actual context measurements and
explicit incompatibility witnesses. It is separate from the main native
context-progress credit and creates no independent copy of its inputs.

Every scientific descendant remains A103. Offer decision-relevant received evidence and
specific missing operands through available shared operations to the immediate parent.
That parent chooses within its available child options or relays a specific need
upward. A coordinator with the relevant options can commission A101 for
missing sequence/family maps, A102 for structural distinctions, and A105 for
needed experimental properties as siblings. Reuse their actual specific maps
and subjects; aggregate axis scores are not component identities or distances.
An information publication starts no work and promises no reply. Retain unmet
needs in the requested typed return.
Profile columns require a physical protein-residue map before region transfer.

Native measurements and their per-use attachment sheets are graded by the host
at publication/receipt, before credit projection. `episode.credit` reads these
sheets and activates no grader. New evidence can qualify retained context
measurements without reacquiring a genome or repeating the context analysis.
Narrow issued grades do not implicitly grant private upstream files.

Use current `resource_context`: one small local job at a time, one CPU and at
most the caller's memory/scratch limits. Panels and windows are bounded.
Large searches require a configured remote/API/HPC resource and a shared need.
Do not keep resubmitting when the shared host is busy; preserve the prepared
handle and use actual admission/status information.
