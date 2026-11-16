# Brief: remove everything backward-facing from your area (15 November 2026)

Repository: /home/chia/repos/gene_annotation_episode, branch first-full-draft-2026-11-10, HEAD a0d9f1666 (clean tree).
Read `AGENTS.md` once. The package under `gene_annotation_episode/episodic_workflow/root/` is a tree of "episode
homes" (directories with `episode.py`); each evidence axis (a101..a108, a110) keeps private copies of many modules.

## The owner's instruction (verbatim)
"Get rid of this whole historical apparatus everywhere. you are refectoring the code, no backward compatibility is
needed and no need to retain past behavior period. everywhere. if you are wasting a single line of code anywhere on
anything backwards facing, that is an affront to this reorg"
and: "send an agent to every arm to remove any historical references or backwards compatibilty so you can do it FAST.
Your prior efforts to save anything at all from the past in any way is an affront. Check every evidence arm every bit
of code with an agent each"

You own ONE area (named in your task). Go through every file in it and remove everything backward-facing. Be
decisive and fast: the default is to delete. Work on distinct file contents (many files are byte-identical copies:
group by sha256 and apply the same edit to every copy inside your area). You may fan out to up to 4 sub-agents over
disjoint sub-directories of your area; give each this brief and a precise file list, and merge their reports.

## What counts as backward-facing — remove it
1. Parameters, branches, helpers and names for the past: `historical`, `legacy`, `prior`, `previous`, `deprecated`,
   `compat`, `migrat*`, `prechange`, `before_*`/`*_before` snapshots of old code, `old_*`, and the code paths they select.
2. Acceptance of more than the current version of a record, receipt, schema, plan, ledger or manifest:
   `PRIOR_VERSION` / `LEGACY_VERSION` constants and branches, `version in (...)` listing older versions, schema
   `anyOf` alternatives for older forms, `_v1` readers kept beside a newer one, upgrade/migration functions. Keep
   exactly one form: the current one. A record that is not the current form must be refused by the existing error.
3. Tables of "moved", "historical", "previous" or "original" digests and any mechanism that accepts an older
   implementation digest. (Current implementation-digest pins stay; see decision 1 below.)
4. Saved copies of old source or old outputs and everything that compares against them: `*.source` files, fixtures
   named original/prechange/baseline/retained/saved-from-run/packet-NNN that were captured from an earlier code
   version, sealed bundles and plans from old runs, and the tests that replay or compare them.
5. Tests whose purpose is to show that current code still accepts, reproduces or equals something old ("original
   behaviour preserved", "historical form still read", "legacy constructor", "before/after the move", hash or AST
   comparisons with saved source, assertions about where code used to live). Delete them, plus helpers and fixtures
   that only they use (check with grep, including bare-name imports inside functions and `import_module` strings).
6. Homes, packages, modules, data files and schemas that exist only for the past (names containing `legacy`,
   `historical`, `retained_input_authority` if it only serves old records, `*_legacy_*.json`, relocation notes such as
   `RELOCATION_REVIEW.md`, per-home `ownership.md` / `ownership_inventory.json` narratives of the reorganisation, and
   code that reads them). First establish whether CURRENT runtime paths use them: if nothing current does, delete;
   if a current path depends on something that merely has a backward-sounding name, do NOT delete or rename it —
   list it under "live despite its name" with the evidence (file:line of the current caller).
