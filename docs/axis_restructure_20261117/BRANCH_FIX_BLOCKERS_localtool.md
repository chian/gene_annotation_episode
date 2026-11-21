# BRANCH_FIX_BLOCKERS_localtool (19 November 2026)

After the schema fix of the A101 head (`BRANCH_RUNS_localtool.md`) and the offline pass over the nine heads, the A101
head's real-model test was run once: `root/a101/sequence_homology_evidence/tests/test_branch_localtool_model_run.py`,
run dir `runs/fixsch_m1` (log `runs/fixsch_m1.log`, pytest output `runs/fixsch_m1/stdout.log`). Result: 2 failed
(407 s). The schema defect is gone; both branches fail later, for another reason. Nothing was fixed after this run.

## What the run shows

| | Branch 1 (`sequence.align`) | Branch 2 (`sequence.align`, `sequence.inspect`) |
|---|---|---|
| Model calls, all answered (no HTTP 400, no `error.json`) | 13 | 28 |
| First decision of the model | `sequence.align` (target against the held reference, global, protein) | `sequence.align` |
| Unit 0 | `execute_selected_tool` `sequence.align`: `completed`, 2 `record_refs` (a source and an observation) | the same |
| Units journaled before the failure | 9: 3 `sequence.align` completed, 5 `reason` completed, 1 `reason` invalid | 14: 3 `sequence.align` completed, 8 `reason` completed, 3 `reason` invalid |
| Credit of every unit | 0.0 (a pairwise alignment earns no A101 credit) | 0.0 |
| `sequence.inspect` | not offered | offered, never chosen |
| Last decision | commission of `published_evidence_assessment` | commission of `published_evidence_assessment` |
| Run | state `active`, failure `KeyError: 'question_context_refs'` | the same |

The model gets its choice and the local tool runs. `ended_by`, the admitted return and resume were not reached.
The bounded-quality controller had not stopped either head when it failed (cutoff 0.001; upper bound of the next
gain 0.018 after 9 units of credit 0 in branch 1).

## Blocker 1: the head does not tell the model what a child's assignment holds

Classification: EPISODE (A101 head, `task.py` and `messages/msg_to_child.py`).

`task.py:child_option` gives every child slot the same `assignment`: `OPEN` (`{'anyOf': [{'type': 'object'}]}`), and
the context's `child_options` name only the slot, its binding path, a description and the selectable return fields.
No schema and no text states the assignment fields of a child. `msg_to_child._literature`
(`messages/msg_to_child.py:65`) reads `given['question_context_refs']` and `given['source_refs']`; the other slots
copy `**arguments['assignment']` into the child's assignment, which the child's form then admits or refuses.

In both branches the model commissioned `published_evidence_assessment` with the head's own assignment shape
(`proposed_annotation_ref`, `evidence_refs`, `constraints`, `context`; branch 1 call 13, branch 2 call 28). The
commission is wrong, and a wrong commission fails (owner's rule): `KeyError: 'question_context_refs'`, raised where
the child is built. The same holds for the six other slots: any commission the model writes is a guess.

Smallest fix (shape, in the episode): one assignment schema per slot in `task.py`, with the fields `msg_to_child`
reads and the child's form takes (as the A102 head's `CHILD_ASSIGNMENTS`, the A106 head's `commission_arguments`
and the A107 head's `CHILD_FIELDS` do), in place of `OPEN`. The assignment still travels as JSON text (kind
`episode_child`), so the schema reaches the model in the property's description and `action` validates the decoded
assignment against it: an answer without `question_context_refs` is then a rejected answer, not a failed run.

## What was fixed before this run (offline pass)

The endpoint rules are in `episode_support/model_exchange/tests/provider_schema_rules.py` (what each rule rests on
is stated there). Each head has `tests/test_decision_schema.py`; all nine pass.

