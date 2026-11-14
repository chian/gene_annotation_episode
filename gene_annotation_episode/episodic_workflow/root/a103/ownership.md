# A103 ownership

| Original module or symbols | Destination in this directory | Change | Role and callers |
| --- | --- | --- | --- |
| Top-level `a103_attachments`, `a103_channels`, `a103_credit`, `a103_detection`, `a103_investigation`, `a103_publication`, `a103_scoring`, `a103_work_report` | Same basenames | Moved | Genomic context evidence, detection, scoring, publication and report; `a103_investigation.A103ServiceFactory`, `scientific_process_episode.ScientificProcessEpisode`, `a103_tools.A103ToolRegistry` |
| Top-level `a103_hpc`, `a103_hpc_worker`, `a103_native_requests`, `a103_native_worker` | Same basenames | Moved | Native context requests, worker and returned result contracts; `a103_tools`, execution services |
| Top-level `a103_tools` | `a103_tools.py` | Moved | Private A103 tool registry; `tools.ToolRegistry` constructs `A103ToolRegistry` |
| Shared `scientific_process_episode.py` A103 branches | `a103_scientific_process_binding.py`, `a103_scientific_report_validation.py` | Split | Task projector, role/tool guards, guidance, received report facts, execution context and report validation; called by `scientific_process_episode.ScientificProcessEpisode` |
| Former mixed `literature_episode.py`: A103 source reading roles, assignment, catalog, custody, and execution | `literature_episode.py:LiteratureEpisode` | Split | A103-only literature source reading; `a103_investigation.py` constructs its private binding. The six copied mixed credit, sheet, selection, and work-report helpers were removed because this A103 reader does not commission those tasks. |
| `a103_detection.search_receipt` | `homology_search_receipt.py` | Moved beside A103 bindings; other axes retain independent copies | Authenticates the original completed phmmer result for A103 requests/tools; error codes and receipt checks remain unchanged |

Axis tests, fixtures and reusable test helpers are under `tests/`; shared
parent tests remain in the repository's top-level `tests/`.

## HPC episode ownership

| Original module or symbol | Private destination | Change | Role and callers |
| --- | --- | --- | --- |
| Top-level `hpc_episodes.py:HPCEpisodes` | `hpc_episode.py:HPCEpisode` | Copied and singularized | This axis's HPC parent binding; its workflow role declaration and the axis-specific execution factory descriptor. |
| Top-level `hpc_campaign.py`, `hpc_ledger.py`, `hpc_prediction.py`, `hpc_queue.py`, `hpc_allocation.py`, `hpc_monitoring.py`, `hpc_history.py`, `hpc_resource_prediction.py`, `hpc_commission_sources.py` | Same basenames in this directory | Copied | This axis's HPC planning, ledger, prediction, queue, monitoring, and saved commission behavior. |
| Top-level `execution_memory.py`, `execution_guidance.py`, `terminal_execution.py`, `terminal_execution_episodes.py` | Same basenames except `terminal_execution_episode.py` | Copied | Local execution memory and terminal action dependencies used by this axis's HPC binding. |

## Scientific process binding copy (2026-11-11)

| Original symbol | Destination | Axis | Role and caller | Change |
| --- | --- | --- | --- | --- |
| `scientific_process_episode.py::ScientificProcessEpisodes` | `scientific_process_episode.py::ScientificProcessEpisode` | A103 | Scientific process binding; `a103_investigation.A103ServiceFactory` calls `scientific_process_setup.prepare_scientific_binding`; saved reopening remains explicitly unresolved | Copied into a singular private binding with axis-constrained assignment, local credit, guidance, fact, report and decision routes; direct implementation dependencies now live in this axis. |

## Execution episode ownership

| Original module or symbol | Private destination | Change | Role and caller |
| --- | --- | --- | --- |
| Former mixed execution binding | execution_episode.py:ExecutionEpisode | Copied and narrowed to A103 BLAST/HMMER launch and result paths | A103 launch and result binding; a103_investigation.py uses its roles. |
| A101 homology execution helpers used by the original shared execution binding | a103_homology_execution.py, a103_execution_bindings.py, and local native_blast*, native_hmmer*, blast_*, hmmer_*, bvbrc_homology_returns.py copies | Copied into A103 | Homology result and receipt handling used when A103 needs sequence context; direct A101 imports removed from A103 source. |
| Top-level execution support | Local execution_contracts.py, launch_instructions.py, practical_execution_operations.py, practical_execution_records.py, practical_execution_state.py, practical_receipt_information.py, resource_records.py, local_file_capture_results.py, and native acquisition copies | Copied | A103 assignment, source capture, practical execution and received result handling. |

The private A103 execution class now contains its BLAST/HMMER launch and result
paths. The copied foreign operation branches were removed. It has not been
validated after the split.

## Private terminal execution binding

| Original module or symbol | Destination | Applicable axis | Episode role and caller | Change |
| --- | --- | --- | --- | --- |
| terminal_execution_episodes.py, TerminalExecutionEpisodes | terminal_execution_episode.py, TerminalExecutionEpisode | A103 | Local or HPC launch command execution; this axis's execution episode and practical service factory | Copied and made singular |
| terminal_scientific_evidence.py | terminal_scientific_evidence.py | A103 | Source custody for this axis's applicable native command profiles | Copied and narrowed |
| practical_yield.py | practical_yield.py | A103 | Private command-result progress estimate | Copied |

## 2026-11-11 monitor binding split

| Original module and symbol | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| episode_monitoring.py: MonitorEpisodes | monitor_episode.py: MonitorEpisode | This axis's monitor binding, commissioned by its execution service | Copied and made axis-private; generic progress infrastructure remains in episode_monitoring.py |

## 2026-11-11 assembled service ownership

| Original module or symbols | Destination | Role and caller | Change |
| --- | --- | --- | --- |
| assembled_service_setup.py: bind_assembled_services, _SavedProgressReader | assembled_service_setup.py | A103 service factory prepares its private scientific, literature, execution, monitor and resource bindings | Copied and selected private classes directly; no owner switch |
| resource_service_setup.py: bind_resource_services | resource_service_setup.py | A103 launch/results credit and adapter setup | Copied for A103; imports A103 resource adapter and binding |
| resource_episodes.py, resource_records.py, launch_instructions.py | resource_episode.py, resource_records.py, launch_instructions.py | A103 resource launch/results, assignment and instruction schemas | Copied for A103 |
| a101_homology_resource_adapter.py, a101_resource_implementation.py | a103_homology_resource_adapter.py, a103_resource_implementation.py | A103 native homology resource adapter and implementation pin | Copied for A103 source-context use |
| homology_*.py, homology_episode.py, homology_progress.py, resource_information.py, resource_operational_credit.py | Same descriptive basenames under A103 | A103 source-context homology and received operational information | Copied for A103; applicability still needs later validation |

| Original module group | Destination | Episode role and caller | Change |
| --- | --- | --- | --- |
| A101 homology source-reader dependencies: hmmer_*.py and phmmer_*.py | Same descriptive basenames under A103 | A103's local native homology measurement and grading workers | Copied for A103 source-context use; scientific applicability remains unvalidated |

## 2026-11-11 private capture dependencies

| Original module or symbols | A103 destination | Role and caller | Change |
| --- | --- | --- | --- |
| Generic exact-file portion of local_file_capture_results.py | local_file_capture_results.py | A103 execution results acquire and retain selected file bytes | Copied narrowed implementation; removed MACS2/LUMPY selectors, output-role resolution and receipt branches |
| Immutable control helpers formerly borrowed from genomic_overlap_result_receipts.py (local extraction reused from expression_nmf_receipt_control.py) | file_capture_receipt_control.py | Immutable saved capture controls; local_file_capture_results.py | Copied only filesystem/JSON control mechanics; no genomic-overlap or NMF implementation import |
| native_file_capture.py | native_file_capture.py | A103 selected exact-file acquisition | Copied with direct package infrastructure imports |
| received_native_file_inputs.py generic context/source/path/input helpers | received_native_file_inputs.py | A103 received-file custody | Copied; MACS2-specific input validation omitted |

A103 genomic context operations remain in a103_native_requests.py and its HPC worker/publication path. The independent genomic-overlap contract/driver and terminal-custody path are retained separately. Communication, Store/material and runtime receipts are now private. No tests, Python commands, parse/import validation or static validation were run.

## 2026-11-11 private practical execution scope

| Original module or symbols | A103 destination | Role and caller | Change |
| --- | --- | --- | --- |
| Applicable practical operations from the separately narrowed A101 snapshot | `practical_execution_operations.py` | A103 execution binding: BLAST/HMMER, preparation, masking, utility, database and generic job mechanics | Independent local implementation; removed copied RNA/Infernal, expression/NMF, and generic genomic-overlap execution branches |
| Applicable practical record schemas from the separately narrowed A101 snapshot | `practical_execution_records.py` | A103 execution requests and receipts | Independent local schemas and validation for the same applicable operations; foreign schemas removed |
| Native receipt filesystem custody helpers | `native_file_receipts.py` | A103 masking and utility attempt capture | Independent local helper replaces borrowing an Infernal driver for file custody |
| Generic executable catalog validation | `execution_inventory.py` | A103 local practical executable selection | Independent local copy |

All four files use A103-local implementation imports, with no sibling-axis fallback. A103 gene-context calculations remain in its native request/HPC worker path: locus binding, reference neighborhoods, neighborhood comparison, fusion, detection inventory and cooccurrence. The genomic-overlap driver and terminal command-custody path are retained independently. Original attempt provenance checks remain; these identify execution attempts rather than select an axis. Acquisition, local-job and communication/material/runtime implementations are now private; the HPC snapshot includes its private domain module. No Python, tests, parse/import checks or static validation were run.

## 2026-11-11 private component correspondence and source grading

| Original module or symbols | A103 destination | Role and caller | Change |
| --- | --- | --- | --- |
| `sequence_attribution.py`: digest, require, original_positions, sequence_link | `sequence_attribution.py` | `a103_attachments.py` resolves each actual component against its received protein reference | Independent local copy; unused scoped-distance API omitted; no root sequence behavior or A101 scoring import |
| `a101_scoring.py`: native map exception/require, coefficients, HMMER/BLAST comparison readers and schema dispatch | `native_correspondence_scoring.py` | Local sequence attribution consumes original residue maps and statistics | Extracted applicable map readers only; no A101 aggregate sheet, scope aggregation or axis credit logic |
| `tool_grading_artifacts.py` | `tool_grading_artifacts.py` | A103 attachment/publication, homology result/execution and BLAST result publication readers | Independent custody, retained-sheet readers and publication; all A103 production callers use local imports |
| `alignment_correspondence.py` | `alignment_correspondence.py` | Private tool-grading correspondence validation | Independent numerical correspondence implementation |
| `biopython_pairwise_grader.py` | `biopython_pairwise_grader.py` | Private retained pairwise correspondence validation | Independent implementation with local correspondence dependency |
| `a101/blast_pairwise_grader.py` and BLAST program-coordinate unit constants | `blast_pairwise_grader.py` | Private retained BLAST pairwise/database correspondence validation | Independent implementation and local constants; no sibling grader or BLAST-search import |

A103's actual locus/component selection, nucleotide placement, reverse correspondence handling, ambiguous residue handling and measurement-specific attachment semantics remain in its existing modules. The selected correspondence/source-reader path now uses private scientific behavior; domain canonical encoding and exception types are now private. Existing test imports in `tests/test_a103_context.py` and `tests/a103_native_fixture.py` still target the root sequence-attribution module and were not edited. Saved descriptor reopening remains a separate unresolved integration task. No tests, Python or static validation were run.

## 2026-11-11 private native snapshots and launch targets

| Original module or symbols | A103 destination | Role and caller | Change |
| --- | --- | --- | --- |
| Root `comparative_ops.py` | `comparative_ops.py` | Source neighborhood and focal arc used by `a103_scoring.py` | Independent A103 copy with private GenBank parser import |
| `acquisition.parse_genbank` | `genbank_parser.py` | Original GenBank coordinate, feature and annotation parsing | Extracted parser only; no acquisition/provider branches |
| `a103_hpc.py` frozen source inventory | Same file | Packages A103 native calculations for its HPC worker | Correct `episodic_workflow` package initializers; A103 scoring/detection/neighborhood/parser stored at their actual private package paths; removed root acquisition/public-configuration/scientific-neighborhood sources |
| Native BLAST database and standard-database result-worker implementation inventories | Corresponding private result-worker files | Original parser/calculator source identity | Local module identities and full package-initializer chain replace A101/root scientific-module selection; database worker's own identity now A103 |
| Native BLAST, masking, utility, HMMER and HMMER-preparation local launch argv | Corresponding five `*_local.py` files | Native worker launch and reopened HMMER command identity | Target the existing A103 private drivers |

The A103 context HPC worker and local context worker already target the correct private package; their scientific imports now reach the private neighborhood/parser files. Root `domain.py` remains explicitly captured for existing canonical encoding and exception/schema infrastructure. HPC custody/commission services remain root integration dependencies.

Separate split still required for the database result-worker dependency inventory: `native_blast_standard_database_calculators.py`, `native_blast_standard_database_metadata.py`, `native_blast_database_metadata.py`, `native_blast_database_population_metadata.py`, `blast_database_population_associations.py`, `blast_report_collection.py`, `blast_grading_inputs.py`, `blast_program_context.py`, `blast_fasta_record_identity.py`, `blast_sequence_database.py`, `blast_database_grader.py`, `blast_profile_inputs.py`, `blast_profile_calculators.py`, `blast_pssm_inputs.py`, `blast_pssm_calculators.py`, `blast_pssm_master_inputs.py`, `blast_iteration_inputs.py`, `blast_iteration_calculators.py`, `blast_vdb_inputs.py`, `blast_vdb_calculators.py` and `blast_search.py` are not present in A103. Conditional database-result dependencies `native_blast_database_convergence.py`, `blast_native_iteration_records.py`, `blast_vdb_function_inputs.py`, `blast_vdb_function_calculators.py` and `native_blast_vdb_function_metadata.py` are also absent. The inventory now requires these local files directly; it does not load A101 as a substitute.

Corrected the preceding residue-map extraction to include its private `NativeCorrespondenceUnavailable` class and `_require`, preserving original error details. No HPC job, Python, tests or static validation ran; snapshot execution and database integration are not claimed validated.

## 2026-11-11 standalone A103 tool registry and source clients

`a103_tools.A103ToolRegistry` now derives only from A103's own `tools.ToolRegistry`. Its copied implementation contains the applicable state/source/material/sequence inspection, reading, alignment-site inspection, BLAST/HMMER result publication, source acquisition and ordinary operation custody methods. No root/sibling ToolRegistry inheritance or forwarding remains. Root protein-structure, RNA/Infernal, assay, flux-balance, molecular-operation configuration and owner-selection branches are absent. Experimental-database acquisition/assay-record catalog branches were not carried from the A101 snapshot. The two outer A103 attribution methods no longer route by axis identity.

| Original implementation | A103 destination | Preserved applicable work |
| --- | --- | --- |
| Narrowed private A101 ToolRegistry snapshot, derived from root `tools.py` | `tools.py`, wired by `a103_tools.py` | Original generic execution/publication methods, durable outcomes and action context; A103's own genomic source additions; configuration record is local |
| Root/A101 explicit public clients and source types | `acquisition.py` | Private SourceSnapshot, HTTP capture, NCBI/UniProt/BLAST/PMC/literature access, exact original sources; added own STRING/UCSC/Ensembl requests; bounded skill observer imports this private module |
| STRING subset of `molecular_provider_acquisition.py` | `string_acquisition.py` | Selected endpoint/taxon/request, transfer and byte identity, native channel qualifications, retained value, acquisition receipt and source publication; no KEGG/Reactome/QuickGO/PubChem/HPA branches |
| Genomic public source contracts and hosts | `ucsc_acquisition.py`, `ensembl_acquisition.py`, `ensembl_acquisition_host.py`, `genomic_source_catalog.py` | Explicit genomic queries, original discovery dependencies, exact DNA intervals and source metadata, original saved-result handling |
| Generic original-action portion of molecular invocation and source-receipt metadata | `genomic_source_invocation.py`, `genomic_source_receipts.py` | Original selected-action identity and retained source/file custody for Ensembl/STRING/UCSC/NCBI/minhash; no foreign assay/structure/capture/FBA branches |
| Strict native JSON parse and acquisition receipt helpers | `source_json.py`, `data_acquisition_receipts.py` | Independent source parsing and four-field acquisition receipts |
| Root legacy source-based reference neighborhood operation | `tools.py` with `genomic_source_catalog.py` and private `comparative_ops.py` | Legacy exact-source neighborhood remains beside A103's received-locus operation |

Independent registry/helper snapshot modules (existing A103 files were retained instead of overwritten): `tools.py`, `acquisition.py`, `provider_jobs.py`, `api_error_feedback.py`, `sequence_ops.py`, `sequence_mapping.py`, `sequence_views.py`, `library_targets.py`, `materials_packing.py`, `read_mapping.py`, `source_locations.py`, `document_tools.py`, `spreadsheet_tools.py`, `spreadsheet_worker.py`, `literature_assets.py`, `image_evidence.py`, `literature_sequence_discovery.py`, `source_sequences.py`, `ncbi_entrez_tools.py`, `ncbi_entrez_acquisition.py`, `biopython_pairwise_grader.py`, `alignment_site_native.py`, `alignment_site_inputs.py`, `alignment_site_calculators.py`, `sequence_composition_grader.py`, `sequence_composition_counts.py`, `sequence_extraction_grader.py`, `sequence_translation_grader.py`, `minimap2_grader.py`, `minimap2_grading_inputs.py`, `api_uniprot.py`, `uniprot_native.py`, `uniprot_native_contracts.py`, `uniprot_publication.py`, `public_configuration.py`, `sequence_worker.py`, `uniprot_service_support.py`, `native_json.py`, `native_timing_information.py`.

Additional missing local sequence/homology dependencies copied for the registry's actual private imports: `blast_graders.py`, `blast_search.py`, `native_blast_hsp_views.py`, `blast_hsp_site_inputs.py`, `blast_hsp_site_calculators.py`, `blast_grading_inputs.py`, `blast_database_grader.py`, `native_hmmer_result_publication.py`, `native_blast_standard_database_metadata.py`, `native_blast_standard_database_calculators.py`, `native_blast_database_convergence.py`, `blast_pairwise_results.py`, `native_blast_result_publication.py`, `native_blast_result_worker.py`, `blast_report_collection.py`, `blast_fasta_record_identity.py`, `blast_database_population_associations.py`, `blast_program_context.py`, `native_blast_database_metadata.py`, `blast_pssm_inputs.py`, `blast_pssm_master_inputs.py`, `blast_sequence_database.py`, `native_blast_database_population_metadata.py`, `blast_pssm_calculators.py`, `blast_vdb_function_calculators.py`, `blast_vdb_function_inputs.py`, `native_blast_vdb_function_metadata.py`, `blast_iteration_calculators.py`, `blast_profile_calculators.py`, `blast_vdb_calculators.py`, `blast_native_iteration_records.py`, `blast_iteration_inputs.py`, `blast_profile_inputs.py`, `blast_vdb_inputs.py`. This supplies the database metadata/calculation files listed as absent in the preceding entry; it does not establish database execution validation. Copies are independent A103 files, with literal Python worker targets adapted to this package. Existing A103 practical/capture/correspondence implementations were preserved.

Residual integration: Store/material containers and parsing entrypoints, domain schemas/exception types, local resource/job execution, ordinary execution statistics, action/receipt infrastructure and the shared AcquisitionError type remain package infrastructure imports. Those are not redirected through a root ToolRegistry. Existing test fixtures and root workflow composition still require separate integration with the private registry/client types; no compatibility fallback was introduced. No Python, tests, static validation or workflow execution ran.

The private `_source` metadata publisher was narrowed to this registry's actually enabled special source providers; copied unavailable-provider exceptions were removed. Native source versions and original source custody remain unchanged for applicable acquisitions.

