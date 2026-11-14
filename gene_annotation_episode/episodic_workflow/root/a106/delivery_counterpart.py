"""Resolve a report's original child from retained action and delivery records."""
import json

from .episode_journal import WorkflowError


def child_role_for_delivery(workflow, source, index):
    action_row = workflow.journal.row('runtime_actions', source.episode_id, index)
    action = json.loads(action_row['action']) if action_row is not None else None
    selected_role = (action.get('role', 'improvement') if action is not None
        and action.get('kind') in {'child', 'job_child', 'episode_child'} else None)
    attempt = workflow.store.db.execute(
        'SELECT child_episode_id FROM runtime_report_attempts '
        'WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
        (workflow.run_id, source.episode_id, index)).fetchone()
    if attempt is not None:
        child = workflow.journal.row('runtime_episodes', attempt['child_episode_id'])
        if child is None:
            raise WorkflowError('original_delivery_child_unavailable')
        path = tuple(tuple(part) for part in json.loads(child['path']))
        if len(path) != len(source.path) + 1 or path[:-1] != tuple(source.path):
            raise WorkflowError('original_delivery_parent_conflict')
        role = path[-1][0]
        if selected_role is not None and role != selected_role:
            raise WorkflowError('original_delivery_child_role_conflict')
        return role
    if selected_role is None:
        raise WorkflowError('original_delivery_counterpart_unavailable')
    return selected_role
