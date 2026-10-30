# Actual HMMER reported-timing verification 001, 2026-10-22

One new engineering `phmmer` job ran against the public HMMER `pdb` selector with `parameters={}` and `page_size=2`, using the actual fixed target's 253-aa translated protein. The new API003 timing binding retained the winning submission's original pre-POST context, the provider's reported `result.stats.elapsed`, one immutable first witness, one typed reported-result statistic and one source-qualified timing fact. Both provider-reported result pages were acquired and published. A cached page-1 read and same-key submission replay preserved the original timing identity, timestamp and single shared-history row.

The provider-reported interval was **0.22888848185539246 seconds**, with measure `hmmer_reported_search_elapsed_seconds` and observation unit `logical_provider_job_reported_result`. It is not a physical-attempt count, queue measurement, HTTP duration or job-turnaround estimate. The first local result receipt was observed at `2026-10-22T07:31:19.992723+00:00`; this is not a provider execution-end timestamp.

The [new derived evidence manifest](/home/chia/repos/gene_annotation_episode/verification/hmmer_reported_timing_actual_service_2026-10-22_001/MANIFEST.json) lists exact file hashes and sizes. This publication is a **partial, token-free derivative**, not a complete database or self-contained replay capsule. Raw databases, transport/capture manifests and eight transport or credential-bearing artifacts remain in the two original private mode-0700 working directories. Their original private paths, SHA256 values and byte sizes are retained in `ORIGINAL_TO_PUBLIC.json`. Original references to omitted bytes remain unchanged; no redacted content is relabeled under an original content address. No redacted transport derivative was needed.

The engineering phases used isolated API003 implementation pin `cde521578e4531b93dcbe9e33eaf58881db867c0664c3cb9af93107d549e2623`. All 13 original after-phase guards match the same 131-source map, and the publisher independently matched those source bytes to that pin. The actual helper SHA256 is `0ba7062f1301f317512a40a7820b5e8cc3cfeaa5739ff55cd4e319d5752cffa0`. The separate [API003 code and fixture capsule](/home/chia/repos/gene_annotation_episode/docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_003.md) is not duplicated or changed by this publication.

| Actual input or binding | Recorded value |
| --- | --- |
| Fixed target | ybhP/b0790, E. coli K-12 MG1655; `input_a5c60b96717424cdf5138420` |
| Original problem | `problem_9d89f9abcb43930a1bb557f1` |
| DNA | 762 nt; SHA256 `62930707904f67975532ff43f609f98f64700a9afbbc3c5eb446e02f3a513f26` |
| Actual translated product | `product_03c3acb11bc333cbc36b076e`; 253 aa |
| Product / P0AAW1 witness SHA256 | `f0cdd3744b5bc986fd574175ecb7155c0ed57c7749098f20300735a3c849560a` |
| Submitted FASTA SHA256 | `8119b5b15f9356bea7417981be3338f471282b458e1d855dd85f89a08745d7ab` |
| Normalized request SHA256 | `de9d0bd2022d656d6359d1e69ee4de0e5b59d393b473ea270a3ad7defe6463ce` |
| Provider job | `provider_job_24b52ef96a8fee7bd0799340` |
| Returned server UUID | `280e4b1f-75a9-46c6-97e6-60f2f92c16f1` |
| Timing source | `source_0b67cd939f50d78539ced326` |
| Caller registry | `execution_registry_hmmer_reported_timing_verification_001` |
| Caller resource | `hmmer-reported-timing-verification-001` |
| Effective client-binding SHA256 | `7c3113045c9b8bd9d0613e12a5fd16eddbddb06fcb6b748b75f68d51dc1f2eb9` |

The new fixed-target seed was created by the existing public seed helper at `/tmp/hmmer-reported-timing-fixed-target-20261022-001`. Its retained receipt reports exact original problem/input/intake/artifact preservation, 11 initial custody references and `observed_changes=[]` for the canonical source's main database and existing WAL/SHM. The publication inspected that retained receipt and the new seed's actual bytes; it did not reopen the canonical source workspace. Translation actually used code11, strand`+`, frame0, interval`[0,762)` and `cds=true`, and its product bytes match the fixed protein witness.

The actual caller reconstructed one `PublicClients`, `ToolRegistry` and their matching registry/client/importer ports per phase. The original 90-second HTTP transport setting remained unchanged. Local limits remained 20 GiB RAM, 4 GiB scratch and no wall budget; they are not remote allocations. The caller bound monitoring information unit1 from its existing configuration, but this engineering harness awarded no episode or scientific credit.

The 13 invocations were preparation/order; a before-submission timing report; submit; one status observation; page-1 acquisition; a timing report; page-1 publication; page-2 acquisition; page-2 publication; another timing report; a cached page-1 read; same-key submission replay; and a final timing report. They were separate explicit selections, with no automatic polling/retry sequence. The original parsed argument records and helper are retained. `COMMANDS.json` labels its canonical argument vectors as **reconstructed from parsed intents**, not verbatim shell command strings; no separate original shell log exists in this evidence.

