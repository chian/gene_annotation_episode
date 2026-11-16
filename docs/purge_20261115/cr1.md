# cr1: one form of the literature controlled-response family (15–16 November 2026)

Area: `R/a104`, `R/a105`, `R/a106`, `R/a108` (`R` = `gene_annotation_episode/episodic_workflow/root`). No sub-agents.
All product and test edits below are in Checkpoint 5 (`330ef3fe7`); compare with `git diff 729169ec5 330ef3fe7 -- R/a10{4,5,6,8}`.
Line numbers marked "(before)" are at `729169ec5`. Scratch: `<scratchpad>/cr1/` (`collapse_inputs.py`, `collapse_v3.py`,
`collapse_calc.py`, `propagate.py`, `a108.py`, `uses.py`, `schema_diff.py`, `verify_copies.py`, `before_after.py`, `results.tsv`,
`orig/` = the 50 original family files).

## Read this first

1. **Only v3 was live; v1 and v2 are gone in all five copies.** The live form computes the same thing: 34 constructed
   nominations read, validated and populated through the original modules and through the collapsed ones give
   byte-identical JSON (extraction and population; run `claude_cr1_071`).
2. **Open cross-arm item (needs the a101 and shared-root owners).** `communication.py` in every arm requires a declared
   `literature_controlled_response_component_cells` schema to equal the local `controlled_response_cells_schema()` exactly.
   Removing the v2 remnants changes that schema. a104, a105 (both copies), a106 and a108 now agree on
   `sha256(json.dumps(schema, sort_keys=True)) = 7afe38bd83305cfe24e80be195b9faa84191f06341b3c39bab9c3ea21919f0e0`;
   `R/a101/library/retained_input_authority` and the shared root (`R/library`, `R/literature_controlled_response_storage.py`)
   still give the old `795c3647…106bcc` (measured, run `claude_cr1_043`). Until they apply the two handoff rows, a
   contract carrying this schema between a101/shared root and these four arms is refused with `invalid_schema`.
   No test in my gate exercises that crossing.
3. **Three whole test files deleted (282 collected tests), no live-form expectation edited.** See `cr1_deleted_tests.tsv`.
4. One older record shape inside v3 was also removed (extraction without `local_pair_extractions`); a106 had already
   done this, a105/a104/a108 had not. Details under "Schema changes".

## Step 1: which profiles a current product path can select

Method: AST reachability over each copy from every product (non-test) importer in the repository
(`uses.py`, run `claude_cr1_003`), plus grep of tool names and version strings.

| profile | evidence | verdict |
|---|---|---|
| v3 | Registered tool `literature.controlled_response.source_v3.populate` (`a105/library/literature_task_families.py:38`, `literature_population_catalog.py:95`; the only `literature.controlled_response.*` name in the four arms, 209 occurrences). `literature_controlled_response_storage.py:367` accepts only that tool; `:532-533` `populate` → `:481` `populate_v3` → `:508` `source.read_controlled_response_v3_inputs` → `v3_inputs.py:196 (before)` `open_controlled_response_sources`. Writer of `controlled_response_source_extraction_v3`: `v3_inputs.py:421 (before)`. | live |
| v2 | Entry points `read_controlled_response_v2_inputs` (`v2_inputs.py:183 (before)`) and `validate_controlled_response_v2_extraction` (`:201`): referenced only inside that file and by `tests/test_literature_controlled_response_v2_inputs.py`. `_SavedSourceContext` (profile `'v2'`) constructed only at `inputs.py:1915 (before)` in `_validate_v2_saved_science`. No tool name, no registry row, no writer of a `…_v2` selection outside these functions. | dead |
| v1 | `read_controlled_response_inputs` (`inputs.py:963 (before)`, the only direct `SourceContext(` besides `open_controlled_response_sources` at `:1472`) and `validate_controlled_response_extraction` (`:1359`): only `tests/test_literature_controlled_response_inputs.py`. The first-form sheet calculator `populate_controlled_response` / `validate_controlled_response_inputs` (`literature_controlled_response_calculations.py`): only v1 code and two test files. | dead |

