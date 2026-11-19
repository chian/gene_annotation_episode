"""A110 plain JSON values: mappings and sequences copied into plain dicts and lists."""
from __future__ import annotations

from collections.abc import Mapping


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value
