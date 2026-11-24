# A101: the tree (tools and child episodes), as the code stands

HEAD = `gene_annotation_episode/episodic_workflow/root/sequence_homology_evidence`; LIB =
`gene_annotation_episode/episodic_workflow/episode_support`. Read from `HEAD/task.py` and each child's `task.py` on 2026-11-21.
Lines marked **[owner]** are the owner's rulings; the rest are decisions made from the owner's criteria, and the owner can strike
any of them.

## The rules this tree follows

- **[owner]** There is no such thing as a code-decided episode. In every episode the model is the router: it chooses one defined
  action per decision, with controlled values, and code carries it out.
- **[owner]** Anything nested in the tree is a child episode. A leaf is a tool or a child episode.
- **[owner]** Children exist because they iterate, launch long jobs that detach (tools are tied to a turn), and let the
  communication of each be controlled separately.
- **[owner]** `pairwise_blast` is a tool call.
- **[owner]** Grading is automatic: it is not an episode and not a separate choice. Graders fill sheets; subscoring sheets score;
  scoring sheets weigh.
- **[owner]** The kind of BLAST use is declared in the commission and also derived from the job; a mismatch fails.
- **[owner]** Credit is only for what is gained. Messages between episodes are controlled data only.
- **[owner]** A real run is a command-line run through `episode_runtime`. No `tests/` folders, no harness scripts.
- **[owner]** Order of work: one pattern in one branch first, then parallelize the repeats. No HPC first. HMMER after BLAST.
- The system packages (`episode_runtime`, `method_loop`, `yield_control`) are not changed to fit this design.

## The tree

```
sequence_homology_evidence                    HEAD: holds the records, decides what to run or commission next
│
│  tools of the head (HEAD/task.py TOOLS)
├─ reason                                     commits a typed scientific interpretation (Store.commit_reasoning)
├─ execute_selected_tool                      runs a tool the commission selected, through the library's ToolRegistry
├─ pairwise_blast                             TOOL: one query against one reference sequence on a local resource: run, fetch, grade in one unit
├─ hmmer_profile_scan                         TOOL: one protein against a profile database (HMMER hmmscan) on a local resource: run, fetch, grade in one unit
│
│  child episodes of the head (HEAD/task.py CHILD_SLOTS)
├─ bvbrc_blast                                CHILD: one protein query against the precomputed BV-BRC database through the BV-BRC application service (Homology)
│   └─ tools of the child: estimate, launch, fix, monitor, extract
├─ bvbrc_msa                                  CHILD: the target aligned with sequences of several candidates of a graded search (MSA application, Muscle)
│   └─ tools of the child: estimate, launch, fix, monitor, extract
├─ bvbrc_metacats                             CHILD: a held alignment tested with MetaCATS; confirms the candidates' conserved sites
│   └─ tools of the child: estimate, launch, fix, monitor, extract
├─ all_vs_all                                 CHILD: the target and sequences of several candidates searched against themselves with BLAST+ on a local resource and clustered with MCL
│   └─ tools of the child: prepare_database, all_vs_all_blast, cluster, commit_clustering, hold
│
└─ hmmer                                      folder holds only __init__.py: no HMMER child episode exists; the head's HMMER use is its hmmer_profile_scan tool
```

`all_vs_all` is declared in the head's `CHILD_SLOTS` in the working tree, with its commission fields, check and description in
`HEAD/task.py`; the agent wiring it had not committed the head's files when this was written, and no note records a real run of it
through the head (`all_vs_all_episode.md` is its own note).

Not in the tree: the five `old_*` folders under HEAD (the old generic launch, monitor, result-acquisition and resource-work
episodes) are reference only and are not run. Cluster (HPC) leaves are not built. Functional regions and joint credit are deferred:
`../DEFERRED_functional_regions_joint_credit.md`.

Why each leaf is what it is:

- **A job that ends within the turn is a tool.** `pairwise_blast` and `hmmer_profile_scan` are local jobs that end in seconds, so nothing
  detaches and there is nothing to monitor or acquire later. The tool refuses a call that cannot succeed (the model picks, code refuses).
- **A job on an outside service is a child.** The three BV-BRC children detach for minutes, iterate over status visits, can be parked and
  resumed, and have their own controlled messages. They share one shape and one library module (`bvbrc_blast_episode.md`).
- **A multi-step analysis the model tunes is a child.** `all_vs_all` has its own steps (database, matrix, clustering tries, one committed
  clustering) that the child's model chooses among; each step is a one-shot tool.
- In a tool and in a child's `extract`, fetching and grading are one action. The model never chooses "grade".

## What each piece is

### `pairwise_blast`, a tool of the head

- **The model fills out** one request (controlled values): `query_ref` (a sequence of the head's scope), `reference_ref` (another sequence
  record the head holds), `program` (`blastp`, `blastn`, `blastx`, `tblastn`, `tblastx`) and `resource_id` (a bound local resource).
- **One check, then one unit.** `check_pairwise_request` checks the request against what the episode holds and the bound resources before
  anything runs; a request with problems is rejected with the things to fix and no unit is made. A request that passes runs as one unit
  (`pairwise_blast_comparison`: build the job, check the kind derived from the job against the declared one, launch on the local resource,
  fetch the report, grade it, keep the sheet through custody). A failure after a passed check is the environment's: `failed`, not retryable.
- **Credit.** The reference sequence is a candidate of vocabulary `reference_sequence`; the comparison is the test `pairwise:<program>@<source>`.
  It is counted the moment its sheet is saved; no reasoning commit is needed. A comparison already held is refused by the check.

