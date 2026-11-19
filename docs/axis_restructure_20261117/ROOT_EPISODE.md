# The root annotation episode (19 November 2026)

The root is an ordinary episode in the ten-file form: `class RootAnnotation(EpisodeBinding)` in
`gene_annotation_episode/episodic_workflow/root/episode.py`, binding path `root`, nine child slots, no tools, no
services. The runner has no knowledge of it. Its files import nothing from an axis folder.

## Files written

All under `gene_annotation_episode/episodic_workflow/root/`.

| File | Holds |
|---|---|
| `__init__.py` | the package docstring |
| `goal.py` | `BINDING_PATH = 'root'`, `GOAL`, `UNIT`, `RESULT` |
| `task.py` | `CHILD_SLOTS` (nine), `TOOLS = {}`, `SERVICES = ()`, `decide` (a `ModelRequest` of numbers and flags; the answer is one of the nine axis names), `action` (the `ChildCall` of the named axis) |
| `credit.py` | `EPSILON`, `K`, `AXIS_WEIGHTS`, `AXIS_CREDIT_UNITS`, `OPERATIONAL_CREDIT_UNITS`, `annotation_credit`, `credit`, and the derivation of `K` as its docstring |
| `yield_estimator.py` | `yield_controller`: `AccumulationYieldController('root', initial_credit, settings['cost'], settings['parameters'])` |
| `episode.py` | `RootAnnotation(EpisodeBinding)` |
| `messages/read_from_parent.py` | `ASSIGNMENT_FORM` (a scope and four `record_refs` fields), `read_from_parent` |
| `messages/msg_to_child.py` | one commission function per slot, `SELECTION` (the return fields selected from each head), `msg_to_child` |
| `messages/read_from_child.py` | `RECORD_FIELDS`, `JOB_FIELDS`, `read_from_child` |
| `messages/internal_summary.py` | `internal_summary` |
| `messages/final_to_parent.py` | `RETURN_FORM` (`credit`, `finding`, selectable `record_refs` and `outstanding_job_refs`), `final_to_parent` |
| `tests/test_root_credit.py` | the credit on real numbers (118 tests) |
| `tests/test_root_episode.py` | the class, the nine slots against the heads' own files, the root's pieces (48 tests) |
| `tests/test_root_model_run.py` | one `@pytest.mark.model_run` test (not run) |

## Files deleted

Deleted in this step, before anything was written: `root/credit.py`, `root/goal.py`, `root/task.py`,
`root/yield_estimator.py`, `root/messages/msg_to_child.py`, `root/messages/read_from_parent.py` (the partial files
of the root writer that was stopped earlier the same day; its `task.py` and `msg_to_child.py` passed
model-written objective and purpose text to the heads) and `root/__pycache__/`.

Already deleted in the working tree when this step began (`git status` shows them as `D` against `caeba803a`):
`root/axes.py`, `root/binding.py`, `root/composition.py`, `root/continuation.py`, `root/decisions.py`,
`root/home.py`, `root/report.py`, `root/tests/test_axes.py`, `root/tests/test_credit.py`. Nothing was restored.

No file of `tests/`, `gene_annotation_episode/`, `gene_annotation_episode/episodic_workflow/`, `examples/` or
`episode_runtime/` (top level of each) names a deleted root module or `annotation_hypervolume`.

## The nine child slots

| Slot (axis role) | Axis folder | Child binding path |
|---|---|---|
| `sequence_homology_evidence` | `root/a101` | `sequence_homology_evidence` |
| `structural_homology_evidence` | `root/a102` | `structural_homology_evidence` |
| `gene_context_evidence` | `root/a103` | `gene_context_evidence` |
| `evolutionary_history_evidence` | `root/a104` | `evolutionary_history_evidence` |
| `experimental_activity_evidence` | `root/a105` | `experimental_activity_evidence` |
| `perturbation_evidence` | `root/a106` | `perturbation_evidence` |
| `partner_presence_evidence` | `root/a107` | `partner_presence_evidence` |
| `sample_context_evidence` | `root/a108` | `sample_context_evidence` |
| `biochemical_feasibility_evidence` | `root/a110` | `biochemical_feasibility_evidence` |

