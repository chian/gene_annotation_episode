# Source trace and modular implementation boundary 453/002

This accompanies `CONTRACT_001.md` and the exact copied examples. Read
`SCHEMA_AND_LIFETIME_CLARIFICATIONS_003.md` with the contract. All three are
planning records, not production implementation or approved prompt templates.

## Observed complete path

The missing capability is an operand-selection transport, not an absent native
alignment or saved-sheet calculation. The following functions were inspected
through their relevant complete implementations, including their callers and
consumers. Source inspection is not a claim that the proposed path was run.

| Stage | Current source and function | Consequence for the proposal |
|---|---|---|
| Authoritative operations | `runtime.py:Workflow.action_schema`; `ScientificProcessEpisodes.catalog`, `common_tool_names`; `tools.py:ToolRegistry.catalog`; `ExecutionEpisodes.assignment_schema` | The frozen original operations, roles, arguments and result selectors remain authoritative. No root tool restoration. |
| Provider transport | `runtime.py:_action_generation_schema`, `_json_episode_assignment`, `_json_tool_arguments`, `_embedded_tool_schema`, `_decode_action_response` | Assignments and composed arguments can be JSON strings. Adapt the semantic schema before this existing encoding, then decode using the adapted semantic schema. |
| Frozen decision request | `runtime.py:DecisionSource.call`, `next`, `instructions`, `exchange_schema`, `exchange_response`, `validate_contract_exchange_request`, `validate_contract_exchange_history`, `exchange_decision`, `apply_response` | Persist private bindings before dispatch; use the same binding for every lookup/reconstruction; resolve before ordinary action admission. |
| Exact schema lookup | `composition_information.py:lookup_schema`, `metadata_catalog`; `runtime.py:Workflow.freeze_contract_information`, `validate_contract_information`, `pending_contract_information`, `contract_information_reply`; `episode_contract_information.py:operation_contract_information`, `return_contract_information` | Existing lookup supplies original contracts, not actual received operands. Add a separate received-operands branch; never turn schema lookup into source access. |
| Model state | `decision_context.py:instructional_model_context`, `model_snapshot`, `state_frame`, `apply_state_frame`; `providers.py:_SessionConnection.complete`, `_presentation` | Private mappings never enter context or frame hashes. Scientific presentation must work for full contexts, bootstrap, updates, lookup continuations and restoration. |
| Scientific text | `scientific_process_prompt.py:_task`, `_received_records`, `_outcome`, `_lookup`, `_information`, `_steering`, `render_episode_steering`, `render_scientific_process_prompt` | Full TASK repeats; typed result fragments are selected/rendered before generic value-table fallbacks. A whole-bundle dump is not an operand interface. |
| Own history | `decision_history.py:_selected_inputs`, `_saved_selection`, `_lookup_detail`, `_record`, `lookup_attempts`; `runtime.py:Workflow._history_rows`, `history_preview`, `history_read` | Historical exact actions remain exact. A typed presentation adapter handles these families' actual operand locations, including detail slices, without treating a historical value as a current grant. |
| Child admission | `runtime.py:Workflow.selected`; `episode_bindings.py:initial_decision_context`, `_received_report_mapping`, `received_report_sources`, `received_report_facts`, `resolve_received_reference`; `ExecutionEpisodes.prepare_assignment`, `_retained_protein_result`, `_retained_genomic_overlap_target`, `_selector` | Only expanded ordinary assignments reach original child validation. A private received-operand port must be distinct from public initial context. |
| Alignment authority | `ScientificProcessEpisodes.execute`; `episode_services.py:authenticate_structure_alignment_operands`; `protein_structure_operands.py:_sequence`, `authenticate_structure_sequence_reference`; `ToolRegistry._alignment_arguments`, `_prepare_alignment_async`, `_align_one` | Existing descriptor/custody/sequence checks run on expanded exact references before native preparation. Keep these functions unchanged. |
| Protein receipt authority | `NativeProteinStructureReturns._commission`, `authenticate`, `_levels`, `_attempts_at`, `_attempt`, `_values`, `_historical`, `_deliveries`, `_received`, `received_context`, `received_facts`, `validate_received_report`, `record_admission`, `_original`, `received_sequence_descriptors`, `authenticate_received_sequence`, `authenticate_received_saved_sheet`, `_completed_alignment` | Use actual requested successful delivery witnesses and frozen ancestry. Preserve provenance occurrences before value deduplication. `_completed_alignment` requires the original exact action. |
| Overlap receipt authority | `genomic_overlap_returns.py:GenomicOverlapReturns` and `episode_return_records.py:EpisodeReturnRecords` | These complete files were read. Actual original selected commissions, returned fields, known-reference boundaries and frozen prefixes govern. The deduplicated received file list alone loses the selected handoff association. |
| Saved result authority | `protein_structure_operands.py:_saved_sheet`, `validate_saved_structure_sheet_operand`, `validate_protein_structure_selected_inputs`; `genomic_overlap_result_receipts.py:_target`, `origins`; `native_genomic_overlap_results.py:retained_target`; `ExecutionEpisodes.execute`, `_selected_result_action` | Preserve the exact handoff + saved descriptor association. Existing selected target, scope and original receipt checks remain; no implicit artifact access. |
| Outcome and observation | `runtime.py:DecisionSource.execute`, `record_effect`, `checkpoint`; `Workflow.execute`, `_receive_form`; family fact/return readers | Resolve before execution. Keep `runtime_actions`, tool receipts, typed forms, own-action observations and closure behavior unchanged. No lookup credit. |

