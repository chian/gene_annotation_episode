# Measured phylogeny return-validation cost and proposed boundary

One retained GeneTree fact read took **22.919 s wall / 22.918 s CPU under cProfile**. It made 59,084,676 function calls. **16.534 cumulative seconds were inside the pure AppService `validate_contract` function**. The final saved phylogeny fact projection took 0.030 s. This supports optimizing repeated contract validation, while preserving the existing authentication and ownership checks.

No production code, existing test, checklist, or design record was changed. No Workflow, native scientific operation, network call, credential access, or model invocation was performed. The proposed optimization below is **not implemented** and has no measured speedup yet.

## 1. Input, closure, and measurement

The original input is `/tmp/pytest-of-chia/pytest-1391/test_configured_native_publica0`, the completed first `gene_tree` mode of `tests/test_bvbrc_phylogeny_host_integration.py` run002. Root reported the first mode had passed and the host process had advanced to directory2. Before copying directory0, the probe found no open descriptors referring to it among readable `/proc` entries, no SQLite WAL/SHM files, and a stable complete byte manifest. It did not inspect directory2 or attach tracing to either live process.

The measured copy is `retained_gene_tree_fixture/` beside this report. Its 138 files / 1,031,274 bytes were byte-identical to the original. SQLite opened with `mode=ro&immutable=1` and `query_only=ON`. The only permitted write-capable open in the copy was the existing zero-byte selected-effects `.lock`, used by the inspected production `SelectedAPIEffects.read` path only to lock and read. Original and copied file manifests, including lock contents and mtimes, remained unchanged after the profile.

**Closure qualification:** this is a closed, completed pytest fixture. `SavedRecords` manually journals episode rows with `state="active"`; it does not run Workflow closure. The retained five lifecycle labels remain exactly as written. This is not evidence of a closed scientific Workflow.

The one complete profiled production call was:

```python
api.phylogeny_returns.received_facts(root_context, original_science_schema)
```

This is the host test's final explicit saved-fact read. `root_context` was reconstructed from its actual saved request; `original_science_schema` came from the original scientific child's requested report contract. The normal root request has no requested phylogeny form; the test separately establishes that `family.received_report_facts(root)` is empty. The diagnostic does not change that request.

Run: `appservice-custody-fixture`. Scope: `{"subject_refs":["input_adb7b6266eb34f916e03549e"]}`. Exact episode identities, original schema, configuration, publication-input paths and expected facts are in `profile_scope.json`.

The retained native inputs are deliberately synthetic:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Aligned FASTA: four rows, four columns | 32 | `321a5e4dbf33c1c937d55d548f4f46242b8cb609d50aad7c8475c0e943a3159d` |
| Newick tree | 39 | `619812b4d487ec324c12654e2205fd477db3ad8896fbb39bf007afde64b516f8` |
| Original closed `state/state.sqlite3` | — | `82819ed497d3f166ab76a04d33254ce16a4b2fe25ec30a2a83e8aef131a44343` |

The supplied Newick is `((A:0,B:0.2)75:0.3,(C:-0.1,D:0.4):0.2);`. The preserved output contains `tips=4`, `cells=16`, `gap_fraction=0.125`, and selected branch lengths `0.0` and `-0.1`. Four missing-requirement rows retain two reason codes: native support unavailable and bootstrap counts unavailable. Valid branch lengths survive that partiality. `observed_facts.json` equals the original frozen typed form exactly.

The copied reader object uses the production `APIServiceExecution`, `BVBRCAppServiceHost`, `AppServiceRecords`, `AppServiceCustody`, and `BVBRCPhylogenyReturns` methods. Only construction is reconstructed: no service clients, executors, or Workflow are started. The configuration is the test's exact `CONFIG` plus its explicit GeneTree adapter pin, and the current implementation digest was checked against both retained publication inputs:

* Adapter implementation: `d2cad59d6b38933bdb7e9d2a3412612b87d70c16567c128d68632fff821e4093`.
* Original selector: `8b23f4abbf832456babb9bd1a3c8aa07b44fd77b818f518623372a61581913b4`.

The probe preloaded relevant production modules, blocked native parser/calculator/adapter functions and their imported aliases, and installed process/network audit guards. No prohibited event occurred. All table counts remained unchanged: 5 episodes, 10 actions, 4 forms, 4 return attempts, 4 manually saved model selections, 72 record receipts, 27 source records, 41 artifacts, and **0 observations**. The complete counts are saved; manually recorded model selections are not model calls made by this diagnostic.

