"""Caller-owned limits and blocking adapters for the durable native lifecycle.

Blocking and detached jobs share native_lifecycle and one protected worker.
The worker/cgroup owns resource enforcement independently of episode lifetimes.
Scratch is monitored with possible overshoot, plus a hard per-file size limit.
This is not a filesystem sandbox or a scientific continuation rule.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import os
from pathlib import Path
import threading
import tomllib
from typing import Mapping

from .acquisition import AcquisitionError
from ._local_job_worker import allocated_bytes


from .local_job_policy import LocalJobPolicy, check_scratch_budget

@dataclass(frozen=True)
class LocalJobResult:
    returncode: int
    stdout_path: Path
    stderr_path: Path
    metadata: dict




def run_local_job(command: list[str], *, cwd: Path, policy: LocalJobPolicy,
                  stdout_path: Path | None = None, stderr_path: Path | None = None,
                  stdin_path: Path | None = None, env: Mapping[str, str] | None = None,
                  cancel_event: threading.Event | None = None,
                  cpu_threads: int = 1) -> LocalJobResult:
    """Wait through the same durable lifecycle used by detached execution."""
    from .native_lifecycle import run_blocking
    return run_blocking(command, cwd=cwd, policy=policy, stdout_path=stdout_path,
        stderr_path=stderr_path, stdin_path=stdin_path, env=env, cancel_event=cancel_event,
        cpu_threads=cpu_threads)


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
