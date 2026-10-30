# Actual public HMMER service verification 001, 2026-10-22

Root executed one explicitly selected engineering `phmmer` job against public
HMMER database `pdb`, with `parameters={}` and `page_size=2`. The actual client
submitted the exact fixed target's translated protein, observed `SUCCESS`,
acquired page 1 and published that retained page through the existing importer.
The original selected submission was then replayed. Read-only publication checks
verified the exact original receipt and timestamp, three operation receipts and
captures, and all six published reference/observation witnesses. No further
verification phase or HTTP request was run to produce this report.

The [derived evidence manifest](/home/chia/repos/gene_annotation_episode/verification/hmmer_actual_service_2026-10-22_001/MANIFEST.json)
identifies every published file by SHA256 and byte size. This is **partial,
credential-free derived evidence**, not a byte-identical complete database or
self-contained replay capsule. The submit response included `Set-Cookie` with
cookie name `sessionid`; its value is absent from this publication. Original
working bytes remain in root-restricted mode-0700 custody. This publication
follows scopes 014 and 015 and leaves older implementations, reports and evidence
generations unchanged.

The script and six selected phase records use API002 runtime implementation pin
`9007ce019b0df13f122cdc53772b45e56684a39755b2e79c9027de2a451fbd1c`.
All six `sources-after.json` guards match their original 128-file source maps,
and a separate read-only source-file check matched that same pin. The pin hashes
sorted relative source paths, a NUL and each raw file SHA256; it is not the other
canonical-JSON source-map digest used in earlier evidence. The included frozen
source-input manifest has SHA256
`bed5cbb32250c45c725941ee4166b4b7fa376b10bded8d7350ed3cfe82cd341c`.
The separately owned correction-source capsule/report002 was pending when this
publication workload was assigned; its delivery is not established or bundled
by this actual-service artifact.

The reviewed script SHA256 is
`562c1f705ffeb924091c76c0d9cc2b75c3e5fd60635cac9f51237fa1f5f4dc7a`.
Its `PREPARATION.json`, `REVIEW.md` and `FILES.json` are retained as historical
pre-execution records. Their statements that no phase had run describe that
preparation checkpoint; the subsequent six actual phase directories and exact
stdout/stderr are retained separately. The compiled syntax-check cache is
intentionally excluded.

| Fixed input and selected binding | Recorded value |
| --- | --- |
| Original problem | `problem_9d89f9abcb43930a1bb557f1` |
| Original target | `input_a5c60b96717424cdf5138420`; ybhP/b0790, E. coli K-12 MG1655 |
| Original DNA | 762 nt; sequence SHA256 `62930707904f67975532ff43f609f98f64700a9afbbc3c5eb446e02f3a513f26` |
| Actual translated product | `product_c38b99fac815e0b58a215d21`; 253 aa |
| Recorded P0AAW1 witness / actual product SHA256 | `f0cdd3744b5bc986fd574175ecb7155c0ed57c7749098f20300735a3c849560a` |
| Submitted FASTA SHA256 | `c75b73f5116ac3883b08579431d5c200694e02715383c340a377bc3131c7deb6` |
| Exact normalized request SHA256 | `e69039baa601f3f38a421ce665bae2a842aa093b25d0ff9b99d19f39460c3876` |
| Provider job | `provider_job_cb683b6c3936f1045d8a9477` |
| Returned server UUID | `9f1d2433-cca8-43b5-8c52-d7d3927dee6f` |
| Caller registry / resource | `execution_registry_hmmer_service_verification_001` / `hmmer-public-service-verification-001` |
| Effective client-binding SHA256 | `7c3113045c9b8bd9d0613e12a5fd16eddbddb06fcb6b748b75f68d51dc1f2eb9` |

The seed was created at the previously declared new destination
`/tmp/hmmer-real-service-fixed-target-20261022-001` by the public
`prepare_fixed_target_seed` helper. The helper used canonical
`cases/gene_001/workspace` only as its documented read-only witness; it did not
construct a Store there or import old scientific/run state. Its receipt preserves
the complete original problem, input, intake indexes, roots and required artifact
bytes. It reports 11 initial references across separate tables: four artifacts,
two sources, and one each of input, material, parse attempt, collection and
collection member. These are custody references, not 11 ordinary `records` rows
or new scientific contributions.

The actual translation used `ToolRegistry.execute('sequence.translate')`, with
the case's code 11, strand `+`, frame 0, interval `[0,762)` and `cds=true`.
Its five original result references, product record and source/mapping records
are retained. Actual product bytes match the required witness digest. The
original source-witness preservation receipt reports unchanged main database,
existing empty WAL and SHM, with `observed_changes=[]`; it does not assert that
all read-only SQLite access is free of bookkeeping effects.

Each phase reconstructed an actual `PublicClients` and `ToolRegistry`, passed
that same registry/client/importer owner to `bind_public_search_ports`, and
compared the saved client preimage and digest. The existing client transport
timeout remained 90 seconds. Local settings remained 20 GiB RAM, 4 GiB scratch
and `wall_seconds=null`; no native compute job was selected. The engineering
resource/registry IDs, operation keys and database were caller operands; no
episode or infrastructure selected a substitute.

