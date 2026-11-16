"""Caller-supplied memory/scratch policy and staged-file scratch preflight.

The module stays beside defaults.toml and applies the inherited workflow
memory ceiling. Process creation and lifetime remain in native_lifecycle.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import os
from pathlib import Path
import tomllib
from typing import Mapping
from .acquisition_types import AcquisitionError
from .local_scratch import allocated_bytes


@dataclass(frozen=True)
class LocalJobPolicy:
    memory_bytes: int
    scratch_bytes: int

    def __post_init__(self) -> None:
        for name in ("memory_bytes", "scratch_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"invalid_local_job_{name}")

    @classmethod
    def from_config(cls, settings: Mapping | None = None) -> LocalJobPolicy:
        defaults = tomllib.loads(Path(__file__).with_name("defaults.toml").read_text())["local_jobs"]
        if settings is not None and not isinstance(settings, Mapping):
            raise ValueError("invalid_local_job_settings")
        supplied = dict(settings or {})
        unknown = supplied.keys() - {"memory_bytes", "scratch_bytes"}
        if unknown:
            raise ValueError("unknown_local_job_setting:" + ",".join(sorted(unknown)))
        configured = {**defaults, **supplied}
        if "memory_bytes" not in supplied:
            from .workflow_budget import ENV, active_budget
            if os.environ.get(ENV):
                # An inherited default is a ceiling, not a declaration that
                # every native helper needs the desktop's full allocation.
                # Explicit caller requests retain their original semantics.
                memory = active_budget()["environment_bounds"]["memory_bytes"]
                configured["memory_bytes"] = min(configured["memory_bytes"], memory)
        return cls(**configured)

    def to_dict(self) -> dict:
        return asdict(self)


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

