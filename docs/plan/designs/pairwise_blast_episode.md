# pairwise_blast: one self-contained action episode, no children, no model (pilot, 2026-11-20)

Binding path: `sequence_homology_evidence/pairwise_blast`. Pilot of the owner's decision: an episode named for the
action it performs, with everything that decides how it behaves (its goal, tools, grader choice, credit, stopping
rule, return) in its own folder, so it is obvious where to tune. No runtime assembly from the knowledge or
instruction libraries, no routing by table or by family branching. The episode's identity is the declaration of the
analysis (a pairwise BLAST: one query sequence against one subject sequence); the job it builds is checked against
that declaration. The generic episodes (local_job_execution, execution_progress_assessment,
execution_result_acquisition, the A101 head) are left unchanged; this episode copies what it needs from them and the
copies diverge.

Revised 2026-11-20 on the owner's correction: ONE episode with no children, fetch and grading ONE coupled automatic
step (grading is not a decision), the wait on the job's end event instead of polling, and the decisions made by
code, with no model request, wherever nothing is a real choice.

## 1. The tree: one episode, no children

- A local pairwise BLAST finishes in about a second. A monitor child would have nothing to watch.
- Fetching the report and grading it are not decisions. Once the job has ended there is exactly one thing to do with
  it, so they are one automatic step inside one tool unit (the grader runs by code after the fetch, the sheet is saved
  through custody), not an episode and not two units the model has to choose between.
- With no children there is one set of files, one stopping rule and one credit to tune.

Files (an episode with no children has no `msg_to_child.py` and no `read_from_child.py`): `goal.py`, `task.py`,
`credit.py`, `yield_estimator.py`, `episode.py`, `messages/read_from_parent.py`, `messages/internal_summary.py`,
`messages/final_to_parent.py`, and `tests/real_run.py` (a plain script that runs the episode for real, not pytest).

## 2. What the parent gives (controlled fields only)

`pairwise_blast_assignment_v1`:

- `analysis_kind`: declared, must be `pairwise`.
- `program`: one of `blastp`, `blastn`, `blastx`, `tblastn`, `tblastx`.
- `query_refs`, `subject_refs`: exactly one subject record each, in custody.
- `resource_id`: the one local resource the job runs on.
- `information_unit`: the credit of establishing the pairwise correspondence (positive number).
- `record_refs`: every record the code reads, passed in custody (the two subject records and the sequence artifacts
  they name).

`read_from_parent` is the only place the assignment is read. A record the parent does not hold, or a pair of
molecules the program cannot compare (`blastp` needs two proteins; `blastn` and `tblastx` two nucleotide sequences;
`blastx` a nucleotide query and a protein subject; `tblastn` a protein query and a nucleotide subject), fails the
run with its error: a wrong commission is not an outcome of a unit.

## 3. The steps, all decided by code

Each unit is a defined tool the task's `decide` returns directly from the state of the episode (the system supports a
`decide` that returns an action with no model request):

