"""Original decision record fields for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
from gene_annotation_episode.execution_contracts import digest


_RECORD_TRACKING = frozenset({"origin", "record_type", "operation_key", "run_id",
    "episode_id", "problem_ref", "sha256", "digest", "created_at", "updated_at",
    "parse_key", "parser_version", "metadata_preview_characters", "auxiliary_artifact_refs"})


def _record(record):
    if not isinstance(record, Mapping):
        return record
    return {key: value for key, value in record.items() if key not in _RECORD_TRACKING}


