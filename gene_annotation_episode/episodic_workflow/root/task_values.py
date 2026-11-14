"""Private root annotation task values."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.method_loop import ClosedRecord
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json

def _plain(value):
    if hasattr(value, 'as_record'):
        return _plain(value.as_record())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value

def _json(value):
    return json.dumps(_plain(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()

@dataclass(frozen=True)
class Record(ClosedRecord):
    value: dict

    def as_record(self):
        return self.value
