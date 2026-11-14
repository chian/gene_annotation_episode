"""Private A106 canonical finding identity primitives."""
import hashlib
import json
from typing import Any

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identity(kind: str, value: Any) -> str:
    return kind + "_" + hashlib.sha256(canonical(value).encode()).hexdigest()[:24]


