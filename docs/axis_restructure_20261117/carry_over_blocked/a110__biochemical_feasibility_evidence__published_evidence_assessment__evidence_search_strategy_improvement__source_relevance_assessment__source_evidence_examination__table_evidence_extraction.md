# a110 table_evidence_extraction: blocked, unplaced and misfits

## Source of the old code was not readable
The repository directory has no `.git` (no commits, `97308b94c` is not an object), so `git show 97308b94c:<path>` was impossible and
no old file was read. The episode was carried from `episode_intent/a110/...table_evidence_extraction.md` (the earlier intent record),
`runs/carry_over/functions/*.tsv`, and the old values in the working-tree `episode.py` (goal, unit, result). The instruction text,
tool argument shapes, output schema, and credit are rewritten from that record, not copied. `docs/axis_restructure_20261117/GOAL.md`
does not exist either.

## BLOCKED-ON-STORE-ACCESS
- `task.py::list_xlsx_sheets`, `task.py::read_xlsx_rows`: old call `xlsx_native(path of the artifact, operation=..., arguments=..., job_limits=...)`
  (`episode_support/tools/documents/biochemical_feasibility_evidence/spreadsheet_tools.py`, needs a file path, a scratch directory and local-job limits)
  -> intended call: a scratch-directory and artifact-file operation of `ctx.store`. The tools raise `NotImplementedError('blocked_on_store_access: ...')`
  after the source-containment and assigned-sheet checks.
- `task.py::_within_source`: old `services.read_record` chain over `parent_source_refs` -> `ctx.store.get(ref)`; works when every source in the chain is held.

## Library not carried / missing (unplaced)
- `literature.reaction.populate`, `literature.reaction.source.populate` (old `_population_catalog`, `_materialize_text_arguments`): modules `reaction_population`,
  `reaction_source_selection`, `literature_reaction_storage`, `literature_component_binding` are not in the library. `task.py` declares both tools; they raise
  `NotImplementedError('a110_reaction_population_not_built')` and are not offered to the model.
- Old `numerical_report_facts` (reaction cells, native observations), `received_reports.validate_received_report`, `reaction_records`,
  `internal_summary._owned_population_task_sources` / `_population_task_context`: same missing modules. `RETURN_FORM` declares no reaction fact source.
- Old `validate_report` called `validate_form(form, schema, resolver)`: axis a110 has no `validate_form`; the form was the parent-written one, which no longer exists.
  `final_to_parent.validate_report` checks the assignment and `FINDING_FORM.admit` instead.

## contract_misfits
- new field: table_evidence_extraction kind (selection form has no union; `kind` names table or window), scope, finding_unit, received_record_refs.
- new field: table_evidence_extraction finding (typed finding with source_ref, anchor, claim, subject, qualification) and reads (selectable).
- The parent-source containment of the old `prepare_assignment` (`literature_reading_outside_assigned_source` against the parent page's assigned source) needs the
  commissioner's source; no field carries it, so it is not checked.
- The window offset-out-of-bounds check (`source_offset_out_of_bounds`) needs the artifact size from a Store read; read_from_parent has no records and it is not carried.
- Generic `scientific_instruction_text.INSTRUCTIONS` describes reasoning commits and child commissions this episode does not offer; it is not used, `task.py` has its own text.
- `source_custody` in `internal_summary` assumes the source record fields `text_ref`, `artifact_ref`, `stdout_ref`, `stderr_ref`, `parent_source_refs` (from the intent record); untested against a real Store.
- Credit (finding_unit x distinct findings) is reconstructed from "scientific credit, no projector"; the old projector was not readable. Accumulation controller chosen; the old files named none.
- The shared `root/a110/.../published_evidence_assessment/literature_binding.py` is no longer imported by this episode; it remains for other episodes.
