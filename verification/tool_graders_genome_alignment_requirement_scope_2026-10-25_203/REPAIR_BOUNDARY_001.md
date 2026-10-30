# GenomeAlignment requirement-reference scope diagnosis

Diagnostic and coding-boundary proposal only, 2026-10-25. No implementation repair has been applied. This record owns no authority/design/accounting changes.

The complete authoritative goal was read verbatim and matched SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`. AGENTS, GOAL, episode structure, time-aware estimation, tool knowledge, practical execution and its original contract, task/steering, tool-grader principles and the fixed GenomeAlignment WORK_STATUS row were read. Applicable contracts are provider D001, frozen INTERFACES002's shared/C/D interfaces, INPUT_RELATIONSHIPS004, and EXTRACTION_CONTRACT001. The objective and all 16 original principles were reread after substantial source study; the final reset also follows the diagnostic/native work. Historical contract status labels are not interpreted as current implementation evidence.

## Verified failure and exact reference domains

The exact 1045-path frozen186 baseline plus the same seven retained fixtures was copied from 197/baseline_candidate into this directory. All 1052 files are byte-identical and separately hashed. Bytecode/cache directories were excluded. The observed baseline is not the concurrently evolving production tree.

`capture_failure_001.py` wraps only the in-memory `validate_genome_alignment_data` entry to save its argument, invokes the original validator unchanged, verifies argument immutability, and re-raises its exception. The existing test produced **1 failure, exit 1, 42.47 seconds**, preserving `bvbrc_genome_alignment_provider_requirement_reference_unknown`. This independently matches 197's pre-performance baseline failure; it is not evidence against the 197 optimization.

The failing argument is `capture_failure_001/data_009.json`. Among every recursively encountered requirement array there is exactly one unresolved path against the scientific union:

| Exact JSON pointer in GenomeAlignmentData | Value | Actual meaning and referent |
| --- | --- | --- |
| `/associations/artifacts/0/artifact/requirement_ids` | `["native"]` | AppService output selections; resolves to original PublicationInputs `/selector/requirements/1`, schema `bvbrc_appservice_schemas.json#/$defs/OutputRequirement`. |
| `/associations/artifacts/0/requirement_ids` | `["ga_association:3e0c84531e03f778e02329016ce35c4758739ec88eab42e5106ff2804ce52fc5"]` | Scientific unmet cause; resolves in associations.requirements and data.requirements to `kind=byte_version_evidence`, `reason_code=bvbrc_genome_alignment_artifact_version_unverified`. |

The selector's `native` OutputRequirement is `{requirement_id:"native", role:"genome_alignment_primary", required:true, declared_format:{format:"mauve_v4",version:"4",mode:null,producer_source_ref:null,transformation_evidence:[]}, producer_rule_evidence:null, exact_object:null}`. It requests the output; it is not a declaration that output bytes remain missing.

The acquired artifact contains all 1007 bytes of the retained v4 example, SHA256 `a0e700b702070ebd061f6ca5c5b0d9338ad8c330ad16b94c9a0090041cd8cd88`, a complete transfer, actual controlled-task manifest association, and unchanged `byte_version_status="unknown"`. Data retains **17 genuine unmet causes: 12 input and 5 association**. It correctly contains no unmet `native` acquisition requirement after the native output has been acquired. Adding a fabricated or stale `native` cause would be incorrect.

The capture contains nine preceding successful validation calls during manifest-only publication and the tenth failing call during native acquisition. Repeated validator calls are not episode actions or credits.

## Actual producer and receiving validators

