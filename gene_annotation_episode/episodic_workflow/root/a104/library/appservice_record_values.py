from __future__ import annotations
'Selected AppService operations in the existing API episode executor.\n\nThis host connects actual episode custody, one selected service invocation and\nimmutable receipts. It does not select a next operation or calculate science.\n'
import json
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.api_selected_call import perform_selected_call
from gene_annotation_episode.episodic_workflow.root.a104.api_selected_effects import EffectConflict
from gene_annotation_episode.episodic_workflow.root.a104.api_services import event as native_event
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_contracts import download_request, validate_contract
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_custody import AppServiceCustody, _references
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_inputs import AppServiceInputs
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_records import AppServiceRecords, PROVIDER, provisional_receipt_ref
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_receipt_values import build_appservice_receipt, confirm_appservice_effects
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError, identity
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, validate_target
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
SERVICE = 'bvbrc_appservice'
SUPPORT_SOURCE = 'bvbrc_appservice_support_refs'

def _common(record):
    return record['value'] if record['contract'] == 'CommonReceipt' else record['value']['receipt']

def _diagnostic(code, *, phase='publication', refs=()):
    return {'code': code, 'phase': phase, 'path': '', 'severity': 'error', 'evidence_refs': list(refs)}
__all__ = ['AppServiceCustody', 'AppServiceInputs', 'AppServiceRecords', 'ContractError', 'EffectConflict', 'PROVIDER', 'SERVICE', 'SUPPORT_SOURCE', '_common', '_diagnostic', '_immutable', '_read', '_references', 'build_appservice_receipt', 'canonical', 'confirm_appservice_effects', 'deepcopy', 'digest', 'download_request', 'identity', 'json', 'native_event', 'perform_selected_call', 'plain', 'provisional_receipt_ref', 'validate_contract', 'validate_target']
