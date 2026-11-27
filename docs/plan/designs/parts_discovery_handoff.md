# Handoff: rebuild parts discovery by the build workflow

Written 2026-11-24 for a fresh session, at the owner's request. It replaces the handoff of the same day. State of the tree:
commit `71f721701` plus the uncommitted files named under "State". Read this whole note before doing anything.

## What went wrong before you, so you do not repeat it

- The first session described the repository's rules correctly and then broke them while building: version names, a folder that
  was not an episode, pieces it made up, code that depended on another episode's modules, an edit to shared code without asking,
  building before checking what exists. The owner: "you read the design really well but then don't actually obey it"; "when you
  read old code you get dragged back into it".
- The second session asked the owner where "an arm's library code" goes, three times, because the earlier handoff told it to ask.
  `AGENTS.md` already answered it. The owner: "It's kind of a dumb question"; "why are you so stuck on the arm's library?"; "i'm
  not sure why you keep asking arm arm arm arm".

What follows from both: a note written by an agent, this one included, is a claim. The owner's words, `AGENTS.md` and the
memory decide. Before you ask the owner anything, look there; if a rule answers it, act on the rule and do not ask.

## Settled; do not ask

- The library. The owner, 2026-11-24: "library is a set of shared function or external functions. they get organized by what
  they are, not where they belong in the workflow. these are mostly built around the idea of shared functions and shared
  libraries." A library function has no arm and no head. It sits in the folder for what it is, and any episode calls it. Before
  writing one, find the shared function that already does the job and call it; a second copy is wrong. A library folder such
  as `sequence_homology_evidence` is right: it is a category of what the tools in it do (sequence homology). The second session
  called those folders misfilings and wrote a check against them; the owner: "the objection to sequence_homology is stupid b/c
  it's a functional category of what a tool does". Never say or think "the arm's library".
- "The library is not for any thinking or deciding."
- Every folder under the root is an episode. The run command finds an episode by following its path's folders from the root.
- Nothing in the code is named after a version; old versions are deleted (`AGENTS.md`).
- "Nothing crosses the boundary of the folder within an episode unless it's part of a shared library."
- "Don't make up new terms ... Those are not named pieces and if they don't belong in a named piece they are deleted."
- Credit is progress, tied to changes in annotation scores; an annotation score is how well a candidate is supported. Never
  describe one as the other.
- Heads merge nothing; the root decides which candidates are the same and passes its grouping down
  (`docs/plan/designs/a102_regrouping.md`).
- What parts discovery is: `docs/plan/designs/parts_discovery_tree.md`.
- Do not edit the run command, `episode_runtime/`, `method_loop/`, `yield_control/`, the root's own files or another episode's
  folder without the owner's word. Another session is building the root and works in `sequence_homology_evidence` and
  `experimental_activity_evidence`.
- Never stash. Commit by exact paths. No pytest, no `tests/` folders. Every Python or native command goes through
  `bash tools/one_workflow.sh --slot a101 runs/<new dir> -- ...` (the second session ran one Python command directly; do not).

## The one reference

The new paradigm is the episode subtree `gene_annotation_episode/episodic_workflow/root/sequence_homology_evidence/` AS IT STANDS
IN THE CODE, with the library functions it calls. Not a design note, not an old tree, not the structural-homology head, not the
first build of parts discovery. Old code gives facts only (what a tool measures), never a shape.

Read first, in this order: `AGENTS.md`; `docs/sop/evidence_axis_build_sop.md`; the reference head (every file), one child
(`bvbrc_blast`) and one library function it calls (`episode_support/tools/similarity_search/sequence_homology_evidence/
hmmer_profile_scan.py`); `docs/plan/designs/parts_discovery_tree.md`; `docs/plan/designs/parts_discovery_find_rna_genes.md`.

## The workflow

### The structure check (written and tried; not yet a gate)

`tools/check_episode_structure.py` reads what one commit would hold (file names and source text; it imports nothing of the
application) and lists violations:

- (a) every folder under `root/` on a changed path is an episode (the five files, `messages/` with its three, and
  `msg_to_child.py` and `read_from_child.py` exactly when it has child folders);
- (b) no added line or added path names a version (`_v<digit>`, `legacy_`, `old_`, `deprecated_`, `previous_`);
- (c) no file under an episode folder imports from another episode's folder;
- (d) is not a check: where a library function sits is judged by what the function is, which the script cannot tell from a
  name;
- (e) every changed path is inside the paths the session declared as its own;
- (f) for an episode declared a copy of a reference episode: a top-level name the reference's file of the same name does not
  define is a violation unless the episode's design note lists it in a table row (file, name, ..., reason). An episode folder
  new in the commit must be declared a copy.

The session's declaration is `runs/structure_declarations/<session id>.txt`: lines `own <path>` and
`copy <episode folder> <reference episode folder> <design note>`. The script's docstring is the full statement.

Tried on scratch files in a throwaway clone (`runs/structure_check_selftest_3/`): each kind
of violation refused, a clean copy of `bvbrc_blast` passed. That was a trial in a clone, not the proof on the real index.

### The gate (drafted and tried with made-up payloads; NOT installed)

A PreToolUse hook on `Bash` of the coding tool, for `.claude/settings.local.json`. Install it with the tool's own configuration
skill, not from memory. Its command:

