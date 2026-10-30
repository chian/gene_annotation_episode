"""Construct planning artifacts only; no production renderer is implemented."""
import ast
from copy import deepcopy
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
ROLE_ROWS = []
CHAIN = ('runtime.DecisionSource.next -> DecisionSource.call -> '
    'DecisionSource.exchange_decision (decision_exchange_v1) or direct complete (legacy) -> '
    'providers.ModelConnection.complete -> _SessionConnection.complete -> _presentation -> '
    '_session/thread-start developerInstructions + turn-start input[0].text; outputSchema remains separate')
COMMON_FIELDS = {
    'assignment': ['goal.objective', 'scope', 'requested_report_purpose', 'requested_form',
        'current_report_update (parent initial values until this child first updates them)',
        'tools[].name/description/input_schema', 'selected_launch_instructions.sections[].text',
        'child_options (actual permitted role/form information)'],
    'own_history': ['last_local_outcome', 'feedback', 'current_credit', 'controller.estimate.expected_next_gain',
        'controller.decision.continuation_cost', 'action_yields (exchange protocol only)',
        'pending_work', 'waiting_support.progress_records', 'report_deliveries',
        'current_report_basis_refs', 'restored_episode_history (legacy only)'],
    'received_reports': ['child_reports[]: only method_loop admitted direct-child typed forms',
        'working_state: when receipt_projection is true, scoped immutable record versions include frozen ancestor receipt prefixes plus own receipts; when false, scoped Store reasoning_view has no receipt-selection filter',
        'execution_resource_capabilities/execution_initial_information: caller-bound initial information',
        'received_bvbrc_values/received_minhash_values: optional binding-projected actually received facts'],
    'prospective_information': ['resource_tool_estimates', 'execution_expectations',
        'native_execution_expectations', 'job_execution_options', 'native_event_targets'],
    'other_actual_current_context_fields': [
        'goal includes objective/result_contract/task_context/goal_id/parent_goal_id (assignment plus host lineage)',
        'current_evidence_vector and optional investigation_progress retained_finding_count/inactive_dependencies/detail_pages (own received-state projector)',
        'credit_binding/scientific_child_credit_binding/controller_binding (caller configuration, currently serialized outside published text filter)',
        'time_accounting (journal own elapsed measurements; not job duration)',
        'visual_evidence (only pixels selected by latest own completed image action)',
        'visible_record_refs (calculated actual supplied-reference basis; a handle is not read content)',
        'available_report_facts (typed source meanings and report schemas)',
        'report_lifecycle (fixed interpretation timing explanation)',
        'tool_knowledge/launch_instruction_library (frozen library discovery metadata)',
        'job_episode_options (bound legacy job role information)',
        'optional monitoring_information_credit/monitoring_information_binding (distinct received timing/status channel)',
        'optional annotation_score/annotation_evidence_vector/annotation_score_binding (scientific roles only; separate from current_credit)',
    ],
}
HISTORY = ('Use decision_history.yield_table rows category, completed_actions, total_yield, '
    'expected_yield.status/band/unavailable_reason, attempted_uncompleted. Categories are actual tool/<name>, '
    'episode_child/<role>, job_child/<role>, child/improvement, reason, wait, etc. Saved signed marginal '
    'credit comes from own runtime_observations in completion order; inherited baseline is excluded. '
    'Show current controller expected_next_gain value/lower/upper/status_code/uncertainty_code/alpha and '
    'continuation_cost separately from category fits and duration estimates. Preserve unavailable/insufficient '
    'states. Select necessary prior attempt operands/statuses and delivered results; ask own_attempts/detail '
    'for older specific attempts. The legacy protocol has no action_yields field and cannot truthfully '
    'manufacture those category statistics from a last outcome. No child history enters the child assignment.')
CURRENT_STEERING = ('DecisionSource.next builds full current context from EpisodeView plus bounded '
    'last_local_outcome and admitted forms. exchange_decision/model_snapshot removes controller.scores and '
    'waiting raw histories, adds action_yields and sends state_frame deltas; own lookup continues the same '
    'decision. For this nonpublished context _presentation JSON-serializes the frame or full context; '
    'it does not build a text TASK/STEERING pair. Legacy only supplies bounded restored_episode_history.')
TRACKING = ['goal.goal_id/parent_goal_id', 'run_id/episode_id and path', 'frame revision/base_revision',
    'conversation_key', 'completion sequence/unit identity', 'controller epoch/configuration/diagnostics',
    'source custody hashes not required by the currently available callable contract',
    'library provenance and process initial_selection_sha256 (except exact pins required as copy operands)']
VERIFY = ('Drive a real DecisionSource request through a controlled _SessionConnection.complete '
    '(or ModelConnection with that owned worker), capturing turn/start input and thread/start '
    'developerInstructions. Cover full legacy context, bootstrap, delta without repeated assignment, '
    'lookup result, restored bootstrap and compaction; assert complete own TASK each time, exact selected '
    'STEERING values, unchanged outputSchema and no new runtime_actions/runtime_observations for lookups. '
    'Do not replace provider.complete with Choices.complete as the rendering assertion.')

