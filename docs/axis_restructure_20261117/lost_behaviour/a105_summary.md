# A105 lost behaviour: HEAD (97308b94c) against the working tree, 18 November 2026

Scope: the 1,272 files at HEAD under `gene_annotation_episode/episodic_workflow/root/a105/`, leaving out
`tests/` (268), `annotation_improvement/` (17) and `method_loop/` (15). Table: `a105.tsv` (44 detailed rows, 12
count rows). Paths written `a105/...` below are under `gene_annotation_episode/episodic_workflow/root/`;
`episode_support/...` is under `gene_annotation_episode/episodic_workflow/`.

## Result

| verdict | files |
|---|---|
| present (same path, placement target, or the same functions in a surviving copy) | 315 |
| intended removal (runner and its support, scientific_process homes, duplicate trees, vendor, provider, yield) | 913 |
| lost capability | 27 |
| uncertain | 17 |

The literature sheet tools themselves are intact: all 35 `literature.*` population tools of HEAD are declared in
`episode_support/literature/storage/literature_populations.py` and offered by the ported literature source, and
their readers, calculations, repositories and graders are at their `placement.tsv` targets. The A105 Store has
the same 88 methods as the shared `gene_annotation_episode/state.py`.

What is lost is around them: what the literature model is told and shown, what a literature parent can ask a
child to return, eight tools of the A105 registry, and four tool families that were deleted outright.

## Lost or uncertain, grouped by what the code did

### 1. Literature decision presentation (8 files lost, 1 uncertain) - offered at HEAD

Each literature binding's `episode.py` set `decision_prompt_renderer = render_literature_experimental_prompt`.
The ported `LiteratureSource` sends a JSON context and the instructions
`INSTRUCTIONS + role instruction + REASONING_COMMIT_REQUIREMENT`.

| HEAD file (a105/library/) | lines | what is gone |
|---|---|---|
| `literature_experimental_prompt.py` | 1,199 | the composer: task sections, received child returns rendered per sheet family, own source results, completed work, current scoring results |
| `literature_experimental_task.py` | 19 | `EXPERIMENTAL_TASK`, the source-experiment interpretation instruction. Its text exists nowhere now |
| `literature_task_selection.py` | 191 | which per-family task sections a decision shows; `A105_ASSAY_SELECTION_TASK` |
| `literature_current_results.py` | 129 | views of current scoring results, findings and interpretations |
| `literature_work_report.py` | 278 | completed-work report with scoring sheets and child-return receipts |
| `literature_source_inputs.py` | 66 | the episode's own source inputs and measurement selectors |
| `literature_reference_parent_prompt.py` | 121 | prompt for a parent receiving reference evidence |
| `literature_kinetic_model_render.py` | 41 | display of received kinetic-model rows; the only family renderer not kept |

