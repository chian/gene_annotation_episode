"""Compose this private literature episode guidance from its commissioned goal and actual context."""
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_investigation_prompt import DECISION_EXCHANGE_PROTOCOL, REASONING_COMMIT_REQUIREMENT, INSTRUCTIONS

def instructions(source, context):
    if source.workflow.is_job_source(source):
        pass
    instructions = _original_prompt.INSTRUCTIONS
    specialist = source.workflow.specialist(source)
    if specialist is not None:
        specialized = specialist.instructions(source.workflow.binding_context(source))
        instructions = specialized if getattr(specialist, 'replaces_default_instructions', False) else instructions + '\n' + specialized
    if source.workflow.permits_common_action(source, 'reason'):
        instructions += '\n' + _original_prompt.REASONING_COMMIT_REQUIREMENT
    if 'tool_knowledge' in context:
        instructions += source.workflow.knowledge.instructions
    if 'launch_instruction_library' in context:
        instructions += source.workflow.launch_instructions.instructions
    instructions += '\nWhen pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work.'
    if source.workflow.permits_common_action(source, 'wait'):
        pass
    if source.workflow.native_event_information is not None and source.workflow.permits_common_action(source, 'wait'):
        pass
    if source.workflow.decision_protocol == _original_prompt.DECISION_EXCHANGE_PROTOCOL:
        old_history_guidance = _original_prompt.INSTRUCTIONS[_original_prompt.INSTRUCTIONS.index('On a fresh provider conversation,'):_original_prompt.INSTRUCTIONS.index('Do not execute native provider tools.')]
        instructions = instructions.replace(old_history_guidance, 'Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again.\n')
    return instructions

from gene_annotation_episode.episodic_workflow.root.a108 import runtime_prompt as _original_prompt
