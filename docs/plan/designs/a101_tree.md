# A101: what we want (the tree, tools and child episodes, local first)

Written 2026-11-20 by Claude from the owner's statements. Lines marked **[owner]** are the owner's rulings; the rest
are my decisions from the owner's criteria, and the owner can strike any of them. This record replaces
`pairwise_blast_episode.md`, `a101_head_wiring.md`, `blast_database_preparation_episodes.md`, `all_vs_all_subtree.md`
and `long_jobs_hpc_api_monitor.md`, which were built on a wrong premise ("code-decided" episodes) and are deleted.

## The rules this tree follows

- **[owner]** There is no such thing as a code-decided episode. In every episode the model is the router: it chooses
  one defined action per decision, with controlled values, and code carries it out.
- **[owner]** Anything nested in the tree is a child episode. A leaf is a tool or a child episode.
- **[owner]** Children exist because they iterate, launch long jobs that detach (tools are tied to a turn), and let
  the communication of each be controlled separately.
- **[owner]** `pairwise_blast` is a tool call.
- **[owner]** Grading is automatic: it is not an episode and not a separate choice. Graders fill sheets; subscoring
  sheets score; scoring sheets weigh.
- **[owner]** For a long job: the launching child ends at the handoff; the parent later commissions the monitor child
  and the result-acquisition child (ruling of 2026-11-18).
- **[owner]** The kind of BLAST use is declared in the commission and also derived from the job; a mismatch fails.
- **[owner]** Credit is only for what is gained. Messages between episodes are controlled data only.
- **[owner]** A real run is a command-line run through `episode_runtime`. No `tests/` folders, no harness scripts.
- **[owner]** Order of work: one pattern in one branch first, then parallelize the repeats. No HPC first. HMMER
  after BLAST.
- The system packages (`episode_runtime`, `method_loop`, `yield_control`) are not changed to fit this design.

## The tree (the owner's approved view; my marks on the right)

```
sequence_homology_evidence                    HEAD: holds the records, decides which analysis to commission next
│
├─ pairwise_blast                             TOOL of the head [owner]: run, fetch, grade in one unit
│
├─ blast_database_preparation                 CHILD EPISODE: builds or masks a database; returns a prepared-data record the head holds and passes on
│   ├─ launch_local                           TOOL of this episode: a small set ends within the turn; build and check in one unit
│   ├─ launch_hpc                             CHILD EPISODE: starts a long job that detaches; ends at the handoff        (last)
│   ├─ monitor                                CHILD EPISODE: iterates visits on a long job                               (last)
│   └─ results                                CHILD EPISODE: acquires a long job's result; the check is automatic in its fetch   (last)
│
├─ database_blast                             CHILD EPISODE: one query vs a reference set: identification
│   ├─ launch_api                             CHILD EPISODE: submits to the hosted service; the search detaches; ends at the handoff
│   ├─ launch_hpc                             CHILD EPISODE: custom database (a prepared-data record named by the head)  (last)
│   ├─ monitor                                CHILD EPISODE: iterates visits on the search
│   └─ results                                CHILD EPISODE: fetches the report; grading into both sheets is automatic in its fetch
│
├─ all_vs_all_blast                           CHILD EPISODE: a set vs itself: relationships, clusters, family context
│   ├─ launch_local                           TOOL of this episode: a small set ends within the turn; run, fetch, grade, cluster in one unit
│   ├─ launch_hpc                             CHILD EPISODE: chunked large sets                                          (last)
│   ├─ monitor                                CHILD EPISODE                                                              (last)
│   └─ results                                CHILD EPISODE: graph, clustering and family-context sheet automatic in its fetch   (last)
│
└─ hmmer                                      after the BLAST part
```

Why each leaf is what it is:

- **A local leaf is a tool.** The owner ruled that `pairwise_blast` is a tool call, and it is a local job that ends
  in about a second. A small local database build and a small local all-vs-all are the same kind of work: the job
  ends within the turn, so nothing detaches and there is nothing to monitor or to acquire later. The tool refuses a
  set above the local size bound (the model picks, code refuses); larger sets go to the cluster leaves.
- **A launch on a service or the cluster, a monitor, and a result acquisition are child episodes.** They are the
  owner's three reasons: the job detaches for minutes or hours, the monitor iterates over visits, and each has its
  own controlled messages. This is also the owner's ruling of 2026-11-18.
