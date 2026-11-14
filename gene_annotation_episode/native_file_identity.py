"""Pure byte-identity records and errors shared by native File capture.

This reusable infrastructure validates supplied identity fields only. It does
not open files, import Store/material services, assign scientific meaning, or
grant source access. native_file_capture re-exports the same actual objects.
"""
from __future__ import annotations
import re
from typing import Literal, TypedDict
import unicodedata


class NativeFileIdentity(TypedDict):
    artifact_ref: str
    sha256: str
    size_bytes: int
    format: str


ErrorCode = Literal[
    "invalid_capture_path", "invalid_file_declaration", "invalid_file_identity",
    "capture_file_unavailable", "retained_artifact_unavailable", "retained_artifact_mismatch",
]

class NativeFileCaptureError(ValueError):
    code: ErrorCode

    def __init__(self, code: ErrorCode):
        self.code = code
        super().__init__(code)


_IDENTITY_FIELDS = frozenset(NativeFileIdentity.__annotations__)

_DIGEST = re.compile(r"[0-9a-f]{64}")

def _require(condition: bool, code: ErrorCode) -> None:
    if not condition:
        raise NativeFileCaptureError(code)


def _label(value) -> bool:
    return type(value) is str and bool(value) and not any(
        unicodedata.category(char) == "Cc" for char in value)


def _digest(value) -> bool:
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _size(value) -> bool:
    return type(value) is int and value >= 0


def _identity(value) -> NativeFileIdentity:
    _require(type(value) is dict and set(value) == _IDENTITY_FIELDS, "invalid_file_identity")
    _require(_digest(value["sha256"]) and _size(value["size_bytes"])
        and _label(value["format"]) and type(value["artifact_ref"]) is str
        and value["artifact_ref"] == "artifact_" + value["sha256"], "invalid_file_identity")
    return dict(value)

