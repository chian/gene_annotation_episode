"""Configured execution hooks, actual library selection and child contracts."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_gene_tree_bundle_adapter as gene
from gene_annotation_episode import bvbrc_codon_tree_bundle_adapter as codon
from gene_annotation_episode.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_homology_tool_info import factory
from test_bvbrc_phylogeny_host_integration import MODES, configured, supplied


def rows(family):
    return {row['name']: row for row in bound_resource_tool_contracts(family)
        if row['name'].startswith(('bvbrc.gene_tree.', 'bvbrc.codon_tree.'))}


@pytest.mark.parametrize('mode', MODES)
def test_configured_mode_reaches_library_and_actual_selected_service(factory, tmp_path, mode):
    create, registry = factory
    case = supplied(mode)
    family = create({'selected-api': configured(case.module)})
    available = family.resource_tool_contracts()
    expected = 'bvbrc.'+('codon_tree' if mode == MODES[2] else 'gene_tree')+'.'+mode
    entry = rows(family)[expected]
    assert entry['name'] not in registry.catalog()
    assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
        'service': 'bvbrc_appservice', 'request': case.request, 'endpoint': 'usable_handoff', 'constraints': {}}
    result = {'version': 'execution_results_assignment_v1',
        'handoff_ref': 'requires-actual-handoff-at-commission', 'selector': case.selector}
    validator = Draft202012Validator(entry['input_schema'])
    for payload in (assignment, result):
        assert validator.is_valid(payload), list(validator.iter_errors(payload))
    assert family.api_execution.validate_assignment(assignment) == assignment
    assert family.api_execution.services['selected-api'].result_catalog(case.request, case.selector)
    library = ScientificToolLibrary.freeze(tmp_path/'library', catalog=[], tool_info=True,
        resource_catalogs={'api': available})
    retrieved = library.retrieve_literal_test('BV-BRC GeneTree CodonTree relationships', available)
    assert expected in {row['name'] for row in retrieved['child_tool_info']}
    assert all(set(row) == {'name', 'description', 'resources'} for row in retrieved['child_tool_info'])
    selection = [{'name': expected, 'resources': 'api'}]
    instructions, = library.resolve_tool_info(selection, available)
    invocation, = library.resolve_invocations(selection, available)
    assert set(instructions) == {'name', 'description', 'resources', 'instructions'}
    assert invocation['instructions'] == instructions['instructions'] == entry['instructions']
    assert invocation['input_schema'] == entry['input_schema']
    assert invocation['invocation_route']['routes'] == [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]


def test_each_actual_provider_is_advertised_only_when_bound(factory):
    create, _ = factory
    assert rows(create({'selected-api': deepcopy(CONFIG)})) == {}
    for module, count, prefix in ((gene, 2, 'bvbrc.gene_tree.'), (codon, 1, 'bvbrc.codon_tree.')):
        values = rows(create({'selected-api': configured(module)}))
        assert len(values) == count and all(name.startswith(prefix) for name in values)
    both = configured(gene)
    both['scientific_adapters'] += configured(codon)['scientific_adapters']
    assert len(rows(create({'selected-api': both}))) == 3


def test_two_resources_preserve_explicit_options_without_selecting_one(factory):
    create, _ = factory
    family = create({'first-api': configured(gene), 'second-api': configured(gene)})
    for name, entry in rows(family).items():
        mode = name.rsplit('.', 1)[1]
        case = supplied(mode)
        validator = Draft202012Validator(entry['input_schema'])
        for resource in ('first-api', 'second-api', 'unbound-api'):
            value = {'version': 'api_service_assignment_v1', 'resource_id': resource,
                'service': 'bvbrc_appservice', 'request': case.request,
                'endpoint': 'usable_handoff', 'constraints': {}}
            assert validator.is_valid(value) == (resource != 'unbound-api')
        assert {route['resource_id'] for route in entry['invocation_route']['routes']} == {
            'first-api', 'second-api'}
        assert len(entry['invocation_route']['routes']) == 4