1. `tests/test_bvbrc_genome_alignment_host.py::selection` defines the original output requirement; `GenomeDriver.native_arguments` selects `requirement_ids=["native"]` in the actual download operands. The service transport alone is controlled; receipt publication, Store, selected-action host and custody are production objects.
2. `bvbrc_appservice_bundle_values._selection` checks the exact original request/selector/argument hashes and calls `_requirements`. `_requirements` resolves every selected ID against **selector.requirements**, checks role, declared format, exact selected object when constrained, and required producer evidence.
3. `build_acquisition_value` copies `args.requirement_ids` into the published `ArtifactMember` and its `AcquisitionReceipt`. `_acquisition` checks the receipt and optional member IDs against the frozen operands; `build_artifact_bundle` retains the original member unchanged. This is the actual producer of the nested `artifact.requirement_ids` value.
4. `AppServicePublications._grade` supplies the actual bundle and authenticated retained records. `collect_retained_records` preserves current/prior receipt custody and original request/task/resource relationships. The C retained-record reader validates supplied byte/content relationships. C does not grant source possession.
5. `bind_genome_alignment_artifacts` deep-copies the original ArtifactMember into `AssociatedArtifact.artifact`. Its separately produced outer `requirement_ids` reference C scientific requirements. `validate_genome_alignment_associations` already validates these distinct responsibilities: the nested artifact through `validate_contract("ArtifactMember",...)`, and the outer IDs through `_requirement_refs(..., associations.requirements)`. Input rows receive the analogous local validation in `validate_genome_alignment_inputs`.
6. `consume_bundle` builds data with the complete requirement union. `validate_genome_alignment_data` validates C outputs, native documents, slots, task and association relationships, and inclusion/equality of all nested reports. Its final `c._links(value, scientific_ids)` then recursively interprets **every dictionary key** named `requirement_ids` as a scientific reference. This is the defective boundary.

There is no OutputRequirement collection in GenomeAlignmentData: it stores the original native task and C/parsed results. D cannot semantically revalidate original output-selection references against a selector it does not possess. Their semantic validator remains the AppService acquisition/publication path; D checks their declared ArtifactMember schema, preserves them, and relies on authenticated custody during replay.

A separate deliberately modified diagnostic input confirms the same recursive walk also misreads a `requirement_ids` key inside OriginalTask's permitted native parameter JSON. This was not present in the reproduced failure. It supports scoping by the declared scientific fields instead of adding a single key-name exception for `artifact`.

## Smallest proposed repair and ownership

Production ownership: **only `gene_annotation_episode/bvbrc_genome_alignment_sheet.py`**, in `validate_genome_alignment_data`, optionally with a private `_data_requirement_links` helper. Test ownership: a new `tests/test_genome_alignment_requirement_scope.py` plus existing suites run unchanged. Integration changes and source-pin publication remain root-owned.

Replace the whole-data recursive `_links` call with an explicit check of these seven already-closed scientific arrays against data.requirements:

| Owner | Exact scientific array paths |
| --- | --- |
| inputs, when present | `files[*].requirement_ids`, `member_bindings[*].requirement_ids`, `contig_bindings[*].requirement_ids`, `feature_bindings[*].requirement_ids` |
| associations, when present | `artifacts[*].requirement_ids`, `native_member_joins[*].requirement_ids`, `bbcols_interval_joins[*].requirement_ids` |

Check the named arrays directly, or pass only those arrays in minimal `requirement_ids` records to the existing strict checker. Do not recursively walk the containing C rows into their ArtifactMembers or OriginalTask values. Keep both complete C validators before this check: they enforce local scientific report membership, unique/nonempty references and meaningful relationships. Keep exact nested-report retention/equality in `_data_groups`/`_union`.

The four native document validators expose no requirement-ID arrays; they and the slot/resolution validators remain unchanged. The closed numerical components and source-binding records have their own scientific reference arrays. **Keep `calculation_contracts._links` and its components-validation call unchanged and strict.** No new global traversal engine, reference union, permissive unknown-ID fallback, name-prefix heuristic or silently removed ArtifactMember field is needed.

