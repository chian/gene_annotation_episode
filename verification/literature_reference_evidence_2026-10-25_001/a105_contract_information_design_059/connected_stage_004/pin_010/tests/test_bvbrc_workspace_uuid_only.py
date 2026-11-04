"""A task-reported UUID is usable without manufacturing an unobserved path."""
from copy import deepcopy

import pytest

from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_readers import _object_binding
from test_api_bvbrc_appservice import (harness, original_request, original_task, bound,
    prepare, OBJECT_UUID, association)


def uuid_object():
    return {'path': None, 'uuid': OBJECT_UUID, 'type': None, 'metadata_receipt_ref': None}


def test_uuid_only_object_preserves_unknown_path():
    obj = uuid_object()
    assert validate_contract('WorkspaceObject', obj) == obj
    assert _object_binding({'object': obj, 'metadata': None}) == (obj, None)


def test_no_object_identity_is_rejected():
    with pytest.raises(ValueError):
        validate_contract('WorkspaceObject', {**uuid_object(), 'uuid': None})


def test_actual_metadata_operation_sends_only_reported_uuid(harness):
    request = original_request()
    selected = {'kind': 'task_info_object', 'receipt_ref': 'task-info-receipt'}
    args = {'objects': [selected], 'options': {}}
    row = {'selection': deepcopy(selected), 'native_reference': OBJECT_UUID,
        'object': uuid_object(), 'metadata': None,
        'task_association': {**association(), 'kind': 'task_info_object',
            'evidence_ref': 'source_task_info', 'pointer': '', 'output_path': None},
        'identity': 'workspace-uuid:' + OBJECT_UUID}
    bindings = bound(request, 'workspace_metadata', args, objects=[row])
    operation = prepare(harness, 'workspace_metadata', args, bindings)
    assert operation['native_operands']['call']['rpc_request']['params'] == [
        {'objects': [OBJECT_UUID], 'metadata_only': 1}]
    assert operation['bound_inputs']['resolved']['objects'][0]['object']['path'] is None
    assert harness.client.calls == []
