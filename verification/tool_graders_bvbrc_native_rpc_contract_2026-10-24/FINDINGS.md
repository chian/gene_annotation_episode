# BV-BRC native primitive contract findings

This is a read-only contract study, not a working service binding or scientific
grader. `CONTRACT_CANDIDATES.json` contains 13 primitive rows with exact native
argument positions, source references, response shapes, retained-data needs,
error states and explicit unknowns. `SOURCES.json` records pinned official source
URLs, revisions, retained paths, sizes and SHA-256 values.

The authoritative goal attachment was read in full and its SHA-256 matched
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The objective and complete design-principles block were reread between the
AppService, Workspace and MinHash studies, before writing these contracts and
before handoff. The complete current contract was reread during final review.
This record does not change the goal, episode ownership, continuation, numerical
scoring requirements or the separate application-artifact workload.

## Established native signatures

| Primitive | Ordered native arguments / transport |
| --- | --- |
| `AppService.enumerate_apps` | `[]`; zero native arguments |
| `AppService.start_app2` | `[app_id:string, params:object, start_params:StartParams]` |
| `AppService.query_tasks` | `[task_ids:list<string>]` |
| stdout | `GET {app_service_base}/task_info/{task_id}/stdout` |
| stderr | `GET {app_service_base}/task_info/{task_id}/stderr` |
| `Workspace.ls` | `[{paths, excludeDirectories?, excludeObjects?, recursive?, fullHierachicalOutput?, query?, adminmode?}]` |
| `Workspace.get` | `[{objects, metadata_only?, adminmode?}]` |
| `Workspace.get_download_url` | `[{objects}]` |
| `Workspace.create` | `[{objects:[[path,type,metadata,data?,creation_time?],...],createUploadNodes?,overwrite?,permission?,...}]` |
| Download | One explicit `GET` of the retained download URL; optional single byte range |
| Upload | One explicit `PUT` to the retained created Shock URL, multipart file field `upload` |
| `Minhash.compute_genome_distance_for_genome2` | `[genome_id,max_pvalue,max_distance,max_hits,include_reference,include_representative,bacterial,viral]` |
| `Minhash.compute_genome_distance_for_fasta2` | `[ws_fasta_path,max_pvalue,max_distance,max_hits,include_reference,include_representative,bacterial,viral]` |

Both MinHash signatures have one string, two floats, then five integers.
Workspace native booleans are integer booleans. The misspelling
`fullHierachicalOutput` is native. `Workspace.ls` has no native `limit`, cursor or
offset in this inspected implementation. Complete structure fields and their
source qualifications are in the JSON rows; the table is only an index.

Official source revisions inspected:

