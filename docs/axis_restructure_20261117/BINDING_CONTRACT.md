# Episode binding contract (19 November 2026, after the third system-type audit and the decisions on its questions)

An episode is written in exactly one way: a class that inherits directly from `episode_runtime.EpisodeBinding`,
with its members supplied by the episode's own files. The class carries the system behaviour (request
admission, the decision loop, tool units, child commissions, controller inputs, the result). The generic runner
(`episode_runtime/`) links a registry of these classes, gives each Episode its recording services, and records
everything that happens in the run journal. The runner also does custody and replay. Episodes contain no
recording, replay or custody code. They name the records they pass, and they read and write records only through
the objects they are handed.

## The rules of the system

These are the owner's rules (`AGENTS.md`, "How the system fails and stops"). Nothing in this contract adds to them.
The five questions the third audit raised are answered ("Decisions of 19 November 2026", at the end): two follow
from these rules (T1: nothing but the yield controller ends an Episode; T3: credit and finding are in every
return). Three are **provisional** (T5: a pass carries only the records named; T10: what a decision reads from a
service is recorded; an `action` may reject a model answer that names an unheld record). Each provisional
decision is implemented in one place, which that section names, so that it is easy to change.

1. **A wrong commission fails.** A parent knows how to call its child: that is what writing its `msg_to_child.py`
   and its prompt is for. A commission that selects a field the child does not declare as selectable, that the
   child's assignment form does not admit, or that passes a record the parent does not hold, raises its error
   (`FormError`, `CustodyError`) and the run fails with that error message. Nothing catches, checks ahead, repairs
   or reports the error back to the model, and nothing at link time compares one episode's names with another's.
2. **Stopping is the yield estimator's alone.** Every unit's credit goes to the episode's yield controller, and
   the controller alone decides when the Episode stops. There is no other stopping rule: no task ends its own
   Episode (`decide` and `action` produce only units), and the system has no action that ends one. Whether a
   lookup, a wait or a check earns credit is that episode's own `credit.py` and settings.
3. **Custody only.** No episode function and no library function reads or writes the Store, its tables or its
   files directly. Everything goes through the custody-scoped store the system hands the episode, or through an
   operation of it that has custody built in.
4. **`yield_estimator.py` reads what `read_from_parent.py` produced**, never the raw assignment.
   `read_from_parent.py` is the only place an assignment is read.
5. **A child declares every field it can return; the parent selects** which of the selectable ones it wants, in
   `msg_to_child.py`. Credit and finding are always returned: every episode's own `return_form` declares `credit`
   and `finding` as required fields (a class-definition check), and the system hands the Episode's credit to
   `final_to_parent`.

## Where things live

