# A106: capabilities at HEAD that exist nowhere in the working tree

Scope: the 1,524 files at `HEAD` under `gene_annotation_episode/episodic_workflow/root/a106/`, without `tests/`,
`annotation_improvement/` and `method_loop/`. Per-file rows: `a106.tsv`. Read from code on 2026-11-18; nothing was run.
Paths below are relative to `root/a106/` at `HEAD` unless they start with `episode_support/` or `root/`.

## Result

Seven groups of working non-runner code are gone from the whole tree (48 files: 26 whole, 22 in part). A further 16
runner files are marked uncertain: they are the old runner, but they held things an episode could do that nothing
does now. The remaining 1,460 files are present (524) or fall under an intended removal (936).

The A106 science is intact: the literature population tools, their calculators, graders, repositories, readers, the BV-BRC
AppService client, the launch, API-job, results and monitor bindings, and SRA file custody all have a current home.

| Verdict | Files | Lines |
|---|---|---|
| present: same path, placement target or identical blob | 390 | 98,591 |
| present: shared copy or other name | 124 | 27,616 |
| present: rewritten on the new layout (AppService host, custody, publication, progress provider) | 10 | 3,094 |
| intended removal: duplicate top-level trees | 366 | 36,594 |
| intended removal: A106 copy of shared `library/retained_input_authority` modules with no home now | 95 | 13,972 |
| intended removal: per-home task/protocol mixin stacks | 354 | 33,985 |
| intended removal: runner runtime, registries, receipts, journals, standalone support | 82 | 9,460 |
| intended removal: extra yield estimators, vendor, per-axis model providers | 39 | 7,074 |
| lost capability (whole file) | 26 | 2,761 |
| lost capability (part of file) | 22 | 3,979 |
| uncertain (runner-owned episode tools, actions and presentation) | 16 | 8,171 |

## Lost capabilities

### 1. Automatic A106 main-evidence judgment is never dispatched

- What it did: after a literature action, for each comparison with current intervention assessments of the proposed
  annotation, one model call judged the final A106 evidence selection (or returned unresolved reasons) and the result
  was saved as the main evidence sheet.
- HEAD files: `runtime.py:1782-1823` (`automatic_score_updates`: prepare, `provider.complete`, complete, add records to
  the outcome) and the hook `scoring/intervention_main_sheet.py` in each of the seven literature homes.
- Tests at HEAD: `tests/test_literature_a106_subscore.py` (12/12, repository half only),
  `tests/test_private_intervention_assessment.py` (56/56).
- Offered at HEAD: yes, by the runner for every literature home.
- Now: `prepare_judgments` and `complete_judgment` exist
  (`episode_support/literature/storage/literature_subscore_storage.py:34,164`) and only tests call them. No record
  mentions this loss.
- To bring back: call both from `root/a106/perturbation_evidence/published_evidence_assessment/literature_source.py`
  after each executed unit, with the `model_provider` collaborator and the recorder. `prepare_judgments` reads the
  head's commission from the table `runtime_episodes`, which nothing creates now; the binding has to pass the
  commission instead.

### 2. `literature.intervention_analysis.contract`

- What it did: built the exact TnSeq or RNASeq adapter selection and `requested_schema` for an AppService results
  selector, so a literature episode could commission launch and results children correctly.
- HEAD files: `library/standalone_intervention_execution.py` (83), `library/intervention_execution_lookup.py` (11), and a
  copy in each literature home's `source_operations.py:185-230`.
- Tests at HEAD: `tests/test_private_literature_analysis_children.py` (10/10),
  `tests/test_private_operational_presentation.py` (120/120).
- Offered at HEAD: yes, in the catalog of the seven literature homes when an AppService resource with a TnSeq or RNASeq
  adapter was configured.
- Now: absent. The prompt still tells the model to use it
  (`episode_support/literature/prompts/literature_perturbation_prompt.py:15`). The adapters and
  `selected_adapter` are present.
- To bring back: `episode_support/tools/service_calls/perturbation_evidence/`, offered by `LiteratureSource.catalog`
  when the binding opens its analysis children; it reads the services of the sibling results binding.

### 3. Monitor's own live AppService observation

- What it did: the monitor chose `query_tasks`, `stdout` or `stderr` in `progress.observe`; one authenticated request
  went to BV-BRC and its request and response were retained as a Source.
