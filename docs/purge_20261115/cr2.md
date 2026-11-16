# cr2: the shared-root copy of the literature controlled-response family, one live form (16 November 2026)

Area: `R/*.py`, `R/library/`, the non-arm homes under `R`, `R/tests/`, `gene_annotation_episode/*.py`, `tests/`
(`R` = `gene_annotation_episode/episodic_workflow/root`). No sub-agents. I committed nothing; my edits were swept into
Checkpoint 9 (`9fc7d3e54`, whose message names only the a102 work) while I was still running the gate. See them with
`git show 9fc7d3e54 -- R/library tests/test_intervention_received_score_operands.py`.
Scratch: `<scratchpad>/cr2/` (`collapse_root.py` generator, `src.py`, `verify_same.py`, `measure.py`, `compare.py`,
`counts.py`, `uses.py`, `untested4.py`, `orig/` = the 17 files before, `m_before.json` / `m_root.json` / `m_a105.json`).

## Read this first

1. **Done. The shared root now gives the arms' cells schema.**
   `sha256(json.dumps(controlled_response_cells_schema(), sort_keys=True, allow_nan=False))`:
   before `795c364703a3116ff809c0d893462b1d74e2af9caf491cf212730abf30106bcc` (run `claude_cr2_006`), now
   `7afe38bd83305cfe24e80be195b9faa84191f06341b3c39bab9c3ea21919f0e0` (run `015`); a105 gives the same (`007`).
   All seven copies agree now, a101 included (a104, a105 library, a105 tools, a106, a108, a101, shared root; run `053`).
2. **v1 and v2 were dead in the shared root too**; nothing had to be stopped on (evidence below).
3. **v3 computes the same.** 34 constructed nominations read, validated and populated through the shared-root modules
   before and after give byte-identical JSON text (extraction 34/34, population 34/34), and identical to a105's.
4. **No test and no fixture of the dead forms existed in `R/tests` or `tests/`.** Nothing deleted, nothing converted;
   `cr2_deleted_tests.tsv` holds its header only. The one change in `tests/` is the handoff row from cr1.
5. **The shared-root copy has no test of its own.** All 228 family tests import a105's copy. Details under "Left for decision".
6. **Untested live code (point 6) is measured, not estimated:** of 502 failure, diagnostic and reason-code sites in
   the live family functions, the 228 remaining tests reach 137. Table below, full list in `cr2_untested_live_sites.tsv`.

## Step 1: which profile a current shared-root product path can select

Method: grep of tool names and version strings outside the arm directories; AST reachability from every importer
in `gene_annotation_episode/`, `tests/`, `examples/`, `tools/` (`uses.py`, run `003`). Line numbers are before this work.

| profile | evidence | verdict |
|---|---|---|
| v3 | Only tool name of the family outside the arms: `literature.controlled_response.source_v3.populate` (87 occurrences, no other `literature.controlled_response.*`). `R/literature_controlled_response_storage.py:426` accepts only that tool; `:601-602` `populate` calls `populate_v3`; `:543` `validate_controlled_response_v3_selection`; `:564` `read_controlled_response_v3_inputs`; `:646` `validate_controlled_response_v3_extraction`. | live |
| v2 | `read_controlled_response_v2_inputs` (`library/…v2_inputs.py:64`) and `validate_controlled_response_v2_extraction` (`:84`): no reference outside that file. `_SavedSourceContext` (profile `v2`) built only at `library/…inputs.py:2267` inside `_validate_v2_saved_science`. | dead |
| v1 | `read_controlled_response_inputs` (`library/…inputs.py:1101`, the only direct `SourceContext(` besides `:1782`) and `validate_controlled_response_extraction` (`:1657`): no reference outside that file. `populate_controlled_response` / `validate_controlled_response_inputs` (`library/…calculations.py:588`, `:266`): used only by v1/v2 code (`inputs.py:33,995,1652,2069`). | dead |

Who set the profile: `SourceContext.__init__` (`inputs.py:1678`) from the selection's `version`; the saved-record
dispatcher `validate_controlled_response_saved_science` (`:2082`) from the same field. The only product caller of
`open_controlled_response_sources` is `v3_inputs.py:84`, after `validate_controlled_response_v3_selection` (`:83`),
whose schema fixes `version` to `controlled_response_source_selection_v3`.
Product importers of the family: 114 files, 15 names, all in `storage` (7), `render` (5), `prompt` (2),
`return_contract` (1). Test importers in my area: one file, `tests/test_intervention_received_score_operands.py` (v3).

