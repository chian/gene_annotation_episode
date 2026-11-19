# a102 structural_homology_evidence/resource_work_submission: blocked, unplaced and misfit items

## BLOCKED-ON-STORE-ACCESS

None. The library functions this episode calls (`records/hpc/resource_records.py`, `instructions/*`,
`tools/tool_knowledge.py`, `model_exchange/*`, `records/progress_views.py`, `jobs/waiting.py::selected_wait`) take
values, files of their own library directory, or a service; none reads the Store. Every Store call of the episode is
`ctx.store` / `records` (`holds`, `get`, `refs`, `artifact`, `commit_reasoning`, `reasoning_schema`).

## BLOCKED-ON-SERVICES (no library module wraps them; the episode calls the named members)

- `resource_adapter`: the old `resource_adapters` (explicit caller bindings by `resource_id`; the A102 adapters were
  in the deleted shared root). Members called: `declared_capabilities()`, `bound_resource_ids()`,
  `adapter_capabilities()`, `can_check_handoff(resource_id)`, `check_handoff(handoff, held, key=)`,
  `facts(assignment)` (handoffs and facts of every configured adapter), `credit_view(assignment, held_refs)`,
  `decision_context(assignment)`. A run without this service fails at link (`service_required`).
- `native_events`: `NativeEventLedger` (`validate_event_targets`, `wait_events`, read member `targets(assignment)`).

## Unplaced old functions

- `ResourceToParent.validate_report`, the per-adapter part (`adapter.validate_report(context, form, schema)` for every
  adapter): it belongs to the adapters (a service) and `final_to_parent` has no service. The handoff-equals-facts
  part is carried (`messages/final_to_parent.py::validate_report`).
- The old `workflow.validate_report(..., grain='launch')` call on the model's `report_update` in `task.py`
  `apply_response`: the report update is not carried (the typed form is the child's/parent's RETURN_FORM); A102 has no
  `validate_form`, and none is called, so nothing raises `NotImplementedError('validate_form_not_built:a102')`.

## Contract misfits

- new field: resource_work_submission completion_target (the credit a usable execution handoff earns; the completion
  controller needs a target; the old code had none).
- new field: resource_work_submission scope (the old request scope), scope_refs and input_refs (record_refs passed in custody).
- new field: resource_work_submission adapter_assignment (optional). The local child's assignment form requires the
  adapter-prepared `practical_assignment_v1`, which the old child produced itself in `prepare_assignment`; this
  parent has no adapter preparation ("no adapter preparation at this level"), so its commissioner supplies it, and a
  `launch_local` commission without it fails in the child's form (rule 1).
- completion credit may pass its target: the credit is the adapters' own credit view (`credit_view`), unbounded, and
  the commissioned `completion_target` is a separate number the commissioner states; nothing ties them (the controller's
  `ValueError('completion_credit_exceeds_target')` is the failure).
- The parent's credit is re-measured only by a resource tool unit (`resource_capabilities`, `resource_inspect`,
  `resource_check_handoff` return `adapter_credit`). Work a child did through the shared adapters changes the adapters'
  credit view, but `credit(summary, records)` has no service and a child unit's outcome carries no adapter credit, so
  the parent's credit rises only at its next resource tool unit. The parent never adds up its children's credits.
- The three children name their handoff record field differently (`execution_handoff_refs`, `execution_handoff_record_refs`,
  `handoff_refs`); the parent keeps that table in `messages/read_from_child.py::REF_FIELD` and selects the optional
  ones in `messages/msg_to_child.py::BASE_SELECTION`. `adapter_facts` is selectable only on the API child.
- The old child action let the model author the child's `launch_instructions`; the strict output transport has no
  clean nullable record, so the child inherits this episode's own pinned `launch_instructions` (the old child had to
  retain them anyway) and the model chooses only the objective, `resource_selection`, `initial_report` and, for the
  API child, `adapter_facts`.
- Old behaviours not carried because they belong to removed mechanisms: the contract-information discovery paragraph
  of the goal and its profile (`request_context` / `episode.return_contract`), `redeliver_report`, the `wait` on
  `pending_child_` handles, report_update/report_basis, `sqlite3.Error` in the handoff check (the adapter service
  raises its own errors now).
- The old `ResourceEpisode` in the working tree (a `JobSubmissionBinding` with a `requests` assignment) was a hook-era
  port that did not match the old files at `97308b94c`; it and `tests/test_resource_work_link.py` were deleted.
- The action schema with `SELECTION_SCHEMA` (nested `allocation` with nullable integers) passes
  `strict_output_schema`, but no real model run was made in this step.
