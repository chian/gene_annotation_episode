# Audit of the carry-over: axis A105 (19 November 2026)

Read-only audit of every episode folder under `gene_annotation_episode/episodic_workflow/root/a105/`, against
`AGENTS.md`, `BINDING_CONTRACT.md`, the reference episodes `episode_runtime/tests/fact_collection/` and
`fact_extraction/`, and each episode's own files at `97308b94c` (read with `git show`). No code or test was changed.

**Result: 8 episodes audited, 0 PASS, 8 with findings.**

The form is right everywhere (file set, one `EpisodeBinding` class, forms, yield controller). The behaviour is not
carried: in every episode the tools, most of the credit and part of the summary and return end in a raise
(`library_not_carried`, `NotImplementedError`) or in a call of library code that still needs the raw Store. No test
runs `decide`, `action`, `internal_summary` or a tool, so the 86 passing tests do not show this.

## Path prefixes

| Short | Episode folder (below `gene_annotation_episode/episodic_workflow/root/a105/`) |
|---|---|
| `EAE/` | `experimental_activity_evidence/` |
| `PEA/` | `EAE/published_evidence_assessment/` |
| `ESSI/` | `PEA/evidence_search_strategy_improvement/` |
| `SRA/` | `ESSI/source_relevance_assessment/` |
| `SEE/` | `SRA/source_evidence_examination/` |
| `PEE/` | `SEE/passage_evidence_extraction/` |
| `SCI/` | `SEE/source_coverage_improvement/` |
| `TEE/` | `SEE/table_evidence_extraction/` |

## What holds in all 8 episodes

- **File set (check 1).** Exactly the ten files (eight for the three leaves), `__init__.py`, `tests/`, child folders.
  No other module, no non-Python file.
- **`episode.py` (check 2).** One class inheriting `EpisodeBinding` only; no import of another episode folder
  (absolute or relative); no table of bindings.
- **Stopping (check 3).** No stopping rule besides the yield controller; no time, token, turn or unit cutoff.
  `decide` and `action` return only `ModelRequest`, `ToolCall`, `ChildCall`.
- **Store (check 3).** No episode file touches `store.db` or the raw `Store` itself. (The library functions they
  call do; see the stub findings.)
- **`yield_estimator.py` (checks 3, 4).** Reads only the parent input; returns a `yield_control` controller that
  matches the old method: accumulation for the head (old projector `yield_method = 'accumulation'`); for the seven
  literature episodes accumulation for `verified_source_leads` and completion with target `credit_unit` x answers
  otherwise (old `_FiniteLiteratureYieldController`).
- **Credit scale (check 4).** No bound, clamp or rescale of credit anywhere.
- **Return form (check 3).** `credit` and `finding` are required fields; the parent selects in `msg_to_child`; the
  field names each parent selects are declared by its child (checked by reading both sides).
- **Typed `investigation_finding` (A105 rule).** Every episode reads `source_claim`, `qualification` and `status`
  from the committed assessment's `investigation_finding` into its summary and returns them in `finding`
  (`EAE/messages/internal_summary.py:46-49`, `PEA/...:156-159`, `SEE/...:2465-2468`, `SCI/...:166-183`,
  `TEE/...:35-40`).
- **Old-runner names (check 5).** No `recorder`, `recall`, `SourceEnd`, `Done` or old runner hook in code.

## Tests run

`bash tools/one_workflow.sh --slot auda105 runs/audit_a105_1 -- env HOME=... http_proxy=... https_proxy=...
PYTHONDONTWRITEBYTECODE=1 eatmydata .venv/bin/python -m pytest -p no:cacheprovider --basetemp=runs/audit_a105_1/tmp
gene_annotation_episode/episodic_workflow/root/a105 -q`: **86 passed in 2.20 s**.

No test uses a mock or a fake. What the tests call, counted in the test files:

