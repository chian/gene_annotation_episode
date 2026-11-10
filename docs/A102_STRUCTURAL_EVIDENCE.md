# A102 structural evidence integration

The opt-in contract `a102_structural_evidence_v2` places comparative and
experimental structure under A102. Its new catalog contains A101–A107 and
A110. A111 is absent from new selection in this catalog. Existing publications,
frozen runs, comparative-only entry points and experimental formula versions
are preserved.

Implementation is written and reviewed at source level. **No tests or workflows
have been run for this change.** End-to-end behavior and compatibility with the
concurrent HPC changes remain to be validated when testing resumes.

## Composition

Use these three entry points together for a new run:

```python
from gene_annotation_episode.a102_structural_workflow import (
    A102StructuralEvidenceServiceFactory,
    A102StructuralEvidenceSubtree,
    create_a102_structural_evidence_workflow,
)
```

`A102StructuralEvidenceServiceFactory` accepts the same dataclass arguments as
`A102ServiceFactory`, including the explicit source publication, tool retrieval,
additional services and resource catalogs. The selected source must be an
unmerged ten-axis publication such as
`research/slotted_process_library/publications/2026-10-24-001`.

For the current execution/HPC family, supply the caller's configured
`ExecutionServiceFactory` as `execution_service_factory`. The merge factory
delegates to it and retains its resource catalogs, progress provider, result
readers and configured HPC prediction/execution branches. It advertises the
actual entry roles and freezes the catalog after registry configuration. This
composition does not also install the legacy local A102 resource adapter.
Conflicting service, credit or resource definitions are rejected rather than
overwritten. Include the execution factory's `as_record()` in the explicit
service-binding definition used for reconstruction. Omitting this port retains
the original A102 service composition.

The factory creates `structural-evidence-catalog/` beneath the caller's run
directory and freezes it through the existing scientific library setup. It
combines A102/A111 instruction provenance, records a source-ID migration map
and original content hashes, and preserves all unaffected entry bytes. This
derived catalog is reproducible from application code and the retained source
publication; it is not the only home of required code or assets. Reconstruction
uses the frozen run library without substituting a newer source publication.
The destination cannot overlap the source publication; an existing destination
must have exactly the expected files, including no remaining A111 entry.

Pass the factory as `episode_service_factory` and its explicit versioned setup
description as `episode_service_binding` to
`create_a102_structural_evidence_workflow`. Supply the configured registry using
the existing `episode_service_inputs='actual_tool_registry_v1'` interface when
native execution services are wanted. Other arguments, including the provider,
controller, initial receipt list and allowed root child roles, remain explicit
caller configuration. This helper installs no stopping budget or executor.

After workflow construction, instantiate `A102StructuralEvidenceSubtree` with
the same workflow directory. Its `commission` method has the legacy subtree's
operands: target, scope, completeness, actual tool selections, question,
optional evidence and constraints. Its default task is `synthesis`.

| Task family | Tasks | Controller meaning |
|---|---|---|
| Shared | `model_inventory`, `target_model_correspondence`, `synthesis` | Received, current retained scientific findings |
| Comparative | `structural_discovery`, `native_comparison`, `functional_feature_geometry`, `functional_contrast`, `reference_attribution`, `local_trait_attribution`, `interface_constraints` | Existing native or specifically attributed correspondence |
| Experimental | `experimental_source_discovery`, `experimental_model_identity`, `experimental_feature_geometry`, `experimental_local_validation`, `experimental_assessment` | Received, current retained scientific findings |

One finding unit is the existing explicit `FindingProgressPolicy(1)` convention;
it is not an experimental support score. The shared parent also uses finding
progress and does not sum child scores. A direct scientific commission selecting
the merged entry without a task context is treated as shared work. Explicit task
contexts are validated against the contract produced by `task_context`.

The existing `LiteratureEpisodes(rate_population=True)` binding supplies
`literature.structure.populate`, `requested_structure_components`,
`literature_structure_cells` and authenticated delivery across episode roles.
This option is the existing umbrella switch for experimental population
families; it does not require kinetic analysis. The scientific prompt scopes
work to structure and the configured tool information controls availability.
An experimental child chooses applicable literature operations using the normal
episode commission mechanism.
Enabling population preserves the literature descriptor's other configuration.

