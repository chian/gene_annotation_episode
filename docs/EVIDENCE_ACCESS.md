# Ordinary evidence operations

These tools execute selected work. They do not decide the biological conclusion,
choose comparative taxa, expand a search, accept an annotation or stop an Episode.
Scientific records, runtime actions and remote job state occupy the same Store;
source bodies and retired histories live on disk.

## Public protein searches

`public.hmmer.databases` reads the currently served databases and versions.
`public.hmmer.search` selects `phmmer` or `hmmscan`, the database and optional
native search parameters. Submission, protocol polling and the first result page
are one ordinary selected action. Polls are not extra scientific turns. Native
reporting/inclusion thresholds describe the search; all returned matches remain
available to reasoning without a further annotation cutoff.

The remote ID commits before polling. Interruption after acceptance resumes that
same search. An ambiguous failed/interrupted submission is recorded explicitly;
the adapter never assumes it failed remotely and silently submits again.
`public.hmmer.collect` resumes a known durable job after transport failure.
`public.hmmer.page` fetches a requested later page without changing query,
database or search parameters. `public.search.jobs` returns bounded pages of
current job ownership, including unresolved submissions. Completed and definitely
not-submitted attempts remain available through `active_only=false`; raw histories
are not loaded by this query. A definitively local preflight failure has no remote
handle to collect; an uncertain submission stays unresolved and is never silently
resubmitted.

Pure network operations run outside the Store thread and write transaction.
Publication and job transitions occur on the owning event-loop thread. Present
native query/job/algorithm/database identities are checked against the actual
selected work. Conflicting identities or unfinished/failed pages return
operational feedback and preserve diagnostic source bytes; they do not publish
target comparisons or completed-action yield observations. Actual HTTP error
status, headers, request identity and response bytes are retained, as are malformed
success-response bytes. Local exceptions remain local diagnostics rather than
fabricated HTTP responses. Owner feedback distinguishes phase, actual cause,
submission state, known handle and collectability. Status alone does not prove
that a POST was never sent or that a remote rejection was definitive. Later
explicit collection can recover a known job; earlier failure records remain
historical and are not relabeled successful.

New HMMER requests and their published source requests declare
`identity_version: "hmmer_single_fasta_sequence_v2"`. `query_sha256` hashes the
exact submitted FASTA UTF-8 bytes, including its header. `sequence_sha256`
hashes only the single parsed sequence: uppercase, whitespace removed, ASCII
symbols, with the FASTA header excluded. The request names both representations
and records the parsed symbol count as `query_length`. A present native input
echo may be a FASTA record or raw sequence; its actual sequence is checked under
the same normalization. Different headers or line wrapping do not invent a
different sequence. Missing optional native input remains unknown.

Historical unversioned HMMER requests retain their original rows, hashes, native
bodies and provider state. Current `describe`/`public.search.jobs` projections
identify their unsupported identity convention and report `collectable: false`
even when the remote handle is known. Attempted reuse, collection or paging
returns `hmmer_request_identity_version_unsupported` before interpreting a cached
result or contacting the provider. This is an operational compatibility limit,
not a finding that the historical query or biological result was wrong. Existing
saved tool-operation replay remains historical replay, and pinned older run
snapshots are unchanged. There is no migration or compatibility fallback.
Unversioned Rfam and explicit BLAST identities retain their own rules.

Reported domain coordinates become zero-based half-open intervals. In phmmer
the query is the model axis; in hmmscan it is the sequence axis. Comparisons keep
the actual external protein/profile as their source subject. Database labels,
taxa and native inclusion flags remain source assertions and measurements.
Searches assign neither function nor taxon to the unknown input.

