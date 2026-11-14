"""Original declared model presentation; private/scientific owners remain explicit."""
from collections.abc import Mapping
from copy import deepcopy
import json
from .decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame

def _rna_comparison_receiver_context(value):
    """Recognize the supplied receiving capability before its first child return.

    ExecutionEpisodes supplies this field only to annotation/scientific
    receivers. Starting their general text TASK while the group is empty keeps
    both frame reconstruction and fixed conversation instructions stable when
    an actual RNA result later arrives. This does not select or invent a result.
    """
    from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_views import PROJECTION_SOURCE
    if not isinstance(value, Mapping) or 'received_rna_comparison_values' not in value:
        return False
    groups = value['received_rna_comparison_values']
    return isinstance(groups, list) and all(
        isinstance(group, Mapping) and set(group) == {'fact_source', 'facts'}
        and group['fact_source'] == PROJECTION_SOURCE and isinstance(group['facts'], list)
        for group in groups)


def _ordinary_runtime_receiver_context(value):
    """Recognize the existing ordinary decision view, not a protocol frame."""
    if not isinstance(value, Mapping):
        return False
    goal, scope, working, tools = (value.get(name) for name in ("goal", "scope", "working_state", "tools"))
    return (isinstance(goal, Mapping) and isinstance(goal.get("objective"), str)
        and bool(goal["objective"].strip()) and isinstance(scope, Mapping)
        and isinstance(scope.get("subject_refs"), (list, tuple))
        and isinstance(working, Mapping) and isinstance(working.get("subjects"), (list, tuple))
        and isinstance(working.get("scope"), Mapping) and working["scope"] == scope
        and isinstance(tools, (list, tuple)) and all(isinstance(tool, Mapping)
            and isinstance(tool.get("name"), str) and bool(tool["name"]) for tool in tools)
        and "requested_form" in value and (value["requested_form"] is None or isinstance(value["requested_form"], Mapping))
        and isinstance(value.get("controller"), Mapping)
        and isinstance(value.get("current_report_update"), Mapping) and "last_local_outcome" in value)


class ModelPresentation:
    def _presentation(self, episode_id, role, instructions, context):
        """Render declared TASKs from reconstructed state; preserve other inputs."""
        from .execution_prompt import is_api_launch_context, render_api_launch_prompt
        from .library.published_scientific_task_presentation import (is_published_scientific_context,
            render_scientific_process_prompt)
        from .library.decision_prompt_text import text_instructions
        from .infernal_result_presentation import infernal_receiver_context
        from .hpc_prompt import is_hpc_context, render_hpc_prompt
        from .monitor_prompt import is_monitor_context, render_monitor_prompt
        from .presentation_literature_context import (
            is_literature_experimental_context)
        from .library.component_literature_presentation import render_component_axis_literature_prompt
        from .presentation_fact_contract import with_fact_contract_instructions
        from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_presentation import is_rna_comparison_results_context
        from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import (
            has_rna_structure_receiver_context, is_rna_structure_results_context)
        from .library.received_molecular_capabilities import has_molecular_receiver_context
        from .library.selected_execution_task_presentation import (
            is_selected_execution_context, render_selected_execution_prompt)

        def has_text_task(value):
            return (is_hpc_context(value) or is_published_scientific_context(value)
                    or is_monitor_context(value)
                    or is_api_launch_context(value)
                    or is_literature_experimental_context(value)
                    or is_rna_comparison_results_context(value)
                    or is_rna_structure_results_context(value)
                    or has_rna_structure_receiver_context(value)
                    or _rna_comparison_receiver_context(value)
                    or has_molecular_receiver_context(value)
                    or is_selected_execution_context(value)
                    or _ordinary_runtime_receiver_context(value))

        key = (episode_id, role)
        previous = self.scientific_prompt_states.get(key)
        state = None
        lookups = []
        if context.get("version") == DECISION_CONTEXT_VERSION:
            kind = context.get("kind")
            if kind == "decision_bootstrap":
                if has_text_task(context.get("fields")):
                    state = apply_state_frame(None, context)
                    lookups = [row["lookup_result"] for row in
                        context.get("restored_public_exchanges", ()) if "lookup_result" in row]
                else:
                    self.scientific_prompt_states.pop(key, None)
            elif kind == "decision_update" and previous is not None:
                state = apply_state_frame(previous, context)
            elif kind == "decision_update" and has_text_task(context.get("fields")):
                # A delta cannot establish the missing task/base state.
                state = apply_state_frame(None, context)
            elif kind == "decision_lookup_result" and previous is not None:
                state = previous
                lookups = [context.get("result")]
                if previous.get('contract_information_profile') == 'operation_contract_information_v1':
                    lookups = list(context.get('pending_contract_information', ()))
                    if context.get('result') not in lookups:
                        lookups.append(context.get('result'))
        elif has_text_task(context):
            # The legacy exchange protocol can carry a newly published process.
            # It already supplies the full state; its response schema is intact.
            state = deepcopy(context)
        if state is not None and has_text_task(state):
            if is_hpc_context(state):
                renderer = render_hpc_prompt
            elif is_literature_experimental_context(state):
                renderer = render_component_axis_literature_prompt
            elif is_published_scientific_context(state):
                renderer = render_scientific_process_prompt
            elif is_api_launch_context(state):
                renderer = render_api_launch_prompt
            elif is_rna_comparison_results_context(state):
                from .rna_structure_comparison_prompt import render_rna_comparison_results_prompt
                renderer = render_rna_comparison_results_prompt
            elif is_rna_structure_results_context(state):
                from .rna_structure_prompt import render_rna_structure_results_prompt
                renderer = render_rna_structure_results_prompt
            elif (is_selected_execution_context(state)
                    and not has_rna_structure_receiver_context(state)
                    and not _rna_comparison_receiver_context(state)):
                renderer = render_selected_execution_prompt
            elif (is_monitor_context(state)
                    and not has_rna_structure_receiver_context(state)
                    and not _rna_comparison_receiver_context(state)
                    and not has_molecular_receiver_context(state)):
                renderer = render_monitor_prompt
            else:
                from .rna_structure_comparison_receiver_prompt import render_rna_comparison_receiver_prompt
                renderer = render_rna_comparison_receiver_prompt
            rendered = renderer(state, instructions, lookup_results=lookups)
            rendered = with_fact_contract_instructions(rendered, state)
            self.scientific_prompt_states[key] = state
            return rendered, text_instructions(instructions)
        if state is not None:
            self.scientific_prompt_states.pop(key, None)
        # Legacy full contexts need the same received-result projection as
        # model_snapshot. Framed contexts were projected before their hashes
        # were computed; do not rewrite a frame or its revision here.
        presented = (context if context.get("version") == DECISION_CONTEXT_VERSION
                     else infernal_receiver_context(context))
        return json.dumps(presented, allow_nan=False), instructions


