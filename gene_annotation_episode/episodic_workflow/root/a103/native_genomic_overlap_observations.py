"""Read fixed files from an already authenticated overlap execution.

These functions do not authenticate episode access, poll a process, parse
scientific results, capture artifacts or create a completed-action observation.
The owning operation supplies the original plan and one actual lifecycle view.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from .native_file_capture import NativeFileCaptureError, _path, _producer_file
from .native_genomic_overlap_contracts import validate_genomic_overlap_run_plan


_RESULT_ROLES = frozenset({"parsed_set", "pair_manifest", "overlap_stdout", "batch_manifest"})


def _window(offset, limit):
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1024 * 1024:
        raise ValueError("bounded_native_output_window_required")


def _detail(directory, relative, *, tail_limit=None):
    root, leaf = _path(str(directory), absolute=True), _path(relative, absolute=False)
    result = {"path": str(root / leaf), "available": False}
    try:
        with _producer_file(root, leaf) as pinned:
            if tail_limit is None:
                result.update(available=True, bytes=pinned.stat().st_size)
            else:
                with pinned.open("rb") as stream:
                    size = os.fstat(stream.fileno()).st_size
                    offset = max(0, size - tail_limit)
                    stream.seek(offset)
                    raw = stream.read(min(tail_limit, max(0, size - offset)))
                result.update(available=True, bytes=size, tail_byte_offset=offset,
                              bytes_base64=base64.b64encode(raw).decode("ascii"))
    except NativeFileCaptureError as error:
        if error.code != "capture_file_unavailable":
            raise
    return result


def genomic_overlap_observed_files(plan: dict, view: dict, *,
        log_window_bytes: int, log_roles: tuple[str, ...]) -> tuple[list[dict], list[dict], bool]:
    """Return availability and requested tails using the existing observation shape."""
    plan = validate_genomic_overlap_run_plan(plan)
    if type(log_window_bytes) is not int or log_window_bytes <= 0:
        raise ValueError("positive_log_window_required")
    if (not isinstance(log_roles, (tuple, list)) or any(type(role) is not str for role in log_roles)
            or len(set(log_roles)) != len(log_roles)
            or any(role not in {"stdout", "stderr"} for role in log_roles)):
        raise ValueError("unsupported_native_log_role")
    if type(view) is not dict or type(view.get("terminal")) is not bool:
        raise ValueError("native_terminal_observation_required")
    attempt = Path(plan["attempt_directory"])
    root = Path(plan["identity"]["execution_id"]).parent
    outputs, logs, result_available = [], [], False
    for selected in plan["requested_job"]["native_genomic_overlap"]["outputs"]:
        role = selected["role"]
        is_log = role in {"stdout", "stderr"}
        limit = log_window_bytes if is_log and role in log_roles else None
        detail = _detail(attempt, selected["relative_path"], tail_limit=limit)
        if is_log and not detail["available"]:
            detail = _detail(root, role + ".log", tail_limit=limit)
        outputs.append({"role": role if is_log else "requested_output:" + detail["path"],
                        "available": detail["available"], "bytes": detail.get("bytes"),
                        "writer_closed": detail["available"] and view["terminal"]})
        result_available |= selected["role"] in _RESULT_ROLES and detail["available"]
        if is_log and role in log_roles and detail["available"]:
            logs.append({"role": role, "path": detail["path"], "offset": detail["tail_byte_offset"],
                         "observed_size": detail["bytes"], "bytes_base64": detail["bytes_base64"]})
    return outputs, logs, result_available


def read_genomic_overlap_output(plan: dict, *, path: str, offset: int, limit: int) -> dict:
    """Read one explicitly allowed bounded window from a pinned regular file."""
    plan = validate_genomic_overlap_run_plan(plan)
    _window(offset, limit)
    target = _path(path, absolute=True)
    attempt = _path(plan["attempt_directory"], absolute=True)
    root = _path(str(Path(plan["identity"]["execution_id"]).parent), absolute=True)
    allowed = {str(attempt / item["relative_path"]): (attempt, item["relative_path"])
               for item in plan["requested_job"]["native_genomic_overlap"]["outputs"]}
    allowed.update({str(root / (role + ".log")): (root, role + ".log")
                    for role in ("stdout", "stderr")})
    if str(target) not in allowed:
        raise ValueError("native_genomic_overlap_original_output_path_required")
    directory, relative = allowed[str(target)]
    with _producer_file(directory, _path(relative, absolute=False)) as pinned:
        with pinned.open("rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            stream.seek(offset)
            raw = stream.read(min(limit, max(0, size - offset)))
    return {"path": str(target), "offset": offset, "returned_bytes": len(raw),
            "size_bytes": size, "bytes_base64": base64.b64encode(raw).decode("ascii"),
            "text_utf8": raw.decode("utf-8", errors="replace")}
