from __future__ import annotations
'Persist exactly the artifacts acquired by selected AppService downloads.\n\nThis module owns no network call, episode decision, scientific formula or loop.\nReceipts and dependency manifests remain immutable across later acquisitions.\n'
from copy import deepcopy
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_bundle_values import build_acquisition_value, build_artifact_bundle
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_records import provisional_receipt_ref
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
DATA_PROVIDER = 'episode.bvbrc_appservice_bundle_data'
DATA_VERSION = 'bvbrc_appservice_bundle_data_v1'
RESULT_VERSION = 'bvbrc_appservice_acquired_bundle_v1'

def _origin(record):
    value = record['value']
    return value['origin'] if record['contract'] in {'CommonReceipt', 'AcquisitionReceipt'} else value['receipt']['origin']

def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(deepcopy(value))
    return result

def _require(condition, code):
    if not condition:
        raise ValueError(code)
__all__ = ['DATA_PROVIDER', 'DATA_VERSION', 'Draft202012Validator', 'RESULT_VERSION', '_immutable', '_origin', '_read', '_require', '_unique', 'build_acquisition_value', 'build_artifact_bundle', 'canonical', 'deepcopy', 'digest', 'plain', 'provisional_receipt_ref', 'validate_contract']
