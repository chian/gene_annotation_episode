from __future__ import annotations

def waiting_context(self, context):
    if self.workflow.native_event_information is not None:
        context['native_event_targets'] = self.workflow.native_event_information.read(self.workflow.binding_context(self))
    if self.workflow.permits_common_action(self, 'wait'):
        context['waiting_support'] = self.workflow.waiting_support(self, context)
    return context

def waiting_instructions(self, instructions):
    if self.workflow.permits_common_action(self, 'wait'):
        instructions += '\nA pending_child_ handle names your original in-process child, not an external event-provider target. To give its existing scheduler time to collect owned work, select wait with that handle, event returned, after_cursor 0 and reconsider_at null. An earlier ready owned sibling may wake this wait first; its original return is then collected before another decision. Waiting only reports readiness and earns no scientific credit. In-process state_changed/progress_committed events and mixed external wait conditions are not supported by this collection channel.'
    if self.workflow.native_event_information is not None and self.workflow.permits_common_action(self, 'wait'):
        instructions += '\nThe separate native_event_targets input names native notification targets assigned or actually received by this episode. A target is registration metadata, not proof that submission succeeded. Its state_changed event means the original service exit receipt was committed; the service may still be closing, so this does not establish result readiness or a child episode return. after_cursor records an event cursor actually received, initially zero. Select your own wait condition and subsequent status/monitor/result work. Request the native_event_targets source in original child forms when that handoff is needed. No event probability, gain or scientific credit follows from registration or passing time alone.'
    return instructions
