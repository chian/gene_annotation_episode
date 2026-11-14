"""Selected factual FBA file/log windows; no scientific interpretation."""
import base64
import os
from pathlib import Path

from .native_flux_balance_contracts import require, validate_flux_balance_run_plan
from .native_flux_balance_storage import confined_file, regular


def _detail(base, relative, *, limit=None):
    try:
        with regular(confined_file(base, relative)) as stream:
            size = os.fstat(stream.fileno()).st_size
            result = {"available": True, "bytes": size}
            if limit is not None:
                offset = max(0, size - limit)
                stream.seek(offset)
                raw = stream.read(min(limit, max(0, size - offset)))
                result.update(offset=offset, bytes_base64=base64.b64encode(raw).decode("ascii"))
            return result
    except FileNotFoundError:
        return {"available": False, "bytes": None}


def flux_balance_observed_files(plan, view, *, log_window_bytes, log_roles):
    """Observe declared files; availability and closure do not imply success."""
    require(type(log_window_bytes) is int and log_window_bytes > 0, "positive_log_window_required")
    require(type(log_roles) in (tuple, list)
        and all(type(role) is str and role in ("stdout", "stderr", "native_log") for role in log_roles)
        and len(set(log_roles)) == len(log_roles), "unsupported_native_log_role")
    require(type(view) is dict and type(view.get("terminal")) is bool
        and type(view.get("quiescent")) is bool, "native_writer_observation_required")
    plan = validate_flux_balance_run_plan(plan)
    attempt, root = Path(plan["attempt_directory"]), Path(plan["identity"]["execution_id"]).parent
    closed = view["terminal"] and view["quiescent"]
    outputs, details, available = [], {}, False
    for row in plan["outputs"]:
        path = str(attempt / row["relative_path"])
        detail = _detail(attempt, row["relative_path"],
            limit=log_window_bytes if row["role"] == "native_log" and "native_log" in log_roles else None)
        outputs.append({"role": "requested_output:" + path,
            "available": detail["available"], "bytes": detail["bytes"],
            "writer_closed": detail["available"] and closed})
        available = available or detail["available"]
        if row["role"] == "native_log":
            details["native_log"] = (path, detail)
    for role in ("stdout", "stderr"):
        path = str(root / (role + ".log"))
        detail = _detail(root, role + ".log", limit=log_window_bytes if role in log_roles else None)
        outputs.append({"role": role, "available": detail["available"], "bytes": detail["bytes"],
            "writer_closed": detail["available"] and closed})
        details[role] = (path, detail)
    logs = []
    for role in log_roles:
        path, detail = details[role]
        if detail["available"]:
            logs.append({"role": role, "path": path, "offset": detail["offset"],
                "observed_size": detail["bytes"], "bytes_base64": detail["bytes_base64"]})
    return outputs, logs, available


def read_flux_balance_output(plan, *, path, offset, limit):
    """Read only a selected bounded window of an original declared output."""
    require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 1048576,
        "bounded_native_output_window_required")
    plan = validate_flux_balance_run_plan(plan)
    attempt, root = Path(plan["attempt_directory"]), Path(plan["identity"]["execution_id"]).parent
    allowed = {str(attempt / row["relative_path"]): (attempt, row["relative_path"]) for row in plan["outputs"]}
    allowed.update({str(root / (role + ".log")): (root, role + ".log") for role in ("stdout", "stderr")})
    require(type(path) is str and path in allowed, "fba_original_output_path_required")
    base, relative = allowed[path]
    with regular(confined_file(base, relative)) as stream:
        size = os.fstat(stream.fileno()).st_size
        stream.seek(offset)
        raw = stream.read(min(limit, max(0, size - offset)))
    return {"path": path, "offset": offset, "returned_bytes": len(raw), "size_bytes": size,
        "bytes_base64": base64.b64encode(raw).decode("ascii"),
        "text_utf8": raw.decode("utf-8", errors="replace")}


__all__ = ["flux_balance_observed_files", "read_flux_balance_output"]
