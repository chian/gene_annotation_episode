"""Original declared model presentation; private/scientific owners remain explicit."""
from collections.abc import Mapping
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame
from gene_annotation_episode.episodic_workflow.root.decision_frame_presentation import present_decision_context

def render_decision_context(self, episode_id, role, instructions, context):
    """Render declared TASKs from reconstructed state; preserve other inputs."""
    from .presentation_selection import source_presentation_selection
    has_text_task, render_task, text_instructions, infernal_receiver_context = source_presentation_selection()

    return present_decision_context(self, episode_id, role, instructions, context,
        has_text_task=has_text_task, render_task=render_task,
        text_instructions=text_instructions,
        infernal_receiver_context=infernal_receiver_context)


render_decision_context.presentation_protocol = 'episode_context_presentation_v1'