- In a tool, and in a results child, fetching and grading are one action. The model never chooses "grade".

## What each local piece is

### `pairwise_blast`, a tool of the head

- **The model supplies** (controlled values): the program (`blastn`, `blastp`, `blastx`, `tblastn`, `tblastx`), the
  query (a subject of the head's scope), the subject (another subject record the head holds), a bound local
  resource.
- **Code does, as one unit,** through one library function: read both sequences through custody; build the A101
  pairwise job with the existing contract; check that the kind derived from the job is `pairwise`; launch it on the
  local resource; wait for the job's end; fetch the one report the job declares; grade it with the existing pairwise
  grader; keep the sheet through custody; return the status, the references of the graded records and the sheet's
  controlled features (paired and identical residues, both lengths, E-value with its search-space context).
- **A failure** (job failed, report of other sequences, molecule the program does not take) is a failed outcome with
  its code. It enters the head's iterator; the model decides what to do next.
- **Credit** is the head's own: the native sequence correspondence read from the graded sheets it holds. A repeated
  comparison adds no correspondence, so it earns nothing.
- The working logic for the steps exists in git history (commit `910c8cc38`, the deleted
  `pairwise_blast/task.py`): it becomes the library function. Its episode wrapper is not restored.

### `blast_database_preparation`, a child episode (local part)

- **The head commissions it** with: the kind (`database_build` or `masking`), the molecule type, the input
  sequence-set record, the kind's switches and numeric parameters, and its credit units.
- **Its model chooses among defined actions:** build on a bound local resource (the `launch_local` tool), or hold
  with a reason from a fixed vocabulary. The cluster actions (commission `launch_hpc`, `monitor`, `results`) are
  added last.
- **The `launch_local` tool does, as one unit:** build the job from the commission with the existing preparation
  contract and driver; check the derived kind; launch; wait for the end; fetch the receipt; decide `usable` with the
  existing receipt evaluation; write the prepared-data record through custody.
- **Credit:** earned when a usable prepared-data record is newly established; a repeat earns nothing.
- **Returns:** credit; a finding (state `usable`, `failed`, `incomplete` or `not_launched`; sequence count; letters;
  file count); selectable: the prepared-data reference.
- The head holds the reference and names it in later commissions of `database_blast` and `all_vs_all_blast`.

### `all_vs_all_blast`, a child episode (local part)

- **The head commissions it** with: the sequence-set record (with controlled function labels of its members), the
  thresholds (minimum identity, coverage of both sequences) as numbers in ranges, the edge rule from a fixed
  vocabulary, the target whose family context is wanted, and its credit unit.
- **Its model chooses among defined actions:** run on a bound local resource (the `launch_local` tool), or hold.
  Cluster actions are added last.
- **The `launch_local` tool does, as one unit:** build the job with the existing all-vs-all contract; check the
  derived kind; launch; wait; fetch the report; build the similarity graph; run the clustering step with its
  parameters recorded; build the family-context sheet; keep them through custody. A run with missing pieces is
  `incomplete`, never "no relatives".
- **Credit:** earned when the family context of the target is newly established.
- **Returns:** credit; a finding (closeness to same-function members, farness from different-function members, core
  or outlier, separation between clusters, cluster size, annotation agreement, independent members); selectable:
  references to the sheet, the graph and the clusters.

### `database_blast`, a child episode (not local)

Its children `launch_api`, `monitor` and `results` are child episodes; each asks its model to choose among its own
defined actions (for a launch: submit or hold; for a monitor: check, read a log window, wait; for results: check
status, fetch, where the fetch grades into the identification sheet and the correspondence sheet). The reference-only
`old_*` folders hold model-routed examples of each (`old_execution_job_submission/local_job_execution` for a launch,
`old_execution_progress_assessment` for a monitor, `old_execution_result_acquisition` for results). It is built after
the local part, and before any cluster leaf.

## Order of work

1. **Pattern A:** the `pairwise_blast` tool on the head, the real entry (`run` and `resume` commands, design in
   `real_entry.md`), and a real run from the command line: the head's model calls the tool, `blastp` runs, the sheet
   is saved, the head's credit reads it, resume asks the model nothing.
2. **Pattern B:** `blast_database_preparation` as a child episode with its `launch_local` tool; the head's child
   wiring (slot, commission fields, `msg_to_child`, `read_from_child`); a real run through the head.
3. **In parallel, the repeats:** `all_vs_all_blast` local (a copy of pattern B) and `database_blast` through the
   hosted service (pattern C: launch, monitor and results children).
4. **Last:** the cluster leaves, then HMMER.

## Other records

- Kind-level designs that stand, to be read for what each analysis measures: `database-search.md`, `all_vs_all.md`,
  `blast_database_preparation.md`. Where they describe episode shapes, this record governs.
- The library modules for these kinds are committed but mostly unrun; each is checked by the real run of the piece
  that calls it.
- Functional regions and joint credit are deferred: `../DEFERRED_functional_regions_joint_credit.md`.

## Pattern A build notes (step zero, written before the code)

What already exists for each thing Pattern A needs; anything that exists is called, not rewritten.

| Needed | What exists (called) | What is written new |
|---|---|---|
| Read the two sequences through custody | `ctx.store.get`, `ctx.store.get_artifact` (the tool's custody-scoped store) | nothing |
| Build the pairwise job, compile its command | `forms/sequence_homology_evidence/blast_pairwise_job.requested_job_from_pairwise` | nothing |
| Declared kind against the kind derived from the job | `forms/sequence_homology_evidence/blast_analysis_kind.checked_analysis_kind` | nothing |
| Launch on the local resource, wait for the end, fetch the files | `jobs/resource_local.execute_on_local_resource(..., wait=True)` (the one inspection point; it calls `JobAccess.run`) | nothing |
| Where the staged files sit | `episode_runtime.job_access.job_handle` and `JobAccess.describe` | nothing |
| Grade the report | `grading/similarity_search/sequence_homology_evidence/blast_graders.grade_blast_result` (mode `pairwise`) | nothing |
| Keep the sheet in custody | `grading/sequence_homology_evidence/tool_grading_artifacts.retain_tool_grading`, `store.put('source', ...)`, the declared search table `native_correspondence.SEARCHES` | nothing |
| Controlled features of the sheet | `grading/similarity_search/sequence_homology_evidence/blast_pairwise_features.grading_features` | nothing |
| The head's credit from the saved sheet | the head's `credit.py` (`A101SequenceCredit`, unchanged) | nothing |
| One function that does the comparison as one unit | the step logic of the deleted episode (commit `910c8cc38`, `pairwise_blast/task.py`: `launch_job`, `wait_for_end`, `fetch_and_grade`) | `tools/similarity_search/sequence_homology_evidence/pairwise_blast_comparison.py`: the three steps joined into one function; `wait=True` replaces the separate wait unit |
| The head offers the tool and acts on the choice | the head's `selection_schema`, `decide`, `action`, `TOOLS` | the `pairwise_blast` option, description and tool function in the head's `task.py`; its outcome row in `messages/internal_summary.py` |
| Start a run from the command line | `episode_runtime.link` / `resume`, `RunJournal`, `ModelProvider`, `job_services`, `Store`; the CLI's `init` | `gene_annotation_episode/run_command.py` (`run`, `resume`, `report`) and their subcommands in `cli.py` |
| The proposed annotation as a record | `Store.put('hypothesis', ..., origin='caller')` (the caller's own record type and origin; no command reaches it) | CLI subcommand `propose-annotation` (one `Store.put`) |
| The frozen process and tool libraries the head's settings name | `SequenceHomologyEvidenceLibrary.freeze`, `ScientificToolLibrary.freeze`, `resolve_tool_info` (no command reaches them) | CLI subcommand `freeze-libraries` (calls those three and prints the selection) |

Two things found while reading that the real run depends on:

- The root sends the head four credit units (`handoff_unit`, `acquired_record_unit`, `information_unit`,
  `completion_target`). The head's `read_from_parent` currently accepts none, so the root's commission would fail.
  The head must accept what its real parent sends.
- The root passes back to the head, on a later visit, only the records the head returned to it, and selects
  `committed_record_refs` and `execution_handoff_refs`. For the head's credit to continue on a later visit, the
  graded records its credit reads must be among the records it returns. They go into `committed_record_refs`.

### Checked against the tool registry (the library's `ToolRegistry`, reached by `execute_selected_tool`)

The registry already has tools of nearly this shape, so each was read before anything was kept:

| Existing in the registry | What it does | Why `pairwise_blast` does not go through it as is |
|---|---|---|
| `sequence.align` (`_align_one`) | aligns two held sequences with the Biopython aligner in a short local job, grades, keeps a source and an `alignment` observation | it is not BLAST, and it runs its job with the registry's own blocking runner (`run_local_job_async`), not through the job service; the registry is handed only the Store, so it cannot reach `job_access` or name a bound resource |
| `public.blast.search` / `public.blast.collect` (`_import_blast`) | imports a result of the public BLAST service: grades it in database mode, keeps a source and one `comparison` observation per alignment | bound to a public-service snapshot and to the database sheet (`shared_hsp_component` refuses a pairwise sheet) |
| `_source`, `_observation` | the registry's private record writers | methods of a registry instance; `_source` takes a body or a service snapshot, not an artifact already fetched |

So `pairwise_blast` is the head's own defined tool, and its one library function is a composition of existing
functions: `requested_job_from_pairwise`, `checked_analysis_kind`, `execute_on_local_resource`,
`grade_blast_result`, `retain_tool_grading`, `grading_features`, `blast_search.hsp_row`, and the registry module's
`measurements`, `number`, `ref`. It produces the same records the registry's BLAST import produces (a source with
its grading artifact and one `comparison` observation per alignment, addressed to its graded cell), which is what
the A101 credit reads.

One correction to this record, found in the code: the head's credit does not rise from a saved sheet alone. The
A101 credit (`native_correspondence.read_details`, given the proposed annotation) scores only the graded cells of
observations that an assessment relates to the proposed annotation with relation `strengthens` and an established
extent. So after a `pairwise_blast` unit the credit is unchanged; it rises when the model commits a reasoning unit
that assesses the proposed annotation against the comparison's observation.

### Pattern A: the first real run (prediction, written before the run)

Workspace `runs/a101_patternA_ws_1`, made with the command line only: `init` registered a two-record protein FASTA (the
76-residue ubiquitin target and a 78-residue reference that differs by one substitution and two added residues);
`propose-annotation` registered the caller's proposed annotation (the target is of the functional family of the
reference); `freeze-libraries` froze the process library and an empty tool library and printed the A101 selection.
The commission file is what the root sends the head: that selection, the proposed annotation, the scope (the
target), the reference and its sequence as evidence, the whole-axis task, the four credit units, and the root's
selection of `committed_record_refs` and `execution_handoff_refs`.

Predicted:

1. The head's first decision: the model chooses the tool `pairwise_blast` with `blastp`, the target as query, the
   reference as subject, the resource `local`. (The only other choice offered is a reasoning commit.)
2. That unit completes: one alignment; 76 of 76 query residues paired, 76 of 78 reference residues, 75 identical;
   E-value about 3.95e-56 with effective search space 4899; one `comparison` observation; four records kept (source,
   grading artifact, search row, observation).
3. The credit after that unit is still 0.0: no assessment relates the observation to the proposed annotation yet.
4. The model then commits a reasoning unit with an assessment of the proposed annotation against the observation.
   If its relation is `strengthens` and its extent is established, the credit rises to the native correspondence of
   the target, a value near 1 (I expect between 0.9 and 1.0; I have not derived the exact value). If the model
   does not write such an assessment, the credit stays 0.0.
5. The yield controller (bounded quality, cutoff 0.01, maximum 1.0) ends the episode within a few units after the
   credit rises, or after a few units that earn nothing.
6. The return: the credit, the finding with the target's sheet features, and `committed_record_refs` holding the
   graded records and the committed reasoning records.
7. `resume` asks the model nothing and returns the same result.

### Pattern A: what the first two runs showed, and the prediction for the third (written before it)

- **Run `a101-patternA-1` (`runs/a101_patternA_run_1`): not predicted.** The model's first call was right (`blastp`,
  the target, the reference, `local`), but every `pairwise_blast` unit was refused before BLAST started
  (`whole_workflow_budget_unavailable`, reason `native_output_outside_workflow_run`, `retryable` false): my services
  file put the local resource's job folder outside the launcher's run directory of that command. The model made the
  same call 21 more times; the credit stayed 0.0; I stopped the run. Two causes, both mine: the configuration, and a
  tool whose offer let a call that cannot succeed be repeated.
