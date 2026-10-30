# Shared registration consumer trace

These are implementation observations, not a replacement goal. The exact changed
functions are listed in CHANGED_FUNCTIONS.json. Numerical semantics remain491's
responsibility; native production remains492's; result workers, qualification,
return custody and original acquisition accounting remain493's. Root494 owns
practical operations, selected input metadata and input-version validation.

## Selection and initialization

ExecutionServiceFactory supplies ExecutionEpisodes.resource_tool_contracts to
ScientificToolLibrary.freeze. Barcode contracts come from
native_barcode_tool_information.barcode_tool_contracts and require an explicit
local operation/software binding. ScientificToolLibrary.resolve_tool_info keeps
the substantive selected instructions, while resolve_invocations supplies the
actual commission route. There is no direct unscoped ToolRegistry execution and
no invented native job mode.

ExecutionEpisodes validates configured barcode bindings during construction and
constructs NativeBarcodeResults before BarcodeReturns. _request_schema and
assignment_schema expose the exact configured request and barcode selector.
prepare_assignment, initialize and _check_parent_inputs call _barcode_inputs and
pass the exact selected barcode assignments to validate_execution_input_versions.
The root-owned operand reader validates the original received prefix, all three
non-null input roles, Store metadata and selected Store paths. Commissioning
does not reopen scientific input bytes. The selected native producer owns byte
validation at execution.

The initialization/reference hooks are consumed by EpisodeBindingRegistry and
Workflow's existing binding construction. _barcode_reference_access precedes
generic reference fallback and preserves explicit denial for protected files.
initial_references admits only actual received selected inputs, the selected
handoff and an authenticated received saved sheet when selected.

## Original target and selected execution

ExecutionTargetReader._native authenticates the original resource, operation
key, attempt digest and expected native.json path. describe_execution_target and
describe_target expose actual barcode format information. returnable_handoff
retains qualified failed native attempts for later partial acquisition through
the existing mechanism. No polling, cancellation or scheduling rule is added.

ExecutionEpisodes._target/_selector and retained_target preserve original target
custody for native or saved selection. catalog and execute dispatch to the493
host. The saved route requires the received barcode_sheet_v1 and does not depend
on live source/native files. Its worker plan contains the saved sheet and
selected parameters/projection only. Original result replay returns the existing
immutable selected-action outcome.

## Requested communication

communication._compile_closed_schema permits the exact registered top-level
barcode fact schemas, rejecting mutation and nesting. _validate_form runs the
barcode semantic validator and registered JSON-schema validation;
_validate_form_semantics preserves meaningful reference checks. Existing NMF,
ATAC and other registered families retain their own validators.

ExecutionEpisodes.fact_sources and received_report_sources expose only the three
public barcode sources. facts and received_report_facts populate requested
records through493. Private contribution-origin and forwarding-prefix records
remain runtime facts; they are not public schema fields or data authority.
The existing execution_result_origin source separately admits barcode's declared
acquisition-semantics labels; those labels are not the private population lineage
used to prevent duplicate credit.

Workflow builds typed forms using the binding facts, validates each original
return, stores runtime_forms, and calls received_form_references during delivery.
The registration forwards validate_report/validate_received_report, exact form
admission and received reference resolution to493's original-frame reader.
Measurement-only returns convey neither saved-sheet nor native-file access.
Receipt inheritance and frozen return prefixes delimit later forwarding.

## Credit and continuation

project_credit consumes493's original acquired population count. Saved
recalculation and already received population origins earn no new acquisition
credit. The private origin records prevent duplicate credit without granting
scientific operands. The generic native completion fallback explicitly declines
barcode, while completion_for_action and verify_completion consume the barcode
host's validated original action proof.

Workflow's existing source-credit, selected-action completion and ordinary
controller paths consume these hooks. Registration does not append observations,
reprice old records, supply synthetic timer/report observations or change the
controller. The scripted component tests intentionally create no method_loop
observations; root496 separately verifies the actual shared Workflow path.

## Presentation and test boundary

The result library describes actual native artifacts, parsers, calculators and
selected projection. The existing provider fallback for ordinary execution
contexts remains an unfinished message boundary documented separately in
BOUNDARIES_AND_CONCURRENT_CHANGES.md. No prompt template was changed.

Shared verification uses actual configured software, actual native and finite
result workers, authored selected-context/action/form records, and unchanged
NMF/ATAC targeted regressions. It does not establish actual model decisions or a
complete Workflow by itself. All application imports and pytest/native work run
inside original native_lifecycle handles with 20 GiB RAM, 4 GiB scratch, zero
swap and no wall limit, with frozen sources and runtime/dependency pins.