## Step 2: what was done

The shared root was the a105 original with its schema builders split into contract modules: 320 of 333 top-level
statements were AST-identical to the a105 original, and the other 13 differed only in import sources (plus cr1's
schema effect 5, already present). So every changed statement was taken from the collapsed a105 module and every
unchanged statement kept its shared-root text (`collapse_root.py`, run `013`).

| shared-root module | result | from a105 module |
|---|---|---|
| `…v2_contracts.py` (418 lines), `…v2_inputs.py` (366) | deleted | (deleted there) |
| `…selection_contracts.py` | the one selection core: axis scale and terminal edge are part of it, version const `…selection_v3`; `controlled_response_arguments_schema` is now `_selection_core_schema` | `inputs` |
| `…v3_contracts.py` | holds `arr`, `enum`, `embed`, `_graph_schema`, `_sheet_schema`, `_extraction_core_schema` (was the v2 `_extraction_schema`) and `_schemas` | `v3_inputs` |
| `…v3_inputs.py` | 9 functions moved in from the v2 module (`_graph_request`, `_read_graph`, `_graph_reading`, `_saved_roster`, `_saved_images`, `_check_witness`, `_validate_text`, `_validate_measurement`, `_validate_graph`); 3 statements replaced | `v3_inputs` |
| `…inputs.py` (2848 → 1924 lines) | 15 names removed, 27 statements replaced, 57 kept. Removed: `VERSION`, `SELECTION_VERSION`, `validate_controlled_response_selection`, `_arm`, `_covariance`, `_cross_control_alias_conflict`, `_resolve_control_alias`, `read_controlled_response_inputs`, `_ROOT_FIELDS`, `_validate_v1_saved_science`, `validate_controlled_response_extraction`, `_selected_arm_field`, `_SavedSourceContext`, `_validate_v2_saved_science`, and the dispatcher (the v3 function now has the name `validate_controlled_response_saved_science`) | `inputs` |
| `…calculations.py` (666 → 390) | 10 names removed: `INPUT_VERSION`, `VERSION`, `CELL_FIELDS`, `REASONS`, `_validate_arm`, `_validate_covariance`, `_validate`, `validate_controlled_response_inputs`, `_effect_reasons`, `populate_controlled_response` | `calculations` |
| `…owner_calculations.py` | module alias `_old` is `arithmetic` (124 sites) | `owner_calculations` |
| `…owner_contracts.py` | module alias `_old` is `declarations` (7 sites) | `owner_calculations` |
| `storage`, `local_calculations`, `v3_population`, `figure_inputs`, `render`, `prompt`, `declarations`, `return_contract` | not touched | |

Imports that the removal left unused were removed (`deepcopy`, `combinations` in `calculations`; `selection`,
`_SELECTION_SCHEMA`, `lru_cache` in the two input modules). A selection that is not v3 is refused by the existing
error `controlled_selection_schema_invalid`. Live record `version` strings are unchanged. No fallback, default,
try/except or presence check was added.

Site counts over the family (`counts.py`, run `018`):

| | files | lines | profile-branch lines | `controlled_response_v2` | v1/v2-named identifiers | `v2` module alias uses | `_old` / `old_facade` aliases | v1/v2 form version strings |
|---|---|---|---|---|---|---|---|---|
| before | 17 | 7684 | 40 | 25 | 28 | 16 | 134 | 13 |
| now | 15 | 5963 | 0 | 0 | 0 | 0 | 0 | 0 |

Remaining `_v1` / `_v2` strings are current record versions of the live form, unchanged:
`controlled_response_owner_inputs_v2`, `…owner_sheet_v2`, `…covariance_source_v1`, `…rate_figure_{selection,extraction}_v1`,
`…rate_pixels_v1`, `…bar_runs_v1`, `…local_{inputs,sheet}_v1`, `…native_implementation_v1`.

## Schema digests (requirement 3)

