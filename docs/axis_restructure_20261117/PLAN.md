# Fixed plan and target (2026-11-19)

This file is the plan. Work follows its order. A new finding goes to the parking lot at the bottom unless it
blocks the "done when" of the item in progress. The plan changes only when the owner changes it.

## Target (the goal's success criteria, as checks)

- T1 The runner names no role or axis; no axis folder has a runner, root task or registry.
- T2 Every episode folder has exactly the ten files and imports nothing from another episode.
- T3 Real tests (no fakes) run the runner through each of the nine heads.
- T4 Real tests show launch/monitor/extract on a real job, the worth-it calculation and cross-run learning.
- T5 Real tests show the root commissions exactly its nine children and the hypervolume, with unbounded credits.
- T6 No scientific_process or legacy_annotation outside docs/; every test file matches 7e662ea29 or is recorded or
  retired with a reason; zero collection errors; no dangling names; no fallbacks.

## Roles that are settled (apply everywhere, do not reopen)

- The model routes; code executes; no exec_command anywhere. Every tool is an action format plus a runner.
- A reflex (provenance, bookkeeping, scoring that every run does) is code at the tail of the unit, not a model choice.
- task.py acts and records; credit.py reads held records and returns a number; the one model call credit needs (the
  judge) is made by the unit as its last step and stored as a held record credit reads.
- Only controlled data crosses between episodes (the parent's `objective`/`purpose` text going down is the exception).
- No generic `reason` tool in any literature episode (extraction is extraction; relevance is a Jev classification;
  judging is the classifier at `accept`). Search strategy and the A105 grading-save action: see parking lot.
- Sonnet agents only. Real-model tests, no fakes. Check the real prompt first.

## Verified so far (real model runs)

Launch (local): A101-A104, A107, A110. Monitor (local): A101-A104, A106, A107, A110. Extract (local): A101-A104,
A107, A110; A104 launch->monitor->extract chain. A102 resource work. A107 HPC planning (decisions only).
A105 examination and leaves. A101 head branches 1-3. API route and A101 API launch (BLAST accepted, unfinished).

## Work list (fixed order)

1. Literature: finish removing `reason` from every literature episode of every axis.
   Done when: no literature task.py/goal/brief/test mentions it; remaining test failures are listed as real dependants.
2. Literature: one extraction episode end to end (A101 table_evidence_extraction): one extraction action that records
   each element (terms, source subjects, contexts, observations, each anchored to a quote) through a custody operation;
   the judge classifier in credit.py, called at the tail of the unit; controlled return.
   Done when: its real prompt is checked and a real-model run passes with credit moving.
3. Copy the extraction episode as private copies: the other two extraction episodes of A101, then the other axes.
   Done when: each axis's extraction episodes pass offline tests and one real run for A101 only.
4. Literature: source_relevance_assessment = provider search + automatic Jev score of every hit + the model's choice.
   Done when: a real run scores real hits and the model picks among scored candidates.
5. Literature: examination, search strategy and the top episode: brief and own action each.
   Done when: one literature branch (A101) runs top to leaf with the real model.
6. Heads: each of the nine reaches and completes a real run (known blockers: A102/A106/A107/A108 first decision;
   A107 services; A110 process_entry; A101 done).
   Done when: each head ends by yield_stop, return admitted, resume replays with no new model call.
7. Root: nine children, hypervolume tests with unbounded credits, one real minimal run.
8. Worth-it calculation and cross-run learning: real tests with logged, readable, overridable settings.
9. HPC wrapper and the other API wrappers; HPC runs (needs the owner's authentication) and API services by the
   inventory.
10. Cleanup against T2 and T6: test_private_bindings, failing test files, records and retirements, ledger.

## Parking lot (not now)

NCBI job still WAITING; credit of a wait's own check row; idle polling after completion (estimator settings); A105
`reason` (it saves the graded interpretation) to be renamed for what it does; A106 score judge conversion; the
A108 classifier; the 147 failing literature storage tests in A106/A107/A108; heads' own `reason`; HPC and EBI HMMER
protocols; A103 launch-parent carry-over loss audit; /tmp quota (move finished runs to runs/ram_archive/ on disk).

## Rules

- One item in progress per area. No new item enters the work list without the owner.
- A fixer gets one task with its done-when. When it reports, I check the done-when and move to the next item.
- A discovery that does not block the current done-when is written in the parking lot and left.

## Note, 2026-11-19 (owner)

The episode names are the owner's and are settled; no renames. published_evidence_assessment: its goal (97308b94c and
now) is to investigate which published evidence bears on the assigned question; it has the ordinary search and read
tools itself and may assign the strategy child; its result is the evidence found with sources, claims and what stays
unresolved. The chain stays as it is.

## Names

The names are the owner's short names from /home/chia/repos/nano-graphrag/question_pipeline/episode_binding/
(web_search, page, strategy, table, chunk, ...). The literature logic comes from those bindings. No rename plan.

## Parking lot, added 2026-11-19 (owner: a detail, add back later)

Figure and plot value extraction for A105: the library has a deterministic bar-plot digitizer
(literature/forms/experimental_activity_evidence/literature_figure_measurements.py, with controlled-response
calculations) and an `image.view` tool in several axes; the A105 episodes read today do not use them. Add it back to the
A105 literature subtree after the main flow is right.
