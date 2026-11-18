# Root with nine evidence-axis children (started 17 November 2026)

Target (owner direction, 17 November 2026): the root annotation episode has exactly nine explicit child bindings, one
per evidence axis, each implemented by its axis folder, named for what it does, with a goal specific to what its own
iteration cycle improves. The root credit is one calibrated, rescaled offset-product hypervolume over the nine axis
scores (ε = 0.5: every single-axis gain is rewarded linearly, and evidence on several axes always earns more than the
same credit on one axis). Removed: the generic `scientific_process` role, the axis-id lookup tables, the duplicate
shared subtrees, each axis's standalone wrapper (own root task, runtime, registry), every generic improvement child and
every `legacy_annotation` reference. Baseline: `7e662ea29` (`docs/verification_20261116/`).

Axis roles (names from `research/slotted_process_library/publications/2026-10-24-001/evidence_axis_options.json`):

| Axis | Library name | Role |
|---|---|---|
| A101 | Sequence homology | `sequence_homology_evidence` |
| A102 | Structural homology (incl. former A111) | `structural_homology_evidence` |
| A103 | Gene context | `gene_context_evidence` |
| A104 | Evolutionary history and phylogenetic placement | `evolutionary_history_evidence` |
| A105 | Experimental molecular activity | `experimental_activity_evidence` |
| A106 | Experimental contribution through perturbation and restoration | `perturbation_evidence` |
| A107 | Required partner presence and coexpression | `partner_presence_evidence` |
| A108 | Organism and sample-context evidence | `sample_context_evidence` |
| A110 | Biochemical feasibility and chemical/resource accounting | `biochemical_feasibility_evidence` |

Findings that set the plan:
- The root commissions one generic role (`scientific_process`) and chooses the axis from an `option_id` in the
  assignment; axis behaviour is reached through axis-id lookup tables (`axis_return_admission.py`, `returns.py`,
  `credit.py`, `axis_contribution_readers.py`). Root composition builds one shared generic class
  (`episode_composition.py`). The registry supports per-axis owner groups, but no caller attaches the axis trees; only
  A105's tree has a saved-binding reconstruction path (`saved_private_binding_catalogue.py`).
- Each axis folder is a full standalone workflow: own entry point, own `runtime.py`, own root annotation task and
  registry, its axis head under the generic name, a generic improvement child and the `legacy_annotation` label.
- `scientific_process` appears 22,877 times in 4,887 files; 10 directories (9 axes + the shared root) hold 9,350 files.

Plan: Phase 1 per axis (rename the axis head to its role inside the axis folder, mechanically, closed within the axis
plus the root lookup tables that name its modules); then relabel `legacy_annotation` and remove the generic
improvement children across the arms; Phase 2 the root contract (nine explicit bindings, one hypervolume, removal of the
generic class, lookup tables and duplicate subtree); Phase 3 per axis, removal of the standalone wrapper so the axis child
runs on the root runtime. Each step: affected test files one at a time through `tools/one_workflow.sh`, whole-tree
collection, dangling-name scan (`runs/claude_inputs/la/dangling.py`), commit.

## Steps

- P1-A108: `a108/scientific_process` → `a108/sample_context_evidence` and every `scientific_process` /
  `ScientificProcess` token inside `a108/` (11 paths, 213 files; script `runs/claude_inputs/la/rename_axis_role.py`);
  the A108 entries of the root lookup tables (`axis_return_admission.py`, `returns.py`).
  `root/tests/test_private_binding_identity.py` now takes each arm's head role from an explicit `AXIS_ROLE` table.
  A108's 36 test files run one at a time: 526 passed, 3 failed, as in the baseline (the same three
  `test_original_molecular_material_port` cases). `test_private_binding_identity`: 70 passed, the 2 baseline a103
  failures. `test_signed_evidence_root`: 24/4 as in the baseline. Collection 50,565, 0 errors; dangling scan unchanged.
- P1-A105: `a105/scientific_process` → `a105/experimental_activity_evidence` and every token inside `a105/` (11 paths,
  379 files); the A105 entries of the root lookup tables; `saved_private_binding_catalogue.py` (A105-only) renamed
  throughout. A105's 184 test files plus the 27 shared files that exercise the saved catalogue, its users and the lookup
  tables (`runs/claude_ax_a105_s0..3`, 211 files): identical per file to the baseline. Binding identity test: baseline.
  Collection 50,565, 0 errors; dangling scan unchanged.
- Test infrastructure: `root/tests/axis_roles.py` is the single table of each arm's head role and class prefix; the
  seven shared arm test helpers (`hpc_*`, `scientific_head_boundaries`) and the binding identity test read the head
  from it instead of hard-coding the generic name. 96 test files that use them: identical per file to the baseline.
  Collection 50,565, 0 errors; dangling scan unchanged.