| Episode | tests | `decide` | `action` | `internal_summary` | a tool | `credit(...)` | `final_to_parent(...)` | runner |
|---|---|---|---|---|---|---|---|---|
| EAE | 12 | 0 | 0 | 0 | 0 | 0 | yes | 0 |
| PEA, ESSI, SRA | 13 each | 0 | 0 | 0 | 0 | 2 task kinds of 6 | yes | 0 |
| SEE | 11 | 0 | 0 | 0 | 0 | 2 of 6 | yes | 0 |
| PEE | 9 | 0 | 0 | 0 | 0 | 2 of 6 | yes | 0 |
| SCI | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| TEE | 10 | 0 | 0 | 0 | 0 | 2 of 6 | yes | 0 |

Every summary passed to `credit` or `final_to_parent` is a dict written by hand in the test.

## Findings by episode

Rule names: **R1** wrong commission just fails (no pre-check, no feedback path); **R4-stub** real code, no stub or
placeholder; **R4-source** carried from the episode's own old files; **R5-except** no try/except that hides errors;
**R5-default** no silent default; **R6** tests exercise decide/action/credit/final_to_parent; **R7** every old
function ends in the scheme as behaviour; **A105** grader and subscoring sheet before credit.

### 1. EAE `experimental_activity_evidence` (head): findings

1. **R4-stub, credit.** `EAE/credit.py:59-61` raises `RuntimeError('library_not_carried:project_finding_progress...')`
   whenever the Episode holds one assessment. `EAE/credit.py:51-58` returns a hand-written copy of the library's
   empty result instead of calling it. `EAE/messages/internal_summary.py:84` calls the same function, so the summary
   raises as soon as a child returns an assessment.
2. **R4-stub, tools.** `EAE/task.py:383`: all 30 registry tools raise before `A105ToolRegistry` is built. Lines
   384-392 after it cannot be reached.
3. **R4-stub and A105, `reason`.** `EAE/task.py:453` raises before `execute_required_grading`; `:440` likewise. The
   grader-and-sheet step is written but cannot run.
4. **A105.** `EAE/task.py:460`: `authorize_source_access=lambda ref, representation: None` replaces the source
   authorization of the grading call with one that allows everything.
5. **R4-stub, return.** `EAE/messages/final_to_parent.py:96-97` raises `NotImplementedError` when
   `experimental_activity_evidence_results` is selected, a field the form declares (`:66-67`). The head selects
   exactly that field from its own kind when the model sets `request_results` (`EAE/messages/msg_to_child.py:91-92`),
   so that commission cannot return.
6. **R1.** `EAE/task.py:734-737`: `action` checks each record named in a child commission with `records.holds` and
   answers the model with `Rejected` feedback. That is a check of a commission with a feedback path.