def add(name, role, producer, decision, task, fields, quantities, operands, deps, file,
        *, example=None, renderer='json.dumps(context, allow_nan=False)', history=HISTORY,
        returns=None, variant=None, scope='main_workflow'):
    row = {'row_name': name, 'scope': scope, 'owning_episode_role': role, 'exact_decision': decision,
        'complete_producer_and_receiving_path': producer + ' -> ' + CHAIN,
        'input_fields_and_origin': deepcopy(COMMON_FIELDS),
        'role_specific_fields_and_origin': fields, 'recurring_TASK_available_now': task,
        'current_STEERING_extraction': CURRENT_STEERING, 'actual_model_text_renderer': renderer,
        'decision_changing_quantities': quantities, 'identifiers_required_as_callable_operands': operands,
        'tracking_fields_to_keep_outside_prompt': deepcopy(TRACKING),
        'required_prior_attempts_action_totals_expectations_uncertainty': history,
        'original_child_task_and_typed_return_constraints': returns or
            'Workflow.selected compiles purpose/schema_json/initial_report_json; build creates the child goal, '
            'scope, assignment and interpretation initial values. Recurring TASK must retain that original '
            'purpose and complete field/type/allowed-value/x-source meanings. Parent yield/private reasoning '
            'are not supplied. report_update interprets the pre-action state; finish/form_with_facts fills '
            'recorded facts, no model report composer. Child results become parent STEERING, not a replacement TASK.',
        'retained_example': example or {'status': 'No retained native Workflow example inspected for this boundary; source inventory only.'},
        'future_renderer_signature': 'render_' + name.replace('-', '_') +
            '(state: Mapping[str, object], instructions: str, *, lookup_results: Sequence[Mapping[str, object]] = ()) -> str',
        'required_renderer_output': 'Exactly detailed recurring TASK text, blank line, then terse decision-specific STEERING text/tables; no JSON envelope. Build the two blocks separately. Output schema is unchanged and remains an independent provider argument.',
        'proposed_owned_file': file, 'precise_dependencies': deps, 'verification_caller': VERIFY,
        'variant_notes': variant, 'status': 'read-only planning; proposed template not implemented or settled'}
    ROLE_ROWS.append(row)

def retained(role, index, detail):
    return {'context_file': f'retained_{role}_{index}.json', 'detail': detail,
        'provenance': 'Closed msa_dna-_7cous9_ Workflow; retained native byte examples served by loopback HTTP; scripted decisions; caller scientific credit zero; no new native execution, live BV-BRC or configured-model inference.'}

add('annotation', 'annotation', 'Workflow.build; DecisionSource.next/instructions; composition_information.restricted_root',
    'Choose the next annotation investigation/interpretation, child or explicit wait for the fixed supplied target.',
    'runtime.INSTRUCTIONS supplies scientific reasoning, limits, typed commitments and report timing; '
    'goal/scope/material facts supply the actual assignment. Published axis/thought instructions are not automatically '
    'installed on this root. Restricted-root action_schema removes ordinary tools; generic prose still says select a tool.',
    {'assignment': ['goal.result_contract.role=annotation', 'scope.subject_refs/read_selection_refs/segments'],
     'received': ['working_state', 'annotation_score/annotation_evidence_vector/annotation_score_binding', 'child_reports']},
    ['retained scientific findings and qualifications', 'current annotation versus alternatives', 'own category yield',
     'pending results/duration support', 'actually available child contracts'],
    ['subject/semantic record references used by reason/commission', 'child roles', 'available option/tool selectors', 'wait handles', 'delivery_ref for repair'],
    ['Workflow.action_schema restricted_root common actions', 'EpisodeView.model_inputs admitted forms', 'annotation_context fields', 'process option/tool metadata lookup results'],
    'gene_annotation_episode/annotation_prompt.py', example=retained('annotation',7,'One admitted scientific child; current_credit=0; last own action is a wait. Controller quantities belong to this root.'))
add('improvement', 'improvement', 'Workflow.selected kind=child -> Workflow.build; DecisionSource.next/instructions',
    'Resolve the parent scoped scientific improvement using iterative evidence and interpretation.',
    'runtime.INSTRUCTIONS plus assigned goal, fixed narrower scope and parent return meanings; no three-slot construction on this legacy path.',
    {'assignment': ['scope', 'goal.objective', 'requested_report_purpose/form'], 'received': ['scoped working_state', 'admitted direct-child forms']},
    ['scoped current evidence and qualifiers', 'own progress/yield', 'pending outcomes'],
    ['scoped record refs', 'tool operands', 'wait handles', 'requested form references'],
    ['scientific_child selection schema', 'interpretation_schema', 'Workflow.build legacy improvement branch'],
    'gene_annotation_episode/improvement_prompt.py', variant='Roleless child only when no scientific_process binding prohibits that route; still source-present for saved/caller legacy runs.')

published_fields={'assignment': ['scientific_process.selection.evidence_axis/thought_pattern/child_tool_info',
    'scientific_process.evidence_axis.investigation_instructions', 'thought_pattern.description/use_when/live_alternatives/decision_guidance/outcome_contingencies/boundary',
    'child_tool_info[].name/description/resources/instructions', 'scientific_process.assignment.evidence_refs/constraints/context'],
    'received': ['selected current interpretations and linked received records', 'admitted child_reports', 'last_local_outcome'],
    'own_history': ['action_yields (exchange only)', 'controller current estimate', 'current_report_update']}
add('scientific-published', 'scientific_process', 'ScientificProcessEpisodes.prepare_invocation/validate_context/instructions/decision_context; DecisionSource.next',
    'Determine the supplied target function under the selected evidence-axis and thought-pattern guidance; choose work or interpretation.',
    'Full published investigation_instructions, selected thought-pattern alternatives/contingencies, actual frozen child_tool_info instructions, assignment and typed return are available now.',
    published_fields, ['native facts, subject/condition correspondence, missing/contradictory evidence', 'own action yields and continuation uncertainty', 'separate annotation support', 'pending returns and durations'],
    ['scientific selection version/library_id/option_id/entry_sha256 are currently required copy operands',
     'child_tool_info exact name/resources pairs', 'revision_origin parent_invocation_ref/preparation_operation_ref for a selected alternative child',
     'source/subject/reference IDs needed by declared tools and typed report'],
    ['scientific_process_prompt._task/_steering', 'evidence_axis_instructions.instruction_view', 'ScientificProcessEpisodes._ASSIGNMENT/_SELECTION', 'alignment_report_presentation'],
    'gene_annotation_episode/scientific_process_prompt.py', renderer='render_scientific_process_prompt via _SessionConnection._presentation after state_frame reduction',
    example=retained('scientific_process',8,'Selected MSA quantities returned through child_reports; frozen selected axis/thought/tool bodies persist. Current scientific credit is zero; no new annotation confidence implied.'))
