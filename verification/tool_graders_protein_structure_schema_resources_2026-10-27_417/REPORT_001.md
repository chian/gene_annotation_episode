# Protein schema resource preparation — 417

The bounded 027 implementation and verification are complete. The private unbound validator now prepares the same fixed outer and inner resources once through `Registry().with_resource(..., Resource.from_contents(document)).crawl()`, then supplies that registry through `_STRICT(document, registry=registry)`. The existing cache remains keyed only by a successful known type name. This changes schema preparation only; `_checked`, strict Python types, finite values, relational checks, receipts, original commissions and current-artifact validation keep their original boundaries.

Production ownership was limited to the `Registry`/`Resource` import and `_execution_validator` in `gene_annotation_episode/native_protein_structure_contracts.py`. An AST comparison confirms every other top-level production statement in that module is unchanged. The profile snapshots differ in exactly this one production module. Existing tests, prompts, numerical sheets/calculators, status rows and the immutable objective were not edited.

Prechange module SHA256: `e40bc91ce1c0c15017ec30b50d5cee1fd6b76e6afc6f1cf2c6637ab4d251a351`. Implemented module SHA256: `44e7308e77e0e6fdcc25cdf4bfa1448037150875c40284ae13ecfe668fc81774`. The complete prechange module, source pins and [exact diff](PRODUCTION_DIFF_001.patch) are retained.

Installed `referencing` 0.37.0 and `jsonschema` 4.26.0 public resource/registry construction and the actual validator initialization/evolution paths were inspected. No private resolver override is used. The exported documents keep their exact nested applicator, definitions, content-derived identifiers and absent inner `$schema`; strict inner validation therefore retains its original type checker. The new private registry has no external retrieval callback.

## Tests actually run

`check001` passed **133 tests in 54.30 seconds**: 48 new resource-resolution cases plus all 85 existing 416/390 schema-reuse, contract, tool-information and native-execution cases. The 48 cases cover exact old/new documents and both resource identities for ten used types; one construction crawl followed by nine real current-payload checks; strict integer/finite-number values; plain types and relational failures; all three native-result alternatives; detached return/public-export mutation isolation; uncached current binding specificity; unknown-resource rejection; unknown-type cache exclusion; and 24 distinct concurrent valid/invalid payloads.

Native tests use synthetic PDB/mmCIF inputs, real worker/driver execution and the existing local lifecycle. They retain actual numerical examples, supplied transforms, retained pairwise alignments, held-out distances, missing/partial data, changed input/output bytes, failed software and replay. This verification is not configured-model scientific work or a new full Workflow run.

All pytest, native/profile work and saved-profile analysis ran through `local_jobs` with 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time limit. Verified cgroups report `memory.max=21474836480`, `memory.swap.max=0`, and `runtime_max=infinity`. Check001 service-wall time was 55.751546 seconds; observed scratch was 27,725,824 bytes. Executed readonly snapshots stayed unchanged, and checkout drift was zero.

## Same retained-input profile

The [profile launcher and diagnostic](HARNESS_EQUALITY_001.json) are byte-identical copies of 415. The launcher uses its own `__file__` to place this attempt under 417. `profile001` used the same closed 410/check007 extraction case, original authority/resolver/semantic-admission callbacks and original Store artifact root. It copied the SQLite state for reading and did not modify 410 or baseline 415. Its dispatch guard recorded no native subprocess or network attempt.

Both real admissions accepted. Catalog, target, selector, return authentication, receipt assignment/intent and actual typed admission outcomes match; stdout is byte-identical. The four retained-input manifests match exactly, as do the source artifact roots. All 3,104 pinned pre-existing baseline 415/416 and existing-test files remained unchanged.

| Interval or count | 415/check002 | 417/profile001 |
| --- | ---: | ---: |
| Profiled diagnostic wall seconds | 32.511627 | 23.840324 |
| Process CPU seconds | 33.281434 | 24.684166 |
| Local service-wall seconds | 33.044875 | 24.587023 |
| Total profile calls | 99,927,635 | 72,806,910 |
| Primitive profile calls | 84,096,872 | 56,976,147 |
| Summed profile self seconds | 32.435445 | 23.767047 |

The diagnostic wall reduction was **8.671303 seconds (26.6714%)** in this single before/after pair. cProfile overhead is included and changes when call counts change; the OS file cache was not controlled. Snapshot/input hashing and final profile serialization are outside the measured interval. No unprofiled latency distribution or full Workflow speedup is inferred.