The per-family instruction texts (`ASSAY_TASK`, `GEL_TASK`, `BINDING_TASK`, `CONTROLLED_RESPONSE_TASK`, ...) and
the other family renderers are still under `episode_support/literature/prompts` and `.../rendering`, but no
non-test code presents them to a model.
Uncertain: `a105/experimental_activity_evidence_prompt.py` (600 lines, the head's prompt); the ported head builds
its own JSON context and I did not compare the sections line by line.

Tests at the baseline: 20 A105 test files imported the composer, among them `test_literature_assay_prompt.py`
1/1, `test_private_literature_renderer_filter.py` 4/4, `test_literature_numerical_declarations_203.py` 234/234
(all retired) and `test_literature_native_rate_censored_bounds.py` 41/41 (now 37/37).
Deleted by: the r2105 repair pass (`runs/claude_r2105/broken3.txt`..`broken5.txt` list these files as broken
importers of the deleted runner; `pruned_tests.tsv` row 111 names the deleted renderer).

To bring back: put the eight files in `episode_support/literature/prompts/experimental_activity_evidence/`
(texts, task selection) and `episode_support/literature/rendering/experimental_activity_evidence/` (composer,
current results, work report, kinetic-model renderer). The binding that offers them is
`a105/experimental_activity_evidence/published_evidence_assessment/literature_binding.py::instructions()` (task
texts) and `literature_source.py::decision_context()` (rendered returns and completed work). The composer read
the old runner state, so it has to be rebuilt over the source's recorded outcomes and the population
repositories; the texts and renderers can return unchanged.

### 2. Requested sheet cells between literature episodes (3 files lost, 2 uncertain) - offered at HEAD

At HEAD a literature parent could ask a child for cells of 23 sheet families (`requested_rate_components`,
`requested_gel_components`, `requested_controlled_response_components`, `requested_ratio_components`,
`requested_binding_components`, `requested_kinetic_components`, `requested_optical_components`, ...), the child
returned exactly that subset, and the parent admitted it into the family repository. The port keeps three:
quantity, assay grading and A105 aggregation (`literature_binding.py::CELL_FIELDS`,
`literature_source.py::_CELL_REPOSITORIES`). This is recorded as a follow-up in
`runs/claude_ablate/a105_contract_requests.md`.

HEAD files (examination home; the same code stood in all seven literature homes and the standalone tree):
`.../source_evidence_examination/from_parent.py` (180), `to_parent.py` (316),
`from_child_table_evidence_extraction.py` (124, and two siblings).
Uncertain: `a105/library/literature_numerical_contracts.py` (the registered sources are kept; `freeze_contracts`,
`validate_frozen_contracts`, `expand_numerical_form`, `uses_fact_references` are gone) and
`a105/episode_report_acquisition.py` (the `redeliver_report` action: taking a wider saved subset from a completed
child).

Tests at the baseline: `test_literature_a105_worksheet.py` 36/36 (now 17/17), `test_literature_gel_storage.py`
16/16 (now 8/8), `test_literature_controlled_response_storage_v3.py` 13/13 (now 10/10),
`test_literature_rate_meaning_delivery_143.py` 9/9 (now 2/2), `test_literature_figure_storage.py` 77/77 (now
59/59), `test_literature_numerical_declarations_203.py` 234/234 (retired).

To bring back: no new folder. The repositories under `episode_support/literature/storage/experimental_activity_evidence/`
still have `project_cells`, `fact_cells` and `receive_cells`, and `literature_populations.py` already routes every
family's cells. Extend `CELL_FIELDS` and `_CELL_REPOSITORIES` to the other families, add their `requested_*`
fields to `LiteratureBinding.assignment_schema()`, and return them in `LiteratureSource._requested_cells`.

### 3. Tools the A105 registry no longer offers (12 files uncertain) - offered at HEAD

`a105/tools.py` was deleted by the runner ablation and rebuilt as
`episode_support/tools/experimental_activity_evidence/tools.py` (`A105ToolRegistry`), which "offers only the
tools whose implementation exists in this axis folder". HEAD offered 27 named tools plus the experiment-database
operations; now 19. The code of the eight dropped tools survives, but only as other axes' copies or shared
modules:

| tool at HEAD | A105 file at HEAD | surviving code | offered at HEAD to |
|---|---|---|---|
| `image.view` | `image_evidence.py` (110) | sibling-axis copies, e.g. `episode_support/findings/biochemical_feasibility_evidence/` | every literature role |
| `source.sequence.scan` | `source_sequences.py` (183) | sibling-axis copies under `episode_support/readers/sequence_operations/` | every literature role |
| `source.xlsx.sheets`, `source.xlsx.rows` | `spreadsheet_tools.py` (kept), `spreadsheet_worker.py` (25) | reader kept for A105; worker only in sibling-axis folders | every literature role |
| `execution.estimate` | `native_timing_information.py` (164) | sibling-axis copies under `episode_support/jobs/local_execution/` | every literature role |
| `public.ncbi.entrez` | `ncbi_entrez_tools.py` (178), `ncbi_entrez_acquisition.py` (635) | sibling-axis copies | the head's registry |
| `public.uniprot.search`, `public.uniprot.record` | `api_uniprot.py`, `uniprot_native*.py`, `uniprot_publication.py`, `uniprot_service_support.py` | shared and package-root copies (three identical) | the head's registry |

The `literature_table` assignment still carries `sheet_key`, but no spreadsheet tool is offered.
Tests at the baseline: none exercised these tools by name except image views
(`test_literature_ratio_source_storage.py` 52/52, `test_literature_ratio_source_runtime_receipt.py` 23/23, both
retired) and `execution.estimate` (`test_private_literature_messages.py` 36/36, retired).

To bring back: A105 copies of `image_evidence.py` (`episode_support/findings/experimental_activity_evidence/`),
`source_sequences.py` (`episode_support/readers/sequence_operations/experimental_activity_evidence/`),
`spreadsheet_worker.py` (`episode_support/jobs/documents/experimental_activity_evidence/`),
`native_timing_information.py` (`episode_support/jobs/local_execution/experimental_activity_evidence/`) and the
Entrez pair (`episode_support/tools|acquisition/sequence_and_context_sources/experimental_activity_evidence/`);
the HEAD files differ from the surviving sibling copies by import lines (and, for `source_sequences.py`, line formatting) only. Then add the definitions and dispatch to
`A105ToolRegistry`, and the five literature tools to `ACCESS_TOOLS` in `literature_binding.py`. The head offers
whatever its registry lists (`selectable_tools`).

### 4. ITC binding thermodynamics tool (7 files lost) - not offered at HEAD

`a105/itc_binding_tool_values.py` (293), `itc_binding_worker.py` (32), `itc_binding_publication.py` (65),
`itc_binding_presentation.py` (282), `molecular_measurement_tools.py` (702), `molecular_result_facts.py` (272),
`assay_artifact_custody.py` (14). They held the tool `analyze_itc_binding_thermodynamics`: request contract,
worker, publication, result views and typed parameter facts. Only the calculator survives
(`gene_annotation_episode/itc_binding_contracts.py`, `itc_binding_fit.py`, `itc_binding_measurements.py`, identical
to the A105 copies).

Nothing offered it to an A105 episode at HEAD: it was not in `ToolRegistry.catalog` and
`itc_binding_tool_values.py` says "Retained callable behavior only; not registered as an episode tool". A105 held
the only axis-private copy; the package-root and `root/library` copies are gone too. No A105 test exercised it.
Deleted by the runner ablation; no per-file record.

To bring back: a tool folder such as `episode_support/tools/experimental_activity_evidence/` (tool values,
publication, presentation), `episode_support/jobs/local_execution/experimental_activity_evidence/` (worker) and
`episode_support/findings/experimental_activity_evidence/` (result facts), with the calculator moved beside them.
The A105 head would offer it through `A105ToolRegistry`. Its custody code read the old runner's return records
and needs rebuilding on the shared Store.

### 5. Protease kinetics analysis tool (5 files lost) - not offered at HEAD

`a105/protease_kinetics_tools.py` (818), `protease_kinetics_result_contracts.py` (207),
`assay_action_context.py` (49), `assay_native_controls.py` (134), `molecular_sequence_result_worker.py` (181):
the tool `analyze_protease_kinetics` (contract, input admission, worker dispatch, output capture, publication
reader) and its result contracts. The calculator survives (`gene_annotation_episode/protease_kinetics_measurements.py`,
identical), as do `molecular_sequence_driver.py` and `molecular_sequence_native.py`.

Nothing offered it to an A105 episode at HEAD; `a105/communication.py` only validated report facts of that
source. No A105 test exercised it (the package-root copy's `tests/test_protease_kinetics_result_contracts.py`,
88/88, is deleted too). Same restoration path as the ITC tool.

### 6. Shared-parent information exchange (2 files lost) - offered at HEAD

`a105/shared_information.py` (333) and `shared_information_results.py` (78): a repository and five tools
(`shared.request_information`, `shared.publish_information`, `shared.resolve_information_need`,
`shared.read_information`, `shared.list_information`) for telling the parent about a missing operand, offering
received evidence and answering a need. `a105/runtime.py` offered them to the roles `annotation`,
`experimental_activity_evidence` and `improvement`. It was a copy of a shared root module that is also gone. No
A105 test named it.

To bring back: `episode_support/records/` (the repository) and `episode_support/tools/` (the five tools), shared
rather than per axis; the head source `runtime_source.py` would add them to its action schema. It authenticated
participants through the old runner's episode records and needs rebuilding on the new runner's commissions.

### 7. Execution planning tool (2 files lost) - offered at HEAD

`a105/experimental_activity_evidence/execution_planning.py` (31) and `a105/execution_planning.py` (44): the head
tool `process.execution` (execution recipe for a selected tool and resource, host capacity, timing history from
execution memory). The head's `ScientificOperations.catalog` added it. No A105 test named it. The execution
memory it read is kept (`episode_support/records/experimental_activity_evidence/execution_memory.py`).

To bring back: `episode_support/tools/experimental_activity_evidence/` with the host observation in
`episode_support/jobs/`; offered by the head source.

### 8. Tool retrieval for a child (2 files uncertain) - offered at HEAD

`a105/scientific_tool_retrieval.py` (225) and `a105/library/scientific_catalog_operations.py` (27): `process.tools`,
a model-backed retrieval of tool information for a child investigation. The port replaces it by design: the head
chooses a child's thought pattern and tools from an enum (contract C6). `episode_support/tools/tool_catalog.py`
still declares `process.tools`, and nothing executes it.

## Not lost, worth knowing

- `a105/library/retained_input_authority/` (216 files) was A105's copy of result contracts and custody readers for
  tools A105 did not offer; every file had a same-name file outside A105 at HEAD. Counted as an intended
  duplicate-tree removal. 88 of those basenames exist nowhere in the working tree now (flux balance returns,
  ATAC and chromatin result receipts, expression NMF, fluorescence, HOMER, lumpy, MACS2 request binding, protein
  structure returns, TF binding, restriction mapping returns). That belongs to the shared-root and owner-axis
  scopes.
- Runner-provided operations that went with the runner: `episode.history`, `episode.credit`,
  `episode.annotation_score`, `episode.monitoring_information`, `episode.estimate_wait`,
  `episode.operation_contract`, `episode.return_contract`, `process.revise`.
- The one lost check already reported in `per_file_comparison/a105_summary.md`
  (`test_required_grading_keeps_typed_finding_in_same_action`) concerns code that is still present.

## Method and limits

Each HEAD file was looked up at its own path, at its `placement.tsv` target, by basename in the live tree
(`gene_annotation_episode/`, `episode_runtime/`, `method_loop/`, `yield_control/`), and by its top-level function
and class names. The 44 detailed rows were read at HEAD and checked by name, tool name and distinctive text in
the live tree. The "present" and "intended removal" counts rest on the path, basename and name matching; I did
not read each of those 1,228 files. The per-home runner files (394 files in the two literature trees and the
head) were judged as a group against the ported sources, not file by file, so a smaller behaviour inside them
that the port dropped could be missed. No per-file record of the A105 modules deleted by the runner ablation
exists; the deletion pass is inferred from `runs/claude_ablate/a105_needs.md`, `a105_contract_requests.md` and the
`runs/claude_r2105/broken*.txt` lists.
