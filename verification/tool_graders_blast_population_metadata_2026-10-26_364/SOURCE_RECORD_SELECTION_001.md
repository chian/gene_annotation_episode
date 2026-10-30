# Original source-record carrier and saved validation

This records workload B's deterministic implementation of PLAN_001 and the two
accepted addenda in packet 361. These are supplied source facts, not confidence
scores or new acquisition instructions. Synthetic examples are identified in
the accompanying verification record.

Only sequence metadata v3 has `population_source_records`. Each element retains
the unchanged closed `RetainedJSONRecord` shape: `source_ref`, `artifact_ref`,
`sha256`, `size_bytes`, `pointer`, and original finite JSON `value`. Source and
artifact identifiers remain separate namespaces. The old envelopes are unchanged.

The records retain the complete original JSON document at pointer `""` and every
selected assertion/census pointer that exists. They also retain the original
metadata payload root, original authenticated bundle root, and captured selected
database manifest root. The root bundle length comes only from the optional
v3 catalog field `bundle_size_bytes`, which C supplies from
`request.bundle_capture.size_bytes`. No JSON reserialization establishes an
original size or digest. If that fact is absent, no bundle root is fabricated.

The bundle is the unique distinct root record whose original `value.version` is
`native_blast_database_bundle_v1` or `native_blast_standard_database_bundle_v1`
as selected by the prepared invocation, and whose original `requested_job`
equals `prepared_inputs.invocation.request`. Exact duplicate records are
coalesced; conflicting identities or multiple distinct candidates are never
resolved by choosing a first record. The selected database is the unique
requested database having the declaration's `database_key`, target role, and
sequence-database preparation type. Its exact original database pointer must
have an available `prepared_inputs.source_relations` entry. Its original bundle
database capture, manifest artifact identity/digest/size, ordered native paths,
and captured file checks must agree with that requested database.

The selected manifest is the unique distinct root record with original value
equal to the requested database's complete `manifest` and original digest and
size equal to its `manifest_file`. The actual `-db` operand in the original
bundle `realized_argv` must equal the operand in the original requested argv and
the ordered native paths joined with the native single-space convention. Neither
operand nor semantic population identity is rewritten. Selection exposes the
original bundle source at `/requested_job/<job key>` and original manifest
source at `/identity`. Missing required records or unresolved custody produce
`selected_database=null`.

For each original selected metadata search, declarations remain in original
order, including duplicate keys, unresolved records and conflicting records.
The original metadata source and `/searches/i/database_population_associations/j`
pointer identify each declaration. A successfully resolved document key maps to
its authenticated document source. An unreceived explicit `received.source_ref`
stays its literal value; another unresolved document key stays the original wire
token. Neither token alone establishes authority. Its retained record is null,
and no successful source normalization-map entry is added. A missing pointer
keeps the same declaration and null pointed record, with the original root
retained where the source JSON is available.

C calls `validate_native_blast_database_population_associations(saved_list,
search=<the original normalized search>, prepared_inputs=<saved preparation>,
source_records=<all population_source_records from every v3 metadata envelope>,
database_profile=<the saved search profile>)` for each selected v3 sequence
search. This validates the closed input shapes, every retained root/pointer
relationship, the complete ordered original declaration list, provenance,
selected database fields, and exact retained assertion/census values. It returns
a detached unchanged list. It does not call extraction, population, native
parsing, calculation, file/network acquisition, or executable tools.

At the worker boundary C must independently authenticate each retained root's
source/artifact identity, original digest and original byte count against the
original request capture/catalog and sealed supplied source bytes. That includes
the bundle root against `request.bundle_capture` and the captured manifest root
against the original manifest source association. Internal equality in a saved
record cannot establish Store authority by itself. Standard saved metadata
validation also compares each pointed value to its retained supplied document.
The validated source relation must match the original prepared invocation and
request; a forged source relation or forged byte identity is not new evidence.

For a v3 sequence search only, B supplies `report_source.source_ref` from the
actual authenticated report catalog. C checks this against the original captured
report source and forwards it unchanged; A keeps it in `source_locator` beside
the original artifact, digest, member and complete SearchKey. Unselected
sequence siblings and domain/profile/VDB/old version sheets retain the original
four-field report-source shape. C must not derive a source from an artifact ID.

The assertion and census values remain actual source-asserted population facts.
An available association does not establish independent external verification,
annotation truth or calibrated confidence.