- **Run `a101-patternA-2` (`runs/a101_patternA_run_2`): not predicted.** With the job folder inside the run directory
  BLAST ran, and the unit then raised `native_blast_requires_native_tool_source`: the Store admits an observation
  with a BLAST alignment address only on a source of the public BLAST provider. The run failed with that error
  after one model call.
- **Changes.** The observation is an `alignment` observation in the shape of the registry's `sequence.align` (no
  address field). The tool's arguments are `query_ref`, `reference_ref`, `program`, `resource_id`; only programs
  that compare the two molecules are offered; a comparison is offered once (not again after it completed or failed
  with `retryable` false); a failed outcome shows its code and `retryable`. The local resource's job folder in the
  services file is inside the launcher's run directory of the command (`real_entry.md`).

Predicted for run `a101-patternA-3`:

1. First decision: `pairwise_blast` with the target as `query_ref`, the reference as `reference_ref`, `blastp` (the
   only program offered for two proteins) and `local`.
2. That unit completes in one shot: one alignment; 76 of 76 query residues paired, 76 of 78 reference residues, 75
   identical; E-value about 3.95e-56 with effective search space 4899; one `alignment` observation; four records
   kept. Credit after it: 0.0.
3. `pairwise_blast` is not offered again. The model's next units are reasoning commits. If one assesses the
   proposed annotation against the observation with relation `strengthens` and an established extent, the credit
   rises to a value near 1; otherwise it stays 0.0.