The profile ran from `2026-10-25T05:32:21.317381+00:00` to `2026-10-25T05:32:44.236224+00:00`. Preparation failures are preserved separately in `SETUP_ATTEMPTS.md`; neither is represented as a successful full profile.

### Observed function costs

Counts below are total invocations, including recursive entries. Cumulative times overlap and must not be added.

| Function | Calls | Cumulative seconds |
| --- | ---: | ---: |
| `BVBRCPhylogenyReturns.received_facts` | 2, one outer call | 22.919 |
| `AppServicePublications.read` | 4 | 22.667 |
| `validate_contract` | 786 | 16.534 |
| `AppServiceRecords.read` | 42 | 14.045 |
| Contract `_walk` | 124,768, 786 outer entries | 12.752 |
| `AppServicePublications._validate_inputs` | 4 | 8.679 |
| `AppServicePublications._bundle` | 4 | 7.507 |
| `BVBRCAppServiceHost.read_handoff` | 32 | 6.420 |
| `AppServiceRecords._acquisition` | 10 | 5.197 |
| `AppServiceCustody._commission` | 472 | 4.651 |
| `Draft202012Validator.check_schema` | 517 | 2.190 |
| `communication.validate_closed_schema` | 492 | 1.811 |
| `contract_schema` | 798 | 0.629 |
| File JSON `_read` | 784 | 0.093 |
| `project_phylogeny_facts` | 1 | 0.030 |
| `Store.get_artifact`, including byte hashes | 169 | 0.018 |

`profile_functions.json` records every measured function and caller edge; `one_received_facts.prof` retains the cProfile data. `profile_cumulative.txt` contains the top 100 entries. No timing is assigned to a name without a measured call.

This measures one retained GeneTree read with profiler overhead. It does not measure unprofiled speed, the host test's complete runtime, CodonTree, or worker133's Workflow. The reported host-test minutes remain root's separate observation.

## 2. Repeated work and its cause

**Measured call edges:** the four `AppServicePublications.read` calls come from `own_results` twice (9.577 s), `_latest` once (6.569 s), and `read_content_source` once (6.520 s). `_latest` first asks `own_results` to authenticate every original result, then reads the latest again. Reading its saved sheet invokes `read_content_source`, which authenticates the same publication again.

Each publication read checks its current acquisition and reconstructs its original dependency bundle. `AppServiceRecords.read` verifies source/artifact bytes, original selected action, frozen native snapshot, publication input relationships and the completed outcome. For acquisition receipts, both `_origin` and `_native` lead through `read_target` to the original handoff again. `read_handoff` reconstructs custody/commission ownership and reads the saved effect state. `_validate_inputs` separately proves the original handoff, support receipts, dependency order, decision cutoffs and adapter configuration. These paths explain the measured 42 receipt reads, 32 handoff reads and 472 commission checks from one fact request.

The fixture contains only two acquisition publications and one original handoff. Thus the repeated calls revisit a small fixed set of unchanged inputs. That statement follows from the retained fixture plus the inspected call graph; cProfile does **not** record argument values. A full count of distinct `validate_contract` payloads was not measured.

The largest measured validator callers are:

| Caller of `validate_contract` | Calls | Cumulative seconds in `validate_contract` |
| --- | ---: | ---: |
| `AppServiceRecords._acquisition` | 20 | 5.090 |
| `AppServiceRecords._decode` | 42 | 3.015 |
| `AppServiceRecords._native` | 42 | 2.587 |
| `AppServiceCustody._validate` | 152 | 1.380 |
| `bundle_values._acquisition` | 7 | 1.353 |
| `bundle_values._publication` | 4 | 1.351 |
| `AppServicePublications._dependency_inputs` | 3 | 1.023 |

**Static explanation of the validator's internal repetition:** `validate_contract` first validates the complete instance with `_Validator.iter_errors`, then `_walk` revisits it for semantic relationships. For every `anyOf`/`oneOf`/`allOf` branch, `_walk` calls `validator.evolve(...).is_valid(value)` to select traversals. The recursive `Json` schema has object/array branches pointing back to `Json`, so nested supplied requests, selectors and snapshots are repeatedly traversed for shape during the relationship pass. The measured `_walk` total is 12.752 s; the exact portion attributable to `Json` was not separately instrumented. The proposal does not assume that all 12.752 s can disappear.

