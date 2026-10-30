# Protein structure consumer and child-ownership trace, 380

2026-10-27. This is a source inspection and exact integration contract for
`B-L107-compare_protein_structures`, alongside `SHARED_CONTRACT_001.md`.
Only this additive packet was written. Production, tests, immutable directions,
377, active RNA work and progress accounting were not changed. **110/308 remains
the parent-reported tally.** No native alignment, structure comparison, service,
HPC job or broad test was run for this packet.

## 1. Finding that controls the implementation scope

**An actual ordinary scientific-child `sequence.align` route exists.** Its
absence from `ExecutionEpisodes.resource_tool_contracts` does not make alignment
unavailable. That resource hook describes a different commission route. The
current selected direct operation already runs a bounded native Biopython worker
and retains the full original traceback. Preserve that route.

**The extraction-to-alignment-to-comparison chain does not yet exist.** The missing
parts are exact structure sequence publication/admission, use authorization in
the existing scientific child, and comparison's original alignment/operand and
received-prefix authentication. These are specific host integration changes.
They do not require an aligner inside the parser, arbitrary gap parameters, a
new alignment resource episode, or root execution tools.

The public supporting call stays exactly:

```text
SequenceAlignmentArguments = {query_ref: ReferenceRef, reference_ref: ReferenceRef,
  molecule: "protein", mode: "local"|"global"}
```

These are all four required arguments in the actual tool contract. Native
`align_pair` additionally has Python defaults gap_open=-10.0 and gap_extend=-0.5;
the public operation does not expose them. Current protein mode uses BLOSUM62.
Those actual settings suffice for 377's explicitly selected retained alignment.
The chosen result is the first native optimal traceback returned by Biopython,
retained in full. Selection of that observation for comparison is explicit;
uniqueness and alternative-count knowledge are not invented.

## 2. Authority and status records actually read

Read in full: the immutable 635-line attachment
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
actual `AGENTS.md`, `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`,
`docs/PRACTICAL_EXECUTION.md`, original
`docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md`,
`docs/TASK_AND_STEERING.md`, `docs/TOOL_KNOWLEDGE.md`,
`docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md`, and all 912 lines of 377.
The immutable objective and all sixteen principles were reread after the native
and implementation study, and again before completing this packet.

The relevant records have different purposes and were not conflated:

| Record inspected | Actual status or meaning |
| --- | --- |
| `research/tool_grader_inventory_2026-10-24/WORK_STATUS.json`, `current/biopython_pairwise` | Historical inventory fields are pending; this is not current binding proof. |
| Same inventory, `biomni.tool.systems_biology.compare_protein_structures` | Pending; no installed/bound/tested result follows from the catalog entry. |
| `research/tool_grader_goal_2026-10-24/WORK_STATUS.json`, `A-L061-protein-local`, `A-L061-protein-global` and their `::local` bindings | Existing records report actual bounded local invocation/publication and shared-loop scientific-child return verification. Their evidence includes B001-PAIR, B001-CHILD-MODES-005 and related root checks. This packet inspected the current source route; it did not rerun that evidence. |
| Same fixed status file, `A-L064-native-pairwise` and its `::local` binding | Existing recorded selected scientific-child read/calculation/return of retained alignments; no aligner rerun for saved-site work. Its original-source/operand authentication is relevant precedent, not structure-map authority. |
| Same fixed file, retained component `B001-PAIR` | Standalone component evidence alone explicitly does not establish complete production execution. |
| Same fixed file, `B-L107-compare_protein_structures` and `::local` | All implementation/binding/verification fields remain `not_assessed`, evidence_ids empty. Planning supplies no completion credit. |

Literature graders and W05 were excluded. No network/auth/resource access was
needed. The upstream native source was inspected locally; no external document
was substituted for actual implementation behavior.

## 3. Complete current alignment route

The affected methods below were read, including their publication and receiving
consumers. `ToolRegistry` is the actual class in `tools.py`; 377's `Tools` naming
is shorthand, not a different binding.

