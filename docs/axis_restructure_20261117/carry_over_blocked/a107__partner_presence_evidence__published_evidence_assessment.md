# a107 published_evidence_assessment: blocked, unplaced and misfit items (19 November 2026)

Old tests of this episode: `tests/test_literature_link.py` (hook-era, built the seven literature bindings through the old head cycle); deleted and recorded in `retired_tests/a107__partner_presence_evidence__published_evidence_assessment.tsv`.
Test run: `runs/cov_a107_06_u161_1`, 9 passed (`tests/test_binding.py`). Private copy of the shape of the carried child `evidence_search_strategy_improvement` (the old files are text-identical copies apart from role, assignment and child, as the intent record says). Deleted first: `literature_binding.py`, `literature_cycle.py`, `episode.py` (hook-era subclass), `tests/test_literature_link.py`. Nothing outside this folder imported them (a108/a110 hold their own copies).

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
| `source_operations.execute` branch for `literature.partner.populate` / `.source.populate` | routes and repository not placed (raw Store); task.py `populate` raises `NotImplementedError('partner_source_contracts_not_placed:populate_partner_sheet')` |
| `numerical_report_facts._rate_facts` / `_rate_fact_sources`, `source_repositories._population_routes`, `source_repositories.literature_partner_repository` | not placed; internal_summary `own_cells` raises `NotImplementedError('partner_source_contracts_not_placed:fact_cells_over_held_sheets')` when this episode holds a sheet of its own |
| `internal_summary._owned_population_task_sources`, `_population_task_context` | helper module has no placement; reads old-runner tables through `store.db`; context keys not carried |
| `component_axis_source_origin`, `component_axis_source_access` decision context | no placement / old-runner wiring; not carried |
| `task_reading_prompt` fixed paragraphs (`lead`, source availability, scope, component reading task, fact-contract task of `library.literature_source_presentation`) | module not placed; prompt keeps layout and sections without them |
| `initial_information`, `received_api_reports`, `received_execution_information` | old-runner catalog readers; no placement |
| `task_instructions` conditional knowledge / launch-instruction texts | added only when configured; no setting names their directories |
| `received_reports.received_form_references` (`repository().receive_cells`) | a write on the child-return path (README 5 item 4); the child holds its sheets and returns `sheet_refs` |
| `from_parent._validate_assignment` Store parts (refs in scope, `source_refs` of namespace `source`) | checks of the commission against the Store; a wrong commission fails |
| `parent_context.initial_decision_context` (reference-evidence parent mode) | belongs to the head (role annotation at path length 1); not carried here |

## contract_misfits

- new field: published_evidence_assessment scope, finding_unit, received_record_refs, literature_partner_components (assignment form; the partner fields of the old schema come from the unplaced `partner_source_contracts`, real names unknown; `literature_partner_components` is the name the child declares).
- The child `evidence_search_strategy_improvement` declares `scope`, `finding_unit`, `received_record_refs`, `literature_partner_components` too; msg_to_child fills each from this episode's own summary and the model supplies only `version`, `question_context_refs`, `prior_search_refs`.
- internal_summary reads `source_refs` as held sources (`records.get`); the parent (head) must pass them in `received_record_refs`. msg_to_child passes every held record as the child's `received_record_refs` (T5); the model's strategy selection must name held records (action rejects otherwise).
- Completion credit: not applicable (accumulation controller; the old yield_estimator returned None); credit is the finding progress, unbounded.
- Typed finding: A107 (the A105/A108 grader-sheet rule does not apply); finding form: source claim, source subject, qualification, target correspondence, source refs.
- Services declared (`tool_catalog`, `public_clients`) and settings (`cost`, `parameters`, `tool_registry`) are needed from the run.
- tests: the child is not imported (rule), so the child's own form admitting this commission is not tested here; that belongs to a runner test with both episodes linked.
- `docs/axis_restructure_20261117/GOAL.md` named in the job does not exist; `.git` is absent at `/home/chia/repos/gene_annotation_episode` (old files read from `/home/chia/repos/gene_annotation_episode_disk/.git`).

## Not repaired

- credit.py calls library project_finding_progress (episode_support/findings/partner_presence_evidence/investigation_progress.py), still on the raw Store: library not carried.
- task.py run_registry hands ctx.store to library ToolRegistry (episode_support/tools/partner_presence_evidence/tools.py), still on store.db, store._require, store.path, sqlite3: library not carried.
- population_catalog, populate and own_cells raise NotImplementedError: no placement exists for partner_source_contracts, the partner repository and fact_cells.
- Tests do not exercise decide, action, credit or internal_summary because of the items above.
