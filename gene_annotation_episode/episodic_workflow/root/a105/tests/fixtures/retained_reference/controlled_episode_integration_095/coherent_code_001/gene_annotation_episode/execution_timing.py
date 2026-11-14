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
