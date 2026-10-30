"""Observe fixed files belonging to an already authenticated chromatin job.

Availability and bounded log bytes are observations, not scientific results or
proof of completion. The caller supplies the original plan and lifecycle view.
These functions neither dispatch work nor create credit or episode turns.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from .native_file_capture import NativeFileCaptureError, _path, _producer_file
from .native_chromatin_interaction_contracts import validate_chromatin_run_plan


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


def chromatin_observed_files(plan: dict, view: dict, *, log_window_bytes: int,
        log_roles: tuple[str, ...]) -> tuple[list[dict], list[dict], bool]:
    """Report original output availability and explicitly requested log tails."""
    plan = validate_chromatin_run_plan(plan)
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
    for selected in plan["outputs"]:
        role = selected["role"]
        is_log = role in {"stdout", "stderr"}
        limit = log_window_bytes if is_log and role in log_roles else None
        detail = _detail(attempt, selected["relative_path"], tail_limit=limit)
        if is_log and not detail["available"]:
            detail = _detail(root, role + ".log", tail_limit=limit)
        outputs.append({"role": role if is_log else "requested_output:" + detail["path"],
            "available": detail["available"], "bytes": detail.get("bytes"),
            "writer_closed": detail["available"] and view["terminal"]})
        # An acquired source or an unsealed table alone is not a result bundle.
        # Manifest availability still requires validation by the results path.
        result_available |= role in {"population_manifest", "bundle"} and detail["available"]
        if is_log and role in log_roles and detail["available"]:
            logs.append({"role": role, "path": detail["path"], "offset": detail["tail_byte_offset"],
                "observed_size": detail["bytes"], "bytes_base64": detail["bytes_base64"]})
    return outputs, logs, result_available


def read_chromatin_output(plan: dict, *, path: str, offset: int, limit: int) -> dict:
    """Read one bounded window from an exact original output or control log."""
    plan = validate_chromatin_run_plan(plan)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1024 * 1024:
        raise ValueError("bounded_native_output_window_required")
    target = _path(path, absolute=True)
    attempt = _path(plan["attempt_directory"], absolute=True)
    root = _path(str(Path(plan["identity"]["execution_id"]).parent), absolute=True)
    allowed = {str(attempt / row["relative_path"]): (attempt, row["relative_path"])
        for row in plan["outputs"]}
    allowed.update({str(root / (role + ".log")): (root, role + ".log") for role in ("stdout", "stderr")})
    if str(target) not in allowed:
        raise ValueError("native_chromatin_interactions_original_output_path_required")
    directory, relative = allowed[str(target)]
    with _producer_file(directory, _path(relative, absolute=False)) as pinned:
        with pinned.open("rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            stream.seek(offset)
            raw = stream.read(min(limit, max(0, size - offset)))
    return {"path": str(target), "offset": offset, "returned_bytes": len(raw), "size_bytes": size,
        "bytes_base64": base64.b64encode(raw).decode("ascii"), "text_utf8": raw.decode("utf-8", errors="replace")}