| Selected operation | Original operation receipt | Captured HTTP entity | Original local receipt time (UTC) |
| --- | --- | --- | --- |
| Submit | `provider_operation_0f3df1f711be460c6f3e4fb6` | HTTP 200; 46 bytes | `2026-10-22T06:11:14.189648+00:00` |
| Status | `provider_operation_68779feb2e08dad0a5afa1cb` | HTTP 200; 1,335 bytes; `SUCCESS` | `2026-10-22T06:11:46.634180+00:00` |
| Result, page 1 / size 2 | `provider_operation_f0e00434ed5151952299d862` | HTTP 200; 11,220 bytes; `SUCCESS`, cached | `2026-10-22T06:12:25.764593+00:00` |

These are three retained selected public-operation captures, not an observed
server-side physical request or redirect count. Their original response
retrieval times are retained separately from the local receipt times. No queue,
execution duration or remote event chronology was inferred. There was one
submission claim, one job/order/scope and three immutable operation receipts.
The later submit invocation reused its original operation key, returned the
entire exact original receipt including its earlier `observed_at`, and added no
claim, capture or operation receipt. The original receipt still reports its
original `accepted`/uncached facts even though the later authoritative job state
is `returned`; history was not refreshed or rewritten.

The no-network publication returned **11 distinct record references and six row
witnesses**. The six rows resolve to two references and four observations, with
the actual result source `source_5a6d2054e88addcb5beb882c`, original job, registry,
request digest, acquisition receipt and selector. The publication proof source
is `source_7ec3e597102a29e37a0d7c00`. Read-only checks validated the original
proof body's exact selector `{first_page:1,last_page:1,page_size:2}`, each row's
source and record type, observation subject/reference relationships, and its
native hit/domain ordinal. The exact raw result has two hits with domain-array
lengths `[3,1]`, agreeing with those four observation witnesses. The other five
returned references are actual source/context/term publications, not extra
reference/observation witnesses. Projection failures are empty.

The provider reported `page_count=2`. Only page 1 was acquired and published;
page 2 and complete result acquisition are unverified. One `SUCCESS` status was
observed in this service execution; no actual pending, failure, stall, repair,
polling sequence or reliability behavior was demonstrated. The explicit
no-network recovery command was available in the script but was not selected.

The publication validator used only `sqlite3` with `mode=ro`, `query_only=ON`
and one read transaction on the new workspace. It imported no application Store
or client and made no phase/HTTP/model/native/scoring call. It checked 21 final
ordinary records, the actual 17 artifacts, the original 11-reference seed,
request/FASTA/client/scope identities, all three receipts/captures, replay and
the six witnesses. No runtime tables, hypotheses, assessments, annotations,
interpretation accounts or native execution records were present. The single
`tool_operations` row is the actual translation.

That read-only inspection created an empty `state.sqlite3-wal` and a 32,768-byte
`state.sqlite3-shm` in the new working workspace. The main database stayed
byte-identical: 282,624 bytes, SHA256
`605f7213e38d585102ffbdd1243ccc1cef02e602b9acaa697f4179fab07de1b6`.
All pre-existing artifact/capture/seed bytes also stayed unchanged. These engine
bookkeeping effects are recorded in `WORKING_CUSTODY.json`; no sidecar cleanup,
application write, checkpoint, journal-mode change or chmod of the original
working records was performed by the publisher.

The token-free export preserves 54 exact phase-evidence files (392,141 bytes)
and 22 safe original workspace files (52,503 bytes), including all three exact
HTTP response entities, request FASTA, safe original artifacts and seed receipt.
Logical exports retain original scientific references, order/scope/request,
claims, immutable receipts and publication witnesses. The raw database, one
session-bearing snapshot artifact and the submit capture manifest remain in
private custody; their original paths, SHA256 values and sizes are listed as
intentional omissions. Three empty local lock files are separately omitted as
bookkeeping. The later reader-created WAL/SHM are recorded and not copied.

The two redacted transport derivatives have new filenames and hashes, with
explicit original-to-derived mappings. They are not stored under original
artifact content-addresses. Original receipt/source references to omitted
material remain unchanged and their public resolution limit is declared.
An internal scan compared every derived output with the private session value
without printing it and found no occurrence. No cookie-bearing contract001
metadata was copied. `MANIFEST.json` hashes the exact report copy and all other
members, excluding itself to avoid a self-hash cycle.

This establishes one actual external-service interface case: original fixed
input custody and translation, selected public submission/status/result ports,
safe acquisition/publication and immutable submission replay. It is not a
configured-model investigation, episode/controller demonstration, scientific
annotation, credited contribution, full-result acquisition or general service
authentication/reliability claim. No scientific interpretation of the returned
hits was made, and the fixed overall goal remains incomplete.
