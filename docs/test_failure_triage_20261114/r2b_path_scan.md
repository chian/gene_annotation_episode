# r2b additional task: static scan of `Path(__file__)` path expressions in product code

Scope: `gene_annotation_episode/episodic_workflow/root/**/*.py`, excluding `/tests/`, `test_*.py`, `conftest.py`,
`__pycache__`. Report only; no repository file was edited, no Python was run. `R/` below means
`gene_annotation_episode/episodic_workflow/root/`. Pre-reorganisation commit: `078b77668` (flat
`gene_annotation_episode/<module>.py`); reorganisation snapshot: `dfe3e6091`.

## Totals

| | count |
|---|---|
| product `.py` files in scope | 27,298 |
| files mentioning `__file__` | 1,029 (1,554 lines) |
| `Path(__file__)…parents[N]` / `.parent` occurrences | 1,022 (458 are variable bindings, 305 are `.glob/.rglob` on an existing directory) |
| `Path(__file__)…with_name(` occurrences | 181 |
| `Path(<imported module>.__file__)…` occurrences (extra) | 67 (31 bindings) |
| `_context_source_path(__file__).resolve().parents[N] / key` occurrences (extra) | 46, all reach the repository root, all 4 key files exist |
| expression sites (file:line) resolved to at least one concrete path | 668 |
| concrete (site, name) targets tested with `[ -e ]` | 104,337 (most come from long literal source rosters) |
| sites with at least one target that does not exist, after manual review | 27 sites in 27 files (A1-A13: 14 files that read or require the path; A14: 13 files that only glob a missing directory) |
| sites the script could not resolve (section D) | 67 `Path(__file__)` sites + 30 `source_file(name)` call sites; many were then evaluated by hand |
| `parents[1]` kept from the flat layout that no longer reaches the repository root (section B) | 14 sites in 13 files |

None of the files named in sections A and B shows as modified in `git status --short` (checked each). The only
modified product file I met was `R/a103/homology_results.py`, which has no finding.

## A. Path expressions whose target does not exist

### A1. `R/library/execution_guidance.py:5` (and its use at :17) — directory missing
- Current: `ROOT = Path(__file__).with_name('execution_instruction_library')`, then `(ROOT/(section+'.md')).read_text()`.
- Resolves to `R/library/execution_instruction_library/` — does not exist.
- Pre-reorganisation (`078b77668:gene_annotation_episode/execution_guidance.py:5`): identical text; the directory was
  `gene_annotation_episode/execution_instruction_library/`.
- The directory now lives at `gene_annotation_episode/execution_instruction_library/` (5 `.md` files) and in every axis
  (`R/a101..a110/execution_instruction_library/`; the nine axis copies of `execution_guidance.py` resolve correctly).
  There is none in `R/` or `R/library/`.
- Used by: `R/scientific_tool_library.py:99` (lazy `from .library.execution_guidance import recipe`).

### A2. `R/a103/bvbrc_comparative_systems_bundle_adapter.py:37` and `R/a103/bvbrc_genome_alignment_bundle_adapter.py:67` — `chemistry.py`
- Current: `Path(__file__).with_name(name).read_bytes()` for `name in sorted(_DEPENDENCIES)`; `_DEPENDENCIES` contains
  `'chemistry.py'` (lines 28 and 34). 1 of 32 and 1 of 44 names missing.
- Resolves to `R/a103/chemistry.py` — does not exist.
- Pre-reorganisation (`…/bvbrc_comparative_systems_bundle_adapter.py:37`, `…/bvbrc_genome_alignment_bundle_adapter.py:68`):
  identical text; `gene_annotation_episode/chemistry.py` existed beside the module.
- `chemistry.py` now lives at `gene_annotation_episode/chemistry.py` and `R/library/chemistry.py`; no axis has one.

### A3. `R/a110/component_axis_native_hpc.py:39-40` — `literature_reaction_calculations.py`
- Current: `axis_directory = Path(__file__).resolve().parent`; `(axis_directory / name).read_text() for name in names`;
  called at :149 with `('__init__.py', *SOURCE_FILES)`; `SOURCE_FILES` (:30-32) contains `'literature_reaction_calculations.py'`.
- Resolves to `R/a110/literature_reaction_calculations.py` — does not exist (the other five names do).
- Pre-reorganisation (`…/component_axis_native_hpc.py:140-141`):
  `directory = Path(__file__).parent`; `(directory/name).read_text() for name in SOURCE_FILES[axis]`.
