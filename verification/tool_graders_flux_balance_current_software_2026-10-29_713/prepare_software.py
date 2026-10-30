"""Explicit verification-only staging; no application imports or native work.

A successful staging return is metadata-unvalidated. Only the separately
retained bounded validation record can establish metadata readiness. Neither
record establishes that the seven-file module root can execute a native job.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat


REQUIRED_FILES = (
    "__init__.py", "execution_contracts.py", "flux_balance_contracts.py",
    "native_flux_balance_contracts.py", "native_flux_balance_storage.py",
    "native_flux_balance_cobra_glpk.py", "native_flux_balance_driver.py",
)
ORIGINAL_PLAN_IDENTITIES = {
    "1d574f373bc37740061eeeb7e0d91c2585905b598227e01cb8f95af8e905d98e": 5407351,
    "73e5742c7878eb51e828c13387969c2ae1d308ec59172e19d1c605fcbfef2b4a": 5407874,
}
REUSED_FIELDS = (
    "python", "python_version", "python_home", "dependency_roots", "runtime_files",
    "solver_runtime_files", "distributions", "solver_interface", "version",
)


class PreparationRefused(ValueError):
    """An explicit input or destination cannot be used without changing it."""


def _absolute(value):
    path = Path(value)
    if not path.is_absolute() or str(path) != str(value) or ".." in path.parts:
        raise PreparationRefused("absolute_explicit_path_required")
    return path


def _stamp(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def file_pin(path):
    """Streaming metadata check of one selected regular file, without rebinding."""
    path = _absolute(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise PreparationRefused("selected_file_not_regular")
        sha = hashlib.sha256()
        while block := stream.read(1024 * 1024):
            sha.update(block)
        if _stamp(before) != _stamp(os.fstat(stream.fileno())):
            raise PreparationRefused("selected_file_changed_during_read")
    return {"path": str(path), "sha256": sha.hexdigest(), "size_bytes": before.st_size}


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _digest(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def immutable_json(path, value):
    raw = _encoded(value) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), 0o444)
    return file_pin(path)


def _json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise PreparationRefused("duplicate_metadata_key")
            result[key] = value
        return result
    def nonfinite(_):
        raise PreparationRefused("nonfinite_metadata")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def check_reused_runtime(software):
    """Compare all original pins; never replace a selected pin with an observation."""
    rows = [("python", software["python"])]
    rows += [(field, pin) for field in ("runtime_files", "solver_runtime_files") for pin in software[field]]
    checks = []
    for role, expected in rows:
        observed, error = None, None
        try:
            observed = file_pin(expected["path"])
            state = "matched" if observed == expected else "mismatched"
        except FileNotFoundError:
            state, error = "missing", "FileNotFoundError"
        except (OSError, ValueError) as failure:
            state, error = "unreadable", type(failure).__name__ + ":" + str(failure)
        checks.append({"role": role, "expected": deepcopy(expected), "observed": observed,
                       "state": state, "error": error})
    return checks


def _copy_source(source, target):
    source_before = file_pin(source)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output, source.open("rb") as original:
        while block := original.read(1024 * 1024):
            output.write(block)
        output.flush()
        os.fsync(output.fileno())
        os.fchmod(output.fileno(), 0o444)
    source_after, copied = file_pin(source), file_pin(target)
    state = "matched" if source_before == source_after and all(
        copied[key] == source_before[key] for key in ("sha256", "size_bytes")) else "mismatched"
    return {"source_before": source_before, "source_after": source_after, "prepared": copied, "state": state}


def stage_flux_balance_current_software(*, selected_plan_path, source_root, destination):
    """Stage exactly029's source selection and original runtime, without execution.

    Returns detached software metadata only when every reused original runtime
    pin matches. ``ready`` is always false: the authoritative application schema
    validator runs separately inside bounded529 and retains its own result.
    On preparation failure no software.json is emitted. Existing nonempty
    destinations are refused, including those left by an earlier failed attempt.
    """
    selected = _absolute(selected_plan_path)
    source_root, destination = _absolute(source_root), _absolute(destination)
    if destination.exists() and (destination.is_symlink() or not destination.is_dir() or any(destination.iterdir())):
        raise PreparationRefused("destination_not_empty_or_regular")
    if source_root.is_relative_to(destination) or destination.is_relative_to(source_root):
        raise PreparationRefused("source_destination_overlap")
    if selected.is_relative_to(destination):
        raise PreparationRefused("selected_plan_destination_overlap")
    if not destination.parent.is_dir():
        raise PreparationRefused("destination_parent_required")
    destination.mkdir(mode=0o700, exist_ok=True)
    receipt = {"version": "flux_balance_software_preparation_v1", "ready": False,
        "readiness_meaning": "prepared_bytes_and_application_metadata_only",
        "status": "preparation_failed", "selected_plan": None, "original_attempt_identity": None,
        "original_source_function_sha256": None, "original_software_sha256": None,
        "old_module_root": None, "old_implementation_files": [], "source_root": str(source_root),
        "module_root": str(destination / "module_root"), "source_checks": [], "reused_runtime_checks": [],
        "software_file": None, "failures": [], "application_schema_validation": "not_run",
        "native_execution": "not_run"}
    software = None
    try:
        receipt["selected_plan"] = file_pin(selected)
        identity = receipt["selected_plan"]
        if ORIGINAL_PLAN_IDENTITIES.get(identity["sha256"]) != identity["size_bytes"]:
            raise PreparationRefused("exact_original688_plan_required")
        plan = _json(selected.read_bytes())
        if file_pin(selected) != identity:
            raise PreparationRefused("selected_plan_changed_during_read")
        original = plan["requested_job"]["native_flux_balance"]["software"]
        receipt.update(original_attempt_identity=deepcopy(plan["identity"]),
            original_source_function_sha256=plan["requested_job"]["native_flux_balance"]["source_function_sha256"],
            original_software_sha256=_digest(original), old_module_root=original["module_root"],
            old_implementation_files=deepcopy(original["implementation_files"]))
        checks = check_reused_runtime(original)
        receipt["reused_runtime_checks"] = checks
        receipt["failures"].extend({"code": "original_runtime_pin_" + row["state"],
            "path": row["expected"]["path"], "role": row["role"]} for row in checks if row["state"] != "matched")
        module_root = destination / "module_root"
        package = module_root / "gene_annotation_episode"
        package.mkdir(parents=True)
        for name in REQUIRED_FILES:
            row = _copy_source(source_root / "gene_annotation_episode" / name, package / name)
            receipt["source_checks"].append(row)
            if row["state"] != "matched":
                receipt["failures"].append({"code": "current_source_changed", "path": row["source_before"]["path"]})
        package.chmod(0o555)
        module_root.chmod(0o555)
        if not receipt["failures"]:
            software = deepcopy(original)
            software["module_root"] = str(module_root)
            software["implementation_files"] = [deepcopy(row["prepared"]) for row in receipt["source_checks"]]
            receipt["software_file"] = immutable_json(destination / "software.json", software)
            receipt["status"] = "staged_metadata_unvalidated"
    except (OSError, ValueError, KeyError, TypeError) as error:
        receipt["failures"].append({"code": "preparation_input_failure", "exception": type(error).__name__, "detail": str(error)})
    receipt_pin = immutable_json(destination / "preparation-receipt.json", receipt)
    return {"ready": False, "software": deepcopy(software), "receipt": deepcopy(receipt), "receipt_file": receipt_pin}
