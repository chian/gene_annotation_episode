"""Original ordinary tool values and exact native work carrier."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

def number(value: float, unit_ref: str | None = None) -> dict:
    return {"type": "number", "value": value, "unit_ref": unit_ref}


def enum(value: str) -> dict:
    return {"type": "enum", "value": value}


def ref(value: str) -> dict:
    return {"type": "reference", "ref": value}


def measurements(**values: dict) -> list[dict]:
    return [{"name": key, "value": value} for key, value in values.items()]


INTEGER = {"type": "integer", "minimum": 0}
POSITIVE = {"type": "integer", "minimum": 1}
TEXT = {"type": "string", "minLength": 1}


@dataclass(frozen=True)
class SequenceWork:
    output_path: Path
    metadata: dict