7. Comments, docstrings and messages that narrate history ("previously", "before the reorganisation", "historical
   caller signature preserved", dated notes, references to old packets/runs). Delete the narration; keep a comment
   only if it explains current behaviour.
Vocabulary caution (the only brake): in this code "original" very often means the original commission, request or
assignment inside ONE workflow run, and "retained"/"saved" often mean records kept during a run and read back by the
same run's later steps (durable replay after restart is current behaviour). Those are current behaviour — keep them.
The test is: does this exist to cope with records, code or behaviour from an EARLIER VERSION OF THE PROGRAM? If yes,
remove it.

## Decisions already made by the owner — apply them inside your area
- Implementation-digest pins (A105-family storage; a104/a105/a106): re-pin to the CURRENT file digest every pin whose
  pinned file is byte-identical to, or differs only in import lines/formatting from, its pre-reorganisation original
  (inventory and classification: `docs/test_failure_triage_20261114/r2d_pin_inventory.tsv`,
  `r2d_pinned_file_differences.tsv`, `r2d.md`); leave pins of files with statement changes (7 in a105/library) as
  they are; remove mechanisms that accept older digests.
- Native-job memory policy: "5 GiB is intended". Any product policy above the launcher bound
  (`gene_annotation_episode/workflow_budget.py` `ENVIRONMENT_BOUNDS['memory_bytes']`; use your axis's existing way of
  referring to it) becomes the bound; tests asserting 20 GiB assert the bound.
- Retained plans carrying `policy.wall_seconds`: retire the tests that replay them and delete those fixtures.
- ATAC/chromatin receipt modules (shared root): `retained_policy(..., historical=...)`, `_historical` and every
  `historical=` argument go; only the current `POLICY` is accepted.

## Rules that still hold
- After your edits every module in your area must still import, current-version behaviour must be unchanged, and the
  A105/A108 grading rules in AGENTS.md must still hold for current records. No new fallbacks or defaults, no
  try/except that hides a failure, no timeouts, no "if it exists" skips: an unplanned case must raise.
- Stay inside your area. Other agents are doing the same in the other areas at the same time. When your removal
  changes or deletes something used from ANOTHER area (a function signature, a name, a file), do not leave a
  compatibility shim: make the change, and append one line to `runs/claude_inputs/purge/handoffs.tsv`
  (`from_area<TAB>to_area<TAB>file:line in the other area<TAB>what must change there`, append with `>>`). Before you
  finish, read that file for rows addressed TO your area and apply them.
- No git add/commit/stash/checkout/reset. Do not touch `verification/`, `runs/` (except your outputs), `.venv`,
  `AGENTS.md`, `tools/`, `docs/`.
- Python runs only through the launcher. Import check for many modules at once:
  `bash tools/one_workflow.sh --slot <slot> runs/claude_<slot>_NNN -- .venv/bin/python tools/verify_episode_homes.py --output runs/claude_<slot>_NNN/unused.json --import-names <dotted.module ...>` (prints `{}` when all import).
  A test file (one per run, isolated; the launcher refuses a pre-existing run directory):
  `mkdir -p runs/claude_<slot>_homes/NNN && bash tools/one_workflow.sh --slot <slot> runs/claude_<slot>_NNN -- env HOME=$PWD/runs/claude_<slot>_homes/NNN http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 all_proxy=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 no_proxy=localhost,127.0.0.1,::1 NO_PROXY=localhost,127.0.0.1,::1 eatmydata .venv/bin/python -m pytest <file> -q -p no:cacheprovider --basetemp=runs/claude_<slot>_NNN/tmp`
  Sub-agents need their own slot names (`<slot>a`, `<slot>b`, ...). No network, ssh, model calls or whole-workflow runs.
- For speed, verify mainly by the import check over all modules of your area plus running the test files whose code
  under test you changed (latest result per test file, for comparison: `results.tsv` in
  `runs/claude_tests_final_20261114_05_s*`, `..._20261115_06_p*`, `..._07_small`, `..._08_m*`, later overriding
  earlier). A full run of the whole tree follows after all areas are done; you do not need one.
- Scratch files go in `<scratchpad>/<slot>/`.

## Output
`runs/claude_inputs/purge/<slot>.md`: what you removed, by class (1-7) with counts (distinct sites, files edited,
files deleted, lines removed, tests deleted); "live despite its name" list with evidence; anything you kept and why;
import-check result; before/after of the test files you ran; handoff rows you wrote and applied. Also
`runs/claude_inputs/purge/<slot>_deleted_tests.tsv` (`file<TAB>test or (whole file)<TAB>reason`). Reply in at most 30
lines.