### `hmmer_profile_scan`, a tool of the head

The same shape: three fields (`query_ref`, `database`, `resource_id`), `check_profile_scan_request`, one unit (`hmmer_profile_scan`). Each
matched family is a candidate of vocabulary `profile_family`; the test is `profile_scan:<database>@<source>`.

### The three BV-BRC children

One shape (`bvbrc_blast_episode.md`): `estimate` (gated), `launch`, `fix`, `monitor`, `extract`; `until launched` parks the child and returns a
wait notice; `until extracted` follows the job to its result and is how a parked job is resumed. The shared machinery is
`LIB/tools/similarity_search/sequence_homology_evidence/bvbrc_job_child.py`; the estimate ledger is `resources/estimate_ledger.sqlite3`. Each
child's own note: `bvbrc_blast_episode.md`, `bvbrc_msa_episode.md`, `bvbrc_metacats_episode.md`.

### `all_vs_all`, a child with local tools

`all_vs_all_episode.md`. Its tools are `prepare_database`, `all_vs_all_blast`, `cluster`, `commit_clustering` and `hold`.

## What the head does with the results

The head's credit is the owner's differential credit over the candidate annotations the held graded sources give
(`a101_differential_credit.md`); the head returns the candidates with their scores, the leading one first. Its ceilings are
`HEAD/credit.py` `ceiling`; its stopping is the forecast controller (`forecast_yield_controller.md`).

## How the first patterns were shown (run history)

Run directories are under `runs/`. Each was started from the command line through the single-workflow launcher (`real_entry.md`).

- **Run `a101-patternA-1`** (`runs/a101_patternA_run_1`). The model's first call was right (`blastp`, the target, the reference, `local`),
  but every `pairwise_blast` unit was refused before BLAST started (`whole_workflow_budget_unavailable`, reason
  `native_output_outside_workflow_run`): the services file put the local resource's job folder outside the launcher's run directory of that
  command. The model made the same call 21 more times and I stopped the run. Two causes: the configuration, and a tool whose offer let a
  call that cannot succeed be repeated.
- **Run `a101-patternA-2`** (`runs/a101_patternA_run_2`). BLAST ran, then the unit raised `native_blast_requires_native_tool_source`: the Store
  admits an observation with a BLAST alignment address only on a source of the public BLAST provider. Changes: the observation is an
  `alignment` observation in the shape of the registry's `sequence.align`; only programs that compare the two molecules are offered; a
  comparison is offered once; a failed outcome shows its code and `retryable`; the local resource's job folder is inside the launcher's run
  directory.
- **Run `a101-patternA-3`** (`runs/a101_patternA_run_3`). The unit completed in one shot (76 of 76 query residues paired, 75 identical, E-value
  3.9499e-56, effective search space 4899, one alignment observation). The credit moved only with the model's reasoning commits, which it kept
  revising, and I stopped the run after 20 model calls.
- **Owner's rulings (2026-11-20).** The head fills out one JSON; one deterministic function checks it and either returns the things to fix or
  the job runs; a correct JSON must simply work. Grading is automatic: no reasoning commit assesses anything, and none switches the credit
  on or off. Changes: `check_pairwise_request` is the one check; the head's `action` rejects a request with problems; the running function
  no longer checks inputs; the credit counts a graded comparison as soon as its sheet is saved.
- **Run `a101-patternA-4`** (`runs/a101_patternA_run_4`, read back with `report` in `runs/a101_patternA_report_4`). One model call, the request
  `blastp` / target / reference / `local`; the unit completed in one shot (76 paired query positions, 75 identical pairs, one observation, 14
  records produced); the return carried the four graded records in `committed_record_refs`. `resume` (`runs/a101_patternA_resume_4`) made 0 model
  calls and returned the same result.
- **Run `a101-patternA-5`** (`runs/a101_patternA_run_5`), a later visit: the commission carried in `evidence_refs` the four records the head
  returned in run 4. The head held its earlier graded comparison; the model made four reasoning commits, then requested the same comparison
  again. The check returned `[{"field": "reference_ref", "code": "comparison_already_held"}]`; the request was rejected with that fix list, no
  unit was recorded and no job ran. Not shown by a real run: a request with a program that does not compare the two molecules, a reference
  that is the query, a query outside the scope, or a resource that is not local (the model never made one; `check_pairwise_request` returned
  the expected fix list for each when called directly, which is not a real run).

## The job child's controlled shape (owner, 2026-11-20)

The owner's words: "one child with 6 actions. make estimate/reason, [must be gated on having made an estimate] launch job, fix mistakes/reason,
monitor/update estimate, extract results", and "I think we can work on that in one loop first and then we can practice the detaching while
monitoring (i.e., come back to this process later or wait overall) after we get these basic forms down". `bvbrc_blast` was the first child built
in this shape, in one loop; the owner's two next steps, a global estimate ledger and a way to park the child and bounce a waiting notice up to the
parent, are built and are described in `bvbrc_blast_episode.md`.

## Other records

- Kind-level designs of the library modules, to be read for what each analysis measures and not for episode shapes: `database-search.md`,
  `all_vs_all.md`, `blast_database_preparation.md`. The episode shapes in them (launch, monitor and results episodes) are not the tree above.
- The real entry (`run`, `resume`, `report`): `real_entry.md`.
- The SOP that tells another axis how to be built the way this one was: `../../sop/evidence_axis_build_sop.md`.
