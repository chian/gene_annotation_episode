"""Authenticate installed A110 reader sources.

An installed reader digest describes the actual finite source files below this
axis.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re


VERSION = 'a110_adapter_source_epochs_v1'
CURRENT_VERSION = 'a110_adapter_reader_sources_v1'
_ROOT = Path(__file__).resolve().parents[6]
_DIRECTORY = Path(__file__).resolve().parent
_MANIFEST = _DIRECTORY / 'adapter_source_identity.json'
_HEX = re.compile(r'[a-f0-9]{64}\Z')
_AXIS = ('gene_annotation_episode', 'episodic_workflow', 'root', 'a110')


def _require(condition, code='appservice_adapter_source_identity_invalid'):
    if not condition:
        raise ValueError(code)


def _digest(value):
    return type(value) is str and _HEX.fullmatch(value) is not None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _path(value):
    _require(type(value) is str and bool(value))
    path = PurePosixPath(value)
    _require(not path.is_absolute() and '..' not in path.parts and str(path) == value)
    _require(path.parts[:4] == _AXIS and path.suffix in {'.py', '.json'})
    return path


def _members(rows):
    _require(type(rows) is list and bool(rows))
    names = []
    for row in rows:
        _require(type(row) is dict and set(row) == {'path', 'sha256', 'size_bytes'})
        _path(row['path'])
        _require(_digest(row['sha256']) and type(row['size_bytes']) is int and row['size_bytes'] >= 0)
        names.append(row['path'])
    _require(names == sorted(set(names)))
    return rows


def _document():
    value = json.loads(_MANIFEST.read_bytes(), object_pairs_hook=_pairs)
    _require(type(value) is dict and set(value) == {'version', 'adapters', 'owners'})
    _require(value['version'] == VERSION and type(value['adapters']) is list
             and type(value['owners']) is dict and bool(value['owners']))
    seen = set()
    for row in value['adapters']:
        _require(type(row) is dict and set(row) == {'adapter_id', 'adapter_version', 'module', 'owner'})
        key = row['adapter_id'], row['adapter_version']
        _require(all(type(part) is str and part for part in key) and key not in seen)
        _require(type(row['module']) is str and row['module'].startswith(
            'gene_annotation_episode.episodic_workflow.root.a110.'))
        _require(row['owner'] in value['owners'])
        seen.add(key)
    for name, row in value['owners'].items():
        _require(type(name) is str and name and type(row) is dict
                 and set(row) == {'current'})
        current = row['current']
        _require(type(current) is dict and set(current) == {'implementation_sha256', 'members'})
        _require(_digest(current['implementation_sha256']))
        _members(current['members'])
    return value


def _frame(result, name, raw):
    result.update(name.encode('utf-8') + b'\0' + str(len(raw)).encode('ascii') + b'\0' + raw)


def _current(owner, record):
    result = hashlib.sha256((CURRENT_VERSION + '\0' + owner + '\0').encode('utf-8'))
    for member in record['members']:
        relative = _path(member['path'])
        path = (_ROOT / relative).resolve(strict=True)
        _require(path.is_relative_to((_ROOT / Path(*_AXIS)).resolve()),
                 'appservice_adapter_current_source_outside_root')
        _frame(result, member['path'], path.read_bytes())
    return result.hexdigest()


def current_implementation_sha256(owner):
    """Hash actual installed reader bytes."""
    document = _document()
    _require(owner in document['owners'])
    return _current(owner, document['owners'][owner]['current'])


def authenticate_adapter_source(adapter_id, adapter_version, module_name,
                                configured_sha256, actual_sha256):
    """Check that a configured implementation is the installed one.

    The returned record grants no action, publication, execution credit or
    scientific validity.
    """
    _require(_digest(configured_sha256) and _digest(actual_sha256),
             'appservice_adapter_implementation_conflict')
    document = _document()
    matches = [row for row in document['adapters'] if
               (row['adapter_id'], row['adapter_version']) == (adapter_id, adapter_version)]
    _require(len(matches) == 1 and matches[0]['module'] == module_name,
             'appservice_adapter_implementation_conflict')
    adapter = matches[0]
    current = _current(adapter['owner'], document['owners'][adapter['owner']]['current'])
    _require(current == actual_sha256, 'appservice_adapter_current_source_conflict')
    _require(configured_sha256 == current, 'appservice_adapter_implementation_conflict')
    return {'mode': 'current_implementation', 'configured_sha256': configured_sha256,
            'current_reader_sha256': current}