**Static explanation of amplification by typed admission:** `TypedReportContract.admit` calls `validate_form`, whose visitor invokes its resolver for each reference/identifier occurrence. The actual retained form has **24 occurrences / 15 distinct `(value, namespace)` pairs**. Nineteen occurrences use phylogeny namespaces and five use `execution_result`. `ExecutionEpisodes.resolve` routes a phylogeny identifier to `resolve_own` or `resolve_received`; each constructs the authenticated facts again before checking membership. The two host-test admissions therefore entail 38 phylogeny resolver invocations, plus their semantic and admission checks. `resolve_own` returns to `facts/_latest`; `resolve_received` returns to `received_context`, recursively validates the immediate child's original form, then reaches the same results publication.

That is an inspected multiplicative path from a small typed form to repeated validation of large custody/selector structures. It is consistent with minute-scale host work. Multiplying the 22.919 s profiled measurement by these counts would **not** be a valid unprofiled runtime estimate.

## 3. One proposed optimization: cache successful pure contract checks within a validation pass

The proposed boundary is **`bvbrc_appservice_contracts.validate_contract`**, whose decision depends on a supplied finite JSON value, its resolved contract schema, and the validator/relationship implementation. It returns a fresh copy or raises a structured contract error. It has no Store, episode, receiver, current time, file, network, or resource input. Its successful shape/relationship check can therefore be reused for the exact same inputs without reusing a custody decision.

Proposed signatures, not implemented code:

```python
# New small passive helper module: pure_contract_validation.py
def contract_validation_pass(
    *, max_entries: int = 256, max_key_bytes: int = 16 * 1024 * 1024
) -> ContextManager[None]: ...

def successful_contract_check(
    *, semantics: tuple[object, ...], contract_name: str,
    schema_bytes: bytes, value_bytes: bytes
) -> bool: ...

def remember_successful_contract_check(
    *, semantics: tuple[object, ...], contract_name: str,
    schema_bytes: bytes, value_bytes: bytes
) -> None: ...

# Existing public contract stays unchanged.
def validate_contract(name: str, value: object): ...

# Extract the existing shape and relationship body with identical failures.
def _validate_contract_value(name: str, value: object, schema: dict) -> None: ...
```

`contract_validation_pass` creates a bounded success set for one synchronous outer validation/read. Nested uses share that pass; leaving the outer call releases it even on failure. A context-local token must also bind the current thread and task identity: a newly created task inheriting a ContextVar must create its own pass rather than reuse the parent's mutable success set. Exceeding the cache budget only bypasses caching and runs the existing validation; it never changes the result or continuation.

`validate_contract` still resolves the contract first, preserving unknown-contract failure precedence. It checks plain finite JSON, freezes a detached input snapshot, and constructs an exact type-preserving canonical encoding. The key contains **the full canonical payload bytes, full resolved schema bytes, contract name, and a semantics token identifying the actual validator/type checker and relationship functions**. A digest alone is insufficient for equality. `true`, `1`, `1.0`, `null`, missing members and finite signed values must retain their current distinctions. Use ASCII-escaped JSON for the private cache key so otherwise accepted Unicode strings do not acquire a new UTF-8 encoding failure. If a value cannot be safely encoded for a key, bypass caching and run unchanged validation; a serialization limit must not become a new contract restriction. On a cache miss, `_validate_contract_value` runs today's complete `_Validator.iter_errors` and `_walk` logic, including all native relationship checks. Only success is recorded. Every caller still receives a fresh detached copy of its current supplied value; no cached mutable object is exposed. Invalid input and structured errors are never cached.

Exact consuming boundaries:

* Wrap `TypedReportContract.admit` in a pass so its existing resolver callbacks and semantic validator can share only successful pure contract checks.
* Wrap the public `BVBRCPhylogenyReturns.facts`, `received_facts`, `resolve_own`, `resolve_received`, `validate_received_report`, and `record_admission` entries in the same nestable pass for calls made outside admission. Internal calls reuse the active pass.
* `AppServiceRecords`, `AppServicePublications`, `AppServiceCustody`, bundle reconstruction and effect-state readers continue to call the same `validate_contract` API and execute all their existing custody/byte/relationship code. No reader result is memoized.

The proposed file boundary is the new passive helper, `bvbrc_appservice_contracts.py`, the small entry scopes in `bvbrc_phylogeny_returns.py`, and the existing synchronous `TypedReportContract.admit` scope in `runtime.py`. It does not change finite forms, selectors, sheets, calculators, results, ownership, credit, continuation or scientific dispatch.

