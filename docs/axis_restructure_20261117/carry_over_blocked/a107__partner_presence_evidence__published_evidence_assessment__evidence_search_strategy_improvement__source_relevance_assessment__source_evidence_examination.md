# a107 source_evidence_examination: blocked, unplaced and misfit items (19 November 2026)

Old tests of this episode: none (the folder had no tests/ at 97308b94c and none in the working tree); the retired-tests file holds only its header.

## blocked_on_store_access

| function | pattern |
|---|---|
| `episode_support/findings/partner_presence_evidence/investigation_progress.py::project_finding_progress` (called by credit.py) | library not carried: `store._require(ref, {'assessment'})` and `store.db.execute('SELECT record_ref FROM current_revisions ...')` -> `records.get(ref)` / `records.require(ref, {'assessment'})` and `records.is_current(ref)` |
| `episode_support/tools/partner_presence_evidence/tools.py::ToolRegistry` (called by task.py run_registry) | library not carried: raw `Store` (`store.db`, `tool_operations` ledger, `store.path`) -> `ctx.store` operations of store-access.md |
| `episode_support/literature/inputs/partner_presence_evidence/literature_assay_inputs.py::materialize_text_witness_inputs` | called with a `read_source` over `ctx.store.get` / `get_artifact`; not verified against the library's own Store use |

## unplaced_old_functions

| old | reason |
|---|---|
| `contracts._population_catalog` (via `library.partner_source_contracts.population_catalog_entries`) | `partner_source_contracts` has no placement; task.py `population_catalog` raises `NotImplementedError('partner_source_contracts_not_placed:population_catalog_entries')`, so `decide` raises while it is unplaced |
| `source_operations.execute` branch for `literature.partner.populate` and `literature.partner.source.populate` (`populate_partner_sheet(LiteraturePartnerRepository(store, run_id), ...)`) | partner population routes and repository not placed and written against the raw Store; task.py `populate` raises `NotImplementedError('partner_source_contracts_not_placed:populate_partner_sheet')` |
| `numerical_report_facts._rate_facts` / `_rate_fact_sources` (`partner_source_contracts.fact_sources`, `fact_cells`, `literature_sheet_updates.current_sheet_refs`) | not placed; internal_summary `own_cells` raises `NotImplementedError('partner_source_contracts_not_placed:fact_cells_over_held_sheets')` when this episode holds a sheet of its own |
| `task_reading_prompt` fixed paragraphs (`lead`, `SOURCE_AVAILABILITY`, `SOURCE_SCOPE`, `COMPONENT_READING_TASK` of `library.literature_source_presentation`) | module not placed; the prompt keeps the layout and the sections without those paragraphs |
| `initial_information` (`execution_initial_information.presentation.resource_information`, `received_api_information`) | old-runner catalog readers; no placement |

## contract_misfits

- new field: source_evidence_examination scope, finding_unit, received_record_refs, literature_partner_components (assignment form; the old schema's partner fields come from the unplaced `partner_source_contracts`, so their real names are unknown).
- new field: passage_evidence_extraction, source_coverage_improvement and table_evidence_extraction name their partner components differently (`partner_components`, `literature_partner_components`, none); the child folders declare `held_refs` (passage) or `received_record_refs` (coverage, table); msg_to_child writes each in the child's own names.
- source_coverage_improvement declares no `sheet_refs` selectable field, so the sheets behind the cells it returns are not passed to this episode in custody; this episode lists their references among its known sheets but returns in `sheet_refs` only the ones it holds.
- completion credit: not applicable (accumulation controller); credit is the finding progress and is not bounded.
- The old parent form was written by the grandparent; here the return form is this episode's own (README rule 5): `literature_partner_cells` and `sheet_refs` are selectable, credit and finding required.
- Typed finding: this is an A107 episode; the A105/A108 grader-sheet rule does not apply. The finding form is the sibling children's own (source claim, source subject, qualification, target correspondence, source refs).
- Services declared (`tool_catalog`, `public_clients`) are the ones the passage child declares; the run must supply factories for them and settings with `cost`, `parameters` and `tool_registry`.
- git: the repository's `.git` is not in `/home/chia/repos/gene_annotation_episode`; old files were read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>`.

## Not repaired

Limits of the system, contract or guide, or library not yet carried; not worked around:

- credit.py: library episode_support/findings/partner_presence_evidence/investigation_progress.py::project_finding_progress uses the raw Store (read_snapshot, validate_scope, _require, db.execute). Pattern: "library not carried".
- task.py run_registry: ToolRegistry(ctx.store, ...) from episode_support/tools/partner_presence_evidence/tools.py is written against the raw Store. Pattern: "library not carried".
- task.py materialize_text_witness_inputs: the library's own Store use is not verified. Pattern: "library not carried".
- task.py population_catalog, populate (literature_partner_populate, literature_partner_source_populate), messages/internal_summary.py own_cells, task.py render_prompt fixed paragraphs and initial_information: library.partner_source_contracts and literature_source_presentation have no placement (unplaced_old_functions).
- messages/read_from_parent.py new fields scope, finding_unit, received_record_refs, literature_partner_components: contract_misfits ("new field").
- source_coverage_improvement's RETURN_FORM declares only literature_partner_cells as selectable, so the sheets behind returned cells are not passed in custody (child's declaration; contract limit).