- [BV-BRC/app_service](https://github.com/BV-BRC/app_service/tree/90c6a00d5a75f0597a53505a31b4d248767ba1d2)
- [BV-BRC/Workspace](https://github.com/BV-BRC/Workspace/tree/f3a13dc5abc43de6951e2dbc4c4407463b8264b0)
- [BV-BRC/p3_minhash](https://github.com/BV-BRC/p3_minhash/tree/2220db387ee6b068993e1765138ac76b853ccde4)
- [marbl/Mash](https://github.com/marbl/Mash/tree/5df1f984a06d568b4c47540042a0e619fd1f7bdd)
- [MG-RAST/Shock](https://github.com/MG-RAST/Shock/tree/9419e651c08a639466c2c57cf51c012eae3e40e2)

These are public source revisions, not confirmed deployed service versions.

## Consequences for effects and replay

Creating an input node, uploading its bytes and submitting a scientific task
are three selected primitive operations with different receipts and identities.
`Workspace.create(createUploadNodes=1)` creates the Workspace object and an empty
Shock node. Its size-zero metadata does not mean the input has uploaded.
The separate multipart `PUT` supplies bytes. `start_app2` creates a task after
native preflight. No application launch was invoked in this study.

`Workspace.create` can also create missing ancestor directories and return their
metadata. Its implementation iterates grouped hashes rather than preserving
input order. Match the target by its actual path and type, and retain the object
UUID and distinct Shock UUID. Do not assume that the first result is the selected
input. An explicit overwrite may delete an existing entry before replacement;
there is no established all-or-nothing transaction or idempotency key.

The four requested effect labels do not cover every native side effect:

- `Workspace.get(metadata_only=0)` can change Shock ACLs before returning a node
  URL; metadata-only access avoids this content-acquisition path.
- `Workspace.get_download_url` inserts expiring download-key records and may
  grant Shock read access. Its response is a transient transfer capability.
- MinHash FASTA internally acquires a Workspace file and can inherit that ACL
  effect. It still returns directly and creates no AppService task.

The affected contract fields disclose this gap rather than pretending those
paths are always mutation-free. Final review corrected the FASTA2 effect from
`none` to `null` with the explicit ACL qualification, consistent with
`Workspace.get`. This does not implement a new effect taxonomy
or workflow layer. No mutating native operation was called. A lost mutation
response remains an uncertain outcome; a newly issued request is not proven
safe replay. In particular, native RPC correlation IDs are not idempotency keys.

## Submission receipt, task status and logs

`start_app2` declares a `Task` result, but the current inspected path returns the
raw `SchedulerDB.create_task` hash through `p3x-submit-job`. That hash has
`id`, `application_id`, `state_code`, `owner`, serialized `params` and `app_spec`,
and request/resource fields. It does not have to resemble `query_tasks` output.
`query_tasks` separately returns a map of formatted task records with `app`,
`status`, decoded `parameters`, timing strings and `storage_location`.

`query_tasks` converts missing database timestamp sentinels into empty strings.
`elapsed_time` is SQL `TIMEDIFF(finish_time,start_time)`, returned as a string only
when both timestamps are recorded. It is not numeric seconds, queue wait or
total turnaround. This query does not add a timezone. The retained schema's
states are evidence, not an exhaustive current enum. No successful live task
record was acquired. No progress metric or task error reason is returned by
this method.

For stdout/stderr, `_task_info` returns the full file through signature-redacting
`sed` with HTTP 200. It does not read `Range`, emit `Content-Range`, or provide an
offset cursor. Requested byte windows must remain distinct from observed
responses. The returned redacted bytes are not offsets into an unredacted
original. A log may still be growing. Authentication is required and the source
checks task ownership or administration before file access.

## Workspace acquisition details

The current `ObjectMeta` spec has 13 fields, including trailing `error`; the
success generator currently emits 12. Field 2 is a parent path in the
implementation despite full-path wording in the spec. Field 11 is the Shock URL.
Preserve a possible trailing error rather than silently discarding it or
requiring it on every success.

`Workspace.get(metadata_only=1)` returns `[ObjectMeta]` per requested object.
The content form returns `[ObjectMeta,ObjectData]`; for a Shock object,
`ObjectData` is a URL, not scientific file bytes. Folder data may be an empty
string. `get_download_url` returns URLs in input order, with null for some
non-file entries. The configured lifetime is not in the response; one hour is
the source fallback, not an observed universal expiry.

The Workspace download implementation understands one `bytes=start-end` or
`bytes=start-` range, using inclusive byte endpoints. It emits 206 with
`Content-Range` and `Content-Length`; malformed/unsupported ranges can fall
through to a whole-body 200. Start-out-of-bounds/416 handling is not established.
The Shock-proxy branch can send success headers before its upstream transfer
finishes. Actual body length, source reported size, partial-read state and
requested versus observed range must remain separate. ETag is not supplied by
the inspected download method and must not be invented.

The native BV-BRC upload client uses a multipart `upload` part and HTTP PUT with
OAuth authorization. The retained official Shock controller returns a separate
`{status,data,error}` envelope. It is not JSON-RPC. Its node `id`, file size and
checksums, when supplied, are explicit transfer validation data. No live upload
or node receipt was acquired.

## Direct MinHash quantities

FASTA mode accepts a Workspace path, copies the file server-side and invokes
`minhash-search`. Genome mode selects an existing sketch, downloaded contigs or
Data API contigs. Native rows are:

`[genome_id, distance, pvalue, counts]`

The last three fields originate in `mash dist`. Perl splits the text and does
not explicitly coerce distance or p-value to JSON numbers, so the actual
number/string representation needs a real reply before parser binding.

For a valid count token `x/s`, retain the original token and both integers.
`x` counts matching sketch hashes; `s` is the compared sampled union count.
Their ratio is estimated Jaccard similarity. It is neither base coverage nor
read/genome population size. Mash's distance derives from that Jaccard value
and actual k-mer length. Its p-value uses the pair's lengths, alphabet, k and
counts under a random-overlap model. Those omitted inputs cannot be invented
from the returned four fields. Native p-value zero may reflect floating-point
rounding/underflow; it is not calibrated annotation confidence.

A retained **upstream Mash native test fixture**, not a BV-BRC service run,
contains `distance=0.12101`, `pvalue=4.48626e-214`, `counts=41/1000`.
The independently checkable count components are 41, 1000 and `41/1000=0.041`.
No scientific result for a user sequence is claimed. Full native distance and
p-value recalculation requires explicit missing sketch/sequence metadata.

The service cap loop permits up to `max_hits+1` rows. Genome mode subsequently
filters returned IDs through the Data API and does not refill missing rows;
FASTA mode does not apply that filter. The search script sorts by distance and
then genome identifiers, can skip unrecognized sketch IDs, and does not dedupe
across reference collections. Pipe exit statuses are not comprehensively
checked. Consequently, an empty reply is not sufficient to prove a successful
complete negative search. No total-hit count, truncation flag, reference release
or actual search-population size is returned.

## What actually ran and what remains

Official public files were fetched by bounded selection and retained. Existing
boundary findings were read; the earlier MCP wrapper audit was not repeated.
No credentials were inspected, no SSH was used, and no input was uploaded or
scientific job submitted. No reference checkout, production code, historical
notes or accounting row was modified.

One unauthenticated read-only JSON-RPC POST actually ran at
`2026-10-24T22:46:13.937710+00:00`:

- URL: `https://www.bv-brc.org/services/app_service`
- Method: `AppService.enumerate_apps`, params `[]`
- Observed: HTTP 403, HTML, `Cf-Mitigated: challenge`, 5,646 body bytes
- Retained request, complete response and observation metadata:
  `observations/enumerate_apps.*`

This is a front-door Cloudflare denial, not evidence of a JSON-RPC method error,
an invalid credential, application availability or a successful native call.
No alternate endpoint was tried.

Outstanding evidence is a successful deployed catalogue response, authorized
task/status/log and create/upload/submission examples, complete task-associated
Workspace artifacts, and MinHash response/reference-sketch metadata. The
application-specific parameter and native scientific artifact schemas remain the
separate worker's responsibility. No parser/calculator, mutation replay,
production path or episode communication was implemented or tested here.

Local verification is limited to JSON readability, the 13 fixed primitive
identities, required handoff field presence, retained-source hashes and the
native upstream count calculation. It is recorded in `VERIFICATION.json`.
