"""Only explicitly bound versions appear in the real tool-information route."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_proteome_bundle_adapter as v1
from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as v2
from gene_annotation_episode.bvbrc_proteome_tool_info import proteome_tool_contracts, _INSTRUCTIONS
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_homology_tool_info import factory
from test_bvbrc_proteome_tool_info import launch, results as legacy_results
from test_bvbrc_proteome_bundle_v2_resolution import fixture, selector


@pytest.mark.parametrize('versions', [('1',), ('2',), ('1', '2'), ('2', '1')])
def test_actual_library_selects_only_bound_versioned_result_contracts(factory, tmp_path, versions):
    create, registry = factory
    config = deepcopy(CONFIG)
    adapters = {'1': v1, '2': v2}
    config['scientific_adapters'] = [dict(adapter_id='bvbrc_proteome', adapter_version=v,
        implementation_sha256=adapters[v].implementation_sha256()) for v in versions]
    family = create({'selected-api': config})
    entries = [row for row in family.resource_tool_contracts() if row['name'] == 'bvbrc.proteome_comparison']
    assert len(entries) == 1
    entry = entries[0]
    check = Draft202012Validator(entry['input_schema'])
    assert check.is_valid(launch())
    assert check.is_valid(legacy_results()) == ('1' in versions)
    result = dict(version='execution_results_assignment_v1', handoff_ref='source_actual_handoff_required', selector=selector(fixture()))
    assert check.is_valid(result) == ('2' in versions)
    result['selector']['adapter']['adapter_version'] = '3'
    assert not check.is_valid(result)
    if versions == ('1',): assert entry['instructions'] == _INSTRUCTIONS
    if '2' in versions:
        for phrase in ('1e-900', 'directional_calculation_parameters', 'directional_support',
            'resolved', 'half-open', 'unbound', 'requirement_id', 'ratio_decimal_places'):
            assert phrase in entry['instructions']
    library = ScientificToolLibrary.freeze(tmp_path / 'library', catalog=[], tool_info=True, resource_catalogs={'api': [entry]})
    selection = [{'name': entry['name'], 'resources': 'api'}]
    assert library.parent_tool_info([entry]) == [{key: entry[key] for key in ('name', 'description', 'resources')}]
    assert library.resolve_tool_info(selection, [entry]) == [{key: entry[key] for key in ('name', 'description', 'resources', 'instructions')}]
    assert library.resolve_invocations(selection, [entry]) == [entry]
    assert entry['name'] not in registry.catalog()


@pytest.mark.parametrize('versions', [(), ('1', '1'), ('2', '2'), ('3',), ['2'], '2', (True,)])
def test_invalid_or_implicit_version_selection_rejected(factory, versions):
    create, _ = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    with pytest.raises(ValueError, match='adapter_versions'):
        proteome_tool_contracts(resource_id='selected-api', assignment_schema=family.api_execution.assignment_schema('selected-api'),
                               adapter_versions=versions)
