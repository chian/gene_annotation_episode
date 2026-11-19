"""The typed AppService receipts an A103 API job or results episode retains in the run's shared Store.

Each typed receipt (``build_appservice_receipt`` or, for a download, ``build_acquisition_value``) is retained as a
``source`` record of provider ``episode.bvbrc_appservice_receipt`` whose artifact is ``{'version', 'contract',
'scope', 'value'}``: ``scope`` is the admitted Store scope its operation ran under (its digest is the receipt's
``origin.scope_sha256``) and ``value`` the typed value without its own receipt reference, which is the record id.
``_decode`` restores that reference when the receipt is read back (``held_inputs.read_receipt``).
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.gene_context_evidence.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.execution_contracts import digest

RECEIPT_PROVIDER = 'episode.bvbrc_appservice_receipt'
VERSION = 'bvbrc_appservice_retained_receipt_v1'


def _common(contract, value):
    if contract == 'AcquisitionReceipt':
        # This is an internal accessor, never another persisted receipt shape.
        return {'origin': value['origin'], 'snapshot': value['snapshot'],
                'receipt_ref': value['artifact']['transfer']['receipt_ref']}
    return value if contract == 'CommonReceipt' else value['receipt']


def _encode(contract, value):
    value = deepcopy(value)
    if contract == 'AcquisitionReceipt':
        if value['publication_ref'] is not None:
            raise ValueError('appservice_acquisition_publication_reference_conflict')
        del value['artifact']['transfer']['receipt_ref']
        return value
    own = _common(contract, value).pop('receipt_ref')
    if contract == 'TaskHandoff':
        if value['original_task'].pop('submission_receipt_ref') != own:
            raise ValueError('appservice_receipt_self_identity_conflict')
    return value


def _decode(contract, value, reference):
    value = deepcopy(value)
    if contract == 'AcquisitionReceipt':
        if 'receipt_ref' in value['artifact']['transfer']:
            raise ValueError('appservice_receipt_stored_self_reference')
        if value['publication_ref'] is not None:
            raise ValueError('appservice_acquisition_publication_reference_conflict')
        value['artifact']['transfer']['receipt_ref'] = reference
        return validate_contract(contract, value)
    common = _common(contract, value)
    if 'receipt_ref' in common:
        raise ValueError('appservice_receipt_stored_self_reference')
    common['receipt_ref'] = reference
    if contract == 'TaskHandoff':
        if 'submission_receipt_ref' in value['original_task']:
            raise ValueError('appservice_receipt_stored_self_reference')
        value['original_task']['submission_receipt_ref'] = reference
    return validate_contract(contract, value)


def provisional_receipt_ref(origin):
    return 'appservice_receipt_intent_' + digest(validate_contract('ReceiptOrigin', origin))


def retain_receipt(store, built, scope, parents):
    """Retain one typed receipt with the admitted scope it ran under; its record id is its receipt ref."""
    common = _common(built['contract'], built['value'])
    # The scope digest is the one the episode computed for the receipt origin (``held_inputs.digest``).
    if common['origin']['scope_sha256'] != hashlib.sha256(canonical(scope).encode('utf-8')).hexdigest():
        raise ContractError('appservice_receipt_scope_digest_conflict')
    artifact = store.artifact(canonical({'version': VERSION, 'contract': built['contract'], 'scope': scope,
                                          'value': _encode(built['contract'], built['value'])}), 'application/json')
    return store.put('source', {
        'provider': RECEIPT_PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None,
        'request_ref': None, 'version': VERSION, 'retrieved_at': None,
        'parent_source_refs': list(dict.fromkeys(parents))}, origin='tool')['id']


__all__ = ['RECEIPT_PROVIDER', 'VERSION', 'provisional_receipt_ref', 'retain_receipt']
