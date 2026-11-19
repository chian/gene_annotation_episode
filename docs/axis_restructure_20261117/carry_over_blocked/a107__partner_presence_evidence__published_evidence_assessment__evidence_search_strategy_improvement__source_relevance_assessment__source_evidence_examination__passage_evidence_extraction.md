# a107 / passage_evidence_extraction: blocked, unplaced and contract misfits (19 November 2026)

## BLOCKED-ON-STORE-ACCESS (library not carried; the call stays as written)

| Function | Pattern: old call -> intended call |
|---|---|
| `tools/partner_presence_evidence/tools.py::ToolRegistry` (task.py `run_registry`, every access tool) | library not carried: `ToolRegistry(store, clients=..., ...)` runs `store.db.execute('CREATE TABLE ... tool_operations')`, `store._require(...)`, `store.put` through private helpers, `tool_operations` ledger -> intended `ToolRegistry(ctx.store, ...)` over the custody operations of store-access.md (the ledger is the system's attempts journal). Called as `ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry']).execute_async(name, arguments, scope=, operation_key=ctx.operation_key, permitted_record_refs=)` |
| `findings/partner_presence_evidence/investigation_progress.py::project_finding_progress` (credit.py) | library not carried: `store.read_snapshot()` (not on `records`), `sqlite3` spool, `store._require(ref, {'assessment'})`, `store.db.execute('SELECT record_ref FROM current_revisions ...')`, `FindingValidity(store, ...)` -> intended `records.require(ref, {'assessment'})`, `records.is_current(ref)`, `records.current_assessments(scope)` |
| `literature/storage/literature_partner_storage.py::LiteraturePartnerRepository` (`fact_cells`, `received_cells`, sheet reads; internal_summary `partner_cells`) | library not carried: `LiteraturePartnerRepository(store, run_id)` with `store.db` operations/delivery tables -> intended work tables under `store.table(T)` / `records.table(T)` |
| `literature/inputs/literature_partner_sheet_population.py::populate` (task.py `populate`) | library not carried: `store.db.execute('SELECT signature,outcome FROM <operations_table> ...')`, `store.transaction()`, `_literature_sheet_updating` flag -> intended declared work table plus `ctx.store.transaction()` |

## Unplaced old functions

| Old | Reason |
|---|---|
| `a107.library.partner_source_contracts` (`population_catalog_entries`, `population_routes`, `fact_sources`, `assignment_schema_fields`) | no module placed (`axis_shared_modules.tsv`: none). `task.py population_catalog` and the population tools raise `NotImplementedError('partner_source_contracts_not_placed:...')`; `partner_cells` raises when sheets are held; the exact names of the partner assignment fields and fact sources are not known |
| `a107.library.literature_source_presentation` (`lead`, `SOURCE_AVAILABILITY`, `SOURCE_SCOPE`, `COMPONENT_READING_TASK`, `FACT_CONTRACT_TASK`, `_section`, `_selected_family`, `_selected_tools`, `VERSION`) | no module placed; `task.py render_prompt` keeps the section layout and the STEERING sentence but not the fixed paragraphs |
| `a107.library.scientific_decision_presentation`, `a107.decision_context` | no module placed; the old state-frame replay is deleted machinery, the text-instruction helper is not needed |
| `a107.library.partner_source_task_selection` (`population_task_metadata_specs`), `a107.library.literature_source_origin` (`component_axis_source_origin`) | no module placed: `_owned_population_task_sources`, `_population_task_context`, `component_axis_source_origin` are not carried |
| `a107.component_axis_source_access.decision_context` / `rejection_detail` | only `source_received_inputs` is placed in `acquisition/sequence_and_context_sources/component_axis_source_access.py`; `component_axis_source_access` in the summary and the rejection detail of the old `_tool_arguments` are not carried (the detail is `{'source_ref', 'refused'}`) |
| `a107.library.execution_initial_information.presentation` (`resource_information`, `received_api_information`), `catalog.readers`, `received_api_reports`, `received_execution_information` | no module placed; `initial_information` is not carried |
| `a107.composition_information` (`CONTRACT_INFORMATION_PROFILE`, `CONTRACT_ARGUMENT_TRANSPORT`) | no module placed; contract-information freezing is deleted exchange machinery; the `argument_transport` of population operations is not carried |
| old check `source_offset_out_of_bounds` (window offset beyond the page artifact size) | needs a Store read of the artifact; `read_from_parent` has no `records` |
| `a107.literature_contract_error.ExperimentalContractError` caught around population | the placed `literature/forms/literature_contract_error.py` was not wired because population raises first |

## Contract misfits

- new field: passage_evidence_extraction held_refs (record_refs: source, its artifact, the sources it descends from for `within_source`, question and prior delivery records, the scope's subjects); the old binding context supplied them.
- new field: passage_evidence_extraction scope (record) and finding_unit (number): the old `scientific_credit` service took the scope from the binding context; `project_finding_progress` needs both.
- new field: passage_evidence_extraction return fields `sheet_refs` (selectable) and finding `source_refs`: the cells name sheets and the claim names records, which a parent can read only if returned (T5).
- `partner_components` (optional assignment field) is a guess for the old requested-component field of the partner route; the old name lives in the unplaced `partner_source_contracts`.
- Tool names cannot contain a dot, so the model selects the old dotted library name (`source.read`) and `action` maps it to the episode's tool (`source_read`). `execution.estimate` and the other access tools are unchanged.
- Plumbing the new form needs and the old runner had inside its services: services `tool_catalog` (read member `entries`: the registry's `catalog()` as a list of `{name, description, input_schema}`) and `public_clients` (the registry's `PublicClients`), and settings `tool_registry` (the registry's executable and cache arguments). `decide` cannot call `ToolRegistry.catalog()` itself (no store). None of the three exists in any run yet.
- `decide` raises today (`population_catalog` is not placed), so the episode cannot run until `partner_source_contracts` is placed; this is by design (no fallback).
- This episode never writes assessments (the old episode had no reason action and offered `reason` nowhere), so `credit` (finding progress over held assessments) stays zero unless the parent passes assessments; `project_finding_progress` also fails today on `records` (library not carried).
- Controller: accumulation with `settings['cost']` and `settings['parameters']`; at cost zero it never stops (README 7b); the old episode had no continuation of its own (`yield_controller` returned None).
- `final_to_parent` returns an explicit "none reported" finding when the model never selected `report_finding` (the controller may stop before it); the finding is required by the class definition and a raise would fail every such run. No target support is manufactured (`target_correspondence` is `unresolved`).
- The shared `INSTRUCTIONS` text still describes `reason`, `child`, `wait` actions and the `report_update`; only the redelivery and history spans are replaced (`replace_span`). The old composer's wait/native-event/launch texts are not appended.
- The axis `validate_form` (JSON-schema report with `x-source`) is not applied: there is no JSON-schema report any more; `validate_report` checks the requested components and sheet references from the summary.
- No `msg_to_child.py` / `read_from_child.py`: no children, as the brief says.
