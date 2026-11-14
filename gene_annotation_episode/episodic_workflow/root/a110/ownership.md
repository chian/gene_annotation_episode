# A110 ownership

## 2026-11-11 private dependency follow-up

| Original module or symbols | Private destination | Current role and caller | Change |
| --- | --- | --- | --- |
| Mixed component catalog, operation-to-axis dispatch and axis admission gates | `component_axis_native_tools.py` | A110 accounting and flux-balance HPC requests, received qualifications and attribution | Bound directly to A110 operations; removed axis routing and execution-owner result metadata |
| Dynamic component contract module selector | `component_axis_native_contracts.py` | A110 native source and selection schemas; private tools and HPC code | Direct local A110 chemical-contract import |
| Root component source-access injection and source reader selection | `component_axis_source_access.py`, `a110_tools.py`, `literature_episode.py`, `scientific_process_episode.py` | Private source-read receipt selection and parent feedback about rejected reads | Local import and local decision-context hooks; scientific parent receives descendant access notices |

This follow-up did not execute tests or import/parse validation. The practical
operations and records were subsequently narrowed to A110 flux-balance and
generic execution, as recorded below. Combined root annotation source-access
wiring remains a later integration task.

The A110 package owns chemical accounting, flux balance and reference reaction evidence. Public callers are the root scientific-process binder, `AllEvidenceToolRegistry`, the literature binder/selector, the A110 subtree factory, and A110-local tests. Root coordination composes these interfaces; reaction calculations, native workers and report projections live here.

| Original module or symbols | Destination | Role and callers | Change |
| --- | --- | --- | --- |
| `a110_investigation`, `a110_tools`, `a110_work_report` | Same basenames here | A110 subtree, tool catalog and work-report shaping; root binder and registry | Moved |
| `a110_qualification`, `a110_experimental_qualification`, `a110_reference_accounting` | Same basenames here | Chemical and experimental qualifications and reference accounting; A110 tools/reports | Moved |
| `a110_chemical_contracts`, `a110_chemical_accounting`, `a110_fba_hpc`, `a110_fba_native` | Same basenames here | Source contracts, native chemical/FBA calculation, commission and receipt admission; A110 tools/worker | Moved and updated to stage axis-local source paths |
| `component_axis_workflow` task instructions, `task_context`, subtree and factory | `component_axis_workflow.py` | A110-only task and service setup; `a110_investigation` and root binder | Split from mixed A107/A110 module |
| `component_axis_reports` schemas, validation, receipt and scoring projections | `component_axis_reports.py` | A110 report contract and received facts; A110 subtree and root binder | Split |
| `component_axis_native_contracts`, `component_axis_native_worker`, `component_axis_native_hpc`, `component_axis_native_tools` | Same basenames here | A110-only native contract, runtime snapshot, publication and tool mixin; A110 tools and root registry | Split; snapshots retain importable package paths |
| `component_axis_cell_receipts.inherited_cells` | `component_axis_cell_receipts.py` | Authenticated A110 inherited population cells; reaction storage | Copied from shared helper |
| Component task projection and scientific guidance formerly inside `scientific_process_episodes` | `a110_scientific_process_binding.py` | `original_task_projector`, `scientific_guidance`; root scientific-process binder | Extracted |
| Original `a102_structural_catalog.prepare_catalog` and its catalog constants | `a102_structural_catalog.py`, `a102_structural_evidence.py` | Standalone historical catalog preparation during A110 service factory setup | Copied, locally imported |
| `literature_reaction_*` source, input, prompt, calculation, storage, rendering and type modules | Same basenames here | Experimental reaction reader, source selection, native operands and population; literature binder and A110 reports | Moved |
| Source reader helpers (`literature_experimental_contracts`, `literature_rate_calculations`, `literature_rate_native_inputs`, `literature_rate_reader`, `literature_partner_defined_units`) | Same basenames here | Reaction literal parsing, validation and rate/partner unit conversion; reaction modules | Copied for A110-local use; reaction storage now owns its own receipt custody |
| `literature_assay_inputs` | `library/literature_assay_inputs.py` | Reused source witness and literal reader for reaction and native-rate operations | Copied, then moved to axis library |
| `literature_partner_source_fields` | `library/literature_partner_source_fields.py` | Reused source-number parsing for reaction and native-rate operations; axis-local input readers | Copied, then moved to axis library |
| `literature_experiment_assessments` | Same basename here | Reaction experiment assessment contract; reaction storage | Copied from shared assessment module |
| Reaction/partner entries formerly inside `literature_episodes` and `literature_task_selection` | `literature_component_binding.py` | A110 catalog entries, task family, scope, aliases, routes, fact and assignment schemas; private `literature_episode.LiteratureEpisode` and `literature_task_selection` | Extracted |
| `literature_episodes.py` A110 binding, reaction catalog, assignment and fact routes | `literature_episode.py` | A110 literature episode and `component_axis_workflow` | Copied and narrowed; dormant foreign-axis methods remain pending removal, with no validation in this pass |
| Reaction source task text and family selection formerly inside `component_axis_literature_prompt` | `literature_component_prompt.py` | A110 reaction/source reading instructions and selector; root prompt composer | Extracted |
| Source and reaction TASK/STEERING rendering | `literature_experimental_prompt.py`, `literature_reference_parent_prompt.py` | A110-only prompt text and state presentation; provider binds these directly | Split from root prompt |
| Sheet dependency publication and receipt admission | `literature_sheet_updates.py` | A110 reaction population and rate storage use | Copied from root and scoped to A110 |
| Admitted scientific-parent source provenance | `literature_source_origin.py` | A110 literature binder reads its own parent-axis origin | Split from mixed root source-origin helper |
| Reaction operation set formerly inside `component_axis_inspection` | `literature_component_binding.inspection_operations` | Identify A110 own saved population outcomes; root inspection index | Extracted |
| A110 tests and reusable inputs | `tests/` and `tests/fixtures/` | Axis-local checks and retained inputs; pytest | Moved/copied from top-level tests and selected retained source records |

The root `episodic_workflow/root/component_axis_execution_context.py` joins request/commission control metadata across axes; `episodic_workflow/root/component_axis_source_access.py` reports access notices across owned branches. Both remain root coordination. Their facts do not change scientific ownership.

## HPC episode ownership

| Original module or symbol | Private destination | Change | Role and callers |
| --- | --- | --- | --- |
| Top-level `hpc_episodes.py:HPCEpisodes` | `hpc_episode.py:HPCEpisode` | Copied and singularized | This axis's HPC parent binding; its workflow role declaration and the axis-specific execution factory descriptor. |
| Top-level `hpc_campaign.py`, `hpc_ledger.py`, `hpc_prediction.py`, `hpc_queue.py`, `hpc_allocation.py`, `hpc_monitoring.py`, `hpc_history.py`, `hpc_resource_prediction.py`, `hpc_commission_sources.py` | Same basenames in this directory | Copied | This axis's HPC planning, ledger, prediction, queue, monitoring, and saved commission behavior. |
| Top-level `execution_memory.py`, `execution_guidance.py`, `terminal_execution.py`, `terminal_execution_episodes.py` | Same basenames except `terminal_execution_episode.py` | Copied | Local execution memory and terminal action dependencies used by this axis's HPC binding. |

## Scientific process binding copy (2026-11-11)

| Original symbol | Destination | Axis | Role and caller | Change |
| --- | --- | --- | --- | --- |
| `scientific_process_episodes.py::ScientificProcessEpisodes` | `scientific_process_episode.py::ScientificProcessEpisode` | A110 | Scientific process binding; `component_axis_workflow.ComponentAxisServiceFactory` calls private `scientific_process_setup.prepare_scientific_binding`; saved reopening remains unresolved | Copied into a singular private binding with axis-constrained assignment, local credit, guidance, fact, report and decision routes; direct behavioral dependencies are private. |
| `component_axis_execution_context.py::prepared_assignments` | `component_axis_execution_context.py::prepared_assignments` | A110 | Private received native request and commission presentation; `scientific_process_episode.py` | Copied and restricted to this axis's request reader. |

## Execution episode copy (2026-11-11)

| Original module or symbol | Private destination | Change | Role and caller |
| --- | --- | --- | --- |
| Former mixed execution binding | execution_episode.py:ExecutionEpisode | Narrowed to A110 reaction and flux-balance work | A110 local/PBS launch and retained FBA result handling; component_axis_workflow.py and execution service descriptor |
| Top-level flux_balance*.py and native_flux_balance*.py | Same basenames in A110 | Copied | A110 FBA request, calculation, capture, result, and return dependencies used by the private execution binding |
| Top-level execution_contracts.py, launch_instructions.py, practical_execution_*.py, practical_receipt_information.py, resource_records.py, local_file_capture_results.py | Same basenames in A110 | Copied | A110 execution assignment, transport, receipt, and source result helpers |
| A101 execution binding symbols previously imported by the mixed execution class | a110_execution_bindings.py | Split | A110 local binding surface without A101 native binding imports |

The A110 execution binding no longer imports A101 behavior. Its A101 BLAST/HMMER selectors, catalogs, assignment validators, source facts, reference resolution, receipt admission, and completion branches were removed. Generic native readers for other scientific work remain in the copied class and still need A110 applicability review. The A110 execution split is incomplete and has not been validated.

## Private terminal execution binding

| Original module or symbol | Destination | Applicable axis | Episode role and caller | Change |
| --- | --- | --- | --- | --- |
| terminal_execution_episodes.py, TerminalExecutionEpisodes | terminal_execution_episode.py, TerminalExecutionEpisode | A110 | Local or HPC launch command execution; this axis's execution episode and practical service factory | Copied and made singular |
| terminal_scientific_evidence.py | terminal_scientific_evidence.py | A110 | Source custody for this axis's applicable native command profiles | Copied and narrowed |
| practical_yield.py | practical_yield.py | A110 | Private command-result progress estimate | Copied |

## 2026-11-11 monitor binding split

| Original module and symbol | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| episode_monitoring.py: MonitorEpisodes | monitor_episode.py: MonitorEpisode | This axis's monitor binding, commissioned by its execution service | Copied and made axis-private; generic progress infrastructure remains in episode_monitoring.py |

## 2026-11-11 private workflow construction

The private component_axis_workflow.py no longer runs A102/A111 catalog migration or accepts an axis selector for task_context/create_workflow. Its local investigation and scientific binding callers use the private signatures. Execution guidance names this axis's operations. A110 service construction passes its concrete execution, monitor, and HPC classes. The source catalog is used directly; combined catalog repair is deferred. No tests or import validation were run.

The private literature constructor and descriptor no longer expose the unused rate_population mode flag. Old saved configuration containing that flag requires later migration.

## 2026-11-11 practical execution branch split

| Original module or symbols | Private destination | Current role and caller | Change |
| --- | --- | --- | --- |
| Mixed native practical handlers and requested-job contracts | `practical_execution_operations.py`, `practical_execution_records.py` | A110 private execution binding and terminal execution; generic commands and flux-balance jobs | Removed foreign native branches, bindings, selectors, output roles and validators; retained FBA input custody, original attempt identity, retry handling, output observations and progress facts |
| Mixed native file-result selectors | `local_file_capture_results.py` | A110 execution generic file-result capture | Removed MACS2/LUMPY selectors and native-plan branches; retained exact-file capture, receipt admission and source publication; renamed the binding reference from owner to execution_binding |
| Root durable native lifecycle | `native_lifecycle.py` | Private practical execution job handles and systemd lifecycle | Copied locally; private execution-memory import retained and root process infrastructure imports made explicit |
| Root inventory catalog implementation | `execution_inventory.py` | Private practical inventory refresh | Copied locally to satisfy the private inventory import |

This pass changed source only: no tests, imports, parsing or static validation
were run. These practical modules no longer select foreign native operations.
Subsequent private-copy passes supplied the receipt/file-custody/material/communication/binding, local-job and process-resource dependencies described below. File capture uses private immutable-control helpers. Execution validation remains deferred.