| Package | Owns |
|---|---|
| `method_loop/` (vendored loop, local patch `generic_loop_outcomes_forms_v10` in `LOCAL_PATCHES.json`) | The generic Episode loop (`Episode`, `EpisodeView`, `Leaf`, `ChildEpisodeUnit`, `ChildProjection`, the `Controller` protocol and `ControllerRuntime`), the declaration record (`EpisodeBindingDeclaration`), the typed forms (`forms.py`: `RecordForm`, `Field`, `DeclaredField`, `ChoiceField`, `SubsetField`, `FormError`, `Commission`) and `jsonvalue.py`. No Store, no application, no episode files, no detached execution. |
| `episode_runtime/` | **The Episode type** (`episode_type.py`: `EpisodeBinding`, `ModelRequest`, `ToolCall`, `ChildCall`, `Rejected`, `ChildMessage`). Linking a registry below any entry (`runner.py`: `link`, `resume`, and `EpisodeRun` with `run`, `next_decision` and `run_unit`; `bindings.py`: `BindingRegistry`), the run journal (`journal.py`: `RunJournal`), the recording services (`recording.py`: model calls, custody, unit attempts, `DecisionContext`, `UnitContext`; `progress.py`: `ProgressClock`, `DecisionClock`), the Store under custody (`store_scope.py`: `RecordReader`, `ScopedStore`; `work_tables.py`: `TableDeclaration`, `TableReader`, `ScopedTable`; `scratch.py`: `ScratchDirectory`, the files of a tool unit's own; `store_ledger.py`: the system's own tables in the Store file, which are the run's claim of its id and the receipts of what units produced), the services channel (`services.py`: the services themselves for tools, read handles with recorded reads for decisions; `work_cache.py`: `WorkCache`, the cache a run may give its episodes as a service), the collaborator check (`collaborators.py`). |
| `yield_control/` | The three yield controllers (`AccumulationYieldController`, `BoundedQualityYieldController`, `CompletionYieldController`) and the version of the progress receipt they read (`PROGRESS_TIME_VERSION`). It imports nothing from the runner. An episode's `yield_estimator.py` returns one of the three; nothing else decides continuation. |
| `episode_support/` | The library, by function. `jobs/native_event_ledger.py` (`NativeEventLedger`) is the ledger of detached local jobs' event targets and publications; it is job support and not part of the loop. It is meant to be reached as a declared service; today no service wraps it and 21 library modules import it directly. |

`episode_runtime.EPISODE_API` names what an episode's files and the library may import from `episode_runtime`:
`ChildCall`, `ChildMessage`, `CustodyError`, `DecisionClock`, `DecisionContext`, `EpisodeBinding`,
`ModelRequest`, `RecordReader`, `Rejected`, `ScopedStore`, `ScopedTable`, `ScratchDirectory`, `ServiceReader`,
`TableDeclaration`, `TableReader`, `ToolCall`, `UnitContext`, `WorkTableError`. Forms come from `method_loop`,
controllers from `yield_control`.

The three system packages (`method_loop/`, `episode_runtime/`, `yield_control/`) are top-level packages of the
repository, beside `gene_annotation_episode/`. They are not inside `episode_support/`.

## The ten files and the members they supply

Each episode folder holds `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py` and
`messages/` with `read_from_parent.py`, `msg_to_child.py`, `read_from_child.py`, `internal_summary.py`,
`final_to_parent.py` (an episode without children has no `msg_to_child.py` or `read_from_child.py`).

| File | Member | Exact form |
|---|---|---|
| `goal.py` | `binding_path` | text: lowercase segments joined by `/`; the episode's package path must end with it (`a/b` in package `....a.b`) |
| `goal.py` | `goal`, `unit`, `result` | non-empty text |
| `task.py` | `child_slots` | `{slot: child binding_path}`; slot names `[a-z][a-z0-9_]*`; several slots may name one child; a slot may name the episode's own binding path |
| `task.py` | `tools` | `{name: tool}`; names `[a-z][a-z0-9_]*`; each `def tool(arguments, ctx)` or `async def tool(arguments, ctx)`, defined in `task.py` |
| `task.py` | `services` | tuple of the distinct service names its functions need (`()` when none) |
| `task.py` | `decide` | `def decide(summary, feedback, ctx)` returns `ModelRequest(role, instructions, context, output_schema)`, `ToolCall(name, arguments)` or `ChildCall(slot, arguments)`; nothing else (it cannot end the Episode) |
| `task.py` | `offered_actions` | `def offered_actions(summary, ctx)` returns the list of the action types this decision offers, built from the same functions `decide` offers the model with: the name of a tool, the slot of a child, `reason` for a reasoning commit (exactly the names a unit is recorded under) |
| `task.py` | `action` | `def action(response, summary, records, ctx)` returns `ToolCall` or `ChildCall`, or raises `Rejected(feedback)` |
| `credit.py` | `credit` | `def credit(summary, records)` returns a finite number (never bounded, clamped or rescaled by the system) |
| `credit.py` | `ceiling` | `def ceiling(summary, records, action_type, arguments, ctx)` returns the most `credit` can rise if the action `action_type` with `arguments` is the next unit (`arguments` `None`: over every arguments the action type can take now): a finite number >= 0, or `method_loop.UNBOUNDED` returned deliberately for an action whose gain has no finite upper bound. No default: the episode answers for every offered action. The system asks for every offered action after `decide`, again for the chosen action after `action`, and raises `episode_ceiling_exceeded:<episode>:<action type>:<rise>:<ceiling>` when the credit's rise over the unit is above the ceiling by more than 1e-9; the journal's `ceilings` table records the offered ceilings, the chosen one and the rise |
| `yield_estimator.py` | `yield_controller` | `def yield_controller(initial_credit, settings, parent_input)` returns one of the three `yield_control` controllers |
| `messages/read_from_parent.py` | `assignment_form` | a `RecordForm` |
| `messages/read_from_parent.py` | `read_from_parent` | `def read_from_parent(assignment, message)` returns the parent input (closed JSON) |
| `messages/msg_to_child.py` | `msg_to_child` | `def msg_to_child(slot, arguments, summary)` returns `ChildMessage(objective, message, assignment, selection)` |
| `messages/read_from_child.py` | `read_from_child` | `def read_from_child(slot, result, summary, records)` returns the report (closed JSON) |
| `messages/internal_summary.py` | `internal_summary` | `def internal_summary(view)` returns the summary (closed JSON) |
| `messages/final_to_parent.py` | `return_form` | a `RecordForm` with the required fields `credit` (type `number`) and `finding` (any type the episode declares) |
| `messages/final_to_parent.py` | `final_to_parent` | `def final_to_parent(summary, completion, selection)` returns the result |
| `episode.py` | the class | exactly one `class X(EpisodeBinding)` in the module `<package>.episode`, assigning each member above from its file |

The parameter names are part of the form (`episode_type.SIGNATURES`). `settings` of `yield_controller` is a copy of
the episode's own entry of the `continuation` collaborator; `parent_input` is exactly what `read_from_parent`
returned for this commission.

`X().declaration(controller)` returns the generated `EpisodeBindingDeclaration`. It is a description, validated at
every controller build; its progress and stopping text are derived from the kind of the controller the episode
built (accumulation: credit accumulates without limit; bounded quality: a maximum; completion: a finite target).

### Class definition checks

Defining the class (importing `episode.py`) raises `TypeError` for each of these:

- a base other than `EpisodeBinding` alone (an episode cannot inherit from another episode); a metaclass; a class
  keyword;
- any dunder the episode defines (`__init__`, `__init_subclass__`, `__getattr__`, `__slots__`, annotations, ...;
  only `__module__`, `__qualname__`, `__doc__` and the names Python adds are allowed);
- a missing member; a member that is not one of the table; an override of a system member (`grain_name`,
  `declaration`, `parent_input`, `entry_request`, `build_controller`, `build_episode`,
  `restore_controller_input`, private helpers);
- child members without child slots, or child slots without child members;
- a class not defined in a module named `<package>.episode`; a second episode class in the same `episode.py`,
  whatever its name (also when it reuses the first one's name); a `binding_path` the package path does not end
  with;
- a function member, or a tool, that is not a module-level function of its own file: a class instance, a
  `functools.partial`, a builtin, a `lambda`, a function of another episode's file (also when imported into this
  episode's file, or rebuilt with this file's module name written onto it), a function built inside another
  function;
- a function member or tool whose parameters are not exactly the ones in the table; a generator; an `async`
  function member (only tools may be `async`);
- an invalid `binding_path`, slot name, child path, tool name or service name; forms that are not `RecordForm`;
- a `return_form` that does not declare `credit` and `finding` as required fields
  (`episode_return_form_must_require:<class>:<fields>`; a field declared `required=False` is selectable and does
  not count), or whose `credit` is not of type `number` (`episode_return_form_credit_must_be_a_number:<class>`).
  The content form of `finding` is the episode's own (the typed investigation finding for an evidence episode).

The class keeps unchangeable copies of `tools` and `child_slots`: changing the file's mapping afterwards does not
reach the class, and an item of the class's copy cannot be assigned.

`BindingRegistry` raises `TypeError` for a binding instance:

- whose class did not pass the definition check (for example a class that was given `EpisodeBinding` as its base
  after its definition): `episode_class_was_not_checked_at_its_definition`;
- whose class was changed after its definition (a member replaced, added or removed, the bases changed):
  `episode_class_changed_after_its_definition:<class>:<members>`;
- that has attributes of its own: `binding_instance_has_attributes_of_its_own`.

Not checked, by the class or by any test today:

| What still gets through | Why it is not closed here |
|---|---|
| `assignment_form` or `return_form` taken from another episode | a `RecordForm` does not know which file made it |
| module-level state a member changes (state shared by every Episode of the binding) | Python cannot tell a constant from state |
| a member or tool whose body calls another episode's function through an import | this is a rule about imports, not about the class |

The import rule ("an episode imports nothing from another episode") needs a test over the source of the episode
folders. `root/tests/test_private_bindings.py` still states the old rule (inheritance from classes of the
episode's own folder) and no `EpisodeBinding` class exists under `root/` yet, so today nothing tests it.
`test_system_recording.py` applies the rule to the test episodes only.

### Example (`episode_runtime/tests/fact_collection/fact_extraction/`)

```python
# episode.py
class FactExtraction(EpisodeBinding):
    binding_path = goal_file.BINDING_PATH
    goal = goal_file.GOAL
    unit = goal_file.UNIT
    result = goal_file.RESULT
    child_slots = task_file.CHILD_SLOTS
    tools = task_file.TOOLS
    services = task_file.SERVICES
    decide = task_file.decide
    action = task_file.action
    credit = credit_file.credit
    yield_controller = yield_file.yield_controller
    assignment_form = from_parent_file.ASSIGNMENT_FORM
    read_from_parent = from_parent_file.read_from_parent
    internal_summary = summary_file.internal_summary
    return_form = final_file.RETURN_FORM
    final_to_parent = final_file.final_to_parent
```

```python
# messages/final_to_parent.py
FINDING_FORM = RecordForm({
    'field': Field('text', 'The commissioned field'),
    'found': Field('boolean', 'Whether a passed record has the field'),
    'value': Field('text', 'The value of the field, when found', required=False),
    'source_ref': Field('text', 'The passed record the value was read from, when found', required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),      # always returned
    'finding': Field('record', 'What the extraction found', form=FINDING_FORM),            # always returned
    'fact': Field('text', 'The extracted value, or "not found"'),
    'fact_refs': Field('record_refs', 'The fact record'),
    'field': Field('text', 'The field that was extracted', required=False),              # selectable
    'records_read': Field('list', 'The records read before the fact was found, in order', required=False),
})

def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': {...}, 'fact': ..., 'fact_refs': [...]}
    ...
```

## What each function is handed

| Function | Is handed |
|---|---|
| `internal_summary(view)` | the `method_loop.EpisodeView`, below |
| `decide(summary, feedback, ctx)` | the summary; the feedback of the last rejected model answer (`None` at first); the `DecisionContext` |
| `action(response, summary, records, ctx)` | the model's response; the summary; the `RecordReader`; the same `DecisionContext` |
| `ceiling(summary, records, action_type, arguments, ctx)` | the summary before the unit; the `RecordReader`; the action type; its arguments (`None` for every offered action); the same `DecisionContext` as `decide` |
| `offered_actions(summary, ctx)` | the summary; the same `DecisionContext` as `decide` |
| `credit(summary, records)` | the summary of the view as it stands once the unit completes; the `RecordReader` |
| `yield_controller(initial_credit, settings, parent_input)` | `credit` of the summary before any unit, computed when the Episode is first entered and journaled (on resume the journaled value is handed over, "Resume"); the episode's settings; the parent input |
| `read_from_parent(assignment, message)` | the admitted assignment and the commissioner's message |
| `msg_to_child(slot, arguments, summary)` | the slot and arguments of the `ChildCall`; the summary |
| `read_from_child(slot, result, summary, records)` | the slot; the child's admitted result; the summary; the `RecordReader` |
| `final_to_parent(summary, completion, selection)` | the summary of the closed Episode; `completion` (`{'ended_by', 'units_consumed', 'credit'}`: how the system ended the Episode and the credit its controller last saw); the selected field names |
| `tool(arguments, ctx)` | the arguments of the `ToolCall`; the `UnitContext` |

**`view`** (`EpisodeView`): `request` and `goal`; `parent_input`; `outcomes` (the outcome of each completed unit, in
order); `updates` and `child_reports` (one per completed child unit; a child unit's own update joins them after the
unit, so the view that prices a unit lists the updates of the units before it and the unit's own report is in
`outcomes`); `units_consumed`; `controller_state`; `key`, `path`, `episode_ref`; and `records`, the `RecordReader`.
On resume the loop restores `outcomes`, `updates` and `child_reports` exactly.

**`records`** (`RecordReader`, read-only): every read of the Store under custody, listed in the next section
(custody questions, reads of one held record, the inventories of held records, scope arithmetic, and
`table(declaration)`, a `TableReader`: `get(row_ref)`, `select(where=None, limit=None, offset=0)`). It has no write
and no transaction. A read of something the Episode does not hold raises `CustodyError`.

**`ctx` of `decide` and `action`** (`DecisionContext`, read-only):

| Field | Meaning |
|---|---|
| `ctx.settings` | a copy of the episode's own entry of the `continuation` collaborator (cost, estimator parameters, thresholds, anything else the caller put there); journaled at link and compared on resume |
| `ctx.services` | a mapping of exactly the service names the episode declared, each to its **read handle** (`ServiceReader`), never to the service: `ctx.services[name].read(member, *arguments)`. It cannot be changed; a name the episode did not declare raises `KeyError` |
| `ctx.clock` | the `DecisionClock` of this decision: `now` (UTC), `began_at` (UTC, when the Episode began), `elapsed_seconds` between them (`None` with `status='unavailable'` and `unavailable_reason` when the clocks cannot be compared), `progress_time` (the progress receipt of the last completed unit, `None` before the first). It is captured once per unit position and recorded, so every `decide` call for the unit, and every replay of it, sees the same time |
| `ctx.run_id`, `ctx.episode_id`, `ctx.binding_path`, `ctx.key` | the run and the Episode |

**What a decision reads from a service is recorded** (provisional, decision T10). `decide` and `action` only read.
They are not handed a service, only its read handle: `ctx.services[name].read(member, *arguments)` returns the
service's public attribute `member` (called with `arguments` when it is callable; a name starting with `_` raises
`ValueError`, arguments for a plain attribute raise `TypeError`) as closed JSON (`TypeError` when the value or an
argument is not JSON). The first read of a member with given arguments at a unit position asks the service and is
recorded in the journal (`service_reads`: position, `{'service', 'member', 'arguments'}`, value). Every later read
of the same request at that position returns the recorded value without asking the service: after a rejected
answer, when the unit runs again after an interruption, and on resume. The next unit position reads again. So,
like the clock, a decision that is made again is made on the values it was first made on, and a service whose
value changed does not make a run unresumable. A handle cannot act: it offers `read` and nothing else, and the
service is built only when a read is not yet recorded.

The journal still refuses a reconstruction that differs from its record: a rebuilt model request
(`JournalError('recorded_model_call_differs:...')`), a rebuilt unit of an abandoned attempt
(`JournalError('abandoned_unit_differs:...')`), a rebuilt closure or result
(`recorded_episode_completion_differs`, `recorded_episode_result_differs`). With settings, clock and service
reads recorded, only changed episode code, or a read of the outside world that goes round `ctx`, can cause one.

**`ctx` of a tool** (`UnitContext`):

| Field | Meaning |
|---|---|
| `ctx.store` | the custody-scoped Store (`ScopedStore`): every record read and write of the unit (next section). There is no `ctx.records`: `ctx.store` is the whole operation set, and `records` elsewhere is its read-only part under the same names |
| `ctx.services` | as above; a tool may act through a service |
| `ctx.model` | the recorded model: `await ctx.model.complete(role, instructions, context, output_schema)` (so the tool is `async def`). The call is journaled under this unit, numbered after the decision's own calls, and a rerun of the unit is given the recorded response |
| `ctx.operation_key` | text, stable for this unit (`op_` plus a digest of run, episode path, unit position and label); identical on every attempt of the unit |
| `ctx.resumed` | true when an earlier attempt of this unit began and did not finish and the unit is being run again |
| `ctx.abandoned` | what those earlier attempts wrote: `({'ref', 'producer_unit', 'written', 'prior'}, ...)` ("Resume", below) |
| `ctx.settings`, `ctx.run_id`, `ctx.episode_id`, `ctx.binding_path` | as in the decision context |

**Side effects.** Before a tool runs or a child is built, the system journals that the unit began (label, operation
key, digest of the arguments); the unit's completion marks it finished. On resume a unit that began and did not
finish runs again with the same `ctx.operation_key` and `ctx.resumed` true. A rebuilt unit that differs (another
label, key or arguments) raises `JournalError('abandoned_unit_differs:...')`. The system guarantees the key and the
began/finished journal, **not the external world**: a tool with an external side effect (a job submission) must be
idempotent on `ctx.operation_key` and may check on `ctx.resumed` whether the effect already happened.

## The Store under custody

The run has one shared Store (`gene_annotation_episode.state.Store`, the `store` collaborator). No episode and no
library function receives it, its SQLite connection (`db`) or its directory (`path`), and no operation hands out
the path of a record, an artifact or a table. One operation hands out a path: `ctx.store.scratch(name)` gives the
running tool unit a directory of its own (`scratch.path`), which the system places beside the Store's files
(`<store directory>/scratch/<episode id>/`). Nothing in it is a record, it is removed when its block is left, and
a library function never builds a path to the Store from it ("Files of the unit's own", below). A library
function that works inside an episode run is handed `ctx.store` (or `records`) by the tool that calls it and
calls only what it offers.

`episode_runtime/tests/test_library_boundary.py` has three tests over the library's source. One fails when a
library module imports a runner internal. One fails when a library function module imports the `Store` class at
run time (an import under `if TYPE_CHECKING:` is not counted); it is red today for
`tools/protein_structure/protein_structure_tools.py`, which opens the Store by path in a worker thread. Neither
sees raw SQL: a library file that runs SQL on the `store.db` it was handed passes both. The third test therefore
reports, and never fails on, the number of `store.db`, `store.path` and private-method sites left in each function
family (lines `RAW_STORE_SITES ...` in the test output: 1,604 `store.db` sites in 253 files on 19 November 2026).

**What is under custody** (held only by a receipt, written only as produced by a unit): Store records of every
kind, inputs, artifacts, material members, and the rows of declared work tables.

**What a read reaches** (provisional, decision T5: *name every record*). A read names one record and that record
must be held. **Holding a record does not hold the records it names.** A pass or a return carries exactly the
records named in its `record_refs` fields, so each `msg_to_child` and each `final_to_parent` lists every record
the receiver's code will read: the assessment and its hypothesis, the observation, the source and the source's
artifact; a sheet is one reference per cell.

Some of the Store's own read operations read further records on the way to their answer. Before this decision
they did so without a receipt for those records. Now each record in the right-hand column must be held as well,
or the read raises `CustodyError` and the Store is not asked (the table `FOLLOWED` in
`episode_runtime/store_scope.py` is the whole of the rule):

| Operation on a held record | Records it reads beyond that record |
|---|---|
| `subject_length(ref)` | of a product or a reference: its sequence artifact (`sequence_ref`; the Store reads its size) |
| `subject_unit(ref)`, `subject_molecule(ref)` | of a feature: its parent subject (`subject_ref`), and that subject's parents while they are features |
| `sequence_mapping(ref)`, `has_exact_mapping(ref)` | of a feature: its parent subjects, as above; of a reference, or of a feature whose parents end in one: the reference's sequence artifact |
| `map_segments(ref, segments)` | what `sequence_mapping(ref)` reads; the sequence artifact of a product or a reference; the subjects the stored mapping of a product runs over |
| `coverage(ref)` | of a feature: its parent subject and what `map_segments` of that parent reads |
| `record_coverage(row)` | of an assessment: its hypothesis (`hypothesis_ref`) and what the hypothesis's coverage reads; of a hypothesis or an observation: every subject it names (`subject_refs`) and what `coverage` of each reads |
| `material_read(ref)` | the material's source (`source_ref`) and that source's artifact (`artifact_ref`), whose bytes are returned |
| `material_annotations(ref)` | the parse attempt's material (`material_ref`) and, when the parse made one, the source of its native annotations (`native_source_ref`) |

A value the caller builds is read the same way. Every subject and read selection a scope or a context mask names
(`validate_scope`, `scope_contains`, `scope_covers`, `scope_coverage`, `scope_dimension_segments`,
`normalize_context_mask`, `context_mask_identity`, `context_mask_subset`, `context_mask_overlap`, and
`assessment_key` for the `context_account_scope` of its record), the target a span names (`footprint_dimension`)
and every subject the path of a mapping names (`footprint_from_mapping`) must be held: the Store reads each to
answer.

Four exceptions remain, each for a stated reason:

- **The members of a collection** (`material_members`, `material_member`, and the writes `material_header` and
  `material_reference`). A member is read by an Episode that holds it or its collection, and the packed bytes of
  its title, sequence and quality are read with it. Reason: members are rows of the collection (there can be very
  many) and their bytes are the collection's own storage; neither has a receipt of its own.
- **`get` of a read subject** (`read_subject_...`). The Store builds that record from the library input and the
  member its reference is made of. Reason: a read subject has no stored row; holding the reference is holding
  that pair.
- **The scope filter of the inventories and of `in_scope`.** To decide whether a held record lies within a scope
  that has read selections or member segments, the Store computes the record's extent with its own
  `record_coverage`, which reads the hypothesis and the subjects the record names. Reason: the answer is only
  which held records are in scope; nothing of a record read on the way is returned, and the inventories return
  held records only.
- **`scope_dimension_segments(scope, dimension_ref)`** reads the record of `dimension_ref` to find its target and
  length. Reason: it answers only when that target (the input itself, or the library of a read subject) is one
  of the scope's subjects, which must be held, and returns an empty list for any other.

No write is a way round: a write requires every record it names to be readable.

Outside the Store, and outside custody, are the run's services (the external world: schedulers, transports, the
native event ledger, tables of earlier estimates), the model provider's call files and the run journal itself.