ROLE_ROWS[-1]['current_STEERING_extraction']='scientific_process_prompt._steering renders own yield/controller tables, separate measures, current linked received interpretations, latest local outcome, admitted returns via alignment_report_presentation, pending work/progress, duration forecasts and explicit lookup replies. _task expands supplied published instructions. It does not read Store or calculate scores. Review remains needed for relevance/size of copied fields and required exact operands.'
add('scientific-unpublished', 'scientific_process', 'ScientificProcessEpisodes.instructions nonpublished branch; decision_context legacy/current nonpublished variants',
    'Investigate assigned support problem using frozen selected process information without treating source provenance as target evidence.',
    'Nonpublished instruction branch plus axis instruction view or legacy annotation.support, thought guidance and actual tools; selector version controls keys.',
    {'assignment': ['scientific_process.annotation/thought/tools for legacy selection', 'scientific_process.evidence_axis/thought_pattern/child_tool_info for current nonpublished selection', 'assignment.context/constraints/evidence_refs'],
     'metadata': ['annotation_support_routes (unavailable/mapped meaning, never scoring or gate)']},
    ['same scientific decision quantities as published variant; support routes are policy metadata only'],
    ['legacy annotation_ref/thought_ref/tools or current exact three-slot selectors', 'semantic refs and revision_origin operands'],
    ['LEGACY_SELECTION_VERSION versus SELECTION_VERSION', 'evidence_axis_instruction_view', 'support_observation_kinds and scientific_support_routes'],
    'gene_annotation_episode/scientific_legacy_prompt.py', variant='Historical nonpublished input variants retained; do not redesign slots, sheets, credit or stored observations.')

lit=[
 ('literature','Which published evidence addresses the assigned question?','literature_assignment_v1','question_context_refs/source_refs','ordinary search/read or narrower strategy child'),
 ('literature_strategy','Which search approach is informative after actual outcomes?','strategy_assignment_v1','question_context_refs/prior_search_refs','search terms, providers and selected search child'),
 ('literature_search','Which returned sources merit examination?','search_assignment_v1','question_context_refs/search_result_refs','source discovery, original-source read or page child'),
 ('literature_page','Where and how should this exact source be examined?','page_assignment_v1','source_ref/representation/artifact_ref/question_context_refs/prior_delivery_refs','source operations or table/ordered/targeted child'),
 ('literature_table','Which table cells, conditions and qualifications resolve the question?','reading_assignment_v1','page plus sheet_key/offset/limit/header_row/where or source byte window','revise selected rows/header/footnotes; no fixed reading quota'),
 ('literature_ordered','Which next document window, reread or interpretation is useful?','reading_assignment_v1','page plus source_ref/representation/offset/limit','native UTF-8 byte continuation in document order as useful'),
 ('literature_targeted','Which supplied passage and neighboring qualifications affect the question?','reading_assignment_v1','page plus selection.spans[] source_ref/representation/offset/limit','separate source-bound spans; never concatenate a fabricated quotation')]
for role,decision,version,fields,guidance in lit:
    add(role.replace('_','-'),role,'LiteratureEpisodes.prepare_assignment/_validate_assignment/instructions/decision_context',decision,
        f'runtime.INSTRUCTIONS + exact _ROLE_INSTRUCTIONS[{role}] + common literature instructions; {guidance}; actual assignment/question and original typed form.',
        {'assignment':[version,fields], 'received':['literature_source_custody','question context refs are supplied operands, not read content'],
         'own_history':['own_literature_outcomes bounded metadata','literature_history_meaning']},
        ['source subject/condition/representation and exact selected passages', 'what was actually searched/read', 'own scientific yields/uncertainty', 'typed page/reading child results where available'],
        ['source_ref', 'artifact/representation as exact custody operand where required', 'UTF-8 byte offset/limit', 'sheet/column/row selectors', 'context refs'],
        ['LiteratureEpisodes.assignment_schema('+role+')', '_ROLE_INSTRUCTIONS['+role+']', 'own_outcomes records/next_offset', 'source.read/XLSX/PDF contracts'],
        'gene_annotation_episode/literature_prompt.py', variant='Inventory of an existing prompt boundary only. Literature grader/search/interpretation implementation is excluded from this tool-grader goal.')

add('monitor','monitor','MonitorEpisodes.prepare_assignment/_assignment/instructions/decision_context/catalog',
    'Choose the next useful observation/read/wait or direct-dependency monitor within the parent progress request.',
    'MonitorEpisodes generic monitoring instructions plus actual target description and requested fields. Current instructions are appended to runtime scientific INSTRUCTIONS because no replaces_default_instructions flag exists; unrelated science prose is therefore present.',
    {'assignment':['monitor_assignment.target_handle/requested_fields/known_progress_refs/permitted_committed_record_types'],
     'received':['monitor_target_description','monitor_direct_dependencies','monitor_received_progress_refs','own/received progress snapshots via selected reads'],
     'own_history':['progress.observe/read/log outcomes']},
    ['observed native state, phase/log measurements and provenance', 'elapsed measure versus expected duration', 'what changed since known snapshots', 'result availability/direct dependencies', 'own monitoring yield and uncertainty'],
    ['target_handle for monitor/wait', 'progress_ref for read/log', 'log_index', 'requested_fields', 'native_operation only when descriptor selected_observation_schema requires it'],
    ['episode_monitoring._ASSIGNMENT/_SNAPSHOT', 'describe_progress_target.selected_observation_schema', 'progress_selection.known_progress_refs', 'progress_records JOB_STATUS_SCHEMA/RESOURCE_STATUS_SCHEMA'],
    'gene_annotation_episode/monitor_prompt.py', variant='One generic episode template with resource-type guidance and actual tool operation/extractors; no per-tool LLM judge.')