### Private A103 service binding (2026-11-11)

| Original behavior | Private destination | A103 callers and preserved behavior |
|---|---|---|
| Applicable WorkflowServices ports | `episode_services.py` | A103 tool/source dispatch, original record and semantic receipt resolution, assignment/credit, progress access, saved/closed scientific requests and original action outcomes. No root WorkflowServices inheritance or forwarding. |
| Registry construction port | `tools.py::ToolRegistry.workflow_services` | Constructs this directory's private WorkflowServices directly. |
| Scientific invocation provenance | `scientific_process_provenance.py` | Original saved and parent preparations, received/frozen process results and lineage. Separate scientific_preparation/scientific_parent_preparation ports replace the owner selector; original preparation outputs use invocation_ref and selection. create_scientific_provenance constructs the private class. |
| Process records, reports, tool contracts and support descriptions | `scientific_process_records.py`, `scientific_process_reports.py`, `episode_reports.py`, `resource_tool_information.py`, `tool_information.py`, `tool_schema_validation.py`, `scientific_support_metadata.py` | Private copies preserve original schemas, process-result projection, actual callable contracts and support metadata. A103 imports now bind locally. |
| BVBRC received metadata/file reader | `molecular_sequence_input_bindings.py`, `molecular_sequence_input_contracts.py`, `bvbrc_appservice_custody.py`, `episode_return_records.py`, `episode_receipts.py` | Preserves the actual read_received_molecular_input callback consumed by BVBRC metadata acquisition, current commission authentication, semantic receipts, admitted file identity and original action matching. The service resolves A103 genomic sources using its existing private genomic_source_receipts implementation. |
| Source representation and immutable input byte selection | `source_bytes.py`, `received_file_bytes.py` | Private source representation selection and the directly required confined immutable byte reader. The byte reader preserves existing failure codes without copying an unrelated execution family. Native BLAST utility source custody uses A103's private contracts/results. Ordinary genomic-source primary-body policies remain in the actual private ToolRegistry source reader. |
| Scientific-process binding | `scientific_process_episode.py` | Keeps A103 context_fact_sources, received_report_facts, received_execution_context, validate_axis_report and original task projector. Removes copied structure alignment, site/restriction, molecular assay/ITC and protein-structure fact catalogs, return/reference adapters and validators. Revision readers are explicitly bound at the three original callsites. |
| Monitor caller cleanup | `monitor_episode.py` | Removes copied MACS2 task lookup/decoration; original target/dependency/progress operations remain. |

No stubs or foreign execution families were added. The A103 context tool dispatch still passes original received operands to context.*, reference.neighborhood, result.blast.hsp and source.locate. Existing native gene-context execution, homology input/result custody, credit, report return and invalid-action behavior remain in their private implementations.

Remaining integration boundaries: root runtime must construct services through the registry port and provenance through create_scientific_provenance, and remove its own foreign mixed callbacks. Workflow credit/progress providers, communication/domain/BindingContext types, evidence-axis contracts/instructions/libraries and numerical controllers remain broader dependencies. The copied AppService custody reader still uses existing root contract-information/transport normalization, execution contracts, launch-instruction records and AppService schema validation; the API execution implementation remains an existing external constructor dependency. These boundaries are recorded, not claimed complete.

No Python, tests, static validation, imports or workflow jobs were run for this extraction.

## Private scientific library and prompt assets — 2026-11-11

A103 scientific/tool library construction and evidence-entry readers are private. A103 constructors and scientific binding import these local classes and helpers. Tool information uses only the actual supplied callable and resource catalogs; the copied global API-catalog injection was removed. Existing gene-context and homology/native execution paths still supply their own declared operations.

Private knowledge and launch manifests select operations declared by A103 tools/resource adapters and their native BLAST/HMMER contracts. Their referenced markdown is copied locally, including gene-context and applicable homology instruction assets. Execution recipe assets are local. Root runtime/service construction, ToolKnowledge/LaunchInstructions and retriever wiring are handled separately. No tests, static checks or Python execution were run.

2026-11-11 runtime binding: this axis's tools.workflow_services now supplies its private service to runtime. Provenance, current tool invocation, instruction libraries, tool retrieval and semantic receipts are constructed through that service. Original runtime investigation/action-delivery and decision-exchange instructions are independent runtime_prompt.py/decision_protocol_prompt.py copies. Original tool_knowledge.py, launch_instructions.py, scientific_tool_retrieval.py, boundary_validation.py and episode_receipts.py have private implementations and direct callers. Imports of already-present local helpers were rebound directly. Message parsing, Store/domain/communication and numerical/execution infrastructure were subsequently copied privately; no execution validation is claimed.

## Private parsing, runtime and decisions — 2026-11-11

A103 now has independent domain, communication/form-reference validation, contract-information/schema readers, runtime, binding/admission, journal, composition, decision-context/exchange/history and original commission helpers. Production Workflow and recorded-frame callers import local implementations. Return records, receipt/admission/completion, replay and acquisition use A103's local BindingContext and private parsing/error types without forwarding to shared runtime. Original canonical identities, source schemas and receipt relationships are preserved. Existing local implementations supply runtime imports where available.

Gene-context scoring and original attribution hooks remain connected, alongside homology/native BLAST/HMMER, file capture, UniProt, BV-BRC data and MinHash source/result readers. Private AppService declarations expose homology and support receipts; copied foreign application return catalogs are removed. The private parser excludes structural, assay, restriction, NMF, FBA and other foreign scientific return branches. Private shared-information presentation includes A103 and generic saved grading views only.

The later private Store/API/native passes below supersede the infrastructure gaps recorded at this stage. Saved reconstruction remains unresolved. No tests, static validation or Python execution were performed.

### Private A103 Store, material and execution-type path (2026-11-11)

Store, materials, sequence/text/GenBank intake, gzip decoding, context masks and evidence geometry are now independent local implementations. Existing private sequence mapping, PAF parsing, library targets, packed materials and BLAST publication validators retain their original input-coordinate, record and artifact semantics. Gene-context source claims, original findings, replacement scope and validity now use local scientific_findings, finding_validity and investigation_progress implementations. Production Store/material callers import local code directly; no new factory or alternate gene-context binding was introduced. Foreign Enrichr and molecular-assay artifact dispatch was removed from the private materials reader.

The active Store.put/commit_reasoning and runtime keyword is account_invocation. The original run/episode tuple is unchanged. Historical serialized digest fields 'owner' in interpretation_account_key and 'account_owner' in acquisition signatures are deliberately retained to keep saved record identities, revisions and replay signatures unchanged. They are historical hash labels only, not API arguments or axis selectors.

A103 has private numerical continuation and vendor estimator source/license/manifests, timing, execution statistics, expectations, resource estimates and native recording. Its actual HomologyStatistics/NativeStatistics and HomologyJobs paths remain intact with direct local references; no A107-specific narrowing was used. Private ordinary_execution, native_lifecycle, local_jobs, local_resources, atomic receipt writer and local worker keep exact native statistics/policy types compatible. Original formulas, source schemas, resource bounds and return semantics are retained. Defaults are available beside the copied local readers. Worker import roots and execution-memory runs/ defaults resolve to the repository after relocation.

The previously missing composition_information module is now a private copy using A103's decision history, tool knowledge, launch instructions and scientific library.

Remaining boundaries include root workflow resource enforcement/native event infrastructure, waiting, service setup and external method_loop/scientific libraries. This is source dependency separation, not a claim that all A103 infrastructure imports are closed. No tests, Python, static validation, imports or workflow jobs were run.


## 2026-11-11 private waiting and episode-loop dependencies

