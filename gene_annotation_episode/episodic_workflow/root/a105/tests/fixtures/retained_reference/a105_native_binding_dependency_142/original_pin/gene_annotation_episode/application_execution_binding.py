"""Publish the caller's selected application reconstruction before execution.

The Store records the original factory choice and immutable C1 descriptor.
Files are atomic projections of that state. No episode, transport or policy is
created here, including recovery of a publication interrupted between writes.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from method_loop.durable import DurableExecutionError, canonical, content_digest

from . import independent_execution as reconstruction


VERSION = 'durable_episode_application_v1'
BINDING_FILE = 'episode-execution-binding.json'
_MARKER = {'version': VERSION, 'binding_file': BINDING_FILE}


@dataclass(frozen=True)
class ExecutionBindingResult:
    settings: dict
    runtime_binding: dict | None


def _failure(code, *references):
    return DurableExecutionError(code, affected_refs=references)


def _object(value):
    result = json.loads(canonical(value))
    if not isinstance(result, dict):
        raise ValueError('execution binding operands must be JSON objects')
    return result


def _same(left, right):
    # JSON booleans, integers and floating values retain their declared types.
    return canonical(left) == canonical(right)


def _runtime_binding(value):
    """The exact C1 runtime_binding shape, without importing its executable."""
    value = _object(value)
    if set(value) != {'factory_module', 'factory_name', 'arguments',
                      'implementation_sha256', 'settings_sha256'}:
        raise ValueError('runtime binding fields must be exact')
    for field in ('factory_module', 'factory_name'):
        name = value[field]
        if (not isinstance(name, str) or not name
                or any(not part.isidentifier() for part in name.split('.'))):
            raise ValueError('factory references must be module/attribute names')
    if not isinstance(value['arguments'], dict):
        raise ValueError('binding arguments must be a JSON object')
    for field in ('implementation_sha256', 'settings_sha256'):
        digest = value[field]
        if (not isinstance(digest, str) or len(digest) != 64
                or any(character not in '0123456789abcdef' for character in digest)):
            raise ValueError('runtime binding digests must be sha256 values')
    return value


def _read(path):
    try:
        return _object(json.loads(path.read_text(encoding='utf-8')))
    except (ValueError, TypeError) as error:
        raise _failure('identity_conflict', str(path)) from error


def _publish(path, value, *, immutable=False):
    """Durable atomic JSON publication; immutable destinations never replace."""
    if immutable and path.exists():
        if not _same(_read(path), value):
            raise _failure('identity_conflict', str(path))
        return
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix='.'+path.name+'-')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(canonical(value)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        if immutable:
            try:
                os.link(temporary, path)
            except FileExistsError:
                if not _same(_read(path), value):
                    raise _failure('identity_conflict', str(path))
        else:
            os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _run(store, directory):
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                              "AND name='runtime_runs'").fetchone()
    rows = ([] if exists is None else store.db.execute(
        "SELECT run_id,settings FROM runtime_runs WHERE json_extract(settings,'$.directory')=?",
        (str(directory),)).fetchall())
    if not rows:
        raise _failure('unavailable_binding', str(directory))
    if len(rows) != 1:
        raise _failure('identity_conflict', str(directory))
    row = rows[0]
    settings = _object(json.loads(row['settings']))
    if not _same(settings.get('problem'), store.problem()):
        raise _failure('identity_conflict', str(directory))
    return row['run_id'], settings


def _known_selection(directory, settings, configuration):
    if configuration is None:
        raise _failure('unavailable_binding', 'tool_configuration')
    pins = {}
    if (directory/'case-launch.json').exists():
        kind = 'fixed_case'
        for name in ('case-launch.json', 'policy-binding.json'):
            path = directory/name
            if not path.is_file():
                raise _failure('unavailable_binding', str(path))
            pins[name] = content_digest(_read(path))
        if not _same(_read(directory/'case-launch.json').get('configuration'), configuration):
            raise _failure('identity_conflict', 'tool_configuration')
    else:
        from .default_scientific_binding import VERSION as DEFAULT_VERSION
        definition = settings.get('binding_definitions', {}).get('credit', {})
        if definition.get('default_entrypoint') != DEFAULT_VERSION:
            raise _failure('unavailable_binding', 'default_entrypoint')
        kind = 'standard_default'
    return {'mode': 'known', 'kind': kind, 'tool_configuration': configuration,
        'implementation_sha256': reconstruction.implementation_sha256(),
        'caller_binding_pins': pins}


def _check_known_selection(directory, selection):
    if selection['implementation_sha256'] != reconstruction.implementation_sha256():
        raise _failure('identity_conflict', 'implementation_sha256')
    for name, expected in selection['caller_binding_pins'].items():
        path = directory/name
        if not path.is_file() or content_digest(_read(path)) != expected:
            raise _failure('identity_conflict', str(path))


def _make_binding(store, directory, selection):
    if selection['mode'] == 'requested':
        return _runtime_binding(selection['runtime_binding'])
    _check_known_selection(directory, selection)
    binding = _runtime_binding(reconstruction.make_runtime_binding(store, directory,
        kind=selection['kind'], tool_configuration=selection['tool_configuration']))
    if (binding['factory_module'] != reconstruction.FACTORY_MODULE
            or binding['factory_name'] != reconstruction.FACTORY_NAME
            or binding['implementation_sha256'] != selection['implementation_sha256']
            or binding['arguments'].get('kind') != selection['kind']
            or not _same(binding['arguments'].get('tool_configuration'), selection['tool_configuration'])
            or binding['arguments'].get('caller_binding_pins') != selection['caller_binding_pins']):
        raise _failure('identity_conflict', str(directory/BINDING_FILE))
    return binding


def bind_episode_execution(store, run_directory, *, settings, requested_binding=None,
                           use_saved_runtime=False, tool_configuration=None,
                           resume=False) -> ExecutionBindingResult:
    """Bind explicit C1 or saved known reconstruction, without starting work.

    Call after the run's scientific/specialist descriptors are frozen in Store.
    A legacy resume retains its semantics. Once marked, recovery uses the saved
    factory intent, even if descriptor publication never completed.
    """
    directory = Path(run_directory).expanduser().resolve()
    supplied = _object(settings)
    requested = None if requested_binding is None else _runtime_binding(requested_binding)
    configuration = None if tool_configuration is None else _object(tool_configuration)
    try:
        with store.transaction():
            run_id, saved = _run(store, directory)
            if not _same(supplied, saved):
                raise _failure('identity_conflict', 'settings')
            marked = saved.get('episode_execution')
            if marked is None:
                if requested is None and not use_saved_runtime:
                    return ExecutionBindingResult(saved, None)
                if resume:
                    raise _failure('identity_conflict', 'episode_execution')
                if (directory/BINDING_FILE).exists():
                    raise _failure('identity_conflict', str(directory/BINDING_FILE))
            elif marked != _MARKER:
                raise _failure('identity_conflict', 'episode_execution')
            store.db.execute('''CREATE TABLE IF NOT EXISTS runtime_execution_bindings (
                run_id TEXT PRIMARY KEY, selection TEXT NOT NULL,
                settings_sha256 TEXT NOT NULL, runtime_binding TEXT)''')
            row = store.db.execute('SELECT * FROM runtime_execution_bindings WHERE run_id=?',
                                   (run_id,)).fetchone()
            if marked is None:
                if row is not None:
                    raise _failure('identity_conflict', 'episode_execution')
                if (configuration is not None and 'tool_configuration' in saved
                        and not _same(configuration, saved['tool_configuration'])):
                    raise _failure('identity_conflict', 'tool_configuration')
                if configuration is None:
                    configuration = saved.get('tool_configuration')
                selection = ({'mode': 'requested', 'runtime_binding': requested} if requested is not None
                             else _known_selection(directory, saved, configuration))
                saved['episode_execution'] = dict(_MARKER)
                if configuration is not None:
                    saved['tool_configuration'] = configuration
                settings_digest = content_digest(saved)
                store.db.execute('INSERT INTO runtime_execution_bindings VALUES(?,?,?,NULL)',
                                 (run_id, canonical(selection), settings_digest))
                store.db.execute('UPDATE runtime_runs SET settings=? WHERE run_id=?',
                                 (canonical(saved), run_id))
                binding = None
            else:
                if row is None:
                    raise _failure('unavailable_binding', str(directory/BINDING_FILE))
                selection = _object(json.loads(row['selection']))
                settings_digest = row['settings_sha256']
                if settings_digest != content_digest(saved):
                    raise _failure('identity_conflict', 'settings')
                if configuration is not None and not _same(configuration, saved.get('tool_configuration')):
                    raise _failure('identity_conflict', 'tool_configuration')
                binding = (None if row['runtime_binding'] is None else
                           _runtime_binding(json.loads(row['runtime_binding'])))
                if (binding is not None and selection['mode'] == 'requested'
                        and not _same(binding, selection['runtime_binding'])):
                    raise _failure('identity_conflict', str(directory/BINDING_FILE))
                if (binding is not None and selection['mode'] == 'known'
                        and binding['settings_sha256'] != settings_digest):
                    raise _failure('identity_conflict', 'settings')
                if requested is not None and not _same(requested, binding if binding is not None else
                        selection.get('runtime_binding')):
                    raise _failure('identity_conflict', str(directory/BINDING_FILE))
        if selection['mode'] == 'known':
            _check_known_selection(directory, selection)
        # D's factory verifies this exact manifest against authoritative Store
        # settings. Repair this projection before calling it, including a crash
        # immediately after the transaction above committed.
        _publish(directory/'run.json', {'run_id': run_id, **saved})
        if binding is None:
            binding = _make_binding(store, directory, selection)
            if selection['mode'] == 'known' and binding['settings_sha256'] != settings_digest:
                raise _failure('identity_conflict', 'settings')
            if (directory/BINDING_FILE).exists() and not _same(_read(directory/BINDING_FILE), binding):
                raise _failure('identity_conflict', str(directory/BINDING_FILE))
            with store.transaction():
                _, current = _run(store, directory)
                if content_digest(current) != settings_digest:
                    raise _failure('identity_conflict', 'settings')
                row = store.db.execute('SELECT runtime_binding FROM runtime_execution_bindings WHERE run_id=?',
                                       (run_id,)).fetchone()
                if row[0] is not None and not _same(_runtime_binding(json.loads(row[0])), binding):
                    raise _failure('identity_conflict', str(directory/BINDING_FILE))
                store.db.execute('UPDATE runtime_execution_bindings SET runtime_binding=? WHERE run_id=?',
                                 (canonical(binding), run_id))
        _publish(directory/BINDING_FILE, binding, immutable=True)
        return ExecutionBindingResult(saved, binding)
    except (OSError, sqlite3.Error) as error:
        raise _failure('storage_failure', str(directory)) from error


__all__ = ['bind_episode_execution', 'ExecutionBindingResult', 'VERSION', 'BINDING_FILE']
