"""Supplied-record schemas; no execution admission."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.blast_utility_contracts import blast_utility_schema_for_version
from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_contracts import DATABASE_OPERAND_SCHEMA, SOFTWARE_SCHEMA

MODES = (("makeblastdb", "create_sequence_database"),
         ("blastdbcmd", "extract_sequences"), ("blastdbcmd", "info"),
         ("blastdbcmd", "metadata"), ("blastdbcheck", "integrity"))
JOB_VERSION = "native_blast_utility_job_v1"
JOB_VERSION_V2 = "native_blast_utility_job_v2"
JOB_VERSION_V3 = "native_blast_utility_job_v3"
VDB_MODES = tuple(("blast_vdb_cmd", mode) for mode in ("extract_sequences", "info", "paths", "paths_all"))
PREPARATION_MODES = (("blastdb_aliastool", "convert_gi_list"),
    ("blastdb_aliastool", "convert_seqid_list"), ("blastdb_aliastool", "inspect_seqid_list"),
    ("blastdb_aliastool", "create_subset_alias"), ("blastdb_aliastool", "aggregate_databases"),
    ("blastdb_aliastool", "aggregate_volumes"), ("makembindex", "create_megablast_index"),
    ("makembindex", "show_filters"), ("makeprofiledb", "create_profile_database"))
LEGACY_MODES = MODES
MODES = LEGACY_MODES + PREPARATION_MODES + VDB_MODES
_RESERVED_ENV = frozenset({"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME",
                          "PYTHONPATH", "PYTHONHOME", "PYTHONDONTWRITEBYTECODE"})
_STR = {"type": "string", "minLength": 1, "pattern": r"^[^\x00\r\n]+$"}
_SHA = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}
_ENV = {"type": "object", "additionalProperties": {"type": "string"}}


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


INPUT_SCHEMA = _object({"input_key": _STR,
    "role": {"enum": ["sequence_input", "taxid_map", "mask_input"]},
    "path": _STR, "format": {"enum": ["fasta", "text", "maskinfo_xml", "maskinfo_asn1_text"]},
    "sha256": _SHA, "size_bytes": {"type": "integer", "minimum": 0},
    "artifact_ref": {"anyOf": [_STR, {"type": "null"}]}})
OUTPUT_SCHEMA = _object({"role": {"enum": ["stdout", "stderr", "database_family"]},
    "path_kind": {"enum": ["file", "prefix"]}, "relative_path": _STR,
    "format": {"enum": ["text", "blastdb_family", "blastdbcmd_tabular_v1",
                          "blastdb_info_text", "blastdb_metadata_json", "blastdbcheck_text"]}})
_HISTORICAL_OPERATION_SCHEMA = {"anyOf": [blast_utility_schema_for_version(version)
    for version in ("blast_utility_operation_v1", "blast_utility_operation_v2")]}
NATIVE_BLAST_UTILITY_JOB_SCHEMA = _object({"version": {"const": JOB_VERSION},
    "operation": _HISTORICAL_OPERATION_SCHEMA, "software": SOFTWARE_SCHEMA, "environment": _ENV,
    "inputs": {"type": "array", "items": INPUT_SCHEMA},
    "databases": {"type": "array", "maxItems": 1, "items": DATABASE_OPERAND_SCHEMA},
    "outputs": {"type": "array", "minItems": 2, "maxItems": 3, "items": OUTPUT_SCHEMA}})
from gene_annotation_episode.episodic_workflow.root.library.blast_preparation_contracts import MATERIALIZATION_ENTRY_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_contracts import DATABASE_OPERAND_SCHEMA as ADDITIONAL_DATABASE_OPERAND_SCHEMA
INPUT_SCHEMA_V2 = deepcopy(INPUT_SCHEMA)
INPUT_SCHEMA_V2["properties"]["role"] = {"enum": ["sequence_input", "taxid_map", "identifier_list",
    "database_list", "profile_list", "profile_input"]}
INPUT_SCHEMA_V2["properties"]["format"] = {"enum": ["fasta", "text", "gi_list_binary",
    "seqid_list_binary", "pssm_asn1_text", "pssm_asn1_binary"]}
OUTPUT_SCHEMA_V2 = _object({"output_key": _STR,
    "role": {"enum": ["stdout", "stderr", "identifier_list", "database_family", "index_family", "statistics"]},
    "path_kind": {"enum": ["file", "prefix"]}, "relative_path": _STR,
    "format": {"enum": ["text", "blastdb_family", "blast_index_family", "gi_list_binary",
        "seqid_list_binary", "blast_seqid_list_info_text"]},
    "population": {"enum": ["file", "prefix_members", "staged_database_members"]},
    "database_key": {"anyOf": [_STR, {"type": "null"}]}})
_ENTRY = deepcopy(MATERIALIZATION_ENTRY_SCHEMA)
del _ENTRY["properties"]["realized_token"]
_ENTRY["required"].remove("realized_token")
_PATH_MAP = _object({"source_path": _STR, "relative_path": _STR})
MATERIALIZATIONS_SCHEMA = _object({
    "database_copies": {"type": "array", "items": _object({"database_key": _STR,
        "native_paths": {"type": "array", "minItems": 1, "items": _PATH_MAP},
        "files": {"type": "array", "minItems": 1, "items": _PATH_MAP}})},
    "list_files": {"type": "array", "items": _object({"input_key": _STR, "relative_path": _STR,
        "grammar": {"enum": ["blast_database_lines", "profile_whitespace_tokens"]},
        "entries": {"type": "array", "minItems": 1, "items": _ENTRY}})}})
NATIVE_BLAST_UTILITY_JOB_V1_SCHEMA = NATIVE_BLAST_UTILITY_JOB_SCHEMA
NATIVE_BLAST_UTILITY_JOB_V2_SCHEMA = _object({"version": {"const": JOB_VERSION_V2},
    "operation": deepcopy(_HISTORICAL_OPERATION_SCHEMA), "software": SOFTWARE_SCHEMA, "environment": _ENV,
    "inputs": {"type": "array", "items": INPUT_SCHEMA_V2},
    "databases": {"type": "array", "items": {"anyOf": [DATABASE_OPERAND_SCHEMA, ADDITIONAL_DATABASE_OPERAND_SCHEMA]}},
    "outputs": {"type": "array", "minItems": 2, "items": OUTPUT_SCHEMA_V2},
    "materializations": MATERIALIZATIONS_SCHEMA})
from gene_annotation_episode.episodic_workflow.root.library.native_blast_vdb_context_schema import vdb_utility_context_request_schema
from gene_annotation_episode.episodic_workflow.root.library.native_blast_vdb_execution_schema import OFFLINE_ENVIRONMENT_SCHEMA, OFFLINE_EXECUTION_SCHEMA
INPUT_SCHEMA_V3 = deepcopy(INPUT_SCHEMA)
INPUT_SCHEMA_V3["properties"]["role"] = {"enum": ["entry_batch", "database_list"]}
INPUT_SCHEMA_V3["properties"]["format"] = {"const": "text"}
OUTPUT_SCHEMA_V3 = _object({"role": {"enum": ["stdout", "stderr"]}, "path_kind": {"const": "file"},
    "relative_path": _STR, "format": {"enum": ["text", "blast_vdb_cmd_table_v1",
        "blast_vdb_info_text_v1", "blast_vdb_paths_text_v1"]}})
NATIVE_BLAST_UTILITY_JOB_V3_SCHEMA = _object({"version": {"const": JOB_VERSION_V3},
    "operation": blast_utility_schema_for_version("blast_utility_operation_v3"),
    "software": SOFTWARE_SCHEMA, "environment": OFFLINE_ENVIRONMENT_SCHEMA,
    "inputs": {"type": "array", "items": INPUT_SCHEMA_V3},
    "databases": {"type": "array", "minItems": 1, "maxItems": 1, "items": ADDITIONAL_DATABASE_OPERAND_SCHEMA},
    "outputs": {"type": "array", "minItems": 2, "maxItems": 2, "items": OUTPUT_SCHEMA_V3},
    "vdb_context_request": vdb_utility_context_request_schema(), "offline_execution": OFFLINE_EXECUTION_SCHEMA})
NATIVE_BLAST_UTILITY_JOB_SCHEMA = {"anyOf": [NATIVE_BLAST_UTILITY_JOB_V1_SCHEMA,
    NATIVE_BLAST_UTILITY_JOB_V2_SCHEMA, NATIVE_BLAST_UTILITY_JOB_V3_SCHEMA]}
NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA = _object({
    "argv": {"type": "array", "minItems": 1,
             "items": {"type": "string", "pattern": r"^[^\x00\r\n]*$"}}, "environment": _ENV,
    "native_blast_utility": NATIVE_BLAST_UTILITY_JOB_SCHEMA})
# A v2 title can be the explicitly selected empty string. Keep the public
# object-shaped schema and the v1 nonempty-argument rule used by saved requests.
NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA["allOf"] = [{
    "if": {"properties": {"native_blast_utility": {"properties": {"version": {"const": JOB_VERSION}}}}},
    "then": {"properties": {"argv": {"items": _STR}}}}]


