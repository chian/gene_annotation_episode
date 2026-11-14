"""Caller-owned limits and blocking adapters for the durable native lifecycle.

Blocking and detached jobs share native_lifecycle and one protected worker.
The worker/cgroup owns resource enforcement independently of episode lifetimes.
Scratch is monitored with possible overshoot, plus a hard per-file size limit.
This is not a filesystem sandbox or a scientific continuation rule.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import math
from pathlib import Path
import threading
import tomllib
from typing import Mapping

from .acquisition import AcquisitionError
from ._local_job_worker import allocated_bytes


@dataclass(frozen=True)
class LocalJobPolicy:
    memory_bytes: int
    scratch_bytes: int
    wall_seconds: float | None = None

    def __post_init__(self) -> None:
        for name in ("memory_bytes", "scratch_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"invalid_local_job_{name}")
        if self.wall_seconds is not None and (type(self.wall_seconds) not in (int, float) or
                not math.isfinite(self.wall_seconds) or self.wall_seconds <= 0):
            raise ValueError("invalid_local_job_wall_seconds")

    @classmethod
    def from_config(cls, settings: Mapping | None = None) -> LocalJobPolicy:
        defaults = tomllib.loads(Path(__file__).with_name("defaults.toml").read_text())["local_jobs"]
        if settings is not None and not isinstance(settings, Mapping):
            raise ValueError("invalid_local_job_settings")
        supplied = dict(settings or {})
        unknown = supplied.keys() - {"memory_bytes", "scratch_bytes", "wall_seconds"}
        if unknown:
            raise ValueError("unknown_local_job_setting:" + ",".join(sorted(unknown)))
        return cls(**{**defaults, **supplied})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LocalJobResult:
    returncode: int
    stdout_path: Path
    stderr_path: Path
    metadata: dict


def check_scratch_budget(cwd: Path, policy: LocalJobPolicy, *, additional_bytes: int = 0) -> None:
    """Check staged files before a known host-side copy; not a reservation.

    The native process monitor remains authoritative during execution. Other
    concurrent writers and allocation rounding can change usage after this
    check; callers must use a directory owned by this one job.
    """
    if type(additional_bytes) is not int or additional_bytes < 0:
        raise ValueError("invalid_local_job_additional_bytes")
    observed = allocated_bytes(Path(cwd))
    if observed + additional_bytes > policy.scratch_bytes:
        raise AcquisitionError("local_job_resource_limit", phase="local_preflight",
            operational={"policy": policy.to_dict(), "resource": "scratch_bytes",
                "limit": policy.scratch_bytes, "enforcement": {
                    "scratch": "monitored_visible_allocated_bytes_with_possible_overshoot"},
                "evidence": {"observed_allocated_bytes": observed,
                    "additional_bytes": additional_bytes, "stage": "staged_inputs"}})


def run_local_job(command: list[str], *, cwd: Path, policy: LocalJobPolicy,
                  stdout_path: Path | None = None, stderr_path: Path | None = None,
                  stdin_path: Path | None = None, env: Mapping[str, str] | None = None,
                  cancel_event: threading.Event | None = None, statistics=None) -> LocalJobResult:
    """Wait through the same durable lifecycle used by detached execution."""
    from .native_lifecycle import run_blocking
    return run_blocking(command, cwd=cwd, policy=policy, stdout_path=stdout_path,
        stderr_path=stderr_path, stdin_path=stdin_path, env=env, cancel_event=cancel_event,
        statistics=statistics)


async def run_cancellable_native(function, *args, **kwargs):
    """Await a synchronous native adapter without abandoning its process tree.

    The supplied adapter must consume cancel_event and reap its native jobs
    before returning. This helper does not make an arbitrary function stoppable.
    """
    if "cancel_event" in kwargs:
        raise ValueError("async_local_job_owns_cancel_event")
    cancellation = threading.Event()
    task = asyncio.create_task(asyncio.to_thread(function, *args,
                              cancel_event=cancellation, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancellation.set()
        # A repeated cancellation must not let the caller delete live scratch.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if task.done() and not task.cancelled():
            task.exception()
        raise


async def run_local_job_async(command: list[str], **kwargs) -> LocalJobResult:
    """Cancellation waits until the native process tree has been stopped."""
    return await run_cancellable_native(run_local_job, command, **kwargs)