Product roots of the whole family (a105/library): 14 names, all in `storage`, `render`, `prompt`
(`COMPONENTS`, `VIEWS`, `PROVIDER`, `LiteratureControlledResponseRepository`, `controlled_response_cells_schema`,
`controlled_response_population_schema`, `implementation_descriptor`, 5 render functions, 2 prompt constants).

## Step 2: what was done (a105/library; the other copies follow from it)

Site counts in `inputs` + `v2_inputs` + `v3_inputs` + `v3_population` (identifiers counted outside string literals):

| copy | files | lines | profile-branch lines | `controlled_response_v2` | v1/v2-named identifiers |
|---|---|---|---|---|---|
| a105/library before → after | 4 → 3 | 3462 → 2712 | 37 → 0 | 22 → 0 | 43 → 0 |
| a105 `…/source_evidence_examination/tools` | 4 → 3 | 3462 → 2712 | 37 → 0 | 22 → 0 | 43 → 0 |
| a104 | 4 → 3 | 4446 → 2736 | 36 → 0 | 22 → 0 | 43 → 0 |
| a106/library | 4 → 3 | 4433 → 2736 | 36 → 0 | 22 → 0 | 43 → 0 |
| a108 `retained_input_authority` (schema-only subset) | 3 → 2 | 376 → 276 | 0 → 0 | 6 → 0 | 14 → 0 |

"Profile-branch lines" = lines with `.profile`, `._profile`, `owner_profile`, `'profile'` or the `tagged` switch.
Remaining `…_v1` / `…_v2` strings are current record versions of the live form and are unchanged:
`controlled_response_owner_inputs_v2`, `controlled_response_owner_sheet_v2`, `controlled_response_covariance_source_v1`,
`controlled_response_rate_figure_{selection,extraction}_v1`, `controlled_response_rate_pixels_v1`,
`controlled_response_bar_runs_v1`, `controlled_response_local_{inputs,sheet}_v1`.

### Removed (shared `literature_controlled_response_inputs.py`, 2449 → 1791 lines)
- Entry points and what only they reached (15 top-level names): `VERSION`, `SELECTION_VERSION`,
  `validate_controlled_response_selection`, `read_controlled_response_inputs`, `validate_controlled_response_extraction`,
  `_arm`, `_covariance` (with its `owner_profile` parameter), `_cross_control_alias_conflict`, `_resolve_control_alias`,
  `_selected_arm_field`, `_ROOT_FIELDS`, `_validate_v1_saved_science` (240 lines), `_validate_v2_saved_science` (100),
  the dispatcher `validate_controlled_response_saved_science` (the v3 function now has that name), base class
  `_SavedSourceContext` (folded into `_SavedV3SourceContext`; its `covariance` attribute and v2 `source()` are gone),
  19 unused entries of `_RESULT_FIELDS` (6 kept).
- Branch arms collapsed to the v3 side in `SourceContext` (`_profile`, the `profile` property, `hasattr`/`getattr`
  guards that only served contexts without v3 registries), `open_controlled_response_sources`,
  `read_controlled_response_arm_science`, `read_controlled_response_text_measurement`, `finish_controlled_response_arm`,
  `finish_controlled_response_inputs`, `_uncertainty`, `_uncertainty_piece`, `_assemble_uncertainty` (parameter `stable`
  was always true), `_reading_entry`, `_reading_field`, `_scope_entry`, `_measurement_entry` (2-tuple endpoint binding),
  `_saved_interpretation` (parameter `control_alias`), `_representations` (`.get('graph_details')`).
- First-form leftovers inside functions v3 calls: the `linear_bar` "graph_unimplemented" arm of `_measurement` and of
  `_operand_from_arm`; `projection_indices` created by `_empty_covariance` and popped again in
  `_project_owner_covariance` / `bind_controlled_response_covariance_scope` (the record now starts with
  `provided_owner_projection`, same final key order); `_calculation_inputs` writing `INPUT_VERSION` that
  `_owner_projection` overwrote (it now writes `controlled_response_owner_inputs_v2` directly).
- `reading_selector=None`, `companion_arms=None`, `covariance_scopes=None` defaults (only the removed profiles omitted
  them; every live caller passes them).