All public signatures and values stay exact: GenomeAlignmentData v1, sheet/components v2, OriginalTask, C input/association v1, optional ArtifactMember.requirement_ids, request/outcome ordering, native measurements and report union ordering. Malformed scientific references and conflicts remain errors; valid cross-domain embedded references cease to be false errors. Do not rename fields, change requiredness, bump schemas, regenerate receipts, rewrite parameters or migrate saved data.

This changes no native/parser/calculator formula, field unit, denominator, row membership, source binding, original task identity, child ownership, method_loop, continuation rule, observation count, credit or practical endpoint behavior.

## Verification required for the repair

1. Re-run the exact existing failing test through `GenomeDriver.acquire_native`, actual AppService publication, D calculation/projection and both own/receiving typed-form resolvers. Its expected original result is coverage `690 / 693`; retain the nested output-selection IDs and all 17 real causes. Run all four existing host modes (v4, XMFA, backbone, BBCols), because every real native acquisition carries the same ArtifactMember field.
2. New positive test: valid nonempty ArtifactMember output IDs absent from the scientific cause union. Also accept its schema-permitted historical absent-field form. Preserve exact input/output equality and detached-copy behavior. A native OriginalTask parameter key named requirement_ids must retain native-JSON meaning; exercise all identical task copies.
3. New negative tests for **each of the seven** scientific row paths: unknown IDs, an OutputRequirement-only ID, missing local causes even if a different/global collection contains the string, duplicate/type-invalid IDs. Keep omission/conflicting reuse of scientific report records rejected by local validation and global union checks.
4. Unknown output-selection IDs, wrong role/format/exact object and altered receipt selection must still fail in the existing host contract; duplicate/invalid ArtifactMember IDs must fail its schema. Never accept the scientific IDs as alternative selector IDs.
5. Keep existing numerical-cell/source-binding unknown-reference tests and altered document/slot/task/association tests. Verify saved validation/projection with scientific parsers/calculators/source comparison disabled; verify explicit recalculation with acquisition and parsers disabled. Recalculation makes a separate result and leaves original data, measurements and history unchanged.
6. Run focused sheet, calculation-contract, calculator, C-input/association, bundle-resolution/projection, saved-structure, host, return and episode-flow suites, with exact selected-tool/child-path assertions. Separate repaired engineering integration from live-resource claims.

## Executed diagnostic evidence and limits

`probe_domains_001.py` ran **16 expected-outcome probes**, all satisfied. It proves the original C outputs, ArtifactMember schema and original selector are valid; the original D error remains; scientific references cannot use the selector ID; missing union causes reject; and selector ID/role/format/exact-object checks remain strict. Deliberate older-shape/native-parameter variants are labeled counterfactual probes, never substitutions for the captured failing acquisition.

The unchanged native v4 calculator was separately run on the captured parsed document and exact explicit selection: union bases **690**, native-declared denominator **693**, coverage **0.9956709956709957**. Complete standalone components are retained. This does **not** establish the failed provider route or its typed return as repaired. No replacement validator was implemented or tested.

Source-pin consequence: sheet.py is already in the GenomeAlignment facade's transitive `_DEPENDENCIES`; editing it changes `implementation_sha256()` automatically. Baseline digest is `42bea987a93cee2902278ba5a2adc047d1b334ffb6f99d7fb2f8f980d410962a`. No dependency-list expansion or change to shared adapter modules is required. Newly configured executions must use the repaired actual pin; the existing adapter binder rejects stale pins. Preserve historical pins, code snapshots, receipts, sheets, native bytes and observations; do not rewrite them to make a new implementation appear original. Saved validation uses original contents and custody, not recalculation. No conversion of old v1/v2 shapes is proposed.

Only this new verification directory was written. No production, other candidate, existing tests, authority/design documents, accounting rows or other agents' jobs were edited/polled/stopped. No live service, remote execution, credential operation or network request was performed. Diagnostic limits were 20 GiB RAM, 4 GiB per-file cap with actual total scratch well below 4 GiB, and no wall-time limit. The repair and repaired full-route verification remain root-assigned work.
