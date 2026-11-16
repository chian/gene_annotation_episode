from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.episodic_workflow.root.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.tool_knowledge import INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS
from gene_annotation_episode.launch_instructions import INSTRUCTIONS as LAUNCH_INSTRUCTIONS
from gene_annotation_episode.episodic_workflow.root.goal import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from .waiting import waiting_instructions

class HomologyAcquisitionTaskInstructions:

    def instructions(self, context):
        instructions = self.workflow.job_episodes.implementation_for_path(self.path).instructions('job_results')
        if self.workflow.permits_common_action(self, 'reason'):
            instructions += '\n' + REASONING_COMMIT_REQUIREMENT
        if 'tool_knowledge' in context:
            instructions += KNOWLEDGE_INSTRUCTIONS
        if 'launch_instruction_library' in context:
            instructions += LAUNCH_INSTRUCTIONS
        instructions += '\nWhen pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work.'
        instructions = waiting_instructions(self, instructions)
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            history_guidance = INSTRUCTIONS[INSTRUCTIONS.index('On a fresh provider conversation,'):INSTRUCTIONS.index('Do not execute native provider tools.')]
            instructions = instructions.replace(history_guidance, 'Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again.\n')
        return instructions
