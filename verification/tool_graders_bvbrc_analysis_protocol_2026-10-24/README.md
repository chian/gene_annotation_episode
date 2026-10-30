# C1 native RPC preparation and support records

This is verification of pure protocol functions, not a deployed scientific
tool or an episode-path integration. No network request, credential search,
submission, Workspace creation, input upload or native analysis was performed
for this workload. `EXAMPLES.json` contains filled, explicitly synthetic
source-derived records and one replay of the already retained real HTTP 403.
`SOURCES.json` identifies the inspected official implementations and hashes.

The immutable goal attachment was read in full and its objective and all sixteen
design principles were reread verbatim after AppService, Workspace and MinHash
source study and before handoff, followed by the current additive contracts.
Contracts 001 and 002 retain separate ownership of protocol, scientific grading,
application preparation and transport/integration.

## Interfaces and record meaning

`prepare_rpc_request(method, params, *, request_id)` validates only the nine
selected primitives and returns the original native method and ordered operands
in a detached JSON-RPC 1.1 request. It inserts no defaults or credentials and
performs no operation. Invalid input raises `RPCValidationError`, a `ValueError`
subclass with a stable `code` and a list of `{code,path}` diagnostics; exception
messages do not serialize supplied operands. Explicit zero, string, null and
omitted values are not interchanged. Flags declared as Workspace integer
booleans require integers zero/one, not Python booleans or strings. MinHash's
native integer flags retain their supplied integer values and native truthy
meaning. The native maximum-hit count is never used to trim a response.

`validate_start_parameters(value)` is shared with C3. Diagnostics are rooted
at `$.start_parameters`. It accepts declared fields and the implementation's
`user_override` and `constraint` strings. `preflight_data` is retained as the
actual JSON object, including nested/numeric values. Neither validation nor
`disable_preflight` establishes staff permission. Unknown StartParams fields
are invalid; application-specific unknown fields belong to C3's separate
qualification.

`decode_rpc_response(content, *, method, request_id, http_status)` consumes
supplied bytes/text and returns exactly `{status,value,native,diagnostics}`.
It recognizes 1.1 `version` and 2.0 `jsonrpc` envelopes explicitly, checks the
original correlation ID without conflating strings, numbers, booleans and
null, and requires one return value. A 1.1 `error:null` may accompany success;
2.0 result/error membership is mutually exclusive. Missing/unsupported versions,
duplicate JSON members, wrong IDs, malformed arity, HTTP errors and native
errors cannot yield a successful value. The full parsed native document and
error object remain available. Non-JSON, missing bodies and numbers outside the
finite Python-float representation are diagnosed separately; the latter has
`unrepresentable_json_number`, not a fabricated finite measurement. Exact bytes
remain the transport's required retained artifact. Parser output does not prove
original-request custody or complete transfer.

`parse_task_records(value, *, operation, requested_task_ids=None)` preserves
the distinct source representations:

| Projection | start_app2 native source | query_tasks native source |
| --- | --- | --- |
| task_id | id, original integer/string | id, original integer/string |
| application_id | application_id | app |
| native_state / state_field | state_code / `state_code` | status / `status` |
| parameters / parameters_field | serialized params / `params` | decoded parameters / `parameters` |
| submit_time, start_time, completed_time, elapsed_time | only if actually supplied | original strings/null/absence |
| storage_location | only if actually supplied | original active/archive or other supplied string |
| output_path, output_file | actual supplied values | only if actually supplied |

Each row also has `record_index`, `task_map_key`, `native_record`, `diagnostics`
and `status`. No submission time is inferred from a request timestamp or SQL
side effect. `req_runtime` remains only in the raw receipt and is not observed
duration. Unknown native states are retained without converting them into a
known state. Missing requested tasks are unknown, not failed/completed tasks.
Task-map keys must match the actual record ID's decimal spelling; the original
integer/string representation is retained. Leading zeros are not silently
normalized into a different requested identity.

`parse_workspace_records(value, *, operation, requested_paths=None)` retains
12-field ObjectMeta success tuples and a possible thirteenth native error
field. Named fields are `name`, `type`, `parent_path`, `creation_time`,
`object_id`, `object_owner`, `size`, `user_metadata`, `automatic_metadata`,
`user_permission`, `global_permission`, `shock_url` and `error`. The Workspace
UUID and Shock URL are distinct. Size is the actual integer; folder zero does
not establish a complete child count. Metadata's nested native values remain
unaltered. `native_metadata` and `native_record` retain the exact original
tuples. An incomplete tuple can retain valid fields without becoming a valid
complete tuple.

