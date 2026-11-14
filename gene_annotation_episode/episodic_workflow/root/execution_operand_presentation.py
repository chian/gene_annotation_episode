"""Present exact operational operands to HPC episodes and their Launch children."""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json


def _file_view(item):
    """Describe frozen input bytes; Launch reads the original host-owned file."""
    if not isinstance(item, Mapping) or not isinstance(item.get('text'), str):
        return item
    raw = item['text'].encode('utf-8')
    return {**{key: value for key, value in item.items() if key != 'text'},
        'text_size_bytes': len(raw), 'text_sha256': hashlib.sha256(raw).hexdigest(),
        'text_access': 'The exact frozen text is supplied to Launch in '
            'hpc_execution_job.supplied_input_file for this plan.'}


def _candidate_view(candidate):
    if not isinstance(candidate, Mapping) or 'files' not in candidate:
        return candidate
    return {**candidate, 'files': [_file_view(item) for item in candidate['files']]}


def plan_outcome_view(outcome):
    """Present typed plans/candidates consistently through outcome/history wrappers.

    This also projects retained pre-fix plan outcomes without changing their
    stored receipts. Launch receives the original executable bytes through its
    existing immutable input file; model identity and forecasts remain exact.
    """
    def project(value):
        if isinstance(value, Mapping):
            if {'plan_id', 'original_prediction', 'practical_assignment'} <= value.keys():
                value = {key: child for key, child in value.items() if key != 'prediction_episode_id'}
                if 'supplied_files' in value:
                    value['supplied_files'] = [_file_view(item) for item in value['supplied_files']]
                return value
            elif {'id', 'queue', 'nodes', 'wall_seconds', 'units', 'files', 'preparation'} <= value.keys():
                return _candidate_view(value)
            return {key: project(child) for key, child in value.items()}
        if isinstance(value, list):
            return [project(child) for child in value]
        if isinstance(value, tuple):
            return tuple(project(child) for child in value)
        return value
    return project(outcome)


def is_hpc_context(state):
    return isinstance(state, Mapping) and (
        'hpc_commission' in state or 'hpc_execution_job' in state)

