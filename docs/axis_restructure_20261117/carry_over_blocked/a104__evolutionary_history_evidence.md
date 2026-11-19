# a104/evolutionary_history_evidence: blocked, unplaced and misfit items

Episode folder: `gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/`. Every item below is
also returned in the structured result. Nothing was worked around: each call stays as written or raises where the old code
used the missing piece.

## BLOCKED-ON-STORE-ACCESS

| function | pattern |
|---|---|
| `episode_support/tools/evolutionary_history_evidence/tools.py::ToolRegistry` (called by `task.py` `selected_tool`) | library not carried: `ToolRegistry(store)` runs `store.db.execute('CREATE TABLE tool_operations ...')`, keeps the `tool_operations` ledger, uses `store.path / 'cache' / 'minimap2'` and `store.db` elsewhere. Old call `ToolRegistry(store, **kw).execute_async(name, args, scope=, operation_key=, permitted_record_refs=)` stays as `ToolRegistry(ctx.store, **ctx.settings['tool_registry']).execute_async(...)` |
| `episode_support/grading/evolutionary_history_evidence/credit.py::A104EvolutionaryCredit.read_details` (called by `credit.py` `credit_view`, hence `credit` and `internal_summary`) | library not carried: `with store.read_snapshot()` (not offered by `records`), `known_record_refs=` receipts. Old call `projector(store, scope, known_record_refs=..., assignment=...)` -> `projector(records, scope, known_record_refs=list(records.refs()), assignment={...})`, as written |
| `episode_support/grading/evolutionary_history_evidence/credit.py::A104PanelIdentityCredit.read_details` and `A104AlignmentSuitabilityCredit.read_details` | library not carried: raw SQL `store.db.execute("SELECT 1 FROM sqlite_master ...")` and `SELECT source_ref FROM a104_native_requests` / `a104_native_results`, `store.read_snapshot()`; intended: a declared work table read through `records.table(...)` |
| `episode_support/grading/evolutionary_history_evidence/credit.py::A104RobustnessCredit.read_details` | library not carried: `store.read_snapshot()`, `known_record_refs` receipts |

Consequence: a run of this head cannot get past the first `internal_summary` / initial `credit` until the A104 credit
projectors are carried. No scripted stand-in was written.

## Unplaced old functions (no module in `episode_support/`; the old modules lived in the old shared root and were not read)

| old name | what happens |
|---|---|
| `a104_investigation.TASKS` | no module in the library; `credit.py credit_projector` no longer raises: any name other than the three selects `A104EvolutionaryCredit`, the old membership check of the name in TASKS and of `allowed_tasks` is a commission check and is not carried |
| `a104_investigation.RECORD_SOURCE`, `received_records`, `fact_sources` | `RECORD_SOURCE` is taken to be `committed_record_refs` (from the old `required_return_sources`); `received_records` is held records; the other sources of `fact_sources()` are not declared |
| `evolutionary_history_evidence_reports.build_process_result`, `merge_process_results`, `project_process_result`, `report_sources`, `validate_process_result` | selecting `evolutionary_history_evidence_results` raises `unplaced:evolutionary_history_evidence_reports.build_process_result`; the other library report sources of `report_sources(library, tool_library)` are not declared in `RETURN_FORM` |
| `alignment_site_returns.alignment_site_fact_sources`, `requested_site_projections`, `project_site_action_return`, `validate_frozen_site_return` (and the services `alignment_site_own_action_results`, `alignment_site_frozen_facts`) | the alignment-site fact sources are not declared in `RETURN_FORM` (their names are unknown), so no parent can select them |
| `evolutionary_result_facts.molecular_fact_sources`, `merge_molecular_facts`, `requested_molecular_fact_sources`, `requested_molecular_fact_fields`, `validate_frozen_molecular_return` (and the services `molecular_own_facts`, `molecular_received_facts`, `molecular_frozen_facts`) | `protein_conservation_outcomes` and `protein_phylogeny_outcomes` are declared (names from `forms/phylogeny`); selecting one raises `unplaced:evolutionary_result_facts.molecular_own_facts` |
| `received_evidence.received_report_facts` (role annotation) | not carried: it served the root; needs `merge_molecular_facts` |
| `a104_scientific_report_validation.validate_axis_report` | not carried: `final_to_parent.validate_report` checks the finding form and that the returned records were produced here |
| `scientific_tool_retrieval.configuration` (the `process.tools` common tool) | `process.tools` is not offered |
| `execution_planning.catalog`, `execution_planning.read` (the `process.execution` common tool) | `process.execution` is not offered |
| `composition_information.CONTRACT_INFORMATION_PROFILE` and contract-information freezing | machinery of the decision exchange; not carried |
| `scientific_support_metadata.support_observation_kinds`, `ScientificServices.scientific_support_routes` and the second goal text | the older support-metadata entry path: such an entry has no credit projector, so `yield_estimator.py` raises `scientific_task_credit_not_declared` as the old `continuation_task` did |
| `providers.render_evolutionary_history_evidence_prompt`, `is_published_scientific_context`, `has_evolutionary_receiver_context` | `decide` sends a structured JSON context instead of rendered text (README 5 item 16) |
| services `episode.annotation_score`, `episode.monitoring_information`, `episode.estimate_wait`, `shared.request_information`, `shared.publish_information`, `shared.resolve_information_need`, `shared.read_information`, `shared.list_information`, `retain_shared_grading_results` | common tools of the old shared services; not offered |