Each row includes `record_index`, `row_index`, `listing_path`, `request_index`,
`request_indices`, `requested_path`, `object_path`, `diagnostics` and `status`.
`ls` keeps every original map key and each local row position. Empty-directory
keys may be absent natively, so the parser does not invent missing pages.
`create` matches all supplied path/UUID identities against actual returned
metadata. Ancestors receive no invented requested-object association. Duplicate
requested paths keep all request indices; duplicate created matches remain
ambiguous. An omitted existing folder is recorded as not returned, not a native
creation failure. `get` preserves native positions, checks the requested path
or object UUID and diagnoses response-count differences. Workspace-UUID aliases
need an explicit mapping not supplied by ObjectMeta; the parser does not guess
that mapping.

For `get`, `content` retains actual ObjectData and `content_kind` distinguishes
not_returned, native_null, inline_text, directory_placeholder, shock_url and
invalid. The metadata's Shock URL determines the native URL branch; a text file
that happens to contain a URL is not relabeled. A content URL is not file bytes.
`get_download_url` retains one URL or native null per returned position, with
its requested path when supplied; it infers neither expiry time nor bytes.

Both support parsers return `{status,records,native,diagnostics}`. Every invalid
row retains its original position/raw value. Row status is `ok` or `invalid`;
top status is `ok` with no diagnostics, `partial` with diagnostics and at least
one valid row, or `invalid` otherwise. These are format/association outcomes,
not scientific completion or annotation support. Optional absent fields project
to null; raw records distinguish absence from explicit native null. A caller
must examine diagnostics and actual requested associations before using a row.

## Additive source corrections

The original native study remains unchanged. Exact source facts found during
C1 implementation were reported to the parent before coding and recorded in
contract 002:

* WorkspaceImpl `ls`, lines 3865–3867, removes the trailing slash from the
  metadata parent-path field itself for `fullHierachicalOutput=1`. Derived
  object paths insert exactly one separator while preserving native parents.
* `_make_shock_node_public`, lines 797–812, actually grants the current user
  read ACL in this revision. It does not make the node public. Content access
  still has possible native ACL effects.
* Workspace `create`, lines 2536–2557, consumes `downloadFromLinks`; the spec
  declares `downloadLinks`. The implemented field is accepted unchanged;
  `downloadLinks=1` yields `declared_but_unused_native_option`; zero is retained.
  An explicit native link-acquisition option can have that native effect if
  executed; no preparer/parser downloads anything.
* SchedulerDB `create_task`, lines 141 and 175, consumes `user_override` and
  `constraint` in addition to the declared StartParams fields.
* `_create_object`, lines 1183–1196, accepts supplied array/object ObjectData and
  JSON-encodes it natively. Preparation preserves those actual inputs rather
  than converting them to strings. Null/omitted metadata and data also remain
  unchanged; native defaults are never inserted by C1.

## Verification and limits

Run `.venv/bin/python -m pytest -q tests/test_bvbrc_analysis_protocol.py`.

The initial runs passed 78 tests; the final run passed 79 after adding an
underflow case that must not turn a nonzero native number into zero. These cover all nine
request primitives, exact native parameter positions, numeric/string/zero/null
distinctions, integer flags, native spelling, both synchronous MinHash modes,
HTTP/RPC error separation, native versions, complete error details, wrong IDs,
absent responses, partial task/object records, unordered creation results,
duplicate/missing associations, URL-versus-content distinction and no-network
execution. The source-derived fixture with elapsed_time `00:02:03` retains that
string; no numeric 123-second runtime or queue estimate is invented. A newly
created upload-node fixture has actual supplied size zero, without claiming
that any input bytes were uploaded. The retained upstream Mash row has the
native `41/1000` token; it is placed in an explicitly synthetic BV-BRC envelope
without scientific recalculation here.

The only real retained HTTP response is the earlier Cloudflare HTML 403. Its
replay produces `http_error` plus `invalid_json`, never `native_rpc_error`.
It does not establish service authentication failure, application failure or
current native availability. Successful AppService/Workspace/MinHash RPCs,
live submissions/uploads/downloads and complete episode communication remain
unverified by this workload. C4 owns transport, request/receipt custody,
execution binding and requested typed returns; C2 owns MinHash numerical
calculations; C3 owns scientific application preparation. These pure-module
tests do not complete any scientific-tool/accounting row.
