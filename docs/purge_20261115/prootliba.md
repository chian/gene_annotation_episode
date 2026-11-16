# prootliba — `bvbrc_*` family of the shared root library (171 modules + 11 JSON)

All paths below are in `gene_annotation_episode/episodic_workflow/root/library/`.

## Totals
- 14 files edited (13 Python, 1 JSON), 0 files deleted, `git diff --stat` over the list: 86 insertions, 141 deletions (net -55; most insertions are the de-indented solr block of `bvbrc_data_readers.py`).
- 12 distinct removal sites. No tests live in this list.
- Import check over all 171 modules (`runs/claude_prootliba_001`): `{}` (all import), run after the last edit.

## Removed, by class
Class 1 (parameters/branches for the past) — 2 sites
- `bvbrc_data_readers.py`: `_decode_native_payload(..., qualified_request=False)` parameter and its "unqualified legacy fixture" branch removed; `_facets(..., is_solr=...)` parameter removed.
- `bvbrc_fastqutils_contracts.py`: `_definition_closure(name, definitions=None)` -> `_definition_closure(name)`.

Class 2 (acceptance of more than the current form) — 5 sites
- `bvbrc_fastqutils_contracts.py`: `_LEGACY_DEFS`, `_CUTADAPT_DEFS`, `_LEGACY_CUTADAPT_DEFS` and the `for historical in (_CUTADAPT_DEFS, _LEGACY_DEFS)` loop in `validate_requested_form` removed. Only the schema rendered from `bvbrc_fastqutils_schemas.json` is accepted; anything else raises the existing `requested_form_invalid`.
- `bvbrc_data_readers.py`: the `application/json` array-with-headers reader ("legacy array/header evidence") removed. Only `application/solr+json` is decoded; other media types fail with the existing `bvbrc_unsupported_media_type`. No current acquirer requests the array form (`bvbrc_data_query.py:510` sends `Accept: application/solr+json` only).
- `bvbrc_comparative_systems_data_inputs.py`: the non-solr branch that called `_decode_native_payload(..., qualified_request=...)` removed (import dropped); two dead `if type(payload) is dict else ...` array branches and the redundant `native_profile == "solr_json_envelope_v1"` test removed.
- `bvbrc_data_schema.py` and `bvbrc_comparative_systems_handoff_schemas.json`: `native_profile` enum loses `json_array_with_headers_v1`; issue code `bvbrc_expected_native_row_array` removed from both, from `bvbrc_data_fields.py` `ISSUE_CODES` and from `bvbrc_data_views.py` `parse_reason`.
- `bvbrc_metacats_calculation_contracts.py`: a non-null `augmented_adequacy` in a saved effects site was still validated although the calculator only ever writes `None` (`bvbrc_metacats_calculators.py:301`). It must now be `None` (`bvbrc_metacats_shape_invalid` otherwise).

Class 7 (history narration) — 5 sites
- `bvbrc_data_schema.py` (docstring: frozen interface date, contract SHA256, corrections 002/003; "Additive correction 2026-10-24_002" comment reduced to its current meaning), `bvbrc_data_query.py` (two "legacy RQL service" remarks), `bvbrc_data_readers.py` (docstrings), `bvbrc_data_fields.py` ("materialized from the reviewed D1 contract (SHA256 ...)"), `bvbrc_metacats_calculators.py` ("Saved v1 counts are never migrated"), `bvbrc_metacats_adequacy.py`, `bvbrc_fastqutils_metric_specs.py` ("additive003" comment), `bvbrc_alignment_bundle_projection.py` ("contracts 025 and 026"), `bvbrc_proteome_sheet_contracts.py` ("review correction 002").

Classes 3, 4, 5, 6: nothing removed (see the next two sections).

