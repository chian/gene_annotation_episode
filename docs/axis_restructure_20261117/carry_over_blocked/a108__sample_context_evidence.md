# sample_context_evidence (A108 head): blocked, unplaced and contract misfits

All library paths are under `gene_annotation_episode/episodic_workflow/episode_support/`.

## Process note

The working repository (`/tmp/ramrepo`, the same tree as `/home/chia/repos/gene_annotation_episode`) has no `.git`; the old files
were read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` (only this episode's own files). The folder
held the hook-era `episode.py` (class on `HeadRuntimeContract` and `ScientificConfiguration`), `configuration.py`,
`runtime_contract.py` (the `a108_home_factory`, the `RuntimeRecord` and the head's own `build_controller`), `runtime_source.py` (the
hook-era decision source with `bound.recorder`) and `tests/test_model_run.py`; all were deleted before the new files were written
(`runtime_contract.py` also held the seven-binding home factory: a table of bindings, not carried). The child folder
`published_evidence_assessment/` was read as data (its `goal.py`, `messages/read_from_parent.py`, `messages/final_to_parent.py`) and
is neither touched nor imported (its test imports its forms; no module of this folder does). Importing `episode.py` passes the
class-definition checks; `tests/test_sample_context_evidence_binding.py` (9 tests) passes.

## BLOCKED-ON-STORE-ACCESS (function, pattern)

- `findings/sample_context_evidence/investigation_progress.py::ScientificFindingProgress.__call__` / `project_finding_progress`
  (credit.py `credit_view`, hence `credit()` and `internal_summary`, hence the initial credit of the controller): "library not
  carried". Old calls: `store.read_snapshot()` (the reader `records` offers none), `store.validate_scope`, `store._require(ref, kinds)`,
  `store.db.execute(... current_revisions ...)`, `store.assessment_key(row)`, `sqlite3.connect('')` for the spool. Intended:
  `records.current_assessments(scope)` / `records.list('assessment', scope)`, `records.is_current(ref)`, `records.require(ref, kinds)`,
  `records.assessment_key(row)`; no transaction. The call stays as written; it raises at the first `credit()` call, from the library
  function, not at the top of `credit()`.
- `findings/sample_context_evidence/finding_validity.py::FindingValidity` and `::target_eligible` (inside the projector above): "library not
  carried" (`sqlite3`, `store._assessment_write_extent`). Intended: `records.current_assessments`, `records.is_current`, custody reads.
- `findings/sample_context_evidence/scientific_findings.py::FindingIdentity` (inside the projector): "library not carried" (private Store
  method). Intended: custody reads.
- `tools/sample_context_evidence/tools.py::ToolRegistry` (task.py `run_access_tool`: every tool of the selection): "library not carried"
  (`store.db.execute('CREATE TABLE IF NOT EXISTS tool_operations ...')` in `__init__`, private Store methods). Intended: `ctx.store` only;
  the `tool_operations` ledger is the system's attempts journal (`ctx.operation_key`).
- `literature/storage/literature_grading_storage.py::LiteratureA108GradingRepository` and
  `literature/grading/sample_context_evidence/literature_required_grading.py::execute` (task.py `reason`): "library not carried" (sheet
  tables are raw `store.db` tables, not declared work tables; `store.commit_reasoning(..., account_owner=...)`). Intended:
  `store.table(T).put`, `store.commit_reasoning(payload, scope, ctx.operation_key)`, `records.table(T).select`.

## Unplaced old functions

- `execution_planning.catalog` and `execution_planning.read` (the `process.execution` tool): not offered. It needs the old
  `workflow.resource_context`, `workflow.episode_bindings` (HPC commissions) and `execution_planning.memory_for` / `execution_memory`
  services; the old schema has `maxItems: 8` and `history(limit=64)`, count limits the current rules forbid.
- The common tools `episode.history`, `episode.credit`, `episode.annotation_score`, `episode.monitoring_information`,
  `episode.estimate_wait` and the five `shared.*` tools (request, publish, resolve, read, list information): old-runner reads of the
  journal and old shared-root modules that are not in `episode_support/`; not offered. (`episode.history` and `episode.credit` are what the
  summary shows now.)
- `library_operations.execute_catalog_operation`'s `library.execute` operations other than `process.search`, `process.entry`,
  `process.sources` and `process.tools`: no module; not offered.
- `library_services.scientific_support_routes` and the `annotation_support_routes` block of the decision context for an axis entry that is
  not an instruction entry: no module in `episode_support/`; not shown.
- `standalone_presentation.uses_root_credit_presentation`, `standalone_frame`, `root_annotation_context`;
  `presentation_fields.annotation_context`, `attach_native_timing`: the root-shaped frame (arms, annotation credits, root score,
  proposed annotations, comparisons) presents the root's state, which this episode does not hold; the native timing context has no field in the
  new credit view.
- The return fact source `sample_context_evidence_results` (`to_parent.facts`: `build_process_result`, `merge_process_results`,
  `project_process_result`, `report_sources`, `validate_process_result` of the old `library/sample_context_evidence_reports`, and
  `private_received_results`, `private_frozen_results` over the old `sample_context_evidence_provenance`): no module in `episode_support/`.
  The field is declared (selectable); `final_to_parent` raises `NotImplementedError('unplaced_old_function:library.sample_context_evidence_reports.project_process_result')`
  where it is selected. A child's returned results ride unprojected in `read_from_child`'s report.
- `validate_form` of the A108 axis: none exists. `messages/final_to_parent.py: validate_form` raises
  `NotImplementedError('validate_form_not_built:a108')`, as the old `validate_report` called it. Consequence: `final_to_parent` raises today
  and no run of this episode returns until the axis has a `validate_form` (as for its child).
- Contract-information freezing (`contract_information_profile`, `freeze_contract_information`, `composition_information`) and the
  `tool_retrieval` configuration (`scientific_tool_retrieval.configuration`): old shared-root modules, not in `episode_support/`; not carried.
- Not carried, as checks of a commission: the old `_assignment` Store checks (proposed annotation in scope and received by the parent,
  evidence references in scope), `_selection` library checks (library id, axis entry kind, `resolve_tool_info` against the live catalog),
  `_validate_origin` (revision origin against the parent's `process.revise` preparation), `_invocation` (objective, purpose, report schema,
  initial report), `prepare_invocation`'s required-return-source check, `validate_context` / `validate_execution_context` and the closed
  commission replay branch.

## Contract misfits

- new field: sample_context_evidence `scope` (the old request scope) and `received_record_refs` (the old binding-context received records):
  new fields of `ASSIGNMENT_FORM`, filled by the commissioner (the root, for the head; this episode's `msg_to_child` for its children).
- new field: sample_context_evidence `proposed_annotation_ref` is a required field of `ASSIGNMENT_FORM` (the old schema made it optional, but
  the old `credit_projector` refused a yield-bound task without it, and the yield settings are always set now).
- new field: sample_context_evidence `selection` travels as selectors (`child_tool_info` as name and resources, as the old assignment did);
  `process_selection` materializes the descriptions and instructions from the tool library (settings `tool_library_directory`). The root's
  `msg_to_child` for this head must pass the selection in that form with the two pinned option references.
- new field: sample_context_evidence `purpose` (in `ChildMessage.message`) and `return_fields` (the child's selectable fields the model
  wants) and, for the recursion, `scope`, `selection`, `evidence_refs`, `revision_origin` are the ChildCall arguments (the old model wrote
  `goal`, `purpose`, `report_schema`, `initial_report`, `assignment` and `scope`). The proposed annotation, the constraints and the context
  with the evidence task are inherited by `msg_to_child` from this episode's own parent input (the old `prepare_assignment` inherited the
  proposed annotation; the constraints and the context were model-written, which an open object cannot be in the strict output schema).
  A narrower child therefore has the parent's evidence task and credit unit.
- new field: `summary` keys `held_source_custody` and `proposed_annotation_subject_refs` exist only so that `msg_to_child` (which has no `records`)
  can name every record the child reads (decision T5).
- new field: sample_context_evidence `known_assessment_refs` and the `source_claim` / `source_subject` / `qualification` / `readings` of the
  typed finding: the old form was written by the parent; the finding's interpretation is the `report` tool's outcome (a head that never
  reports returns `written: false`). `known_assessment_refs` is a `record_refs` field of the finding so that the parent holds what the head's
  credit counts.
- The head's `reason` couples the grader selection and the saved subscoring sheet (`literature_required_grading`, a copy of the sibling
  literature episode's `reason` with this role), as AGENTS.md "Required literature evidence processing" requires; the old head ran
  `store.commit_reasoning` without a grader. The head offers no population tool, so a sheet is saved only through the graded `reason`. A
  decision for the owner: whether the head's own reasoning is graded or only its literature child's.
- Settings: `ctx.settings['tool_registry']` holds the keyword arguments of `ToolRegistry` including a `PublicClients` object, which is not
  closed JSON; settings are journaled at link and compared on resume (BINDING_CONTRACT, "What each function is handed"). The same holds for
  the sibling literature episodes. `process_library_directory`, `tool_library_directory` and `knowledge_library_directory` are read from disk
  inside tools (outside the Store and outside any service); no service wraps them.
- The first unit of every commission is the lookup `process_selection` (credit 0): the old head showed the axis, the thought pattern and the tools
  from the start, in the decision context. With an accumulation controller the first unit's zero marginal credit is an observation like any other.
- The old required return sources (`sample_context_evidence_results` and `committed_record_refs` under the root's annotation task) are the
  parent's choice of `ChildMessage.selection` now; the head selects `committed_record_refs` from its recursion on every commission.
- T5: the head returns assessments in `known_assessment_refs` / `committed_record_refs` without the records they name (hypothesis,
  observation, source, artifact, subjects); the reader of the return (its parent's credit via `FindingValidity` / `target_eligible`) will need
  them. `committed_record_refs` follows the sibling's meaning ("records the reasoning commits created or changed"), which includes what the commit
  created. Whether `record_refs` fields inside the nested `finding` form are put into custody like top-level ones is not stated in the contract;
  `read_from_child` reads `finding['committed_record_refs']` and `finding['graded_sheet_refs']` as the sibling does.
- Slot names are the folder names (`sample_context_evidence`, `published_evidence_assessment`); the old roles were `sample_context_evidence` and
  `literature`. Tool names are lowercase with underscores (`process_search`, `source_read`, ...); the old names had dots. The model sees
  `library_name` in the tool catalogue.
- Completion credit: not applicable. The head's projector has `yield_method` `accumulation`; the old `bounded_quality` and `completion` branches
  were unreachable for it and are not carried. No "completion credit may pass its target" misfit.