- The file now lives at `R/a110/library/literature_reaction_calculations.py` (a110 code imports it from there, e.g.
  `R/a110/a110_chemical_accounting.py:13`) and `R/library/`. The a107 copy of this module has no missing name.
  The second caller (`R/a110/a110_fba_hpc.py:121-122`, `FBA_SOURCES`) resolves fully.

### A4. `R/library/native_phmmer_preparation.py:43-45` — `phmmer_result_worker.py`
- Current: `Path(__file__).with_name(name).read_bytes() for name in ('phmmer_format.py', 'phmmer_result_worker.py',
  'phmmer_grading_worker.py', 'hmmer_search_inputs.py', 'hmmer_search_grader.py', 'hmmer_graders.py')`.
- `R/library/phmmer_result_worker.py` does not exist (the other five do).
- No pre-reorganisation ancestor under this name (first commit `dfe3e6091`). The same loop was
  `078b77668:gene_annotation_episode/homology_results.py:288-290` with identical text; `phmmer_result_worker.py`
  was then a flat sibling.
- The file now exists only in `R/a101/`, `R/a103/`, `R/a104/`. The axis copies of the loop
  (`R/a101|a103|a104/homology_results.py:288`) resolve fully.
- Used by: `R/homology_results.py:12`.

### A5. `R/terminal_binding_catalogue.py:233-235` — `yield.py` in six homes
- Current (`source_record`, :222-239): `owner = <repo>/gene_annotation_episode/episodic_workflow/root`;
  `required.update(owner / home / (name + '.py') for name in ('credit', …, 'waiting', 'yield'))` for the six homes in
  `PARENT_ENTRIES`; then `required.issubset(set(files))` or `ValueError('root_terminal_catalogue_source_required')`.
- `R/{,legacy_annotation/,scientific_process/}{local,hpc}_job_execution/yield.py` do not exist (6 paths); the other
  20 names exist in all six homes.