## Left because it is a file/digest/version registration
- `bvbrc_fastqutils_legacy_v2_schemas.json` and `bvbrc_fastqutils_legacy_cutadapt_schemas.json` are NOT deleted. No code loads them any more, but `bvbrc_fastqutils_bundle_adapter.py:24-25` (`_DEPENDENCIES`) and `:41` (`_ROOT_DEPENDENCIES`) still name them and `implementation_sha256()` reads every listed file, so deleting them without editing those lists would make the current FastqUtils adapter fail at configuration. To finish: delete the two files and remove their two names from both lists (plus `a110/library/received_execution_dependencies/adapter_source_identity.json:746,751,872,877`, which registers its own copies).
- Every `_DEPENDENCIES` / `_ROOT_DEPENDENCIES` list and `implementation_sha256()` in the `bvbrc_*_bundle_adapter*.py` modules, including `_LEGACY_DEPENDENCIES` in `bvbrc_proteome_bundle_adapter_v2.py:14,18`. Untouched.
- Adapter digests change for every adapter whose listed files were edited (data, comparative systems, fastqutils, metacats, proteome, alignment). No pin was touched.

## Live despite its name
- Proteome adapter 1 and 2 are both current, selectable implementations, not old/new readers: `bvbrc_appservice_adapters.py:17-18,30` installs both; `episodic_workflow/root/bvbrc_proteome_returns.py:49` uses version `'1'`; `root/bvbrc_appservice_publication.py:290,528` lists both. Version 2 is built on version 1's modules (`bvbrc_proteome_bundle_v2_resolution.py:27` subclasses `legacy._Resolution`). So `bvbrc_proteome_bundle_schemas.json`, `bvbrc_proteome_bundle_v2_schemas.json`, `bvbrc_proteome_bundle_v2_*`, `bvbrc_proteome_bundle_adapter_v2.py`, the `legacy` import alias, and the record fields `legacy_sheet` / `components['legacy']` (`bvbrc_proteome_bundle_v2_schemas.json:12087,12288`) all stay.
- "legacy" as BV-BRC GenomeComparison vocabulary: `legacy_first_hsp_only`, `legacy_subject_endpoint_difference`, `legacy_hsp_data_not_retained`, `legacy_blast_pairwise_text` (`bvbrc_proteome_calculators.py:26`, `bvbrc_proteome_native.py:283`, proteome JSON schemas).
- samstat "legacy": the samstat 2.2.3 HTML report format beside 2.5.0 (`bvbrc_fastqutils_samstat_legacy.py:678`, `bvbrc_fastqutils_resolution.py:12`, `samstat_legacy_*` metrics in `bvbrc_fastqutils_schemas.json:533`). Upstream tool versions (`'0.6.10'`, `'0.12.1'`, `'1.1.0'`, `compatible=`) likewise.
- MetaCATS `legacy_example_tsv` layout and `legacy_star` (`bvbrc_metacats_formats.py:140,155`), CodonTree `pgfams_legacy` membership dialect (`bvbrc_codon_tree_native.py:248`): upstream file formats.
- CodonTree `historical_frequencies` / `_validate_historical` (`bvbrc_codon_tree_inputs.py:331,1098`, `bvbrc_phylogeny_common_contracts.py:588-622`, `bvbrc_codon_tree_grader.py:65`): the pre-trim stage of one native run, a field of the current assembly record.
- MinHash `{}` selector and `bvbrc_minhash_grading_v1`/`_v2` (`bvbrc_minhash_views.py:354-359`, `bvbrc_minhash_contracts.py:66`): two current modes (without / with pair metadata). `library/execution_progress.py:1212` passes `{}`; the axis writers emit v1 when there are no inputs (`a101/api_bvbrc_minhash.py:268`).
- `previous`, `prior`, `earlier`, `old_links`, `before`/`after` (trimming, renaming), `frozen`, `incompatible_*`, `prior_acquisition_receipt_refs`: loop variables, same-run records or science.