`records` offers every row of this table that is not marked "`ctx.store` only"; `ctx.store` offers all of it, and
nothing else. The operations stage 1 of the carry-over built (19 November 2026) are in the table with the others;
`carry_over_guide/store-access.md`, "System operations built in stage 1", names the old library pattern each one
replaces.

| Kind | Operations | Custody rule |
|---|---|---|
| Custody questions | `holds(ref)`, `refs()`, `receipt(ref)` | |
| Reads of one named record | `get`, `get_artifact`, `open_artifact(ref)`, `require(ref, kinds=None, *, field_path=None)`, `is_current(ref)`, `get_input`, `roots(ref)`, `named_references(ref)`, `subject_length`, `subject_unit`, `subject_molecule`, `coverage`, `record_coverage(row)`, `sequence_mapping`, `has_exact_mapping`, `map_segments`, `material_members`, `material_errors`, `material_read`, `material_member`, `material_annotations` | the record must be held, and so must every record the operation reads beyond it ("What a read reaches"), else `CustodyError`. A collection member is read by an Episode that holds it or its collection. `named_references` only lists the references the record names: naming is not holding |
| The Store's ownership rules over a held record | `assessment_write_extent(ref)`, `assert_library_write_scope(ref, scope)` | the record, and every record the rule reads (the hypothesis and observation of an assessment, the subjects those name, what each subject's coverage and mapping follow, the scope's subjects and read selections), must be held, else `CustodyError` |
| Inventories | `list(kind, scope=None, limit=None, offset=0)`, `count(kind, scope=None, *, current=False)`, `subjects(scope)`, `references(scope)`, `targets()`, `problem()`, `current_assessments(scope=None, limit=None, offset=0)`, `current_annotations(...)`, `iter_current_annotations(...)`, `iter_current_accounts(kind, scope=None, page_size=100)`, `current_assessment_subset(refs)`, `reference_subset(candidates, scope)`, `in_scope(ref, scope)`, `query_records(kind, scope, limit=100, offset=0, *, current_only=False, references=None)`, `reasoning_view(scope, limit=100)` | each returns only what the Episode holds; a `scope` must name only held subjects and read selections |
| The reads of a read library | `library_members(library_ref, *, selection_ref=None, offset=0, limit=50, scope=None)`, `selection_members(selection_ref, limit=None, offset=0)`, `read_subject_ref(library_ref, member_ref)` | `library_members`: the library, every collection it binds, the scope's subjects and read selections and `selection_ref` must be held. `selection_members`: the read selection must be held. `read_subject_ref`: the library must be held. The read references these return are names: `get` of a read subject needs that reference held |
| The diagnostics of the Episode's own tool outcomes | `is_diagnostic_ref(ref)` | `ref` must be held, else `CustodyError`; another Episode's diagnostic is not one of this Episode's |
| Scope arithmetic over held subjects | `validate_scope(scope, parent_scope=None)`, `scope_contains`, `scope_covers`, `scope_coverage(scope)`, `scope_dimension_segments(scope, dimension_ref)`, `scope_measure(scope, target_ref)`, `iter_scope_coverage(scope, target_ref=None)` | every subject and read selection a scope names must be held, else `CustodyError` (the Store reads those inputs to answer) |
| Arithmetic over a value the caller builds | `normalize_context_mask`, `context_mask_identity`, `context_mask_subset`, `context_mask_overlap`, `context_mask_measure(mask, target_ref)`, `context_mask_target_full(mask, target_ref)`, `context_mask_dimension_segments(mask, dimension_ref)`, `context_mask_positions(mask, target_ref, limit=None, offset=0)`, `footprint_dimension`, `footprint_from_mapping`, `assessment_key` | every subject, read selection or target the value names must be held, else `CustodyError` (the Store reads those to answer) |
| Reads no record | `reasoning_schema()` | |
| Work tables, read | `table(declaration)`: `get(row_ref)`, `select(where=None, limit=None, offset=0, *, withdrawn=False)` | below |
| Writes (`ctx.store` only) | `put(kind, record, *, origin, scope=None)`, `artifact(data, media_type='application/octet-stream')`, `artifact_file(path, media_type='application/octet-stream')`, `artifact_stream(stream, media_type='application/octet-stream')`, `caller_source(value, provider)`, `commit_reasoning(payload, scope, operation_key)`, `register_material(input_path=None, *, source_ref=None, **options)`, `create_problem(input_path=None, **options)`, `parse_material(material_ref, *, format=None)`, `material_header(member_ref, *, offset=0, limit=12000)`, `material_reference(member_ref)`, `select_library_members(library_ref, *, member_refs=None, ordinal_ranges=None, scope=None)`, `reclaim(ref)` | every record the write names must be readable by the unit, else `CustodyError`; the Episode holds what the write created or changed as produced at this unit |
| Work tables, write (`ctx.store` only) | `table(declaration).put(values)`, `table(declaration).withdraw(key)` | below |
| Files of the unit's own (`ctx.store` only) | `with scratch(name='work') as scratch:` then `scratch.path`, `scratch.copy_artifact(ref, name)`, `await scratch.compute(function, *args, **kwargs)` | outside custody: nothing in the directory is a record. Only while a tool unit runs; `copy_artifact` requires the artifact held |
| Sections of the unit's work (`ctx.store` only) | `with section(name) as outer:` | only while a tool unit runs; the state is this Episode's and lasts for the call |
| Transactions (`ctx.store` only) | `transaction()`, `read_snapshot()`, `in_transaction()` | the writes of a transaction are receipted when it commits |

