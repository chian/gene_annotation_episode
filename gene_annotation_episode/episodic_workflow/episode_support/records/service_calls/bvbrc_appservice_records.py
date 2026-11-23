"""Typed AppService receipts in the existing Store (native sources: ``bvbrc_appservice_native_sources``).

This persistence component makes no request and no scientific calculation.
The custody helper separately establishes which receiver possesses a receipt.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.perturbation_evidence.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.perturbation_evidence.bvbrc_appservice_contracts import download_request, validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.readers.service_calls.perturbation_evidence.bvbrc_appservice_readers import qualify_download
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import identity
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.episode_support.jobs.perturbation_evidence.practical_execution_state import _immutable, _read


PROVIDER = 'episode.bvbrc_appservice_receipt'
VERSION = 'bvbrc_appservice_retained_receipt'
_CONTRACTS = {'CommonReceipt', 'CatalogReceipt', 'PreparationReceipt',
    'WorkspaceReceipt', 'UploadReceipt', 'TaskInfoReceipt', 'TaskObservation',
    'CapabilityReceipt', 'TaskHandoff', 'AcquisitionReceipt'}


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