add('execution-launch','launch','ExecutionEpisodes.prepare_assignment/_launch/instructions/decision_context/initial_decision_context',
    'Choose a permitted concrete execution request/resource and whether its returned handoff meets the original endpoint.',
    'ExecutionEpisodes launch instructions; original requests map, immutable inputs/constraints, pinned manuals, real capability and inventory descriptions; child construction contracts.',
    {'assignment':['execution_assignment.version=execution_launch_assignment_v1','requests[resource_id]','immutable_input_versions','constraints','launch_instructions'],
     'received':['execution_resource_capabilities','execution_initial_information','execution_progress','child_reports typed handoff']},
    ['availability/authentication', 'resource allocations and limits', 'compatible duration support', 'prior attempted resource outcome', 'returned usable handoff/practical completion', 'own operational yields'],
    ['resource_id', 'original concrete request fields', 'immutable_input_versions when required to copy assignment', 'launch instruction pins', 'handoff refs used by follow-up child'],
    ['ExecutionEpisodes.assignment_schema(launch)', '_match_request original constraints', 'execution_completed/execution_handoff_refs fact schemas', 'ResourceToolEstimator projection fields'],
    'gene_annotation_episode/launch_prompt.py', example=retained('launch',0,'A sole selected-api request for BV-BRC MSA is available; current operational credit=0. The launch still owns the explicit child selection.'))
add('execution-api','launch_api','ExecutionEpisodes.instructions/decision_context -> APIServiceExecution.decision_context or APIExecution.decision_context legacy',
    'Choose preparation, primitive API operation, observation, transfer or repair for the fixed assigned service job; establish its requested handoff.',
    'ExecutionEpisodes API instructions interpolate actual service. Assignment carries the real selected request, resource, endpoint and constraints. Generic service capabilities/operation contracts come from catalog. Legacy HMMER API and generic API have different data fields.',
    {'assignment':['execution_assignment.resource_id/service/request/endpoint/constraints','api_request'],
     'own_history':['api_received_progress[name].state/kind/facts','api_execution_completed'],
     'legacy_fields':['api_execution_assignment','api_execution_prepared_request','api_execution_job','api_execution_completion']},
    ['preparation errors and required inputs', 'immediate response versus asynchronous job', 'native status/submission uncertainty', 'authentication/rate limit facts', 'operational endpoint state and own yields'],
    ['exact native operation name', 'preparation_receipt_ref/support_receipt_ref', 'job/handoff identity when required by selected API operation', 'parameter pointers/workspace object locators/input_bindings', 'resource_id'],
    ['api_service_assignment_v1.request and service-specific assignment_schema', 'APIServiceExecution._events facts', 'APIExecution legacy version discriminator', 'catalog input_schema per actual service'],
    'gene_annotation_episode/api_execution_prompt.py', example=retained('launch_api',1,'Own api.bvbrc_appservice.prepare completed with zero credit; submit uses its exact preparation receipt. No service job exists merely because preparation completed.'),
    variant='One generic API template with native-operation information; MSA, Homology, MinHash and other services are contracts/data, not new LLM judges or episode types.')

for kind, role in [('local','launch_local'),('hpc','launch_hpc')]:
    add('practical-'+kind,role,'ExecutionEpisodes._delegate -> PracticalResourceEpisodes.instructions/decision_context; also standalone PracticalResourceEpisodes binding',
        'Choose actual preparation/context/command/job observation or repair for the original '+kind+' requested endpoint.',
        'PracticalResourceEpisodes.instructions with full original job argv/environment or native_hmmer request, workspace, predicates/completion keys, constraints and actual resource capabilities. Local/HPC use distinct callable job.start contracts.',
        {'assignment':['practical_assignment.requested_job/workspace/resource_kind/endpoint/progress_requirements/completion_keys/initial_context/constraints'],
         'own_history':['practical_working_context','practical_progress','practical_completion','practical_current_inventory'],
         'caller':['practical_resource_configuration','practical_initial_information','practical_resource_information/capabilities (standalone initial hook)']},
        ['validated satisfied requirements versus remaining exact endpoint', 'command exit/stdout/stderr and working cwd/environment', 'confirmed failed versus uncertain native attempt', 'saved inventory versus present observation', 'own operational yield/uncertainty'],
        ['exact argv/env/path', 'receipt_ref for original execution', 'retry_failed_execution_id only for explicit retry',
         'queue and native resources for HPC' if kind=='hpc' else 'original local job request',
         'resource_id where included by ExecutionEpisodes request schema'],
        ['practical_execution_records.ASSIGNMENT_SCHEMA/CONTEXT_SCHEMA', 'operation_catalog('+kind+')', 'PracticalState.credit_view/context/completion_proof', 'practical_yield exact-zero endpoint semantics'],
        'gene_annotation_episode/practical_execution_prompt.py', variant='Standalone and delegated routes share this actual producer; not counted twice. HPC requires BioReason storage and EpiCalib when Aurora is the selected deployment; no invented resource or wall-time budget.')