Details that matter:

- **What a write names.** A record names another by a value under a key `ref` or `..._ref`, or in a list under
  `..._refs` or `dependencies` (the Store's own rule). `put` requires every such reference of the record, and every
  subject of its `scope`, to be readable. `commit_reasoning` requires every reference of the payload that is not an
  alias (`@name`) of the same payload. A work-table row requires its `record_refs` columns. `register_material`
  requires its `source_ref`. `parse_material` requires the material and every record the material names (its
  source, sample, library and context records). `material_reference` requires the member's collection and every
  record the collection names. A write that is refused raises `CustodyError` and writes nothing. The same error is
  raised for a reference that does not exist: custody does not say which.
- **No silent page.** `list` returns every held record of the kind unless a `limit` is given. `query_records`,
  `reasoning_view` and `material_members` are paged and say so in their result (`total`, `next_offset`).
  `iter_current_accounts` reads every page.
- **`open_artifact(ref)`** returns a read-only binary file object over the bytes of a held artifact, for content
  too large to load with `get_artifact`. It is opened by descriptor and has no path. A tool that needs a file on
  disk for an external program copies the artifact into a scratch directory of its unit:
  `scratch.copy_artifact(ref, name)` ("Files of the unit's own", below).
- **`record_coverage(row)`** uses only `row['id']`: the coverage is computed from the stored record.
- **`query_records(references=[...])`** requires each named reference to be held.
- **`is_current(ref)`** says whether a held assessment, annotation or interpretation account is the current
  revision of its lineage. With the `current_*` inventories it lets `credit` count only current records.
- `commit_reasoning` names this Episode `(run_id, episode_id)` as the account owner, so two Episodes of one binding
  under the same key (in two parents, or in two runs that share a Store) have separate interpretation accounts.
  The Store's commit is idempotent on `operation_key`: pass `ctx.operation_key`. `reasoning_schema()` is the JSON
  schema of the payload.
- `register_material(source_ref=...)` requires the source to be readable. The Episode holds the returned material
  record and, transitively, the records it names that it did not hold (the records the call created: the source
  of new bytes, that source's artifact, the context records). `create_problem` likewise holds the problem's
  subjects and what they name.
- **Parsing is a write.** `parse_material` writes a parse attempt, a collection, its members and, for compressed
  or annotated input, further sources; `material_reference` writes a reference and a context record;
  `material_header` writes the title's artifact when the member is stored packed. The Episode holds what each
  created (the members through their collection) and can read all of it.
- `problem()` returns the problem record with `subject_refs` limited to the subjects the Episode holds.
- **Every write is one Store transaction with its receipt.** A write outside `ctx.store.transaction()` runs in a
  Store transaction of its own. The receipt of each write is written in that Store transaction (a system table of
  the Store file), so a record and its receipt commit or roll back together; the journal's copy follows the commit
  and is recovered from the Store when a process is cut in between ("Resume"). A write inside
  `ctx.store.transaction()` is held provisionally (it can be read back inside the transaction) and is receipted
  when the outermost transaction commits. When a transaction rolls back, no receipt is written, the Episode does
  not hold what it wrote, and the unit's `produced` list does not name it. A write that raises (also the Store's
  `RevisionConflict`) therefore leaves nothing in the Store. A custody write inside a Store transaction that
  `ctx.store` did not open raises `CustodyError`.
- **What stage 1 built, and what is still not offered.** Everything an earlier version of this contract listed as
  "not offered, because no custody-limited form exists yet" now has one, in the table above:

  | Old use of the Store | The custody-limited operation |
  |---|---|
  | `store._caller_source(value, provider)` | `store.caller_source(value, provider)`: the canonical bytes of `value` as an artifact and a `source` record of origin `caller`; the Episode holds both as produced |
  | `store._assessment_write_extent(row)` | `reader.assessment_write_extent(row['id'])`: the same segments, `[]` or `None`, computed over held records; a reference that is not an assessment raises `ValueError` |
  | `store._record_roots(kind, row)` | `reader.roots(row['id'])` |
  | `store._assert_library_write_scope(kind, row, scope, current=row)` | `reader.assert_library_write_scope(row['id'], scope)`: raises the Store's `ContractError` unless the held record is owned within `scope` |
  | `store._refs(row)` | `reader.named_references(row['id'])` |
  | `scope_measure`, `iter_scope_coverage`, `read_subject_ref`, `context_mask_measure`, `context_mask_target_full`, `context_mask_dimension_segments` | the same names on `reader` |
  | `context_mask_target_query(mask, target_ref)` (returned SQL for the caller to run) | `reader.context_mask_positions(mask, target_ref, limit=None, offset=0)`: the rows of that query (`target_ref`, `member_ref`, `dimension_ref`, `read_ref`, `length`, `unit`, `start`, `end`), ordered by member, unit, start and end |
  | a temporary file or directory under `store.path`; an artifact's file given to an external program; `Store(path)` opened in a worker thread | `store.scratch(name)`, `scratch.copy_artifact(ref, name)`, `await scratch.compute(function, ...)` |
  | an artifact captured from a file or a download without loading it | `store.artifact_file(path, media_type)`, `store.artifact_stream(stream, media_type)` |
  | `store._literature_sheet_updating` (a flag the literature library set on the Store object it was handed) | `with store.section('literature_sheet_updating') as outer:` |
  | `DELETE` of a row of the function's own table | `store.table(T).withdraw(key)` |
  | a cache directory under `store.path`; "was this already fetched by anyone" | the `work_cache` service (`episode_runtime.WorkCache`), declared like any service ("Collaborators and services") |

  Still not offered, and not planned: the Store itself, its connection (`db`), its directory (`path`), `commit`
  (a single write is a transaction of its own; several writes that must be one step are `with
  store.transaction():`), the path of an artifact (`artifact_path`), the SQL of `context_mask_target_query`, and
  any query over rows or records the Episode does not hold. The Store's static helpers `_unit`, `_merge_segments`
  and `_covered_by` read nothing: they are not store operations and become pure functions of a library module
  (stage 2). `carry_over_guide/store-access.md` maps every old raw-Store pattern of the library to its
  replacement; its table "No replacement yet" is empty.
- **Files of the unit's own** (`episode_runtime/scratch.py`). `with ctx.store.scratch('label') as scratch:` gives
  the running tool unit a new, empty directory (`scratch.path`, a `pathlib.Path`), removed with everything in it
  when the block is left, also by an error. Nothing in it is a record: an input enters through a custody read
  (`scratch.copy_artifact(ref, 'inputs/name')` returns the path of a copy checked against the artifact's digest)
  and a result leaves as a write of the store (`artifact_file`). `await scratch.compute(function, *args,
  **kwargs)` runs `function(*args, cancel_event=<threading.Event>, **kwargs)` in a worker thread and returns its
  value; the thread is given files and plain values, and `ctx.store` refuses every call from it
  (`CustodyError('scoped_store_used_outside_the_thread_of_its_unit')`). A cancelled unit sets the event and
  waits for the thread before the directory is removed. A unit that ends with a directory open raises
  `CustodyError('unit_ended_with_an_open_scratch_directory')`. What a cut process left is removed when the
  Episode is next built, so a rerun gets an empty directory: a scratch file never carries work across an
  interruption.
- **`artifact_file(path)` and `artifact_stream(stream)`** write an artifact from a file, or from a binary file
  object or an iterable of `bytes`, hashed while copied and never loaded. Each is one receipted write, like
  `artifact`.
- **`section(name)`** yields `True` for the outermost entry of the named section in this Episode's unit and
  `False` for a call made inside it, so a library function whose work calls itself does its once-per-call part
  only at the outermost entry. It is released by an error too.
- **The reads of a read library.** `library_members` returns the Store's own page (`{'library_ref',
  'selection_ref', 'members', 'total', 'offset', 'limit', 'next_offset', 'next_query'}`, each member the read
  subject in its model view, in the library's order; `scope=None` is the whole library).
  `select_library_members` is the Store's own `select` as one receipted transaction: it returns the
  `read_selection` record, which the Episode holds as produced at the unit (the library, every collection it
  binds, the scope's subjects and read selections and every member named must be held; the Store's refusals are
  unchanged). `selection_members` returns the references of the reads a held read selection froze, ordered by
  reference (all, or a page). A read is read without holding its reference through the page (its record) and
  `material_member(member['member_ref'])` (its sequence, through the held collection).
- **`is_diagnostic_ref(ref)`** says whether the value a tool unit of this Episode returned names the held record
  `ref` under a key `diagnostic_ref`, at any depth. It is known for every recorded unit (again after a resume)
  and for the unit being completed from the moment its tool returned, so `credit` of that unit sees it; the tool
  that is still running has no outcome yet. A library function uses it to keep a diagnostic from being read as
  a source.

**Work tables.** A library function that kept its own SQL table of an Episode's work (a scoring sheet and its
cells, a grading ledger, a credit projection) declares it and uses it only through custody:

```python
SHEET = TableDeclaration(name='probe_sheet', columns=('sheet', 'cell', 'value', 'source_ref'),
                         key=('sheet', 'cell'), record_refs=('source_ref',))

def write_cell(store, sheet, cell, value, source_ref):          # called by a tool with ctx.store
    return store.table(SHEET).put({'sheet': sheet, 'cell': cell, 'value': value, 'source_ref': source_ref})

def cells(reader, sheet):                                        # called with ctx.store or records
    return reader.table(SHEET).select({'sheet': sheet})
```

- A row has a reference (`row_...`) derived from the table, the writing Episode and the row's declared key: the
  same Episode writing the same key again writes the same row (equal values change nothing; other values make
  revision 2, 3, ...). The system fills `id`, `record_type` (`'work_row'`), `table`, `run_id`, `episode_id`, `unit`,
  `operation_key` and `revision`; a declaration cannot use those names as columns.
- `put` is receipted as produced by the unit (on commit, inside a transaction). Every reference in the declared
  `record_refs` columns must be readable by the writing unit.
- A row is read only by an Episode that holds it. It is passed to a child or returned to a parent by naming its
  reference in a `record_refs` field, like any record; `select` returns the held rows of the table in receipt
  order, filtered by equality on value or system columns (all of them unless a `limit` is given). `credit` can
  therefore check through `records` that a sheet exists before it gives credit.
- The rows of every declared table live in one system table of the Store's SQLite file, on the Store's own
  connection, so they commit or roll back with the records written beside them. A table's declaration is recorded
  on its first committed use; a later use with another declaration raises `WorkTableError`.
- `withdraw(key)` (the declared key columns and their values) is what a library function does where it used to
  delete a row: the row stays, marked, as its next revision with the system column `withdrawn` true, held as
  produced by the unit. `select` leaves withdrawn rows out (`select(where, withdrawn=True)` returns them too),
  `get(row_ref)` returns the row with its mark, and `put` with the same key makes it live again. Only a row this
  Episode wrote can be withdrawn (`WorkTableError` otherwise).
- What a unit that did not finish wrote to a row (a withdrawal too) is taken back when the run is resumed
  ("Resume").

**Custody is a rule, not a wall.** It is enforced by the system's own paths and by tests, not against deliberate
bypass. No object an episode receives has an admission method (the three passes are functions of `recording.py`
that only the runner calls), and the attributes that hold the Store and the custody object are private and not
part of this contract. Known limits: Python can still reach those attributes, and a file object from
`open_artifact` still names its file to the operating system; a unit that writes the same bytes as an existing
record it does not hold then holds that record as produced (content-addressed writes repeat, so `producer` means an
Episode that wrote these bytes); two episodes that declare the same service share that object.

## The loop of one Episode

1. `read_from_parent(assignment, message)` is the Episode's `parent_input`. Before each unit the task sees
   `summary = internal_summary(view)`.
2. `decide(summary, feedback, ctx)` returns a `ModelRequest` or an action. For a `ModelRequest` the system asks the
   model and `action(response, summary, records, ctx)` returns an action or raises `Rejected(feedback)`: the model's
   answer is malformed or unworthy. A rejection creates no unit and gives the controller nothing; `decide` is called
   again with that `feedback`. Every model call is journaled with its request, so the feedback the model saw is
   replayed with it. `action` always returns a unit for an answer it accepts: an answer that selects no unit is
   an invalid answer and is rejected like any other. An episode's `action` must therefore accept at least one
   unit at every decision; a decision that rejects every answer never produces a unit, and nothing else stops it
   (rule 2 forbids a count cutoff).

   **A model-named record that is not held** (provisional): `action` may reject a model answer that names a record
   `records.holds(ref)` denies, as it rejects any invalid answer. The test episode `probe` does. This is the
   validation of a model answer about an argument of the episode's own tool. It is not a check of a commission:
   what `msg_to_child` passes is never checked by an episode, and a commission that passes an unheld record fails
   (rule 1). An `action` that does not check lets the reference reach the tool: a read through `ctx.store` then
   raises `CustodyError`, and so does `commit_reasoning` for a payload that names an unheld record. A tool that
   does not handle that error ends the run with it. So a tool that takes model-named references asks
   `ctx.store.holds(ref)` first and returns a failure outcome; the system adds nothing for this.
3. The action is one of two:
   - `ToolCall(name, arguments)` runs `tools[name](arguments, ctx)` as one `Leaf`. The outcome is
     `{'kind': 'tool', 'tool', 'arguments', 'outcome': <what the tool returned>, 'produced': [refs]}`. A tool reports
     its own failures by returning them; an exception ends the run (it is recorded in the journal as the run's
     failure). A tool name the episode did not declare raises `LookupError`.
   - `ChildCall(slot, arguments)` builds the commission from `msg_to_child` and runs the child as one
     `ChildEpisodeUnit` under the key `<slot>_<position>`. The outcome is `{'kind': 'child', 'slot', 'arguments' (the
     `ChildCall` arguments), 'message' ({objective, message, assignment, selection} of the `ChildMessage`),
     'completion' ({ended_by, units_consumed}), 'result' (the child's admitted result), 'report' (what
     `read_from_child` made of it, called once)}`. A prediction made when commissioning rides in `arguments` or
     `message` and is therefore kept. A slot the episode did not declare raises `LookupError`. A wrong commission
     fails (rule 1): the error is raised where the child is built, after the unit's attempt was journaled, so the
     run ends with the error recorded as its failure, no child Episode exists, the unit stays `began`, and resuming
     the unchanged run raises the same error. What a correction then meets: when it is in the child (the child now
     declares the field), the commission is unchanged and the run resumes; when it changes what the parent sends,
     resume raises `JournalError('abandoned_unit_differs:...')`; when it changes the prompt, resume raises
     `JournalError('recorded_model_call_differs:...')`. In the last two cases a new run is started.
   There is no third action. `decide` and `action` cannot end the Episode; a `decide` or an `action` that returns
   anything else (`None` included) raises `TypeError('task_action_must_be_a_ToolCall_or_a_ChildCall:<path>:...')`,
   which ends the run as any error of an episode's code does. The loop itself raises when a source returns no
   unit (`method_loop`: "an Episode source must return a unit: only the controller ends an Episode").
4. Each unit's controller input is `{'credit': credit(internal_summary(view.with_unit(outcome)), records),
   'estimation_context': {'progress_time': <the unit's progress receipt>}}`. The episode's yield controller
   observes it and decides whether the Episode stops (rule 2). Its step for each unit (credit, marginal credit,
   estimate, decision, stop) is journaled. The runner checks that the controller from
   `yield_controller(credit(initial summary), settings, parent_input)` is one of the three `yield_control`
   controllers. `credit(initial summary)` is the Episode's initial credit: it is computed once, when the Episode
   is first entered, and journaled (`episodes.initial_credit`); an Episode that is entered again is built from the
   journaled value ("Resume"). **This is the only way an Episode ends** (`ended_by` has the one value `'yield_stop'`):
   - a completion or bounded-quality controller stops when its forecast upper bound of the next unit's credit is
     at or below its cost: a completion controller at the latest when credit reaches the commission's target (the
     forecast is then exactly zero), a bounded-quality controller at the latest at its maximum, and either
     earlier, when its units stop earning;
   - an accumulation controller (`AccumulationYieldController`, nano-graphrag's estimator controller) has no
     cost. From 8 units attempted and 4 observed, a unit is flat when the upper bound of the expected next
     marginal hypervolume credit is at or below gamma (`ADAPTIVE_CONTROL`: after each unit max(the one-result
     resolution, 0.1 x the median of the productive credits of the last 8 units); `FIXED_CONTROL`: 0.06); it
     stops after 4 flat units in a row, or when none of its `items` (the episode's input list) remains;
   - an episode with nothing left to gain still offers units (a wait, a check, a lookup). What they earn is its
     own `credit.py` and settings; when they earn nothing the forecast falls to the cost (an accumulation
     controller's units turn flat) and the controller stops it. A head with only an outstanding job ends this
     way, and the root commissions it again later (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, section 8);
   - **a closing value the model writes** (a closing text, a final report) is produced by a tool unit: the
     episode declares a tool for it (a `close` or `report` tool), the model selects it as its action with the
     value in the arguments, and the tool returns it. The outcome is journaled with the unit, the summary holds
     it (`view.outcomes`), and `final_to_parent` reads it from the summary. Selecting that tool does not end the
     Episode; what the unit earns, and so whether the controller then stops, is the episode's credit.
5. The result is `final_to_parent(internal_summary(<view of the closed record>), completion, selection)` with
   `completion = {'ended_by', 'units_consumed', 'credit'}`: `ended_by` is `'yield_stop'`, and `credit` is the
   Episode's credit as its controller last saw it (the cumulative credit of its last unit: the credit it stopped
   on). An episode returns that value as its `credit`; it does not state its credit formula a second time, and
   a credit that reads records needs no `records` in `final_to_parent`. The result is admitted against the
   commission's return form, which always contains `credit` and `finding`.

## The one channel from a child to its parent

The child's typed result is the only channel. The child declares in its own `final_to_parent.py` every field it can
return: the **required** fields (`Field(..., required=True)`, always returned; `credit` and `finding` are among
them in every episode, by the class-definition check, and can therefore never be selected) and the
**selectable** fields (`required=False`: fields the child declares it can return when asked). The parent never authors
a return form. In `msg_to_child` the parent chooses, for this commission, which selectable fields it wants:
`ChildMessage(objective, message, assignment, selection)`, `selection` a tuple of selectable field names (possibly
empty). `RecordForm.select(names)` builds the commission's return form (required fields plus the selected, now
required); a name that is not a selectable field of the child's form raises `FormError` when the commission is made
(rule 1). The child's `final_to_parent(summary, completion, selection)` returns the required fields and the selected
ones; the system admits the result only against that form. `read_from_child(slot, result, summary, records)`
receives the admitted result (the selected fields are present). The entry caller selects likewise: the entry input
is exactly `{'assignment', 'message', 'selection'}`.

The method loop requires every child edge to carry a reporting contract; the system type derives it
(`{'report': ...}`), no episode authors one, and the `report` of an update is what `read_from_child` returned.

## Runner entry points

- `link(registry, entry_path, entry_input, *, run_id, journal, collaborators, ancestors=(), key=None)` records a new
  run and builds the entry Episode below `entry_path`. Any registered binding can be the entry. What it does with
  the caller's input, and when:

  | Step | What is looked at | Error | The run id afterwards |
  |---|---|---|---|
  | 1 | the entry binding is registered | `MissingBinding` | free |
  | 2 | the ancestors | `LinkError` (below) | free |
  | 3 | the four collaborators, settings for every binding of the subtree, a factory for every declared service | `LinkError` | free |
  | 4 | the entry input has exactly the keys `assignment`, `message`, `selection` | `ValueError` | free |
  | 5 | the entry's own assignment form takes the assignment (as it does for a commission) | `FormError` | free |
  | 6 | the run id is not claimed in this Store by a run of another journal | `LinkError('run_id_claimed_in_this_store_by_another_journal:<run_id>')` | free in this journal |
  | 7 | the run is recorded (`runs`), then settings and declared services | `JournalError('run_already_recorded:...')` | used |
  | 8 | the entry's own return form takes the selection; the assignment form takes the assignment a second time | `FormError` | used; the run stays `active` |
  | 9 | each record a `record_refs` field of the entry assignment names exists in the Store (it becomes an `entry` receipt) | `CustodyError('entry_record_not_in_store:<ref>')` | used; the run stays `active` |
  | 10 | the entry Episode's commission is journaled; `read_from_parent` runs | the error it raises | used; the run stays `active` |

  What `link` looks at in the caller's entry input is exactly steps 4, 5, 8 and 9, at the points the table gives.
  Before the run is recorded: that the input has the three keys (4) and that the entry's own assignment form
  takes the assignment (5); a refusal there leaves the run id free. After the run is recorded, when the entry
  Episode is built: that the entry's own return form takes the selection and its assignment form takes the
  assignment (8), and that each record a `record_refs` field of the assignment names exists in the Store (9); a
  refusal there leaves a recorded run in state `active`. These are steps of `link` on the input of the run's
  caller. They are not a check of a commission and are not described as one: a commission is what a parent's
  `msg_to_child` builds, nothing looks at it before its child is built, and rule 1 is about it. Nothing was added
  to `link` or removed from it for this. An error at steps 8 to 10 is raised by `link` and is not recorded as the
  run's failure.
- `EpisodeRun.run()` runs the entry Episode until its yield controller stops it, builds its result and closes the
  run. An error that ends the run is recorded (`journal.run_failure(run_id)`).
  Nothing closes such a run, so its state stays `active`; a resume gets further after an interruption and raises
  the same error again after a wrong commission.
- `EpisodeRun.next_decision()` and `EpisodeRun.run_unit(tool_call)` step the entry Episode of a linked or resumed
  run in place of `run()` ("Stepping a run", below).
- `resume(registry, *, run_id, journal, collaborators)` re-links a recorded run from its recorded entry.
- `BindingRegistry(bindings)` registers only instances of classes that passed the definition check, are unchanged
  since, and have no attributes of their own ("Class definition checks"); a home constructs them.

**Ancestors.** With `ancestors` (top-down `{'binding_path', 'key', 'goal'}`), the entry is an inner node below a scoped
boundary: the top goal must be a root goal, each later goal refines its predecessor, each ancestor is a declared child
slot of the one above it, and ancestors are never built, run or journaled.

### Stepping a run: the first decision and one tool unit, without a model call

A real run of an episode whose `decide` returns a `ModelRequest` asks the model. Two operations of `EpisodeRun`
let the run's caller (a test, a driver) take the model's place for the entry Episode. They are system
operations: the Episode's own loop runs (`method_loop.Episode.run_async`, with the runner's hooks), so the yield
controller, the journal, custody and replay are those of any run, and the caller touches nothing of the runner.
Both are coroutines, like `run()`; each call may be given to an `asyncio.run` of its own.

| Call | Returns | What it does |
|---|---|---|
| `await linked.next_decision()` | what the episode's `decide` returns first: a `ModelRequest`, a `ToolCall` or a `ChildCall` | enters the Episode exactly as `run()` does (its yield controller is built from `credit` of the initial summary, in a resumed run from that credit as it was journaled; the units recorded for it, none in a new run, are replayed), builds `internal_summary(view)` and calls `decide(summary, None, ctx)` with the decision context of the next unit (its clock and its service reads are recorded as in any run). The model is not asked and no unit is consumed. Asked again, it returns the same decision, made on the recorded clock and reads. After `run_unit` it is the first decision for the unit that follows |
| `await linked.run_unit(tool_call)` | the unit's outcome: `{'kind': 'tool', 'tool', 'arguments', 'outcome', 'produced'}` | runs `tool_call` (a `ToolCall(name, arguments)`) as the Episode's next unit, as the loop runs it when the episode's own decision names that action: the attempt is journaled before the tool runs, the tool is handed the Episode's `UnitContext` (the custody-scoped Store on the run's real Store, the declared services, the recorded model, the unit's operation key), what it writes is receipted as produced by the unit, `credit` of the summary with the outcome goes to the yield controller, and the unit is journaled with the controller's step. `decide` and the model are not asked. The first step enters the Episode as `next_decision` does |
| `linked.view` | the entry Episode's `EpisodeView` where the stepped run stands | after the units run so far (of the closed Episode once its controller has stopped it): `outcomes`, `units_consumed`, `controller_state` (the yield controller's state: `stop`, `current_credit`), and `records`, the Episode's read-only `RecordReader`. A test calls the episode's own functions on it (`X.internal_summary(linked.view)`, `X.credit(summary, linked.view.records)`) |

What follows from the loop being the real one:

- **Stopping stays the yield estimator's.** When the controller's step for a stepped unit says stop, the Episode
  is closed, its result built and admitted and the run closed, as `run()` does; `await linked.run()` then returns
  that `{'entry', 'record', 'result'}`. A stopped Episode has no further unit and no further decision:
  `run_unit` and `next_decision` raise `RuntimeError('episode_stopped_by_its_yield_controller:<entry path>')`
  (the run is closed, so nothing is recorded as its failure). A test that steps several units gives the episode
  settings under which its controller goes on.
- **`run()` finishes a stepped run.** While the Episode is open, `await linked.run()` lets it run on from where
  the steps left it, by its own decisions (the model is asked from then on), until its controller stops it.
- **Resume replays stepped units.** A stepped unit is in the journal like any unit, so `resume(...)` replays it
  and does not run it again; `next_decision()` on the resumed run is the decision after the recorded units, and
  `run()` on it goes on by the episode's own decisions. A resumed closed run has nothing left to step.
- **A cut stepped unit runs again.** An error a tool raises ends the step and is recorded as the run's failure;
  the unit stays `began`. On the resumed run `run_unit` with the same `ToolCall` runs it again with the same
  `ctx.operation_key`, `ctx.resumed` true and `ctx.abandoned` naming what the cut attempt wrote. Another action at
  that position raises `JournalError('abandoned_unit_differs:...')`, as it does when a decision is rebuilt
  differently.
- **Only the entry Episode is stepped.** `run_unit` takes a `ChildCall(slot, arguments)` the same way: the
  commission is built by `msg_to_child` and the child runs as in any run, by its own decisions.
- An action that is neither raises the loop's `TypeError('task_action_must_be_a_ToolCall_or_a_ChildCall:...')`; a
  tool the episode did not declare raises `LookupError`.

```python
linked = link(BindingRegistry([X()]), X.binding_path, entry_input, run_id='r', journal=journal,
              collaborators=collaborators)
request = asyncio.run(linked.next_decision())                       # the episode's ModelRequest; no model call
outcome = asyncio.run(linked.run_unit(ToolCall('populate', arguments)))   # a real, journaled, receipted unit
summary = X.internal_summary(linked.view)                            # the Episode after that unit
assert linked.view.records.receipt(outcome['produced'][0])['how'] == 'produced'
```

`episode_runtime/tests/test_stepped_runs.py` is the worked example (the `probe` episode).

## Collaborators and services

Every run is linked with four collaborators, checked before anything is recorded:

| Name | Interface |
|---|---|
| `store` | the run's one shared `gene_annotation_episode.state.Store` (checked at link: `get`, `get_artifact`, `put`, `artifact`); episodes reach it only through custody |
| `model_provider` | `async complete(episode_id, role, instructions, context, output_schema)` |
| `continuation` | a `Mapping` with the settings of every binding path in the subtree; **journaled at link and compared on resume** (`JournalError('recorded_continuation_settings_differ:<path>')`). The episode's entry reaches `yield_controller` (`settings`), `decide`, `action` and tools (`ctx.settings`) |
| `services` | a `Mapping` of service name -> zero-argument factory; every name any binding of the subtree declares must be present |

A service is the run's access to something outside the Store. Each is built once per run, on its first use, and
shared by every episode that declares it. A tool is handed the service (`ctx.services[name]`) and may act through
it. `decide` and `action` are handed its read handle (`ctx.services[name].read(member, *arguments)`); what they
read is journaled per unit position and replayed ("What each function is handed"). The journal records each binding's declared names (compared on resume:
`JournalError('recorded_services_differ:<path>')`) and each build (which Episode first used it, at which unit). A
resumed run builds its services again, and their in-memory state starts empty: a service that keeps state across a
resume must keep it durably and be idempotent on `ctx.operation_key`.