| Step | Current code and actual transmitted information |
| --- | --- |
| Discover actual operations | `WorkflowServices.tool_catalog` reads `workflow.tools.catalog`; `tool_information_catalog` merges that direct catalog with separately validated commissioned resource contracts. `resource_tool_information.tool_information_contracts` explicitly labels the direct entries. A source-library name is not substituted for a bound operation. |
| Select a scientific child's tools | Complete `scientific_tool_library.py` resolves the selected actual contracts. `ScientificProcessEpisodes._tool_resolution_for`, `_tool_resolution`, `_proposed_selection` and `catalog` preserve the original selection. The current version places only selected direct operations in this child's direct catalog. Resource operations remain commission descriptions. |
| Selected own action | `ScientificProcessEpisodes.execute` validates operation membership and the exact arguments, then calls `WorkflowServices.execute_tool`. The service dispatches the existing `ToolRegistry.execute_async`; there is no new episode or private scientific loop. |
| Read actual sequences | `ToolRegistry._alignment_arguments` calls `_check_sequence_operand` for the query and `Store.subject_length` for the reference, then `_sequence` for both. `_sequence` reads an actual registered sequence artifact. References without a genomic input footprint are permitted evidence. The generic reference self-map is amino-acid sequence position, not structure residue numbering. |
| Execute selected native work | `execute_async` / `_execute_operation_async` -> `_prepare_sequence_work_async` -> `_prepare_alignment_async` -> `_sequence_worker_async` -> common `run_local_job_async` -> `sequence_worker.py` -> `sequence_ops.align_pair`. The worker has no Store handle and no in-process fallback. Caller-selected LocalJobPolicy remains the resource policy. |
| Retain native facts | `sequence_ops.align_pair` uppercases, applies actual matrix/gap/mode settings, takes the first returned alignment and retains original aligned strings, coordinate path, intervals, lengths, counts, score and native version. A real no-alignment return is explicit `aligned=false`. It supplies no gap/score fields, which must not be invented later. |
| Publish source and observation | `_perform` -> `_align_one`: `grade_biopython_pairwise` makes the full sheet/calculation; `_source` stores the entire native JSON and full grading auxiliary. Source provider is `biopython.alignment`, with ordered deduplicated `operand_refs=[query,reference]`. The observation has one query subject, one reference source-subject, exact dependencies and native intervals. |
| Preserve actual selected operation | `_save` retains name/arguments/scope/result in `tool_operations`; runtime stores the child action and its result. The returned preview omits aligned strings and coordinates, but the original source artifact does not. Comparison must read that full artifact. |
| Return existing observation identity | `Workflow.facts` derives `committed_record_refs` from actual own runtime action results and freezes them at closure. Existing typed forms can return the original source/observation refs. `ScientificProcessEpisodes.facts`, `validate_report`, `initial_references`, and generic receipt/form validation preserve process ownership. A selected child can pass an actual alignment observation without introducing a protein-specific aligner. |
| Authenticate original scientific association | `alignment_site_native.immutable_record`, `source_descriptor`, `reference_operands`, `reference_source_operands`, and `biopython_molecule` check original source/provider/operand identities and matching retained full native result. `source_tool_gradings` preserves the full original sheet. These helpers do not, by themselves, prove that the consuming child received the descriptor or observation. |

Current root restrictions remain in `composition_information.py` and runtime's
`restricted_root` handling. The parent's discovery/commission ability does not
grant it scientific execution.

The complete `sequence_ops.py`, `sequence_worker.py`,
`biopython_pairwise_grader.py`, `tool_grading_artifacts.py`,
`alignment_site_native.py`, `alignment_site_mapping.py`,
`resource_tool_information.py` and `scientific_tool_library.py` were inspected.
The complete affected tool methods were read, including their asynchronous
execution, grading, original-operation storage and native cleanup paths. No
claim is made that every unrelated branch of the large registry/runtime was
reviewed.

## 4. Minimal supporting-operation integration contract

