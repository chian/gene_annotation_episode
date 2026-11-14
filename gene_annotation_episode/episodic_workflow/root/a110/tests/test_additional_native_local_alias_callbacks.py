"""Actual A110 ATAC/chromatin/NMF reference callbacks with controlled custody.

SQLite executes each original classification query. Completed-receipt and
received-report authentication are explicit test collaborators, not saved-state
or native scientific validation. All private host/receipt constructors run.
"""
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_receiving_owner import HistoricalReceivedExecutionOwner
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import atac_differential_result_receipts as atac_receipts
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import chromatin_interaction_result_receipts as chromatin_receipts
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import expression_nmf_result_receipts as nmf_receipts
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_results import NativeAtacDifferentialResults
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_chromatin_interaction_results import NativeChromatinInteractionResults
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_expression_nmf_results import NativeExpressionNMFResults

REFERENCE = 'artifact_' + 'a' * 64
OTHER = 'artifact_' + 'b' * 64
FAMILIES = [
    ('atac', NativeAtacDifferentialResults, atac_receipts, 'atac_results', 'atac_returns',
     '_atac_reference_access', 'atac_differential_result_selector_v1'),
    ('chromatin', NativeChromatinInteractionResults, chromatin_receipts, 'native_chromatin_interaction_results',
     'native_chromatin_interaction_returns', '_chromatin_reference_access', 'chromatin_interaction_result_selector_v1'),
    ('nmf', NativeExpressionNMFResults, nmf_receipts, 'native_expression_nmf_results',
     'native_expression_nmf_returns', '_expression_nmf_reference_access', 'expression_nmf_result_selector_v1'),
]


@pytest.fixture(params=FAMILIES, ids=[row[0] for row in FAMILIES])
def boundary(request):
    name, cls, module, field, returns_field, callback, selector = request.param
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE runtime_actions (run_id TEXT, episode_id TEXT, result TEXT)')
    owner = HistoricalReceivedExecutionOwner.__new__(HistoricalReceivedExecutionOwner)
    owner.run_id = 'controlled-run'
    owner.store = SimpleNamespace(db=db)
    context = SimpleNamespace(role='results', scope={}, assignment={'selector': {'version': selector, 'mode': 'native_result'}})
    received = []
    authority = SimpleNamespace(context=lambda episode_id: SimpleNamespace(scope={'original_episode': episode_id}),
        resolve_received=lambda *args: received.append(args) or True)
    setattr(owner, returns_field, authority)
    host = cls(owner)
    setattr(owner, field, host)
    calls = []
    failure = []
    def authenticate(**kwargs):
        calls.append(kwargs)
        if failure:raise failure[0]
        return {'controlled_authenticated_receipt': True}
    host.receipts.read_completed = authenticate
    facts = module.empty_facts()
    host.receipts.completed_receipts = lambda selected: [{'facts': facts}]
    def add(*, original_input=False):
        file = {'artifact_ref': REFERENCE}
        value = {'version': module.VERSION, 'intent': {'operation_key': 'original-operation'}}
        if name == 'atac':
            value['intent']['target'] = {'assignment': {'requested_job': {'native_atac_differential': {
                'request': {'inputs': [{'file': {'artifact_ref': REFERENCE if original_input else OTHER}}]}}}}}
            value['diagnostic_derived_reference'] = REFERENCE
        elif name == 'chromatin':
            value['worker_capture'] = {'outputs': [] if original_input else [{'capture': {'observed': file}}], 'failures': []}
            value['capture'] = {'files': [{'specification': {'role': 'original_contact'}, 'retained': {'file': file}}]} if original_input else None
        else:
            value['worker_capture'] = None if original_input else {'outputs': [{'observed': file}]}
            value['capture'] = {'files': [{'role': 'original_input', 'retained': {'file': file}}]} if original_input else None
        db.execute('INSERT INTO runtime_actions VALUES (?,?,?)', ('controlled-run', 'original-episode', json.dumps({'result': value})))
    result = SimpleNamespace(name=name, owner=owner, host=host, module=module, context=context,
        received=received, authenticated=calls, failure=failure, add=add, facts=facts,
        access=lambda reference=REFERENCE, namespace='artifact': getattr(owner, callback)(context, reference, namespace))
    yield result
    db.close()


def test_nonartifact_reference_remains_unclassified(boundary):
    assert boundary.access('external-reference') is None
    assert boundary.authenticated == boundary.received == []


def test_actual_local_alias_resolves_only_explicit_own_saved_fact(boundary):
    boundary.add()
    file = {'artifact_ref': REFERENCE}
    boundary.facts[boundary.module.SAVED_SOURCE].append(file if boundary.name == 'nmf' else {'sheet': file, 'tables': []})
    assert boundary.access() is True
    assert boundary.authenticated == [{'episode_id': 'original-episode', 'operation_key': 'original-operation',
                                        'scope': {'original_episode': 'original-episode'}}]
    assert boundary.received == []


def test_original_supplied_operand_does_not_become_private_output(boundary):
    boundary.add(original_input=True)
    assert boundary.access() is None
    assert boundary.authenticated == boundary.received == []


def test_invalid_original_receipt_is_not_granted_or_swallowed(boundary):
    boundary.add()
    error = ValueError('controlled_original_receipt_rejected')
    boundary.failure.append(error)
    with pytest.raises(ValueError) as caught:
        boundary.access()
    assert caught.value is error
    assert boundary.received == []


def test_received_recipient_uses_original_return_authority(boundary):
    boundary.add()
    boundary.context.role = 'annotation'
    assert boundary.access() is True
    assert boundary.received == [(boundary.context, REFERENCE, 'artifact')]


def test_wrong_namespace_is_denied_before_own_fact_read(boundary):
    def forbidden(*args, **kwargs):
        raise AssertionError('wrong namespace must not inspect own facts')
    boundary.host.own_fact_groups = forbidden
    assert boundary.host.resolve_own(boundary.context, REFERENCE, 'source') is False


def test_original_atac_reference_scanner_keeps_nested_private_metadata():
    value = {'definition': [REFERENCE, {'deeper': OTHER}], 'not_artifacts': ['artifact_short', 'artifact_' + 'A' * 64]}
    assert list(atac_receipts.artifact_references(value)) == [REFERENCE, OTHER]