| Selected operation with an HTTP capture | Original receipt | Local receipt time, UTC | Entity bytes |
| --- | --- | --- | ---: |
| Submit | `provider_operation_108552079e6545474a0b84b7` | `2026-10-22T07:30:22.356238+00:00` | 46 |
| Status, `SUCCESS` | `provider_operation_4f8a4e3724b4713cc66862ac` | `2026-10-22T07:30:41.792942+00:00` | 1335 |
| Result page1 / size2 | `provider_operation_26bc8bd463741aea924eabd1` | `2026-10-22T07:31:19.992723+00:00` | 11190 |
| Result page2 / size2 | `provider_operation_4e88be472b0304cdea6ed5c3` | `2026-10-22T07:32:49.497534+00:00` | 4225 |

These are **four retained selected-operation captures**, not an observed physical HTTP request/redirect count. Their source retrieval times are separately retained in `CHECKS.json`. There is one submission claim and five operation receipts: the new-key cached read adds its own receipt but reuses page1's original capture. The same-key submit replay returns the entire original submit receipt, including `2026-10-22T07:30:22.356238+00:00`, and adds no receipt, claim or capture. It keeps the original receipt's accepted-state facts even though the later authoritative job is returned.

The winning submission binding names that exact original receipt/key/UUID and its matching immutable intent. Its start context is `captured_before_submission` with `condition_ref=null`: the original history read established no configured condition, so this is observed unspecified, not an unavailable/unknown capture. The first witness names the original page1 receipt/entity and observation time. Both page bodies explicitly match the original UUID, `phmmer`, `pdb` and reported elapsed value. Later page acquisition, timing reports, cached read and replay retain that same witness/source and exactly one reported-result row. The old native `run_statistics` table remains empty.

The first-witness source hash equals the canonical complete original witness hash. The local timing source body has the original order scope and subject, exact witness, null text/request references and original result observation time. Actual timing-reader facts retain those same source/job/unit/duration/time relationships. The logical exports preserve the complete intent, winning submit binding, first witness, typed statistic, source and immutable snapshots.

The original before-submission expectation snapshot `execution_expectation_32603c20e45645f41ed619087c2e9253ca9179e122b6f49c491d4b55cbba542b` remains unchanged at `history_through_sequence=0`: support0, no matching history and no duration estimate. Later reports supply support1 and empirical mean/min/max equal to the named reported interval. API `job_ref`, `sample_ref`, comparison elapsed and outcome/reliability support stay null; timing relation remains unknown. The statistical class keeps remote implementation, CPU, memory, scratch, wall budget, corpus sizes and reference revision/digest unknown. Biological sources separately retain the provider's `pdb` version label`03.25` and release-date assertion`2025-01-01`; that metadata does not alter the original exposed-configuration class or establish the deployed daemon build.

| Biological publication | Page1 | Page2 |
| --- | ---: | ---: |
| Returned distinct record references | 11 | 6 |
| Reference row witnesses | 2 | 1 |
| Observation row witnesses | 4 | 1 |
| Native hit domain-array lengths | `[3,1]` | `[1]` |
| Projection failures | 0 | 0 |

All eight publication row witnesses resolve to their actual source, original acquisition receipt, job/request/selector, subject/reference relationships and hit/domain ordinals. Both publications record `page_count=2`; pages1 and2 were acquired and published. This establishes coverage of the provider-reported pages for this request, not scientific completion or interpretation of the hits. The new Store has 28 ordinary records and 23 artifacts, one actual translation operation, no reasoning commits/runtime tables and no hypotheses, assessments, annotations, interpretation accounts or native execution records.

The publisher used only standard-library file/JSON/hash operations and `sqlite3` with `mode=ro`, `query_only=ON` and short read transactions on the three authorized new databases. It imported or constructed no application Store, Workflow, ledger, client, recovery, scorer or controller and invoked no phase, HTTP, model or native computation. The one failed publisher inspection probe was a schema-shape assumption about an intake-reference list; its diagnostic is retained separately and did not run application work. The complete validation/staging invocation then passed. None of the 13 actual phase records contains a failure file.

Every pre-existing private file remained byte/mode identical. Read-only SQLite access created only a new empty `state.sqlite3-wal` and a 32,768-byte `state.sqlite3-shm` in the new workspace; no cleanup, checkpoint, journal-mode change or chmod of raw originals was performed. The main new workspace database remains 294,912 bytes, SHA256 `05ff66558d813946ed0c8f3e116d7d918a19e74da14515c72053daaf347c1696`. `WORKING_CUSTODY.json` records those bookkeeping effects.

The derivative retains 128 exact original files: 108 phase-evidence files (617,195 bytes) and 20 safe workspace files (52,870 bytes), including all four response entities. It also provides separately named logical exports and validator/provenance files. Twenty-two originals are intentionally omitted: three databases plus the two reader sidecars, four raw capture manifests, eight transport/credential-bearing artifacts and five empty lock files. An in-memory scan of every output against the actual private session value and its common encoded forms found no occurrence; no credential value or raw header was printed. `MANIFEST.json` hashes the exact report copy and all other members, excluding itself to avoid a hash cycle.

This establishes actual new-job reported-timing custody and future same-exposed-configuration forecast support for one public-service engineering case. It does not establish provider physical-attempt/retry/reliability counts, a queue/turnaround model, deployed clock/build semantics, a configured-model timing-informed decision, detached episode/controller behavior, scientific interpretation, annotation improvement or credited scientific contribution. The previous successful API002 job remains outside this new timing registration/export. The fixed overall scientific goal remains incomplete.