**The work cache** (`episode_runtime.WorkCache`) is the service for work worth keeping across Episodes and runs
that is no record: the run's caller supplies `{'work_cache': lambda: WorkCache(directory)}`, an episode declares
`'work_cache'` in its `services`, and a tool calls `ctx.services['work_cache'].directory(name)` (a `Path` that
persists, for an external program's own cache), `.get(namespace, key)` (the bytes kept under a key of closed
JSON, or `None`), `.put(namespace, key, data)` and `.has(namespace, key)` (the question a decision may read).
Bytes found in the cache become the Episode's own product when the tool writes them with `ctx.store.artifact`.
It is a service and not an operation of the scoped store because a cache is nothing an Episode holds, passes or
returns, and it outlives the unit.

Errors: `LinkError('collaborator_required:<names>')`, `LinkError('collaborator_interface:<name>:<what>')`,
`LinkError('continuation_settings_required:<paths>')`, `LinkError('service_required:<path>:<service>')`,
`LinkError('yield_controller_must_be_a_yield_control_controller:<path>')` (when the controller is built), and the
ancestry errors (`ancestor_requires_binding_path_key_goal`, `ancestor_key_required`,
`top_ancestor_goal_must_be_a_root_goal`, `ancestor_goal_does_not_refine_its_parent`,
`ancestor_is_not_a_declared_child`, `entry_is_not_a_declared_child_of_its_parent`).