7. **R5-except.** `EAE/task.py:391` (`except Exception` to a failure outcome); `EAE/task.py:742` (`KeyError` and
   `TypeError` of the episode's own code become model feedback).
8. **R5-default.** `EAE/task.py:679` `ctx.settings.get('knowledge_library_directory')`.
9. **R6.** `EAE/tests/test_binding.py`: no `decide`, `action`, `internal_summary`, tool or `credit(...)` call.
   `:147-151` names itself "the credit is real code" and checks only that the text `NotImplementedError` is absent
   from `credit.py` (the stub raises `RuntimeError`). `:129-130` asserts the `NotImplementedError` of finding 5.
10. **R7.** Sample: `ScientificOperations._proposed_selection` is in `EAE/task.py:406-434`;
    `to_child_published_evidence_assessment.prepare_request` is in `EAE/messages/msg_to_child.py:98-110`;
    **`ScientificReport.facts`** (own process result merged with the children's) is nowhere: nothing builds a
    process result, and the docstring of `EAE/messages/internal_summary.py:11-12` says it is carried.
    `EAE/messages/final_to_parent.py:90-98` is described as "the old `validate_report` body" and is not.

### 2. PEA `published_evidence_assessment`: findings

1. **R4-stub, credit.** `PEA/credit.py:114` (assessment answers), `:139`, `:164`, `:191` via `:53` (measurement,
   experiments, assembly) raise `library_not_carried`. Credit runs for 2 of the 6 task kinds.
2. **R4-stub, tools.** `PEA/task.py:422` (all 28 access and acquisition tools), `:486` via `:233` (all 35 population
   tools), `:386`, `:389`, `:434` (source authorization on the population route). Only `report` runs.
3. **R4-stub and A105, `reason`.** `PEA/task.py:510` raises before `execute_required_grading`; `:496` likewise.
4. **R4-stub, summary and return.** `PEA/messages/internal_summary.py:115` raises for the first requested cell
   family; `:132` raises on every summary when `requested_assay_grading_components` is set.
   `PEA/messages/final_to_parent.py:130-131`: the declared field `literature_completed_work` is never produced
   (`KeyError`).
5. **R1.** `PEA/task.py:940-944`: `records.holds` on the records of a child commission, with `Rejected` feedback.
6. **R5-except.** `PEA/task.py:430`, `:953`.
7. **R5-default.** `PEA/task.py:319`, `:321`, `:381`, `:432`, `:894`, `:906` (`settings.get(..., False)`; the grading
   flag defaults to true at `:321`).
8. **R6.** `PEA/tests/test_binding.py`: no `decide`, `action`, `internal_summary` or tool. `:160` is the same text
   check as EAE finding 9.
9. **R7.** Sample: `credit.validate_lead` is in `PEA/task.py:266-297`; `goal.validate_commission` is in
   `PEA/messages/read_from_parent.py:158-170`; **`LiteratureSummary._received_fact_display_context`** (and the ten
   other display contexts) exist only as a "not carried" note at `PEA/messages/internal_summary.py:19-29`.

### 3. ESSI `evidence_search_strategy_improvement`: findings

Same code as PEA apart from names (compared with `diff`). Same nine findings at these lines:

1. **R4-stub, credit.** `ESSI/credit.py:114`, `:139`, `:164`, `:191` via `:53`.
2. **R4-stub, tools.** `ESSI/task.py:421`, `:485` via `:232`, `:385`, `:388`, `:433`.
3. **R4-stub and A105, `reason`.** `ESSI/task.py:509`, `:495`.
4. **R4-stub, summary and return.** `ESSI/messages/internal_summary.py:113`, `:130`;
   `ESSI/messages/final_to_parent.py:132` (`literature_completed_work` raises `library_not_carried`).
5. **R1.** `ESSI/task.py:939-943`.
6. **R5-except.** `ESSI/task.py:429`, `:952`.
7. **R5-default.** `ESSI/task.py:318`, `:320`, `:380`, `:431`, `:893`, `:905`.
8. **R6.** `ESSI/tests/test_binding.py` as PEA; text check at `:159`.
9. **R7.** As PEA; the note is at `ESSI/messages/internal_summary.py:18-28`.

### 4. SRA `source_relevance_assessment`: findings

Same code as ESSI apart from names and the page fields. Same nine findings:

1. **R4-stub, credit.** `SRA/credit.py:114`, `:139`, `:164`, `:191` via `:53`.
2. **R4-stub, tools.** `SRA/task.py:421`, `:485` via `:232`, `:385`, `:388`, `:433`.
3. **R4-stub and A105, `reason`.** `SRA/task.py:509`, `:495`.
4. **R4-stub, summary and return.** `SRA/messages/internal_summary.py:113`, `:130`;
   `SRA/messages/final_to_parent.py:130-131` (`KeyError` for `literature_completed_work`).
5. **R1.** `SRA/task.py:939-944`.
6. **R5-except.** `SRA/task.py:429`, `:953`.
7. **R5-default.** `SRA/task.py:318`, `:320`, `:380`, `:431`, `:893`, `:905`.
8. **R6.** `SRA/tests/test_binding.py` as PEA; text check at `:159`.
9. **R7.** As PEA; the note is at `SRA/messages/internal_summary.py:18-28`.

### 5. SEE `source_evidence_examination`: findings

1. **R4-stub, credit.** `SEE/credit.py:114`, `:139`, `:164`, `:191` via `:53`.
2. **R4-stub, tools.** `SEE/task.py:741` (10 access tools), `:800` via `:523` (35 population tools).
3. **R4-stub and A105, `reason`.** `SEE/task.py:824`, `:810`.
4. **R4-stub, summary and return.** `SEE/messages/internal_summary.py:2423` (cell families), `:2440` (assay grading
   requested), `:2157`, `:2208`, `:2267` (display contexts for requested families);
   `SEE/messages/final_to_parent.py:130-131` (`KeyError` for `literature_completed_work`).
5. **R4-stub, placeholder objects.** A class `_NotCarried` whose every use raises: `SEE/task.py:214-228` with three
   names bound to it at `:281-283`; `SEE/messages/internal_summary.py:49-63` with thirteen names at `:168-179` and
   `:2114`.
6. **R7, code parked without being wired.** `SEE/task.py:231-485` ("generated for task": copies of thirteen
   library helpers; the ten I looked up by name are called from nowhere in the episode). `SEE/messages/internal_summary.py:66-2020` (about 1,950
   lines of the old prompt renderers; the file's own docstring `:17-21` says "the renderer is not wired into
   `decide`"). `SEE/messages/internal_summary.py:2117-2125` `prepare_completed_work`, marked "NOT WIRED", calls a
   placeholder. These functions are counted as placed and do nothing.
7. **R1.** `SEE/messages/msg_to_child.py:48-51`: `msg_to_child` checks the page the model named against the
   parent's and raises. It fails the run and gives no feedback, but it is a check of the commission before the
   child is built. (`SEE/task.py:1165-1166` correctly passes a child selection unchecked.)
8. **R5-except.** `SEE/task.py:749`, `:1175`.
9. **R5-default.** `SEE/task.py:609`, `:611`, `:1116`, `:1128`.
10. **R6.** `SEE/tests/test_binding.py`: no `decide`, `action`, `internal_summary` or tool; text check at `:150`.
11. **R7.** Sample: `SourceReferences._within_source` is in `SEE/task.py:662-675`; `credit.validate_lead` in
    `SEE/task.py:556-587`; **`decision_presentation.prepare_completed_work`** is finding 6.

### 6. PEE `passage_evidence_extraction` (leaf): findings

1. **R4-stub, credit.** `PEE/credit.py:109`, `:134`, `:159`, `:186` via `:49`.
2. **R4-stub, tools.** `PEE/task.py:397` (10 access tools), `:456` via `:184` (35 population tools).
3. **R4-stub and A105, `reason`.** `PEE/task.py:480`, `:466`.
4. **R4-stub, summary and return.** `PEE/messages/internal_summary.py:103`, `:120`;
   `PEE/messages/final_to_parent.py:131-132` (`literature_completed_work` always raises).
5. **R5-except.** `PEE/task.py:405`, `:816`.
6. **R5-default.** `PEE/task.py:269`, `:271`, `:765`, `:776`.
7. **R6.** `PEE/tests/test_binding.py`: no `decide`, `action`, `internal_summary` or tool; text check at `:128`.
8. **R7.** Sample: `validate_lead` is in `PEE/task.py:217`; `_within_source` in `PEE/task.py:320`;
   **`goal.validate_commission`** is dropped (`PEE/messages/read_from_parent.py:15-19` says so; only the
   duplicate-experiment test is kept at `:157-160`, the requested-metrics and requested-measurement tests are
   gone). The display contexts are a note only (`PEE/messages/internal_summary.py:15`).

### 7. SCI `source_coverage_improvement` (leaf): findings

Written in another style: no `library_not_carried` raise. It calls the raw-Store library directly ("the calls stay
as written", `SCI/task.py:21-22`). `ScopedStore` and `RecordReader` offer no `.db`, so these calls cannot run. I
read this from the code; I did not execute it.

1. **R4-stub, return: the episode can never return.** `SCI/messages/final_to_parent.py:486`: `validate_report` ends
   in an unconditional `raise NotImplementedError('validate_form_not_built:a105')`, and `final_to_parent` always
   calls it (`:493`). `:447` raises for `literature_completed_work`.
2. **R4-stub, tools (unmarked).** `SCI/task.py:389` `A105ToolRegistry(ctx.store, ...)` (its constructor runs
   `store.db.execute`); `:356`, `:402`, `:441`, `:623` build `<Repository>(store, run_id)`; `:633` calls
   `required_grading.execute`, which passes `account_owner=` to `commit_reasoning`.
3. **R4-stub, credit (unmarked).** `SCI/credit.py:416-420` (`FindingValidity`, `target_eligible`), `:459`, `:482`,
   `:486`, `:507-509` (repositories and `current_sheet_refs` over `store.db`). Credit runs for leads and screening,
   and returns 0 without a library call while no sheet is held (`:447-452`).
4. **R4-stub, summary (unmarked).** `SCI/messages/internal_summary.py:376`, `:433`, `:446`, `:456`.
5. **A105, grading is optional.** `SCI/task.py:192-203`: `assay_grading_population` defaults to false.
   `SCI/task.py:240-244` then offers `reason` without `evidence_processing`, and `:630-632` commits with plain
   `store.commit_reasoning`, with no grader and no sheet. `SCI/credit.py:536-541` gives credit for such an
   assessment. The old episode had the same switch; the other A105 literature episodes made grading unconditional.
6. **A105, no sheet check at return.** `SCI/messages/final_to_parent.py:419-437` returns assessments without the
   `required_grading_sheet_not_saved` test the other episodes have.
7. **R5-except.** `SCI/task.py:396`: `except Exception` around `registry.execute_async` turns the library's own
   `store.db` errors into ordinary failed outcomes that enter the iterator. `SCI/task.py:748`.
8. **R5-default.** `SCI/task.py:192`, `:197`, `:702`, `:703`.
9. **Old-runner operand.** `SCI/credit.py:307-313` rebuilds the old binding context (`LiteratureContext` with role
   `literature_ordered` and a role path) to feed the library.
10. **R4-source.** `SCI/goal.py:4-5`: `GOAL` is a new sentence, not the old instruction text (that text is in
    `SCI/messages/internal_summary.py:50-62`).
11. **R6.** `SCI/tests/test_source_coverage_improvement_binding.py`: 5 tests; none calls `decide`, `action`,
    `credit`, `internal_summary`, a tool or `final_to_parent`. Finding 1 is therefore not seen by any test.
12. **R7.** Sample: `validate_lead` is in `SCI/credit.py:354-388`; `_population_routes` in `SCI/credit.py:279-289`;
    **`to_parent.validate_report`** is finding 1.

### 8. TEE `table_evidence_extraction` (leaf): findings

1. **R4-source.** `TEE/credit.py:3-6` and `TEE/task.py:5-9` say the code was written from the intent record because
   "the git history of 97308b94c is not readable in this checkout". It is readable (`git show
   97308b94c:.../table_evidence_extraction/credit.py`, 289 lines). The episode is a re-expression of a note, not a
   carry of its old files.
2. **R4-stub, credit.** `TEE/credit.py:54` raises `NotImplementedError` for measurement, experiments and assembly.
   `TEE/credit.py:97-101` calls `FindingValidity` and `target_eligible` (raw Store, unmarked).
3. **R4-stub, tools.** `TEE/task.py:274-275` raises `NotImplementedError` for `image.view`, `source.xlsx.sheets`
   and `source.xlsx.rows`, which the episode offers to the model (`:98-104`, `:192-194`). For a table episode these
   are its own tools. `TEE/task.py:276` and `:404-410` call the raw-Store registry and grading repository unmarked.
4. **A105, grading dropped with a source lead.** `TEE/task.py:383-399`: when `source_lead` is present the commit is
   plain `store.commit_reasoning` (`:391`), with no grader and no sheet. The old code ran the required grading
   inside that transaction.
5. **A105, no sheet check at return.** `TEE/messages/final_to_parent.py:85-100`.
6. **R4-stub, return.** `TEE/messages/final_to_parent.py:81`: `cells` raises `NotImplementedError` for all three
   declared cell families.
7. **Return carries no records.** `TEE/messages/final_to_parent.py:55-69`: the form has no `record_refs` field, so
   the assessments and sheets the episode commits never reach its parent
   (`SEE/messages/read_from_child.py:27-28`, `:38-39` return empty lists for this slot). The parent's credit cannot
   count them.
8. **R5-except.** `TEE/task.py:283` (as SCI finding 7), `:481`.
9. **R5-default.** `TEE/task.py:276` `settings.get('tool_registry', {})`, `:434`.
10. **Old-runner operand.** `TEE/task.py:400-403` rebuilds `LiteratureContext` with role `literature_table`.
11. **R6.** `TEE/tests/test_binding.py`: no `decide`, `action`, `internal_summary` or tool.
12. **R7.** Sample: the sheet-key lock of `_tool_arguments` is in `TEE/task.py:247-259`; **`credit.measured_answers`**
    is finding 2; **the population route** (`LiteratureOperations.execute` population branch,
    `_materialize_text_arguments`, 35 operations in the old `task.py`) is absent and declared "not built"
    (`TEE/messages/internal_summary.py:8-11`, `TEE/messages/final_to_parent.py:10-11`).

## A105 "Required literature evidence processing": summary

| Episode | Grader and sheet in the `reason` unit | Runs today | Sheet test before return | Typed finding retained |
|---|---|---|---|---|
| EAE | always (`task.py:463-468`) | no, raises at `:453` | yes, `final_to_parent.py:94-95` | yes |
| PEA | always (`task.py:772-800`) | no, raises at `:510` | yes, `:114-115` | yes |
| ESSI | always | no, `:509` | yes, `:115-116` | yes |
| SRA | always | no, `:509` | yes, `:114-115` | yes |
| SEE | always (`task.py:1014-1040`) | no, `:824` | yes, `:114-115` | yes |
| PEE | always | no, `:480` | yes, `:114-115` | yes |
| SCI | only when the setting is true; default false (`task.py:192-203`, `:630-632`) | no (raw-Store library) | **no** | yes |
| TEE | not with a `source_lead` (`task.py:390-391`) | no (raw-Store library) | **no** | yes |

The sheet test where it exists is coarse: one saved sheet satisfies any number of assessments.

## Totals by finding type

| Finding type | EAE | PEA | ESSI | SRA | SEE | PEE | SCI | TEE | Total |
|---|---|---|---|---|---|---|---|---|---|
| Tools stubbed or blocked (raise at call, or raw-Store library call) | 2 | 4 | 4 | 4 | 3 | 3 | 3 | 3 | 26 |
| Tests do not exercise the paths, or pin or evade a stub | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 16 |
| Summary or return stubbed; declared return field cannot be produced | 1 | 2 | 2 | 2 | 3 | 2 | 3 | 1 | 16 |
| try/except that hides errors | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 16 |
| A105 grader and sheet step not runnable, optional, dropped or unchecked | 2 | 1 | 1 | 1 | 1 | 1 | 3 | 3 | 13 |
| Credit not computable (stub or blocked) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 9 |
| Old function absent as behaviour (of 3 sampled per episode) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 9 |
| Silent default of a setting | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 8 |
| Check of a commission (with model feedback, or in `msg_to_child`) | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 5 |
| Not carried from the episode's own old files | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 3 |
| Old-runner operand rebuilt (`LiteratureContext`) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| Unwired code parked in an episode file | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 2 |
| Return carries no records in custody | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| **Total** | 14 | 15 | 15 | 15 | 17 | 13 | 18 | 19 | **126** |

Counting: one finding per distinct defect per episode; a defect with several line sites counts once. The stub rows
together are 51 of the 126.

## Not checked

- No tool, `decide`, `action` or `internal_summary` was executed: the failures of the unmarked raw-Store calls in
  SCI and TEE are read from the code (`episode_runtime/store_scope.py` offers no `.db`), not observed.
- Function accounting is a sample of 3 old functions per episode (24 of about 4,070 rows in
  `runs/carry_over/functions/a105__*.tsv`); 9 of the 24 are not present as behaviour.
- The library under `episode_support/` was read only where an episode calls it.