The child binding path is the `BINDING_PATH` each head's own `goal.py` declares (the heads' paths are their role
names, without the axis folder). A test reads each head's `goal.py` and compares.

## Credit and the derivation of k

    credit = prod_i (1 + k * v_i) ** w_i - 1

`v_i` is the credit the head of axis `i` returned at its latest return (0 before its first return). The root
never bounds, clamps or rescales it.

Definition used (`README.md` of this folder: "one calibrated, rescaled offset-product hypervolume ... ε = 0.5";
the arithmetic it restates is `softened_hypervolume` of `gene_annotation_episode/credit.py` at `7e662ea29`):

1. Offset product: each axis contributes the factor `ε + (1 − ε)·v`, with `0 < ε < 1`, so
   `H(v) = Π_i (ε + (1 − ε)·v_i)^w_i`.
2. Rescaled by its value with no credit, `H(0) = Π_i ε^w_i`:
   `H(v) / H(0) = Π_i (1 + ((1 − ε)/ε)·v_i)^w_i`.
3. Calibrated so that no credit is 0: subtract 1.

So **k = (1 − ε)/ε**, and **ε = 0.5 gives k = 1**. The code computes `K = (1.0 - EPSILON) / EPSILON` from
`EPSILON = 0.5`; a test checks, in exact rational arithmetic, that the formula equals the rescaled and calibrated
offset product on every test vector, including credits of 1e6 to 1e30.

The old arithmetic also divided by `1 − H(0)` to map scores in [0, 1] onto [0, 1]. That step needs bounded scores
and is not used.

**The brief for this step said the existing `root/credit.py` "has k = 1 and is wrong".** The value is not wrong
under the only definition found: the two documents of this folder that state it (`README.md`,
`REVIEW_CARRY_OVER_WORKFLOW.md` section 13), the committed `root/credit.py` and the old `softened_hypervolume`
all give `k = (1 − ε)/ε`, which is 1 at ε = 0.5. What was wrong in the committed file is its form (weights passed
as an argument, input checks, an overflow guard, refusal of negative credits). If another definition of ε is
meant (for example the factor `ε + v`, which gives `k = 1/ε = 2`), the change is the one line `K = ...`.

## Weights, settings and the estimator

- **Weights.** `AXIS_WEIGHTS` in `credit.py`: 1.0 for each of the nine axes. One axis alone has credit exactly
  `k·v` (the code returns `K * v` itself for weight 1, so it is exact in floating point up to 1e300). An equal
  split of a total `T` over `n` axes has credit `(1 + k·T/n)^n − 1`, above `k·T` for every `n > 1` and growing
  with `n`.
- **Axis settings.** `AXIS_CREDIT_UNITS` in `credit.py`: the credit of one retained finding the root tells each
  head in its commission (`context.evidence_task.credit_unit`; `finding_unit` for partner presence). All 1.0.
  `OPERATIONAL_CREDIT_UNITS`: the units of the heads' operational children, for the two heads whose assignment
  takes them (A101, A107). All 1.0. These are the settings that make the axes comparable; they are not tuned.
- **Estimate credit** is separate: it is not read, not returned and not in the credit.
- **Estimator.** `AccumulationYieldController` (open-ended: no target, no maximum). It stops the root when its
  forecast upper bound of the next commission's gain is at or below `settings['cost']`, the root's own entry of
  the run's continuation settings. It takes nothing from the parent input and does not read the assignment.
