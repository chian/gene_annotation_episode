# Sub-brief for the pa104 sub-agents (area: `gene_annotation_episode/episodic_workflow/root/a104/`)

Read `runs/claude_inputs/purge/BRIEF.md` first (and `AGENTS.md` once). This file narrows and OVERRIDES it where they differ.
`A` = `gene_annotation_episode/episodic_workflow/root/a104`. `S` =
`/tmp/claude-1000/-home-chia-repos-gene-annotation-episode/6505138e-b5fa-4641-9b42-c1589dca8429/scratchpad/pa104`.

## Owner update (later than the brief; it wins)
Verbatim: "any test code that is only meant to be run on the prior code can be DELETED. DO nto adjust any registrations or
checks that have to do with files or hashes for files or versions. DELETE ANY TEST THAT WAS TIED TO SPECIFIC INSTANCE OF THE
CODEBASE. NOW. DO IT."
1. PRODUCT CODE: do NOT re-pin, update, remove or otherwise edit any registration or check that concerns file digests, file
   lists, file locations or version stamps. The brief's pin decision is cancelled. Leave every pin table (`_FROZEN`,
   `_PURE_HASHES*`, `_PINNED`, `_MOVED_HASHES`, `_LEGACY_FROZEN`, `sha256_at_release`, `custody_sha256`,
   `_RETAINED_SAVED_DEPENDENCY_RELEASES`, implementation-compatibility digest pairs ...) and every digest/version check
   exactly as it is, even when its name sounds historical. When in doubt whether something is such a check: leave it and list
   it in your report under "left because of the owner update".
2. TESTS: DELETE every test tied to a specific instance of the codebase: tests that assert or depend on file hashes, pinned
   digests, implementation-dependency pins, source snapshots (`*.py.txt`, `own_source`, `*.source`), AST dumps /
   `inspect.getsource` / reading product `.py` text, file inventories or ownership records, where code lives (module paths,
   "private owner" location assertions, forbidden-import scans), module/file registrations, version strings of a particular code
   state, saved outputs or retained fixtures captured from an earlier code state (original/prechange/preunion/retained/
   packet-NNN/saved carriers/cold probes that replay a saved original), and tests written to run against the prior code. Delete
   them outright together with helpers and fixtures only they use. Do NOT repair, re-point or adapt such tests. A test that
   exercises current behaviour with inputs it builds itself stays.
3. Speed over polish: delete first, then import-check.

## What remains to remove from product code (brief classes 1, 6, 7 and the non-digest/non-version part of 2)
Parameters/branches/helpers for an earlier version of THIS PROGRAM (`historical`, `legacy`, `prior`, `previous`,
`compat`, `old_`, `*_before`, migration/upgrade functions, readers of older record FORMS that are not version/digest checks),
modules and data files that exist only for the past and that no current runtime path uses, and comments/docstrings/messages
that narrate history. Vocabulary brakes, in addition to the brief's:
- Scientific/tool vocabulary is NOT history: Bayesian/Dirichlet "prior", PSI-BLAST "previous iteration", "previous" row/
  element in a loop, HMMER2/HMMER3 "legacy" file formats and BLAST "legacy"/v4/v5 database formats produced by external
  tools, "compatible" units/alphabets/coordinates, "original" commission/request/source/sequence, "retained"/"saved" records
  of the same run. Keep all of that.
- If removing something would need a change to a digest/version check or pin table, do not remove it; list it.
- If a current runtime path uses something with a backward-sounding name, keep it and list it under "live despite its name"
  with file:line of the caller.
- ownership.md / ownership_inventory.json / *.ownership.json were already deleted by the coordinator (nothing read them).

## Mechanics
- You own exactly the files in your list `S/list_<X>.txt` (paths relative to `A`). `S/groups_<X>.tsv` has one line per
  distinct content: `count<TAB>path<TAB>path...` for byte-identical copies; apply the same edit to every copy (sed/perl over
  the group is fine). Many files in D are near-identical copies differing in import lines: treat them alike.
- When you change or delete a name/signature/file that is used elsewhere in `A` outside your list, grep all of `A`; make the
  minimal call-site edit there yourself only if the file is product code and the edit is one line; otherwise append a row to
  `runs/claude_inputs/purge/pa104_internal.tsv` (`from<TAB>to(list letter)<TAB>file:line<TAB>what must change`) with `>>`.
  For uses outside `A` follow the brief (`handoffs.tsv`). Read `pa104_internal.tsv` for rows to your list before finishing.
- Never run the two retained-authority tests (`tests/test_a104_retained_*_authority.py`): they take CPU-hours.
- Python only through the launcher with YOUR slot name, run directories `runs/claude_<slot>_NNN` (NNN from 001). Import check:
  `bash tools/one_workflow.sh --slot <slot> runs/claude_<slot>_NNN -- .venv/bin/python tools/verify_episode_homes.py --output runs/claude_<slot>_NNN/unused.json --import-names <dotted.module ...>`
  (dotted names start `gene_annotation_episode.episodic_workflow.root.a104.`; prints `{}` when all import). Run it over every
  module you edited (and, for the tests agent, every remaining test helper/test module) before finishing. Run a test file only
  if you changed code it tests and it is cheap; use the brief's command.
- No git add/commit/stash/checkout/reset (plain `rm` to delete). No sub-agents. No new files in the repository other than your
  outputs under `runs/`.
- Scratch: `S/<slot>/`.

## Output (write files, then reply in at most 25 lines)
`runs/claude_inputs/purge/<slot>.md`: removed items by brief class 1-7 with counts (distinct sites, files edited, files
deleted, lines removed, tests deleted); "live despite its name" with evidence; "left because of the owner update"; anything
else kept and why; import-check result (run directory); internal/handoff rows written and applied.
`runs/claude_inputs/purge/<slot>_deleted_tests.tsv`: `file<TAB>test or (whole file)<TAB>reason` (tests agent; others only if
they deleted tests).
