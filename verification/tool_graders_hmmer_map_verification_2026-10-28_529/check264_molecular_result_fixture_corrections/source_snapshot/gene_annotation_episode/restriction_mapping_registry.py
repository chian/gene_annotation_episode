"""Host operands for one selected restriction operation and its durable replay.

Catalog installation and episode decisions belong to their existing owners.
This adapter selects no additional work and calculates no scientific quantities.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import stat
import sys

from .domain import ContractError, canonical
from .materials import artifact_path
from .restriction_mapping_bound_contracts import (
    restriction_native_request, validate_restriction_alias_arguments,
    validate_restriction_bound_record,
)
from .restriction_mapping_inputs import restriction_sequence_witness
from .restriction_mapping_jobs import RestrictionMappingJobs, restriction_operation_directory
from .restriction_mapping_publication import (
    read_published_restriction_result, read_restriction_input,
    retain_restriction_input, publish_restriction_result,
)


ALIASES = frozenset(("find_restriction_sites", "find_restriction_enzymes"))
_IMPLEMENTATIONS = ("restriction_mapping_contracts.py", "restriction_mapping_readers.py",
    "restriction_mapping_worker.py", "restriction_mapping_inputs.py",
    "restriction_mapping_bound_contracts.py", "restriction_mapping_jobs.py",
    "restriction_mapping_publication.py", "restriction_mapping_registry.py")


class RestrictionOperationUnpublished(RuntimeError):
    """Preserve an original unfinished selection for ordinary runtime restore."""


def restriction_work_reserved(store, operation_key):
    present = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='restriction_mapping_operations'").fetchone()
    return present is not None and store.db.execute(
        "SELECT 1 FROM restriction_mapping_operations WHERE operation_key=?",
        (operation_key,)).fetchone() is not None


def _require(condition, code):
    if not condition:
        raise ContractError("restriction_" + code)


def _received(reference, permitted):
    _require(type(permitted) in (tuple, list)
        and all(type(value) is str and bool(value) for value in permitted)
        and reference in permitted, "operand_not_received")


def _pin(path):
    """Pin regular selected host bytes; this is not scientific analysis."""
    path = Path(path).resolve(strict=True)
    before = path.lstat()
    _require(stat.S_ISREG(before.st_mode), "software_conflict")
    digest = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
        closed = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    _require(stamp(before) == stamp(opened) == stamp(closed) == stamp(path.lstat()), "software_conflict")
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": before.st_size}


def _software(store, key, *, mode, prior=None):
    directory = restriction_operation_directory(store, key)
    # Keep only import/runtime paths deliberately selected by this host. Never
    # copy credentials or unrelated provider environment into a native worker.
    package_root = str(Path(__file__).resolve().parent.parent)
    import_paths = [package_root]
    for path in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if path:
            resolved = str(Path(path).resolve())
            if resolved not in import_paths:
                import_paths.append(resolved)
    environment = {"PATH": os.defpath, "PYTHONPATH": os.pathsep.join(import_paths),
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(directory), "TMP": str(directory), "TEMP": str(directory),
        "XDG_CACHE_HOME": str(directory / "cache"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    if os.environ.get("PYTHONHOME"):
        environment["PYTHONHOME"] = str(Path(os.environ["PYTHONHOME"]).resolve())
    names = list(_IMPLEMENTATIONS)
    if mode == "native":
        selected = distribution("biopython")
        _require(selected.version == "1.88", "software_conflict")
        provenance = {"biopython_version": selected.version,
            "native_source_file": _pin(selected.locate_file("Bio/Restriction/Restriction.py")),
            "dictionary_file": _pin(selected.locate_file("Bio/Restriction/Restriction_Dictionary.py"))}
        names.append("restriction_mapping_native.py")
    else:
        _require(prior is not None and prior["native"] is not None, "native_unavailable")
        provenance = deepcopy(prior["native"]["software"])
        _require(provenance["biopython_version"] == "1.88"
            and provenance["native_source_file"] is not None
            and provenance["dictionary_file"] is not None, "software_conflict")
    return validate_restriction_bound_record("Software", {
        "python": _pin(sys.executable),
        "implementation_files": [_pin(Path(__file__).with_name(name)) for name in names],
        **provenance, "environment": environment})


def _authorize_retained(registry, reservation, permitted, *, scope):
    retained = read_restriction_input(registry.store, reservation["input_source_ref"])
    _received(retained["witness"]["sequence_ref"], permitted)
    if reservation["work_mode"] == "saved":
        _received(reservation["prior_result_source_ref"], permitted)
    # Validate present scope/ownership, retaining the original sequence bytes.
    # No new extraction, alias revision or numerical calculation occurs here.
    registry._check_sequence_operand(retained["witness"]["sequence_ref"], scope)


async def prepare_restriction_work(registry, tool_name, arguments, *, scope,
        operation_key, permitted_record_refs):
    arguments = validate_restriction_alias_arguments(tool_name, arguments)
    normalized = registry.store.validate_scope(scope)
    jobs = RestrictionMappingJobs(registry.store)
    try:
        existing = jobs.publication_state(operation_key)
    except ContractError as error:
        if str(error) != "restriction_operation_missing":
            raise
        existing = None
    if existing is not None:
        reservation = existing["reservation"]
        _require(reservation["tool_name"] == tool_name
            and canonical(reservation["arguments"]) == canonical(arguments)
            and canonical(reservation["scope"]) == canonical(normalized), "operation_conflict")
        _authorize_retained(registry, reservation, permitted_record_refs, scope=normalized)
        if existing["execution_proof"] is None:
            # Complete unchanged pre-dispatch preparation after interruption.
            jobs.reserve(**{field: reservation[field] for field in (
                "operation_key", "tool_name", "arguments", "scope", "input_source_ref",
                "sequence_binding", "worker_request", "software", "policy")})
            await jobs.run_async(operation_key)
        return reservation
    prior = None
    if arguments["mode"] == "native":
        selected = registry.store.get(arguments["sequence_ref"])
        witness = restriction_sequence_witness(registry.store, arguments["sequence_ref"],
            namespace="reference" if selected["record_type"] == "reference" else "subject",
            scope=normalized, permitted_record_refs=permitted_record_refs,
            sequence_reader=registry._sequence, check_operand=registry._check_sequence_operand)
        retained = retain_restriction_input(registry.store, operation_key=operation_key,
            tool_name=tool_name, arguments=arguments, scope=normalized, witness=witness)
        request = restriction_native_request(tool_name, arguments,
            sequence=witness["sequence"], sequence_binding=retained["sequence_binding"])
    else:
        _received(arguments["result_source_ref"], permitted_record_refs)
        prior = read_published_restriction_result(registry.store,
            arguments["result_source_ref"], scope=normalized)
        _require(prior["body"]["tool_name"] == tool_name, "saved_alias_conflict")
        _received(prior["witness"]["sequence_ref"], permitted_record_refs)
        retained = {"input_source_ref": prior["body"]["input_source_ref"],
            "sequence_binding": prior["sequence_binding"]}
        def saved_file(role):
            file = prior["body"]["files"][role]
            if file is None:
                return None
            return {"path": str(artifact_path(registry.store, file["artifact_ref"])),
                "sha256": file["sha256"], "size_bytes": file["size_bytes"]}
        _require(prior["native"] is not None, "native_unavailable")
        request = {"version": "restriction_worker_request_v1", "mode": "saved",
            "native_file": saved_file("native"), "catalog_file": saved_file("catalog"),
            "selected_sequence": retained["sequence_binding"]}
    reservation = jobs.reserve(operation_key=operation_key, tool_name=tool_name,
        arguments=arguments, scope=normalized, **retained, worker_request=request,
        software=_software(registry.store, operation_key, mode=arguments["mode"], prior=prior),
        policy=registry.local_job_policy.to_dict())
    await jobs.run_async(operation_key)
    return reservation


def publish_restriction_work(registry, operation_key):
    _require(registry.store.db.in_transaction, "publication_transaction_required")
    return publish_restriction_result(registry.store, operation_key)


def replay_restriction_work(registry, tool_name, arguments, *, scope,
        operation_key, permitted_record_refs):
    arguments = validate_restriction_alias_arguments(tool_name, arguments)
    state = RestrictionMappingJobs(registry.store).publication_state(operation_key)
    reservation = state["reservation"]
    _require(reservation["tool_name"] == tool_name
        and canonical(reservation["arguments"]) == canonical(arguments)
        and canonical(reservation["scope"]) == canonical(registry.store.validate_scope(scope)), "operation_conflict")
    _authorize_retained(registry, reservation, permitted_record_refs, scope=scope)
    row = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
        (operation_key,)).fetchone()
    _require(row is not None and row["id"] == reservation["operation_ref"]
        and row["name"] == tool_name and row["arguments"] == canonical(arguments)
        and canonical(registry.store.validate_scope(json.loads(row["scope"]))) == canonical(reservation["scope"])
        and state["published_outcome"] is not None
        and row["result"] == canonical(state["published_outcome"]), "publication_conflict")
    read_published_restriction_result(registry.store, state["published_source_ref"], scope=scope)
    return deepcopy(state["published_outcome"])


def retire_restriction_work(registry, operation_key):
    RestrictionMappingJobs(registry.store).retire(operation_key)


__all__ = ["ALIASES", "RestrictionOperationUnpublished", "restriction_work_reserved",
    "prepare_restriction_work", "publish_restriction_work",
    "replay_restriction_work", "retire_restriction_work"]
