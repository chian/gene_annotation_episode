"""Own A104 LocalExecution goal plus complete original context and report guidance."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime_prompt import DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT

def instructions(source, context):
    instructions = source.workflow.job_episodes.instructions(source.path[-1][0]) if source.workflow.is_job_source(source) else INSTRUCTIONS
    specialist = source.workflow.specialist(source)
    if specialist is not None:
        specialized = specialist.instructions(source.workflow.binding_context(source))
        instructions = specialized if getattr(specialist, 'replaces_default_instructions', False) else instructions + '\n' + specialized
    if source.workflow.permits_common_action(source, 'reason'):
        instructions += '\n' + REASONING_COMMIT_REQUIREMENT
    if 'tool_knowledge' in context:
        instructions += source.workflow.knowledge.instructions
    if 'launch_instruction_library' in context:
        instructions += source.workflow.launch_instructions.instructions
    instructions += '\nWhen pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work.'
    if source.workflow.permits_common_action(source, 'wait'):
        instructions += '\nA pending_child_ handle names your original in-process child, not an external event-provider target. To give its existing scheduler time to collect owned work, select wait with that handle, event returned, after_cursor 0 and reconsider_at null. An earlier ready owned sibling may wake this wait first; its original return is then collected before another decision. Waiting only reports readiness and earns no scientific credit. In-process state_changed/progress_committed events and mixed external wait conditions are not supported by this collection channel.'
    if source.workflow.native_event_information is not None and source.workflow.permits_common_action(source, 'wait'):
        instructions += '\nThe separate native_event_targets input names native notification targets assigned or actually received by this episode. A target is registration metadata, not proof that submission succeeded. Its state_changed event means the original service exit receipt was committed; the service may still be closing, so this does not establish result readiness or a child episode return. after_cursor records an event cursor actually received, initially zero. Select your own wait condition and subsequent status/monitor/result work. Request the native_event_targets source in original child forms when that handoff is needed. No event probability, gain or scientific credit follows from registration or passing time alone.'
    if source.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
        old_history_guidance = INSTRUCTIONS[INSTRUCTIONS.index('On a fresh provider conversation,'):INSTRUCTIONS.index('Do not execute native provider tools.')]
        instructions = instructions.replace(old_history_guidance, 'Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again.\n')
    return instructions


def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'instructions': instructions}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime_prompt',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.instructions')
    globals()['instructions'] = bound['instructions']

from gene_annotation_episode.episodic_workflow.root.a104 import runtime_prompt as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
