"""Original supplied-record schemas extracted from native_blast_vdb_utility_execution; no execution admission."""
from __future__ import annotations

VERSION = "native_blast_vdb_offline_execution_v1"
RECEIPT_VERSION = "native_blast_vdb_offline_receipt_v1"
OFFLINE_FAILURE_CODES = frozenset({"offline_launcher_unavailable", "offline_runtime_identity_mismatch",
    "offline_setup_failed", "offline_status_unavailable", "offline_configuration_conflict", "offline_child_exec_failed"})
_FILE = {"type": "object", "properties": {"path": {"type": "string", "minLength": 1},
    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "size_bytes": {"type": "integer", "minimum": 0}},
    "required": ["path", "sha256", "size_bytes"], "additionalProperties": False}
OFFLINE_EXECUTION_SCHEMA = {"type": "object", "properties": {
    "version": {"const": VERSION}, "launcher": _FILE, "runtime_files": {"type": "array", "items": _FILE},
    "runtime_aliases": {"type": "array", "items": {"type": "object", "properties": {
        "path": {"type": "string", "minLength": 1}, "target_path": {"type": "string", "minLength": 1}},
        "required": ["path", "target_path"], "additionalProperties": False}},
    "system_interface_profile": {"const": "blast_vdb_bwrap_local_v1"}},
    "required": ["version", "launcher", "runtime_files", "runtime_aliases", "system_interface_profile"],
    "additionalProperties": False}
OFFLINE_ENVIRONMENT_SCHEMA = {"type": "object", "properties": {
    "NCBI_VDB_CONFIG": {"type": "string", "minLength": 1}, "BLAST_USAGE_REPORT": {"const": "false"},
    "NCBI_USAGE_REPORT_ENABLED": {"const": "false"}, "DO_NOT_TRACK": {"const": "1"}, "LC_ALL": {"const": "C"}},
    "required": ["NCBI_VDB_CONFIG", "BLAST_USAGE_REPORT", "NCBI_USAGE_REPORT_ENABLED", "DO_NOT_TRACK", "LC_ALL"],
    "additionalProperties": False}