### 4.1 Publish extraction as a real existing reference

D's extraction results publisher consumes C's original `ExtractionNative`, the
original selected `ExtractRequest`, captured complete native bytes and actual
result receipt. A's `StructureSequence` must have sequence_available=true,
known positive length, fully resolved symbols and exact original residue map.

It stores uppercase ASCII sequence bytes without header/newline, canonical
StructureSequence JSON, and the existing closed domain reference fields given
in SHARED section 4.1. **Use `Store.put("reference", reference_payload, origin="tool")`**,
where reference_payload is the exact closed record in that section. The
actual `Store._validate_record` reference branch for origin=`extracted` rejects sequence
bytes and lengths because that origin has a different source-anchor meaning.
No new domain record type or relaxation is required. `Store.subject_length`,
`subject_molecule`, `subject_unit`, `sequence_mapping` and `_sequence` already
support the ordinary protein reference.

The exact `StructureSequenceDescriptor` is derived from that original result
and returned under `execution_protein_structure_sequences`, or as the identical
selected descriptor field in an extracted-sequence projection. Its allowed_uses
are explicit. Admission must associate the same descriptor value with the
original successful typed form; possession of its hashes alone is insufficient.
Sequence/reference publication is unavailable when symbols/population fail;
partial raw/map information and failure rows remain returnable.

The descriptor's reference set is exactly reference_ref, sequence_file,
residue_map_file, structure_file artifact refs, and custody's handoff_ref,
source_ref and bundle_artifact_ref. An admitted descriptor authorizes only those
exact operands for its declared uses; it does not authorize arbitrary bundle
auxiliaries or imply that every hidden map number was displayed to the parent.
When a different scientific child is commissioned, the parent explicitly
supplies this operand reference set in its existing evidence_refs and freezes
the relevant received-prefix evidence. No generic source-envelope expansion is
used to discover additional files.

### 4.2 Add one preflight at the existing scientific-child dispatch boundary

Current `ScientificProcessEpisodes.execute` passes received_record_refs only to
`result.blast.hsp`. It does not authenticate structure-derived sequence
descriptors. `_alignment_arguments` checks existence/length and input scope,
not original extraction receipt authority. This is the missing integration,
not a missing native aligner.

Root owns this minimal new service port:

```python
def WorkflowServices.authenticate_structure_alignment_operands(
    self, context: BindingContext, arguments: SequenceAlignmentArguments
) -> StructureAlignmentAdmission
```

```text
StructureAlignmentAdmission = {query: StructureSequenceDescriptor|null,
  reference: StructureSequenceDescriptor|null}
```

The service invokes D's exact
`authenticate_structure_sequence_reference(store, context, reference_ref,
returns=protein_returns)` port for each structure-derived operand. The output
is used for host validation only; it does not add tool arguments or a numerical
observation. Null means the operand is an ordinary non-structure reference and
the pre-existing validation applies. It does **not** mean a structure reference
was found but its required original descriptor is missing.

Classification uses the immutable reference's actual source and the new protein
results owner's original extraction record. It is not inferred from the label,
accession prefix, sequence text, or a user-supplied flag. The protein family
denial precedes generic fallback: a protein extraction source with no admitted
descriptor yields sequence_not_received, never the ordinary-reference branch.

`ScientificProcessEpisodes.execute` calls this port after its existing schema
validation and before `services.execute_tool` for selected sequence.align.
If selected `execution.estimate` targets sequence.align, the same preflight
applies to its nested four alignment arguments because `_estimate_native` reads
the operand bytes too. This adds no timing probe or estimator decision.

The preflight validates both operands independently: context/run/episode/path,
original request/knowledge manifest, declared use `sequence_align`, actual
successful original extraction action and form, frozen ancestry/prefix, exact
reference/source identity and molecule/length, both sequence/map bytes and
original selection. It reads retained data only. No source acquisition, sequence
repair, alignment, follow-up child or retry occurs during authentication.