- `waiting.py` → `a103/waiting.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `wait_estimation_inputs.py` → `a103/wait_estimation_inputs.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `local_return_history.py` → `a103/local_return_history.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `completion_evidence.py` → `a103/completion_evidence.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `inprocess_waiting.py` → `a103/inprocess_waiting.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `episode_monitoring.py` → `a103/episode_monitoring.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `progress_records.py` → `a103/progress_records.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `episode_source_failure.py` → `a103/episode_source_failure.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `episode_input_versions.py` → `a103/episode_input_versions.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `native_events.py` → `a103/native_events.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `native_event_information.py` → `a103/native_event_information.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.
- `workflow_budget.py` → `a103/workflow_budget.py`: independent applicable implementation for A103 runtime/frame/native progress callers; existing private copies retained.

A103 retains its actual homology job status/event reader, bound to its private HomologyJobs and resource schemas. The vendored `method_loop/` package and license/source manifests are copied to `a103/library/method_loop/`; production imports and durable child-worker commands bind directly to that private package. Original continuation, native observations and return identities are preserved. Provider/prompt/reconstruction and other helper separation remain unfinished. No tests or static checks were run.

2026-11-11 acquisition class placement correction: the earlier local `acquisition.py` self-import was replaced with its independent original `AcquisitionError` class, preserving the original fields and RuntimeError base. No execution validation was run.

### Private A103 provider and gene-context presentation (2026-11-11)

Providers/authentication, scientific-process and receiver text, API-launch/HPC/monitor prompts, native HMMER/preparation presentation, alignment presentation, completed-action reports and shared-information results now have independent implementations and direct A103 callers. Existing local defaults and the copied private workflow-resource reader supply their original configuration/transport behavior. Original model frames, task instructions, selected source bodies, API failures, native timing and parent return forms retain their meanings.

The work report invokes A103's original a103_work_report directly, without a multi-axis registry. It preserves exact locus/neighborhood/recurrence/fusion/co-occurrence/detection/contrast quantities, native STRING channels, measurement-specific attributions and original action credit. A103's own registered legacy report conversion is retained. Steering includes its gene-context sheet, native genomic outcomes, tool attachments, source contributions and received BV-BRC values. Sequence/genome alignment presentation uses private copies of the original reference codecs; the exact REFERENCE_KINDS and decoding behavior are preserved. HMMER/homology, selected API execution and HPC/monitor views remain.

Foreign RNA/NMF, chemical/assay, phylogeny, structural and MACS2 render dispatch was removed. No scientific calculator, custody rule, source value or score was substituted. Presentation value_source/credit_episode replace unused owner metadata; the original saved scientific records remain untouched. Additional directly required private helper modules: none.

Broader native service/setup and iterator dependency work remains separately recorded. Acquisition modules were left untouched for root's concurrent correction. No tests, Python, static validation, imports or workflow jobs were run.

### Private A103 construction, API custody and native monitoring (2026-11-11)

Application execution binding, independent reconstruction, tool construction, execution planning/progress, scientific setup and the execution-service factory now have independent A103 implementations. Runtime, A103ServiceFactory, assembled setup and HPC readers bind them directly. Saved reconstruction still reports its existing unavailable private reopen paths; no new reopening policy was added. The implementation digest covers A103's private package, and the controller descriptor names A103's numerical implementation.

APIServiceExecution, selected-effect records/calls and BV-BRC AppService/Data/MinHash hosts now use independent A103 implementations. HMMER, NCBI BLAST, UniProt and BV-BRC retain their native handoff, selected-action, acquired-source, frozen return and credit semantics. AppService scientific dispatch binds the private Homology adapter only; its original parsers, scoring, subject qualification, schema JSON and Homology definition assets are private. Implementation hashing reads private dependency files without a root fallback. Foreign phylogeny, chemical, RNA, proteome, intervention and other AppService return adapters were removed, including copied catalog, completion and partial-publication switches.

Monitoring retains actual homology/BLAST/HMMER, genomic-overlap, API and HPC paths. Unrelated RNA/NMF, structure, assay, flux-balance, MACS2, chromatin and LUMPY branches were removed. Terminal command custody retains A103's genomic-overlap profile and removes the foreign structural/flux compact-return cases. Source worker primitives were extracted independently into native_record_identity/native_worker_files/native_driver_runtime; HMMER and BLAST callers bind the applicable private primitives. Native database terminal custody, alignment-site and HMMER grading dependencies, HPC plan/result readers and component-assessment helpers are private.

Active AppService original_job_context method/parameter names and original_context variables replace generic owner identifiers. Historical OriginalJobOwner/original_job_owner schema and receipt fields, and historical hashed owner labels, remain byte-compatible record identities; they do not select an axis. Existing unfinished saved-binding reopening remains unfinished. No tests, Python, static validation, imports or jobs were run; file separation does not establish workflow execution validation.

2026-11-11: root `execution_input_versions.py` ordinary immutable-input version/content path has an independent private `a103/execution_input_versions.py`, called by `ExecutionEpisode._versions`. No ATAC/FBA/NMF/structure exceptions or common-reader fallback are included. Preserves original received-scope, revision and byte-hash checks.

2026-11-11 numerical-source retirement: this axis's numerical provenance names
its own private vendor source and MIT license. Its private numerical/timing
implementations and source manifest retain the original estimator, receipt-time
semantics and formulas. Former shared numerical/timing implementation paths were
retired; no tests or execution were run.

2026-11-11: native BLAST implementation inventories and the separate publication subprocess now load only this axis's qualified private modules, including its own `domain` and alignment correspondence helpers. Removed the old name-prefix switch that selected top-level helpers. The embedded subprocess uses an absolute private worker import; native byte/scoring logic is unchanged.


2026-11-11: Preserved the actual private PracticalState credit callback by copying original `practical_execution_credit.py` directly into this directory. It uses this directory’s assignment validator and preserves original satisfied-requirement keys, baseline, signed losses and operational receipt semantics. No shared import, alternative scorer or validation run was introduced.

2026-11-11: The actual registered genomic-overlap execution information retains its original operation descriptions and now names A103’s own driver/capture/parser/preparation and practical-observation implementations in descriptor metadata. Its scientific branch remains present.

2026-11-11 API-original retirement: original mixed API/AppService behavioral
modules were removed after private callers were bound. Applicable private
publication predicates and parser-module descriptions were narrowed, with exact
original custody and outcome semantics retained. Full original-to-private mapping
is recorded in root/ownership.md. No tests or execution were run.

2026-11-11: removed dormant foreign native target-marker helpers copied by the earlier broad dependency pass: `native_infernal_acquisition.py`, `native_infernal_preparation_acquisition.py`, `native_protein_structure_acquisition.py`, `native_rna_structure_acquisition.py`. No current private production caller imports or names these helpers; this axis retains only its actual native execution paths. Original applicable implementations remain in the axes that use them.

## 2026-11-11 — Additional original-module placements

This supplement records original modules not named individually above. It maps their complete applicable module contents, including methods and constants; previous symbol-specific narrowing notes remain authoritative. Callers listed here are direct private imports or qualified worker module references, not execution receipts. It does not claim runtime validation.

| Original module/symbols | Destination | Current role/caller | Change |
|---|---|---|---|
| `gene_annotation_episode/_local_job_worker.py` (module contents) | `a103/_local_job_worker.py` | Private dependency used by `homology_jobs.py`, `homology_results.py`, `local_jobs.py`, `native_blast_driver.py`, `native_events.py`, `native_hmmer_driver.py`, `native_lifecycle.py`, `native_worker_files.py` | Copied/split; private implementation |
| `gene_annotation_episode/a103_channels.py` (module contents) | `a103/a103_channels.py` | Private dependency used by `a103_attachments.py`, `a103_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a103_credit.py` (module contents) | `a103/a103_credit.py` | Private dependency used by `a103_investigation.py`, `a103_scientific_process_binding.py` | Copied/split; private implementation |
| `gene_annotation_episode/a103_detection.py` (module contents) | `a103/a103_detection.py` | Private dependency used by `a103_scoring.py` | Copied/split; private implementation |
| `gene_annotation_episode/a103_hpc_worker.py` (module contents) | `a103/a103_hpc_worker.py` | Private dependency used by `a103_hpc.py` | Copied/split; private implementation |
| `gene_annotation_episode/a103_native_worker.py` (module contents) | `a103/a103_native_worker.py` | Private dependency used by `a103_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a103_publication.py` (module contents) | `a103/a103_publication.py` | Private dependency used by `a103_attachments.py`, `a103_channels.py`, `a103_credit.py`, `a103_hpc.py`, `a103_investigation.py`, `a103_native_requests.py`, `a103_tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/a103_work_report.py` (module contents) | `a103/a103_work_report.py` | Private dependency used by `episode_work_report.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_result_presentation.py` (module contents) | `a103/alignment_result_presentation.py` | Private dependency used by `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/alignment_site_mapping.py` (module contents) | `a103/alignment_site_mapping.py` | Private dependency used by `alignment_site_inputs.py`, `blast_hsp_site_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_blast.py` (module contents) | `a103/api_blast.py` | Private dependency used by `api_service_execution.py`, `api_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_bvbrc.py` (module contents) | `a103/api_bvbrc.py` | Private dependency used by `api_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_bvbrc_appservice.py` (module contents) | `a103/api_bvbrc_appservice.py` | Private dependency used by `api_services.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_bvbrc_minhash.py` (module contents) | `a103/api_bvbrc_minhash.py` | Private dependency used by `api_services.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_execution.py` (module contents) | `a103/api_execution.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_selected_call.py` (module contents) | `a103/api_selected_call.py` | Private dependency used by `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_selected_effects.py` (module contents) | `a103/api_selected_effects.py` | Private dependency used by `api_service_execution.py`, `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_service_execution.py` (module contents) | `a103/api_service_execution.py` | Private dependency used by `bvbrc_appservice_host.py`, `bvbrc_appservice_publication.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/api_services.py` (module contents) | `a103/api_services.py` | Private dependency used by `api_blast.py`, `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py`, `api_service_execution.py`, `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/application_execution_binding.py` (module contents) | `a103/application_execution_binding.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/blast_pairwise_result_views.py` (module contents) | `a103/blast_pairwise_result_views.py` | Private dependency used by `execution_episode.py`, `execution_progress.py`, `native_blast_hsp_views.py`, `native_blast_result_publication.py`, `native_blast_result_worker.py`, `native_blast_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/blast_result_views.py` (module contents) | `a103/blast_result_views.py` | Private dependency used by `alignment_site_native.py`, `api_service_execution.py`, `execution_episode.py`, `execution_progress.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/blast_utility_result_views.py` (module contents) | `a103/blast_utility_result_views.py` | Private dependency used by `a103_execution_bindings.py`, `communication.py`, `execution_episode.py`, `execution_progress.py`, `native_blast_utility_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_analysis_protocol.py` (module contents) | `a103/bvbrc_analysis_protocol.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py`, `bvbrc_analysis_transport.py`, `bvbrc_application_definitions.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_readers.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_minhash_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_analysis_transport.py` (module contents) | `a103/bvbrc_analysis_transport.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_bvbrc_minhash.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_application_definitions.py` (module contents) | `a103/bvbrc_application_definitions.py` | Private dependency used by `api_bvbrc_appservice.py`, `bvbrc_appservice_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_adapters.py` (module contents) | `a103/bvbrc_appservice_adapters.py` | Private dependency used by `api_bvbrc_appservice.py`, `bvbrc_appservice_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_bundle_values.py` (module contents) | `a103/bvbrc_appservice_bundle_values.py` | Private dependency used by `bvbrc_appservice_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_contracts.py` (module contents) | `a103/bvbrc_appservice_contracts.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_selected_call.py`, `api_selected_effects.py`, `api_services.py`, `bvbrc_appservice_bundle_values.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_monitor.py`, `bvbrc_appservice_publication.py`, `bvbrc_appservice_readers.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_appservice_records.py`, `bvbrc_appservice_tool_info.py`, `bvbrc_homology_bundle_adapter.py`, `bvbrc_homology_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_host.py` (module contents) | `a103/bvbrc_appservice_host.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_inputs.py` (module contents) | `a103/bvbrc_appservice_inputs.py` | Private dependency used by `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_monitor.py` (module contents) | `a103/bvbrc_appservice_monitor.py` | Private dependency used by `api_service_execution.py`, `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_publication.py` (module contents) | `a103/bvbrc_appservice_publication.py` | Private dependency used by `bvbrc_appservice_host.py`, `bvbrc_homology_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_readers.py` (module contents) | `a103/bvbrc_appservice_readers.py` | Private dependency used by `api_bvbrc_appservice.py`, `bvbrc_appservice_bundle_values.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_receipt_values.py`, `bvbrc_appservice_records.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_receipt_values.py` (module contents) | `a103/bvbrc_appservice_receipt_values.py` | Private dependency used by `bvbrc_appservice_host.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_records.py` (module contents) | `a103/bvbrc_appservice_records.py` | Private dependency used by `api_service_execution.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_appservice_tool_info.py` (module contents) | `a103/bvbrc_appservice_tool_info.py` | Private dependency used by `api_bvbrc_appservice.py`, `api_service_execution.py`, `bvbrc_appservice_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_calculators.py` (module contents) | `a103/bvbrc_data_calculators.py` | Private dependency used by `bvbrc_data_publication.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_feature_sequences.py` (module contents) | `a103/bvbrc_data_feature_sequences.py` | Private dependency used by `bvbrc_data_publication.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_fields.py` (module contents) | `a103/bvbrc_data_fields.py` | Private dependency used by `bvbrc_data_feature_sequences.py`, `bvbrc_data_molecular.py`, `bvbrc_data_publication.py`, `bvbrc_data_query.py`, `bvbrc_data_readers.py`, `bvbrc_data_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_host.py` (module contents) | `a103/bvbrc_data_host.py` | Private dependency used by `api_service_execution.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_molecular.py` (module contents) | `a103/bvbrc_data_molecular.py` | Private dependency used by `bvbrc_data_publication.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_publication.py` (module contents) | `a103/bvbrc_data_publication.py` | Private dependency used by `api_bvbrc.py`, `api_service_execution.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_query.py` (module contents) | `a103/bvbrc_data_query.py` | Private dependency used by `api_bvbrc.py`, `bvbrc_data_publication.py`, `bvbrc_data_readers.py`, `bvbrc_data_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_readers.py` (module contents) | `a103/bvbrc_data_readers.py` | Private dependency used by `api_bvbrc.py`, `bvbrc_data_calculators.py`, `bvbrc_data_publication.py`, `bvbrc_data_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_schema.py` (module contents) | `a103/bvbrc_data_schema.py` | Private dependency used by `api_bvbrc.py`, `api_service_execution.py`, `bvbrc_data_calculators.py`, `bvbrc_data_feature_sequences.py`, `bvbrc_data_host.py`, `bvbrc_data_molecular.py`, `bvbrc_data_publication.py`, `bvbrc_data_readers.py`, `bvbrc_data_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_data_views.py` (module contents) | `a103/bvbrc_data_views.py` | Private dependency used by `api_bvbrc.py`, `bvbrc_data_host.py`, `bvbrc_data_publication.py`, `execution_episode.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_bundle_adapter.py` (module contents) | `a103/bvbrc_homology_bundle_adapter.py` | Private dependency used by `bvbrc_appservice_adapters.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_grader.py` (module contents) | `a103/bvbrc_homology_grader.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_inputs.py` (module contents) | `a103/bvbrc_homology_inputs.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py`, `bvbrc_homology_grader.py`, `bvbrc_homology_metadata.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_metadata.py` (module contents) | `a103/bvbrc_homology_metadata.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_homology_subject_binding.py` (module contents) | `a103/bvbrc_homology_subject_binding.py` | Private dependency used by `bvbrc_homology_bundle_adapter.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_contracts.py` (module contents) | `a103/bvbrc_minhash_contracts.py` | Private dependency used by `api_bvbrc_minhash.py`, `api_service_execution.py`, `bvbrc_minhash_host.py`, `bvbrc_minhash_views.py`, `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_grader.py` (module contents) | `a103/bvbrc_minhash_grader.py` | Private dependency used by `api_bvbrc_minhash.py`, `bvbrc_minhash_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_host.py` (module contents) | `a103/bvbrc_minhash_host.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/bvbrc_minhash_views.py` (module contents) | `a103/bvbrc_minhash_views.py` | Private dependency used by `bvbrc_minhash_host.py`, `communication.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/communication.py` (module contents) | `a103/communication.py` | Private dependency used by `a103_homology_execution.py`, `a103_homology_resource_adapter.py`, `a103_hpc.py`, `a103_investigation.py`, `a103_scientific_process_binding.py`, `a103_scientific_report_validation.py`, `a103_tools.py`, `alignment_site_native.py`, `api_execution.py`, `api_selected_call.py`, `api_service_execution.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_host.py`, `bvbrc_appservice_inputs.py`, `bvbrc_appservice_monitor.py`, `bvbrc_appservice_publication.py`, `bvbrc_appservice_records.py`, `bvbrc_data_host.py`, `bvbrc_data_views.py`, `bvbrc_homology_returns.py`, `bvbrc_minhash_host.py`, `ensembl_acquisition_host.py`, `episode_admission.py`, `episode_contract_information.py`, `episode_monitoring.py`, `episode_return_records.py`, `episode_services.py`, `execution_contracts.py`, `execution_episode.py`, `execution_input_versions.py`, `execution_progress.py`, `execution_service_setup.py`, `genomic_source_invocation.py`, `homology_episode.py`, `homology_jobs.py`, `homology_progress.py`, `hpc_episode.py`, `hpc_result_receipts.py`, `literature_episode.py`, `local_file_capture_results.py`, `local_return_history.py`, `molecular_sequence_input_bindings.py`, `monitor_episode.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_masking_results.py`, `native_blast_results.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_utility_results.py`, `native_event_information.py`, `native_hmmer_preparation_results.py`, `native_hmmer_results.py`, `native_profile_presentation.py`, `native_timing_information.py`, `pending_assignment.py`, `practical_receipt_information.py`, `progress_records.py`, `received_native_file_inputs.py`, `resource_episode.py`, `resource_estimation.py`, `resource_information.py`, `resource_operational_credit.py`, `resource_records.py`, `resource_tool_information.py`, `runtime.py`, `scientific_process_episode.py`, `scientific_process_provenance.py`, `scientific_process_reports.py`, `shared_information.py`, `terminal_execution_episode.py`, `terminal_scientific_evidence.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/component_assessment_dependencies.py` (module contents) | `a103/component_assessment_dependencies.py` | Private dependency used by `a103_credit.py` | Copied/split; private implementation |
| `gene_annotation_episode/composition_information.py` (module contents) | `a103/composition_information.py` | Private dependency used by `a103_investigation.py`, `literature_episode.py`, `resource_episode.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/context_masks.py` (module contents) | `a103/context_masks.py` | Private dependency used by `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_context.py` (module contents) | `a103/decision_context.py` | Private dependency used by `providers.py`, `runtime.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_exchanges.py` (module contents) | `a103/decision_exchanges.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/decision_history.py` (module contents) | `a103/decision_history.py` | Private dependency used by `composition_information.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/default_scientific_binding.py` (module contents) | `a103/default_scientific_binding.py` | Private dependency used by `application_execution_binding.py`, `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_admission.py` (module contents) | `a103/episode_admission.py` | Private dependency used by `episode_completion.py`, `local_return_history.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_application_services.py` (module contents) | `a103/episode_application_services.py` | Private dependency used by `a103_investigation.py`, `assembled_service_setup.py`, `execution_service_setup.py`, `independent_execution.py`, `resource_service_setup.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_bindings.py` (module contents) | `a103/episode_bindings.py` | Private dependency used by `a103_homology_resource_adapter.py`, `api_execution.py`, `api_service_execution.py`, `bvbrc_appservice_custody.py`, `bvbrc_appservice_monitor.py`, `episode_composition.py`, `episode_monitoring.py`, `episode_progress_credit.py`, `episode_return_records.py`, `episode_services.py`, `execution_episode.py`, `execution_progress.py`, `form_reference_validation.py`, `genomic_source_receipts.py`, `hpc_episode.py`, `independent_execution.py`, `literature_episode.py`, `local_file_capture_results.py`, `molecular_sequence_input_bindings.py`, `monitor_episode.py`, `practical_receipt_information.py`, `received_native_file_inputs.py`, `resource_episode.py`, `resource_information.py`, `resource_operational_credit.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_commissions.py` (module contents) | `a103/episode_commissions.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_completion.py` (module contents) | `a103/episode_completion.py` | Private dependency used by `completion_evidence.py`, `decision_history.py`, `episode_admission.py`, `inprocess_replay.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_composition.py` (module contents) | `a103/episode_composition.py` | Private dependency used by `independent_execution.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_contract_information.py` (module contents) | `a103/episode_contract_information.py` | Private dependency used by `bvbrc_appservice_custody.py`, `episode_return_records.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_journal.py` (module contents) | `a103/episode_journal.py` | Private dependency used by `bvbrc_appservice_custody.py`, `completion_evidence.py`, `decision_exchanges.py`, `decision_history.py`, `episode_admission.py`, `episode_commissions.py`, `episode_completion.py`, `episode_report_acquisition.py`, `inprocess_replay.py`, `resource_service_setup.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_progress_credit.py` (module contents) | `a103/episode_progress_credit.py` | Private dependency used by `assembled_service_setup.py`, `execution_service_setup.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_report_acquisition.py` (module contents) | `a103/episode_report_acquisition.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/episode_work_report.py` (module contents) | `a103/episode_work_report.py` | Private dependency used by `execution_prompt.py`, `hpc_prompt.py`, `monitor_prompt.py`, `runtime.py`, `scientific_process_prompt.py`, `shared_information_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_contracts.py` (module contents) | `a103/evidence_axis_contracts.py` | Private dependency used by `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py`, `scientific_support_metadata.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_axis_instructions.py` (module contents) | `a103/evidence_axis_instructions.py` | Private dependency used by `a103_investigation.py`, `decision_context.py`, `scientific_process_episode.py`, `scientific_process_library.py` | Copied/split; private implementation |
| `gene_annotation_episode/evidence_geometry.py` (module contents) | `a103/evidence_geometry.py` | Private dependency used by `a103_credit.py`, `component_assessment_dependencies.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_expectations.py` (module contents) | `a103/execution_expectations.py` | Private dependency used by `a103_homology_resource_adapter.py`, `independent_execution.py`, `runtime.py`, `tools.py`, `wait_estimation_inputs.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_planning.py` (module contents) | `a103/execution_planning.py` | Private dependency used by `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_progress.py` (module contents) | `a103/execution_progress.py` | Private dependency used by `execution_episode.py`, `hpc_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_prompt.py` (module contents) | `a103/execution_prompt.py` | Private dependency used by `providers.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_recording.py` (module contents) | `a103/execution_recording.py` | Private dependency used by `_local_job_worker.py`, `execution_expectations.py`, `homology_episode.py`, `homology_jobs.py`, `native_lifecycle.py`, `native_timing_information.py`, `ordinary_execution.py`, `state.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_service_setup.py` (module contents) | `a103/execution_service_setup.py` | Private dependency used by `a103_investigation.py`, `assembled_service_setup.py` | Copied/split; private implementation |
| `gene_annotation_episode/execution_timing.py` (module contents) | `a103/execution_timing.py` | Private dependency used by `decision_exchanges.py`, `decision_history.py`, `episode_journal.py`, `numerical.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/finding_validity.py` (module contents) | `a103/finding_validity.py` | Private dependency used by `investigation_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/form_reference_validation.py` (module contents) | `a103/form_reference_validation.py` | Private dependency used by `communication.py`, `native_blast_database_results.py`, `native_blast_masking_results.py`, `native_blast_results.py`, `native_blast_standard_database_results.py`, `native_blast_utility_contracts.py`, `native_blast_utility_results.py`, `native_hmmer_preparation_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/genbank_intake.py` (module contents) | `a103/genbank_intake.py` | Private dependency used by `material_parsing.py`, `materials.py` | Copied/split; private implementation |
| `gene_annotation_episode/genomic_overlap_calculations.py` (module contents) | `a103/genomic_overlap_calculations.py` | Private dependency used by `genomic_overlap_execution_information.py`, `genomic_overlap_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/genomic_overlap_contracts.py` (module contents) | `a103/genomic_overlap_contracts.py` | Private dependency used by `genomic_overlap_calculations.py`, `genomic_overlap_execution_information.py`, `genomic_overlap_inputs.py`, `genomic_overlap_result_views.py`, `genomic_overlap_result_worker.py`, `genomic_overlap_return_views.py`, `native_genomic_overlap_contracts.py` | Copied/split; private implementation |
| `gene_annotation_episode/genomic_overlap_execution_information.py` (module contents) | `a103/genomic_overlap_execution_information.py` | Private dependency used by `execution_progress.py` | Copied/split; private implementation |
| `gene_annotation_episode/genomic_overlap_inputs.py` (module contents) | `a103/genomic_overlap_inputs.py` | Private dependency used by `genomic_overlap_calculations.py`, `genomic_overlap_execution_information.py`, `genomic_overlap_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/genomic_overlap_result_views.py` (module contents) | `a103/genomic_overlap_result_views.py` | Private dependency used by `genomic_overlap_execution_information.py`, `genomic_overlap_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/genomic_overlap_result_worker.py` (module contents) | `a103/genomic_overlap_result_worker.py` | Private dependency used by `genomic_overlap_execution_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/genomic_overlap_return_views.py` (module contents) | `a103/genomic_overlap_return_views.py` | Private dependency used by `genomic_overlap_execution_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmalign_grader.py` (module contents) | `a103/hmmalign_grader.py` | Private dependency used by `hmmer_graders.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmalign_inputs.py` (module contents) | `a103/hmmalign_inputs.py` | Private dependency used by `hmmalign_grader.py`, `hmmer_alignment_preparation_calculations.py`, `hmmer_alignment_preparation_data.py`, `hmmer_emission_data.py`, `hmmer_graders.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_input_alphabet.py` (module contents) | `a103/hmmer_alignment_input_alphabet.py` | Private dependency used by `hmmer_alignment_input_validation.py`, `hmmer_alignment_preparation_data.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_input_blocks.py` (module contents) | `a103/hmmer_alignment_input_blocks.py` | Private dependency used by `hmmer_alignment_preparation_data.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_input_fasta.py` (module contents) | `a103/hmmer_alignment_input_fasta.py` | Private dependency used by `hmmer_alignment_preparation_data.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_input_phylip.py` (module contents) | `a103/hmmer_alignment_input_phylip.py` | Private dependency used by `hmmer_alignment_preparation_data.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_input_types.py` (module contents) | `a103/hmmer_alignment_input_types.py` | Private dependency used by `hmmer_alignment_input_alphabet.py`, `hmmer_alignment_input_blocks.py`, `hmmer_alignment_input_fasta.py`, `hmmer_alignment_input_phylip.py`, `hmmer_alignment_input_validation.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_input_validation.py` (module contents) | `a103/hmmer_alignment_input_validation.py` | Private dependency used by `hmmer_alignment_preparation_calculations.py`, `hmmer_alignment_preparation_data.py`, `hmmer_preparation_result_views.py`, `native_hmmer_preparation_driver.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_pb_sampling.py` (module contents) | `a103/hmmer_alignment_pb_sampling.py` | Private dependency used by `hmmer_alignment_preparation_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_preparation_calculations.py` (module contents) | `a103/hmmer_alignment_preparation_calculations.py` | Private dependency used by `native_hmmer_preparation_driver.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_preparation_data.py` (module contents) | `a103/hmmer_alignment_preparation_data.py` | Private dependency used by `hmmer_alignment_preparation_calculations.py`, `hmmer_preparation_result_views.py`, `native_hmmer_preparation_driver.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_alignment_tree_weights.py` (module contents) | `a103/hmmer_alignment_tree_weights.py` | Private dependency used by `hmmer_alignment_preparation_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_artifact_calculations.py` (module contents) | `a103/hmmer_artifact_calculations.py` | Called by `native_hmmer_preparation_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_artifact_data.py` (module contents) | `a103/hmmer_artifact_data.py` | Private dependency used by `hmmer_artifact_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_emission_calculations.py` (module contents) | `a103/hmmer_emission_calculations.py` | Called by `native_hmmer_preparation_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_emission_data.py` (module contents) | `a103/hmmer_emission_data.py` | Private dependency used by `hmmer_emission_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_fm_calculations.py` (module contents) | `a103/hmmer_fm_calculations.py` | Called by `native_hmmer_preparation_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_fm_data.py` (module contents) | `a103/hmmer_fm_data.py` | Private dependency used by `hmmer_fm_calculations.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_driver.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_graders.py` (module contents) | `a103/hmmer_graders.py` | Private dependency used by `hmmer_native_result_views.py`, `homology_results.py`, `phmmer_grading_worker.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_model_binary.py` (module contents) | `a103/hmmer_model_binary.py` | Private dependency used by `hmmer_model_binary2.py`, `hmmer_model_data.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_model_binary2.py` (module contents) | `a103/hmmer_model_binary2.py` | Private dependency used by `hmmer_model_calculations.py`, `hmmer_model_data.py`, `hmmer_preparation_result_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_model_calculations.py` (module contents) | `a103/hmmer_model_calculations.py` | Private dependency used by `hmmer_alignment_preparation_calculations.py`, `hmmer_artifact_calculations.py`, `hmmer_emission_calculations.py`, `hmmer_statistics_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_model_data.py` (module contents) | `a103/hmmer_model_data.py` | Private dependency used by `hmmer_alignment_preparation_calculations.py`, `hmmer_alignment_preparation_data.py`, `hmmer_artifact_calculations.py`, `hmmer_artifact_data.py`, `hmmer_emission_calculations.py`, `hmmer_emission_data.py`, `hmmer_model_binary.py`, `hmmer_model_binary2.py`, `hmmer_model_calculations.py`, `hmmer_model_legacy.py`, `hmmer_preparation_result_views.py`, `hmmer_statistics_data.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_model_legacy.py` (module contents) | `a103/hmmer_model_legacy.py` | Private dependency used by `hmmer_model_data.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_model_source_cells.py` (module contents) | `a103/hmmer_model_source_cells.py` | Private dependency used by `hmmer_model_binary.py`, `hmmer_model_binary2.py`, `hmmer_model_calculations.py`, `hmmer_model_legacy.py`, `hmmer_preparation_result_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_native_result_views.py` (module contents) | `a103/hmmer_native_result_views.py` | Private dependency used by `execution_episode.py`, `execution_progress.py`, `native_hmmer_result_publication.py`, `native_hmmer_results.py`, `native_profile_presentation.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_preparation_result_views.py` (module contents) | `a103/hmmer_preparation_result_views.py` | Private dependency used by `execution_episode.py`, `execution_progress.py`, `native_hmmer_preparation_results.py`, `native_profile_presentation.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_search_grader.py` (module contents) | `a103/hmmer_search_grader.py` | Private dependency used by `hmmer_graders.py`, `phmmer_grading_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_search_inputs.py` (module contents) | `a103/hmmer_search_inputs.py` | Private dependency used by `hmmer_graders.py`, `hmmer_search_grader.py`, `phmmer_grading_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_simulation_calculations.py` (module contents) | `a103/hmmer_simulation_calculations.py` | Called by `native_hmmer_preparation_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_simulation_data.py` (module contents) | `a103/hmmer_simulation_data.py` | Private dependency used by `hmmer_simulation_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_statistics_calculations.py` (module contents) | `a103/hmmer_statistics_calculations.py` | Called by `native_hmmer_preparation_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/hmmer_statistics_data.py` (module contents) | `a103/hmmer_statistics_data.py` | Private dependency used by `hmmer_statistics_calculations.py` | Copied/split; private implementation |
| `gene_annotation_episode/homology_jobs.py` (module contents) | `a103/homology_jobs.py` | Private dependency used by `a103_homology_resource_adapter.py`, `episode_return_records.py`, `execution_expectations.py`, `execution_recording.py`, `homology_episode.py`, `homology_progress.py`, `homology_results.py`, `monitoring_credit.py`, `native_event_information.py`, `progress_records.py`, `resource_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/homology_query.py` (module contents) | `a103/homology_query.py` | Private dependency used by `episode_return_records.py`, `homology_episode.py`, `resource_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/homology_recovery.py` (module contents) | `a103/homology_recovery.py` | Retained original callable `recover_unparsed_searches`; no current production entry invokes it | Copied/split; private implementation |
| `gene_annotation_episode/homology_results.py` (module contents) | `a103/homology_results.py` | Private dependency used by `a103_homology_resource_adapter.py`, `homology_episode.py`, `homology_recovery.py`, `resource_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_prompt.py` (module contents) | `a103/hpc_prompt.py` | Private dependency used by `providers.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_result_receipts.py` (module contents) | `a103/hpc_result_receipts.py` | Private dependency used by `a103_hpc.py` | Copied/split; private implementation |
| `gene_annotation_episode/hpc_scientific_commission.py` (module contents) | `a103/hpc_scientific_commission.py` | Private dependency used by `a103_hpc.py` | Copied/split; private implementation |
| `gene_annotation_episode/independent_execution.py` (module contents) | `a103/independent_execution.py` | Private dependency used by `application_execution_binding.py` | Copied/split; private implementation |
| `gene_annotation_episode/inprocess_replay.py` (module contents) | `a103/inprocess_replay.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/investigation_progress.py` (module contents) | `a103/investigation_progress.py` | Private dependency used by `default_scientific_binding.py` | Copied/split; private implementation |
| `gene_annotation_episode/journal_metadata.py` (module contents) | `a103/journal_metadata.py` | Private dependency used by `episode_journal.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_jobs.py` (module contents) | `a103/local_jobs.py` | Private dependency used by `a103_tools.py`, `document_tools.py`, `homology_episode.py`, `homology_jobs.py`, `homology_recovery.py`, `homology_results.py`, `native_blast_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_driver.py`, `native_blast_local.py`, `native_blast_masking_contracts.py`, `native_blast_masking_local.py`, `native_blast_masking_results.py`, `native_blast_result_publication.py`, `native_blast_results.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_blast_utility_contracts.py`, `native_blast_utility_local.py`, `native_blast_utility_results.py`, `native_driver_runtime.py`, `native_hmmer_driver.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_driver.py`, `native_hmmer_preparation_local.py`, `native_hmmer_preparation_results.py`, `native_hmmer_result_publication.py`, `native_hmmer_results.py`, `native_lifecycle.py`, `practical_execution_operations.py`, `read_mapping.py`, `spreadsheet_tools.py`, `terminal_execution.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/local_resources.py` (module contents) | `a103/local_resources.py` | Private dependency used by `a103_homology_resource_adapter.py`, `native_lifecycle.py`, `resource_episode.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/material_gzip.py` (module contents) | `a103/material_gzip.py` | Private dependency used by `materials.py` | Copied/split; private implementation |
| `gene_annotation_episode/material_parsing.py` (module contents) | `a103/material_parsing.py` | Private dependency used by `materials.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/materials.py` (module contents) | `a103/materials.py` | Private dependency used by `a103_homology_resource_adapter.py`, `alignment_site_native.py`, `homology_episode.py`, `homology_results.py`, `image_evidence.py`, `library_targets.py`, `local_file_capture_results.py`, `materials_packing.py`, `native_blast_acquisition.py`, `native_blast_database_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py`, `native_blast_hsp_views.py`, `native_blast_result_publication.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py`, `native_event_information.py`, `native_file_capture.py`, `native_hmmer_acquisition.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_result_publication.py`, `resource_information.py`, `state.py`, `terminal_scientific_evidence.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/monitor_prompt.py` (module contents) | `a103/monitor_prompt.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/monitoring_credit.py` (module contents) | `a103/monitoring_credit.py` | Private dependency used by `homology_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_acquisition.py` (module contents) | `a103/native_blast_acquisition.py` | Private dependency used by `execution_episode.py`, `native_blast_result_publication.py`, `native_blast_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_contracts.py` (module contents) | `a103/native_blast_contracts.py` | Private dependency used by `blast_pairwise_result_views.py`, `blast_pairwise_results.py`, `native_blast_acquisition.py`, `native_blast_driver.py`, `native_blast_hsp_views.py`, `native_blast_local.py`, `native_blast_masking_contracts.py`, `native_blast_result_publication.py`, `native_blast_result_worker.py`, `native_blast_tool_info.py`, `native_blast_utility_contracts.py`, `native_blast_utility_tool_info.py`, `native_file_receipts.py`, `practical_execution_operations.py`, `practical_execution_records.py`, `sequence_masking_result_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_database_acquisition.py` (module contents) | `a103/native_blast_database_acquisition.py` | Private dependency used by `execution_episode.py`, `native_blast_database_result_publication.py`, `native_blast_database_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_database_contracts.py` (module contents) | `a103/native_blast_database_contracts.py` | Private dependency used by `blast_native_iteration_records.py`, `native_blast_database_acquisition.py`, `native_blast_database_convergence.py`, `native_blast_database_driver.py`, `native_blast_database_metadata.py`, `native_blast_database_result_publication.py`, `native_blast_database_result_worker.py`, `native_blast_utility_contracts.py`, `practical_execution_records.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_database_driver.py` (module contents) | `a103/native_blast_database_driver.py` | Private dependency used by `native_blast_utility_driver.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_database_result_publication.py` (module contents) | `a103/native_blast_database_result_publication.py` | Private dependency used by `alignment_site_native.py`, `blast_result_views.py`, `evidence_axis_contracts.py`, `evidence_geometry.py`, `execution_episode.py`, `native_blast_database_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_database_result_views.py` (module contents) | `a103/native_blast_database_result_views.py` | Private dependency used by `communication.py`, `execution_episode.py`, `execution_progress.py`, `native_blast_database_result_publication.py`, `native_blast_database_result_worker.py`, `native_blast_database_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_database_result_worker.py` (module contents) | `a103/native_blast_database_result_worker.py` | Private dependency used by `native_blast_database_result_publication.py`, `native_blast_standard_database_calculators.py`, `native_blast_standard_database_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_database_results.py` (module contents) | `a103/native_blast_database_results.py` | Private dependency used by `a103_execution_bindings.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_driver.py` (module contents) | `a103/native_blast_driver.py` | Private dependency used by `native_blast_local.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_local.py` (module contents) | `a103/native_blast_local.py` | Private dependency used by `native_blast_acquisition.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_masking_acquisition.py` (module contents) | `a103/native_blast_masking_acquisition.py` | Private dependency used by `execution_episode.py`, `native_blast_masking_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_masking_contracts.py` (module contents) | `a103/native_blast_masking_contracts.py` | Private dependency used by `execution_progress.py`, `native_blast_masking_acquisition.py`, `native_blast_masking_driver.py`, `native_blast_masking_local.py`, `native_blast_masking_results.py`, `native_blast_masking_tool_info.py`, `practical_execution_operations.py`, `practical_execution_records.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_masking_driver.py` (module contents) | `a103/native_blast_masking_driver.py` | Private dependency used by `native_blast_masking_local.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_masking_local.py` (module contents) | `a103/native_blast_masking_local.py` | Private dependency used by `native_blast_masking_acquisition.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_masking_results.py` (module contents) | `a103/native_blast_masking_results.py` | Private dependency used by `a103_execution_bindings.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_masking_tool_info.py` (module contents) | `a103/native_blast_masking_tool_info.py` | Private dependency used by `a103_execution_bindings.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_results.py` (module contents) | `a103/native_blast_results.py` | Private dependency used by `a103_execution_bindings.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_standard_database_acquisition.py` (module contents) | `a103/native_blast_standard_database_acquisition.py` | Private dependency used by `execution_episode.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_standard_database_contracts.py` (module contents) | `a103/native_blast_standard_database_contracts.py` | Private dependency used by `blast_utility_result_views.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_calculators.py`, `native_blast_standard_database_driver.py`, `native_blast_standard_database_metadata.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_result_views.py`, `native_blast_standard_database_result_worker.py`, `native_blast_utility_contracts.py`, `practical_execution_records.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_standard_database_driver.py` (module contents) | `a103/native_blast_standard_database_driver.py` | Called by `native_blast_standard_database_contracts.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_standard_database_result_publication.py` (module contents) | `a103/native_blast_standard_database_result_publication.py` | Private dependency used by `alignment_site_native.py`, `blast_result_views.py`, `evidence_axis_contracts.py`, `evidence_geometry.py`, `execution_episode.py`, `native_blast_standard_database_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_standard_database_result_views.py` (module contents) | `a103/native_blast_standard_database_result_views.py` | Private dependency used by `communication.py`, `execution_episode.py`, `execution_progress.py`, `native_blast_standard_database_calculators.py`, `native_blast_standard_database_result_publication.py`, `native_blast_standard_database_result_worker.py`, `native_blast_standard_database_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_standard_database_result_worker.py` (module contents) | `a103/native_blast_standard_database_result_worker.py` | Private dependency used by `native_blast_standard_database_result_publication.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_standard_database_results.py` (module contents) | `a103/native_blast_standard_database_results.py` | Private dependency used by `a103_execution_bindings.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_tool_info.py` (module contents) | `a103/native_blast_tool_info.py` | Private dependency used by `a103_execution_bindings.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_utility_acquisition.py` (module contents) | `a103/native_blast_utility_acquisition.py` | Private dependency used by `execution_episode.py`, `native_blast_utility_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_utility_contracts.py` (module contents) | `a103/native_blast_utility_contracts.py` | Private dependency used by `episode_services.py`, `execution_progress.py`, `native_blast_utility_acquisition.py`, `native_blast_utility_driver.py`, `native_blast_utility_local.py`, `native_blast_utility_results.py`, `native_blast_utility_tool_info.py`, `practical_execution_operations.py`, `practical_execution_records.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_utility_driver.py` (module contents) | `a103/native_blast_utility_driver.py` | Private dependency used by `native_blast_utility_local.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_utility_local.py` (module contents) | `a103/native_blast_utility_local.py` | Private dependency used by `native_blast_utility_acquisition.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_utility_results.py` (module contents) | `a103/native_blast_utility_results.py` | Private dependency used by `a103_execution_bindings.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_blast_utility_tool_info.py` (module contents) | `a103/native_blast_utility_tool_info.py` | Private dependency used by `a103_execution_bindings.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_database_terminal_custody.py` (module contents) | `a103/native_database_terminal_custody.py` | Private dependency used by `execution_progress.py`, `native_blast_database_acquisition.py`, `native_blast_database_result_publication.py`, `native_blast_standard_database_acquisition.py`, `native_blast_standard_database_result_publication.py`, `terminal_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_genomic_overlap_contracts.py` (module contents) | `a103/native_genomic_overlap_contracts.py` | Private dependency used by `genomic_overlap_execution_information.py`, `genomic_overlap_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_acquisition.py` (module contents) | `a103/native_hmmer_acquisition.py` | Private dependency used by `execution_episode.py`, `native_hmmer_preparation_results.py`, `native_hmmer_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_contracts.py` (module contents) | `a103/native_hmmer_contracts.py` | Private dependency used by `hmmer_native_result_views.py`, `native_hmmer_acquisition.py`, `native_hmmer_driver.py`, `native_hmmer_local.py`, `native_hmmer_result_publication.py`, `native_hmmer_tool_info.py`, `native_profile_presentation.py`, `practical_execution_operations.py`, `practical_execution_records.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_driver.py` (module contents) | `a103/native_hmmer_driver.py` | Private dependency used by `native_hmmer_local.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_local.py` (module contents) | `a103/native_hmmer_local.py` | Private dependency used by `native_hmmer_acquisition.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_preparation_acquisition.py` (module contents) | `a103/native_hmmer_preparation_acquisition.py` | Private dependency used by `execution_episode.py`, `native_blast_masking_acquisition.py`, `native_blast_utility_acquisition.py`, `native_blast_utility_driver.py`, `native_hmmer_preparation_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_preparation_contracts.py` (module contents) | `a103/native_hmmer_preparation_contracts.py` | Private dependency used by `hmmer_preparation_result_views.py`, `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_driver.py`, `native_hmmer_preparation_job_schema.py`, `native_hmmer_preparation_local.py`, `native_hmmer_preparation_tool_info.py`, `native_profile_presentation.py`, `practical_execution_operations.py`, `practical_execution_records.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_preparation_driver.py` (module contents) | `a103/native_hmmer_preparation_driver.py` | Private dependency used by `native_hmmer_preparation_acquisition.py`, `native_hmmer_preparation_local.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_preparation_job_schema.py` (module contents) | `a103/native_hmmer_preparation_job_schema.py` | Private dependency used by `native_hmmer_preparation_tool_info.py`, `native_profile_presentation.py`, `practical_execution_records.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_preparation_local.py` (module contents) | `a103/native_hmmer_preparation_local.py` | Private dependency used by `native_hmmer_preparation_acquisition.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_preparation_results.py` (module contents) | `a103/native_hmmer_preparation_results.py` | Private dependency used by `a103_execution_bindings.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_preparation_tool_info.py` (module contents) | `a103/native_hmmer_preparation_tool_info.py` | Private dependency used by `a103_execution_bindings.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_results.py` (module contents) | `a103/native_hmmer_results.py` | Private dependency used by `a103_execution_bindings.py`, `execution_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_hmmer_tool_info.py` (module contents) | `a103/native_hmmer_tool_info.py` | Private dependency used by `a103_execution_bindings.py`, `practical_execution_operations.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_lifecycle.py` (module contents) | `a103/native_lifecycle.py` | Private dependency used by `a103_tools.py`, `execution_recording.py`, `homology_jobs.py`, `homology_results.py`, `local_jobs.py`, `local_resources.py`, `native_blast_local.py`, `native_blast_masking_local.py`, `native_blast_utility_local.py`, `native_events.py`, `native_hmmer_local.py`, `native_hmmer_preparation_local.py`, `ordinary_execution.py`, `practical_execution_operations.py`, `terminal_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/native_profile_presentation.py` (module contents) | `a103/native_profile_presentation.py` | Private dependency used by `execution_episode.py`, `providers.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/nhmmer_grader.py` (module contents) | `a103/nhmmer_grader.py` | Private dependency used by `hmmer_graders.py` | Copied/split; private implementation |
| `gene_annotation_episode/nhmmer_inputs.py` (module contents) | `a103/nhmmer_inputs.py` | Private dependency used by `hmmer_graders.py`, `nhmmer_grader.py` | Copied/split; private implementation |
| `gene_annotation_episode/numerical.py` (module contents) | `a103/numerical.py` | Private dependency used by `completion_evidence.py`, `decision_history.py`, `episode_admission.py`, `episode_completion.py`, `episode_journal.py`, `episode_monitoring.py`, `episode_reports.py`, `execution_episode.py`, `hpc_campaign.py`, `hpc_episode.py`, `hpc_monitoring.py`, `independent_execution.py`, `monitor_episode.py`, `practical_yield.py`, `runtime.py`, `scientific_process_episode.py` | Copied/split; private implementation |
| `gene_annotation_episode/ordinary_execution.py` (module contents) | `a103/ordinary_execution.py` | Private dependency used by `tool_configuration.py`, `tools.py` | Copied/split; private implementation |
| `gene_annotation_episode/pending_assignment.py` (module contents) | `a103/pending_assignment.py` | Private dependency used by `episode_commissions.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/phmmer_format.py` (module contents) | `a103/phmmer_format.py` | Private dependency used by `homology_results.py`, `phmmer_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/phmmer_grading_worker.py` (module contents) | `a103/phmmer_grading_worker.py` | Private dependency used by `homology_results.py`, `phmmer_result_worker.py` | Copied/split; private implementation |
| `gene_annotation_episode/phmmer_result_worker.py` (module contents) | `a103/phmmer_result_worker.py` | Private dependency used by `homology_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/provider_authentication.py` (module contents) | `a103/provider_authentication.py` | Private dependency used by `providers.py` | Copied/split; private implementation |
| `gene_annotation_episode/providers.py` (module contents) | `a103/providers.py` | Private dependency used by `independent_execution.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/resource_estimation.py` (module contents) | `a103/resource_estimation.py` | Private dependency used by `a103_homology_resource_adapter.py`, `assembled_service_setup.py`, `homology_episode.py`, `independent_execution.py`, `monitoring_credit.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/run_statistics.py` (module contents) | `a103/run_statistics.py` | Private dependency used by `execution_expectations.py`, `execution_recording.py`, `ordinary_execution.py`, `resource_estimation.py`, `runtime.py`, `waiting.py` | Copied/split; private implementation |
| `gene_annotation_episode/runtime.py` (module contents) | `a103/runtime.py` | Private dependency used by `a103_investigation.py`, `bvbrc_appservice_custody.py`, `default_scientific_binding.py`, `episode_report_acquisition.py`, `episode_return_records.py`, `independent_execution.py`, `inprocess_replay.py` | Copied/split; private implementation |
| `gene_annotation_episode/schema_information_text.py` (module contents) | `a103/schema_information_text.py` | Private dependency used by `episode_contract_information.py`, `scientific_process_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/schema_support.py` (module contents) | `a103/schema_support.py` | Private dependency used by `episode_contract_information.py`, `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_findings.py` (module contents) | `a103/scientific_findings.py` | Private dependency used by `finding_validity.py`, `investigation_progress.py`, `state.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_library.py` (module contents) | `a103/scientific_process_library.py` | Private dependency used by `a103_investigation.py`, `composition_information.py`, `decision_context.py`, `episode_services.py`, `scientific_process_episode.py`, `scientific_process_setup.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_prompt.py` (module contents) | `a103/scientific_process_prompt.py` | Private dependency used by `execution_prompt.py`, `providers.py`, `receiver_prompt.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_process_setup.py` (module contents) | `a103/scientific_process_setup.py` | Private dependency used by `a103_investigation.py`, `assembled_service_setup.py` | Copied/split; private implementation |
| `gene_annotation_episode/scientific_tool_library.py` (module contents) | `a103/scientific_tool_library.py` | Private dependency used by `a103_investigation.py`, `episode_services.py`, `scientific_process_records.py`, `scientific_process_setup.py`, `scientific_tool_retrieval.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_contracts.py` (module contents) | `a103/sequence_masking_contracts.py` | Private dependency used by `native_blast_masking_contracts.py`, `native_blast_masking_driver.py`, `native_blast_masking_results.py`, `native_blast_masking_tool_info.py`, `sequence_masking_inputs.py`, `sequence_masking_result_views.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_inputs.py` (module contents) | `a103/sequence_masking_inputs.py` | Private dependency used by `native_blast_masking_driver.py` | Copied/split; private implementation |
| `gene_annotation_episode/sequence_masking_result_views.py` (module contents) | `a103/sequence_masking_result_views.py` | Private dependency used by `a103_execution_bindings.py`, `communication.py`, `execution_episode.py`, `execution_progress.py`, `native_blast_masking_results.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information.py` (module contents) | `a103/shared_information.py` | Private dependency used by `runtime.py` | Copied/split; private implementation |
| `gene_annotation_episode/shared_information_results.py` (module contents) | `a103/shared_information_results.py` | Private dependency used by `episode_work_report.py`, `runtime.py`, `shared_information.py` | Copied/split; private implementation |
| `gene_annotation_episode/tool_configuration.py` (module contents) | `a103/tool_configuration.py` | Private dependency used by `independent_execution.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_return_contracts.py` (module contents) | `a103/uniprot_return_contracts.py` | Private dependency used by `communication.py`, `episode_contract_information.py`, `execution_episode.py`, `uniprot_return_projection.py`, `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_return_projection.py` (module contents) | `a103/uniprot_return_projection.py` | Private dependency used by `uniprot_returns.py` | Copied/split; private implementation |
| `gene_annotation_episode/uniprot_returns.py` (module contents) | `a103/uniprot_returns.py` | Private dependency used by `api_service_execution.py` | Copied/split; private implementation |

2026-11-11: the private vendored numerical template now imports its completion/end-state types from this package's independent `library/method_loop/`, not the top-level repository loop. Upstream numerical code and constants are unchanged; this is the local import-placement patch.

## 2026-11-11 final A103 source-placement accounting

The current A103 entry is `a103_investigation.A103ServiceFactory`, with private `tools.ToolRegistry`, `runtime.Workflow`, scientific/literature bindings and the caller-supplied local execution factory. Missing original BLAST result returns, utility/masking preparation, HMMER preparation grading/publication, and HPC launch authentication dependencies are now independent local files. The exact private worker module names, producer-manifest paths and result-publication subprocess commands now name A103. The HPC source snapshot carries A103's domain module rather than the removed root implementation. No interpretation, calculation, native selection or continuation rule was changed.

The genomic-overlap path remains private: `terminal_scientific_evidence` uses `native_genomic_overlap_contracts`, whose pinned driver is `native_genomic_overlap_driver`; that driver imports A103's `genomic_overlap_inputs`, `genomic_overlap_contracts`, `acquisition` and `local_jobs`. This does not replace A103's locus/neighborhood/detection/native-request tools or add a new launch route. The copied unused MACS2 monitor service and foreign FBA/MACS2/LUMPY compact-request receipt branches were removed; original A103 receipt/action identity checks remain.

| Original module | Private destination | Actual caller | Change |
| --- | --- | --- | --- |
| `blast_database_extraction.py` | `a103/blast_database_extraction.py` | `blast_database_inspection.py`, `blast_preparation_inputs.py`, `blast_preparation_result_assembly.py`, `blast_vdb_utility_contracts.py`, `blast_vdb_utility_inputs.py`, `native_blast_utility_result_worker.py` | Independent private copy |
| `blast_database_inspection.py` | `a103/blast_database_inspection.py` | `blast_preparation_inputs.py`, `blast_vdb_utility_inputs.py`, `native_blast_utility_result_worker.py` | Independent private copy |
| `blast_database_preparation.py` | `a103/blast_database_preparation.py` | `blast_preparation_population.py`, `blast_preparation_result_assembly.py`, `blast_utility_result_views.py`, `native_blast_utility_result_worker.py` | Independent private copy |
| `blast_maskinfo_inputs.py` | `a103/blast_maskinfo_inputs.py` | `execution_progress.py`, `native_blast_masking_result_worker.py`, `sequence_masking_contracts.py` | Independent private copy |
| `blast_preparation_contracts.py` | `a103/blast_preparation_contracts.py` | `blast_preparation_inputs.py`, `blast_preparation_population.py`, `blast_utility_contracts.py`, `blast_vdb_utility_contracts.py`, `native_blast_utility_contracts.py`, `native_blast_utility_materializations.py`, `native_blast_utility_tool_info.py`, `native_blast_vdb_utility_context.py` | Independent private copy |
| `blast_preparation_inputs.py` | `a103/blast_preparation_inputs.py` | `blast_preparation_result_assembly.py`, `native_blast_utility_driver.py`, `native_blast_utility_materializations.py`, `native_blast_vdb_utility_context.py` | Independent private copy |
| `blast_preparation_population.py` | `a103/blast_preparation_population.py` | `blast_database_preparation.py`, `blast_preparation_result_assembly.py`, `blast_utility_contracts.py` | Independent private copy |
| `blast_utility_contracts.py` | `a103/blast_utility_contracts.py` | `blast_database_extraction.py`, `blast_database_inspection.py`, `blast_database_preparation.py`, `blast_preparation_contracts.py`, `blast_preparation_inputs.py`, `blast_preparation_population.py`, `blast_preparation_result_assembly.py`, `blast_utility_result_views.py`, `blast_vdb_utility_contracts.py`, `blast_vdb_utility_inputs.py`, `native_blast_utility_contracts.py`, `native_blast_utility_materializations.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_result_worker.py`, `native_blast_utility_results.py`, `native_blast_vdb_utility_context.py` | Independent private copy |
| `blast_utility_historical_fact_schemas.py` | `a103/blast_utility_historical_fact_schemas.py` | `communication.py` | Independent private copy |
| `blast_vdb_utility_contracts.py` | `a103/blast_vdb_utility_contracts.py` | `blast_utility_contracts.py`, `blast_utility_result_views.py`, `blast_vdb_utility_inputs.py`, `native_blast_utility_result_worker.py`, `native_blast_vdb_utility_context.py` | Independent private copy |
| `bvbrc_homology_tool_info.py` | `a103/bvbrc_homology_tool_info.py` | `a103_execution_bindings.py` | Independent private copy |
| `native_blast_database_returns.py` | `a103/native_blast_database_returns.py` | `a103_execution_bindings.py`, `execution_progress.py` | Independent private copy |
| `native_blast_database_tool_info.py` | `a103/native_blast_database_tool_info.py` | `a103_execution_bindings.py` | Independent private copy |
| `native_blast_masking_result_publication.py` | `a103/native_blast_masking_result_publication.py` | `native_blast_masking_results.py` | Independent private copy |
| `native_blast_masking_result_worker.py` | `a103/native_blast_masking_result_worker.py` | `native_blast_masking_result_publication.py` | Independent private copy |
| `native_blast_masking_returns.py` | `a103/native_blast_masking_returns.py` | `a103_execution_bindings.py` | Independent private copy |
| `native_blast_returns.py` | `a103/native_blast_returns.py` | `a103_execution_bindings.py` | Independent private copy |
| `native_blast_standard_database_returns.py` | `a103/native_blast_standard_database_returns.py` | `a103_execution_bindings.py` | Independent private copy |
| `native_blast_standard_database_tool_info.py` | `a103/native_blast_standard_database_tool_info.py` | `a103_execution_bindings.py` | Independent private copy |
| `native_blast_utility_capture_failure.py` | `a103/native_blast_utility_capture_failure.py` | `native_blast_utility_results.py` | Independent private copy |
| `native_blast_utility_materializations.py` | `a103/native_blast_utility_materializations.py` | `native_blast_utility_acquisition.py`, `native_blast_utility_contracts.py`, `native_blast_utility_driver.py` | Independent private copy |
| `native_blast_utility_result_publication.py` | `a103/native_blast_utility_result_publication.py` | `native_blast_utility_results.py` | Independent private copy |
| `native_blast_utility_result_worker.py` | `a103/native_blast_utility_result_worker.py` | `native_blast_utility_capture_failure.py`, `native_blast_utility_result_publication.py`, `native_blast_vdb_utility_context.py` | Independent private copy |
| `native_blast_utility_returns.py` | `a103/native_blast_utility_returns.py` | `a103_execution_bindings.py` | Independent private copy |
| `native_blast_vdb_utility_context.py` | `a103/native_blast_vdb_utility_context.py` | `native_blast_utility_acquisition.py`, `native_blast_utility_contracts.py`, `native_blast_utility_driver.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_result_worker.py`, `native_blast_utility_results.py` | Independent private copy |
| `native_blast_vdb_utility_execution.py` | `a103/native_blast_vdb_utility_execution.py` | `native_blast_utility_contracts.py`, `native_blast_utility_driver.py` | Independent private copy |
| `native_genomic_overlap_driver.py` | `a103/native_genomic_overlap_driver.py` | `genomic_overlap_execution_information.py`, `native_genomic_overlap_contracts.py` | Independent private copy |
| `native_hmmer_preparation_failure_views.py` | `a103/native_hmmer_preparation_failure_views.py` | `native_hmmer_preparation_results.py` | Independent private copy |
| `native_hmmer_preparation_result_publication.py` | `a103/native_hmmer_preparation_result_publication.py` | `native_hmmer_preparation_results.py` | Independent private copy |
| `native_hmmer_preparation_result_worker.py` | `a103/native_hmmer_preparation_result_worker.py` | `native_blast_masking_result_worker.py`, `native_blast_utility_result_worker.py`, `native_hmmer_preparation_result_publication.py`, `native_hmmer_preparation_results.py` | Independent private copy |
| `native_hmmer_preparation_returns.py` | `a103/native_hmmer_preparation_returns.py` | `a103_execution_bindings.py`, `runtime.py` | Independent private copy |
| `native_hmmer_preparation_worker.py` | `a103/native_hmmer_preparation_worker.py` | `native_hmmer_preparation_result_worker.py` | Independent private copy |
| `hpc_launch_authentication.py` | `a103/hpc_launch_authentication.py` | `execution_episode.py` | Independent private copy |
| `sequence_masking_calculations.py` | `a103/sequence_masking_calculations.py` | `execution_progress.py`, `native_blast_masking_result_worker.py` | Independent private copy |
| `windowmasker_statistics.py` | `a103/windowmasker_statistics.py` | `execution_progress.py`, `native_blast_masking_result_worker.py` | Independent private copy |
| `blast_vdb_utility_inputs.py` | `a103/blast_vdb_utility_inputs.py` | `execution_progress.py`, `native_blast_utility_result_worker.py` | Independent private copy |
| `blast_preparation_result_assembly.py` | `a103/blast_preparation_result_assembly.py` | `native_blast_utility_result_worker.py` | Independent private copy |

The existing `private_binding_reopen_pending` and `private_scientific_reopen_pending` failures in `episode_composition.py` remain unchanged. Combined reconstruction and execution validation are not claimed. No Python, tests, parse/import validation, static suite or investigation was run.

## 2026-11-11 iterator package placement

Moved the independently copied `library/method_loop/` package to `method_loop/` beside the private workflow code. It contains episode bindings, continuation and return mechanics, so it is outside the standalone-helper library. Direct imports and durable-worker module paths now name this private location; the worker package-root depth follows the moved files. Original license and provenance manifests remain with the copy. No runtime behavior or stopping rule was added.

2026-11-11: Root scalar helpers used by `a103_credit.py` were independently extracted into `a103_contribution.py`. The private record fixes A103 directly; contribution range, native correspondence/prerequisite arithmetic and attribution are preserved. Callers no longer import root scientific arithmetic or pass an axis selector.

## 2026-11-11 original gene-context file dispositions

The remaining top-level genomic-overlap, ComparativeSystems, GenomeAlignment/Mauve and GenomeComparison implementations and their schema assets are now private A103 files. Existing copies were preserved; missing original implementations were copied without registering new adapters or adding service assembly. Current direct callers are listed below. Entries without a current caller remain explicit original extension callables, not a claim of live workflow wiring. Historical schema/receipt labels remain unchanged.

| Original top-level file | Private destination | Caller or retained entry | Disposition |
| --- | --- | --- | --- |
| `bvbrc_comparative_systems_bundle_adapter.py` | `a103/bvbrc_comparative_systems_bundle_adapter.py` | Retained unbound original callable: `implementation_sha256`; current service registry does not select this extension | Original independently copied |
| `bvbrc_comparative_systems_bundle_contracts.py` | `a103/bvbrc_comparative_systems_bundle_contracts.py` | `bvbrc_comparative_systems_bundle_adapter.py`, `bvbrc_comparative_systems_bundle_projection.py`, `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_host_inputs.py`, `bvbrc_comparative_systems_returns.py`, `bvbrc_comparative_systems_tool_info.py` | Original independently copied |
| `bvbrc_comparative_systems_bundle_projection.py` | `a103/bvbrc_comparative_systems_bundle_projection.py` | `bvbrc_comparative_systems_bundle_adapter.py`, `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_publication.py`, `bvbrc_comparative_systems_returns.py` | Original independently copied |
| `bvbrc_comparative_systems_bundle_resolution.py` | `a103/bvbrc_comparative_systems_bundle_resolution.py` | `bvbrc_comparative_systems_bundle_adapter.py` | Original independently copied |
| `bvbrc_comparative_systems_calculation_contracts.py` | `a103/bvbrc_comparative_systems_calculation_contracts.py` | `bvbrc_comparative_systems_bundle_contracts.py`, `bvbrc_comparative_systems_bundle_projection.py`, `bvbrc_comparative_systems_calculators.py` | Original independently copied |
| `bvbrc_comparative_systems_calculators.py` | `a103/bvbrc_comparative_systems_calculators.py` | `bvbrc_comparative_systems_bundle_resolution.py` | Original independently copied |
| `bvbrc_comparative_systems_data_contracts.py` | `a103/bvbrc_comparative_systems_data_contracts.py` | `bvbrc_comparative_systems_bundle_contracts.py`, `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_data_inputs.py` | Original independently copied |
| `bvbrc_comparative_systems_data_inputs.py` | `a103/bvbrc_comparative_systems_data_inputs.py` | `bvbrc_comparative_systems_bundle_resolution.py` | Original independently copied |
| `bvbrc_comparative_systems_fact_contracts.py` | `a103/bvbrc_comparative_systems_fact_contracts.py` | `bvbrc_comparative_systems_bundle_adapter.py`, `bvbrc_comparative_systems_bundle_contracts.py`, `bvbrc_comparative_systems_bundle_projection.py`, `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_returns.py` | Original independently copied |
| `bvbrc_comparative_systems_handoff_contracts.py` | `a103/bvbrc_comparative_systems_handoff_contracts.py` | `bvbrc_comparative_systems_bundle_contracts.py`, `bvbrc_comparative_systems_bundle_projection.py`, `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_calculation_contracts.py`, `bvbrc_comparative_systems_calculators.py`, `bvbrc_comparative_systems_data_contracts.py`, `bvbrc_comparative_systems_data_inputs.py`, `bvbrc_comparative_systems_fact_contracts.py`, `bvbrc_comparative_systems_host_inputs.py`, `bvbrc_comparative_systems_native.py`, `bvbrc_comparative_systems_publication.py`, `bvbrc_comparative_systems_returns.py`, `bvbrc_comparative_systems_sheet.py`, `bvbrc_comparative_systems_sheet_contracts.py` | Original independently copied |
| `bvbrc_comparative_systems_handoff_schemas.json` | `a103/bvbrc_comparative_systems_handoff_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_comparative_systems_host_inputs.py` | `a103/bvbrc_comparative_systems_host_inputs.py` | Retained unbound original callable: `collect_comparative_systems_inputs`; current service registry does not select this extension | Original independently copied |
| `bvbrc_comparative_systems_native.py` | `a103/bvbrc_comparative_systems_native.py` | `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_sheet.py` | Original independently copied |
| `bvbrc_comparative_systems_publication.py` | `a103/bvbrc_comparative_systems_publication.py` | `bvbrc_comparative_systems_returns.py` | Original independently copied |
| `bvbrc_comparative_systems_returns.py` | `a103/bvbrc_comparative_systems_returns.py` | Retained unbound original callables: `ComparativeSystemsReturnError`, `comparative_systems_fact_sources`, `parent_form_schema`, `requested_sources`, `project_comparative_systems_return_facts`, `BVBRCComparativeSystemsReturns`; current service registry does not select this extension | Original independently copied |
| `bvbrc_comparative_systems_sheet.py` | `a103/bvbrc_comparative_systems_sheet.py` | `bvbrc_comparative_systems_bundle_resolution.py` | Original independently copied |
| `bvbrc_comparative_systems_sheet_contracts.py` | `a103/bvbrc_comparative_systems_sheet_contracts.py` | `bvbrc_comparative_systems_bundle_projection.py`, `bvbrc_comparative_systems_bundle_resolution.py`, `bvbrc_comparative_systems_sheet.py` | Original independently copied |
| `bvbrc_comparative_systems_tool_info.py` | `a103/bvbrc_comparative_systems_tool_info.py` | Retained unbound original callables: `comparative_systems_tool_contracts`, `validate_comparative_request`; current service registry does not select this extension | Original independently copied |
| `bvbrc_genome_alignment_associations.py` | `a103/bvbrc_genome_alignment_associations.py` | `bvbrc_genome_alignment_bundle_resolution.py` | Original independently copied |
| `bvbrc_genome_alignment_bundle_adapter.py` | `a103/bvbrc_genome_alignment_bundle_adapter.py` | Retained unbound original callable: `implementation_sha256`; current service registry does not select this extension | Original independently copied |
| `bvbrc_genome_alignment_bundle_contracts.py` | `a103/bvbrc_genome_alignment_bundle_contracts.py` | `bvbrc_genome_alignment_bundle_adapter.py`, `bvbrc_genome_alignment_bundle_projection.py`, `bvbrc_genome_alignment_bundle_resolution.py`, `bvbrc_genome_alignment_returns.py`, `bvbrc_genome_alignment_tool_info.py` | Original independently copied |
| `bvbrc_genome_alignment_bundle_projection.py` | `a103/bvbrc_genome_alignment_bundle_projection.py` | `bvbrc_genome_alignment_bundle_resolution.py`, `bvbrc_genome_alignment_returns.py` | Original independently copied |
| `bvbrc_genome_alignment_bundle_resolution.py` | `a103/bvbrc_genome_alignment_bundle_resolution.py` | `bvbrc_genome_alignment_bundle_adapter.py` | Original independently copied |
| `bvbrc_genome_alignment_calculation_contracts.py` | `a103/bvbrc_genome_alignment_calculation_contracts.py` | `bvbrc_genome_alignment_bundle_contracts.py`, `bvbrc_genome_alignment_calculators.py`, `bvbrc_genome_alignment_sheet.py` | Original independently copied |
| `bvbrc_genome_alignment_calculators.py` | `a103/bvbrc_genome_alignment_calculators.py` | `bvbrc_genome_alignment_bundle_resolution.py` | Original independently copied |
| `bvbrc_genome_alignment_host_inputs.py` | `a103/bvbrc_genome_alignment_host_inputs.py` | Retained unbound original callable: `collect_retained_records`; current service registry does not select this extension | Original independently copied |
| `bvbrc_genome_alignment_input_contracts.py` | `a103/bvbrc_genome_alignment_input_contracts.py` | `bvbrc_genome_alignment_associations.py`, `bvbrc_genome_alignment_bundle_resolution.py`, `bvbrc_genome_alignment_inputs.py`, `bvbrc_genome_alignment_sheet.py`, `mauve_backbone_calculators.py`, `mauve_v4_calculators.py` | Original independently copied |
| `bvbrc_genome_alignment_inputs.py` | `a103/bvbrc_genome_alignment_inputs.py` | `bvbrc_genome_alignment_associations.py`, `bvbrc_genome_alignment_bundle_resolution.py` | Original independently copied |
| `bvbrc_genome_alignment_retained_records.py` | `a103/bvbrc_genome_alignment_retained_records.py` | `bvbrc_genome_alignment_associations.py`, `bvbrc_genome_alignment_inputs.py` | Original independently copied |
| `bvbrc_genome_alignment_returns.py` | `a103/bvbrc_genome_alignment_returns.py` | Retained unbound original callables: `genome_alignment_fact_sources`, `requested_sources`, `project_genome_alignment_facts`, `BVBRCGenomeAlignmentReturns`; current service registry does not select this extension | Original independently copied |
| `bvbrc_genome_alignment_sheet.py` | `a103/bvbrc_genome_alignment_sheet.py` | `bvbrc_genome_alignment_bundle_projection.py`, `bvbrc_genome_alignment_bundle_resolution.py`, `bvbrc_genome_alignment_calculation_contracts.py`, `bvbrc_genome_alignment_calculators.py` | Original independently copied |
| `bvbrc_genome_alignment_tool_info.py` | `a103/bvbrc_genome_alignment_tool_info.py` | Retained unbound original callable: `genome_alignment_tool_contracts`; current service registry does not select this extension | Original independently copied |
| `bvbrc_proteome_bundle_adapter.py` | `a103/bvbrc_proteome_bundle_adapter.py` | `bvbrc_proteome_bundle_adapter_v2.py` | Original independently copied |
| `bvbrc_proteome_bundle_adapter_v2.py` | `a103/bvbrc_proteome_bundle_adapter_v2.py` | Retained unbound original callables: `implementation_sha256`, `consume_bundle`; current service registry does not select this extension | Original independently copied |
| `bvbrc_proteome_bundle_contracts.py` | `a103/bvbrc_proteome_bundle_contracts.py` | `bvbrc_proteome_bundle_adapter.py`, `bvbrc_proteome_bundle_projection.py`, `bvbrc_proteome_bundle_resolution.py`, `bvbrc_proteome_bundle_v2_contracts.py`, `bvbrc_proteome_fact_contracts.py`, `bvbrc_proteome_returns.py`, `bvbrc_proteome_tool_info.py` | Original independently copied |
| `bvbrc_proteome_bundle_projection.py` | `a103/bvbrc_proteome_bundle_projection.py` | `bvbrc_proteome_bundle_resolution.py`, `bvbrc_proteome_directional_projection.py`, `bvbrc_proteome_returns.py` | Original independently copied |
| `bvbrc_proteome_bundle_resolution.py` | `a103/bvbrc_proteome_bundle_resolution.py` | `bvbrc_proteome_bundle_adapter.py`, `bvbrc_proteome_bundle_v2_resolution.py` | Original independently copied |
| `bvbrc_proteome_bundle_schemas.json` | `a103/bvbrc_proteome_bundle_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_proteome_bundle_v2_contracts.py` | `a103/bvbrc_proteome_bundle_v2_contracts.py` | `bvbrc_proteome_bundle_adapter_v2.py`, `bvbrc_proteome_bundle_v2_resolution.py`, `bvbrc_proteome_directional_projection.py`, `bvbrc_proteome_directional_saved_validation.py`, `bvbrc_proteome_numerical_sheet.py`, `bvbrc_proteome_returns.py`, `bvbrc_proteome_tool_info.py` | Original independently copied |
| `bvbrc_proteome_bundle_v2_resolution.py` | `a103/bvbrc_proteome_bundle_v2_resolution.py` | `bvbrc_proteome_bundle_adapter_v2.py` | Original independently copied |
| `bvbrc_proteome_bundle_v2_schemas.json` | `a103/bvbrc_proteome_bundle_v2_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_proteome_calculators.py` | `a103/bvbrc_proteome_calculators.py` | `bvbrc_proteome_bundle_resolution.py` | Original independently copied |
| `bvbrc_proteome_data_contracts.py` | `a103/bvbrc_proteome_data_contracts.py` | `bvbrc_proteome_bundle_contracts.py`, `bvbrc_proteome_bundle_projection.py`, `bvbrc_proteome_bundle_resolution.py`, `bvbrc_proteome_bundle_v2_contracts.py`, `bvbrc_proteome_calculators.py`, `bvbrc_proteome_inputs.py`, `bvbrc_proteome_joins.py`, `bvbrc_proteome_sheet.py`, `bvbrc_proteome_sheet_contracts.py` | Original independently copied |
| `bvbrc_proteome_data_schemas.json` | `a103/bvbrc_proteome_data_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_proteome_directional.py` | `a103/bvbrc_proteome_directional.py` | `bvbrc_proteome_bundle_v2_resolution.py` | Original independently copied |
| `bvbrc_proteome_directional_calculators.py` | `a103/bvbrc_proteome_directional_calculators.py` | `bvbrc_proteome_bundle_v2_resolution.py` | Original independently copied |
| `bvbrc_proteome_directional_contracts.py` | `a103/bvbrc_proteome_directional_contracts.py` | `bvbrc_proteome_bundle_v2_contracts.py`, `bvbrc_proteome_bundle_v2_resolution.py`, `bvbrc_proteome_directional.py`, `bvbrc_proteome_directional_numerical_contracts.py`, `bvbrc_proteome_directional_sheet.py` | Original independently copied |
| `bvbrc_proteome_directional_fact_contracts.py` | `a103/bvbrc_proteome_directional_fact_contracts.py` | `bvbrc_proteome_bundle_adapter_v2.py`, `bvbrc_proteome_bundle_v2_contracts.py`, `bvbrc_proteome_directional_projection.py`, `bvbrc_proteome_returns.py` | Original independently copied |
| `bvbrc_proteome_directional_geometry.py` | `a103/bvbrc_proteome_directional_geometry.py` | `bvbrc_proteome_directional_calculators.py`, `bvbrc_proteome_directional_numerical_contracts.py` | Original independently copied |
| `bvbrc_proteome_directional_numerical_contracts.py` | `a103/bvbrc_proteome_directional_numerical_contracts.py` | `bvbrc_proteome_bundle_v2_contracts.py`, `bvbrc_proteome_directional_calculators.py`, `bvbrc_proteome_directional_saved_validation.py`, `bvbrc_proteome_directional_sheet.py`, `bvbrc_proteome_numerical_sheet.py` | Original independently copied |
| `bvbrc_proteome_directional_numerical_schemas.json` | `a103/bvbrc_proteome_directional_numerical_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_proteome_directional_projection.py` | `a103/bvbrc_proteome_directional_projection.py` | `bvbrc_proteome_bundle_adapter_v2.py`, `bvbrc_proteome_returns.py` | Original independently copied |
| `bvbrc_proteome_directional_saved_validation.py` | `a103/bvbrc_proteome_directional_saved_validation.py` | `bvbrc_proteome_bundle_v2_contracts.py` | Original independently copied |
| `bvbrc_proteome_directional_schemas.json` | `a103/bvbrc_proteome_directional_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_proteome_directional_sheet.py` | `a103/bvbrc_proteome_directional_sheet.py` | `bvbrc_proteome_bundle_v2_resolution.py` | Original independently copied |
| `bvbrc_proteome_fact_contracts.py` | `a103/bvbrc_proteome_fact_contracts.py` | `bvbrc_proteome_bundle_adapter.py`, `bvbrc_proteome_bundle_contracts.py`, `bvbrc_proteome_bundle_projection.py`, `bvbrc_proteome_bundle_resolution.py`, `bvbrc_proteome_directional_fact_contracts.py`, `bvbrc_proteome_directional_projection.py`, `bvbrc_proteome_returns.py` | Original independently copied |
| `bvbrc_proteome_inputs.py` | `a103/bvbrc_proteome_inputs.py` | `bvbrc_proteome_bundle_resolution.py` | Original independently copied |
| `bvbrc_proteome_joins.py` | `a103/bvbrc_proteome_joins.py` | `bvbrc_proteome_bundle_resolution.py` | Original independently copied |
| `bvbrc_proteome_native.py` | `a103/bvbrc_proteome_native.py` | `bvbrc_proteome_bundle_resolution.py` | Original independently copied |
| `bvbrc_proteome_native_contracts.py` | `a103/bvbrc_proteome_native_contracts.py` | `bvbrc_proteome_bundle_contracts.py`, `bvbrc_proteome_bundle_projection.py`, `bvbrc_proteome_directional_contracts.py`, `bvbrc_proteome_fact_contracts.py`, `bvbrc_proteome_joins.py`, `bvbrc_proteome_native.py`, `bvbrc_proteome_sheet.py`, `bvbrc_proteome_sheet_contracts.py` | Original independently copied |
| `bvbrc_proteome_native_schemas.json` | `a103/bvbrc_proteome_native_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_proteome_numerical_sheet.py` | `a103/bvbrc_proteome_numerical_sheet.py` | `bvbrc_proteome_bundle_v2_resolution.py` | Original independently copied |
| `bvbrc_proteome_returns.py` | `a103/bvbrc_proteome_returns.py` | Retained unbound original callables: `ProteomeReturnError`, `proteome_fact_sources`, `requested_sources`, `project_proteome_facts`, `BVBRCProteomeReturns`; current service registry does not select this extension | Original independently copied |
| `bvbrc_proteome_sheet.py` | `a103/bvbrc_proteome_sheet.py` | `bvbrc_proteome_bundle_resolution.py` | Original independently copied |
| `bvbrc_proteome_sheet_contracts.py` | `a103/bvbrc_proteome_sheet_contracts.py` | `bvbrc_proteome_bundle_contracts.py`, `bvbrc_proteome_bundle_projection.py`, `bvbrc_proteome_bundle_v2_contracts.py`, `bvbrc_proteome_calculators.py`, `bvbrc_proteome_directional_saved_validation.py`, `bvbrc_proteome_fact_contracts.py`, `bvbrc_proteome_joins.py`, `bvbrc_proteome_numerical_sheet.py`, `bvbrc_proteome_sheet.py` | Original independently copied |
| `bvbrc_proteome_sheet_schemas.json` | `a103/bvbrc_proteome_sheet_schemas.json` | Schema asset read by its private contract module and adapter source manifest | Original independently copied |
| `bvbrc_proteome_tool_info.py` | `a103/bvbrc_proteome_tool_info.py` | Retained unbound original callable: `proteome_tool_contracts`; current service registry does not select this extension | Original independently copied |
| `comparative_ops.py` | `a103/comparative_ops.py` | `a103_scoring.py`, `tools.py` | Existing private copy preserved |
| `genomic_overlap_calculations.py` | `a103/genomic_overlap_calculations.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_result_worker.py`, `sequence_masking_calculations.py` | Existing private copy preserved |
| `genomic_overlap_contracts.py` | `a103/genomic_overlap_contracts.py` | `genomic_overlap_calculations.py`, `genomic_overlap_execution_information.py`, `genomic_overlap_inputs.py`, `genomic_overlap_presentation.py`, `genomic_overlap_result_receipts.py`, `genomic_overlap_result_views.py`, `genomic_overlap_result_worker.py`, `genomic_overlap_return_views.py`, `native_genomic_overlap_capture.py`, `native_genomic_overlap_contracts.py`, `native_genomic_overlap_preparation.py`, `native_genomic_overlap_results.py` | Existing private copy preserved |
| `genomic_overlap_execution_information.py` | `a103/genomic_overlap_execution_information.py` | `execution_progress.py` | Existing private copy preserved |
| `genomic_overlap_inputs.py` | `a103/genomic_overlap_inputs.py` | `genomic_overlap_calculations.py`, `genomic_overlap_execution_information.py`, `genomic_overlap_result_worker.py`, `native_genomic_overlap_contracts.py`, `native_genomic_overlap_driver.py`, `native_genomic_overlap_preparation.py` | Existing private copy preserved |
| `genomic_overlap_operands.py` | `a103/genomic_overlap_operands.py` | Retained unbound original callable: `validate_genomic_overlap_job_inputs`; current service registry does not select this extension | Original independently copied |
| `genomic_overlap_presentation.py` | `a103/genomic_overlap_presentation.py` | Retained unbound original callables: `genomic_overlap_scientific_job_view`, `select_genomic_overlap_execution_values`, `select_genomic_overlap_presentation`, `render_genomic_overlap_projections`; current service registry does not select this extension | Original independently copied |
| `genomic_overlap_result_receipts.py` | `a103/genomic_overlap_result_receipts.py` | `native_genomic_overlap_results.py` | Original independently copied |
| `genomic_overlap_result_views.py` | `a103/genomic_overlap_result_views.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_result_worker.py` | Existing private copy preserved |
| `genomic_overlap_result_worker.py` | `a103/genomic_overlap_result_worker.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_result_receipts.py`, `native_genomic_overlap_preparation.py` | Existing private copy preserved |
| `genomic_overlap_return_views.py` | `a103/genomic_overlap_return_views.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_presentation.py`, `genomic_overlap_result_receipts.py`, `genomic_overlap_returns.py`, `native_genomic_overlap_results.py` | Existing private copy preserved |
| `genomic_overlap_returns.py` | `a103/genomic_overlap_returns.py` | `genomic_overlap_execution_information.py` | Original independently copied |
| `mauve_backbone_calculators.py` | `a103/mauve_backbone_calculators.py` | `bvbrc_genome_alignment_calculators.py` | Original independently copied |
| `mauve_backbone_contracts.py` | `a103/mauve_backbone_contracts.py` | `bvbrc_genome_alignment_associations.py`, `bvbrc_genome_alignment_calculation_contracts.py`, `bvbrc_genome_alignment_sheet.py`, `mauve_backbone_calculators.py`, `mauve_backbone_formats.py` | Original independently copied |
| `mauve_backbone_formats.py` | `a103/mauve_backbone_formats.py` | `bvbrc_genome_alignment_bundle_resolution.py` | Original independently copied |
| `mauve_v4_calculation_contracts.py` | `a103/mauve_v4_calculation_contracts.py` | `bvbrc_genome_alignment_calculation_contracts.py`, `mauve_v4_calculators.py` | Original independently copied |
| `mauve_v4_calculators.py` | `a103/mauve_v4_calculators.py` | `bvbrc_genome_alignment_calculators.py` | Original independently copied |
| `mauve_v4_format_contracts.py` | `a103/mauve_v4_format_contracts.py` | `bvbrc_genome_alignment_associations.py`, `bvbrc_genome_alignment_bundle_resolution.py`, `bvbrc_genome_alignment_calculation_contracts.py`, `bvbrc_genome_alignment_sheet.py`, `mauve_v4_calculation_contracts.py`, `mauve_v4_calculators.py`, `mauve_v4_formats.py` | Original independently copied |
| `mauve_v4_formats.py` | `a103/mauve_v4_formats.py` | `bvbrc_genome_alignment_bundle_resolution.py` | Original independently copied |
| `native_genomic_overlap_capture.py` | `a103/native_genomic_overlap_capture.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_result_receipts.py`, `native_genomic_overlap_results.py` | Original independently copied |
| `native_genomic_overlap_contracts.py` | `a103/native_genomic_overlap_contracts.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_operands.py`, `genomic_overlap_presentation.py`, `genomic_overlap_result_receipts.py`, `genomic_overlap_result_worker.py`, `native_genomic_overlap_capture.py`, `native_genomic_overlap_driver.py`, `native_genomic_overlap_local.py`, `native_genomic_overlap_observations.py`, `native_genomic_overlap_results.py`, `native_genomic_overlap_tool_info.py` | Existing private copy preserved |
| `native_genomic_overlap_driver.py` | `a103/native_genomic_overlap_driver.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_result_receipts.py`, `native_genomic_overlap_contracts.py`, `native_genomic_overlap_local.py`, `native_genomic_overlap_tool_info.py` | Existing private copy preserved |
| `native_genomic_overlap_local.py` | `a103/native_genomic_overlap_local.py` | `genomic_overlap_result_receipts.py` | Original independently copied |
| `native_genomic_overlap_observations.py` | `a103/native_genomic_overlap_observations.py` | Retained unbound original callables: `genomic_overlap_observed_files`, `read_genomic_overlap_output`; current service registry does not select this extension | Original independently copied |
| `native_genomic_overlap_preparation.py` | `a103/native_genomic_overlap_preparation.py` | `genomic_overlap_execution_information.py`, `genomic_overlap_result_receipts.py`, `native_genomic_overlap_results.py` | Original independently copied |
| `native_genomic_overlap_results.py` | `a103/native_genomic_overlap_results.py` | `genomic_overlap_execution_information.py` | Original independently copied |
| `native_genomic_overlap_tool_info.py` | `a103/native_genomic_overlap_tool_info.py` | Retained unbound original callables: `genomic_overlap_tool_contracts`, `genomic_overlap_tool_information`; current service registry does not select this extension | Original independently copied |

Required helper copies: 

| Original helper or symbols | Destination | Actual caller | Disposition |
| --- | --- | --- | --- |
| `native_atac_differential_preparation._dependencies; native_atac_differential_contracts driver schema/dependencies; native_flux_balance_storage file_pin and exact confined-read helpers` | `a103/genomic_overlap_worker_runtime.py` | `native_genomic_overlap_preparation.py` | Independent applicable helper copy |
| `bvbrc_appservice_saved_results.py` | `a103/bvbrc_appservice_saved_results.py` | `bvbrc_comparative_systems_returns.py`, `bvbrc_genome_alignment_returns.py`, `bvbrc_proteome_returns.py` | Independent applicable helper copy |
| `bvbrc_alignment_values.py` | `a103/bvbrc_alignment_values.py` | `bvbrc_genome_alignment_associations.py`, `bvbrc_genome_alignment_bundle_projection.py`, `bvbrc_genome_alignment_bundle_resolution.py`, `bvbrc_genome_alignment_calculation_contracts.py`, `mauve_backbone_calculators.py`, `mauve_backbone_contracts.py`, `mauve_backbone_formats.py`, `mauve_v4_calculation_contracts.py`, `mauve_v4_calculators.py`, `mauve_v4_format_contracts.py`, `mauve_v4_formats.py`, `xmfa_calculation_contracts.py`, `xmfa_calculators.py`, `xmfa_coordinates.py`, `xmfa_format_contracts.py`, `xmfa_formats.py`, `xmfa_source_contracts.py`, `xmfa_sources.py` | Independent applicable helper copy |
| `xmfa_format_contracts.py` | `a103/xmfa_format_contracts.py` | `bvbrc_genome_alignment_associations.py`, `bvbrc_genome_alignment_calculation_contracts.py`, `bvbrc_genome_alignment_sheet.py`, `mauve_backbone_calculators.py`, `mauve_backbone_contracts.py`, `mauve_backbone_formats.py`, `mauve_v4_format_contracts.py`, `xmfa_calculators.py`, `xmfa_coordinates.py`, `xmfa_formats.py`, `xmfa_sources.py` | Independent applicable helper copy |
| `xmfa_formats.py` | `a103/xmfa_formats.py` | `bvbrc_genome_alignment_bundle_resolution.py` | Independent applicable helper copy |
| `xmfa_source_contracts.py` | `a103/xmfa_source_contracts.py` | `bvbrc_genome_alignment_calculation_contracts.py`, `bvbrc_genome_alignment_input_contracts.py`, `xmfa_sources.py` | Independent applicable helper copy |
| `xmfa_calculation_contracts.py` | `a103/xmfa_calculation_contracts.py` | `bvbrc_genome_alignment_calculation_contracts.py`, `mauve_backbone_calculators.py`, `mauve_backbone_contracts.py`, `mauve_v4_calculation_contracts.py`, `mauve_v4_calculators.py`, `xmfa_calculators.py`, `xmfa_coordinates.py` | Independent applicable helper copy |
| `xmfa_calculators.py` | `a103/xmfa_calculators.py` | `bvbrc_genome_alignment_calculators.py` | Independent applicable helper copy |
| `xmfa_coordinates.py` | `a103/xmfa_coordinates.py` | `bvbrc_genome_alignment_calculators.py`, `xmfa_calculators.py` | Independent applicable helper copy |
| `xmfa_sources.py` | `a103/xmfa_sources.py` | `bvbrc_genome_alignment_calculators.py`, `xmfa_calculators.py`, `xmfa_coordinates.py` | Independent applicable helper copy |
| `phylogeny_calculation_contracts.py` | `a103/phylogeny_calculation_contracts.py` | `bvbrc_alignment_values.py`, `bvbrc_genome_alignment_input_contracts.py`, `mauve_backbone_contracts.py`, `mauve_v4_calculation_contracts.py`, `mauve_v4_format_contracts.py`, `xmfa_calculation_contracts.py`, `xmfa_source_contracts.py` | Independent applicable helper copy |
| `phylogeny_format_contracts.py` | `a103/phylogeny_format_contracts.py` | `bvbrc_genome_alignment_input_contracts.py`, `xmfa_format_contracts.py`, `xmfa_source_contracts.py` | Independent applicable helper copy |
| `terminal_native_file_capture.py` | `a103/terminal_native_file_capture.py` | `genomic_overlap_result_receipts.py`, `native_genomic_overlap_capture.py` | Independent applicable helper copy |

`homology_search_receipt.search_receipt` now sits beside the A103 binding files because it authenticates received execution evidence. Its direct callers are `a103_native_requests.prepare`, `a103_tools.A103ToolRegistry` and retained `homology_recovery.recover_unparsed_searches`; A103 test imports were updated. No binding, return or continuation hook remains in A103 library/. The two A110 library helpers, `literature_assay_inputs` and `literature_partner_source_fields`, remain standalone source readers reused by reaction, native-input and meaning tasks; they contain no episode binding or credit policy.

Adapter source fingerprints now read local A103 files. The copied legacy manifest entries for unused Rfam discovery were removed because A103 acquisition does not import that path. The GenomeComparison v2 BLAST dependencies no longer use a sibling-directory path. Generated action files such as assignment.json, intent.json and receipt.json are runtime records, not missing source assets. No catalog registration, saved-binding reopening, test execution, Python or static suite was added.

All 94 original top-level files/assets in the preceding disposition table are now retired. The A101 implementation received its independent GenomeComparison/proteome copies before those originals were removed. No private implementation imports the retired root behavior. Existing legacy test/harness migration and saved descriptor reopening remain separate; this source-placement work is not execution validation.

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
`yield.py`; registration, context, available actions/children and local assembly
in `episode.py`. Scientific scoring dependencies and their distinct descriptive
filenames remain as recorded above. Cross-episode tests/fixtures remain at this
axis's `tests/` until their precise local owner is established. Relocation is
pending; this entry fixes the chosen name before any binding moves.

### Scientific-process binding relocation applied

`scientific_process/episode.py` now owns the one `scientific_process` registration. The original module is removed; callers import the new binding directly. Each supporting class is private to this episode and has no registration.

- `scientific_process/episode.py`: `__init__`, `as_record`, `contract_information_profile`, `_role`, `child_roles`, `permitted_common_actions`, `allowed_children`, `instructions`, `_information_catalog`, `_closed_tool_resolution`, `_tool_resolution_for`, `_tool_resolution`, `catalog`, `common_tool_names`, `decision_context`, `execute`, `initial_decision_context`.
- `scientific_process/requests.py`: `assignment_schema`, `child_assignment_schema`, `_selection`, `_assignment`, `_invocation`, `prepare_assignment`, `_validate_origin`, `prepare_invocation`, `restore_closed_process`, `restore_saved_process`, `validate_context`, `validate_execution_context`, `_original_selection`, `_proposed_selection`.
- `scientific_process/returns.py`: `required_return_sources`, `fact_sources`, `facts`, `resolve`, `validate_report`, `initial_references`.
- `scientific_process/credit.py`: `credit_kind`, `credit_projector`, `credit_view`.
- `scientific_process/yield.py`: `private_yield_binding`, `continuation_task`, `yield_controller`.

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

Each binding retains its own local methods: `requests.py` for assignments and request-derived schemas; `returns.py` for source/fact/report delivery; `credit.py` for task progress; `yield.py` for existing forecast behavior; `waiting.py` for existing wait declarations; `episode.py` for registration, construction, actions, and selected grader/repository assembly. Files are created only for existing responsibilities. Descriptive calculators, graders and sheet storage retain their names and current axis ownership pending the dependency-placement review.

The current source-reading roles also perform applicable interpretation/population and grading work. That task mixture is preserved here; a later goal must decide task-specific divisions. Root evidence assessment can search/read directly as well as commission the nested strategy/search/source chain. Cross-role literature tests and shared fixtures remain at their common owner until the test-placement review.

### Literature role separation applied

The former multi-role class has been removed. Each recorded directory now has one independently implemented `LiteratureEpisode` with a singleton registration role; child-only bindings have empty entry roles. Their request/report/credit/yield/wait methods are private local supporting classes. The published-evidence episode exposes `create_binding_tree` only as caller assembly of seven separate instances, with copied existing caller configuration. It is not a registered binding, continuation policy or forwarding replacement. Existing scientific method bodies are preserved, including applicable A105/A108 grading and typed findings.

`literature` support map:

- `scientific_process/published_evidence_assessment/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/waiting.py`: `supports_wait`.

`literature_strategy` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/waiting.py`: `supports_wait`.