| Head | Result |
|---|---|
| A101 | fixed: a child with no selectable return field has no `selection` (was `{'type': 'array', 'maxItems': 0}`, the recorded HTTP 400); the reasoning commit is the tool `reason` with JSON-text arguments (inline it had 1,116 enum values, 407 properties and 10 levels; the endpoint's published limit is 1,000 enum values) |
| A102 | fixed: `LIST = {'type': 'array'}` at five child-argument fields now names its items (`RECORDS`, `TEXTS`) |
| A103 | OK |
| A104 | fixed: open objects `scope` and `initial_report` of both child options now travel as JSON text (`strict_output`, `open_records_as_text`); reasoning commit as the tool `reason` (1,115 enum values inline) |
| A105 | fixed: open objects `scope` (both children) and `constraints` now travel as JSON text; `decide` used `GOAL` without importing it (`NameError` at every decision) |
| A106 | fixed: launch `immutable_input_versions` had no `items`; `launch_instructions` was `{'type': ['object', 'null']}`, an open object the transport did not carry as text |
| A107 | fixed: `return_fields` omitted for a child with nothing selectable (was `maxItems: 0` without `items`); the `OBJECT` commission arguments now travel as JSON text; reasoning commit as the tool `reason` (1,281 enum values inline); `action` decoded against the strict schema instead of the original one, so JSON-text arguments were never parsed |
| A108 | OK |
| A110 | OK (the output schema is the action name and `arguments_json`) |

Mid-level episodes, same open-object defect, transport changed to carry open records as JSON text:
A101 `resource_result_acquisition`, `resource_work_submission` and its `api_`, `hpc_` and
`local_resource_work_execution`; A107 `execution_job_submission`.

## Found and not fixed

Schema defects left in mid-level episodes:

- `evidence_processing` is an object with properties that is not closed (`{'type': 'object', 'properties': {'kind':
  ...}}`), which the endpoint refuses; its fields are the owner's to state. Seven sites:
  A101 `resource_work_submission/task.py:248` and `.../api_resource_work_execution/task.py:224`;
  A102 `resource_work_submission/api_resource_work_execution/task.py:234`;
  A103 `resource_work_submission/task.py:267` and its `api_` (223), `hpc_` (221) and `local_` (224) children.
- The Store's whole reasoning schema inline under kind `reason` (1,057 to 1,092 enum values, over the published
  limit of 1,000): A101 `resource_result_acquisition/task.py:143`, `resource_work_submission/task.py:247`,
  `.../local_resource_work_execution/task.py:141`; A103 `resource_result_acquisition/task.py:144`.
- A106 `published_evidence_assessment/task.py:405-406` (a literature episode, not touched): the same
  `immutable_input_versions` without `items` and `launch_instructions` type list the head had.
- A107 `execution_job_submission`: transport changed, its schema not built offline (`_schema` needs a summary).

Heads that cannot reach their first model decision in a real run (not schema defects; found building the worlds):

- A102, A106, A108 (and A107, same code): `internal_summary` reads the finding progress through
  `episode_support/findings/<axis>/investigation_progress.py:project_finding_progress`, which opens
  `store.read_snapshot()` on the `RecordReader` it is handed: `AttributeError: 'RecordReader' object has no
  attribute 'read_snapshot'` (structural_homology_evidence:109, perturbation_evidence:106,
  sample_context_evidence:106, partner_presence_evidence:83).
- A107: `decide` reads the services `tool_catalog`, `tool_library`, `a107_library`, `tool_knowledge` and
  `launch_instructions`, which nothing implements.
- A110: the first unit `decide` names, `process_entry`, raises `NotImplementedError('old_module_not_placed:
  biochemical_feasibility_evidence_library.resolve')`.
- A107 `hpc_work_planning/task.py` does not import (`No module named ...jobs.hpc.partner_presence_evidence.hpc_ledger`).

The schema tests of A102, A106, A107, A108 and A110 therefore build the schema with the head's own schema functions
on real operands; A101, A103, A104 and A105 are stepped to the first model request in a world.