## What the runner records, by itself

All of it goes into the run journal, `RunJournal(path)`, a single SQLite file. The journal has an identity of its
own (`journal.identity`, made once with the file). A run id is unique within one journal.

| Table | What | When |
|---|---|---|
| `runs` | entry (path, input, ancestors, key), state, closing record (`ended_by`, `units`, `result`), the failure that ended it | `link`; when the entry Episode's controller stops it (in `EpisodeRun.run`, or on a stepped unit), or on an error of `run` or of a step |
| `settings` | the continuation settings of each binding path | `link` (compared on resume) |
| `services` | the service names each binding path declares | `link` (compared on resume) |
| `service_builds` | each service the run built: name, the Episode that first used it, its unit | first use (again after a resume) |
| `episodes` | binding path and commission (request, assignment, selection); initial credit (`credit` of the summary before any unit, which the yield controller is built from); completion (`ended_by`, `units`, `credit`: the credit the controller stopped on); admitted result | when built; when first entered (the controller build; read, never computed again, on resume); when closed; when its result is admitted |
| `parent_inputs` | digest of each Episode's parent input | controller build (compared on resume) |
| `attempts` | each unit that began: label, operation key, arguments digest, state `began`/`finished`, how often it began | before a tool runs or a child is built; with the unit record |
| `units` | label, controller input, outcome, (child units) update, and the controller's step of each completed unit | the loop's completed-unit hook |
| `model_calls` | request and response, by unit position and call index (the decision's calls, then the tool's) | each model call |
| `service_reads` | what a decision read from a service: unit position, request (`service`, `member`, `arguments`), value | the first read of that request at that position |
| `receipts` | each record an Episode holds: how, from, to, unit, producer, producer unit | each entry pass, commission and child return; for a production, after the Store transaction that wrote the record committed (a copy of the Store's own receipt, below) |
| `abandoned_receipts` | what an attempt of a unit that did not finish produced | when the run is resumed |
| `progress_points` | the clock points: origin, reference span, per-unit progress receipts, per-decision clocks | first use |

**Progress receipts.** `bound.progress.receipt(position)` is an `episode_progress_time_v1` receipt, captured once per
unit and recorded; it is `status='unavailable'` with its reason when the clocks cannot be compared, never estimated.
The system type puts it in every controller input; `ctx.clock.progress_time` shows the last one to `decide`.


**The system's tables in the Store file** (`store_ledger.py`, `work_tables.py`; on the Store's own connection):

