"""Original native_blast_utility_acquisition scientific values and explicit received-record contracts."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import DATABASE_ROLES
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import JOB_VERSION_V2
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import JOB_VERSION_V3
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import OUTPUT_ROLES
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import _error
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import _producer_path
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import database_file_selections
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import measurement_pair
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import native_blast_digest
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import staged_relative
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import validate_native_blast_utility_bundle
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import validate_native_blast_utility_plan

VERSION = "native_blast_utility_captured_bundle_v1"

CAPTURE_FAILURE_CODES = frozenset({"sealed_bundle_unavailable", "original_bundle_invalid", "original_owner_invalid",
    "original_file_unavailable", "original_file_identity_mismatch", "input_not_original", "unsealed_file"})

_CAPTURE_FIELDS = {"version", "source_ref", "plan", "original_bundle", "bundle_artifact_ref", "bundle_validated", "artifacts", "failures"}

_ROW_FIELDS = {"direction", "input_key", "database_key", "role", "ordinal", "original_path", "artifact_ref", "sha256", "size_bytes", "format", "completeness"}

_ASSOCIATION_FIELDS = {"direction", "input_key", "database_key", "role", "ordinal", "original_path"}

_FORMATS = {"fasta", "text", "maskinfo_xml", "maskinfo_asn1_text", "blastdbcmd_tabular_v1", "blastdb_info_text",
            "blastdb_metadata_json", "blastdbcheck_text", "blastdb_binary", "json", "unknown",
            "gi_list_binary", "seqid_list_binary", "blast_alias_text", "blast_seqid_list_info_text",
            "blast_index_binary", "blast_index_map_text", "blast_profile_aux_text", "pssm_asn1_text", "pssm_asn1_binary"}

_VDB_FORMATS = {"blast_vdb_cmd_table_v1", "blast_vdb_info_text_v1", "blast_vdb_paths_text_v1"}

def _selected_files(plan, bundle):
    """Keep original-path identity distinct from the actual staged-read location."""
    job, root = plan["requested_job"]["native_blast_utility"], Path(plan["attempt_directory"])
    result = []
    inputs = job["inputs"] if bundle is None else bundle["inputs"]
    for ordinal, row in enumerate(inputs):
        relative = staged_relative(row) if bundle is None else row["relative_path"]
        pair = (None, None) if bundle is None else measurement_pair(row, "final_")
        original = bundle is not None and pair == measurement_pair(row, "staged_") == measurement_pair(row, "expected_")
        result.append({"direction": "input", "input_key": row["input_key"], "database_key": None,
            "role": row["role"], "ordinal": ordinal, "original_path": row["path"] if bundle is None else row["original_path"],
            "format": row["format"], "completeness": "complete" if original else "unknown",
            "size_bytes": pair[0], "sha256": pair[1], "original": original,
            "read_root": str(root), "read_relative": relative})
    outputs = [r for r in job["outputs"] if r["path_kind"] == "file"] if bundle is None else bundle["artifacts"]
    for row in outputs:
        result.append({"direction": "output", "input_key": None, "database_key": None,
            "role": row["role"], "ordinal": row.get("ordinal", 0), "original_path": str(root / row["relative_path"]),
            "format": row["format"], "completeness": row.get("completeness", "unknown"),
            "size_bytes": row.get("size_bytes"), "sha256": row.get("sha256"), "original": bundle is not None,
            "read_root": str(root), "read_relative": row["relative_path"]})
    databases = database_file_selections(job) if bundle is None else bundle["database_files"]
    for ordinal, row in enumerate(databases):
        path = Path(row["original_path"])
        pair = (None, None) if bundle is None else measurement_pair(row, "final_")
        original = bundle is not None and pair == measurement_pair(row, "before_") == measurement_pair(row, "expected_")
        fmt = ("blastdb_metadata_json" if path.suffix in {".njs", ".pjs"} else "blastdb_binary") if row["role"] == "database_file" else (
            "json" if row["role"] in {"manifest", "metadata_manifest", "input_manifest"} else "unknown")
        if job["version"] == JOB_VERSION_V3:
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_vdb_utility_context import vdb_utility_database_operands
            db = next(d for d in vdb_utility_database_operands(job) if d["database_key"] == row["database_key"])
            if db["kind"] == "vdb" and row["role"] == "database_file":
                fmt = "unknown"
            elif row["role"] == "preparation_receipt":
                fmt = "json"
        result.append({"direction": "database", "input_key": None, "database_key": row["database_key"],
            "role": row["role"], "ordinal": ordinal, "original_path": str(path), "format": fmt,
            "completeness": "complete" if original else "unknown", "size_bytes": pair[0], "sha256": pair[1],
            "original": original, "read_root": str(path.parent), "read_relative": path.name})
    if job["version"] == JOB_VERSION_V2:
        result.extend(_materialized_files(plan, bundle, result))
    return result

def _materialized_files(plan, bundle, selected):
    """646/002+003: immutable originals and realized occurrences stay separate."""
    job, root = plan["requested_job"]["native_blast_utility"], Path(plan["attempt_directory"])
    receipts = [] if bundle is None else bundle["materializations"]
    by_relative = {r["relative_path"]: r for r in receipts}
    result = []
    originals = {r["input_key"]: r for r in job["inputs"]}
    db_files = {(r["database_key"], r["original_path"]): r for r in selected if r["direction"] == "database" and r["role"] == "database_file"}
    requests = [(r["input_key"], None, r["role"], i, staged_relative(r), r["format"])
                for i, r in enumerate(job["inputs"])]
    ordinal = 0
    for copy in job["materializations"]["database_copies"]:
        for row in copy["files"]:
            requests.append((None, copy["database_key"], "database_file", ordinal, row["relative_path"],
                             db_files[copy["database_key"], row["source_path"]]["format"]))
            ordinal += 1
    requests += [(r["input_key"], None, "materialized_list", i, r["relative_path"], "text")
                 for i, r in enumerate(job["materializations"]["list_files"])]
    for key, db, role, ordinal, relative, fmt in requests:
        receipt = by_relative.get(relative)
        pair, original = (None, None), False
        if receipt is not None:
            if receipt["kind"] == "list_rewrite":
                pair = receipt["size_bytes"], receipt["sha256"]
                original = not any(f["stage"] == "materializations" and f["relative_path"] == relative for f in bundle["failures"])
            else:
                final = receipt["final"]
                pair = (None, None) if final is None else (final["size_bytes"], final["sha256"])
                original = receipt["expected"] == receipt["staged"] == final
        result.append({"direction": "materialization", "input_key": key, "database_key": db,
            "role": role, "ordinal": ordinal, "original_path": str(root / relative), "format": fmt,
            "completeness": "complete" if original else "unknown", "size_bytes": pair[0], "sha256": pair[1],
            "original": original, "read_root": str(root), "read_relative": relative})
    return result

def _key(row):
    return tuple(row[k] for k in ("direction", "input_key", "database_key", "role", "ordinal", "original_path"))

def _association(row, *, nullable=False, preparation=False, vdb=False):
    if nullable and row["direction"] is None:
        if any(row[k] is not None for k in _ASSOCIATION_FIELDS):
            _error("capture_global_failure_association")
        return
    direction = row["direction"]
    if type(direction) is not str or direction not in ({"input", "output", "database", "materialization"} if preparation else {"input", "output", "database"}):
        _error("capture_direction_invalid")
    if type(row["ordinal"]) is not int or row["ordinal"] < 0:
        _error("capture_ordinal_invalid")
    _producer_path(row["original_path"], absolute=True)
    roles = {"input": {"sequence_input", "taxid_map", "mask_input"}, "output": OUTPUT_ROLES, "database": DATABASE_ROLES}
    if vdb:
        roles["input"] = {"entry_batch", "database_list"}
    if preparation:
        roles["input"] |= {"identifier_list", "database_list", "profile_list", "profile_input"}
        roles["output"] = set(roles["output"]) | {"identifier_list", "alias_file", "index_file", "profile_file", "statistics"}
        roles["materialization"] = roles["input"] | {"materialized_list", "database_file"}
    if type(row["role"]) is not str or row["role"] not in roles[direction]:
        _error("capture_role_invalid")
    for key, expected in (("input_key", direction == "input" or direction == "materialization" and row["role"] != "database_file"),
                          ("database_key", direction == "database" or direction == "materialization" and row["role"] == "database_file")):
        if expected and (type(row[key]) is not str or not row[key]) or not expected and row[key] is not None:
            _error("capture_key_invalid")

def validate_native_blast_utility_capture(value):
    capture = finite_json_copy(value)
    if (type(capture) is not dict or set(capture) != _CAPTURE_FIELDS or capture["version"] != VERSION
            or type(capture["bundle_validated"]) is not bool or type(capture["artifacts"]) is not list
            or type(capture["failures"]) is not list):
        _error("capture_shape_invalid")
    validate_native_blast_utility_plan(capture["plan"])
    preparation = capture["plan"]["requested_job"]["native_blast_utility"]["version"] == JOB_VERSION_V2
    vdb = capture["plan"]["requested_job"]["native_blast_utility"]["version"] == JOB_VERSION_V3
    for key in ("source_ref", "bundle_artifact_ref"):
        if capture[key] is not None and (type(capture[key]) is not str or not capture[key]):
            _error("capture_reference_invalid")
    if capture["bundle_validated"]:
        if capture["bundle_artifact_ref"] is None:
            _error("capture_bundle_reference_required")
        validate_native_blast_utility_bundle(capture["original_bundle"], capture["plan"])
        if not capture["original_bundle"]["writer_closed"]:
            _error("capture_writer_not_closed")
    elif capture["original_bundle"] is not None or capture["source_ref"] is not None or capture["artifacts"]:
        _error("capture_unvalidated_measurements_forbidden")
    seen = set()
    for row in capture["artifacts"]:
        if type(row) is not dict or set(row) != _ROW_FIELDS:
            _error("capture_artifact_shape")
        _association(row, preparation=preparation, vdb=vdb)
        pair = measurement_pair(row)
        if (pair[0] is None or row["artifact_ref"] != "artifact_" + row["sha256"]
                or type(row["format"]) is not str or row["format"] not in (_FORMATS | _VDB_FORMATS if vdb else _FORMATS)
                or type(row["completeness"]) is not str or row["completeness"] not in {"complete", "partial", "unknown"}
                or _key(row) in seen):
            _error("capture_artifact_identity_invalid")
        seen.add(_key(row))
    seen_failures = set()
    for row in capture["failures"]:
        if (type(row) is not dict or set(row) != {"stage", "code", "diagnostic_artifact_ref"} | _ASSOCIATION_FIELDS
                or row["stage"] != "custody" or type(row["code"]) is not str or row["code"] not in CAPTURE_FAILURE_CODES
                or row["diagnostic_artifact_ref"] is not None and (type(row["diagnostic_artifact_ref"]) is not str
                    or not row["diagnostic_artifact_ref"].startswith("artifact_"))):
            _error("capture_failure_shape")
        _association(row, nullable=True, preparation=preparation, vdb=vdb)
        digest = native_blast_digest(row)
        if digest in seen_failures:
            _error("capture_duplicate_failure")
        seen_failures.add(digest)
    return capture
