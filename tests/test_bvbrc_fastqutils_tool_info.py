"""Configured selection reaches real child invocation contracts and form compiler."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_returns import fastqutils_fact_sources, parent_form_schema
from gene_annotation_episode.bvbrc_fastqutils_tool_info import fastqutils_tool_contracts
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.workflow_values import _compile_form
from gene_annotation_episode.episodic_workflow.root.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.root.a101.tests.test_bvbrc_homology_tool_info import factory
from test_api_bvbrc_appservice import CONFIG, original_request
from test_bvbrc_appservice_custody import api_assignment
from test_bvbrc_fastqutils_returns import f


def configured():
    value = deepcopy(CONFIG)
    value['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION}]
    return value


def query():
    request = original_request()
    request['required_application_id'] = 'FastqUtils'
    request['parameters'] = {'paired_end_libs': [{'read1': '/input/first.fq', 'read2': None}],
        'single_end_libs': [{'read': '/input/second.fq'}], 'srr_libs': [],
        'recipe': ['FASTQC', 'TRIM', 'FASTQC'], 'output_path': '/selected/output', 'output_file': 'reads'}
    return request


def entry(family):
    return fastqutils_tool_contracts(resource_id='selected-api',
        assignment_schema=family.api_execution.assignment_schema('selected-api'))[0]


def test_bound_library_supplies_parent_information_and_child_instructions(factory, tmp_path):
    create, registry = factory
    family = create({'selected-api': configured()})
    row = entry(family)
    catalogs = {'api': [item for item in family.resource_tool_contracts() if item['resources'] == 'api']}
    assert row in catalogs['api'] and row['name'] not in registry.catalog()
    assert row['name'] not in {item['name'] for item in create({'selected-api': deepcopy(CONFIG)}).resource_tool_contracts()}
    library = ScientificToolLibrary.freeze(tmp_path / 'library', catalog=[], resource_catalogs=catalogs)
    selected = [{'name': row['name'], 'resources': 'api'}]
    assert library.resolve_tool_info(selected, catalogs['api']) == [
        {key: row[key] for key in ('name', 'description', 'resources', 'instructions')}]
    assert library.parent_tool_info([row]) == [{key: row[key] for key in ('name', 'description', 'resources')}]
    assert library.resolve_invocations(selected, catalogs['api']) == [row]
    assert row['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]}


@pytest.mark.parametrize('change', ['empty_inputs', 'recipe', 'output', 'resource', 'application'])
def test_tool_contract_rejects_incomplete_or_unselected_operands(factory, change):
    create, _ = factory
    family = create({'selected-api': configured()})
    value = api_assignment(query())
    params = value['request']['parameters']
    if change == 'empty_inputs': params.update(paired_end_libs=[], single_end_libs=[], srr_libs=[])
    elif change == 'recipe': params['recipe'] = []
    elif change == 'output': params.pop('output_path')
    elif change == 'resource': value['resource_id'] = 'not-selected'
    else: value['request']['required_application_id'] = 'Homology'
    assert not Draft202012Validator(entry(family)['input_schema']).is_valid(value)


def test_seven_sources_reach_actual_workflow_form_compiler(factory):
    create, _ = factory
    family = create({'selected-api': configured()})
    data, fields = f.seven_family_data()
    schema = parent_form_schema(validate_requested_form(f.schema(fields)))
    definitions = fastqutils_fact_sources()
    assert len(definitions) == 7
    workflow = SimpleNamespace(job_episodes=None, native_event_information=None, native_timing_information=None,
        project_annotation_score=None, resource_estimator=None, episode_bindings=EpisodeBindingRegistry([family]))
    for role in ('results', 'scientific_process', 'annotation'):
        sources = Workflow.report_sources(workflow, role)
        assert set(definitions) <= sources.keys()
        assert _compile_form(json.dumps(schema), sources) == schema
