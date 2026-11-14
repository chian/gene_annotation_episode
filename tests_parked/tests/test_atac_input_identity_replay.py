"""ATAC input authority, actual native staging failures, and closed replay.

Run through packet487's pinned bounded runner. Authored byte identities test
commission authority; original retained478 science is only replayed. The two
fresh driver cases fail staging before any MACS2 operation can start.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store
from test_atac_differential_operands import f, context, make_assignment
from test_atac_differential_execution_integration import selected

F = import_module('gene_annotation_episode.episodic_workflow.root.tests.fixtures.atac.workflow_478.fixture_helpers')


def versions(assignment):
    return [{'reference': row['file']['artifact_ref'], 'version': None,
        'content_sha256': row['file']['sha256']}
        for row in assignment['requested_job']['native_atac_differential']['input_bindings']]


def deny(*args, **kwargs):
    raise AssertionError('identity validation or closed replay attempted new work or input bytes')


def attach_source(store, artifact):
    return store.put('source', dict(provider='fixture.selected-input', accession=None, uri=None,
        artifact_ref=artifact, text_ref=None, request_ref=None, version=None, retrieved_at=None), origin='caller')


@pytest.mark.parametrize('physical_state', ['missing', 'changed'])
@pytest.mark.parametrize('source_attached', [False, True])
def test_atac_input_identity_replay_admits_exact_metadata_without_bytes(
        f, selected, monkeypatch, physical_state, source_attached):
    assignment = selected.assignment
    if source_attached:
        for row in versions(assignment):
            attach_source(f.store, row['reference'])
    for binding in selected.job['input_bindings']:
        path = Path(binding['path'])
        path.unlink() if physical_state == 'missing' else path.write_bytes(b'changed physical bytes')
    before = list(f.store.db.iterdump())
    with monkeypatch.context() as patch:
        for name in ('get_artifact', 'artifact', 'put'):
            patch.setattr(f.store, name, deny)
        for name in ('read_bytes', 'read_text', 'open', 'stat', 'lstat', 'resolve'):
            patch.setattr(Path, name, deny)
        for name in ('__init__', 'bind', 'receive'):
            patch.setattr(EpisodeReceipts, name, deny)
        assert selected.owner._versions(versions(assignment), f.scope,
            context=f.root, atac_assignments=[assignment]) is None
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('fault, expected', [
    ('declared_hash', 'execution_input_version_conflict'),
    ('revision', 'execution_input_version_conflict'),
    ('request_hash', 'atac_input_invalid_requested_job'),
    ('request_size', 'atac_input_artifact_metadata_mismatch'),
    ('store_size', 'atac_input_artifact_metadata_mismatch'),
    ('path', 'atac_input_selected_path_mismatch'),
    ('request_binding', 'atac_input_invalid_requested_job'),
    ('request_argv', 'atac_input_invalid_requested_job'),
    ('unreceived', 'atac_input_input_not_received'),
])
def test_atac_input_identity_replay_rejects_wrong_identity(f, selected, monkeypatch, fault, expected):
    assignment = deepcopy(selected.assignment)
    supplied = versions(assignment)
    job = assignment['requested_job']['native_atac_differential']
    if fault == 'declared_hash':
        supplied[0]['content_sha256'] = 'f' * 64
    elif fault == 'revision':
        supplied[0]['version'] = '1'
    elif fault == 'request_hash':
        job['request']['inputs'][0]['file']['sha256'] = 'f' * 64
        job['input_bindings'][0]['file']['sha256'] = 'f' * 64
    elif fault == 'request_size':
        job['request']['inputs'][0]['file']['size_bytes'] += 1
        job['input_bindings'][0]['file']['size_bytes'] += 1
    elif fault == 'store_size':
        f.store.db.execute('UPDATE artifacts SET size=size+1 WHERE id=?', (f.refs[0],))
    elif fault == 'path':
        job['input_bindings'][0]['path'] = '/unselected/input.bam'
    elif fault == 'request_binding':
        job['input_bindings'].reverse()
    elif fault == 'request_argv':
        assignment['requested_job']['argv'][-1] = 'other-plan.json'
    else:
        f.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?', (f.refs[0],))
    monkeypatch.setattr(f.store, 'get_artifact', deny)
    before = list(f.store.db.iterdump())
    with pytest.raises(ValueError, match='^' + expected + '$'):
        selected.owner._versions(supplied, f.scope, context=f.root, atac_assignments=[assignment])
    assert list(f.store.db.iterdump()) == before


def test_atac_input_identity_replay_preserves_inheritance_prefix(f, selected, monkeypatch):
    child = context(f, parent=f.root, role='launch', persist=False)
    supplied = versions(selected.assignment)
    monkeypatch.setattr(f.store, 'get_artifact', deny)
    assert selected.owner._versions(supplied, f.scope,
        context=child, atac_assignments=[selected.assignment]) is None
    late = f.store.artifact(b'only received after this child was constructed')
    f.receipts.receive(f.root.episode_id, [late], kind='own_action')
    metadata = f.store.get(late)
    altered = deepcopy(selected.assignment)
    job = altered['requested_job']['native_atac_differential']
    file = dict(artifact_ref=late, sha256=metadata['sha256'], size_bytes=metadata['size'], format='bam')
    job['request']['inputs'][0]['file'] = file
    job['request']['samples'][0]['input_artifact_refs'] = [late]
    job['input_bindings'][0]['file'] = deepcopy(file)
    job['input_bindings'][0]['path'] = str(f.store.path / 'artifacts' / file['sha256'][:2] / file['sha256'])
    with pytest.raises(ValueError, match='^atac_input_input_not_received$'):
        selected.owner._versions(versions(altered), f.scope, context=child, atac_assignments=[altered])
    request = plain(child.request)
    request['message']['knowledge_inheritance']['through_receipt_index'] += 1
    with pytest.raises(ValueError, match='^atac_input_invalid_context$'):
        selected.owner._versions(supplied, f.scope,
            context=replace(child, request=request), atac_assignments=[selected.assignment])


def test_atac_input_identity_replay_preserves_parent_scope(f, selected, monkeypatch):
    narrow = deepcopy(f.scope)
    narrow['segments'] = [dict(target_ref=f.scope['subject_refs'][0], start=0, end=4, unit='nt')]
    narrow = f.store.validate_scope(narrow, f.scope)
    child = context(f, parent=f.root, role='launch', persist=False, scope=narrow)
    monkeypatch.setattr(f.store, 'get_artifact', deny)
    assert selected.owner._versions(versions(selected.assignment), narrow,
        context=child, atac_assignments=[selected.assignment]) is None
    with pytest.raises(ValueError, match='^scope_segments_outside_parent$'):
        selected.owner._versions(versions(selected.assignment), f.scope,
            context=child, atac_assignments=[selected.assignment])


@pytest.mark.parametrize('protection', ['atac', 'chromatin', 'protein'])
def test_atac_input_identity_replay_preserves_protected_reference_denials(f, selected, monkeypatch, protection):
    reference = f.refs[0]
    attach_source(f.store, reference)
    assert f.store.reference_subset([reference], f.scope) == [reference]
    monkeypatch.setattr(selected.owner, '_' + protection + '_reference_access',
        lambda context, ref, namespace: False if ref == reference else None)
    monkeypatch.setattr(f.store, 'get_artifact', deny)
    with pytest.raises(ValueError):
        selected.owner._versions(versions(selected.assignment), f.scope,
            context=f.root, atac_assignments=[selected.assignment])


def test_atac_input_identity_replay_generic_inputs_keep_byte_checks(f, selected, monkeypatch):
    supplied = versions(selected.assignment)
    with pytest.raises(ValueError, match='^execution_input_outside_assigned_scope$'):
        selected.owner._versions(supplied, f.scope, context=f.root)
    unrelated = f.store.artifact(b'explicitly received but not selected')
    f.receipts.receive(f.root.episode_id, [unrelated], kind='own_action')
    with pytest.raises(ValueError, match='^execution_input_outside_assigned_scope$'):
        selected.owner._versions([dict(reference=unrelated, version=None, content_sha256=None)],
            f.scope, context=f.root, atac_assignments=[selected.assignment])
    source = attach_source(f.store, supplied[0]['reference'])
    generic = [dict(supplied[0], reference=source['id'])]
    reads, original_read = [], f.store.get_artifact
    def record_read(reference):
        reads.append(reference)
        return original_read(reference)
    monkeypatch.setattr(f.store, 'get_artifact', record_read)
    assert selected.owner._versions(generic, f.scope,
        context=f.root, atac_assignments=[selected.assignment]) is None
    assert reads == [supplied[0]['reference']]
    with pytest.raises(ValueError, match='^execution_input_version_conflict$'):
        selected.owner._versions([dict(generic[0], content_sha256='f' * 64)], f.scope,
            context=f.root, atac_assignments=[selected.assignment])
    path = Path(selected.job['input_bindings'][0]['path'])
    path.unlink()
    with pytest.raises(FileNotFoundError):
        selected.owner._versions(generic, f.scope, context=f.root, atac_assignments=[selected.assignment])