| Table | What | When |
|---|---|---|
| `episode_runs` | which journal owns each run id written to this Store | `link` and `resume`, before the run is recorded or re-linked |
| `episode_produced` | the receipt of each record a unit produced: run, Episode, record, unit, and whether the attempt was abandoned | in the Store transaction that wrote the record |
| `episode_work_tables`, `episode_work_rows` | each work table's declaration; the rows, each with the row as it stood before the unit that last wrote it | first committed use; each `put` |
| `episode_abandoned_rows` | what an attempt of a unit that did not finish wrote to a row | when the run is resumed |

## Custody

An Episode holds a Store record, artifact or work-table row only through a receipt the runner recorded:

| How | When | Condition, and the error when it is not met |
|---|---|---|
| `entry` | named in a `record_refs` field of the entry assignment | it exists in the Store; `CustodyError('entry_record_not_in_store:...')` raised by `link` after the run is recorded |
| `commissioned` | named in a `record_refs` field of the assignment `msg_to_child` builds | the commissioning parent holds it; `CustodyError('record_not_held_by_commissioner:...')`, and the commission fails (rule 1) |
| `returned` | named in a `record_refs` field of a direct child's admitted result | the child holds it; `CustodyError('returned_record_not_held:...')` |
| `produced` | written through `ctx.store` by one of the Episode's own tool units | the Store transaction of the write committed; every record the write names was readable by the unit |

A receipt is `{'ref', 'how', 'from', 'to', 'unit', 'producer', 'producer_unit'}`; the first receipt of a record stands,
and every pass is all or nothing. A pass carries exactly the records named in the `record_refs` fields, and none
of the records those name (provisional, decision T5): the giver names every record the receiver needs, and a
read that would follow a name to a record that was not passed raises `CustodyError` ("What a read reaches").

**A produced receipt and its record are one atomic step.** The receipt is written in the Store's own file
(`episode_produced`), in the transaction that wrote the record. The journal's `receipts` row is a copy made after
the commit. When a process is cut between the Store's commit and the journal's copy, the copy is made from the
Store when the Episode is next built (resume); the unit that was running did not finish, so what it produced is
then abandoned as below.

## Resume

`resume` re-links the recorded entry. A rebuilt commission that differs from its record raises `JournalError`; so do
different continuation settings, different declared services, a different parent input, a different model request
and a changed abandoned unit. `resume` claims the run id in the Store again (refused when a run of another journal
holds it there). Each Episode gets its
recorded units (controller input, outcome, update) as `method_loop.resume_units`; a child whose parent unit completed
is not rebuilt; receipts reload from the journal.

