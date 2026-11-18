"""Private original A102 selected native execution presentation."""
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence_prompt import Mapping, _execution_presentation_values, _pick, _section, _selected_execution_task, _steering, _values, is_selected_execution_context

def present_native_task(state, instructions, *, lookup_results=()):
    """Present the detached original execution TASK with current own STEERING."""
    if not is_selected_execution_context(state):
        raise ValueError('selected_execution_task_required')
    steering = _execution_presentation_values(_pick(state, ('action_yields', 'controller', 'current_credit', 'completed_action_reports', 'last_local_outcome', 'feedback', 'child_reports', 'pending_work', 'report_deliveries', 'waiting_support', 'resource_tool_estimates', 'pending_child_delivery')))
    lookups = [_execution_presentation_values(value) for value in lookup_results]
    parts = [_selected_execution_task(state, instructions), _steering(steering, lookups)]
    progress = {}
    if isinstance(state.get('execution_progress'), Mapping):
        progress['execution_progress'] = _pick(state['execution_progress'], ('execution_completed',))
    if isinstance(state.get('practical_progress'), Mapping):
        progress['practical_progress'] = _pick(state['practical_progress'], ('credit', 'initial_credit', 'operational_credit', 'requirements', 'satisfied_keys'))
    if 'practical_completion' in state:
        progress['practical_completion'] = state['practical_completion']
    if progress:
        _section(parts, 'Current execution information', _values(_execution_presentation_values(progress)))
    return '\n\n'.join(parts)