## HPC comparison and automatic numerical admission

With a configured `ExecutionServiceFactory.hpc_commissions`, the merged factory
binds the actual HPC resources to the A102 registry before freezing tool
information. `structure.request_hpc_comparison` then becomes available. Without
that configured HPC owner, this operation is absent from the callable catalog.

The operation selects received structural bindings, US-align or Foldseek, and a
configured resource. A US-align request has one reference; Foldseek retains the
existing bounded panel of at most 32. A reference-only measured model also
requires explicit target regions and optional received sequence-correspondence
operands. Direct target models and reference-to-target transfer stay separate.
No function annotation is required.

The operation freezes the original inputs, software pins and a source snapshot
of the existing native implementation. Its result contains a host-issued
`commission_source_ref` and `hpc_assignment` for the normal `hpc` child. The
existing HPC parent and its prediction/execution sisters own the next decisions,
staging, allocation, monitoring and collection. Scientific commands do not run
as part of request preparation. Official software assets can be acquired during
Launch; compilation and structural algorithms execute inside the allocation.
Existing completed, received requests are reused.

`a102_hpc_worker.py` calls the existing `a102_native_worker` algorithms from the
staged, hash-pinned package. It writes the original unit's `result.json`, as
required by `hpc.results`. The original native output is also retained on the
compute side. The compact result uses a bounded compressed payload; an output
too large for the existing 512 KiB HPC collection contract reports the need for
a smaller reference panel rather than silently dropping comparisons.

After the result reaches a scientific receiver, the normal receipt callback
automatically runs A102 admission. `hpc_result_receipts.read_received_result`
uses the configured HPC owner's original ledger and publication interfaces. It
checks the completed collection, original unit, result bytes, plan and scope.
The A102 adapter checks the original staged implementation/request, Python
command, software pins, compute/job identity, model bindings, maps and geometry.
Qualified comparisons call the existing `publish_comparison` grader; no new
alignment or fit occurs on the receiving machine. The resulting grants then
enter the existing attribution refresh and comparative scorer.

Execution addresses, commands and stdout identities stay attached to the
received HPC admission. Identical comparison data retain the same numerical
identity across repeated delivery; another job address alone does not create a
new primary comparison. Changed scientific variants retain the existing
comparative variant rules. Failed execution, unavailable admission and missing
target bindings are explicit parent-visible states with no B grant. Later
receipt of missing bindings triggers admission through the same callback.

The same callback also consumes explicitly admitted ordinary/native saved-sheet
descriptors through `publish_received_comparisons`. The existing return authority
validates the selected recalculation grant before the adapter opens any saved
numerical artifact. This closes the former dependency on an active ordinary
tool invocation. A Source handle or an unselected projection still cannot grant
the whole sheet. The original producer callback remains compatible.

This A102 route uses the completed `HPCEpisodes` service directly. It does not
enable or depend on the separate legacy `native_protein_structure` PBS resource
binding. Its local-only guard is therefore not a blocker for this integration.

## Parent consumption

The default return includes separate comparative/experimental applicability,
source records, experimental numerical cells, scope qualifications, subject
correspondence references and information needs. `controller_progress` is
labelled separately from scientific results.

For the merged catalog, the scientific binding uses the existing
`initial_decision_context` callback, which the runtime invokes on fresh model
calls. Annotation and scientific parents receive `received_structural_evidence`
automatically after ordinary child-return admission. Its `reports` retain the
original commissioning goal and scope alongside resolved components. The
existing `EpisodeReturnRecords` reader authenticates the original immediate
child, contract, returned form and frozen host facts. Resolution then uses the
receiving episode's actual record and numerical-cell receipts.

The parent view also builds a union keyed by original sheet/component and
comparison/attachment Source. This connects shared dependencies and assessment
revisions across different child returns, without adding child credits or
counting a redelivered legacy sheet as another observation. Original per-return
interpretations remain visible. No runtime, HPC or native producer change is
needed for this presentation hook.

