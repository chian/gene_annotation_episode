# pairwise_blast: one self-contained action episode (pilot, 2026-11-20)

Binding path: `sequence_homology_evidence/pairwise_blast`. Pilot of the owner's decision: an episode named for the
action it performs, with everything that decides how it behaves (its goal, prompt, tools, grader choice, credit,
stopping rule, return) in its own folder, so it is obvious where to tune. No runtime assembly from the knowledge or
instruction libraries, no routing by table or by family branching. The episode's identity is the declaration of the
analysis (a pairwise BLAST: one query sequence against one subject sequence); the job it builds is checked against
that declaration. The generic episodes (local_job_execution, execution_progress_assessment,
execution_result_acquisition, the A101 head) are left unchanged; this episode copies what it needs from them and the
copies diverge.

## 1. The tree: one episode, no children

The suggestion was a head with private children for launching, monitoring and fetching plus grading. I decided
against children for this pilot, for these reasons:

- Everything the three children do is a call on the job service (`launch`, `check`, `fetch`) plus one grading
  function. Each is already a library function. A child episode around a single library call adds a folder of ten
  files, a commission and a return form, and nothing a decision needs.
- A local pairwise BLAST starts as a detached job (the launch returns at the handoff and the job runs on without the
  episode) and ends within seconds to minutes. Nothing in it needs an episode to outlive the parent's turn.
- With no children there is one prompt, one set of tools, one credit and one stopping rule to tune.

Where children would be needed: the same analysis on a cluster, where the job waits in a queue for hours. That
variant would be a copy of this episode that commissions launch, monitor and result children. It is not part of
this pilot.

Files (an episode with no children has no `msg_to_child.py` and no `read_from_child.py`): `goal.py`, `task.py`,
`credit.py`, `yield_estimator.py`, `episode.py`, `messages/read_from_parent.py`, `messages/internal_summary.py`,
`messages/final_to_parent.py`, and `tests/real_run.py` (a plain script that runs the episode for real, not pytest).

## 2. What the parent gives (controlled fields only)

`pairwise_blast_assignment_v1`:

- `analysis_kind`: declared, must be `pairwise`.
- `program`: one of `blastp`, `blastn`, `blastx`, `tblastn`, `tblastx`.
- `query_refs`: exactly one subject record in custody (a record with a sequence).
- `subject_refs`: exactly one subject record in custody (the sequence searched against).
- `resource_id`: the one local resource the job runs on.
- `information_unit`: the credit of establishing the pairwise correspondence (positive number).

`read_from_parent` is the only place the assignment is read. It checks that each reference list has one entry. The
records are not read there. A record the parent does not hold, or a pair of molecules the program cannot compare
(`blastp` needs two proteins; `blastn` and `tblastx` two nucleotide sequences; `blastx` a nucleotide query and a
protein subject; `tblastn` a protein query and a nucleotide subject), fails the commission with its error.

## 3. What the episode decides, with which defined actions

The model chooses exactly one action per unit, with controlled arguments. It writes no command and no job. Code
builds the job from the commission.

| Action | Offered | What code does |
|---|---|---|
| `launch_job` (resource_id) | until a job has been handed off | builds the two FASTA artifacts from the two records, builds the pairwise job with the library, derives the kind from the job and checks it against the declared kind, stages the two FASTA files with the job and launches it through the local-resource inspection point. Returns at handoff. |
| `check_job` | once handed off | one status request through the job service (writes a check row) |
| `fetch_report` | once handed off and not closed | fetches only the one report file the job declares (the service refuses while the job has not ended: a failed unit, the job stays open) |
| `grade_report` | once the report is held and no valid grading is saved | grades the report into the pairwise sheet of the job's own two operands and keeps the grading |

A failure of a unit is an outcome of the unit, with the credit it earned (none). A wrong commission is not an
outcome: it fails the run with its error.

## 4. The job, and the declared-versus-derived kind

The job is the library's pairwise job (`blast_pairwise_job_v1`): two FASTA operands and one JSON report, no stdout or
stderr output declared (owner D10). The commission declares `pairwise`; the single derivation function derives the
kind from the job built and the two must agree before anything launches (owner D9). The episode builds nothing but
pairwise jobs, so a mismatch means a bug in the builder, and it fails loudly.

The two FASTA files are staged by the job service into the job's own directory and the job's command names them by
their absolute path there (the directory is `<workspace>/<handle>`, both public). The job record itself is written to
custody as an artifact by the launch unit, so every later unit and the grading read it from custody.

## 5. Credit (owner D17: only what is gained)

