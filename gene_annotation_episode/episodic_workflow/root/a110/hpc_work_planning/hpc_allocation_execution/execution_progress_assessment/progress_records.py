"""Read identity and timestamps without acquiring new progress."""
from __future__ import annotations
from datetime import datetime
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError

def _timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise ContractError('progress_utc_timestamp_required') from error
    return result

def _unique(values):
    return list(dict.fromkeys(values))