Relevant existing semantic presentation mechanisms were inspected. RNA and
Infernal have detached receiver projections; instruction-library options retain
their library selection operands. Neither supplies a general, authenticated
choice-to-received-protein/overlap mapping. `state_frame` revisions and contract
information digests are reconstruction identities, not model operands. Generic
`_values` or a hidden full JSON descriptor does not create an addressable option.

The existing `GenomicOverlapResultReceipts.origins` may use a representative
origin only after proving identical targets. The proposed binding must not
misdescribe that as permission to guess an origin: each option is constructed
from a proved delivery occurrence and its matching original selected handoff.

## Exact change surface

The following is the proposed minimal coding ownership after user feedback on
the display contract. It is not permission to implement new model templates
now. Function names for **new** ports below are proposed exact interfaces;
existing names are source names.

### A. Protein authority adapter owner

Own a new private `protein_received_operands.py` and a new
`NativeProteinStructureReturns.received_operand_fields(context)` port. The
port returns detached `AuthenticatedReceivedField` values defined in 001/003.
It reuses the existing authentication/witness functions and enumerates eligible
sequence and saved-sheet delivery occurrences before value deduplication.

Add only a receipt traversal helper if necessary to retain the existing
`_deliveries` witness association; existing returned facts and their order must
not change. The adapter may read original request/selector metadata through the
already accepted received-authority path. It must not read native bytes or add
unrequested sheet cells, map coordinates, sequences or private child state.

Outputs: `structure_sequence` and `protein_saved_sheet` carriers, permitted
uses, scientific attributes with explicit availability, and all exact private
witnesses. No runtime/provider edits belong to this owner.

### B. Overlap authority adapter owner

Own a new private `genomic_overlap_received_operands.py` and a new
`GenomicOverlapReturns.received_operand_fields(context)` port. Retain each
actually requested saved-file occurrence, original result origin and exact
selected handoff together before `_received` deduplicates values. Reuse the
existing `_attempt`, `_historical`, frozen closure-prefix and original receipt
proofs. This requires no new experiment, parser or calculator.

Outputs: `genomic_overlap_saved_sheet` carriers and separate received projection
occurrences. Attach scientific labels only from this receiver's supplied job or
requested return. Link projections to the saved sheet through the proved
original result relationship, not by digest alone. A projection-only receiver
gets no reusable sheet entry. No runtime/provider edits belong to this owner.

### C. Shared transport owner

Own a new pure `received_operand_bindings.py` implementing the four ports in
001, with the schema refinement in 003. It accepts only authenticated family
carriers and explicit frozen original contracts. It performs no Store scan,
scientific computation, model call, result read or resource decision.

Own the small integration edits in these exact existing functions:

| Function | Required change |
|---|---|
| `episode_bindings.py:EpisodeBindingRegistry` new `received_operand_fields(context)` | Aggregate explicitly bound family ports into a private typed sequence; reject conflicting witness/entry identities. Do not add it to `initial_decision_context`. |
| `execution_episodes.py:ExecutionEpisodes` new `received_operand_fields(context)` | Dispatch to the two existing family's return authorities, respecting role/receiver scope. The existing scientific process can receive execution facts without owning those private proofs. |
| `runtime.py:DecisionSource.call` | On the first request for a decision, obtain/freeze private entries and persist the snapshot, semantic adapter schema and safe availability summary. Restore saved values on retries. |
| `runtime.py:DecisionSource.exchange_schema` and `composition_information.py:lookup_schema` | Add the exact optional `received_operands` query branch for the three declared uses without changing original operation contracts. |
| `runtime.py:DecisionSource.exchange_decision` | Serve pages from the saved snapshot, journal public replies/exposure, compose adapted output schema, and preserve it through restart/compaction. No `Workflow.execute` scientific dispatch for this lookup. |
| `runtime.py:DecisionSource.validate_contract_exchange_request`, `validate_contract_exchange_history` | Validate adapted generation schema and safe reply/exposure against this decision's saved private binding. Restore identical public pages, not refreshed current candidates. |
| `runtime.py:DecisionSource.apply_response` | Decode using adapted semantic schema, validate it, resolve only declared marker slots, preserve raw response and a private resolution record, then validate original schema and call existing selection. |
| `runtime.py:Workflow.freeze_contract_information`, `validate_contract_information` | Preserve the original schema/catalog as authoritative. Add/check transport binding association separately so output-schema verification accounts for the adapted envelope. Do not change exact original schema lookup payloads. |
| `runtime.py:DecisionSource.instructions` | Add only user-reviewed detailed operand-use instructions to TASK transport guidance. Existing substantive task/constraints remain full. |

