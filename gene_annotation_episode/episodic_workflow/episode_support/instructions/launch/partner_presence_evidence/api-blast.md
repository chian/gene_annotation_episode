# Run the assigned NCBI BLAST search through separately selected requests

Run the original sequence search and retain the information needed to monitor
and obtain its results. Keep the registered sequence, selected program, database,
hit-list size, scientific scope and caller constraints fixed. Choose the next
preparation, submission, status or result request using actual outcomes. A
different database search or a replacement sequence requires the responsible
parent's assignment; service transport does not make that scientific choice.

## Assigned request and actual operations

This resource uses service `ncbi_blast` in `api_service_assignment_v1`. Its
closed request is `{subject_ref, program, database, hitlist_size?}`. Program is
one of `blastn`, `blastp`, `blastx`, `tblastn`, `tblastx`; its required input
molecule must match the registered operand. An omitted hit-list size resolves
to 50 in the native command without changing the recorded original request.
The caller's configured NCBI contact and shared provider-access directory are
required for the actual client. Their configured state is information available
before choosing this service; a contact value is not a model-facing credential.

| Operation | Actual selected work |
| --- | --- |
| `api.blast.prepare` | Resolve and validate the original sequence/settings locally, without HTTP. |
| `api.blast.submit` | Commit the selected request and issue one native submission. Retain its actual RID and reported RTOE. |
| `api.blast.status` | Obtain one status response for that original RID. Available to result acquisition as well as the service catalog. |
| `api.blast.fetch` | In result acquisition, fetch one native JSON2 response for the original RID. It performs no preliminary status poll or waiting loop. |

Each operation takes empty arguments and uses the original assignment/handle.
Submission includes operand resolution; a separate prepare action is useful
when its information informs the next choice, not a required first stage.
Results use empty native selector `{}`. Choosing a status observation and
choosing result retrieval are separate actions; the parent need not commission
another monitor before results acquisition can inspect readiness.

## Provider constraints and uncertain outcomes

NCBI's Common URL API uses `CMD=Put` to submit and `CMD=Get` with the returned
RID for status or retrieval. Retain the native response before interpreting it.
RTOE is the service's reported estimate, not a validated remaining duration or a
mandatory wait chosen by infrastructure. Preserve `WAITING`, `READY`, `FAILED`
and `UNKNOWN` without inventing queue position, throughput or completion fraction.
`WAITING` establishes an accepted unfinished search, not that native execution
has begun. `READY` can legitimately report no hits.

NCBI requires at least ten seconds between service contacts and at least sixty
seconds between polls of one RID. The client returns earliest-permitted timing
or explicit spacing feedback; no primitive sleeps or polls automatically. Use
those factual limits when choosing a permitted request, another useful action
or an available explicit wait. They are not a fixed episode polling cadence.

An unknown submission outcome is not proof that no job exists. Preserve the
original intent, response, handle and specific failure. Recovery does not repeat
the POST. A confirmed local not-sent failure and an uncertain remote submission
are different facts; the episode and parent need that distinction for repair.
An observation failure is not evidence that the search failed.

## Handoff, native results and interpretation

A validated original RID establishes the usable monitoring/results handoff;
the search may still be unfinished. Validated completion immediately sets this
practical assignment's future expected credit to zero, retaining the final
actual gain. Monitoring and results operate independently on that same work.

Result publication requires the original actual submission response and matching
query/program identity. A READY status response is protocol information, not a
scientific result payload. Fetch retains the original JSON2/archive bytes and
native member bytes, reported program version, requested/effective database,
reference subjects, HSP scores, E-values, alignments and coordinate units. Native
database alias resolution remains reported source information; it is not a
silent change by episode infrastructure. Keep valid HSPs and their source when
another HSP cannot be projected. A native no-hit result is scoped to this
submitted operand and recorded search settings, not biological absence.

The scientific parent interprets sequence evidence and its transfer limits.
Acquisition assigns neither function nor lineage. Source custody, operational
progress, duration measurements and scientific annotation support remain
separate. Repeated publication does not repeat the physical search or add new
credit for the same content.

## Sources

- [NCBI BLAST developer usage guidelines](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html).
- [NCBI BLAST Common URL API](https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html).
- Actual bindings: `api_blast.py`, the single-request `PublicClients.blast`,
  `blast_search.py` and native publication in `tools.py`. The API episode does
  not wrap the older `RemoteSearches.search/collect` polling loop.
