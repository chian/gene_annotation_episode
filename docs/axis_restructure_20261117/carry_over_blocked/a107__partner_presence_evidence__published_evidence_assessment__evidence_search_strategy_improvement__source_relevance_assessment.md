# a107 source_relevance_assessment: blocked, unplaced and misfit items (19 November 2026)

Old tests of this episode: none (no tests/ at 97308b94c, none in the working tree); the retired-tests file holds only its header.
Test run: `runs/cov_a107_07_u163_1`, 9 passed.

## blocked_on_store_access

| function | pattern |
|---|---|
| `episode_support/findings/partner_presence_evidence/investigation_progress.py::project_finding_progress` (credit.py) | library not carried: `store._require(ref, {'assessment'})` and `store.db.execute('SELECT record_ref FROM current_revisions ...')` -> `records.require(ref, {'assessment'})` and `records.is_current(ref)` |
| `episode_support/tools/partner_presence_evidence/tools.py::ToolRegistry` (task.py run_registry; access and acquisition tools) | library not carried: raw `Store` (`store.db`, `tool_operations` ledger, `store.path` temp dirs, `store._require`) -> `ctx.store` operations of store-access.md; temporary directories and streamed downloads are "No replacement yet" |
| `episode_support/literature/inputs/partner_presence_evidence/literature_assay_inputs.py::materialize_text_witness_inputs` (task.py) | called with a `read_source` over `ctx.store.get` / `get_artifact`; not verified against the library's own Store use |

## unplaced_old_functions

| old | reason |
|---|---|
| `contracts._population_catalog` (via `library.partner_source_contracts.population_catalog_entries`) | no placement; task.py `population_catalog` raises `NotImplementedError('partner_source_contracts_not_placed:population_catalog_entries')`, so `decide` raises until it is placed |
| `source_operations.execute` branch for `literature.partner.populate` / `literature.partner.source.populate` (`populate_partner_sheet(LiteraturePartnerRepository(store, run_id), ...)`) | routes and repository not placed, repository written against the raw Store; task.py `populate` raises `NotImplementedError('partner_source_contracts_not_placed:populate_partner_sheet')` |
| `numerical_report_facts._rate_facts` / `_rate_fact_sources`, `source_repositories._population_routes` (`partner_source_contracts.fact_sources`, `population_routes`, `literature_sheet_updates.current_sheet_refs`) | not placed; internal_summary `own_cells` raises `NotImplementedError('partner_source_contracts_not_placed:fact_cells_over_held_sheets')` when this episode holds a sheet of its own |
| `internal_summary._owned_population_task_sources`, `_population_task_context` (`partner_source_task_selection`, `sqlite_master`, `runtime_actions` through `store.db`) | the helper module has no placement and the reads are old-runner tables; the model context keys `literature_owned_population_sources` and `literature_selected_population_attempt` are not carried |
| `component_axis_source_origin` (`library.literature_source_origin`) and `component_axis_source_access` decision context | `literature_source_origin` has no placement; `source_access_context(workflow, ...)` is old-runner wiring; both context keys are not carried |
| `task_reading_prompt` fixed paragraphs (`lead`, `SOURCE_AVAILABILITY`, `SOURCE_SCOPE`, `COMPONENT_READING_TASK` of `library.literature_source_presentation`) | module not placed; prompt keeps the layout and sections without them |
| `initial_information` (`execution_initial_information.presentation.resource_information`, `received_api_information`) | old-runner catalog readers; no placement |
| `task_instructions` conditional texts for tool knowledge and launch instructions (`workflow.knowledge.instructions`, `workflow.launch_instructions.instructions`) | added only when those inputs were configured; this episode has no setting naming their directories, so they are not added (library `ToolKnowledge` / `LaunchInstructions` exist) |
| `received_reports.received_form_references` (`repository().receive_cells`) | a write on the child-return path (README section 5 item 4); the child holds its sheets and returns `sheet_refs`; read_from_child writes nothing |

## contract_misfits

- new field: source_relevance_assessment scope, finding_unit, received_record_refs, literature_partner_components (assignment form; the partner fields of the old schema come from the unplaced `partner_source_contracts`, so their real names are unknown; `literature_partner_components` is the name the child declares).
- new field: source_evidence_examination (the child) declares `scope`, `finding_unit`, `received_record_refs` and `literature_partner_components`; msg_to_child fills each from this episode's own summary (the page fields come from the model's selection).
- The old assignment declared `search_result_refs` but internal_summary read `assignment.get('source_refs')` (old bug: the custody list was empty and `page` never present). The carried summary builds the custody from `search_result_refs`; no page confinement applies to this episode's tools (the assignment never named a page).
- msg_to_child passes every held record in `received_record_refs` (a pass carries only the records named, T5); the page's own `question_context_refs` / `prior_delivery_refs` are record_refs in the child's form too and must be held (action rejects an unheld page selection as an invalid model answer).
- completion credit: not applicable (accumulation controller); credit is the finding progress and is not bounded.
- Typed finding: A107 episode (the A105/A108 grader-sheet rule does not apply). The finding form is the child's own form (source claim, source subject, qualification, target correspondence, source refs).
- Services declared (`tool_catalog`, `public_clients`) are the child's; the run must supply factories and settings with `cost`, `parameters`, `tool_registry`.
- tests: the child is not imported by the tests (rule), so the child's own form admitting this episode's commission is not tested here; the check belongs to a runner test with both episodes linked.
- git: the repository's `.git` is not at `/home/chia/repos/gene_annotation_episode` (symlink to `/tmp/ramrepo`); old files were read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>`.
