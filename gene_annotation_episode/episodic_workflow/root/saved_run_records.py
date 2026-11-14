"""Authenticate saved run.json against the original Store journal."""
from __future__ import annotations
import json
from pathlib import Path
from .method_loop.durable import DurableExecutionError

def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError as error:
        raise _failure('unavailable_binding', str(path)) from error
    except (ValueError, TypeError) as error:
        raise _failure('identity_conflict', str(path)) from error


def _failure(code, *references):
    return DurableExecutionError(code, affected_refs=references)


def _settings(store, directory):
    manifest = _read_json(directory/'run.json')
    row = store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
                           (manifest['run_id'],)).fetchone()
    if row is None:
        raise _failure('unavailable_binding', str(directory/'run.json'))
    settings = json.loads(row[0])
    if (manifest != {'run_id': manifest['run_id'], **settings}
            or settings['directory'] != str(directory)
            or settings['problem'] != store.problem()):
        raise _failure('identity_conflict', str(directory/'run.json'))
    return manifest['run_id'], settings


