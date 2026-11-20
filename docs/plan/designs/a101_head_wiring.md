# A101 head wiring: structure first, then the head commissions `pairwise_blast` (2026-11-20)

Owner ruling: `pairwise_blast` ran alone, which is not a test. The head must have the approved tree below it and
commission its children. This record is the step-zero list and the design. Prediction is at the end, written before the
run.

## What I read in full (step zero)

The A101 head (all files), `pairwise_blast` (all files), `episode_runtime/episode_type.py` (the episode type), the head's
world and tests, D1-D20 of the plan, AGENTS.md.

## What exists, per function I will write

| Needed | Exists | Decision |
|---|---|---|
| A parent commissioning a child with controlled fields | head `task.commission_fields`, `task.child_option`, `task.action` (builds `ChildCall`), `messages/msg_to_child.py` (`ChildMessage`), `messages/read_from_child.py` | reuse the pattern; add the `pairwise_blast` slot to each |
| Custody pass of the records a child reads | `msg_to_child._custody` over `summary['named_refs']` | call it for the query and the subject |
| What the head shows its model of a child's report | `read_from_child` returns credit, finding, record refs, handoff refs | unchanged: `pairwise_blast` declares `execution_*_refs` names it already reads |
| The head's credit from a graded sheet | `credit.A101SequenceCredit` (native correspondence over held records, scope target) | unchanged |
| Listing the bound local resources | `ctx.services['job_access'].read('resources')` (used by `launch_resources` for API) | a new small reader for local resources only |
| The pairwise child's declared return fields | `pairwise_blast/messages/final_to_parent.py` | selected by name: `execution_blast_graded_refs`, `execution_completed` required; `execution_handoff_refs`, `execution_job_record_refs` optional |

Nothing new is written in the library.

## Structure

Under `root/a101/sequence_homology_evidence/` the head's children are exactly the approved ones:
`pairwise_blast` (built), `blast_database_preparation`, `database_blast`, `all_vs_all_blast` (each a folder; the built
parts stay, the unbuilt parts are empty importable packages with `__init__.py` only, no stub episodes), and `hmmer`
(an empty package). The generic episodes (`execution_job_submission` and its leaves, `execution_progress_assessment`,
`execution_result_acquisition`, `resource_work_submission` and its leaves, `resource_result_acquisition`) stay on disk
only as templates for the remaining builds; the head no longer names them. They are the pending deletion.

## The head after wiring

- **Child slots:** `pairwise_blast` only (the approved children that exist). Removed: the six generic slots, the
  `literature` slot (its subtree is deleted on purpose) and the recursive slot to itself (it is not in the approved
  tree). With the recursive slot gone, `process_revise` (which only prepared a selection for that child) has no
  consumer and is removed with `revisions`, `REVISION_ARGUMENTS` and their prompt text.
- **Commission of `pairwise_blast` (controlled fields only):** `program` from the fixed set of the child's contract;
  `query_ref` one subject of the head's scope (the credit reads correspondence of the scope's target, so only these
  are offered); `subject_ref` one held subject record; `resource_id` one bound local resource. The head's model writes
  no assignment, objective or message. A query equal to the subject is rejected before any unit. Options are not
  commissioned: the child's form has none.
- **`msg_to_child`** builds the child's assignment in its own form from those fields: version, declared analysis kind
  `pairwise`, program, `query_refs`, `subject_refs`, `resource_id`, the information unit from the head's
  `child_credit_units`, and `record_refs` = the two subject records with the sequence artifacts they name (custody).
  It selects `execution_blast_graded_refs` and `execution_completed` always, and the model's optional choices
  (`execution_handoff_refs`, `execution_job_record_refs`).
- **What the head's model sees (`read_from_child`):** the child's credit and finding (the controlled features of the
  saved pairwise sheet), never the sheet. The sheet, its source and its search row come back as record references the
  head holds.
- **Credit:** the head's credit stays the native correspondence over what it holds (`A101SequenceCredit`), read from
  the saved sheet. The child's own credit is information and is never added to it. Credit is gained only by the graded
  correspondence; a repeat of a held comparison adds nothing (D17).
- **Prompt:** the head's own `GOAL` and instruction text are rewritten for what it can commission (pairwise now) and no
  longer describe launch, monitor or results children; the knowledge and launch instruction libraries are no longer
  assembled into the head's prompt. The head's selected evidence axis and thought pattern (its assignment's
  `selection`) stay, since they are its own assignment.
- **Outstanding handoffs:** `final_to_parent` counts a `pairwise_blast` report that is not completed as outstanding;
  `outstanding_jobs`, `launches`, `acquirable_jobs`, the API-resource reader and the monitor/results commission builders
  go with the removed children.
- **Tests:** the pytest files of the head that exercise the removed children (commissions, decision schema,
  episode-form checks of the six children, the literature subtree) are deleted. Nothing new is written as pytest. The
  head's world helper stays and is brought up to date; the test is a plain script.

## Prediction for the real run through the head (written before running)

World: the head's real world (a held target and a held reference protein differing at one residue, a proposed
annotation, the frozen libraries), one local resource with a 1 GiB policy, the bundled `blastp`, the real model at
the head, no tool of the local registry that answers the similarity question, and the instruction to compare the
target with the held reference by a pairwise BLAST.

1. The head's first decision is the commission of `pairwise_blast` with program `blastp`, the target as query, the
   reference as subject and the bound local resource (1 model call).
2. The child runs three code-decided units (launch, wait for the end event, fetch and grade) with 0 model calls, earns
   its information unit 1.0 at the grading, and returns the graded refs and `execution_completed` true.
3. The head's credit after the child is positive and close to the top of its scale (the pair differs at one of 70
   residues; I expect more than 0.9, not certain of the exact scale). The head ends by `yield_stop` after 1 to 3
   model calls in total.
4. Resume returns the same result with 0 new model calls (head and child).
5. Refusals, each with its own error and no job started (the jobs directory empty): a commission selecting a field the
   child does not declare fails at the child's form admission; a commission naming a record the head does not hold
   fails where `msg_to_child` follows the record's named records (a `KeyError`).
