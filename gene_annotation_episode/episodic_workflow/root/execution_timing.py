"""Measured execution intervals; no credit, yield or scheduling decisions.

UTC timestamps locate events. Durations use the monotonic clock and exclude
offline gaps between executions. An abruptly lost interval stays unknown.
Parent child-invocation time includes the child's work, so durations across
episode levels must not be summed as compute consumption.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

VERSION = "measured_episode_execution_intervals_v1"
PROGRESS_TIME_VERSION = "episode_progress_time_v1"


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _process_identity(pid=None):
    pid = os.getpid() if pid is None else pid
    try:
        # comm can contain whitespace and ')'; fields after its final ')' start
        # at process-stat field 3. Start time is field 22.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] == "Z":
            return None
        return {"pid": pid, "start_ticks": fields[19],
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
    except (OSError, IndexError):
        return None


def owner_is_live(owner):
    """Resolve the recorded process incarnation, never just its PID."""
    return bool(owner is not None and _process_identity(owner["pid"]) == owner)


def capture_progress_time(journal, episode_id, *, original_decision_index=None):
    """Freeze a real clock point, without creating a progress observation.

    The first received progress point fixes the measured reference span used
    by the numerical binding. A decision query may read that span, but cannot
    establish it. Runtime persists receipt points in estimation contexts and
    decision points in the original model request. Replay reads those records.

    This is elapsed real time, including idle/wait time on the same boot, not a
    sum of overlapping dispatch durations or an estimate of compute usage.
    Cross-boot subtraction and historical reconstruction are unavailable.
    """
    owner = _process_identity()
    now = time.monotonic_ns()
    result = {"version": PROGRESS_TIME_VERSION, "run_id": journal.run_id,
        "episode_id": episode_id, "original_decision_index": original_decision_index,
        "point_kind": "decision_query" if original_decision_index is None else "progress_receipt",
        "captured_at": _utc(), "observed_monotonic_ns": now,
        "boot_id": None if owner is None else owner["boot_id"],
        "origin_decision_index": None, "origin_monotonic_ns": None,
        "reference_observation_monotonic_ns": None, "reference_elapsed_seconds": None,
        "elapsed_seconds": None, "status": "unavailable", "unavailable_reason": None,
        "clock": "monotonic", "time_unit": "seconds", "includes_idle_time": True,
        "is_compute_consumption": False}
    origin = journal.db.execute("SELECT call_index,timing FROM runtime_model_calls "
        "WHERE run_id=? AND episode_id=? AND purpose='decision' ORDER BY call_index LIMIT 1",
        (journal.run_id, episode_id)).fetchone()
    previous = journal.db.execute("SELECT data FROM runtime_estimation_contexts "
        "WHERE run_id=? AND episode_id=? ORDER BY rowid LIMIT 1",
        (journal.run_id, episode_id)).fetchone()
    raw = None if origin is None or origin["timing"] is None else json.loads(origin["timing"])
    spans = [] if raw is None else raw.get("intervals", [])
    first = spans[0] if spans else {}
    start, identity = first.get("started_monotonic_ns"), first.get("owner")
    if type(start) is not int or not isinstance(identity, dict):
        result["unavailable_reason"] = "episode_origin_clock_unavailable"
        return result
    result.update(origin_decision_index=origin["call_index"], origin_monotonic_ns=start)
    if owner is None or identity.get("boot_id") != owner["boot_id"] or now < start:
        result["unavailable_reason"] = "episode_clock_not_comparable"
        return result
    result["elapsed_seconds"] = (now - start) / 1e9
    if previous is not None:
        reference = json.loads(previous["data"]).get("progress_time")
        if (not isinstance(reference, dict) or reference.get("status") != "available"
                or reference.get("version") != PROGRESS_TIME_VERSION
                or reference.get("run_id") != journal.run_id or reference.get("episode_id") != episode_id
                or reference.get("origin_monotonic_ns") != start
                or reference.get("boot_id") != owner["boot_id"]):
            result["unavailable_reason"] = "recorded_progress_clock_unavailable"
            return result
        reference_ns = reference.get("reference_observation_monotonic_ns")
        if (type(reference_ns) is not int or not start < reference_ns <= now
                or reference.get("reference_elapsed_seconds") != (reference_ns-start)/1e9):
            result["unavailable_reason"] = "recorded_progress_reference_span_unavailable"
            return result
        result.update(reference_observation_monotonic_ns=reference["reference_observation_monotonic_ns"],
            reference_elapsed_seconds=reference["reference_elapsed_seconds"])
    elif original_decision_index is None:
        result["unavailable_reason"] = "progress_reference_span_unobserved"
        return result
    elif now == start:
        result["unavailable_reason"] = "progress_reference_span_has_zero_duration"
        return result
    else:
        result.update(reference_observation_monotonic_ns=now,
            reference_elapsed_seconds=result["elapsed_seconds"])
    result.update(status="available", unavailable_reason=None)
    return result


def snapshot(record):
    """Read measured totals and, when its owner is live, current elapsed time.

    A missing owner is not evidence of a zero-duration interval. No timer read
    writes state or constitutes a completed action/estimator observation.
    """
    if record is None:
        return None
    if isinstance(record, str):
        record = json.loads(record)
    spans = record["intervals"]
    running = spans[-1] if spans and spans[-1]["state"] == "running" else None
    live = bool(running and owner_is_live(running["owner"]))
    elapsed = ((time.monotonic_ns() - running["started_monotonic_ns"]) / 1e9
               if live else None)
    return {"version": VERSION,
        "measured_elapsed_seconds": record["measured_elapsed_seconds"],
        "live_interval_elapsed_seconds": elapsed,
        "interval_count": len(spans),
        "unmeasured_ended_intervals": record["unmeasured_ended_intervals"] + bool(running and not live),
        "state": ("running" if live else "end_unobserved" if running else
                  spans[-1]["state"] if spans else "unmeasured"),
        "time_unit": "seconds", "clock": "monotonic",
        "includes_child_wait": True, "is_compute_consumption": False}


@contextmanager
def measure(read, write):
    """Attach actual dispatch time to its existing authoritative journal row."""
    record = read()
    record = json.loads(record) if record else {"version": VERSION, "intervals": [],
        "measured_elapsed_seconds": 0.0, "unmeasured_ended_intervals": 0}
    if record["intervals"] and record["intervals"][-1]["state"] == "running":
        # A prior execution did not record its end. Never turn downtime into
        # measured work or invent an end timestamp/duration during recovery.
        record["intervals"][-1]["state"] = "end_unobserved"
        record["unmeasured_ended_intervals"] += 1
    span = {"state": "running", "owner": _process_identity(), "started_at": _utc(),
            "started_monotonic_ns": time.monotonic_ns(), "ended_at": None,
            "elapsed_seconds": None, "exception_type": None}
    record["intervals"].append(span)
    write(json.dumps(record, separators=(",", ":"), allow_nan=False))
    try:
        yield
    except BaseException as error:
        span["state"] = ("interrupted" if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError))
                         else "raised")
        span["exception_type"] = type(error).__name__
        raise
    else:
        # Returned work may be a failed tool result. This is timing, not a
        # scientific completion judgment or an instruction to award credit.
        span["state"] = "returned"
    finally:
        span["elapsed_seconds"] = (time.monotonic_ns() - span["started_monotonic_ns"]) / 1e9
        span["ended_at"] = _utc()
        record["measured_elapsed_seconds"] += span["elapsed_seconds"]
        write(json.dumps(record, separators=(",", ":"), allow_nan=False))