`measure.py` on the shared root before (run `006`), now (`015`) and a105 (`007`); `compare.py` (run `016`).
"Equal" means the JSON text is identical with key order preserved, which is stricter than the sorted digest.

| schema root | shared root now = a105 | changed by this work |
|---|---|---|
| cells (`NATIVE_RETURN_SCHEMA_V3_007`) | equal, `7afe38bd…f0e0` | yes (was `795c3647…6bcc`) |
| arguments / population (`SELECTION_SCHEMA_V3_007`) | equal, `6040ddb18241cf0a…` | no |
| extraction (`EXTRACTION_SCHEMA_V3_007`) | equal, `b0ed884117b720df…` | yes (was `078092c2dd1b599d…`) |
| owner sheet (`_sheet_schema`) | equal, `1fe7e4b9040f565d…` | no |
| owner arguments | equal, `a652dad6a666a1d0…` | no |
| local inputs, local sheet, population, native fact, graph | equal (5 of 5) | yes |
| `implementation_descriptor()` | equal; `native_schema_sha256` `39a60286…4874` | yes (was `223827c1…e87c`); nothing in code, tests, examples or tools pins either value |

What changed in the cells schema is exactly cr1's effects 1 to 4: `$defs` 294 → 250; 46 removed (42 `S_*`, 2
`Selection`, 2 `MeasurementExtractionV2`), 2 added (`G_GraphMeasurementExtraction`, `Parsed_G_GraphMeasurementExtraction`);
8 defs differ, by the `reader_contract_version` const (2), the diagnostic code enum (2), and the two references to
the renamed def (4). Effect 5 (`local_pair_extractions` required) was already in the shared root.

## Same code as a105 (requirement 4)

`verify_same.py` (run `017`): 305 top-level statements of the 15 shared-root files compared with a105/library, with
import-from statements reduced to module base name and imported names. **301 identical.** Every a105 statement has a
shared-root counterpart. The four that differ:
- `owner_contracts._ROLES` and `owner_contracts._schema`: the module alias is `declarations` here and `arithmetic`
  in a105, because here the constants live in `…declarations.py`, which holds no arithmetic.
- `local_calculations.controlled_response_local_arguments_schema` and `._result_schema`: import `_schemas` from
  `…v3_contracts` here and from `…v3_inputs` in a105 (not edited).

Layout that stays different on purpose: the contract modules (`selection_contracts`, `owner_contracts`,
`v3_contracts`, `declarations`, `return_contract`) exist only here; 21 home files (`numerical_report_fields.py:230`)
import the cells schema through `return_contract` without loading the readers. Text layout is mixed: kept
statements keep the shared-root wrapping, replaced ones carry a105's single-line layout.

## Tests and fixtures (requirement 5)

- No file under `R/tests` or `tests/` imported a v1/v2 entry point or stored a v1/v2-form selection (grep over all
  file types outside the arms: no `…source_selection_v[12]`, `…source_extraction_v[12]`, `controlled_response_v2`).
- Handoff `cr1 → ptests` applied: the `args.update(...)` in `controlled_response_rows`
  (`tests/test_intervention_received_score_operands.py`, 2 lines) is deleted. The a106 fixture it reads already
  stores `version = controlled_response_source_selection_v3` and the five empty collections (checked).
- No scientific expectation of any test was edited.

## Untested live code (requirement 6; nothing ported)

Method: the three test files cr1 deleted were read from `729169ec5`. The 14 remaining a105 family test files were run
once each with a line recorder (`sys.monitoring`, plugin `<scratchpad>/cr2/plug/cr2lines.py`; runs `035`-`048`,
228 passed, 258.2 s). A "site" is a string code passed to `_fail`, `_diag`, `_diagnostic`, an `…Error`
constructor or `partial` (failure or diagnostic), or to `append`/`add`/`extend`/`update` (reason or qualification).
The same functions exist, AST-identical, in the shared root.

- 255 live functions; 132 have lines no remaining test executes; 3 are never entered (`calculations._alias_reasons`,
  `storage.controlled_response_population_schema`, `LiteratureControlledResponseRepository.populate`).
- 502 sites; 137 executed by a remaining test.
- 48 unexecuted sites in 31 functions carry a code that a deleted test named and could reach (29 distinct codes).

By the three themes cr1 named (lines executed / statement lines; sites executed / sites):