The former root component_axis_inspection.py is copied privately here with only the local inspection-operation catalog. Its retained read/search/result view is restored in this axis’s source-access decision context. The mixed root module is removed.

The private component_axis_execution_context.py now reads local HPC commissions and no longer checks an axis-owner discriminator. Its request link projection remains private; the unused mixed root fallback reader was removed.

## 2026-11-11 private source identity and correspondence

| Original module or symbols | Destination | Change and caller |
| --- | --- | --- |
| component_source_identity.py | component_source_identity.py | Copied and narrowed to A110's qualification reader and single tool; local tools/qualification callers updated |
| component_sequence_attribution.py | component_sequence_attribution.py | Copied for local source-identity and qualification uses |
| a103_attachments._sequence, _component_link, component_link | component_sequence_link.py | Copied only applicable received-component correspondence mechanics |
| sequence_attribution.py | sequence_attribution.py | Copied for local residue correspondence |
| a101_scoring.py | native_correspondence_scoring.py | Private copy of the existing native-grade interpretation; existing grade version retained |

Root source readers and runtime record infrastructure remain dependencies. No tests or import validation were run.

| `tools.ToolRegistry._sequence`, `library_targets.is_library` | `a110/received_sequence_reader.py` | A110 received correspondence sequences | Copied privately; component sequence attribution calls directly. Packed-byte custody now imports private `materials_packing`; no validation run. |
| `sequence_views.py` | `a110/sequence_views.py` | A110 private sequence orientation | Copied; called by private received sequence reader. |

| `materials_packing.packed/component_info/component_chunks/component_window`, `materials._verified_artifact_path` | `a110/received_sequence_reader.py` | A110 received sequence bytes | Copied applicable readers and digest verification directly. Removed root packing import and mixed provider-policy dispatch; existing correspondence callers retain their received-record checks. No execution validation. |

### Private native correspondence dependencies (2026-11-11)

| Original implementation | Private destination | Applicable role and callers | Change |
|---|---|---|---|
| `alignment_correspondence.py` | `a110/alignment_correspondence.py` | A110 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `biopython_pairwise_grader.py` | `a110/biopython_pairwise_grader.py` | A110 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `tool_grading_artifacts.py` | `a110/tool_grading_artifacts.py` | A110 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `blast_pairwise_grader.py` | `a110/blast_pairwise_grader.py` | A110 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `sequence_attribution.py` | `a110/sequence_attribution.py` | A110 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |
| `a101/a101_scoring.py` | `a110/native_correspondence_scoring.py` | A110 native sequence map/grading custody; direct local callers | Copied applicable implementation; no cross-axis call. |

Updated direct imports in `a110_experimental_qualification.py`, `a110_qualification.py`, `component_axis_native_hpc.py`, `sequence_attribution.py`. BLAST program units are private constants when only the grader needs them. Existing native sheet formats and scoring equations are preserved. No Python, tests or static validation run.

Native correspondence scoring was narrowed to `hmmer_comparisons`, `blast_comparisons`, `route_native_grading`, their private exception/require helper and `SCALES`. Copied A101 sheet aggregation, coverage and credit-facing compilation were removed; only applicable mapping readers remain.

| `source_locations._immutable/received_source` | `a110/source_locations.py` | A110 source identity declaration byte custody | Copied applicable immutable/source-receipt/scope checks; mixed provider access dispatch removed from this private binding. |
| `source_sequences.py`, `literature_sequence_discovery.protein_operand` | `a110/source_sequences.py` | A110 source identity literal sequence scan | Copied scanner and its protein operand helper; component_source_identity now imports both reader modules locally. Scientific matching, byte witnesses and unresolved sequence cases preserved. |

A110 tools and native result readers no longer select scientific access by assignment axis. `current_scoring_sheets` projects this private binding directly without configured-axis sets or axis filtering. The native request freezer binds its existing A110 HPC metadata internally. Scientific receipt, scope, input identity and grading checks remain. Root ToolRegistry/service inheritance and older report-schema axis parameters still require separate splitting; no validation run.

### Private A110 execution setup (2026-11-11)

| Original module/symbol | Private destination | Role and caller | Change |
|---|---|---|---|
| `execution_service_setup.ExecutionServiceFactory`, `_freeze`, `_ProgressReader` | `a110/execution_service_setup.py` | A110ServiceFactory and component workflow execution/monitor/HPC setup | Split; only flux-balance environment configuration remains, with concrete private episode classes instead of class-selection arguments. |
| `episode_progress_credit.py` | `a110/episode_progress_credit.py` | Private execution setup received monitoring information | Copied original information-credit projection. |
| `progress_records.py`, homology job status schema literals | `a110/progress_records.py` | Private monitor/resource progress records | Copied typed progress mechanics and literal historical status shape without importing A101 jobs. |

Removed A110ServiceFactory axis-membership and shared ToolRegistry inheritance enforcement. Direct private imports establish bindings. Generic configuration containers, communication/domain types, source registry and service dependencies now have private implementations. No tests, Python or parse/import validation run.

| `molecular_measurement_tools.authenticate_itc_invocation`, unfinished-action exception | `a110/flux_balance_invocation.py` | Original FBA invocation and unfinished native publication | Copied applicable action authentication as `authenticate_flux_balance_invocation` and private `FluxBalanceOperationUnpublished`; FBA modules no longer import unrelated assay tools for the exception. |
| `genomic_overlap_result_receipts` immutable control helpers | `a110/file_capture_receipt_control.py` | FBA prepared/input controls | Copied applicable immutable file primitives, removing the genomic-overlap dependency. |
| `native_file_capture.py`, `materials.artifact_file/_verified_artifact_path` | `a110/native_file_capture.py`, `a110/native_artifacts.py` | FBA native file receipts and bounded byte custody | Copied capture/digest routines; all A110 direct capture imports now private. |

### Private A110 source and FBA registry (2026-11-11)

| Original module or separated symbols | Destination | Applicable caller/role | Change |
|---|---|---|---|
| `tools.ToolRegistry` source catalog, selected source/document execution, original-action replay, durable publication/failure, sequence inspection/view/translation, chemical publication and FBA hooks | `a110/tools.py` | `A110ToolRegistry` private base | Split into independent implementation; no root ToolRegistry inheritance. Removed BLAST/HMMER/native pairwise/read-mapping/RNA/structure/assay/variant/regulation execution catalogs, preparation and publication. |
| `acquisition.PublicClients`, source snapshot and source/NCBI/UniProt/PMC/article helpers, Rhea and ChEBI methods | `a110/acquisition.py` | Private source registry clients | Copied selected source acquisition and byte-preserving parsers; removed BLAST/HMMER clients and parser. Chemical source client uses private provider contracts. |
| `molecular_provider_acquisition` KEGG/Reactome/PubChem request, source identity/representation, receipt and publication functions | `a110/chemical_source_acquisition.py` | Private selected chemical-source operations | Split; STRING, QuickGO and HPA schemas/branches removed. Actual requested identifiers, literal native data, byte limits, partial/invalid source outcomes and immutable source publication preserved. |
| `chemistry.py` | `a110/chemistry.py` | Rhea/ChEBI native source projection | Copied; no host physiological/target inference introduced. |
| `source_locations.py` locator/scanner helpers | `a110/source_locations.py` | Private source registry literal byte locator; existing source identity calls | Extended existing private received-source checks with its original literal locator functions. |
| `boundary_validation.ModelOutputError/parse_json_value`, `data_acquisition_receipts.py` | `a110/source_json.py`, `a110/data_acquisition_receipts.py` | Chemical source strict JSON and acquisition confirmation | Private applicable parser and receipt copies. |
| `api_error_feedback.py` | `a110/api_error_feedback.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `sequence_ops.py` | `a110/sequence_ops.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `sequence_mapping.py` | `a110/sequence_mapping.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `library_targets.py` | `a110/library_targets.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `materials_packing.py` | `a110/materials_packing.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `document_tools.py` | `a110/document_tools.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `spreadsheet_tools.py` | `a110/spreadsheet_tools.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `spreadsheet_worker.py` | `a110/spreadsheet_worker.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `literature_assets.py` | `a110/literature_assets.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `image_evidence.py` | `a110/image_evidence.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `literature_sequence_discovery.py` | `a110/literature_sequence_discovery.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `ncbi_entrez_tools.py` | `a110/ncbi_entrez_tools.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `ncbi_entrez_acquisition.py` | `a110/ncbi_entrez_acquisition.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `experimental_database_acquisition.py` | `a110/experimental_database_acquisition.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `experimental_database_records.py` | `a110/experimental_database_records.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `sequence_composition_grader.py` | `a110/sequence_composition_grader.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `sequence_composition_counts.py` | `a110/sequence_composition_counts.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `sequence_extraction_grader.py` | `a110/sequence_extraction_grader.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `sequence_translation_grader.py` | `a110/sequence_translation_grader.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `api_uniprot.py` | `a110/api_uniprot.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `uniprot_native.py` | `a110/uniprot_native.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `uniprot_native_contracts.py` | `a110/uniprot_native_contracts.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `uniprot_publication.py` | `a110/uniprot_publication.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `public_configuration.py` | `a110/public_configuration.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `uniprot_service_support.py` | `a110/uniprot_service_support.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `native_json.py` | `a110/native_json.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |
| `native_timing_information.py` | `a110/native_timing_information.py` | A110 source/sequence/received byte processing | Private copy of applicable helper; no A101 runtime import. |

The registry consumes the existing private `FluxBalanceOperationUnpublished` and original invocation binder; prepared/saved FBA work retains its original replay, failure, publication and partial-result paths. Existing A110 source/sequence attribution graders were preserved. Source byte readers, document and workbook subprocess module paths now name A110. Sequence helper copy contains composition/translation only; native pairwise calculation is absent.

The later private Store/domain/communication/receipt, material, native resource and transport copies supersede the dependency boundary recorded at this stage. Saved combined construction remains unresolved. No Python, tests, parse/import/static validation, model calls or HPC execution were run.

## Private workflow service split — 2026-11-11

`ToolRegistry.workflow_services` constructs A110's private `WorkflowServices`; `tool_invocation` binds its actual current-invocation context and received-input reader, without structural or SRA dispatch. Scientific provenance, records, reports, source/file input contracts and original receipt-frame readers are private copies. Explicit current and parent preparation readers replace the ownership selector and are passed directly at revision validation callsites.

A110 chemical qualification, native execution/component facts, received component context, scoring sheets, grading and report validation remain connected. Foreign structure, assay, alignment-site, restriction-mapping, variant and MACS return paths were removed from its scientific binding. Ordinary FBA output custody and applicable chemical/Entrez publication receipt checks use the private finite `publication_reference_access.py`; the private FBA backend imports it directly. Native FBA execution/return bindings remain in their existing private modules.

Private scientific/tool libraries, entry contracts, tool information and schema readers use only actual supplied tool/resource catalogs, without global catalog injection. Knowledge and launch manifests select A110 operations and include their own referenced markdown. Execution recipe assets are local. Remaining root dependencies include runtime projector/progress/native-event ports, Store/domain/communication, receipt/return infrastructure, saved-frame transport decoding, native-file capture, material windows and execution planning; those are not claimed split by this service edit. Runtime wiring is handled separately. No tests, Python execution or static validation were run.

2026-11-11 runtime binding: this axis's tools.workflow_services now supplies its private service to runtime. Provenance, current tool invocation, instruction libraries, tool retrieval and semantic receipts are constructed through that service. Original runtime investigation/action-delivery and decision-exchange instructions are independent runtime_prompt.py/decision_protocol_prompt.py copies. Original tool_knowledge.py, launch_instructions.py, scientific_tool_retrieval.py, boundary_validation.py and episode_receipts.py have private implementations and direct callers. Imports of already-present local helpers were rebound directly. Root message parsing, Store/domain/communication, numerical/execution infrastructure and remaining helper dependencies are still open; no execution validation is claimed.

## Private parser, runtime and decision records — 2026-11-11

