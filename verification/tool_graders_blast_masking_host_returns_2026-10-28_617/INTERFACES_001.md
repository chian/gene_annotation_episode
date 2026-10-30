# Masking host adapters, exact integration ports

This implements the existing610/001–006,613 core and615 producer contracts and
616/INTERFACES_001. The original user attachment remains authoritative. Only the
two new host modules and focused tests belong to617. No prompt template, numerical
calculator, native operation, episode role or shared dispatch is added here.

`native_blast_masking_results` exports `NativeBLASTMaskingResults`,
`VERSION='native_blast_masking_acquired_result_v1'`, `operation_catalog()`.
The class has `applies(context)`, async `execute(context,target,tool_name,arguments,
operation_key)`, `facts(context)`, `credit_view(context,receiver_selection)`,
`result_identity(reference,scope)`, `completion(context)`,
`resolve(context,reference,namespace)`, `read_result(reference,scope,assignment=None)`,
`retained_target(context)`, `retained_reference_access(context,reference,namespace)`
and `validate_statistics_binding(context,job)`.

`native_blast_masking_returns` exports `NativeBLASTMaskingReturns`, `FACT_SOURCES`
(the six616 dotted sources) and `requested_sources(schema)`. The class extends
`EpisodeReturnRecords`, supplying `received_facts(context,schema)`,
`validate_received_report(context,form,schema)`,
`record_admission(context,form,schema,operation_key)`,
`resolve_received(context,reference,namespace)`,
`resolve_received_reference_metadata(context,reference,namespace)` and
`received_context(context)` plus the original authentication overrides.

Owner attributes: `store`, `run_id`, `directory`, `resources`, `handoff_unit`,
`acquired_record_unit`, `native_blast_masking_results`,
`native_blast_masking_returns`, `job_progress_provider.targets`.
Owner methods called: `_target(context)`, `_result_directory(context)`,
`_selected_result_action(episode_id,key,name,arguments)`; targets calls are
`read_target(handoff_ref,scope)` and `observe_target(target,operation_key=...)`.
The saved target reader must authenticate historical handoffs without accessing
removed native paths. `_target` consults `retained_target` first. Generated
statistics admission calls `validate_statistics_binding` with the assigning
parent context before commissioning; it checks explicitly received source and
statistics artifact against the actual original counts result. Caller declarations
never become authenticated generation. The same original relation is retained
with the selected masking job and checked against captured bytes downstream.

Root approved the616 scalar-status correction: Projection.status remains one
Status; the fact-source schema is an array of Status. Own facts wrap the original
status and receiving parents deduplicate exact complete rows. No latest-wins
projection is introduced. Generic execution_result_refs stays generic; no seventh
masking fact source is invented. Only selected original artifact rows and explicit
Store references grant data. Provenance references and virtual record/statistics
identities do not grant underlying files.

Receipts retain the exact selected action, target, assignment, observation,
Capture, Prepared and Publication. A later explicit projection can reuse the
same authenticated captured original. `reused_from` names the original receipt;
it grants no additional acquisition credit and never invokes the native job.
Replay validates retained bytes and frozen values without parsing/calculation.
One returned action result remains one own runtime observation.

Focused checks use529/run_checks.py check072_masking_host_returns and check005
dependencies under20GiB RAM/4GiB scratch/zero swap/no wall cap. They establish the
adapter/return boundary separately from root's full Workflow integration. Saved
authentic native fixtures are reused; this owner runs no native programs.