| theme | functions | lines | sites | least covered live functions (sites) |
|---|---|---|---|---|
| graph reading and saved graph checks | 36 | 536/685 | 22/111 | `v3_inputs._validate_graph` 1/37, `figure_inputs._validate` 6/19, `figure_inputs._strict_decode` 0/7, `figure_inputs._pixels` 2/7, `figure_inputs._count_recipe` 1/6, `figure_inputs._literal` 0/4 |
| covariance source and projection | 12 | 268/317 | 11/52 | `inputs._JSON.parse` 1/11, `inputs._project_owner_covariance` 2/11, `inputs._source_model_shape` 0/7, `inputs._effective_model` 2/8, `inputs.bind_controlled_response_covariance_scope` 1/5 |
| saved-record checks (tampering) | 15 | 313/400 | 8/69 | `inputs._saved_uncertainty` 0/13, `inputs.validate_controlled_response_saved_science` 3/12, `inputs._saved_unit` 0/8, `inputs._saved_number` 0/6, `inputs._saved_witness` 1/6, `v3_inputs._saved_roster` 0/5, `v3_inputs._validate_text` 0/5 |

Codes a deleted test asserted whose live emitting line no remaining test executes (deleted file in brackets):

| live function | codes |
|---|---|
| `calculations._cell` [calculations] | `numeric_range_failure`, `uninformative_bounds` |
| `calculations._alias_reasons`, `._common_alias_reasons` [calculations] | `conflicting_source_literal` |
| `calculations._pair_reasons` [calculations] | `different_condition_correspondence`, `incompatible_unit_dimension` |
| `calculations._qualifications` [calculations] | `estimated_covariance`, `unknown_control_reuse` |
| `calculations._enum`, `._identity` [calculations] | `unsupported_value`, `nonempty_identity_required` |
| `inputs._JSON.parse` [inputs, v2_inputs] | `source_json_duplicate_key`, `source_json_nonfinite` |
| `inputs._source_model_shape` [inputs, v2_inputs] | `source_covariance_shape_invalid` |
| `inputs._check_document_nominations` [inputs, v2_inputs] | `source_label_token_binding_mismatch`, `source_variable_index_out_of_bounds` |
| `inputs._project_owner_covariance` [inputs] | `covariance_projection_precision_invalid` |
| `inputs._effective_model` [inputs, v2_inputs] | `source_model_projection_rounding` |
| `inputs._scope_binding` [v2_inputs] | `owner_witness_not_in_role` |
| `inputs._uncertainty`, `._saved_uncertainty` [inputs, v2_inputs] | `source_uncertainty_unit_conflicting` |
| `inputs._assemble_uncertainty`, `._display` [inputs, v2_inputs] | `source_numeric_range` |
| `inputs._saved_unit` [inputs] | `saved_unavailable_definition_mismatch` |
| `inputs._Context.__init__`, `v3_inputs._saved_roster` [v2_inputs] | `artifact_content_conflict` |
| `inputs._Context.source`, `._SavedV3SourceContext.source`, `v3_inputs._read_graph` [v2_inputs] | `unselected_source_read` |
| `inputs._Context.witness` [inputs] | `source_dependency_unavailable` |
| `inputs.SourceContext._active`, `._SavedV3SourceContext._active` [v2_inputs] | `source_context_closed` |
| `inputs._measurement_entry` [v2_inputs] | `source_stage_context_mismatch` |
| `v3_inputs._validate_graph` [v2_inputs] | `saved_graph_status_mismatch`, `conflicting` |
| `figure_inputs.read_controlled_response_rate_figure` [v2_inputs] | `conflicting` |
| `owner_calculations._reading_dependencies` [v2_inputs] | `canceled_unit_unknown` |
| `owner_calculations.populate_controlled_response_owner` [v2_inputs] | `unresolved_censoring_model` |

Limits of the method: attribution is by code string, so a deleted test that only expected "some error" is not
attributed (the theme table does not depend on that); a line counts as executed when any part of it ran.

## Left for decision

1. **The shared-root copy has no test of its own.** `R/tests` has no file of this family; in `tests/` only
   `test_intervention_received_score_operands.py` builds the shared-root repository, and its 8 tests that do so fail
   before and after at `R/literature_ratio_source_storage.py:151` (`literature_reading_outside_assigned_source`,
   recorded in rec5 as not established). What stands for the shared root is identity with a105 (301/305
   statements), the equal schemas and the 34 constructed cases.