No change to the actual public `sequence.align` schema, sequence worker,
alignment algorithm or root catalog is required. An additional hook inside
`ToolRegistry._sequence` would be insufficient because that method has no
scientific-child receiving context; it would also overreach unrelated uses.

### 4.3 Authenticate the selected original alignment for comparison

D's `authenticate_selected_alignment` takes the explicit AlignmentDescriptor,
both exact extraction descriptors and orientation. It returns the full
AlignmentSnapshot to A, as fixed in SHARED section 8. The following conditions
are all required:

1. Prove authority for both extraction descriptors with
   allowed_uses containing structure_correspondence. Check the newly selected
   structure file/model/chain/basis/variant/symbol/CA/metadata policies equal the
   original extraction selections. Re-extract the original sequence/map and
   require exact agreement before A's explicit rebind_structure_sequence changes
   only the operation-local single/fixed/moving role label in a detached copy.
   The resulting selection must equal the comparison's named-side selection;
   no other selection field or original map byte is changed.
2. Prove the alignment observation was this scientific parent's actual completed
   own sequence.align result, or was explicitly returned in a successful original
   typed form admitted before the comparison child was commissioned. When an
   observation is inherited through ancestors, require the frozen report-prefix
   proof at every boundary. Merely querying all Store rows is insufficient.
3. Match original_operation_key to the actual selected runtime/tool operation,
   exact query_ref/reference_ref/molecule/mode, completed result and observation.
   The current supported producer is sequence.align; do not silently admit an
   unrelated alignment tool because lengths match. An older source lacking
   operand_refs may use the existing original-operation fallback, still with
   this exact operation association and received authority.
4. Validate immutable observation/source/reference records. Source provider is
   biopython.alignment; its artifact is exactly native_file. Observation has one
   subject and one source-subject; source operand_refs equal their ordered
   deduplicated pair. Orientation fixes which extraction reference is query.
   Dependencies and actual stored native lengths must agree; equal sequences
   under different reference identities are not interchangeable.
5. Resolve exactly one original full grading auxiliary for that source. Its
   native_artifact_ref/provider and `sheet.native_result` must type-sensitively
   match the original native bytes. Require the healthy accepted schema in
   SHARED section 12 and exact equality with the existing pure sheet builder's
   result. The grading file is an original retained artifact, not a new caller
   reconstruction standing in for the old one.
6. Pass native and full sheet unchanged to A. A validates every traceback step,
   interval, length, column/gap and symbol against both complete extracted
   sequences. Symbols outside a local traceback come from those extraction
   artifacts. A never aligns, pads, matches author/residue numbers, enumerates
   alternatives or chooses an unselected traceback.

The received observation establishes authority to its exact original native
source/grade for this selected comparison. It does not imply the receiver has
already seen all corresponding numerical values. Numerical delivery is proved
separately by the eventual comparison projection.

### 4.4 Original own actions and frozen receiving paths are different proofs

`EpisodeReturnRecords` supplies immutable saved-context, successful immediate
child form, original selected commission, original report schema, frozen facts
and redelivery checks. `rna_structure_comparison_operands._context` and
`_received_operand_value` show the existing necessary frozen-ancestry treatment:
the manifest must equal original knowledge_inheritance; ancestor report attempts
must be in the saved received_report_prefix and predate the child commission.

D must use those semantics for protein descriptors and alignments. Its own-action
case checks runtime_actions/tool_operations belonging to the identified ancestor
before the commission; it must not pretend an own action was a child return.
Its received-form case validates the actual returned observation reference and
original source facts, not just current EpisodeReceipts.known membership. A
sibling's action, a later ancestor receipt, an altered original schema, or a
source-only receipt that did not return the needed descriptor is insufficient.

The authority helpers are read-only implementation validation, not a new model
reviewer, scientific gate or execution layer. Missing retained bytes after
established authority yield retained_artifact_missing and preserve other facts;
they do not authorize reacquisition or make the old receipt cease to exist.

## 5. Exact new protein route and shared consumers

