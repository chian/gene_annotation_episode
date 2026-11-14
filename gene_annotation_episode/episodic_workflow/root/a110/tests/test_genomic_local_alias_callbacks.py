"""Actual receiver/host methods with controlled stored-receipt collaborators.

Constructors are deliberately bypassed only for the large historical receiver.
The real host and receipt classes are constructed, SQLite runs the original
ownership query, and exact receipt authentication/return collaborators are
controlled. This does not validate saved restoration or scientific artifacts.
"""
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a110 import genomic_overlap_result_receipts as receipts
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_genomic_overlap_results import NativeGenomicOverlapResults
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.genomic_overlap_return_views import SAVED_SOURCE
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_receiving_owner import HistoricalReceivedExecutionOwner

REFERENCE = 'artifact_' + 'a' * 64


@pytest.fixture
def boundary():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE runtime_actions (run_id TEXT, episode_id TEXT, result TEXT)')
    owner = HistoricalReceivedExecutionOwner.__new__(HistoricalReceivedExecutionOwner)
    owner.run_id = 'controlled-run'
    owner.store = SimpleNamespace(db=db)
    context = SimpleNamespace(role='results', scope={'controlled': True},
        assignment={'selector': {'version': 'genomic_overlap_result_selector_v1', 'mode': 'native_result'}})
    calls = []
    authority = SimpleNamespace(
        context=lambda episode_id: SimpleNamespace(scope={'original_episode': episode_id}),
        resolve_received=lambda *args: calls.append(('received', args)) or True,
        authenticate_received_saved_sheet=lambda *args: calls.append(('saved', args)))
    owner.native_genomic_overlap_returns = authority
    owner.native_genomic_overlap_results = NativeGenomicOverlapResults(owner)
    host = owner.native_genomic_overlap_results
    authenticated = []
    failure = []
    def authenticate(**kwargs):
        authenticated.append(kwargs)
        if failure:
            raise failure[0]
        return {'controlled_authenticated_receipt': True}
    host.receipts.read_completed = authenticate
    groups = receipts.empty_facts()
    host.receipts.completed_receipts = lambda selected: [{'facts': groups}]
    def add(*, artifact=REFERENCE, malformed=False, field='/outputs/sheet', run_id='controlled-run'):
        capture = {'outputs': [] if malformed else [{'observed': {'artifact_ref': artifact}}],
            'failures': [{'field_path': field, 'observed_value': {'artifact_ref': artifact}}] if malformed else []}
        value = {'result': {'version': receipts.VERSION, 'worker_capture': capture,
                           'intent': {'operation_key': 'original-operation'}}}
        db.execute('INSERT INTO runtime_actions VALUES (?,?,?)', (run_id, 'original-episode', json.dumps(value)))
    value = SimpleNamespace(owner=owner, host=host, context=context, calls=calls,
                            authenticated=authenticated, failure=failure, groups=groups, add=add)
    yield value
    db.close()


def access(value, reference=REFERENCE, namespace='artifact'):
    return value.owner._genomic_overlap_reference_access(value.context, reference, namespace)


def test_absent_host_keeps_unclassified_result(boundary):
    boundary.owner.native_genomic_overlap_results = None
    assert access(boundary) is None


@pytest.mark.parametrize('reference', [None, 7, 'external-reference'])
def test_real_host_classifies_nonartifact_without_receipt_access(boundary, reference):
    assert access(boundary, reference) is None
    assert boundary.authenticated == boundary.calls == []


def test_unowned_artifact_does_not_fall_through_to_received_authority(boundary):
    assert access(boundary) is None
    assert boundary.authenticated == boundary.calls == []


def test_private_artifact_namespace_denial_is_preserved(boundary):
    boundary.add()
    assert access(boundary, namespace='source') is False
    assert len(boundary.authenticated) == 1
    assert boundary.calls == []


def test_own_saved_fact_is_admitted_through_actual_local_host_alias(boundary):
    boundary.add()
    boundary.groups[SAVED_SOURCE].append({'artifact_ref': REFERENCE})
    assert access(boundary) is True
    assert boundary.authenticated == [{'episode_id': 'original-episode', 'operation_key': 'original-operation',
                                        'scope': {'original_episode': 'original-episode'}}]
    assert boundary.calls == []


def test_explicit_received_saved_sheet_uses_original_authenticator(boundary):
    boundary.add()
    supplied = {'artifact_ref': REFERENCE}
    boundary.context.assignment['selector'].update(mode='saved_sheet_recalculation', saved_sheet_file=supplied)
    assert access(boundary) is True
    assert boundary.calls == [('saved', (boundary.context, supplied))]


def test_nonresults_recipient_uses_existing_received_authority(boundary):
    boundary.add()
    boundary.context.role = 'annotation'
    assert access(boundary) is True
    assert boundary.calls == [('received', (boundary.context, REFERENCE, 'artifact'))]


def test_original_receipt_authentication_failure_keeps_exception_identity(boundary):
    boundary.add()
    error = ValueError('controlled_original_receipt_rejected')
    boundary.failure.append(error)
    with pytest.raises(ValueError) as caught:
        access(boundary)
    assert caught.value is error
    assert boundary.calls == []


def test_malformed_orphan_output_remains_private(boundary):
    boundary.add(malformed=True)
    assert boundary.host.owns_reference(REFERENCE) is True
    assert len(boundary.authenticated) == 1


def test_unrelated_failure_field_does_not_manufacture_ownership(boundary):
    boundary.add(malformed=True, field='/inputs/sheet')
    assert boundary.host.owns_reference(REFERENCE) is False
    assert boundary.authenticated == []


def test_original_run_identity_limits_private_artifact_classification(boundary):
    boundary.add(run_id='another-run')
    assert boundary.host.owns_reference(REFERENCE) is False
    assert boundary.authenticated == []


def test_resolve_own_rejects_wrong_namespace_before_reading_facts(boundary):
    def forbidden(*args, **kwargs):
        raise AssertionError('wrong namespace must not read facts')
    boundary.host.own_fact_groups = forbidden
    assert boundary.host.resolve_own(boundary.context, REFERENCE, 'source') is False
