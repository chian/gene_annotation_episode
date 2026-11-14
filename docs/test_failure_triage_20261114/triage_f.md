# triage_f: product modules that fail to import (34 modules, 5 homes)

Source: `runs/claude_homes_all_20261114_01/homes.json` (`import_failures`).
Pre-reorganisation reference: `078b77668`. Reorganisation snapshot: `dfe3e6091`.

## Outcome

| | modules | state |
|---|---|---|
| Fixed by import-line edit, verified by running | 2 | `root.library.macs2_peak_tools`, `root.a110.literature_current_results` |
| Still failing, product defect, not edited | 32 | 14 root, 16 a102, 1 a104, 1 a107 |

Edits (3 lines, 2 files, no commit):

```
gene_annotation_episode/episodic_workflow/root/library/macs2_peak_tools.py   | 4 ++--
gene_annotation_episode/episodic_workflow/root/a110/literature_current_results.py | 2 +-
```

## Did the automated re-pointing cause any of this? No.

`git show --name-only` for `3dd58552a`, `22c1bab66`, `f29225f0a` (and `632283f17`, `6a02e91ba`, `123a39831`):
none touches any non-test file under `episodic_workflow/root/`. Every failing import line is byte-for-byte
what `dfe3e6091` committed (checked with `git show dfe3e6091:<path>` for the atac receipts, macs2, a102
`blast_iteration_inputs`, a104 `bvbrc_phylogeny_tool_info`; `git log` for the rest shows `dfe3e6091` as the
only commit). All ten causes come from the reorganisation itself.

## Per cause

### 1 and 2. root: `retained_policy` from `root.library.native_{atac_differential,chromatin_interaction}_contracts` (14 modules) -- product_defect, NOT edited

- Original (`078b77668:gene_annotation_episode/atac_differential_result_receipts.py:40-43`,
  `chromatin_interaction_result_receipts.py:43-46`): imported `POLICY, atac_driver_argv, validate_atac_requested_job,
  validate_atac_run_plan, _dependency_roots` (chromatin: plus `TABLE_ROLES, TABLE_NAMES`). No `retained_policy`.
  The name `retained_policy` does not occur anywhere in `078b77668` outside `verification/`. The original compared
  against the constant: `same(plan["policy"], POLICY)` (old lines 626, 639, 680, 748, 757, 801, 818).
- Current: the reorganisation split the monolithic receipts file into `root/library/atac_result_*_receipts.py`
  and `chromatin_result_*_receipts.py` (new files, no pre-reorg ancestor) and changed the behaviour to
  `policy = retained_policy(plan['policy'], historical=_historical(intent))`
  (`root/library/atac_result_native_receipts.py:232,287`, `atac_result_worker_receipts.py:75`,
  `chromatin_result_native_receipts.py:205,260`, `chromatin_result_worker_receipts.py:92`).
- A function with that signature exists nowhere. The only `def retained_policy` in 33,111 .py files (tracked and
  untracked, excluding `verification/`, `runs/`, `build/`; `_superseded/` searched separately) is
  `def retained_policy(value)` -- one positional argument, no `historical` -- in
  `a101|a105|a106|a108/library/retained_input_authority/retained_native_read_profiles.py:38` and
  `a104/library/retained_native_read_profiles.py:38`. `git log -S"def retained_policy(" --all` returns only
  `dfe3e6091`; `git log -G"def retained_policy\(.*historical" --all` returns nothing.
- Second missing piece in the same call sites: `validate_atac_run_plan(value["original_plan"], historical=...)`
  (`atac_result_native_receipts.py:231`) and `validate_chromatin_run_plan(..., historical=...)`
  (`chromatin_result_native_receipts.py:204`), but every copy of those validators (root/library, top-level,
  a101, a105, a106, a108, a110) is `def validate_*_run_plan(value)`. So even if the import resolved, these
  calls would raise `TypeError`.
- Why no edit: the name is defined in no allowed scope (root/, root/library), the candidates are in other axes
  and have a different signature, and dropping `retained_policy` from the import line would only move the
  failure to a `NameError` at call time.
- Candidate sources for a real repair (owner decision): (i) the per-axis `retained_native_read_profiles.py`
  (two accepted policy profiles, with and without `wall_seconds: None`) -- would need a root copy and a
  `historical` parameter that no version has; (ii) revert the root split modules to the original constant
  comparison `same(..., POLICY)`. These differ in which saved policies are accepted, i.e. scientific/authority
  behaviour, not plumbing.
- Used by: live. `root/execution_episodes.py:222,228` (lazy), 60 `operations.py` homes under root
  (`operation_catalog`, lazy, e.g. `root/execution_result_acquisition/operations.py:43,47`), 60
  `report_fields.py` (`ORIGIN`, `SAVED_ORIGIN`, lazy), `root/library/atac_differential_presentation.py:189`,
  `root/library/chromatin_interaction_presentation.py:173`. All are function-level imports, which is why
  those homes import but would fail when the atac/chromatin path is taken.

