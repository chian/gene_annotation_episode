"""Original A106 Literature analysis commissions require their own private children."""
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a106.tests.test_private_multi_parent_construction import full_workflow


@pytest.mark.parametrize('scientific', [False, True])
@pytest.mark.parametrize('role', ['launch', 'results'])
def test_original_literature_analysis_child_has_exact_commissioning_owner(
        full_workflow, scientific, role):
    _, workflow = full_workflow
    parent_path = (('annotation', 'root'),)
    if scientific:
        parent_path += (('perturbation_evidence', 'science'),)
    registry = workflow.episode_bindings
    literature = registry.for_child(parent_path, 'literature')
    path = parent_path + (('literature', 'original-literature'),)
    context = SimpleNamespace(role='literature', path=path)
    assert role in literature.allowed_children(context, ())
    child = registry.for_child(path, role)
    assert child.commissioning_parent == literature.binding_path
    assert child is not registry.for_child(parent_path, role)
    assert child.roles == (role,)
    assert registry.for_path(path + ((role, 'original-analysis'),)) is child


@pytest.mark.parametrize('service,adapters,expected_children,expected_catalog', [
    (None, (), (), False),
    ('another_service', (), (), False),
    ('bvbrc_appservice', (), ('launch', 'results'), False),
    ('bvbrc_appservice', (('bvbrc_tnseq', '1'),), ('launch', 'results'), True),
    ('bvbrc_appservice', (('bvbrc_rnaseq', '1'),), ('launch', 'results'), True),
    ('bvbrc_appservice', (('unrelated_adapter', '1'),), ('launch', 'results'), False),
])
def test_original_appservice_child_gate_and_scientific_catalog_are_distinct(
        service, adapters, expected_children, expected_catalog):
    from gene_annotation_episode.episodic_workflow.root.a106.library import standalone_intervention_execution as intervention_execution

    resource = SimpleNamespace(service=service, scientific_adapters=adapters)
    binding = SimpleNamespace(api_execution=SimpleNamespace(services={'original': resource}))

    class ConfiguredProvider:
        roles = () if service is None else ('results',)

        def for_role(self, role):
            assert role == 'results'
            return binding

        def for_context_role(self, role, *, path=None, owner=None):
            assert path is None and owner is None
            return self.for_role(role)

    services = SimpleNamespace(workflow=SimpleNamespace(episode_bindings=ConfiguredProvider()))
    assert intervention_execution.analysis_children(services) == expected_children
    catalog = intervention_execution.contract_catalog(services)
    assert bool(catalog) is expected_catalog
    if expected_catalog:
        entry, = catalog
        assert entry['name'] == intervention_execution.CONTRACT_OPERATION
        assert entry['input_schema']['properties']['resource_id']['enum'] == ['original']