**The initial credit is journaled, not recomputed.** An Episode's yield controller is built from `credit` of its
summary before any unit. The system computes that credit once, when the Episode is first entered (`run`,
`next_decision` or `run_unit`), and journals it (`episodes.initial_credit`; `journal.episodes(run_id)` shows it). An
Episode that is entered again (the entry of a resumed run, closed or cut; a child whose parent's unit runs again)
holds from the start every record its recorded units produced or received, because its receipts reload before its
controller is built. `credit` of its summary before any unit would then count them (a credit that reads an
inventory of custody: `records.list`, `records.refs()`, a work-table `select`) and the controller would start from
the credit of the end of the run. So on resume `credit` is not asked for the initial summary: the controller is
built from the journaled value and observes the recorded controller inputs, which gives the recorded marginal
credits, steps and stop. This is the system's; an episode's `credit` and `internal_summary` may read whatever
inventory they like.

Resuming a closed run replays its recorded units: the controller observes the recorded controller inputs again
and stops at the same unit, so no decision is made and no service is read. `final_to_parent` runs again. The
rebuilt closure and result must equal their records: a difference raises
`JournalError('recorded_episode_completion_differs:...')` or `JournalError('recorded_episode_result_differs:...')`.
Nothing new is recorded when they are equal. A unit that is decided again in an open run reads the recorded
values of its clock and of its service reads, so a service whose value changed since does not change the
decision.

**A unit that began and did not finish runs again. One rule covers what its abandoned attempt wrote:** it is
visible to the rerun's tool and to nothing else.

- When the run is resumed, before the unit is decided again, everything the unfinished unit produced is abandoned:
  its receipts leave the Episode's custody (they stay in `abandoned_receipts` as trace), a work-table row it
  created is removed, and a row it rewrote is put back as it stood before the unit. The `returned` receipts of an
  unfinished child unit are dropped too; the child unit runs again and its return is receipted again.
- So `view.records` and the `records` of `credit`, `action` and `read_from_child` never show what an abandoned
  attempt wrote, and the decision for the unit is rebuilt from the state its first attempt was decided on.
- The rerun's tool is told in `ctx.abandoned`: `({'ref', 'producer_unit', 'written', 'prior'}, ...)`. For a Store
  record or artifact `written` and `prior` are `None`; while the tool runs it may read the record through
  `ctx.store` (`get`, `get_artifact`, and as a reference a write names). For a work-table row `written` is the row
  as the last abandoned attempt left it and `prior` the row as it stood before the unit and stands again (`None`
  when the attempt created the row).
- `ctx.store.reclaim(ref)` makes an abandoned record the rerun's own product (held as produced at this unit); for
  a row it writes the abandoned row again. A content-addressed write the rerun repeats is produced again by
  itself, without `reclaim`.
- What the rerun does not reclaim is readable by nothing once the tool returns. An episode whose summary, credit
  or report then names such a record gets `CustodyError` in that same unit: the unit does not complete, and every
  resume fails the same way until the episode's code is corrected.
- A revisioned kind (assessment, annotation, interpretation account) is not retried by the system: a retried write
  with the original `expected_revision` raises the Store's `RevisionConflict`; the tool finds the abandoned
  revision in `ctx.abandoned`, reads it and reclaims it. (The Store's current revision is the abandoned one until
  then; the custody-limited `current_*` inventories do not show it, because the Episode does not hold it.)

## Forms

`RecordForm({name: Field | DeclaredField | ChoiceField | SubsetField})` names every field of a closed JSON record. The
types are `text`, `number`, `integer`, `boolean`, `record`, `list` and `record_refs`. Admission is exact: a missing,
unknown or mistyped field raises `FormError`; nothing is defaulted. In a *return* form `required=False` marks a
selectable field (above); in an *assignment* form it lets the supplier omit the field. `DeclaredField` is a value the
declaring episode fixes; `ChoiceField` and `SubsetField` choose among declared options.

## Launch, monitor, extract

`LAUNCH_MONITOR_EXTRACT_MECHANICS.md` is the design, written against this contract: job access and the estimate
table are services, job records travel in custody, the monitor and result acquisition are child episodes the parent
commissions, and a head with only an outstanding job is ended by its yield controller when the forecast yield of
its remaining units (waits and checks) does not exceed their cost; the root commissions it again later. Its last
section lists what the system does not provide yet.


## Tests

Test-only episodes live in the episode file structure under `episode_runtime/tests/`: `fact_collection/` (parent),
`fact_collection/fact_extraction/` (child) and `probe/` (a plan-driven head with two slots to one child and one slot
to its own kind). `sheet_library.py` is a test-only library module with a declared work table. A test that needs an
episode differing in one way gets a real package on disk (`conftest.py`, `episode_variant`). They run with the real
runner, `RunJournal`, `Store`, `method_loop` and `yield_control`; nothing is faked, and a test that needs a model
answer calls the model (`-m model_run`).

- `test_system_recording.py`: custody, journaling, interruption and resume, closed-run replay, the declaration, the
  controller-kind text, a wrong commission failing, what the test episodes import, every Episode ended by its
  controller with its credit in the closure and in the result, a task that offers no unit failing the run;
- `test_probe_runs.py`: services and their journal, the decision context and its recorded clock, a service value
  that changes across a resume (the decision is made again on the recorded read), the read handles, an
  interruption after a side effect, abandoned attempts and `reclaim`, a controller stop and its replay, settings
  and services compared on resume, several child slots, an episode commissioning its own kind three deep,
  completion and bounded controllers built from the parent input, credit reading records and returned as the
  system's credit, an episode with nothing left to do going on until its estimator stops it, no stop at cost
  zero, a closing value written by a tool unit, selected return fields, a wrong commission failing; a credit that
  counts held records (the cells of a sheet) under each of the three controllers: the closed run resumed with
  every product already held replays to the recorded stop with no unit, no model call and no new journal row, and
  a run cut mid-way goes on with the controller history of the uncut run;
- `test_scoped_store.py`: what `ctx.store` offers and refuses, an artifact opened without its path, transactions
  and receipts on commit, the reasoning commit and the inventories, the account owner, scopes over unheld subjects,
  material registration, work tables;
- `test_custody_rules.py`: a write that names an unheld record is refused (`put`, `register_material`,
  `commit_reasoning`), parsing as a receipted write and what a passed material or collection lets an Episode do,
  scope arithmetic, coverage and the reference filter over unheld records, each read that follows a reference
  refused until the followed record is held too, mask, span and mapping arithmetic over unheld subjects, credit
  reading the current inventories through `records`, one run id in two journals over one Store, an inventory
  without a silent page;
- `test_abandoned_attempts.py`: an abandoned record taken over, one not taken over, abandonment before the unit is
  decided again, a rewritten row put back, a created row removed, a cut between the Store's commit and the
  journal's receipt, no Store receipt after a rollback;
- `test_system_operations.py`: the operations stage 1 built, each through a library function of
  `operations_library.py`: the scratch directory, its worker thread, cancellation and a cut process; artifacts
  from a file and from a stream; a caller value as a source; a row withdrawn instead of deleted; sections; the
  work cache; the Store's ownership rules and the measures of a scope and a context mask over held records; the
  reads of a read library paged, frozen and listed; the diagnostics of the Episode's own tool outcomes;
- `test_stepped_runs.py`: `next_decision` returns the episode's own model request and asks no model; a unit
  the caller names with `run_unit` leaves the same units, credits, controller steps, attempts, receipts, closure
  and result as the whole run that names the same actions; a stopped Episode has no further step; a cut stepped
  unit runs again on resume with its key, and another action in its place is refused; resume replays stepped
  units and `run()` finishes the run; a cancellation reaches the stepped unit; a worker thread and a child call
  inside a stepped unit; an action the episode cannot run; a resumed stepped run whose credit counts held records
  shows the controller of the run that was stepped (the journaled initial credit) in `view`;
- `test_link.py`: every reachable `LinkError`, the ancestry refusals, an inner entry;
- `test_class_definition.py`: each class-definition refusal (a return form without required `credit` and
  `finding` among them) and each registry refusal;
- `test_journal_and_progress.py`: the journal, a service read recorded once per request and unit position, a
  unit rebuilt differently refused, the initial credit computed once and read from its record afterwards, the
  progress and decision clocks, the forms, `yield_control`'s imports;
- `test_library_boundary.py`: the library imports no runner internal; no library function module imports the
  `Store` class at run time (red today for one module, see "The Store under custody"); the report of raw-Store
  sites per function family;
- `test_model_run.py` (`-m model_run`): the real model chooses a field; a model-named unheld record is rejected,
  and the recorded calls replay although the service value in the request has changed; a tool asks the model
  through `ctx.model` and a rerun is given the recorded answer.

## Decisions of 19 November 2026

The third audit (`AUDIT_SYSTEM_EPISODE_TYPE_3.md`, section 14) put five questions. They are answered here. T1 and
T3 follow from the owner's stated rules. T5, T10 and the held-record check are **provisional**: each is
implemented in the one place named below, so that the owner can change it there.

- **T1. Nothing but the yield controller ends an Episode** (rule 2). `Done` is removed, with `END_EXHAUSTED` and
  the `closing` value of the closure. `decide` and `action` produce only a `ToolCall` or a `ChildCall`; a model
  answer that selects no unit is an invalid answer, rejected by `action` through `Rejected` like any other;
  `ended_by` has the one value `'yield_stop'`. A closing value the model writes is the outcome of a tool unit the
  episode declares for it. A head with only an outstanding job is ended by its controller when the forecast yield
  of its remaining units does not exceed their cost, and the root commissions it again later. ("The loop of one
  Episode", steps 3 to 5.)
- **T3. Credit and finding are in every return** (rule 5). `completion` carries the Episode's credit as its
  controller last saw it; the class definition requires `credit` (a number) and `finding` as required fields of
  every episode's own `return_form`, so neither can be left out or made selectable. Each episode declares the
  content form of its `finding` (the typed investigation finding for an evidence episode); the system requires
  only that the field is in the form and in the result. The system does not compare the returned `credit` with
  `completion['credit']`. ("Class definition checks"; "The loop of one Episode", step 5.)
- **T5 (provisional). A pass carries only the records named.** Passing or returning a record carries the records
  named in the `record_refs` fields and none of the records those name; each `msg_to_child` and `final_to_parent`
  lists every record the receiver needs. The Store reads that followed a name without a receipt now require the
  followed record to be held, with four stated exceptions (a collection's members, a read subject, the scope
  filter of the inventories, the dimension of `scope_dimension_segments`). The failure is
  `CustodyError`. **Where:** the table `FOLLOWED` with `followed` and `RecordReader._follow` in
  `episode_runtime/store_scope.py`, and the mask, span and mapping guards of `RecordReader` beside them. ("What a
  read reaches".) The other choice (a pass carries the records the named records name, each with a receipt)
  would replace that table by a closure computed in `recording.pass_records` and `return_records`.
- **T10 (provisional). What a decision reads from a service is recorded.** `decide` and `action` are handed read
  handles; each read is journaled once per unit position and replayed, like the clock. **Where:**
  `episode_runtime/services.py` (`DecisionServices`, `ServiceReader`), `recording.ServiceReads`,
  `RunJournal.service_read` (table `service_reads`) and the one line of `BoundEpisode.decision_context` that
  builds the handles. ("What each function is handed".) The other choice (services closed to `decide` and
  `action`) would hand them an empty mapping there.
- **The held-record check in `action` (provisional; the audit's question 6).** An `action` may reject a model
  answer that names a record the Episode does not hold, through `Rejected`, as an invalid answer. It is never a
  check of a commission. A reasoning payload that names an unheld record raises `CustodyError` from
  `commit_reasoning` and ends the run when the tool does not handle it, so a tool that takes model-named
  references asks `ctx.store.holds(ref)` first. **Where:** nothing in the system; the two lines of
  `episode_runtime/tests/probe/task.py` (`action`) and the model-run test that uses them. ("The loop of one
  Episode", step 2.)

Still open, from the same section of the audit: whether the owner wants the input of the run's caller treated
like a commission, so that `link` looks at nothing of it before the run is recorded ("Runner entry points" says
exactly what `link` looks at today, and when); large outcomes; the 54 old recorder call sites in the library.