`literature_search` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/waiting.py`: `supports_wait`.

`literature_page` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/waiting.py`: `supports_wait`.

`literature_table` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/waiting.py`: `supports_wait`.

`literature_ordered` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/waiting.py`: `supports_wait`.

`literature_targeted` support map:

- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py`: `__init__`, `as_record`, `contract_information_configuration`, `contract_information_profile`, `_role`, `permitted_common_actions`, `reasoning_action_schema`, `accept_reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `allowed_children`, `child_roles`, `instructions`, `initial_decision_context`, `decision_context`, `catalog`, `execute`, `automatic_score_judgments`, `complete_score_judgment`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/requests.py`: `child_assignment_schema`, `assignment_schema`, `_validate_page`, `_validate_assignment`, `prepare_assignment`, `_tool_arguments`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/returns.py`: `_require`, `_artifact`, `_within_source`, `fact_sources`, `facts`, `current_report_facts`, `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`, `resolve`, `validate_report`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/credit.py`: `credit_kind`, `credit_view`, `credit_projector`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/yield.py`: `continuation_task`, `yield_controller`.
- `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/waiting.py`: `supports_wait`.


## 2026-11-11 operational episode destinations recorded before relocation

The following plan follows declared child roles and the existing configured scientific parent. Resource-backed and direct execution bindings are alternative existing implementations; their distinct task homes do not imply simultaneous registration. Parent-specific copies preserve original request, report, operational/monitoring credit, yield and waiting behavior.