add('execution-results','results','ExecutionEpisodes.prepare_assignment/_selector/instructions/decision_context/catalog -> selected API/native result operators',
    'Choose the next acquisition/status/read needed for the original selected native result and requested numerical projection, preserving valid partial data.',
    'ExecutionEpisodes result instructions plus original handoff/selector, target description, exact artifact/parser/parameter contracts and requested typed return. Scientific interpretation remains with receiving scientific parent.',
    {'assignment':['execution_assignment.handoff_ref/selector','execution_target.assignment/resource_kind','execution_target_description'],
     'own_history':['execution_progress','last_local_outcome partial acquired result/missing requirements'],
     'conditional':['own_bvbrc_values only for BV-BRC Data request']},
    ['actual retained artifact availability/byte coverage/partiality', 'missing requirement identity and next eligible acquisition', 'format/version/mode and original selected output', 'native state and current-filesystem limitation', 'operational yield and completion'],
    ['handoff_ref', 'selector requirement_id/role/declared_format and actual requested fields', 'support_receipt_ref/source_ref/native workspace locators', 'path/offset/limit for native reads', 'parser/calculator selector parameters'],
    ['execution_results_assignment_v1', 'ExecutionEpisodes._selector native/API/HMMER validation', 'execution_target_description.selected result operations', 'requested_schema x-alignment-fact/x-homology-fact/etc fields', 'execution_result_refs/execution_completed return facts'],
    'gene_annotation_episode/results_prompt.py', example=retained('results',5,'Four prior acquisition operations have retained partial information; same original MSA selector requests cells/entropy/gaps/members/native_score/sites/missing. Next available download is chosen with a recorded capability. Native rows remain real measurements, not annotation probabilities.'),
    variant='Concrete contract variants: generic native filesystem, native HMMER result selector, legacy HMMER API, and generic API/service results. ExecutionEpisodes does NOT call APIServiceExecution.decision_context for results: actual fields are execution_target/description/progress plus optional own_bvbrc_values. Keep this distinction in dispatch tests.')

old_res=[('launch','Choose a permitted adapter-backed execution approach.'),('launch_api','Investigate selected adapter API availability/authentication and execution.'),
 ('launch_local','Investigate preparation/execution/receiving interface on selected local adapter.'),('launch_hpc','Investigate selected environment, queue and staging through the bound HPC adapter.'),('results','Acquire the requested data from the original adapter handoff.')]
for role,decision in old_res:
    add('resource-adapter-'+role.replace('_','-'),role,'ResourceEpisodes.prepare_assignment/instructions/decision_context; adapter.decision_context; HomologyResourceAdapter._legacy',decision,
        'ResourceEpisodes exact role responsibility + parent job/input/CPU/search constraints and iterative ownership; runtime.INSTRUCTIONS is also appended because this legacy binding does not replace it.',
        {'assignment':['role','assignment.resource_launch_assignment_v1 or resource_results_assignment_v1','job_request/immutable_input_versions/constraints/resource_selection/software_knowledge_refs/resource_knowledge_refs/adapter_assignment; or handoff/requested_data_selector'],
         'received':['resource_capabilities','resource_tool_estimates','admitted typed handoffs']},
        ['actual capability availability','adapter compatible timing forecasts','native handoff/state/partial acquisition','own operational yield'],
        ['resource_selection resource_id/kind/allocation/capability_binding_ref','job_ref/handoff/receiving-interface refs','actual adapter operation operands','selected manual pins'],
        ['resource_records.LAUNCH_SCHEMA/RESULTS_SCHEMA/HANDOFF_SCHEMA', 'ResourceEpisodes._adapter', 'HomologyResourceAdapter.catalog and decision_context'],
        'gene_annotation_episode/resource_adapter_prompt.py', variant='Alternative registered binding for existing roles; cannot coexist with ExecutionEpisodes for the same role. Source-present compatibility path, not proof of deployment.')

for role,decision in [('job_launch','Prepare/submit assigned detached homology job and repair usable receiving handoff.'),
        ('job_monitor','Gain useful assigned homology job status/timing information from selected observations.'),
        ('job_results','Acquire/extract requested native homology evidence and preserve partial extraction.')]:
    add(role.replace('_','-'),role,'HomologyEpisodes.instructions/working_state/catalog; DecisionSource.instructions uses job branch',decision,
        'HomologyEpisodes role-specific instructions replace base scientific instructions; assignment is fixed query/CPU/search and supplied handoff, requested form remains parent-owned.',
        {'assignment':['working_state.role/assignment (job_assignment)'], 'own_history':['last_local_outcome samples/checks/extraction'],
         'timing':['execution_expectations','resource_tool_estimates','monitoring_information_credit/binding when configured']},
        ['actual query/search/CPU configuration','native status/elapsed measure/handoff failures','result completeness/parse failures','new versus known timing measurements','own operational or monitoring yield'],
        ['job_ref','handoff interface refs','query_ref','snapshot/sample refs','extract ordinals/selectors'],
        ['HomologyEpisodes.commission_schemas/assign/assignment', 'HANDOFF_SCHEMA/SAMPLE_SCHEMA/RESULT_PROGRESS_SCHEMA', 'job report_sources'],
        'gene_annotation_episode/homology_job_prompt.py', variant='Legacy flat job roles remain distinct from modern launch/resource/monitor/results bindings; do not treat them as proof of the new structure.')

for version,field,task in [('v1','tools','names/descriptions/exact callable input contracts'),('v2','child_tool_info','actual name/description/resource-kind pairs, frozen instructions supplied by host after selection')]:
    add('tool-retrieval-'+version,'FAST retrieval (not an episode)','ScientificToolRetriever.retrieve -> provider.complete(call_identity, FAST, instructions, {investigation,catalog}, output_schema)',
        'Select the useful actually available tools for the parent desired investigation; no scientific judgment or execution choice.',
        ('scientific_tool_retrieval.INSTRUCTIONS' if version=='v1' else 'TOOL_INFO_INSTRUCTIONS')+' plus investigation and complete '+task+'.',
        {'assignment':['investigation','catalog'],'own_history':[],'received':[]},
        ['available actual operations and their fit/prerequisites for the described investigation; no numerical score or episode yield'],
        ['exact callable tool names'] if version=='v1' else ['exact name/resources identity pairs'],
        ['ScientificToolRetriever.retrieve context', 'output_schema(names)' if version=='v1' else 'tool_info_output_schema(catalog)', 'library.resolve/resolve_tool_info'],
        'gene_annotation_episode/tool_retrieval_prompt.py', history='One primitive information lookup, not its own episode. No inherited parent yields/private reasoning, artificial history or manufactured observation. If called during request_context composition lookup it remains the same unfinished parent decision.',
        returns='Closed tools array or child_tool_info selector array. Host resolves exact selected names/pairs to substantive frozen instructions. An empty result is allowed; no explanation, planning prose or invented descriptor.',
        scope='non_episode_model_call')
    ROLE_ROWS[-1]['complete_producer_and_receiving_path']='ScientificToolRetriever.retrieve -> ModelConnection.complete FAST -> _SessionConnection.complete/_presentation -> JSON fallback -> thread/start developerInstructions, turn/start input and separate outputSchema'
    ROLE_ROWS[-1]['input_fields_and_origin']={'assignment':['investigation','catalog'], 'own_history':[], 'received_reports':[]}

