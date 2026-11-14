"""Actual machine observations and owned transport exit; no work budgets."""
import asyncio
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
from .provider_errors import ModelCallError

def _resource_snapshot(budget):
    """Retain observed aggregate task pressure without an admission guess."""
    root = Path('/sys/fs/cgroup') / budget['slice_cgroup'].lstrip('/')
    values = {'observed_at': datetime.now(timezone.utc).isoformat(),
              'slice_cgroup': budget['slice_cgroup']}
    for name in ('pids.current', 'pids.max', 'pids.events',
                 'memory.current', 'memory.events'):
        try:
            raw = (root / name).read_text().strip()
            values[name] = (raw if raw == 'max' else int(raw) if raw.isdecimal() else
                           {key: int(value) for key, value in
                            (line.split() for line in raw.splitlines())})
        except (OSError, ValueError) as error:
            values[name] = {'unavailable': type(error).__name__}
    return values


def _model_process_command(command, environment_bounds):
    """Make the admitted CPU allowance visible to native thread-pool sizing.

    A cgroup CPU quota limits consumed CPU time but leaves all host CPUs in
    sched_getaffinity. Make the actual CPU allowance visible to native libraries
    without configuring or enforcing a task/thread count ceiling.
    """
    allowed = sorted(os.sched_getaffinity(0))
    count = max(1, environment_bounds["cpu_percent"] // 100)
    # Spread separate coordinators over their permitted CPUs; never select
    # a CPU outside an inherited affinity constraint.
    start = os.getpid() % len(allowed)
    selected = (allowed[start:] + allowed[:start])[:count]
    taskset = shutil.which("taskset")
    if taskset is None:
        raise ModelCallError("model_cpu_affinity_tool_unavailable")
    return [taskset, "--cpu-list", ",".join(map(str, selected)), *command], selected


def _seed_codex_index(directory):
    """Take a consistent read-only index snapshot; never rescan all rollouts."""
    original = Path(os.environ.get('CODEX_SQLITE_HOME') or
        os.environ.get('CODEX_HOME') or Path.home()/'.codex').expanduser().resolve()
    copied = []
    for source in sorted(original.glob('state_*.sqlite')):
        destination = directory/source.name
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as reader:
            with closing(sqlite3.connect(destination)) as writer:
                reader.backup(writer)
        copied.append({'source':str(source),'snapshot':str(destination),
            'bytes':destination.stat().st_size})
    return copied


def owned_process_group_running(group):
    """Observe this owned group only; escaped descendants remain cgroup-owned."""
    for directory in Path('/proc').iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            fields = (directory / 'stat').read_bytes().rsplit(b')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        if fields[0] not in {b'Z', b'X', b'x'} and int(fields[2]) == group:
            return True
    return False


async def wait_owned_process_group_exit(group):
    while owned_process_group_running(group):
        # Observation cadence only: there is no elapsed/count stopping condition.
        await asyncio.sleep(0.05)