## Uncertain, kept
- `'reviewed_source'` / `'source_contract'` values in `bvbrc_fastqutils_metric_specs.py` (79), `bvbrc_fastqutils_samstat_specs.py` (62), `bvbrc_fastqutils_cutadapt_specs.py` (23), `bvbrc_fastqutils_sra_specs.py` (1) cite old packets ("193 CONTRACT_001", "207 NATIVE_FIELDS_002.json"). They are data fields of the current spec records, not comments; removing them changes the spec shape. Left for a decision.
- Docstring mentions kept because they describe current limits: "correction002" (`bvbrc_proteome_calculators.py:309`, `bvbrc_proteome_sheet.py:7`), "frozen 002 schema" (`bvbrc_proteome_native_contracts.py:5`), "observed on 2026-10-24" (`bvbrc_data_fields.py:3`), "frozen D1 interface" (`bvbrc_data_query.py:29`).
- Not read line by line: the list is 143,927 lines; coverage was by three vocabulary greps over every file plus reading each hit's context, not a full read.

## Tests run (top-level `tests/`, not edited; all owned by other areas)
- `tests/test_bvbrc_data_readers.py`: 78 passed before -> 71 passed, 7 failed. All 7 call `_decode_native_payload` on `application/json` array captures (`retained(...)` helper and `test_array_unknown_total_...`).
- `tests/test_bvbrc_comparative_systems_data_inputs.py`: 54 passed before -> 52 passed, 2 failed: `test_legacy_array_remains_unknown_population`, and `test_pure_extraction_and_saved_validation_forbid_external_work` (monkeypatches the removed `_decode_native_payload` name on the module).
- `tests/test_bvbrc_fastqutils_contracts.py`: 40 passed (unchanged). `tests/test_bvbrc_metacats_expected_adequacy.py`: 23 passed (unchanged).
- Not attributable to this slot: `tests/test_bvbrc_metacats_calculators.py` and `tests/test_bvbrc_fastqutils_projection.py` fail at collection, and one test in `tests/test_bvbrc_fastqutils_saved_form_evolution.py` fails, because top-level `gene_annotation_episode.phylogeny_formats` / `gene_annotation_episode.bvbrc_fastqutils_sheet` no longer exist (another area's removal).
- Will fail on import of removed names, not run: `tests/test_bvbrc_fastqutils_samstat_contracts.py` (`c._LEGACY_DEFS`, `c._CUTADAPT_DEFS`, reads the legacy cutadapt JSON) and `tests/test_bvbrc_fastqutils_sra.py:10,197` (`_LEGACY_CUTADAPT_DEFS`, two-argument `_definition_closure`).

## Cross-list and external records
- `cross.tsv`: no row names a file on this list; none written (nothing another list imports was changed).
- Public names removed / signatures changed: 12 rows in `/tmp/claude-1000/-home-chia-repos-gene-annotation-episode/6505138e-b5fa-4641-9b42-c1589dca8429/scratchpad/prootlib/prootliba_external.tsv`.

# Literature list (second assignment: 270 `literature_*` modules, list `c.txt`)

## Totals
- 5 files edited, 0 deleted, `git diff --stat` over those five: 2 insertions, 57 deletions. 5 removal sites. (The parent's two earlier edits in this list are not counted.)
- Import check over all 270 modules (`runs/claude_prootliba_012`): `{}` (all import), run after the last edit.
- No test run: the only tests touching the two changed record shapes are axis copies (`a105/tests/...`, `a110/tests/...`), which use the axis libraries, not this one.

## Removed
Class 2 (older record form) — 2 sites
- `literature_product_coupling_projection.py`: `_meaning_v1` (display policy for saved payloads with no `projection_version`, "from the immutable218pin001") deleted; `_projection_policy` now refuses a payload whose `projection_version` is absent or not current with the existing `product_coupling_saved_projection_version_unsupported`. The current writer always records it (`root/literature_product_coupling_storage.py:117`).
- `literature_controlled_response_v3_contracts.py` + `literature_controlled_response_inputs.py` (`_validate_v3_saved_science`): `local_pair_extractions` was "optional only for saved legacy extractions"; it is now required and the "Legacy saved shape" branch that popped it from the expected value is gone. The current writer always emits it (`literature_controlled_response_v3_inputs.py:361`).

Class 7 (narration) — 3 comments
- `literature_controlled_response_inputs.py` ("legacy ordering ... is retained"), `literature_rate_observation_inputs.py` and `literature_rate_observation_calculations.py` ("legacy complete v1 ... retained/unchanged").

## Follow-up outside this list
- `root/literature_product_coupling_storage.py:308` still accepts the saved key set without `projection_version`; it calls `_projection_policy(saved)` first, so such a record is already refused, but the tuple should keep only `original_keys | {'projection_version'}`.

## Left because it is a file/digest/version registration
- As listed by the parent, untouched: `literature_kinetic_inputs` (`LEGACY_VERSION`, `LEGACY_DEPENDENCIES`, `DEPENDENCY_RELEASES`), `literature_summary_precision_release` (`_HISTORICAL_V3/V4`), `literature_endpoint_signal_source_receipt` (`_HISTORICAL_V2/V3_RELEASE`), `literature_optical_dependency_custody`, `literature_saved_adapter_definitions` (`_HISTORICAL_ADAPTERS`), `literature_measurement_validation_implementation`.

## Live despite its name (literature)
- Tool input forms the model selects today, not older records: `version in (None, 'a105_kinetic_source_selection_v1')` and the figure/assay equivalents (`literature_task_selection.py:256-262`), gel `VERSION`/`VERSION_V2` (`literature_gel_inputs.py:151,174`), reaction `DATA_VERSION`/`MEANINGS_DATA_VERSION` (`literature_reaction_inputs.py:234`), compiled-assay "old requests" in the operation schema (`literature_compiled_assay_return_schema.py:17-21`).
- `legacy` as the name of the base calculator a current one is built on: `literature_compiled_assay_calculations.py:349-362` (`_populate_v2` feeds `populate_compiled_assay`), `literature_perturbation_summary.py:463`, `literature_controlled_response_inputs.py:1386` (local dict), `old_facade` = `literature_controlled_response_v2_inputs` (`:2764`).
- `legacy_stored_cell` basis: written today by `root/literature_rate_storage.py:874`.
- "Historical"/"superseded"/"previously" in displays and assessments mean earlier forms, receipts or revised sheets of the same run: `literature_a106_render.py:120`, `literature_experiment_assessments.py:63-80`, `literature_steering_display.py:80,240`, `literature_supplied_result_display.py:86,453`, `literature_current_results.py:1`, `literature_assay_grading_render.py:28`.
- `legacy_task_relevant` / `literature_legacy_figure_contract_work`: as verified by the parent.

## Uncertain, kept
- `literature_perturbation_summary.py:160-169,352-356,585-588`: `interpretation_basis` is optional ("historical v2 inputs"). The source-selection writer always supplies it (`literature_perturbation_source.py:125,177`), but a retained `a106_source_measurements_v2` data document read through `data_source_ref` (`literature_perturbation_inputs.py:149`) may omit it, and I could not show that path is old-only.
- `literature_task_schema.py:17-19`: `yield_settings` is not required ("saved commissions predating private yield bindings"). Making it required changes the model-facing commission schema; I did not establish that every current commission carries it.
- `literature_record_projection.py:26-34`: falls back to `working_state` when `literature_received_fact_display` is absent ("retain historical pure views"); writer of the display key not traced.
- `literature_reaction_return_contracts.py:40` ("historical assay-typed subjects") and `:66` ("legacy numerical sheet"): the numerical and semantic sheet versions are both produced today; the role recovery was not traced.
- `literature_product_coupling_projection.py:103` comment still cites "retained207case"; `literature_reaction_native_inputs.py:7,308` and `literature_partner_native_inputs.py:223` mention the "historical reader"/"old saved records" while describing the current input path.
- Coverage is by vocabulary greps over all 270 files (50,155 lines) and reading each hit in context, not a full read.

# Mechanical pass (third instruction: old digest/release tables go, with their readers)

This reverses the earlier "left because it is a file/digest/version registration" entries for OLD forms in both lists. Current-pin code was not touched (another agent owns it).

## Totals
- 9 files touched: 6 edited, 3 deleted (2 JSON, 1 module); `git diff --stat`: 12 insertions, 26,859 deletions (almost all of it the two JSON files and the historical release tables).
- Import check over both lists (440 modules, `runs/claude_prootliba_013`): 438 import; 2 fail (`literature_a105_aggregation`, `literature_a106_subscore`), both only because `root/literature_sheet_updates.py:19` still imports the deleted `literature_saved_adapter_definitions`. That file is outside my lists.

## Removed
- `bvbrc_fastqutils_legacy_v2_schemas.json` and `bvbrc_fastqutils_legacy_cutadapt_schemas.json` deleted; their names removed from `_DEPENDENCIES` and `_ROOT_DEPENDENCIES` in `bvbrc_fastqutils_bundle_adapter.py`.
- `literature_kinetic_inputs.py`: `LEGACY_VERSION`, `LEGACY_DEPENDENCIES`, `DEPENDENCY_RELEASES` removed; `DEPENDENCIES` is now a literal with the same current values. `literature_kinetic_validation.py` accepts only the current extraction version (`_fail("extraction.version")` otherwise).
- `literature_summary_precision_release.py`: `_HISTORICAL_V3_FILES`, `_HISTORICAL_V3_SLOT_FILES`, `_HISTORICAL_V4_FILES`, `_HISTORICAL_V4_SLOT_FILES`, `is_historical_v3_summary_precision_implementation`, `is_historical_v4_summary_precision_implementation` removed.
- `literature_endpoint_signal_source_receipt.py`: `_HISTORICAL_V2_RELEASE`, `_HISTORICAL_V3_RELEASE`, `retained_v2_receipt`, `retained_v3_receipt` removed.
- `literature_optical_dependency_custody.py`: `saved_dependencies_valid` accepts the current receipt only.
- `literature_saved_adapter_definitions.py` deleted (`_HISTORICAL_ADAPTERS`, `defining_adapter_coordinates`). It only mapped pre-reorganisation `gene_annotation_episode.<module>` adapter names to current ones; adapter names are written today from `type(repository).__module__` (`root/literature_sheet_updates.py:154,161`), so nothing current produces the old names.

## Follow-ups outside my lists (root area)
- `root/literature_sheet_updates.py:19,173`: drop the import and the `defining_adapter_coordinates` call. Until then that module, and anything importing it, fails to import.
- `root/literature_kinetic_summary_precision_storage.py:17-18,412,414`: top-level import of the two removed `is_historical_*` predicates, so this module fails to import until they and their branches go.
- `root/literature_endpoint_signal_storage.py:220-224`: lazy imports of `retained_v3_receipt` / `retained_v2_receipt`; fails only on the old-receipt path.
- `root/literature_kinetic_storage.py` and `root/literature_population_task_metadata.py` no longer reference `LEGACY_VERSION` (already changed by another agent).

## Not touched (current-pin mechanism, the other agent's)
- `literature_kinetic_inputs.DEPENDENCIES` and `literature_optical_validation._LEXICAL_DEPENDENCY`: single current tables whose values name old top-level modules that no longer exist on disk (`gene_annotation_episode.literature_assay_inputs`, `...literature_rate_native_inputs`, `...literature_partner_source_fields`). No alternative is accepted there.
- `literature_optical_dependency_custody` `_PINNED` / `_SPEC` reconstruction of original hashes inside `current_dependencies`; `literature_measurement_validation_implementation`; `_CURRENT_FILES` / `_RELEASE` tables; all `implementation_sha256` code.
- No `_RETAINED_SAVED_DEPENDENCY_RELEASES`-style table exists in either list.
