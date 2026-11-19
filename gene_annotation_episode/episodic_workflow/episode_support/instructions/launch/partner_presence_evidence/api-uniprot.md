# Retrieve the assigned protein information from UniProt

Use the assigned accession or search query to obtain UniProt records needed for
the parent's investigation. Preserve the original query, scientific scope and
requested result. Decide which available request or retained response supplies
that result; neither a paper's citation nor a functional label replaces the
actual record. UniProt entries describe their source proteins. They do not
establish an experiment on the annotation target.

## Assigned request and available operations

This API resource uses service `uniprot` in `api_service_assignment_v1`. Its
closed request is either `{operation: "record", accession: "..."}` or
`{operation: "search", query: "...", size?: integer, cursor?: "..."}`. Search
size is 1–500; an omitted size is resolved to 10 in the actual command without
rewriting the parent's original request. Use only explicitly supplied accessions,
queries and constraints. Credentials are not required for these public reads.

| Operation | Available work |
| --- | --- |
| `api.uniprot.record` | In API execution, one record request for the assigned accession. |
| `api.uniprot.search` | In API execution, one page for the original query and any assigned cursor. |
| `api.uniprot.collect` | In results acquisition, publish the retained original response, or request the specifically selected cursor page. |

Each operation takes empty arguments; the original assignment and requested
result selector supply the meaningful inputs. No operation traverses pages,
polls, retries, changes the annotation target or interprets function in a private
loop. Use preparation and earlier outcomes to decide what useful work remains.

The public endpoints are `GET https://rest.uniprot.org/uniprotkb/{accession}`
and `GET https://rest.uniprot.org/uniprotkb/search` with the query, size, JSON
format and any selected cursor. A search returns one page; the response's
`Link` header supplies its actual next cursor when another page is available.
Retain that cursor and any reported total count/release information. Do not
construct a cursor from page numbers or treat a page as the entire result set.

## Reuse, publication and completion

A successful immediate response completes the assigned record/page request;
there is no remote job to invent or monitor. Its validated handoff retains the
actual response for the results episode. Empty result selector `{}` consumes
that retained response without another HTTP request. For a search, selector
`{cursor?: "...", size?: integer}` requests one explicitly selected page of the
same original query. A record result requires an empty selector. A changed
selector is different requested work, not permission to alter the query.

Publication retains original response bytes, request/transport provenance,
source subjects, sequences, source annotations and returned pagination. Inspect
the actual protein and organism behind a record before transferring a conclusion
to the target. Preserve conflicting source labels and missing evidence as such.
An empty search page describes that query and page; it is not proof that the
gene lacks a function. A failed request is an access failure.

Replay and cached publication reuse the same actual response. Repeated source
content does not create an additional contribution. Validated completion of the
original practical request sets its future expected credit to zero while
retaining the final actual gain. Completing one requested page does not complete
an unrestricted biological investigation. Keep HTTP time, scientific support
and the episode's own yields distinct.

## Sources

- [UniProt programmatic entry queries](https://www.uniprot.org/help/api_queries).
- [UniProt API documentation](https://www.uniprot.org/api-documentation/).
- [UniProt API paper: entry/search endpoints, page sizes and Link pagination](https://academic.oup.com/nar/article/53/W1/W547/8126256).
- Actual bindings: `api_uniprot.py`, `acquisition.py`, `tools.py` and the common
  `api_service_execution.py`. Instructions alone enable no callable operation.