4. The yield controller ends the episode. `resume` asks the model nothing and returns the same result.

### Pattern A: what the third run showed, the owner's rulings on it, and the prediction for the fourth

- **Run `a101-patternA-3` (`runs/a101_patternA_run_3`).** Call 1 was `pairwise_blast` with a correct request and the
  unit completed in one shot (76 of 76 query residues paired, 75 identical, E-value 3.9499e-56, effective search
  space 4899, one alignment observation), as predicted. The credit stayed 0.0 until call 2, a reasoning commit that
  assessed the observation, raised it to 0.947; the model then kept revising its assessment and the credit went up
  and down with it. I stopped the run after 20 model calls. The estimator at cutoff 0.01 had not stopped.
- **Owner's rulings (2026-11-20).** The head fills out one JSON; one deterministic function checks it and either
  returns the things to fix or the job runs; a correct JSON must simply work. Grading is automatic: no reasoning
  commit assesses anything, and none switches the credit on or off.
- **Changes.** `check_pairwise_request` (in the tool's library module) is the one check; the head's `action` rejects
  a request with problems (`Rejected`, so no unit is made) and the feedback lists the things to fix. The running
  function no longer checks inputs; a failure after a passed check is a fault of the environment, `failed` and not
  retryable. The head's credit no longer hands the proposed annotation to the native-correspondence projection, so
  every graded comparison the head holds counts as soon as its sheet is saved (the projection given a proposed
  annotation counts only assessed observations; without it, it scores every held graded observation over the scope).
  Nothing was added to the scoring: the same `read_details` and `compile_native_sheet` are called.
- **Setting.** The head's yield cutoff for these runs is 0.1 (it was 0.01): the native correspondence is at most
  1.0, a unit is worth making only if it can add at least 0.1, and after a comparison that gives 0.947 at most
  0.053 remains.

Predicted for run `a101-patternA-4` (a fresh workspace, `runs/a101_patternA_ws_2`, same inputs):

1. Call 1: the `pairwise_blast` request with the target as `query_ref`, the reference as `reference_ref`, `blastp`,
   `local`. The check finds nothing to fix. The unit completes in one shot with the same features as in run 3.
2. The credit right after that unit is 0.947, with no reasoning commit.
3. The yield estimator ends the episode after that unit (at most 0.053 remains, below the cutoff 0.1): one unit,
   one model call. If its estimate is not bounded by the remaining amount it may allow one more unit.
4. The return: credit 0.947, the target's sheet features, and `committed_record_refs` holding the source, the
   grading artifact, the search row and the observation.
5. `resume` asks the model nothing and returns the same result.
