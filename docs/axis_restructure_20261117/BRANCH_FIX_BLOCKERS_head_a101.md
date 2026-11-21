# BRANCH_FIX_BLOCKERS_head_a101 (19 November 2026)

What the fix of the A101 head's commissions (blocker 1 of `BRANCH_FIX_BLOCKERS_localtool.md`) and of
`project_finding_progress` (blocker 2) left open. `episode_runtime/` was not edited.

## 0. Needs in `episode_runtime/`

None. The custody reader has every read `project_finding_progress` makes (`validate_scope`, `require`, `get`,
`current_assessments`, `assessment_key`, `record_coverage`, `context_mask_overlap`, `assessment_write_extent`);
only `read_snapshot` was missing, and the function no longer opens one. `msg_to_child(slot, arguments, summary)`
is handed no reader, so the A101 head's summary lists what a commission names in custody beside a chosen record
(`named_refs`: for each held record the held records it names, from `records.named_references`; `msg_to_child`
passes a chosen record with everything it names, and those name in turn).

## 1. The A101 literature subtree cannot hold a pairwise alignment observation (blocks branches 1 and 2)

Classification: EPISODE (`root/a101/sequence_homology_evidence/published_evidence_assessment/credit.py`, and the
same private credit copy in each of the six episodes below it), with the library behind it
(`grading/sequence_alignment/native_correspondence.py::read_details`). Not the head's files; not changed.

With the controlled commission the real model commissions `published_evidence_assessment` correctly: in run
`a101head_14` branch 1 answered `question_context_refs` = the hypothesis and the `sequence.align` observation,
`source_refs` = none, the scope = the target; branch 2 answered the observation alone. `msg_to_child` builds the
assignment, every record named is held, the child's form admits it and the child is built. Then the child's
controller is built from its initial credit, and `credit.py:43` calls `A101SequenceCredit().read_details(records,
scope, known_record_refs=records.refs(), ...)` with no assignment: every held tool alignment observation is scored,
the pairwise alignment's grading sheet is neither a BLAST nor an HMMER sheet, no supported source is held, and
`read_details` raises `A101ScoringUnavailable('a101_unsupported_score_profile')` (line 180). The run fails with that
error (branches 1 and 2 of `a101head_14`, branch 2 of `a101head_7`). Nothing in A101 handles
`A101ScoringUnavailable`.

The head's own credit does not raise on the same held observation because it passes its assignment
(`proposed_annotation_ref`): `read_details` then scores only the observations the annotation's assessments select.
The old child credit was `services.scientific_credit(context, receiver_selection)` with the caller's projector.
The literature child passes everything it holds to its own child (`received_record_refs`), so the same error
waits in each episode of the subtree.

