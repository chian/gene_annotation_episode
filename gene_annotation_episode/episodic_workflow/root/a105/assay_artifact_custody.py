"""Original retained assay-artifact byte verification."""
import hashlib

def _publication_bytes(store, reference):
    """Verify the original artifact ID, metadata and complete retained bytes."""
    from .native_file_capture import NativeFileCaptureError, _metadata
    metadata = _metadata(store, reference)
    # This is an authenticated producer's internal read. Model-facing material
    # access has separate File permissions; no such permission is conferred here.
    raw = store.get_artifact(reference)
    if len(raw) != metadata["size"] or hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
        raise NativeFileCaptureError("retained_artifact_mismatch")
    return raw

