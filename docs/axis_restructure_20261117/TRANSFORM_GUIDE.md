# Transform guide: what the carry-over has to do (19 November 2026)

The first carry-over copied the shape (ten files, one class) and left the behaviour behind: wherever old code
touched the old Store it was marked blocked, stubbed with `NotImplementedError`, or tested only for form. The
audits (`AUDIT_CARRY_OVER_*.md`) found 0 of 146 audited episodes able to run. This guide replaces the first
instructions. The point of the carry-over is to **transform each old function into code that works in the new
paradigm and runs**, not to copy it and not to park it.

## Rules for every agent in every stage

1. **The new paradigm only.** `store.db` (the old Store's SQLite connection) is not part of the structure. Never
   write against it, wrap it, shim it, or add it to the custody store. Never import the `Store` class from the
   library. Records come in through the custody reader (`ctx.records`, `ctx.store`), results go out through the
   scoped store, a function's own tables are declared work tables (`TableDeclaration`, `store.table(T)`), and
   what cannot be said that way becomes a system operation with custody built in. The mapping for every old
   call is `carry_over_guide/store-access.md`; the API is `BINDING_CONTRACT.md`; the worked example is
   `episode_runtime/tests/`.
2. **No stubs, no parking.** No `NotImplementedError`, no `BLOCKED-*` note, no "unplaced" row, no
   `except Exception` that turns an error into an outcome, no `.get(x, default)` on a required setting, no
   service named that nothing implements. If an operation is missing, build it (in the system stage) or stop and
   report it as a blocker with the exact missing operation; do not work around it.
3. **Behaviour must run.** Every changed function has a real test that executes it on real records through the
   real runner or the real scoped store (no fakes, mocks, scripted stand-ins, no tests that assert a stub).
   A form-only test does not count. A function with no test that runs it is not done.
4. **Owner rules (AGENTS.md "How the system fails and stops")** hold everywhere: a wrong commission fails with
   its error (no pre-check, feedback, autofix); stopping belongs to the yield estimator only; the estimator reads
   `read_from_parent` output; a child declares its return fields and the parent selects them; credit and finding
   always returned; axis credit never bounded. No elapsed-time/token/turn cutoffs.
5. **Old behaviour is the source of intention** (each episode's own files at `97308b94c`, `git show
   97308b94c:<path>`; the old shared root is never read). Account for each old function in
   `runs/carry_over/functions/<episode>.tsv`: it lands in the episode file it serves or in a library function
   the episode calls. "Not carried" needs a reason that is a design decision of the owner, not a difficulty.
6. **Python only through the launcher:** `bash tools/one_workflow.sh --slot <slot> runs/<fresh-dir> -- env
   HOME=$PWD/runs/<fresh-dir>/home http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9
   PYTHONDONTWRITEBYTECODE=1 eatmydata .venv/bin/python -m pytest -p no:cacheprovider
   --basetemp=runs/<fresh-dir>/tmp <paths>`. The run directory must not exist beforehand. Never run
   `tests/test_bvbrc_proteome_host_integration.py`. Never touch `root/a110/tests/fixtures/genuine_fba360/`.
7. **The disk is a spinning disk shared by about ten agents:** read only the files you need; no recursive greps
   or finds over the repository or `runs/`.
8. Report in the form: to be done / being done / done, with counts. Say what failed.

## Stages, in order (each stage starts when the one before it passes its check)

### Stage 1: the system operations and services that are missing (Fable)
Build, in `episode_runtime/` (and its tests), each row of "No replacement yet" in `store-access.md`, and the
job services named in `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` "Not provided yet" (`job_access`, the estimate table,
the HPC ledger, native events, resource adapter, instruction libraries), as operations with custody built in,
journaled and replayable by the system. One agent owns `store_scope.py`/`work_tables.py` operations; a second owns
the job services in new files. Check: real tests for each operation through the real runner; the red test
`test_library_boundary.py` is the standing measure.

### Stage 2: the library, by family (Sonnet, one agent per module group)
For each library module group under `episode_support/` (families of `store-access.md` section 1: literature,
records, jobs, tools, acquisition, readers, grading, others; split large families by sub-folder), apply section 3
of `store-access.md`: give functions the scoped store or reader, replace each call per the table, declare tables,
delete the raw SQL, `sqlite_master` checks, run/episode/operation-key columns and the `*_operations` and
`*_received` ledgers. Check per module: no `store.db`, no `Store` import, no `store.path`, tests that run it.
The nine per-axis copies of the Store's material implementation (`records/documents/*/materials.py`) become one
copy with the Store, as the table says.

### Stage 3: the episodes, leaf first (Sonnet, one agent per episode, depth by depth)
For each episode, replace every stub and every blocked or unplaced item with working code that calls the stage-2
library; tests must run `decide`, `action`, every tool, `credit` on real records, `read_from_child`,
`internal_summary` and `final_to_parent` through the real runner to a returned result, and real model-run tests
(`@pytest.mark.model_run`) for each head. Fix every audit finding of its axis (`AUDIT_CARRY_OVER_<axis>.md`).

### Stage 4: the root, the checks, the audit (Fable)
Root episode (nine children, Π(1 + k·vᵢ)^wᵢ − 1, wᵢ = 1, k for ε = 0.5, accumulation estimator); delete
`root/axes.py` and every dangling name; zero collection errors; every test file matches `7e662ea29` or its change
is recorded; then an independent Fable audit of everything, which must find 0 stubs, 0 form-only tests.

## Shape first, no guards (owner, 19 November 2026)

This is Python. Do not add guards, defensive checks, validations of inputs that the structure already fixes,
`None` handling, type checks, try/except, or "what if" branches, and do not report their absence. A wrong input
raises its own error and that is the correct behaviour. The first and most important property is the shape: every
function in the file it belongs to, every call going through the new paradigm (custody reader, scoped store, work
tables, declared services, the three yield estimators), nothing duplicated, nothing carried only because the old
code had it. An audit finding of the kind "unguarded", "no check for", "can raise TypeError on ..." is not a
finding. Do not compare with the old code's behaviour except to find what an episode is meant to do.

## Old functions that existed only for the old runner are dropped (owner, 19 November 2026)

`final_to_parent(summary, completion, selection)` is a short function: it builds the return dictionary from the
summary and `completion['credit']`, and the episode's `RETURN_FORM` declares the fields; the system admits the
return against the form. Worked example: `episode_runtime/tests/fact_collection/messages/final_to_parent.py`.
An old `validate_report`, `validate_form`, `validate_received_report`, report-contract declaration, or any other
function whose only job was to feed the old runner's checks is old-runner machinery: it is dropped, not carried
and not stubbed. A field that cannot be expressed in a form (for example an old `null` value) is declared in a
form-expressible way or removed; selecting a declared field never raises. The same holds for `from_parent`,
`to_child` and `from_child` request/receipt steps: only what the worked examples show survives.

## goal.py creates a goal record (owner, 19 November 2026)

`goal.py` creates the episode's goal as a record, a fixed target. `task.py` and `credit.py` use that record
selectively. Nothing calls `goal.py`'s code; they use its output. The record does not have to be sent to the model
by `decide`, and an episode whose `decide` never shows the goal is correct. An audit finding of the form "the goal
never reaches the prompt" is not a finding. Do not name other uses of the goal.

## What a child returns is chosen and summarized by the child (owner, 19 November 2026)

Messages between episodes are heavily summarized, chosen and customized to the decision the parent has to make
next. A child does not offer up everything it holds and leave the parent to choose. The child filters and
summarizes itself: where it makes sense it summarizes trends (code that takes many outputs and returns a
summary of them, not the outputs one by one), and the records named in a `record_refs` field are the ones the
child chose for that parent's next decision. `final_to_parent` therefore builds a curated return from the
summary; it does not copy the summary or `internal_summary`'s contents into the return. Likewise `msg_to_child`
passes the child what the child needs for its task, and `read_from_child` takes from a result what the parent's
next decision needs. The declared return fields stay the child's menu; the parent's selection picks from the
menu; what the child puts in each selected field is the child's own summary. An audit finding of the form
"the child does not return every record / every item" is not a finding.

### The exemplar of a compressed return (owner, 19 November 2026)

`source_relevance_assessment` (A101) is the model of a return: the parent needs to know whether the child was
productive, whether it has stopped being productive, and so how many more times to launch it. The return is the
child's credit, the amount of progress, plus its minimal finding. Nothing else is returned, because nothing else
helps that decision. When writing or judging any `final_to_parent.py`, ask what the parent decides next and return
only what that decision needs. A return that offers many fields is correct only where the parent's next decision
needs them (for example, a launched job's handoff records).

## Controlled messages only: no free text between episodes (owner, 19 November 2026)

What passes from a child to its parent is controlled data only: numbers, integers, booleans, values from a fixed
vocabulary, and `record_refs`. No model-written paragraphs, no free-form text, no interpretation strings, no
"qualification" prose. A model-written paragraph that reaches the parent's model is an opportunity for prompt
injection and is a violation of the controlled-messaging principle, more severe than a return that is merely too
large. Any `Field('text', ...)` in a `final_to_parent.py` (or in the form of anything a child sends a parent) must
hold only a value the code controls (a fixed vocabulary or an id), never what the model wrote. The same holds for
`msg_to_child` (what the parent sends a child) and for what `read_from_child` shows the parent's model. The
child's own prose stays inside the child (its records and its own decisions), and the parent receives its credit,
counts, flags and chosen record refs.

Credit is the productivity signal (owner, 19 November 2026). Whether a child was productive, and whether it has
stopped being productive, is its credit and the trend of its credit. No returned field restates it: no boolean,
no enum, no judgement, no paragraph about how productive the child was.

Controlled messaging overrides everything (owner, 19 November 2026), including the A105/A108 requirement that an
assessment retain its typed `investigation_finding`: the finding stays a record inside the episode that wrote it;
the parent receives credit and record references, never the finding's text.

Refinement (owner, 19 November 2026): words are allowed in a defined field, such as an annotation, that has a
fixed meaning and a bounded length and does not invite a paragraph. What is forbidden is a field that invites
open-ended prose (interpretation, qualification, relevance explanation, "why" text). A text field in a return form
must be a named annotation with one stated meaning and a length bound, or a fixed vocabulary.

## The investigation finding (owner, 19 November 2026)

An A105/A108 `investigation_finding` is evidence for an annotation: its type and its strength, as controlled
features that code reads from the grading (subscoring) sheet: for example the number of assays, the statistical
deviation or noise, the signal. Numbers, counts and fixed-vocabulary values; no source claim, subject or
qualification prose. The sheet stays a record in the episode that graded it; the parent receives the features and the
sheet's reference. Which features exist for a grader is whatever its subscoring sheet defines.

No open fields (owner, 19 November 2026; replaces the earlier allowance of an annotation field)
Every field that passes between episodes has a controlled answer set that code can validate: a number in a
range, a count, a boolean, a value from a fixed vocabulary, or a record reference. One field holds one thing.
There is no open text field and no field that gathers evidence into one place. A free-form paragraph in a return
(`interpretation`, `qualification`, `relevance`, `annotation`, and every similar `Field('text', ...)`) is converted
into a set of such fields. A text field is allowed only where its values are a fixed vocabulary that the form
validates.

An annotation field is allowed (owner, 19 November 2026). An annotation is a gene, function or product ID or name:
a controlled name that comes from a looked-up list. It is a real data field, different from free text, and the
"no open fields" rule above does not forbid it. The forbidden thing is free text (paragraphs, explanations,
interpretations), not annotations.

Annotation values are not looked up (owner, 19 November 2026): an annotation conceptually comes from a list of
controlled names, but no code has to look it up or verify it against that list. The form declares the field as an
annotation and takes the value as given.

## The investigation-finding feature tables are adopted (owner, 19 November 2026)

The owner formulated the grading sheets by hand and does not review the feature tables again. Stage 3 uses
`INVESTIGATION_FINDING_FEATURES_<axis>.md` (a101 to a108, a110) as the investigation-finding fields: they are copied
from the sheets' own schemas. Where a table offers an alternative for the owner to decide, the choice is:
A110 `evidence_type` comes from the cited observation's own kind (code reads it; the model never writes it);
A105 carries no annotation field of its own (the annotation is the reference to the assertion record).
Anything the tables leave out stays out. Do not ask the owner to re-confirm a feature.
