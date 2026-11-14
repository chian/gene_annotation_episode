"""Current-source identity and separately authenticated historical custody.

These tests exercise source authentication only, without API clients, scientific
execution, saved episode restoration or assertions of scientific validity.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import adapter_source_identity as identity


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def epoch(tmp_path, monkeypatch):
    relative = Path('gene_annotation_episode/episodic_workflow/root/a110/library/received_execution_dependencies')
    directory = tmp_path / relative
    directory.mkdir(parents=True)
    sources = {'owned_adapter.py': b'def validate(value):\n    return value\n',
               'owned_contract.py': b'ORIGINAL_FAILED_STATUS = "failed"\n'}
    members = []
    current_parts = [b'a110_adapter_reader_sources_v1\0owned_adapter\0']
    for name, raw in sorted(sources.items()):
        path = relative / name
        (tmp_path / path).write_bytes(raw)
        members.append({'path': str(path), 'sha256': _sha(raw), 'size_bytes': len(raw)})
        current_parts.extend([str(path).encode(), b'\0', str(len(raw)).encode(), b'\0', raw])
    current_sha = _sha(b''.join(current_parts))
    prior = {'owned_adapter.py': b'# original complete adapter\n',
             'owned_contract.py': b'# original failed and invalid contracts\n'}
    custody = directory / 'adapter_source_custody'
    custody.mkdir()
    original_members, original_parts = [], []
    for name, raw in sorted(prior.items()):
        (custody / (_sha(raw) + '.source')).write_bytes(raw)
        original_members.append({'path': name, 'sha256': _sha(raw), 'size_bytes': len(raw)})
        original_parts.extend([name.encode(), b'\0', str(len(raw)).encode(), b'\0', raw])
    original_sha = _sha(b''.join(original_parts))
    module = 'gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.owned_adapter'
    document = {'version': identity.VERSION,
        'adapters': [{'adapter_id': 'owned', 'adapter_version': '1', 'module': module, 'owner': 'owned_adapter'}],
        'owners': {'owned_adapter': {
            'original': {'commit': 'a' * 40, 'implementation_sha256': original_sha, 'members': original_members},
            'current': {'implementation_sha256': current_sha, 'members': members}}},
        'preparation': {'boundary': 'test source custody only'}}
    manifest = directory / 'adapter_source_identity.json'
    manifest.write_text(json.dumps(document))
    monkeypatch.setattr(identity, '_ROOT', tmp_path)
    monkeypatch.setattr(identity, '_DIRECTORY', directory)
    monkeypatch.setattr(identity, '_MANIFEST', manifest)
    return {'root': tmp_path, 'directory': directory, 'manifest': manifest, 'document': document,
            'module': module, 'current': current_sha, 'original': original_sha}


def bind(epoch, configured, *, received=False, actual=None):
    return identity.authenticate_adapter_source('owned', '1', epoch['module'], configured,
        epoch['current'] if actual is None else actual, retained_reader=received)


def test_current_digest_is_actual_reader_bytes_not_original_digest(epoch):
    assert identity.current_implementation_sha256('owned_adapter') == epoch['current']
    assert epoch['current'] != epoch['original']
    assert bind(epoch, epoch['current']) == {
        'mode': 'current_implementation', 'configured_sha256': epoch['current'],
        'current_reader_sha256': epoch['current'], 'original_commit': None}


def test_saved_digest_requires_explicit_received_boundary_and_retains_both_identities(epoch):
    with pytest.raises(ValueError, match='appservice_adapter_implementation_conflict'):
        bind(epoch, epoch['original'])
    assert bind(epoch, epoch['original'], received=True) == {
        'mode': 'retained_source_reader', 'configured_sha256': epoch['original'],
        'current_reader_sha256': epoch['current'], 'original_commit': 'a' * 40}
    assert json.loads(epoch['manifest'].read_text()) == epoch['document']


def test_current_dependency_edit_changes_digest_and_invalidates_reviewed_saved_transition(epoch):
    member = epoch['document']['owners']['owned_adapter']['current']['members'][1]
    path = epoch['root'] / member['path']
    path.write_bytes(path.read_bytes() + b'# changed contract\n')
    changed = identity.current_implementation_sha256('owned_adapter')
    assert changed not in {epoch['original'], epoch['current']}
    with pytest.raises(ValueError, match='appservice_adapter_current_source_conflict'):
        bind(epoch, epoch['current'])
    with pytest.raises(ValueError, match='appservice_adapter_retained_reader_source_conflict'):
        bind(epoch, epoch['original'], received=True, actual=changed)
    assert bind(epoch, changed, actual=changed)['mode'] == 'current_implementation'


def test_original_source_tamper_cannot_be_accepted_by_matching_saved_label(epoch):
    member = epoch['document']['owners']['owned_adapter']['original']['members'][0]
    path = epoch['directory'] / 'adapter_source_custody' / (member['sha256'] + '.source')
    path.write_bytes(b'forged original source\n')
    with pytest.raises(ValueError, match='appservice_adapter_source_custody_conflict'):
        bind(epoch, epoch['original'], received=True)
    assert bind(epoch, epoch['current'])['mode'] == 'current_implementation'


def test_missing_original_custody_remains_unavailable_and_does_not_break_fresh_identity(epoch):
    member = epoch['document']['owners']['owned_adapter']['original']['members'][0]
    (epoch['directory'] / 'adapter_source_custody' / (member['sha256'] + '.source')).unlink()
    assert bind(epoch, epoch['current'])['mode'] == 'current_implementation'
    with pytest.raises(FileNotFoundError):
        bind(epoch, epoch['original'], received=True)


def test_unknown_epoch_and_wrong_adapter_module_are_rejected(epoch):
    with pytest.raises(ValueError, match='appservice_adapter_implementation_conflict'):
        bind(epoch, 'f' * 64, received=True)
    with pytest.raises(ValueError, match='appservice_adapter_implementation_conflict'):
        identity.authenticate_adapter_source('owned', '1', epoch['module'] + '_other',
            epoch['original'], epoch['current'], retained_reader=True)


@pytest.mark.parametrize('section,path', [('current', '../foreign.py'), ('original', 'nested/foreign.py')])
def test_source_members_cannot_escape_their_declared_owner(epoch, section, path):
    document = deepcopy(epoch['document'])
    document['owners']['owned_adapter'][section]['members'][0]['path'] = path
    epoch['manifest'].write_text(json.dumps(document))
    with pytest.raises(ValueError, match='appservice_adapter_source_identity_invalid'):
        identity.current_implementation_sha256('owned_adapter')


def test_duplicate_manifest_keys_are_invalid(epoch):
    raw = epoch['manifest'].read_text()
    epoch['manifest'].write_text('{"version":"spoofed",' + raw[1:])
    with pytest.raises(ValueError, match='appservice_adapter_source_identity_invalid'):
        identity.current_implementation_sha256('owned_adapter')
