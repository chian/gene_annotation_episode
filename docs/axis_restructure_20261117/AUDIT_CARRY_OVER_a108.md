# Audit of the A108 carry-over (read-only, 19 November 2026)

Scope: every episode folder under `gene_annotation_episode/episodic_workflow/root/a108/` (8 episodes), read file by
file against `AGENTS.md`, `BINDING_CONTRACT.md`, the reference episodes `episode_runtime/tests/fact_collection/` and
`fact_extraction/`, and each episode's own old files at `97308b94c` (`git show`). No code or test was changed.

Result: **8 episodes audited, 0 PASS, 8 with findings.** No episode can complete a run today: every
`final_to_parent` raises `NotImplementedError`, and every tool and the head's credit call library code that is not on
custody.

Tests were run once through the launcher (`runs/audit_a108_2`, slot `auda108`): 66 passed in 1.05 s. They are
structural (see F7) and say nothing about a run.

Path aliases used below (all under `root/a108/`):

| Alias | Folder |
|---|---|
| HEAD | `sample_context_evidence/` |
| PEA | `sample_context_evidence/published_evidence_assessment/` |
| ESSI | `PEA/evidence_search_strategy_improvement/` |
| SRA | `ESSI/source_relevance_assessment/` |
| SEE | `SRA/source_evidence_examination/` |
| TEE | `SEE/table_evidence_extraction/` (leaf) |
| SCI | `SEE/source_coverage_improvement/` (leaf) |
| PEE | `SEE/passage_evidence_extraction/` (leaf) |

Library paths are under `gene_annotation_episode/episodic_workflow/episode_support/`.

## What holds in all 8 episodes

- Check 1, file set: exactly the ten files (eight for the three leaves), `__init__.py`, child folders, `tests/`.
  No other behaviour module.
