"""A107 molecular publication bytes declarations."""
import hashlib

def _publication_bytes(store, reference):
    """Verify the original artifact ID, metadata and complete retained bytes."""
    from gene_annotation_episode.episodic_workflow.root.a107.native_file_capture import NativeFileCaptureError, _metadata
    metadata = _metadata(store, reference)
    raw = store.get_artifact(reference)
    if len(raw) != metadata['size'] or hashlib.sha256(raw).hexdigest() != metadata['sha256']:
        raise NativeFileCaptureError('retained_artifact_mismatch')
    return raw
