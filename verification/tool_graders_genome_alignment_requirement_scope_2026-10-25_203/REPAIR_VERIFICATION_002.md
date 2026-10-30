# GenomeAlignment requirement-reference scope repair verification

The approved isolated repair is verified. **855 distinct test cases passed** across the new scope tests, existing core suites, six fixture-completed cases, actual host publication/return tests and the composed Workflow. Production has not been changed. Root owns review and integration with other changes.

The earlier diagnosis remains an unchanged historical record in `REPAIR_BOUNDARY_001.md`. The original authoritative goal and all 16 principles were read verbatim before coding and reread after substantial native/source work. Applicable provider D001, C interfaces and extraction contracts remain unchanged. No new scientific formula, numerical meaning, schema, custody rule, episode behavior, controller rule or accounting status is introduced.

## Exact defect and repaired boundary

The original failing data is preserved at `capture_failure_001/data_009.json`. Its sole unresolved array under the old recursive scientific-ID traversal was `/associations/artifacts/0/artifact/requirement_ids = ["native"]`. The actual AppService acquisition producer copied this field from the selected download operands. Its referent is the original selector's `/requirements/1`, an `OutputRequirement` with role `genome_alignment_primary` and declared format `mauve_v4` version `4`.

The adjacent outer `/associations/artifacts/0/requirement_ids` is a different contract: C scientific unmet causes. Its byte-version qualification resolves to the original local scientific report and complete data union. The captured data correctly has 17 scientific causes and no unmet `native` output acquisition cause after acquisition.

Only `repair_candidate/gene_annotation_episode/bvbrc_genome_alignment_sheet.py` changed. A private `_data_requirement_links` helper replaces the whole-data recursive `_links` call in `validate_genome_alignment_data`. It checks exactly these seven named scientific arrays:

| Owner | Direct scientific arrays |
| --- | --- |
| `inputs` when present | `files[*].requirement_ids`, `member_bindings[*].requirement_ids`, `contig_bindings[*].requirement_ids`, `feature_bindings[*].requirement_ids` |
| `associations` when present | `artifacts[*].requirement_ids`, `native_member_joins[*].requirement_ids`, `bbcols_interval_joins[*].requirement_ids` |

The complete C validators still run first, enforcing each array's shape, uniqueness and local report membership. Exact global report inclusion and record equality remain mandatory. The full numerical-components `_links` call and every native, slot, task, document, association and source-binding validator remain unchanged. The AppService owner still validates output-selector membership, role, format, exact object, original operands and receipt custody. D preserves and schema-validates the nested ArtifactMember; it cannot reinterpret its output IDs against a scientific report union.

No string-prefix rule, union of unrelated domains, skipped C validation, silent input repair or ArtifactMember field deletion was added. Native OriginalTask parameter JSON retains its original meanings, including native keys named `requirement_ids`. Public signatures and data v1/sheet-components v2 shapes are unchanged. `REPAIR_DIFF_001.patch` contains the complete source delta and the sole added test file, `tests/test_genome_alignment_requirement_scope.py`.

## Executed verification

| Saved run | Actual result | Scope |
| --- | --- | --- |
| `repair_scope_001` | 80 passed; exit 0; 1.83 s | New positive/negative reference-domain cases |
| `repair_core_001` | 750 passed, 6 missing-file failures; exit 1; 482.61 s | Unchanged sheet, calculation, C extraction/association, retained-record, bundle, projection, facade, tool-info, return, saved-structure and AppService bundle-value suites |
| `baseline_core_failures_002` | Same 6 missing-file failures; exit 1; 0.80 s | Exact six cases on unchanged frozen baseline |
| `repair_completed_fixtures_002` | 6 passed; exit 0; 0.90 s | Only those six cases with exact retained fixtures supplied in a separate copy |
| `repair_host_001` | 13 passed; exit 0; 902.04 s | Original failing resolver case plus complete unchanged host suite |
| `repair_episode_001` | 6 passed; exit 0; 1109.81 s | Complete unchanged composed Workflow suite |

Every run retains its exact arguments, log, JUnit results and receipt. The 750 passing core cases were not rerun. The six failures were fixture omissions in the deliberately narrow 1045-path baseline plus seven retained fixtures, not changed scientific assertions. `FIXTURE_COMPLETION_MANIFEST_001.json` records a separate `repair_fixture_candidate`: all 1053 repaired files copied unchanged, plus exactly seven required retained fixtures. The three added native byte hashes match the already-frozen FILLED_EXAMPLES artifact hashes. The synthetic reverse/overlap document, components and supplied inputs remain explicitly synthetic; the retained producer source remains a source-default example, not deployment evidence. No newer implementation or modified assertion was copied.

The six approved verification groups are covered as follows:

1. **Actual publication and return consumers.** The original `test_public_genome_resolvers_reuse_facts_but_preserve_possession_and_semantics` now passes through `GenomeDriver.acquire_native`, actual AppService `_grade`, bundle consumption, calculation/projection and own/receiving typed-form resolvers. All four native host modes pass through original parent admission. These tests retain real Store, selected-operation and custody implementations with controlled transport.
2. **Valid distinct domains.** New tests preserve nonempty ArtifactMember output IDs absent from scientific causes, historical absence of that optional field, detached-copy behavior and exact input equality. Native task JSON accepts list, string and object values under a native key named `requirement_ids`, with all identical task copies preserved.
3. **Every scientific array stays strict.** Each of the seven paths rejects unknown and output-only IDs, IDs belonging only to the other local report, duplicate IDs, nonstrings, nonarrays, missing local causes, missing global causes and conflicting global records. Nullable C values remain supported.
4. **Output semantics and custody stay strict.** Unknown/scientific-only selector IDs, wrong role/format/exact object, malformed ArtifactMember IDs, wrong task/receipt, unreceived inputs and incorrect current/prior receipt relationships reject in their original owners. Existing tests and assertions were unchanged.
5. **Numerical/source references and saved history stay strict.** Core corruption tests and `component_scope_002/receipt.json` reject bad numerical cause IDs and actual source document/record/member/block references with scientific implementations disabled. Saved host and Workflow replay preserve original forms, receipts and histories; explicit recalculation uses saved data with I/O and parsing disabled.
6. **Complete engineering path.** The unchanged Workflow uses selected tool information, actual bound API calls, controlled loopback HTTP, the production scientific provider, original typed return admission across both parent boundaries, shared `method_loop`, practical endpoints and ordinary controllers. Original ownership, detailed TASK/curt STEERING, exact-zero resource closure and one-observation accounting all pass.

