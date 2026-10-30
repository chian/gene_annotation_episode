# MinHash tool-information correction

The result description and manual incorrectly said that the production return path had no supplied metadata and could not recalculate distance or p-value. The existing implementation and retained verification in packet 523 already establish explicit pair-input selection, saved-sheet calculation and requested typed returns. This correction reuses that work.

The original user-supplied attachment remains authoritative. This packet records the narrowly assigned library edit; it does not redefine the goal or replace its operating principles.

## Exact changes

- `gene_annotation_episode/api_bvbrc_minhash.py`: replace only `BVBRCMinhashService.result_capabilities()[0].description` with the exact parent-approved description. The operation name, empty argument schema, launch descriptions, execution and numerical code are unchanged.
- `gene_annotation_episode/knowledge/bvbrc-minhash.md`: preserve the heading and first two paragraphs byte for byte; replace only the result section using section B of packet 533. Use `records` in the legacy-result explanation and explicit `{}` action arguments. Omit the internal selector version label from the instructional prose; the existing assignment schema remains authoritative. Correct the source wording to include completed own work, received child returns and selected parent inputs, as the host permits. Describe the calculations family as four saved pair input fields, so it does not imply a complete sheet or metadata envelope is returned.
- `gene_annotation_episode/knowledge/index.json`: replace only the MinHash summary with section C of packet 533, unchanged.

No prompt/template, schema, registry, test, numerical implementation, progress row or historical design record was edited. The complete three-file before snapshots, scoped diff and SHA-256 pairs are retained here.

## Factual trace

| Manual statement | Complete implementation inspected |
| --- | --- |
| Parent sees name, description and resources; selected child receives substantive instructions through the existing library | `tool_information.py` in full, including `parent_view`, `_documents`, `make_tool_info` and `workflow_execution_catalogs`; `scientific_tool_library.py` in full; selected-information assignment/resolution/catalog/context functions in `scientific_process_episodes.py`. |
| Legacy `{}`, explicit `native_result` and `saved_sheet`, fixed empty result arguments | `bvbrc_minhash_contracts.py` in full; `api_bvbrc_minhash.py` in full, especially `prepare`, `result_catalog` and `publish`. |
| Selected saved sheet belongs to the original request and response | `BVBRCMinhashHost.validate_inputs`, `read_received_result`, `_frozen_inputs` and `read_own`, within the complete host file; saved-result validation in the complete contracts and service files. |
| No search or metadata acquisition by the result operation; completed selection replay retains its original output | Complete `APIServiceExecution.execute` and `_execute_locked`; complete `publish_existing_acquisition`; complete service/host methods. The cache path reads the original handoff. Replay returns retained outcomes/publications before fresh calculation or pointer extraction. |
| Native row order, duplicates, raw values, parse statuses and valid partial measurements remain retained | Complete `bvbrc_minhash_grader.py`, `bvbrc_minhash_views.py` and service publication path. |
| Four positive-integer-or-null inputs, no boolean/string coercion, exact query association and one evidence record per nonnull field | Complete contracts module, especially `_pair_metadata`, `_query_associations` and publication-input validation. |
| Source ownership, original native or bound auxiliary artifact, exact JSON pointer and exact integer value | Complete host file, especially `possession`, `_metadata_artifact`, `_json_value`, `_pointer` and `metadata_bindings`. A stored source alone does not establish custody. |
| Pair joins use both original `row_index` and `genome_id`; duplicates and mismatches remain diagnosed | Complete grader `_metadata_index` and `calculate_minhash_components`, and complete projection association/validation path. |
| Supplied parameters do not prove remote parameters; response/search metadata do not provide the missing quantities | Complete contracts, grader, service and projection paths retain `native_parameter_equivalence=unestablished` and unknown search metadata; packet 517 contract and root clarification state the available-data limit. |
| Sampled shared/union fraction, capped and unsaturated distance, existing binomial upper tail, unavailable dependent cells and numerical diagnostics | Complete grader, including shared fraction helper, distance and p-value functions; complete projection validator. No numerical formula or default was changed or added. |
| Four requested return families, saved values only, source-only/counts-only boundaries | Complete `minhash_fact_sources`, `project_minhash_facts` and host requested/own/received/admission functions. Calculation rows copy only the four saved metadata scalar fields, not complete provenance or pair records. |
| Discovery summary and frozen instructions | Complete `ToolKnowledge` and `ScientificToolLibrary` implementations. Metadata discovery does not load manual bodies; frozen snapshots preserve their prior instruction bytes. |

The section B phrase “received source” was narrower than the actual host contract: completed own selected work also qualifies, and selected parent inputs have custody checks. The corrected wording follows those branches. The draft's broad “pair inputs” return phrase was made precise to match the four scalar fields actually projected. No out-of-scope implementation repair was needed.

The saved-sheet statement follows `ROOT_INTERFACE_CLARIFICATION_001.md`: the existing calculator may internally validate the saved native cells by calling the parser. The manual does not claim parser-free recalculation. Ordinary retained-output replay remains separate from a newly selected calculation.

## Verification performed and reused

`STATIC_VERIFICATION.json` records source-only checks using Python standard-library AST/JSON parsing and byte/structure comparison:

- The evaluated parent description exactly equals the approved text.
- The service AST is identical after substituting the old description back into the new tree. This covers all executable code, launch declarations and schemas.
- The manual heading and first two paragraphs are byte-preserved.
- The new discovery summary exactly equals section C; the parsed index is otherwise identical.

No application import, pytest run, scientific execution, service request or HPC execution was performed by this workload. No wording-mirroring tests were added.

The existing bounded numerical/episode evidence was reused from `verification/tool_graders_minhash_metadata_verification_2026-10-27_523/INTEGRATION_VERIFICATION_002.md`, read in full. That report records 47 passing selected cases in check005 and the already passing check004/component evidence. These are historical engineering-fixture results, not tests run for this wording change. Its explicit 2/3 example records k=1 distance `0.22314355131420976` and p-value `0.2592592592592592`; selected saved-sheet k=2 records `0.11157177565710488` and `0.10400000000000001`. Native values `0.223144` and `0.259259` remain separate.

## Existing test nodes handed to root

Both requested test modules were read in full. These existing nodes cover library construction, parent/child information separation, unchanged callable contracts, frozen snapshots and metadata/manual retrieval:

1. `tests/test_child_tool_information.py::test_every_actual_registry_and_execution_operation_has_four_fields`
2. `tests/test_child_tool_information.py::test_parent_information_excludes_instructions_child_gets_actual_contract_and_executes`
3. `tests/test_child_tool_information.py::test_new_snapshot_reopens_frozen_information_and_legacy_snapshot_is_not_upgraded`
4. `tests/test_tool_knowledge.py::test_metadata_discovery_does_not_open_manuals_and_reads_page_exact_lines`
5. `tests/test_tool_knowledge.py::test_frozen_run_keeps_instructions_when_source_changes_and_detects_corruption`

Root owns any new bounded execution under 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time limit. This packet does not claim those tests have run. The original verified arithmetic and replay paths were not changed, so repeating their scientific tests is not needed for this text-only correction absent a new concern.

The task completes the assigned factual tool-library correction and static checks only. Generic episode TASK/STEERING construction and live BV-BRC results/remote sketch parameter equivalence remain separate, unfinished obligations; this packet claims neither. The objective and all ten operating principles were reread verbatim from the original attachment after the substantive source work, followed by the complete 517 contract and root interface clarification. `GOAL.md` was not read or used.