| Function | Before calls | After calls | Before cumulative s | After cumulative s |
| --- | ---: | ---: | ---: | ---: |
| Registry.crawl | 294 | 8 | 8.347450 | 0.198791 |
| Native payload _checked | 293 | 293 | 9.724798 | 1.472889 |
| Validate request | 125 | 125 | 4.035673 | 0.475870 |
| Validate job | 58 | 58 | 7.459792 | 0.856140 |
| Validate requested job | 26 | 26 | 7.669407 | 1.012015 |
| Compile job | 32 | 32 | 3.992985 | 0.333417 |
| Private validator construction | 7 | 7 | 0.670821 | 0.830003 |
| Public schema construction | 9 | 9 | 0.847901 | 0.805670 |
| Return authentication | 17 | 17 | 12.245964 | 12.061447 |
| Base return authentication | 54 | 54 | 4.697993 | 4.648544 |
| Original commission checks | 37 | 37 | 3.920788 | 3.831257 |
| Completed receipt traversal | 3 | 3 | 18.397799 | 10.797198 |
| Verify selected artifacts | 1 | 1 | 0.001888 | 0.001802 |
| Current scientific bytes | 4 | 4 | 0.001539 | 0.001474 |
| Closed form check_schema | 1 | 1 | 5.135837 | 5.034064 |

Cumulative times overlap and must not be added. Warm tests establish no rediscovery while checking current values; the real diagnostic retains seven private constructor calls and now eight total registry crawls. All 293 payload validations and the reported authority/receipt/current-byte counts remain present. No payload or authority outcome is cached.

| Original admitted/input record | Bytes | Exact SHA256 in both runs |
| --- | ---: | --- |
| action | 65 | `7d3ff18a97ca27db07b225160f232484771de4a99800776e4ae5659aa0c5aaf8` |
| result | 67,611 | `a955bd925b20f24075ff4453bf5ed00d67d284e81cfd52faffb2ea6eed563230` |
| form | 2,439 | `926a3865a20b90142d8da502aab348577f1231611f3f1a90d4f5c0885d9ba530` |
| facts | 3,790 | `78b24fde1a1817115f61aebe505da3a862f37eb8a78e9f648b33faf5e4b13a41` |
| request | 961,364 | `161d8c1860a1ed5cb125c170294a0b1db5e876b0c91d14cf984b629b7982a80a` |

The unchanged harness does **not** serialize the returned `ParentReport` object. Exact equality is established for the actual admitted input form and frozen facts plus successful real admission; a separate output-object byte comparison is not claimed. Profile001 observed scratch was 42,704,896 bytes. Its executed snapshot and retained inputs stayed unchanged, with zero checkout drift.

## Inspected path and remaining scope

The full native execution contract module and direct `_checked` consumers were read, together with the actual native local/worker/driver, tool-information, acquisition, publication, result host, result-receipt and typed-return paths. The selected operand/selector, practical assignment/resource validation, execution owner target/resolver/report, result-worker and saved-sheet entry paths were traced. The changed function only constructs private schema resources: it selects no action/resource and writes no durable scientific state. Original selected actions, receipt publication, frozen typed facts, current artifact checks, credit and continuation remain owned by the existing consumers.

The immutable objective (SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`), AGENTS.md, required design records, relevant fixed inventory row, contract027, 415 comparison and 416/390 tests/harness were read. After substantial source/output examination, the full objective including all 16 design principles was reread verbatim, followed by contract027. Tools remain tasks inside episode problem-solving processes.

There were no failed pytest, native/profile or profile-analysis attempts. Two read-only discovery/diff commands failed before execution work: an absent optional `scripts` search directory (exit 2), and `git diff` in this non-Git workspace (exit 129). Their details are retained in [commands](COMMANDS.md). All executed attempts are preserved.

The bounded 027 change is verified. Whole-protein integration/completion, configured-model decision behavior, unprofiled/full Workflow speed, and unrelated tool acceptance remain outside this packet. Live 410 was never stopped or modified. Root retains shared integration and accounting; this packet changes no tally or goal.

## Reproduction and evidence

```sh
.venv/bin/python -B verification/tool_graders_protein_structure_schema_resources_2026-10-27_417/run_bounded.py check001
.venv/bin/python -B verification/tool_graders_protein_structure_schema_resources_2026-10-27_417/run_profile_bounded.py profile001
.venv/bin/python -B verification/tool_graders_protein_structure_schema_resources_2026-10-27_417/run_analysis_bounded.py analysis001
```

Existing attempt directories are exclusive and must be preserved; a further authorized run requires a new output name. The saved-profile comparison script intentionally names the original profile001.

- [Pytest request](check001/selected_request.json), [output](check001/stdout.txt), [receipt](check001/receipt.json), [frozen sources](check001/source_pins_before.json).
- [Profile request](profile001/selected_request.json), [binary profile](profile001/diagnostic.prof), [stages](profile001/profile_stages.json), [receipt](profile001/receipt.json).
- [Exact comparison](analysis001/comparison.json), [baseline preservation](analysis001/baseline_preservation.json), [admitted input form](analysis001/admitted_input_form.json), [frozen facts](analysis001/frozen_input_facts.json), [analysis receipt](analysis001/receipt.json).
- [Complete cumulative profile](analysis001/profile_all_cumulative.txt), [complete self-time profile](analysis001/profile_all_tottime.txt).
