"""Standalone native plan identity from exact original command-custody rules.

Private serialization here belongs only to this identity check. No scientific
profile, receipt receiver, iterator, or native driver is imported.
"""
from collections.abc import Mapping
import hashlib
import json
from pathlib import PurePosixPath


def _plain(value):
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


def _canonical(value):
    return json.dumps(_plain(value), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)



def _digest(value):
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()



def terminal_plan_identity(owner, *, attempt_directory):
    """Validate current command identity without pretending it is a job handle."""
    if not isinstance(owner, Mapping) or not isinstance(owner.get('execution_id'), str):
        return False
    execution = PurePosixPath(owner['execution_id'])
    root = execution.parent
    return (execution.is_absolute() and execution.name == 'intent.json'
        and '..' not in execution.parts and root.name == _digest(owner.get('operation_key'))
        and root.parent.name == 'commands'
        and root.parent.parent.name == _digest({
            'run_id': owner.get('run_id'), 'episode_id': owner.get('episode_id')})
        and root.parent.parent.parent.name == '.episode-execution'
        and PurePosixPath(attempt_directory).is_relative_to(root)
        and PurePosixPath(attempt_directory) != root)