The episode's credit is the information it establishes about the pair, and nothing else earns credit: the launch, a
check and a fetch earn nothing, a refused grading earns nothing, and a repeat of a grading already saved earns
nothing. `information_unit` is earned once when a grading of the pairwise sheet for the job's own two operands is
saved: the sequences' correspondence is then known where it was not. A sheet with no aligned residues is also a
determination and earns the same unit; "no alignment found" by a local alignment is not absence of homology, and the
sheet says so through its counts. Whether the unit should scale with how much is established (for instance the
paired fraction) is a follow-up for the owner.

## 6. Stopping

Only the yield estimator stops the episode. It is the completion controller with the `information_unit` as its
target; its cost and uncertainty parameter are this episode's settings (`cost`, `parameters`). The settings also hold
`blast_executable_directory`, where the BLAST programs are.

## 7. The sheet, the score route and E-value

The grading uses the existing pairwise grader and keeps it with the existing retention function, a source record
over the report, and the existing search row. So the existing A101 score route reads exactly what it reads today.
The controlled features are read by code from the saved sheet with the existing feature reader: counts and
fractions of paired and identical residues, the native E-value and its search-space context (owner D8), absent when
the report does not give them. Nothing is defaulted.

## 8. What the episode returns upward (controlled values and references)

Always: `credit` and `finding` (whether the job was handed off, its last observed state, the counts of units that
completed or failed, and the saved sheet's controlled features). Selectable: `execution_handoff_refs`,
`execution_job_record_refs`, `execution_blast_graded_refs` (the saved sheet, its source and its search row) and
`execution_completed`. These are the names the generic episodes use, so a parent reads either.

## 9. What already exists, and what is written

| Needed | Exists | Used by |
|---|---|---|
| Build and compile the pairwise job | `requested_job_from_pairwise` | called |
| Derive and check the analysis kind | `checked_analysis_kind` | called |
| Launch on a local resource, with staged inputs | `execute_on_local_resource` (inspection point), `job_handle`, route `describe` | called |
| Status, fetch, closure rows | `JobAccess.check`, `JobAccess.fetch` | called |
| Job rows read from custody | `job_records` readers | called |
| Grading, retention, search row | `grade_blast_result`, `retain_tool_grading`, `SEARCHES` | called |
| Features of the saved sheet | `blast_pairwise_features.saved_grading_features`, `SHEET_FEATURES`, `MEANINGS` | called |
| Strict action schema to the model, decode | `action_transport.generation_schema`, `decode_response` | called |
| Rejection feedback | `rejection_feedback` | called |
| Stopping | `CompletionYieldController` | called |
| Canonical JSON, digests | `execution_contracts.canonical`, `digest` | called |
| The grading unit (checks of operands against the report) | episode code in the generic results episode (`blast_pairwise_grade`) | copied into this episode and simplified (the job is this episode's own) |
| Form fields for the features | episode code in the generic results and head `final_to_parent` (`feature_field`) | copied (a few lines) |
| The five actions, the prompt, the summary, the credit | nothing: each belongs to this episode | written here |

No new library function is needed. One restriction is deliberate: the library's job contract needs an absolute
operand path, so the commission's staged files are addressed by the job directory path (derived from the public
handle and workspace).

## 10. Prediction for the real run

Local resource, real `blastp` 2.17.0+, real model. Query: 76-residue ubiquitin. Subject: the same with one
substitution and two extra residues (78 residues).

- Four model decisions in order `launch_job`, `check_job` (the job is tiny, so likely `finished` already),
  `fetch_report`, `grade_report`; at most one extra decision. Credit per unit 0, 0, 0 and the information unit
  (1.0) at the grading. The episode ends by its yield controller after the grading.
- Saved sheet: 76 of 76 query residues paired, 76 of 78 subject residues, 75 identical pairs (identity about 0.987),
  one alignment, a native E-value about 3.9e-56 with the search-space context the report gives.
- Returned fields only: credit, finding, the references; the sheet stays in this episode.
- Resume asks the model nothing and returns the same result.
- The existing A101 score route accepts the saved grading: one comparison, 76 residue pairs.
- Refusals, each failing with its error and no job started: no declared kind; a declared kind outside the
  vocabulary; a query record the commission names but custody does not hold; a protein pair with `blastn`.

A risk I cannot settle by reading: the completion controller may stop the episode after the zero-credit units
(launch, check, fetch) before the grading is chosen. The run shows it. If so, the stopping rule is this episode's own
and is changed here, in one place.

## 11. Comparison with the generic path

Measured after the run: files and lines needed here against the four generic episodes plus their commissioning, the
number of places a change to the pairwise analysis touches, and anything that was harder. The pairwise path inside the
generic results episode is not removed (follow-up).
