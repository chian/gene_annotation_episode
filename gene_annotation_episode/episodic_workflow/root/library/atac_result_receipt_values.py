"""Selected atac action controls and completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Completed-action checks use frozen controls and Store metadata, never scientific bytes.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
from typing import Literal, TypedDict

from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import validate_target
from gene_annotation_episode.native_file_capture import NativeFileIdentity, _identity
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_contracts import validate_atac_result_record
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_return_views import FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE, validate_atac_fact_values
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_worker import validate_atac_result_worker_plan, validate_atac_result_worker_result
from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_capture import validate_atac_native_capture
from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import POLICY, atac_driver_argv, validate_atac_requested_job, validate_atac_run_plan, _dependency_roots
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_receipt
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation


VERSION = "native_atac_differential_acquired_result_v1"


class AtacDifferentialResultIntent(TypedDict):
    version: Literal["atac_differential_result_intent_v1"]
    run_id: str
    episode_id: str
    path: list[list[str]]
    scope: dict
    assignment: dict
    original_request_sha256: str
    operation_key: str
    tool_name: Literal["execution.results.status", "execution.results.collect"]
    arguments: dict
    target: dict


class AtacDifferentialHandoffProof(TypedDict):
    source_record: dict
    body: dict
    assignment_snapshot: dict
    start_receipt: dict


class AtacDifferentialNativeSnapshot(TypedDict):
    original_plan: dict
    plan_file: NativeFileIdentity
    handle: dict
    handle_file: NativeFileIdentity
    request: dict
    request_raw: str
    request_file: NativeFileIdentity
    started_marker: dict | None
    started_marker_file: NativeFileIdentity | None
    driver_started: bool | None


class AtacDifferentialOrigin(TypedDict):
    episode_id: str
    operation_key: str


class AtacDifferentialQualifiedFiles(TypedDict):
    sheet: NativeFileIdentity | None
    calculations: NativeFileIdentity | None
    projection: NativeFileIdentity | None
    diagnostics: NativeFileIdentity | None
    tables: list[dict]
    calculated_tables: list[dict]


class AtacDifferentialFactGroups(TypedDict):
    atac_differential_projection: list[dict]
    atac_differential_saved_sheets: list[dict]
    atac_differential_failures: list[dict]


class AtacDifferentialSheetEvidence(TypedDict):
    version: Literal["atac_differential_sheet_evidence_v1"]
    sheet_file: NativeFileIdentity
    request_sha256: str
    original_identity: dict
    reference: dict
    samples: list[dict]
    conditions: list[dict]
    callpeak_bindings: list[dict]
    comparison: dict
    bam_references: list[dict]
    depth_selection: dict
    parsed_extents: list[dict]
    raw_tables: list[dict]
    calculations: dict | None
    projection_file: NativeFileIdentity | None
    native_record_population: bool
    private_refs: list[str]


class AtacDifferentialResultReceipt(TypedDict):
    version: Literal["native_atac_differential_acquired_result_v1"]
    intent: AtacDifferentialResultIntent
    handoff_proof: AtacDifferentialHandoffProof
    original_origins: list[AtacDifferentialOrigin]
    observation: dict | None
    native: AtacDifferentialNativeSnapshot | None
    source_action_file: NativeFileIdentity | None
    writer_closure_file: NativeFileIdentity | None
    capture: dict | None
    worker_plan: dict | None
    worker_capture: dict | None
    worker_execution: dict | None
    qualified_files: AtacDifferentialQualifiedFiles
    projection: dict | None
    host_failures: list[dict]
    facts: AtacDifferentialFactGroups
    sheet_evidence: AtacDifferentialSheetEvidence | None
    acquired_population: str | None
    delivery_complete: bool


@dataclass(frozen=True)
class AtacDifferentialResultAction:
    intent: AtacDifferentialResultIntent
    directory: Path


_READING = ContextVar("atac_differential_receipt_reading", default=())
_READ_CACHE = ContextVar("atac_differential_receipt_read_cache", default=None)
_OUTPUTS = ("sheet", "calculations", "projection", "diagnostics")
_TRACK_ROLES = ("signal1", "background1", "signal2", "background2")


def _finite_json_copy(value):
    canonical(value)  # Reject NaN/infinity; controls are ordinary finite JSON.
    return deepcopy(value)


def require(condition, code="atac_differential_result_authority_conflict"):
    if not condition:
        raise ValueError(code)


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), "atac_differential_result_invalid_record")


def same(left, right):
    return canonical(left) == canonical(right)


def artifact_references(value):
    """Locate artifact identities in validated nested controls and measurements.

    Software dependency objects are part of the control records. They are not
    the reference-string dependencies used by Store scientific records.
    """
    if isinstance(value, dict):
        for child in value.values():
            yield from artifact_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from artifact_references(child)
    elif type(value) is str and re.fullmatch(r"artifact_[0-9a-f]{64}", value):
        yield value


def decode(raw, *, newline=False, canonical_bytes=True):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "atac_differential_result_duplicate_key")
            result[key] = value
        return result
    value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs))
    require(not canonical_bytes or raw == canonical(value).encode("utf-8") + (b"\n" if newline else b""),
            "atac_differential_result_noncanonical_control")
    return value


@contextmanager
def directory(path, *, create=False):
    value = str(path)
    pure = PurePosixPath(value)
    require(pure.is_absolute() and str(pure) == value and value != "/" and ".." not in pure.parts
            and not any(c in value for c in "\0\r\n\\"), "atac_differential_result_invalid_path")
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in pure.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        require(os.fstat(fd).st_uid == os.geteuid(), "atac_differential_result_invalid_path")
        yield fd


@contextmanager
def regular(fd, name, *, flags=os.O_RDONLY):
    require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
    handle = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        require(stat.S_ISREG(os.fstat(handle).st_mode), "atac_differential_result_invalid_path")
        yield handle
    finally:
        os.close(handle)


def read_control(path):
    try:
        with directory(path.parent) as fd, regular(fd, path.name) as handle, os.fdopen(os.dup(handle), "rb") as stream:
            raw = stream.read()
    except FileNotFoundError:
        return None
    value = decode(raw, newline=path.name == "assignment.json" and raw.endswith(b"\n"))
    require(type(value) is dict, "atac_differential_result_invalid_record")
    return value


def immutable(path, value):
    value = _finite_json_copy(value)
    with directory(path.parent, create=True) as fd:
        previous = read_control(path)
        if previous is not None:
            require(same(previous, value), "atac_differential_result_control_conflict")
            return
        temporary = "." + path.name + "." + secrets.token_hex(16) + ".writing"
        try:
            with regular(fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as handle:
                with os.fdopen(os.dup(handle), "wb") as stream:
                    stream.write(canonical(value).encode("utf-8") + (b"\n" if path.name == "assignment.json" else b""))
                    stream.flush()
                os.fchmod(handle, 0o444)
                os.fsync(handle)
            try:
                os.link(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except FileExistsError:
                require(same(read_control(path), value), "atac_differential_result_control_conflict")
            os.fsync(fd)
        finally:
            os.unlink(temporary, dir_fd=fd)


def empty_facts() -> AtacDifferentialFactGroups:
    return {source: [] for source in FACT_SOURCES}


def empty_files() -> AtacDifferentialQualifiedFiles:
    return {**{role: None for role in _OUTPUTS}, "tables": [], "calculated_tables": []}


def unique(rows):
    result, seen = [], set()
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


def outcome(receipt):
    refs = list(dict.fromkeys(file["artifact_ref"] for bundle in receipt["facts"][SAVED_SOURCE]
        for file in (bundle["sheet"], *(r["file"] for r in bundle["tables"]))))
    return {"status": "completed", "record_refs": refs, "changed_record_refs": refs,
            "result": deepcopy(receipt), "feedback": None}


def qualified_files(capture, execution):
    result = empty_files()
    if capture is None or capture["result"] is None or execution is None:
        return result
    validate_atac_result_record("WorkerCapture", capture)
    declared = validate_atac_result_worker_result(capture["result"])["outputs"]
    require(len(declared) == len(capture["outputs"]))
    success = (execution["returncode"] == 0 and execution["failure"] is None
        and execution["terminal"] is True and execution["quiescent"] is True)
    for expected, row in zip(declared, capture["outputs"]):
        require(row["role"] == expected["role"] and row["table_key"] == expected["table_key"]
            and same(row["capture"]["declared"], expected["declaration"]))
        file = deepcopy(row["capture"]["observed"]) if success and row["capture"]["outcome"] == "verified" else None
        if row["role"] == "track_table":
            result["tables"].append({"table_key": row["table_key"], "file": file})
        elif row["role"] in {"partitions", "components", "regions"}:
            result["calculated_tables"].append({"table_key": row["table_key"], "role": row["role"], "file": file})
        else:
            require(row["role"] in _OUTPUTS)
            result[row["role"]] = file
    return result


def closure_value(receipt):
    return {"version": "atac_differential_writer_closure_v1", "intent_sha256": digest(receipt["intent"]),
        "native": receipt["native"], "observation": receipt["observation"]}