- HEAD files: `bvbrc_appservice_monitor.py` (414); the `native_operation` operand in
  `perturbation_evidence/execution_progress_assessment/progress_operations.py`; wiring in `execution_progress.py` and
  `api_service_execution.py:328-332`.
- Tests at HEAD: none for the native observation; `…/execution_progress_assessment/tests/test_progress_task.py` (9/9)
  covers `progress.observe` generally.
- Offered at HEAD: yes, to the A106 monitor.
- Now: the monitor reads only receipts that other episodes retained
  (`episode_support/jobs/service_calls/perturbation_evidence/job_provider.py`). `status` and `task_info` remain
  available to the API-job and results bindings, and `prepare_observation(native_operation=…)` still exists in
  `episode_support/acquisition/service_calls/perturbation_evidence/api_bvbrc_appservice.py:677`.
- To bring back: an observation adapter in `episode_support/jobs/service_calls/perturbation_evidence/`, called by
  `job_provider.observe`, with the operand added to the monitor's `tool_catalog` in `monitor_runtime.py`.

### 4. Shared information exchange (`shared.*` tools)

- What it did: five tools and their store: a child asks its parent for a missing operand, a parent answers with
  evidence it received, either side reads or pages the exchange; a read returns the saved grading of what it delivered.
- HEAD files: `shared_information.py` (332), `shared_information_results.py` (85).
- Tests at HEAD: only presentation of its context (`tests/test_private_literature_presentation_boundaries.py` 64/64,
  `tests/test_private_operational_presentation.py` 120/120).
- Offered at HEAD: yes, by the runner to roles `annotation`, `perturbation_evidence` and `improvement`
  (`runtime.py:1687-1711, 2271, 2560`); the same module existed in every axis and the shared root.
- To bring back: `episode_support/tools/`, offered by the head binding and the root annotation binding. Custody used the
  old runner's return records; it has to use the records each binding holds. `episode_runtime` runs a child to
  completion inside one parent unit, so a request can reach the parent only in the child's return unless the runner
  gains a channel.

### 5. Model-based tool retrieval for `process.tools`

- What it did: one recorded model call selected tool/resource variants from the real tool map for a described
  investigation.
- HEAD file: `scientific_tool_retrieval.py` (225). Tests at HEAD in A106: none.
- Offered at HEAD: only when the head configuration carried `tool_retrieval`; otherwise `process.tools` used the
  literal retrieval, which still exists (`episode_support/tools/tool_catalog.py:248`) and is called by nothing.
- To bring back: `episode_support/tools/` beside `tool_catalog.py`, offered by the head's `runtime_source.py`.

### 6. `process.execution` and the planning context

- What it did: execution instructions for one selected tool/resource pair, host capacity, cached queue and inventory
  observations, and timing history for given execution profiles.
- HEAD files: `execution_planning.py` (70), `perturbation_evidence/execution_planning.py` (36). Tests in A106: none.
- Offered at HEAD: yes, in the head's catalog.
- To bring back: `episode_support/jobs/` (the instruction files are already in `episode_support/instructions/execution/`),
  offered by the head binding.

### 7. Literature episode's decision presentation

- What it did: gave the literature model its examined source inputs, completed work with recorded credit, current
  scoring and findings views, covariance meanings, kinetic-model meanings, and the display contexts of the ratio-source,
  controlled-response, gel, native-rate, endpoint-signal, summary-precision, measurement-comparison and
  concentration-window sheets.
- HEAD files: `library/literature_source_inputs.py`, `literature_work_report.py`, `literature_work_results.py`,
  `literature_current_results.py`, `a106_work_report.py`, `literature_covariance_presentation.py`,
  `literature_kinetic_model_render.py`, `literature_prompt_binding.py`, `literature_experimental_prompt.py`,
  `literature_reference_parent_prompt.py`, `literature_experimental_task.py` (1,414 lines), and `internal_summary.py`
  and `decision_presentation.py` in each of the seven literature homes.
- Tests at HEAD: `tests/test_literature_perturbation_covariance_meanings.py` (12, 11 passed),
  `tests/test_private_literature_provider_routing.py` (28/28), `tests/test_private_literature_tracking_projection.py`
  (4/4), `tests/test_private_literature_presentation_boundaries.py` (64/64).