- Check 2, `episode.py`: one class inheriting `EpisodeBinding` alone; no import from another episode folder (only
  `.`/`..` imports inside the episode's own folder); no table or registry of bindings.
- Stopping: `decide` and `action` return only `ToolCall`, `ChildCall` or `ModelRequest`, or raise `Rejected`. No
  other stop rule, no elapsed-time, token, turn or count cutoff.
- No `store.db` or raw `Store` use written in an episode file (the raw use is in the library they call, F3).
- `yield_estimator.py` reads `settings` and `parent_input['task']` only, never the assignment.
- `return_form` requires `credit` (number) and `finding`; the parent selects in `msg_to_child`.
- `credit.py` is real code, not a stub, and never bounds, clamps or rescales.
- Yield controller matches the old method. HEAD: accumulation (old projector `yield_method = 'accumulation'`,
  `findings/sample_context_evidence/investigation_progress.py:42`). The seven literature episodes: accumulation for
  `verified_source_leads`, completion with target `credit_unit` for `source_answer` (old `YieldController` and
  `_FiniteLiteratureYieldController` / `_RemainingCommissionedCredit`).
- No old-runner name in code (`recorder`, `recall`, `SourceEnd`, `Done`, `wait`, `redeliver_report` appear only in
  docstrings that say they are not carried).

## Finding types

| Id | Finding | Rule |
|---|---|---|
| F1 | `final_to_parent` always raises `NotImplementedError('validate_form_not_built:a108')`: the old `validate_form` lived in the old shared root (`a108/communication.py:695`) and has no library function | check 4/5: stub; no episode returns |
| F2 | The return form declares selectable fields that raise `NotImplementedError` when selected | owner rule 5: a child declares what it can return |
| F3 | Tools and credit call library code that reads and writes the raw Store (`store.db`, `store._require`, `read_snapshot`, own SQL tables); under the custody store it raises `AttributeError` | owner rule 3: library never touches the Store directly |
| F4 | `except Exception` turns any error of a selected tool into a `failed` outcome | check 5: try/except that hides errors |
| F5 | `ctx.settings.get('tool_registry', {})`: a missing setting is silently an empty registry configuration | check 5: silent default |
| F6 | `action` checks the records of a child commission with `records.holds` and returns feedback to the model | owner rule 1: no pre-check and no feedback path for a commission |
| F7 | Tests never call `decide` or `action`, never run the episode through the runner, call `credit` only with empty input and `None` for `records`, and call `final_to_parent` only to assert that it raises | check 6 |
| F8 | Old episode functions dropped or weakened (function accounting) | AGENTS.md: "None is dropped" |
| F9 | A108 required literature processing not carried through to the parent | AGENTS.md, "Required literature evidence processing" |
| F10 | A dataclass in `task.py` rebuilds the old binding context (`role`, `path`, `request`, `received_record_refs`) so that the un-carried library can be called | AGENTS.md: no shims |
| F11 | `msg_to_child` selects `literature_screening_answers` and `read_from_child` discards it | owner rule 5 (selection without use) |
| F12 | Leftovers and false statements in one file | check 5 |

## Per episode

### HEAD `sample_context_evidence` — findings

- F1 `messages/final_to_parent.py:82` (called at `:90`, `:109`).
- F2 `messages/final_to_parent.py:108`: `sample_context_evidence_results` is declared (`:67`) and raises. The head's
  own model may select it for its recursion child (`task.py:253`, `messages/msg_to_child.py:64`), which then fails.
- F3 `credit.py:39`: `ScientificFindingProgress.__call__` reaches `investigation_progress.py:106`
  (`store.read_snapshot()`), `:78`/`:130` (`store._require`), `:150` (`store.db.execute`). `records` is a
  `RecordReader`, which has none of these, so `credit()` raises on its first call. `messages/internal_summary.py:108`
  calls the same function for every summary, so the head cannot build its first summary or its controller.
  `task.py:501`: `ToolRegistry.__init__` runs `store.db.execute('CREATE TABLE ...')`
  (`tools/sample_context_evidence/tools.py:73`). `task.py:624-631`: `LiteratureA108GradingRepository` and
  `literature_required_grading.execute` (`store.db` in `literature/storage/literature_storage.py:22,64,129`;
  `commit_reasoning(..., account_owner=...)` at `literature_required_grading.py:116-118`, a keyword the custody
  store does not take).
- F4 `task.py:508`.
- F5 `task.py:501`.
- F6 `task.py:718` and `task.py:722-723` (`held(...)` before `ChildCall`, rejected through `Rejected` at `:732`).
- F7 `tests/test_sample_context_evidence_binding.py:189-199` asserts both `NotImplementedError`s; summaries are
  hand-built dicts (`:118-126`); no test of `decide`, `action`, `credit`, `internal_summary`, `read_from_child`.
- F8 Function accounting:
  - `credit.original_task_projector` -> `messages/read_from_parent.py:65-72` and `credit.py:26-28`: present.
  - `scientific_operations.ScientificOperations.execute`: the `process.revise` branch is `task.py:467-490`
    (present); the `process.execution` branch (`execution_planning.catalog`, `read`) is not offered
    (`task.py:28-33`): dropped. Also dropped there: `episode.history`, `episode.credit`,
    `episode.annotation_score`, `episode.monitoring_information`, `episode.estimate_wait`, the `shared.*` tools.
  - `to_parent.ScientificReport.facts` -> `messages/final_to_parent.py:107-108`: `NotImplementedError`.
- F9 The old head committed reasoning without a grader. The new `reason` (`task.py:616-631`) is a copy of the
  literature episode's coupling: added, not carried, and the blocked file records it as an owner decision still
  open. It cannot run (F3).
- F10 `task.py:298-310` (`GradingContext`).

### PEA `published_evidence_assessment` — findings

- F1 `messages/final_to_parent.py:91` (called at `:102`, `:132`).
- F2 `messages/final_to_parent.py:128`, `:130`; `messages/internal_summary.py:65` (`saved_cells`: the grading and
  aggregation cells raise once the parent requested components and a sheet is saved).
- F3 `credit.py:84-88` (`FindingValidity`, `target_eligible`: `finding_validity.py:24` `store._assessment_write_extent`);
  `task.py:406` (`ToolRegistry`); `task.py:362-367`, `:540`, `:629`, `:639` (sheet repositories and required grading).
- F4 `task.py:413`.
- F5 `task.py:277`, `task.py:406`.
- F6 `task.py:724-726`.
- F7 `tests/test_published_evidence_assessment_binding.py`: class, file set, imports, form, controller kind,
  `msg_to_child` on a hand-built summary (`:102-116`). Nothing else.
- F8 Function accounting:
  - `credit.validate_lead` -> `task.py:553-587`: present, on custody (`store.require`).
  - `credit.LiteratureTaskCredit.__call__` / `_answers` -> `credit.py:103-129`: present, scope and target checks
    kept (`:109-114`).
  - `to_parent.LiteratureReport._a108_facts` -> `messages/internal_summary.py:58-66`: `NotImplementedError`.
- F10 `task.py:245-256` (`LiteratureContext`).
- F11 `messages/msg_to_child.py:40-41` selects `literature_screening_answers`; `messages/read_from_child.py:21-27`
  does not read it.

### ESSI `evidence_search_strategy_improvement` — findings

- F1 `messages/final_to_parent.py:91`.
- F2 `messages/final_to_parent.py:128`, `:130`; `messages/internal_summary.py:66`.
- F3 `credit.py:84-88`; `task.py:406`; `task.py:362-367`, `:540`, `:629`, `:639`.
- F4 `task.py:413`.
- F5 `task.py:277`, `task.py:406`.
- F6 `task.py:724-726`.
- F7 `tests/test_evidence_search_strategy_improvement_binding.py`: as PEA.
- F8 Function accounting:
  - `yield_estimator._private_yield_controller` -> `yield_estimator.py:14-20`: present.
  - `credit.screening_answers` -> `credit.py:58-76` with `messages/internal_summary.py:134-142`: present.
  - `to_parent.LiteratureReport.current_report_facts` -> `messages/final_to_parent.py:127-131`: `NotImplementedError`.
- F10 `task.py:245-256`.

### SRA `source_relevance_assessment` — findings

- F1 `messages/final_to_parent.py:91`.
- F2 `messages/final_to_parent.py:128`, `:130`; `messages/internal_summary.py:66`.
- F3 `credit.py:84-88`; `task.py:406`; `task.py:362-367`, `:540`, `:629`, `:639`.
- F4 `task.py:413`.
- F5 `task.py:277`, `task.py:406`.
- F7 `tests/test_source_relevance_assessment_binding.py`: as PEA.
- F8 Function accounting:
  - `credit.lead_dispositions` -> `credit.py:46-55` with `messages/internal_summary.py:127-132`: present.
  - `grading/contextual_interpretation.execute_reasoning` -> `task.py:604-640`: present.
  - `to_parent.validate_report` -> `messages/final_to_parent.py:94-109`: its `validate_form` step is the stub (F1).
- F10 `task.py:245-256`.
- F11 `messages/msg_to_child.py:42-43` selects `literature_screening_answers`; `messages/read_from_child.py` does
  not read it.
- F12 `task.py:275`: docstring says "the three child commissions"; the episode has one child.

### SEE `source_evidence_examination` — findings

- F1 `messages/final_to_parent.py:90`.
- F2 `messages/final_to_parent.py:127`, `:129`; `messages/internal_summary.py:56`.
- F3 `credit.py:84-88`; `task.py:424`; the repository and required-grading calls of `populate` and `reason`.
- F4 `task.py:431`.
- F5 `task.py:257`, `task.py:424`; `messages/msg_to_child.py:52-53` (`assignment.get(..., [])`).
- F7 `tests/test_source_evidence_examination_binding.py`: as PEA.
- F8 Function accounting:
  - `source_references.SourceReferences._within_source` -> `task.py:319-332`: present, same walk.
  - `from_child_*.receive_report` -> `messages/read_from_child.py:14-37`: present for the table and coverage
    children; the passage child's findings and sheets are dropped (F9).
  - `to_parent.LiteratureReport._a108_facts` -> `messages/internal_summary.py:49-56`: `NotImplementedError`.
- F9 `messages/read_from_child.py:25-26`: for the passage child the report carries no `assessment_findings` and no
  `graded_sheet_refs`, so the typed `investigation_finding` of each assessment that child committed, and the sheets
  it saved, do not reach this episode's finding. `messages/msg_to_child.py:27` and `:37-43`: requested A108 cells
  are not asked of the passage child (its fields raise), so requested components are silently missing for work
  done there.
- F10 `task.py:225-236`.
- F11 `messages/msg_to_child.py:35-36` selects `literature_screening_answers`; `messages/read_from_child.py:30-37`
  does not read it.

### TEE `table_evidence_extraction` — findings

- F1 `messages/final_to_parent.py:90`.
- F2 `messages/final_to_parent.py:131`, `:133`; `messages/internal_summary.py:53`.
- F3 `credit.py:84-88`; `task.py:392`; `task.py:345-353`, `:490`, `:579`, `:589`.
- F4 `task.py:399`.
- F5 `task.py:224`, `task.py:392`.
- F7 `tests/test_binding.py:134-143` asserts the `NotImplementedError`s; `:121-122` passes `None` as the store;
  `:146-158` tests only the pure span arithmetic of credit.
- F8 Function accounting:
  - `grading/contextual_interpretation.reasoning_has_task_content` -> `task.py:646-652`: present.
  - `goal.commissioned_task` -> `messages/read_from_parent.py:112-132`: present, schema validated.
  - `to_parent.LiteratureReport._a108_facts` -> `messages/internal_summary.py:46-53`: `NotImplementedError`.
- F10 `task.py:192-203`.

### SCI `source_coverage_improvement` — findings

- F1 `messages/final_to_parent.py:86` (called at `:91`).
- F2 `messages/final_to_parent.py:104`, `:106`.
- F3 `credit.py:74-78`; `task.py:365`; `task.py:269-279`, `:530`.
- F4 `task.py:372`.
- F5 `task.py:193`, `task.py:365`; `messages/internal_summary.py:42` (cells read as `[]` when a population result
  has none).
- F7 `tests/test_binding.py:98-106` asserts the `NotImplementedError`; `:115` calls `credit(summary, None)`.
- F8 Function accounting:
  - `goal.task_schema` -> `messages/read_from_parent.py:62-80`: present.
  - `credit.LiteratureTaskCredit.__call__` -> `credit.py:93-109`: the annotation-in-scope and target-root checks
    (`literature_task_annotation_outside_scope`, `literature_task_requires_target_annotation`) are dropped; the five
    non-leaf siblings and TEE keep them.
  - `to_parent.LiteratureReport._a108_facts` -> `messages/internal_summary.py:40-71`: present by another route
    (cells read from the population outcomes).
- F10 `task.py:250-262` (`GradingContext`).
- F12 `messages/read_from_parent.py:65-72`: the task schema still admits the old `yield_settings` (kind, cutoff,
  uncertainty_alpha), which the other seven removed.

### PEE `passage_evidence_extraction` — findings

- F1 `messages/final_to_parent.py:86` (called at `:92`).
- F2 `messages/final_to_parent.py:98-105`: four of the six selectable fields raise (both cell families, current
  sheets, completed work).
- F3 `credit.py:89-93`; `task.py:366`; `task.py:318-325`, `:464`, `:544`, `:551`.
- F4 `task.py:373`.
- F5 `task.py:217`, `task.py:366`.
- F7 `tests/test_binding.py:100-109` asserts the `NotImplementedError`; `:125`, `:129` call `credit(summary, None)`
  on empty input; the task fixture (`:26`) has no `version`, which the old schema required.
- F8 Function accounting:
  - `goal.commissioned_task` -> `messages/read_from_parent.py:85-101`: `validate_schema(task, task_schema())` is
    dropped; kind, axis and credit unit are checked by hand, the version and the shape of `source_refs` and
    `examined` are not.
  - `credit.LiteratureTaskCredit.__call__` -> `credit.py:108-124`: the scope and target checks are dropped.
  - `grading/contextual_interpretation.execute_reasoning` -> `task.py:530-559`: present.
- F9 `messages/final_to_parent.py:33-44`: the finding has the model-written `source_claim`, `source_subject`,
  `qualification` and `target_correspondence`, and `assessment_refs`, but not the recorded `investigation_finding`
  of each assessment (TEE and SCI return it). The saved sheets (`summary['sheet_refs']`,
  `messages/internal_summary.py:134`) are in no returnable field.
- F10 `task.py:187-196` (`LibraryCallContext`).
- F12 `credit.py:3-5` says the old projector "lived in the old shared root, which is not read". It was in this
  episode's own old `credit.py` (class `LiteratureTaskCredit`, line 139 at `97308b94c`).

## A108 required literature processing, by rule

| Rule | State |
|---|---|
| Grader selected and subscoring sheet saved in the original action, before credit | Wired in all 8 `reason` tools through `literature_required_grading.execute`. Not runnable (F3). No test. |
| Typed `investigation_finding` retained | Enforced in the library (`literature_required_grading.py`, `evidence_assessment_source_finding_required`). Returned per assessment by HEAD, PEA, ESSI, SRA, SEE, TEE (`assessment_findings`) and SCI (`findings`). Not returned by PEE; dropped by SEE for the passage child (F9). |
| Original observation identities explicit for evidence counts | Only in the library (`literature/storage/literature_grading_storage.py:43-52`, key `a108_original_observation`). The aggregation cells that carry the counts cannot be returned by PEA, ESSI, SRA, SEE, TEE or PEE (F2). |
| Sheet saved even when the parent requests no cells | Follows from the coupling; not runnable (F3). |

## Totals by finding type

| Id | Finding | Episodes | Sites |
|---|---|---|---|
| F1 | `final_to_parent` always raises | 8 | 8 |
| F2 | Declared return fields that raise | 8 | 19 |
| F3 | Library not on custody: tools and credit fail | 8 | 8 (every tool; HEAD credit always, literature credit for assessments) |
| F4 | `except Exception` to a failed outcome | 8 | 8 |
| F5 | Silent default | 8 | 17 |
| F6 | Commission pre-check with feedback | 3 | 4 |
| F7 | Tests do not exercise the decide, action, credit and return paths | 8 | 8 test files |
| F8 | Old functions dropped or weakened | 8 | 11 of the 24 sampled |
| F9 | A108 processing not carried to the parent | 3 | 4 |
| F10 | Old binding-context shim | 8 | 8 |
| F11 | Selected field discarded | 3 | 3 |
| F12 | Leftover or false statement | 3 | 3 |

Notes on certainty. F6 rests on reading the provisional contract rule narrowly: it allows `action` to reject a
model answer that names an unheld record for the episode's own tool, and says a commission is never checked; SRA
and SEE, copies of the same file, do not make the check. F3 was confirmed by reading the library lines named and
`episode_runtime/store_scope.py` (`RecordReader` has no `db`, `_require` or `read_snapshot`); it was not run,
because no test reaches it.
