# A110: behaviour present at HEAD (97308b94c) and absent from the working tree (18 November 2026)

Table: `a110.tsv` in this folder. Nothing in the repository was changed to make it; only these two files were written.

## Result

A110 lost its own science. What remains for A110 is source reading, public acquisition, HPC planning, job
execution and monitoring. The chemical accounting tools, flux-balance analysis and the reaction population of
its literature episodes exist nowhere in the working tree.

| verdict | files | lines |
|---|---|---|
| lost capability (no implementation anywhere now) | 49 | 12,181 |
| uncertain (old-protocol half of a lost route, or a rule that changed) | 17 files + 3 behaviours inside old homes | 4,532 |
| present (same path, placement target, or another axis's copy) | 186 | |
| intended removal | 1,398 | |
| total in scope | 1,650 | |

- 41 of the 49 lost files (10,155 lines) were deleted by the `rp110` reachability prune on 18 November, about
  15:08 to 15:18. No record names them. Its criterion was "no non-test A110 module imports it".
- 8 lost files (2,026 lines) were deleted earlier the same day with the old runner (`r2110`). They are named in
  `runs/claude_ablate/a110_needs.md` as "the old FBA tool route" and related lists.
- Every lost file can be read back with `git show HEAD:<path>`.
- The task text the A110 head still receives (`biochemical_feasibility_evidence/axis_task_context.py`) tells the
  model to call `chemistry.request_accounting_hpc`, `chemistry.prepare_reference_accounting`,
  `chemistry.reaction_evidence`, `chemistry.experimental_reaction_evidence`,
  `chemistry.source_identity_evidence`, `chemistry.request_flux_balance_hpc`, `literature.reaction.populate` and
  `literature.reaction.source.populate`. None of these operations exists now.

Paths below are relative to `gene_annotation_episode/episodic_workflow/`. `BFE` means
`root/a110/biochemical_feasibility_evidence`. `ES` means `episode_support`.

## Lost capabilities, by what they did

### G1. Chemical accounting and qualification tools (12 lost files, 2,982 lines; 1 uncertain)

What it did:

- `chemistry.request_accounting_hpc`: freeze a declared chemical panel and commission an HPC calculation of exact
  atom and charge residuals, explicit electron terms, pathway and carrier accounting and conditional Gibbs
  energies (`a110_chemical_accounting.calculate`, schema in `a110_chemical_contracts.py`).
- `chemistry.prepare_reference_accounting`: assemble that panel from received Rhea and ChEBI records
  (`a110_reference_accounting.py`).
- `chemistry.reaction_evidence` and `chemistry.experimental_reaction_evidence`: qualify a received result for one
  reaction and one protein, and supply the A110 contribution to the root (`a110_qualification.py`,
  `a110_experimental_qualification.py`).
- `chemistry.source_identity_evidence`: link an original assay role to an actual protein (`component_source_identity.py`).
- The registry that offered them, recorded each action and admitted the HPC results (`a110_tools.py`,
  `component_axis_native_tools.py`, `component_axis_native_contracts.py`, `component_axis_native_hpc.py`,
  `component_axis_native_worker.py`), and the projection of the results for reports (`a110_work_report.py`).

HEAD files: all under `root/a110/`. Deleted by `rp110`, except `a110_work_report.py` (`r2110`).

Baseline tests: `root/a110/tests/test_a110_reference_accounting.py` 8/8;
`root/a110/tests/test_a110_experimental_finding_binding.py` 8/8; `tests/test_component_source_identity.py` 20/20;
`tests/test_component_axis_source_receipts.py` 5/5; `tests/test_component_native_return_instructions.py` 6/6;
`tests/test_scientific_hpc_environment.py` 4/4; `root/tests/test_signed_evidence_root.py` 24 of 28.
(`test_a110_experimental_finding_binding.py` was deleted earlier as a scripted-fake test, per
`runs/claude_ablate/a110_results.md`; the others went with the old runner or with the code.)

Offered at HEAD: yes. `A110ToolRegistry` listed the tools in its catalog. `root/a110/tool_configuration.build_tools`
built that registry by default and `root/a110/independent_execution.py:315-318` gave it to every reconstructed
A110 episode. The head resolved its commissioned tool list against that catalog (`BFE/tool_selection.py`). The 41
run directories `runs/a110_accounting_autonomous_*` (5 to 8 November) are from this route; they were not
re-examined here.

What survives: the same machinery for A107 only. `ES/tools/sequence_and_context_sources/component_axis_native_tools.py`,
`ES/forms/sequence_and_context_sources/component_axis_native_contracts.py`,
`ES/jobs/sequence_and_context_sources/component_axis_native_hpc.py` and `component_axis_native_worker.py`, and
`ES/records/sequence_and_context_sources/component_source_identity.py` name `A107`, `partner.*` operations and
`host.a107.qualification`; the worker rejects any other axis. The A107 contribution helper
(`ES/grading/partner_presence_evidence/contribution.py`) differs from A110's by its axis label only.

To bring it back:

- Calculator and schema: `ES/calculations/biochemical_feasibility_evidence/` and `ES/forms/biochemical_feasibility_evidence/`.
- Panel preparation, source identity and the registry class: `ES/tools/biochemical_feasibility_evidence/`, next to `tools.py`.
- Qualification and contribution: `ES/grading/biochemical_feasibility_evidence/`.
- The A110 arm of the component-native request, HPC freeze, worker and result admission: per-axis copies under
  `ES/forms|jobs/sequence_and_context_sources/biochemical_feasibility_evidence/`, as the layout does for other
  unmerged per-axis copies.
- Binding: the head. `BFE/home.py` must build the chemistry registry instead of the base `ToolRegistry`, so the
  head's `tools` subset (`BFE/episode.py`) lists the operations.
- Missing links that are new work, not restoration:
  - The tools authenticate against `current_invocation`, which `rp110` pruned from A110's `tools.py`; `BFE/unit_source.py` must set it.
  - The accounting request publishes an HPC commission source, which the head must hand to `hpc_work_planning`.
  - Result admission needs a reader of a received HPC result. `hpc_result_receipts.read_received_result` read the
    deleted `runtime_actions` journal and must be rewritten over the records of `hpc_allocation_execution`.

### G2. Flux-balance analysis (22 lost files, 6,721 lines; 10 uncertain, 3,175 lines)

What it did:

- The tool `perform_flux_balance_analysis` with modes inspect, edit, solve, read_stored and calculate_saved
  (`flux_balance_tools.py`, `flux_balance_ordinary.py`, `native_flux_balance_tool_info.py`).
- Readers of retained Cobra/GLPK captures and of the five-column flux table (`flux_balance_readers.py`, 1,563 lines).
- The numerical authority for saved FBA evidence (`flux_balance_calculations.py`: residuals, bound checks,
  objective, partial terms), the sheet (`flux_balance_sheet.py`) and its selected views (`flux_balance_result_views.py`,
  `flux_balance_result_contracts.py`, `flux_balance_result_selection.py`, `flux_balance_return_views.py`).
- The finite result worker and its staging (`flux_balance_result_worker.py`, `flux_balance_worker_contracts.py`,
  `flux_balance_worker_staging.py`, `native_flux_balance_preparation.py`, `native_flux_balance_capture.py`,
  `flux_balance_native_capture_contracts.py`).
- Model inspection and editing without optimisation (`flux_balance_model_tools.py`, `flux_balance_model_worker.py`,
  `flux_balance_model_execution.py`).
- Remote FBA on HPC: `chemistry.request_flux_balance_hpc` (`a110_fba_hpc.py`, `a110_fba_native.py`).
- The results episode's FBA operations (`native_flux_balance_results.py`).

Deleted by: `rp110` (16 files, including the readers and calculations) and `r2110` (6 files).

Baseline tests on the A110 copies: `tests/test_flux_balance_core_679.py` 48/48,
`tests/test_flux_balance_evidence_parsing_689.py` 60/60, `tests/test_flux_balance_partial_terms_683.py` 9/9,
`tests/test_flux_balance_prior_sources_692.py` 41/41 (all import `a110.flux_balance_calculations`);
`root/a110/tests/test_bound_received_inputs.py` 3/3; `root/a110/tests/test_native_failure_form_boundaries.py` 26/26.
The `root/library` twins of the readers, model tools, capture and worker contracts were tested by
`tests/test_flux_balance_readers_680.py` 51/51, `test_flux_balance_parser_recovery_686.py` 28/28,
`test_flux_balance_parser_boundary_684.py` 4/4, `test_flux_balance_evidence_contracts_687.py` 95/95,
`test_flux_balance_model_tools.py` 29/29, `test_flux_balance_model_views.py` 70/70,
`test_flux_balance_native_capture_697.py` 41/41, `test_flux_balance_ordinary.py` 3/3,
`test_flux_balance_ordinary_returns.py` 10/10. Those twins and all these test files are gone too; the twins belong
to the shared comparison.

Offered at HEAD: yes. `ToolRegistry.configure_flux_balance_resources` (`root/a110/tools.py:91`), called by
`ExecutionServiceFactory` (`root/a110/execution_service_setup.py:138`), added the tool to the registry catalog. The
three result-acquisition homes returned `native_flux_balance_results.operation_catalog()` for an FBA handoff
(`BFE/execution_result_acquisition/work_operations.py`). The execution homes reported FBA facts
(`flux_balance_return_views` in their `to_parent.py`).

What survives, with nothing that uses it: the Cobra/GLPK driver and its contracts
(`ES/tools/metabolic_feasibility/native_flux_balance_driver.py`, `native_flux_balance_cobra_glpk.py`,
`native_flux_balance_bindings.py`, `native_flux_balance_observations.py`, `ES/forms/flux_balance_contracts.py`,
`ES/forms/native_flux_balance_contracts.py`, `ES/jobs/native_flux_balance_local.py`,
`ES/records/native_flux_balance_storage.py`). The job can still be described and run; its output can no longer be
read, calculated, viewed or returned.

To bring it back:

- Readers, calculations, sheet and views: `ES/readers/metabolic_feasibility/`, `ES/calculations/metabolic_feasibility/`,
  `ES/forms/metabolic_feasibility/`.
- Worker, staging, preparation and capture: `ES/jobs/metabolic_feasibility/`.
- The tool, model tools and remote request: `ES/tools/metabolic_feasibility/`, beside the surviving driver.
- Bindings: the head's registry (configured from the home operands, as `configure_flux_balance_resources` did);
  `BFE/execution_job_submission/submission_source.py` for an FBA launch; the three result-acquisition bindings
  (`BFE/execution_result_acquisition/acquisition_source.py`) for the FBA result operations.
- The 10 uncertain files are the episode-facing custody of this route (`flux_balance_custody.py`,
  `flux_balance_returns.py`, `flux_balance_result_receipts.py`, `flux_balance_request_binding.py`,
  `flux_balance_operands.py`, `flux_balance_execution_inputs.py`, `flux_balance_invocation.py`,
  `execution_input_versions.py`, `publication_reference_access.py`, `ordinary_fba_reader_custody.py`). They are
  written against the deleted `BindingContext` and return records. Their job (which FBA inputs an episode may use,
  where a selected action's state is kept, which published FBA files may be referenced) has to be rebuilt on the
  new forms and Store; the request schemas in `flux_balance_request_binding.py` are reusable as they are.

### G3. Reaction population in the literature episodes (13 lost files, 1,999 lines; 1 uncertain)

What it did: the operations `literature.reaction.populate` and `literature.reaction.source.populate`. A literature
episode read retained reaction measurements or selected source spans, calculated reported-ratio statistics,
comparisons between named reaction predictions and resource capacity and coverage
(`populate_reaction_constraints`), saved the sheet and its cells on the shared Store
(`LiteratureReactionRepository`), published source-supported meanings and native observations, and replayed a
saved operation by its key.

HEAD files: `library/literature_reaction_calculations.py`, `literature_reaction_inputs.py`,
`literature_reaction_native_inputs.py`, `literature_reaction_meanings.py`, `reaction_native_observations.py`,
`reaction_population.py`, `reaction_population_contracts.py`, `reaction_report_contracts.py`,
`reaction_source_selection.py`, `literature_component_binding.py`, `literature_reaction_types.py`,
`literature_reaction_storage.py`, `literature_reaction_native_storage.py`. All deleted by `rp110`.

Baseline tests (all in `root/a110/tests/`): `test_literature_reaction_calculations.py` 69/69,
`test_literature_reaction_inputs.py` 120/120, `test_literature_reaction_native_inputs_129.py` 27/27,
`test_literature_reaction_native_identity_129.py` 4/4, `test_literature_reaction_storage.py` 47/47,
`test_literature_reaction_meanings.py` 17/17; also `tests/test_reaction_source_witness_labels.py` 8/8 and
`tests/test_source_literal_display_labels.py` 18/18. The last recorded sweep before the prune still had them passing
(`runs/claude_r2110_t7`: 296 passed, 1 failed).

Offered at HEAD: yes, by all seven literature bindings. `BFE/published_evidence_assessment/source_operations.py`
added the two operations to the catalog and executed them; `numerical_report_facts.py` returned
`literature_reaction_cells`, the semantic cells and native observations in the report.

What survives: the instruction text (`ES/literature/readers/literature_reaction_instructions.py`,
`ES/literature/prompts/literature_reaction_prompt.py`), the two renderers
(`ES/literature/rendering/literature_reaction_meanings_render.py`, `literature_reaction_native_render.py`) and the
inputs the calculator depends on, as other axes' copies that differ by import lines only
(`literature_assay_inputs.py`, `literature_experimental_contracts.py`, `literature_partner_source_fields.py`,
`literature_partner_defined_units.py`, `literature_sheet_updates.py`, `literature_experiment_assessments.py`).

To bring it back:

- `ES/literature/calculations/biochemical_feasibility_evidence/`, `ES/literature/inputs/biochemical_feasibility_evidence/`,
  `ES/literature/forms/biochemical_feasibility_evidence/`, `ES/literature/storage/biochemical_feasibility_evidence/`.
- Binding: `BFE/published_evidence_assessment/literature_binding.py` (shared by the seven literature bindings) adds
  the two operations to its selectable set, and `BFE/unit_source.py` executes them on a repository built over the
  run's Store and `bound.run_id`.
- New work: `LiteratureReactionRepository.received_cells` used parent cell receipts that no longer exist
  (`a110_needs.md` records an explicit raise there). `library/literature_task_selection.py` (uncertain) chose the
  reaction instructions from the requested work; the binding needs an equivalent.

### G4. The A110 typed report (1 lost file, 382 lines)

`component_axis_reports.py`: the report schema with reaction component and meaning cells, admission of only the
numerical subset the receiver was given, received reports, current scoring sheets, revision marking and dependence
between experimental and native results. Deleted by `r2110`. Test: `tests/test_component_native_return_instructions.py` 6/6.

Offered at HEAD: yes, it was the head's report (`a110_investigation.report_schema`, `resolve_report`;
`BFE/from_parent.py`, `internal_summary.py`, `report_integrity.py`).

Now the head and every A110 binding return `credit` and `finding` (text) only (`BFE/runtime_contract.py`). To bring
it back: schemas in `ES/forms/biochemical_feasibility_evidence/`; the head and literature bindings declare the cell
fields as commissionable report fields. This depends on G3 (the cells) and G1 (qualification facts).

### G5. The head's planning and selection information (1 lost, 1 uncertain, 1 behaviour)

- `execution_planning.py` (lost, `rp110`): the information tool `process.execution` gave the execution recipe for a
  selected tool and resource, the local and Aurora planning context and timing cases. The head offered it
  (`BFE/tool_selection.py`, `scientific_operations.py`). It is gone in every axis. Home: `ES/jobs/`, beside
  `execution_timing.py` and `execution_inventory.py`; binding: the head.
- `scientific_tool_retrieval.py` (uncertain, `rp110`): `process.tools`, one recorded model call that picked a
  child's tools from the registry. Gone in every axis. The new contract lets the commissioner choose a child's
  tools as a subset field; whether that replaces the retrieval call is the owner's decision.
- The process library (`process.search`, `process.entry`, `process.sources`) and `process.revise`: A110's copy
  `biochemical_feasibility_evidence_library.py` was deleted by `rp110`. Other axes' copies survive
  (`ES/configuration/experimental_activity_evidence/process_options.py`, also A103 and A107). The A110 head offers
  none of it; `a110_needs.md` states "no thought-pattern/tool selection from the A110 library".

### G6. Results: selecting job files by path (3 uncertain files, 916 lines)

`local_file_capture_results.py` let a commissioner name files of a local job to capture as sources. The new result
acquisition retains the output snapshots the job receipt already lists (`BFE/execution_result_acquisition/acquisition_source.py`);
it has no selection by path. The old code is bound to the deleted receipts. Decide whether path selection is wanted.

### G7. HPC: waiting on a monitor schedule, and the launch handoff rule (uncertain)

- `hpc.monitor.wait` is offered by no axis. A103, A104 and A107 declare it `NOT_PORTED` in their
  `allocation_runtime.py`; A110's file omits it without that declaration, and `rp110` cut `MonitorCronController`
  out of A110's `hpc_monitoring.py` (18 of 133 lines remain). The controller survives in the A102, A104 and A107 copies.
- `library/hpc_handoff_report_contract.py`: an HPC launch child's return had to carry the original handoff fact.
  `a110_needs.md` item 5 says the check belongs in the HPC parent's return admission; that was not verified here.

### G8. Literature reader: assigned-source rule and tool list (uncertain)

At HEAD a literature reader with a page assignment could read, and populate from, only its assigned source and
sources derived from it (`literature_reading_outside_assigned_source`). `BFE/unit_source.py` has no such rule; it
passes tools the records the episode received or can see. The literature bindings' selectable operations also no
longer include `source.experimental.records`, the experimental database searches (`public.sabiork|brenda|bioassay|chembl|mavedb.*`)
and `execution.estimate`. These remain in the registry, so only the head can select them.

## Code that survives but no A110 episode can reach

- The FBA driver set listed under G2.
- `knowledge.search`, `knowledge.entry`, `knowledge.read` (`ES/tools/tool_knowledge.py`; A110's knowledge files are
  at `ES/knowledge/biochemical_feasibility_evidence/`). No binding of any axis offers them.
- Symbols `rp110` cut out of A110's kept files because no A110 module called them. They survive in other axes'
  copies: `communication.validate_form` and the schema compilers; `ExecutionExpectations`; `NativeEventProvider`;
  `NativeTimingInformation`; `practical_execution_state.verify_completion`;
  `practical_execution_operations.read_inventory`; the terminal handoff validators of `terminal_scientific_evidence.py`;
  `investigation_progress.received_axis_credit`. The rows of those files in `a110.tsv` list them.
- A110's literature rate reader files survive only as other axes' copies. The A110 route was already incomplete at
  HEAD (`literature_rate_domains.py` imported a `literature_rate_storage` that never existed in A110), so nothing is
  counted as lost there.

## Intended removals (1,398 files)

| category | files |
|---|---|
| old homes of the head subtree: task and protocol layer of the head and its 25 child homes | 851 |
| duplicate tree `library/received_execution_dependencies/` (A110 copies of other axes' and shared modules) | 346 |
| receiving context (`library/received_execution_information/`, `library/execution_initial_information/`, others) | 81 |
| task and protocol layers at the top level and in `library/` | 59 |
| per-axis runner, registries and runner support | 29 |
| receipts inheritance (result receipts and returns of other tool families) | 11 |
| journals | 6 |
| vendor folder | 5 |
| extra yield estimators | 4 |
| per-axis model providers | 3 |
| annotation_improvement envelopes | 2 |
| package marker of a removed folder | 1 |

For each old home the table names the binding that replaced it and what that binding does not carry. Operation
names were compared between HEAD and now for HPC planning, allocation, prediction, the monitor, local and HPC job
execution; all are kept except `hpc.monitor.wait`.

## Limits of this comparison

- The 851 old home files were classified by home, with operation names compared. Their decision rules were not
  compared line by line with the new bindings, apart from the points listed under G4, G5, G7 and G8.
- Excluded as the task states: tests, `annotation_improvement/`, `method_loop/`, and the five top-level trees that
  duplicate the head subtree (`hpc_work_planning/`, `published_evidence_assessment/`, `execution_job_submission/`,
  `execution_result_acquisition/`, `execution_progress_assessment/`; 842 files, 695 byte-identical with the
  head-subtree copy and 147 differing). The 147 differing files were not read.
- 150 basenames of `library/received_execution_dependencies/` and 11 receipt/return modules of other tool families
  (fluorescence, genomic overlap, protein structure, molecular sequence, LUMPY, MACS2, BV-BRC AppService custody)
  have no file of the same name anywhere now. A110 only held copies; whether the originals are lost belongs to the
  shared and other-axis comparisons.
- Deletion times come from run directories (`runs/rp110-scan3` to `scan7`, `runs/rp110-prune1` to `7`,
  `runs/claude_r2110_t7`) and `runs/claude_ablate/a110_needs.md`. Everything after 97308b94c is uncommitted.
- No test was run.