```
input=$(cat); command=$(jq -r '.tool_input.command // empty' <<<"$input"); grep -Eq '\bgit\b.*\bcommit\b' <<<"$command" || exit 0; declaration="$CLAUDE_PROJECT_DIR/runs/structure_declarations/$(jq -r '.session_id' <<<"$input").txt"; [ -f "$declaration" ] || exit 0; bash "$CLAUDE_PROJECT_DIR/tools/one_workflow.sh" --slot a101 "$CLAUDE_PROJECT_DIR/runs/structure_gate_$(date +%Y%m%dT%H%M%S)_$$" -- python3 -I tools/check_episode_structure.py --declaration "$declaration" --directory "$(jq -r '.cwd' <<<"$input")" --hook-command "$command" >&2 || exit 2
```

What it does: a command with no `git commit` passes unread; a session with no declaration is not gated (so the session building
the root is not blocked); a commit must be the only command (`cd <folder> &&` may precede it), in a form whose content can be
read before it runs (`-a`, `--amend`, `git add ... && git commit` are refused). Limits: it is the tool's hook, so a commit made
outside the tool's shell is not gated; and a commit is refused while a workflow runs in slot `a101` of this checkout.

The owner was shown the script and this hook on 2026-11-24 and has not yet said to turn it on. That yes is the owner's.

### The second reader

After each build step, an agent given ONLY the reference files and the diff of the new files, with this brief and nothing
else: "Here are the reference files and the diff of the new files. Report every place the new files depart from the
reference." Its report goes to the owner unedited.

### The procedure for every piece (an episode, a tool, a child)

1. Inventory: what exists that already does the job, where, what it measures. Facts only. Written to a note before anything.
2. Mapping: each piece of the reference and the piece of the new episode that corresponds to it, same kind of name, same file.
   Something with no counterpart in the reference is not built; first see whether a settled rule answers it, and only if none
   does, it goes to the owner. The owner sees the table before step 3.
3. Copy: the new episode file starts as a copy of the reference file; change only what must differ. (Episodes are copied.
   Library functions are shared, not copied.)
4. Check: the structure check passes; the second reader's report is attached.
5. Diff: every difference from the reference with its reason.
6. Run: a real run from a worktree pinned at the commit, the prediction written first (SOP Step 11).

Short steps. Report after each. One piece at a time.

## State

Uncommitted in the working tree: `tools/check_episode_structure.py` (new), `docs/plan/designs/parts_discovery_find_rna_genes.md`
(new), this note (rewritten). Nothing of the head is built.

The head at `71f721701`, all of it not conforming:

- `root/parts_discovery/` does not import: `task.py`, `credit.py`, `messages/internal_summary.py` and
  `messages/final_to_parent.py` import library modules that were deleted. It carries made-up pieces (`mode_of`,
  `offered_codes`, three request checks in `task.py`, `rna_parts`).
- The first build's library copies, to delete: `episode_support/tools/rna_gene_finding/`, `episode_support/grading/
  rna_gene_finding/`, `episode_support/grading/tool_grading/`, and the kinds `rna_gene_scan_results` and `rna_gene_scan_report`
  in `episode_support/records/data_products.py`.
- The gene-finding and composition modules of the first build were deleted in `ed887cd94`; their last text is in `2203e7df9`.
  A record of what was measured, not a shape.
- Measured facts: `parts_discovery_tree.md` ("First real run", "Audit and second real run"), `runs/parts_survey_1/`,
  `runs/parts_code_check_1/`.

The first tool, `find_rna_genes` (`docs/plan/designs/parts_discovery_find_rna_genes.md`, inventory and mapping done):

- The library already holds the function: `rna_family_scan` in `episode_support/tools/structure_search/
  structural_homology_evidence/rna_family_scan.py` runs the same `cmscan` command and keeps every hit with its positions,
  strand, bit score and threshold. The head's tool calls it. No new library file.
- Its check admits only an RNA query; a piece of DNA is refused. The molecules admitted must become an argument of the check.
  That changes one call in `root/structural_homology_evidence/task.py`, which is another episode's folder: that one edit needs
  the owner's word. The function has not been run on a piece of DNA.
- Not derived yet: how a hit of the sheet becomes a part with an annotation score, and what proves the unit's ceiling. In the
  reference a candidate is a family name reported at most once; here it is a part (kind, positions, strand) and one family is
  found at many places (446 hits on the E. coli chromosome). Derive it from the tree note's "Scores and credit" and the
  reference's `credit.py`, and put it in the table for the owner.

Which heads load (checked at `97bfdf8be`): the root with its 14 episodes, `sequence_homology_evidence`,
`structural_homology_evidence`, `experimental_activity_evidence`. The other six evidence heads fail with
`episode_lacks_members: offered_actions, ceiling`. `parts_discovery` fails on its deleted imports.

Not verified, so do not state it as done: the structural-homology work of 2026-11-23 has not run as an episode (the owner
parked that axis); nothing in parts discovery has run since its library was regrouped.

## Do next, in this order, reporting after each

1. Read what "Read first" lists.
2. Redo the head table of `find_rna_genes` in its note: the call of the shared `rna_family_scan`, and the
   derived score and ceiling. Show the owner that table. Build nothing of the head before the owner has seen it.
3. When the owner says to turn on the gate: install the hook, write the declaration, prove it (for each kind of violation
   stage one new scratch file, show the refusal, unstage and delete it), then commit the script and the notes by exact paths.
4. After the owner has seen the table: procedure steps 3 to 6 for `find_rna_genes`, then the next tool by the same
   procedure.