- **Selections.** The selection each head is commissioned with (evidence-axis option, thought pattern, tools, in
  that head's own selection form) is the root's setting `settings['axis_selections'][slot]`. Option references
  carry library digests, so they cannot be constants of a file.

## Controlled messaging

- **In.** `ASSIGNMENT_FORM` has a `scope` record and four `record_refs` fields. No text field. The entry message
  is not read.
- **To a head.** A fixed objective sentence per axis; the selection from the settings; the proposed annotation
  reference; the scope; the finding task (fixed values and a number); credit units (numbers); record references;
  `constraints: {}`; an empty message (A104's `read_from_parent` requires `purpose` and `initial_report`: it gets
  the fixed value `whole_axis_findings` and `{}`). The model's answer is one of nine axis names and nothing of it
  is passed on but the choice of slot.
- **From a head.** `read_from_child` takes `credit`, the numbers and booleans of `finding` (under the head's own
  field names), and the record references of the fields named in `RECORD_FIELDS` and `JOB_FIELDS`. Text, lists
  and nested records of a finding are not read. `internal_summary` reads only these reports.
- **To the model.** Per axis: weight, credit, the credit of each return, the number of commissions, the numbers
  and flags of the latest finding, the number of outstanding job records, and what one more credit on the axis
  would add. Tests fill every text field of a head's return with a marker and assert it is absent from the
  summary, the request and the root's return.
- **Out.** `RETURN_FORM`: `credit`; `finding` (the number of commissions and, per axis, credit, commissions,
  outstanding jobs); selectable `record_refs` and `outstanding_job_refs`. Field types used: number, integer,
  record, record_refs.

**A head with an outstanding job.** Its return's job field goes to `outstanding_job_refs` of its axis; the model
sees the count, works on other axes and names the axis again later; every commission of an axis passes back
every record its head returned, the job records among them.

## Test results

Run with the launcher (`tools/one_workflow.sh --slot root`, empty `HOME`, blocked proxy, `eatmydata`).

| Run | Paths | Result |
|---|---|---|
| `runs/root_1` | `test_root_credit.py`, `test_root_episode.py` | 166 passed |
| `runs/root_2` | `root/tests/` (all) | 208 passed, 36 failed, 1 deselected |
| `runs/root_3` | `test_root_model_run.py --collect-only -m model_run` | 1 test collected; not run |

The 36 failures are all in `root/tests/test_private_bindings.py`, which predates this step and states the old
rule over the axis trees (`BINDING_CONTRACT.md` says so). It was not changed.

What the tests check: the formula against exact rational arithmetic on nine vectors (to 1e30 per axis); one axis
alone exactly `k·v` for each of the nine axes at ten values (1e-9 to 1e300, and a negative correction); an equal
split beating concentration for 2 to 9 axes at five totals; no bound through 1e12 on one axis and 1e6 on all
nine; the class and its nine slots; each head's own `BINDING_PATH`, assignment form, `read_from_parent` and return
form taking the root's commission and selection (nine heads, all pass); `decide`, `action` (a `ChildCall`, and a
rejection of an answer naming no axis), `read_from_child`, `internal_summary`, `credit`, `final_to_parent` and the
controller.

## Not done, and what it needs

1. **No run of the root through the runner.** `link` at `root` builds the nine heads and every episode below
   them and requires continuation settings and a service factory for each. No composition of a run exists in the
   repository (the declared services include `job_access`, `estimate_table`, `native_events`, `tool_catalog`,
   `resource_adapter`, `resources`, `instruction_libraries`). The model-run test therefore asks the real model
   the root's own request and stops at the commission, which the chosen head's forms admit. It does not follow
   `episode_runtime/tests/test_model_run.py` through `link`, `run` and `resume`.
2. **The controller stopping the root is not tested here.** It needs progress receipts from a run. The
   system's own tests cover the accumulation controller stopping an episode.
3. **Only the sequence-homology head declares a job field** (`execution_handoff_refs`). The other heads with
   launch children return no job records, and no head reads job records from its assignment: the root passes them
   back in the head's custody field, where the head holds them but does not yet treat them as outstanding jobs.
4. **Four heads require library text in the selection.** A101, A103, A104 and A106 validate canonical tool rows
   (`description`, `instructions`) in `selection.child_tool_info`. The root passes the rows its settings give. It
   is frozen library text, not model text, but it is text in a commission.
5. **Eight heads' `finding` still declares model-written text** (interpretation, qualification or source-claim
   fields in the `final_to_parent.py` of A102, A103, A104, A105, A106, A107, A108 and A110 as they stood at
   14:06 on 19 November; A101's text fields hold fixed values). The root does not read it, but the system admits
   it into the root's unit outcome (`outcome['result']`) and the journal.