- A selection that is not v3 is refused by the existing error `controlled_selection_schema_invalid`
  (`SourceContext.__init__` and the v3 selection validation). `unsupported_stage_selector` and the codes raised only
  inside the deleted functions can no longer be raised; none of them was in a schema.
- `literature_controlled_response_calculations.py` (529 → 302 lines): `INPUT_VERSION`, `VERSION`, `CELL_FIELDS`,
  `REASONS`, `validate_controlled_response_inputs`, `populate_controlled_response`, `_validate`, `_validate_arm`,
  `_validate_covariance`, `_effect_reasons`. What remains is the arithmetic the owner calculator uses; its alias in
  `literature_controlled_response_owner_calculations.py` is `arithmetic` instead of `_old` (88 sites, as the other
  modules already call it).

### Moved (so that v3 stands alone)
- `literature_controlled_response_v2_inputs.py` is deleted. `literature_controlled_response_v3_inputs.py` (440 → 814
  lines) now holds what it used from it: `arr`, `enum`, `embed`, `_graph_schema`, `_sheet_schema`, the extraction core
  (`_extraction_core_schema`, formerly the v2 `_extraction_schema`), `_graph_request`, `_read_graph`, `_graph_reading`,
  `_saved_roster`, `_saved_images`, `_check_witness`, `_validate_text`, `_validate_measurement`, `_validate_graph`.
  Not moved (dead): `controlled_response_v2_arguments_schema`, `validate_controlled_response_v2_selection`,
  `read_controlled_response_v2_inputs`, `validate_controlled_response_v2_extraction`.
- The v2 additions to the selection (axis scale, terminal edge) are part of the one selection core in the shared
  module (`_selection_core_schema`, version const `controlled_response_source_selection_v3`); `_schemas()` in the v3
  module completes it as before.
- Registries naming the deleted file: `a105/…/source_evidence_examination/implementation_sources.py` (2 entries),
  `a105/library/literature_sheet_updates.py` and `a106/library/literature_sheet_updates.py` (1 map entry each),
  `a106/literature_implementation_sources.py`, `a104/library/source_descriptor_inputs.py`, 12 `a104/**/binding_record.py`.

### Schema changes (all are removals or renames of dead-version material; `schema_diff.py`, runs `claude_cr1_040-042`)
Compared before/after over the 7 schemas of `_schemas()` and the cells schema:
1. Defs `Selection` and `S_*` (the embedded v2 selection, never referenced by a v3 schema) are gone: 374 defs counting
   prefixed copies.
2. `DependencyRecord.reader_contract_version` const `…extraction_v2` → `…extraction_v3` in the 15 unreferenced copies
   (the referenced one already said v3).
3. Def `MeasurementExtractionV2` is named `GraphMeasurementExtraction` (17 defs, 34 `$ref`s).
4. Diagnostic code enum loses `graph_rate_reader_unimplemented` and `covariance_shared_values_conflicting`; their only
   raising sites were v1/v2 code.
5. `local_pair_extractions` is required in the extraction, and `validate_controlled_response_saved_science` no longer
   accepts an extraction without it (4 lines). The writer always emits it; a106 already had both changes; the only test
   of the older shape asserted its refusal and still passes.
No property, def or enum member reachable from a v3 schema root was otherwise added, removed or changed.
`implementation_descriptor()['native_schema_sha256']` changes accordingly (no test or fixture pins it).

### Tests and fixtures (a105)
- `tests/test_literature_controlled_response_v3_inputs.py`: `Fixture` no longer inherits; it holds the source, witness,
  covariance and measurement helpers itself and loads `fixtures/retained_reference/a105_controlled_full_source_design_069/CONSTRUCTED_SOURCE_SELECTIONS.json`.
- Fixture conversion (run `claude_cr1_012`): the 14 selections of `CONSTRUCTED_SOURCE_CASES_001.json` rewritten once with
  `version = controlled_response_source_selection_v3` and the five empty v3 collections; checked per case that all other
  values, value types and key order are unchanged. The new file keeps `name`, `selection`, `source_covariance_text`;
  the six keys only the v2 tests read are dropped. Old file deleted (no other user).