`DecisionSource.next` can continue constructing scientific context as now:
private fields are obtained in `call`, not carried through its public context.
`_action_generation_schema` and `_decode_action_response` can remain generic
functions used with the correct semantic schema; no global reference rewriting
is justified. If implementation requires changing them, the shared owner must
show why the wrapper cannot handle the declared slots and preserve their
current encoded-assignment/null semantics.

`Workflow.selected`, `Workflow.execute`, `DecisionSource.execute`,
`interpretation_context`, scientific authorization, `ExecutionEpisodes`'
`prepare_assignment`, target/selector/execute methods, and ordinary catalog
schemas remain unchanged. They consume expanded exact values only. Do not add
private choice markers to their receipts or reinterpret completed actions.

### D. Scientific presentation owner

Own pure `protein_received_operand_presentation.py` and
`genomic_overlap_received_operand_presentation.py`. Inputs are already supplied
typed scientific views and public lookup replies. Outputs are detached
selected context fragments plus text/tables; no Store or journal reads.

This owner must first obtain feedback on concrete message examples as required
by TASK_AND_STEERING. Do not implement 413 or 422's draft tables wholesale.

Exact existing consumers needing integration are:

| Function | Required change |
|---|---|
| `scientific_process_prompt.py:render_episode_steering` | Select these two family's fragments before `_steering`; render scientific object choices and calculation occurrences separately. |
| `scientific_process_prompt.py:_lookup` | Render the new page and recognized family action/history detail scientifically. No raw descriptors in fallback tables. |
| `scientific_process_prompt.py:_task` | Supply reviewed complete operand-use meaning where relevant; do not shorten full task, constraints, tool information or return meanings. |
| `providers.py:_SessionConnection._presentation` | Recognize the reviewed protein/overlap receiver context; select its renderer for full/bootstrap/update/lookup/reconstruction, including non-published-root receivers. Never route those recognized fragments through raw JSON fallback. |
| `decision_context.py:model_snapshot` | Apply the detached typed projection before computing frame revisions if the safe public projection is not already installed by `DecisionSource.call`. Choose one placement; never rewrite a hashed frame in `_presentation`. |

The final placement above is mechanical: prefer installing the safe public
projection before `model_snapshot` in `DecisionSource.call`, so
`model_snapshot`, `state_frame`, `apply_state_frame`, `_SessionConnection.complete`
and history storage stay unchanged. Both placements must not be installed.
The presentation owner supplies one pure selector; the shared transport owner
wires that selector at the chosen single boundary.

Raw `child_reports`, `last_local_outcome`, applicable `working_state` records,
own-attempt input pages and detail slices are consumed through these family's
typed selectors. This is not a generic scrub of every `_ref` string: some
scientific references elsewhere are independently declared operands. Exact
history storage and history selection semantics remain unchanged. Requesting a
history detail does not itself expose a new current choice; a separate current
operand page can do that if the receiver still has the legitimate receipt.

Root/shared ownership should serialize C and the existing-file edits from D.
A and B can be assigned independently with private modules and explicit
typed outputs; they must not each invent their own token, prompt, runtime
lookup, alias registry or saved-action representation. This boundary is the
reason for the planning task; it does not add a reviewer episode or runtime gate.

## Verification evidence read and work not performed

Read relevant complete functions in the existing protein Workflow integration,
native overlap Workflow, same-decision exchange and frozen contract-information
test paths. Retained sources are the actual engineering fixture records named
and hashed in `RETAINED_SELECTION_EXAMPLES_001.json`. They show existing exact
operations with scripted action choices. They do not establish that the
proposed marker interface or model presentation works.

No tests/imports/native work were run for this packet. Future implementation
verification should reuse the meaningful real decision paths described in 001,
including frozen replay and the two native fixture families, under the required
20 GiB RAM / 4 GiB scratch / zero swap native lifecycle with no invented wall
budget. No all-suite run or count increase is claimed.

No evidence-axis, W05, literature, grading formula, annotation credit, yield,
estimation, continuation, account, resource scope or original goal changed.
