The frozen API001 source has two concrete response-handling gaps: a documented pending/null result is classified as invalid before the not-ready branch, and malformed top-level JSON can escape as AttributeError without an operation receipt. Neither finding was obtained by submitting work to the public service.

The full documented path/parameter comparison remains in [comparison.md](comparison.md). This second record adds the explicitly authorized database-capability GET and the actual local malformed-status probe. Earlier raw entities and comparison records remain unchanged.

At 2026-10-22T05:54:27.174411+00:00, [the exact OpenAPI-defined database metadata endpoint](https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/databases) returned HTTP 200 with these values:

| ID | Type | Observed status | Version | Advertised release date |
| --- | --- | --- | --- | --- |
| pfam | hmm | enabled | 37.2 | 2025-01-01 |
| refprot | seq | paused | 2025_01 | 2025-01-01 |
| swissprot | seq | paused | 2025_01 | 2025-01-01 |
| uniprot | seq | paused | 2025_01 | 2025-01-01 |
| pdb | seq | enabled | 03.25 | 2025-01-01 |
| rp15 | seq | paused | 2024_04 | 2025-01-01 |
| rp35 | seq | paused | 2024_04 | 2025-01-01 |
| rp55 | seq | paused | 2024_04 | 2025-01-01 |
| rp75 | seq | paused | 2024_04 | 2025-01-01 |
| mgnify30_c2 | seq | enabled | 2026_07 | 2026-07-11 |
| mgnify30_c5_fl | seq | enabled | 2026_07 | 2026-07-11 |
| mgnify30_c5_ppfam | seq | enabled | 2026_07 | 2026-07-11 |

These are exact advertised status/version/release-date values, not successful execution observations. In particular, the reference/SwissProt/UniProt and representative-proteome entries are paused in this snapshot despite their presence in the narrative documentation. The listing also exposes three enabled MGnify entries absent from the retained latest narrative database page. A database must remain an explicit caller/episode operand; these facts authorize no automatic substitution. Submission access, actual search availability and algorithm/database execution pairings are still unverified.

The capability URL was derived from `ebi-openapi.body` at `#/paths/~1Tools~1hmmer~1api~1v1~1search~1databases/get`, operationId `search_api_get_databases`. Exact bytes, headers, retrieval time, endpoint provenance and status are in `ebi-databases.body` and `ebi-databases.metadata.json`. Entity SHA256: `3debeec4192deff9020a943798e47486b7203816e2a00f987ba516784561ea5a`.

The malformed-object path was inspected from callback through closure:

1. `public_search_operations.py:325-389` captures the fixture's returned SourceSnapshot bytes into the original immutable capsule and releases its worker-owned lock in finally. Parsing JSON is later work.
2. `_observe` reserves the original selection, checks replay and original order, then imports the retained capsule in a Store transaction (`:624-700`).
3. `provider_jobs.validate_remote_identity` calls `native.get` (`provider_jobs.py:40`), so JSON null/list/string/number produces AttributeError before a response representation can be classified.
4. `_observe` catches ValueError/TypeError/KeyError/AcquisitionError (`:730`), excluding AttributeError. `Store.transaction` rolls back and rethrows (`state.py:79-97`). No selected-status terminal receipt is committed.
5. Same-key replay finds the retained capsule and skips another fixture request (`public_search_operations.py:673-689`) but repeats the same AttributeError. Captured bytes remain intact. It does not authorize a fresh request or a replacement job.

`nonobject_probe.py` executes the actual unmodified status port on the imported in-memory FixtureClient, in an isolated Store under this evidence directory. One fixture submission establishes accepted state; it is an in-memory response, not an HTTP/public submission. The first selected status captures JSON `[]`; its same-key replay raises the same AttributeError. Exactly one fixture status call occurred, no status receipt was saved, no transaction remained open, and authoritative state remained accepted. The raw capsule retained exact entity SHA256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`. There were zero network requests, model/native calls or result fetches. Exact script, command, JSON observations and stdout are retained alongside this record.

The separate pending/null proof remains explicitly constructed rather than fetched: `{status:PENDING,result:null,page_count:null}` passes the published ResultResponseSchema, while the actual pure identity validator raises provider_result_representation. The ordinary parse_hmmer accepts its non-SUCCESS status. P calls identity validation at `public_search_operations.py:700` before inspecting state at `:701`; its general invalid-response mapping therefore precedes the intended result_not_ready/remote_job_failed branch at `:704-707`.

Any separate correction must retain present `result.stats.id`, `algo` and `database` identity checks; pure negative probes confirmed current remote_identity_conflict_id/algo/database behavior. It must preserve original capture bytes/times/selection, replay and one-request semantics, original non-null request and job identities, and successful result witnesses. This evidence makes no source change and adopts no alternative parsing or resource-selection policy.

All 128 original application/shared-loop source hashes still match the frozen manifest. Runtime implementation pin remains `8b5bb9541dedf73e99514083cd4da8b6c8435c806a867f1b12063321b289c4be`; the distinct canonical source-hash-map digest remains `43eb830554b542d43430d9987cbb8bb52d3f83b6b488cd79c0100b54a952965a`. No source, tests or live state were changed.
