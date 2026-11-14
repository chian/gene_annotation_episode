import json
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.prepared_record_identity import digest
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain

def validate_results_preparation(store, run_id, selected, actual, child):
    """Authenticate the original host-added C9 wrapper, without re-execution."""
    native = actual.get('adapter_assignment', {})
    if set(native) != {'version', 'job_ref', 'handoff_source_ref', 'scope_sha256', 'original_job_request_sha256'}:
        return False
    if native['version'] != 'a102_structural_results_assignment_v1':
        return False
    row = store.db.execute('SELECT * FROM a102_resource_jobs WHERE run_id=? AND job_ref=?', (run_id, native['job_ref'])).fetchone()
    if row is None or row['handoff'] is None:
        return False
    if selected['handoff'] != json.loads(row['handoff']) or native['handoff_source_ref'] != row['handoff_source_ref'] or native['scope_sha256'] != digest(plain(child.scope)) or (native['original_job_request_sha256'] != digest(json.loads(row['request']))):
        return False
    from gene_annotation_episode.episodic_workflow.root.a101.method_loop.identities import EpisodeRef
    parent = EpisodeRef(run_id, child.path[:-1]).episode_id
    if store.db.execute('SELECT 1 FROM a102_handoff_deliveries WHERE run_id=? AND episode_id=? AND job_ref=?', (run_id, parent, native['job_ref'])).fetchone() is None:
        return False
    try:
        store.validate_scope(plain(child.scope), parent_scope=json.loads(row['scope']))
    except ValueError:
        return False
    return True