2. Which of the untested sites above get live-form tests, and against which copy.
3. `validate_controlled_response_local_sheet` and `validate_controlled_response_v3_population` are live-form
   validators with no caller in the shared root (a105 calls them from tests only). Kept; not backward-facing.
4. Eight diagnostic codes have no raising site here either (enum only, 1 occurrence each), as cr1 reported for the arms.
5. Unused module-level imports that predate this work are left: 13 names in `…inputs.py` (`ContractError`, `REF`,
   `ROLES`, `TEXT`, `OFFSET`, `WITNESS_FIELDS`, `array`, `defs`, `enum`, `interpretation`, `nullable`, `obj`,
   `defined_rate_unit_schema`), `_obj` and `_schema` in `…owner_calculations.py`.
6. 15 dated reports under `docs/` still name the two deleted modules (`docs/purge_20261115/`,
   `docs/test_failure_triage_20261114/`, `docs/test_audit_verdicts_20261114.tsv`). `docs/` was not to be touched.

## Gate

1. Site counts: table above.
2. Import check over all shared-root product modules outside the arms (6,271) and the top-level package (272):
   `{}` in every run (`claude_cr2_019`-`025`, `027`). `gene_annotation_episode.__main__` is left out: it calls the
   command line at import (`raise SystemExit(main())`) and exits on the checker's own arguments (run `026`);
   `gene_annotation_episode.cli` is in the list and imports.
3. Tests, one file per launcher run, isolated form. By the rule in the brief one file qualifies (mentions the family
   or imports an edited module); five files that reach the family through `communication.py` and the storage
   repositories were added. Per test: same ids, same state, same failure message as before (`junitcmp.py`, run `034`).
   No test that passed before fails.

| file | before | now | run |
|---|---|---|---|
| `tests/test_intervention_received_score_operands.py` | 24 passed, 8 failed, 4.16 s (`claude_rec5_final/276`) | 24 passed, 8 failed, 4.31 s | `claude_cr2_028` |
| `R/tests/test_root_typed_communication_support.py` | 12 passed, 0.12 s (`claude_rec5_root1/078`) | 12 passed, 0.12 s | `029` |
| `R/tests/test_root_contract_snapshots.py` | 4 passed, 0.11 s (`…/055`) | 4 passed, 0.11 s | `030` |
| `R/tests/test_root_episode_boundary.py` | 1 passed, 4 failed, 2.97 s (`…/059`) | 1 passed, 4 failed, 2.96 s | `031` |
| `R/tests/test_root_saved_report_redelivery.py` | 2 passed, 8 failed, 0.25 s (`…/071`) | 2 passed, 8 failed, 0.24 s | `032` |
| `tests/test_literature_cell_possession.py` | 9 passed, 17 failed, 5.45 s (`claude_rec5_final/290`) | 9 passed, 17 failed, 5.71 s | `033` |

Expected and measured (written to `<scratchpad>/cr2/expected.txt` before each launch):

| step | expected | measured |
|---|---|---|
| import check, 8 runs | 8 to 16 minutes | 29 s. The estimate had no measured basis and was about 20 times too high |
| the one qualifying test file | 4.2 s | 4.31 s |
| five added files | about 11.5 s | 9.14 s (13.45 s for all six; 13.07 s before) |
| recorder runs of the 14 a105 files | 250 to 258 s | 258.2 s |

## Size (my 10 files inside `9fc7d3e54`)

Product: 9 files in `R/library` (7 modified, 2 deleted), +1184 −2905 lines. Tests: 1 file, −2 lines. No fixture.
The gate above ran on exactly this content: the files have not changed since run `015`.
53 launcher runs (`runs/claude_cr2_001`-`053`); run `002` was a reachability scan of mine that walked `runs/`, which I
stopped and repeated with the directories pruned (`003`).

## Handoffs

- Applied: `cr1 → prootlib,proot` (this work) and `cr1 → ptests` (`tests/test_intervention_received_score_operands.py`).
- Written: none. The removed names had no user outside the family (`uses.py`), and no copy is left with the old schema.
