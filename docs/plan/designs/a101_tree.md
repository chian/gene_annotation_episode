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