- Offered at HEAD: yes, in every literature decision.
- Now: `literature_source.py:395-425` presents the received-fact display, current scoring sheets and the last page of
  own outcomes. Twelve render modules the old providers called are present under
  `episode_support/literature/rendering/` with no importer.
- To bring back: readers over the recorder's outcomes in `episode_support/literature/rendering/perturbation_evidence/`,
  called from `LiteratureSource.decision_context`.

## Uncertain: runner files that held episode behaviour

The runner is an intended removal. These parts of it were things an episode could do, and no code does them now:

- `runtime.py`: the tools `episode.history`, `episode.credit` (paged detail), `episode.annotation_score`,
  `episode.monitoring_information`, `episode.estimate_wait`.
- `waiting.py`, `wait_estimation_inputs.py`, `local_return_history.py`, `inprocess_waiting.py`, `decision_waiting.py`:
  the wait action and its estimate. `episode_report_acquisition.py`: `redeliver_report`.
- `decision_history.py`, `decision_protocol_prompt.py`, `composition_information.py`,
  `episode_contract_information.py`: own-attempt and contract lookups inside one decision.
- `perturbation_evidence_prompt.py`, `execution_prompt.py`, `receiver_prompt.py`, `library/monitor_prompt.py`,
  `episode_work_report.py`: prompt renderers; the bindings now send instructions and a JSON context.

## Present but offered by no binding

Not lost by the definition above, but no A106 episode can reach them: `knowledge.search/entry/read`
(`episode_support/tools/tool_knowledge.py` and A106's four knowledge entries), `process.search/entry/sources` and the
literal `process.tools` (`episode_support/configuration/perturbation_evidence/process_options.py`,
`tools/tool_catalog.py`), the launch-instruction tools, and the 39 kept modules that
`runs/rp106-graph3/stdout.log` listed as having no live importer at that time (literature prompts and renders,
resource estimation, `api_selected_call`, `api_selected_effects`). The twelve literature render modules checked today
still have no importer; the others were not rechecked.

## For the other scopes

95 A106 copies of shared `library/retained_input_authority` modules have no file of the same name or functions anywhere
now (result receipts, returns and request bindings for ATAC differential, chromatin interaction, expression NMF,
fluorescence, flux balance, protein structure, genomic overlap, HOMER, LUMPY, MACS2, TF binding, restriction mapping;
BV-BRC annotation, assembly, variation, subspecies and influenza contracts; `api_enrichr`). No A106 episode could
produce these at HEAD (its launch family was API-only with TnSeq and RNASeq adapters), so they are counted here as
duplicate copies. Whether each survives for its owning axis has to come from the shared and owning-axis reports.

## How the deletions happened

| Pass | Record | Lost files it removed |
|---|---|---|
| First ablation | `runs/claude_ab106_tools/deleted_files.txt` | `runtime.py`, `shared_information.py` |
| Runner-apparatus deletion, second pass | `runs/claude_ablate/a106_needs.md`, "Deleted (step 1)" | `bvbrc_appservice_monitor.py`, the seven homes' `source_operations.py`, `scoring/`, `internal_summary.py`, `decision_presentation.py`, `library/standalone_intervention_execution.py`, `literature_experimental_prompt.py`, `literature_reference_parent_prompt.py` |
| rp106 reachability prune | `runs/rp106-graph2/stdout.log` against `rp106-graph3` | `scientific_tool_retrieval.py`, `execution_planning.py`, `library/intervention_execution_lookup.py`, `literature_source_inputs.py`, `literature_work_report.py`, `literature_current_results.py`, `a106_work_report.py`, `literature_prompt_binding.py`, `literature_experimental_task.py` |
| After rp106-graph3 | none found | `literature_covariance_presentation.py`, `literature_work_results.py` |
| No record found | | `shared_information_results.py`, `literature_kinetic_model_render.py`, `perturbation_evidence/execution_planning.py` |

## Limits of this report

- The ten files marked "rewritten" (AppService host, custody, publication, API execution, progress provider) were
  matched by function, not compared behaviour by behaviour.
- "Present" for a placed file means the file is there; only `tools.py`, `communication.py`, the gel storage and the
  AppService tool list were diffed against `HEAD`.
- Tests cited are A106's own; the same shared modules may have had tests under the root or other axes.
