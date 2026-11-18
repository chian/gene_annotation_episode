"""Original A103 presentation selection, frames, renderer priority and JSON fallback."""
from collections.abc import Mapping
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame
from gene_annotation_episode.episodic_workflow.root.a103.execution_prompt import is_api_launch_context, render_api_launch_prompt
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence_prompt import is_published_scientific_context, render_gene_context_evidence_prompt, text_instructions

def _ordinary_runtime_receiver_context(value):
    """Recognize the existing ordinary decision view, not a protocol frame."""
    if not isinstance(value, Mapping):
        return False
    goal, scope, working, tools = (value.get(name) for name in ('goal', 'scope', 'working_state', 'tools'))
    return isinstance(goal, Mapping) and isinstance(goal.get('objective'), str) and bool(goal['objective'].strip()) and isinstance(scope, Mapping) and isinstance(scope.get('subject_refs'), (list, tuple)) and isinstance(working, Mapping) and isinstance(working.get('subjects'), (list, tuple)) and isinstance(working.get('scope'), Mapping) and (working['scope'] == scope) and isinstance(tools, (list, tuple)) and all((isinstance(tool, Mapping) and isinstance(tool.get('name'), str) and bool(tool['name']) for tool in tools)) and ('requested_form' in value) and (value['requested_form'] is None or isinstance(value['requested_form'], Mapping)) and isinstance(value.get('controller'), Mapping) and isinstance(value.get('current_report_update'), Mapping) and ('last_local_outcome' in value)

def present_source_task(self, episode_id, role, instructions, context):
    """Render declared TASKs from reconstructed state; preserve other inputs."""
    from gene_annotation_episode.episodic_workflow.root.a103.library.hpc_prompt import is_hpc_context, render_hpc_prompt
    from gene_annotation_episode.episodic_workflow.root.a103.library.monitor_prompt import is_monitor_context, render_monitor_prompt
    from .task_presentation import render_receiver_prompt
    from gene_annotation_episode.episodic_workflow.root.a103.native_profile_presentation import has_native_profile_receiver_context
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence_prompt import is_selected_execution_context, render_selected_execution_prompt

    def has_text_task(value):
        return is_hpc_context(value) or is_published_scientific_context(value) or is_monitor_context(value) or is_api_launch_context(value) or is_selected_execution_context(value) or has_native_profile_receiver_context(value) or _ordinary_runtime_receiver_context(value)
    key = (episode_id, role)
    previous = self.scientific_prompt_states.get(key)
    state = None
    lookups = []
    if context.get('version') == DECISION_CONTEXT_VERSION:
        kind = context.get('kind')
        if kind == 'decision_bootstrap':
            if has_text_task(context.get('fields')):
                state = apply_state_frame(None, context)
                lookups = [row['lookup_result'] for row in context.get('restored_public_exchanges', ()) if 'lookup_result' in row]
            else:
                self.scientific_prompt_states.pop(key, None)
        elif kind == 'decision_update' and previous is not None:
            state = apply_state_frame(previous, context)
        elif kind == 'decision_update' and has_text_task(context.get('fields')):
            state = apply_state_frame(None, context)
        elif kind == 'decision_lookup_result' and previous is not None:
            state = previous
            lookups = [context.get('result')]
            if previous.get('contract_information_profile') == 'operation_contract_information_v1':
                lookups = list(context.get('pending_contract_information', ()))
                if context.get('result') not in lookups:
                    lookups.append(context.get('result'))
    elif has_text_task(context):
        state = deepcopy(context)
    if state is not None and has_text_task(state):
        if is_hpc_context(state):
            renderer = render_hpc_prompt
        elif is_published_scientific_context(state):
            renderer = render_gene_context_evidence_prompt
        elif is_api_launch_context(state):
            renderer = render_api_launch_prompt
        elif is_selected_execution_context(state):
            renderer = render_selected_execution_prompt
        elif is_monitor_context(state) and (not has_native_profile_receiver_context(state)):
            renderer = render_monitor_prompt
        else:
            renderer = render_receiver_prompt
        rendered = renderer(state, instructions, lookup_results=lookups)
        self.scientific_prompt_states[key] = state
        return (rendered, text_instructions(instructions))
    if state is not None:
        self.scientific_prompt_states.pop(key, None)
    return (json.dumps(context, allow_nan=False), instructions)
