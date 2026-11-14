"""The actual private scientific binding identifies itself without aliasing."""
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.root.a105.episode_composition import scientific_binding_compatible
from .test_private_scientific_process import scientific_binding


def test_actual_scientific_descriptor_is_compatible_with_itself():
    actual = scientific_binding().as_record()
    assert actual['version'] == 'scientific_process_episode_v10'
    assert scientific_binding_compatible(actual, deepcopy(actual))


def test_scientific_identity_rejects_changed_current_configuration_or_code():
    actual = scientific_binding().as_record()
    for key, value in [('version', 'scientific_process_episode_v11'),
                       ('binding_id', 'literature'),
                       ('implementation_sha256', '0' * 64),
                       ('configuration', {'library': {'substituted': True}})]:
        recorded = deepcopy(actual)
        recorded[key] = value
        assert not scientific_binding_compatible(actual, recorded)
