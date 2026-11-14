"""Original native_hmmer_preparation_acquisition scientific values and explicit received-record contracts."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError
from pathlib import PurePosixPath
from gene_annotation_episode.episodic_workflow.root.a101.library.native_record_identity import finite_json_copy

VERSION = "native_hmmer_preparation_capture_v1"

_PREFIX = "native_hmmer_preparation_"

_CAPTURE_FIELDS = {"version", "bundle_artifact_ref", "bundle_validated", "artifacts",
    "invalid_artifacts", "failures", "complete"}

_ROW_FIELDS = {"direction", "role", "ordinal", "format", "relative_path", "artifact_ref"}

def _error(code):
    raise ContractError(_PREFIX + code)

def _path(value, *, absolute=False):
    if (type(value) is not str or not value or any(c in value for c in "\0\r\n\\")
            or value.startswith("//") or ".." in value.split("/") or value in {".", "/"}):
        _error("capture_path_invalid")
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or str(path) != value:
        _error("capture_path_invalid")
    return path

def _shape(capture):
    capture = finite_json_copy(capture)
    if (type(capture) is not dict or set(capture) != _CAPTURE_FIELDS or capture["version"] != VERSION
            or type(capture["bundle_validated"]) is not bool or type(capture["complete"]) is not bool
            or capture["bundle_artifact_ref"] is not None and type(capture["bundle_artifact_ref"]) is not str
            or any(type(capture[k]) is not list for k in ("artifacts", "invalid_artifacts", "failures"))):
        _error("capture_receipt_invalid")
    for row in capture["artifacts"] + capture["invalid_artifacts"]:
        if (type(row) is not dict or set(row) != _ROW_FIELDS or type(row["direction"]) is not str
                or row["direction"] not in {"input", "working_copy", "output"}
                or type(row["ordinal"]) is not int or row["ordinal"] < 0
                or row["direction"] == "output" and row["ordinal"] != 0
                or any(type(row[k]) is not str or not row[k] for k in ("role", "format", "relative_path", "artifact_ref"))):
            _error("capture_artifact_row_invalid")
        _path(row["relative_path"])
    for row in capture["failures"]:
        if (type(row) is not dict or set(row) != {"stage", "code", "record_key"}
                or row["stage"] != "capture" or type(row["code"]) is not str or not row["code"]
                or row["record_key"] is not None):
            _error("capture_failure_invalid")
    return capture
