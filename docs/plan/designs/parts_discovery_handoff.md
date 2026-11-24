# Handoff: set up the build workflow, then rebuild parts discovery by it

Written 2026-11-24 for a fresh session, at the owner's request ("you need to give me exact instructions and plan to pass to new
session to set up this workflow"). State of the tree: commit `7ec78c748`. Read this whole note before doing anything.

## Why this exists

The session before you described the repository's rules correctly and then broke them while building: names with versions, a
folder that was not an episode, library folders named after the arm, pieces it made up, code that depended on another episode's
modules, an edit to shared code without asking, and building before checking what exists. The owner's diagnosis: "you read the
design really well but then don't actually obey it"; "when you read old code you get dragged back into it". Stating the rules
again is not the fix. The fix is a workflow whose checks do not depend on your judgment.

## The one reference

The new paradigm is the episode subtree `gene_annotation_episode/episodic_workflow/root/sequence_homology_evidence/` AS IT STANDS IN
THE CODE, with the library modules it calls. Not a design note, not an old tree, not the structural-homology head, not the first
build of parts discovery. Old code is never a shape and never a starting point; when the owner tells you to look at it, you take
from it a short list of facts (what a tool measures) and close it. The owner, when the previous session proposed starting a tool
from old code: "we are trying to get everything refactored into the new paradigm and you are creating something else".

Read first, in this order: `AGENTS.md` (all of it); `docs/sop/evidence_axis_build_sop.md`; the reference subtree itself (every
file of the head; one child, `bvbrc_blast`; the library file of one tool,
`episode_support/tools/similarity_search/sequence_homology_evidence/hmmer_profile_scan.py`); then
`docs/plan/designs/parts_discovery_tree.md` and `docs/plan/designs/a103_tree.md` for what the arm is meant to do.

## Rulings of the owner you must not re-ask (2026-11-23 and 24)

- Every folder under the root is an episode ("If A101 isn't an episode then it isn't a folder"). The run command finds an episode
  by following its path's folders from the root. Done in `97bfdf8be`: the nine heads sit directly under `root/`.
- Nothing in the code is named after a version; old versions are deleted (`AGENTS.md`).
- "Nothing crosses the boundary of the folder within an episode unless it's part of a shared library."
- "The library is not for any thinking or deciding."
- "Don't make up new terms ... Those are not named pieces and if they don't belong in a named piece they are deleted."
- Credit is progress, tied to changes in annotation scores; an annotation score is how well a candidate is supported. Never
  describe one as the other. "credit and decisions by design should never fight each other".
- Arms merge nothing; the root decides which candidates are the same and passes its grouping down
  (`docs/plan/designs/a102_regrouping.md`).
- The parts arm: what was agreed is in `parts_discovery_tree.md` (the piece of DNA is the one fixed thing; the default genetic code
  unless a special case is triggered; every reading is revisable; it proposes parts and checks claims about what is there; a tool
  is a fixed workflow called the same way every time, an iterative workflow of different tools is a child episode).