A110 now has independent domain/communication/form-reference/schema implementations and its own runtime, binding/admission, journal, composition, decision-context/exchange/history, commissions, completion, replay and return-record helpers. Production Workflow and recorded-frame callers use these private implementations and matching local context/error types. Runtime execution does not forward to the root runtime. Original canonical record and receipt identities remain unchanged.

The closed-form parser retains registered file-capture and FBA schemas, exact native FBA value validation and local schema resources. Structural, restriction, homology, assay-native, NMF and other foreign scientific return validators are excluded. The runtime retains actual component/qualification return views, local reaction scoring-sheet delivery and reaction projection-version feedback; it removes concrete HMMER/MinHash/Addgene reference branches. File admission uses a private immutable source-record helper without importing alignment behavior. Composition requires exact original descriptors instead of carrying foreign historical implementation repair pairs.

Subsequent private Store, numerical, provider, transport and input-identity copies supersede the root dependency list recorded at this stage. The existing composition reopen path remains pending. No tests, static validation, imports or Python execution were run; no other-axis or root files were edited.

## Private Store, material intake and geometry — 2026-11-11

The previous Store/account follow-up is now split: `state.py`, material intake/parsing/gzip, GenBank intake, library-target identity, context masks, evidence geometry and scientific-finding validation are independent A110 files. Existing private material packing and sequence mapping remain their direct dependencies. Workflow, source, receipt and geometry callers bind locally. The private Store retains chemical-record custody, source assertions, component sequence/context attribution, findings and original revision relationships. Foreign BLAST/HMMER/Infernal/Minimap observation publication validations and their schema markers are removed; applicable ordinary source and coordinate semantics remain. Artifact access binds A110's private FBA/publication restrictions and no Enrichr restriction.

The active Store/runtime API is `account_invocation`. Historical hashed payload labels `owner` and `account_owner` remain only in identity/signature construction so existing account keys and reasoning-commit identities do not change; they do not choose bindings or grant capabilities. No compatibility parameter or ownership selector was introduced.

Private copies of runtime return facts and contract metadata information also complete their direct imports. Root execution recording/timing/numerical/provider/resource orchestration remains explicit infrastructure and still requires later splitting. This update reports file separation only, not validation or a completed workflow run. No tests, static checks or Python execution were run.

## Private numerical and native execution infrastructure — 2026-11-11

A110 now directly binds private numerical estimation/controller code and its licensed vendor source, execution timing/statistics/recording, native event delivery, local jobs/resources/worker, resource estimates and execution expectations. Existing local native lifecycle and source/FBA workers use the matching private exact types. The worker's file-entry import root and module launch names now resolve A110 implementations. FBA and chemical calculation modules remain the actual private executors; no replacement scientific calculation was added.

The homology assigned-statistics adapter, homology expectation reconstruction/planning, ordinary alignment statistics adapter and foreign native database terminal dispatch are removed. Source spreadsheet and configured execution-class snapshots retain original receipt/statistic identities. The historical null `homology` descriptor field remains inert for saved expectation identity, with no homology constructor or dispatch. Vendor provenance/license files and the required local resource defaults are copied unchanged. The private resource-bound reader still authenticates the existing window launcher's original module identity, not a second workflow launcher or new scientific stopping policy. CPU/RAM/swap enforcement semantics are unchanged.

Still explicit root dependencies include providers and construction, waiting/completion orchestration, instruction/prompt and execution planning helpers reached outside this limited infrastructure set. This is source separation only; no tests, import/parse/static validation or Python execution was performed.

The private resource defaults include the original local tool/job/resource sections needed by their local file readers. Execution planning also has its own copy over private execution memory/guidance/contracts. Native-event information for legacy assigned jobs remains a root runtime dependency; the FBA worker/event publication path is local.

## Private waiting, completion and resource monitoring — 2026-11-11

Waiting, wait-estimation inputs, completion evidence, in-process waits and episode monitoring are now private A110 implementations. The existing private local-return reader, episode admission/completion and runtime directly bind these copies and private numerical/timing types. FBA/local/PBS resource progress, original receipt identity, received progress credit and ordinary iterator observations remain intact.

The unused legacy homology native-job status schema, its progress-credit branch and duration normalization were removed. The private monitor and completion boundary accept actual episode status and A110 resource status. NativeEventInformation construction, wait/report/resolver/fact branches and native-job-event configuration were removed from the private runtime, without borrowing A101's event reader. FBA native worker event publication remains in its private operational lifecycle. Generic caller-bound job-episode orchestration outside those removed homology progress/event paths remains an explicit runtime interface.

Root provider/construction, work-report and HPC prompt helpers remain pending separation; no new adapter, scientific behavior or stopping gate was introduced. Source changes only: no tests, parse/import/static validation or Python execution.

## Private provider, prompts and completed-work account — 2026-11-11

A110 now uses private providers/provider authentication/defaults and their error/model-role types. Its renderer independently retains published scientific TASKs, ordinary receiver TASKs, selected FBA execution/API TASKs and actual HPC/monitor presentation. Component scoring sheets, chemical/native component reports, per-use qualifications, saved reaction cells and reaction meanings remain visible. The ordinary decision/state reconstruction, supplied schemas, outcomes and feedback are preserved. RNA, structure, homology/profile, NMF and assay-native renderer dispatch is excluded.

The private completed-work report calls the original `a110_work_report.completed_work_result` directly, retaining actual chemical/FBA/component/reaction quantities alongside the original action's earned credit. There is no multi-axis adapter registry or imported foreign grading schema. Saved A110 legacy component forms project through their existing private report schema. Runtime and prompt/frame callers bind the local provider/prompt/report files.

The prior private waiting/execution/resource/receipt infrastructure remains local. Construction and episode-input version helpers are now private; source snapshots and FBA worker/deployment paths now use the private package. Reopening remains explicitly unresolved, and successful execution is not claimed. No tests, imports, static validation or Python execution were run.

## Private construction, input frames and loop library — 2026-11-11

A110 now has private application reconstruction/publication, input-version pinning, scientific descriptor preparation, public/tool configuration and finding-progress/validity helpers. Construction uses its actual `A110ToolRegistry`, original remote FBA bindings and direct execution service factory, with only applicable source PDF operands. Foreign fixed-case and homology factory selection are removed. Saved execution/literature/scientific binding reopening errors remain explicit; no new reconstruction bridge or guessed descriptor was added. The return-record frame compares A110's exact original assignment and no longer imports structural/homology adapter preparation.

`method_loop/`, including its original license and source/patch manifests, is copied to `library/method_loop/`. A110 production imports now use that private loop's exact record/context/return/error types. Its durable subprocess launches the private worker module with the placement-correct repository import root. The estimator, scientific credit and ordinary iterator semantics are unchanged.

FBA custody, HPC result/commission/progress support, source display labels and evidence-contract native validation are now private. A110 has no AppService execution binding. Source gathering is not execution validation. No tests, imports, static checks or Python execution were run.

2026-11-11 acquisition class placement correction: the earlier local `acquisition.py` self-import was replaced with its independent original `AcquisitionError` class, preserving the original fields and RuntimeError base. No execution validation was run.

### 2026-11-11 — Remaining FBA custody and execution helper copies

- Replaced the root AppService custody dependency with private `flux_balance_custody.py`: original selected frame, commission, closed-return, and actual FBA handoff possession checks. No BV-BRC service contract or application-selection branch is retained.
- Flattened the six borrowed result-receipt methods and immutable-control helpers into `flux_balance_result_receipts.py`; no genomic-overlap class delegation remains. Original selected action, retained bytes, receipt controls and failed-result semantics remain.
- Copied HPC result receipts/commission construction, resource execution progress, received-file context, practical credit, component assessment dependencies, source display labels and literature contract errors privately; callers now use these copies. Foreign native BLAST observation validation and MACS/LUMPY compact-receipt readers were removed.
- Copied worker source-closure, dependency pinning and immutable staging into `flux_balance_worker_staging.py`; the worker snapshot names A110’s implementation and private loop. No ATAC helper import remains.
- Removed the unused API execution construction/dispatch, API launch prompt/schema branches and the no-op execution adapter file. A110 actual execution remains local FBA and HPC; original HTTP source tools remain separate private tool implementations. Progress readers retain original FBA input-file custody, resource observations and PBS receipt ancestry.
- This is source separation only. No tests, Python commands or static validation were run. Existing explicit saved-binding reopening failures remain unresolved; this change does not claim workflow validation. Tests still have older import paths and were outside this pass.

The private resource-dependency receipt retains the historical JSON field `owner_episode_id` solely to preserve its saved source/hash identity. It contains the originating episode ID and is not a binding selector or enforcement switch; active variables use episode/invocation terminology. As with the private Store’s historical hashed labels, removing that stored label requires an explicit identity migration outside this file split.

2026-11-11 numerical-source retirement: this axis's numerical provenance names
its own private vendor source and MIT license. Its private numerical/timing
implementations and source manifest retain the original estimator, receipt-time
semantics and formulas. Former shared numerical/timing implementation paths were
retired; no tests or execution were run.

## 2026-11-11 — Retired original chemical and flux-balance locations

The private implementations retain their original scientific readers, calculators, graders and worker/result relationships. Their callable module contents are accounted below; source differences are private dependency imports, original-context naming and private worker dispatch rather than new scientific behavior. A110 retains its own chemical readers and local/PBS flux-balance execution; it has no APIServiceExecution producer.

| Original module/symbols | Destination | Actual role/caller | Change |
|---|---|---|---|
| `chemistry.py` (complete module) | `a110/chemistry.py` | A110 chemical formula/reaction reader | Moved; old top-level copy removed |
| `flux_balance_calculations.py` (complete module) | `a110/flux_balance_calculations.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_contracts.py` (complete module) | `a110/flux_balance_contracts.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_execution_inputs.py` (complete module) | `a110/flux_balance_execution_inputs.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_model_execution.py` (complete module) | `a110/flux_balance_model_execution.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_model_tools.py` (complete module) | `a110/flux_balance_model_tools.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_model_worker.py` (complete module) | `a110/flux_balance_model_worker.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_native_capture_contracts.py` (complete module) | `a110/flux_balance_native_capture_contracts.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_operands.py` (complete module) | `a110/flux_balance_operands.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_ordinary.py` (complete module) | `a110/flux_balance_ordinary.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_readers.py` (complete module) | `a110/flux_balance_readers.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_request_binding.py` (complete module) | `a110/flux_balance_request_binding.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_result_contracts.py` (complete module) | `a110/flux_balance_result_contracts.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_result_receipts.py` (complete module) | `a110/flux_balance_result_receipts.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_result_selection.py` (complete module) | `a110/flux_balance_result_selection.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_result_views.py` (complete module) | `a110/flux_balance_result_views.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_result_worker.py` (complete module) | `a110/flux_balance_result_worker.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_return_views.py` (complete module) | `a110/flux_balance_return_views.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_returns.py` (complete module) | `a110/flux_balance_returns.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_sheet.py` (complete module) | `a110/flux_balance_sheet.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_tools.py` (complete module) | `a110/flux_balance_tools.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `flux_balance_worker_contracts.py` (complete module) | `a110/flux_balance_worker_contracts.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_bindings.py` (complete module) | `a110/native_flux_balance_bindings.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_capture.py` (complete module) | `a110/native_flux_balance_capture.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_cobra_glpk.py` (complete module) | `a110/native_flux_balance_cobra_glpk.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_contracts.py` (complete module) | `a110/native_flux_balance_contracts.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_driver.py` (complete module) | `a110/native_flux_balance_driver.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_local.py` (complete module) | `a110/native_flux_balance_local.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_observations.py` (complete module) | `a110/native_flux_balance_observations.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_preparation.py` (complete module) | `a110/native_flux_balance_preparation.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_results.py` (complete module) | `a110/native_flux_balance_results.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_storage.py` (complete module) | `a110/native_flux_balance_storage.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |
| `native_flux_balance_tool_info.py` (complete module) | `a110/native_flux_balance_tool_info.py` | A110 private flux-balance request, local/PBS execution, result receipt or sheet publication | Moved; old top-level copy removed |