for role,decision in [('parent','Commission launch/monitor/results or interpret returned synthetic mapping summaries; select waits/scheduled commission.'),
 ('launch','Prepare fixed local mapping workload and usable handoff.'),('monitor','Observe requested progress/remaining time from handed-off job.'),('results','Acquire/extract requested available mapping blocks.')]:
    add('local-example-'+role,role+' (local_example)','local_example.workflow.Source.next -> JobWorkflow.schema/tools/monitoring_estimate/history',decision,
        'local_example.workflow.INSTRUCTIONS is a single literal containing all four roles plus exact workload/assignment and role tool catalog; current backend gets raw full context.',
        {'assignment':['role','goal','assignment','workload','available_tools','requested_form','report_fact_schemas','child_form_examples (parent only)'],
         'own_history':['own_recorded_facts','own_last_outcome','feedback','controller','prior_decisions (24-row metadata index)'],
         'received':['child_reports','monitoring_yield (parent only)','pending_commissions (parent only)']},
        ['native block/read counts','actual status and simple completed-block duration estimate','requested block coverage','own role credit/controller estimate','synthetic fixture limitations'],
        ['job_ref/workload_ref/workspace_ref in handoff','sample/receipt/commission refs','block_index','due/wait seconds'],
        ['local_example.workflow.HANDOFF/STATUS/SUMMARY/FACTS', 'JobWorkflow.schema', 'Source.next'],
        'gene_annotation_episode/local_example/prompt.py', history='This separate example stores prior_decisions metadata and raw controller fields; no decision_exchange yield_table or own_attempts request_context. Preserve its explicit simple monitoring_estimate meaning and label it historical example, not the main workflow or current production estimator.',
        variant='Existing separate example backend consumer. Inventory only; not a proposal to add its scheduled-work behavior to the main workflow.',scope='separate_local_example')
    ROLE_ROWS[-1]['complete_producer_and_receiving_path']='local_example.workflow.Source.next -> injected provider or providers.ModelConnection.complete REASONING -> _SessionConnection.complete/_presentation JSON fallback -> native thread/start and turn/start'

assert len(ROLE_ROWS)==31
assert len({r['row_name'] for r in ROLE_ROWS})==31

# Concrete transport, lookup and both-direction communication boundaries are
# separate from role templates: these wrap a receiving role, not extra episodes.
BOUNDARIES=[]
def boundary(name,producer,receiver,inputs,meaning,signature,deps):
    BOUNDARIES.append({'row_name':name,'producer':producer,'receiving_function':receiver,
        'actual_input_fields_and_origin':inputs,'decision_effect_and_TASK_STEERING_requirement':meaning,
        'current_renderer':'Published scientific recipient gets scientific_process_prompt text; other recipients JSON fallback unless this is only a host record.',
        'required_future_interface':signature,'proposed_owned_file':'gene_annotation_episode/prompt_exchange.py',
        'precise_dependencies':deps,'verification_caller':VERIFY})

boundary('transport-legacy-full','DecisionSource.call legacy','_SessionConnection._presentation',
    ['full instructional_model_context','bounded restored_episode_history on fresh native session'],
    'Repeat complete receiver TASK and selected current own/received STEERING; preserve original saved context/schema on replay.',
    'render_request(boundary: PromptBoundaryV1, full_state: Mapping, instructions: str) -> RenderedPrompt',
    ['runtime_model_calls.request.context/schema','DecisionSource.instructions'])
boundary('transport-bootstrap','DecisionSource.exchange_decision -> state_frame(snapshot,None)','_SessionConnection._presentation',
    ['version/kind/base_revision/revision/fields/removed_fields','fields = model_snapshot(context,yield_table)'],
    'Construct authoritative presentation state and full TASK/STEERING; frame identifiers are host-only.',
    'reduce_frame(previous: None, frame: Mapping) -> Mapping', ['decision_context.apply_state_frame','model_snapshot'])
boundary('transport-update','DecisionSource.exchange_decision -> state_frame(snapshot,previous)','_SessionConnection._presentation',
    ['changed top-level fields','removed_fields','base_revision/revision'],
    'Apply and validate delta host-side, then render full TASK again. Sending only delta JSON loses recurring task.',
    'reduce_frame(previous: Mapping, frame: Mapping) -> Mapping', ['apply_state_frame','conversation_key and compaction epoch'])
boundary('transport-lookup-continuation','DecisionSource.exchange_decision public lookup','_SessionConnection._presentation',
    ['kind=decision_lookup_result','result','decision_index/exchange_index (host)'],
    'Full same receiver TASK, selected reply as STEERING, unchanged own-action history; no action/controller observation.',
    'render_request(boundary: PromptBoundaryV1, state: Mapping, instructions: str, lookup_results: Sequence[Mapping]) -> RenderedPrompt',
    ['original state snapshot','resolved lookup result only'])
