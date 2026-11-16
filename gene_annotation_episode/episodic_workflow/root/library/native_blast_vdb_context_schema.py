"""Supplied-record schemas; no execution admission."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.blast_utility_contracts import SCHEMAS
from gene_annotation_episode.episodic_workflow.root.library.blast_preparation_contracts import DATABASE_DEPENDENCY_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.native_blast_database_contracts import DATABASE_OPERAND_SCHEMA as ADDITIONAL_DATABASE_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.native_blast_standard_database_contracts import DATABASE_OPERAND_SCHEMA

REQUEST_VERSION = "native_blast_vdb_utility_context_request_v1"
AUTHENTICATION_VERSION = "native_blast_vdb_context_authentication_v1"
_PREFIX = "/requested_job/native_blast_utility/vdb_context_request"
_STR = {"type": "string", "minLength": 1, "pattern": r"^[^\s\x00]+$"}
_INT = {"type": "integer", "minimum": 0}
_SHA = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}
_POINTER = {"type": "string", "pattern": r"^(?:/(?:[^~]|~[01])*)?$"}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def _array(items):
    return {"type": "array", "items": items}


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


ORIGIN_SCHEMA = {"anyOf": [
    _object({"kind": {"const": "request"}}),
    _object({"kind": {"const": "selected_json"}, "document_key": _STR, "pointer": _POINTER}),
]}
SAMPLE_ORIGIN_SCHEMA = {"anyOf": [*deepcopy(ORIGIN_SCHEMA["anyOf"]),
    _object({"kind": {"const": "dataset_sample"}, "document_key": _STR,
             "dataset_pointer": _POINTER, "sample_index": _INT})]}
JSON_ADDRESS_SCHEMA = {"anyOf": [
    _object({"kind": {"const": "database_manifest"}, "database_key": _STR}),
    _object({"kind": {"const": "database_metadata_manifest"}, "database_key": _STR, "manifest_index": _INT}),
    _object({"kind": {"const": "database_sidecar"}, "database_key": _STR,
             "role": {"enum": ["preparation_input_manifest", "preparation_receipt"]}}),
]}
DATABASE_FILE_ADDRESS_SCHEMA = _object({"kind": {"const": "database_file"},
    "database_key": _STR, "file_index": _INT})
DEPENDENCY_DECLARATION_SCHEMA = {"anyOf": [*deepcopy(ORIGIN_SCHEMA["anyOf"]),
    _object({"kind": {"const": "alias_directive"}, "database_key": _STR, "file_index": _INT,
             "directive": {"enum": ["DBLIST", "VDBLIST"]}, "directive_row_ordinal": _INT,
             "token_ordinal": _INT})]}
LIST_REFERENCE_SCHEMA = {"anyOf": [
    _object({"kind": {"const": "input"}, "input_key": _STR}),
    _object({"kind": {"const": "database_list"}, "list_key": _STR}),
]}


def _request_schema():
    props = deepcopy(SCHEMAS["VDBUtilityContext"]["properties"])
    props["source_inputs"]["items"]["properties"]["source"] = deepcopy(ORIGIN_SCHEMA)
    props["entry_identifier_bindings"]["items"]["properties"]["source"] = deepcopy(ORIGIN_SCHEMA)
    member = props["member_bindings"]["items"]["properties"]
    member["provenance"] = deepcopy(ORIGIN_SCHEMA)
    for key in ("read_identity", "reference_identity"):
        member[key]["anyOf"][0]["properties"]["source"] = deepcopy(ORIGIN_SCHEMA)
    props["sample_links"]["items"]["properties"]["link"]["properties"]["source"] = deepcopy(SAMPLE_ORIGIN_SCHEMA)
    dep = deepcopy(DATABASE_DEPENDENCY_SCHEMA["properties"])
    del dep["list_occurrence_id"]
    dep.update(list_ref=_nullable(LIST_REFERENCE_SCHEMA), declaration=DEPENDENCY_DECLARATION_SCHEMA)
    return _object({"version": {"const": REQUEST_VERSION},
        "documents": _array(_object({"document_key": _STR, "selection": JSON_ADDRESS_SCHEMA})),
        **{k: props[k] for k in ("source_inputs", "entry_identifier_bindings", "member_bindings", "sample_links")},
        "dependency_databases": _array({"anyOf": [DATABASE_OPERAND_SCHEMA, ADDITIONAL_DATABASE_SCHEMA]}),
        "database_lists": _array(_object({"list_key": _STR, "selection": DATABASE_FILE_ADDRESS_SCHEMA,
            "grammar": {"enum": ["vdb_whitespace_tokens", "blast_database_lines"]}})),
        "declared_dependencies": _array(_object(dep))})


REQUEST_SCHEMA = _request_schema()


def vdb_utility_context_request_schema() -> dict:
    return deepcopy(REQUEST_SCHEMA)


