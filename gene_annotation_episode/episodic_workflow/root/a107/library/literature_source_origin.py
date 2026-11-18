"""A107 source-reading task provenance from an admitted scientific parent."""
import json

def component_axis_source_origin(services, context):
    workflow = getattr(services, 'workflow', None)
    store = getattr(workflow, 'store', None)
    if store is None or context.run_id != workflow.run_id:
        return None
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_episodes'").fetchone() is None:
        return None
    for index in range(len(context.path) - 2, -1, -1):
        if context.path[index][0] != 'partner_presence_evidence':
            continue
        row = store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=? AND json(path)=json(?)', (context.run_id, json.dumps(context.path[:index + 1]))).fetchone()
        if row is not None:
            return {'version': 'admitted_component_axis_source_origin_v1', 'scientific_parent_episode_id': row['episode_id'], 'meaning': 'Original admitted scientific commission; source-reading task provenance only'}
        return None
    return None
