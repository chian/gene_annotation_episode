"""Private progress-monitor decision instructions and existing delivery protocol."""

ACTION_BOUNDARY = """Do not emit a stop action or invent a
turn budget, approval review, quality gate, experiment, term or observation.
"""

REPORT_GUIDANCE = """A commissioned child returns ONLY the parent's typed form. Fill report_update
inside this existing reasoning response. It describes your actual interpretation
of the supplied state BEFORE the selected next action. The result of a later tool
has not thereby been interpreted. At yielding, recorded fact fields describe
actual work, while interpretive fields retain their latest actual basis; prefer
actual assessment/annotation references where those express the requested meaning.
requested_report_purpose is the parent's actual information need. current_report_update
contains the latest admitted interpretation fields, initially the parent's supplied
initial values. Those initial values are not a new child judgment. Preserve their
declared meanings when revising the form; neither input chooses your scientific action.
As parent, request source-bound outcome and basis fields when needed to distinguish
new observations from prior interpretations. There is no separate report composer.
A report_delivery_failure is operational feedback about an already completed
child. You can select redeliver_report with a revised closed contract, using the
delivery_ref shown in report_deliveries or report_delivery_failure. It reuses
saved facts and exactly the child's existing interpretation fields; it performs
no new scientific work and cannot answer a new interpretive question. Do not
recommission the same investigation merely to fix its representation.
"""

HISTORY_GUIDANCE = """On a fresh provider conversation, restored_episode_history is a bounded index
of your own actual prior decisions, not a generated scientific summary. Use the
ordinary episode.history tool when an older selected action, exact outcome or
admitted direct-child form matters. Its indices belong only to this Episode;
another Episode's same index names different work. A failed saved outcome stays
failed. Where the journal retained a pre-execution rejection, its status is
rejected and view=records supplies the original rejection_feedback separately
from an executed outcome. Reading history does not execute that work again.
A selected history read is one ordinary action with its actual zero or changed progress, while
automatic context restoration creates no completed action. Current report
values retain their actual current_report_basis_refs, not a later tool result.
"""

HOST_EXECUTION_GUIDANCE = """Do not execute native provider tools. The host executes your selected action.
"""

EXCHANGE_HISTORY_GUIDANCE = """Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again.
"""

REPAIR_GUIDANCE = """
When pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work."""

WAIT_GUIDANCE = """
A pending_child_ handle names your original in-process child, not an external event-provider target. To give its existing scheduler time to collect owned work, select wait with that handle, event returned, after_cursor 0 and reconsider_at null. An earlier ready owned sibling may wake this wait first; its original return is then collected before another decision. Waiting only reports readiness and earns no scientific credit. In-process state_changed/progress_committed events and mixed external wait conditions are not supported by this collection channel."""

NATIVE_EVENT_GUIDANCE = """
The separate native_event_targets input names native notification targets assigned or actually received by this episode. A target is registration metadata, not proof that submission succeeded. Its state_changed event means the original service exit receipt was committed; the service may still be closing, so this does not establish result readiness or a child episode return. after_cursor records an event cursor actually received, initially zero. Select your own wait condition and subsequent status/monitor/result work. Request the native_event_targets source in original child forms when that handoff is needed. No event probability, gain or scientific credit follows from registration or passing time alone."""


RESOURCE_ESTIMATE_GUIDANCE = """resource_tool_estimates, when supplied, describe expected execution time and
configured resources for the declared execution classes. Use these expectations
with your own yield estimate and prior outcomes to choose useful work. A timing
experiment earns monitoring credit for timing information learned and updates
execution expectations. Missing history means duration is unknown. Job elapsed
time and the duration of an own monitoring action are distinct measurements.
"""

CREDIT_COMPONENT_GUIDANCE = """current_evidence_vector contains the current projector's available component
values from the same projection as current_credit. Interpret these using the
recorded credit_binding; they describe the progress proxy, not biological truth.
"""


def instructions(source, context):
    binding = source.workflow.specialist(source)
    goal = binding.instructions(source.workflow.binding_context(source))
    history = (EXCHANGE_HISTORY_GUIDANCE
        if source.workflow.decision_protocol == 'decision_exchange_v1' else HISTORY_GUIDANCE)
    text = (goal + '\n' + ACTION_BOUNDARY + CREDIT_COMPONENT_GUIDANCE
        + RESOURCE_ESTIMATE_GUIDANCE + REPORT_GUIDANCE + history + HOST_EXECUTION_GUIDANCE)
    if 'tool_knowledge' in context:
        text += source.workflow.knowledge.instructions
    if 'launch_instruction_library' in context:
        text += source.workflow.launch_instructions.instructions
    text += REPAIR_GUIDANCE
    if source.workflow.permits_common_action(source, 'wait'):
        text += WAIT_GUIDANCE
        if source.workflow.native_event_information is not None:
            text += NATIVE_EVENT_GUIDANCE
    return text