### 3. root: `library.macs2_peak_tools` -- `No module named 'gene_annotation_episode.communication'` -- FIXED

- Original (`078b77668:gene_annotation_episode/macs2_peak_tools.py:15,17`): `from .communication import plain`,
  `from .episode_return_records import EpisodeReturnRecords`.
- Current before edit: lines 16 and 18 used `gene_annotation_episode.communication` and
  `gene_annotation_episode.episode_return_records`; neither top-level module exists (absent already at
  `dfe3e6091`). Line 18 was a second broken import hidden behind line 16.
- Targets: `root/communication.py` and `root/episode_return_records.py` -- the only modules of those names in
  root/ or root/library. `plain` is re-exported from `root/library/record_values.py:8` and is textually
  identical to the original. `EpisodeReturnRecords.__init__`, `_require`, `authenticate` (file lines 1-126) are
  identical to the original apart from the docstring and the module's own imports. The root class has lost
  four methods (`decision_witnesses`, `source_admission_before`, `file_admission_before`,
  `_results_assignment`); macs2 uses only `EpisodeReturnRecords(...).authenticate(context)` (line 420), so
  that is irrelevant here. The surviving top-level `gene_annotation_episode/macs2_peak_tools.py:15,17` already
  points at the same two root modules.
- Edit: lines 16 and 18 now import from `gene_annotation_episode.episodic_workflow.root.communication` and
  `...root.episode_return_records`.
- Used by: live. `root/direct_tool_catalog.py:34`, `root/direct_tool_execution.py:194`,
  `root/library/molecular_result_facts.py:351` (all lazy).

### 4-6. a102: `from . import blast_pssm_calculators | blast_iteration_calculators | blast_vdb_calculators` (15 modules) -- product_defect (files missing), NOT edited

- Original: the same relative imports, resolving to `gene_annotation_episode/blast_*_calculators.py`.
- Current: a102 never received these files (`git log --all` on `a102/blast_*_calculators.py` is empty).
  A fourth one is hidden behind the first failure: `blast_profile_calculators`
  (`a102/native_blast_database_result_worker.py:21`). a103, a104 and a107 have all four, byte-identical to the
  original (same blob hashes). root/library has all four, differing from the original only in import lines
  re-pointed into root/library (`blast_pssm_calculators` is byte-identical).
- Why no edit, although root/library is an allowed scope with exactly one copy each:
  1. `a102/native_blast_database_result_worker.py:1326-1338` names them as a102-local modules:
     `_module_name(name)` returns `"gene_annotation_episode.episodic_workflow.root.a102." + name` and
     `_implementation_modules()` calls `importlib.import_module` on `blast_profile_calculators`,
     `blast_pssm_calculators`, `blast_iteration_calculators`, `blast_vdb_calculators`. An import-line edit
     would make the module import and then fail in the implementation-identity step. That list is not an
     import line, so it is outside what I may change.
  2. root/library `blast_vdb_calculators` binds to root/library `blast_vdb_inputs`, `blast_program_context`,
     `blast_pairwise_grader`, `blast_sequence_database`, while the a102 callers use a102's own copies of those
     (different blobs). One calculation would run on two copies of the same helpers.
- Faithful repair (owner decision, needs file copies): add the four original files to a102 as a103/a104/a107
  have them; their relative imports then resolve to a102 siblings.
- Used by: live, through lazy imports. `a102/blast_result_views.py`, `a102/alignment_site_native.py`,
  `a102/library/evidence_geometry.py` import `native_blast_{,standard_}database_result_publication`;
  `blast_result_views` is used by `a102/tools.py:656,1726`, `a102/api_service_execution.py:936`,
  `a102/execution_progress.py:443`. The workers are also launched by module name
  (`native_blast_database_result_publication.py:592`, `native_blast_standard_database_result_publication.py:438`).
  Nothing outside a102 imports them.

### 7 and 9. a102 and a107: `from . import hmmer_artifact_data` in `native_hmmer_preparation_worker` -- product_defect (files missing), NOT edited

- Original: `from . import hmmer_artifact_data as artifact_data` plus eight sibling imports.
- Current: nine modules are missing in each of a102 and a107, not one. Lines 17-20, 22, 24-27 of both
  `native_hmmer_preparation_worker.py` files: `hmmer_artifact_data`, `hmmer_artifact_calculations`,
  `hmmer_emission_data`, `hmmer_emission_calculations`, `hmmer_fm_calculations`, `hmmer_simulation_data`,
  `hmmer_simulation_calculations`, `hmmer_statistics_data`, `hmmer_statistics_calculations`. Never committed
  under a102 or a107. a103 and a104 have all nine, byte-identical to the original. root/library has all
  nine; non-import lines are identical to the original (0 differing lines each).