This table distinguishes the new protein resource/result binding from the
already usable supporting alignment route. Root edits shared consumers only
after current RNA owners release them. The actual local operation class is
`LocalPracticalOperations`, correcting 377's shorthand `PracticalLocalOperations`.

| Consumer inspected | Required change and exact handoff |
| --- | --- |
| `ExecutionEpisodes.__init__`, `as_record`, `resource_tool_contracts`; complete `ExecutionServiceFactory` | Reconstruct C's selected local software/job adapter and D's result/return adapters. Export the three actual tool contracts from native_protein_structure_tool_info with direct information fields separate from commission schemas. The existing generic factory needs no protein-private executor. |
| `practical_execution_records.REQUESTED_JOB_SCHEMA`; local assignment validation; `ExecutionEpisodes._request_schema`, `prepare_assignment`, `_check_parent_inputs`, `initial_references` | Admit exactly NativeProteinJob/RequestedProteinJob. Validate available input references, local 20 GiB/4 GiB/no-wall policy and D's original operand authority before reservation. Forward the selected request; choose no scientific alternative. |
| `LocalPracticalOperations` constructor whitelist, `validate_assignment`, `_handle`, `_job_fact`, `observe_execution`, `read_output`, `_execute` | Match the exact NativeProteinBinding; reserve C's NativeProteinRunPlan via prepare_local_protein_structure; start only on selected practical.job.start; expose exact original request/plan/output identities. Bound log/output reads validate that original attempt and output-path whitelist. Unknown started attempts do not rerun. Explicit retry remains an episode action using actual failed-attempt evidence. |
| C local adapter -> existing native lifecycle -> C driver -> C worker | One immutable attempt, exact selected software and staged input bytes -> A ParsedStructure/StructureSequence/Correspondence/StructureMetadata -> B sheet/components -> C native result and sealed NativeProteinBundle. Driver command and requested worker command remain distinct. |
| `ExecutionTargetReader._native`, `describe_execution_target`, `describe_target`, `usable_handoff`, `returnable_handoff`, `observe_target`, `read_file` | Authenticate C's exact plan/reservation; report actual liveness, logs, return code, captured roles and measured duration. Make failed/partial captured results returnable without calling them native success. No invented percent progress or queue duration. |
| `ExecutionEpisodes._selector`, result assignment schema, `catalog`, `execute` | Select exact ProteinResultSelector and original handoff. complete_bound_bundle uses original native parameters; retained_sheet_only consumes an admitted SavedSheetDescriptor and new explicit parameters. Status/collect have empty action arguments because assignment already fixes the selection. |
| D acquisition/result worker/publication/results | Capture once, verify C manifest/input/software/request, parse exact retained native result and retain full original sheet/components. Original comparison baseline is not silently recalculated. New saved-sheet calculation calls B without producer access. Projection consumes already populated records. |
| D result publication -> existing Store -> D result views | Real extraction reference plus descriptor; actual comparison sheet and original components descriptors; exact selected ProjectionResults and ProteinFailureReturns. Native raw tables stay separate from selected CA rows and calculations. |
| `communication._compile_closed_schema` | Register the four exact protein x-source schemas from SHARED section 10 at top level, with type-sensitive exact schema equality. No arbitrary numeric/prose fact replacement. |
| `ExecutionEpisodes.fact_sources`, `facts`, `received_report_sources`, `received_report_facts`, `validate_received_report`, `received_form_references`, `initial_references`, `resolve`, `resolve_received_reference` | Original fact/return equality; only requested projection values and declared descriptor operands become known. Run family-specific refusal before generic source fallback. Preserve actual original forms and frozen-prefix proof under reconstruction. |
| `episode_receipts.receive` | Add native_protein_structure_bundle_v1 to protected source-envelope cases, preventing recursive access to all auxiliaries. Explicit typed descriptors authorize exact declared operands instead. |
| `ExecutionEpisodes._native_results_complete`, `_proof_for_action`, `completion_for_action`, `verify_completion` | Validate original requested delivery, including explicit unavailable cells. Native success, capture completeness and delivery completeness remain different. Use the existing immediate exact-zero practical endpoint and one own-action observation. |
| D protein presentation -> shared RNA374 selectors/renderers, scientific-process prompt and provider transport | Render only already selected fields/units/denominators/qualifiers. Full TASK survives each iteration; selected curt STEERING contains decision-relevant facts. Never render full sheets, custody/hash records or hidden source lookups. Concrete wording is not settled by this packet. |
| Existing composition / independent execution reconstruction | Persist exact resource configuration, selected request, original form/prefix and result custody. Shared method_loop still owns iterative work; no protein-specific background agent or scheduler. |