The adapter follows the current [HMMER API documentation](https://hmmer-web-docs.readthedocs.io/en/latest/api.html)
and [provider OpenAPI specification](https://www.ebi.ac.uk/Tools/hmmer/api/v1/openapi.json).
Actual protocol/integration checks are under `validation/providers/` and
`validation/component-hmmer/`. Their known reference queries are explicitly
adapter calibration, not demonstrations of intelligent annotation.

## Reference acquisition and source reading

UniProt calls execute the installed skill client unchanged. A response observer
retains the actual HTTP entity bytes and selected pagination/release headers;
the source records the client path/hash and representation. Next-page cursors
come from the actual Link header. A compact helper preview is never substituted
for the full evidence. Public labels and computational annotations remain
attributed to the external source.

NCBI sequence acquisitions retain GenBank/GenPept bodies and optional exact
requested nucleotide intervals. The parser preserves fuzzy boundaries, ordered
compound segments, source qualifiers, topology and unavailable sequence. It does
not interpret an undefined CONTIG sequence as actual bases.

`reference.neighborhood` inspects an acquired nucleotide reference around one
selected locus tag, protein ID or coordinate. It preserves source version,
labels, strand, partialness and actual original-coordinate mapping. Duplicate
locations are ambiguous; missing fetched flanks are unavailable context. Wrapping
requires a fully represented circular source record. Source neighborhoods do
not establish target function, orthology or biological absence.

Literature search and full-text reading preserve the returned source and an
ordered paragraph projection. That projection omits headings, table cells and
other XML elements. `source.read` accepts `representation: "original"` to read
the exact retained XML, or `representation: "text"` (the default) for the paragraph
projection when available. Results identify the actual artifact/representation
and give an executable `next_query` that preserves it. Both representations can
supply exact byte anchors. Reads use bounded windows; digest verification still
streams the selected artifact. Malformed XML retains the acquired original source
and returns specific partial-projection feedback. Extracted assay subjects,
measurements and scientific assessments retain
their separate origins. No extra report composer or approval model is used.

Committing an exact textual anchor also streams the artifact digest, then reads
only the selected quote interval. A short quote no longer materializes its
entire source in RAM. The source association, original/text/stdout/stderr artifact
identity, half-open UTF-8 byte offsets and exact quoted bytes keep their existing
meaning. Corruption outside the quote still fails the original integrity check.
This changes neither the interpretation nor the contribution credited for it;
it adds no new tool or communication field. The pinned live investigation retains
its captured implementation until a separately prepared run uses this correction.

Full-text imports also retain primary `publication_identifiers` as typed DOI,
PMID and PMCID values. These come only from the article's direct primary
metadata, not cited references, subarticles, filenames or the requested ID.
URL-form DOI values and numeric PMC values are normalized; duplicate identical
IDs are retained once. The original bytes keep all reported metadata and
version details. The source's requested accession stays distinct from its
reported identifiers. These are provenance facts, not scientific findings,
evidence-independence judgments or credit contributions.

Malformed identifiers, conflicting IDs and a requested/reported PMCID mismatch
produce specific `metadata_issues` in the existing operation result. Multiple
primary-header candidates yield ambiguity feedback without silently choosing
one. Neither condition discards the original article or usable paragraph text.
Missing metadata remains missing; no identifier is fabricated from a citation.
The source record and ordinary state/export projections retain the optional
typed fields without introducing another state table, model call, observation,
controller rule or global-statistics channel.

Thirty-two affected checks passed in 56.12 seconds across source reading,
external evidence, public searches and annotation-score separation. They include
reacquisition of differently formatted bytes with the same primary publication
IDs, citation/subarticle exclusion, malformed/ambiguous metadata with retained
text, operation replay and unchanged scientific credit. Independent review
found and then confirmed repairs for first-header selection and oversized
numeric metadata failures; neither was observed in the live investigation.
The primary-article fixture is a 159,375-byte exact copy of already retained
PMC8874281 XML with its SHA-256/provenance recorded under `tests/fixtures`.
It replaces a test dependency on a deleted temporary run file; no network
retrieval was needed. This does not yet define semantic finding equivalence or
install the proposed investigation-progress credit rule.

## Actual sequence operands and views

Acquired external sequences and their derived products can be inspected, aligned,
translated, predicted and searched without acquiring original-input credit
membership. Native alignments retain both actual operand intervals. Sites
distinguish a measured gap from an unexamined position.

An unspecified input can use a selected protein search model directly; that
processing choice does not rewrite the supplied molecule declaration. Optional
`sequence.view` makes source-bound extracts and explicit orientations reusable.
RNA reverse complement preserves U; protein complement returns specific contract
feedback rather than applying a DNA transformation to amino acids.

## Explicit current limits

NCBI BLAST uses the same durable selected-search owner through
`public.blast.search` and `public.blast.collect`. It binds the original query/RID,
retains actual HTTP/ZIP custody and imports native source-bound HSP comparisons.
Submission still requires caller contact; no email is invented. The CLI selects a
shared caller-configurable provider-access directory for cooperating request
clocks. See [BLAST_EVIDENCE.md](BLAST_EVIDENCE.md) for exact units, source/DB
meanings, no-hit distinctions, offline evidence and current single-query limits.

These operations do not yet provide every needed evidence modality: raw-read
handling, full RNA/regulatory analysis, experimental-data analysis, chemical
models and authenticated BV-BRC/queued compute need further implementation.
Transport failures and absent modalities are not negative biological findings.
