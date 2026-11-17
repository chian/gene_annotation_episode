# Removing the `legacy_annotation` route and home (17 November 2026)

Owner direction (16 November 2026): an unbound `improvement` role fails explicitly, and removing a fallback outranks
avoiding restructuring, so the route that served the unbound role is removed completely. Baseline: `7e662ea29`
(`docs/verification_20261116/`). Each step is verified and committed before the next.

Verification per step: affected test files through `tools/one_workflow.sh` (per file, isolated HOME, blocked proxy),
compared per file with `docs/verification_20261116/results_per_file.tsv`; whole-tree `pytest --collect-only`;
the static dangling-name scan (`runs/claude_inputs/la/dangling.py`, copied from the purge) compared with
`docs/verification_20261116/dangling_names.tsv`. Retired tests: `retired.tsv`.

## Phase A: shared root

- A1 (`95d1b77db`): the monitor, terminal, resource, execution and HPC catalogues no longer construct or accept
  `legacy_annotation` members; the Literature parent family is annotation + scientific_process (14 members);
  `predefined_parent_routes` no longer routes an unbound `improvement` role; the registry's entry lookup requires an
  explicit `'annotation'` parent instead of defaulting a missing one to `legacy_annotation`. Whole-tree run
  `runs/claude_la_a1_s0..3`: identical per file to the baseline. Collection 50,585, 0 errors. Dangling scan unchanged.
- A2 (`1608d1067`): the implicit improvement child is removed from the shared runtime.
  - Selection kind `child` (commission the implicit `improvement` child) is no longer offered by
    `library/action_contracts.py`, executed by `action_execution.py`, or accepted in the child-kind sets, SQL filters and
    commission checks; role defaults `selection.get('role', 'improvement')` now require the role. Model-visible
    effect: a shared-root episode with no bound `improvement` role is no longer offered a child action that, since the
    owner decision, could only raise `episode_role_not_bound:improvement`. Explicit `episode_child`/`job_child`
    commissions are unchanged.
  - The legacy branches of the operational, literature and predefined child message owners and of
    `library/nominal_child_messages.py` are removed; `exchange_for_improvement` and the root edge files
    `to_child_legacy_annotation.py` / `from_child_legacy_annotation.py` are deleted.
  - `library/homology_episode_family.HomologyEpisodes` no longer builds the standalone legacy homology implementations;
    `implementation_for_path` accepts only the annotation parent (record version `root_homology_episode_family_v3`).
  - Tests: the shared-root and top-level run `runs/claude_la_a2_s0..3` (596 files) changed 7 files. Fixed:
    `test_episode_admission` fixture commissions an explicit `episode_child` `improvement` (restores
    `test_episode_completion` and `test_episode_source_checkpoint`); `test_root_episode_boundary` asserts an unbound root
    offers no child action; `test_public_root_callers` asserts the nested improvement homology path raises
    `fixed_homology_parent_path_required`. Retired 20 cases (`retired.tsv`): two `child/improvement` category cases and
    the 18 legacy monitor/standalone homology cases of `test_private_context_parent_identity`.
    `test_live_a106_binding` failed only in the concurrent shard run (`local_resource_busy`) and passes alone (8/8).
    Each changed file re-run alone: baseline counts minus retired cases. Collection 50,565 (= 50,585 − 20), 0 errors.
    Dangling scan unchanged.
- A3: the shared-root `legacy_annotation/` home is deleted (1,598 files; it had no tests and, after A1/A2, no importer).
  Shared-root and top-level run `runs/claude_la_a3_s0..3` (596 files): identical per file to the baseline except the
  retired cases and `test_live_a106_binding` (4 `local_resource_busy`). That test reserves memory/scratch against the
  machine's actual free capacity (`a106/local_resources.py`, `reserve`), which four concurrent shards can exhaust; run
  alone it passes 8/8 (`runs/claude_la_a3_a106`). Collection 50,565, 0 errors. Dangling scan unchanged.
- Remaining after Phase A: the string `'legacy_annotation'` in the arms (a101–a110), where it names the entry parent of
  each arm's implicit, unbound `improvement` episode (served by the arm's `annotation_improvement` home through
  `selects_improvement_parent` / `is_improvement_parent`), and `root/tests/test_private_binding_identity.py`, which
  exercises the arms' registries with that label. That is Phase B.
