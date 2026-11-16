"""Pure public source-snapshot and acquisition-error value types.

The acquisition clients re-export these exact objects. Defining provenance is
this reusable infrastructure module; no service, transport or retry policy is
implemented here.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from typing import Any


@dataclass(frozen=True)
class SourceSnapshot:
    service: str
    url: str
    request: dict[str, Any]
    retrieved_at: str
    content: bytes
    media_type: str
    transport: dict[str, Any]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


class AcquisitionError(RuntimeError):
    def __init__(self, code: str, *, retry_after: float | None = None, job_ref: str | None = None,
                 snapshot: SourceSnapshot | None = None, phase: str | None = None,
                 submission_outcome: str | None = None, diagnostic: dict | None = None,
                 operational: dict | None = None):
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after
        self.job_ref = job_ref
        self.snapshot = snapshot
        self.phase = phase
        self.submission_outcome = submission_outcome
        self.diagnostic = diagnostic
        self.operational = operational

