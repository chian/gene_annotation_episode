# Durable BLAST evidence for selected unknown material

`public.blast.search` accepts `subject_ref`, one of `blastn`, `blastp`, `blastx`,
`tblastn`, `tblastx`, a requested `database`, and optional `hitlist_size` (default
50 at this tool boundary). `public.blast.collect` accepts only the persistent
`job_ref`. The old episode-facing submit/status/fetch interfaces are removed;
there is no unbound RID plus newly chosen subject interface.

The selected subject can be an actual original sequence/read, mapped derivative
or registered external evidence sequence. A library container is never a sequence.
An original operand must fit the assigned measurement scope; the adapter does
not crop it or enlarge the scope. Optional `sequence.view` can create an explicitly
chosen bounded operand. No known taxon, reference subset or acquired family is a
prerequisite. Choosing a search model does not rewrite caller molecule declarations.

## One owner and one ordinary action

The existing `RemoteSearches` owns one durable intent, actual subject, FASTA and
sequence hashes, program, requested database, hitlist setting and selected
processing model. It commits the intent before the one submission. Exact returned
submission bytes, RID and optional RTOE are durable before polling. Its existing
protocol loop waits on that same handle. Protocol waiting, status checks and result
retrieval form one selected ordinary action, with no private Episode, automatic
scientific followup, new controller or hidden stopping budget.

Interrupted accepted jobs resume that handle. A failed or interrupted POST with
unknown outcome is not resubmitted. Only a known local preflight establishes
`not_sent`, including missing caller contact or missing configured transport.
Transport/protocol failures retain exact response diagnostics and useful owner
feedback. Explicit collection may recover an accepted handle; an earlier failed
attempt retains its original outcome. Cache/replay does not duplicate scientific
records. `public.search.jobs` supplies operational handle/state metadata.

Contact comes only from caller configuration `[public].ncbi_email` or the existing
`NCBI_EMAIL` fallback. Nothing invents a contact or authentication. Offline fixtures
are labelled synthetic, including their non-routable example contact.

## Actual request timing and native bytes

The adapter executes the installed BLAST skill's single-request primitives. Its
ready-result primitive performs exactly one result GET; the helper's ordinary
fetch operation would first issue another SearchInfo request. The shared owner
already obtained actual READY status. It does not run the helper's autonomous
`run` loop or change the installed client.

An observer preserves each actual HTTP entity, response metadata and prepared
request bytes, plus installed script path/hash. ZIP bytes are retained intact;
the helper's merged/reserialized JSON is not labelled original HTTP. Received
entities remain usable for native validation even if a compact helper projection
fails. HTTP errors and malformed native output remain diagnostics with original
bytes, not biological negatives or fabricated HTTP successes.

The CLI selects `[public].provider_access_dir` once. Its default is
`~/.cache/gene_annotation_episode/provider_access`, shared across workspaces.
Explicit library callers configure `PublicClients(access_dir=...)`; ToolRegistry
inventories do not supply a hidden workspace-specific BLAST transport default.
Cooperating clients using this directory share a locked request clock advanced
conservatively at worker completion/failure before lock release (a slow worker
cannot make its early reservation appear to be an old HTTP contact): every
HTTP operation has the 10-second floor and status polling for one RID has the
60-second floor. RTOE informs the first protocol wait. The shared owner schedules
requests; a racing caller can still receive precise not-sent spacing feedback.
Automatic HTTP redirects are disabled for these single-request operations. A
3xx response retains its body and Location as `provider_redirect_not_followed`
feedback; no unspaced redirect request is issued. No failed POST or external
failure is automatically retried. Effective directory
and scope are exposed in catalog/transport metadata. This coordinates configured
clients, not unrelated applications or all traffic from a machine/IP.

## Typed measurements and source identity