| Original class | Registered role | Chosen home (`episode.py`) | Commissioning parent |
| --- | --- | --- | --- |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/execution_job_submission` | `scientific_process` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/execution_job_submission/api_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/execution_job_submission/local_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/execution_job_submission/hpc_job_execution` | `scientific_process/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/execution_result_acquisition` | `scientific_process` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/execution_progress_assessment` | `scientific_process` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `scientific_process/hpc_work_planning` | `scientific_process` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `scientific_process/hpc_work_planning/hpc_resource_prediction` | `scientific_process/hpc_work_planning` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/execution_job_submission` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `scientific_process/hpc_work_planning/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/execution_result_acquisition` | `scientific_process/hpc_work_planning` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/execution_progress_assessment` | `scientific_process/hpc_work_planning` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` | `scientific_process/hpc_work_planning/hpc_allocation_execution` |
| `resource_episode.py:ResourceEpisode` | `launch` | `scientific_process/resource_work_submission` | `scientific_process` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `scientific_process/resource_work_submission/api_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `scientific_process/resource_work_submission/local_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `scientific_process/resource_work_submission/hpc_resource_work_execution` | `scientific_process/resource_work_submission` |
| `resource_episode.py:ResourceEpisode` | `results` | `scientific_process/resource_result_acquisition` | `scientific_process` |
| `homology_episode.py:HomologyEpisode` | `job_launch` | `scientific_process/homology_job_submission` | `scientific_process` |
| `homology_episode.py:HomologyEpisode` | `job_monitor` | `scientific_process/homology_job_monitoring` | `scientific_process` |
| `homology_episode.py:HomologyEpisode` | `job_results` | `scientific_process/homology_result_acquisition` | `scientific_process` |

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

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/api_job_execution` (`launch_api`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/hpc_work_planning` (`hpc`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/hpc_resource_prediction` (`hpc_prediction`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/hpc_allocation_execution` (`hpc_execution`):

- `episode.py`: `__init__`, `targets`, `as_record`, `child_roles`, `allowed_children`, `permitted_common_actions`, `state`, `initialize`, `initial_decision_context`, `_current_model`, `_history`, `_shared_history`, `instructions`, `decision_context`, `catalog`, `_candidates`, `_features`, `_comparisons`, `_freeze`, `_candidate`, `_last_forecast`, `_collected_unit_ids`, `_uncollected_completed_unit_ids`, `_target`, `_known`, `_window`, `_allocation`, `_measure`, `execute`, `frozen_reference`.
- `requests.py`: `assignment_schema`, `commission_identity`, `_commission`, `prepare_assignment`, `_tool_request`, `original_launch_handoff`.
- `returns.py`: `export_closed`, `resolve_received_reference`, `read_evidence`, `_publish`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_quality`, `credit_view`.
- `yield.py`: `yield_controller`, `continuation_for_action`, `activity_advice`, `practical_estimator`.
- `waiting.py`: `_observe_queue`, `_queue`.

`scientific_process/hpc_work_planning/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` (`launch_api`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission` (`launch`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` (`launch_api`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution` (`launch_local`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition` (`results`):

- `episode.py`: `__init__`, `as_record`, `child_roles`, `required_return_sources`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`, `allowed_children`, `_masking_selector`, `_masking_inputs`, `_retained_masking_target`, `_masking_reference_access`, `_utility_selector`, `_utility_inputs`, `_retained_utility_target`, `_utility_reference_access`, `_versions`, `_recorded_results_assignment`, `_delegate`, `_practical_context`, `initialize`, `_check_parent_inputs`, `state`, `_resource_information`, `initial_decision_context`, `capabilities`, `resource_tool_contracts`, `permitted_common_actions`, `instructions`, `_with_selected_execution_task`, `decision_context`, `_target`, `_selector`, `catalog`, `execute`, `_result_directory`, `_windows`, `_selected_result_action`, `_execute_native_results`, `_publish_result`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`, `_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_generic_result_selector_progress`, `_native_results_complete`.
- `requests.py`: `child_assignment_schema`, `assignment_schema`, `_permitted`, `prepare_assignment`.
- `returns.py`: `_received`, `_forwards_bvbrc_reports`, `_forwards_minhash_reports`, `received_report_sources`, `received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `validate_received_report`, `fact_sources`, `facts`, `_live_facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `_closed_credit_carrier`, `_closed_credit_receipts`, `_closed_credit_value`, `_closed_credit_facts`, `_closed_operational_credit_view`, `project_credit`, `_live_project_credit`, `credit_view`, `_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`.
- `yield.py`: `_request_yield_class`, `_task_yield_profile`, `yield_controller`, `_launch_yield_controller`, `_launch_api_yield_controller`, `_launch_local_yield_controller`, `_launch_hpc_yield_controller`, `_results_yield_controller`, `practical_estimator`.
- `terminal_execution.py`: private operative terminal implementation; no additional registered role or nested iterator.

`scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` (`monitor`):

- `episode.py`: `__init__`, `as_record`, `_role`, `child_roles`, `required_return_sources`, `permitted_common_actions`, `allowed_children`, `instructions`, `_own_progress_refs`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_assignment`, `prepare_assignment`.
- `returns.py`: `_received`, `_snapshot`, `fact_sources`, `facts`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.
- `yield.py`: `yield_controller`.
- `progress_observations.py`: this monitor's observation provider, factual schemas and numerical observation helpers.

`scientific_process/resource_work_submission` (`launch`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_work_submission/api_resource_work_execution` (`launch_api`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_work_submission/local_resource_work_execution` (`launch_local`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_work_submission/hpc_resource_work_execution` (`launch_hpc`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/resource_result_acquisition` (`results`):

- `episode.py`: `__init__`, `child_roles`, `as_record`, `contract_information_profile`, `permitted_common_actions`, `capabilities`, `allowed_children`, `_adapter`, `instructions`, `decision_context`, `catalog`, `execute`.
- `requests.py`: `assignment_schema`, `_permitted`, `_require_launch_child_instruction_pins`, `prepare_assignment`.
- `returns.py`: `fact_sources`, `facts`, `received_form_references`, `initial_references`, `resolve`, `validate_report`.
- `credit.py`: `credit_kind`, `credit_view`.

`scientific_process/homology_job_submission` (`job_launch`):

- `episode.py`: `__init__`, `with_native_events`, `recover_native_events`, `bind_job_native_events`, `as_record`, `recover_statistics`, `instructions`, `describe`, `prospective_execution_classes`, `prospective_execution_options`, `working_state`, `binding_for`, `has_information_channel`, `catalog`, `execute`, `_execute`, `_validate_launch_return`, `_validate_monitor_return`, `_validate_results_return`, `_validate_role_return_sources`, `_validate_recorded_return`.
- `requests.py`: `commission_schemas`, `_query`, `assign`, `assignment`.
- `returns.py`: `fact_sources`, `resolve`, `facts`, `validate_report`.
- `credit.py`: `_launch_credit`, `_monitor_credit`, `_results_credit`, `initial_credit`, `credit_kind`, `credit_view`.
- `waiting.py`: `latest_sample`, `recorded_sample`, `latest_checked_status`, `received_timing_records`.

`scientific_process/homology_job_monitoring` (`job_monitor`):

- `episode.py`: `__init__`, `with_native_events`, `recover_native_events`, `bind_job_native_events`, `as_record`, `recover_statistics`, `instructions`, `describe`, `prospective_execution_classes`, `prospective_execution_options`, `working_state`, `binding_for`, `has_information_channel`, `catalog`, `execute`, `_execute`, `_validate_launch_return`, `_validate_monitor_return`, `_validate_results_return`, `_validate_role_return_sources`, `_validate_recorded_return`.
- `requests.py`: `commission_schemas`, `_query`, `assign`, `assignment`.
- `returns.py`: `fact_sources`, `resolve`, `facts`, `validate_report`.
- `credit.py`: `_launch_credit`, `_monitor_credit`, `_results_credit`, `initial_credit`, `credit_kind`, `credit_view`.
- `waiting.py`: `latest_sample`, `recorded_sample`, `latest_checked_status`, `received_timing_records`.

`scientific_process/homology_result_acquisition` (`job_results`):

- `episode.py`: `__init__`, `with_native_events`, `recover_native_events`, `bind_job_native_events`, `as_record`, `recover_statistics`, `instructions`, `describe`, `prospective_execution_classes`, `prospective_execution_options`, `working_state`, `binding_for`, `has_information_channel`, `catalog`, `execute`, `_execute`, `_validate_launch_return`, `_validate_monitor_return`, `_validate_results_return`, `_validate_role_return_sources`, `_validate_recorded_return`.
- `requests.py`: `commission_schemas`, `_query`, `assign`, `assignment`.
- `returns.py`: `fact_sources`, `resolve`, `facts`, `validate_report`.
- `credit.py`: `_launch_credit`, `_monitor_credit`, `_results_credit`, `initial_credit`, `credit_kind`, `credit_view`.
- `waiting.py`: `latest_sample`, `recorded_sample`, `latest_checked_status`, `received_timing_records`.


## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/execution_job_submission/api_job_execution` | `execution_job_submission/api_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission` | `execution_job_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_job_submission/hpc_job_execution` | `execution_job_submission/hpc_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission/local_job_execution` | `execution_job_submission/local_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_progress_assessment` | `execution_progress_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_result_acquisition` | `execution_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_job_monitoring` | `homology_job_monitoring` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_job_submission` | `homology_job_submission` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_result_acquisition` | `homology_result_acquisition` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning` | `hpc_work_planning` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` | `hpc_work_planning/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission` | `hpc_work_planning/execution_job_submission` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `hpc_work_planning/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `hpc_work_planning/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_progress_assessment` | `hpc_work_planning/execution_progress_assessment` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_result_acquisition` | `hpc_work_planning/execution_result_acquisition` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution` | `hpc_work_planning/hpc_allocation_execution` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
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
| `scientific_process/resource_result_acquisition` | `resource_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/api_resource_work_execution` | `resource_work_submission/api_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission` | `resource_work_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/hpc_resource_work_execution` | `resource_work_submission/hpc_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission/local_resource_work_execution` | `resource_work_submission/local_resource_work_execution` | private copy | resource_work_submission |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

## 2026-11-11 commissioning-parent correction recorded before relocation

The runtime action-schema audit corrects the earlier assumption that every entry role belongs beneath scientific_process. The legacy annotation/improvement source may commission entry roles directly (runtime.action_schema); the signed annotation collection restricts its own children to scientific_process. These are distinct parent contexts. Standalone entry bindings and their descendants therefore receive private axis-root homes below, while scientific-process descendants retain their own copies. The axis container remains an ownership folder, not an invented axis-head episode. Its legacy annotation parent is embedded in runtime.py and has no separate axis-head binding; legacy improvement recursion remains unresolved, rather than expanded into fictitious directories.

Homology job_child requires specialist is None. It cannot be commissioned by the scientific-process specialist. Its three homes move to the axis container; the earlier scientific-process placement is superseded. No new commissioning edge is introduced.

| Previous home | Final standalone home | Operation | Immediate commissioning parent |
| --- | --- | --- | --- |
| `scientific_process/execution_job_submission/api_job_execution` | `execution_job_submission/api_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission` | `execution_job_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_job_submission/hpc_job_execution` | `execution_job_submission/hpc_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_job_submission/local_job_execution` | `execution_job_submission/local_job_execution` | private copy | execution_job_submission |
| `scientific_process/execution_progress_assessment` | `execution_progress_assessment` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/execution_result_acquisition` | `execution_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_job_monitoring` | `homology_job_monitoring` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_job_submission` | `homology_job_submission` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/homology_result_acquisition` | `homology_result_acquisition` | move | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning` | `hpc_work_planning` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution` | `hpc_work_planning/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission` | `hpc_work_planning/execution_job_submission` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution` | `hpc_work_planning/execution_job_submission/hpc_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution` | `hpc_work_planning/execution_job_submission/local_job_execution` | private copy | hpc_work_planning/execution_job_submission |
| `scientific_process/hpc_work_planning/execution_progress_assessment` | `hpc_work_planning/execution_progress_assessment` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/execution_result_acquisition` | `hpc_work_planning/execution_result_acquisition` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution` | `hpc_work_planning/hpc_allocation_execution` | private copy | hpc_work_planning |
| `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution` | private copy | hpc_work_planning/hpc_allocation_execution/execution_job_submission |
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
| `scientific_process/resource_result_acquisition` | `resource_result_acquisition` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/api_resource_work_execution` | `resource_work_submission/api_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission` | `resource_work_submission` | private copy | legacy annotation in runtime.py (axis head absent); improvement fallback unresolved |
| `scientific_process/resource_work_submission/hpc_resource_work_execution` | `resource_work_submission/hpc_resource_work_execution` | private copy | resource_work_submission |
| `scientific_process/resource_work_submission/local_resource_work_execution` | `resource_work_submission/local_resource_work_execution` | private copy | resource_work_submission |

The role-token registry cannot register the standalone and scientific-process instances together, nor the repeated HPC descendants. Placement is complete for these finite declared parent edges; choosing a private parent at runtime and reopening old saved compositions remain unavailable. No parent silently falls back to another parent's implementation.

`homology_service_setup.py:create_homology_bindings` owns the plain legacy job construction helper formerly placed in scientific_process/episode.py; it registers no binding and supplies no shared task policy. The actual private classes remain in the three recorded homology homes.

## 2026-11-11 binding test ownership

Current direct literature tests now import the private role matching their explicit context; standalone parent contexts use the standalone copy. Tests that construct root/runtime workflows stay at the common axis test owner. Scientific graders, sheets and fixtures are shared by the independent standalone/scientific copies and retain the common axis owner. Historical combined tests with already-retired top-level imports remain unavailable; source placement does not repair their missing runtime.

No reviewed direct binding test is exclusive to one private episode: existing tests retain the common axis owner.

Shared required fixtures stay in `tests/fixtures/`; reusable named test helpers remain in `tests/` when imported by other tests. No fixture or helper is moved into disposable runs. The detailed support/test inventory records the final owners.

## 2026-11-11 final request-responsibility placement

The following existing incoming-assignment/schema/constraint methods move unchanged from each private episode.py class into that same home's requests.py mixin. These are method placements, not additional bindings or a change to admission behavior.

- `execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.
- `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/requests.py`: `_request_schema`, `_validate_request`, `_launch`, `_constraints`.

## 2026-11-11 final role and supporting-code index

The [complete ownership inventory](ownership_inventory.json) is the exact appendix to this record: it maps every original binding class to its singleton role, actual parent, final home, local method symbols and responsibility files. It also records every descriptive support module, its owner, imports, direct callers and consuming episodes; every library symbol and its explicit importing modules; and each test/helper and required fixture file. Unreferenced retained modules are recorded with empty consumers, not represented as active evidence or bindings. Shared scientific graders, readers, sheets and calculators keep their descriptive names at the common axis owner. Their functions are not merged with investigation credit.

| Original binding | Role | Final home | Parent | Supporting files |
| --- | --- | --- | --- | --- |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `execution_job_submission/api_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `execution_job_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `execution_job_submission/hpc_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `execution_job_submission/local_job_execution/episode.py` | execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `execution_progress_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `execution_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `homology_episode.py:HomologyEpisode` | `job_monitor` | `homology_job_monitoring/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py` |
| `homology_episode.py:HomologyEpisode` | `job_launch` | `homology_job_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py` |
| `homology_episode.py:HomologyEpisode` | `job_results` | `homology_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `hpc_work_planning/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `hpc_work_planning/execution_job_submission/api_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `hpc_work_planning/execution_job_submission/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `hpc_work_planning/execution_job_submission/hpc_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `hpc_work_planning/execution_job_submission/local_job_execution/episode.py` | hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `hpc_work_planning/execution_progress_assessment/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `hpc_work_planning/execution_result_acquisition/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `hpc_work_planning/hpc_allocation_execution/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/episode.py` | hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/episode.py` | hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `hpc_work_planning/hpc_resource_prediction/episode.py` | hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `published_evidence_assessment/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `resource_episode.py:ResourceEpisode` | `results` | `resource_result_acquisition/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `resource_work_submission/api_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch` | `resource_work_submission/episode.py` | legacy annotation in runtime.py; dedicated axis head absent; improvement fallback unresolved | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `resource_work_submission/hpc_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `resource_work_submission/local_resource_work_execution/episode.py` | resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `scientific_process_episode.py:ScientificProcessEpisode` | `scientific_process` | `scientific_process/episode.py` | root annotation; scientific_process self-recursion (not expanded) | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/execution_job_submission/api_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/execution_job_submission/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/execution_job_submission/local_job_execution/episode.py` | scientific_process/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/execution_progress_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/execution_result_acquisition/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc` | `scientific_process/hpc_work_planning/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/execution_job_submission/api_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/execution_job_submission/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/execution_job_submission/local_job_execution/episode.py` | scientific_process/hpc_work_planning/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/execution_progress_assessment/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/execution_result_acquisition/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_execution` | `scientific_process/hpc_work_planning/hpc_allocation_execution/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_api` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_hpc` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `launch_local` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `monitor_episode.py:MonitorEpisode` | `monitor` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `progress_observations.py`, `requests.py`, `returns.py`, `yield.py` |
| `execution_episode.py:ExecutionEpisode` | `results` | `scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/episode.py` | scientific_process/hpc_work_planning/hpc_allocation_execution | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `terminal_execution.py`, `yield.py` |
| `hpc_episode.py:HPCEpisode` | `hpc_prediction` | `scientific_process/hpc_work_planning/hpc_resource_prediction/episode.py` | scientific_process/hpc_work_planning | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature` | `scientific_process/published_evidence_assessment/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_strategy` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/episode.py` | scientific_process/published_evidence_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_search` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_page` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_targeted` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_ordered` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `literature_episode.py:LiteratureEpisode` | `literature_table` | `scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/episode.py` | scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination | `credit.py`, `episode.py`, `requests.py`, `returns.py`, `waiting.py`, `yield.py` |
| `resource_episode.py:ResourceEpisode` | `results` | `scientific_process/resource_result_acquisition/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_api` | `scientific_process/resource_work_submission/api_resource_work_execution/episode.py` | scientific_process/resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch` | `scientific_process/resource_work_submission/episode.py` | scientific_process | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_hpc` | `scientific_process/resource_work_submission/hpc_resource_work_execution/episode.py` | scientific_process/resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |
| `resource_episode.py:ResourceEpisode` | `launch_local` | `scientific_process/resource_work_submission/local_resource_work_execution/episode.py` | scientific_process/resource_work_submission | `credit.py`, `episode.py`, `requests.py`, `returns.py` |

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

## 2026-11-12 original negative bundle guards

Thirty private execution owners restore the original eleven-version exclusions before generic result parsing and resolution. Actual pre-change omission observations and the initial invalid-context fixture are retained separately. All thirty corrected constructor/Store/Journal/receipt checks pass after the two-guard change. The required helper and test live under `tests/`. This proves negative routing with malformed bundles; positive historical custody, receiving closure, private tasks, restoration, shared-root integration and autonomous science remain open.

## 2026-11-12 current private binding reconstruction

The axis composition reconstructs an explicit set of 43 current private binding identities and preserves complete descriptors, actual Store/run/services operands and caller-supplied credit. Before repair all direct constructors returned but composition raised `private_binding_reopen_pending`; after repair the identical construction and required identity/rejection checks pass. This controlled diagnostic does not establish the full application factory, historical migration, receiving authority, all private tasks/messages, independent saved reopening or autonomous science. Historical descriptors and earlier scientific milestones remain unchanged.

## 2026-11-12 API V2 private task connection

Six API children now select their private complete task/state/instructions/presentation with exact original saved branches. Six parent selectors route API returns through their private receiver. Actual local preparation, invalid outcomes, original progress/replay and provider frame/fallback checks pass 162 named cases before and after installation. Synthetic parent admission is separately classified. Remote native custody, full restoration, broad receiving closure and autonomy are not established.

## 2026-11-12 API instruction-service correction

Six actual private API task classes again call the original instruction service, preserving custom returned-object and exception identity. The default service selects each declared private composer; absent and None nonparticipants retain the original fallback. The recorded baseline has twelve custom-callback mismatches, all corrected in the installed observation. Twenty-six exact instruction-only unit cases pass. These checks use controlled instruction ports and do not establish constructors, native work, scientific results or full workflow restoration. The preceding API task stage and its original evidence remain preserved.

## 2026-11-12 Existing private task instruction callback correction

The recorded 24-file two-axis correction restores each original instruction service callback and declares its unchanged private composer as a static class selection. All 392 exact instruction-boundary cases pass in the linked actual evidence, preserving private default text and generic nonparticipant fallback. Scope is actual task/service methods with controlled ports; constructors, native/scientific work, full restoration and autonomy are not established. Earlier validation and descriptors remain historical. Current source fingerprints and explicit old/new source transitions are recorded separately.

## 2026-11-12 source-family V4 organizational tasks and substantive request assembly

Fourteen source-reading homes now select their private complete task, instructions and original presentation policy; twelve internal child exchanges have substantive outgoing request assembly and named receipt owners. The original selected assignment reaches child admission once, and original request construction retains its transaction, identity and knowledge inheritance order. Direct and nonparticipating builds retain their original call and fallback. The actual 318-case baseline and 540-case installed suite preserve returned invalid/failed/unavailable outcomes, original action/receipt identities, saved replay, immutable request comparison, and provider frame/JSON/priority behavior. The separate actual 44/58 instruction cases preserve custom callbacks and default private composers after the authenticated seven-file hook and twelve-file A103 portion of the full24/392 callback correction with its 56-file metadata. Fourteen actual service checks still raise the inherited scientific_task_credit_not_declared error. Controlled zero-credit connection fixtures and constructor observation stops do not supply production scientific credit. Full workflow restoration, broad receiving authority, autonomous science and shared-root integration are not established.

## 2026-11-12 Launch V4 private task and named child receiving connections

Six Launch homes now select complete private tasks, state, instructions and original provider presentation. Twelve named local/HPC child receiving endpoints are connected at those Launch parents; their child implementations are unchanged. The six original API receiver bodies remain exact. Actual baseline and installed suites each passed 204 named controlled cases, and full raw constructor/action/progress/admission observations match except the declared task type. Historical receipt custody, complete child private tasks, broad receiving authority, full restoration, autonomous science and shared-root integration are not established by this stage.

## 2026-11-12 Native child private task connections

Twelve original local/HPC child private tasks and messages; preserved six Launch receiver portfolios; four unchanged HPC descriptor footprint transitions. Actual evidence is linked below in the corresponding inventory stage; this controlled engineering validation is not native/scientific execution or full restoration. Historical stages and descriptors are retained.

## Installed private Resource ownership (2026-11-13)

Ten Resource homes have installed private tasks and bindings. Their current inventories record the exact installed source epoch and original destinations. The final behavioral union remains pending; implementation ownership and scientific workflow validation are separate.

Current selected private ownership reconciliation: exact finite source authority `runs/root_a102_a103_installed_prompt_selection_preparation_01/SOURCE_SELECTION.json` supplies the current head, private source, Resource and parent-private records. The earlier request/return-era current catalogues and three former top-level Homology bindings have explicit historical custody in the inventory. Actual current methods, source membership, source fingerprints, import consumers and message endpoints are recorded there. Candidate implementation and canonical installation remain separate; this metadata preparation executes no tests.

Installed existing12 responsibility successor:98 new private owners and114 changed existing modules are accounted across12 homes, with complete398 own-module catalogues and refreshed current source/receiver/call facts. Actual source application: `runs/root_a103_existing12_source_application_01/applied/application.json`. Current source map5088 (A1032627), original descriptor/validation history and other44 fingerprint values remain separately qualified.

Installed HPC-child12 responsibility successor:100 new private owners and108 changed existing modules are accounted across12 homes, with complete424 own-module catalogues and refreshed current source/receiver/call facts. Actual source application: `runs/root_next36_source_application_01/applied/application.json`. Current source map5338 (A1032727), original descriptor/validation history and other44 fingerprint values remain separately qualified.

Installed execution30 responsibility successor:240 new private modules and162 changed existing modules across30 homes, complete1266 own-module catalogues, both message directions, actual private provider/context/history owners and18 named Launch outgoing endpoints. Actual source application: `runs/root_execution60_source_application_01/applied/application.json`. Current combined source5728/A1032967; original descriptor/validation histories and other44 formulas remain separately qualified.

Current remaining30 ownership covers Resource10, SourceFamily14 and Homology6: 429 distinct source targets and 252 additions. The complete A103 map contains 3219 modules. Thirty-two already-owned external inventories receive current endpoint joins; these are not additional organization gaps. Actual source application: `runs/root_remaining40_source_application_01/applied/application.json`.


## 2026-11-13 prepared final parent exchanges

Six existing parent exchanges own complete typed request and saved/failure/nonreceipt admission. Actual18 covers Scientific recursion/Literature; corrected actual36 covers legacy annotation Resource2/Literature/Scientific. The initial36 attempt remains28 failed/8 passed and is not added again. Original typed errors, saved report reuse, failed-action credit replay, mutable runtime identities and custom fallback are retained with scientific/context/credit ports explicitly controlled. Source installation remains pending; installed child30/838/96 remains unchanged. The original whole-axis formula has3233 proposed operands; legacy annotation uses its unchanged sorted-byte formula over28 immediate sources. Current accounts: `runs/fourth_a103_parent_metadata_generation_01/prepared/FINGERPRINT.json` and `runs/fourth_a103_parent_metadata_generation_01/prepared/LEGACY_FINGERPRINT.json`. Actual results: `runs/root_a103_parent_exchange18_01/verification.json` and `runs/root_a103_parent36_02/verification.json`. Scientific policy admits only recursion/Literature; excluded factory groups and generic protocol/storage responsibilities are recorded in `runs/root_a103_final_parent_metadata_preparation_02/CENSUS.json`. No scientific/native execution or complete restoration is claimed.


## 2026-11-13 current report, action and commissioning policy

Current policy sources, exact private configuration and all150 private task/report consumers are recorded in `runs/fourth_a103_policy_metadata04_01/prepared/CALLER_OWNERSHIP.json`. Actual shared scientific return forms and report assembly have explicit same-axis library owners; Scientific snapshot qualification and annotation projection/commissioning retain their actual defining homes. Generic protocol, storage and iterator mechanics remain separately recorded. All75 existing private homes retain their actual descriptor formula and configuration; no implementation hash is invented for a descriptor without one. Actual report13, commissioning16 and cold30 retain separate source/input epochs in `runs/fourth_a103_policy_metadata04_01/prepared/CONTROLLED_EVIDENCE.json`. Existing parent18/36 and child milestones are not rerun or relabelled. The updated JSON inventory records current source facts and raw prior values. This preparation is not installation: actual installation status requires the application and complete postchecks recorded in `docs/EVIDENCE_AXIS_LEDGER.md`.


## 2026-11-13 Scientific owners and original provider preservation

Current Scientific definitions and original runtime, provider and prompt namespace lookups are recorded in `runs/main_a103_final_provider152_metadata_01/prepared/PROVIDER_OWNERSHIP.json`. The two retired module bodies have exact per-symbol private owners; the current support roster retains3246 actual source files. All75 existing private homes keep their own original descriptor formula and configuration. Configuration-only records receive no invented source digest. The 150 existing policy consumers remain linked in `runs/main_a103_final_provider152_metadata_01/prepared/CALLER_OWNERSHIP.json`. Actual provider48 and installed Scientific39 retain their literal source/input epochs; earlier report13, commissioning16, cold30, parent18/36 and child outcomes remain historical successful scopes. These source and supplied-port controls do not establish a complete native, scientific or restored workflow. Current installation status requires the actual application and complete postchecks in `docs/EVIDENCE_AXIS_LEDGER.md`.


## Historical standalone annotation-parent narrative

# A103 legacy_annotation ownership

This predefined `annotation` episode has its actual implementation in this directory. This metadata is prepared with the parent-private source and constructor-excluded head-guard cleanup; it does not claim canonical installation or runtime validation.

The declaration in episode.py selects LegacyAnnotationTask and the actual LegacyAnnotationEpisode. The current implementation fingerprint is adac13b5ab008e8826d817eb5655869adc1312dd5a0afcd57f3667f8b9d6c6ac, computed from the 19 exact top-level Python files recorded in ownership_inventory.json. The prior fingerprint adac13b5ab008e8826d817eb5655869adc1312dd5a0afcd57f3667f8b9d6c6ac remains historical; saved descriptor equality is unchanged.

| File | Responsibility |
| --- | --- |
| __init__.py | Existing package marker; contains no behavior claim. |
| credit.py | Apply the configured original operational, monitoring or parent scientific progress projection. |
| decision_delivery.py | Use the configured provider and original pending/completed decision exchange protocol. |
| episode.py | Declare the concrete parent or child and connect its private task, prompt and binding mixins. |
| from_child_homology_job_monitoring.py | Admit this named child’s original typed response into the actual parent state. |
| from_child_homology_job_submission.py | Admit this named child’s original typed response into the actual parent state. |
| from_child_homology_result_acquisition.py | Admit this named child’s original typed response into the actual parent state. |
| from_parent.py | Validate and admit the original scoped assignment and immutable execution request. |
| goal.py | Interpret the commissioned goal and declare the original applicable work and progress meaning. |
| instructions.py | Compose the private instruction text while preserving the original injected instruction service. |
| internal_summary.py | Present actual working state, assigned work and retained information to the decision process. |
| task.py | Choose, acquire and execute actual work; retain original outcome, credit, replay and decision-loop paths. |
| task_state.py | Construct the exact own role/parent identity; retain action state, failure capture, restore and checkpoints. |
| task_waiting.py | Record changes to the source suspension condition. |
| to_child_homology_job_monitoring.py | Prepare this parent’s original request to the child named by the file. |
| to_child_homology_job_submission.py | Prepare this parent’s original request to the child named by the file. |
| to_child_homology_result_acquisition.py | Prepare this parent’s original request to the child named by the file. |
| to_parent.py | Select, validate and present requested facts and qualifications to the actual parent. |
| yield.py | Bind the original caller-supplied continuation controller and its unchanged task context/settings. |

This parent commissions the three private child homes below. Its own incoming assignment, credit and yield implementation remain explicit.

- gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/to_child_homology_job_submission.py -> gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/homology_job_submission/from_parent.py
- gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/homology_job_submission/to_parent.py -> gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/from_child_homology_job_submission.py

- gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/to_child_homology_job_monitoring.py -> gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/homology_job_monitoring/from_parent.py
- gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/homology_job_monitoring/to_parent.py -> gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/from_child_homology_job_monitoring.py

- gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/to_child_homology_result_acquisition.py -> gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/homology_result_acquisition/from_parent.py
- gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/homology_result_acquisition/to_parent.py -> gene_annotation_episode/episodic_workflow/root/a103/legacy_annotation/from_child_homology_result_acquisition.py

Original reasoning/replay, executed failed/invalid/unavailable outcomes, waiting, callback credit and report identity remain unchanged. The removed head guards belonged only to the six private Homology children: submission, monitoring and result acquisition under each of legacy_annotation and legacy_improvement. Each child's exact constructor role and parent checks exclude the scientific_process role; the real scientific head retains those guards. This parent's implementation is unchanged by that twelve-file cleanup. Applicable controller/Store/native services remain explicit external dependencies in the inventory. No new scientific episode, grader, score or continuation rule is introduced.

Three existing saved-parent-counterpart cases jointly cover the six children and both actual parents. Their future results must be reported separately from source review, prior test epochs and cross-release restoration. Tests/helpers remain at a103/tests and the existing private monitoring test directory; this metadata creates no test or fixture. Broader source-family/resource metadata and complete scientific workflow validation remain separate.


## 2026-11-13 prepared final parent exchanges

Six existing parent exchanges own complete typed request and saved/failure/nonreceipt admission. Actual18 covers Scientific recursion/Literature; corrected actual36 covers legacy annotation Resource2/Literature/Scientific. The initial36 attempt remains28 failed/8 passed and is not added again. Original typed errors, saved report reuse, failed-action credit replay, mutable runtime identities and custom fallback are retained with scientific/context/credit ports explicitly controlled. Source installation remains pending; installed child30/838/96 remains unchanged. The original whole-axis formula has3233 proposed operands; legacy annotation uses its unchanged sorted-byte formula over28 immediate sources. Current accounts: `runs/fourth_a103_parent_metadata_generation_01/prepared/FINGERPRINT.json` and `runs/fourth_a103_parent_metadata_generation_01/prepared/LEGACY_FINGERPRINT.json`. Actual results: `runs/root_a103_parent_exchange18_01/verification.json` and `runs/root_a103_parent36_02/verification.json`. Scientific policy admits only recursion/Literature; excluded factory groups and generic protocol/storage responsibilities are recorded in `runs/root_a103_final_parent_metadata_preparation_02/CENSUS.json`. No scientific/native execution or complete restoration is claimed.


## 2026-11-13 current report, action and commissioning policy

Current policy sources, exact private configuration and all150 private task/report consumers are recorded in `runs/fourth_a103_policy_metadata04_01/prepared/CALLER_OWNERSHIP.json`. Actual shared scientific return forms and report assembly have explicit same-axis library owners; Scientific snapshot qualification and annotation projection/commissioning retain their actual defining homes. Generic protocol, storage and iterator mechanics remain separately recorded. All75 existing private homes retain their actual descriptor formula and configuration; no implementation hash is invented for a descriptor without one. Actual report13, commissioning16 and cold30 retain separate source/input epochs in `runs/fourth_a103_policy_metadata04_01/prepared/CONTROLLED_EVIDENCE.json`. Existing parent18/36 and child milestones are not rerun or relabelled. The updated JSON inventory records current source facts and raw prior values. This preparation is not installation: actual installation status requires the application and complete postchecks recorded in `docs/EVIDENCE_AXIS_LEDGER.md`.


## 2026-11-13 Scientific owners and original provider preservation

Current Scientific definitions and original runtime, provider and prompt namespace lookups are recorded in `runs/main_a103_final_provider152_metadata_01/prepared/PROVIDER_OWNERSHIP.json`. The two retired module bodies have exact per-symbol private owners; the current support roster retains3246 actual source files. All75 existing private homes keep their own original descriptor formula and configuration. Configuration-only records receive no invented source digest. The 150 existing policy consumers remain linked in `runs/main_a103_final_provider152_metadata_01/prepared/CALLER_OWNERSHIP.json`. Actual provider48 and installed Scientific39 retain their literal source/input epochs; earlier report13, commissioning16, cold30, parent18/36 and child outcomes remain historical successful scopes. These source and supplied-port controls do not establish a complete native, scientific or restored workflow. Current installation status requires the actual application and complete postchecks in `docs/EVIDENCE_AXIS_LEDGER.md`.


## 2026-11-13 Current hierarchy and directional ownership

Current physical home: `a103/`. Its current source, actual binding declarations, descriptor operands and explicit private/shared responsibility split are recorded in `ownership_inventory.json` under the root `bindings` entry with `home: ""`. This section supersedes earlier current-layout statements; those original bytes remain above as historical evidence. Four existing physical homes moved without changing their runtime roles or binding identifiers. The six completed parent exchanges, six Resource returns and shared late HPC policy retain their original callback/error order. Nested improvement task-aware credit/yield refusals and Scientific child whitelist remain literal. Actual affected85 is the explicit retained53 plus affected32 union; the initial failed85 remains literal history. Earlier provider48 and Scientific39 retain their own source epochs. No complete scientific/native/restored workflow execution is inferred. Installation status requires actual application and complete postchecks in `docs/EVIDENCE_AXIS_LEDGER.md`.
