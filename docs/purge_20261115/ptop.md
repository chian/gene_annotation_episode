# ptop: backward-facing removal in the top-level package, `method_loop/`, `examples/` (15 November 2026)

Area: files directly in `gene_annotation_episode/` (369 modules at start, 273 now), its data files and
sub-directories other than `episodic_workflow/`, the repository-level `method_loop/`, `examples/`, and (by handoff
from pa104/pa107) the package-data table of `pyproject.toml`. No commits. The four sub-agents the brief allows could
not be started (the session's sub-agent limit was already reached), so the sweep of the remaining 273 modules was done
by one agent with targeted searches, not by reading every line; see "Not examined line by line".

## 1. Duplicate modules: which side current code imports

Method: an AST import graph over 32,518 Python files (run `runs/claude_ptop_001/graph.json`): imports with relative
levels resolved, plus string constants naming `gene_annotation_episode.<module>`. Seeds are current product code:
everything under `episodic_workflow/root` outside `tests/`, `examples/`, `tools/`, the `gene-episode` entry point and
the launcher. Closure through top-level modules. Checked separately: file-name literals resolved against the top-level
directory (`parents[N] / name`, repo-relative `gene_annotation_episode/<file>` literals, `with_name`), non-Python
references, and dynamic imports.

Finding that corrects the earlier analysis: the top-level package is NOT unused by the root runtime. Root product
code imports about 120 top-level modules directly (`domain` from 3,217 files, `launch_instructions` 1,656,
`execution_contracts` 1,309, `acquisition` 1,210, ...) and launches others as `python -m gene_annotation_episode.<worker>`.
What is true is narrower: for the modules that also exist in `root/` or `root/library/`, root code imports its own copy.

- Top-level modules with a counterpart in `root/` or `root/library/`: 244 (27 + 218, one in both; the earlier "26"
  missed `credit.py` because of a sort-order error in the comparison).
- Deleted, no current product importer: 96 modules, 32,275 lines
  (`runs/claude_inputs/purge/ptop_work/deleted_modules.txt`). 79 had no importer at all outside tests. 16 more
  (the ATAC and chromatin host chain: `atac_differential_returns`, `atac_differential_result_receipts`,
  `native_atac_differential_results`, `..._preparation`, `..._local`, `atac_differential_execution_information`,
  `atac_differential_return_views`, and the eight chromatin equivalents including
  `chromatin_interaction_legacy_return_schemas`) were named only in descriptive "implementation" strings of
  `root/library/*_execution_information.py`; nothing imports or launches them. Plus `scientific_credit.py` (retired
  stubs, no counterpart, tests only).
- Kept because current product code imports, launches or reads them: 148
  (`runs/claude_inputs/purge/ptop_kept_duplicates.tsv`: module, counterpart, reason, evidence file). 20 are imported
  directly by root product code or examples, 101 are reached through other live top-level modules, 26 are named as
  worker/driver modules in root product code (`DRIVER_MODULE`, `REQUIRED_MODULES`, `-m` command lists),
  `hpc_allocation.py` is read as text by `hpc_campaign.py:161`.
- `episode_bindings.py` (second `BindingContext`) is kept: 11 live top-level modules import it
  (`molecular_reference_privacy.py:259`, `molecular_measurement_tools.py`, `enrichr_reference_privacy.py`,
  `form_reference_validation.py`, `case_execution.py`, ...) and `examples/local_hpc_routing_investigation.py:127`.
  The defect r4a P4 describes (top-level modules type-check against this class while root builds
  `root.receiving_context.BindingContext`) is therefore still present; repairing it means re-pointing those 11
  modules, which is a behaviour change outside this removal.
- Repository-level `method_loop/` is kept: 29 root product files and 13 top-level modules import it, and
  `method_loop.durable` launches `-m method_loop.durable_worker`. `root/method_loop/` (differs only in `durable.py`)
  belongs to proot.
- Unreferenced by product code, no root counterpart, kept (only home of that code): `episode_progress_credit.py`,
  `fixed_target_seed.py`, `geo_acquisition.py`, `literature_contract_error.py` (eight axis copies exist).

## 2. Removed, by class

| class | what | where |
|---|---|---|
| 6 | 96 leftover modules (above) | `gene_annotation_episode/*.py` |
| 6 | three legacy data files, 26,231 lines; no reader left at top level, root reads its own copies | `bvbrc_fastqutils_legacy_v2_schemas.json`, `bvbrc_fastqutils_legacy_cutadapt_schemas.json`, `literature_assay_grading_legacy_cells_v1.json` |
| 6 | `local_example/workflow.py` (336 lines): imported `..communication`, `..numerical`, `..providers`, `..runtime`, which no longer exist there; did not import at HEAD; nothing references it | |
| 2 | acceptance of the two older RequestedForm grammars: `_LEGACY_DEFS`, `_CUTADAPT_DEFS`, `_LEGACY_CUTADAPT_DEFS`, the `definitions` argument of `_definition_closure`; a non-current form now fails `requested_form_invalid` | `bvbrc_fastqutils_contracts.py` |
| 2 | saved resource definitions/settings carrying `cpu_threads` / `max_running_jobs`: `_saved_limits`, the `_restoring_definition` parameter and its two alternative definitions | `local_resources.py` |
| 2 | handles written without `local_resources` metadata (the "legacy never-dispatched handle" branch and three `if 'local_resources' in ...` guards, the `cpu_threads` default); receipts with retired policy settings (`LocalJobPolicy(**meta['policy'])`) | `native_lifecycle.py` |
| 2 | reading the `practical.job.start` tool name of earlier runs | `hpc_prediction_audit.py` |
| 2 | prepared records that predate `root_goal` | `examples/partner_chemical_investigation.py` |
| 2 | `ALTER TABLE commissions ADD COLUMN failure` migration | `method_loop/durable.py` |
| 1 | retired scorer stubs `CreditPolicy`, `project_credit`, `_retired`, and the old-import names `AXES`, `PROJECTION_VERSION`, `LEGACY_INTEGRATION`, `STABLE_INTEGRATION` | `credit.py` |
| 1 | retired `credit_policy` parameter and its "retired" error; CLI no longer passes it | `export.py`, `cli.py` |
| 1 | unused compatibility helpers `parse_uniprot`, `uniprot_pagination` | `acquisition.py` |
| 7 | history narration in 13 places | `acquisition_types.py`, `workflow_budget.py` (one docstring line, nothing else touched), `boundary_validation.py`, `bvbrc_fastqutils_metric_specs.py`, `chromatin_hic_records.py`, `local_job_policy.py`, `hpc_prediction.py`, `molecular_result_facts.py`, `tool_grading_artifacts.py`, `evidence_geometry.py`, `source_display_labels.py`, `component_assessment_dependencies.py`, `local_resources.py` |
| 3 | none found in this area | |

Counts: 100 files deleted (58,842 lines); 34 files edited (about 580 lines removed); tests deleted: 0 (the area has
no test files).

Owner decision applied (handoff row from h2, 11 sites plus one bound derived from it): native/local job memory policy
is the 5 GiB launcher bound in `molecular_sequence_ordinary.py`, `native_atac_differential_contracts.py`,
`native_chromatin_interaction_contracts.py`, `native_homer_execution.py`, `somatic_variant_contracts.py` (also
`java_heap_mb < 5 * 1024`), `molecular_sequence_result_contracts.py` (three sites),
`chromatin_interaction_contracts.py` (`_DEFINITIONS` Policy const), `defaults.toml` (`[local_jobs]`,
`[local_resources]`), and three sentences in `knowledge/*.md`. Written as the literal 5368709120: several of these
modules run inside isolated workers that carry only a listed module set, so they do not import `workflow_budget`.

`pyproject.toml` package-data (handoffs from pa104 and pa107, plus this area's own entries): 99 patterns that match
no file were removed; 10 packages remain.

## 3. Live despite its name (kept)

| name | where | evidence that current code uses it |
|---|---|---|
| `legacy_uniprot_records`, `legacy_publication`, `LegacyPublication` | `uniprot_native.py`, `uniprot_native_contracts.py` | `root/tool_reference_imports.py:141,195`; field of the current native record schema |
| `legacy_pointer` | `alignment_correspondence.py`, `biopython_pairwise_grader.py`, `tool_grading_artifacts.py` | field of the current correspondence instance record |
| `_LEGACY_PROFILE = "legacy_v1"` | `molecular_sequence_result_contracts.py:39` | default profile of the current ORF operations (`field_table`, `molecular_sequence_fact_sources`) |
| `_historical_store_root`, `_historical_path`, `_historical`, `_validate_historical`, `historical_result_witness` | `homer_motif_tools.py`, `macs2_peak_tools.py`, `tf_binding_tools.py`, `somatic_variant_*`, `esm_gene_embedding_tools.py`, `enrichr_returns.py`, `bvbrc_fastqutils_returns.py` | they authenticate results completed earlier in the same run (durable replay), not records of an earlier program |
| `legacy_checkpoint_requires_timer_only_wait` | `hpc_scheduler.py:31` | the wait-id checkpoint form is passed today by `examples/aurora_resource_prediction_investigation.py:236` and `examples/local_hpc_routing_investigation.py:210,277` |
| `samstat_legacy_*`, `legacy_columns_absent`, `old_p_value`, "legacy BioMart" | fastqutils SAMstat modules, `enrichr_contracts.py`, `acquisition.py:1010` | formats of external tools and services |
| `prepare_ordinary_orf_attempt`, `run_ordinary_orf_attempt`, `compile_ordinary_orf_selection` ("Compatibility ...") | `molecular_sequence_ordinary.py`, `molecular_sequence_tools.py` | the current ORF path calls them (`molecular_sequence_tools.py:330,567,569`, same lines in `root/library`) |
| historical observations / weights | `hpc_prediction.py`, `hpc_campaign.py` | timing history used for prediction |
| coexisting versions `tool_grading_artifact_v1/_v2`, `execution_status_v1/_v2`, `molecular_sequence_request_v1/_v2/_v3`, driver request `_v1/_v2` | `tool_grading_artifacts.py:58`, `episode_progress_credit.py:59`, `molecular_sequence_native.py`, `molecular_sequence_driver.py` | each is written by current code for a different operation or mode (e.g. `tool_grading_artifacts.py:58` writes v2 with correspondence, v1 without) |

## 4. Kept and undecided (first pass; items 1-4 below were decided in the second pass, section 8)

- `materials.py:642` accepts manifest `schema_version` 1 and 2: a user-supplied input file; no writer in the product
  to show which is current.
- `api_rfam.py:181` ("Older report selections remain artifact-only") and `:252` (envelopes without an HTTP capture
  are skipped): model-facing text and a guard whose current use I did not establish.
- Comments that call a current data variant "legacy" without any selecting code: `rcsb_acquisition.py:318`,
  `molecular_provider_acquisition.py:220,614`, `bvbrc_appservice_contracts.py:455`, `addgene_sequence_returns.py:385`,
  `alignment_site_native.py:321,359`, `state.py:436,591,668`, `scientific_findings.py:102`.
- `knowledge/index.json` (3 entries) and `launch_instruction_library/index.json` (1) list deleted modules in their
  descriptive `provenance` arrays (`experimental_database_measurements.py`, `native_blast_contracts.py`,
  `alignment_site_returns.py`, `blast_search.py`); nothing validates these paths. Left as they are.
- Digest and module-name registrations (`REQUIRED_MODULES`, `DRIVER_MODULE`, `*_SHA256`, `method_loop/LOCAL_PATCHES.json`
  with the pre-edit hash of `durable.py`): untouched, left to h4.

## 5. Not examined line by line

The remaining 273 modules (96,000 lines) were searched for
`historical|legacy|deprecated|compat|migrat|retired|stale|older|previously|superseded|alias|moved|relocat`, version
tuples, schema migrations and code-movement narration, and every hit of the first eight terms was read in context.
The roughly 300 `previous`, 76 `prior`, 150 `before_/_before` and 900 `_v1` hits were sampled, not read one by one;
the samples were all in-run or scientific meanings. A backward-facing branch that uses none of these words would
not have been found.

## 6. Verification

- Import check of all 272 top-level modules, `local_example.*` and `method_loop.*`: before edits
  (`runs/claude_ptop_010`) one failure, `local_example.workflow` (pre-existing); after all edits (`runs/claude_ptop_019`) the same single
  failure and no other; that file was deleted afterwards.
- Test files for the changed modules (before = latest earlier result; passed/failed):
  `test_native_lifecycle` 6/0 -> 6/0; `test_local_jobs` 10/0 (+1 skipped) -> same; `test_export` 13/0 -> 13/0;
  `test_local_resource_capacity` 0/10 -> 0/10 (same pre-existing causes: `KeyError: 'cpu_threads'`,
  `native_request_exceeds_environment_bounds`, `whole_workflow_budget_unavailable`, `KeyError: 'job_slots'`);
  `test_local_job_configuration` 6/1 -> 6/1 (same case); `test_bvbrc_fastqutils_contracts` 40/0 -> 18/0 (the file
  now collects 18; I did not edit it); `test_detached_job_service` 2/0 -> 1 failed in run 037
  (`service_did_not_initialize`), 2/0 on rerun 038: intermittent under host load.
- Not run: the roughly 190 test files that import deleted modules or removed names; they now fail at import by
  design and are listed as handoffs.

## 7. Handoffs

Written (257 rows in `handoffs.tsv`): ptests 164, proot 52, pa105 16, pa101 8, prootlib 7, pa107 4, pa103 2, pa106 2,
pa108 1, pa110 1. Kinds: importers of the 96 deleted modules (215 rows); the seven descriptive strings in
`root/library/atac_differential_execution_information.py` and `chromatin_interaction_execution_information.py` that
name deleted modules; about 30 test files importing the retired `project_credit` from `gene_annotation_episode.credit`;
tests of the old fastqutils grammars, `uniprot_pagination`, saved `max_running_jobs` definitions; the 5 GiB policy.
Applied (addressed to ptop): h2 memory row (all 11 sites); pa104 and pa107 `pyproject.toml` rows. The pa107 row about
`tests/test_chemistry_evidence.py:265` names a file in ptests' area: forwarded to ptests, not applied.

## 8. Second pass (after the coordinator's follow-up)

The sub-agent fan-out was tried again and refused again (session limit of 20 concurrent sub-agents), so this pass was
also done by one agent.

Decided and removed:
- `allow_legacy_quote` is gone from `domain.source_location_inputs` (the quote property is always removed from location
  inputs) and from its caller `state.py:1898`. A reasoning proposal whose anchor supplies `quote` is now refused by the
  existing representation error. `Store.put` still accepts host-built anchors that carry a quote (they are validated by
  the record schema and `_anchor`). One caller elsewhere: `root/literature_required_grading.py:169-170` (handoff to proot);
  until it drops the argument that call raises `TypeError`.
- Material manifest: `materials.py` accepts only `schema_version` 2 (versions 1 and 2 were treated identically; the
  documented form is 2). The three examples that wrote version 1 now write 2.
- `api_rfam.py`: the skip for envelopes without an HTTP request capture is removed (the current client always records
  it, `acquisition.py` `_http`); the "Older report selections" sentence is reworded. The selector versions v1-v3 are
  defined in `root/library/rfam_batch_contracts.py` (prootlib).
- Old uncapped BV-BRC download form (found behind a "legacy" comment): `Arguments_download` now requires `max_bytes`
  in `bvbrc_appservice_schemas.json` (both occurrences); `download_request` accepts only
  `{url, byte_range, max_bytes}`; the tolerance in `bvbrc_appservice_readers.py`, `bvbrc_appservice_preparation.py`,
  `bvbrc_appservice_publication_validation.py` and the "retained contracts accept the exact old shape" patch in
  `bvbrc_appservice_tool_info.py` are removed.
- `protease_kinetics_components_v1` (no current writer; `protease_kinetics_measurements.COMPONENTS_SCHEMA` is v2) is
  removed from `molecular_sequence_result_contracts.py` `SCHEMAS`, `REASONS` and the qualifier reason enum.
- `knowledge/index.json` and `launch_instruction_library/index.json`: every `provenance` entry naming a file that does
  not exist was removed, not only the four from this purge: 56 and 28 entries (they named the pre-reorganisation
  layout, e.g. `gene_annotation_episode/tools.py`). Ten instruction entries now have an empty `provenance` list
  (`native-gene-context`, `native-blast-standard-database-results`, `native-blast-database`, `native-blast-pairwise`,
  `blast-hsp-columns`, `bvbrc-minhash-distance-results`, `hmmer-api-numerical-results`, `native-phmmer`,
  `native-structural-homology`, `launch-api-bvbrc-data-v2`); nothing validates the field.
- Comments calling a current variant "legacy" reworded in `rcsb_acquisition.py`, `molecular_provider_acquisition.py`,
  `alignment_site_native.py`, `state.py`, `addgene_sequence_returns.py`.
- Handoffs applied: `examples/a101_a102_root_mock.py` deleted (it imported a deleted test fixture; proothomes row);
  `pyproject.toml` testpaths/pythonpath entries for `root/homology_job_submission` removed (proothomes row). The
  prootlib row about `molecular_measurement_tools.py:257,312` needed no change.

Read in this pass: all 513 hits of `previous`, `prior`, `before_`, `_before` (every one is an in-run, algorithmic or
scientific meaning; none removed), and the 957 `_v<digit>` hits as follows: the 120 lines where a version takes part
in a set, tuple, comparison chain or conditional were read and their writers traced; the other roughly 840 are single
constants or single equality checks. Also checked: 183 `anyOf`/`oneOf` uses (nullable or union types, none an older
form), upgrade/convert/migrate function names (none), defaulted `.get()` reads in `state.py`, `domain.py`,
`materials.py` (schema-optional fields).

Still kept, with the writer evidence:
- `blast_database_sheet_v1/_v2/_v3` (`tool_grading_artifacts.py:23`): all three are written by
  `root/library/blast_database_grader.py:24-26`.
- `molecular_sequence_request_v1/_v2/_v3`, driver request/declaration `_v1/_v2`, worker plan `_v1/_v2`, supplied
  failure `_v1/_v2`: one per current operation or branch (`molecular_sequence_result_contracts.py:1869-1870`,
  `primer_placement_result_contracts.py:69-70`, `protease_kinetics_tools.py:270,278`, `SUPPLIED_PLAN_VERSION`).
- `execution_status_v1/_v2`: both are schemas in `root/progress_observations.py:21,23`.
- Markerless Biopython pairwise results (`biopython_pairwise_grader.py:247-266`, `native_format is None`): the
  aligner writes the `biopython_pairwise_native_v2` marker (`sequence_ops.py:134`), but
  `reference_edit_outcomes.py:462` declares the format nullable for supplied alignments; not established that the
  markerless form is old-only. Undecided.
- `rcsb_entry_receipt(legacy)` / `rcsb_file_receipt(legacy)` parameter names, `legacy_checkpoint_requires_timer_only_wait`,
  and the other "live despite its name" rows of section 3.

Not done: a line-by-line read of the 96,000 lines for backward-facing code that uses no keyword and no version
string. The structural searches above are the substitute.

Verification of the second pass: import check over all 272 remaining top-level modules, `local_example` and
`method_loop` (`runs/claude_ptop_051`): no failure. Tests: `test_bvbrc_appservice_contracts` 35/0 -> 35/0;
`test_material_intake` 15/4 -> 15/0; `test_state` 25/0 -> 17/4 (version-1 manifests and explicit-quote commits);
`test_bvbrc_appservice_readers` 58/0 -> 45/13 (all `download_request_invalid`: snapshots without `max_bytes`);
`test_tool_knowledge` 3/3 -> 3/2 (the file now collects 5). The new failures are tests of the removed old forms and
are handed to ptests.

Totals after both passes: 101 files deleted, 53 edited. Handoff rows added in this pass: 12 (ptests 7, proot 3,
prootlib 2).
