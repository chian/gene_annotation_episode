"""Exercise real A110 adapter registration against its installed source assets.

These controlled checks only bind adapter modules and authenticate source bytes.
They do not construct API clients, restore saved episodes or execute science.
"""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import adapter_source_identity as identity
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import bvbrc_appservice_adapters as registry


@pytest.fixture
def epochs():
    document = json.loads(identity._MANIFEST.read_bytes())
    assert len(document['adapters']) == 17
    current, retained = [], []
    for row in document['adapters']:
        owner = document['owners'][row['owner']]
        base = {'adapter_id': row['adapter_id'], 'adapter_version': row['adapter_version']}
        current.append({**base, 'implementation_sha256': owner['current']['implementation_sha256']})
        retained.append({**base, 'implementation_sha256': owner['original']['implementation_sha256']})
    return document, current, retained


def test_all_real_adapters_bind_their_actual_current_source_identity(epochs):
    document, current, _ = epochs
    bound = registry.bind_adapters(current)
    assert len(bound) == 17
    for row in document['adapters']:
        implementation, configured = bound[row['adapter_id'], row['adapter_version']]
        assert implementation.__name__ == row['module']
        assert implementation.implementation_sha256() == configured
        assert configured == document['owners'][row['owner']]['current']['implementation_sha256']


def test_all_retained_bindings_authenticate_original_custody_without_relabeling(epochs):
    document, _, retained = epochs
    before = deepcopy(retained)
    bound = registry.bind_adapters(retained, retained_reader=True)
    assert retained == before
    assert len(bound) == 17
    for row in document['adapters']:
        implementation, configured = bound[row['adapter_id'], row['adapter_version']]
        owner = document['owners'][row['owner']]
        assert implementation.__name__ == row['module']
        assert configured == owner['original']['implementation_sha256']
        assert implementation.implementation_sha256() == owner['current']['implementation_sha256']
        assert configured != implementation.implementation_sha256()


def test_real_registry_rejects_original_fingerprint_in_fresh_binding(epochs):
    _, _, retained = epochs
    with pytest.raises(ValueError, match='^appservice_adapter_implementation_conflict$'):
        registry.bind_adapters(retained)


def test_real_registry_preserves_duplicate_configuration_failure(epochs):
    _, current, _ = epochs
    with pytest.raises(ValueError, match='^appservice_adapter_configuration_conflict$'):
        registry.bind_adapters([current[0], deepcopy(current[0])])


def test_real_registry_preserves_unknown_adapter_unavailability(epochs):
    _, current, _ = epochs
    unknown = {'adapter_id': 'unavailable_unregistered_adapter',
               'adapter_version': '1', 'implementation_sha256': 'f' * 64}
    assert registry.bind_adapters([unknown]) == {}
    known = registry.bind_adapters([unknown, current[0]])
    assert set(known) == {(current[0]['adapter_id'], current[0]['adapter_version'])}
