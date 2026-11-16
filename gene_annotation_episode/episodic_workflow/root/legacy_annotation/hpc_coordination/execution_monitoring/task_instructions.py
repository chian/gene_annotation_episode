from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.episodic_workflow.root.goal import INSTRUCTIONS
from gene_annotation_episode.tool_knowledge import INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS
from gene_annotation_episode.launch_instructions import INSTRUCTIONS as LAUNCH_INSTRUCTIONS
from gene_annotation_episode.episodic_workflow.root.goal import REASONING_COMMIT_REQUIREMENT

class MonitorTaskInstructions:

    def instructions(self, context):
        instructions = INSTRUCTIONS
        specialist = self.workflow.specialist(self)
        if specialist is not None:
            specialized = specialist.instructions(self.workflow.binding_context(self))
            instructions = specialized if getattr(specialist, 'replaces_default_instructions', False) else instructions + '\n' + specialized
        if self.workflow.permits_common_action(self, 'reason'):
            instructions += '\n' + REASONING_COMMIT_REQUIREMENT
        if 'tool_knowledge' in context:
            instructions += KNOWLEDGE_INSTRUCTIONS
        if 'launch_instruction_library' in context:
            instructions += LAUNCH_INSTRUCTIONS
        instructions += '\nWhen pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work.'
        if self.workflow.permits_common_action(self, 'wait'):
            instructions += '\nA pending_child_ handle names your original in-process child, not an external event-provider target. To give its existing scheduler time to collect owned work, select wait with that handle, event returned, after_cursor 0 and reconsider_at null. An earlier ready owned sibling may wake this wait first; its original return is then collected before another decision. Waiting only reports readiness and earns no scientific credit. In-process state_changed/progress_committed events and mixed external wait conditions are not supported by this collection channel.'
        if self.workflow.native_event_information is not None and self.workflow.permits_common_action(self, 'wait'):
            instructions += '\nThe separate native_event_targets input names native notification targets assigned or actually received by this episode. A target is registration metadata, not proof that submission succeeded. Its state_changed event means the original service exit receipt was committed; the service may still be closing, so this does not establish result readiness or a child episode return. after_cursor records an event cursor actually received, initially zero. Select your own wait condition and subsequent status/monitor/result work. Request the native_event_targets source in original child forms when that handoff is needed. No event probability, gain or scientific credit follows from registration or passing time alone.'
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            history_guidance = INSTRUCTIONS[INSTRUCTIONS.index('On a fresh provider conversation,'):INSTRUCTIONS.index('Do not execute native provider tools.')]
            instructions = instructions.replace(history_guidance, 'Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again.\n')
        return instructions