A supplementary diagnostic attempt, `component_scope_001`, incorrectly looked for `requirement_ids` inside XMFABindings and stopped during diagnostic setup. That schema has file/record/member/document reference fields instead. Its unchanged script and failure receipt are retained; `component_scope_002` checks those actual fields and passes six rejection probes. This did not change any implementation or existing test.

## Native values and original custody

`HOST_MODE_RESULTS_001.json` contains the actual published facts and typed forms, with the original bundle artifacts compared exactly against the nested artifacts in the sheet.

| Native mode | Original requested host value | Retained data scientific causes | Byte-version status |
| --- | --- | --- | --- |
| Mauve v4 | 690 / 693 = 0.9956709956709957 | 17 | unknown |
| Mauve 1 XMFA | 40 / 48 = 0.8333333333333334 | 25 | unknown |
| Backbone | 50 | 26 | unknown |
| BBCols | 52 | 28 | unknown |

In every case the nested original `requirement_ids=["native"]` survives, remains absent from the scientific cause union, and the complete original task agrees across publication and all C/data copies. The v4 acquired artifact remains 1007 bytes with SHA256 `a0e700b702070ebd061f6ca5c5b0d9338ad8c330ad16b94c9a0090041cd8cd88`. `repair_inputs_001` separately proves that the exact originally failing data now validates unchanged and produces native components exactly equal to the earlier standalone baseline calculation.

Workflow evidence is under `repair_candidate/verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/runs/mauve-v4-xrhnri2v/`. The numerical return records numerator 690, denominator 693, the explicit native population and zero selected gaps. It retains missing original-source mapping and 18 missing requirements in that distinct Workflow setup. Both parent returns contain the original requested facts.

The launch/API/results episodes complete 1/2/7 own actions respectively and close with exact-zero future estimates, preserving final gains. The scientific and root episodes use the unchanged ordinary yield controller. Saved replay records **26 actions, 27 model calls, 26 observations, 224 record receipts and 5 report attempts both before and after**, with zero new HTTP calls and the original action unchanged. Same-plan recalculation equals the original sheet; changed selected segments yield a separate 677/693 result while retaining the original 690/693 sheet and history. Host changed-denominator recalculation separately preserves union bases 690 while making the fraction unavailable under denominator `none`.

## Pin and integration consequences

The existing dependency closure already includes sheet.py. Its list and framing algorithm are unchanged. Actual pins on these frozen sources are:

- Baseline: `42bea987a93cee2902278ba5a2adc047d1b334ffb6f99d7fb2f8f980d410962a`.
- Repair: `319485ab8568e5aabf462037fdcdaea845fd74c832a5bf2aa0870f88952bc173`.

`repair_inputs_001/receipt.json` records actual binder rejection of the old configured pin with `appservice_adapter_implementation_conflict` and successful binding of the repaired pin. No old source pin, publication, history or receipt was rewritten. Historical optional-field absence still validates. Replay uses original contents and custody with scientific functions and live pin computation disabled; no saved-format migration or implicit recalculation is introduced.

The repair pin above describes this frozen baseline plus this repair. Root must compute the actual pin of any later composition with performance/shared-host changes; it must not label that different source closure with this pin. Integration scope remains exactly the repaired sheet module and the new test file.

Frozen sheet hashes are `110d92d7d046dd29000b5f03801c351912b590c6d14f3f949b457c51ce2e44e8` before and `28cdceb6364ea0ccd7f94768ddf081d54e9b7e19db1e5218bd9862f443fa6654` after. The new test hash is `2f075b6b02024b2ac63bae6151afe967c88658a360de62fec1f1aac38d532eb5`. `REPAIR_BEFORE_MANIFEST_001.json`, `REPAIR_AFTER_MANIFEST_001.json`, `FINAL_AUDIT_001.json` and `OUTPUT_HASHES_REPAIR_002.json` record the full source/evidence audit. Workflow guards report no source additions, changes or missing before-hashes.

## Scope and limits

This verifies the isolated defect repair and its engineering integration on retained native data with controlled decisions/service replies. It does not establish live BV-BRC, a newly executed alignment, a configured model run, local scientific executable deployment or HPC execution. The Workflow alone uses authorized 127.0.0.1 HTTP; pure tests forbid external connections, and saved-read/recalculation checks additionally disable acquisition and scientific parsing/computation as appropriate.

All writes are within this owned verification directory. The original 1052-file baseline and 192 diagnostic outputs remain unchanged. No production, other candidate, authority/design, accounting, shared host or `method_loop` file was edited; no other agent's job was polled, stopped or restarted. Runs used 20 GiB address-space limits and remained below the 4 GiB total scratch ceiling. No wall-time cap was imposed. Final file-byte totals and immutable output hashes are recorded by the final audit.