Applications needing to resolve one admitted return explicitly can still call:

```python
from gene_annotation_episode.a102_structural_report import resolve_report

resolved = resolve_report(
    store,
    admitted_form,
    context=receiving_episode_context,
    structure_repository=services.literature_structure_repository(),
)
```

The context must contain the receiver's actual receipts. The repository must
belong to the same Store/run. Validation uses `validate_fact_values`, so a
received sheet reference cannot expose components that were not delivered.
The adapter preserves the original assessment scope separately from receiving
scope. It exposes model/revision/source identity and selections without copying
unrequested raw validation measurements into the return.
It retains the saved calculation version rather than relabelling historical
cells with the currently imported version. Acquisition provenance includes
the original Source identities, artifacts, requests and retrieval metadata.
Local validation retains its granularity, native metric, selectors, missing
reasons and original saved-value locations. Those locations identify provenance;
they do not admit additional numbers or authorize opening a private artifact.
Native RSCC values require the existing separately authorized source reader.

Merged-report validation also runs at the reporting boundary. It refreshes only
the reporting episode's actual durable receipts when a stored commission context
predates the child's acquisitions. An evidence-returned/partial interpretation
requires the corresponding delivered records or cells.

Comparative results are resolved through the existing native numerical grants
and `A102StructuralCredit`. `correspondence_B` remains `None` when no eligible
correspondence exists; a measured eligible zero is retained. An unresolved
reference attribution does not make B available; it needs an
actual projected correspondence in the existing comparative sheet. Feature, contrast,
trait and interface sheets stay separate. Experimental-only work requires no
alignment and reports no comparative B. Experimental rows retain all six
existing component meanings, bounds, conditions and missing reasons:
`local_fit_index`, `geometry_support_fraction`, `geometry_opposition_fraction`,
`source_geometry_positive`, `source_geometry_opposing`, `source_geometry_signed`.

Experiment identity, shared source provenance, coordinate-file identity and
deposited-entry/revision identity, structural bindings and attachment measurement
origins are distinguished. Shared identities connect uses
without deleting different questions or observations. Revisions among delivered
assessments mark superseded results and unresolved heads. Missing predecessors
remain explicit; this adapter does not discover private replacement assessments.
Unlinked uses are not declared independent. There is no numerical aggregation
that could count a legacy A111 sheet again as a new observation.

Target transfer is not established by source geometry. Correspondence records
and source-bound claim assessments retain that separate responsibility. The
existing run and delivery boundaries also apply to legacy sheets; this change
does not introduce a cross-run import bypass.

`combined_scientific_score` is `None`, with an explicit missing combination-policy
status. Consumers requiring one scalar must not substitute B, finding progress
or a sum/product of experimental and comparative components. A final scalar
policy remains a separate scientific decision, as specified in the merge plan.

## Concurrent work and deferred validation

The new modules own instructions/catalog transformation, experimental views,
reports, A102 HPC requests/admission and composition. Shared edits cover
implementation hashes, instruction/progress selection, report validation,
parent context and receipt-adapter injection. Existing execution-planning and
A104 changes are preserved. Runtime supplies the actual configured scientific
and HPC return authorities; it does not choose or submit structural work.

Native execution remains delegated to the original `A102ServiceFactory` or the
explicitly configured current `ExecutionServiceFactory`. This
integration adds narrow request/configuration and receipt-adapter methods to
`a102_tools.py`, plus the common saved-comparison bridge. Native algorithms,
native setup, resource adapters, numerical formulas, scheduler, HPC prediction,
monitoring, launch and result publication implementations remain intact. Actual
tool availability remains supplied by the configured registry. Experimental
cells continue through their independent authenticated literature interface.

The [goal](A102_STRUCTURAL_EVIDENCE_MERGE_GOAL.md) and
[plan](A102_STRUCTURAL_EVIDENCE_MERGE_PLAN.md) retain the validation conditions:
comparative-only, experimental-only, both paths sharing a structure,
missing/conflicting evidence and legacy evidence, through actual parent
consumption. Those full workflows remain deferred. No passing-test claim or
validated-completion claim is made.