The old top-level chemical/tool paths and obsolete native-worker imports no longer provide these implementations; old combined callers remain unavailable. Required model/source assets and native inputs remain in the private source/assets. No tests, parse/import checks or workflows were run.

## 2026-11-11 — Additional original-module placements

This supplement records original modules not named individually above. It maps their complete applicable module contents, including methods and constants; previous symbol-specific narrowing notes remain authoritative. Callers listed here are direct private imports or qualified worker module references, not execution receipts. It does not claim runtime validation.

| Original module/symbols | Destination | Current role/caller | Change |
|---|---|---|---|
| `gene_annotation_episode/_local_job_worker.py` (module contents) | `a110/_local_job_worker.py` | Private dependency used by `execution_recording.py`, `local_jobs.py`, `native_events.py`, `native_lifecycle.py` | Copied/split; private implementation |
| `gene_annotation_episode/a110_chemical_accounting.py` (module contents) | `a110/a110_chemical_accounting.py` | Private dependency used by `a110_reference_accounting.py`, `component_axis_native_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/a110_chemical_contracts.py` (module contents) | `a110/a110_chemical_contracts.py` | Private dependency used by `a110_reference_accounting.py`, `component_axis_native_contracts.py` | Copied/split; private implementation |
| `gene_annotation_episode/a110_fba_hpc.py` (module contents) | `a110/a110_fba_hpc.py` | Private dependency used by `a110_tools.py`, `component_axis_native_hpc.py`, `component_axis_native_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a110_fba_native.py` (module contents) | `a110/a110_fba_native.py` | Private dependency used by `component_axis_native_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/a110_investigation.py` (module contents) | `a110/a110_investigation.py` | Public A110 entry: `create_a110_workflow`, `A110ServiceFactory`, `A110Subtree`; invokes private `component_axis_workflow.create_workflow` and private component service/subtree classes | Copied/split; private implementation |
| `gene_annotation_episode/a110_reference_accounting.py` (module contents) | `a110/a110_reference_accounting.py` | Private dependency used by `a110_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a110_work_report.py` (module contents) | `a110/a110_work_report.py` | Private dependency used by `episode_work_report.py` | Copied/split; private implementation |
| `gene_annotation_episode/application_execution_binding.py` (module contents) | `a110/application_execution_binding.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/communication.py` (module contents) | `a110/communication.py` | Private dependency used by `a102_structural_evidence.py`, `a110_experimental_qualification.py`, `a110_fba_hpc.py`, `a110_qualification.py`, `a110_reference_accounting.py`, `a110_scientific_process_binding.py`, `a110_tools.py`, `component_axis_cell_receipts.py`, `component_axis_execution_context.py`, `component_axis_native_hpc.py`, `component_axis_native_tools.py`, `component_axis_reports.py`, `component_axis_source_access.py`, `component_axis_workflow.py`, `component_source_identity.py`, `episode_admission.py`, `episode_contract_information.py`, `episode_monitoring.py`, `episode_return_records.py`, `episode_services.py`, `execution_contracts.py`, `execution_episode.py`, `execution_input_versions.py`, `execution_progress.py`, `execution_service_setup.py`, `flux_balance_custody.py`, `flux_balance_execution_inputs.py`, `flux_balance_invocation.py`, `flux_balance_operands.py`, `flux_balance_request_binding.py`, `flux_balance_result_receipts.py`, `flux_balance_returns.py`, `flux_balance_tools.py`, `hpc_episode.py`, `hpc_result_receipts.py`, `literature_episode.py`, `literature_experiment_assessments.py`, `literature_reaction_source.py`, `literature_reaction_storage.py`, `literature_sheet_updates.py`, `local_file_capture_results.py`, `local_return_history.py`, `molecular_sequence_input_bindings.py`, `monitor_episode.py`, `native_flux_balance_results.py`, `native_timing_information.py`, `pending_assignment.py`, `practical_receipt_information.py`, `progress_records.py`, `received_input_frames.py`, `received_native_file_inputs.py`, `resource_estimation.py`, `resource_records.py`, `resource_tool_information.py`, `runtime.py`, `scientific_process_episode.py`, `scientific_process_provenance.py`, `scientific_process_reports.py`, `shared_information.py`, `terminal_execution_episode.py`, `terminal_scientific_evidence.py` | Copied/split; private implementation |
| `gene_annotation_episode/completion_evidence.py` (module contents) | `a110/completion_evidence.py` | Private dependency used by `hpc_monitoring.py`, `practical_yield.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/component_assessment_dependencies.py` (module contents) | `a110/component_assessment_dependencies.py` | Private dependency used by `a110_experimental_qualification.py`, `a110_qualification.py` | Copied/split; private implementation |
| `gene_annotation_episode/component_axis_native_worker.py` (module contents) | `a110/component_axis_native_worker.py` | Private dependency used by `component_axis_native_hpc.py` | Copied/split; private implementation |
| `gene_annotation_episode/composition_information.py` (module contents) | `a110/composition_information.py` | Private dependency used by `component_axis_workflow.py`, `literature_episode.py`, `literature_experimental_prompt.py`, `literature_reference_parent_prompt.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/context_masks.py` (module contents) | `a110/context_masks.py` | Private dependency used by `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_context.py` (module contents) | `a110/decision_context.py` | Private dependency used by `providers.py`, `runtime.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_exchanges.py` (module contents) | `a110/decision_exchanges.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_history.py` (module contents) | `a110/decision_history.py` | Private dependency used by `composition_information.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/default_scientific_binding.py` (module contents) | `a110/default_scientific_binding.py` | Private dependency used by `application_execution_binding.py`, `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/domain.py` (module contents) | `a110/domain.py` | Private dependency used by `a102_structural_catalog.py`, `a102_structural_evidence.py`, `a110_experimental_qualification.py`, `a110_fba_hpc.py`, `a110_qualification.py`, `a110_reference_accounting.py`, `a110_scientific_process_binding.py`, `a110_tools.py`, `acquisition.py`, `chemical_source_acquisition.py`, `chemistry.py`, `completion_evidence.py`, `component_axis_cell_receipts.py`, `component_axis_execution_context.py`, `component_axis_native_hpc.py`, `component_axis_native_tools.py`, `component_axis_reports.py`, `component_axis_source_access.py`, `component_axis_workflow.py`, `component_sequence_attribution.py`, `component_sequence_link.py`, `component_source_identity.py`, `context_masks.py`, `data_acquisition_receipts.py`, `document_tools.py`, `episode_admission.py`, `episode_bindings.py`, `episode_commissions.py`, `episode_composition.py`, `episode_input_versions.py`, `episode_monitoring.py`, `episode_services.py`, `evidence_axis_contracts.py`, `evidence_geometry.py`, `execution_episode.py`, `execution_progress.py`, `experimental_database_acquisition.py`, `experimental_database_records.py`, `finding_validity.py`, `flux_balance_custody.py`, `flux_balance_invocation.py`, `flux_balance_operands.py`, `flux_balance_tools.py`, `genbank_intake.py`, `hpc_commission_sources.py`, `hpc_episode.py`, `hpc_result_receipts.py`, `image_evidence.py`, `independent_execution.py`, `investigation_progress.py`, `library_targets.py`, `literature_assets.py`, `literature_episode.py`, `literature_experiment_assessments.py`, `literature_partner_defined_units.py`, `literature_rate_native_inputs.py`, `literature_reaction_inputs.py`, `literature_reaction_meanings.py`, `literature_reaction_native_storage.py`, `literature_reaction_source.py`, `literature_reaction_storage.py`, `literature_sequence_discovery.py`, `literature_sheet_updates.py`, `local_file_capture_results.py`, `material_parsing.py`, `materials.py`, `materials_packing.py`, `molecular_sequence_input_bindings.py`, `monitor_episode.py`, `native_artifacts.py`, `native_file_capture.py`, `native_flux_balance_results.py`, `native_timing_information.py`, `practical_receipt_information.py`, `progress_records.py`, `received_native_file_inputs.py`, `received_sequence_reader.py`, `runtime.py`, `scientific_findings.py`, `scientific_process_episode.py`, `scientific_process_provenance.py`, `scientific_process_records.py`, `scientific_process_reports.py`, `scientific_support_metadata.py`, `scientific_tool_retrieval.py`, `sequence_attribution.py`, `shared_information.py`, `source_display_labels.py`, `source_locations.py`, `source_record_identity.py`, `source_sequences.py`, `state.py`, `terminal_execution_episode.py`, `tool_grading_artifacts.py`, `tools.py`, `uniprot_publication.py`, `uniprot_service_support.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_admission.py` (module contents) | `a110/episode_admission.py` | Private dependency used by `episode_completion.py`, `local_return_history.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_application_services.py` (module contents) | `a110/episode_application_services.py` | Private dependency used by `component_axis_workflow.py`, `execution_service_setup.py`, `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_bindings.py` (module contents) | `a110/episode_bindings.py` | Private dependency used by `episode_composition.py`, `episode_monitoring.py`, `episode_progress_credit.py`, `episode_return_records.py`, `episode_services.py`, `execution_episode.py`, `execution_progress.py`, `flux_balance_custody.py`, `flux_balance_execution_inputs.py`, `flux_balance_operands.py`, `flux_balance_request_binding.py`, `flux_balance_result_receipts.py`, `flux_balance_returns.py`, `form_reference_validation.py`, `hpc_episode.py`, `independent_execution.py`, `literature_episode.py`, `local_file_capture_results.py`, `molecular_sequence_input_bindings.py`, `monitor_episode.py`, `practical_receipt_information.py`, `publication_reference_access.py`, `received_native_file_inputs.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_commissions.py` (module contents) | `a110/episode_commissions.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_completion.py` (module contents) | `a110/episode_completion.py` | Private dependency used by `completion_evidence.py`, `decision_history.py`, `episode_admission.py`, `inprocess_replay.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_composition.py` (module contents) | `a110/episode_composition.py` | Private dependency used by `independent_execution.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_contract_information.py` (module contents) | `a110/episode_contract_information.py` | Private dependency used by `episode_return_records.py`, `flux_balance_custody.py`, `received_input_frames.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_input_versions.py` (module contents) | `a110/episode_input_versions.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_journal.py` (module contents) | `a110/episode_journal.py` | Private dependency used by `completion_evidence.py`, `decision_exchanges.py`, `decision_history.py`, `episode_admission.py`, `episode_commissions.py`, `episode_completion.py`, `episode_report_acquisition.py`, `flux_balance_custody.py`, `inprocess_replay.py`, `received_input_frames.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_report_acquisition.py` (module contents) | `a110/episode_report_acquisition.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_reports.py` (module contents) | `a110/episode_reports.py` | Private dependency used by `runtime.py`, `scientific_process_reports.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_return_records.py` (module contents) | `a110/episode_return_records.py` | Private dependency used by `a110_tools.py`, `component_axis_cell_receipts.py`, `component_axis_execution_context.py`, `component_axis_native_tools.py`, `component_axis_reports.py`, `component_axis_source_access.py`, `episode_services.py`, `execution_episode.py`, `execution_input_versions.py`, `flux_balance_custody.py`, `flux_balance_execution_inputs.py`, `flux_balance_invocation.py`, `flux_balance_operands.py`, `flux_balance_returns.py`, `flux_balance_tools.py`, `hpc_episode.py`, `hpc_result_receipts.py`, `inprocess_replay.py`, `local_file_capture_results.py`, `molecular_sequence_input_bindings.py`, `publication_reference_access.py`, `received_input_frames.py`, `received_native_file_inputs.py`, `runtime.py`, `scientific_process_episode.py`, `shared_information.py`, `terminal_scientific_evidence.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_services.py` (module contents) | `a110/episode_services.py` | Private dependency used by `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_source_failure.py` (module contents) | `a110/episode_source_failure.py` | Private dependency used by `episode_admission.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_work_report.py` (module contents) | `a110/episode_work_report.py` | Private dependency used by `hpc_prompt.py`, `monitor_prompt.py`, `runtime.py`, `scientific_process_prompt.py`, `shared_information_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_contracts.py` (module contents) | `a110/evidence_axis_contracts.py` | Private dependency used by `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py`, `scientific_support_metadata.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_instructions.py` (module contents) | `a110/evidence_axis_instructions.py` | Private dependency used by `a102_structural_evidence.py`, `component_axis_workflow.py`, `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_geometry.py` (module contents) | `a110/evidence_geometry.py` | Private dependency used by `component_assessment_dependencies.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_expectations.py` (module contents) | `a110/execution_expectations.py` | Private dependency used by `independent_execution.py`, `runtime.py`, `tools.py`, `wait_estimation_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_input_versions.py` (module contents) | `a110/execution_input_versions.py` | Private dependency used by `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_planning.py` (module contents) | `a110/execution_planning.py` | Private dependency used by `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_progress.py` (module contents) | `a110/execution_progress.py` | Private dependency used by `execution_episode.py`, `hpc_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_recording.py` (module contents) | `a110/execution_recording.py` | Private dependency used by `_local_job_worker.py`, `native_lifecycle.py`, `native_timing_information.py`, `ordinary_execution.py`, `state.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_timing.py` (module contents) | `a110/execution_timing.py` | Private dependency used by `decision_exchanges.py`, `decision_history.py`, `episode_journal.py`, `numerical.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/finding_validity.py` (module contents) | `a110/finding_validity.py` | Private dependency used by `investigation_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/form_reference_validation.py` (module contents) | `a110/form_reference_validation.py` | Private dependency used by `communication.py` | Copied/split; private implementation |
| `gene_annotation_episode/genbank_intake.py` (module contents) | `a110/genbank_intake.py` | Private dependency used by `material_parsing.py`, `materials.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_prompt.py` (module contents) | `a110/hpc_prompt.py` | Private dependency used by `providers.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_result_receipts.py` (module contents) | `a110/hpc_result_receipts.py` | Private dependency used by `component_axis_native_hpc.py`, `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_scientific_commission.py` (module contents) | `a110/hpc_scientific_commission.py` | Private dependency used by `component_axis_native_hpc.py` | Copied/split; private implementation |
| `gene_annotation_episode/independent_execution.py` (module contents) | `a110/independent_execution.py` | Private dependency used by `application_execution_binding.py` | Copied/split; private implementation |
| `gene_annotation_episode/inprocess_replay.py` (module contents) | `a110/inprocess_replay.py` | Private dependency used by `component_axis_workflow.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/inprocess_waiting.py` (module contents) | `a110/inprocess_waiting.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/investigation_progress.py` (module contents) | `a110/investigation_progress.py` | Private dependency used by `component_axis_workflow.py`, `default_scientific_binding.py` | Copied/split; private implementation |
| `gene_annotation_episode/journal_metadata.py` (module contents) | `a110/journal_metadata.py` | Private dependency used by `episode_journal.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_contract_error.py` (module contents) | `a110/literature_contract_error.py` | Private dependency used by `literature_episode.py`, `literature_experimental_contracts.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_current_results.py` (module contents) | `a110/literature_current_results.py` | Retained original `current_scoring_view`, `current_findings_view`, `current_interpretation_view`, `render_current_scoring_results`, `render_current_findings`; no current production caller | Copied/split; private implementation |
| `gene_annotation_episode/literature_experiment_assessments.py` (module contents) | `a110/literature_experiment_assessments.py` | Private dependency used by `literature_reaction_inputs.py`, `literature_reaction_source.py`, `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_experimental_contracts.py` (module contents) | `a110/literature_experimental_contracts.py` | Private dependency used by `literature_partner_defined_units.py`, `literature_rate_calculations.py`, `literature_rate_native_inputs.py`, `literature_rate_reader.py`, `literature_reaction_calculations.py`, `literature_reaction_inputs.py`, `literature_reaction_native_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_partner_defined_units.py` (module contents) | `a110/literature_partner_defined_units.py` | Private dependency used by `literature_rate_native_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_calculations.py` (module contents) | `a110/literature_rate_calculations.py` | Retained original `populate_rate_contrast`; no current production caller; its exact reported-domain helper is copied as `literature_rate_domains.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_native_inputs.py` (module contents) | `a110/literature_rate_native_inputs.py` | Private dependency used by `literature_experimental_contracts.py`, `literature_rate_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_rate_reader.py` (module contents) | `a110/literature_rate_reader.py` | Retained original `read_rate_table`; no current production caller | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_calculations.py` (module contents) | `a110/literature_reaction_calculations.py` | Private dependency used by `a110_chemical_accounting.py`, `a110_experimental_qualification.py`, `a110_work_report.py`, `literature_component_binding.py`, `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_inputs.py` (module contents) | `a110/literature_reaction_inputs.py` | Private dependency used by `literature_reaction_native_inputs.py`, `literature_reaction_source.py`, `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_meanings.py` (module contents) | `a110/literature_reaction_meanings.py` | Private dependency used by `literature_reaction_inputs.py`, `literature_reaction_native_inputs.py`, `literature_reaction_native_storage.py`, `literature_reaction_source.py`, `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_meanings_render.py` (module contents) | `a110/literature_reaction_meanings_render.py` | Retained original `render_meanings`; no current production caller | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_native_inputs.py` (module contents) | `a110/literature_reaction_native_inputs.py` | Private dependency used by `literature_reaction_inputs.py`, `literature_reaction_native_storage.py`, `literature_reaction_source.py`, `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_native_render.py` (module contents) | `a110/literature_reaction_native_render.py` | Retained original `is_row` and `render_rows`; no current production caller | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_native_storage.py` (module contents) | `a110/literature_reaction_native_storage.py` | Private dependency used by `literature_component_binding.py`, `literature_episode.py`, `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_prompt.py` (module contents) | `a110/literature_reaction_prompt.py` | Private dependency used by `literature_component_binding.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_source.py` (module contents) | `a110/literature_reaction_source.py` | Private dependency used by `literature_component_binding.py`, `literature_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_storage.py` (module contents) | `a110/literature_reaction_storage.py` | Private dependency used by `a110_experimental_qualification.py`, `component_axis_reports.py`, `literature_component_binding.py`, `literature_episode.py`, `literature_reaction_native_storage.py`, `literature_task_selection.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_reaction_types.py` (module contents) | `a110/literature_reaction_types.py` | Private dependency used by `literature_reaction_inputs.py`, `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_task_selection.py` (module contents) | `a110/literature_task_selection.py` | Private dependency used by `literature_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/literature_work_results.py` (module contents) | `a110/literature_work_results.py` | Retained original `returned_result`, `original_json_sql`, `result_projection_sql`; no current production caller | Copied/split; private implementation |
| `gene_annotation_episode/local_jobs.py` (module contents) | `a110/local_jobs.py` | Private dependency used by `document_tools.py`, `flux_balance_model_execution.py`, `flux_balance_tools.py`, `native_flux_balance_local.py`, `native_flux_balance_preparation.py`, `native_flux_balance_results.py`, `native_lifecycle.py`, `practical_execution_operations.py`, `spreadsheet_tools.py`, `terminal_execution.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_resources.py` (module contents) | `a110/local_resources.py` | Private dependency used by `native_lifecycle.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_return_history.py` (module contents) | `a110/local_return_history.py` | Private dependency used by `completion_evidence.py`, `runtime.py`, `wait_estimation_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/material_gzip.py` (module contents) | `a110/material_gzip.py` | Private dependency used by `materials.py` | Copied/split; private implementation |
| `gene_annotation_episode/material_parsing.py` (module contents) | `a110/material_parsing.py` | Private dependency used by `materials.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/materials.py` (module contents) | `a110/materials.py` | Private dependency used by `component_axis_native_hpc.py`, `episode_services.py`, `image_evidence.py`, `library_targets.py`, `local_file_capture_results.py`, `materials_packing.py`, `molecular_sequence_input_bindings.py`, `state.py`, `terminal_scientific_evidence.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/molecular_sequence_input_bindings.py` (module contents) | `a110/molecular_sequence_input_bindings.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/molecular_sequence_input_contracts.py` (module contents) | `a110/molecular_sequence_input_contracts.py` | Private dependency used by `molecular_sequence_input_bindings.py` | Copied/split; private implementation |
| `gene_annotation_episode/monitor_prompt.py` (module contents) | `a110/monitor_prompt.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_events.py` (module contents) | `a110/native_events.py` | Private dependency used by `_local_job_worker.py`, `native_lifecycle.py` | Copied/split; private implementation |
| `gene_annotation_episode/numerical.py` (module contents) | `a110/numerical.py` | Private dependency used by `completion_evidence.py`, `decision_history.py`, `episode_admission.py`, `episode_completion.py`, `episode_journal.py`, `episode_monitoring.py`, `episode_reports.py`, `execution_episode.py`, `hpc_campaign.py`, `hpc_episode.py`, `hpc_monitoring.py`, `independent_execution.py`, `monitor_episode.py`, `practical_yield.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/ordinary_execution.py` (module contents) | `a110/ordinary_execution.py` | Private dependency used by `tool_configuration.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/pending_assignment.py` (module contents) | `a110/pending_assignment.py` | Private dependency used by `episode_commissions.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/practical_execution_credit.py` (module contents) | `a110/practical_execution_credit.py` | Private dependency used by `practical_execution_state.py` | Copied/split; private implementation |
| `gene_annotation_episode/practical_execution_state.py` (module contents) | `a110/practical_execution_state.py` | Private dependency used by `execution_episode.py`, `hpc_episode.py`, `terminal_execution.py`, `terminal_execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/provider_authentication.py` (module contents) | `a110/provider_authentication.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/providers.py` (module contents) | `a110/providers.py` | Private dependency used by `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/received_native_file_inputs.py` (module contents) | `a110/received_native_file_inputs.py` | Private dependency used by `local_file_capture_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/resource_estimation.py` (module contents) | `a110/resource_estimation.py` | Private dependency used by `independent_execution.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/resource_tool_information.py` (module contents) | `a110/resource_tool_information.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/run_statistics.py` (module contents) | `a110/run_statistics.py` | Private dependency used by `execution_expectations.py`, `execution_recording.py`, `ordinary_execution.py`, `resource_estimation.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/runtime.py` (module contents) | `a110/runtime.py` | Private dependency used by `component_axis_workflow.py`, `default_scientific_binding.py`, `episode_report_acquisition.py`, `episode_return_records.py`, `flux_balance_custody.py`, `independent_execution.py`, `inprocess_replay.py`, `received_input_frames.py` | Copied/split; private implementation |
| `gene_annotation_episode/schema_information_text.py` (module contents) | `a110/schema_information_text.py` | Private dependency used by `episode_contract_information.py`, `literature_experimental_prompt.py`, `literature_reference_parent_prompt.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/schema_support.py` (module contents) | `a110/schema_support.py` | Private dependency used by `episode_contract_information.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_findings.py` (module contents) | `a110/scientific_findings.py` | Private dependency used by `finding_validity.py`, `investigation_progress.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_library.py` (module contents) | `a110/scientific_process_library.py` | Private dependency used by `a102_structural_catalog.py`, `component_axis_workflow.py`, `composition_information.py`, `decision_context.py`, `episode_services.py`, `scientific_process_episode.py`, `scientific_process_setup.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_prompt.py` (module contents) | `a110/scientific_process_prompt.py` | Private dependency used by `literature_experimental_prompt.py`, `literature_reference_parent_prompt.py`, `providers.py`, `receiver_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_provenance.py` (module contents) | `a110/scientific_process_provenance.py` | Private dependency used by `episode_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_records.py` (module contents) | `a110/scientific_process_records.py` | Private dependency used by `component_axis_workflow.py`, `episode_services.py`, `evidence_axis_instructions.py`, `flux_balance_returns.py`, `runtime.py`, `scientific_process_episode.py`, `scientific_process_library.py`, `scientific_process_prompt.py`, `scientific_process_provenance.py`, `scientific_process_reports.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_reports.py` (module contents) | `a110/scientific_process_reports.py` | Private dependency used by `scientific_process_episode.py`, `scientific_process_provenance.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_setup.py` (module contents) | `a110/scientific_process_setup.py` | Private dependency used by `component_axis_workflow.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_support_metadata.py` (module contents) | `a110/scientific_support_metadata.py` | Private dependency used by `episode_services.py`, `scientific_process_episode.py`, `scientific_process_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_tool_library.py` (module contents) | `a110/scientific_tool_library.py` | Private dependency used by `component_axis_workflow.py`, `episode_services.py`, `scientific_process_records.py`, `scientific_process_setup.py`, `scientific_tool_retrieval.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information.py` (module contents) | `a110/shared_information.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information_results.py` (module contents) | `a110/shared_information_results.py` | Private dependency used by `episode_work_report.py`, `runtime.py`, `shared_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/source_display_labels.py` (module contents) | `a110/source_display_labels.py` | Private dependency used by `literature_reaction_storage.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_configuration.py` (module contents) | `a110/tool_configuration.py` | Private dependency used by `independent_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_information.py` (module contents) | `a110/tool_information.py` | Private dependency used by `resource_tool_information.py`, `scientific_process_prompt.py`, `scientific_process_records.py`, `scientific_process_reports.py`, `scientific_tool_library.py`, `scientific_tool_retrieval.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_schema_validation.py` (module contents) | `a110/tool_schema_validation.py` | Private dependency used by `resource_tool_information.py`, `scientific_tool_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/wait_estimation_inputs.py` (module contents) | `a110/wait_estimation_inputs.py` | Private dependency used by `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/waiting.py` (module contents) | `a110/waiting.py` | Private dependency used by `flux_balance_request_binding.py`, `flux_balance_result_receipts.py`, `flux_balance_tools.py`, `local_file_capture_results.py`, `local_return_history.py`, `runtime.py`, `wait_estimation_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/workflow_budget.py` (module contents) | `a110/workflow_budget.py` | Private dependency used by `local_jobs.py`, `local_resources.py`, `native_lifecycle.py`, `providers.py`, `runtime.py`, `terminal_execution.py` | Copied/split; private implementation |

2026-11-11: the private vendored numerical template now imports its completion/end-state types from this package's independent `library/method_loop/`, not the top-level repository loop. Upstream numerical code and constants are unchanged; this is the local import-placement patch.

## 2026-11-11 final A110 source-placement accounting

The private entry remains `a110_investigation.create_a110_workflow` / `A110ServiceFactory`, using `component_axis_workflow`, `tools.ToolRegistry`, and local/PBS FBA execution. No API service implementation was added. The remaining original rate-domain helper is copied without changing its enclosure calculations or historical identity labels. Unused retained renderer/rate entry points are explicitly named in the module rows above. The copied runtime's dormant `reads.map` validation branch was removed because the A110 registry has no such operation.

| Original module or symbol | Private destination | Actual caller | Change |
| --- | --- | --- | --- |
| `literature_rate_domains.py` | `a110/literature_rate_domains.py` | Retained `literature_rate_calculations.populate_rate_contrast` reads `VERSION`, `native_domain_trace`, `apply_native_domains` | Independent exact helper copy |
| `component_axis_native_hpc.snapshot_sources` | `a110/component_axis_native_hpc.py` | `component_axis_native_hpc.freeze` and `a110_fba_hpc.freeze` | Named scientific files resolve only in A110; root-file fallback removed; package initializers retained |
| `a110_fba_hpc.freeze` deployment implementation comparison | `a110/a110_fba_hpc.py` | `component_axis_native_hpc.freeze` for original `chemistry.request_flux_balance_hpc` | Remote and local implementation paths name the same private files |
| `native_flux_balance_contracts.validate_flux_balance_software` | `a110/native_flux_balance_contracts.py` | `a110_fba_hpc.normalize`, original native FBA bindings and driver | Required implementation-file paths use private A110 names; original software identity checks retained |
| `native_flux_balance_preparation` worker source pin | `a110/native_flux_balance_preparation.py` | Original retained FBA result worker staging/validation | Pins private `flux_balance_result_worker.py` at its actual source snapshot path |
| `workflow_budget` coordinator command identity | `a110/workflow_budget.py` | Private coordinator resource-context reader | Recognizes its own private module command |

Neither A110 nor A103 contains `literature_implementation_sources.py` or calls that root-fallback helper. A110 snapshot source selection now has no behavioral root fallback. Saved descriptor reopening remains explicitly unresolved in `episode_composition.py`; this placement pass does not claim a reconstructed or executed workflow. No Python, tests, parse/import validation, static suite or job was run.

## 2026-11-11 iterator package placement

Moved the independently copied `library/method_loop/` package to `method_loop/` beside the private workflow code. It contains episode bindings, continuation and return mechanics, so it is outside the standalone-helper library. Direct imports and durable-worker module paths now name this private location; the worker package-root depth follows the moved files. Original license and provenance manifests remain with the copy. No runtime behavior or stopping rule was added.

2026-11-11: Root scalar helpers used by `a110_qualification.py` were independently extracted into `a110_contribution.py`. The private record fixes A110 directly; contribution range, native correspondence/prerequisite arithmetic and attribution are preserved. Callers no longer import root scientific arithmetic or pass an axis selector.

### 2026-11-11 remaining original/source-library disposition

The top-level chemical/FBA originals, including `chemistry.py`, are already retired with independent A110 implementations recorded above. No additional A110-only scientific original was found in this remaining-root pass. `library/literature_assay_inputs.py` and `library/literature_partner_source_fields.py` remain standalone source/witness/number readers used by reaction source population, reaction native inputs, meaning records and defined-unit readers. Binding, return, grading and continuation files remain outside library/. No test or new execution path was added.

## 2026-11-11 recorded scientific-process episode destination

Before relocation: `scientific_process_episode.py:ScientificProcessEpisode` is
assigned to `scientific_process/episode.py` beneath this axis in
`gene_annotation_episode/episodic_workflow/root/`. Registered role: `scientific_process`;
commissioning parents: root annotation and the same recursive scientific-process
role. Keep the generic name: the assignment mixes task-selected investigation,
preparation/revision, tool choices and scientific result interpretation. A later
goal must divide those tasks and provide the missing dedicated axis head. This
pass must not manufacture either an axis head or infinitely nested recursion.

Supporting responsibilities: assignment/schema/preparation in `requests.py`;
typed reports, received results and references in `returns.py`; original task
projection in `credit.py`; task-selected continuation settings/estimator in
`yield_estimator.py`; registration, context, available actions/children and local assembly
in `episode.py`. Scientific scoring dependencies and their distinct descriptive
filenames remain as recorded above. Cross-episode tests/fixtures remain at this
axis's `tests/` until their precise local owner is established. Relocation is
pending; this entry fixes the chosen name before any binding moves.

### Scientific-process binding relocation applied

`scientific_process/episode.py` now owns the one `scientific_process` registration. The original module is removed; callers import the new binding directly. Each supporting class is private to this episode and has no registration.

- `scientific_process/episode.py`: `__init__`, `as_record`, `contract_information_profile`, `_role`, `child_roles`, `permitted_common_actions`, `allowed_children`, `instructions`, `_information_catalog`, `_closed_tool_resolution`, `_tool_resolution_for`, `_tool_resolution`, `catalog`, `common_tool_names`, `decision_context`, `execute`, `_component_scoring_facts`, `current_report_facts`, `initial_decision_context`, `_validate_component_axis_report`.
- `scientific_process/requests.py`: `assignment_schema`, `child_assignment_schema`, `_selection`, `_assignment`, `_invocation`, `prepare_assignment`, `_validate_origin`, `prepare_invocation`, `restore_closed_process`, `restore_saved_process`, `validate_context`, `validate_execution_context`, `_original_selection`, `_proposed_selection`.
- `scientific_process/returns.py`: `required_return_sources`, `fact_sources`, `facts`, `received_report_facts`, `validate_received_report`, `resolve`, `validate_report`, `initial_references`.
- `scientific_process/credit.py`: `credit_kind`, `credit_projector`, `credit_view`.
- `scientific_process/yield_estimator.py`: `private_yield_binding`, `continuation_task`, `yield_controller`.

Implementation fingerprinting continues to cover this axis's source tree, including the extracted files. No credit, yield, scientific scoring, report, waiting or request rule is changed. Descriptive scientific-process helper placement and test ownership remain to be completed in this pass.

## 2026-11-11 literature destinations recorded before splitting

The original `literature_episode.py:LiteratureEpisode` registers seven roles. These private replacements retain the current role-specific assignment, tools, source custody, grading, report, credit, yield and waiting semantics. Paths below are relative to this axis.

| Registered role | Chosen directory / binding | Commissioning parent |
| --- | --- | --- |
| `literature` | `scientific_process/published_evidence_assessment/episode.py` | `scientific_process` |
| `literature_strategy` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | `scientific_process/published_evidence_assessment` |
| `literature_search` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` |
| `literature_page` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` |
| `literature_table` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` |
| `literature_ordered` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` |
| `literature_targeted` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` |