| Unit | When | What it does |
|---|---|---|
| `launch_job` | no job handed off yet | builds the two FASTA artifacts from the two records, builds the pairwise job with the library, derives the kind from the job and checks it against the declared kind, stages the two FASTA files with the job and launches it through the local-resource inspection point. Returns at handoff; the job detaches. |
| `wait_for_end` | handed off, end not yet seen | the system's defined wait on the job's end event (`native_events.wait`, the end event of the job's own event target, no deadline). It reports readiness only and earns nothing. |
| `fetch_and_grade` | the end event was seen, nothing graded | one coupled step: fetches only the report the job declares through the job service, then grades it into the pairwise sheet of the job's own two operands, keeps the grading with its source and search row, all through custody. |

Then the episode returns controlled values and references. If a unit fails (the launch is refused, the fetch is
refused) the failure is the outcome of that unit and earns nothing; the next decision repeats the step the state
calls for, and the yield controller ends the episode when further units stop being expected to earn.

## 4. Is a real choice left? None for pairwise.

The program, the resource and the two sequences come from the commission. Whether to launch is not a choice: the
episode exists to launch this comparison, and a refused launch is repeated by the same rule. When to fetch is not a
choice either: the end event says the job has ended. Grading is not a choice. So no model request exists in this
episode and it asks the model nothing, in a first run and on resume. A model request would appear only where a real
choice does: for example a variant that lets the model pick the program or the options from a vocabulary, or an
all-vs-all that chooses thresholds. The system still requires the episode to declare an `action` member and the run
to supply a model provider; here the member can never be reached (it fails loudly if it ever is).

## 5. The job, and the declared-versus-derived kind

The job is the library's pairwise job (`blast_pairwise_job_v1`): two FASTA operands and one JSON report, no stdout or
stderr output declared (owner D10). The commission declares `pairwise`; the single derivation function derives the
kind from the job built, and the two must agree before anything launches (owner D9). The episode builds nothing but
pairwise jobs, so a mismatch means a bug in the builder and it fails loudly.

The two FASTA files are staged by the job service into the job's own directory and the job's command names them by
their absolute path there (the directory is `<workspace>/<handle>`, both public). The job record is written to custody
as an artifact by the launch unit, so every later unit and the grading read it from custody.

## 6. Credit (owner D17: only what is gained)

The episode's credit is the information it establishes about the pair; nothing else earns credit. The launch, the wait
and a refused grading earn nothing. The `information_unit` is earned once, when a grading of the pairwise sheet for
the job's own two operands is saved: the correspondence is then known where it was not. The task makes no second
grading, so a repeat cannot earn. A sheet with no aligned residues is also a determination and earns the same unit
("no alignment found" by a local alignment is not absence of homology; the sheet's counts say what was found).
Whether the unit should scale with how much is established is a follow-up for the owner.

## 7. Stopping

Only the yield estimator stops the episode: the completion controller with the `information_unit` as its target; its
cost and uncertainty parameter are this episode's settings (`cost`, `parameters`). The settings also hold
`blast_executable_directory`, where the BLAST programs are. A risk to check in the run: the controller could stop the
episode after the zero-credit units (launch, wait) before the grading unit runs. If so, the stopping rule is this
episode's own and is changed here, in one place.

## 8. The sheet, the score route and E-value

The grading uses the existing pairwise grader and keeps it with the existing retention function, a source record over
the report and the existing search row, so the existing A101 score route reads what it reads today. The controlled
features are read by code from the saved sheet with the existing feature reader: counts and fractions of paired and
identical residues, the native E-value and its search-space context (owner D8), absent when the report does not give
them. Nothing is defaulted.

## 9. What the episode returns upward (controlled values and references)

Always: `credit` and `finding` (whether the job was handed off and graded, its last observed state, the counts of
units that completed or failed, and the saved sheet's controlled features). Selectable: `execution_handoff_refs`,
`execution_job_record_refs`, `execution_blast_graded_refs` (the saved sheet, its source and its search row) and
`execution_completed`. These are the names the generic episodes use, so a parent reads either.

## 10. Why long-running actions would still have children

For a database search, all-vs-all or preparation the job is not a second long. The launch ends at handoff and the job
runs on, possibly for hours on a cluster queue, and the results are wanted later, possibly hours later and not by the
same run of the episode that launched. So those actions keep a launch child (it ends at handoff and returns the
handoff record, which a parent holds across hours) and a results child (it runs later from that record and grades),
and they get a monitor child only for long cluster jobs, where something has to watch the queue and the job's state
over time. The pairwise job needs none of them because the whole life of the job fits inside one run. Not built now.

## 11. What already exists, and what is written

| Needed | Exists | Used by |
|---|---|---|
| Build and compile the pairwise job | `requested_job_from_pairwise` | called |
| Derive and check the analysis kind | `checked_analysis_kind` | called |
| Launch on a local resource, with staged inputs | `execute_on_local_resource` (inspection point), `job_handle`, route `describe` | called |
| Wait on the job's end event | `native_events.wait` (service) | called |
| Fetch and closure rows | `JobAccess.fetch` | called |
| Job rows read from custody | `job_records` readers | called |
| Grading, retention, search row | `grade_blast_result`, `retain_tool_grading`, `SEARCHES` | called |
| Features of the saved sheet | `blast_pairwise_features.saved_grading_features`, `SHEET_FEATURES`, `MEANINGS` | called |
| Stopping | `CompletionYieldController` | called |
| Canonical JSON | `execution_contracts.canonical` | called |
| The grading checks of operands against the report | episode code in the generic results episode (`blast_pairwise_grade`) | copied into this episode and simplified (the job is this episode's own) |
| The wait unit | episode code in the generic monitor (`progress_wait`) | copied and simplified |
| Form fields for the features | episode code in the generic results and head `final_to_parent` (`feature_field`) | copied (a few lines) |
| The three units, the state rule that decides them, the summary, the credit | nothing: each belongs to this episode | written here |

No new library function is needed. One restriction is deliberate: the library's job contract needs an absolute operand
path, so the staged files are addressed by the job directory path (from the public handle and workspace).

## 12. Prediction for the real run

Local resource, real `blastp` 2.17.0+. Query: 76-residue ubiquitin. Subject: the same with one substitution and two
extra residues (78 residues). No model asked.

- Three units in order: `launch_job`, `wait_for_end`, `fetch_and_grade`; zero model calls. Credit per unit 0, 0 and
  the information unit (1.0). The episode ends by its yield controller after the grading, in a few seconds.
- The wait returns on the job's end event (the job ends within about a second).
- Saved sheet: 76 of 76 query residues paired, 76 of 78 subject residues, 75 identical pairs (identity about 0.987),
  one alignment, a native E-value about 3.9e-56 with the search-space context the report gives.
- Returned fields only; the sheet stays in this episode.
- Resume returns the same result and asks nothing.
- The existing A101 score route accepts the saved grading: one comparison, 76 residue pairs.
- Refusals, each failing with its error and no job started: no declared kind; a declared kind outside the vocabulary;
  a query record the commission names but custody does not hold; a protein pair with `blastn`.

## 13. Observed (real runs, 2026-11-20) and comparison with the generic path

Runs: `runs/a101_pairwise_blast_real_1` and `runs/a101_pairwise_blast_real_2` (the second after fixing a bug in my
script that kept two of the four refusal cases from running; the first run's commission is identical).

Predicted against observed:

- Three units `launch_job`, `wait_for_end`, `fetch_and_grade`, zero model calls: observed exactly (0 model calls in the
  journal, on disk and on resume). The wait woke on the job's end event (`state_changed`).
- Credit 0, 0, 1.0 and the controller stopped at the grading: observed (`ended_by: yield_stop`, 3 units). The risk that
  the controller would stop on the two zero-credit units did not occur.
- Sheet: 76 of 76 query residues paired, 76 of 78 subject residues, 75 identical pairs, identity 0.9868, one alignment,
  E-value 3.9499e-56 with effective search space 4899, effective alignment length 7, Karlin parameters 0.267, 0.041,
  0.14 and threshold 10: observed exactly, read by code from the saved sheet.
- Returned fields only (credit, finding, the references); the job state was `finished`, read from the closure row; the
  only job record is the closure (no check unit, so no check row).
- Resume returned the same result and asked nothing: observed.
- The existing A101 score route accepted the saved grading: one comparison, bits 153.68, 76 residue pairs: observed.
- Refusals, each failing with its error and no job started (one job directory exists in the whole run): no declared
  kind (`missing_field:analysis_kind`); a kind outside the vocabulary (`differs_from_declared_value`); a query record
  custody does not hold (`entry_record_not_in_store`); a protein pair with `blastn`
  (`pairwise_blast_molecules_not_comparable`).

Not exercised by a real run: the grader's refusal of a report of other sequences (the commission cannot tamper with
it, since the episode builds the job itself); that code is a copy of the generic episode's and is untested here. A fetch
refused because results are not yet available (the wait on the end event made the fetch succeed the first time).

Comparison with the generic path, from the actual files:

| | generic (launch leaf + monitor + results episode) | pairwise_blast |
|---|---|---|
| episodes | 3 (plus the head that commissions them) | 1, no children |
| files / lines (py, no tests) | 26 files, 2,426 lines (269 + 665 + 1,492) | 8 files, 438 lines |
| model calls for the same comparison | 4 in the launch and results chain I ran (1 + 3), plus 4 to 7 per monitor visit | 0 |
| commissions a parent must build | 3 (launch, monitor, results), none built yet by the head | 1 |
| places that carry the pairwise analysis | 6 files of the results episode plus the shared contract and features | one folder plus the same shared library |

Removed: two episodes, all child commissioning, every model call, about 1,990 lines. Not removed: the pairwise path in
the generic results episode (follow-up).

What was harder or worse:

- The library's job contract needs an absolute operand path, so the staged files are addressed as
  `<workspace>/<handle>/<name>`. That couples the episode to the route's directory layout (both pieces are public).
- About 60 lines (the grading unit, the feature form) are copies of the generic episodes' code. That is what private
  bindings intend, and it is what to expect each time a similar episode is added.
- The system requires an `action` member and a model-provider collaborator even for an episode that never asks a model.
  `action` here can never be reached and raises; the run supplies a provider it never uses.
- No monitor means no check rows, no progress credit and no estimate-table record of how long the job took; the job
  state comes from the closure row only. For a one-second job nothing is lost; for a long job it would be.
- The settings carry `blast_executable_directory`: the location of the programs is configuration an episode now reads.