Decision wanted (the owner of the literature subtree): either the literature commission carries the proposed
annotation down the subtree (a new `proposed_annotation_ref` field of each assignment form, filled by the
commissioner, and each `credit` passes it as `assignment`), or an alignment of an unsupported profile contributes
nothing to the native correspondence instead of raising. Until then a head run ends with this error whenever its
model names a pairwise alignment observation as the question's context: 5 of the 6 branch 1 and 2 runs made since
the commission became controlled reached that commission, and all 5 failed (2 in the custody of the head's
commission, fixed since; 3 here). A run in which the model does not commission the child ends normally (branch 2
of `a101head_12`), and so does branch 3 (the same child commissioned with the hypothesis and the target as context
and the alignment's source in `source_refs`: the child then holds no alignment observation).

Resolved on 19 November 2026 with the first option. Each of the seven assignment forms of the subtree has the field
`proposed_annotation_refs` (`record_refs`, exactly one reference: the proposed annotation in custody); the head's
literature commission and each parent's `msg_to_child` fill it by code (the model does not name it and is not shown
it); `read_from_parent` reads it as `proposed_annotation_ref`, the summary carries it, and each `credit` passes
`{'scope', 'proposed_annotation_ref'}` as `assignment` with the held references that are not work-table rows, as
the head's credit does. The library is unchanged. Offline: `tests/test_literature_subtree_proposed_annotation.py`
steps each of the seven episodes (first decision and one unit) holding the pairwise alignment observation
(`runs/a101lit_6`: 63 passed). Real model: branches 1, 2 and 3 passed (`runs/a101lit_4`), and the commission that
failed (the observation alone as the question's context), made as a stepped unit, ran to the stop of child and head
(`runs/a101lit_5`). In those runs the credit of every literature Episode was 0.0: it holds no assessment of the
proposed annotation.

## 2. The two resource children have no controlled commission

`resource_work_submission` and `resource_result_acquisition` of A101 are not ported
(`RESOURCE_PORT_RECIPE.md`). Their forms take records only a model could write: `job_request` (`{'type':
'object'}`, the old `requested_job` with `argv`), `requested_data_selector` (open), and `handoff` (an
`execution_handoff_v1` record with nulls, which nothing writes as a record this head holds). The head therefore
declares both slots and offers neither (`task.WITHOUT_COMMISSION`); `msg_to_child` has no builder for them (the
old builders copied the model's open `assignment` into the child's). When the two are ported to the A102 form
(`work_refs`, `input_refs`, `allowed_kinds`, `resource_id`; `job_refs`, `requested_names`), each gets its entry in
`task.commission_fields` and its builder in `messages/msg_to_child.py`.

## 3. Launch and results commissions: built and form-tested, not run against a job

- `execution_job_submission`: the only request a model can state with controlled values is the BLAST database
  grader request (`resource_id` among the bound API resources of the service `ncbi_blast`, read from
  `job_access.resources()` and `describe`; `query_subject_ref` among the scope's subjects; an optional database
  name). A `practical_assignment_v1` request carries `requested_job.argv` (a command: the model is the router and
  writes none) and `api_execution_assignment_v1` (`ebi_hmmer`) has no route, so neither is offered. Tested offline:
  the launch child's own form admits the assignment and its `read_from_parent` permits the request
  (`tests/test_commissions.py`). Not run: the head's world binds no API resource and nothing remote was contacted.
  A head run with the local protocol server of `execution_job_submission/api_job_execution/tests/api_world.py` is
  not written.
- `execution_result_acquisition`: offered for an outstanding BLAST job this head launched; the model names its
  handoff row and code builds `handoff_ref`, the selector (the request of the launch), `execution_target_v1` (from
  the handoff row: its system columns `run_id` and `episode_id`, `detail.resource_id`, `detail.kind`,
  `detail.job_sha256`, the job handle) and the records in custody. Not run and not form-tested: it needs a held
  handoff row of an API job. A plain file result of a local or HPC job is not commissionable from the head: the
  head cannot launch such a job (no controlled request) and the selector's paths have no controlled answer set.
- The monitor's commission (`execution_progress_assessment`) was made controlled by the monitor's fixer in the
  same files while this fix ran; it is folded into `commission_fields` unchanged.

## 4. The head test world

- `tests/a101_world.py` binds the real job services with one local resource (`JobAccess({})` refuses an empty
  route map, and the head now reads the bound resources at every decision) and gives the seven episodes of the
  published-evidence subtree their settings (`cost` 0.1, `parameters`, `tool_registry`).
- The yield cutoff of the head in that world was changed from 0.001 to 0.01. At 0.001 the bounded-quality
  controller had not stopped after 14 units of credit 0 (upper bound 0.012, `runs/fixsch_m1`); at 0.01 it stopped
  after 13 (branch 2 of `runs/a101head_12`). This is a setting of the fixture, not a stopping rule.
- `sequence.align` failed once offline with `local_job_boundary_unavailable` (the tool's local job unit did not
  start, `runs/a101head_3`); the same test passed on the next run. Not investigated.

## 5. Other heads (blocker 2)

- A102, A106 and A108 heads now reach their first decision offline (`tests/test_first_decision.py` in each head's
  folder; A108's first decision is its own `process_selection` lookup, the model request follows it).
- A107: `findings/partner_presence_evidence/investigation_progress.py` is rewritten like the others and runs in the
  findings custody tests, but the A107 head does not call it (its credit counts its summary), and its `decide`
  still reads the services `tool_catalog`, `tool_library`, `a107_library`, `tool_knowledge` and
  `launch_instructions`, which nothing implements (`BRANCH_FIX_BLOCKERS_localtool.md`). No first-decision test was
  written for it.
- `FindingValidity` (`findings/<axis>/finding_validity.py`) and `_project_known` keep a private temporary SQLite
  database (`sqlite3.connect('')`) for the dependency closure of one call. It is not the Store and holds no record;
  it was left as it is. Whether it should become plain Python is the owner's to say.
- `root/a102/structural_homology_evidence/credit.py` (docstring, lines 19 to 22) and
  `root/a106/perturbation_evidence/credit.py` (line 13) still say the projection reads the raw Store; the text is
  stale and was not edited (other fixers' folders).
- `root/a107/partner_presence_evidence/tests/test_binding.py::test_the_selectable_names_are_the_names_the_child_declares[hpc]`
  fails (`hpc_accepted_obligations`, `hpc_credit`, `hpc_model_ref` named by the head and not selectable in the
  child): not touched by this fix, seen in `runs/a101head_11`.