Each binding retains its own local methods: `requests.py` for assignments and request-derived schemas; `returns.py` for source/fact/report delivery; `credit.py` for task progress; `yield_estimator.py` for existing forecast behavior; `waiting.py` for existing wait declarations; `episode.py` for registration, construction, actions, and selected grader/repository assembly. Files are created only for existing responsibilities. Descriptive calculators, graders and sheet storage retain their names and current axis ownership pending the dependency-placement review.

The current source-reading roles also perform applicable interpretation/population and grading work. That task mixture is preserved here; a later goal must decide task-specific divisions. Root evidence assessment can search/read directly as well as commission the nested strategy/search/source chain. Cross-role literature tests and shared fixtures remain at their common owner until the test-placement review.

### Literature role separation applied

The former multi-role class has been removed. Each recorded directory now has one independently implemented `LiteratureEpisode` with a singleton registration role; child-only bindings have empty entry roles. Their request/report/credit/yield/wait methods are private local supporting classes. The published-evidence episode exposes `create_binding_tree` only as caller assembly of seven separate instances, with copied existing caller configuration. It is not a registered binding, continuation policy or forwarding replacement. Existing scientific method bodies are preserved, including applicable A105/A108 grading and typed findings.

`literature` support map:

- `scientific_process/published_evidence_assessment/episode.py`: `literature_reaction_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/waiting.py`: `supports_wait`.

