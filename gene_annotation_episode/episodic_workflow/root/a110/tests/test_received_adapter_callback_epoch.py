"""Actual current/retained adapter authentication after the callback source epoch."""
from importlib import import_module
import pytest

from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import adapter_source_identity as identity


@pytest.mark.parametrize('owner,old_current', [
    ('bvbrc_comparative_systems_bundle_adapter', '90a2461cffdd18657e8f1f71242a8eb7fa51d878f4732edadd3dfff8fe8449fe'),
    ('bvbrc_genome_alignment_bundle_adapter', 'b7937b1834e1bc6b3e200dc80cc4814a06e7f69dc10391630ccf944a16a56740'),
])
def test_original_custody_stays_valid_but_previous_current_epoch_is_not_relabelled(owner, old_current):
    document = identity._document()
    adapter, = [row for row in document['adapters'] if row['owner'] == owner]
    module = import_module(adapter['module'])
    actual = module.implementation_sha256()
    assert actual != old_current
    original = document['owners'][owner]['original']['implementation_sha256']
    arguments = (adapter['adapter_id'], adapter['adapter_version'], adapter['module'])
    current = identity.authenticate_adapter_source(*arguments, actual, actual)
    assert current['mode'] == 'current_implementation'
    retained = identity.authenticate_adapter_source(*arguments, original, actual, retained_reader=True)
    assert retained['mode'] == 'retained_source_reader'
    assert retained['configured_sha256'] == original
    assert retained['current_reader_sha256'] == actual
    for retained_reader in (False, True):
        with pytest.raises(ValueError, match='appservice_adapter_implementation_conflict'):
            identity.authenticate_adapter_source(*arguments, old_current, actual, retained_reader=retained_reader)
