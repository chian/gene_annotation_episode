"""Actual resource factory/catalog, closed form and selected instruction binding."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator
from gene_annotation_episode import bvbrc_comparative_systems_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_comparative_systems_tool_info import comparative_systems_tool_contracts
from gene_annotation_episode.bvbrc_comparative_systems_returns import comparative_systems_fact_sources, parent_form_schema
from gene_annotation_episode.bvbrc_comparative_systems_fact_contracts import requested_selection
from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.runtime import Workflow, _compile_form
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from types import SimpleNamespace
from test_bvbrc_homology_tool_info import factory
from test_bvbrc_comparative_systems_episode_flow import query, result_selector
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_custody import api_assignment


def configured():
    value = deepcopy(CONFIG)
    value['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
        'implementation_sha256': adapter.implementation_sha256()}]
    return value


def entry(family):
    return comparative_systems_tool_contracts(resource_id='selected-api',
        assignment_schema=family.api_execution.assignment_schema('selected-api'))[0]


def test_exact_installed_adapter_actual_resource_catalog_and_selected_information(factory, tmp_path):
    create, registry = factory
    family = create({'selected-api': configured()})
    row = entry(family)
    catalogs = {'api': [item for item in family.resource_tool_contracts() if item['resources'] == 'api']}
    assert row in catalogs['api']
    assert row['name'] not in registry.catalog()
    absent = create({'selected-api': deepcopy(CONFIG)})
    assert row['name'] not in {item['name'] for item in absent.resource_tool_contracts()}
    library = ScientificToolLibrary.freeze(tmp_path / 'library', catalog=[], tool_info=True,
        resource_catalogs=catalogs)
    selection = [{'name': row['name'], 'resources': 'api'}]
    assert library.resolve_tool_info(selection, catalogs['api']) == [{key: row[key] for key in ('name','description','resources','instructions')}]
    assert library.resolve_invocations(selection, catalogs['api']) == [row]
    assert library.parent_tool_info([row]) == [{key: row[key] for key in ('name','description','resources')}]
    assert 'all three native views' in row['instructions']
    assert 'possessed_artifact' in row['instructions']


def test_original_two_arrays_and_output_survive_real_assignment_validation(factory):
    create, _ = factory
    family = create({'selected-api': configured()})
    value = api_assignment(query())
    value['request']['parameters']['genome_groups'] = ['/selected/groups/a', '/selected/groups/a']
    original = deepcopy(value)
    assert Draft202012Validator(entry(family)['input_schema']).is_valid(value)
    assert family.api_execution.validate_assignment(value) == original
    assert value == original
    results = {'version':'execution_results_assignment_v1','handoff_ref':'source_actual_required','selector':result_selector()}
    validator = Draft202012Validator(entry(family)['input_schema'])
    assert validator.is_valid(results), list(validator.iter_errors(results))
    results['selector']['adapter']['parameters']['document_selection']['documents'][0]['role'] = 'invented'
    assert not validator.is_valid(results)


@pytest.mark.parametrize('wrong', ['missing_ids','missing_groups','string_ids','empty_both','empty_member','missing_output','wrong_resource'])
def test_invalid_actual_launch_operands_rejected(factory, wrong):
    create, _ = factory
    family = create({'selected-api': configured()})
    value = api_assignment(query())
    params = value['request']['parameters']
    if wrong == 'missing_ids': params.pop('genome_ids')
    elif wrong == 'missing_groups': params.pop('genome_groups')
    elif wrong == 'string_ids': params['genome_ids'] = '1.1'
    elif wrong == 'empty_both': params.update(genome_ids=[], genome_groups=[])
    elif wrong == 'empty_member': params['genome_groups'] = [' ']
    elif wrong == 'missing_output': params.pop('output_path')
    else: value['resource_id'] = 'unselected'
    assert not Draft202012Validator(entry(family)['input_schema']).is_valid(value)
    with pytest.raises(ValueError): family.api_execution.validate_assignment(value)


def test_seven_finite_sources_reach_real_workflow_schema_compiler(factory):
    create, _ = factory
    family = create({'selected-api': configured()})
    definitions = comparative_systems_fact_sources()
    assert len(definitions) == 7
    workflow = SimpleNamespace(job_episodes=None, native_event_information=None, native_timing_information=None,
        project_annotation_score=None, resource_estimator=None, episode_bindings=EpisodeBindingRegistry([family]))
    parent = parent_form_schema(requested_selection(result_selector()['requested_schema']))
    validate_closed_schema(parent)
    for role in ('results', 'scientific_process', 'annotation'):
        sources = Workflow.report_sources(workflow, role)
        assert set(definitions) <= sources.keys()
        assert _compile_form(json.dumps(parent), sources) == parent


def test_cached_schema_templates_remain_detached_and_equal():
    from gene_annotation_episode.bvbrc_comparative_systems_returns import _fact_source_templates
    before=_fact_source_templates.__wrapped__()
    value=comparative_systems_fact_sources()
    assert value==before
    first=next(iter(value))
    value[first]['report_schema']['items']['properties'].clear()
    assert comparative_systems_fact_sources()==before