`literature_strategy` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py`: `literature_reaction_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/waiting.py`: `supports_wait`.

`literature_search` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py`: `literature_reaction_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/waiting.py`: `supports_wait`.

`literature_page` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py`: `literature_reaction_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/waiting.py`: `supports_wait`.

`literature_table` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py`: `literature_reaction_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/waiting.py`: `supports_wait`.

`literature_ordered` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py`: `literature_reaction_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/waiting.py`: `supports_wait`.

`literature_targeted` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py`: `literature_reaction_repository`, `__init__`, `reference_evidence`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `_owned_population_task_sources`, `_population_task_context`, `catalog`, `execute`, `_population_routes`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`, `_materialize_text_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `_rate_fact_sources`, `_rate_facts`, `received_report_sources`, `received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/yield_estimator.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/waiting.py`: `supports_wait`.


## 2026-11-11 operational episode destinations recorded before relocation

The following plan follows declared child roles and the existing configured scientific parent. Resource-backed and direct execution bindings are alternative existing implementations; their distinct task homes do not imply simultaneous registration. Parent-specific copies preserve original request, report, operational/monitoring credit, yield and waiting behavior.

| Original class | Registered role | Chosen home (`episode.py`) | Commissioning parent |
| --- | --- | --- | --- |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/execution_job_submission` | `scientific_process` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/execution_job_submission/local_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/execution_job_submission/hpc_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/execution_result_acquisition` | `scientific_process` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/execution_progress_assessment` | `scientific_process` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `scientific_process/hpc_work_planning` | `scientific_process` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `scientific_process/hpc_work_planning/hpc_resource_prediction` | `scientific_process/hpc_work_planning` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/execution_job_submission` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/execution_result_acquisition` | `scientific_process/hpc_work_planning` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/execution_progress_assessment` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |

