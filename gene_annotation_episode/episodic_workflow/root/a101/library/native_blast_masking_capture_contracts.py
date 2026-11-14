"""Original native_blast_masking_acquisition scientific values and explicit received-record contracts."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_masking_contracts import _error
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_masking_contracts import _pair
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_masking_contracts import _path
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_masking_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_masking_contracts import validate_preflight_failures

VERSION = "native_blast_masking_capture_v1"

CAPTURE_FAILURE_CODES = frozenset({"sealed_bundle_unavailable", "original_bundle_invalid", "original_owner_invalid",
    "original_file_unavailable", "original_file_identity_mismatch", "input_not_original", "unsealed_file"})

_ROW_KEYS = {"direction", "role", "ordinal", "format", "relative_path", "artifact_ref", "sha256", "size_bytes"}

def _key(row):
    return row["direction"], row["role"], row["ordinal"], row["relative_path"]

def validate_native_blast_masking_capture(value):
    capture = finite_json_copy(value)
    if (type(capture) is not dict or set(capture) != {"version", "bundle_artifact_ref", "bundle_validated", "artifacts", "failures"}
            or capture["version"] != VERSION or type(capture["bundle_validated"]) is not bool
            or type(capture["artifacts"]) is not list or type(capture["failures"]) is not list
            or capture["bundle_artifact_ref"] is not None and type(capture["bundle_artifact_ref"]) is not str
            or capture["bundle_validated"] and capture["bundle_artifact_ref"] is None):
        _error("capture_shape_invalid")
    seen = set()
    for row in capture["artifacts"]:
        if (type(row) is not dict or set(row) != _ROW_KEYS or type(row["direction"]) is not str or row["direction"] not in {"input", "output"}
                or type(row["ordinal"]) is not int or row["ordinal"] != 0
                or any(type(row[k]) is not str or not row[k] for k in ("role", "format", "relative_path", "artifact_ref"))):
            _error("capture_artifact_invalid")
        _path(row["relative_path"])
        if _pair(row)[0] is None or row["artifact_ref"] != "artifact_" + row["sha256"] or _key(row) in seen:
            _error("capture_artifact_identity_invalid")
        seen.add(_key(row))
    for f in capture["failures"]:
        if (type(f) is not dict or set(f) != {"stage", "code", "direction", "role", "ordinal", "relative_path", "diagnostic_artifact_ref", "input_failures"}
                or f["stage"] != "custody" or type(f["code"]) is not str or f["code"] not in CAPTURE_FAILURE_CODES
                or f["diagnostic_artifact_ref"] is not None and (type(f["diagnostic_artifact_ref"]) is not str
                    or not f["diagnostic_artifact_ref"].startswith("artifact_"))):
            _error("capture_failure_invalid")
        validate_preflight_failures(f["input_failures"])
        if f["input_failures"]:
            _error("capture_custody_input_failure_context")
        if f["direction"] is None:
            if any(f[k] is not None for k in ("role", "ordinal", "relative_path")):
                _error("capture_failure_association_invalid")
        else:
            if type(f["direction"]) is not str or f["direction"] not in {"input", "output"} or type(f["ordinal"]) is not int or f["ordinal"] != 0 or type(f["role"]) is not str:
                _error("capture_failure_association_invalid")
            _path(f["relative_path"])
    if not capture["bundle_validated"] and capture["artifacts"]:
        _error("capture_unsealed_artifacts_forbidden")
    return capture