- Why no edit: the root/library copies import root/library `hmmer_model_data`, `hmmer_model_calculations`
  and, through them, `hmmer_model_binary2`, which were refactored beyond imports (35, 2 and 115 differing
  non-import lines against the a102/a107 copies, which equal the original). The a102/a107 worker keeps using
  its own `hmmer_model_data`, `hmmer_fm_data`, `hmmer_alignment_preparation_*`. Pointing nine imports at
  root/library would run one grading through two different implementations of the HMMER model decoder. I
  could not establish that the refactor is behaviour-preserving, so condition (c) is not plainly met.
  If the owner accepts root/library's refactored `hmmer_model_*` as equivalent, the edit is mechanical: nine
  lines per file in the form root/library's own worker uses
  (`from gene_annotation_episode.episodic_workflow.root.library import hmmer_artifact_data as artifact_data`).
- Faithful repair (needs file copies): add the nine original files to a102 and a107.
- Used by: live, lazily. `native_hmmer_preparation_result_worker.py:255`
  (`from .native_hmmer_preparation_worker import grade_hmmer_preparation`) in both axes; that result worker is
  imported by `native_hmmer_preparation_results.py`, `native_hmmer_preparation_result_publication.py`,
  `native_blast_masking_result_worker.py`, `native_blast_utility_result_worker.py` in both axes. In a107,
  `native_hmmer_preparation_results` is in turn referenced by `a107_execution_bindings.py`,
  `execution_progress.py` and several `to_parent.py` / `completion.py` homes (grep on the module name; I did
  not trace each reference).

### 8. a104: `bvbrc_phylogeny_tool_info` -- no module `a104.scientific_process.execution_result_acquisition.requests` -- product_defect, NOT edited (one-line fix ready)

- Original (`078b77668:gene_annotation_episode/bvbrc_phylogeny_tool_info.py:11`):
  `from .execution_episodes import RESULTS_SCHEMA`.
- Current: `a104/execution_episodes.py` does not exist and no `requests.py` exists anywhere under root. In
  a104, 31 modules define `RESULTS_SCHEMA` with the same text, equal to the original
  (`obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})`):
  30 private episode-home modules (`result_records.py`, `received_result_values.py`, `contracts.py`) and the
  axis library `a104/library/execution_result_request_contracts.py:5`. `a104/resource_records.py:75` defines
  a different schema under the same name.
- Why no edit: condition (b) asks for exactly one provider in the axis; there are 31. They are textually
  identical, so the choice cannot change the value, but I did not treat that as permission.
- Ready fix: `from .library.execution_result_request_contracts import RESULTS_SCHEMA`. Precedent: the two
  sibling modules whose original import was the same line (`bvbrc_homology_tool_info`,
  `bvbrc_proteome_tool_info`) now import exactly that (`a104/library/bvbrc_homology_tool_info.py:10`,
  `bvbrc_proteome_tool_info.py:6`).
- Used by: nothing. No file in a104 (tests included) references `bvbrc_phylogeny_tool_info` or
  `phylogeny_tool_contracts`. The live consumer is root's copy
  (`root/execution_resource_information.py:224` -> `root/library/bvbrc_phylogeny_tool_info`). Unused leftover copy.

### 10. a110: `literature_current_results` -- `No module named 'gene_annotation_episode.episodic_workflow.domain'` -- FIXED

- Original (`078b77668:gene_annotation_episode/literature_current_results.py:10`): `from .domain import canonical`.
- Current before edit: `from ...domain import canonical`, which from `root/a110/` resolves to
  `episodic_workflow.domain`. The rest of the file is identical to the original.
- Target: `a110/domain.py`, the only `domain.py` in a110; `canonical` there is textually identical to the
  original. The a102 and a104 copies of this module use `from .domain import canonical`.
- Edit: line 10 is now `from .domain import canonical`.
- Used by: nothing. No file in a110 or elsewhere references `a110.literature_current_results`. Unused leftover copy.

## Verification

Run through the launcher, slot `triage_f`:

- `runs/claude_triage_triage_f_01`: the two edited modules -> `{}` (both import). 1.2 s.
- `runs/claude_triage_triage_f_02`: all 34 originally failing modules -> 32 failures, the two edited modules
  absent, the other 32 with the same messages as in `homes.json`. 2.0 s.

Not run: the full `verify_episode_homes.py` sweep over 593 homes, and any test.

Read, not run: every "used by" statement (grep over tracked and untracked .py files excluding `verification/`,
`runs/`, `_superseded/`, `build/`), the equality claims (blob hashes and diffs), and the prediction that an
a102 BLAST import edit would fail later in `_implementation_modules()`.

## Other observations

- `a110/literature_rate_domains.py:201,254,259,266,277` has function-level relative imports of
  `literature_rate_storage` and `literature_rate_source_render`, which do not exist in `a110/`. Not in
  `homes.json` because they are lazy; not investigated further.
- Process note: my first command parsed `homes.json` with a bare `python3` heredoc, outside the launcher. It
  read one JSON file and imported nothing from the repository; everything after that used grep/sed/git or the
  launcher.
- `a103/homology_results.py` shows as modified in the working tree; that is not from this task.