- `test_literature_controlled_response_v3_stages.py` uses that `Fixture` (`local=False`) instead of loading the v2 test
  file with `runpy`. `…_local_calculations.py`, `…_owner_calculations.py`, `…_saved_local_witnesses.py`: alias and
  wording only (see `cr1_deleted_tests.tsv`). No assertion about a scientific value was edited.
- `a106/tests/fixtures/a106_source_components/controlled_response_source_case.json`: selection converted the same way
  (its user is `tests/test_intervention_received_score_operands.py`, handoff row written); README states current content.

## Copies and their equivalence
- The originals of a105 tools, a104 and a106 were AST-identical to a105/library apart from project import statements,
  except that a106 already carried change 5 above. Each was regenerated from the a105/library result with its own
  import sources kept per imported name (`propagate.py`). Result (`verify_copies.py`, run `claude_cr1_070`): all 8
  remaining family modules of each copy are AST-identical to a105/library apart from project imports; on 17
  constructed nominations each copy's extraction and population digests equal a105/library's; schema dumps of the four
  copies are byte-identical. Side effect: a104 and a106 files now use a105's line layout (they were wrapped differently).
- a108 keeps a schema-only subset (`inputs`: selection core; `v2_inputs` + `v3_inputs`: schema builders). Shown: each
  original was exactly the corresponding subset of the a105 original; the new files are the same subsets of the
  collapsed a105 modules (35 and 10 statements, all present in order). `_old` → `arithmetic` (7 sites).
- Not touched: `storage`, `local_calculations`, `v3_population`, `figure_inputs`, `render`, `prompt` in every copy.
  The A105 grading and sheet-saving code is unchanged; record versions `literature_controlled_response_record_v3` and
  `…component_fact_v3` are unchanged.

## Left for decision
1. a101 and shared-root copies (item 2 at the top): handoff rows `cr1 → pa101` and `cr1 → prootlib,proot`.
2. The 121 deleted v2 tests also exercised code v3 still uses (graph partials, covariance projection, saved-record
   tampering) through the v2 entry point. The 14 remaining family files keep 228 tests. Whether to rewrite some of those cases against
   the v3 reader is a coverage decision I did not take.
3. Eight diagnostic codes in the extraction enum had no raising site before this work either and were left:
   `canceled_source_representation_difference`, `covariance_incomplete_owner_binding`, `covariance_owner_subset`,
   `source_covariance_full_scope_invalid`, `source_covariance_projection_loss`, `source_model_active_scope_unresolved`,
   `source_reading_nomination_identity`, `unresolved_active_representation_model`.
4. `validate_controlled_response_local_sheet` and `validate_controlled_response_v3_population` are live-form validators
   called only by tests; kept.
5. The module map in `literature_sheet_updates.py` `_adapter` (old module path → `library` path; a105 and a106) is
   relocation material outside this task; only its v2 entry was removed.
6. Fixture directory name `retained_reference/a105_controlled_full_source_design_069` kept (file renames not required).

## Gate
1. Site counts: table above.
2. Import check over all product modules: a105 1287 modules `{}` (`claude_cr1_044`), a108 924 `{}` (`045`),
   a106 1536 `{}` (`046`), a104 3899 `{}` (`047`).
3. Tests, one file per launcher run, isolated form. Expected before launching: about 345 s pytest-reported
   (258 s for the 14 controlled-response files + 87 s others), about 390 s wall. Measured: 335 s pytest-reported,
   352 s summed wall, 22 files. No test that passed before fails.