The supported native result is one JSON2 database-search report, either direct
JSON or one payload in a JSON2 ZIP/manifest. Original archive, exact JSON member
ordinal/name/bytes and submission source use existing forward `parent_source_refs`,
so normal export carries their actual custody. No new exporter or result composer
is introduced. Program and present query title/length are checked against the
committed request. Service-generated `query_id` is not mistaken for the FASTA
subject ID. Requested database and actual `search_target` remain distinct: native
resolution such as `nt` to `core_nt` is not falsely rejected as a wrong job.
Native `report.version` is BLAST software provenance; database release remains
unknown rather than borrowing that software version.

Each independently valid HSP becomes a source-bound `comparison` with the actual
query subject, a source-local reference hit, separate query/reference operand
intervals and available numeric measurements. Multiple descriptions of one native
hit remain aliases/source metadata, not separate independent matches. No full
reference sequence is inferred from the gapped `hseq` alignment. A known native
hit length permits bounds checking only for this trusted native reference operand;
ordinary sequence execution still requires actual complete sequence bytes.
`has_exact_mapping` returns false for a reference without sequence bytes, so an
ordinary inferred transfer can preserve its native operand bounds and unavailable
source traversal without crashing projection or inventing a physical source map.

Native one-based inclusive endpoints normalize to
`[min(from,to)-1,max(from,to))`. Original endpoints, strand/frame and exact native
report/hit/HSP locator remain in the constrained, host-only `native_blast` field.
Optional frame integers, including zero, remain source metadata rather than
becoming frame-consistency admission rules. That field is excluded from the
model-authored observation schema while remaining in authoritative native records. A blastx or
tblastx query interval is already in original nucleotide positions, so there is
no additional multiplication by three. `model_unit=aa` remains explicit when the
alignment translates an axis. Native coordinate units are separately recorded.
For an unspecified original, physical units remain its immutable `symbol` unit.
A nucleotide reference hit does not establish DNA versus RNA: it remains
molecule `unspecified`, generic physical unit `symbol`, with native nt coordinates
and alignment unit explicit. Later actual sequence acquisition is separate work.

All reported matches remain available; there is no added identity/evalue cutoff,
annotation selection, function/taxon transfer or scientific acceptance verdict.
Optional numeric fields remain absent if unavailable; actual zeros remain zero.
Malformed independent HSPs return exact row feedback while valid rows and original
sources survive. The ordinary output previews twelve HSP rows, with complete typed
state accessible through existing query tools and native details in source bytes.

An explicit native `hits=[]` is distinguishable from omitted hits. NCBI's native
Search schema declares hits optional; omission retains unknown hit-count meaning,
not a fabricated zero-hit conclusion. Native messages are preserved without
classifying arbitrary messages as negatives. READY status never replaces full
native result/query validation. Even an explicit empty hit array means only no
reported hit in this operand under the recorded provider search; it cannot prove
absence from an organism or from other databases/settings.

Credit is unchanged. Acquisition, status activity and parsed hit counts earn no
annotation credit. Reasoning must use actual observations and current assessments/
annotations; existing exact member-local geometry and source identity project
that recorded contribution. Ordinary controlled parent forms remain unchanged.

## Evidence and current limits

The tests use synthetic JSON2, ZIP, pending/failure/cancellation and malformed-row
fixtures, actual local Stores and the actual installed client under a local HTTP
stub. No public BLAST search or model call validates this implementation yet.
The checked API/source references are the current
[NCBI Common URL API](https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html),
[developer usage rules](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html),
and [native result schema](https://raw.githubusercontent.com/ncbi/ncbi-cxx-toolkit-public/master/src/objects/blastxml2/blastxml2.asn).

Multiquery/iterative/bl2seq result reports, arbitrary BLAST parameter surfaces,
automatic reference/taxon acquisition and large-library BLAST scheduling are not
implemented by this slice. Unsupported/malformed wrappers retain their received
bytes and feedback. There is no claim of a scalable full-library BLAST service,
biological annotation accuracy or completion of the build goal.