The HPC prediction and allocation-execution episodes are siblings. HPC planning and allocation execution each commission their own submission, monitoring and result-acquisition copies. No generic children directory is introduced. Repeated run invocations reuse these source homes. Generic execution roles currently mix environment preparation, native/API work, recovery and result delivery under their original assignment; this mixture remains, with task-specific scientific divisions deferred.

Existing supporting methods will be extracted into local requests, returns, credit, yield and waiting files where present. Native parsers, calculators, graders and scientific sheets retain descriptive names. Monitor observation calculators retain their descriptive implementation file; monitoring information credit is not scientific scoring.

The existing `TerminalExecutionEpisode` is delegated inside `ExecutionEpisode` for the same `launch_local`/`launch_hpc` iteration; it is not a commissioned child. Its operative methods belong to each corresponding local/HPC job-execution home in `terminal_execution.py`, with the single private registration supplied by that home's `episode.py`. The old two-role operative class must not create a second registration or a fictitious nested episode.

Runtime limitations: saved composition currently raises `private_binding_reopen_pending`, and the registry indexes only a role token. Parent-specific duplicate-role registration and legacy monolithic homology runtime/adapter interfaces must be reported explicitly until a caller can address their private paths. Do not choose one parent's binding as a fallback for another.

### Literature extraction verification

`runs/episode_literature_checks_20261111/checks.json` verifies this axis's seven
new private bindings: each imports, constructs with the original defaults, keeps
its original assignment schema/child roles/credit kind/wait declaration, and
registers alongside the other six without a role collision. Original method
bodies are preserved after import/path normalization; source-fingerprint and
singleton registration identity changes are checked separately. The axis's
scientific grading behavior is retained, with no new scientific run claimed.
Remaining task-specific test placement and descriptive dependency ownership
must still be reviewed before the full relocation goal can be complete.

### Operational private implementations written

Each planned home now contains one singleton-role class with its original methods split into private responsibility files. Descriptor binding IDs name the stable source home so repeated-parent copies have distinct ownership; registered role tokens and scientific return contents retain their existing meanings. The original modules are temporarily retained only until their callers and receipt-source references are rebound; they must be removed before this pass is complete.