boundary('transport-restored-bootstrap','DecisionSource.exchange_decision after conversation loss/retry/compaction','_SessionConnection._presentation',
    ['bootstrap fields','restored_public_exchanges','restored_pending_decision_index'],
    'Reconstruct full TASK and selected answered information; do not narrate transcript or repeat answered lookup. Existing scientific branch extracts lookup_result only.',
    'restore_pending(snapshot: Mapping, public_exchanges: Sequence[Mapping]) -> RestoredPresentation',
    ['decision_exchanges frozen request/restoration.snapshot','response_recorded/lookup_result_recorded'])

lookup_rows=[
 ('own-attempts','decision_history.lookup_attempts','records[].decision_index/category/status/completed_gain/inputs/published_references; next_query', 'Specific prior selected inputs and original completed gain; not raw full outcome body.'),
 ('own-attempt-detail','decision_history._lookup_detail','decision_index/pointer/offset/limit/values/next_query','An exact selected-input slice; schema allows no other episode owner; no new evidence access.'),
 ('child-options-index','composition_information.child_options(role=None)','available roles/construction/required assignment fields/return fact sources','Actual allowed choices, not child execution or selected itinerary.'),
 ('child-options-detail','composition_information.child_options(role=<actual role>)','assignment operand table/return fact meaning table','Instructions needed to construct that exact child and its original requested form.'),
 ('knowledge-search','ToolKnowledge.search','entry_id/name/description/tools/provenance metadata/pagination','Discover actual instruction documents; not installed capability or evidence.'),
 ('knowledge-entry','ToolKnowledge.entry','entry index/sections/provenance/operation names','Select relevant instruction sections; provenance remains host context unless needed.'),
 ('knowledge-read','ToolKnowledge.read','entry_id/section_id/text/offset/returned_lines/total_lines/next_query','Exact selected instruction window; line offsets are callable operands, not source-byte anchors.'),
 ('launch-instructions-search','LaunchInstructions.search','resource_kind filtered metadata and pagination','Discover instructions, no availability claim or resource choice.'),
 ('launch-instructions-entry','LaunchInstructions.entry','section index, sources, pins','Select instruction sections, preserve host provenance.'),
 ('launch-instructions-read','LaunchInstructions.read','selected text window and next_query','Actual software/resource guidance; after selection recurring task must retain required substance.'),
 ('launch-instructions-select','LaunchInstructions.select','version/library_id/sections entry_id,section_id,sha256','Exact returned selection is a required child assignment operand. It performs no launch.'),
 ('process-search','ScientificProcessLibrary.search','slot/query/offset/limit -> A/P option references and metadata','Retrieve evidence_axis/thought_pattern alternatives; child_tool_info remains separate actual tool selection.'),
 ('process-entry','ScientificProcessLibrary.entry via instructional_model_context','option_ref and instruction-projected entry','Detailed selected investigation/thought guidance, no full scoring sheet inserted in prompt.'),
 ('process-sources','ScientificProcessLibrary.sources','option_ref/offset/limit -> provenance page','Instruction provenance only; cannot become new target evidence.'),
 ('process-tools','Workflow.execute -> ScientificToolRetriever.retrieve or literal library search','investigation -> child_tool_info or legacy tools/catalog','May make FAST information lookup before current action; root selects no child automatically. No extra completed action when invoked as composition lookup.'),
 ('lookup-feedback','DecisionSource.exchange_response/exchange_decision error branches','status invalid/failed; feedback.category/code/detail or exception_type','Repair same pending response/lookup with full TASK and exact constrained feedback; no manufactured observations.')]
for name,producer,fields,meaning in lookup_rows:
    boundary('lookup-'+name,producer+' -> DecisionSource.exchange_decision.resolve_lookup',
        'recipient _SessionConnection._presentation -> role renderer', [fields],meaning,
        'render_lookup_'+name.replace('-','_')+'(result: Mapping) -> str',
        ['composition_information.lookup_schema','decision_context.instructional_model_context',fields])
    BOUNDARIES[-1]['proposed_owned_file']='gene_annotation_episode/prompt_lookup.py'

boundary('parent-to-child-ordinary','Workflow.selected -> build -> EpisodeGoal.child/EpisodeRequest','child DecisionSource.next/call',
    ['selected goal/scope/purpose/schema_json/initial_report_json','job_assignment or episode_assignment','frozen selected instructions'],
    'Host typed request is not a model prompt. Child receives its actual assigned TASK and necessary supplied facts only. No parent yields/private reasoning; child then owns choices and own yields.',
    'child_task_inputs(request: EpisodeRequest, assignment: Mapping, selected_instructions: Mapping | None) -> TaskInputs',
    ['interpretation_schema','binding.prepare_assignment/prepare_invocation','Workflow.build'])
boundary('parent-to-child-durable','Workflow.commission_child -> CommissionCoordinator.select -> independent_execution child reconstruction','same child DecisionSource.next/call',
    ['spec.child.request/scope/role','input_versions/constraints/expectation_snapshot_refs (host records)'],
    'Durable execution does not create a new instruction template or expose commission wrapper. Same assigned child TASK survives reconstruction; parent controller history is not a child input.',
    'child_task_inputs(request: EpisodeRequest, assignment: Mapping, selected_instructions: Mapping | None) -> TaskInputs',
    ['independent_execution _check_assignment and child build','spec.child.request original identity'])
boundary('child-to-parent-typed-return','DecisionSource.finish -> Workflow.facts -> form_with_facts -> TypedReportContract.admit/episode_admission -> receive_form -> EpisodeView.model_inputs','receiving parent DecisionSource.next/call',
    ['requested admitted form values','declared x-source field meanings','actual report_update interpretation basis','requested closing episode_yield (if requested)'],
    'Preserve the parent TASK; selected typed returned facts/qualifications become parent STEERING. No model composer and no child private history. Child yield, when expressly requested, remains labeled child closing forecast, never a parent local observation.',
    'render_received_form(form: Mapping, schema: Mapping, purpose: str) -> str',
    ['parent original closed report schema','receive_form receipt admission','EpisodeView._model_inputs'])
