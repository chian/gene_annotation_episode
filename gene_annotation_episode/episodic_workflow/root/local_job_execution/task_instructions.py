"""Original local terminal task source_instructions with explicitly accounted fixed-role branches."""
from __future__ import annotations
from ..decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.tool_knowledge import INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS
from gene_annotation_episode.launch_instructions import INSTRUCTIONS as LAUNCH_INSTRUCTIONS
from .decision_guidance import REPORT_PROTOCOL, HISTORY_PROTOCOL, EXECUTION_EXPECTATIONS, HOST_EXECUTION_PROTOCOL


class LocalTaskInstructions:
    def instructions(self, context):
        specialist = self.workflow.specialist(self)
        instructions = specialist.instructions(self.workflow.binding_context(self))
        instructions += '\n' + REPORT_PROTOCOL + EXECUTION_EXPECTATIONS + HISTORY_PROTOCOL + HOST_EXECUTION_PROTOCOL
        if 'tool_knowledge' in context:
            instructions += KNOWLEDGE_INSTRUCTIONS
        if 'launch_instruction_library' in context:
            instructions += LAUNCH_INSTRUCTIONS
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            old_history_guidance = HISTORY_PROTOCOL
            instructions = instructions.replace(old_history_guidance,
                'Use request_context exchanges for your own attempt metadata and selected inputs; '
                'these create no completed action or observation. Read exact previously received '
                'outcomes with the ordinary episode.history tool, view=records and selected '
                'decision_indices. That read supplies its own ordinary action observation and '
                'does not execute or credit the historical work again.\n')
        return instructions

