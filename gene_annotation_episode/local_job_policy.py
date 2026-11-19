"""Caller-supplied memory/scratch policy and staged-file scratch preflight.

Process creation and lifetime remain in native_lifecycle.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
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
    def from_config(cls, settings: Mapping) -> LocalJobPolicy:
        """The caller's declared ``memory_bytes`` and ``scratch_bytes``; anything else raises."""
        if not isinstance(settings, Mapping):
            raise ValueError("invalid_local_job_settings")
        supplied = dict(settings)
        unknown = supplied.keys() - {"memory_bytes", "scratch_bytes"}
        if unknown:
            raise ValueError("unknown_local_job_setting:" + ",".join(sorted(unknown)))
        missing = {"memory_bytes", "scratch_bytes"} - supplied.keys()
        if missing:
            raise ValueError("local_job_setting_required:" + ",".join(sorted(missing)))
        return cls(**supplied)

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