boundary('child-return-alignment-projection','scientific_process_prompt._steering -> alignment_report_presentation','published scientific parent TASK/STEERING',
    ['admitted {source_ref,field,value} rows for bvbrc_alignment or bvbrc_genome_alignment fields','readable decoded association names'],
    'Existing family-specific text projection removes only presentation IDs for numeric alignment fields; source data and action/report operands unchanged. Other families remain exact values. Do not assume this implements generic child-return projection.',
    'alignment_report_presentation(report: Mapping) -> Mapping',
    ['bvbrc_alignment_bundle_contracts.decode_reference','bvbrc_genome_alignment_bundle_contracts.decode_reference'])
BOUNDARIES[-1]['proposed_owned_file']='gene_annotation_episode/alignment_result_presentation.py'

for row in BOUNDARIES:
    row.update(owning_episode_role='The actual receiving semantic role row above; this projection creates no episode.',
        exact_decision='The receiving role retains its exact decision and original assignment; only declared currently received information changes.',
        recurring_TASK_available_now='The complete TASK contents of the receiving semantic row, independent of whether this request is a bootstrap, delta, lookup, repair or admitted return.',
        current_STEERING_extraction='Producer fields listed in this row plus the receiving semantic row own-state extraction; published scientific text filters are the only current text path.',
        quantities_changing_the_decision='Only the requested values, their missing/partial/failure status, meaningful associations and the receiving role original own category/controller/duration fields; lookup itself earns no credit.',
        identifiers_required_as_callable_operands='Keep exact declared lookup operands: view, operation, entry_id, section_id, option_ref, role, offsets/limits, decision_index/pointer, tool name/resources or handoff/record references as applicable. Distinguish them from frame/run/episode/hash tracking. The recipient tool/return schema determines whether an ID is callable.',
        tracking_fields_to_exclude=deepcopy(TRACKING),
        required_prior_attempts_action_totals_expectations_uncertainty=HISTORY,
        original_child_task_and_typed_return_constraints='Original requested purpose, closed schema and interpretation meaning remain unchanged. No new fields or return composer. Parent TASK survives a child return; child TASK contains no parent yield history.',
        retained_example='PROVIDER_DISPATCH_EVIDENCE.json contains actual retained-context dispatch and explicitly synthetic frames. Retained per-role contexts apply to parent-child projections. No retained same-decision metadata lookup was generated by that MSA run; those rows are source-only.',
        status='read-only planning; no implementation or template approval claimed')

write=lambda name,value:(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
write('TEMPLATE_INVENTORY.json',{'status':'source-derived draft for root/user review; no production edits',
    'counting_rule':'One role+substantive binding/instruction contract. Identical delegated producer counted once. Runtime frame/lookup projections counted separately; actual tool modes are inputs, not handwritten episode templates.',
    'counts':{'main_workflow_role_names':19,'main_workflow_role_binding_templates':25,'FAST_non_episode_contracts':2,'separate_example_roles':4,'semantic_template_rows':31,'transport_projection_rows':5,'same_decision_lookup_rows':16,'parent_child_projection_rows':4},
    'roles':ROLE_ROWS,'boundaries':BOUNDARIES})

lines=['# Source-based prompt boundary inventory (planning only)', '',
 'The current source has **19 main Workflow role names**, represented by **25 role/binding instruction contracts**. The difference is one published/nonpublished scientific split and five legacy ResourceEpisodes contracts alternative to the modern five-role ExecutionEpisodes family. There are also **two FAST retrieval contracts** and **four roles in the separate local example**: **31 semantic template rows**. No historical example count was used. Standalone and delegated PracticalResourceEpisodes producers are counted once.', '',
 'The five transport forms, sixteen same-decision lookup/feedback projections and four communication projections are a separate cross-cutting inventory. They are not 25 extra episode kinds. Each receiving semantic template must be exercised with its supported transport forms. Actual tool families and scientific modes remain data/contracts under the existing role; they are not new LLM judge templates.', '',
 'Every detailed row—including inputs by origin, current TASK/STEERING availability, callable versus tracking IDs, needed numerical history, original typed form, proposed exact signature/file, dependencies and provider-dispatch caller—is in TEMPLATE_INVENTORY.json. This Markdown table is its scan index.', '',
 '| Row | Owner | Actual producer | Decision | Current input text | Proposed renderer file |',
 '| --- | --- | --- | --- | --- | --- |']
for r in ROLE_ROWS:
    producer=r['complete_producer_and_receiving_path'].split(' -> ')[0]
    lines.append('| '+' | '.join(x.replace('|','\\|').replace('\n',' ') for x in [r['row_name'],r['owning_episode_role'],producer,r['exact_decision'],'TASK/STEERING' if r['row_name']=='scientific-published' else 'JSON fallback',r['proposed_owned_file']])+' |')
lines += ['', 'The main source path is DecisionSource.next → call → exchange_decision/direct complete → ModelConnection.complete → _SessionConnection.complete → _presentation. Root and independent child worker constructors both select this same backend. No second shipped native model transport was found. Injected Choices/Fake providers in tests are caller test substitutes, not another production renderer. FAST calls and local_example also use this backend when ModelConnection is supplied.', '',
 '| Projection boundary | Complete producer | Receiving function |', '| --- | --- | --- |']
for r in BOUNDARIES:
    lines.append('| '+' | '.join(x.replace('|','\\|') for x in [r['row_name'],r['producer'],r['receiving_function']])+' |')
(OUT/'BOUNDARY_TABLE.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'semantic_rows':len(ROLE_ROWS),'projection_rows':len(BOUNDARIES)}))
