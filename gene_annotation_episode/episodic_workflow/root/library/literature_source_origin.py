"""Read the admitted scientific ancestor's source-task provenance."""
import json


def component_axis_source_origin(services, context):
    """Read only the nearest admitted scientific ancestor's axis metadata.

    No axis is inferred from a goal, source label or available capability. The
    result is task provenance, never scientific evidence or a selected assay.
    """
    from ..scientific_process_records import SELECTION_VERSION
    workflow = getattr(services, 'workflow', None)
    store = getattr(workflow, 'store', None)
    if store is None or context.run_id != workflow.run_id:
        return None
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_episodes'").fetchone() is None:
        return None
    for index in range(len(context.path)-2, -1, -1):
        if context.path[index][0] != 'scientific_process':
            continue
        row = store.db.execute("SELECT episode_id, "
            "json_extract(request,'$.message.episode_assignment.selection.version') AS version, "
            "json_extract(request,'$.message.episode_assignment.selection.evidence_axis.option_id') AS axis "
            "FROM runtime_episodes WHERE run_id=? AND json(path)=json(?)",
            (context.run_id, json.dumps(context.path[:index+1]))).fetchone()
        if row is not None and row['version'] == SELECTION_VERSION and row['axis'] in {'A107', 'A110'}:
            return {'version': 'admitted_component_axis_source_origin_v1',
                'evidence_axis': row['axis'], 'scientific_parent_episode_id': row['episode_id'],
                'meaning': 'Original admitted scientific commission; source-reading task provenance only'}
        return None
    return None


