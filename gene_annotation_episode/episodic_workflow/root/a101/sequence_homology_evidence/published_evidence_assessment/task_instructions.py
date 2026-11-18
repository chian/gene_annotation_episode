"""Compose this A101 literature goal and actual context with its applicable original actions."""
from gene_annotation_episode.episodic_workflow.root.a101.library.literature_investigation_prompt import DECISION_EXCHANGE_PROTOCOL, REASONING_COMMIT_REQUIREMENT, INSTRUCTIONS

def instructions(source, context):
    instructions = INSTRUCTIONS
    specialist = source.workflow.specialist(source)
    if specialist is not None:
        specialized = specialist.instructions(source.workflow.binding_context(source))
        instructions = specialized if getattr(specialist, 'replaces_default_instructions', False) else instructions + '\n' + specialized
    if 'tool_knowledge' in context:
        instructions += source.workflow.knowledge.instructions
    if 'launch_instruction_library' in context:
        instructions += source.workflow.launch_instructions.instructions
    instructions += '\nWhen pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work.'
    if source.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
        old_history_guidance = INSTRUCTIONS[INSTRUCTIONS.index('On a fresh provider conversation,'):INSTRUCTIONS.index('Do not execute native provider tools.')]
        instructions = instructions.replace(old_history_guidance, 'Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again.\n')
    return instructions