| file | before (`rec4_gate_results.tsv`) | now | run |
|---|---|---|---|
| `a105/tests/test_literature_controlled_response_v3_inputs.py` | 22 passed in 18.80s | 22 passed in 17.53s | claude_cr1_048 |
| `a105/tests/test_literature_controlled_response_v3_stages.py` | 37 passed in 13.85s | 37 passed in 13.83s | claude_cr1_049 |
| `a105/tests/test_literature_controlled_response_saved_local_witnesses.py` | 17 passed in 10.51s | 17 passed in 10.01s | claude_cr1_050 |
| `a105/tests/test_literature_controlled_response_local_calculations.py` | 18 passed in 5.58s | 18 passed in 5.30s | claude_cr1_051 |
| `a105/tests/test_literature_controlled_response_owner_calculations.py` | 49 passed in 0.11s | 49 passed in 0.11s | claude_cr1_052 |
| `a105/tests/test_literature_controlled_response_v3_population.py` | 8 passed in 6.79s | 8 passed in 6.72s | claude_cr1_053 |
| `a105/tests/test_literature_controlled_response_figure_inputs.py` | 35 passed in 0.25s | 35 passed in 0.24s | claude_cr1_054 |
| `a105/tests/test_literature_controlled_response_communication.py` | 6 passed in 10.53s | 6 passed in 8.75s | claude_cr1_055 |
| `a105/tests/test_literature_controlled_response_render_v3.py` | 3 passed in 8.70s | 3 passed in 8.27s | claude_cr1_056 |
| `a105/tests/test_literature_controlled_response_runtime_custody_v3.py` | 5 passed in 16.67s | 5 passed in 15.94s | claude_cr1_057 |
| `a105/tests/test_literature_controlled_response_uncertainty_units_v3.py` | 2 passed in 17.19s | 2 passed in 16.89s | claude_cr1_058 |
| `a105/tests/test_literature_controlled_response_unavailable_joint_storage_v3.py` | 6 passed in 40.58s | 6 passed in 41.13s | claude_cr1_059 |
| `a105/tests/test_literature_controlled_response_scope_context_storage_v3.py` | 7 passed in 43.68s | 7 passed in 42.57s | claude_cr1_060 |
| `a105/tests/test_literature_controlled_response_storage_v3.py` | 13 passed in 64.62s | 13 passed in 62.99s | claude_cr1_061 |
| `a105/tests/test_literature_assay_grading_inputs.py` | 25 passed in 4.14s | 25 passed in 3.86s | claude_cr1_062 |
| `a105/…/source_evidence_examination/tests/test_literature_assay_grading_inputs.py` | 25 passed in 4.21s | 25 passed in 4.29s | claude_cr1_063 |
| `a105/tests/test_literature_a105_aggregation_325.py` | 16 passed in 9.49s | 16 passed in 9.38s | claude_cr1_064 |
| `a105/tests/test_private_context_hook_ownership.py` | 8 passed in 5.52s | 8 passed in 5.30s | claude_cr1_065 |
| `a105/tests/test_literature_numerical_declarations_203.py` | 234 passed in 29.01s | 234 passed in 25.75s | claude_cr1_066 |
| `a104/tests/test_saved_binding_restoration.py` | 99 passed in 24.81s | 99 passed in 24.74s | claude_cr1_067 |
| `a104/tests/test_registered_saved_bindings.py` | 18 passed in 7.17s | 18 passed in 7.24s | claude_cr1_068 |
| `tests/test_intervention_received_score_operands.py` (other area; reads the converted a106 fixture) | 24 passed, 8 failed (earlier `results.tsv`) | 24 passed, 8 failed (same 8: `test_scoped_component_key_cannot_hide_a_saved_inference`) | claude_cr1_069 |

Deleted from the previous 17: `test_literature_controlled_response_calculations.py` (93 passed), `…_inputs.py` (68 passed),
`…_v2_inputs.py` (121 passed). a104, a106 and a108 have no test of this family; their evidence is the equivalence above.

## Size (`git diff --numstat 729169ec5 330ef3fe7`, four arms)
55 files: 43 modified, 11 deleted, 1 added. Product `.py`: 41 files, +5492 −11833 (a104/a106 counts include the changed
line layout). Test `.py`: 8 files, +76 −1938. Fixtures and README: 6 files (3 deleted, 1 added, 2 rewritten).

## Handoff rows written (none were addressed to this slot)
- `cr1 → pa101`: apply the a108 result to `a101/library/retained_input_authority` (files were identical apart from the arm name).
- `cr1 → prootlib,proot`: make the shared-root `controlled_response_cells_schema()` identical (target digest and the five schema effects).
- `cr1 → ptests`: `tests/test_intervention_received_score_operands.py:143-145` `args.update(...)` is now a no-op; delete it.