### Dependency and invalidation conditions

| Change or boundary | Required behavior |
| --- | --- |
| Any supplied contract value changes | Its exact payload bytes differ; validate again. |
| Any reachable packaged definition or supplied nested schema changes | Its full schema/payload bytes differ; validate again. |
| Validator/type checker/relationship implementation changes | A different semantics token and a fresh pass; validate again. |
| Input is nonfinite, non-JSON, cyclic, or has invalid key/type structure | Preserve the existing failure; do not form a reusable success. |
| Input or a previous returned value is mutated | Snapshot/key uses the new supplied value; returned copies share no mutable cache object. |
| Outer call exits, raises, or reconstruction begins | Discard the success set. No persistence or reuse across independently observed state. |
| A Store row, artifact file, action outcome, selected effect, report attempt or original commission changes | Its current readers still execute. Artifact byte hashing and original-record comparisons still occur before use; pure validation success never authenticates a file or grants possession. |
| Episode/scope, `before` cutoff, inherited receipt prefix, selected adapter or original selector changes | Existing custody and publication checks execute with those actual operands. No cached permission, publication, form or facts can bypass them. |
| A sibling or ancestor asks for a reference | Existing immediate-parent forms and requested-source selection still control it. The cache contains no reference registry or receiver permissions. |

This boundary targets the observed 16.534 s validator cost while preserving the 169 actual artifact reads/hashes and every custody/commission traversal. It does not eliminate all repeated fact reconstruction, schema checking or copying. No quantitative speedup or complete resolution of host-test runtime is claimed without implementation and measurement.

Before accepting an implementation, root should verify equivalence for successful/invalid contracts, strict scalar types, missing versus null, nonfinite and cyclic inputs, fresh-copy behavior, changed input/schema/rules inside one pass, and bounded-cache bypass. The existing adversarial byte tampering, wrong selector/adapter, wrong owner/scope/cutoff, sibling isolation, frozen-form mismatch and immediate-parent return tests must still fail at the same boundaries. The retained host fixture must return the same facts with unchanged action/observation counts and parser/calculator/network blockers. These are proposed checks; they have not been run for an unimplemented cache.

## Evidence files and inspected source identities

`input_manifest.json` retains every original input file digest and closure check; `retained_input_summary.json` retains the complete synthetic native bytes and reference-occurrence paths. `source_hashes.json` contains 262 source/assets/dependency hashes, verified unchanged across the profile. Principal production hashes are:

| Source | SHA-256 |
| --- | --- |
| `bvbrc_phylogeny_returns.py` | `eeb008272fcc5a88601a01c1e146d9cfcb8c739f41bdd1db33faeb5a7a7acb1b` |
| `bvbrc_appservice_publication.py` | `60f9e410f1ac4b79df07b17771366a567ccb9835c1d18f707870dca7b7340aae` |
| `bvbrc_appservice_records.py` | `8066e1d41511150254702b69bd00ad100446a6c0606ddefa20769701b393f354` |
| `bvbrc_appservice_custody.py` | `27b5907ed762be2aca499ca9af94005a9d2950af8468fa32fac3316c134db134` |
| `bvbrc_appservice_contracts.py` | `b5cfb867d1065d91a66e1d337b2c73a7bbc1d92084e00e8ae67d51f574e45c62` |
| `bvbrc_appservice_schemas.json` | `d21f7a4450e23e346ee0a3ed52d3466a7d5f212fe25aecab5fcf738f60d99924` |
| `episode_return_records.py` | `a470cd1ac87b43bcbaa964d433e5e7ff36e7b7ce399634c53bec0a4f89244f65` |
| `api_service_execution.py` | `5f4960c36d4540a8a961ee2eb5290633bfbe7b93827fe73214cfe41629533c5a` |

Source inspection covered the complete named return/publication/custody/record/API paths, the host integration's fixture helpers, `ExecutionEpisodes` fact/resolve/admission consumers, `TypedReportContract.admit`, `validate_form`, the full AppService contract validator, bundle reconstruction, native download qualification, selected-effect reads, and the Store artifact authentication path. The immutable goal's objective and full DESIGN PRINCIPLES block were reread verbatim after substantial examination, followed by the exact assigned task. This report is implementation evidence and a proposal, not new design authority or a completion claim for GeneTree/CodonTree.