- No pre-reorganisation ancestor (first commit `dfe3e6091`). Commit `5cafe5c43` ("Rename yield.py to
  yield_estimator.py …") renamed the files; this list still says `'yield'`. A sweep for the literals `'yield'`,
  `"yield"`, `/yield.py` over all product files finds only this line.
- Used by: `R/episode_composition.py:383,420`, `R/episode_bindings.py:209`.

### A6. `R/literature_rate_observation_storage.py:415` — 8 of 12 receipt files
- Current: `Path(__file__).with_name(name).read_bytes() for name in self._receipt_files()` (`_original_implementation`,
  called at :457); the tuple is at :405-410.
- Missing under `R/`: `literature_rate_observation_inputs.py`, `literature_rate_observation_calculations.py`,
  `literature_rate_observation_prompt.py`, `literature_numerical_return_presentation.py` (all four now in `R/library/`),
  `spreadsheet_tools.py` (now `gene_annotation_episode/spreadsheet_tools.py`), and `literature_episodes.py`,
  `literature_experimental_prompt.py`, `literature_reference_parent_prompt.py` (not in `R/`, `R/library/` or the
  top-level package; the two prompts exist only in axes a102, a104, a105, a106, a108).
- Pre-reorganisation (`…/literature_rate_observation_storage.py:517`): identical text; all were flat siblings.
- This is an implementation-digest site (A105 family): report only.

### A7. `R/literature_binding_interaction_storage.py:121-123` — 7 of 9 names
- Current: `names = [*_FROZEN, "literature_binding_interaction_validation.py", "literature_binding_interaction_storage.py",
  "literature_binding_interaction_render.py"]`; `Path(__file__).with_name(name).read_bytes() for name in names`.
- Missing under `R/`: the two literal names `…_validation.py`, `…_render.py`, and five `_FROZEN` keys
  (`literature_binding_interaction_inputs.py`, `…_calculations.py`, `literature_binding_visual_inputs.py`,
  `literature_binding_reader.py`, `literature_experimental_contracts.py`). All seven now live in `R/library/`.
- Pre-reorganisation (`…/literature_binding_interaction_storage.py:113-115`): identical text.
- Reached only for a saved receipt that is neither absent nor `root_binding_interaction_implementation_v3`
  (:110-120 return earlier). Implementation-digest site: report only.

### A8. `R/literature_kinetic_storage.py:81-82` — 3 of 4 names
- Current: `names = [*_FROZEN, "literature_kinetic_validation.py", "literature_kinetic_storage.py"]`; `with_name(name)`.
- Missing under `R/`: `literature_kinetic_validation.py`, `literature_kinetic_inputs.py`,
  `literature_partner_source_fields.py` (all in `R/library/`).
- Pre-reorganisation (`…/literature_kinetic_storage.py:82`): identical text.
- Lines 76-79 return `prospective('kinetic')` when the module is loaded under its `R/` name, so this loop is not
  reached in a normal import. Implementation-digest site: report only.

### A9. `R/literature_product_coupling_storage.py:74` — 3 of 3 names
- Current: `Path(__file__).with_name(name).read_bytes() for name in _FROZEN`.
- Missing under `R/`: `literature_product_coupling_inputs.py`, `…_calculations.py`, `…_prompt.py` (all in `R/library/`).
- Pre-reorganisation (`…/literature_product_coupling_storage.py:308`): identical text.
- Lines 71-73 return `prospective('product_coupling')` under the `R/` module name, so not reached in a normal import.

### A10. `R/literature_binding_interaction_release.py:59-61` — `gene_annotation_episode/record_serialization.py`
- Current: `project = Path(__file__).resolve().parents[3]` (the repository root); `(project / relative).read_bytes()`
  for `relative in _RELEASE['files']`; the roster (:10-36) names `gene_annotation_episode/record_serialization.py` (:35).
- That file does not exist; `record_serialization.py` exists only at `R/library/record_serialization.py`.
- No pre-reorganisation ancestor (module and `record_serialization.py` both first appear in `dfe3e6091`).

### A11. `R/literature_product_kinetic_relocation.py:85-88` — same missing file, two rosters
- Current: `project = Path(__file__).resolve().parents[3]`; `path = project / relative` for `expected['files']`;
  both `_RELEASES['kinetic']` (:33) and `_RELEASES['product_coupling']` (:58) name
  `gene_annotation_episode/record_serialization.py`. No ancestor before `dfe3e6091`.
- This is the function A8 and A9 fall through to, so the kinetic and product-coupling "prospective" checks both read
  a path that does not exist.

### A12. `R/literature_concentration_window_release.py:28-31` — `R/published_evidence_assessment/source_contracts.py`
- Current: `root = Path(__file__).parents[3]`; `(root / name).read_bytes() for name in _FILES`; `_FILES` (:19, 206 names)
  includes `gene_annotation_episode/episodic_workflow/root/published_evidence_assessment/source_contracts.py`.
- That file does not exist (never committed there; `dfe3e6091` has none). `source_contracts.py` exists at
  `R/scientific_process/source_contracts.py` and under several axes' `published_evidence_assessment/`.
- No ancestor before `dfe3e6091`. Used by `R/literature_concentration_window_storage.py:14`.

### A13. `R/library/literature_endpoint_signal_source_receipt.py:1230-1232` — same missing file
- Current: `root = Path(__file__).resolve().parents[4]`; `(root / name).read_bytes() for name in _RELEASE['current_sources']`;
  the roster (:15-194, 178 names) includes the same `…/root/published_evidence_assessment/source_contracts.py` (:187).
- No ancestor before `dfe3e6091`.

### A14. `R/a105/**/published_evidence_assessment/**/source_contracts.py:57-60` (13 of the 14 copies) — `prompts/`, `tools/` directories
- Current: `home = Path(__file__).parent`; `for name in ('prompts', 'tools', 'grading', 'scoring'): paths.extend((home / name).glob('*.py'))`.
- `prompts/` and `tools/` are missing in 13 homes (7 under `R/a105/published_evidence_assessment/…`,
  6 under `R/a105/scientific_process/published_evidence_assessment/…`); `grading/` and `scoring/` exist. The only
  `prompts/` and `tools/` directories in a105 are in
  `R/a105/scientific_process/…/source_evidence_examination/`, whose own loader is `implementation_sources.py`.
- `glob` on a missing directory yields nothing, so nothing raises; those bytes are simply not in the digest.
- No ancestor before `dfe3e6091`.

## B. `parents[1]` kept from the flat layout (target directory exists, but it is no longer the repository root)

In `078b77668` each module sat at `gene_annotation_episode/<module>.py`, so `Path(__file__).resolve().parents[1]` was
the repository root. Sibling copies were rewritten to `parents[4]` (or `[6]`); these were not:

| file:line | current expression | resolves to | sibling copies / pre-reorg |
|---|---|---|---|
| `R/a103/native_blast_masking_result_publication.py:231` | `env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]), …}` | `R/` | a101, a102, a107, `R/library`: `parents[4]`; pre-reorg :231 `parents[1]` |
| `R/a103/native_blast_utility_result_publication.py:275` | same `PYTHONPATH` form | `R/` | a101, a102, a107, `R/library`: `parents[4]`; pre-reorg :275 |
| `R/a103/native_hmmer_preparation_result_publication.py:271` | `_source_closure(Path(__file__).resolve().parents[1], modules)` | `R/` | a101, a102, a104, a107, `R/library`: `parents[4]`; pre-reorg :271 |
| `R/a103/native_hmmer_preparation_result_publication.py:278` | `freeze_driver_runtime(module_root=str(Path(__file__).resolve().parents[1]), …)` | `R/` | same; pre-reorg :278 |
| `R/a107/native_infernal_local.py:24` | `{"PYTHONPATH": str(Path(__file__).resolve().parents[1]), …}` | `R/` | `R/library`: `parents[4]`; pre-reorg :24 |
| `R/a107/native_infernal_preparation_local.py:27` | same | `R/` | `R/library`: `parents[4]`, a110 copy: `parents[6]`; pre-reorg :27 |
| `R/a107/native_rna_structure_local.py:21` | same | `R/` | `R/library`: `parents[4]`; pre-reorg :21 |
| `R/a102/execution_memory.py:65`, `R/a104/execution_memory.py:65`, `R/a110/execution_memory.py:65` | `default = Path(__file__).resolve().parents[1]/'runs'/'shared-execution'/'memory.sqlite3'` | `R/runs/shared-execution/memory.sqlite3` | a101, a103, a105-a108: `parents[4]` → `<repo>/runs/shared-execution/…`; pre-reorg :65 `parents[1]` |
| `R/a101|a105|a106|a108/library/retained_input_authority/native_protein_structure_preparation.py:61` | `_PACKAGE_ROOT = str(Path(__file__).resolve().parents[1])` (default `package_root` of `_intent`, :162) | `R/<axis>/library/` | a102 and `R/library` copies: `parents[4]`; pre-reorg :82 `parents[1]` |

Consequences read from the code, not run: with `PYTHONPATH=R/` a child `python -m gene_annotation_episode.…` cannot
import the package; the three `execution_memory.py` copies default to a database inside application source.
`R/runs/shared-execution/` exists on disk (created 2026-11-12, ignored by `.gitignore:30 *.sqlite3`), which is
the run-output-in-source case AGENTS.md forbids. The four `retained_input_authority` copies may be intentional
(they authenticate retained inputs); I did not establish that.

Of 556 `parents[N]` occurrences, 187 resolve to the repository root. Of the 169 lines that use a `__file__`-based
directory as an import root (`PYTHONPATH`, `sys.path`, `module_root`, `package_root`, `_source_closure`), 152 resolve
to the repository root, 11 are in this table, and 6 search upward for the directory that contains the package.
The `execution_memory.py` rows are not import roots and are counted separately.

## C. Related: literal repository-relative paths that do not exist (not built from `__file__`; not analysed in depth)

A sweep of all product files for quoted `gene_annotation_episode/….(py|json|md|toml)` literals found 6,237 distinct
paths, 16 missing. Two are A10-A13. The rest are compared against a runtime manifest root or a snapshot root, not
opened relative to `__file__`:
- `R/a102|a104/native_blast_standard_database_driver.py:220-223,264`, `R/a102|a104/native_blast_database_driver.py:242,317`,
  `R/a102|a104/native_blast_standard_database_contracts.py:621-623`, `R/a102|a104/native_blast_database_contracts.py:609`:
  the a102 and a104 copies compare `Path(__file__).resolve()` and the manifest roster against
  `…/root/a101/native_blast_*_driver.py`, `…/a101/native_blast_*_contracts.py`, `…/a101/blast_program_context.py`,
  `…/a101/blast_pssm_inputs.py`. Those paths name another axis, and three of the four do not exist even in a101 (they
  are in `R/a101/library/`). The a101, a103 and a107 copies name their own axis.
- `R/library/native_blast_standard_database_contracts.py:621`: required roster names
  `gene_annotation_episode/native_blast_standard_database_driver.py` (does not exist).
- `gene_annotation_episode/{expression_nmf,fluorescence,flux_balance}_result_worker.py` and `fluorescence_fcs_reader.py`
  in `native_expression_nmf_preparation.py`, `native_fluorescence_{contracts,preparation}.py`,
  `native_flux_balance_preparation.py` (mostly `retained_input_authority` copies; also `R/a107`, `R/a110`,
  `R/a104/library`, `R/library/native_flux_balance_preparation.py:328`): membership tests on saved pin lists.
- `R/a101/library/native_blast_*_contracts.py:634-683`, `R/a110/library/received_execution_dependencies/native_blast_*_contracts.py:466,482`:
  rosters commented as retained historical profiles.
- `R/scientific_process/definition_inputs.py:327`: `…/a106/a106_work_report.py` in `OPTIONAL_WORK_REPORT_FILES`,
  guarded by `is_file()` at `R/scientific_process/binding_record.py:11-12` — benign.
- `R/a104/literature_implementation_sources.py:11`: `LITERATURE_BINDING_SOURCES_BEFORE_SOURCE_TASKS_20261112` lists 28
  `requests.py` / `returns.py` paths that do not exist; the tuple is referenced nowhere else.

## D. Not statically resolvable (count only)

67 `Path(__file__)` sites and 30 `source_file(name)` call sites were left unresolved by the script. The bundle adapters, release rosters, definition inputs and the items marked "checked by hand" below were then evaluated manually; the rest are unchecked. Examples:
1. `R/a10x/bvbrc_application_definitions.py:105,110` — `_SPECS / entry["original_file"]` (names come from a JSON index; 6 files).
2. `R/a110/library/received_execution_dependencies/adapter_source_identity.py:101,147,154` — paths from a JSON manifest.
3. `R/a105/molecular_measurement_tools.py:57` — `with_name(_molecular_worker_module(operation).rsplit(".", 1)[-1] + ".py")` (both possible values checked by hand: exist).
4. `R/a104|a105|a106/literature_implementation_sources.py:7,10,11` — `source_file(name)` helper; names come from callers in other modules.
5. `R/a105/library/literature_optical_storage.py:57`, `…/literature_endpoint_signal_storage.py:145` — `source_file(name)`; the script found no literal name source (unchecked).
6. `R/library/literature_controlled_response_v2_inputs.py:42,58` — `names = [*shared.DEPENDENCIES, …]` mapped through a `paths` dictionary (its 12 values, the 14 in `…_v3_inputs.py` and the 36 in `R/literature_controlled_response_storage.py` checked by hand: exist).
7. `R/a105/…/source_evidence_examination/implementation_sources.py:9,11` — dictionary-mapped names (the two literal maps were checked by hand: 216 + 245 entries, all exist).
8. `R/library/literature_optical_dependency_custody.py:22,37` — `root / selected["relative_target"]` (JSON string; its 4 values checked by hand: exist).
9. `R/a105/runtime_assets.py:16` — conditional tuple (3 literal names checked by hand: exist).
10. `R/library/resource_binding_records.py:118-124` — `home + '/' + name + '.py'` product (45 homes x 22 names checked by hand: all exist).

## Method and blind spots

Method: `grep` for `__file__` in the 27,298 product files (1,029 files), then an mawk script
(`…/scratchpad/r2b/pathscan7.awk`) that (1) binds variables assigned from `Path(__file__)[.resolve()|.absolute()]`
followed by `.parents[N]` / `.parent…` / `.with_name('lit')`, and variables derived from those with `/ 'lit'`,
`.parents[N]` or `.parent`; (2) parses every `<base> / 'lit' / …`, `.joinpath('lit')` and `with_name('lit')`;
(3) when the last component is an identifier, looks for the literal tuple/list it loops over (same line or next three
lines first, then the nearest `for` in the ten lines before), a module-level collection of that name, a same-file
function returning literals, or literal call sites of the enclosing function; (4) resolves
`Path(<alias>.__file__)` through the file's import line. Each resolved path was tested with `[ -e ]`; 64-hex strings
(digest values picked up from dictionaries) were dropped. Every site reported missing by the script was then read by
hand; conditionals (`a if name == … else b`), dictionary-valued names, JSON-embedded rosters, cross-module name lists
(`definition_inputs.py`, `source_file()` callers, `SOURCE_FILES` passed as an argument) and `self._method()` name
sources were evaluated by hand or with a small helper (`varstrings.awk`). Pre-reorganisation text came from
`git show 078b77668:gene_annotation_episode/<basename>.py`.

Blind spots:
- Names that reach a path through another module, a function argument, a JSON file or run-time data are only covered
  where listed above; section D sites are unchecked.
- A variable bound inside one function is assumed to keep its meaning until reassigned or the next `def`; a name reused
  for something else on a path the script cannot see would be mis-resolved.
- Where a line holds two loops over different collections, or a conditional chooses between two bases, the script may
  attribute names to the wrong base. Every "missing" result was hand-checked, but a wrong attribution that happened to
  resolve to an existing file would be reported as fine.
- `os.path`-based expressions: none found. `Path(__file__).parent.glob(...)` (305) was not expanded.
- Existence only: a path that exists but is the wrong copy (another axis, the top-level package versus `R/library`)
  is not detected, except for the `parents[1]` cases in section B.
- Test files and fixtures were out of scope.