`scientific_process/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield_estimator.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/hpc_work_planning` (`hpc`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield_estimator.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/hpc_resource_prediction` (`hpc_prediction`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield_estimator.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/hpc_allocation_execution` (`hpc_execution`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield_estimator.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield_estimator.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_flux_balance_reference_access`, `_flux_balance_selector`, `_retained_flux_balance_target`, `_versions`, `_flux_balance_inputs`, `_matches_flux_balance_assignment`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield_estimator.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield_estimator.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.


## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/execution_job_submission` | `execution_job_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_job_submission/hpc_job_execution` | `execution_job_submission/hpc_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission/local_job_execution` | `execution_job_submission/local_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_progress_assessment` | `execution_progress_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_result_acquisition` | `execution_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning` | `hpc_work_planning` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning/execution_job_submission` | `hpc_work_planning/execution_job_submission` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `hpc_work_planning/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `hpc_work_planning/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_progress_assessment` | `hpc_work_planning/execution_progress_assessment` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_result_acquisition` | `hpc_work_planning/execution_result_acquisition` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution` | `hpc_work_planning/hpc_allocation_execution` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_resource_prediction` | `hpc_work_planning/hpc_resource_prediction` | private copy | hpc_work_planning |
| `scientific_process/published_evidence_assessment` | `published_evidence_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement` | private copy | published_evidence_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | private copy | published_evidence_assessment/evidence_search_strategy_improvement |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/execution_job_submission` | `execution_job_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_job_submission/hpc_job_execution` | `execution_job_submission/hpc_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission/local_job_execution` | `execution_job_submission/local_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_progress_assessment` | `execution_progress_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_result_acquisition` | `execution_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning` | `hpc_work_planning` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning/execution_job_submission` | `hpc_work_planning/execution_job_submission` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `hpc_work_planning/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `hpc_work_planning/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_progress_assessment` | `hpc_work_planning/execution_progress_assessment` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_result_acquisition` | `hpc_work_planning/execution_result_acquisition` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution` | `hpc_work_planning/hpc_allocation_execution` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | private copy | hpc_work_planning/hpc_allocation_execution |
| `scientific_process/hpc_work_planning/hpc_resource_prediction` | `hpc_work_planning/hpc_resource_prediction` | private copy | hpc_work_planning |
| `scientific_process/published_evidence_assessment` | `published_evidence_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement` | private copy | published_evidence_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment` | private copy | published_evidence_assessment/evidence_search_strategy_improvement |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |
| `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction` | private copy | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

## 2026-11-11 binding test ownership

Current direct literature tests now import the private role matching their explicit context; standalone parent contexts use the standalone copy. Tests that construct root/runtime workflows stay at the common axis test owner. Scientific graders, sheets and fixtures are shared by the independent standalone/scientific copies and retain the common axis owner. Historical combined tests with already-retired top-level imports remain unavailable; source placement does not repair their missing runtime.

No reviewed direct binding test is exclusive to one private episode: existing tests retain the common axis owner.

Shared required fixtures stay in `tests/fixtures/`; reusable named test helpers remain in `tests/` when imported by other tests. No fixture or helper is moved into disposable runs. The detailed support/test inventory records the final owners.

## 2026-11-11 final request-responsibility placement

The following existing incoming-assignment/schema/constraint methods move unchanged from each private episode.py class into that same home's requests.py mixin. These are method placements, not additional bindings or a change to admission behavior.

- `execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.

## 2026-11-11 final role and supporting-code index

The [complete ownership inventory](ownership_inventory.json) is the exact appendix to this record: it maps every original binding class to its singleton role, actual parent, final home, local method symbols and responsibility files. It also records every descriptive support module, its owner, imports, direct callers and consuming episodes; every library symbol and its explicit importing modules; and each test/helper and required fixture file. Unreferenced retained modules are recorded with empty consumers, not represented as active evidence or bindings. Shared scientific graders, readers, sheets and calculators keep their descriptive names at the common axis owner. Their functions are not merged with investigation credit.

| Original binding | Role | Final home | Parent | Supporting files |
| --- | --- | --- | --- | --- |
| `execution_episode.py:ExecutionEpisode` | `launch` | `execution_job_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `execution_job_submission/hpc_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `execution_job_submission/local_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `execution_progress_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `execution_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `hpc_work_planning/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `hpc_work_planning/execution_job_submission/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `hpc_work_planning/execution_job_submission/hpc_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `hpc_work_planning/execution_job_submission/local_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `hpc_work_planning/execution_progress_assessment/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `hpc_work_planning/execution_result_acquisition/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `hpc_work_planning/hpc_allocation_execution/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `hpc_work_planning/hpc_resource_prediction/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `published_evidence_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `scientific_process_episode.py:ScientificProcessEpisode` | `scientific_process` | `scientific_process/episode.py` | root annotation; scientific_process self-recursion (not expanded) | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/execution_job_submission/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/execution_job_submission/local_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/execution_progress_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/execution_result_acquisition/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `scientific_process/hpc_work_planning/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/execution_job_submission/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/execution_progress_assessment/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/execution_result_acquisition/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield_estimator.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield_estimator.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `scientific_process/hpc_work_planning/hpc_resource_prediction/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `scientific_process/published_evidence_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | scientific_process/published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield_estimator.py` |

The old scientific_process_episode.py, literature_episode.py and applicable operational *_episode.py modules have been removed. The tables above supersede earlier temporary-retention notes. The terminal operative behavior is private in the corresponding execution home and has no independent role registration. Generic scientific-process recursion and the missing task-specific axis head remain explicit. Scientific process still mixes target interpretation, tool selection and child commissioning; launch still mixes preparation, native/API execution and recovery. Their later scientific divisions are not redesigned here.

The role-only registry still cannot address equal role tokens under different parents. Existing axis service factories construct the scientific-parent family; standalone homes are independent source owners. The retained top-level A101 resource service explicitly constructs its five standalone private roles. Saved composition/reopening and the original legacy multi-role homology interface remain unavailable for complete composition. Every monitoring binding also retains its original monitor-to-monitor recursive edge; this reuses its owner home rather than expanding directories without end. No working whole-axis scientific workflow is claimed by the relocation. Consumer lists in the appendix describe static import reachability, not evidence of execution or scientific use.


## 2026-11-11 complete private implementation scope: parent identity

The full requested responsibility split remains incomplete. The earlier
structural completion claim is limited to the placement review. The
[current requirement audit](../../../../docs/EPISODE_PRIVATE_IMPLEMENTATION_PROGRESS.md)
records the complete specification and remaining work.

The axis-local registry now resolves explicit binding paths and original
commissioning parents. Core runtime selection, private task construction,
credit/continuation and child contracts use those identities. Ambiguous
role-only lookup fails; legacy bindings without private paths retain their
existing selection. This is reusable dispatch infrastructure, not a new episode
or scientific policy. The matching inventory entry names functions and callers.

Retained controlled verification: `runs/private_binding_identity_20261111_final/comparison.json` — 184 passes and the same 23 A105
baseline failures, with identical failure messages. All nine scientific-process
method bodies are preserved. Resource-route lookup, native replay ownership,
saved reopening and complete responsibility splits remain separate outstanding
work. No autonomous scientific workflow or full restoration is claimed.


## 2026-11-11 remaining monitor responsibility extraction

Each existing monitor now has its own goal, task, decision exchange, state, operations, reports, credit and yield files, plus recursive directional messages and tests. Per-episode ownership files and inventories describe current files, dependencies and remaining parent-message/applicability work. The whole monitor check has 426 passes and two inherited A106 Store initialization failures; original-binding reproduction is retained. See `runs/monitor_tree_20261111_audit/`, `runs/monitor_tree_20261111_behavior/` and `runs/monitor_tree_20261111_a106_baseline/`. This is controlled connection validation, not autonomous monitoring or full restoration.

## 2026-11-11 named monitor parent exchanges

Each existing scientific/HPC parent of a progress monitor now has connected
`to_child_execution_progress_assessment.py` and
`from_child_execution_progress_assessment.py`. Current parent and child
inventories record both endpoints and their saved action/report-attempt identity.
The parent methods retain their original bodies; HPC implementation fingerprints
include the new message files. The seven missing legacy parent homes across the
axes remain explicit. Retained verification and the corrected test exception
assertions are in `runs/monitor_parent_tree_20261111_records/validation.json`:
530 current passing checks and two inherited A106 Store-construction failures.
The parents' larger task divisions and the full organization remain incomplete.

## 2026-11-11 private monitor task narrowing

Monitor decision snapshots and fresh input preparation now have private implementation files. Inapplicable scientific/job/read-mapping/shared-grading branches were removed with their destinations or non-applicability recorded. Baseline 272 checks pass; expanded validation has 698 passes and the same two inherited A106 Store failures. Source audit and current inventories are under `runs/monitor_task_narrowing_20261111_{audit,records}/`. Private instructions, prompt rendering, caller credit presentation and the full episode-tree organization remain open.

## 2026-11-11 monitor instructions and renderer ownership

Each private monitor now composes applicable instructions in `task_instructions.py` and selects `library/monitor_prompt.py` explicitly. The old root formatter moved; its consumers are recorded in `library/monitor_prompt.ownership.json`. Provider transport accepts the declared renderer through an optional interface, preserving default behavior. Binding fingerprints include the selected library source. The expanded suite has 1,032 passes and two inherited A106 failures; all 340 affected instruction checks pass after the final guidance preservation. Source and current identity receipts are under `runs/monitor_prompt_ownership_20261111_{audit02,records}/`. Earlier instruction/rendering limitations are superseded for these monitors. Caller credit-shape presentation, restoration and the full episode-tree organization remain unfinished.

## 2026-11-11 monitor credit calculator ownership

Private monitor credit files now select `library/progress_information_credit.py` with explicit caller operands; custom projectors remain unchanged. Consumers, source provenance, actual projector names and per-axis branch accounting are in `library/progress_information_credit.ownership.json`. A104 restores its original missing shared dependency; A107 removes an unsupported legacy job branch. Stale public-reader imports in affected setup paths were repaired. Validation has 1,302 passes and two unchanged A106 Store failures, plus 34 passing actual-outcome/runtime-credit connections. Full service construction, saved reopening, caller-specific presentation and wider organization remain open.

## 2026-11-11 canonical workflow resource infrastructure

This axis now imports machine ownership/enforcement directly from the canonical module. Its own Policy, AcquisitionError and scientific/native implementation bodies remain unchanged.

The same actual launcher/owner now serves these consumers. The canonical checker, launcher, one-CPU/5-GiB/no-swap bounds and authentication guards are unchanged. Four axes previously failed sixteen owner checks; after the import repair their eight default Policy/Resources boundaries and three ToolRegistries return, and all five redundant copies are retired. A104's ToolRegistry now exposes a separate missing `local_tools` KeyError. A102 retains its three separately observed missing-default KeyErrors. These are constructor diagnostics, not a test-pass count or native/scientific workflow validation.

Original checker sources, metadata, fingerprints and receipts remain historical. Any source changes predating this repair are listed separately from its exact delta. The existing CPU/thread gate is documented by a separate no-native diagnostic and remains open; no count limit or stopping rule was added. Full private splitting and saved-workflow restoration remain incomplete. Complete scoped evidence: `runs/workflow_resource_infrastructure_20261111_records_prepare`.


<!-- private_nonhead_guard_current_source_proposal_20261113 -->

## 2026-11-13 private non-head guard source proposal

This sparse current-source proposal accounts for selected private homes and scientific head fingerprint. The source manifest `runs/root_private_head_guard_successor_preparation_01/sources.json` removes only the finite non-head scientific validation guards proved unreachable through the actual declared construction, dispatch and restoration paths (or literal-false A104 comparisons). Constructors remain unchanged and actual scientific-head checks remain owned by their heads. The own-home AST catalogue includes actual methods, bodies, line ranges, imports, calls and unresolved receiver attributes; previous installed source moves are accounted for, not attributed to this guard edit. The actual head source digest and its original producer operands are recorded in `runs/root_nonhead_guard_metadata_generation_01/prepared/scientific_fingerprint_accounts.json`; this is not a hash of the full configured descriptor. Historical records and earlier receipt claims retain their original bytes. This is source-only preparation: application, runtime validation and saved-descriptor acceptance remain separate. The existing connected-run canonical freeze remains in force.


## 2026-11-13 installed private non-head guard epoch

The preceding source-only proposal is retained preparation history. The A10736/A11024 source changes and their68 metadata documents are now installed. All exact afterimages and actual scientific source fingerprints passed a separate read-only audit. The initial application receipt retains its post-write metadata lookup error; no failed receipt was rewritten. The same30 original native boundary probes before/after installation preserve150 returned-action and180 wait observations, including failed/invalid/unavailable outcomes and saved-action replay, with no semantic differences after documented run-specific timing/workspace normalization. This is controlled connection validation, not whole saved-workflow restoration or autonomous science. Main released the preceding HPC source reservation; its480 earlier controlled cases retain their original epochs. Actual source/application/audit/comparison evidence: `runs/fourth_guard60_metadata68_prepare_01/prepared/sources.json`, `runs/fourth_guard60_metadata68_application_01/application.json`, `runs/fourth_guard60_installed_audit_01/verification.json`, `runs/fourth_guard60_comparison_01/comparison.json`.


## Retained execution owner integration (2026-11-13)

Current ownership is recorded under `retained_owner_import_corrections_20261113`. The coherent source candidate contains 365 production files, 224 required production assets, eight test modules and their original fixture; both actual source-index consumers retain strict current identity checks and their original ordered membership. All 268 examined original import edges now select actual same-axis defining owners. The candidate workspace passed 66 controlled cases and 363 imports. Canonical postchecks remain pending; saved restoration, native production and autonomous scientific validation are unclaimed.

The actual current scientific source fingerprint is `2a3e849b4d6344057ee3231287f2dd3e99b86671356e17071b89f187bd28a152`; predecessor `e25b5574a1aba9335ca2f3cac639f2e50999ab06ba820286e41ff22805d261b0` and its retained results remain attached to their original epoch. Original source custody, explicit fresh/retained identity policy, finite transport and environment policy changes, tests, assets and exact application manifest are recorded together.


### Installed controlled validation

The preparation note above is historical. The exact 365-source production cohort is installed and passed 66 focused controlled test cases in the canonical source tree. Actual source records, consumer observations and limitations are retained under `retained_owner_import_corrections_20261113.installed_controlled_validation`. The changed source epoch is authenticated without rewriting earlier receipts. Saved restoration, native production execution and autonomous scientific validation remain unclaimed.


## Retained runtime owner successor (2026-11-13)

Current source ownership is recorded under `retained_owner_callback_form_successor_20261113`: 9 production paths and 268 examined original import edges. Restore original own-reference callbacks on four actual retained native hosts and their receipts, the original ATAC nested reference helper and four missing native schema/semantic branches. Existing FBA/fluorescence callbacks and FBA form handling remain intact. Controlled tests preserve actual failed/invalid outcomes, source authority and exception causes. The actual scientific source fingerprint is `cd9f0ab99226f5e155296b3ec76a5fda20b7e003f576bc6c763d520ed69fc4cd`, successor to `2a3e849b4d6344057ee3231287f2dd3e99b86671356e17071b89f187bd28a152`. Earlier accounts and validation receipts remain historical evidence for their stated source epochs. Controlled candidate checks are linked; canonical postchecks remain pending. Saved workflow restoration, native scientific execution and autonomous scientific validation remain separate and unclaimed here.


### Installed controlled validation

The preparation note above is historical. The exact 9-source production cohort is installed and passed 69 focused controlled test cases in the canonical source tree. Actual source records, consumer observations and limitations are retained under `retained_owner_callback_form_successor_20261113.installed_controlled_validation`. The changed source epoch is authenticated without rewriting earlier receipts. Saved restoration, native production execution and autonomous scientific validation remain unclaimed.


## Current parent request organization (2026-11-13)

`private_parent_request_organization_20261113` records the current parent-owned assembly, literal source identities, current private inventories, exact descriptor operands and preserved historical fields. The 46 controlled candidate cases passed across both axes; canonical postchecks remain pending. Other organization defects, restoration and autonomous scientific validation are separate.


### Installed parent request epoch

`private_parent_request_organization_20261113` is now installed. Actual canonical checks passed 46 cases across A107/A110, and all four literal source indices were evaluated against exact current bytes. The inventory links the application, check and actual workload-exit receipts. Earlier preparation notes and historical source epochs remain retained. No broader organization, saved restoration or autonomous scientific completion is inferred.


## Current private organization successor (2026-11-13)

`private_responsibility_organization_20261113` records current private owners, retired paths, literal source identities, exact descriptor operands and preserved historical fields. The linked 1742 controlled candidate cases passed across both axes; canonical postchecks remain pending. Earlier guard/import/HPC480 results remain attached to their original epochs. Inherited limitations, restoration and autonomous scientific validation are separate.


### Installed organization epoch

`private_responsibility_organization_20261113` is now installed. Actual canonical checks passed 1742 controlled cases across the selected axes, and 4 literal source indices were evaluated against exact current bytes. Scope: Controlled tests of changed private boundaries, original typed invalid/failed outcomes, requests/returns, source/exception identities, actual owned selections, retained numerical/credit/yield behavior, and source operands. These shared controls do not establish invocation of every private home, native/HPC execution, saved-workflow restoration, or autonomous scientific validation. The inventory links application, check and actual workload-exit receipts. Earlier validation and HPC480 remain attached to their original source epochs. This shared cohort does not establish invocation of every private home, saved restoration or autonomous scientific validation.


Current A110 source and dependency ownership is recorded under `implicit_annotation_parent_organization_20261113`. The existing implicit annotation parent is explicit; the 51 registered child identities remain. The current record carries exact descriptor formula/source operands and separately scoped controlled evidence. Earlier receipts remain attached to their original epochs. Canonical installation and full saved-workflow or autonomous validation are separate Main-owned decisions and records.


## 2026-11-13 current parent preservation and conditional improvement

Current ownership is recorded in `current_parent_report_scientific_and_improvement_20261113`. The original registered child identities and their historical outcomes are retained. Parent report/constructor/live-global preservation has the disjoint actual38 union; Scientific endpoint live globals have actual20. Conditional improvement has the explicit86+12 union98, with its original failed run preserved. The separate48+2 union covers current report/action/root policy owners and the original cold cases, with failed50 raw receipts and independent import/cold verification preserved; earlier98 is not relabelled as final-policy execution. Exact private configuration, assembly provider and unique root-policy consumers are recorded in `runs/main_a107_a110_policy50_controls_generation_01/prepared/CALLER_OWNERSHIP.json`. These controlled boundary results use named supplied ports and original errors, without autonomous science, native execution or full saved restoration claims. The actual descriptor formula and byte operands are recalculated in `runs/main_a107_a110_final_metadata07_01/prepared/a110/SCIENTIFIC_FINGERPRINT.json` and `runs/main_a107_a110_final_metadata07_01/prepared/a110/DESCRIPTORS.json`. The descriptive `annotation_improvement` home retains runtime role `improvement` and introduces no registration or saved descriptor. Prior current values remain raw history. The six inherited A110 import diagnostics remain open as recorded in `runs/root_a107_a110_final_parent_metadata_preparation_01/HELPER_DISPOSITION.md`. This record supplies preparation provenance; current installation status is governed by `docs/EVIDENCE_AXIS_LEDGER.md`, requiring an actual application receipt and complete source/metadata membership, byte and mode postchecks.


## 2026-11-14 original-provider and late HPC policy ownership

Current source, method, descriptor-formula and infrastructure associations are in `current_original_provider_late_policy_and_descriptor_ownership_20261114` and the refreshed current fields of `ownership_inventory.json`. The existing task/objective/commissioning/child/scientific grading/credit/yield/waiting/report responsibilities remain substantive; this successor restores authentic mutable original-provider reads in their private owners. All eight private HPC receipts retain their original private direct fallback, saved-return and timing bodies. The actual56 evidence in `runs/main_a107_a110_final_descriptor224_metadata_01/prepared/CONTROLLED_EVIDENCE.json` covers only the named callback/provider/private-class/cold-entry boundaries. That56 remains at source870; its exact18 policy transitions and32 descriptor-member transitions are accounted separately, with5194 original operands unchanged. Actual22 measures late HPC policy, native Name/builtin errors and four cold entries at source874. The two same-axis standalone validator libraries and their16 private consumers preserve the original schema/error position and literal custom fallback; all other episode policies retain their named owners. Prior38/20/98/50 and child/native milestones retain their actual source epochs; there is no full-workflow, scientific execution or restoration claim. Exactly16 original runtime-containing descriptor maps per axis append the moved policy library, retaining formula/order/configuration/identity. Actual4 runs all32 real original/current descriptor methods against copied actual bytes and verifies policy-byte sensitivity with minimal/complete supplied configuration. Scientific already includes the library through its original whole-axis formula. Other formulas remain unchanged; no saved descriptor is rewritten or constructor invoked. Unchanged descriptions retain their existing owners, with current source and dependency associations explicit; earlier dated source observations and overwritten raw values remain history. The six inherited A110 helper diagnostics remain qualified in `runs/root_a107_a110_final_parent_metadata_preparation_01/HELPER_DISPOSITION.md`. Preparation from actual original-provider boundary evidence. Current installation status is governed by docs/EVIDENCE_AXIS_LEDGER.md and its actual application and complete source/metadata byte, mode and membership postchecks.