## Contract misfits

- new field: a104/evolutionary_history_evidence scope (the old code took the Store scope from the request of the commission).
- new field: a104/evolutionary_history_evidence record_refs (the records the commission names beside the evidence: the proposed annotation, the subjects of the scope). `evidence_refs` is a `record_refs` field where the old schema had reference text.
- new field: a104/evolutionary_history_evidence message `purpose` and `initial_report` are read from the commissioner's message (the old `_invocation` required them); the root's `msg_to_child` must send both.
- Settings the episode reads (new, no old equivalent in one place): `yield_bindings` (the old `yield_bindings`), `process_library_directory`, `tool_library_directory`, `tool_registry`, and optional `tool_knowledge_directory`, `launch_instruction_directory`.
- Completion target: the old `CompletionYieldController` had no target. The target is the `maximum_credit` of the credit definition (`panel_identity` and `alignment_suitability`: 1), which `parent_input` selects through `a104_task`; the contract says the target comes from `parent_input` and the A104 assignment carries no target field. Those two credits are `len(details)` with at most one detail, so they cannot pass the target.
- `RETURN_FORM` declares `protein_conservation_outcomes` and `protein_phylogeny_outcomes` as `list` fields; the source records they name (`source_ref`) cannot travel in custody because they are not `record_refs` fields (the fields mix values and references). `read_from_child` collects `molecular_source_refs` but the parent cannot return them in custody.
- `decide` has no Store: the commit schema (`reasoning_schema`), the working state and the credit view reach it through `internal_summary` (`view.records`), and the old availability check of the selected tools against the registry catalog (`_information_catalog`, `tool_catalog(scope)`) cannot be made before the model chooses; it happens where the registry runs the tool.
- `view.path` depth: the old rule "a child directly under the root must return the process results" (`len(parent.path) == 1`) is `path_depth == 1` in `msg_to_child`, which is true only when this head is the entry of the run; with the real root above it the rule never applies. Whether the root's commissions of this head should select `evolutionary_history_evidence_results` is the root's `msg_to_child`.
- `process.revise` makes `parent_invocation_ref` from `scientific_invocation_ref(ctx.run_id, ((ctx.binding_path, ctx.episode_id),))`: `UnitContext` has no structural path. The old validation of that origin against the parent's journal is not carried (a wrong commission fails).
- `task.py` offers `episode_child` only for this slot and `hpc` (the old `allowed_child_roles`); `launch`, `monitor`, `results`, `literature` are declared slots with old assemblers in `msg_to_child.py` but nothing offers them (the old code did the same).
- The running `report_update` (an interpretation sent with every decision) is a `report` action now (a tool unit); `finding` is the typed finding of this episode (written, interpretation, qualification, counts, credit view). A104 has no typed `investigation_finding` requirement (that is A105/A108).
- No real runner test (link, RunJournal, Store, controller) was written: it needs `ToolRegistry` and the A104 credit projectors in the final Store form; a scripted stand-in would be a fake.
