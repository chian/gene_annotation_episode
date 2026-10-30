# Retrieve the assigned BV-BRC genome, feature or protein-family data

Run the public BV-BRC data query the parent assigned and return the source data
it requested. Preserve its collection, filters, selected fields, ordering and
page. Use the returned subjects and native values to identify what was actually
retrieved; a database's functional label does not establish the target gene's
measured activity.

The configured service is `bvbrc_data`. Its default Data API location is
`https://www.bv-brc.org/api`. A caller can explicitly configure another BV-BRC
deployment's base URL and request timeout. The query does not accept a URL,
credentials or arbitrary HTTP method. Public data was retrieved without an
authorization token during verification on 2026-10-23. That observation does not
guarantee future service availability.

## Specify the actual query

The request contains:

| Field | Meaning |
| --- | --- |
| `collection` | `genome`, `genome_feature` or `protein_family_ref`. |
| `filters` | An array of field/operator/value predicates. They are combined with AND. An empty array requests the selected collection's first assigned page. |
| Filter `field` | The actual BV-BRC field name, such as `gene`, `feature_id`, `genome_id`, `accession`, `pgfam_id`, `plfam_id` or `family_id`, as appropriate to the collection. |
| Filter `operator` | `eq`, `ne`, `gt`, `lt` or `in`. `in` requires a nonempty array of scalar values; the other operators require a scalar. |
| Filter `value` | A literal string, number or boolean, or an array for `in`. Values are encoded individually; text inside a value cannot add another RQL operation. |
| `fields` | Optional array of returned field names. If omitted or empty, the service's default fields are returned. Unknown or absent returned fields are not filled with invented values. |
| `sort` | Optional array of `{field, direction}` objects, where direction is `asc` or `desc`. Choose relevant stable ordering when comparing pages. |
| `limit` | Positive number of records requested on this page; default 25. This is a page-size operand, not an investigation quota. |
| `offset` | Nonnegative starting result offset; default zero. |

The original assignment keeps any omitted optional fields omitted. Defaults are
resolved only into the selected native request. The client sends one GET using
the documented RQL expressions, including `limit(count,start)`. It does not
retrieve subsequent pages automatically.

For example, locating reference records named ybhP can use collection
`genome_feature` and filter `{field: gene, operator: eq, value: ybhP}`. Such a
query can return proteins from many genomes. Retain each actual `feature_id`,
`genome_id`, organism label and replicon accession rather than treating every
row as the fixed gene under annotation.

To examine a particular genome's neighbors, use explicit genome and replicon
filters together with the selected coordinate interval. Preserve the source's
one-based inclusive `start` and `end` and separate `strand`. The client neither
converts them to target coordinates nor infers neighborhood membership,
homology, co-expression or functional association scores. For family queries,
keep PGF/PLF membership and family descriptions as the source's reported data.

## Choose an available operation

`api.bvbrc.query` takes empty arguments and retrieves the original assigned
query's one page. A successful response is already completed data retrieval.
There is no remote job identifier, queue or running state to manufacture, and
no status-poll operation for this service. Validated response metadata can
establish the requested usable handoff. The original practical endpoint and
configured controller determine closure; retrieving a page does not complete
the scientific annotation.

`api.bvbrc.result` takes empty arguments in the results episode. Its parent's
selector may contain only `offset` and `limit`; the original collection, filters,
fields and ordering remain fixed. An empty selector retains the original page.
When the selected effective page matches the original page, acquire the actual
retained response without another HTTP request. A different selected offset or
limit makes exactly one new data request. Changing the scientific query requires
an explicitly assigned request, rather than an unrecorded substitution.

## Read the actual page and preserve its limits

The JSON response is an array of native source rows. Result publication retains
the exact response bytes and request/response provenance and returns the rows
with page metadata. It creates no target assay, assessment or annotation. A
missing family, protein accession or condition field stays missing; it is not
evidence that the biological feature is absent. Zero returned rows is a
completed empty query result, not proof against a gene function.

Keep `Content-Range` verbatim. An observed response with two rows reported
`items 0-2/88287`; that end value must not be treated as an inclusive last row.
The next offset uses the requested offset plus the actual returned row count.
The total is reported only when the native header supplies it. A missing total
remains unknown. A continuation identifies another possible page; it does not
select another action or prove the query should continue.

Use observation times when comparing service facts. A monitor can report the
retained immediate response's terminal observation; there is no new remote job
to poll. Keep HTTP response time distinct from queue, execution and total
turnaround measurements. This provider does not invent those unmeasured
intervals or a duration forecast.

Failures preserve the actual response when one was received. HTTP errors retain
status, body and relevant headers such as `Retry-After`. A redirect is recorded
without following it. An incomplete body retains its partial bytes and cannot
establish a completed handoff. Requests are not retried automatically. Preserve
specific failure information and useful partial results so the responsible
episode can choose its next action.

## Distinguish public data from BV-BRC computational jobs

BV-BRC also has an authenticated computational AppService, separate from this
public Data API. The official AppService client uses
`https://p3.theseed.org/services/app_service`; BV-BRC's architecture documentation
also lists `https://www.bv-brc.org/services/app_service`. An unauthenticated
read-only request to the former returned the explicit JSON-RPC error
"Authentication required for AppService but no authentication header was
passed" during verification. The latter returned a Cloudflare HTML rejection;
that proxy response is different from an application authentication result.

AppService submission, monitoring and Workspace result operations are not
implemented or exposed by this `bvbrc_data` provider. Documentation about
`start_app` does not make it an available operation. Do not represent a public
data page as a submitted computational job or claim that authenticated BV-BRC
computations were tested.

## Primary sources

- BV-BRC Data API: https://www.bv-brc.org/api/doc/
- Genome features and field meanings: https://www.bv-brc.org/api/doc/genome_feature
- Protein-family references: https://www.bv-brc.org/api/doc/protein_family_ref
- Official Data API implementation and RQL protocol: https://github.com/BV-BRC/BV-BRC-API/blob/master/README.md
- BV-BRC service architecture: https://www.bv-brc.org/docs/system_documentation/system_architecture.html
- AppService specification: https://github.com/BV-BRC/app_service/blob/master/AppService.spec
- Official AppService client: https://github.com/BV-BRC/BV-BRC-Go-SDK/blob/main/appservice/client.go