The upstream Biomni `compare_protein_structures` implementation was read
completely at `reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/systems_biology.py`
in the located checkout. It uses permissive PDB/first-model assumptions, integer-number
intersection, coordinate mutation/rounded output and a descriptive 2 Å label.
Those behaviors do not satisfy 377 and are not reused as authenticated native
science. The new worker identifies the corrected local implementation explicitly.

## 6. Next work and bounded dependencies

After root's contract review, fresh A/B/C can proceed in parallel on 377's
exclusive modules and tests. There is no blanket scientific blocker:

- **A** owns exact scientific types/validation and PDB/mmCIF raw readers,
  inventories, sequence maps, retained correspondence and metadata extraction.
  Its consumers are B's sheet builder and C/D's workers. Input bytes and original
  alignment/descriptor data are supplied explicitly; A performs no host lookup.
- **B** owns populated sheets, explicit selection resolution, fit/transform and
  saved-sheet calculations. It can implement against SHARED and the hand examples
  before A's reader runs. Its numeric fixtures are synthetic and labeled so;
  numerical success is not native-format or episode-path verification.
- **C** owns job/run-plan/bundle validation, actual selected local reservation,
  driver/worker and tool information. It consumes the exact A/B ports. Only the
  assembled native invocation check needs completed A/B modules. It does not
  align or choose chains/conformers/fit sites.
- **D/root integration** owns original extraction publication, the small
  scientific-child preflight above, retained alignment proof, exact selected
  return/admission/custody and presentation. D can build against the fixed types;
  final shared wiring waits for root's active RNA consumers, not for a newly
  invented alignment resource route.

Actual acceptance still requires the real extraction -> scientific-child
sequence.align -> original retained traceback -> comparison path, explicit-map
mode, supplied-transform/held-out/degenerate cases, missing coordinates and
confidence, partial failures, saved recalculation with producer unavailable,
frozen return/reconstruction, selected provider text and original endpoint.
Tests must reject same-length wrong references, unreceived descriptors, altered
tracebacks, sibling visibility, post-commission receipts and hidden auxiliary
access. The small numeric examples alone cannot close B-L107.

Two scientific choices that were vague in 377 are explicit here: missing
occupancy preserves otherwise valid coordinates with an unknown qualifier;
reported occupancy outside [0,1] is invalid for selection. The numerical SSE
roundoff tolerance is explicit and retained. An unresolved correspondence
population yields null counts, while an authenticated native aligned=false
result has genuine P=0. These are reviewable contract decisions; none supplies
extra experimental information, significance or functional confidence.

The outstanding work is implementation and verification of these named
interfaces. No external credential, network source or HPC installation blocks
the A/B/C deterministic work. If D cannot establish a particular original
received descriptor or alignment action, that selected retained-alignment
request is unavailable; unrelated explicit-map/parser/calculator work remains
valid. This planning packet does not mark any fixed row complete.

Final packet checks: EXAMPLES_001.json parses as finite JSON; a standard-library
arithmetic check confirms y@R+t in the supplied-transform example, held-out
SSE/RMSD/mean and strict threshold counts, and the four distinct full PDB
positions despite the repeated integer 10. These checks did not import project
modules, call native tools or run tests. The three files in this packet are the
only files written by this lane.