- Do not edit shared code (the run command, `episode_runtime/`, `method_loop/`, `yield_control/`, the root's own files, another
  episode's folder) without the owner's word. Another session is building the root and works in `sequence_homology_evidence` and
  `experimental_activity_evidence`.
- Never stash. Commit by exact paths. No pytest, no `tests/` folders. Python and native programs only through
  `bash tools/one_workflow.sh --slot a101 runs/<new dir> -- ...`.

## One thing that is NOT settled: where an arm's library code goes

Two facts that do not agree, both true. Put them to the owner before placing any library file; do not choose yourself.

- The owner: "Library code is grouped wrong if it is grouped by arm name."
- The reference: its library sits in `episode_support/tools/similarity_search/sequence_homology_evidence/` (a function group, then a
  folder named after the head) and ALSO in `episode_support/tools/sequence_homology_evidence/` and
  `episode_support/grading/sequence_homology_evidence/` (named after the head directly). In the reference the request check of a
  tool (`check_profile_scan_request`) lives in the library file beside the tool's unit function.

## Part 1: set up the workflow (do this first; build nothing before it works)

1. A structure check: ONE script that reads the tree and the staged changes and fails with a list of violations. The owner
   ordered this workflow set up (the request quoted at the top). Tests and harness scripts stay banned: this script reads file
   names and source text only; it imports and runs nothing of the application. Proposed home: `tools/check_episode_structure.py`
   (a new file; `tools/` already holds the launcher). Show the owner the script before turning it on. It checks, for the episode
   folders and library files the staged changes touch:
   a. every folder under `root/` on the changed paths is an episode: it holds `goal.py`, `task.py`, `credit.py`,
      `yield_estimator.py`, `episode.py` and `messages/` with `read_from_parent.py`, `internal_summary.py`, `final_to_parent.py`,
      and `msg_to_child.py` and `read_from_child.py` exactly when it has child episode folders;
   b. no added line names a version (`_v<digits>`, `legacy_`, `old_`, `deprecated_`, `previous_`), outside names of outside tools;
   c. no file under an episode folder imports from another episode's folder;
   d. LEFT OUT until the owner answers the library-placement question above: whether a library file may sit in a folder named
      after a head. Do not write this check from your own reading;
   e. every staged path is inside the folders the session declared as its own at the start; anything else stops the commit;
   f. for an episode built by copying a reference episode: the names defined at the top level of each of its files, compared
      with the reference file's names; every name with no counterpart is printed, and the commit stops unless the episode's
      design note lists that name with its reason.
2. Make it a gate that runs before every commit without relying on you: a hook of the coding tool (use its own configuration
   skill to set it up; do not write the hook from memory). Show the owner the hook and the script before turning it on.
3. A second reader: after each build step, an agent that is given ONLY the reference files and the diff of the new files (not your
   reasoning, not the design note) and reports where the new files depart from the reference. Its report goes to the owner
   unedited.
4. Prove the gate: for each kind of violation, stage one deliberate example (a new scratch file, never an edit of a real one),
   show the owner the check refusing it, then unstage and delete the scratch file. Never stash.

## Part 2: the procedure for every piece (an episode, a tool, a child)

1. Inventory. Search the current library and the reference for code that already does the job. Write what you find as facts:
   what exists, where, what it measures. Old-paradigm code gives facts only. No building until this file exists.
2. Mapping. A table: each piece of the reference (file, constant, function) and the piece of the new episode that corresponds to
   it, with the same kind of name in the same file. Anything you want that has no counterpart in the reference is not built: it
   goes to the owner as a question. Show the owner the table before step 3.
3. Copy. The new piece starts as a copy of the reference piece; change only what must differ.
4. Check. The structure check passes; the second reader's report is attached.
5. Diff. Give the owner every difference from the reference with its reason. A difference with no reason is a violation.
6. Run. Only now a real run, from a worktree pinned at the commit, with the prediction written first (SOP Step 11).

Keep steps short. Report after each one. Do not chain several pieces before the owner has seen the first.

## Part 3: the first job under the workflow

Rebuild the head of parts discovery with its first pass, by Part 2.

State of the arm at `7ec78c748`, all of it to be treated as not conforming:

- `root/parts_discovery/` exists and does not import: its `task.py`, `credit.py`, `messages/internal_summary.py` and
  `messages/final_to_parent.py` import library modules that were deleted. It carries pieces the previous session made up
  (`mode_of`, `offered_codes`, `local_resource`, `tried`, `owed_action`, three request checks moved into `task.py`, `rna_parts`).
- Library left over from it: `episode_support/tools/rna_gene_finding/find_rna_genes.py` (imports a deleted helper),
  `episode_support/grading/rna_gene_finding/rna_gene_sheet.py`, `episode_support/grading/tool_grading/tool_grading_artifacts.py`
  (a copy of a module the reference has as `grading/sequence_homology_evidence/tool_grading_artifacts.py`, in a folder the previous
  session invented).
- The gene-finding and composition modules of the first build were deleted in `ed887cd94`; their last text is in commit
  `2203e7df9` under `episode_support/tools/gene_finding/`, `tools/sequence_composition/`, `grading/gene_finding/`,
  `grading/sequence_composition/`. They are a record of what was measured, not a shape to restore.
- Facts measured on real DNA are in `parts_discovery_tree.md` ("First real run", "Audit and second real run") and in
  `runs/parts_survey_1/` and `runs/parts_code_check_1/`: what the gene finder and the RNA scan return, their time and memory, and
  that a wrong genetic code gives a LOWER sum of the finder's scores but MORE genes. Two earlier real runs of the first build
  gave 64 genes and 7 RNA genes on a 60,001-base stretch.
- Read-only notes on the old gene context tree: `runs/context_inventory/head.md` and `library.md`. That tree is old-runner code and
  does not load; the notes are facts only.

Do first, in this order, reporting to the owner after each: (1) read what "Read first" lists; (2) put the library-placement
question to the owner, with the two facts and nothing else; (3) Part 1; (4) Part 2 step 1 (inventory) and step 2 (mapping) for
ONE tool of the head against the reference's `hmmer_profile_scan`. Build nothing of the arm before the owner has seen that table.

## Which heads load today (checked at `97bfdf8be`)

The root with its 14 episodes, `sequence_homology_evidence`, `structural_homology_evidence`, `experimental_activity_evidence`. The
other six evidence heads fail with `episode_lacks_members: offered_actions, ceiling` (old-runner code). `parts_discovery` fails on
its deleted imports.

## Not verified, so do not state it as done

- The structural-homology work of 2026-11-23 (identifiers on its candidates, applying the root's grouping) was import-checked and
  checked on old records; it has not run as an episode. The owner parked that axis.
- Nothing in parts discovery has run since its library was regrouped.
